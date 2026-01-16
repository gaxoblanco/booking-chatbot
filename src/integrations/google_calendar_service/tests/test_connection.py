"""
Script de prueba para verificar la conexión con Google Calendar API.

Este script valida que:
1. Las credenciales sean válidas
2. Se pueda conectar a la API
3. Se listen los calendarios accesibles
4. Se pueda leer eventos de un calendario

Uso:
    python test_connection.py
    
Requisitos:
    - Tener el archivo service-account.json en config/google/
    - Al menos un calendario compartido con la Service Account
"""

import logging
import sys
from pathlib import Path

# Agregar el directorio padre al path para importar el módulo
sys.path.insert(0, str(Path(__file__).parent.parent))

from google_calendar_service.auth import AuthManager
from google_calendar_service.calendar import CalendarClient

# Configurar logging para ver el proceso
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_connection():
    """
    Prueba la conexión con Google Calendar API.
    """
    print("\n" + "="*70)
    print("PRUEBA DE CONEXIÓN CON GOOGLE CALENDAR API")
    print("="*70 + "\n")
    
    # PASO 1: Inicializar AuthManager
    print("📋 Paso 1: Cargando credenciales...")
    print("-" * 70)
    
    try:
        auth_manager = AuthManager()
        print(f"✅ Archivo de credenciales encontrado: {auth_manager.credentials_path}")
        
        # Mostrar información de la Service Account
        email = auth_manager.get_service_account_email()
        project_id = auth_manager.get_project_id()
        
        print(f"📧 Service Account Email: {email}")
        print(f"🏗️  Project ID: {project_id}")
        
    except FileNotFoundError as e:
        print(f"\n❌ ERROR: {e}")
        print("\n💡 SOLUCIÓN:")
        print("   1. Ir a Google Cloud Console")
        print("   2. Crear Service Account")
        print("   3. Descargar archivo JSON")
        print("   4. Guardar como: config/google/service-account.json")
        return False
    except Exception as e:
        print(f"\n❌ ERROR inesperado: {e}")
        return False
    
    # PASO 2: Obtener credenciales
    print("\n🔑 Paso 2: Autenticando con Google...")
    print("-" * 70)
    
    try:
        credentials = auth_manager.get_credentials()
        print("✅ Credenciales obtenidas exitosamente")
        
        # Validar credenciales
        if auth_manager.validate_credentials():
            print("✅ Credenciales validadas correctamente")
        else:
            print("⚠️  Advertencia: No se pudieron validar las credenciales")
            
    except Exception as e:
        print(f"\n❌ ERROR al autenticar: {e}")
        print("\n💡 Verificar que:")
        print("   - El archivo JSON sea válido")
        print("   - La API de Calendar esté habilitada en Google Cloud Console")
        return False
    
    # PASO 3: Crear cliente de Calendar
    print("\n📅 Paso 3: Conectando con Google Calendar API...")
    print("-" * 70)
    
    try:
        calendar_client = CalendarClient(credentials)
        print("✅ Cliente de Calendar API creado exitosamente")
        
    except Exception as e:
        print(f"\n❌ ERROR al crear cliente: {e}")
        return False
    
    # PASO 4: Listar calendarios accesibles
    print("\n📋 Paso 4: Listando calendarios accesibles...")
    print("-" * 70)
    
    try:
        calendars = calendar_client.list_calendars()
        
        if not calendars:
            print("\n⚠️  No se encontraron calendarios accesibles")
            print("\n💡 SOLUCIÓN:")
            print(f"   1. Compartir un calendario con: {email}")
            print("   2. Dar permisos: 'Hacer cambios en eventos'")
            print("   3. Esperar 1-2 minutos para que se propaguen los permisos")
            return False
        
        print(f"\n✅ Se encontraron {len(calendars)} calendario(s):\n")
        
        for i, cal in enumerate(calendars, 1):
            print(f"{i}. {cal.get('summary', 'Sin nombre')}")
            print(f"   ID: {cal.get('id')}")
            print(f"   Rol: {cal.get('accessRole')}")
            print(f"   Zona horaria: {cal.get('timeZone', 'No especificada')}")
            print()
        
    except Exception as e:
        print(f"\n❌ ERROR al listar calendarios: {e}")
        return False
    
    # PASO 5: Probar acceso a eventos (opcional)
    print("\n📅 Paso 5: Verificando acceso a eventos...")
    print("-" * 70)
    
    try:
        # Intentar leer eventos del primer calendario
        first_calendar_id = calendars[0]['id']
        print(f"Intentando leer eventos de: {calendars[0].get('summary')}")
        
        # Obtener eventos de hoy
        from datetime import datetime, timedelta
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        
        events = calendar_client.get_events(
            calendar_id=first_calendar_id,
            time_min=today.isoformat() + 'Z',
            time_max=tomorrow.isoformat() + 'Z'
        )
        
        print(f"✅ Se encontraron {len(events)} evento(s) para hoy")
        
        if events:
            print("\nEventos:")
            for event in events[:5]:  # Mostrar máximo 5
                print(f"  - {event.get('summary', 'Sin título')}")
                start = event.get('start', {}).get('dateTime', 'Hora no especificada')
                print(f"    Inicio: {start}")
        
    except Exception as e:
        print(f"⚠️  Advertencia al leer eventos: {e}")
        print("Esto puede ser normal si no hay eventos o permisos limitados")
    
    # RESUMEN FINAL
    print("\n" + "="*70)
    print("✅ CONEXIÓN EXITOSA")
    print("="*70)
    print("\n✨ El servicio está configurado correctamente y listo para usar\n")
    
    return True


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
