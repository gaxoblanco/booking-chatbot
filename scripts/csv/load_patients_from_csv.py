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

     docker exec -it whatsapp-demo python3 scripts/csv/load_patients_from_csv.py /app/data/csv/pacientes_demo.csv --weeks 4
     docker exec -it whatsapp-demo python3 scripts/csv/delete_patients_from_csv.py /app/data/csv/pacientes_demo.csv
"""

import sys
import csv
import argparse
from pathlib import Path
from datetime import timedelta, date, datetime
from typing import Optional, List, Dict

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
    """Construye RRULE semanal hasta la fecha indicada.
    DEPRECATED: usar build_rrule_from_sessions() para soportar múltiples frecuencias.
    """
    day = RRULE_DAY[weekday_idx]
    end = until.strftime('%Y%m%dT235959Z')
    return f'RRULE:FREQ=WEEKLY;BYDAY={day};UNTIL={end}'


# Valores válidos de sessions_per_month y su descripción legible
VALID_SESSIONS_PER_MONTH = {
    1: 'mensual',
    2: 'quincenal',
    4: 'semanal',
}
# Nota: 3 sesiones/mes no está soportado por limitaciones del estándar RRULE.
# El sistema rechaza filas con sessions_per_month=3 con mensaje explicativo.

DEFAULT_SESSIONS_PER_MONTH = 4  # semanal — compatibilidad con CSVs existentes sin la columna

# Valores válidos de week_of_month (solo aplica para sessions_per_month=1)
# -1 = último del mes, 1-4 = 1ra a 4ta semana del mes
VALID_WEEK_OF_MONTH = {-1, 1, 2, 3, 4}


def week_of_month(d: date) -> int:
    """
    Retorna qué número de semana dentro del mes es la fecha d.
    Ejemplo: si d es el 2do miércoles del mes → retorna 2.
    Si cae en la 5ta semana → retorna -1 (último del mes, más robusto en RRULE).
    """
    nth = (d.day - 1) // 7 + 1
    return -1 if nth == 5 else nth


def build_rrule_from_sessions(weekday_idx: int, until: date, sessions_per_month: int,
                               first_date: date,
                               week_of_month_override: Optional[int] = None) -> str:
    """
    Construye la RRULE correcta según la frecuencia mensual deseada.

    Args:
        weekday_idx:            Día de la semana (0=lunes ... 6=domingo)
        until:                  Fecha límite de la recurrencia
        sessions_per_month:     Frecuencia mensual — solo acepta 1, 2 o 4
        first_date:             Primera fecha real de la sesión
        week_of_month_override: Semana del mes explícita para casos mensuales.
                                Valores válidos: 1, 2, 3, 4, -1 (último).
                                Si es None, se infiere desde first_date.
                                Solo aplica cuando sessions_per_month=1, se ignora en otros casos.

    Returns:
        String RRULE válido para Google Calendar API

    Raises:
        ValueError: si sessions_per_month no es 1, 2 ni 4

    Ejemplos:
        sessions_per_month=4                    → RRULE:FREQ=WEEKLY;INTERVAL=1;BYDAY=MO;UNTIL=...
        sessions_per_month=2                    → RRULE:FREQ=WEEKLY;INTERVAL=2;BYDAY=MO;UNTIL=...
        sessions_per_month=1, override=None     → RRULE:FREQ=MONTHLY;BYDAY=2MO;UNTIL=...  (inferido)
        sessions_per_month=1, override=1        → RRULE:FREQ=MONTHLY;BYDAY=1MO;UNTIL=...  (explícito)
        sessions_per_month=1, override=-1       → RRULE:FREQ=MONTHLY;BYDAY=-1MO;UNTIL=... (último)
    """
    if sessions_per_month not in VALID_SESSIONS_PER_MONTH:
        raise ValueError(
            f"sessions_per_month={sessions_per_month} no está soportado. "
            f"Valores válidos: {sorted(VALID_SESSIONS_PER_MONTH.keys())} "
            f"(3 sesiones/mes no es representable en RRULE estándar)"
        )

    day       = RRULE_DAY[weekday_idx]
    until_str = until.strftime('%Y%m%dT235959Z')

    if sessions_per_month == 4:
        # Semanal: cada 1 semana
        return f'RRULE:FREQ=WEEKLY;INTERVAL=1;BYDAY={day};UNTIL={until_str}'

    if sessions_per_month == 2:
        # Quincenal: cada 2 semanas
        return f'RRULE:FREQ=WEEKLY;INTERVAL=2;BYDAY={day};UNTIL={until_str}'

    if sessions_per_month == 1:
        # Mensual: usar week_of_month explícito si viene, sino inferir desde first_date
        if week_of_month_override is not None:
            nth = week_of_month_override
        else:
            nth = week_of_month(first_date)
        return f'RRULE:FREQ=MONTHLY;BYDAY={nth}{day};UNTIL={until_str}'


def dt_iso(d: date, t: str) -> str:
    """Combina fecha + hora en formato ISO con offset Argentina."""
    return f"{d.isoformat()}T{t}:00-03:00"


def sep(c='=', w=70): print(c * w)


def time_to_minutes(t: str) -> int:
    """Convierte HH:MM a minutos desde medianoche."""
    h, m = map(int, t.split(':'))
    return h * 60 + m


def check_overlap(prof_phone: str, weekday_idx: int, start_time: str,
                  end_time: str, patient_phone: str) -> Optional[Dict]:
    """
    Verifica si el horario propuesto solapa con alguna cita existente
    del profesional en ese día de la semana.

    Busca citas del profesional en la próxima ocurrencia del día,
    ya que la BD guarda la primera fecha real de cada cita recurrente.

    Args:
        prof_phone:    Teléfono del profesional
        weekday_idx:   Día de la semana (0=lunes ... 6=domingo)
        start_time:    Inicio propuesto "HH:MM"
        end_time:      Fin propuesto "HH:MM"
        patient_phone: Teléfono del paciente a cargar

    Returns:
        Dict con info del conflicto si hay solapamiento, None si está libre.
        Ejemplo: {'tipo': 'solapado', 'ocupado_por': 'Juan Pérez', 'inicio': '09:00', 'fin': '09:50'}
        O:       {'tipo': 'duplicado', 'ocupado_por': 'mismo paciente'}
    """
    # Calcular la próxima fecha del día de la semana
    target_date = next_weekday_date(weekday_idx).isoformat()

    # Obtener todas las citas del profesional en esa fecha
    try:
        with db.get_connection() as conn:
            conn.row_factory = __import__('sqlite3').Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT a.id, a.client_phone, a.start, a.end, c.name as client_name
                FROM appointments a
                LEFT JOIN clients c ON a.client_phone = c.phone
                WHERE a.professional_phone = ?
                AND a.appointment_date = ?
                AND a.status NOT IN ('cancelada_cliente', 'cancelada_profesional')
            """, (prof_phone, target_date))
            existing = [dict(r) for r in cursor.fetchall()]
    except Exception:
        return None  # Si falla la consulta, dejamos pasar

    new_start = time_to_minutes(start_time)
    new_end   = time_to_minutes(end_time)

    for apt in existing:
        apt_start = time_to_minutes(apt['start'])
        apt_end   = time_to_minutes(apt['end'])

        # Solapamiento: los rangos se tocan (excluimos el caso borde donde uno empieza justo cuando termina el otro)
        if new_start < apt_end and new_end > apt_start:
            # Caso 1: mismo paciente, mismo horario exacto → duplicado
            if apt['client_phone'] == patient_phone and apt['start'] == start_time:
                return {
                    'tipo':        'duplicado',
                    'ocupado_por': f"{apt['client_name'] or apt['client_phone']} (mismo paciente)",
                    'inicio':      apt['start'],
                    'fin':         apt['end'],
                }
            # Caso 2: horario solapado (mismo u otro paciente)
            return {
                'tipo':        'solapado',
                'ocupado_por': apt['client_name'] or apt['client_phone'],
                'inicio':      apt['start'],
                'fin':         apt['end'],
            }

    return None  # Sin conflicto


def write_rejected_csv(rechazados: List[Dict], output_dir: str = '/app/data/rechazados') -> str:
    """
    Escribe el CSV de pacientes no cargados.

    Args:
        rechazados: Lista de dicts con los datos del rechazo
        output_dir: Directorio de salida

    Returns:
        Ruta del archivo generado
    """
    today     = datetime.now().strftime('%Y-%m-%d')
    filename  = f"pacientes_no_cargados_{today}.csv"
    filepath  = Path(output_dir) / filename

    # Crear directorio si no existe
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    fieldnames = ['phone', 'name', 'professional_phone', 'weekday',
                  'start_time', 'duration_minutes', 'sessions_per_month', 'motivo', 'ocupado_por']

    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rechazados:
            writer.writerow({k: r.get(k, '') for k in fieldnames})

    return str(filepath)

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

    stats    = {'total': 0, 'ok': 0, 'errores': 0, 'rechazados': 0}
    errores  = []
    rechazados: List[Dict] = []  # Pacientes no cargados por conflicto de horario

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

                # sessions_per_month — opcional, default 4 (semanal)
                # Valores válidos: 1 (mensual), 2 (quincenal), 4 (semanal)
                # Valor 3 rechazado: no representable en RRULE estándar
                raw_spm = row.get('sessions_per_month', '').strip()
                if raw_spm == '':
                    sessions_per_month = DEFAULT_SESSIONS_PER_MONTH
                else:
                    try:
                        sessions_per_month = int(raw_spm)
                    except ValueError:
                        msg = f"sessions_per_month inválido: '{raw_spm}' (debe ser 1, 2 o 4)"
                        print(f"   ❌ {msg}")
                        stats['errores'] += 1
                        errores.append((n, name, msg))
                        continue

                    if sessions_per_month not in VALID_SESSIONS_PER_MONTH:
                        if sessions_per_month == 3:
                            msg = (
                                "sessions_per_month=3 no está soportado. "
                                "3 sesiones/mes no es representable en RRULE estándar. "
                                "Usá 2 (quincenal) o 4 (semanal) y coordiná la excepción manualmente."
                            )
                        else:
                            msg = (
                                f"sessions_per_month={sessions_per_month} inválido. "
                                f"Valores válidos: 1 (mensual), 2 (quincenal), 4 (semanal)"
                            )
                        print(f"   ❌ {msg}")
                        stats['errores'] += 1
                        errores.append((n, name, msg))
                        rechazados.append({
                            'phone': phone, 'name': name,
                            'professional_phone': prof_phone, 'weekday': weekday_str,
                            'start_time': start_time, 'duration_minutes': duration_minutes,
                            'sessions_per_month': sessions_per_month,
                            'motivo': msg, 'ocupado_por': '',
                        })
                        continue

                # week_of_month — opcional, solo aplica para sessions_per_month=1 (mensual)
                # Valores válidos: 1, 2, 3, 4, -1 (último del mes)
                # Si está vacío → se infiere automáticamente desde la primera fecha
                raw_wom = row.get('week_of_month', '').strip()
                week_of_month_override = None  # default: inferir desde first_date

                if raw_wom != '':
                    try:
                        week_of_month_override = int(raw_wom)
                    except ValueError:
                        msg = f"week_of_month inválido: '{raw_wom}' (debe ser 1, 2, 3, 4 o -1)"
                        print(f"   ❌ {msg}")
                        stats['errores'] += 1
                        errores.append((n, name, msg))
                        continue

                    if week_of_month_override not in VALID_WEEK_OF_MONTH:
                        msg = (
                            f"week_of_month={week_of_month_override} inválido. "
                            f"Valores válidos: 1, 2, 3, 4, -1 (último del mes)"
                        )
                        print(f"   ❌ {msg}")
                        stats['errores'] += 1
                        errores.append((n, name, msg))
                        continue

                    # Advertencia si se usa con frecuencia no mensual (no es error fatal)
                    if sessions_per_month != 1:
                        freq_label = VALID_SESSIONS_PER_MONTH[sessions_per_month]
                        print(f"   ⚠️  week_of_month={week_of_month_override} se ignora "
                              f"para frecuencia {freq_label} (solo aplica con sessions_per_month=1)")

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
                    rechazados.append({
                        'phone': phone, 'name': name,
                        'professional_phone': prof_phone, 'weekday': weekday_str,
                        'start_time': start_time, 'duration_minutes': duration_minutes,
                        'motivo': msg, 'ocupado_por': '',
                    })
                    continue

                calendar_id = professional.get('calendar_id')
                if not calendar_id:
                    msg = "El profesional no tiene calendar_id configurado"
                    print(f"   ❌ {msg}")
                    stats['errores'] += 1
                    errores.append((n, name, msg))
                    rechazados.append({
                        'phone': phone, 'name': name,
                        'professional_phone': prof_phone, 'weekday': weekday_str,
                        'start_time': start_time, 'duration_minutes': duration_minutes,
                        'motivo': msg, 'ocupado_por': '',
                    })
                    continue

                # ── Calcular horarios ─────────────────────────────────────
                end_time   = add_minutes(start_time, duration_minutes)
                first_date = next_weekday_date(weekday_idx)
                rrule      = build_rrule_from_sessions(weekday_idx, until_date,
                                                       sessions_per_month, first_date,
                                                       week_of_month_override)
                freq_label = VALID_SESSIONS_PER_MONTH[sessions_per_month]

                # Para mensual: mostrar qué semana del mes se usó (explícita o inferida)
                if sessions_per_month == 1:
                    nth_used   = week_of_month_override if week_of_month_override is not None \
                                 else week_of_month(first_date)
                    nth_origen = 'explícito' if week_of_month_override is not None else 'inferido'
                    wom_info   = f" | semana del mes: {nth_used} ({nth_origen})"
                else:
                    wom_info   = ''

                print(f"   👤 Paciente    : {name} ({phone})")
                print(f"   👨‍⚕️ Profesional : {professional['name']}")
                print(f"   📅 Día         : {weekday_str} | {start_time}–{end_time} ({duration_minutes} min)")
                print(f"   🔁 Frecuencia  : {freq_label} ({sessions_per_month}x/mes){wom_info}")
                print(f"   📆 Primera     : {first_date}")
                print(f"   🔁 RRULE       : {rrule}")

                if dry_run:
                    print(f"   🔍 DRY RUN: se crearía evento recurrente hasta {until_date}")
                    stats['ok'] += 1
                    continue

                # ── 0. Validar solapamiento antes de tocar Calendar ───────
                conflicto = check_overlap(
                    prof_phone    = prof_phone,
                    weekday_idx   = weekday_idx,
                    start_time    = start_time,
                    end_time      = end_time,
                    patient_phone = phone,
                )

                if conflicto:
                    if conflicto['tipo'] == 'duplicado':
                        motivo = f"Paciente ya cargado en ese horario"
                    else:
                        motivo = f"Horario solapado con {conflicto['inicio']}-{conflicto['fin']}"

                    ocupado_por = conflicto['ocupado_por']
                    print(f"   ⚠️  {motivo} — ocupado por: {ocupado_por}")

                    stats['rechazados'] += 1
                    rechazados.append({
                        'phone':             phone,
                        'name':              name,
                        'professional_phone': prof_phone,
                        'weekday':           weekday_str,
                        'start_time':        start_time,
                        'duration_minutes':  duration_minutes,
                        'motivo':            motivo,
                        'ocupado_por':       ocupado_por,
                    })
                    continue
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
    print(f"   ⚠️  Rechazados     : {stats['rechazados']}")
    print(f"   ❌ Errores        : {stats['errores']}")

    if errores:
        print()
        print("   Detalle de errores:")
        for row_n, pname, msg in errores:
            print(f"   Fila {row_n}: {pname} → {msg}")

    # ── Generar CSV de rechazados si hay alguno ───────────────────────────
    if rechazados and not dry_run:
        try:
            csv_path_out = write_rejected_csv(rechazados)
            print()
            print(f"   📄 CSV de no cargados: {csv_path_out}")
            print(f"      {len(rechazados)} paciente(s) requieren revisión del profesional")
        except Exception as e:
            print(f"\n   ⚠️  No se pudo generar CSV de rechazados: {e}")

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
        # Encabezado con todas las columnas
        w.writerow(['phone', 'name', 'professional_phone', 'weekday',
                    'start_time', 'duration_minutes', 'sessions_per_month',
                    'week_of_month', 'email', 'modality', 'notes'])
        # Semanal — week_of_month vacío (no aplica)
        w.writerow(['+5491112345678', 'Juan Pérez',   '+5491100000001', 'martes',  '10:00', '50', '4', '',  'juan@email.com', 'presencial', 'Semanal'])
        # Quincenal — week_of_month vacío (no aplica)
        w.writerow(['+5491187654321', 'María García', '+5491100000002', 'jueves',  '14:00', '50', '2', '',  '',               'virtual',    'Quincenal'])
        # Mensual con semana explícita — 1er viernes del mes
        w.writerow(['+5491156789012', 'Carlos López', '+5491100000001', 'viernes', '09:00', '50', '1', '1', '',               'presencial', 'Mensual - 1er viernes'])
        # Mensual con semana explícita — último jueves del mes
        w.writerow(['+5491198765432', 'Ana Martínez', '+5491100000001', 'jueves',  '11:00', '50', '1', '-1','',               'virtual',    'Mensual - último jueves'])
        # Mensual sin semana explícita — se infiere desde la primera fecha
        w.writerow(['+5491167891234', 'Pedro Suárez', '+5491100000002', 'lunes',   '16:00', '50', '1', '',  '',               'presencial', 'Mensual - semana inferida'])

    print(f"✅ Template creado: {path}")
    print(f"\nRequeridas : phone, name, professional_phone, weekday, start_time, duration_minutes")
    print(f"Opcionales : sessions_per_month (default: 4), week_of_month, email, modality, notes")
    print(f"\nValores de sessions_per_month:")
    print(f"   4 → semanal    (default, compatible con CSVs sin esta columna)")
    print(f"   2 → quincenal")
    print(f"   1 → mensual")
    print(f"   3 → NO soportado (rechazado con mensaje explicativo)")
    print(f"\nValores de week_of_month (solo aplica con sessions_per_month=1):")
    print(f"   1  → 1er semana del mes  (ej: 1er jueves)")
    print(f"   2  → 2da semana del mes")
    print(f"   3  → 3ra semana del mes")
    print(f"   4  → 4ta semana del mes")
    print(f"   -1 → última semana del mes")
    print(f"   vacío → se infiere automáticamente desde la primera fecha calculada")
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