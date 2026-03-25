"""
Intent Enum
===========
Enumeración de intenciones soportadas por el modelo.
"""

from enum import Enum


class Intent(str, Enum):
    """
    Intenciones soportadas por el detector.

    Cada intención representa una acción que el usuario quiere realizar.
    """

    # Búsqueda de profesionales/turnos
    SEARCH_PROFESSIONAL = "search_professional"
    """Buscar profesional o solicitar turno"""

    # Consulta de turnos
    VIEW_MY_APPOINTMENTS = "view_my_appointments"
    """Ver mis turnos programados"""

    VIEW_TOMORROW = "view_tomorrow"
    """Ver turnos de mañana"""

    # Gestión de turnos
    CANCEL_APPOINTMENT = "cancel_appointment"
    """Cancelar un turno existente"""

    # Información
    INFO_CENTER = "info_center"
    """Información sobre el centro/clínica"""

    # Sociales
    GREETING = "greeting"
    """Saludo o bienvenida"""

    # Fallback
    UNKNOWN = "unknown"
    """Intención no reconocida"""

    # Importación de agenda (solo en estado PROF_AGENDA_IMPORT_REVIEW)
    AGENDA_VIEW_READY = "agenda_view_ready"
    """Ver pacientes listos para cargar"""

    AGENDA_VIEW_OVERLAPS = "agenda_view_overlaps"
    """Ver pacientes con solapamiento de horario"""

    AGENDA_VIEW_EXISTING = "agenda_view_existing"
    """Ver pacientes que ya estaban cargados"""

    AGENDA_VIEW_ERRORS = "agenda_view_errors"
    """Ver pacientes con datos inválidos"""

    AGENDA_CONFIRM_UPLOAD = "agenda_confirm_upload"
    """Confirmar carga de pacientes listos"""

    AGENDA_CANCEL_UPLOAD = "agenda_cancel_upload"
    """Cancelar la carga de agenda"""

    # Agendar para terceros
    BOOK_FOR_THIRD_PARTY = "book_for_third_party"
    """Agendar turno para otra persona"""

    def __str__(self) -> str:
        """String representation."""
        return self.value

    @classmethod
    def from_string(cls, value: str) -> 'Intent':
        """
        Convierte string a Intent enum.

        Args:
            value: String con el nombre de la intención

        Returns:
            Intent enum correspondiente

        Raises:
            ValueError: Si la intención no existe
        """
        try:
            return cls(value)
        except ValueError:
            return cls.UNKNOWN

    @classmethod
    def all_intents(cls) -> list:
        """
        Retorna lista de todas las intenciones.

        Returns:
            Lista de strings con nombres de intenciones
        """
        return [intent.value for intent in cls]
