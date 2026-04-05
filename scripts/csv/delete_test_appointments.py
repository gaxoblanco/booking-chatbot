"""
Script para eliminar citas de prueba creadas durante testing.

Elimina de la BD las citas y sus eventos en Google Calendar.
Los profesionales y pacientes NO se eliminan.

Uso:
    # Ver qué borraría (sin borrar nada)
    docker exec whatsapp-demo python3 scripts/csv/delete_test_appointments.py --phone +5493704969801 --dry-run

    # Borrar todas las citas de un número
    docker exec whatsapp-demo python3 scripts/csv/delete_test_appointments.py --phone +5493704969801 --yes

    # Borrar una cita específica por ID
    docker exec whatsapp-demo python3 scripts/csv/delete_test_appointments.py --id 2 --yes

    # Borrar todas las citas de la BD
    docker exec whatsapp-demo python3 scripts/csv/delete_test_appointments.py --all-test --yes
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, '/app')

from src.database.database import db


def sep(c='=', w=60): print(c * w)


def cancel_google_event(apt: dict, dry_run: bool) -> bool:
    """Cancela el evento en Google Calendar si existe."""
    google_event_id = apt.get('google_event_id')
    if not google_event_id:
        print(f"      ℹ️  Sin google_event_id — solo se borra de BD")
        return True

    professional = db.get_professional(apt['professional_phone'])
    calendar_id  = professional.get('calendar_id') if professional else None

    if not calendar_id:
        print(f"      ℹ️  Profesional sin calendar_id — solo se borra de BD")
        return True

    if dry_run:
        print(f"      🔍 DRY RUN: cancelaría evento {google_event_id}")
        return True

    try:
        from src.integrations.google_calendar_service import GoogleCalendarService
        calendar_service = GoogleCalendarService()
        service = calendar_service._build_service()
        service.events().delete(
            calendarId=calendar_id,
            eventId=google_event_id,
        ).execute()
        print(f"      ✅ Evento {google_event_id} eliminado de Google Calendar")
        return True
    except Exception as e:
        if 'notFound' in str(e) or '404' in str(e):
            print(f"      ℹ️  Evento ya no existe en Google Calendar")
            return True
        print(f"      ⚠️  Error en Google Calendar: {e}")
        return False


def delete_appointment(apt: dict, dry_run: bool) -> bool:
    """Borra una cita de BD y su evento en Google Calendar."""
    apt_id = apt['id']

    print(f"\n   📅 Cita #{apt_id}")
    print(f"      Paciente:     {apt['client_phone']}")
    print(f"      Profesional:  {apt.get('professional_name', apt['professional_phone'])}")
    print(f"      Fecha:        {apt['appointment_date']} {apt['start']}")
    print(f"      Estado:       {apt['status']}")

    # Cancelar en Google Calendar primero
    cancel_google_event(apt, dry_run)

    # Borrar de BD
    if dry_run:
        print(f"      🔍 DRY RUN: eliminaría cita #{apt_id} de BD")
        return True

    try:
        with db.get_connection() as conn:
            conn.execute("DELETE FROM appointments WHERE id = ?", (apt_id,))
        print(f"      ✅ Cita #{apt_id} eliminada de BD")
        return True
    except Exception as e:
        print(f"      ❌ Error eliminando cita #{apt_id}: {e}")
        return False


def run(args):
    sep()
    print("🗑️  ELIMINAR CITAS DE PRUEBA")
    sep()
    print(f"   Modo: {'🔍 DRY RUN' if args.dry_run else '⚠️  ELIMINACIÓN REAL'}")

    appointments = []

    # ── Obtener citas según el modo ───────────────────────────────────────────
    if args.id:
        apt = db.get_appointment(args.id)
        if not apt:
            print(f"\n❌ Cita #{args.id} no encontrada")
            sys.exit(1)
        appointments = [apt]

    elif args.phone:
        appointments = db.get_appointments_by_client(args.phone)
        if not appointments:
            print(f"\nℹ️  No hay citas para {args.phone}")
            sys.exit(0)

    elif args.all_test:
        # Todas las citas activas (útil para limpiar testing)
        with db.get_connection() as conn:
            rows = conn.execute("""
                SELECT a.*, p.name as professional_name
                FROM appointments a
                LEFT JOIN professionals p ON a.professional_phone = p.phone
                ORDER BY a.id DESC
            """).fetchall()
        appointments = [dict(r) for r in rows]
        if not appointments:
            print("\nℹ️  No hay citas en la BD")
            sys.exit(0)

    # ── Mostrar y confirmar ───────────────────────────────────────────────────
    print(f"\n   Citas encontradas: {len(appointments)}")

    if not args.dry_run and not args.yes:
        confirm = input(f"\n⚠️  ¿Eliminar {len(appointments)} cita(s)? (s/N): ").strip().lower()
        if confirm not in ('s', 'si', 'sí', 'y', 'yes'):
            print("❌ Cancelado")
            sys.exit(0)

    # ── Procesar ──────────────────────────────────────────────────────────────
    ok = 0
    errors = 0

    for apt in appointments:
        if delete_appointment(apt, args.dry_run):
            ok += 1
        else:
            errors += 1

    # ── Resumen ───────────────────────────────────────────────────────────────
    sep()
    print(f"📊 RESUMEN")
    sep()
    print(f"   ✅ Eliminadas: {ok}")
    print(f"   ❌ Errores:    {errors}")
    if args.dry_run:
        print(f"\n   ⚠️  DRY RUN — ningún dato fue modificado")
    sep()


def main():
    parser = argparse.ArgumentParser(
        description='Elimina citas de prueba de la BD y Google Calendar.'
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--phone', help='Borrar todas las citas de un número (+5493704969801)')
    group.add_argument('--id',    type=int, help='Borrar una cita específica por ID')
    group.add_argument('--all-test', action='store_true', help='Borrar TODAS las citas de la BD')

    parser.add_argument('--dry-run', action='store_true', help='Simular sin borrar nada')
    parser.add_argument('--yes', '-y', action='store_true', help='Confirmar sin preguntar')

    args = parser.parse_args()
    run(args)


if __name__ == '__main__':
    main()
