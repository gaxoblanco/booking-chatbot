"""
EJEMPLO DE INTEGRACIÓN CON EL CHATBOT
======================================

Este archivo muestra cómo integrar el GoogleCalendarService
con el sistema de reservas del chatbot de WhatsApp.
"""

from datetime import datetime, timedelta
from src.integrations.google_calendar_service import GoogleCalendarService


class AppointmentCalendarIntegration:
    """
    Integración entre el sistema de citas y Google Calendar.
    
    Esta clase actúa como puente entre el chatbot y Google Calendar,
    sincronizando las reservas en ambas direcciones.
    """
    
    def __init__(self):
        """Inicializa el servicio de Google Calendar."""
        self.calendar_service = GoogleCalendarService()
    
    # ========================================================================
    # FLUJO: CLIENTE BUSCA DISPONIBILIDAD
    # ========================================================================
    
    def show_available_slots_to_client(
        self,
        professional_phone: str,
        date: str,
        db  # Referencia a la base de datos del chatbot
    ) -> list:
        """
        Obtiene slots disponibles para mostrar al cliente.
        
        Uso en client_handler.py:
            slots = integration.show_available_slots_to_client(
                professional_phone="+5491187654321",
                date="2026-01-17",
                db=database
            )
            
            # Formatear para WhatsApp
            message = "Horarios disponibles:\n\n"
            for i, slot in enumerate(slots, 1):
                message += f"{i}. {slot['start']} - {slot['end']}\n"
        
        Args:
            professional_phone: Teléfono del profesional
            date: Fecha en formato 'YYYY-MM-DD'
            db: Instancia de la base de datos
        
        Returns:
            list: Lista de slots disponibles
        """
        # 1. Obtener configuración del profesional desde BD
        professional = db.get_professional(professional_phone)
        
        if not professional:
            raise ValueError(f"Profesional {professional_phone} no encontrado")
        
        # 2. Obtener calendar_id (email) del profesional
        calendar_id = professional.get('calendar_id')
        if not calendar_id:
            raise ValueError(f"Profesional no tiene calendar_id configurado")
        
        # 3. Consultar disponibilidad en Google Calendar
        slots = self.calendar_service.get_available_slots(
            calendar_id=calendar_id,
            date=date,
            working_hours=professional['working_hours'],
            slot_duration_minutes=professional['slot_duration']
        )
        
        return slots
    
    # ========================================================================
    # FLUJO: CLIENTE CONFIRMA CITA
    # ========================================================================
    
    def create_appointment_in_calendar(
        self,
        professional_phone: str,
        client_phone: str,
        client_name: str,
        date: str,
        start_time: str,
        end_time: str,
        appointment_type: str,
        db  # Referencia a la base de datos
    ) -> dict:
        """
        Crea una cita en Google Calendar y en la BD del chatbot.
        
        Uso en appointment_service.py:
            result = integration.create_appointment_in_calendar(
                professional_phone="+5491187654321",
                client_phone="+5491112345678",
                client_name="Juan Pérez",
                date="2026-01-17",
                start_time="14:00",
                end_time="15:00",
                appointment_type="Consulta inicial",
                db=database
            )
            
            print(f"Cita creada con ID: {result['appointment_id']}")
            print(f"Google Event ID: {result['google_event_id']}")
        
        Args:
            professional_phone: Teléfono del profesional
            client_phone: Teléfono del cliente
            client_name: Nombre del cliente
            date: Fecha en 'YYYY-MM-DD'
            start_time: Hora inicio en 'HH:MM'
            end_time: Hora fin en 'HH:MM'
            appointment_type: Tipo de consulta
            db: Instancia de la base de datos
        
        Returns:
            dict: {
                'appointment_id': ID en BD local,
                'google_event_id': ID en Google Calendar,
                'success': bool
            }
        """
        # 1. Obtener configuración del profesional
        professional = db.get_professional(professional_phone)
        calendar_id = professional['calendar_id']
        
        # 2. Crear evento en Google Calendar
        google_event = self.calendar_service.create_appointment(
            calendar_id=calendar_id,
            start_datetime=f"{date} {start_time}",
            end_datetime=f"{date} {end_time}",
            client_name=client_name,
            client_phone=client_phone,
            appointment_type=appointment_type
        )
        
        google_event_id = google_event['id']
        
        # 3. Guardar en BD local con referencia a Google Calendar
        appointment_id = db.create_appointment({
            'professional_phone': professional_phone,
            'client_phone': client_phone,
            'client_name': client_name,
            'date': date,
            'start_time': start_time,
            'end_time': end_time,
            'appointment_type': appointment_type,
            'google_event_id': google_event_id,  # ⭐ IMPORTANTE: Guardar ID
            'status': 'confirmed',
            'created_at': datetime.now().isoformat()
        })
        
        return {
            'appointment_id': appointment_id,
            'google_event_id': google_event_id,
            'success': True
        }
    
    # ========================================================================
    # FLUJO: CLIENTE CANCELA CITA
    # ========================================================================
    
    def cancel_appointment_in_calendar(
        self,
        appointment_id: int,
        cancellation_reason: str,
        db  # Referencia a la base de datos
    ) -> bool:
        """
        Cancela una cita tanto en Google Calendar como en BD local.
        
        Uso en client_handler.py o appointment_service.py:
            success = integration.cancel_appointment_in_calendar(
                appointment_id=123,
                cancellation_reason="Cliente solicitó cancelación",
                db=database
            )
            
            if success:
                send_whatsapp_message(client_phone, "Cita cancelada exitosamente")
        
        Args:
            appointment_id: ID de la cita en BD local
            cancellation_reason: Motivo de cancelación
            db: Instancia de la base de datos
        
        Returns:
            bool: True si se canceló exitosamente
        """
        # 1. Obtener información de la cita desde BD
        appointment = db.get_appointment(appointment_id)
        
        if not appointment:
            raise ValueError(f"Cita {appointment_id} no encontrada")
        
        # 2. Obtener google_event_id
        google_event_id = appointment.get('google_event_id')
        
        if not google_event_id:
            # Si no hay google_event_id, solo cancelar en BD
            db.update_appointment(appointment_id, {'status': 'cancelled'})
            return True
        
        # 3. Obtener calendar_id del profesional
        professional = db.get_professional(appointment['professional_phone'])
        calendar_id = professional['calendar_id']
        
        # 4. Cancelar en Google Calendar
        success = self.calendar_service.cancel_appointment(
            calendar_id=calendar_id,
            event_id=google_event_id,
            cancellation_reason=cancellation_reason
        )
        
        # 5. Actualizar estado en BD local
        if success:
            db.update_appointment(appointment_id, {
                'status': 'cancelled',
                'cancellation_reason': cancellation_reason,
                'cancelled_at': datetime.now().isoformat()
            })
        
        return success
    
    # ========================================================================
    # FLUJO: REPROGRAMAR CITA
    # ========================================================================
    
    def reschedule_appointment_in_calendar(
        self,
        appointment_id: int,
        new_date: str,
        new_start_time: str,
        new_end_time: str,
        db  # Referencia a la base de datos
    ) -> bool:
        """
        Reprograma una cita a un nuevo horario.
        
        Args:
            appointment_id: ID de la cita
            new_date: Nueva fecha 'YYYY-MM-DD'
            new_start_time: Nueva hora inicio 'HH:MM'
            new_end_time: Nueva hora fin 'HH:MM'
            db: Instancia de la base de datos
        
        Returns:
            bool: True si se reprogramó exitosamente
        """
        # 1. Obtener cita actual
        appointment = db.get_appointment(appointment_id)
        google_event_id = appointment['google_event_id']
        
        # 2. Obtener calendar_id
        professional = db.get_professional(appointment['professional_phone'])
        calendar_id = professional['calendar_id']
        
        # 3. Reprogramar en Google Calendar
        updated_event = self.calendar_service.reschedule_appointment(
            calendar_id=calendar_id,
            event_id=google_event_id,
            new_start_datetime=f"{new_date} {new_start_time}",
            new_end_datetime=f"{new_date} {new_end_time}"
        )
        
        # 4. Actualizar en BD local
        db.update_appointment(appointment_id, {
            'date': new_date,
            'start_time': new_start_time,
            'end_time': new_end_time,
            'updated_at': datetime.now().isoformat()
        })
        
        return True


# ============================================================================
# EJEMPLO DE USO EN EL CHATBOT
# ============================================================================

"""
# En bot_controller.py o donde inicialices los servicios:

from integrations.appointment_calendar_integration import AppointmentCalendarIntegration

calendar_integration = AppointmentCalendarIntegration()


# En client_handler.py - Cuando el cliente busca horarios:

def handle_show_availability(phone, message, session, db):
    # ... lógica para obtener fecha y profesional ...
    
    try:
        slots = calendar_integration.show_available_slots_to_client(
            professional_phone=session.get('selected_professional'),
            date=session.get('selected_date'),
            db=db
        )
        
        if not slots:
            return "No hay horarios disponibles para este día."
        
        # Formatear respuesta
        response = f"Horarios disponibles para {session.get('selected_date')}:\\n\\n"
        for i, slot in enumerate(slots[:10], 1):
            response += f"{i}. {slot['start']} - {slot['end']}\\n"
        
        return response
        
    except Exception as e:
        logger.error(f"Error al consultar disponibilidad: {e}")
        return "Hubo un error al consultar la disponibilidad. Intente más tarde."


# En appointment_service.py - Cuando se confirma una cita:

def create_appointment(professional_phone, client_phone, client_name, 
                      date, start_time, end_time, appointment_type, db):
    try:
        result = calendar_integration.create_appointment_in_calendar(
            professional_phone=professional_phone,
            client_phone=client_phone,
            client_name=client_name,
            date=date,
            start_time=start_time,
            end_time=end_time,
            appointment_type=appointment_type,
            db=db
        )
        
        if result['success']:
            logger.info(
                f"Cita creada: BD ID={result['appointment_id']}, "
                f"Google ID={result['google_event_id']}"
            )
            return result['appointment_id']
        
    except Exception as e:
        logger.error(f"Error al crear cita: {e}")
        raise


# En client_handler.py - Cuando se cancela una cita:

def handle_cancel_appointment(phone, appointment_id, db):
    try:
        success = calendar_integration.cancel_appointment_in_calendar(
            appointment_id=appointment_id,
            cancellation_reason="Cliente solicitó cancelación por WhatsApp",
            db=db
        )
        
        if success:
            return "Tu cita ha sido cancelada exitosamente."
        else:
            return "Hubo un error al cancelar la cita. Contacta al profesional."
            
    except Exception as e:
        logger.error(f"Error al cancelar cita: {e}")
        return "Error al procesar la cancelación."
"""
