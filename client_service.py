"""
Client Business Logic
=====================
Handles all client-side business logic including:
- Professional searches with filters
- Availability calculations
- Result ranking and randomization
- Analytics tracking
"""

from database import db
from datetime import datetime, timedelta, date, time
from typing import List, Dict, Optional, Tuple
import random


class ClientService:
    """
    Service layer for client operations.
    Implements business logic for searching and contacting professionals.
    """

    def __init__(self):
        """Initialize client service."""
        self.db = db

    # ==========================================
    # AVAILABILITY CHECKING
    # ==========================================

    def is_professional_available(self, phone: str, date_str: str, time_str: str) -> bool:
        """
        Check if professional is available on specific date and time.

        Business Logic:
        1. Check if there's a specific free slot for that date/time → AVAILABLE
        2. Check weekly schedule for that day/time → If busy, NOT AVAILABLE
        3. If not in weekly schedule → AVAILABLE (default)

        Args:
            phone: Professional's phone
            date_str: Date in YYYY-MM-DD format (e.g., "2025-11-15")
            time_str: Time in HH:MM format (e.g., "14:00")

        Returns:
            True if available, False if busy

        Examples:
            >>> service.is_professional_available("+5491112345678", "2025-11-15", "14:00")
            True
        """
        try:
            # Parse date to get day of week
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            day_of_week = date_obj.weekday()  # 0=Monday, 6=Sunday

            # Step 1: Check specific free slots (highest priority)
            free_slots = self.db.get_free_slots(phone, from_date=date_str)
            for slot in free_slots:
                if slot['date'] == date_str:
                    # Check if time falls within this free slot
                    if slot['start_time'] <= time_str < slot['end_time']:
                        return True  # Has specific free slot

            # Step 2: Check weekly schedule (recurring busy hours)
            weekly = self.db.get_weekly_schedule(phone)
            for schedule in weekly:
                if schedule['day_of_week'] == day_of_week:
                    # Check if time falls within busy hours
                    if schedule['start_time'] <= time_str < schedule['end_time']:
                        return False  # Is busy in weekly schedule

            # Step 3: Not in schedule = Available by default
            return True

        except Exception as e:
            print(f"[CLIENT] ❌ Error checking availability: {e}")
            return False

    def count_available_hours_today(self, phone: str) -> int:
        """
        Count how many hours a professional is available TODAY.
        Counts hours from current time until end of day.

        Args:
            phone: Professional's phone

        Returns:
            Number of available hours remaining today
        """
        try:
            now = datetime.now()
            today_str = now.strftime("%Y-%m-%d")
            current_hour = now.hour

            available_hours = 0

            # Check each hour from now until 23:00
            for hour in range(current_hour, 24):
                time_str = f"{hour:02d}:00"
                if self.is_professional_available(phone, today_str, time_str):
                    available_hours += 1

            return available_hours

        except Exception as e:
            print(f"[CLIENT] ❌ Error counting today's hours: {e}")
            return 0

    def count_available_hours_date(self, phone: str, date_str: str) -> int:
        """
        Count available hours for a specific date (full day 00:00-23:59).

        Args:
            phone: Professional's phone
            date_str: Date in YYYY-MM-DD format

        Returns:
            Number of available hours on that date
        """
        try:
            available_hours = 0

            # Check each hour of the day
            for hour in range(24):
                time_str = f"{hour:02d}:00"
                if self.is_professional_available(phone, date_str, time_str):
                    available_hours += 1

            return available_hours

        except Exception as e:
            print(f"[CLIENT] ❌ Error counting date hours: {e}")
            return 0

    def count_available_hours_week(self, phone: str) -> int:
        """
        Count total available hours in the next 7 days.

        Args:
            phone: Professional's phone

        Returns:
            Total available hours in next week
        """
        try:
            total_hours = 0
            today = datetime.now().date()

            # Check next 7 days
            for day_offset in range(7):
                check_date = today + timedelta(days=day_offset)
                date_str = check_date.strftime("%Y-%m-%d")
                total_hours += self.count_available_hours_date(phone, date_str)

            return total_hours

        except Exception as e:
            print(f"[CLIENT] ❌ Error counting week hours: {e}")
            return 0

    # ==========================================
    # SEARCH OPERATIONS
    # ==========================================

    def search_professionals_by_filters(self, zone: str = None, gender: str = None,
                                        accept_prepaga: bool = None, online_sessions: bool = None,
                                        date_str: str = None, time_str: str = None,
                                        limit: int = 10) -> List[Dict]:
        """
        Search professionals with filters.
        Returns up to 'limit' professionals with most availability.

        Business Logic:
        1. Apply base filters (zone, gender, prepaga, online_sessions)
        2. If date/time specified, filter only available at that time
        3. Rank by availability (hours available)
        4. Randomize among top results
        5. Return top 'limit' professionals

        Args:
            zone: Filter by zone ('norte'/'sur')
            gender: Filter by gender ('m'/'f'/'otro')
            accept_prepaga: Filter by prepaga acceptance
            online_sessions: Filter by online sessions (True/False/None)
            date_str: Filter by availability on date (YYYY-MM-DD)
            time_str: Filter by availability at time (HH:MM)
            limit: Maximum number of results (default 10)

        Returns:
            List of professional dictionaries with availability info
        """
        try:
            print(f"[CLIENT] 🔍 Searching professionals with filters:")
            print(
                f"         Zone: {zone}, Gender: {gender}, Prepaga: {accept_prepaga}")
            print(
                f"         Online: {online_sessions}, Date: {date_str}, Time: {time_str}, Limit: {limit}")

            # Step 1: Get base filtered results
            professionals = self.db.search_professionals(
                zone=zone,
                gender=gender,
                accept_prepaga=accept_prepaga,
                online_sessions=online_sessions
            )

            print(
                f"[CLIENT] Found {len(professionals)} professionals after base filters")

            if not professionals:
                return []

            # Step 2: Calculate availability for each professional
            results = []

            for prof in professionals:
                phone = prof['phone']

                # If specific date/time requested, check availability
                if date_str and time_str:
                    if not self.is_professional_available(phone, date_str, time_str):
                        continue  # Skip if not available at requested time

                    # Count availability on that specific date
                    availability_score = self.count_available_hours_date(
                        phone, date_str)

                elif date_str:
                    # Date specified but no time - count hours available that day
                    availability_score = self.count_available_hours_date(
                        phone, date_str)
                    if availability_score == 0:
                        continue  # Skip if no availability that day

                else:
                    # No date specified - count availability in next week
                    availability_score = self.count_available_hours_week(phone)

                # Add availability score to professional data
                prof['availability_score'] = availability_score
                results.append(prof)

            print(
                f"[CLIENT] {len(results)} professionals available after availability check")

            if not results:
                return []

            # Step 3: Sort by availability (descending)
            results.sort(key=lambda x: x['availability_score'], reverse=True)

            # Step 4: Randomize among top results (add variety)
            # Take top candidates (more than limit to allow randomization)
            top_candidates = results[:min(len(results), limit * 2)]

            # Randomize
            random.shuffle(top_candidates)

            # Step 5: Return limited results
            final_results = top_candidates[:limit]

            print(f"[CLIENT] ✅ Returning {len(final_results)} professionals")

            return final_results

        except Exception as e:
            print(f"[CLIENT] ❌ Error searching professionals: {e}")
            import traceback
            traceback.print_exc()
            return []

    def search_available_today(self, zone: str = None, gender: str = None,
                               accept_prepaga: bool = None, limit: int = 10) -> List[Dict]:
        """
        Search professionals available TODAY.

        Business Logic:
        1. Filter professionals by base criteria
        2. Check who has availability remaining today
        3. If < limit results, add professionals with soonest future availability
        4. Randomize and return

        Args:
            zone: Filter by zone
            gender: Filter by gender
            accept_prepaga: Filter by prepaga
            limit: Maximum results (default 10)

        Returns:
            List of professionals available today
        """
        today = datetime.now().strftime("%Y-%m-%d")

        # Search with today's date
        results = self.search_professionals_by_filters(
            zone=zone,
            gender=gender,
            accept_prepaga=accept_prepaga,
            date_str=today,
            limit=limit
        )

        # If we have enough results, return them
        if len(results) >= limit:
            return results[:limit]

        # If < limit, try to fill with tomorrow's availability
        print(
            f"[CLIENT] Only {len(results)} available today, searching tomorrow...")

        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        tomorrow_results = self.search_professionals_by_filters(
            zone=zone,
            gender=gender,
            accept_prepaga=accept_prepaga,
            date_str=tomorrow,
            limit=limit * 2  # Get more to fill the gap
        )

        # Combine results (avoid duplicates)
        seen_phones = {prof['phone'] for prof in results}
        for prof in tomorrow_results:
            if prof['phone'] not in seen_phones and len(results) < limit:
                prof['available_from'] = 'tomorrow'  # Mark as tomorrow
                results.append(prof)
                seen_phones.add(prof['phone'])

        return results[:limit]

    def search_professionals_in_time_range(self, date_str: str, time_start: str,
                                           time_end: str, zone: str = None,
                                           gender: str = None, limit: int = 10) -> List[Dict]:
        """
        Search professionals available in a time range (e.g., morning or afternoon).

        Args:
            date_str: Date in YYYY-MM-DD format
            time_start: Start time in HH:MM format (e.g., "08:00")
            time_end: End time in HH:MM format (e.g., "13:00")
            zone: Optional zone filter
            gender: Optional gender filter
            limit: Maximum results

        Returns:
            List of available professionals with availability scores
        """
        try:
            print(
                f"[CLIENT] 🔍 Searching in time range: {time_start} - {time_end}")

            # Get all professionals matching base filters
            professionals = self.db.search_professionals(
                zone=zone,
                gender=gender
            )

            if not professionals:
                return []

            # Check availability for each hour in the range
            results = []

            for prof in professionals:
                phone = prof['phone']
                available_hours = 0

                # Parse time range
                start_hour = int(time_start.split(':')[0])
                end_hour = int(time_end.split(':')[0])

                # Check each hour in the range
                for hour in range(start_hour, end_hour):
                    time_str = f"{hour:02d}:00"
                    if self.is_professional_available(phone, date_str, time_str):
                        available_hours += 1

                # Only include if has at least 1 hour available
                if available_hours > 0:
                    prof['availability_score'] = available_hours
                    results.append(prof)

            print(
                f"[CLIENT] Found {len(results)} professionals with availability in range")

            if not results:
                return []

            # Sort by availability
            results.sort(key=lambda x: x['availability_score'], reverse=True)

            # Randomize top results
            top_candidates = results[:min(len(results), limit * 2)]
            random.shuffle(top_candidates)

            return top_candidates[:limit]

        except Exception as e:
            print(f"[CLIENT] ❌ Error searching time range: {e}")
            return []
    # ==========================================
    # CONTACT
    # ==========================================

    def log_search(self, client_phone: str, search_type: str, filters: Dict,
                   results: List[Dict], session_id: str = None) -> int:
        """
        Log a client search for analytics.

        Args:
            client_phone: Client's phone
            search_type: Type of search performed
            filters: Filters applied
            results: Search results
            session_id: Session identifier

        Returns:
            Search ID
        """
        try:
            # Increment view count for all professionals in results
            for prof in results:
                self.db.increment_professional_views(prof['phone'])

            # Log the search
            search_id = self.db.log_client_search(
                client_phone=client_phone,
                search_type=search_type,
                search_params=filters,
                result_count=len(results),
                session_id=session_id
            )

            print(f"[CLIENT] ✅ Search logged: ID {search_id}")
            return search_id

        except Exception as e:
            print(f"[CLIENT] ❌ Error logging search: {e}")
            return None

    def contact_professional(self, search_id: int, professional_phone: str,
                             result_position: int = None) -> bool:
        """
        Log when client contacts a professional.
        Updates analytics and professional metrics.

        Args:
            search_id: ID of search that led to contact
            professional_phone: Professional contacted
            result_position: Position in results (1-based)

        Returns:
            True if successful
        """
        try:
            # Increment profile views
            self.db.increment_profile_views(professional_phone)

            # Log the contact
            success = self.db.log_professional_contact(
                search_id=search_id,
                professional_phone=professional_phone,
                result_position=result_position
            )

            if success:
                print(f"[CLIENT] ✅ Contact logged: {professional_phone}")

            return success

        except Exception as e:
            print(f"[CLIENT] ❌ Error logging contact: {e}")
            return False

    def get_professional_detail(self, phone: str) -> Optional[Dict]:
        """
        Get complete professional information including availability.

        Args:
            phone: Professional's phone

        Returns:
            Professional details with schedule info
        """
        try:
            prof = self.db.get_professional(phone)
            if not prof:
                return None

            # Add schedule information
            prof['weekly_schedule'] = self.db.get_weekly_schedule(phone)
            prof['free_slots'] = self.db.get_free_slots(
                phone, from_date=datetime.now().strftime("%Y-%m-%d"))

            # Add availability metrics
            prof['hours_available_today'] = self.count_available_hours_today(
                phone)
            prof['hours_available_week'] = self.count_available_hours_week(
                phone)

            return prof

        except Exception as e:
            print(f"[CLIENT] ❌ Error getting professional detail: {e}")
            return None

    # ==========================================
    # FORMATTING HELPERS
    # ==========================================

    def format_professional_for_display(self, prof: Dict) -> str:
        """
        Format professional data for WhatsApp display.

        Args:
            prof: Professional dictionary

        Returns:
            Formatted string for display
        """
        from messages import Messages
        msg = Messages()

        # Basic info
        output = f"👤 {prof['name']}\n"
        output += f"📱 {prof['phone']}\n"

        if prof.get('email'):
            output += f"📧 {prof['email']}\n"

        output += f"📍 {msg.format_zona(prof.get('zone', ''))}\n"
        output += f"💳 Prepaga: {msg.format_prepaga(prof.get('accept_prepaga', False))}\n"
        output += f"👤 {msg.format_sexo(prof.get('gender', ''))}\n"

        # Availability info
        if 'availability_score' in prof:
            output += f"⏰ Disponibilidad: {prof['availability_score']} horas\n"

        return output

    def format_results_list(self, results: List[Dict]) -> str:
        """
        Format list of professionals for WhatsApp display.

        Args:
            results: List of professionals

        Returns:
            Formatted string with numbered list
        """
        if not results:
            # No results found - show options
            output = "❌ No se encontraron profesionales con estos criterios.\n\n"
            output += "¿Qué deseas hacer?\n"
            output += "1️⃣ Modificar búsqueda\n"
            output += "2️⃣ Ver todos los profesionales disponibles\n"
            output += "0️⃣ Volver al menú"
            return output

        output = f"✅ Encontrados {len(results)} profesional(es):\n\n"

        for idx, prof in enumerate(results, start=1):
            output += f"{idx}️⃣ {prof['name']}\n"
            output += f"   📍 {self._format_zone(prof.get('zone'))}\n"
            output += f"   💳 Prepaga: {self._format_prepaga(prof.get('accept_prepaga'))}\n"
            output += f"   🏥 {prof.get('especialidad', 'No especificada')}\n"

            # Show available days (brief)
            available_days = self._get_available_days_brief(prof['phone'])
            output += f"   📅 {available_days}\n"

            output += "\n"

        output += "Responde con el número para ver detalles.\nO escribe '0' para volver al menú."

        return output

    def _get_available_days_brief(self, phone: str) -> str:
        """
        Get brief summary of available days for search results.

        Args:
            phone: Professional's phone

        Returns:
            Brief availability string (e.g., "Disponible: Lun, Mar, Jue")
        """
        # Get weekly schedule (busy hours)
        weekly = self.db.get_weekly_schedule(phone)

        day_names = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']

        if not weekly:
            # No busy schedule = available all week
            return "Disponible toda la semana"

        # Get busy days
        busy_days = {schedule['day_of_week'] for schedule in weekly}

        # Get available days (inverse of busy)
        available_days = [day for day in range(7) if day not in busy_days]

        if len(available_days) == 7:
            return "Disponible toda la semana"
        elif len(available_days) >= 5:
            return "Disponible casi toda la semana"
        elif len(available_days) >= 1:
            available_names = [day_names[day] for day in available_days]
            return f"Disponible: {', '.join(available_names)}"
        else:
            # Check if has specific free slots
            from datetime import datetime, timedelta
            today = datetime.now().date()
            next_week = today + timedelta(days=7)
            free_slots = self.db.get_free_slots(
                phone, from_date=today.strftime("%Y-%m-%d"))

            upcoming = [
                slot for slot in free_slots
                if today <= datetime.strptime(slot['date'], "%Y-%m-%d").date() <= next_week
            ]

            if upcoming:
                return f"{len(upcoming)} horarios libres esta semana"
            else:
                return "Consultar disponibilidad"

    def format_professional_detail(self, prof: Dict) -> str:
        """
        Format complete professional details for display.
        Shows full contact info, schedule, and specific free slots.

        Args:
            prof: Professional dictionary with schedule info

        Returns:
            Formatted detailed view
        """
        output = f"👨‍⚕️ {prof['name']}\n"
        output += "=" * 40 + "\n\n"

        # Contact info with WhatsApp link
        output += "📞 CONTACTO:\n"

        # Generate WhatsApp link
        clean_phone = prof['phone'].replace(
            '+', '').replace('-', '').replace(' ', '').replace('(', '').replace(')', '')
        # whatsapp_link = f"https://wa.me/{clean_phone}"

        output += f"   📱 {prof['phone']}\n"
        # output += f"   💬 {whatsapp_link}\n"

        if prof.get('email'):
            output += f"   📧 {prof['email']}\n"
        output += "\n"

        # Professional info
        output += "ℹ️ INFORMACIÓN:\n"
        output += f"   📍 Zona: {self._format_zone(prof.get('zone'))}\n"
        output += f"   👤 Sexo: {self._format_gender(prof.get('gender'))}\n"
        output += f"   💳 Prepaga: {self._format_prepaga(prof.get('accept_prepaga'))}\n"
        output += f"   🏥 Especialidad: {prof.get('especialidad', 'No especificada')}\n"
        output += "\n"

        # Availability section
        output += "⏰ DISPONIBILIDAD:\n\n"

        # Available days this week (from weekly schedule)
        output += self._format_weekly_availability(prof['phone'])
        output += "\n"

        # Specific free slots (next 14 days)
        if prof.get('free_slots'):
            output += "🆓 HORARIOS LIBRES CONFIRMADOS:\n"
            from datetime import datetime, timedelta

            today = datetime.now().date()
            two_weeks = today + timedelta(days=14)

            count = 0
            for slot in prof['free_slots']:
                slot_date = datetime.strptime(slot['date'], "%Y-%m-%d").date()

                if today <= slot_date <= two_weeks:
                    day_name = ['Lun', 'Mar', 'Mié', 'Jue',
                                'Vie', 'Sáb', 'Dom'][slot_date.weekday()]
                    output += f"   ✅ {day_name} {slot_date.day:02d}/{slot_date.month:02d} {slot['start_time']}-{slot['end_time']}\n"
                    count += 1

                    if count >= 5:  # Show max 5 slots
                        remaining = len([s for s in prof['free_slots']
                                         if today <= datetime.strptime(s['date'], "%Y-%m-%d").date() <= two_weeks]) - 5
                        if remaining > 0:
                            output += f"   ... y {remaining} horarios más\n"
                        break

            if count == 0:
                output += "   No hay horarios libres confirmados en las próximas 2 semanas.\n"

            output += "\n"

        # Simplified call to action
        output += "💬 Click en el link de WhatsApp para contactar\n\n"
        output += "1️⃣ Nueva búsqueda\n"
        output += "0️⃣ Volver al menú"

        return output

    def _format_weekly_availability(self, phone: str) -> str:
        """
        Format weekly availability showing which days are generally available.

        Args:
            phone: Professional's phone

        Returns:
            Formatted weekly availability string
        """
        weekly = self.db.get_weekly_schedule(phone)
        day_names = ['Lunes', 'Martes', 'Miércoles',
                     'Jueves', 'Viernes', 'Sábado', 'Domingo']

        if not weekly:
            return "📅 Disponible todos los días (sin horarios ocupados configurados)\n"

        # Get busy days
        busy_days = {schedule['day_of_week'] for schedule in weekly}

        output = "📅 DÍAS DISPONIBLES (esta semana):\n"

        for day in range(7):
            if day not in busy_days:
                output += f"   ✅ {day_names[day]} - Disponible\n"
            else:
                # Show busy hours
                busy_hours = [s for s in weekly if s['day_of_week'] == day]
                hours = ', '.join(
                    [f"{s['start_time']}-{s['end_time']}" for s in busy_hours])
                output += f"   ❌ {day_names[day]} - Ocupado ({hours})\n"

        return output
    # ==========================================
    # PRIVATE HELPERS
    # ==========================================

    def _format_zone(self, zone: str) -> str:
        """Format zone for display."""
        zones = {
            'norte': 'Zona Norte',
            'sur': 'Zona Sur'
        }
        return zones.get(zone, 'No especificada')

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
        return genders.get(gender, 'No especificado')

    # ==========================================
    # CAMBIOS EN client_service.py PARA PSIVALE
    # ==========================================

    # Nuevo método principal de búsqueda Psivale:

    def search_professionals_psivale(
        self,
        enfoque: str = None,
        poblacion: str = None,
        modalidad: str = None,
        zone: str = None,
        horarios: str = None,
        fee_range: str = None,
        gender: str = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        Search professionals with Psivale-specific filters.

        Args:
            enfoque: Therapeutic approach (e.g., "tcc", "gestaltica")
            poblacion: Population served (e.g., "adultos", "ninos")
            modalidad: Modality ('online', 'presencial', 'ambas')
            zone: Zone ('norte', 'sur', 'nueva_cordoba')
            horarios: Schedule preference (e.g., "manana", "tarde")
            fee_range: Fee range (e.g., "0-15000", "25000-35000")
            gender: Gender preference ('m', 'f', 'otro')
            limit: Maximum number of results

        Returns:
            List of matching professionals with formatted data
        """
        try:
            print(f"[CLIENT_SERVICE] 🔍 Psivale search with filters:")
            print(f"         Enfoque: {enfoque}, Población: {poblacion}")
            print(f"         Modalidad: {modalidad}, Zone: {zone}")
            print(
                f"         Horarios: {horarios}, Fee: {fee_range}, Gender: {gender}")

            # Use database search method
            professionals = self.db.search_professionals_psivale(
                enfoque=enfoque,
                poblacion=poblacion,
                modalidad=modalidad,
                zone=zone,
                horarios=horarios,
                fee_range=fee_range,
                gender=gender
            )

            print(f"[CLIENT_SERVICE] Found {len(professionals)} professionals")

            if not professionals:
                return []

            # Limit results
            professionals = professionals[:limit]

            # Enrich with formatted data
            enriched_results = []
            for prof in professionals:
                enriched = self._enrich_professional_data_psivale(prof)
                enriched_results.append(enriched)

            return enriched_results

        except Exception as e:
            print(f"[CLIENT_SERVICE] ❌ Error in Psivale search: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _enrich_professional_data_psivale(self, prof: Dict) -> Dict:
        """
        Enrich professional data with formatted fields for display.

        Args:
            prof: Raw professional data from database

        Returns:
            Enriched professional data with display-friendly formats
        """
        enriched = prof.copy()

        # Format enfoque for display
        if prof.get('enfoque_terapeutico'):
            enriched['enfoque_display'] = self._format_enfoques_display(
                prof['enfoque_terapeutico']
            )
        else:
            enriched['enfoque_display'] = 'No especificado'

        # Format población for display
        if prof.get('poblacion'):
            enriched['poblacion_display'] = self._format_poblacion_display(
                prof['poblacion']
            )
        else:
            enriched['poblacion_display'] = 'No especificado'

        # Format modalidad for display
        if prof.get('modalidad'):
            modalidad_map = {
                'online': '💻 Online',
                'presencial': '🏢 Presencial',
                'ambas': '🔀 Online y Presencial'
            }
            enriched['modalidad_display'] = modalidad_map.get(
                prof['modalidad'],
                prof['modalidad'].capitalize()
            )
        else:
            enriched['modalidad_display'] = 'No especificado'

        # Format horarios for display
        if prof.get('horarios_disponibles'):
            enriched['horarios_display'] = self._format_horarios_display(
                prof['horarios_disponibles']
            )
        else:
            enriched['horarios_display'] = 'No especificado'

        # Format zone for display
        if prof.get('zone'):
            zone_map = {
                'norte': 'Zona Norte',
                'sur': 'Zona Sur',
                'nueva_cordoba': 'Nueva Córdoba'
            }
            enriched['zone_display'] = zone_map.get(
                prof['zone'], prof['zone'].capitalize())
        else:
            enriched['zone_display'] = 'No especificado'

        # Format fee_range for display
        if prof.get('fee_range'):
            enriched['fee_display'] = self._format_fee_display(
                prof['fee_range'])
        else:
            enriched['fee_display'] = 'A consultar'

        # Format gender for display
        if prof.get('gender'):
            gender_map = {'m': 'Masculino', 'f': 'Femenino', 'otro': 'Otro'}
            enriched['gender_display'] = gender_map.get(
                prof['gender'], 'No especificado')
        else:
            enriched['gender_display'] = 'No especificado'

        return enriched

    def _format_enfoques_display(self, enfoques: List[str]) -> str:
        """Format therapeutic approaches for display."""
        if not enfoques:
            return 'No especificado'

        enfoque_map = {
            'tcc': 'TCC',
            'contextual': 'Contextuales (ACT, DBT, FAP)',
            'sistemica': 'Sistémica',
            'gestaltica': 'Gestáltica',
            'psicoanalisis': 'Psicoanálisis',
            'neuropsicologia': 'Neuropsicología'
        }

        formatted = [enfoque_map.get(e, e.capitalize()) for e in enfoques]
        return ', '.join(formatted)

    def _format_poblacion_display(self, poblaciones: List[str]) -> str:
        """Format populations for display."""
        if not poblaciones:
            return 'No especificado'

        poblacion_map = {
            'ninos': 'Niños/as',
            'adolescentes': 'Adolescentes',
            'adultos': 'Adultos',
            'parejas': 'Parejas/Familias'
        }

        formatted = [poblacion_map.get(p, p.capitalize()) for p in poblaciones]
        return ', '.join(formatted)

    def _format_horarios_display(self, horarios: List[str]) -> str:
        """Format schedules for display."""
        if not horarios:
            return 'No especificado'

        horario_map = {
            'manana': 'Mañana',
            'tarde': 'Tarde',
            'noche': 'Noche',
            'sabado': 'Sábados'
        }

        formatted = [horario_map.get(h, h.capitalize()) for h in horarios]
        return ', '.join(formatted)

    def _format_fee_display(self, fee_range: str) -> str:
        """Format fee range for display."""
        if not fee_range:
            return 'A consultar'

        # If it's a range like "0-15000"
        if '-' in fee_range:
            try:
                parts = fee_range.split('-')
                min_val = int(parts[0])
                max_val = int(parts[1])

                if min_val == 0:
                    return f"Hasta ${max_val:,}"
                elif max_val > 90000000:  # Very high number = "Más de"
                    return f"Más de ${min_val:,}"
                else:
                    return f"${min_val:,} – ${max_val:,}"
            except:
                return fee_range

        return fee_range

    def format_results_list_psivale(self, professionals: List[Dict]) -> str:
        """
        Format list of professionals for display (Psivale version).

        Args:
            professionals: List of professional data

        Returns:
            Formatted string with numbered list
        """
        if not professionals:
            return """🌿 No encontré psicólogos con exactamente esos filtros.

    Pero no te preocupes, esto no significa que no haya profesionales para vos.

    ¿Qué querés hacer?
    1️⃣ Ampliar la búsqueda (menos filtros)
    2️⃣ Ver todos los profesionales disponibles
    3️⃣ Empezar de nuevo

    Responde con el número."""

        lines = []
        lines.append(
            f"💚 Encontré {len(professionals)} psicólogo(s) que se ajustan a tu búsqueda:\n")

        for i, prof in enumerate(professionals, 1):
            name = prof.get('name', 'Sin nombre')
            enfoque = prof.get('enfoque_display', 'No especificado')
            modalidad = prof.get('modalidad_display', 'No especificado')
            zone = prof.get('zone_display', 'No especificado')

            lines.append(f"{i}️⃣ {name}")
            lines.append(f"   🧠 {enfoque}")
            lines.append(f"   {modalidad} - {zone}")
            lines.append("")  # Blank line

        lines.append(
            "🌿 Cada uno de estos profesionales puede acompañarte en tu proceso.\n")
        lines.append("Responde con el número para ver más detalles.")
        lines.append("O escribí '0' para hacer una nueva búsqueda.")

        return "\n".join(lines)

    def format_professional_detail_psivale(self, prof: Dict) -> str:
        """
        Format professional detail view (Psivale version).

        Args:
            prof: Professional data

        Returns:
            Formatted detail string
        """
        lines = []

        # Header with name
        name = prof.get('name', 'Sin nombre')
        lines.append(f"🧠 {name}\n")

        # Main info
        enfoque = prof.get('enfoque_display', 'No especificado')
        lines.append(f"🎯 Enfoque: {enfoque}")

        poblacion = prof.get('poblacion_display', 'No especificado')
        lines.append(f"👥 Trabaja con: {poblacion}")

        modalidad = prof.get('modalidad_display', 'No especificado')
        lines.append(f"💻 Modalidad: {modalidad}")

        zone = prof.get('zone_display', 'No especificado')
        lines.append(f"📍 Zona: {zone}")

        horarios = prof.get('horarios_display', 'No especificado')
        lines.append(f"📅 Horarios: {horarios}")

        fee = prof.get('fee_display', 'A consultar')
        lines.append(f"💰 Honorarios: {fee}")

        # Bio if exists
        if prof.get('bio'):
            lines.append(f"\n📝 Sobre el profesional:")
            lines.append(prof['bio'])

        # Footer with options
        lines.append("\n━━━━━━━━━━━━━━━━━━━━\n")
        lines.append("¿Qué querés hacer?")
        lines.append("1️⃣ Ver contacto")
        lines.append("2️⃣ Volver a resultados")
        lines.append("3️⃣ Nueva búsqueda")
        lines.append("\nResponde con el número.")

        return "\n".join(lines)

    def format_contact_info_psivale(self, prof: Dict) -> str:
        """
        Format contact information (Psivale version).

        Args:
            prof: Professional data

        Returns:
            Formatted contact string
        """
        phone = prof.get('phone', 'No disponible')
        email = prof.get('email', 'No disponible')
        name = prof.get('name', 'el profesional')

        return f"""💚 Perfecto, acá está el contacto de {name}:

    📱 WhatsApp: {phone}
    📧 Email: {email}

    🌿 Recordá que dar el primer paso vale.
    Mucha suerte en tu proceso.

    ¿Qué querés hacer ahora?
    1️⃣ Ver otros profesionales
    2️⃣ Nueva búsqueda
    0️⃣ Volver al menú"""

    def build_search_summary_psivale(self, filters: Dict) -> str:
        """
        Build search summary text from filters (Psivale version).

        Args:
            filters: Dictionary of applied filters

        Returns:
            Formatted summary string
        """
        lines = []
        lines.append("🌿 Estás buscando:")
        lines.append("")

        if filters.get('enfoque'):
            enfoque_display = self._format_enfoques_display(
                [filters['enfoque']])
            lines.append(f"🧠 Enfoque: {enfoque_display}")

        if filters.get('poblacion'):
            poblacion_display = self._format_poblacion_display(
                [filters['poblacion']])
            lines.append(f"👥 Para: {poblacion_display}")

        if filters.get('modalidad'):
            modalidad_map = {
                'online': '💻 Sesiones online',
                'presencial': '🏢 Sesiones presenciales',
                'ambas': '🔀 Cualquier modalidad'
            }
            lines.append(modalidad_map.get(
                filters['modalidad'], filters['modalidad']))

        if filters.get('zone'):
            zone_map = {
                'norte': '📍 Zona Norte',
                'sur': '📍 Zona Sur',
                'nueva_cordoba': '📍 Nueva Córdoba'
            }
            lines.append(zone_map.get(filters['zone'], f"📍 {filters['zone']}"))

        if filters.get('horarios'):
            horarios_display = self._format_horarios_display(
                [filters['horarios']])
            lines.append(f"📅 Horarios: {horarios_display}")

        if filters.get('fee_range'):
            fee_display = self._format_fee_display(filters['fee_range'])
            lines.append(f"💰 Presupuesto: {fee_display}")

        lines.append("")
        lines.append("Buscando psicólogos que se ajusten a tu perfil...")
        lines.append("")
        lines.append("💚 Gracias por compartir. Este paso vale.")

        return "\n".join(lines)


# Global client service instance
client_service = ClientService()
