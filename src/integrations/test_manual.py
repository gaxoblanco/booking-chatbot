# Crear archivo: test_manual.py
from google_calendar_service.auth import AuthManager
from google_calendar_service.calendar import CalendarClient

auth = AuthManager()
creds = auth.get_credentials()
client = CalendarClient(creds)

# Intentar acceder directamente al calendario del propietario
calendar_id = 'gax0blanco93@gmail.com'  # Tu email

try:
    cal = client.get_calendar(calendar_id)
    print(f"✅ Acceso exitoso: {cal.get('summary')}")
except Exception as e:
    print(f"❌ Error: {e}")