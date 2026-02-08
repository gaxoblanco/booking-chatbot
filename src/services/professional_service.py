"""
Professional Business Logic
============================
Handles all professional-side business logic including:
- Profile management (registration, updates)
- Certificate handling
- Schedule management (weekly, specific slots)
- Availability calculations
"""

from src.database.database import db
from datetime import datetime, timedelta, date, time
from typing import List, Dict, Optional, Tuple
import os


class ProfessionalService:
    """
    Service layer for professional operations.
    Implements business logic for profile and schedule management.
    """

    def __init__(self):
        """Initialize professional service."""
        self.db = db

    # ==========================================
    # PROFILE MANAGEMENT
    # ==========================================

    def register_or_update_professional(self, phone: str, **kwargs) -> bool:
        """
        Register a new professional or update existing one.
        Accepts partial updates - only provided fields are updated.
        """
        try:
            # Get existing professional if exists
            existing = self.db.get_professional(phone)

            # Merge with existing data (keep old values if not provided)
            if existing:
                data = {
                    'name': kwargs.get('name', existing.get('name')),
                    'email': kwargs.get('email', existing.get('email')),
                    'zone': kwargs.get('zone', existing.get('zone')),
                    'gender': kwargs.get('gender', existing.get('gender')),
                    'accept_prepaga': kwargs.get('accept_prepaga', existing.get('accept_prepaga', False)),
                    'category': kwargs.get('category', existing.get('category')),
                    # ← AGREGAR
                    'bio': kwargs.get('bio', existing.get('bio')),
                    # ← AGREGAR
                    'fee_range': kwargs.get('fee_range', existing.get('fee_range'))
                }
            else:
                # New professional - use provided values or None
                data = {
                    'name': kwargs.get('name'),
                    'email': kwargs.get('email'),
                    'zone': kwargs.get('zone'),
                    'gender': kwargs.get('gender'),
                    'accept_prepaga': kwargs.get('accept_prepaga', False),
                    'category': kwargs.get('category'),
                    'bio': kwargs.get('bio'),              # ← AGREGAR
                    'fee_range': kwargs.get('fee_range')   # ← AGREGAR
                }

            # Add to database
            success = self.db.add_professional(
                phone=phone,
                name=data['name'],
                email=data['email'],
                zone=data['zone'],
                gender=data['gender'],
                accept_prepaga=data['accept_prepaga'],
                category=data['category']  # ← CORREGIR: era 'especialidad'
            )

            # Update bio and fee_range separately if provided
            if success:
                if data.get('bio'):
                    self.db.update_professional_bio(phone, data['bio'])
                if data.get('fee_range'):
                    self.db.update_professional_fee_range(
                        phone, data['fee_range'])

                action = "updated" if existing else "registered"
                print(f"[PROF_SERVICE] ✅ Professional {action}: {phone}")

            return success

        except Exception as e:
            print(
                f"[PROF_SERVICE] ❌ Error registering/updating professional: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_professional_info(self, phone: str) -> Optional[Dict]:
        """
        Get complete professional information.

        Args:
            phone: Professional's phone

        Returns:
            Professional data or None
        """
        try:
            return self.db.get_professional(phone)
        except Exception as e:
            print(f"[PROF_SERVICE] ❌ Error getting professional info: {e}")
            return None

    def has_complete_profile(self, phone: str) -> bool:
        """
        Check if professional has completed all required profile fields.

        Args:
            phone: Professional's phone

        Returns:
            True if profile is complete, False otherwise
        """
        try:
            prof = self.db.get_professional(phone)
            if not prof:
                return False

            # Required fields
            required = ['name', 'email', 'zone', 'gender', 'certificate_path']

            for field in required:
                if not prof.get(field):
                    return False

            return True

        except Exception as e:
            print(f"[PROF_SERVICE] ❌ Error checking profile completion: {e}")
            return False

    def get_missing_profile_fields(self, phone: str) -> List[str]:
        """
        Get list of missing required profile fields.

        Args:
            phone: Professional's phone

        Returns:
            List of missing field names
        """
        try:
            prof = self.db.get_professional(phone)
            if not prof:
                return ['name', 'email', 'zone', 'gender', 'certificate_path']

            required = {
                'name': 'Nombre',
                'email': 'Email',
                'zone': 'Zona',
                'gender': 'Género',
                'certificate_path': 'Certificado'
            }

            missing = []
            for field, label in required.items():
                if not prof.get(field):
                    missing.append(label)

            return missing

        except Exception as e:
            print(f"[PROF_SERVICE] ❌ Error getting missing fields: {e}")
            return []

    # ==========================================
    # CERTIFICATE MANAGEMENT
    # ==========================================

    def save_certificate(self, phone: str, file_path: str) -> bool:
        """
        Save certificate file path for professional.

        Args:
            phone: Professional's phone
            file_path: Path where certificate is stored

        Returns:
            True if successful
        """
        try:
            success = self.db.update_certificate(phone, file_path)

            if success:
                print(
                    f"[PROF_SERVICE] ✅ Certificate saved: {phone} -> {file_path}")

            return success

        except Exception as e:
            print(f"[PROF_SERVICE] ❌ Error saving certificate: {e}")
            return False

    def has_certificate(self, phone: str) -> bool:
        """
        Check if professional has uploaded certificate.

        Args:
            phone: Professional's phone

        Returns:
            True if certificate exists
        """
        try:
            return self.db.professional_has_certificate(phone)
        except Exception as e:
            print(f"[PROF_SERVICE] ❌ Error checking certificate: {e}")
            return False

    def verify_certificate(self, phone: str) -> bool:
        """
        Manually verify a professional's certificate.
        For MVP: Auto-verification (always returns True if certificate exists).
        Future: Admin review process.

        Args:
            phone: Professional's phone

        Returns:
            True if verified
        """
        try:
            if not self.has_certificate(phone):
                print(
                    f"[PROF_SERVICE] ⚠️ No certificate to verify for {phone}")
                return False

            # MVP: Auto-verify
            print(f"[PROF_SERVICE] ✅ Certificate auto-verified for {phone}")
            return True

        except Exception as e:
            print(f"[PROF_SERVICE] ❌ Error verifying certificate: {e}")
            return False

    def get_certificate_path(self, phone: str) -> Optional[str]:
        """
        Get path to professional's certificate file.

        Args:
            phone: Professional's phone

        Returns:
            File path or None
        """
        try:
            prof = self.db.get_professional(phone)
            return prof.get('certificate_path') if prof else None
        except Exception as e:
            print(f"[PROF_SERVICE] ❌ Error getting certificate path: {e}")
            return None


    # ==========================================
    # SCHEDULE VIEWING & FORMATTING
    # ==========================================

    def format_profile_summary(self, phone: str) -> str:
        """
        Format professional profile summary for display.

        Args:
            phone: Professional's phone

        Returns:
            Formatted profile string
        """
        try:
            prof = self.get_professional_info(phone)
            if not prof:
                return "❌ Perfil no encontrado"

            output = "👨‍⚕️ TU PERFIL\n"
            output += "=" * 40 + "\n\n"

            output += f"📱 Teléfono: {prof['phone']}\n"
            output += f"👤 Nombre: {prof.get('name', '❌ No configurado')}\n"
            output += f"📧 Email: {prof.get('email', '❌ No configurado')}\n"
            output += f"📍 Zona: {self._format_zone(prof.get('zone'))}\n"
            output += f"👥 Género: {self._format_gender(prof.get('gender'))}\n"
            output += f"💳 Acepta Prepaga: {self._format_prepaga(prof.get('accept_prepaga'))}\n"
            output += f"📜 Certificado: {'✅ Cargado' if prof.get('certificate_path') else '❌ Falta'}\n\n"

            # Stats
            output += "📊 ESTADÍSTICAS:\n"
            output += f"   👁️ Vistas: {prof.get('total_views', 0)}\n"
            output += f"   📋 Perfil visto: {prof.get('total_profile_views', 0)}\n"
            output += f"   📞 Contactos: {prof.get('total_contacts', 0)}\n\n"

            # Check if profile is complete
            missing = self.get_missing_profile_fields(phone)
            if missing:
                output += f"⚠️ Campos faltantes: {', '.join(missing)}\n"
            else:
                output += "✅ Perfil completo\n"

            return output

        except Exception as e:
            print(f"[PROF_SERVICE] ❌ Error formatting profile: {e}")
            return "❌ Error al cargar perfil"

    # ==========================================
    # PRIVATE HELPERS
    # ==========================================

    def _format_zone(self, zone: str) -> str:
        """Format zone for display."""
        zones = {
            'norte': 'Zona Norte',
            'sur': 'Zona Sur'
        }
        return zones.get(zone, '❌ No configurada')

    def _format_prepaga(self, accepts: bool) -> str:
        """Format prepaga acceptance."""
        return "Sí" if accepts else "No"

    def _format_gender(self, gender: str) -> str:
        """Format gender for display."""
        genders = {
            'm': 'Masculino',
            'f': 'Femenino',
            'otro': 'Otro'
        }
        return genders.get(gender, '❌ No configurado')

    def get_available_slots(
        self,
        professional_phone: str,
        date: str,
        duration_minutes: int = 50,
        exclude_appointment_id: int = None
    ) -> List[Dict]:
        """
        Obtener slots disponibles desde Google Calendar con cache.
        
        Cache TTL: 15 minutos
        IMPORTANTE: No cachea resultados vacíos
        """
        from src.integrations.google_calendar_service import GoogleCalendarService
        from src.services.cache_manager import get_cached_slots, cache_slots
        import json
        
        try:
            # Obtener configuración del profesional
            professional = self.db.get_professional(professional_phone)
            
            if not professional:
                return []
            
            calendar_id = professional.get('calendar_id')
            if not calendar_id:
                print(f"[PROF_SERVICE] ⚠️ Profesional {professional_phone} sin calendar_id")
                return []
            
            # Verificar cache primero
            cached_slots = get_cached_slots(calendar_id, date)
            if cached_slots is not None:
                return cached_slots
            
            # Obtener working_hours
            working_hours_json = professional.get('working_hours')
            if working_hours_json:
                working_hours = json.loads(working_hours_json)
            else:
                working_hours = {'start': '09:00', 'end': '18:00'}
            
            print(f"[PROF_SERVICE] 🔍 Consultando Google Calendar...")
            print(f"[PROF_SERVICE]    Calendar: {calendar_id}")
            print(f"[PROF_SERVICE]    Date: {date}")
            print(f"[PROF_SERVICE]    Working hours: {working_hours}")
            
            # Consultar Google Calendar
            calendar_service = GoogleCalendarService()
            slots = calendar_service.get_available_slots(
                calendar_id,
                date,
                working_hours,
                duration_minutes
            )
            
            print(f"[PROF_SERVICE] 📊 Slots obtenidos: {len(slots)}")
            
            # ⭐ CRÍTICO: Solo cachear si hay slots
            if slots:
                cache_slots(calendar_id, date, slots)
                print(f"[PROF_SERVICE] 💾 Cached {len(slots)} slots")
            else:
                print(f"[PROF_SERVICE] ⚠️ No slots found - NOT CACHING empty result")
            
            return slots
            
        except Exception as e:
            print(f"[PROF_SERVICE] ❌ Error getting slots from Google Calendar: {e}")
            import traceback
            traceback.print_exc()
            return []
        
    def get_available_dates_for_reschedule(
        self,
        professional_phone: str,
        current_appointment_date: str,
        current_appointment_id: int,
        days_to_search: int = 7,
        max_dates: int = 7
    ) -> List[Dict]:
        """
        Obtener fechas disponibles para reprogramar una cita.

        Busca desde HOY hasta los próximos 7 días (semana actual).
        Excluye la fecha actual de la cita.

        Args:
            professional_phone: Teléfono del profesional
            current_appointment_date: Fecha actual de la cita (YYYY-MM-DD)
            current_appointment_id: ID de la cita a reprogramar
            days_to_search: Cuántos días buscar desde hoy (default 7)
            max_dates: Máximo de fechas a retornar (default 7)

        Returns:
            Lista de fechas disponibles:
            [
                {
                    'date': datetime.date(2025, 12, 12),
                    'date_str': '12/12/2025',
                    'day_name': 'Jueves',
                    'day_name_short': 'Jue',
                    'slots_count': 5,
                    'is_today': False,
                    'is_tomorrow': True
                },
                ...
            ]
        """
        from datetime import datetime, timedelta, date as date_type

        try:
            today = date_type.today()
            current_time = datetime.now()

            # Determinar desde qué día empezar
            # Si es muy tarde hoy (después de las 16:00), empezar desde mañana
            if current_time.hour >= 16:
                start_date = today + timedelta(days=1)
                print(
                    f"[PROF_SERVICE] ⏰ Es tarde ({current_time.hour}:00), empezando desde mañana")
            else:
                start_date = today
                print(f"[PROF_SERVICE] 📅 Buscando desde hoy")

            available_dates = []

            # Buscar en los próximos N días
            for days_ahead in range(days_to_search):
                check_date = start_date + timedelta(days=days_ahead)
                date_str_db = check_date.strftime("%Y-%m-%d")

                # ✅ IMPORTANTE: Excluir la fecha actual de la cita
                if date_str_db == current_appointment_date:
                    print(
                        f"[PROF_SERVICE] ⏭️  Saltando fecha actual de la cita: {date_str_db}")
                    continue

                # Obtener slots disponibles para esta fecha
                slots = self.get_available_slots(
                    professional_phone,
                    date_str_db,
                    duration_minutes=50,
                    exclude_appointment_id=current_appointment_id
                )

                # Si hay slots disponibles, agregar la fecha
                if slots:
                    # Nombres de días en español
                    day_names = ['Lunes', 'Martes', 'Miércoles',
                                 'Jueves', 'Viernes', 'Sábado', 'Domingo']
                    day_names_short = ['Lun', 'Mar',
                                       'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']

                    date_info = {
                        'date': check_date,
                        'date_str': check_date.strftime("%d/%m/%Y"),
                        'date_db': date_str_db,
                        'day_name': day_names[check_date.weekday()],
                        'day_name_short': day_names_short[check_date.weekday()],
                        'slots_count': len(slots),
                        'is_today': check_date == today,
                        'is_tomorrow': check_date == today + timedelta(days=1)
                    }

                    available_dates.append(date_info)

                    print(
                        f"[PROF_SERVICE] ✅ {date_info['day_name']} {date_info['date_str']}: {len(slots)} slots")

                    # Limitar cantidad de fechas
                    if len(available_dates) >= max_dates:
                        break

            return available_dates

        except Exception as e:
            print(f"[PROF_SERVICE] ❌ Error getting available dates: {e}")
            import traceback
            traceback.print_exc()
            return []

    def validate_calendar_access(self, calendar_id: str) -> bool:
        """
        Valida que tengamos acceso al calendario del profesional.
        
        Args:
            calendar_id: Email del calendario de Google
        
        Returns:
            bool: True si tenemos acceso, False si no
        """
        try:
            from src.integrations.google_calendar_service import GoogleCalendarService
            from datetime import datetime
            
            calendar_service = GoogleCalendarService()
            
            # Intentar acceder al calendario
            can_access = calendar_service.check_calendar_access(calendar_id)
            
            if can_access:
                print(f"[PROF_SERVICE] ✅ Acceso validado al calendario: {calendar_id}")
                return True
            else:
                print(f"[PROF_SERVICE] ❌ Sin acceso al calendario: {calendar_id}")
                return False
                
        except Exception as e:
            print(f"[PROF_SERVICE] ❌ Error validando acceso: {e}")
            return False

    def setup_google_calendar(self, phone: str, calendar_email: str) -> dict:
        """
        Configura Google Calendar para un profesional.
        
        Args:
            phone: Teléfono del profesional
            calendar_email: Email del calendario de Google
        
        Returns:
            dict: {'success': bool, 'message': str}
        """
        import json
        
        try:
            # Validar acceso
            if not self.validate_calendar_access(calendar_email):
                return {
                    'success': False,
                    'message': 'no_access'
                }
            
            # Configurar en la BD
            working_hours = {'start': '09:00', 'end': '18:00'}
            
            success = self.db.execute_query("""
                UPDATE professionals 
                SET 
                    calendar_id = ?,
                    working_hours = ?,
                    slot_duration = 60,
                    timezone = 'America/Argentina/Buenos_Aires'
                WHERE phone = ?
            """, (calendar_email, json.dumps(working_hours), phone))
            
            if success:
                print(f"[PROF_SERVICE] ✅ Google Calendar configurado: {phone}")
                return {
                    'success': True,
                    'message': 'configured'
                }
            else:
                return {
                    'success': False,
                    'message': 'db_error'
                }
                
        except Exception as e:
            print(f"[PROF_SERVICE] ❌ Error configurando calendar: {e}")
            return {
                'success': False,
                'message': 'error'
            }

# Global professional service instance
professional_service = ProfessionalService()
