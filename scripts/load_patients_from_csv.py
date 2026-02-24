"""
Script para carga masiva de pacientes desde CSV con citas recurrentes.

Crea los pacientes en la BD y genera un evento recurrente semanal (RRULE)
en el Google Calendar del profesional asignado, reutilizando
GoogleCalendarService.create_recurring_appointment().

Columnas REQUERIDAS del CSV:
    phone, name, professional_phone, weekday, start_time, duration_minutes

Columnas OPCIONALES:
    email, modality, notes

Uso:
    python scripts/load_patients_from_csv.py pacientes.csv
    python scripts/load_patients_from_csv.py pacientes.csv --weeks 20
    python scripts/load_patients_from_csv.py pacientes.csv --dry-run
    python scripts/load_patients_from_csv.py --template
"""

import sys
import csv
import argparse
from pathlib import Path
from datetime import timedelta, date
from typing import Optional

sys.path.append('.')

from src.database.database import db
from src.integrations.google_calendar_service import GoogleCalendarService

# ── Constantes ────────────────────────────────────────────────────────────────

DEFAULT_WEEKS    = 12
WEEKS_FOREVER    = 520  # ~10 años, equivalente a 'sin fecha límite'
DEFAULT_DURATION = 50
TIMEZONE         = 'America/Argentina/Buenos_Aires'

WEEKDAY_MAP = {
    'lunes': 0,     'monday': 0,    'mon': 0,   '0': 0,
    'martes': 1,    'tuesday': 1,   'tue': 1,   '1': 1,
    'miércoles': 2, 'miercoles': 2, 'wednesday': 2, 'wed': 2, '2': 2,
    'jueves': 3,    'thursday': 3,  'thu': 3,   '3': 3,
    'viernes': 4,   'friday': 4,    'fri': 4,   '4': 4,
    'sábado': 5,    'sabado': 5,    'saturday': 5, 'sat': 5, '5': 5,
    'domingo': 6,   'sunday': 6,    'sun': 6,   '6': 6,
}

RRULE_DAY = {0: 'MO', 1: 'TU', 2: 'WE', 3: 'TH', 4: 'FR', 5: 'SA', 6: 'SU'}

# ── Helpers ───────────────────────────────────────────────────────────────────

def parse_weekday(value: str) -> Optional[int]:
    return WEEKDAY_MAP.get(value.strip().lower())


def next_weekday_date(target: int) -> date:
    """Próxima fecha que cae en el día target (0=lunes). Si hoy es ese día, retorna hoy."""
    today = date.today()
    days  = (target - today.weekday()) % 7
    return today + timedelta(days=days)


def add_minutes(time_str: str, minutes: int) -> str:
    """Suma minutos a HH:MM y retorna HH:MM."""
    h, m  = map(int, time_str.split(':'))
    total = h * 60 + m + minutes
    return f"{total // 60:02d}:{total % 60:02d}"


def build_rrule(weekday_idx: int, until: date) -> str:
    """Construye RRULE semanal hasta la fecha indicada."""
    day = RRULE_DAY[weekday_idx]
    end = until.strftime('%Y%m%dT235959Z')
    return f'RRULE:FREQ=WEEKLY;BYDAY={day};UNTIL={end}'


def dt_iso(d: date, t: str) -> str:
    """Combina fecha + hora en formato ISO con offset Argentina."""
    return f"{d.isoformat()}T{t}:00-03:00"


def sep(c='=', w=70): print(c * w)

# ── Carga principal ───────────────────────────────────────────────────────────

def load_patients(csv_path: str, weeks: int, dry_run: bool):
    if not Path(csv_path).exists():
        print(f"❌ Archivo no encontrado: {csv_path}")
        sys.exit(1)

    until_date = date.today() + timedelta(weeks=weeks)

    print()
    sep()
    print("📋 CARGA DE PACIENTES CON CITAS RECURRENTES")
    sep()
    print(f"   Archivo : {csv_path}")
    print(f"   Semanas : {weeks}  (hasta {until_date})")
    print(f"   Modo    : {'🔍 DRY RUN' if dry_run else '✍️  Escritura real'}")
    print()

    # Inicializar servicio de Calendar una sola vez
    calendar_service = GoogleCalendarService()

    stats    = {'total': 0, 'ok': 0, 'errores': 0}
    errores  = []

    try:
        with open(csv_path, encoding='utf-8') as f:
            reader = csv.DictReader(f)

            # Validar columnas requeridas
            required = ['phone', 'name', 'professional_phone',
                        'weekday', 'start_time', 'duration_minutes']
            missing  = [c for c in required if c not in (reader.fieldnames or [])]
            if missing:
                print(f"❌ Faltan columnas: {', '.join(missing)}")
                sys.exit(1)

            for row in reader:
                stats['total'] += 1
                n = stats['total']

                # ── Leer campos ───────────────────────────────────────────
                phone            = row['phone'].strip()
                name             = row['name'].strip()
                prof_phone       = row['professional_phone'].strip()
                weekday_str      = row['weekday'].strip()
                start_time       = row['start_time'].strip()
                duration_minutes = int(row['duration_minutes'].strip() or DEFAULT_DURATION)

                # Opcionales
                email    = row.get('email',    '').strip() or None
                modality = row.get('modality', 'presencial').strip() or 'presencial'
                notes    = row.get('notes',    '').strip() or None

                sep('-')
                print(f"Fila {n}: {name} ({phone})")
                sep('-')

                # ── Validar día ───────────────────────────────────────────
                weekday_idx = parse_weekday(weekday_str)
                if weekday_idx is None:
                    msg = f"Día inválido: '{weekday_str}'"
                    print(f"   ❌ {msg}")
                    stats['errores'] += 1
                    errores.append((n, name, msg))
                    continue

                # ── Validar profesional y calendar_id ─────────────────────
                professional = db.get_professional(prof_phone)
                if not professional:
                    msg = f"Profesional no encontrado: {prof_phone}"
                    print(f"   ❌ {msg}")
                    print(f"      💡 ¿Ya cargaste los profesionales?")
                    print(f"         docker exec whatsapp-demo python scripts/load_professionals_from_csv.py /app/data/csv/profesionales_demo.csv")
                    stats['errores'] += 1
                    errores.append((n, name, msg))
                    continue

                calendar_id = professional.get('calendar_id')
                if not calendar_id:
                    msg = "El profesional no tiene calendar_id configurado"
                    print(f"   ❌ {msg}")
                    stats['errores'] += 1
                    errores.append((n, name, msg))
                    continue

                # ── Calcular horarios ─────────────────────────────────────
                end_time   = add_minutes(start_time, duration_minutes)
                first_date = next_weekday_date(weekday_idx)
                rrule      = build_rrule(weekday_idx, until_date)

                print(f"   👤 Paciente    : {name} ({phone})")
                print(f"   👨‍⚕️ Profesional : {professional['name']}")
                print(f"   📅 Día         : {weekday_str} | {start_time}–{end_time} ({duration_minutes} min)")
                print(f"   📆 Primera     : {first_date}")
                print(f"   🔁 RRULE       : {rrule}")

                if dry_run:
                    print(f"   🔍 DRY RUN: se crearía evento recurrente hasta {until_date}")
                    stats['ok'] += 1
                    continue

                # ── 1. Crear/actualizar paciente en BD ────────────────────
                db.add_client(phone=phone, name=name, email=email)
                print(f"   ✅ Paciente en BD")

                # ── 2. Crear evento recurrente en Google Calendar ─────────
                try:
                    created = calendar_service.create_recurring_appointment(
                        calendar_id    = calendar_id,
                        start_datetime = dt_iso(first_date, start_time),
                        end_datetime   = dt_iso(first_date, end_time),
                        client_name    = name,
                        client_phone   = phone,
                        rrule          = rrule,
                        modality       = modality,
                        email          = email,
                        notes          = notes,
                        timezone_str   = TIMEZONE,
                    )
                    google_event_id = created['id']
                    print(f"   ✅ Google Calendar : {google_event_id}")

                except Exception as e:
                    msg = f"Error Google Calendar: {e}"
                    print(f"   ❌ {msg}")
                    stats['errores'] += 1
                    errores.append((n, name, msg))
                    continue

                # ── 3. Guardar primera ocurrencia en BD ───────────────────
                appointment_id = db.create_appointment(
                    client_phone       = phone,
                    professional_phone = prof_phone,
                    appointment_date   = first_date.isoformat(),
                    start              = start_time,
                    end                = end_time,
                    duration_minutes   = duration_minutes,
                    session_type       = 'seguimiento',
                    modality           = modality,
                    google_event_id    = google_event_id,
                    notes              = notes,
                )

                if appointment_id:
                    print(f"   ✅ Cita en BD      : #{appointment_id}")
                    stats['ok'] += 1
                else:
                    print(f"   ⚠️  Evento en Calendar creado, pero falló el guardado en BD")
                    stats['ok'] += 1   # Calendar está ok; BD se puede reintentar

    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)

    # ── Resumen ───────────────────────────────────────────────────────────────
    print()
    sep()
    print("📊 RESUMEN")
    sep()
    print(f"   Total procesados : {stats['total']}")
    print(f"   ✅ Exitosos       : {stats['ok']}")
    print(f"   ❌ Errores        : {stats['errores']}")

    if errores:
        print()
        print("   Detalle de errores:")
        for row_n, pname, msg in errores:
            print(f"   Fila {row_n}: {pname} → {msg}")

    if dry_run:
        print(f"\n⚠️  DRY RUN: ningún dato fue modificado.")

    print()
    sep()
    print("✅ PROCESO COMPLETADO")
    sep()
    print()


# ── Template ──────────────────────────────────────────────────────────────────

def create_template():
    path = 'pacientes_template.csv'
    with open(path, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['phone', 'name', 'professional_phone', 'weekday',
                    'start_time', 'duration_minutes', 'email', 'modality', 'notes'])
        w.writerow(['+5491112345678', 'Juan Pérez',   '+5491100000001', 'martes',  '10:00', '50', 'juan@email.com', 'presencial', ''])
        w.writerow(['+5491187654321', 'María García',  '+5491100000002', 'jueves',  '14:00', '50', '',               'virtual',    ''])
        w.writerow(['+5491156789012', 'Carlos López',  '+5491100000001', 'viernes', '09:00', '50', '',               'presencial', 'Paciente fijo'])

    print(f"✅ Template creado: {path}")
    print(f"\nRequeridas : phone, name, professional_phone, weekday, start_time, duration_minutes")
    print(f"Opcionales : email, modality, notes")
    print(f"\nDías válidos: lunes, martes, miércoles, jueves, viernes, sábado, domingo")
    print(f"\nEjecutar con:")
    print(f"   python scripts/load_patients_from_csv.py {path}")


# ── CLI ───────────────────────────────────────────────────────────────────────



def pick_weeks() -> int:
    """
    Pregunta al usuario por cuánto tiempo crear la recurrencia.
    Retorna la cantidad de semanas seleccionada.
    """
    opciones = [
        (4,             "4 semanas   (~1 mes)"),
        (DEFAULT_WEEKS, "12 semanas  (~3 meses, recomendado)"),
        (WEEKS_FOREVER, "Sin límite  (~10 años)"),
    ]

    print()
    sep()
    print("📅 ¿HASTA CUÁNDO REPETIR LAS SESIONES?")
    sep()
    for i, (_, label) in enumerate(opciones, 1):
        print(f"   {i}. {label}")
    print()

    while True:
        try:
            raw = input("Seleccioná una opción [1-3]: ").strip()
            idx = int(raw) - 1
            if 0 <= idx < len(opciones):
                weeks, label = opciones[idx]
                print(f"   ✅ Seleccionado: {label.strip()}")
                print()
                return weeks
            else:
                print("   ⚠️  Ingresá 1, 2 o 3")
        except (ValueError, KeyboardInterrupt):
            print("\n   Cancelado.")
            sys.exit(0)


CSV_DIR = Path('/app/data/csv')


def pick_csv() -> str:
    """
    Lista los CSV disponibles en CSV_DIR y pide al usuario que elija uno.
    Retorna la ruta absoluta al archivo seleccionado.
    """
    csv_files = sorted(CSV_DIR.glob('*.csv')) if CSV_DIR.exists() else []

    if not csv_files:
        print(f"❌ No se encontraron archivos CSV en {CSV_DIR}")
        print(f"   Asegurate de montar la carpeta data/ en docker-compose.yml")
        sys.exit(1)

    print()
    sep()
    print("📂 CSV DISPONIBLES")
    sep()
    for i, f in enumerate(csv_files, 1):
        print(f"   {i}. {f.name}")
    print()

    while True:
        try:
            raw = input(f"Seleccioná un archivo [1-{len(csv_files)}]: ").strip()
            idx = int(raw) - 1
            if 0 <= idx < len(csv_files):
                selected = str(csv_files[idx])
                print(f"   ✅ Seleccionado: {csv_files[idx].name}")
                print()
                return selected
            else:
                print(f"   ⚠️  Ingresá un número entre 1 y {len(csv_files)}")
        except (ValueError, KeyboardInterrupt):
            print("\n   Cancelado.")
            sys.exit(0)


def main():
    parser = argparse.ArgumentParser(
        description='Carga masiva de pacientes con citas recurrentes en Google Calendar.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python scripts/load_patients_from_csv.py pacientes.csv
  python scripts/load_patients_from_csv.py pacientes.csv --weeks 20
  python scripts/load_patients_from_csv.py pacientes.csv --dry-run
  python scripts/load_patients_from_csv.py --template
        """
    )
    parser.add_argument('csv_path', nargs='?',  help='Ruta al CSV de pacientes')
    parser.add_argument('--weeks',   type=int,  default=None, metavar='N',
                        help=f'Semanas de recurrencia hacia adelante (default: interactivo si no se especifica)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Simula la carga sin escribir nada')
    parser.add_argument('--template', action='store_true',
                        help='Genera pacientes_template.csv y termina')

    args = parser.parse_args()

    if args.template:
        create_template()
        return

    if not args.csv_path:
        # Sin path → preguntar CSV interactivamente
        args.csv_path = pick_csv()

    if args.weeks is None:
        # Sin --weeks explícito → preguntar duración interactivamente
        args.weeks = pick_weeks()

    load_patients(args.csv_path, args.weeks, args.dry_run)


if __name__ == '__main__':
    main()