"""
AppointmentCalendarService - Integración entre chatbot y Google Calendar.

Este servicio actúa como puente entre el sistema de citas del chatbot
y Google Calendar, sincronizando las reservas en ambos sistemas.

Uso:
    from src.integrations.appointment_calendar_service import AppointmentCalendarService
    
    calendar_service = AppointmentCalendarService(database)
    
    # Consultar disponibilidad
    slots = calendar_service.get_available_slots(professional_phone, date)
    
    # Crear cita
    appointment_id = calendar_service.create_appointment(...)
    
    # Cancelar cita
    calendar_service.cancel_appointment(appointment_id)
"""

import logging
import json
from datetime import datetime
from typing import List, Dict, Optional

from .google_calendar_service import GoogleCalendarService

# Configurar logger
logger = logging.getLogger(__name__)


class AppointmentCalendarService:
    """
    Servicio de integración entre sistema de citas y Google Calendar.
    
    Sincroniza las operaciones de citas entre la base de datos local
    del chatbot y Google Calendar de los profesionales.
    """
    
    def __init__(self, database):
        """
        Inicializa el servicio de integración.
        
        Args:
            database: Instancia de la base de datos del chatbot
        """
        self.db = database
        self.calendar_service = GoogleCalendarService()
        logger.info("AppointmentCalendarService inicializado")
    
    # ========================================================================
    # DISPONIBILIDAD
    # ========================================================================
    
    def get_available_slots(
        self,
        professional_phone: str,
        date: str
    ) -> List[Dict]:
        """
        Obtiene slots disponibles de un profesional para una fecha.
        
        Args:
            professional_phone: Teléfono del profesional
            date: Fecha en formato 'YYYY-MM-DD'
        
        Returns:
            List[Dict]: Lista de slots disponibles
                [
                    {
                        'date': '2026-01-17',
                        'start': '09:00',
                        'end': '10:00',
                        'start_datetime': '2026-01-17T09:00:00-03:00',
                        'end_datetime': '2026-01-17T10:00:00-03:00',
                        'duration_minutes': 60
                    },
                    ...
                ]
        
        Raises:
            ValueError: Si el profesional no existe o no está configurado
        """
        logger.info(
            f"Consultando disponibilidad de {professional_phone} para {date}"
        )
        
        try:
            # 1. Obtener configuración del profesional desde BD
            professional = self.db.get_professional(professional_phone)
            
            if not professional:
                raise ValueError(f"Profesional {professional_phone} no encontrado")
            
            # 2. Verificar que tenga calendar_id configurado
            calendar_id = professional.get('calendar_id')
            if not calendar_id:
                raise ValueError(
                    f"Profesional {professional_phone} no tiene calendar_id configurado. "
                    "Configure primero el email de su calendario de Google."
                )
            
            # 3. Obtener horario laboral (parsear JSON)
            working_hours_json = professional.get('working_hours')
            if working_hours_json:
                working_hours = json.loads(working_hours_json)
            else:
                # Default: 9 AM a 6 PM
                working_hours = {'start': '09:00', 'end': '18:00'}
                logger.warning(
                    f"Profesional {professional_phone} sin working_hours, usando default"
                )
            
            # 4. Obtener duración de consulta
            slot_duration = professional.get('slot_duration', 60)
            
            # 5. Consultar disponibilidad en Google Calendar
            slots = self.calendar_service.get_available_slots(
                calendar_id=calendar_id,
                date=date,
                working_hours=working_hours,
                slot_duration_minutes=slot_duration
            )
            
            logger.info(
                f"Encontrados {len(slots)} slots disponibles para {professional_phone}"
            )
            
            return slots
            
        except Exception as e:
            logger.error(f"Error al obtener disponibilidad: {e}")
            raise
    
    def check_slot_available(
        self,
        professional_phone: str,
        date: str,
        start_time: str,
        end_time: str
    ) -> bool:
        """
        Verifica si un slot específico está disponible.
        
        Args:
            professional_phone: Teléfono del profesional
            date: Fecha en 'YYYY-MM-DD'
            start_time: Hora inicio en 'HH:MM'
            end_time: Hora fin en 'HH:MM'
        
        Returns:
            bool: True si está disponible
        """
        try:
            professional = self.db.get_professional(professional_phone)
            calendar_id = professional['calendar_id']
            
            is_available = self.calendar_service.check_slot_available(
                calendar_id=calendar_id,
                start_datetime=f"{date} {start_time}",
                end_datetime=f"{date} {end_time}"
            )
            
            return is_available
            
        except Exception as e:
            logger.error(f"Error al verificar slot: {e}")
            return False
    
    # ========================================================================
    # CREACIÓN DE CITAS
    # ========================================================================
    
    def create_appointment(
        self,
        professional_phone: str,
        client_phone: str,
        client_name: str,
        date: str,
        start_time: str,
        end_time: str,
        appointment_type: str,
        notes: Optional[str] = None
    ) -> int:
        """
        Crea una cita en Google Calendar y en la BD local.
        
        Args:
            professional_phone: Teléfono del profesional
            client_phone: Teléfono del cliente
            client_name: Nombre del cliente
            date: Fecha en 'YYYY-MM-DD'
            start_time: Hora inicio en 'HH:MM'
            end_time: Hora fin en 'HH:MM'
            appointment_type: Tipo de consulta
            notes: Notas adicionales (opcional)
        
        Returns:
            int: ID de la cita en BD local
        
        Raises:
            Exception: Si hay error al crear la cita
        """
        logger.info(
            f"Creando cita: {client_name} con {professional_phone} "
            f"el {date} a las {start_time}"
        )
        
        try:
            # 1. Obtener configuración del profesional
            professional = self.db.get_professional(professional_phone)
            calendar_id = professional['calendar_id']
            
            # 2. Crear evento en Google Calendar
            logger.info("Creando evento en Google Calendar...")
            google_event = self.calendar_service.create_appointment(
                calendar_id=calendar_id,
                start_datetime=f"{date} {start_time}",
                end_datetime=f"{date} {end_time}",
                client_name=client_name,
                client_phone=client_phone,
                appointment_type=appointment_type,
                notes=notes
            )
            
            google_event_id = google_event['id']
            logger.info(f"Evento creado en Google Calendar: {google_event_id}")
            
            # 3. Guardar en BD local con referencia a Google Calendar
            logger.info("Guardando cita en BD local...")
            # Calculate duration
            from datetime import datetime as dt
            duration = int((dt.strptime(end_time, '%H:%M') - 
                          dt.strptime(start_time, '%H:%M')).seconds / 60)
            
            # Map appointment_type to valid session_type
            session_type_map = {
                'Consulta': 'primera_vez',
                'primera_vez': 'primera_vez',
                'seguimiento': 'seguimiento',
                'evaluacion': 'evaluacion'
            }
            session_type = session_type_map.get(appointment_type, 'primera_vez')
            
            appointment_id = self.db.create_appointment(
                client_phone=client_phone,
                professional_phone=professional_phone,
                appointment_date=date,
                start_time=start_time,
                end_time=end_time,
                duration_minutes=duration,
                session_type=session_type,  # ✅ Mapped value
                modality='presencial',
                google_event_id=google_event_id,  # ⭐ IMPORTANTE
                notes=notes
            )
            
            logger.info(
                f"Cita creada exitosamente. "
                f"BD ID: {appointment_id}, Google ID: {google_event_id}"
            )
            
            return appointment_id
            
        except Exception as e:
            logger.error(f"Error al crear cita: {e}")
            # Si falló después de crear en Google, intentar limpiar
            if 'google_event_id' in locals():
                try:
                    self.calendar_service.cancel_appointment(
                        calendar_id, google_event_id
                    )
                    logger.info("Evento de Google Calendar limpiado")
                except:
                    pass
            raise
    
    # ========================================================================
    # CANCELACIÓN DE CITAS
    # ========================================================================
    
    def cancel_appointment(
        self,
        appointment_id: int,
        cancellation_reason: str = "Cancelado por el cliente"
    ) -> bool:
        """
        Cancela una cita en Google Calendar y en BD local.
        
        Args:
            appointment_id: ID de la cita en BD local
            cancellation_reason: Motivo de la cancelación
        
        Returns:
            bool: True si se canceló exitosamente
        """
        logger.info(f"Cancelando cita {appointment_id}")
        
        try:
            # 1. Obtener información de la cita desde BD
            appointment = self.db.get_appointment(appointment_id)
            
            if not appointment:
                raise ValueError(f"Cita {appointment_id} no encontrada")
            
            # 2. Obtener google_event_id
            google_event_id = appointment.get('google_event_id')
            
            if google_event_id:
                # 3. Obtener calendar_id del profesional
                professional = self.db.get_professional(
                    appointment['professional_phone']
                )
                calendar_id = professional['calendar_id']
                
                # 4. Cancelar en Google Calendar
                logger.info(f"Cancelando evento en Google Calendar: {google_event_id}")
                self.calendar_service.cancel_appointment(
                    calendar_id=calendar_id,
                    event_id=google_event_id,
                    cancellation_reason=cancellation_reason
                )
                logger.info("Evento cancelado en Google Calendar")
            else:
                logger.warning(
                    f"Cita {appointment_id} no tiene google_event_id, "
                    "solo se cancelará en BD local"
                )
            
            # 5. Actualizar estado en BD local
            self.db.update_appointment(appointment_id, {
                'status': 'cancelled',
                'cancellation_reason': cancellation_reason,
                'cancelled_at': datetime.now().isoformat()
            })
            
            logger.info(f"Cita {appointment_id} cancelada exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"Error al cancelar cita: {e}")
            raise
    
    # ========================================================================
    # REPROGRAMACIÓN
    # ========================================================================
    
    def reschedule_appointment(
        self,
        appointment_id: int,
        new_date: str,
        new_start_time: str,
        new_end_time: str
    ) -> bool:
        """
        Reprograma una cita a un nuevo horario.
        
        Args:
            appointment_id: ID de la cita
            new_date: Nueva fecha 'YYYY-MM-DD'
            new_start_time: Nueva hora inicio 'HH:MM'
            new_end_time: Nueva hora fin 'HH:MM'
        
        Returns:
            bool: True si se reprogramó exitosamente
        """
        logger.info(
            f"Reprogramando cita {appointment_id} a {new_date} {new_start_time}"
        )
        
        try:
            # 1. Obtener cita actual
            appointment = self.db.get_appointment(appointment_id)
            google_event_id = appointment.get('google_event_id')
            
            if google_event_id:
                # 2. Obtener calendar_id
                professional = self.db.get_professional(
                    appointment['professional_phone']
                )
                calendar_id = professional['calendar_id']
                
                # 3. Reprogramar en Google Calendar
                self.calendar_service.reschedule_appointment(
                    calendar_id=calendar_id,
                    event_id=google_event_id,
                    new_start_datetime=f"{new_date} {new_start_time}",
                    new_end_datetime=f"{new_date} {new_end_time}"
                )
            
            # 4. Actualizar en BD local
            self.db.update_appointment(appointment_id, {
                'date': new_date,
                'start_time': new_start_time,
                'end_time': new_end_time,
                'updated_at': datetime.now().isoformat()
            })
            
            logger.info(f"Cita {appointment_id} reprogramada exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"Error al reprogramar cita: {e}")
            raise