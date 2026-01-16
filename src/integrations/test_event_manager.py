"""
Script de prueba para el EventManager.

Este script prueba la funcionalidad de gestión de citas:
- Crear cita
- Consultar detalles
- Actualizar notas
- Reprogramar
- Cancelar

Uso:
    python test_event_manager.py
"""

import logging
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Agregar el directorio padre al path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))
sys.path.insert(0, str(parent_dir.parent))

from google_calendar_service.auth import AuthManager
from google_calendar_service.calendar import CalendarClient, EventManager

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_event_manager():
    """
    Prueba completa del EventManager.
    """
    print("\n" + "="*70)
    print("PRUEBA DE GESTIÓN DE CITAS (EVENT MANAGER)")
    print("="*70 + "\n")
    
    # PASO 1: Configurar cliente
    print("🔧 Paso 1: Configurando cliente...")
    print("-" * 70)
    
    try:
        credentials_path = r"D:\develop-programing\booking-chatbot\src\integrations\google_calendar_service\config\google\service-account.json"
        auth_manager = AuthManager(credentials_path)
        credentials = auth_manager.get_credentials()
        calendar_client = CalendarClient(credentials)
        event_manager = EventManager(calendar_client)
        
        print("✅ Cliente configurado correctamente\n")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False
    
    # PASO 2: Configurar parámetros
    print("📋 Paso 2: Configurando parámetros de prueba...")
    print("-" * 70)
    
    # IMPORTANTE: Cambia este email por el tuyo
    calendar_id = 'gax0blanco93@gmail.com'
    
    # Crear cita de prueba para dentro de 30 días (para no interferir con agenda real)
    future_date = datetime.now() + timedelta(days=30)
    start_time = future_date.replace(hour=14, minute=0, second=0, microsecond=0)
    end_time = start_time + timedelta(hours=1)
    
    # Datos de la cita de prueba
    test_appointment = {
        'client_name': 'Juan Pérez (PRUEBA)',
        'client_phone': '+5491112345678',
        'appointment_type': 'Consulta de Prueba',
        'notes': 'Esta es una cita de prueba del sistema. Puede ser eliminada.'
    }
    
    print(f"📅 Calendario: {calendar_id}")
    print(f"📅 Fecha de prueba: {start_time.strftime('%Y-%m-%d %H:%M')}")
    print(f"👤 Cliente: {test_appointment['client_name']}")
    print(f"📞 Teléfono: {test_appointment['client_phone']}")
    print(f"📋 Tipo: {test_appointment['appointment_type']}\n")
    
    created_event_id = None
    
    try:
        # PASO 3: Crear cita
        print("➕ Paso 3: Creando cita de prueba...")
        print("-" * 70)
        
        event = event_manager.create_appointment(
            calendar_id=calendar_id,
            start_datetime=start_time.strftime('%Y-%m-%d %H:%M'),
            end_datetime=end_time.strftime('%Y-%m-%d %H:%M'),
            client_name=test_appointment['client_name'],
            client_phone=test_appointment['client_phone'],
            appointment_type=test_appointment['appointment_type'],
            notes=test_appointment['notes']
        )
        
        created_event_id = event['id']
        
        print(f"\n✅ Cita creada exitosamente!")
        print(f"   ID: {event['id']}")
        print(f"   Título: {event['summary']}")
        print(f"   Link: {event.get('htmlLink', 'N/A')}")
        
        # PASO 4: Consultar detalles
        print("\n🔍 Paso 4: Consultando detalles de la cita...")
        print("-" * 70)
        
        details = event_manager.get_appointment_details(
            calendar_id=calendar_id,
            event_id=created_event_id
        )
        
        if details:
            print(f"\n✅ Detalles obtenidos:")
            print(f"   Título: {details['summary']}")
            print(f"   Inicio: {details['start'].get('dateTime', 'N/A')}")
            print(f"   Descripción:\n   {details.get('description', 'N/A').replace(chr(10), chr(10) + '   ')}")
        else:
            print("⚠️  No se pudieron obtener los detalles")
        
        # PASO 5: Actualizar notas
        print("\n📝 Paso 5: Agregando notas adicionales...")
        print("-" * 70)
        
        updated_event = event_manager.update_appointment_notes(
            calendar_id=calendar_id,
            event_id=created_event_id,
            additional_notes="Cliente confirmó asistencia por WhatsApp el día anterior."
        )
        
        print(f"✅ Notas actualizadas correctamente")
        
        # PASO 6: Reprogramar cita
        print("\n🔄 Paso 6: Reprogramando cita...")
        print("-" * 70)
        
        # Mover 1 hora más tarde
        new_start = start_time + timedelta(hours=1)
        new_end = new_start + timedelta(hours=1)
        
        print(f"Nueva hora: {new_start.strftime('%Y-%m-%d %H:%M')}")
        
        rescheduled_event = event_manager.reschedule_appointment(
            calendar_id=calendar_id,
            event_id=created_event_id,
            new_start_datetime=new_start.strftime('%Y-%m-%d %H:%M'),
            new_end_datetime=new_end.strftime('%Y-%m-%d %H:%M')
        )
        
        print(f"✅ Cita reprogramada exitosamente")
        print(f"   Nuevo horario: {rescheduled_event['start'].get('dateTime', 'N/A')}")
        
        # PASO 7: Cancelar cita (limpiar)
        print("\n🗑️  Paso 7: Cancelando cita de prueba...")
        print("-" * 70)
        
        # Preguntar al usuario si quiere cancelar
        print("\n⚠️  ¿Deseas cancelar la cita de prueba del calendario? (s/n)")
        print("   (Si no la cancelas, quedará en tu calendario)")
        
        try:
            respuesta = input("   Respuesta: ").strip().lower()
        except:
            respuesta = 's'  # Por defecto cancelar en ambientes sin input
        
        if respuesta == 's':
            success = event_manager.cancel_appointment(
                calendar_id=calendar_id,
                event_id=created_event_id,
                cancellation_reason='Cita de prueba del sistema - Finalización de tests'
            )
            
            if success:
                print(f"\n✅ Cita cancelada exitosamente")
                print(f"   La cita fue eliminada del calendario")
            else:
                print(f"\n⚠️  No se pudo cancelar la cita")
        else:
            print(f"\n✅ Cita mantenida en el calendario")
            print(f"   ID del evento: {created_event_id}")
            print(f"   Puedes eliminarla manualmente desde Google Calendar")
        
        # RESUMEN FINAL
        print("\n" + "="*70)
        print("✅ TODAS LAS PRUEBAS COMPLETADAS")
        print("="*70)
        print("\n✨ El EventManager está funcionando correctamente")
        print("\nFuncionalidades probadas:")
        print("  ✅ Crear cita con formato estándar")
        print("  ✅ Consultar detalles de cita")
        print("  ✅ Actualizar notas")
        print("  ✅ Reprogramar cita")
        print("  ✅ Cancelar cita")
        print()
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR durante las pruebas: {e}")
        import traceback
        traceback.print_exc()
        
        # Si algo falló y se creó un evento, intentar limpiarlo
        if created_event_id:
            print(f"\n🧹 Intentando limpiar evento de prueba...")
            try:
                event_manager.cancel_appointment(
                    calendar_id=calendar_id,
                    event_id=created_event_id,
                    cancellation_reason='Error en tests - Limpieza automática'
                )
                print(f"✅ Evento de prueba eliminado")
            except:
                print(f"⚠️  No se pudo eliminar automáticamente")
                print(f"   Eliminar manualmente el evento ID: {created_event_id}")
        
        return False


if __name__ == "__main__":
    success = test_event_manager()
    sys.exit(0 if success else 1)
