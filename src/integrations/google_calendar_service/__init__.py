"""
Google Calendar Service - Módulo de integración con Google Calendar.

Este módulo proporciona una interfaz simplificada para gestionar
calendarios, disponibilidad y citas usando Google Calendar API.

Uso básico:
    from google_calendar_service import GoogleCalendarService
    
    service = GoogleCalendarService()
    
    # Consultar disponibilidad
    slots = service.get_available_slots(...)
    
    # Crear cita
    event = service.create_appointment(...)
    
    # Cancelar cita
    service.cancel_appointment(...)
"""

from .google_calendar_service import GoogleCalendarService
from .auth import AuthManager
from .calendar import CalendarClient, AvailabilityChecker, EventManager

__version__ = '1.0.0'
__all__ = [
    'GoogleCalendarService',
    'AuthManager',
    'CalendarClient',
    'AvailabilityChecker',
    'EventManager'
]
