"""
Script para eliminar pacientes cargados desde un CSV demo.

Elimina de la BD los clientes y sus citas, y cancela los eventos
recurrentes en Google Calendar usando el google_event_id almacenado.

Uso:
    python scripts/delete_patients_from_csv.py pacientes_demo.csv
    python scripts/delete_patients_from_csv.py pacientes_demo.csv --dry-run
"""

import sys
import csv
import argparse
from pathlib import Path

sys.path.append('.')

from src.database.database import db
from src.integrations.google_calendar_service import GoogleCalendarService


def sep(c='=', w=70): print(c * w)


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

    with open(csv_path, encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            stats['total'] += 1
            phone = row['phone'].strip()
            name  = row['name'].strip()

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
                    prof_phone      = apt['professional_phone']
                    professional    = db.get_professional(prof_phone)
                    calendar_id     = professional.get('calendar_id') if professional else None

                    print(f"   📅 Cita #{apt_id} | {apt['appointment_date']} {apt['start']}")

                    # ── Cancelar evento en Google Calendar ─────────────────
                    if google_event_id and calendar_id:
                        if dry_run:
                            print(f"   🔍 DRY RUN: cancelaría evento {google_event_id} en Calendar")
                        else:
                            try:
                                # Eliminar todas las ocurrencias (evento recurrente padre)
                                service = calendar_service._build_service()
                                service.events().delete(
                                    calendarId=calendar_id,
                                    eventId=google_event_id,
                                ).execute()
                                print(f"   ✅ Evento eliminado de Calendar: {google_event_id}")
                            except Exception as e:
                                # Si ya no existe en Calendar, continuar igual
                                if 'notFound' in str(e) or '404' in str(e):
                                    print(f"   ℹ️  Evento ya no existe en Calendar")
                                else:
                                    print(f"   ⚠️  Error en Calendar (se elimina igual de BD): {e}")
                    else:
                        print(f"   ℹ️  Sin google_event_id, solo se elimina de BD")

                    # ── Eliminar cita de BD ────────────────────────────────
                    if dry_run:
                        print(f"   🔍 DRY RUN: eliminaría cita #{apt_id} de BD")
                    else:
                        try:
                            with db.get_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute(
                                    "DELETE FROM appointments WHERE id = ?", (apt_id,)
                                )
                            print(f"   ✅ Cita #{apt_id} eliminada de BD")
                        except Exception as e:
                            print(f"   ❌ Error eliminando cita #{apt_id}: {e}")
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
                    print(f"   ✅ Paciente eliminado de BD")
                    stats['ok'] += 1
                except Exception as e:
                    print(f"   ❌ Error eliminando paciente: {e}")
                    stats['errores'] += 1
                    errores.append((phone, name, str(e)))

    # ── Resumen ───────────────────────────────────────────────────────────────
    print()
    sep()
    print("📊 RESUMEN")
    sep()
    print(f"   Total procesados  : {stats['total']}")
    print(f"   ✅ Eliminados      : {stats['ok']}")
    print(f"   ℹ️  No encontrados  : {stats['no_encontrados']}")
    print(f"   ❌ Errores         : {stats['errores']}")

    if errores:
        print()
        print("   Detalle de errores:")
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
        description='Elimina pacientes demo cargados desde un CSV.',
        epilog="""
Ejemplos:
  python scripts/delete_patients_from_csv.py pacientes_demo.csv
  python scripts/delete_patients_from_csv.py pacientes_demo.csv --dry-run
        """
    )
    parser.add_argument('csv_path', help='Ruta al CSV con los pacientes a eliminar')
    parser.add_argument('--dry-run', action='store_true',
                        help='Simula sin eliminar nada')

    args = parser.parse_args()
    delete_patients(args.csv_path, args.dry_run)


if __name__ == '__main__':
    main()
