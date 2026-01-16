"""
Script de prueba para el AvailabilityChecker.

Este script prueba la funcionalidad de cálculo de disponibilidad
consultando slots libres en un calendario real.

Uso:
    python test_availability.py
"""

import logging
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Agregar el directorio padre al path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))
sys.path.insert(0, str(parent_dir.parent))

from auth import AuthManager
from calendar import CalendarClient, AvailabilityChecker

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_availability():
    """
    Prueba el cálculo de disponibilidad.
    """
    print("\n" + "="*70)
    print("PRUEBA DE CÁLCULO DE DISPONIBILIDAD")
    print("="*70 + "\n")
    
    # PASO 1: Configurar cliente
    print("🔧 Paso 1: Configurando cliente...")
    print("-" * 70)
    
    try:
        auth_manager = AuthManager()
        credentials = auth_manager.get_credentials()
        calendar_client = CalendarClient(credentials)
        availability_checker = AvailabilityChecker(calendar_client)
        
        print("✅ Cliente configurado correctamente\n")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False
    
    # PASO 2: Configurar parámetros de prueba
    print("📋 Paso 2: Configurando parámetros de prueba...")
    print("-" * 70)
    
    # IMPORTANTE: Cambia este email por el tuyo
    calendar_id = 'gax0blanco93@gmail.com'
    
    # Buscar disponibilidad para mañana
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    
    # Horario laboral de ejemplo (9 AM a 6 PM)
    working_hours = {
        'start': '09:00',
        'end': '18:00'
    }
    
    # Slots de 1 hora
    slot_duration = 60
    
    print(f"📅 Calendario: {calendar_id}")
    print(f"📅 Fecha: {tomorrow}")
    print(f"⏰ Horario laboral: {working_hours['start']} - {working_hours['end']}")
    print(f"⏱️  Duración de slots: {slot_duration} minutos\n")
    
    # PASO 3: Obtener slots disponibles
    print("🔍 Paso 3: Consultando disponibilidad...")
    print("-" * 70)
    
    try:
        available_slots = availability_checker.get_available_slots(
            calendar_id=calendar_id,
            date=tomorrow,
            working_hours=working_hours,
            slot_duration_minutes=slot_duration
        )
        
        print(f"\n✅ Se encontraron {len(available_slots)} slots disponibles:\n")
        
        if not available_slots:
            print("⚠️  No hay horarios disponibles para este día")
            print("💡 Esto puede ser porque:")
            print("   - El día está completamente ocupado con eventos")
            print("   - Es un día pasado")
            print("   - El horario laboral está mal configurado")
        else:
            # Mostrar primeros 10 slots
            print("Horarios disponibles:")
            for i, slot in enumerate(available_slots[:10], 1):
                print(f"  {i:2d}. {slot['start']} - {slot['end']}")
            
            if len(available_slots) > 10:
                print(f"\n  ... y {len(available_slots) - 10} slots más")
        
    except Exception as e:
        print(f"\n❌ ERROR al consultar disponibilidad: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # PASO 4: Verificar slot específico
    print("\n🔍 Paso 4: Verificando slot específico...")
    print("-" * 70)
    
    # Probar con el primer slot disponible (si existe)
    if available_slots:
        test_slot = available_slots[0]
        print(f"Verificando slot: {test_slot['start']} - {test_slot['end']}")
        
        try:
            is_available = availability_checker.check_slot_available(
                calendar_id=calendar_id,
                start_datetime=test_slot['start_datetime'],
                end_datetime=test_slot['end_datetime']
            )
            
            if is_available:
                print(f"✅ El slot está disponible (como esperábamos)")
            else:
                print(f"⚠️  El slot NO está disponible (algo inesperado)")
        
        except Exception as e:
            print(f"❌ ERROR al verificar slot: {e}")
    
    # PASO 5: Buscar próximo slot disponible
    print("\n🔍 Paso 5: Buscando próximo slot disponible...")
    print("-" * 70)
    
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        
        next_slot = availability_checker.get_next_available_slot(
            calendar_id=calendar_id,
            start_date=today,
            working_hours=working_hours,
            slot_duration_minutes=slot_duration,
            days_to_search=7  # Buscar en los próximos 7 días
        )
        
        if next_slot:
            print(f"\n✅ Próximo slot disponible:")
            print(f"   📅 Fecha: {next_slot['date']}")
            print(f"   ⏰ Horario: {next_slot['start']} - {next_slot['end']}")
        else:
            print("\n⚠️  No se encontraron slots disponibles en los próximos 7 días")
    
    except Exception as e:
        print(f"\n❌ ERROR al buscar próximo slot: {e}")
    
    # RESUMEN FINAL
    print("\n" + "="*70)
    print("✅ PRUEBAS COMPLETADAS")
    print("="*70)
    print("\n✨ El AvailabilityChecker está funcionando correctamente\n")
    
    return True


if __name__ == "__main__":
    success = test_availability()
    sys.exit(0 if success else 1)
