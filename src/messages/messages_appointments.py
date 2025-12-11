"""
Appointment Messages
====================
Mensajes del sistema de gestión de citas.
Usado por ambos roles: cliente y profesional.
"""

from src.config.domain_config import DomainConfig


class AppointmentMessages:
    """
    Mensajes del sistema de citas.
    Incluye: reserva, gestión, cancelación, reprogramación.
    """

    # ==========================================
    # CLIENT - BOOKING FLOW (Inicio de reserva)
    # ==========================================

    CLIENT_START_BOOKING = f"""📅 *Agendar {DomainConfig.APPOINTMENT_NAME_UPPER}*

Vas a agendar una {DomainConfig.APPOINTMENT_NAME} con este {DomainConfig.PROFESSIONAL_TITLE_LOWER}.

¿Para quién es la {DomainConfig.APPOINTMENT_NAME}?
1️⃣ Para mí
2️⃣ Para otra persona

_Escribe *0* para volver_"""

    # Preguntar nombre del paciente (si es para otra persona)
    CLIENT_BOOKING_PATIENT_NAME = f"""👤 *Datos del {DomainConfig.PATIENT_LABEL_UPPER}*

¿Cuál es el nombre completo del {DomainConfig.PATIENT_LABEL}?

Ejemplo: Juan Pérez

_Escribe *0* para cancelar_"""

    CLIENT_BOOKING_PATIENT_PHONE = f"""📞 *Teléfono del {DomainConfig.PATIENT_LABEL_UPPER}* (opcional)

¿Cuál es el teléfono del {DomainConfig.PATIENT_LABEL}?

Formato: +5491112345678

• Escribe el teléfono
• O envía *saltar* para omitir

_Escribe *0* para volver_"""

    # Elegir modalidad (si está habilitado en config)
    CLIENT_BOOKING_SELECT_MODALITY = f"""📍 *Modalidad de Atención*

¿Cómo preferís la {DomainConfig.APPOINTMENT_NAME}?

{{modality_options}}

_Escribe *0* para volver_"""

    # Seleccionar fecha
    CLIENT_BOOKING_SELECT_DATE = f"""📅 *Seleccionar Fecha*

Fechas disponibles para tu {DomainConfig.APPOINTMENT_NAME}:

{{available_dates}}

Por favor:
• Envía el número de la fecha deseada
• O escribe la fecha en formato DD/MM/YYYY

_Escribe *0* para volver_"""

    # Seleccionar horario
    CLIENT_BOOKING_SELECT_TIME = f"""⏰ *Horarios Disponibles*

📅 Fecha: {{date}}

{{available_slots}}

Envía el número del horario que prefieras.

_Escribe *0* para elegir otra fecha_"""

    # No hay horarios disponibles para la fecha elegida
    CLIENT_NO_SLOTS_AVAILABLE = f"""😔 *No hay horarios disponibles*

Lo sentimos, este {DomainConfig.PROFESSIONAL_TITLE_LOWER} no tiene horarios disponibles para esta fecha.

¿Qué deseas hacer?
1️⃣ Elegir otra fecha
2️⃣ Ver otros {DomainConfig.PROFESSIONAL_TITLE_PLURAL_LOWER}
0️⃣ Volver al menú"""

    # No hay fechas disponibles en general
    CLIENT_NO_DATES_AVAILABLE = f"""😔 *Sin disponibilidad*

Este {DomainConfig.PROFESSIONAL_TITLE_LOWER} no tiene fechas disponibles en los próximos {{days}} días.

¿Qué deseas hacer?
1️⃣ Ver otros {DomainConfig.PROFESSIONAL_TITLE_PLURAL_LOWER}
0️⃣ Volver al menú"""

    # ==========================================
    # CLIENT - COLLECT CLIENT DATA
    # ==========================================

    CLIENT_BOOKING_COLLECT_NAME = """👤 *Tus Datos*

Para completar la reserva, necesitamos algunos datos.

¿Cuál es tu nombre completo?

Ejemplo: María González

_Escribe *0* para cancelar_"""

    CLIENT_BOOKING_COLLECT_EMAIL = """📧 *Email* (opcional)

¿Cuál es tu email?

Te enviaremos la confirmación y recordatorios por esta vía.

Ejemplo: maria@ejemplo.com

• Escribe tu email
• O envía *saltar* para omitir

_Escribe *0* para volver_"""

    CLIENT_BOOKING_COLLECT_AGE = """🎂 *Edad* (opcional)

¿Cuál es tu edad?

Ejemplo: 28

• Escribe tu edad
• O envía *saltar* para omitir

_Escribe *0* para volver_"""

    CLIENT_BOOKING_COLLECT_GENDER = """👤 *Género* (opcional)

¿Cuál es tu género?

1️⃣ Masculino
2️⃣ Femenino
3️⃣ Otro
4️⃣ Prefiero no decir

• Escribe el número
• O envía *saltar* para omitir

_Escribe *0* para volver_"""

    # ==========================================
    # CLIENT - APPOINTMENT REASON
    # ==========================================

    CLIENT_BOOKING_REASON = f"""📝 *{DomainConfig.REASON_LABEL}*

{{reason_prompt}}

• Escribe el motivo
• O envía *saltar* para omitir

_Escribe *0* para volver_"""

    # ==========================================
    # CLIENT - CONFIRM BOOKING
    # ==========================================

    CLIENT_BOOKING_CONFIRM = f"""✅ *Confirmar Reserva*

{{booking_for_info}}
📅 Fecha: *{{date}}*
⏰ Hora: *{{time}}*
👨‍⚕️ {DomainConfig.PROFESSIONAL_TITLE}: *{{professional_name}}*
📍 Modalidad: *{{modality}}*
⏱️ Duración: *{{duration}} minutos*
{{reason_info}}

¿Confirmas esta reserva?

1️⃣ Sí, confirmar
0️⃣ Cancelar"""

    # ==========================================
    # CLIENT - BOOKING SUCCESS
    # ==========================================

    CLIENT_BOOKING_SUCCESS = f"""🎉 *¡Reserva Exitosa!*

Tu {DomainConfig.APPOINTMENT_NAME} ha sido registrada:

{DomainConfig.APPOINTMENT_EMOJI} {DomainConfig.APPOINTMENT_NAME_UPPER} #{{appointment_id}}
📅 {{date}}
⏰ {{time}}
👨‍⚕️ {{professional_name}}
📍 {{modality}}

{{status_info}}

{{next_steps_info}}

¿Qué deseas hacer?
1️⃣ Ver mis {DomainConfig.APPOINTMENT_NAME_PLURAL}
2️⃣ Buscar otro {DomainConfig.PROFESSIONAL_TITLE_LOWER}
0️⃣ Menú principal"""

    CLIENT_BOOKING_SUCCESS_AUTO_CONFIRMED = f"""Estado: *Confirmada* ✅

{DomainConfig.APPOINTMENT_CONFIRMED_MESSAGE}"""

    CLIENT_BOOKING_SUCCESS_PENDING = f"""Estado: *Pendiente de confirmación* ⏳

{DomainConfig.APPOINTMENT_PENDING_MESSAGE}"""

    # ==========================================
    # CLIENT - VIEW APPOINTMENTS
    # ==========================================

    CLIENT_VIEW_APPOINTMENTS = f"""📋 *Mis {DomainConfig.APPOINTMENT_NAME_PLURAL.title()}*

{{appointments_list}}

_Envía el número de la {DomainConfig.APPOINTMENT_NAME} para ver detalles_
_Escribe *0* para volver al menú_"""

    CLIENT_NO_APPOINTMENTS = f"""📋 *Mis {DomainConfig.APPOINTMENT_NAME_PLURAL.title()}*

No tienes {DomainConfig.APPOINTMENT_NAME_PLURAL} próximas.

¿Quieres buscar un {DomainConfig.PROFESSIONAL_TITLE_LOWER}?
1️⃣ Sí, buscar
0️⃣ Volver al menú"""

    CLIENT_APPOINTMENTS_LIST_ITEM = """{{number}}. {{status_emoji}} {{date}} {{time}} - {{professional_name}}
   {{status_text}}"""

    # ==========================================
    # CLIENT - APPOINTMENT DETAIL
    # ==========================================

    CLIENT_APPOINTMENT_DETAIL = f"""📋 *{DomainConfig.APPOINTMENT_NAME_UPPER} #{{id}}*

📅 Fecha: *{{date}}*
⏰ Hora: *{{time}}*
👨‍⚕️ {DomainConfig.PROFESSIONAL_TITLE}: *{{professional_name}}*
📞 {{professional_phone}}
📍 Modalidad: *{{modality}}*
⏱️ Duración: *{{duration}} min*
{{reason_display}}

{{status_badge}}

{{options}}

_Escribe *0* para volver_"""

    # Opciones según el estado de la cita
    CLIENT_APPOINTMENT_OPTIONS_PENDING = f"""Opciones disponibles:
1️⃣ Cancelar {DomainConfig.APPOINTMENT_NAME}"""

    CLIENT_APPOINTMENT_OPTIONS_CONFIRMED = f"""Opciones disponibles:
1️⃣ Reprogramar {DomainConfig.APPOINTMENT_NAME}
2️⃣ Cancelar {DomainConfig.APPOINTMENT_NAME}"""

    CLIENT_APPOINTMENT_FINISHED = f"""Esta {DomainConfig.APPOINTMENT_NAME} ya finalizó."""

    CLIENT_APPOINTMENT_ALREADY_CANCELLED = f"""Esta {DomainConfig.APPOINTMENT_NAME} fue cancelada."""

    # ==========================================
    # CLIENT - CANCEL APPOINTMENT
    # ==========================================

    CLIENT_CANCEL_APPOINTMENT_CONFIRM = f"""⚠️ *Cancelar {DomainConfig.APPOINTMENT_NAME_UPPER}*

¿Estás seguro que deseas cancelar?

📅 {{date}} a las {{time}}
👨‍⚕️ {{professional_name}}

{{policy_info}}

1️⃣ Sí, cancelar
0️⃣ No, volver"""

    CLIENT_CANCEL_POLICY_INFO = f"""📋 *Política de cancelación:*
{DomainConfig.CANCELLATION_POLICY}"""

    CLIENT_CANCEL_TOO_LATE = f"""⚠️ *No se puede cancelar*

Tu {DomainConfig.APPOINTMENT_NAME} es en {{hours_until}} horas.

{DomainConfig.CANCELLATION_POLICY}

Por favor contacta directamente al {DomainConfig.PROFESSIONAL_TITLE_LOWER}:
📞 {{professional_phone}}

_Escribe *0* para volver_"""

    CLIENT_CANCEL_REASON = f"""📝 *Motivo de Cancelación* (opcional)

¿Por qué cancelas la {DomainConfig.APPOINTMENT_NAME}?

Esto nos ayuda a mejorar el servicio.

• Escribe el motivo
• O envía *0* para omitir y cancelar directamente"""

    CLIENT_APPOINTMENT_CANCELLED = f"""✅ *{DomainConfig.APPOINTMENT_NAME_UPPER} Cancelada*

{DomainConfig.APPOINTMENT_CANCELLED_MESSAGE}

El {DomainConfig.PROFESSIONAL_TITLE_LOWER} ha sido notificado.

¿Qué deseas hacer?
1️⃣ Ver mis {DomainConfig.APPOINTMENT_NAME_PLURAL}
2️⃣ Buscar nuevo {DomainConfig.PROFESSIONAL_TITLE_LOWER}
0️⃣ Menú principal"""

    # ==========================================
    # CLIENT - RESCHEDULE APPOINTMENT
    # ==========================================

    CLIENT_RESCHEDULE_START = f"""🔄 *Reprogramar {DomainConfig.APPOINTMENT_NAME_UPPER}*

{DomainConfig.APPOINTMENT_NAME_UPPER} actual:
📅 {{old_date}} a las {{old_time}}
👨‍⚕️ {{professional_name}}

Vamos a buscar una nueva fecha y horario.

_Presiona cualquier tecla para continuar_
_Escribe *0* para cancelar_"""

    CLIENT_RESCHEDULE_TOO_LATE = f"""⚠️ *No se puede reprogramar*

Tu {DomainConfig.APPOINTMENT_NAME} es en {{hours_until}} horas.

Solo se puede reprogramar con al menos {{limit}} horas de anticipación.

Por favor contacta al {DomainConfig.PROFESSIONAL_TITLE_LOWER}:
📞 {{professional_phone}}

_Escribe *0* para volver_"""

    CLIENT_RESCHEDULE_SELECT_DATE = f"""📅 *Nueva Fecha*

{DomainConfig.APPOINTMENT_NAME_UPPER} actual: {{old_date}} a las {{old_time}}

Fechas disponibles:

{{available_dates}}

Envía el número de la nueva fecha.

_Escribe *0* para cancelar_"""

    CLIENT_RESCHEDULE_SELECT_TIME = f"""⏰ *Nuevo Horario*

📅 Nueva fecha: {{new_date}}

Horarios disponibles:

{{available_slots}}

Envía el número del nuevo horario.

_Escribe *0* para elegir otra fecha_"""

    CLIENT_RESCHEDULE_CONFIRM = f"""✅ *Confirmar Reprogramación*

*{DomainConfig.APPOINTMENT_NAME_UPPER} Original:*
📅 {{old_date}} a las {{old_time}}

*Nueva {DomainConfig.APPOINTMENT_NAME_UPPER}:*
📅 {{new_date}} a las {{new_time}}
👨‍⚕️ {{professional_name}}

¿Confirmas el cambio?

1️⃣ Sí, confirmar
0️⃣ Cancelar"""

    CLIENT_RESCHEDULE_SUCCESS = f"""🎉 *¡{DomainConfig.APPOINTMENT_NAME_UPPER} Reprogramada!*

Tu {DomainConfig.APPOINTMENT_NAME} ha sido actualizada:

📅 Nueva fecha: *{{new_date}}*
⏰ Nueva hora: *{{new_time}}*
👨‍⚕️ {{professional_name}}

Estado: *Confirmada* ✅

El {DomainConfig.PROFESSIONAL_TITLE_LOWER} ha sido notificado del cambio.

¿Qué deseas hacer?
1️⃣ Ver detalle de la {DomainConfig.APPOINTMENT_NAME}
2️⃣ Ver todas mis {DomainConfig.APPOINTMENT_NAME_PLURAL}
0️⃣ Menú principal"""

    # ==========================================
    # PROFESSIONAL - VIEW APPOINTMENTS
    # ==========================================

    PROF_VIEW_APPOINTMENTS = f"""📅 *Próximas {DomainConfig.APPOINTMENT_NAME_PLURAL.title()}*

{{appointments_list}}

_Envía el número de la {DomainConfig.APPOINTMENT_NAME} para gestionar_
_Escribe *0* para volver al menú_"""

    PROF_NO_APPOINTMENTS = f"""📅 *Próximas {DomainConfig.APPOINTMENT_NAME_PLURAL.title()}*

No tienes {DomainConfig.APPOINTMENT_NAME_PLURAL} próximas agendadas.

_Escribe *0* para volver al menú_"""

    PROF_APPOINTMENTS_LIST_ITEM = """{{number}}. {{status_emoji}} {{date}} {{time}} - {{client_name}}
   {{status_text}}"""

    # ==========================================
    # PROFESSIONAL - APPOINTMENT DETAIL
    # ==========================================

    PROF_APPOINTMENT_DETAIL = f"""📋 *{DomainConfig.APPOINTMENT_NAME_UPPER} #{{id}}*

📅 Fecha: *{{date}}*
⏰ Hora: *{{time}}*
👤 {DomainConfig.PATIENT_LABEL_UPPER}: *{{client_name}}*
📞 {{client_phone}}
📍 Modalidad: *{{modality}}*
⏱️ Duración: *{{duration}} min*
{{reason_display}}

{{status_badge}}

{{options}}

_Escribe *0* para volver_"""

    # Opciones para profesional según estado
    PROF_APPOINTMENT_OPTIONS_PENDING = f"""Opciones:
1️⃣ Confirmar {DomainConfig.APPOINTMENT_NAME}
2️⃣ Rechazar {DomainConfig.APPOINTMENT_NAME}"""

    PROF_APPOINTMENT_OPTIONS_CONFIRMED = f"""Opciones:
1️⃣ Marcar como completada
2️⃣ Cancelar {DomainConfig.APPOINTMENT_NAME}"""

    PROF_APPOINTMENT_OPTIONS_COMPLETED = f"""Esta {DomainConfig.APPOINTMENT_NAME} está completada."""

    # ==========================================
    # PROFESSIONAL - CONFIRM APPOINTMENT
    # ==========================================

    PROF_CONFIRM_APPOINTMENT = f"""✅ *Confirmar {DomainConfig.APPOINTMENT_NAME_UPPER}*

¿Confirmas esta {DomainConfig.APPOINTMENT_NAME}?

📅 {{date}} a las {{time}}
👤 {DomainConfig.PATIENT_LABEL_UPPER}: {{client_name}}
📞 {{client_phone}}

1️⃣ Sí, confirmar
0️⃣ Volver"""

    PROF_APPOINTMENT_CONFIRMED = f"""✅ *{DomainConfig.APPOINTMENT_NAME_UPPER} Confirmada*

La {DomainConfig.APPOINTMENT_NAME} ha sido confirmada exitosamente.

El {DomainConfig.PATIENT_LABEL} recibirá una notificación de confirmación.

_Escribe *0* para volver_"""

    # ==========================================
    # PROFESSIONAL - REJECT/CANCEL APPOINTMENT
    # ==========================================

    PROF_REJECT_APPOINTMENT = f"""❌ *Rechazar {DomainConfig.APPOINTMENT_NAME_UPPER}*

¿Estás seguro que deseas rechazar esta solicitud?

📅 {{date}} a las {{time}}
👤 {DomainConfig.PATIENT_LABEL_UPPER}: {{client_name}}

1️⃣ Sí, rechazar
0️⃣ Volver"""

    PROF_CANCEL_APPOINTMENT = f"""⚠️ *Cancelar {DomainConfig.APPOINTMENT_NAME_UPPER}*

¿Estás seguro que deseas cancelar?

📅 {{date}} a las {{time}}
👤 {DomainConfig.PATIENT_LABEL_UPPER}: {{client_name}}

1️⃣ Sí, cancelar
0️⃣ Volver"""

    PROF_CANCEL_REASON = f"""📝 *Motivo de Cancelación*

¿Por qué cancelas la {DomainConfig.APPOINTMENT_NAME}?

El {DomainConfig.PATIENT_LABEL} recibirá este mensaje.

• Escribe el motivo
• O envía *0* para omitir

_Recomendamos siempre dar una explicación al {DomainConfig.PATIENT_LABEL}_"""

    PROF_APPOINTMENT_CANCELLED = f"""✅ *{DomainConfig.APPOINTMENT_NAME_UPPER} Cancelada*

La {DomainConfig.APPOINTMENT_NAME} ha sido cancelada.

El {DomainConfig.PATIENT_LABEL} ha sido notificado.

_Escribe *0* para volver_"""

    PROF_APPOINTMENT_REJECTED = f"""✅ *Solicitud Rechazada*

La solicitud de {DomainConfig.APPOINTMENT_NAME} ha sido rechazada.

El {DomainConfig.PATIENT_LABEL} ha sido notificado.

_Escribe *0* para volver_"""

    # ==========================================
    # PROFESSIONAL - MARK AS COMPLETED
    # ==========================================

    PROF_MARK_COMPLETED = f"""✅ *Marcar como Completada*

¿Confirmas que esta {DomainConfig.APPOINTMENT_NAME} se realizó?

📅 {{date}} a las {{time}}
👤 {{client_name}}

1️⃣ Sí, completada
0️⃣ Volver"""

    PROF_APPOINTMENT_COMPLETED = f"""✅ *{DomainConfig.APPOINTMENT_NAME_UPPER} Completada*

La {DomainConfig.APPOINTMENT_NAME} ha sido marcada como completada.

_Escribe *0* para volver_"""

    # ==========================================
    # PROFESSIONAL - NO SHOW
    # ==========================================

    PROF_MARK_NO_SHOW = f"""⚠️ *Marcar como No Asistió*

¿El {DomainConfig.PATIENT_LABEL} no asistió a esta {DomainConfig.APPOINTMENT_NAME}?

📅 {{date}} a las {{time}}
👤 {{client_name}}

1️⃣ Sí, no asistió
0️⃣ Volver"""

    PROF_APPOINTMENT_NO_SHOW = f"""✅ *Marcada como No Asistió*

La {DomainConfig.APPOINTMENT_NAME} ha sido marcada como "no asistió".

El {DomainConfig.PATIENT_LABEL} será notificado.

{DomainConfig.NO_SHOW_POLICY}

_Escribe *0* para volver_"""

    # ==========================================
    # HELPER METHODS
    # ==========================================

    @staticmethod
    def format_appointment_status(status: str) -> str:
        """
        Formatear estado de cita con emoji.

        Args:
            status: Código de estado

        Returns:
            Estado formateado con emoji
        """
        statuses = {
            'pendiente_confirmacion': '⏳ Pendiente de confirmación',
            'confirmada': '✅ Confirmada',
            'completada': '✔️ Completada',
            'cancelada_cliente': '❌ Cancelada por cliente',
            'cancelada_profesional': '❌ Cancelada por profesional',
            'no_asistio': '⚠️ No asistió',
            'reagendada': '🔄 Reagendada'
        }
        return statuses.get(status, status)

    @staticmethod
    def format_status_emoji(status: str) -> str:
        """
        Obtener solo el emoji del estado.

        Args:
            status: Código de estado

        Returns:
            Emoji del estado
        """
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
        """
        Formatear modalidad con emoji.

        Args:
            modality: Código de modalidad

        Returns:
            Modalidad formateada
        """
        return DomainConfig.MODALITY_LABELS.get(modality, modality)

    @staticmethod
    def format_appointment_for_list(appointment: dict, number: int) -> str:
        """
        Formatear cita para lista (vista resumida).

        Args:
            appointment: Diccionario con datos de la cita
            number: Número en la lista

        Returns:
            String formateado para mostrar en lista
        """
        from messages_common import common_messages

        date_formatted = common_messages.format_date_natural(
            appointment['appointment_date'])
        time_formatted = common_messages.format_time_24h(
            appointment['start_time'])
        status_emoji = AppointmentMessages.format_status_emoji(
            appointment['status'])
        status_text = AppointmentMessages.format_appointment_status(
            appointment['status'])

        # Decidir si mostrar nombre de cliente o profesional
        if 'client_name' in appointment:
            name = appointment['client_name'] or 'Sin nombre'
        else:
            name = appointment.get('professional_name', 'Sin nombre')

        return f"{number}. {status_emoji} {date_formatted} {time_formatted} - {name}\n   {status_text}"


# Singleton instance
appointment_messages = AppointmentMessages()
