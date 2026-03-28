"""
Appointment Service - Wrapper
Delegates to AppointmentCalendarService for full integration
"""

from src.integrations.appointment_calendar_service import AppointmentCalendarService
from src.database.database import db


class AppointmentService:
    """
    Service wrapper for appointment operations.
    Delegates to AppointmentCalendarService for Google Calendar integration.
    """
    
    def __init__(self):
        """Initialize with database connection."""
        self.calendar_service = AppointmentCalendarService(db)
    
    def create_appointment(
        self,
        client_phone: str,
        client_name: str,
        professional_phone: str,
        date: str,
        start_time: str,
        end_time: str,
        appointment_type: str = "Consulta",
        notes: str = None,
        patient_phone: str = None      # GAP 4 — teléfono del paciente real si es tercero
    ) -> str:
        """
        Create appointment in Google Calendar AND database.
        
        Args:
            client_phone: Client phone number
            client_name: Client name
            professional_phone: Professional phone number
            date: Date in YYYY-MM-DD format
            start_time: Start time in HH:MM format
            end_time: End time in HH:MM format
            appointment_type: Type of appointment (default: "Consulta")
            notes: Optional notes
            patient_phone: Phone of the actual patient if booked for a third party
        
        Returns:
            str: appointment ID
        """
        # Delegate to AppointmentCalendarService which handles both
        # Google Calendar creation AND database storage
        appointment_id = self.calendar_service.create_appointment(
            professional_phone=professional_phone,
            client_phone=client_phone,
            client_name=client_name,
            date=date,
            start_time=start_time,
            end_time=end_time,
            appointment_type=appointment_type,
            notes=notes,
            patient_phone=patient_phone    # GAP 4
        )
        
        # Return appointment_id (database ID)
        # The google_event_id is stored in the database
        return str(appointment_id)
    
    def cancel_appointment(
        self,
        appointment_id: int,
        cancellation_reason: str = "Cancelado por el cliente"
    ) -> bool:
        """
        Cancel appointment in both Google Calendar and database.
        
        Args:
            appointment_id: Database appointment ID
            cancellation_reason: Reason for cancellation
        
        Returns:
            bool: True if successful
        """
        return self.calendar_service.cancel_appointment(
            appointment_id=appointment_id,
            cancellation_reason=cancellation_reason
        )
    
    def reschedule_appointment(
        self,
        appointment_id: int,
        new_date: str,
        new_start_time: str,
        new_end_time: str
    ) -> bool:
        """
        Reschedule appointment to new date/time.
        
        Args:
            appointment_id: Database appointment ID
            new_date: New date in YYYY-MM-DD format
            new_start_time: New start time in HH:MM format
            new_end_time: New end time in HH:MM format
        
        Returns:
            bool: True if successful
        """
        return self.calendar_service.reschedule_appointment(
            appointment_id=appointment_id,
            new_date=new_date,
            new_start_time=new_start_time,
            new_end_time=new_end_time
        )
    
    def get_available_slots(
        self,
        professional_phone: str,
        date: str
    ):
        """
        Get available slots for a professional on a date.
        
        Args:
            professional_phone: Professional phone number
            date: Date in YYYY-MM-DD format
        
        Returns:
            List of available time slots
        """
        return self.calendar_service.get_available_slots(
            professional_phone=professional_phone,
            date=date
        )


# Global instance
appointment_service = AppointmentService()