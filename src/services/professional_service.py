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
    # WEEKLY SCHEDULE MANAGEMENT
    # ==========================================

    def add_weekly_busy_hours(self, phone: str, day_of_week: int,
                              start_time: str, end_time: str) -> bool:
        """
        Add recurring busy hours for a specific day of week.
        This schedule repeats every week.

        Args:
            phone: Professional's phone
            day_of_week: Day number (0=Monday, 6=Sunday)
            start_time: Start time in HH:MM format (e.g., "09:00")
            end_time: End time in HH:MM format (e.g., "17:00")

        Returns:
            True if successful

        Example:
            >>> # Mark every Monday 9am-5pm as busy
            >>> service.add_weekly_busy_hours("+5491112345678", 0, "09:00", "17:00")
            True
        """
        try:
            success = self.db.add_weekly_schedule(
                phone, day_of_week, start_time, end_time)

            if success:
                day_names = ['Lunes', 'Martes', 'Miércoles',
                             'Jueves', 'Viernes', 'Sábado', 'Domingo']
                print(
                    f"[PROF_SERVICE] ✅ Weekly schedule added: {day_names[day_of_week]} {start_time}-{end_time}")

            return success

        except Exception as e:
            print(f"[PROF_SERVICE] ❌ Error adding weekly schedule: {e}")
            return False

    def add_multiple_weekly_schedules(self, phone: str, schedules: List[Dict]) -> Tuple[int, int]:
        """
        Add multiple weekly schedules at once.
        Useful for "quick setup" where user provides full week.

        Args:
            phone: Professional's phone
            schedules: List of dictionaries with:
                - day_of_week: int (0-6)
                - start_time: str (HH:MM)
                - end_time: str (HH:MM)

        Returns:
            Tuple of (success_count, total_count)

        Example:
            >>> schedules = [
            ...     {"day_of_week": 0, "start_time": "09:00", "end_time": "17:00"},
            ...     {"day_of_week": 2, "start_time": "09:00", "end_time": "17:00"},
            ... ]
            >>> service.add_multiple_weekly_schedules("+5491112345678", schedules)
            (2, 2)
        """
        try:
            success_count = 0

            for schedule in schedules:
                if self.add_weekly_busy_hours(
                    phone,
                    schedule['day_of_week'],
                    schedule['start_time'],
                    schedule['end_time']
                ):
                    success_count += 1

            print(
                f"[PROF_SERVICE] ✅ Added {success_count}/{len(schedules)} weekly schedules")
            return (success_count, len(schedules))

        except Exception as e:
            print(f"[PROF_SERVICE] ❌ Error adding multiple schedules: {e}")
            return (0, len(schedules))

    def get_weekly_schedule(self, phone: str) -> List[Dict]:
        """
        Get all weekly recurring schedules for professional.

        Args:
            phone: Professional's phone

        Returns:
            List of schedule dictionaries
        """
        try:
            return self.db.get_weekly_schedule(phone)
        except Exception as e:
            print(f"[PROF_SERVICE] ❌ Error getting weekly schedule: {e}")
            return []

    def remove_weekly_schedule(self, phone: str, day_of_week: int,
                               start_time: str, end_time: str) -> bool:
        """
        Remove a specific weekly recurring schedule.

        Args:
            phone: Professional's phone
            day_of_week: Day number
            start_time: Start time
            end_time: End time

        Returns:
            True if successful
        """
        try:
            return self.db.remove_weekly_schedule(phone, day_of_week, start_time, end_time)
        except Exception as e:
            print(f"[PROF_SERVICE] ❌ Error removing weekly schedule: {e}")
            return False

    def clear_all_weekly_schedules(self, phone: str) -> bool:
        """
        Remove ALL weekly schedules for a professional.
        Used for "reset" functionality.

        Args:
            phone: Professional's phone

        Returns:
            True if successful
        """
        try:
            schedules = self.get_weekly_schedule(phone)
            success_count = 0

            for schedule in schedules:
                if self.remove_weekly_schedule(
                    phone,
                    schedule['day_of_week'],
                    schedule['start_time'],
                    schedule['end_time']
                ):
                    success_count += 1

            print(f"[PROF_SERVICE] ✅ Cleared {success_count} weekly schedules")
            return success_count == len(schedules)

        except Exception as e:
            print(f"[PROF_SERVICE] ❌ Error clearing schedules: {e}")
            return False

    # ==========================================
    # SPECIFIC FREE SLOT MANAGEMENT
    # ==========================================

    def mark_slot_as_free(self, phone: str, date_str: str,
                          start_time: str, end_time: str) -> bool:
        """
        Mark a specific date/time slot as FREE.
        This OVERRIDES the weekly recurring schedule.

        Use case: Client cancelled, professional has unexpected opening.

        Args:
            phone: Professional's phone
            date_str: Date in YYYY-MM-DD format (e.g., "2025-11-15")
            start_time: Start time in HH:MM format
            end_time: End time in HH:MM format

        Returns:
            True if successful

        Example:
            >>> # Client cancelled Monday 2pm slot
            >>> service.mark_slot_as_free("+5491112345678", "2025-11-15", "14:00", "15:00")
            True
        """
        try:
            success = self.db.add_free_slot(
                phone, date_str, start_time, end_time)

            if success:
                print(
                    f"[PROF_SERVICE] ✅ Slot marked as FREE: {date_str} {start_time}-{end_time}")

            return success

        except Exception as e:
            print(f"[PROF_SERVICE] ❌ Error marking slot as free: {e}")
            return False

    def get_free_slots(self, phone: str, future_only: bool = True) -> List[Dict]:
        """
        Get all specific free slots for professional.

        Args:
            phone: Professional's phone
            future_only: If True, only return future slots (default)

        Returns:
            List of free slot dictionaries
        """
        try:
            if future_only:
                today = datetime.now().strftime("%Y-%m-%d")
                return self.db.get_free_slots(phone, from_date=today)
            else:
                return self.db.get_free_slots(phone)
        except Exception as e:
            print(f"[PROF_SERVICE] ❌ Error getting free slots: {e}")
            return []

    def remove_free_slot(self, phone: str, date_str: str,
                         start_time: str, end_time: str) -> bool:
        """
        Remove a specific free slot.
        Used when slot gets booked or professional changes mind.

        Args:
            phone: Professional's phone
            date_str: Date in YYYY-MM-DD format
            start_time: Start time
            end_time: End time

        Returns:
            True if successful
        """
        try:
            return self.db.remove_free_slot(phone, date_str, start_time, end_time)
        except Exception as e:
            print(f"[PROF_SERVICE] ❌ Error removing free slot: {e}")
            return False

    # ==========================================
    # SCHEDULE VIEWING & FORMATTING
    # ==========================================

    def get_complete_schedule(self, phone: str) -> Dict:
        """
        Get complete schedule including weekly and specific free slots.

        Args:
            phone: Professional's phone

        Returns:
            Dictionary with:
                - weekly_schedule: List of recurring schedules
                - free_slots: List of specific free slots
                - formatted: Human-readable formatted schedule
        """
        try:
            weekly = self.get_weekly_schedule(phone)
            free_slots = self.get_free_slots(phone, future_only=True)

            return {
                'weekly_schedule': weekly,
                'free_slots': free_slots,
                'formatted': self.format_schedule(weekly, free_slots)
            }

        except Exception as e:
            print(f"[PROF_SERVICE] ❌ Error getting complete schedule: {e}")
            return {
                'weekly_schedule': [],
                'free_slots': [],
                'formatted': "Error al obtener agenda"
            }

    def format_schedule(self, weekly_schedule: List[Dict], free_slots: List[Dict]) -> str:
        """
        Format schedule for WhatsApp display.

        Args:
            weekly_schedule: List of weekly schedules
            free_slots: List of specific free slots

        Returns:
            Formatted string for display
        """
        output = "📅 TU AGENDA\n"
        output += "=" * 40 + "\n\n"

        # Weekly schedule
        if weekly_schedule:
            output += "📆 HORARIOS OCUPADOS (Recurrentes):\n"

            # Group by day
            by_day = {}
            for schedule in weekly_schedule:
                day = schedule['day_of_week']
                if day not in by_day:
                    by_day[day] = []
                by_day[day].append(
                    f"{schedule['start_time']}-{schedule['end_time']}")

            day_names = ['Lunes', 'Martes', 'Miércoles',
                         'Jueves', 'Viernes', 'Sábado', 'Domingo']
            for day in range(7):
                if day in by_day:
                    output += f"   ❌ {day_names[day]}: {', '.join(by_day[day])}\n"
                else:
                    output += f"   ✅ {day_names[day]}: Disponible\n"
            output += "\n"
        else:
            output += "📆 No tienes horarios ocupados recurrentes configurados.\n\n"

        # Specific free slots
        if free_slots:
            output += "🆓 HORARIOS LIBRES ESPECÍFICOS:\n"
            for slot in free_slots[:10]:  # Show max 10
                output += f"   ✅ {slot['date']} {slot['start_time']}-{slot['end_time']}\n"

            if len(free_slots) > 10:
                output += f"   ... y {len(free_slots) - 10} más\n"
            output += "\n"
        else:
            output += "🆓 No tienes horarios libres específicos marcados.\n\n"

        output += "💡 Los clientes verán tu disponibilidad basada en esta agenda."

        return output

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
        Obtener slots disponibles para un profesional en una fecha específica.

        Genera slots basándose en:
        1. Horarios libres específicos (specific_free_slots)
        2. Horario laboral general (9:00-18:00 si no hay weekly_schedule)
        3. Excluye slots ocupados por citas existentes

        Args:
            professional_phone: Teléfono del profesional
            date: Fecha en formato YYYY-MM-DD
            duration_minutes: Duración de cada slot (default 50 min)
            exclude_appointment_id: ID de cita a excluir (para reprogramación)

        Returns:
            Lista de slots disponibles:
            [
                {
                    'start_time': '10:00',
                    'end_time': '10:50',
                    'date': '2025-12-15'
                },
                ...
            ]
        """
        from datetime import datetime, timedelta

        try:
            # Convertir fecha a datetime
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            day_of_week = date_obj.weekday()  # 0=Lunes, 6=Domingo

            available_slots = []

            # ==========================================
            # PASO 1: Verificar slots libres específicos
            # ==========================================
            specific_free_slots = self.db.get_free_slots(
                professional_phone,
                from_date=date
            )

            for free_slot in specific_free_slots:
                if free_slot['date'] == date:
                    # Este día tiene un slot libre específico
                    start_time = datetime.strptime(
                        free_slot['start_time'], "%H:%M")
                    end_time = datetime.strptime(
                        free_slot['end_time'], "%H:%M")

                    # Generar slots de duración específica dentro del rango
                    current_time = start_time
                    while current_time + timedelta(minutes=duration_minutes) <= end_time:
                        slot_start = current_time.strftime("%H:%M")
                        slot_end = (
                            current_time + timedelta(minutes=duration_minutes)).strftime("%H:%M")

                        # Verificar que el slot no esté ocupado
                        is_available = self.db.check_slot_availability(
                            professional_phone,
                            date,
                            slot_start,
                            slot_end,
                            exclude_appointment_id=exclude_appointment_id
                        )

                        if is_available:
                            available_slots.append({
                                'start_time': slot_start,
                                'end_time': slot_end,
                                'date': date
                            })

                        # Avanzar al siguiente slot (con buffer de 10 min)
                        current_time += timedelta(minutes=duration_minutes + 10)

            # Si hay slots específicos, solo retornar esos
            if available_slots:
                return available_slots

            # ==========================================
            # PASO 2: Verificar horario semanal
            # ==========================================
            weekly_schedule = self.db.get_weekly_schedule(professional_phone)

            # Buscar si este día está en el horario semanal
            day_schedule = None
            for schedule in weekly_schedule:
                if schedule['day_of_week'] == day_of_week and not schedule.get('is_busy', True):
                    day_schedule = schedule
                    break

            # Si no hay horario semanal para este día, usar horario por defecto
            if not day_schedule:
                # Verificar si el día está marcado como ocupado
                is_busy_day = any(
                    s['day_of_week'] == day_of_week and s.get('is_busy', True)
                    for s in weekly_schedule
                )

                if is_busy_day:
                    # Día completamente ocupado en el schedule semanal
                    return []

                # Día no tiene schedule = usar horario por defecto 9:00-18:00
                start_time = datetime.strptime("09:00", "%H:%M")
                end_time = datetime.strptime("18:00", "%H:%M")
            else:
                # Usar horario del schedule semanal
                start_time = datetime.strptime(
                    day_schedule['start_time'], "%H:%M")
                end_time = datetime.strptime(day_schedule['end_time'], "%H:%M")

            # ==========================================
            # PASO 3: Generar slots dentro del horario
            # ==========================================
            current_time = start_time
            while current_time + timedelta(minutes=duration_minutes) <= end_time:
                slot_start = current_time.strftime("%H:%M")
                slot_end = (
                    current_time + timedelta(minutes=duration_minutes)).strftime("%H:%M")

                # Verificar que el slot no esté ocupado por una cita
                is_available = self.db.check_slot_availability(
                    professional_phone,
                    date,
                    slot_start,
                    slot_end,
                    exclude_appointment_id=exclude_appointment_id
                )

                if is_available:
                    available_slots.append({
                        'start_time': slot_start,
                        'end_time': slot_end,
                        'date': date
                    })

                # Avanzar al siguiente slot (duración + 10 min de buffer)
                current_time += timedelta(minutes=duration_minutes + 10)

            return available_slots

        except Exception as e:
            print(f"[PROF_SERVICE] ❌ Error getting available slots: {e}")
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


# Global professional service instance
professional_service = ProfessionalService()
