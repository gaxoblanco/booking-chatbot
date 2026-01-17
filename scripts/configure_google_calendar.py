"""
Configurar profesionales con Google Calendar.
"""

import sys
import json
sys.path.append('.')

from src.database.database import db


def configure_professional_calendar(phone: str, calendar_email: str):
    """Configura Google Calendar para un profesional."""
    
    # Horario laboral: 9 AM a 6 PM
    working_hours = {
        'start': '09:00',
        'end': '18:00'
    }
    
    try:
        # Actualizar profesional con datos de Google Calendar
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE professionals 
                SET 
                    calendar_id = ?,
                    working_hours = ?,
                    slot_duration = 60,
                    timezone = 'America/Argentina/Buenos_Aires'
                WHERE phone = ?
            """, (calendar_email, json.dumps(working_hours), phone))
        
        print(f"✅ Profesional {phone} configurado con Google Calendar")
        print(f"   📧 Calendar ID: {calendar_email}")
        print(f"   ⏰ Horario: {working_hours['start']} - {working_hours['end']}")
        print(f"   ⏱️  Duración de consulta: 60 minutos")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🔧 CONFIGURAR GOOGLE CALENDAR")
    print("="*60 + "\n")
    
    # Configurar el profesional Demo
    success = configure_professional_calendar(
        phone="+5491100000000",
        calendar_email="gax0blanco93@gmail.com"  # Tu calendario
    )
    
    if success:
        print("\n✅ Configuración completada")
        print("\n📝 Próximo paso:")
        print("   Copiar appointment_calendar_service.py a src/integrations/")
    else:
        print("\n❌ Configuración falló")