"""
CalendarClient - Cliente base para interactuar con Google Calendar API.

Este módulo proporciona una interfaz simplificada para realizar operaciones
CRUD (Create, Read, Update, Delete) sobre calendarios y eventos.

Operaciones principales:
- Listar calendarios accesibles
- Obtener eventos de un calendario
- Crear nuevos eventos
- Actualizar eventos existentes
- Eliminar eventos
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..config import GOOGLE_CONFIG

# Configurar logger
logger = logging.getLogger(__name__)


class CalendarClient:
    """
    Cliente para operaciones con Google Calendar API.
    
    Proporciona métodos para interactuar con calendarios y eventos
    usando la API de Google Calendar v3.
    
    Attributes:
        credentials: Credenciales de autenticación de Google
        service: Objeto service de Google Calendar API
    """
    
    def __init__(self, credentials):
        """
        Inicializa el cliente de Google Calendar.
        
        Args:
            credentials: Credenciales autenticadas obtenidas de AuthManager
        
        Raises:
            Exception: Si no se puede construir el servicio de Google Calendar
        """
        self.credentials = credentials
        self.service = None
        
        try:
            # Construir el servicio de Google Calendar API
            logger.info("Construyendo servicio de Google Calendar API...")
            
            self.service = build(
                'calendar',
                GOOGLE_CONFIG['api_version'],
                credentials=credentials
            )
            
            logger.info("Servicio de Google Calendar API construido exitosamente")
            
        except Exception as e:
            error_msg = f"Error al construir servicio de Google Calendar: {e}"
            logger.error(error_msg)
            raise
    
    def list_calendars(self) -> List[Dict]:
        """
        Lista todos los calendarios accesibles por la Service Account.
        
        Retorna información de todos los calendarios a los que la Service Account
        tiene acceso (calendarios compartidos con ella).
        
        Returns:
            List[Dict]: Lista de calendarios con su información básica
                Cada dict contiene: id, summary, description, timeZone, accessRole
        
        Raises:
            HttpError: Si hay un error en la llamada a la API
        """
        try:
            logger.info("Obteniendo lista de calendarios...")
            
            # Llamar a la API para obtener lista de calendarios
            calendar_list = self.service.calendarList().list().execute()
            
            calendars = calendar_list.get('items', [])
            logger.info(f"Se encontraron {len(calendars)} calendarios accesibles")
            
            # Loggear información de cada calendario (útil para debugging)
            for cal in calendars:
                logger.debug(
                    f"Calendario: {cal.get('summary', 'Sin nombre')} "
                    f"(ID: {cal.get('id')}, Rol: {cal.get('accessRole')})"
                )
            
            return calendars
            
        except HttpError as e:
            logger.error(f"Error HTTP al listar calendarios: {e}")
            raise
        except Exception as e:
            logger.error(f"Error inesperado al listar calendarios: {e}")
            raise
    
    def get_calendar(self, calendar_id: str) -> Optional[Dict]:
        """
        Obtiene información de un calendario específico.
        
        Args:
            calendar_id: ID del calendario (normalmente el email del propietario)
        
        Returns:
            Dict: Información del calendario, o None si no se encuentra
                Contiene: id, summary, description, timeZone, etc.
        """
        try:
            logger.info(f"Obteniendo información del calendario: {calendar_id}")
            
            calendar = self.service.calendars().get(calendarId=calendar_id).execute()
            
            logger.debug(f"Calendario obtenido: {calendar.get('summary', 'Sin nombre')}")
            return calendar
            
        except HttpError as e:
            if e.resp.status == 404:
                logger.warning(f"Calendario no encontrado: {calendar_id}")
                return None
            logger.error(f"Error HTTP al obtener calendario: {e}")
            raise
        except Exception as e:
            logger.error(f"Error al obtener calendario: {e}")
            raise
    
    def get_events(
        self,
        calendar_id: str,
        time_min: str,
        time_max: str,
        max_results: int = 250
    ) -> List[Dict]:
        """
        Obtiene eventos de un calendario en un rango de tiempo.
        
        Args:
            calendar_id: ID del calendario
            time_min: Fecha/hora mínima en formato ISO 8601 (ej: '2024-12-15T00:00:00Z')
            time_max: Fecha/hora máxima en formato ISO 8601
            max_results: Número máximo de eventos a retornar (default: 250)
        
        Returns:
            List[Dict]: Lista de eventos en el rango especificado
                Cada evento contiene: id, summary, start, end, status, etc.
        
        Raises:
            HttpError: Si hay un error en la llamada a la API
        """
        try:
            logger.info(
                f"Obteniendo eventos del calendario {calendar_id} "
                f"entre {time_min} y {time_max}"
            )
            
            # Llamar a la API para obtener eventos
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,  # Expandir eventos recurrentes
                orderBy='startTime'  # Ordenar por hora de inicio
            ).execute()
            
            events = events_result.get('items', [])
            logger.info(f"Se encontraron {len(events)} eventos")
            
            return events
            
        except HttpError as e:
            if e.resp.status == 403:
                logger.error(
                    f"Sin permisos para acceder al calendario {calendar_id}. "
                    "Verificar que el calendario esté compartido con la Service Account."
                )
            logger.error(f"Error HTTP al obtener eventos: {e}")
            raise
        except Exception as e:
            logger.error(f"Error al obtener eventos: {e}")
            raise
    
    def create_event(self, calendar_id: str, event_data: Dict) -> Dict:
        """
        Crea un nuevo evento en un calendario.
        
        Args:
            calendar_id: ID del calendario donde crear el evento
            event_data: Datos del evento en formato de Google Calendar API
                Debe contener al menos: summary, start, end
                Ejemplo:
                {
                    'summary': 'Consulta - Juan Pérez',
                    'description': 'Consulta inicial',
                    'start': {'dateTime': '2024-12-15T14:00:00-03:00'},
                    'end': {'dateTime': '2024-12-15T15:00:00-03:00'}
                }
        
        Returns:
            Dict: Evento creado con todos sus datos (incluye 'id' generado)
        
        Raises:
            HttpError: Si hay un error en la llamada a la API
            ValueError: Si event_data no contiene los campos requeridos
        """
        # Validar que el evento tenga los campos mínimos requeridos
        required_fields = ['summary', 'start', 'end']
        missing_fields = [field for field in required_fields if field not in event_data]
        
        if missing_fields:
            error_msg = f"event_data falta campos requeridos: {missing_fields}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        try:
            logger.info(
                f"Creando evento '{event_data.get('summary')}' "
                f"en calendario {calendar_id}"
            )
            
            # Crear el evento
            event = self.service.events().insert(
                calendarId=calendar_id,
                body=event_data
            ).execute()
            
            logger.info(f"Evento creado exitosamente. ID: {event.get('id')}")
            logger.debug(f"Link del evento: {event.get('htmlLink')}")
            
            return event
            
        except HttpError as e:
            if e.resp.status == 403:
                logger.error(
                    f"Sin permisos para crear eventos en {calendar_id}. "
                    "Verificar permisos de la Service Account."
                )
            logger.error(f"Error HTTP al crear evento: {e}")
            raise
        except Exception as e:
            logger.error(f"Error al crear evento: {e}")
            raise
    
    def update_event(
        self,
        calendar_id: str,
        event_id: str,
        event_data: Dict
    ) -> Dict:
        """
        Actualiza un evento existente.
        
        Args:
            calendar_id: ID del calendario que contiene el evento
            event_id: ID del evento a actualizar
            event_data: Datos actualizados del evento (mismo formato que create_event)
        
        Returns:
            Dict: Evento actualizado con todos sus datos
        
        Raises:
            HttpError: Si hay un error en la llamada a la API
        """
        try:
            logger.info(f"Actualizando evento {event_id} en calendario {calendar_id}")
            
            # Actualizar el evento
            event = self.service.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=event_data
            ).execute()
            
            logger.info(f"Evento {event_id} actualizado exitosamente")
            return event
            
        except HttpError as e:
            if e.resp.status == 404:
                logger.error(f"Evento {event_id} no encontrado en calendario {calendar_id}")
            logger.error(f"Error HTTP al actualizar evento: {e}")
            raise
        except Exception as e:
            logger.error(f"Error al actualizar evento: {e}")
            raise
    
    def delete_event(self, calendar_id: str, event_id: str) -> bool:
        """
        Elimina un evento de un calendario.
        
        Args:
            calendar_id: ID del calendario que contiene el evento
            event_id: ID del evento a eliminar
        
        Returns:
            bool: True si se eliminó exitosamente
        
        Raises:
            HttpError: Si hay un error en la llamada a la API
        """
        try:
            logger.info(f"Eliminando evento {event_id} de calendario {calendar_id}")
            
            # Eliminar el evento
            self.service.events().delete(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            
            logger.info(f"Evento {event_id} eliminado exitosamente")
            return True
            
        except HttpError as e:
            if e.resp.status == 404:
                logger.warning(f"Evento {event_id} no encontrado (ya fue eliminado?)")
                return False
            if e.resp.status == 410:
                logger.warning(f"Evento {event_id} ya fue eliminado previamente")
                return False
            logger.error(f"Error HTTP al eliminar evento: {e}")
            raise
        except Exception as e:
            logger.error(f"Error al eliminar evento: {e}")
            raise
    
    def check_calendar_access(self, calendar_id: str) -> bool:
        """
        Verifica si la Service Account tiene acceso a un calendario.
        
        Útil para validar antes de intentar operaciones.
        
        Args:
            calendar_id: ID del calendario a verificar
        
        Returns:
            bool: True si tiene acceso, False en caso contrario
        """
        try:
            calendar = self.get_calendar(calendar_id)
            return calendar is not None
        except HttpError as e:
            if e.resp.status in [403, 404]:
                return False
            raise
        except Exception:
            return False

    def create_secondary_calendar(
            self,
            summary: str,
            timezone_str: str = 'America/Argentina/Buenos_Aires'
        ) -> str:
            """
            Crea un calendario secundario en la cuenta de la Service Account.

            El calendario se crea en la cuenta de la Service Account y luego
            se comparte con el profesional vía share_calendar_with_email().

            Args:
                summary: Nombre del calendario (ej: 'Turnos - Dr. Blanco')
                timezone_str: Zona horaria del calendario

            Returns:
                str: ID del calendario creado (ej: 'xyz123@group.calendar.google.com')

            Raises:
                HttpError: Si hay error en la API
            """
            try:
                logger.info(f"Creando calendario secundario: '{summary}'")

                calendar_body = {
                    'summary': summary,
                    'timeZone': timezone_str
                }

                # Crear el calendario en la cuenta de la Service Account
                created = self.service.calendars().insert(
                    body=calendar_body
                ).execute()

                calendar_id = created.get('id')
                logger.info(f"Calendario creado exitosamente. ID: {calendar_id}")

                return calendar_id

            except HttpError as e:
                logger.error(f"Error HTTP al crear calendario: {e}")
                raise
            except Exception as e:
                logger.error(f"Error al crear calendario: {e}")
                raise

    def share_calendar_with_email(
        self,
        calendar_id: str,
        email: str,
        role: str = 'writer'
    ) -> bool:
        """
        Comparte un calendario con un email usando la API de ACL.

        Roles disponibles:
          - 'reader'  → solo lectura
          - 'writer'  → puede crear y editar eventos (recomendado para profesionales)
          - 'owner'   → control total

        Args:
            calendar_id: ID del calendario a compartir
            email: Email con quien compartir (ej: 'profesional@gmail.com')
            role: Nivel de acceso ('writer' por defecto)

        Returns:
            bool: True si se compartió exitosamente

        Raises:
            HttpError: Si hay error en la API
        """
        try:
            logger.info(f"Compartiendo calendario {calendar_id} con {email} (rol: {role})")

            acl_rule = {
                'scope': {
                    'type': 'user',
                    'value': email
                },
                'role': role
            }

            self.service.acl().insert(
                calendarId=calendar_id,
                body=acl_rule
            ).execute()

            logger.info(f"Calendario compartido exitosamente con {email}")
            return True

        except HttpError as e:
            logger.error(f"Error HTTP al compartir calendario: {e}")
            raise
        except Exception as e:
            logger.error(f"Error al compartir calendario: {e}")
            raise