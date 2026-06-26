"""
Bot Controller v3.1 - Con Sistema de Intenciones NLU
======================================================
Orquestador principal del bot con detección inteligente de intenciones.

NUEVO EN v3.1:
✅ Detección automática de intenciones (NLU)
✅ Extracción de entidades (fecha, zona, horario, especialidad)
✅ Shortcuts inteligentes (omitir menú cuando sea posible)
✅ Flujo adaptativo según lo que el usuario menciona

CAMBIOS DE v3.0:
- ❌ Eliminado: ROLE_SELECTION (ya no preguntamos "¿Eres cliente o profesional?")
- ❌ Eliminado: Flujo de registro de profesionales (se cargan manualmente)
- ❌ Eliminado: Sistema de claves de acceso
- ✅ Simplificado: Solo flujo de CLIENTES
- ✅ Automático: Reconocimiento inteligente de usuarios

Este archivo es el cerebro del bot:
- Recibe mensajes de WhatsApp
- Identifica usuarios automáticamente
- Detecta intenciones con NLU ⭐ NUEVO
- Extrae entidades del mensaje ⭐ NUEVO
- Hace shortcuts cuando es posible ⭐ NUEVO
- Maneja comandos globales
- Delega a handlers específicos

Ejemplos de uso:
- "necesito psicólogo mañana" → Detecta intent + entidades → Busca directamente
- "ver mis turnos" → Detecta intent → Muestra citas directamente
- "hola" → Sin intent específico → Muestra menú tradicional
"""

from src.integrations.reminder import reminder_integration_service
from src.bot.professional_handler import ProfessionalHandler
from src.bot.client_handler import ClientHandler
from src.bot import freelance_handler
from src.config.filter_config import FeatureFlags
from src.services.user_service import user_service
from src.services.intent_detector import intent_detector, Intent
from src.integrations.ml.hybrid_intent_detector import hybrid_intent_detector
from src.integrations.conversation_context_service.event_store import event_store
from src.integrations.waitlist.slot_offer_handler import should_handle_as_slot_offer, handle_slot_offer_response 
from src.services.conversation_logger import conversation_logger
from src.messages.messages_common import common_messages
from src.messages.messages_client import client_messages
from src.messages.messages_professional import professional_messages
from src.core.states import (
    ConversationState,
    UserRole,
    session_manager,
    SessionData
)
from src.core.conversation_context import context_manager
from src.bot.reminder_handler import should_handle_as_reminder, handle_reminder_response
import os
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Agregar raíz del proyecto al path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class BotController:
    """
    Controlador principal del bot v3.1 con NLU.
    
    Mejoras sobre v3.0:
    - Detecta intenciones en lenguaje natural
    - Extrae entidades automáticamente
    - Hace shortcuts cuando es posible
    - Flujo más corto y natural
    """

    def __init__(self):
        """Inicializar controlador del bot."""
        self.client_handler = ClientHandler()
        self.professional_handler = ProfessionalHandler()

    def process_message(self, phone_number: str, message: str) -> str:
        """
        Procesa mensaje entrante y retorna respuesta.
        Wrapper que garantiza que la sesión siempre se persiste en Redis.
        """
        try:
            response = self._process_message(phone_number, message)
            return response
        finally:
            # Guardar la sesión que realmente usó _process_message
            try:
                session = session_manager.get_session(phone_number)
                session_manager.save_session(session)
            except Exception as e:
                print(f"[SESSION] ⚠️ Error guardando sesión: {e}")

    def _process_message(self, phone_number: str, message: str) -> str:
        """
        Lógica interna de procesamiento de mensajes.
        Llamado por process_message() que se encarga del save de sesión.

        FLUJO v3.1:
        1. Identificar usuario automáticamente
        2. Detectar intención del mensaje (NLU) ⭐ NUEVO
        3. Intentar shortcut si es posible ⭐ NUEVO
        4. Si no, seguir flujo tradicional

        Args:
            phone_number: Número de WhatsApp del usuario
            message: Mensaje de texto del usuario

        Returns:
            Respuesta del bot
        """
        # ==========================================
        # 1. IDENTIFICACIÓN INTELIGENTE DE USUARIO
        # ==========================================
        user_info = user_service.identify_user(phone_number)

        # Log de acción (analytics)
        if FeatureFlags.ANALYTICS_TRACKING:
            user_service.log_action(
                phone=phone_number,
                action_type='message',
                details={'message_length': len(message)},
                session_id=phone_number
            )

        # ==========================================
        # 2. OBTENER O CREAR SESIÓN
        # ==========================================
        session = session_manager.get_session(phone_number)
        # Contexto de conversación (para NLU avanzado)
        conv_context = context_manager.get_context(phone_number)

        # Inferir contexto entre sesiones si la sesión es nueva
        # Permite orientar el routing sin depender del estado de Redis
        if session.state.value in ('start', 'client_main_menu'):
            from src.integrations.conversation_context_service import context_service
            _recent_ctx = context_service.get_recent_context(phone_number)
            if _recent_ctx['pending_reminder']:
                session.transition_to(ConversationState.AWAITING_REMINDER_RESPONSE)
                print(f"[CTX] Sesión nueva con reminder pendiente → AWAITING_REMINDER_RESPONSE")
            elif _recent_ctx.get('pending_slot_offer'):
                session.transition_to(ConversationState.AWAITING_SLOT_OFFER)
                print(f"[CTX] Sesión nueva con oferta pending → AWAITING_SLOT_OFFER")

        # ── PRIORIDAD MÁXIMA: respuesta a recordatorio ──────────────────────
        # Va ANTES del NLU y de cualquier bypass de estado.
        # should_handle_as_reminder() consulta BD directamente — no depende
        # del estado de sesión ni de Redis.
        if should_handle_as_reminder(session, message):
            return handle_reminder_response(session, message)
        
        # Segunda prioridad: respuesta a oferta de adelantamiento (waitlist)
        # Consulta BD directamente — no depende del estado de sesión.
        if should_handle_as_slot_offer(session, message):
            response = handle_slot_offer_response(session, message)
            if response is not None:
                return response
            # response == None significa que la oferta ya no existe

        # Limpiar mensaje
        message = message.strip()
        message_lower = message.lower()

        # ==========================================
        # 3. SUPER COMANDO: "HOLA" CON NLU ⭐
        # ==========================================
        if message_lower in ['hola', 'hello', 'hi', 'hey', 'buenos días', 'buenas tardes', 'buenas noches']:
            
            # ⭐ NUEVO: Detectar si "hola" viene con intención adicional
            # Ejemplo: "hola, necesito psicólogo mañana"
            intent_result = intent_detector.detect(message, context={
                'role': session.role,
                'user_info': user_info
            })
            
            # Si solo es saludo sin intención clara, resetear y mostrar menú
            if intent_result['intent'] == Intent.GREETING:
                session.reset()
                conv_context.reset()
                
                # Profesional registrado
                if user_info['user_type'] == 'professional':
                    session.set_role(UserRole.PROFESSIONAL)
                    session.transition_to(ConversationState.PROF_MAIN_MENU)
                    greeting = f"¡Hola Dr/Dra. {user_info['name']}! 👋\n\n" if user_info['name'] else "¡Hola! 👋\n\n"
                    return greeting + professional_messages.PROF_MAIN_MENU
                
                # Cliente (default)
                session.set_role(UserRole.CLIENT)
                session.transition_to(ConversationState.CLIENT_MAIN_MENU)
                user_info['phone_number'] = phone_number
                return user_service.generate_welcome_message(user_info)
            
            # ⭐ Si hay intención adicional, procesarla abajo

        # ==========================================
        # 4. DETECCIÓN DE INTENCIÓN (NLU) ⭐ NUEVO
        # ==========================================
        
        # Interceptar '0' antes del NLU en estados donde el ML lo confunde
        # con info_center u otras intenciones
        msg_stripped = message.strip()

        if msg_stripped == '0':
            # CLIENT_MAIN_MENU — repetir menú
            if session.state == ConversationState.CLIENT_MAIN_MENU:
                return user_service.generate_welcome_message({
                    'user_type': 'new', 'name': None, 'is_registered': False,
                    'has_pending_appointments': False, 'pending_appointments': [],
                    'profile': None, 'phone_number': session.phone_number
                })
            # CLIENT_VIEW_APPOINTMENTS — volver al menú principal
            elif session.state == ConversationState.CLIENT_VIEW_APPOINTMENTS:
                session.clear_temp()
                session.transition_to(ConversationState.CLIENT_MAIN_MENU)
                return user_service.generate_welcome_message({
                    'user_type': 'new', 'name': None, 'is_registered': False,
                    'has_pending_appointments': False, 'pending_appointments': [],
                    'profile': None, 'phone_number': session.phone_number
                })
            # CLIENT_APPOINTMENT_DETAIL — volver a la lista de citas
            elif session.state == ConversationState.CLIENT_APPOINTMENT_DETAIL:
                session.clear_temp()
                session.transition_to(ConversationState.CLIENT_VIEW_APPOINTMENTS)
                return self.client_handler.handle_client_view_appointments(session, '')

        # Interceptar texto natural en CLIENT_APPOINTMENT_DETAIL antes del NLU
        # "reprogramar", "cancelar", "1", "2" — el NLU los confunde
        if session.state == ConversationState.CLIENT_APPOINTMENT_DETAIL:
            _REPROG = {'reprogramar', 'quiero reprogramar', 'cambiar fecha',
                       'cambiar turno', 'mover turno', 'mover fecha'}
            _CANCEL = {'cancelar', 'quiero cancelar', 'no puedo ir',
                       'no voy', 'borrar turno', 'eliminar turno'}
            msg_apt = msg_stripped.lower()
            if msg_stripped in ('1',) or msg_apt in _REPROG:
                handler = self.get_handler_for_state(session.state)
                return handler(session, '1')
            if msg_stripped in ('2',) or msg_apt in _CANCEL:
                handler = self.get_handler_for_state(session.state)
                return handler(session, '2')

        # Interceptar números en CLIENT_BOOKING_CONFIRMED antes del NLU
        if (session.state == ConversationState.CLIENT_BOOKING_CONFIRMED
                and msg_stripped in ('1', '2', '0')):
            handler = self.get_handler_for_state(session.state)
            return handler(session, msg_stripped)

        # Interceptar confirmaciones y números en CLIENT_SHOW_RESULTS antes del NLU
        # "si", "dale", "1", "2" → el NLU los confunde con unknown/agenda_confirm/greeting
        if session.state == ConversationState.CLIENT_SHOW_RESULTS:
            results = session.get_temp('search_results', [])

            # Sin resultados → sesión vieja o corrupta, limpiar y dejar pasar al NLU
            if not results and not msg_stripped.isdigit():
                session.clear_temp()
                session.transition_to(ConversationState.START)
                # No retornamos — el NLU procesa el mensaje como nueva búsqueda

            else:
                _CONFIRM_SHOW = {
                    'si', 'sí', 'dale', 'ok', 'bueno', 'va', 'perfecto',
                    'ese', 'esa', 'ese mismo', 'esa misma', 'ese profesional',
                }
                msg_lower_show = msg_stripped.lower()

                # Número directo → pasar al handler
                if msg_stripped.isdigit():
                    handler = self.get_handler_for_state(session.state)
                    return handler(session, msg_stripped)

                # Confirmación corta con un solo resultado → seleccionar automáticamente
                if msg_lower_show in _CONFIRM_SHOW and len(results) == 1:
                    handler = self.get_handler_for_state(session.state)
                    return handler(session, '1')

        # Pre-convertir input natural en CLIENT_FILTER_INPUT antes del NLU
        # para evitar que intenciones como view_tomorrow o greeting hagan shortcut
        # cuando el usuario está respondiendo a un filtro específico.
        if session.state == ConversationState.CLIENT_FILTER_INPUT:
            current_filter = session.get_temp('current_filter_type')
            msg_lower_pre = msg_stripped.lower()

            # ── Filtro de horario: acepta texto de franja ───────────────────
            if current_filter == 'time':
                _TIME_MAP = {
                    'mañana': '1', 'manana': '1', 'por la mañana': '1',
                    'a la mañana': '1', 'de mañana': '1',
                    'tarde': '2', 'por la tarde': '2',
                    'a la tarde': '2', 'de tarde': '2',
                    'noche': '3', 'por la noche': '3',
                    'a la noche': '3', 'de noche': '3',
                }
                for kw, num in _TIME_MAP.items():
                    if kw in msg_lower_pre:
                        print(f"[FILTER] ⏰ Horario natural '{msg_stripped}' → opción {num}")
                        msg_stripped = num
                        message = num
                        break

            # Helper de normalización compartido por todos los filtros de texto
            import unicodedata as _ud
            def _fnorm(s):
                nfd = _ud.normalize('NFD', s)
                return ''.join(c for c in nfd
                               if _ud.category(c) != 'Mn').lower().strip()
            msg_norm_f = _fnorm(msg_lower_pre)

            # ── Filtro de especialidad: acepta texto fuzzy ──────────────────
            if current_filter == 'specialty':
                _SPECIALTY_MAP = {
                    'medico general': '1', 'medico': '1', 'clinico': '1',
                    'general': '1', 'medicina general': '1', 'clinica': '1',
                    'dentista': '2', 'odontologo': '2', 'odontologia': '2',
                    'dental': '2', 'dientes': '2', 'muela': '2',
                    'psicologo': '3', 'psicologia': '3', 'psico': '3',
                    'terapia': '3', 'terapeuta': '3', 'psiquiatra': '3',
                    'kinesiologo': '4', 'kinesiologia': '4', 'kinesio': '4',
                    'fisioterapeuta': '4', 'fisioterapia': '4', 'fisiatra': '4',
                    'rehabilitacion': '4',
                    'nutricionista': '5', 'nutricion': '5', 'nutri': '5',
                    'dietista': '5', 'dietologo': '5', 'dieta': '5',
                    'otro': '6', 'otros': '6', 'otra': '6', 'otras': '6',
                    'no se': '6', 'no importa': '6', 'cualquiera': '6',
                }
                for kw, num in _SPECIALTY_MAP.items():
                    if kw in msg_norm_f or msg_norm_f in kw:
                        print(f"[FILTER] 🩺 Especialidad '{msg_stripped}' → opción {num}")
                        msg_stripped = num
                        message = num
                        break

            # ── Filtro de zona: acepta nombre de zona ───────────────────────
            elif current_filter == 'zone':
                _ZONE_MAP = {
                    'norte': '1', 'zona norte': '1', 'del norte': '1',
                    'sur': '2', 'zona sur': '2', 'del sur': '2',
                    'este': '3', 'zona este': '3', 'del este': '3',
                    'oeste': '4', 'zona oeste': '4', 'del oeste': '4',
                    'cualquiera': '5', 'no importa': '5', 'indistinto': '5',
                    'da igual': '5', 'no aplica': '5', 'sin zona': '5',
                    'todas': '5', 'todo': '5',
                }
                for kw, num in _ZONE_MAP.items():
                    if kw in msg_norm_f:
                        print(f"[FILTER] 📍 Zona '{msg_stripped}' → opción {num}")
                        msg_stripped = num
                        message = num
                        break

            # ── Filtro de prepaga: confirmación / negación / indiferente ────
            elif current_filter == 'prepaga':
                _SI  = {'si', 'con prepaga', 'obra social', 'tengo prepaga',
                        'si tengo', 'acepta prepaga', 'con cobertura', 'con os'}
                _NO  = {'no', 'no tengo', 'sin prepaga', 'particular',
                        'efectivo', 'de bolsillo', 'privado', 'sin cobertura',
                        'no acepta prepaga', 'pago particular'}
                _ANY = {'cualquiera', 'no importa', 'da igual', 'indiferente',
                        'indistinto', 'no aplica', 'ambos', 'me da igual',
                        'con o sin', 'lo que sea'}
                from src.core.normalizers import normalize_yes_no_any
                resultado = normalize_yes_no_any(message)
                if resultado == '1': msg_stripped = '1'
                elif resultado == '2': msg_stripped = '2'
                elif resultado == '3': msg_stripped = '3'

            # ── Filtro de género: acepta texto natural ──────────────────────
            elif current_filter == 'gender':
                from src.core.normalizers import normalize_gender
                genero = normalize_gender(message)
                if genero == 'm':   msg_stripped = '1'
                elif genero == 'f': msg_stripped = '2'
                elif genero == 'any': msg_stripped = '3'

        # Intentar NLU en estados donde tiene sentido
        # Expandido para incluir más estados donde el usuario puede dar comandos naturales
        nlu_enabled_states = [
            ConversationState.START,
            ConversationState.CLIENT_MAIN_MENU,
            ConversationState.CLIENT_NEW_USER_MENU,
            ConversationState.CLIENT_MULTIFILTER_MENU,
            # CLIENT_SHOW_RESULTS excluido: solo números o nombres — el NLU confunde '2','3' como intenciones
            ConversationState.CLIENT_FILTER_INPUT,
            ConversationState.CLIENT_VIEW_APPOINTMENTS,
            # CLIENT_APPOINTMENT_DETAIL excluido — solo acepta 1/2/0 + texto natural
            # que se intercepta antes del NLU
            # CLIENT_BOOKING_CONFIRMED excluido: solo números 1/2/0 — NLU confunde con unknown
            ConversationState.PROF_MAIN_MENU,
            ConversationState.PROF_AGENDA_IMPORT_REVIEW,    
            ConversationState.CLIENT_FREELANCE_BOOK_DATE, # flujo freelance
        ]
        
        if session.state in nlu_enabled_states:
            # Números solos → siempre son selección de menú, nunca intención semántica.
            # El ML no tiene contexto para saber qué significa "2" en cada estado,
            # así que los pasamos directo al handler sin pasar por NLU.
            if msg_stripped.isdigit():
                handler = self.get_handler_for_state(session.state)
                if handler:
                    return handler(session, message)

            # Prefixear mensaje con estado para intenciones contextuales
            PREFIXED_STATES = {ConversationState.PROF_AGENDA_IMPORT_REVIEW}
            text_for_model = (
                f"[{session.state.value.upper()}] {message}"
                if session.state in PREFIXED_STATES
                else message
            )

            intent_result = hybrid_intent_detector.detect(text_for_model, context={
                'role': session.role,
                'state': session.state,
                'user_info': user_info,
                'conversation_history': conv_context.get_history_text()
            })
            
            # Logging mejorado con información del sistema híbrido
            print(f"[NLU] Intent: {intent_result['intent'].value} (conf: {intent_result['confidence']:.2f})")
            print(f"[NLU] Source: {intent_result['source']} (ML: {intent_result['ml_confidence']:.2f}, Rules: {intent_result['rules_confidence']:.2f})")
            if intent_result['entities']:
                print(f"[NLU] Entidades: {intent_result['entities']}")

            # ==========================================
            # 4.1 INTERCEPCIÓN DE CONSULTAS FUERA DE ALCANCE
            # Si el ML detecta unknown con alta confianza, es una pregunta
            # legítima que el sistema no puede responder (precio, dirección, etc).
            # Respondemos amigablemente en lugar de llegar al handler y
            # devolver "opción inválida".
            #
            # Umbral 0.7: mismo que usan los shortcuts de otros intents.
            # Solo aplica en estados de menú (no en flujos de ingreso de datos
            # donde el usuario podría estar escribiendo texto libre válido).
            # ==========================================
            UNKNOWN_INTERCEPT_STATES = {
                # Solo interceptar en START donde el usuario escribe libremente
                # En los menús (MAIN_MENU, etc.) los números son opciones válidas
                # y no deben ser interceptados como "unknown"
                ConversationState.START,
                ConversationState.CLIENT_SHOW_RESULTS,
                ConversationState.PROF_MAIN_MENU,
            }

            if (
                intent_result['intent'] == Intent.UNKNOWN
                and intent_result['confidence'] >= 0.7
                and session.state in UNKNOWN_INTERCEPT_STATES
            ):
                print(f"[NLU] ⚠️ Consulta fuera de alcance interceptada (conf: {intent_result['confidence']:.2f})")
                welcome = user_service.generate_welcome_message({
                    'user_type': user_info.get('user_type', 'new'),
                    'name': user_info.get('name'),
                    'is_registered': user_info.get('is_registered', False),
                    'has_pending_appointments': False,
                    'pending_appointments': [],
                    'profile': None,
                    'phone_number': phone_number
                })
                return common_messages.UNKNOWN_QUERY

            # Logging automático para dataset de ML
            conversation_logger.log_message(
                phone=phone_number,
                message=message,
                detected_intent=intent_result['intent'].value,
                detected_entities=intent_result['entities'],
                confidence=intent_result['confidence'],
                shortcut_used=intent_result.get('can_shortcut', False),
                session_state=session.state.value,
                user_role=session.role.value if session.role else None,
                context_data={
                    'has_accumulated_entities': len(conv_context.get_entities()) > 0,
                    'conversation_turns': len(conv_context.conversation_history),
                    'detection_source': intent_result.get('source', 'unknown'),
                    'ml_confidence': intent_result.get('ml_confidence', 0.0),
                    'rules_confidence': intent_result.get('rules_confidence', 0.0),
                }
            )

            # Persistir evento en BD para inferencia de contexto entre sesiones
            event_store.record(
                client_phone = phone_number,
                session_id   = phone_number,
                event_type   = 'message',
                intent       = intent_result['intent'].value,
                confidence   = intent_result['confidence'],
                state_before = session.state.value,
            )

            # Marcar para revisión si confianza baja
            if intent_result['confidence'] < 0.5:
                conversation_logger.mark_for_review(
                    phone=phone_number,
                    message=message,
                    detected_intent=intent_result['intent'].value,
                    priority='high'
                )
            
            # Agregar al historial
            conv_context.add_message(
                message=message,
                intent=intent_result['intent'].value,
                entities=intent_result['entities']
            )

            # CRÍTICO: Acumular entidades si hay alguna detectada
            # Esto funciona incluso si el intent es "unknown" pero detectó entidades
            if intent_result['entities']:
                print(f"[NLU] Entidades detectadas: {intent_result['entities']}")
                
                # No acumular entidades para intents que no son búsqueda directa
                NON_SEARCH_INTENTS = {
                    Intent.INFO_CENTER,
                    Intent.VIEW_MY_APPOINTMENTS,
                    Intent.CANCEL_APPOINTMENT,
                    Intent.GREETING,
                    Intent.BOOK_FOR_THIRD_PARTY,  # ← el shortcut setea booking_for y resetea contexto
                }
                if intent_result['intent'] in NON_SEARCH_INTENTS:
                    pass  # ignorar entidades, dejar que el shortcut maneje el intent
                else:
                    tiene_entidades_busqueda = any(k in intent_result['entities'] for k in
                                                ['fecha', 'especialidad', 'horario', 'zona', 'genero', 'prepaga', 'professional_name'])

                    if tiene_entidades_busqueda or session.state == ConversationState.CLIENT_MULTIFILTER_MENU:
                        # Si es una búsqueda nueva desde START o CLIENT_MAIN_MENU,
                        # resetear el contexto para no arrastrar entidades de búsquedas anteriores
                        # (ej: professional_name o horario de una búsqueda previa)
                        if (intent_result['intent'] == Intent.SEARCH_PROFESSIONAL
                                and session.state in (ConversationState.START, ConversationState.CLIENT_MAIN_MENU)):
                            conv_context.reset()
                            print("[CONTEXT] Contexto reseteado — nueva búsqueda desde menú")

                        conv_context.update_entities(intent_result['entities'], merge=True)
                        accumulated = conv_context.get_entities()
                        print(f"[CONTEXT] Entidades totales acumuladas: {accumulated}")

                        if self._can_execute_search(accumulated):
                            print(f"[CONTEXT] ✅ Suficiente información, ejecutando búsqueda")
                            return self._execute_smart_search(session, accumulated)
                        else:
                            print(f"[CONTEXT] ⚠️ Falta información crítica")
                            missing = self._get_missing_required_entities(accumulated)
                            return self._ask_for_missing_entity(session, accumulated, missing)
                        
            # Conversión de input natural (solo en CLIENT_FILTER_INPUT)
            if session.state == ConversationState.CLIENT_FILTER_INPUT:
                converted_message = self._convert_natural_input(
                    message, intent_result, session
                )
                if converted_message != message:
                    print(f"[NLU] Input convertido: '{message}' → '{converted_message}'")
                    message = converted_message
                    message_lower = message.lower()
            # ── Intenciones de importación de agenda ──────────────────────
            INTENT_TO_MESSAGE = {
                Intent.AGENDA_VIEW_READY:      '2',
                Intent.AGENDA_VIEW_OVERLAPS:   '3',
                Intent.AGENDA_VIEW_EXISTING:   '4',
                Intent.AGENDA_VIEW_ERRORS:     '5',
                Intent.AGENDA_CONFIRM_UPLOAD:  '1',
                Intent.AGENDA_CANCEL_UPLOAD:   '0',
            }
            if (session.state == ConversationState.PROF_AGENDA_IMPORT_REVIEW
                    and intent_result['intent'] in INTENT_TO_MESSAGE
                    and intent_result['confidence'] >= 0.7):
                message = INTENT_TO_MESSAGE[intent_result['intent']]
                message_lower = message

            # Para otros intents (no búsqueda), intentar shortcut
            if intent_result['intent'].value not in ['search_professional', 'unknown'] and intent_result['confidence'] >= 0.7:
                conv_context.set_intent(intent_result['intent'].value)
                shortcut_response = self._try_intent_shortcut(
                    session, intent_result, user_info
                )
                if shortcut_response:
                    return shortcut_response
        # (Reminder check movido a sección 4.2 — antes del bypass de números)

        # ==========================================
        # 5. COMANDOS GLOBALES
        # ==========================================

        # Comando global 'volver' — excluir estados donde el handler lo maneja distinto
        _VOLVER_EXCLUIR = {
            ConversationState.CLIENT_CONFIRM_BOOKING,      # volver → horarios
            ConversationState.CLIENT_VIEW_DETAIL_WITH_BOOKING,  # volver → resultados
        }
        if message_lower in ['menu', 'menú', 'volver'] and session.state not in _VOLVER_EXCLUIR:
            return self.handle_return_to_menu(session)

        # Comando global 'cancelar' — excluir estados donde el handler lo maneja como confirmación
        _CANCELAR_EXCLUIR = {
            ConversationState.CLIENT_CANCEL_REASON,     # cancelar = confirmar la cancelación
            ConversationState.CLIENT_CONFIRM_BOOKING,   # cancelar = volver
        }
        if message_lower in ['cancelar', 'cancel', 'salir'] and session.state not in _CANCELAR_EXCLUIR:
            return self.handle_cancel(session)

        if message_lower in ['ayuda', 'help', '?']:
            return common_messages.HELP_MESSAGE
        
        # ==========================================
        # Comandos secretos — solo en development
        if os.getenv('FLASK_ENV', 'development') != 'production':
            if message_lower in ['enviar recordatorio', 'enviar recordatorios']:
                result = reminder_integration_service.trigger_now()
                return result.get('message', '❌ Error ejecutando recordatorios.')

            if message_lower in ['scheduler status', 'estado scheduler']:
                from src.integrations.scheduler.engine import scheduler_engine
                status = scheduler_engine.get_status()
                lines = [f"🔄 Scheduler: {'✅ corriendo' if status['running'] else '❌ detenido'}"]
                for jid, jinfo in status.get('jobs', {}).items():
                    next_run = jinfo.get('next_run', 'N/A')
                    lines.append(f"  • {jid}: próximo {next_run}")
                return "\n".join(lines)
        # ==========================================

        # ==========================================
        # 6. ENRUTAR A HANDLER SEGÚN ESTADO
        # ==========================================

        handler = self.get_handler_for_state(session.state)

        try:
            response = handler(session, message)
            # Si el handler devuelve None, el estado fue reseteado a START
            # Repasar el mensaje por el flujo normal (NLU + shortcut)
            if response is None:
                print(f"[CTRL] Handler devolvió None — repasando mensaje desde START")
                handler2 = self.get_handler_for_state(session.state)
                if handler2 != handler and session.state == ConversationState.START:
                    # Solo reintentar si el estado cambió a START
                    return self._process_message(session.phone_number, message)
                session_manager.save_session(session)
                return common_messages.UNKNOWN_QUERY
            # Registrar state_after ahora que el handler ya transicionó
            # Actualiza el último evento registrado con el estado de destino
            try:
                from src.integrations.conversation_context_service.event_store import event_store as _es
                with _es.db.get_connection() as _conn:
                    _conn.execute("""
                        UPDATE conversation_events
                        SET state_after = ?
                        WHERE client_phone = ?
                        ORDER BY created_at DESC
                        LIMIT 1
                    """, (session.state.value, phone_number))
            except Exception:
                pass  # No crítico — state_after es best-effort
            # Persistir estado en Redis antes de responder
            session_manager.save_session(session)
            return response
        except Exception as e:
            print(f"❌ Error procesando mensaje: {str(e)}")
            import traceback
            traceback.print_exc()
            session_manager.save_session(session)
            return common_messages.ERROR_GENERIC

    def _convert_natural_input(self, message: str, intent_result: Dict, session: SessionData) -> str:
        """
        Convierte input en lenguaje natural al formato esperado por los filtros.
        
        Por ejemplo:
        - "hoy" → Fecha de hoy en formato DD/MM/YYYY
        - "mañana" → Fecha de mañana en formato DD/MM/YYYY
        - "14:00" → "14:00" (ya está correcto)
        - "tarde" → Podría convertirse a opción numérica
        
        Args:
            message: Mensaje original del usuario
            intent_result: Resultado de la detección NLU
            session: Sesión actual
            
        Returns:
            Mensaje convertido o mensaje original si no se pudo convertir
        """
        from datetime import date, timedelta
        
        entities = intent_result.get('entities', {})
        current_filter = session.get_temp('current_filter_type')
        
        print(f"[NLU] Converting input for filter: {current_filter}")
        
        # Convertir fechas relativas
        if 'fecha' in entities:
            fecha_entity = entities['fecha']
            print(f"[NLU] Fecha entity detected: {fecha_entity}")
            
            if fecha_entity == 'hoy':
                converted = date.today().strftime('%d/%m/%Y')
                print(f"[NLU] 'hoy' → {converted}")
                return converted
            elif fecha_entity == 'mañana':
                converted = (date.today() + timedelta(days=1)).strftime('%d/%m/%Y')
                print(f"[NLU] 'mañana' → {converted}")
                return converted
            elif fecha_entity == 'pasado_mañana':
                converted = (date.today() + timedelta(days=2)).strftime('%d/%m/%Y')
                print(f"[NLU] 'pasado_mañana' → {converted}")
                return converted
            elif '/' in str(fecha_entity):
                # Ya es una fecha en formato DD/MM/YYYY
                print(f"[NLU] Fecha ya en formato correcto: {fecha_entity}")
                return str(fecha_entity)
        
        # Convertir horarios a números de opción si estamos en filtro de horario
        if current_filter == 'time' and 'horario' in entities:
            horario_entity = entities['horario']
            print(f"[NLU] Horario entity detected: {horario_entity}")
            
            # Mapeo de texto a número de opción
            horario_map = {
                'mañana': '1',
                'tarde': '2',
                'noche': '3'
            }
            
            if horario_entity in horario_map:
                converted = horario_map[horario_entity]
                print(f"[NLU] '{horario_entity}' → opción {converted}")
                return converted
        
        # Si no se pudo convertir, devolver original
        print(f"[NLU] No conversion needed or possible")
        return message
    
    def _try_intent_shortcut(self, session: SessionData, intent_result: Dict, user_info: Dict) -> Optional[str]:
        """
        Intenta hacer shortcut basado en la intención detectada.
        
        Args:
            session: Sesión del usuario
            intent_result: Resultado de detección de intención
            user_info: Info del usuario
            
        Returns:
            Respuesta del bot si hace shortcut, None si debe seguir flujo normal
        """
        intent = intent_result['intent']
        entities = intent_result['entities']
        can_shortcut = intent_result['can_shortcut']
        
        print(f"[NLU] Intentando shortcut para: {intent.value}")
        
        # ==========================================
        # INTENT: VER MIS CITAS
        # ==========================================
        if intent == Intent.VIEW_MY_APPOINTMENTS:
            print("[NLU] → Shortcut: Ver citas directamente")
            session.set_role(UserRole.CLIENT)
            session.transition_to(ConversationState.CLIENT_VIEW_APPOINTMENTS)
            return self.client_handler.handle_client_view_appointments(session, "")
        
        # ==========================================
        # INTENT: CANCELAR TURNO
        # ==========================================
        elif intent == Intent.CANCEL_APPOINTMENT:
            print("[NLU] → Cancelar turno")
            session.set_role(UserRole.CLIENT)
            session.transition_to(ConversationState.CLIENT_VIEW_APPOINTMENTS)
            return self.client_handler.handle_client_view_appointments(session, '')

        # ==========================================
        # INTENT: AGENDAR PARA TERCEROS
        # ==========================================
        elif intent == Intent.BOOK_FOR_THIRD_PARTY:
            # Feature flag — desactivar con FeatureFlags.THIRD_PARTY_BOOKING = False
            if not FeatureFlags.THIRD_PARTY_BOOKING:
                print("[NLU] → THIRD_PARTY_BOOKING desactivado, redirigiendo a búsqueda normal")
                return self._try_intent_shortcut(
                    session,
                    {**intent_result, 'intent': Intent.SEARCH_PROFESSIONAL},
                    user_info
                )

            print("[NLU] → Agendar para tercero")
            session.set_role(UserRole.CLIENT)
            session.set_temp('booking_for', 'other')
            session.set_temp('_third_party_active', True)  # proteger del limpiado
            if intent_result['entities'].get('third_party_relation'):
                session.set_temp(
                    'third_party_relation',
                    intent_result['entities']['third_party_relation']
                )

            # Limpiar contexto acumulado de búsquedas anteriores
            # para no arrastrar professional_name u otras entidades viejas
            conv_context = context_manager.get_context(session.phone_number)
            conv_context.reset()
            print("[NLU] → Contexto de búsqueda reseteado para flujo de tercero")
            # Reutilizar flujo de búsqueda con intent simulado
            return self._try_intent_shortcut(
                session,
                {**intent_result, 'intent': Intent.SEARCH_PROFESSIONAL},
                user_info
            )

        # ==========================================
        # INTENT: VER DISPONIBLES MAÑANA
        # ==========================================
        elif intent == Intent.VIEW_TOMORROW:
            print("[NLU] → Shortcut: Ver disponibles mañana")
            session.set_role(UserRole.CLIENT)
            
            from src.services.client_service import client_service
            from datetime import date, timedelta
            
            tomorrow = date.today() + timedelta(days=1)
            date_str = tomorrow.strftime('%Y-%m-%d')
            date_formatted = tomorrow.strftime('%d/%m/%Y')
            
            # Guardar en sesión
            session.set_temp('search_date', date_str)
            session.set_temp('search_date_formatted', date_formatted)
            
            # Preparar filtros
            filters = {}
            if 'horario' in entities:
                filters['time_preference'] = entities['horario']
                session.set_temp('time_preference', entities['horario'])
            
            # Buscar
            results = client_service.search_professionals_by_filters(
                date_str=date_str,
                **filters,
                limit=10
            )
            
            session.set_temp('search_results', results)
            session.transition_to(ConversationState.CLIENT_SHOW_RESULTS)
            
            # Formatear resultados
            if not results:
                # Verificar si es porque no existen o porque no hay disponibilidad
                no_profs = session.get_temp('no_professionals_found')
                
                if no_profs:
                    session.clear_temp()
                    return (
                        "😔 No encontré profesionales que cumplan con esos requisitos:\n"
                        f"• Especialidad: {entities.get('especialidad', 'cualquiera')}\n"
                        f"• Género: {entities.get('genero', 'cualquiera')}\n"
                        f"• Prepaga: {'Sí' if entities.get('prepaga') else 'No importa'}\n\n"
                        "Podés intentar:\n"
                        "• Cambiar los filtros\n"
                        "• Escribir 'buscar' para búsqueda asistida"
                    )
                else:
                    return (
                        f"😔 No encontré profesionales disponibles para {date_formatted}.\n\n"
                        "Hay profesionales que cumplen tus requisitos pero no tienen horarios disponibles ese día.\n\n"
                        "Podés intentar:\n"
                        "• Otra fecha\n"
                        "• Escribir 'buscar' para ver más opciones"
                    )
            
            formatted = client_service.format_search_results_with_slots(
                professionals=results,
                date_str=date_str,
                show_max_slots=3
            )
            
            header = f"✅ Encontré {len(results)} profesional(es) disponible(s) para mañana ({date_formatted}):\n\n"
            return header + formatted
        
        # ==========================================
        # INTENT: INFORMACIÓN DEL CENTRO
        # ==========================================
        elif intent == Intent.INFO_CENTER:
            print("[NLU] → Shortcut: Info del centro")
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            session.clear_temp()
            return user_service.get_center_info()
        
        # ==========================================
        # INTENT: BÚSQUEDA DE PROFESIONAL
        # ==========================================
        elif intent == Intent.SEARCH_PROFESSIONAL:
            print(f"[NLU] → Búsqueda de profesional (can_shortcut: {can_shortcut})")
            session.set_role(UserRole.CLIENT)

            # Limpiar contexto de tercero SOLO si el usuario busca directamente para sí mismo
            # NO limpiar si venimos del shortcut de book_for_third_party (flag _third_party_active)
            if (session.get_temp('booking_for') == 'other'
                    and not session.get_temp('_third_party_active')):
                session.set_temp('booking_for', None)
                session.set_temp('third_party_relation', None)
                session.set_temp('third_party_name', None)
                session.set_temp('third_party_phone', None)
                session.set_temp('third_party_age', None)
                session.set_temp('third_party_data_collected', None)
                print("[NLU] → Limpiado contexto de tercero para búsqueda normal")

            # Guardar entidades detectadas
            if 'especialidad' in entities:
                session.set_temp('especialidad', entities['especialidad'])
            if 'zona' in entities:
                session.set_temp('zona', entities['zona'])
            if 'fecha' in entities:
                session.set_temp('fecha', entities['fecha'])
            if 'horario' in entities:
                session.set_temp('time_preference', entities['horario'])
            if 'modalidad' in entities:
                session.set_temp('modalidad', entities['modalidad'])
            
            # Si puede hacer shortcut (tiene info suficiente)
            if can_shortcut:
                print("[NLU] → Ejecutando búsqueda directa")
                result = self._execute_smart_search(session, entities)
                session.set_temp('_third_party_active', None)  # limpiar flag
                return result
            
            # Si no, iniciar flujo de filtros pidiendo lo que falta
            else:
                print("[NLU] → Falta info, iniciando flujo de filtros")
                missing = intent_result.get('missing_entities', [])
                return self._start_filter_flow(session, entities, missing)

        # ==========================================
        # INTENT: CONFIRM_ACTION
        # ==========================================
        elif intent == Intent.CONFIRM_ACTION:
            _CONFIRM_STATES = {
                ConversationState.CLIENT_CONFIRM_BOOKING,
                ConversationState.CLIENT_CONFIRM_CANCEL,
                ConversationState.CLIENT_RESCHEDULE_CONFIRM,
            }
            if session.state in _CONFIRM_STATES:
                print(f"[NLU] → confirm_action en {session.state.value} → message='1'")
                handler = self.get_handler_for_state(session.state)
                return handler(session, '1')
            # En CLIENT_MAIN_MENU una afirmación = quiero agendar
            if session.state == ConversationState.CLIENT_MAIN_MENU:
                print("[NLU] → confirm_action en client_main_menu → freelance_start")
                return freelance_handler.handle_freelance_start(session)
            print(f"[NLU] → confirm_action fuera de estado de confirmación ({session.state.value}) — ignorado")
            return None

        # ==========================================
        # INTENT: DENY_ACTION
        # ==========================================
        elif intent == Intent.DENY_ACTION:
            _DENY_STATES = {
                ConversationState.CLIENT_CONFIRM_BOOKING,
                ConversationState.CLIENT_CONFIRM_CANCEL,
                ConversationState.CLIENT_RESCHEDULE_CONFIRM,
            }
            if session.state in _DENY_STATES:
                print(f"[NLU] → deny_action en {session.state.value} → message='0'")
                handler = self.get_handler_for_state(session.state)
                return handler(session, '0')
            print(f"[NLU] → deny_action fuera de estado de confirmación ({session.state.value}) — ignorado")
            return None

        # No hay shortcut disponible
        print("[NLU] → No se puede hacer shortcut")
        return None
    
    def _execute_smart_search(self, session: SessionData, entities: Dict) -> str:
        """
        Ejecuta búsqueda inteligente con las entidades extraídas.
        
        Args:
            session: Sesión del usuario
            entities: Entidades extraídas/acumuladas del contexto
            
        Returns:
            Resultados de búsqueda formateados
        """
        from src.services.client_service import client_service
        from datetime import datetime, timedelta, date
        from src.core.conversation_context import context_manager

        # Obtener contexto
        conv_context = context_manager.get_context(session.phone_number)
        
        # Convertir fecha relativa a absoluta
        fecha_entity = entities.get('fecha')

        # 🔍 DEBUG: Ver qué fecha tiene el servidor
        hoy = date.today()
        print(f"[DEBUG] Hoy según el servidor: {hoy} ({hoy.strftime('%d/%m/%Y')})")
        print(f"[DEBUG] Fecha entity: '{fecha_entity}'")

        # Manejar fecha pasada
        if fecha_entity == 'fecha_pasada':
            return ("⚠️ La fecha que ingresaste ya pasó.\n\n"
                "Por favor elige una fecha futura:\n"
                "• 'hoy'\n"
                "• 'mañana'\n"
                "• 'DD/MM/YYYY'")

        # Si no especifica fecha, asumir 'hoy' por defecto
        if not fecha_entity:
            print(f"[NLU] No se especificó fecha, asumiendo 'hoy' por defecto")
            fecha_entity = 'hoy'

        if fecha_entity == 'hoy':
            date_obj = date.today()
        elif fecha_entity == 'mañana':
            date_obj = date.today() + timedelta(days=1)
            print(f"[DEBUG] Mañana calculado: {date_obj} ({date_obj.strftime('%d/%m/%Y')})")
        elif fecha_entity == 'pasado_mañana':
            date_obj = date.today() + timedelta(days=2)
        elif fecha_entity:
            # ⭐ NUEVO: Intentar parsear múltiples formatos
            try:
                # Formato DD/MM/YYYY
                date_obj = datetime.strptime(fecha_entity, '%d/%m/%Y').date()
                print(f"[DEBUG] Fecha parseada DD/MM/YYYY: {date_obj}")
            except:
                try:
                    # ⭐ Formato YYYY-MM-DD (viene del extractor de días de semana)
                    date_obj = datetime.strptime(fecha_entity, '%Y-%m-%d').date()
                    print(f"[DEBUG] Fecha parseada YYYY-MM-DD: {date_obj}")
                except:
                    try:
                        # Formato DD/MM (sin año)
                        day, month = map(int, fecha_entity.split('/'))
                        year = date.today().year
                        date_obj = date(year, month, day)
                        print(f"[DEBUG] Fecha parseada DD/MM: {date_obj}")
                    except:
                        print(f"[ERROR] No se pudo parsear fecha: '{fecha_entity}', usando HOY")
                        date_obj = date.today()  # Fallback a hoy
        else:
            date_obj = date.today()
        
        date_str = date_obj.strftime('%Y-%m-%d')
        date_formatted = date_obj.strftime('%d/%m/%Y')
        
        # Preparar filtros
        filters = {}
        if 'zona' in entities:
            filters['zone'] = entities['zona']
        if 'especialidad' in entities:
            filters['specialty'] = entities['especialidad']
        if 'horario' in entities:
            filters['time_preference'] = entities['horario']
        if 'modalidad' in entities:
            filters['modality'] = entities['modalidad']
        if 'genero' in entities:
            # Convertir a formato esperado por BD (m/f)
            gender_map = {'masculino': 'm', 'femenino': 'f'}
            filters['gender'] = gender_map.get(entities['genero'])
            print(f"[NLU] Género mapeado: {entities['genero']} → {filters['gender']}")
        if 'prepaga' in entities:
            filters['accept_prepaga'] = True
            print(f"[NLU] Filtro prepaga activado")
        
        # Si hay nombre de profesional, agregarlo como filtro
        professional_name_filter = entities.get('professional_name')
        if professional_name_filter:
            filters['professional_name'] = professional_name_filter
            print(f"[NLU] 🎯 Agregando filtro de nombre a BD: '{professional_name_filter}'")

        # Modo freelance — forzar filtro por el profesional único
        if session.get_temp('flow_context') == 'freelance':
            from src.config.config import Config
            prof_phone = getattr(Config, 'SINGLE_PROFESSIONAL_PHONE', '').strip()
            if prof_phone:
                filters['professional_phone_filter'] = prof_phone
        
        # Guardar filtros en contexto (para refinamiento futuro)
        conv_context.save_search_filters(filters)
        
        # Buscar profesionales
        results = client_service.search_professionals_by_filters(
            date_str=date_str,
            **filters,
            limit=10
        )
        
        # Guardar en sesión
        session.set_temp('search_results', results)
        session.set_temp('search_date', date_str)
        session.set_temp('search_date_formatted', date_formatted)

        # Modo freelance — ir directo al detalle sin pasar por lista de resultados
        if session.get_temp('flow_context') == 'freelance' and results:
            professional = results[0]
            session.set_temp('selected_professional', professional)
            session.transition_to(ConversationState.CLIENT_VIEW_DETAIL_WITH_BOOKING)
            session_manager.save_session(session)
            return client_service.format_professional_detail_with_slots(
                professional=professional,
                date_str=date_str,
                time_preference=filters.get('time_preference'),
            )

        session.transition_to(ConversationState.CLIENT_SHOW_RESULTS)
        session_manager.save_session(session)

        session.transition_to(ConversationState.CLIENT_SHOW_RESULTS)
        # Persistir inmediatamente — el siguiente mensaje debe leer este estado
        session_manager.save_session(session)
        
        # Sin resultados — intentar fallbacks inteligentes
        if not results:
            time_pref = filters.get('time_preference')

            # Fallback 1: turno opuesto del mismo día
            if time_pref in ('mañana', 'tarde', 'noche'):
                OPUESTO = {'mañana': 'tarde', 'tarde': 'mañana', 'noche': 'mañana'}
                turno_alt = OPUESTO[time_pref]
                filters_alt = {**filters, 'time_preference': turno_alt}
                results_alt = client_service.search_professionals_by_filters(
                    professional_phone_filter=filters.get('professional_phone_filter'),
                    date_str=date_str, **filters_alt, limit=10
                )
                if results_alt:
                    session.set_temp('search_results', results_alt)
                    session.set_temp('time_preference', turno_alt)
                    session_manager.save_session(session)
                    formatted = client_service.format_search_results_with_slots(
                        professionals=results_alt, date_str=date_str, show_max_slots=3
                    )
                    return (f"😔 No hay turnos de {time_pref} para {date_formatted}, "
                            f"pero encontré disponibilidad de *{turno_alt}*:\n\n{formatted}")

            # Fallback 2: día siguiente sin filtro de horario
            from datetime import datetime, timedelta
            try:
                next_date = (datetime.strptime(date_str, '%Y-%m-%d') + timedelta(days=1)).date()
                next_str = next_date.strftime('%Y-%m-%d')
                next_formatted = next_date.strftime('%d/%m')
                filters_next = {k: v for k, v in filters.items() if k != 'time_preference'}
                results_next = client_service.search_professionals_by_filters(
                    date_str=next_str, **filters_next, limit=10
                )
                if results_next:
                    session.set_temp('search_results', results_next)
                    session.set_temp('search_date', next_str)
                    session.set_temp('search_date_formatted', next_formatted)
                    session.set_temp('time_preference', None)
                    session_manager.save_session(session)
                    formatted = client_service.format_search_results_with_slots(
                        professionals=results_next, date_str=next_str, show_max_slots=3
                    )
                    filter_text = self._format_applied_filters(entities)
                    return (f"😔 No encontré para {date_formatted}{filter_text}, "
                            f"pero hay disponibilidad el *{next_formatted}*:\n\n{formatted}")
            except Exception:
                pass

            # Sin fallback — mensaje estándar
            filter_text = self._format_applied_filters(entities)
            return (f"😔 No encontré profesionales disponibles para {date_formatted}{filter_text}\n\n"
                    "Podés intentar:\n"
                    "• Otra fecha (ej: 'mañana', 'pasado mañana', '01/02/2026)\n"
                    "• Cambiar filtros (escribe 'filtros')\n"
                    "• Escribir 'buscar' para empezar de nuevo")
        
        # Formatear resultados
        formatted = client_service.format_search_results_with_slots(
            professionals=results,
            date_str=date_str,
            show_max_slots=3
        )
        
        return formatted

    def _start_filter_flow(self, session: SessionData, entities: Dict, missing: List[str]) -> str:
        """
        Inicia flujo de filtros pidiendo solo lo que falta.
        
        Args:
            session: Sesión del usuario
            entities: Entidades ya extraídas
            missing: Lista de entidades faltantes
            
        Returns:
            Pregunta para siguiente filtro
        """
        # Transicionar a flujo de multi-filtro
        session.transition_to(ConversationState.CLIENT_MULTIFILTER_MENU)
        
        # Preparar mensaje personalizado — con contexto de tercero si aplica
        booking_for = session.get_temp('booking_for') if FeatureFlags.THIRD_PARTY_BOOKING else None
        relation    = session.get_temp('third_party_relation') if FeatureFlags.THIRD_PARTY_BOOKING else None
        if booking_for == 'other' and relation:
            mensaje = f"Para el turno de tu {relation}, "
        else:
            mensaje = "Perfecto! "
        
        # Confirmar lo que entendió
        confirmaciones = []
        if 'especialidad' in entities:
            confirmaciones.append(f"buscarás {entities['especialidad']}")
        if 'zona' in entities:
            confirmaciones.append(f"en zona {entities['zona']}")
        if 'fecha' in entities:
            confirmaciones.append(f"para {entities['fecha']}")
        if 'horario' in entities:
            confirmaciones.append(f"por la {entities['horario']}")
        
        if confirmaciones:
            mensaje += " ".join(confirmaciones).capitalize() + ".\n\n"
        
        # Preguntar lo que falta (solo el primero)
        if 'fecha' in missing:
            mensaje += "¿Para qué fecha necesitas el turno?\n"
            mensaje += "Ej: 'mañana', 'hoy', '25/12'"
        elif 'horario' in missing:
            mensaje += "¿En qué horario preferís?\n"
            mensaje += "1️⃣ Mañana\n2️⃣ Tarde\n3️⃣ Noche"
        elif 'zona' in missing:
            mensaje += "¿En qué zona?\n"
            mensaje += "Ej: 'Palermo', 'Belgrano', 'Online'"
        elif 'especialidad' in missing:
            mensaje += "¿Qué tipo de profesional buscas?\n"
            mensaje += "Ej: 'Psicólogo', 'Nutricionista'"
        else:
            # Tiene todo, buscar
            mensaje = "Buscando profesionales..."
            return self._execute_smart_search(session, entities)
        
        return mensaje
    
    def get_handler_for_state(self, state: ConversationState):
        """Obtiene handler para el estado actual."""
        handlers = {
            ConversationState.START: self.handle_start,
            ConversationState.PROF_MAIN_MENU: self.professional_handler.handle_prof_main_menu,
            ConversationState.PROF_VIEW_APPOINTMENTS: self.professional_handler.handle_prof_view_appointments,
            ConversationState.PROF_INFO_MENU: self.professional_handler.handle_prof_info_menu,
            ConversationState.PROF_INFO_NAME: self.professional_handler.handle_prof_info_name,
            ConversationState.PROF_INFO_EMAIL: self.professional_handler.handle_prof_info_email,
            ConversationState.PROF_INFO_ZONA: self.professional_handler.handle_prof_info_zona,
            ConversationState.PROF_INFO_GENERO: self.professional_handler.handle_prof_info_genero,
            ConversationState.PROF_INFO_PREPAGA: self.professional_handler.handle_prof_info_prepaga,
            ConversationState.PROF_INFO_ESPECIALIDAD: self.professional_handler.handle_prof_info_especialidad,
            ConversationState.PROF_INFO_QUICK: self.professional_handler.handle_prof_info_quick,
            ConversationState.PROF_INFO_BIO: self.professional_handler.handle_prof_info_bio,
            ConversationState.PROF_INFO_FEE_RANGE: self.professional_handler.handle_prof_info_fee_range,
            ConversationState.PROF_AGENDA_IMPORT_REVIEW: self.professional_handler.handle_prof_agenda_import_review,
            ConversationState.PROF_AGENDA_IMPORT_DETAIL: self.professional_handler.handle_prof_agenda_import_detail,
            ConversationState.CLIENT_MAIN_MENU: self.client_handler.handle_client_main_menu,
            ConversationState.CLIENT_NEW_USER_MENU: self.client_handler.handle_client_main_menu,
            ConversationState.CLIENT_MULTIFILTER_MENU: self.client_handler.handle_client_multifilter_menu,
            ConversationState.CLIENT_FILTER_INPUT: self.client_handler.handle_client_filter_input,
            ConversationState.CLIENT_SEARCH_QUICK: self.client_handler.handle_client_search_quick,
            ConversationState.CLIENT_SHOW_RESULTS: self.client_handler.handle_client_show_results,
            ConversationState.CLIENT_VIEW_DETAIL: self.client_handler.handle_client_view_detail,
            ConversationState.CLIENT_VIEW_DETAIL_WITH_BOOKING: self.client_handler.handle_client_view_detail_with_booking,
            ConversationState.CLIENT_CONFIRM_BOOKING: self.client_handler.handle_client_confirm_booking,
            ConversationState.CLIENT_COLLECT_OWN_NAME: self.client_handler.handle_client_collect_own_name,
            ConversationState.CLIENT_THIRD_PARTY_CHOICE: self.client_handler.handle_client_third_party_choice,
            ConversationState.CLIENT_THIRD_PARTY_NAME:   self.client_handler.handle_client_third_party_name,
            ConversationState.CLIENT_THIRD_PARTY_PHONE:  self.client_handler.handle_client_third_party_phone,
            ConversationState.CLIENT_THIRD_PARTY_AGE:    self.client_handler.handle_client_third_party_age,
            ConversationState.CLIENT_BOOKING_CONFIRMED: self.client_handler.handle_client_booking_confirmed,
            ConversationState.CLIENT_VIEW_APPOINTMENTS: self.client_handler.handle_client_view_appointments,
            ConversationState.CLIENT_APPOINTMENT_DETAIL: self.client_handler.handle_client_appointment_detail,
            ConversationState.CLIENT_CANCEL_APPOINTMENT: self.client_handler.handle_client_cancel_appointment,
            ConversationState.CLIENT_CANCEL_REASON: self.client_handler.handle_client_cancel_reason,
            ConversationState.CLIENT_CANCEL_SUCCESS: self.client_handler.handle_client_cancel_success,
            ConversationState.CLIENT_RESCHEDULE_APPOINTMENT: self.client_handler.handle_client_reschedule_appointment,
            ConversationState.CLIENT_RESCHEDULE_SELECT_DATE: self.client_handler.handle_client_reschedule_select_date,
            ConversationState.CLIENT_RESCHEDULE_SELECT_TIME: self.client_handler.handle_client_reschedule_select_time,
            ConversationState.CLIENT_RESCHEDULE_CONFIRM: self.client_handler.handle_client_reschedule_confirm,
            ConversationState.CLIENT_CONFIRM_CANCEL: self.client_handler.handle_confirm_cancel,
            ConversationState.CLIENT_SELECT_CANCEL: self.client_handler.handle_select_cancel,
            ConversationState.CLIENT_FREELANCE_BOOK_DATE: lambda s, m: freelance_handler.handle_freelance_book_date(s, m),
            ConversationState.CLIENT_FREELANCE_BOOK_TIME: lambda s, m: _route_freelance_time(s, m),
            ConversationState.AWAITING_REMINDER_RESPONSE: lambda s, m: handle_reminder_response(s, m),
            ConversationState.AWAITING_SLOT_OFFER: lambda s, m: handle_slot_offer_response(s, m),
        }
        return handlers.get(state, self.handle_unknown_state)

    def handle_start(self, session: SessionData, message: str) -> str:
        """Maneja estado inicial."""
        session.set_role(UserRole.CLIENT)
        session.transition_to(ConversationState.CLIENT_MAIN_MENU)
        user_info = user_service.identify_user(session.phone_number)
        user_info['phone_number'] = session.phone_number
        return user_service.generate_welcome_message(user_info)

    def handle_return_to_menu(self, session: SessionData) -> str:
        """Vuelve al menú principal."""
        session.clear_temp()
        if session.role == UserRole.PROFESSIONAL:
            session.transition_to(ConversationState.PROF_MAIN_MENU)
            return professional_messages.PROF_MAIN_MENU
        else:
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            user_info = user_service.identify_user(session.phone_number)
            user_info['phone_number'] = session.phone_number
            return user_service.generate_welcome_message(user_info)

    def handle_cancel(self, session: SessionData) -> str:
        """Cancela operación actual."""
        session.clear_temp()
        return self.handle_return_to_menu(session)

    def handle_unknown_state(self, session: SessionData, message: str) -> str:
        """Maneja estado desconocido."""
        print(f"⚠️ Estado desconocido: {session.state}")
        return common_messages.ERROR_UNKNOWN_STATE + "\n\n" + self.handle_return_to_menu(session)
    
    def _can_execute_search(self, entities: Dict) -> bool:
        """
        Determina si hay suficiente información para ejecutar búsqueda.
        
        LÓGICA: Solo necesita fecha (especialidad es opcional).
        
        Args:
            entities: Entidades acumuladas
            
        Returns:
            True si puede buscar
        """
        # Mínimo requerido: fecha
        has_date = 'fecha' in entities and entities['fecha']
        
        return has_date


    def _get_missing_required_entities(self, entities: Dict) -> List[str]:
        """
        Obtiene lista de entidades requeridas faltantes.
        
        Args:
            entities: Entidades acumuladas
            
        Returns:
            Lista de entidades faltantes
        """
        required = ['fecha']  # Solo fecha es requerida
        missing = []
        
        for req in required:
            if req not in entities or not entities[req]:
                missing.append(req)
        
        return missing


    def _ask_for_missing_entity(self, session: SessionData, entities: Dict, missing: List[str]) -> str:
        """
        Pregunta por la siguiente entidad faltante de forma contextual.
        
        Args:
            session: Sesión actual
            entities: Entidades ya acumuladas
            missing: Lista de entidades faltantes
            
        Returns:
            Mensaje preguntando por la entidad
        """
        if not missing:
            # No falta nada, ejecutar búsqueda
            return self._execute_smart_search(session, entities)
        
        # Preguntar por la primera faltante
        next_missing = missing[0]
        
        session.transition_to(ConversationState.CLIENT_MULTIFILTER_MENU)
        
        # Construir mensaje contextual según lo que ya tiene
        context_parts = []
        if 'especialidad' in entities:
            context_parts.append(f"Buscarás {entities['especialidad']}")
        if 'genero' in entities:
            gender_text = 'profesional mujer' if entities['genero'] == 'femenino' else 'profesional hombre'
            context_parts.append(gender_text)
        if 'prepaga' in entities:
            context_parts.append('que acepte obra social')

        # GAP 1 — Personalizar prefijo si es para un tercero
        booking_for = session.get_temp('booking_for') if FeatureFlags.THIRD_PARTY_BOOKING else None
        relation    = session.get_temp('third_party_relation') if FeatureFlags.THIRD_PARTY_BOOKING else None
        if booking_for == 'other' and relation:
            context = f"Para el turno de tu {relation}, "
            if context_parts:
                context += ", ".join(context_parts) + ".\n\n"
        else:
            context = "Perfecto! " + ", ".join(context_parts) + ".\n\n" if context_parts else ""
        
        # Mensaje según la entidad faltante
        if next_missing == 'fecha':
            return (f"{context}"
                    f"¿Para qué fecha necesitas el turno?\n"
                    f"Ej: 'hoy', 'mañana', 'pasado mañana', 'DD/MM'")
        
        elif next_missing == 'horario':
            return (f"{context}"
                    f"¿En qué horario preferís?\n"
                    f"Ej: 'mañana', 'tarde', 'noche'")
        
        elif next_missing == 'especialidad':
            return (f"{context}"
                    f"¿Qué especialidad buscás?\n"
                    f"Ej: 'psicología', 'nutrición', 'kinesiología'")
        
        else:
            return f"{context}¿Qué {next_missing} necesitas?"


    def _format_applied_filters(self, entities: Dict) -> str:
        """
        Formatea filtros aplicados para mostrar al usuario.
        
        Args:
            entities: Entidades usadas en la búsqueda
            
        Returns:
            Texto formateado con los filtros
        """
        filters_used = []
        
        if 'especialidad' in entities:
            filters_used.append(f"Especialidad: {entities['especialidad']}")
        if 'genero' in entities:
            filters_used.append(f"Género: {entities['genero']}")
        if 'prepaga' in entities:
            filters_used.append("Acepta obra social")
        if 'horario' in entities:
            filters_used.append(f"Horario: {entities['horario']}")
        if 'zona' in entities:
            filters_used.append(f"Zona: {entities['zona']}")
        
        if not filters_used:
            return ""
        
        return " con:\n• " + "\n• ".join(filters_used)
    
    
def _route_freelance_time(session, message):
    """
    CLIENT_FREELANCE_BOOK_TIME tiene 2 sub-pasos en el mismo estado:
      - Primer mensaje: elegir horario (1/2/3) → mostrar pantalla de filtros
      - Segundo mensaje: confirmar búsqueda (1) o volver (0)
    Se distinguen con session.get_temp('freelance_filters_shown').
    """
    if not session.get_temp('freelance_filters_shown', False):
        response = freelance_handler.handle_freelance_book_time(session, message)
        session.set_temp('freelance_filters_shown', True)
        return response
    else:
        return freelance_handler.handle_freelance_confirm_search(session, message)

# ==========================================
# INSTANCIA GLOBAL
# ==========================================
bot_controller = BotController()