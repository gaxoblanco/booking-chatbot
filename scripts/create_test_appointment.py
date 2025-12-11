#!/usr/bin/env python3
"""
Script para crear citas de prueba
==================================
Crea citas con fechas específicas para testing.

Uso:
    python scripts/create_test_appointment.py                    # Cita mañana a las 10:00
    python scripts/create_test_appointment.py --days 3           # Cita en 3 días
    python scripts/create_test_appointment.py --days 7 --time 14:00  # Cita en 7 días a las 14:00
"""
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.database import db


# Teléfonos de prueba
TEST_CLIENT_PHONE = "+5491123456789"
TEST_CLIENT_NAME = "Test Client"
TEST_PROF_PHONE = "+5491112345678"
TEST_PROF_NAME = "Dr. Test Professional"


def create_test_appointment(
    days_from_now: int = 2,
    time: str = "10:00",
    duration: int = 50,
    modality: str = "presencial"
):
    """
    Crea una cita de prueba.
    
    Args:
        days_from_now: Días desde hoy para la cita
        time: Hora de la cita (formato HH:MM)
        duration: Duración en minutos
        modality: Modalidad (presencial/virtual/ambas)
    """
    
    # Calcular fecha
    appointment_date = datetime.now() + timedelta(days=days_from_now)
    date_str = appointment_date.strftime("%Y-%m-%d")
    
    # Calcular hora de fin
    start_time = datetime.strptime(time, "%H:%M")
    end_time = start_time + timedelta(minutes=duration)
    end_time_str = end_time.strftime("%H:%M")
    
    # Datos de la cita (sin client_name ni professional_name - no están en DB)
    appointment_data = {
        'client_phone': TEST_CLIENT_PHONE,
        'professional_phone': TEST_PROF_PHONE,
        'appointment_date': date_str,
        'start_time': time,
        'end_time': end_time_str,
        'duration_minutes': duration,
        'modality': modality,
        'session_type': 'primera_vez',
        'notes': None
    }
    
    try:
        # Verificar si ya existe
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id FROM appointments 
                WHERE professional_phone = ? 
                AND appointment_date = ? 
                AND start_time = ?
            """, (TEST_PROF_PHONE, date_str, time))
            
            existing = cursor.fetchone()
            if existing:
                print(f"⚠️  Ya existe una cita en {date_str} a las {time}")
                print(f"   ID: {existing['id']}")
                return existing['id']
        
        # Crear cita
        appointment_id = db.create_appointment(**appointment_data)
        
        if appointment_id:
            # Obtener el appointment completo para mostrar nombres
            apt = db.get_appointment(appointment_id)
            
            print(f"✅ Cita creada exitosamente!")
            print(f"   ID: {appointment_id}")
            print(f"   📅 Fecha: {appointment_date.strftime('%A %d/%m/%Y')}")
            print(f"   ⏰ Hora: {time}")
            print(f"   👨‍⚕️ Profesional: {apt.get('professional_name', TEST_PROF_NAME) if apt else TEST_PROF_NAME}")
            print(f"   📱 Cliente: {apt.get('client_name', TEST_CLIENT_NAME) if apt else TEST_CLIENT_NAME}")
            print(f"   📍 Modalidad: {modality}")
            print(f"   ⏱️ Duración: {duration} min")
            
            # Calcular horas hasta la cita
            appointment_datetime = datetime.strptime(f"{date_str} {time}", "%Y-%m-%d %H:%M")
            hours_until = (appointment_datetime - datetime.now()).total_seconds() / 3600
            print(f"   ⏳ En {hours_until:.1f} horas ({days_from_now} días)")
            
            if hours_until >= 24:
                print(f"   ✅ Puede cancelarse (>24hs)")
            else:
                print(f"   ⚠️  No puede cancelarse (<24hs)")
            
            return appointment_id
        else:
            print(f"❌ Error al crear la cita")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def create_multiple_appointments():
    """Crea un set de citas de prueba con diferentes fechas."""
    print("🗓️  Creando múltiples citas de prueba...\n")
    
    appointments = [
        {"days_from_now": 2, "time": "10:00", "modality": "presencial"},
        {"days_from_now": 3, "time": "14:00", "modality": "virtual"},
        {"days_from_now": 5, "time": "11:00", "modality": "presencial"},
        {"days_from_now": 7, "time": "16:00", "modality": "ambas"},
    ]
    
    created = 0
    for apt in appointments:
        print(f"\n{'-'*50}")
        result = create_test_appointment(**apt)
        if result:
            created += 1
    
    print(f"\n{'='*50}")
    print(f"✅ {created} citas creadas de {len(appointments)}")


def show_upcoming_appointments():
    """Muestra todas las citas futuras del cliente de prueba."""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM appointments 
                WHERE client_phone = ? 
                AND appointment_date >= date('now')
                ORDER BY appointment_date, start_time
            """, (TEST_CLIENT_PHONE,))
            
            appointments = cursor.fetchall()
            
            if not appointments:
                print("ℹ️  No hay citas futuras")
                return
            
            print(f"📋 Citas Futuras ({len(appointments)}):\n")
            
            for apt in appointments:
                apt_datetime = datetime.strptime(
                    f"{apt['appointment_date']} {apt['start_time']}", 
                    "%Y-%m-%d %H:%M"
                )
                hours_until = (apt_datetime - datetime.now()).total_seconds() / 3600
                days_until = hours_until / 24
                
                can_cancel = "✅ Puede cancelar" if hours_until >= 24 else "⚠️ Muy cerca"
                
                print(f"   ID {apt['id']}: {apt_datetime.strftime('%a %d/%m/%Y')} {apt['start_time']}")
                print(f"      Estado: {apt['status']}")
                print(f"      En {days_until:.1f} días ({hours_until:.1f}hs) - {can_cancel}")
                print()
                
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description='Crea citas de prueba para testing'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=2,
        help='Días desde hoy para la cita (default: 2)'
    )
    parser.add_argument(
        '--time',
        type=str,
        default='10:00',
        help='Hora de la cita en formato HH:MM (default: 10:00)'
    )
    parser.add_argument(
        '--duration',
        type=int,
        default=50,
        help='Duración en minutos (default: 50)'
    )
    parser.add_argument(
        '--modality',
        type=str,
        default='presencial',
        choices=['presencial', 'virtual', 'ambas'],
        help='Modalidad de la sesión (default: presencial)'
    )
    parser.add_argument(
        '--multiple',
        action='store_true',
        help='Crear múltiples citas de prueba'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='Listar citas futuras sin crear nuevas'
    )
    
    args = parser.parse_args()
    
    # Si se pide listar, mostrar y salir
    if args.list:
        show_upcoming_appointments()
        return
    
    # Si se pide múltiples
    if args.multiple:
        create_multiple_appointments()
    else:
        # Crear una sola cita
        print("🗓️  Creando cita de prueba...\n")
        create_test_appointment(
            days_from_now=args.days,
            time=args.time,
            duration=args.duration,
            modality=args.modality
        )
    
    print("\n" + "="*50)
    print("\n📋 Para ver todas las citas:")
    print("   python scripts/create_test_appointment.py --list\n")


if __name__ == "__main__":
    main()
