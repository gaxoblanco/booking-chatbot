"""
AvailabilityChecker - Calculador de disponibilidad de horarios.

Este módulo analiza el calendario de un profesional y determina qué
slots de tiempo están disponibles para nuevas reservas.

Lógica principal:
1. Obtener todos los eventos del día desde Google Calendar
2. Generar todos los slots posibles según horario laboral
3. Filtrar slots que se superponen con eventos existentes
4. Retornar lista de slots disponibles
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from ..models.time_slot import TimeSlot
from ..utils.timezone_helper import (
    combine_date_time,
    get_day_start_end,
    generate_time_slots,
    parse_google_datetime,
    to_iso_format,
    DEFAULT_TIMEZONE
)

# Configurar logger
logger = logging.getLogger(__name__)


class AvailabilityChecker:
    """
    Calculador de disponibilidad de horarios en calendarios.
    
    Analiza los eventos existentes en un calendario y determina
    qué bloques de tiempo están disponibles para reservar.
    
    Attributes:
        calendar_client: Cliente de CalendarClient para acceder a la API
    """
    
    def __init__(self, calendar_client):
        """
        Inicializa el checker de disponibilidad.
        
        Args:
            calendar_client: Instancia de CalendarClient configurada
        """
        self.calendar_client = calendar_client
        logger.info("AvailabilityChecker inicializado")
    
    def get_available_slots(
        self,
        calendar_id: str,
        date: str,
        working_hours: Dict[str, str],
        slot_duration_minutes: int,
        break_duration_minutes: int = 0,
        timezone_str: Optional[str] = None
    ) -> List[Dict]:
        """
        Obtiene todos los slots disponibles para un día específico.
        
        Args:
            calendar_id: ID del calendario a consultar (email del profesional)
            date: Fecha en formato 'YYYY-MM-DD'
            working_hours: Horario laboral, ej: {'start': '09:00', 'end': '18:00'}
            slot_duration_minutes: Duración de cada slot en minutos (ej: 60)
            break_duration_minutes: Minutos de descanso entre slots (default: 0)
            timezone_str: Zona horaria (default: Argentina)
        
        Returns:
            List[Dict]: Lista de slots disponibles con formato:
                [
                    {
                        'date': '2026-01-16',
                        'start': '09:00',
                        'end': '10:00',
                        'start_datetime': '2026-01-16T09:00:00-03:00',
                        'end_datetime': '2026-01-16T10:00:00-03:00',
                        'duration_minutes': 60
                    },
                    ...
                ]
        
        Example:
            slots = checker.get_available_slots(
                calendar_id='profesional@gmail.com',
                date='2026-01-16',
                working_hours={'start': '09:00', 'end': '18:00'},
                slot_duration_minutes=60
            )
        """
        tz = timezone_str or DEFAULT_TIMEZONE
        
        logger.info(
            f"Calculando disponibilidad para {calendar_id} "
            f"en fecha {date} con slots de {slot_duration_minutes}min"
        )
        
        try:
            # 1. Obtener eventos existentes del día
            busy_slots = self._get_busy_slots(calendar_id, date, tz)
            logger.info(f"Encontrados {len(busy_slots)} slots ocupados")
            
            # 2. Generar todos los slots posibles según horario laboral
            all_possible_slots = self._generate_all_slots(
                date,
                working_hours,
                slot_duration_minutes,
                break_duration_minutes,
                tz
            )
            logger.info(f"Generados {len(all_possible_slots)} slots posibles")
            
            # 3. Filtrar slots disponibles (los que no se superponen con eventos)
            available_slots = self._filter_available_slots(all_possible_slots, busy_slots)
            logger.info(f"Disponibles {len(available_slots)} slots libres")
            
            # 4. Convertir a formato de salida
            result = [slot.to_dict() for slot in available_slots]
            
            return result
            
        except Exception as e:
            logger.error(f"Error al calcular disponibilidad: {e}")
            raise
    
    def check_slot_available(
        self,
        calendar_id: str,
        start_datetime: str,
        end_datetime: str,
        timezone_str: Optional[str] = None
    ) -> bool:
        """
        Verifica si un slot específico está disponible.
        
        Útil para validar una reserva específica antes de crearla.
        
        Args:
            calendar_id: ID del calendario
            start_datetime: Inicio del slot en formato ISO o 'YYYY-MM-DD HH:MM'
            end_datetime: Fin del slot en formato ISO o 'YYYY-MM-DD HH:MM'
            timezone_str: Zona horaria
        
        Returns:
            bool: True si el slot está disponible, False si está ocupado
        
        Example:
            available = checker.check_slot_available(
                calendar_id='profesional@gmail.com',
                start_datetime='2026-01-16T14:00:00',
                end_datetime='2026-01-16T15:00:00'
            )
        """
        tz = timezone_str or DEFAULT_TIMEZONE
        
        try:
            # Parsear datetimes
            if 'T' not in start_datetime:
                # Formato simple 'YYYY-MM-DD HH:MM'
                start_dt = datetime.strptime(start_datetime, '%Y-%m-%d %H:%M')
                end_dt = datetime.strptime(end_datetime, '%Y-%m-%d %H:%M')
            else:
                # Formato ISO
                start_dt = parse_google_datetime(start_datetime, tz)
                end_dt = parse_google_datetime(end_datetime, tz)
            
            # Crear TimeSlot a verificar
            slot_to_check = TimeSlot(
                start=start_dt,
                end=end_dt,
                duration_minutes=int((end_dt - start_dt).total_seconds() / 60)
            )
            
            # Obtener eventos existentes en ese rango
            date_str = start_dt.strftime('%Y-%m-%d')
            busy_slots = self._get_busy_slots(calendar_id, date_str, tz)
            
            # Verificar si se superpone con algún evento existente
            for busy_slot in busy_slots:
                if slot_to_check.overlaps_with(busy_slot):
                    logger.info(
                        f"Slot {start_datetime} - {end_datetime} NO disponible "
                        f"(se superpone con evento existente)"
                    )
                    return False
            
            logger.info(f"Slot {start_datetime} - {end_datetime} está disponible")
            return True
            
        except Exception as e:
            logger.error(f"Error al verificar disponibilidad de slot: {e}")
            return False
    
    def _get_busy_slots(
        self,
        calendar_id: str,
        date: str,
        timezone_str: str
    ) -> List[TimeSlot]:
        """
        Obtiene todos los slots ocupados (eventos existentes) para un día.
        
        Args:
            calendar_id: ID del calendario
            date: Fecha en formato 'YYYY-MM-DD'
            timezone_str: Zona horaria
        
        Returns:
            List[TimeSlot]: Lista de slots ocupados
        """
        # Obtener inicio y fin del día
        day_start, day_end = get_day_start_end(date, timezone_str)
        
        # Consultar eventos del día en Google Calendar
        events = self.calendar_client.get_events(
            calendar_id=calendar_id,
            time_min=to_iso_format(day_start),
            time_max=to_iso_format(day_end)
        )
        
        # Convertir eventos a TimeSlots
        busy_slots = []
        for event in events:
            # Ignorar eventos cancelados
            if event.get('status') == 'cancelled':
                continue
            
            # Extraer inicio y fin del evento
            start_data = event.get('start', {})
            end_data = event.get('end', {})
            
            # Parsear datetime (puede ser dateTime o date)
            if 'dateTime' in start_data:
                start_dt = parse_google_datetime(start_data['dateTime'], timezone_str)
                end_dt = parse_google_datetime(end_data['dateTime'], timezone_str)
            elif 'date' in start_data:
                # Evento de día completo, ocupar todo el día
                start_dt = combine_date_time(start_data['date'], '00:00', timezone_str)
                end_dt = combine_date_time(end_data['date'], '23:59', timezone_str)
            else:
                logger.warning(f"Evento sin fecha válida: {event.get('id')}")
                continue
            
            # Crear TimeSlot
            duration = int((end_dt - start_dt).total_seconds() / 60)
            busy_slot = TimeSlot(
                start=start_dt,
                end=end_dt,
                duration_minutes=duration,
                date=date
            )
            busy_slots.append(busy_slot)
            
            logger.debug(
                f"Evento ocupado: {event.get('summary', 'Sin título')} "
                f"({busy_slot.start.strftime('%H:%M')}-{busy_slot.end.strftime('%H:%M')})"
            )
        
        return busy_slots
    
    def _generate_all_slots(
        self,
        date: str,
        working_hours: Dict[str, str],
        slot_duration_minutes: int,
        break_duration_minutes: int,
        timezone_str: str
    ) -> List[TimeSlot]:
        """
        Genera todos los slots posibles según el horario laboral.
        
        Args:
            date: Fecha en formato 'YYYY-MM-DD'
            working_hours: Horario laboral {'start': 'HH:MM', 'end': 'HH:MM'}
            slot_duration_minutes: Duración de cada slot
            break_duration_minutes: Minutos de descanso entre slots
            timezone_str: Zona horaria
        
        Returns:
            List[TimeSlot]: Lista de todos los slots posibles
        """
        # Generar lista de horarios
        time_slots = generate_time_slots(
            start_time=working_hours['start'],
            end_time=working_hours['end'],
            slot_duration_minutes=slot_duration_minutes,
            break_duration_minutes=break_duration_minutes
        )
        
        # Convertir a objetos TimeSlot
        slots = []
        for start_time, end_time in time_slots:
            start_dt = combine_date_time(date, start_time, timezone_str)
            end_dt = combine_date_time(date, end_time, timezone_str)
            
            slot = TimeSlot(
                start=start_dt,
                end=end_dt,
                duration_minutes=slot_duration_minutes,
                date=date
            )
            slots.append(slot)
        
        return slots
    
    def _filter_available_slots(
        self,
        all_slots: List[TimeSlot],
        busy_slots: List[TimeSlot]
    ) -> List[TimeSlot]:
        """
        Filtra los slots disponibles eliminando los que se superponen con eventos.
        
        Args:
            all_slots: Todos los slots posibles
            busy_slots: Slots ocupados por eventos existentes
        
        Returns:
            List[TimeSlot]: Slots que están disponibles
        """
        available = []
        
        for slot in all_slots:
            # Verificar si se superpone con algún evento ocupado
            is_available = True
            
            for busy_slot in busy_slots:
                if slot.overlaps_with(busy_slot):
                    is_available = False
                    logger.debug(
                        f"Slot {slot.start.strftime('%H:%M')}-{slot.end.strftime('%H:%M')} "
                        f"ocupado (se superpone con evento existente)"
                    )
                    break
            
            if is_available:
                available.append(slot)
        
        return available
    
    def get_next_available_slot(
        self,
        calendar_id: str,
        start_date: str,
        working_hours: Dict[str, str],
        slot_duration_minutes: int,
        days_to_search: int = 7,
        timezone_str: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Encuentra el próximo slot disponible a partir de una fecha.
        
        Útil para sugerir al usuario el siguiente horario disponible.
        
        Args:
            calendar_id: ID del calendario
            start_date: Fecha desde donde buscar en formato 'YYYY-MM-DD'
            working_hours: Horario laboral
            slot_duration_minutes: Duración del slot buscado
            days_to_search: Cuántos días buscar hacia adelante (default: 7)
            timezone_str: Zona horaria
        
        Returns:
            Dict: Primer slot disponible encontrado, o None si no hay ninguno
        
        Example:
            next_slot = checker.get_next_available_slot(
                calendar_id='profesional@gmail.com',
                start_date='2026-01-16',
                working_hours={'start': '09:00', 'end': '18:00'},
                slot_duration_minutes=60
            )
            # {'date': '2026-01-17', 'start': '10:00', 'end': '11:00', ...}
        """
        tz = timezone_str or DEFAULT_TIMEZONE
        
        # Buscar día por día
        current_date = datetime.strptime(start_date, '%Y-%m-%d')
        
        for day_offset in range(days_to_search):
            search_date = (current_date + timedelta(days=day_offset)).strftime('%Y-%m-%d')
            
            logger.info(f"Buscando slots disponibles en: {search_date}")
            
            # Obtener slots del día
            slots = self.get_available_slots(
                calendar_id=calendar_id,
                date=search_date,
                working_hours=working_hours,
                slot_duration_minutes=slot_duration_minutes,
                timezone_str=tz
            )
            
            # Si hay algún slot disponible, retornar el primero
            if slots:
                logger.info(f"Encontrado slot disponible: {slots[0]}")
                return slots[0]
        
        logger.warning(
            f"No se encontraron slots disponibles en los próximos {days_to_search} días"
        )
        return None
