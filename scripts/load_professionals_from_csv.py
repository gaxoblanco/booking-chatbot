"""
Script para carga masiva de profesionales desde CSV.

Formato del CSV:
phone,name,email,calendar_email,zone,gender,accept_prepaga,category

Ejemplo:
+5491112345678,Dr. Juan Pérez,juan@email.com,juan.perez@gmail.com,norte,m,1,Médico General
+5491187654321,Dra. María González,maria@email.com,maria.gonzalez@gmail.com,sur,f,0,Dentista

Uso:
    python scripts/load_professionals_from_csv.py profesionales.csv
"""

import sys
sys.path.append('.')

import csv
import json
from pathlib import Path
from src.database.database import db
from src.services.professional_service import professional_service
from src.integrations.google_calendar_service import GoogleCalendarService


def parse_boolean(value: str) -> bool:
    """Convierte string a boolean."""
    return value.lower() in ['1', 'true', 'si', 'sí', 'yes', 's', 'y']


def load_professionals_from_csv(csv_path: str):
    """
    Carga profesionales desde un archivo CSV.
    
    Args:
        csv_path: Ruta al archivo CSV
    """
    
    if not Path(csv_path).exists():
        print(f"❌ ERROR: Archivo no encontrado: {csv_path}")
        return
    
    print("\n" + "="*70)
    print("📋 CARGA MASIVA DE PROFESIONALES DESDE CSV")
    print("="*70)
    
    # Obtener email de Service Account
    calendar_service = GoogleCalendarService()
    service_account_email = calendar_service.get_service_account_email()
    
    print(f"\n📧 Service Account Email:")
    print(f"   {service_account_email}")
    print(f"\nLos profesionales deben compartir su calendario con este email.")
    print("="*70)
    
    # Estadísticas
    stats = {
        'total': 0,
        'nuevos': 0,
        'actualizados': 0,
        'sin_cambios': 0,
        'con_calendar': 0,
        'sin_calendar': 0,
        'errores': 0
    }
    
    profesionales_sin_acceso = []
    
    # Leer CSV
    try:
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            # Validar columnas requeridas
            required_columns = ['phone', 'name', 'email', 'calendar_email', 'zone', 'gender', 'accept_prepaga', 'category']
            if not all(col in reader.fieldnames for col in required_columns):
                print(f"❌ ERROR: El CSV debe tener estas columnas:")
                print(f"   {', '.join(required_columns)}")
                return
            
            for row in reader:
                stats['total'] += 1
                
                phone = row['phone'].strip()
                name = row['name'].strip()
                email = row['email'].strip()
                calendar_email = row['calendar_email'].strip()
                zone = row['zone'].strip().lower()
                gender = row['gender'].strip().lower()
                accept_prepaga = parse_boolean(row['accept_prepaga'])
                category = row['category'].strip()
                
                print(f"\n{'='*70}")
                print(f"📋 Procesando: {name} ({phone})")
                print(f"{'='*70}")
                
                # 1. Verificar si ya existe
                existing = db.get_professional(phone)
                
                if existing:
                    print(f"   ℹ️  Profesional ya existe en BD")
                    
                    # Comparar datos
                    cambios = []
                    if existing.get('name') != name:
                        cambios.append(f"nombre: '{existing.get('name')}' → '{name}'")
                    if existing.get('email') != email:
                        cambios.append(f"email: '{existing.get('email')}' → '{email}'")
                    if existing.get('zone') != zone:
                        cambios.append(f"zona: '{existing.get('zone')}' → '{zone}'")
                    if existing.get('gender') != gender:
                        cambios.append(f"género: '{existing.get('gender')}' → '{gender}'")
                    if existing.get('accept_prepaga') != accept_prepaga:
                        cambios.append(f"prepaga: {existing.get('accept_prepaga')} → {accept_prepaga}")
                    if existing.get('category') != category:
                        cambios.append(f"categoría: '{existing.get('category')}' → '{category}'")
                    if existing.get('calendar_id') != calendar_email:
                        cambios.append(f"calendar: '{existing.get('calendar_id')}' → '{calendar_email}'")
                    
                    if cambios:
                        print(f"   ⚠️  Cambios detectados:")
                        for cambio in cambios:
                            print(f"      - {cambio}")
                        
                        # Actualizar
                        success = db.add_professional(
                            phone=phone,
                            name=name,
                            email=email,
                            zone=zone,
                            gender=gender,
                            accept_prepaga=accept_prepaga,
                            category=category
                        )
                        
                        if success:
                            stats['actualizados'] += 1
                            print(f"   ✅ Datos actualizados")
                        else:
                            stats['errores'] += 1
                            print(f"   ❌ Error al actualizar")
                            continue
                    else:
                        stats['sin_cambios'] += 1
                        print(f"   ✅ Datos sin cambios")
                else:
                    # 2. Crear nuevo profesional
                    print(f"   🆕 Nuevo profesional")
                    
                    success = db.add_professional(
                        phone=phone,
                        name=name,
                        email=email,
                        zone=zone,
                        gender=gender,
                        accept_prepaga=accept_prepaga,
                        category=category
                    )
                    
                    if success:
                        stats['nuevos'] += 1
                        print(f"   ✅ Profesional creado")
                    else:
                        stats['errores'] += 1
                        print(f"   ❌ Error al crear")
                        continue
                
                # 3. Validar acceso a Google Calendar
                print(f"\n   📅 Validando acceso a Google Calendar...")
                print(f"      Calendario: {calendar_email}")
                
                has_access = professional_service.validate_calendar_access(calendar_email)
                
                if has_access:
                    print(f"      ✅ Acceso confirmado")
                    stats['con_calendar'] += 1
                    
                    # Configurar Google Calendar
                    working_hours = {'start': '09:00', 'end': '18:00'}
                    
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
                    
                    print(f"      ✅ Google Calendar configurado")
                    
                else:
                    print(f"      ❌ Sin acceso al calendario")
                    stats['sin_calendar'] += 1
                    profesionales_sin_acceso.append({
                        'name': name,
                        'phone': phone,
                        'calendar_email': calendar_email
                    })
        
        # Resumen final
        print("\n" + "="*70)
        print("📊 RESUMEN DE CARGA")
        print("="*70)
        print(f"\n📈 Estadísticas:")
        print(f"   Total procesados: {stats['total']}")
        print(f"   🆕 Nuevos: {stats['nuevos']}")
        print(f"   🔄 Actualizados: {stats['actualizados']}")
        print(f"   ✅ Sin cambios: {stats['sin_cambios']}")
        print(f"   ❌ Errores: {stats['errores']}")
        print(f"\n📅 Google Calendar:")
        print(f"   ✅ Con acceso: {stats['con_calendar']}")
        print(f"   ❌ Sin acceso: {stats['sin_calendar']}")
        
        # Listar profesionales sin acceso
        if profesionales_sin_acceso:
            print(f"\n{'='*70}")
            print(f"⚠️  PROFESIONALES SIN ACCESO A GOOGLE CALENDAR")
            print(f"{'='*70}")
            print(f"\nEstos profesionales NO aparecerán en búsquedas hasta que compartan")
            print(f"su calendario con: {service_account_email}\n")
            
            for i, prof in enumerate(profesionales_sin_acceso, 1):
                print(f"{i}. {prof['name']} ({prof['phone']})")
                print(f"   📧 Calendario: {prof['calendar_email']}")
                print()
            
            print(f"📋 INSTRUCCIONES PARA COMPARTIR:")
            print(f"1. Abrir Google Calendar: https://calendar.google.com")
            print(f"2. En 'Mis calendarios' → Click en ⋮ del calendario")
            print(f"3. 'Configuración y uso compartido'")
            print(f"4. 'Compartir con personas específicas' → '+ Agregar personas'")
            print(f"5. Pegar: {service_account_email}")
            print(f"6. Permisos: 'Hacer cambios en eventos'")
            print(f"7. Click 'Enviar'")
            print(f"8. Esperar 1-2 minutos")
            print(f"9. Ejecutar este script nuevamente")
        else:
            print(f"\n✅ Todos los profesionales tienen acceso a Google Calendar")
        
        print("\n" + "="*70)
        print("✅ CARGA COMPLETADA")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


def create_template_csv():
    """Crea un archivo CSV de ejemplo."""
    template_path = 'profesionales_template.csv'
    
    with open(template_path, 'w', encoding='utf-8', newline='') as file:
        writer = csv.writer(file)
        
        # Header
        writer.writerow(['phone', 'name', 'email', 'calendar_email', 'zone', 'gender', 'accept_prepaga', 'category'])
        
        # Ejemplos
        writer.writerow(['+5491112345678', 'Dr. Juan Pérez', 'juan@email.com', 'juan.perez@gmail.com', 'norte', 'm', '1', 'Médico General'])
        writer.writerow(['+5491187654321', 'Dra. María González', 'maria@email.com', 'maria.gonzalez@gmail.com', 'sur', 'f', '0', 'Dentista'])
        writer.writerow(['+5491156789012', 'Lic. Carlos Rodríguez', 'carlos@email.com', 'carlos.rodriguez@gmail.com', 'norte', 'm', '1', 'Psicólogo'])
    
    print(f"✅ Template creado: {template_path}")
    print(f"\nEdita este archivo con los datos reales y ejecuta:")
    print(f"   python scripts/load_professionals_from_csv.py {template_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\n❌ ERROR: Debes proporcionar la ruta al archivo CSV")
        print("\nUso:")
        print("   python scripts/load_professionals_from_csv.py profesionales.csv")
        print("\nPara crear un template de ejemplo:")
        print("   python scripts/load_professionals_from_csv.py --template")
        sys.exit(1)
    
    if sys.argv[1] == '--template':
        create_template_csv()
    else:
        csv_path = sys.argv[1]
        load_professionals_from_csv(csv_path)
