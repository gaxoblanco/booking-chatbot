"""
EventManager - Gestión de eventos de citas en Google Calendar.

Este módulo proporciona una interfaz de alto nivel para crear, modificar
y eliminar eventos de citas, con un formato estándar que incluye
información del cliente y configuración de recordatorios.

Funcionalidades principales:
- Crear citas con formato estándar
- Cancelar citas
- Reprogramar citas
- Actualizar información de citas
- Configurar recordatorios automáticos
"""

import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta

from ..utils.timezone_helper import (
    combine_date_time,
    to_iso_format,
    parse_google_datetime,
    DEFAULT_TIMEZONE
)

# Configurar logger
logger = logging.getLogger(__name__)


class EventManager:
    """
    Gestor de eventos de citas en Google Calendar.
    
    Proporciona métodos de alto nivel para crear y gestionar citas
    con un formato estándar que incluye datos del cliente.
    
    Attributes:
        calendar_client: Cliente de CalendarClient para acceder a la API
    """
    
    def __init__(self, calendar_client):
        """
        Inicializa el gestor de eventos.
        
        Args:
            calendar_client: Instancia de CalendarClient configurada
        """
        self.calendar_client = calendar_client
        logger.info("EventManager inicializado")
    
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
        
        Esta función crea un evento con formato estándar que incluye:
        - Título con nombre del cliente
        - Descripción con información de contacto
        - Tipo de consulta
        - Recordatorios automáticos
        
        Args:
            calendar_id: ID del calendario (email del profesional)
            start_datetime: Inicio de la cita (ISO format o 'YYYY-MM-DD HH:MM')
            end_datetime: Fin de la cita (ISO format o 'YYYY-MM-DD HH:MM')
            client_name: Nombre completo del cliente
            client_phone: Teléfono del cliente (con código país, ej: +5491112345678)
            appointment_type: Tipo de consulta (ej: 'Consulta inicial', 'Seguimiento')
            notes: Notas adicionales opcionales
            reminders: Lista de recordatorios personalizados (opcional)
            timezone_str: Zona horaria (default: Argentina)
        
        Returns:
            Dict: Evento creado con todos sus datos, incluye 'id' del evento
        
        Raises:
            ValueError: Si los datos son inválidos
            Exception: Si hay error al crear el evento
        
        Example:
            event = event_manager.create_appointment(
                calendar_id='profesional@gmail.com',
                start_datetime='2026-01-17T14:00:00',
                end_datetime='2026-01-17T15:00:00',
                client_name='Juan Pérez',
                client_phone='+5491112345678',
                appointment_type='Consulta inicial',
                notes='Primera consulta, derivado por Dr. García'
            )
            print(f"Cita creada con ID: {event['id']}")
        """
        tz = timezone_str or DEFAULT_TIMEZONE
        
        logger.info(
            f"Creando cita para {client_name} "
            f"en {calendar_id} desde {start_datetime}"
        )
        
        try:
            # Validar datos obligatorios
            self._validate_appointment_data(
                client_name, client_phone, appointment_type
            )
            
            # Parsear y formatear datetimes
            if 'T' not in start_datetime:
                # Formato simple 'YYYY-MM-DD HH:MM'
                date_str = start_datetime.split()[0]
                time_str = start_datetime.split()[1]
                start_dt = combine_date_time(date_str, time_str, tz)
                
                date_str = end_datetime.split()[0]
                time_str = end_datetime.split()[1]
                end_dt = combine_date_time(date_str, time_str, tz)
            else:
                # Formato ISO
                start_dt = parse_google_datetime(start_datetime, tz)
                end_dt = parse_google_datetime(end_datetime, tz)
            
            # Construir datos del evento con formato estándar
            event_data = self._build_event_data(
                start_dt=start_dt,
                end_dt=end_dt,
                client_name=client_name,
                client_phone=client_phone,
                appointment_type=appointment_type,
                notes=notes,
                reminders=reminders,
                timezone_str=tz
            )
            
            # Crear evento en Google Calendar
            event = self.calendar_client.create_event(
                calendar_id=calendar_id,
                event_data=event_data
            )
            
            logger.info(
                f"Cita creada exitosamente. "
                f"ID: {event['id']}, Link: {event.get('htmlLink')}"
            )
            
            return event
            
        except ValueError as e:
            logger.error(f"Datos de cita inválidos: {e}")
            raise
        except Exception as e:
            logger.error(f"Error al crear cita: {e}")
            raise
    
    def cancel_appointment(
        self,
        calendar_id: str,
        event_id: str,
        cancellation_reason: Optional[str] = None
    ) -> bool:
        """
        Cancela una cita existente.
        
        Elimina el evento del calendario. Opcionalmente puede registrar
        el motivo de cancelación en los logs.
        
        Args:
            calendar_id: ID del calendario
            event_id: ID del evento a cancelar
            cancellation_reason: Motivo de la cancelación (opcional, para logs)
        
        Returns:
            bool: True si se canceló exitosamente
        
        Example:
            success = event_manager.cancel_appointment(
                calendar_id='profesional@gmail.com',
                event_id='abc123xyz',
                cancellation_reason='Cliente solicitó cancelación'
            )
        """
        logger.info(
            f"Cancelando cita {event_id} en calendario {calendar_id}"
        )
        
        if cancellation_reason:
            logger.info(f"Motivo de cancelación: {cancellation_reason}")
        
        try:
            success = self.calendar_client.delete_event(
                calendar_id=calendar_id,
                event_id=event_id
            )
            
            if success:
                logger.info(f"Cita {event_id} cancelada exitosamente")
            else:
                logger.warning(f"No se pudo cancelar la cita {event_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error al cancelar cita: {e}")
            raise
    
    def reschedule_appointment(
        self,
        calendar_id: str,
        event_id: str,
        new_start_datetime: str,
        new_end_datetime: str,
        timezone_str: Optional[str] = None
    ) -> Dict:
        """
        Reprograma una cita existente a un nuevo horario.
        
        Mantiene toda la información de la cita original (cliente, tipo, etc.)
        pero cambia el horario.
        
        Args:
            calendar_id: ID del calendario
            event_id: ID del evento a reprogramar
            new_start_datetime: Nueva hora de inicio (ISO format o 'YYYY-MM-DD HH:MM')
            new_end_datetime: Nueva hora de fin
            timezone_str: Zona horaria
        
        Returns:
            Dict: Evento actualizado
        
        Example:
            updated_event = event_manager.reschedule_appointment(
                calendar_id='profesional@gmail.com',
                event_id='abc123xyz',
                new_start_datetime='2026-01-18T10:00:00',
                new_end_datetime='2026-01-18T11:00:00'
            )
        """
        tz = timezone_str or DEFAULT_TIMEZONE
        
        logger.info(
            f"Reprogramando cita {event_id} a nuevo horario: {new_start_datetime}"
        )
        
        try:
            # Obtener evento actual para preservar información
            events = self.calendar_client.get_events(
                calendar_id=calendar_id,
                time_min=datetime.now().isoformat() + 'Z',
                time_max=(datetime.now() + timedelta(days=365)).isoformat() + 'Z'
            )
            
            current_event = None
            for event in events:
                if event['id'] == event_id:
                    current_event = event
                    break
            
            if not current_event:
                raise ValueError(f"Evento {event_id} no encontrado")
            
            # Parsear nuevos datetimes
            if 'T' not in new_start_datetime:
                date_str = new_start_datetime.split()[0]
                time_str = new_start_datetime.split()[1]
                new_start_dt = combine_date_time(date_str, time_str, tz)
                
                date_str = new_end_datetime.split()[0]
                time_str = new_end_datetime.split()[1]
                new_end_dt = combine_date_time(date_str, time_str, tz)
            else:
                new_start_dt = parse_google_datetime(new_start_datetime, tz)
                new_end_dt = parse_google_datetime(new_end_datetime, tz)
            
            # Actualizar solo las fechas, mantener todo lo demás
            updated_event_data = current_event.copy()
            updated_event_data['start'] = {
                'dateTime': to_iso_format(new_start_dt),
                'timeZone': tz
            }
            updated_event_data['end'] = {
                'dateTime': to_iso_format(new_end_dt),
                'timeZone': tz
            }
            
            # Actualizar evento
            updated_event = self.calendar_client.update_event(
                calendar_id=calendar_id,
                event_id=event_id,
                event_data=updated_event_data
            )
            
            logger.info(f"Cita {event_id} reprogramada exitosamente")
            return updated_event
            
        except Exception as e:
            logger.error(f"Error al reprogramar cita: {e}")
            raise
    
    def update_appointment_notes(
        self,
        calendar_id: str,
        event_id: str,
        additional_notes: str
    ) -> Dict:
        """
        Agrega notas adicionales a una cita existente.
        
        Útil para agregar información posterior a la creación de la cita,
        como recordatorios del profesional o cambios en el motivo de consulta.
        
        Args:
            calendar_id: ID del calendario
            event_id: ID del evento
            additional_notes: Notas a agregar
        
        Returns:
            Dict: Evento actualizado
        """
        logger.info(f"Actualizando notas de cita {event_id}")
        
        try:
            # Obtener evento actual
            events = self.calendar_client.get_events(
                calendar_id=calendar_id,
                time_min=datetime.now().isoformat() + 'Z',
                time_max=(datetime.now() + timedelta(days=365)).isoformat() + 'Z'
            )
            
            current_event = None
            for event in events:
                if event['id'] == event_id:
                    current_event = event
                    break
            
            if not current_event:
                raise ValueError(f"Evento {event_id} no encontrado")
            
            # Agregar notas a la descripción existente
            current_description = current_event.get('description', '')
            updated_description = (
                f"{current_description}\n\n"
                f"--- Notas adicionales ---\n"
                f"{additional_notes}"
            )
            
            # Actualizar evento
            updated_event_data = current_event.copy()
            updated_event_data['description'] = updated_description
            
            updated_event = self.calendar_client.update_event(
                calendar_id=calendar_id,
                event_id=event_id,
                event_data=updated_event_data
            )
            
            logger.info(f"Notas actualizadas en cita {event_id}")
            return updated_event
            
        except Exception as e:
            logger.error(f"Error al actualizar notas: {e}")
            raise
    
    def get_appointment_details(
        self,
        calendar_id: str,
        event_id: str
    ) -> Optional[Dict]:
        """
        Obtiene los detalles completos de una cita.
        
        Args:
            calendar_id: ID del calendario
            event_id: ID del evento
        
        Returns:
            Dict: Datos del evento, o None si no se encuentra
        """
        logger.info(f"Obteniendo detalles de cita {event_id}")
        
        try:
            events = self.calendar_client.get_events(
                calendar_id=calendar_id,
                time_min=datetime.now().isoformat() + 'Z',
                time_max=(datetime.now() + timedelta(days=365)).isoformat() + 'Z'
            )
            
            for event in events:
                if event['id'] == event_id:
                    logger.info(f"Cita {event_id} encontrada")
                    return event
            
            logger.warning(f"Cita {event_id} no encontrada")
            return None
            
        except Exception as e:
            logger.error(f"Error al obtener detalles de cita: {e}")
            raise
    
    def _validate_appointment_data(
        self,
        client_name: str,
        client_phone: str,
        appointment_type: str
    ):
        """
        Valida que los datos de la cita sean correctos.
        
        Args:
            client_name: Nombre del cliente
            client_phone: Teléfono del cliente
            appointment_type: Tipo de consulta
        
        Raises:
            ValueError: Si algún dato es inválido
        """
        if not client_name or len(client_name.strip()) < 2:
            raise ValueError("El nombre del cliente debe tener al menos 2 caracteres")
        
        if not client_phone or len(client_phone) < 10:
            raise ValueError("El teléfono debe tener al menos 10 dígitos")
        
        if not appointment_type or len(appointment_type.strip()) < 3:
            raise ValueError("El tipo de consulta es requerido")
    
    def _build_event_data(
        self,
        start_dt: datetime,
        end_dt: datetime,
        client_name: str,
        client_phone: str,
        appointment_type: str,
        notes: Optional[str],
        reminders: Optional[List[Dict]],
        timezone_str: str
    ) -> Dict:
        """
        Construye el objeto de datos del evento con formato estándar.
        
        Formato estándar:
        - Título: "Consulta - [Nombre Cliente]"
        - Descripción: Info de contacto + tipo + notas
        - Recordatorios: Email 24h antes, Popup 1h antes
        
        Args:
            start_dt: Datetime de inicio
            end_dt: Datetime de fin
            client_name: Nombre del cliente
            client_phone: Teléfono del cliente
            appointment_type: Tipo de consulta
            notes: Notas adicionales
            reminders: Recordatorios personalizados
            timezone_str: Zona horaria
        
        Returns:
            Dict: Datos del evento en formato Google Calendar API
        """
        # Construir título
        summary = f"Consulta - {client_name}"
        
        # Construir descripción con formato estándar
        description_lines = [
            f"👤 Cliente: {client_name}",
            f"📞 Teléfono: {client_phone}",
            f"📋 Tipo: {appointment_type}",
        ]
        
        if notes:
            description_lines.append(f"\n📝 Notas:\n{notes}")
        
        description = "\n".join(description_lines)
        
        # Configurar recordatorios
        if reminders is None:
            # Recordatorios por defecto
            reminders_config = {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},  # 1 día antes
                    {'method': 'popup', 'minutes': 60}         # 1 hora antes
                ]
            }
        else:
            reminders_config = {
                'useDefault': False,
                'overrides': reminders
            }
        
        # Construir objeto de evento
        event_data = {
            'summary': summary,
            'description': description,
            'start': {
                'dateTime': to_iso_format(start_dt),
                'timeZone': timezone_str
            },
            'end': {
                'dateTime': to_iso_format(end_dt),
                'timeZone': timezone_str
            },
            'reminders': reminders_config,
            # Color del evento (opcional, celeste para citas)
            'colorId': '7'  # Celeste/Turquesa
        }
        
        return event_data
