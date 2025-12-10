"""
Appointment Service
===================
Gestión de citas/turnos.
"""
from src.database.database import db
from datetime import datetime
from typing import List, Dict, Optional


class AppointmentService:
    """Servicio para gestionar citas."""

    def create_appointment(self, client_phone, professional_phone,
                           date, start_time, end_time) -> int:
        """Crear nueva cita."""
        pass

    def get_upcoming_appointments(self, phone, role='client') -> List[Dict]:
        """Obtener próximas citas."""
        pass

    def confirm_appointment(self, appointment_id) -> bool:
        """Confirmar cita."""
        pass

    def cancel_appointment(self, appointment_id, reason) -> bool:
        """Cancelar cita."""
        pass
