"""
Appointment Messages
====================
Mensajes del flujo de citas. Leen del tono activo.
Los métodos helper estáticos se mantienen sin cambios.
"""

from src.config.domain_config import DomainConfig
from src.messages.loader import get_msg


class AppointmentMessages:

    # --- Vista de citas ---

    @property
    def CLIENT_VIEW_APPOINTMENTS(self):
        return get_msg("CLIENT_VIEW_APPOINTMENTS",
            f"📋 *Mis {DomainConfig.APPOINTMENT_NAME_PLURAL.title()}*\n\n"
            "{appointments_list}\n\n"
            f"_Enviá el número para ver detalles_\n"
            "_Escribe *0* para volver al menú_"
        )

    @property
    def CLIENT_NO_APPOINTMENTS(self):
        return get_msg("CLIENT_NO_APPOINTMENTS",
            f"No tenés {DomainConfig.APPOINTMENT_NAME_PLURAL} programadas.\n\n"
            "1️⃣ Buscar profesional\n0️⃣ Volver al menú"
        )

    @property
    def CLIENT_BOOKING_COLLECT_NAME(self):
        return get_msg("CLIENT_BOOKING_COLLECT_NAME")

    # --- Confirmación de turno ---

    @property
    def CLIENT_CONFIRM_BOOKING(self):
        return get_msg("CLIENT_CONFIRM_BOOKING")

    @property
    def CLIENT_BOOKING_SUCCESS(self):
        return get_msg("CLIENT_BOOKING_SUCCESS")

    @property
    def CLIENT_BOOKING_ERROR(self):
        return get_msg("CLIENT_BOOKING_ERROR")

    # --- Detalle ---

    @property
    def CLIENT_APPOINTMENT_DETAIL(self):
        return get_msg("CLIENT_APPOINTMENT_DETAIL")

    @property
    def CLIENT_APPOINTMENT_OPTIONS_CONFIRMED(self):
        return get_msg("CLIENT_APPOINTMENT_OPTIONS_CONFIRMED",
            f"1️⃣ Reprogramar {DomainConfig.APPOINTMENT_NAME}\n"
            f"2️⃣ Cancelar {DomainConfig.APPOINTMENT_NAME}"
        )

    @property
    def CLIENT_APPOINTMENT_OPTIONS_PENDING(self):
        return get_msg("CLIENT_APPOINTMENT_OPTIONS_PENDING",
            f"1️⃣ Reprogramar {DomainConfig.APPOINTMENT_NAME}\n"
            f"2️⃣ Cancelar {DomainConfig.APPOINTMENT_NAME}"
        )

    @property
    def CLIENT_APPOINTMENT_FINISHED(self):
        return get_msg("CLIENT_APPOINTMENT_FINISHED",
            f"Esa {DomainConfig.APPOINTMENT_NAME} ya pasó, no se puede cancelar."
        )

    @property
    def CLIENT_APPOINTMENT_ALREADY_CANCELLED(self):
        return get_msg("CLIENT_APPOINTMENT_ALREADY_CANCELLED",
            f"Esa {DomainConfig.APPOINTMENT_NAME} ya estaba cancelada."
        )

    # --- Cancelación ---

    @property
    def CLIENT_CANCEL_APPOINTMENT_CONFIRM(self):
        return get_msg("CLIENT_CANCEL_APPOINTMENT_CONFIRM")

    @property
    def CLIENT_CANCEL_POLICY_INFO(self):
        return get_msg("CLIENT_CANCEL_POLICY_INFO")

    @property
    def CLIENT_CANCEL_TOO_LATE(self):
        return get_msg("CLIENT_CANCEL_TOO_LATE")

    @property
    def CLIENT_CANCEL_BLOCKED_CONFIRMED(self):
        return get_msg("CLIENT_CANCEL_BLOCKED_CONFIRMED")

    @property
    def CLIENT_CANCEL_ERROR(self):
        return get_msg("CLIENT_CANCEL_ERROR")

    @property
    def CLIENT_APPOINTMENT_CANCELLED(self):
        return get_msg("CLIENT_APPOINTMENT_CANCELLED",
            f"✅ {DomainConfig.APPOINTMENT_NAME_UPPER} cancelada.\n\n"
            "1️⃣ Buscar nuevo turno · 0️⃣ Menú"
        )

    # --- Reprogramación ---

    @property
    def CLIENT_RESCHEDULE_SELECT_DATE(self):
        return get_msg("CLIENT_RESCHEDULE_SELECT_DATE")

    @property
    def CLIENT_RESCHEDULE_SELECT_TIME(self):
        return get_msg("CLIENT_RESCHEDULE_SELECT_TIME")

    @property
    def CLIENT_RESCHEDULE_CONFIRM(self):
        return get_msg("CLIENT_RESCHEDULE_CONFIRM")

    @property
    def CLIENT_RESCHEDULE_SUCCESS(self):
        return get_msg("CLIENT_RESCHEDULE_SUCCESS")

    @property
    def CLIENT_RESCHEDULE_TOO_LATE(self):
        return get_msg("CLIENT_RESCHEDULE_TOO_LATE")

    @property
    def CLIENT_NO_DATES_AVAILABLE(self):
        return get_msg("CLIENT_NO_DATES_AVAILABLE")

    @property
    def CLIENT_NO_SLOTS_AVAILABLE(self):
        return get_msg("CLIENT_NO_SLOTS_AVAILABLE")

    # --- Métodos helper estáticos — sin cambios ---

    @staticmethod
    def format_appointment_status(status: str) -> str:
        statuses = {
            'pendiente_confirmacion': '⏳ Pendiente',
            'confirmada': '✅ Agendada',
            'completada': '✔️ Completada',
            'cancelada_cliente': '❌ Cancelada',
            'cancelada_profesional': '❌ Cancelada',
            'no_asistio': '⚠️ No asistió',
            'reagendada': '🔄 Reagendada'
        }
        return statuses.get(status, status)

    @staticmethod
    def format_status_emoji(status: str) -> str:
        emojis = {
            'pendiente_confirmacion': '⏳',
            'confirmada': '✅',
            'completada': '✔️',
            'cancelada_cliente': '❌',
            'cancelada_profesional': '❌',
            'no_asistio': '⚠️',
            'reagendada': '🔄'
        }
        return emojis.get(status, '📅')

    @staticmethod
    def format_modality(modality: str) -> str:
        return DomainConfig.MODALITY_LABELS.get(modality, modality)



    @property
    def CONFIRM_BOOKING_HEADER(self):
        return get_msg("CONFIRM_BOOKING_HEADER")

    @property
    def BOOKING_SUCCESS(self):
        return get_msg("BOOKING_SUCCESS")

    @property
    def BOOKING_ERROR(self):
        return get_msg("BOOKING_ERROR")

    @property
    def THIRD_PARTY_INTRO(self):
        return get_msg("THIRD_PARTY_INTRO")

    @property
    def THIRD_PARTY_PHONE(self):
        return get_msg("THIRD_PARTY_PHONE")

    @property
    def THIRD_PARTY_AGE(self):
        return get_msg("THIRD_PARTY_AGE")

    @property
    def CANCEL_ERROR_TECHNICAL(self):
        return get_msg("CANCEL_ERROR_TECHNICAL")

    @property
    def CANCEL_BLOCKED_TIME(self):
        return get_msg("CANCEL_BLOCKED_TIME")

    @property
    def CANCEL_BLOCKED_CONFIRMED(self):
        return get_msg("CANCEL_BLOCKED_CONFIRMED")

    @property
    def RESCHEDULE_ERROR_TECHNICAL(self):
        return get_msg("RESCHEDULE_ERROR_TECHNICAL")

    @property
    def RESCHEDULE_BLOCKED_TIME(self):
        return get_msg("RESCHEDULE_BLOCKED_TIME")

    @property
    def APPOINTMENT_LOAD_ERROR(self):
        return get_msg("APPOINTMENT_LOAD_ERROR")

    @property
    def APPOINTMENT_FINISHED(self):
        return get_msg("APPOINTMENT_FINISHED")

    @property
    def APPOINTMENT_CANT_RESCHEDULE(self):
        return get_msg("APPOINTMENT_CANT_RESCHEDULE")

    @property
    def DATE_ALREADY_PASSED(self):
        return get_msg("DATE_ALREADY_PASSED")


    @property
    def BOOKING_LIMIT_GLOBAL(self):
        return get_msg("BOOKING_LIMIT_GLOBAL")

    @property
    def BOOKING_LIMIT_PER_PROFESSIONAL(self):
        return get_msg("BOOKING_LIMIT_PER_PROFESSIONAL")

appointment_messages = AppointmentMessages()