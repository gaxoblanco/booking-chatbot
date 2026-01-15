#!/usr/bin/env python3
"""
Script para Crear Profesionales de Prueba
==========================================
Crea profesionales con horarios y disponibilidad para testing.

Uso:
    python scripts/seed_professionals.py              # Crear 3 profesionales
    python scripts/seed_professionals.py --count 5    # Crear 5 profesionales
    python scripts/seed_professionals.py --reset      # Borrar y crear nuevos
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta, date

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.database import db
from src.config.domain_config import DomainConfig


def create_test_professionals(count=3, reset=False):
    """
    Crea profesionales de prueba con horarios y disponibilidad.
    
    Args:
        count: Número de profesionales a crear (default 3)
        reset: Si True, borra profesionales existentes primero
    """
    
    print("\n" + "="*60)
    print("🏥 CREANDO PROFESIONALES DE PRUEBA")
    print("="*60 + "\n")
    
    # Reset si se solicita
    if reset:
        print("🗑️  Borrando profesionales existentes...")
        with db.get_connection() as conn:
            cursor = conn.cursor()
            # Borrar profesionales de prueba (los que empiezan con +54911)
            cursor.execute("DELETE FROM professionals WHERE phone LIKE '+54911%'")
            cursor.execute("DELETE FROM weekly_schedule WHERE professional_phone LIKE '+54911%'")
            cursor.execute("DELETE FROM specific_free_slots WHERE professional_phone LIKE '+54911%'")
            conn.commit()
        print("✅ Profesionales borrados\n")
    
    # Obtener configuración del dominio
    zones = list(DomainConfig.ZONES.keys()) if hasattr(DomainConfig, 'ZONES') else ['norte', 'sur']
    categories = list(DomainConfig.CATEGORIES.values()) if hasattr(DomainConfig, 'CATEGORIES') else ['General', 'Especialista']
    
    # Datos de profesionales de prueba
    test_professionals = [
        # ============================================
        # PROFESIONAL DEMO - SIEMPRE DISPONIBLE
        # ============================================
        {
            "phone": "+5491100000000",
            "name": "Dr. Demo Disponible",
            "email": "demo@test.com",
            "zone": zones[0] if len(zones) > 0 else "norte",
            "gender": "m",
            "accept_prepaga": True,
            "category": categories[0] if len(categories) > 0 else "Médico General",
            "bio": "Profesional de prueba con disponibilidad completa para testing. Turnos disponibles todos los días.",
            "fee_range": "5000-8000",
            "weekly_hours": [
                (0, "08:00", "20:00"),  # Lunes
                (1, "08:00", "20:00"),  # Martes
                (2, "08:00", "20:00"),  # Miércoles
                (3, "08:00", "20:00"),  # Jueves
                (4, "08:00", "20:00"),  # Viernes
                (5, "09:00", "18:00"),  # Sábado
            ],
            "always_available": True  # Flag especial para crear slots automáticos
        },
        # ============================================
        # PROFESIONALES NORMALES
        # ============================================
        {
            "phone": "+5491112345678",
            "name": "Dr. Juan Pérez",
            "email": "juan.perez@test.com",
            "zone": zones[0] if len(zones) > 0 else "norte",
            "gender": "m",
            "accept_prepaga": True,
            "category": categories[0] if len(categories) > 0 else "Médico General",
            "bio": "Especialista con amplia experiencia. Atención personalizada.",
            "fee_range": "10000-15000",
            "weekly_hours": [(0, "09:00", "17:00"), (2, "09:00", "17:00"), (4, "09:00", "13:00")]  # Lun, Mie, Vie
        },
        {
            "phone": "+5491187654321",
            "name": "Dra. María González",
            "email": "maria.gonzalez@test.com",
            "zone": zones[1] if len(zones) > 1 else "sur",
            "gender": "f",
            "accept_prepaga": False,
            "category": categories[1] if len(categories) > 1 else "Dentista",
            "bio": "Dedicada al cuidado integral de la salud.",
            "fee_range": "8000-12000",
            "weekly_hours": [(1, "10:00", "18:00"), (3, "10:00", "18:00")]  # Mar, Jue
        },
        {
            "phone": "+5491156789012",
            "name": "Lic. Carlos Rodríguez",
            "email": "carlos.rodriguez@test.com",
            "zone": zones[0] if len(zones) > 0 else "norte",
            "gender": "m",
            "accept_prepaga": True,
            "category": categories[2] if len(categories) > 2 else "Psicólogo",
            "bio": "Enfoque cognitivo-conductual. Sesiones online y presenciales.",
            "fee_range": "12000-18000",
            "weekly_hours": [(0, "14:00", "20:00"), (1, "14:00", "20:00"), (3, "14:00", "20:00")]  # Lun, Mar, Jue
        },
        {
            "phone": "+5491198765432",
            "name": "Dra. Ana Martínez",
            "email": "ana.martinez@test.com",
            "zone": zones[1] if len(zones) > 1 else "sur",
            "gender": "f",
            "accept_prepaga": True,
            "category": categories[3] if len(categories) > 3 else "Kinesiólogo",
            "bio": "Rehabilitación y terapia física especializada.",
            "fee_range": "15000-20000",
            "weekly_hours": [(0, "08:00", "12:00"), (2, "08:00", "12:00"), (4, "08:00", "12:00")]  # Lun, Mie, Vie
        },
        {
            "phone": "+5491145678901",
            "name": "Lic. Pedro Fernández",
            "email": "pedro.fernandez@test.com",
            "zone": zones[0] if len(zones) > 0 else "norte",
            "gender": "m",
            "accept_prepaga": False,
            "category": categories[4] if len(categories) > 4 else "Nutricionista",
            "bio": "Nutrición deportiva y control de peso.",
            "fee_range": "10000-14000",
            "weekly_hours": [(1, "15:00", "19:00"), (3, "15:00", "19:00"), (5, "10:00", "14:00")]  # Mar, Jue, Sáb
        }
    ]
    
    # Crear solo la cantidad solicitada
    professionals_to_create = test_professionals[:count]
    
    created_count = 0
    for prof_data in professionals_to_create:
        try:
            # Extraer campos que NO van en add_professional
            weekly_hours = prof_data.pop('weekly_hours', [])
            bio = prof_data.pop('bio', None)
            fee_range = prof_data.pop('fee_range', None)
            always_available = prof_data.pop('always_available', False)
            
            # Agregar profesional (solo campos básicos)
            success = db.add_professional(**prof_data)
            
            if success:
                # Agregar certificado simulado
                cert_path = f"certificates/{prof_data['phone']}/cert_test.jpg"
                db.update_certificate(prof_data['phone'], cert_path)
                
                # Actualizar bio y fee_range si existen
                if bio:
                    db.update_professional_bio(prof_data['phone'], bio)
                if fee_range:
                    db.update_professional_fee_range(prof_data['phone'], fee_range)
                
                # Agregar horarios semanales de ocupación
                for day, start, end in weekly_hours:
                    db.add_weekly_schedule(prof_data['phone'], day, start, end)
                
                # Si es el profesional demo, crear slots para los próximos 30 días
                if always_available:
                    print(f"   🔄 Creando slots automáticos para los próximos 30 días...")
                    today = date.today()
                    
                    # Crear slots de 1 hora desde las 9:00 hasta las 19:00 cada día
                    slots_created = 0
                    for days_ahead in range(1, 31):  # Próximos 30 días
                        slot_date = today + timedelta(days=days_ahead)
                        
                        # Crear slots cada hora
                        for hour in range(9, 19):  # 9:00 a 19:00
                            start_time = f"{hour:02d}:00"
                            end_time = f"{hour+1:02d}:00"
                            
                            try:
                                db.add_specific_free_slot(
                                    prof_data['phone'],
                                    slot_date.strftime('%Y-%m-%d'),
                                    start_time,
                                    end_time
                                )
                                slots_created += 1
                            except:
                                pass  # Ignorar duplicados
                    
                    print(f"   ✅ {slots_created} slots creados para demo")
                
                else:
                    # Para profesionales normales: marcar algunos slots libres para mañana y pasado
                    tomorrow = date.today() + timedelta(days=1)
                    day_after = date.today() + timedelta(days=2)
                    
                    # Horarios disponibles para mañana
                    free_slots_tomorrow = [
                        ("10:00", "11:00"),
                        ("14:00", "15:00"),
                        ("16:00", "17:00")
                    ]
                    
                    # Horarios disponibles para pasado mañana
                    free_slots_day_after = [
                        ("09:00", "10:00"),
                        ("15:00", "16:00")
                    ]
                
                
                created_count += 1
                
                # Mensaje de confirmación
                print(f"✅ Creado: {prof_data['name']}")
                print(f"   📍 Zona: {prof_data['zone']}")
                print(f"   📋 Categoría: {prof_data['category']}")
                print(f"   💳 Prepaga: {'Sí' if prof_data['accept_prepaga'] else 'No'}")
                print(f"   📅 Horarios: {len(weekly_hours)} días/semana")
                
                if always_available:
                    print(f"   ⭐ DEMO: Disponibilidad completa (30 días)")
                else:
                    print(f"   🆓 Slots libres: {len(free_slots_tomorrow)} (mañana) + {len(free_slots_day_after)} (pasado)")
                
                print()
                
        except Exception as e:
            print(f"❌ Error creando {prof_data['name']}: {e}\n")
    
    print("="*60)
    print(f"✅ {created_count}/{count} profesionales creados exitosamente")
    print("="*60 + "\n")
    
    # Mostrar estadísticas
    stats = db.get_stats()
    print("📊 Estadísticas actuales:")
    print(f"   Total profesionales: {stats.get('total_professionals', 0)}")
    print(f"   Búsquedas: {stats.get('total_searches', 0)}")
    print(f"   Contactos: {stats.get('total_contacts', 0)}\n")
    
    return created_count


def show_professionals():
    """Muestra todos los profesionales en la base de datos."""
    print("\n" + "="*60)
    print("📋 PROFESIONALES REGISTRADOS")
    print("="*60 + "\n")
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT phone, name, zone, gender, accept_prepaga, category
            FROM professionals
            ORDER BY name
        """)
        
        professionals = cursor.fetchall()
        
        if not professionals:
            print("⚠️  No hay profesionales registrados\n")
            return
        
        for prof in professionals:
            print(f"👤 {prof['name']}")
            print(f"   📱 {prof['phone']}")
            print(f"   📍 Zona: {prof['zone']}")
            print(f"   👥 Género: {prof['gender']}")
            print(f"   💳 Prepaga: {'Sí' if prof['accept_prepaga'] else 'No'}")
            print(f"   📋 Categoría: {prof['category']}\n")
        
        print(f"Total: {len(professionals)} profesionales\n")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Crear profesionales de prueba')
    parser.add_argument('--count', type=int, default=3, help='Número de profesionales a crear (default: 3)')
    parser.add_argument('--reset', action='store_true', help='Borrar profesionales existentes primero')
    parser.add_argument('--show', action='store_true', help='Mostrar profesionales existentes')
    
    args = parser.parse_args()
    
    if args.show:
        show_professionals()
    else:
        create_test_professionals(count=args.count, reset=args.reset)
        print("💡 Tip: Usa --show para ver todos los profesionales registrados")
        print("💡 Tip: Usa --reset para borrar y crear nuevos profesionales\n")