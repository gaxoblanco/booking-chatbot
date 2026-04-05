"""
Script para carga masiva de profesionales desde CSV.

Formato del CSV:
phone,name,email,calendar_email,zone,gender,accept_prepaga,category

Ejemplo:
+5491112345678,Dr. Juan Pérez,juan@email.com,juan.perez@gmail.com,norte,m,1,Médico General
+5491187654321,Dra. María González,maria@email.com,maria.gonzalez@gmail.com,sur,f,0,Dentista

Uso:
    python scripts/load_professionals_from_csv.py profesionales.csv
    docker exec whatsapp-demo python3 scripts/csv/load_professionals_from_csv.py /app/data/csv_src/profesionales_demo.csv
"""

import sys
sys.path.append('.')

import csv
import json
import time
from pathlib import Path
from src.database.database import db
from src.services.professional_service import professional_service
from src.integrations.google_calendar_service import GoogleCalendarService


def parse_boolean(value: str) -> bool:
    """Convierte string a boolean."""
    return value.lower() in ['1', 'true', 'si', 'sí', 'yes', 's', 'y']

def parse_horario(horario_str: str) -> dict:
    """
    Convierte el string de horario del CSV al JSON por día que espera la BD.

    Formato de entrada:  "lunes:09:00-17:00|martes:09:00-17:00|viernes:09:00-13:00"
    Formato de salida:   {"lunes": {"start": "09:00", "end": "17:00"}, ...}

    Días válidos: lunes, martes, miercoles, jueves, viernes, sabado, domingo
    Días no incluidos = el profesional no trabaja ese día.
    Retorna dict vacío si el string es vacío o inválido.
    """
    dias_validos = {'lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo'}
    result = {}

    if not horario_str or not horario_str.strip():
        return result

    for bloque in horario_str.strip().split('|'):
        bloque = bloque.strip()
        if ':' not in bloque:
            print(f"      ⚠️  Bloque de horario inválido (sin día): '{bloque}'")
            continue

        # Separar día del rango horario — el día es la primera parte antes del primer ':'
        partes = bloque.split(':', 1)
        dia = partes[0].strip().lower()
        rango = partes[1].strip()  # "09:00-17:00"

        if dia not in dias_validos:
            print(f"      ⚠️  Día no reconocido: '{dia}' — se ignora")
            continue

        if '-' not in rango:
            print(f"      ⚠️  Rango horario inválido para {dia}: '{rango}'")
            continue

        start, end = rango.split('-', 1)
        result[dia] = {'start': start.strip(), 'end': end.strip()}

    return result

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
            required_columns = ['phone', 'name', 'email', 'calendar_email', 'gender', 'accept_prepaga', 'category']
            if not all(col in reader.fieldnames for col in required_columns):
                print(f"❌ ERROR: El CSV debe tener estas columnas:")
                print(f"   {', '.join(required_columns)}")
                return
            
            for row in reader:
                # Saltear fila de descripción (REQUERIDO / opcional)
                if row['phone'].strip().upper() in ('REQUERIDO', 'OPCIONAL', 'REQUIRED', 'OPTIONAL'):
                    continue

                stats['total'] += 1
                
                phone = row['phone'].strip()
                name = row['name'].strip()
                email = row['email'].strip()
                calendar_email = row['calendar_email'].strip()
                zone = row.get('zone', '').strip().lower() or None
                gender = row['gender'].strip().lower()
                accept_prepaga = parse_boolean(row['accept_prepaga'])
                category = row['category'].strip()
                slot_duration = int(row.get('slot_duration', '60').strip() or 60)
                working_hours = parse_horario(row.get('horario', ''))
                
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

                # 3a. Guardar calendar_email en BD siempre (aunque no tenga acceso aún)
                # Necesario para que validate_pending_calendars.py pueda revalidar después
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE professionals
                        SET calendar_email = ?
                        WHERE phone = ?
                    """, (calendar_email, phone))

                # 3b. Validar acceso a Google Calendar con reintentos
                print(f"\n   📅 Validando acceso a Google Calendar...")
                print(f"      Calendario: {calendar_email}")
                

                # 4 intentos con espera incremental: 2s, 5s, 10s, 20s
                INTENTOS      = 4
                ESPERAS       = [2, 5, 10, 20]
                has_access    = False

                for intento in range(1, INTENTOS + 1):
                    has_access = professional_service.validate_calendar_access(calendar_email)
                    if has_access:
                        break
                    if intento < INTENTOS:
                        espera = ESPERAS[intento - 1]
                        print(f"      ⏳ Intento {intento}/{INTENTOS} fallido — reintentando en {espera}s...")
                        time.sleep(espera)
                    else:
                        print(f"      ❌ Intento {intento}/{INTENTOS} fallido — sin acceso")

                if has_access:
                    print(f"      ✅ Acceso confirmado (intento {intento}/{INTENTOS})")
                    stats['con_calendar'] += 1

                    # Crear calendario secundario y compartirlo con el profesional
                    result = professional_service.setup_google_calendar(
                        phone=phone,
                        calendar_email=calendar_email,
                        professional_name=name
                    )

                    if result['success']:
                        # Guardar working_hours y slot_duration del CSV
                        # (setup_google_calendar solo guarda calendar_id y timezone)
                        with db.get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("""
                                UPDATE professionals
                                SET
                                    working_hours = ?,
                                    slot_duration = ?
                                WHERE phone = ?
                            """, (json.dumps(working_hours), slot_duration, phone))

                        dias_configurados = list(working_hours.keys()) if working_hours else []
                        print(f"      ✅ Calendario secundario: {result['calendar_id']}")
                        print(f"      ⏱️  Slot duration: {slot_duration} min")
                        print(f"      📅 Días: {', '.join(dias_configurados) if dias_configurados else 'ninguno'}")
                    else:
                        print(f"      ❌ Error creando calendario secundario: {result['message']}")
                        stats['errores'] += 1
                else:
                    # Agoté los reintentos → guardar para enviar email
                    stats['sin_calendar'] += 1
                    profesionales_sin_acceso.append({
                        'name':           name,
                        'email':          calendar_email, # email instructivo va a la cuenta de Google
                        'phone':          phone,
                        'calendar_email': calendar_email,
                    })
                    print(f"      📧 Se enviará email de solicitud a {email}")
        
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
        
        # ── Profesionales sin acceso → enviar email ──────────────────────────
        if profesionales_sin_acceso:
            print(f"\n{'='*70}")
            print(f"⚠️  PROFESIONALES SIN ACCESO A GOOGLE CALENDAR")
            print(f"{'='*70}")
            print(f"\n   {len(profesionales_sin_acceso)} profesional(es) no pudieron validar el calendario")
            print(f"   después de 4 intentos. Se les enviará email con instrucciones.\n")

            for i, prof in enumerate(profesionales_sin_acceso, 1):
                print(f"   {i}. {prof['name']} ({prof['phone']})")
                print(f"      📧 {prof['email']}  |  📅 {prof['calendar_email']}")

            # Enviar emails si SMTP está configurado
            try:
                from src.integrations.email.email_service import is_configured
                from src.integrations.email.calendar_invitation import send_calendar_invitations

                if is_configured():
                    print(f"\n   📤 Enviando emails...")
                    email_stats = send_calendar_invitations(
                        profesionales_sin_acceso,
                        service_account_email,
                    )
                    print(f"\n   ✅ Enviados  : {email_stats['enviados']}")
                    print(f"   ❌ Errores   : {email_stats['errores']}")
                    print(f"   ⚠️  Sin email  : {email_stats['sin_email']}")
                else:
                    print(f"\n   💡 SMTP no configurado — emails no enviados.")
                    print(f"      Agregá SMTP_HOST, SMTP_USER y SMTP_PASSWORD al .env")
                    print(f"      o ejecutá manualmente:")
                    print(f"      docker exec -it whatsapp-demo python scripts/send_calendar_invitations.py")

            except ImportError:
                print(f"\n   ⚠️  Módulo de email no instalado — emails no enviados.")
                print(f"      Revisá src/integrations/email/")

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
        writer.writerow(['phone', 'name', 'email', 'calendar_email', 'zone', 'gender', 'accept_prepaga', 'category', 'slot_duration', 'horario'])
        
        # Ejemplos
        writer.writerow(['+5491112345678', 'Dr. Juan Pérez', 'juan@email.com', 'juan.perez@gmail.com', 'norte', 'm', '1', 'Médico General', '40', 'lunes:09:00-17:00|martes:09:00-17:00|miercoles:09:00-17:00|jueves:09:00-17:00|viernes:09:00-13:00'])
        writer.writerow(['+5491187654321', 'Dra. María González', 'maria@email.com', 'maria.gonzalez@gmail.com', 'sur', 'f', '0', 'Dentista', '30', 'lunes:10:00-18:00|miercoles:10:00-18:00|viernes:10:00-18:00'])
        writer.writerow(['+5491156789012', 'Lic. Carlos Rodríguez', 'carlos@email.com', 'carlos.rodriguez@gmail.com', 'norte', 'm', '1', 'Psicólogo', '50', 'martes:09:00-17:00|jueves:09:00-17:00|sabado:10:00-14:00'])
    
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