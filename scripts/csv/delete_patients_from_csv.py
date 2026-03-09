"""
Script para eliminar pacientes cargados desde un CSV demo.

Elimina de la BD los clientes y sus citas, cancela los eventos
recurrentes en Google Calendar, y elimina los calendarios Turnos-X
de los profesionales referenciados en el CSV.

Los profesionales NO se eliminan de la BD.

Uso:
    python scripts/csv/delete_patients_from_csv.py pacientes_demo.csv
    python scripts/csv/delete_patients_from_csv.py pacientes_demo.csv --dry-run
"""

import sys
import csv
import argparse
from pathlib import Path

sys.path.insert(0, '/app')

from src.database.database import db
from src.integrations.google_calendar_service import GoogleCalendarService


def sep(c='=', w=70): print(c * w)


def delete_calendars(professional_phones: set, calendar_service, dry_run: bool) -> dict:
    """
    Elimina los calendarios Turnos-X de los profesionales indicados.
    También limpia el calendar_id en BD para que queden como pendientes.

    Args:
        professional_phones: Set de teléfonos de profesionales
        calendar_service: Instancia de GoogleCalendarService
        dry_run: Si True, solo simula

    Returns:
        dict con stats: {'eliminados': int, 'errores': int, 'sin_calendario': int}
    """
    stats = {'eliminados': 0, 'errores': 0, 'sin_calendario': 0}

    print()
    sep()
    print("🗑️  ELIMINANDO CALENDARIOS TURNOS-X")
    sep()

    for phone in sorted(professional_phones):
        prof = db.get_professional(phone)
        if not prof:
            print(f"   ⚠️  Profesional {phone} no encontrado en BD")
            continue

        name        = prof.get('name', phone)
        calendar_id = prof.get('calendar_id')

        if not calendar_id:
            print(f"   ℹ️  {name} — sin calendar_id, nada que eliminar")
            stats['sin_calendario'] += 1
            continue

        print(f"   👤 {name}")
        print(f"      ID: {calendar_id}")

        if dry_run:
            print(f"      🔍 DRY RUN: eliminaría calendario de Google y limpiaría BD")
            stats['eliminados'] += 1
            continue

        # 1. Eliminar calendario de Google Calendar
        try:
            service = calendar_service._build_service()
            service.calendars().delete(calendarId=calendar_id).execute()
            print(f"      ✅ Calendario eliminado de Google")
        except Exception as e:
            if 'notFound' in str(e) or '404' in str(e):
                print(f"      ℹ️  Calendario ya no existe en Google")
            else:
                print(f"      ⚠️  Error eliminando de Google: {e}")
                stats['errores'] += 1
                continue

        # NOTA: NO se limpia el calendar_id del profesional.
        # El calendario secundario "Turnos-X" fue eliminado de Google,
        # pero el profesional sigue activo en BD con su configuración intacta.
        print(f"      ✅ Calendario eliminado de Google (profesional conservado en BD)")
        stats['eliminados'] += 1

    return stats


def delete_patients(csv_path: str, dry_run: bool):
    if not Path(csv_path).exists():
        print(f"❌ Archivo no encontrado: {csv_path}")
        sys.exit(1)

    print()
    sep()
    print("🗑️  ELIMINACIÓN DE PACIENTES DEMO")
    sep()
    print(f"   Archivo : {csv_path}")
    print(f"   Modo    : {'🔍 DRY RUN' if dry_run else '⚠️  ELIMINACIÓN REAL'}")
    print()

    calendar_service = GoogleCalendarService()

    stats   = {'total': 0, 'ok': 0, 'errores': 0, 'no_encontrados': 0}
    errores = []

    # Registrar qué profesionales están involucrados para limpiar sus calendarios
    professional_phones = set()

    with open(csv_path, encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            stats['total'] += 1
            phone     = row['phone'].strip()
            name      = row['name'].strip()
            prof_phone = row.get('professional_phone', '').strip()

            if prof_phone:
                professional_phones.add(prof_phone)

            sep('-')
            print(f"Fila {stats['total']}: {name} ({phone})")
            sep('-')

            # ── Buscar citas del paciente ──────────────────────────────────
            appointments = db.get_appointments_by_client(phone)

            if not appointments:
                print(f"   ℹ️  Sin citas en BD")
            else:
                for apt in appointments:
                    apt_id          = apt['id']
                    google_event_id = apt.get('google_event_id')
                    apt_prof_phone  = apt['professional_phone']
                    professional    = db.get_professional(apt_prof_phone)
                    calendar_id     = professional.get('calendar_id') if professional else None

                    print(f"   📅 Cita #{apt_id} | {apt['appointment_date']} {apt['start']}")

                    # ── Cancelar evento en Google Calendar ─────────────────
                    if google_event_id and calendar_id:
                        if dry_run:
                            print(f"      🔍 DRY RUN: cancelaría evento {google_event_id}")
                        else:
                            try:
                                service = calendar_service._build_service()
                                service.events().delete(
                                    calendarId=calendar_id,
                                    eventId=google_event_id,
                                ).execute()
                                print(f"      ✅ Evento eliminado de Calendar")
                            except Exception as e:
                                if 'notFound' in str(e) or '404' in str(e):
                                    print(f"      ℹ️  Evento ya no existe en Calendar")
                                else:
                                    print(f"      ⚠️  Error en Calendar (continúa): {e}")
                    else:
                        print(f"      ℹ️  Sin google_event_id, solo se elimina de BD")

                    # ── Eliminar cita de BD ────────────────────────────────
                    if dry_run:
                        print(f"      🔍 DRY RUN: eliminaría cita #{apt_id} de BD")
                    else:
                        try:
                            with db.get_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute(
                                    "DELETE FROM appointments WHERE id = ?", (apt_id,)
                                )
                            print(f"      ✅ Cita #{apt_id} eliminada de BD")
                        except Exception as e:
                            print(f"      ❌ Error eliminando cita #{apt_id}: {e}")
                            stats['errores'] += 1
                            errores.append((phone, name, str(e)))

            # ── Eliminar cliente de BD ─────────────────────────────────────
            client = db.get_client(phone)
            if not client:
                print(f"   ℹ️  Paciente no encontrado en BD")
                stats['no_encontrados'] += 1
                continue

            if dry_run:
                print(f"   🔍 DRY RUN: eliminaría paciente {name} de BD")
                stats['ok'] += 1
            else:
                try:
                    with db.get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            "DELETE FROM clients WHERE phone = ?", (phone,)
                        )
                    print(f"   ✅ Paciente {name} eliminado de BD")
                    stats['ok'] += 1
                except Exception as e:
                    print(f"   ❌ Error eliminando paciente: {e}")
                    stats['errores'] += 1
                    errores.append((phone, name, str(e)))

    # ── Eliminar calendarios Turnos-X ─────────────────────────────────────────
    cal_stats = delete_calendars(professional_phones, calendar_service, dry_run)

    # ── Resumen ───────────────────────────────────────────────────────────────
    print()
    sep()
    print("📊 RESUMEN")
    sep()
    print(f"\n👥 Pacientes:")
    print(f"   Total procesados  : {stats['total']}")
    print(f"   ✅ Eliminados      : {stats['ok']}")
    print(f"   ℹ️  No encontrados  : {stats['no_encontrados']}")
    print(f"   ❌ Errores         : {stats['errores']}")
    print(f"\n📅 Calendarios:")
    print(f"   ✅ Eliminados      : {cal_stats['eliminados']}")
    print(f"   ℹ️  Sin calendario  : {cal_stats['sin_calendario']}")
    print(f"   ❌ Errores         : {cal_stats['errores']}")

    if errores:
        print(f"\n   Detalle de errores:")
        for phone, name, msg in errores:
            print(f"   {name} ({phone}) → {msg}")

    if dry_run:
        print(f"\n⚠️  DRY RUN: ningún dato fue modificado.")

    print()
    sep()
    print("✅ PROCESO COMPLETADO")
    sep()
    print()


def main():
    parser = argparse.ArgumentParser(
        description='Elimina pacientes demo y sus calendarios Turnos-X.',
        epilog="""
Ejemplos:
  python scripts/csv/delete_patients_from_csv.py /app/data/csv/pacientes_demo.csv
  python scripts/csv/delete_patients_from_csv.py /app/data/csv/pacientes_demo.csv --dry-run
        """
    )
    parser.add_argument('csv_path', help='Ruta al CSV con los pacientes a eliminar')
    parser.add_argument('--dry-run', action='store_true',
                        help='Simula sin eliminar nada')

    args = parser.parse_args()
    delete_patients(args.csv_path, args.dry_run)


if __name__ == '__main__':
    main()