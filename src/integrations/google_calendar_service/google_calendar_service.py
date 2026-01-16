"""
GoogleCalendarService - Interfaz principal del servicio.

Esta clase actúa como fachada que simplifica el uso de todos
los componentes del servicio de Google Calendar.

Proporciona una API unificada para:
- Autenticación
- Gestión de calendarios
- Cálculo de disponibilidad
- Creación y gestión de citas
"""

import logging
from typing import Dict, List, Optional

from .auth import AuthManager
from .calendar import CalendarClient, AvailabilityChecker, EventManager

# Configurar logger
logger = logging.getLogger(__name__)


class GoogleCalendarService:
    """
    Servicio unificado de Google Calendar.
    
    Proporciona una interfaz simplificada para todas las operaciones
    de calendario, disponibilidad y gestión de citas.
    
    Uso básico:
        service = GoogleCalendarService()
        slots = service.get_available_slots(...)
        event = service.create_appointment(...)
    
    Attributes:
        auth_manager: Gestor de autenticación
        calendar_client: Cliente de Calendar API
        availability_checker: Calculador de disponibilidad
        event_manager: Gestor de eventos/citas
    """
    
    def __init__(self, credentials_path: Optional[str] = None):
        """
        Inicializa el servicio completo de Google Calendar.
        
        Args:
            credentials_path: Ruta al archivo de credenciales (opcional)
        """
        logger.info("Inicializando GoogleCalendarService...")
        
        # Inicializar autenticación
        self.auth_manager = AuthManager(credentials_path)
        credentials = self.auth_manager.get_credentials()
        
        # Inicializar cliente base
        self.calendar_client = CalendarClient(credentials)
        
        # Inicializar componentes especializados
        self.availability_checker = AvailabilityChecker(self.calendar_client)
        self.event_manager = EventManager(self.calendar_client)
        
        logger.info("GoogleCalendarService inicializado correctamente")
    
    # ========================================================================
    # MÉTODOS DE DISPONIBILIDAD
    # ========================================================================
    
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
            calendar_id: Email del profesional
            date: Fecha en formato 'YYYY-MM-DD'
            working_hours: {'start': 'HH:MM', 'end': 'HH:MM'}
            slot_duration_minutes: Duración de cada slot
            break_duration_minutes: Minutos de descanso entre slots
            timezone_str: Zona horaria (default: Argentina)
        
        Returns:
            List[Dict]: Lista de slots disponibles
        """
        return self.availability_checker.get_available_slots(
            calendar_id=calendar_id,
            date=date,
            working_hours=working_hours,
            slot_duration_minutes=slot_duration_minutes,
            break_duration_minutes=break_duration_minutes,
            timezone_str=timezone_str
        )
    
    def check_slot_available(
        self,
        calendar_id: str,
        start_datetime: str,
        end_datetime: str,
        timezone_str: Optional[str] = None
    ) -> bool:
        """
        Verifica si un slot específico está disponible.
        
        Args:
            calendar_id: Email del profesional
            start_datetime: Inicio del slot
            end_datetime: Fin del slot
            timezone_str: Zona horaria
        
        Returns:
            bool: True si está disponible
        """
        return self.availability_checker.check_slot_available(
            calendar_id=calendar_id,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            timezone_str=timezone_str
        )
    
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
        
        Args:
            calendar_id: Email del profesional
            start_date: Fecha desde donde buscar
            working_hours: Horario laboral
            slot_duration_minutes: Duración del slot
            days_to_search: Días a buscar (default: 7)
            timezone_str: Zona horaria
        
        Returns:
            Dict: Primer slot disponible, o None
        """
        return self.availability_checker.get_next_available_slot(
            calendar_id=calendar_id,
            start_date=start_date,
            working_hours=working_hours,
            slot_duration_minutes=slot_duration_minutes,
            days_to_search=days_to_search,
            timezone_str=timezone_str
        )
    
    def is_slot_available(
        self,
        calendar_id: str,
        date: str,
        time: str,
        duration_minutes: int = 50,
        timezone_str: Optional[str] = None
    ) -> bool:
        """
        Verifica si un slot específico está disponible.
        
        WRAPPER conveniente sobre check_slot_available() que acepta
        date + time separados en lugar de start_datetime + end_datetime.
        
        Args:
            calendar_id: Email del profesional (ej: 'professional@gmail.com')
            date: Fecha en formato 'YYYY-MM-DD' (ej: '2025-01-17')
            time: Hora en formato 'HH:MM' (ej: '14:00')
            duration_minutes: Duración del slot en minutos (default: 50)
            timezone_str: Zona horaria (default: 'America/Argentina/Buenos_Aires')
        
        Returns:
            bool: True si el slot está disponible (no hay eventos), False si está ocupado
        
        Examples:
            >>> service = GoogleCalendarService()
            >>> available = service.is_slot_available(
            ...     calendar_id='doctor@gmail.com',
            ...     date='2025-01-17',
            ...     time='14:00',
            ...     duration_minutes=50
            ... )
            >>> print(f"Disponible: {available}")
            Disponible: True
        """
        from datetime import datetime, timedelta
        
        # Default timezone
        if not timezone_str:
            timezone_str = 'America/Argentina/Buenos_Aires'
        
        try:
            # Construir datetime de inicio
            start_dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
            
            # Calcular datetime de fin
            end_dt = start_dt + timedelta(minutes=duration_minutes)
            
            # Formatear para Calendar API (ISO format con timezone)
            # Formato: 2025-01-17T14:00:00-03:00
            start_datetime = f"{start_dt.strftime('%Y-%m-%dT%H:%M:%S')}-03:00"
            end_datetime = f"{end_dt.strftime('%Y-%m-%dT%H:%M:%S')}-03:00"
            
            # Usar el método existente check_slot_available
            available = self.check_slot_available(
                calendar_id=calendar_id,
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                timezone_str=timezone_str
            )
            
            logger.debug(
                f"Slot check: {calendar_id} on {date} {time} "
                f"for {duration_minutes}min = {'Available' if available else 'Busy'}"
            )
            
            return available
            
        except Exception as e:
            logger.error(f"Error checking slot availability: {e}")
            import traceback
            traceback.print_exc()
            return False
        
    # ========================================================================
    # MÉTODOS DE GESTIÓN DE CITAS
    # ========================================================================
    
    def create_appointment(
        self,
        calendar_id: str,
        start_datetime: str,
        end_datetime: str,
        client_name: str,
        client_phone: str,
        appointment_type: str,
        notes: Optional[str] = None,
        reminders: Optional[List[Dict]] = None,
        timezone_str: Optional[str] = None
    ) -> Dict:
        """
        Crea una nueva cita en el calendario.
        
        Args:
            calendar_id: Email del profesional
            start_datetime: Inicio de la cita
            end_datetime: Fin de la cita
            client_name: Nombre del cliente
            client_phone: Teléfono del cliente
            appointment_type: Tipo de consulta
            notes: Notas adicionales (opcional)
            reminders: Recordatorios personalizados (opcional)
            timezone_str: Zona horaria
        
        Returns:
            Dict: Evento creado con 'id'
        """
        return self.event_manager.create_appointment(
            calendar_id=calendar_id,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            client_name=client_name,
            client_phone=client_phone,
            appointment_type=appointment_type,
            notes=notes,
            reminders=reminders,
            timezone_str=timezone_str
        )
    
    def cancel_appointment(
        self,
        calendar_id: str,
        event_id: str,
        cancellation_reason: Optional[str] = None
    ) -> bool:
        """
        Cancela una cita existente.
        
        Args:
            calendar_id: Email del profesional
            event_id: ID del evento a cancelar
            cancellation_reason: Motivo de cancelación (opcional)
        
        Returns:
            bool: True si se canceló exitosamente
        """
        return self.event_manager.cancel_appointment(
            calendar_id=calendar_id,
            event_id=event_id,
            cancellation_reason=cancellation_reason
        )
    
    def reschedule_appointment(
        self,
        calendar_id: str,
        event_id: str,
        new_start_datetime: str,
        new_end_datetime: str,
        timezone_str: Optional[str] = None
    ) -> Dict:
        """
        Reprograma una cita a un nuevo horario.
        
        Args:
            calendar_id: Email del profesional
            event_id: ID del evento
            new_start_datetime: Nueva hora de inicio
            new_end_datetime: Nueva hora de fin
            timezone_str: Zona horaria
        
        Returns:
            Dict: Evento actualizado
        """
        return self.event_manager.reschedule_appointment(
            calendar_id=calendar_id,
            event_id=event_id,
            new_start_datetime=new_start_datetime,
            new_end_datetime=new_end_datetime,
            timezone_str=timezone_str
        )
    
    def update_appointment_notes(
        self,
        calendar_id: str,
        event_id: str,
        additional_notes: str
    ) -> Dict:
        """
        Agrega notas adicionales a una cita.
        
        Args:
            calendar_id: Email del profesional
            event_id: ID del evento
            additional_notes: Notas a agregar
        
        Returns:
            Dict: Evento actualizado
        """
        return self.event_manager.update_appointment_notes(
            calendar_id=calendar_id,
            event_id=event_id,
            additional_notes=additional_notes
        )
    
    def get_appointment_details(
        self,
        calendar_id: str,
        event_id: str
    ) -> Optional[Dict]:
        """
        Obtiene los detalles completos de una cita.
        
        Args:
            calendar_id: Email del profesional
            event_id: ID del evento
        
        Returns:
            Dict: Datos del evento, o None si no existe
        """
        return self.event_manager.get_appointment_details(
            calendar_id=calendar_id,
            event_id=event_id
        )
    
    # ========================================================================
    # MÉTODOS DE CALENDARIOS
    # ========================================================================
    
    def list_calendars(self) -> List[Dict]:
        """
        Lista todos los calendarios accesibles.
        
        Returns:
            List[Dict]: Lista de calendarios
        """
        return self.calendar_client.list_calendars()
    
    def get_calendar(self, calendar_id: str) -> Optional[Dict]:
        """
        Obtiene información de un calendario específico.
        
        Args:
            calendar_id: ID del calendario (email)
        
        Returns:
            Dict: Información del calendario, o None
        """
        return self.calendar_client.get_calendar(calendar_id)
    
    def check_calendar_access(self, calendar_id: str) -> bool:
        """
        Verifica si se tiene acceso a un calendario.
        
        Args:
            calendar_id: ID del calendario
        
        Returns:
            bool: True si tiene acceso
        """
        return self.calendar_client.check_calendar_access(calendar_id)
    
    # ========================================================================
    # MÉTODOS DE INFORMACIÓN
    # ========================================================================
    
    def get_service_account_email(self) -> Optional[str]:
        """
        Obtiene el email de la Service Account.
        
        Returns:
            str: Email de la Service Account
        """
        return self.auth_manager.get_service_account_email()
    
    def get_project_id(self) -> Optional[str]:
        """
        Obtiene el ID del proyecto de Google Cloud.
        
        Returns:
            str: ID del proyecto
        """
        return self.auth_manager.get_project_id()
