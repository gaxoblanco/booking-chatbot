"""
validate_pending_calendars.py
==============================
Re-valida el acceso a Google Calendar de profesionales pendientes.

Un profesional queda "pendiente" cuando:
- Fue cargado desde CSV
- No tenía acceso al calendario en ese momento
- Se le envió email con instrucciones

Una vez que el profesional compartió su calendario con la Service Account,
correr este script para completar su configuración.

Uso:
    docker exec -it whatsapp-demo python scripts/validate_pending_calendars.py
"""

import sys
import json
import time

# Asegurar que el path del proyecto esté disponible
sys.path.insert(0, '/app')

from src.database.database import db
from src.services.professional_service import professional_service


def get_pending_professionals() -> list:
    """
    Obtiene profesionales que tienen calendar_email pero no calendar_id.
    Son los que quedaron pendientes de autorización.
    """
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT phone, name, calendar_email, working_hours, slot_duration
                FROM professionals
                WHERE calendar_email IS NOT NULL
                  AND (calendar_id IS NULL OR calendar_id = '')
                ORDER BY name
            """)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        print(f"❌ Error consultando BD: {e}")
        return []


def main():
    print()
    print("=" * 70)
    print("🔄 VALIDACIÓN DE CALENDARIOS PENDIENTES")
    print("=" * 70)

    # 1. Obtener pendientes
    pendientes = get_pending_professionals()

    if not pendientes:
        print("\n✅ No hay profesionales pendientes. Todos están configurados.")
        return

    print(f"\n📋 Profesionales pendientes: {len(pendientes)}")
    for p in pendientes:
        print(f"   • {p['name']} ({p['phone']}) → {p['calendar_email']}")

    print()

    # Estadísticas
    stats = {'resueltos': 0, 'siguen_pendientes': 0, 'errores': 0}

    for prof in pendientes:
        phone          = prof['phone']
        name           = prof['name']
        calendar_email = prof['calendar_email']
        working_hours  = json.loads(prof['working_hours']) if prof.get('working_hours') else {}
        slot_duration  = prof.get('slot_duration') or 60

        print("-" * 70)
        print(f"👤 {name} ({phone})")
        print(f"   📅 Validando acceso a: {calendar_email}")

        # Validar acceso
        has_access = professional_service.validate_calendar_access(calendar_email)

        if not has_access:
            print(f"   ⏳ Sigue sin acceso — pendiente")
            stats['siguen_pendientes'] += 1
            continue

        print(f"   ✅ ¡Acceso confirmado!")

        # Crear calendario secundario y compartirlo
        result = professional_service.setup_google_calendar(
            phone=phone,
            calendar_email=calendar_email,
            professional_name=name
        )

        if not result['success']:
            print(f"   ❌ Error creando calendario: {result['message']}")
            stats['errores'] += 1
            continue

        # Guardar working_hours y slot_duration
        # (setup_google_calendar ya guardó calendar_id y timezone)
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE professionals
                    SET working_hours = ?,
                        slot_duration = ?
                    WHERE phone = ?
                """, (json.dumps(working_hours), slot_duration, phone))

            dias = list(working_hours.keys()) if working_hours else []
            print(f"   📅 Calendario: {result['calendar_id']}")
            print(f"   ⏱️  Slot duration: {slot_duration} min")
            print(f"   📋 Días: {', '.join(dias) if dias else 'ninguno'}")
            stats['resueltos'] += 1

        except Exception as e:
            print(f"   ❌ Error guardando horarios: {e}")
            stats['errores'] += 1

    # Resumen
    print()
    print("=" * 70)
    print("📊 RESUMEN")
    print("=" * 70)
    print(f"   ✅ Resueltos       : {stats['resueltos']}")
    print(f"   ⏳ Siguen pendientes: {stats['siguen_pendientes']}")
    print(f"   ❌ Errores         : {stats['errores']}")

    if stats['siguen_pendientes'] > 0:
        print(f"""
💡 {stats['siguen_pendientes']} profesional(es) todavía no compartieron su calendario.
   Cuando lo hagan, volvé a correr:
   docker exec -it whatsapp-demo python scripts/validate_pending_calendars.py
""")
    else:
        print("\n🎉 ¡Todos los profesionales están configurados!")

    print("=" * 70)


if __name__ == '__main__':
    main()