"""
Freelance Handler
=================
Flujo corto de booking para modo profesional único (SINGLE_PROFESSIONAL_MODE=true).

RESPONSABILIDAD:
    Manejar los 3 pasos propios de este modo:
        1. Preguntar fecha           → CLIENT_FREELANCE_BOOK_DATE
        2. Preguntar horario         → CLIENT_FREELANCE_BOOK_TIME
        3. Mostrar filtros + confirmar (1 sola opción)
           → transición a CLIENT_VIEW_DETAIL_WITH_BOOKING
             con el profesional ya cargado en session.temp

    A partir del paso 3 todo se reutiliza del flujo normal:
    ClientHandler.handle_client_view_detail_with_booking → confirmación →
    booking → recordatorios → cancelación → reprogramación.

NO HACE:
    - Filtros de zona, género, prepaga, especialidad
    - Lista de resultados con N profesionales
    - Nada del flujo multi-profesional

ACTIVACIÓN:
    Solo se llega acá desde client_handler.handle_client_main_menu
    cuando Config.SINGLE_PROFESSIONAL_MODE == True y el usuario
    eligió "agendar reunión".

DEPENDENCIAS:
    - src/config/config.py          → Config.SINGLE_PROFESSIONAL_PHONE
    - src/database/database.py      → db.get_professional()
    - src/services/client_service.py → format_professional_detail_with_slots()
    - src/core/validators.py        → parse_date()
    - src/messages/loader.py        → get_msg()
    - src/core/states.py            → ConversationState
"""

import logging
from typing import Optional

from src.core.states import ConversationState, SessionData
from src.messages.loader import get_msg
from src.core.validators import parse_date

logger = logging.getLogger(__name__)


# =========================================================================
# CONSTANTES INTERNAS
# =========================================================================

# Opciones de preferencia de horario que acepta el paso 2
_TIME_OPTIONS = {
    '1': 'mañana',   # hasta las 13hs
    '2': 'tarde',    # desde las 13hs
    '3': None,       # sin preferencia
}

# Labels legibles para mostrar en el mensaje de filtros
_TIME_LABELS = {
    'mañana': 'mañana (hasta las 13hs)',
    'tarde':  'tarde (desde las 13hs)',
    None:     'cualquier horario',
}


# =========================================================================
# PASO 1 — INICIO: preguntar fecha
# =========================================================================

def handle_freelance_start(session: SessionData) -> str:
    """
    Punto de entrada al flujo freelance.
    Llamado desde client_handler cuando SINGLE_PROFESSIONAL_MODE=True
    y el usuario eligió agendar una reunión.

    Transiciona a CLIENT_FREELANCE_BOOK_DATE y muestra CLIENT_ASK_FECHA.
    """
    session.clear_temp()  # ← limpiar cualquier estado anterior
    session.transition_to(ConversationState.CLIENT_FREELANCE_BOOK_DATE)
    return get_msg('CLIENT_ASK_FECHA')


# =========================================================================
# PASO 2 — FECHA: parsear y preguntar horario
# =========================================================================

def handle_freelance_book_date(session: SessionData, message: str) -> str:
    """
    Recibe la fecha elegida por el cliente.
    Valida y parsea con parse_date() (mismo parser que usa el flujo multi-prof).
    Si es válida, guarda en session.temp y avanza a pregunta de horario.

    Args:
        session: Sesión del cliente.
        message: Texto libre del cliente ("mañana", "el viernes", "15/07", etc.)

    Returns:
        Pregunta de horario (CLIENT_ASK_HORA) o mensaje de error (INVALID_DATE).
    """
    # Cancelar → volver al menú
    if message.strip() == '0':
        from src.core.states import ConversationState
        session.clear_temp()
        session.transition_to(ConversationState.CLIENT_MAIN_MENU)
        return get_msg('CLIENT_MAIN_MENU')

    # Parsear fecha con el validador existente
    result = parse_date(message)

    if not result.valid:
        logger.debug(f"[FREELANCE] Fecha inválida: '{message}' — {result.error}")
        return (
            f"{get_msg('INVALID_DATE')}\n\n"
            "_Escribí *0* para cancelar_"
        )

    # Guardar fecha parseada en sesión
    session.set_temp('search_date',     result.value)   # 'YYYY-MM-DD'
    session.set_temp('search_date_str', result.display) # 'lunes 15 de julio'

    logger.info(f"[FREELANCE] Fecha aceptada: {result.value} ({result.display})")

    # Avanzar a pregunta de horario
    session.transition_to(ConversationState.CLIENT_FREELANCE_BOOK_TIME)
    return get_msg('CLIENT_ASK_HORA')


# =========================================================================
# PASO 3 — HORARIO: mostrar filtros activos + confirmar búsqueda
# =========================================================================

def handle_freelance_book_time(session: SessionData, message: str) -> str:
    """
    Recibe la preferencia de horario (1/2/3).
    Construye el mensaje de "filtros activos" con vitrina del sistema.
    Opción 1 → lanza la búsqueda y transiciona a CLIENT_VIEW_DETAIL_WITH_BOOKING.
    Opción 0 → vuelve a preguntar fecha.

    Args:
        session: Sesión del cliente.
        message: '1' (mañana) | '2' (tarde) | '3' (sin preferencia) | '0' (volver)

    Returns:
        Mensaje de filtros activos, o directamente la pantalla de detalle
        si la búsqueda devuelve resultados.
    """
    # Volver → preguntar fecha de nuevo
    if message.strip() == '0':
        session.transition_to(ConversationState.CLIENT_FREELANCE_BOOK_DATE)
        return get_msg('CLIENT_ASK_FECHA')

    # Validar opción de horario
    if message.strip() not in _TIME_OPTIONS:
        return (
            f"{get_msg('INVALID_OPTION')}\n\n"
            f"{get_msg('CLIENT_ASK_HORA')}"
        )

    time_preference = _TIME_OPTIONS[message.strip()]  # 'mañana' | 'tarde' | None
    session.set_temp('time_preference', time_preference)

    date_str     = session.get_temp('search_date')
    date_display = session.get_temp('search_date_str', date_str)
    time_label   = _TIME_LABELS.get(time_preference, 'cualquier horario')

    logger.info(
        f"[FREELANCE] Búsqueda → fecha={date_str}, horario={time_preference}"
    )

    # Construir bloque de filtros activos (vitrina del sistema)
    filters_preview = _build_filters_preview(date_display, time_label)

    # Mostrar pantalla informativa con 1 sola opción (confirmar búsqueda)
    tpl = get_msg('CLIENT_FREELANCE_FILTERS_INFO')
    if tpl:
        return tpl.format(
            date_label=date_display,
            time_label=time_label,
            filters_preview=filters_preview,
        )

    # Fallback si el tono no tiene CLIENT_FREELANCE_FILTERS_INFO
    return _fallback_filters_msg(date_display, time_label, filters_preview)


def handle_freelance_confirm_search(session: SessionData, message: str) -> str:
    """
    El cliente respondió al mensaje de filtros activos.
    '1' → lanzar búsqueda y pasar a detalle del profesional.
    '0' → volver a preguntar fecha (reiniciar el flujo corto).

    Se llama desde bot_controller cuando el estado es
    CLIENT_FREELANCE_BOOK_TIME y ya pasó la pantalla de filtros.
    En la práctica este es el "segundo mensaje" en ese estado.

    NOTA: La pantalla de filtros y esta confirmación comparten el estado
    CLIENT_FREELANCE_BOOK_TIME para no necesitar un cuarto estado.
    Se distinguen por session.get_temp('freelance_filters_shown').
    """
    if message.strip() == '0':
        # Volver a fecha
        session.set_temp('freelance_filters_shown', False)
        session.transition_to(ConversationState.CLIENT_FREELANCE_BOOK_DATE)
        return get_msg('CLIENT_ASK_FECHA')

    if message.strip() != '1':
        # No entendió — repetir opciones
        return (
            "Respondé *1* para ver los horarios disponibles "
            "o *0* para cambiar la fecha."
        )

    # Lanzar búsqueda con el profesional único pre-cargado
    return _load_professional_and_show_detail(session)


# =========================================================================
# HELPERS PRIVADOS
# =========================================================================

def _build_filters_preview(date_label: str, time_label: str) -> str:
    """
    Construye el bloque de texto con los filtros activos para mostrar
    como vitrina. Usa las constantes de línea del tono si existen,
    o construye strings directamente como fallback.

    Returns:
        String multilínea listo para interpolar en CLIENT_FREELANCE_FILTERS_INFO.
    """
    from src.config.config import Config
    from src.database.database import db

    lines = []

    # Filtro de fecha
    line_date = get_msg('CLIENT_FREELANCE_FILTER_LINE_DATE')
    if line_date:
        lines.append(line_date.format(date_label=date_label))
    else:
        lines.append(f"✅ Fecha: *{date_label}*")

    # Filtro de horario
    line_time = get_msg('CLIENT_FREELANCE_FILTER_LINE_TIME')
    if line_time:
        lines.append(line_time.format(time_label=time_label))
    else:
        lines.append(f"✅ Horario: *{time_label}*")

    # Filtro de modalidad — detectar desde el perfil del profesional
    prof_phone = getattr(Config, 'SINGLE_PROFESSIONAL_PHONE', '')
    if prof_phone:
        prof = db.get_professional(prof_phone)
        if prof:
            online    = prof.get('online_sessions', False)
            presencial = prof.get('presencial', True)  # default True si no está el campo

            if online and presencial:
                line = get_msg('CLIENT_FREELANCE_FILTER_LINE_BOTH')
                lines.append(line or "✅ Modalidad: *online y presencial*")
            elif online:
                line = get_msg('CLIENT_FREELANCE_FILTER_LINE_ONLINE')
                lines.append(line or "✅ Modalidad: *online* (Google Meet)")
            else:
                line = get_msg('CLIENT_FREELANCE_FILTER_LINE_PRESENCIAL')
                lines.append(line or "✅ Modalidad: *presencial*")

    # Filtros del sistema disponibles (solo informativos, no activos)
    lines.append("")
    lines.append("_Otros filtros disponibles en el sistema: zona, género,_")
    lines.append("_especialidad, prepaga — se activan según el tipo de servicio._")

    return "\n".join(lines)


def _load_professional_and_show_detail(session: SessionData) -> str:
    """
    Carga el profesional configurado en SINGLE_PROFESSIONAL_PHONE,
    ejecuta la búsqueda de slots para la fecha/horario elegidos,
    y transiciona a CLIENT_VIEW_DETAIL_WITH_BOOKING.

    Si no hay slots disponibles, informa y vuelve a preguntar fecha.

    Returns:
        Pantalla de detalle del profesional con slots, o mensaje de sin resultados.
    """
    from src.config.config import Config
    from src.database.database import db
    from src.services.client_service import client_service
    from src.core.states import ConversationState

    prof_phone = getattr(Config, 'SINGLE_PROFESSIONAL_PHONE', '').strip()

    if not prof_phone:
        # Config inválida — no debería llegar acá si config_validator corrió
        logger.error("[FREELANCE] SINGLE_PROFESSIONAL_PHONE no configurado")
        return get_msg('ERROR_GENERIC')

    date_str        = session.get_temp('search_date')
    time_preference = session.get_temp('time_preference')

    # Buscar profesional con slots para esa fecha
    # Reutiliza search_professionals() con el teléfono como filtro de nombre/phone
    results = client_service.search_professionals(
        date_str=date_str,
        time_preference=time_preference,
        professional_phone_filter=prof_phone,   # ← parámetro nuevo, ver PATCH client_service
        limit=1,
    )

    if not results:
        logger.info(
            f"[FREELANCE] Sin slots para {date_str} "
            f"(horario: {time_preference})"
        )
        session.transition_to(ConversationState.CLIENT_FREELANCE_BOOK_DATE)
        return (
            f"{get_msg('CLIENT_NO_RESULTS')}\n\n"
            "_Escribí una fecha diferente o *0* para volver al menú._"
        )

    professional = results[0]
    session.set_temp('selected_professional', professional)
    session.set_temp('search_results',        results)

    session.transition_to(ConversationState.CLIENT_VIEW_DETAIL_WITH_BOOKING)

    # Reutilizar el formatter existente — sin cambios
    return client_service.format_professional_detail_with_slots(
        professional=professional,
        date_str=date_str,
        time_preference=time_preference,
    )


def _fallback_filters_msg(
    date_label: str,
    time_label: str,
    filters_preview: str,
) -> str:
    """
    Mensaje de filtros cuando el tono no tiene CLIENT_FREELANCE_FILTERS_INFO.
    Usado como red de seguridad para tonos que no incluyen la constante.
    """
    return (
        f"📅 *{date_label}* · 🕐 *{time_label}*\n\n"
        f"{filters_preview}\n\n"
        f"1️⃣ Ver horarios disponibles\n"
        f"0️⃣ Cambiar fecha u horario"
    )
