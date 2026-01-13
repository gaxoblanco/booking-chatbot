"""
Bot Controller
==============
Orquestador principal del bot. Procesa mensajes entrantes y delega a handlers específicos.

Este archivo es el cerebro del bot:
- Recibe mensajes de WhatsApp
- Identifica usuarios automáticamente (NUEVO)
- Detecta intenciones (NUEVO)
- Maneja comandos globales
- Delega a handlers específicos (cliente/profesional)
- Gestiona errores

Responsabilidades:
- Router principal (process_message)
- Comandos globales (hola, menu, cancelar, ayuda)
- Delegación a handlers
- Integración con user_service (NUEVO)
- Integración con filter_config (NUEVO)
"""

from src.bot.professional_handler import ProfessionalHandler
from src.bot.client_handler import ClientHandler
from src.config.filter_config import FilterConfig, FeatureFlags
from src.services.user_service import user_service
from src.messages.messages_common import common_messages
from src.messages.messages_client import client_messages
from src.messages.messages_professional import professional_messages
from src.core.states import (
    ConversationState,
    UserRole,
    session_manager,
    SessionData
)
import sys
from pathlib import Path

# Agregar raíz del proyecto al path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


# Imports de handlers


class BotController:
    """
    Controlador principal del bot.

    Maneja el flujo de mensajes y delega a handlers específicos.
    Integra reconocimiento inteligente de usuarios y filtros dinámicos.
    """

    def __init__(self):
        """Inicializar controlador del bot."""
        # Los mensajes se importan como singletons desde los módulos

        # Handlers específicos (ya no reciben messages)
        self.client_handler = ClientHandler()
        self.professional_handler = ProfessionalHandler()

    def process_message(self, phone_number: str, message: str) -> str:
        """
        Procesa mensaje entrante y retorna respuesta.

        Este es el método principal del bot. Recibe cada mensaje de WhatsApp
        y lo procesa según el estado actual de la conversación.

        FLUJO:
        1. Identificar usuario (NUEVO) → user_service
        2. Verificar comandos globales (hola, menu, cancelar)
        3. Manejar gate de certificado (profesionales)
        4. Delegar a handler específico según estado

        Args:
            phone_number: Número de WhatsApp del usuario
            message: Mensaje de texto del usuario

        Returns:
            Respuesta del bot
        """
        # ==========================================
        # 1. IDENTIFICACIÓN INTELIGENTE DE USUARIO
        # ==========================================
        if FeatureFlags.INTELLIGENT_USER_RECOGNITION:
            user_info = user_service.identify_user(phone_number)

            # Log de acción (analytics)
            if FeatureFlags.ANALYTICS_TRACKING:
                user_service.log_action(
                    phone=phone_number,
                    action_type='message',
                    details={'message_length': len(message)},
                    session_id=phone_number  # TODO: usar session_id real
                )

        # ==========================================
        # 2. OBTENER O CREAR SESIÓN
        # ==========================================
        session = session_manager.get_session(phone_number)

        # Limpiar mensaje
        message = message.strip()
        message_lower = message.lower()

        # ==========================================
        # 3. SUPER COMANDO: "HOLA" SIEMPRE RESETEA
        # ==========================================
        # Sin importar el estado, "hola" reinicia la conversación
        if message_lower in ['hola', 'hello', 'hi', 'hey', 'buenos días', 'buenas tardes', 'buenas noches']:

            # Si el usuario está registrado, mostrar mensaje personalizado
            if FeatureFlags.INTELLIGENT_USER_RECOGNITION and user_info['is_registered']:
                session.reset()

                # Determinar estado inicial según tipo de usuario
                if user_info['user_type'] == 'professional':
                    session.set_role(UserRole.PROFESSIONAL)
                    session.transition_to(ConversationState.PROF_MAIN_MENU)
                elif user_info['user_type'] == 'client':
                    session.set_role(UserRole.CLIENT)
                    session.transition_to(ConversationState.CLIENT_MAIN_MENU)
                elif user_info['user_type'] == 'new':
                    session.reset()
                    session.set_role(UserRole.CLIENT)
                    session.transition_to(
                        ConversationState.CLIENT_NEW_USER_MENU)  # ✅ Nuevo estado
                    return user_service.generate_welcome_message(user_info)

                # Generar mensaje personalizado
                if user_info['user_type'] == 'professional':
                    # Usar menú profesional completo
                    greeting = f"¡Hola Dr/Dra. {user_info['name']}! 👋" if user_info['name'] else "¡Hola! 👋"
                    return greeting + "\n\n" + professional_messages.PROF_MAIN_MENU
                else:
                    return user_service.generate_welcome_message(user_info)

            # Usuario nuevo → detectar intención
            elif FeatureFlags.INTELLIGENT_USER_RECOGNITION:
                intention = user_service.detect_intention(message)

                session.reset()

                if intention == 'professional':
                    # ❌ ANTES:
                    # session.set_role(UserRole.PROFESSIONAL)
                    # session.transition_to(ConversationState.PROF_NEED_CERTIFICATE)
                    # return professional_messages.PROF_NEED_CERTIFICATE

                    # ✅ AHORA:
                    session.set_role(UserRole.PROFESSIONAL)
                    session.transition_to(
                        ConversationState.PROF_NEED_ACCESS_KEY)
                    return professional_messages.PROF_NEED_ACCESS_KEY

                elif intention == 'client':
                    # Usuario dice "hola" o "busco turno"
                    session.set_role(UserRole.CLIENT)
                    session.transition_to(ConversationState.CLIENT_MAIN_MENU)
                    return user_service.generate_welcome_message(user_info)

                else:
                    # Intención ambigua → preguntar rol
                    session.transition_to(ConversationState.ROLE_SELECTION)
                    return common_messages.WELCOME

            # Fallback: comportamiento original
            else:
                session.reset()
                session.transition_to(ConversationState.ROLE_SELECTION)
                return common_messages.WELCOME

        # ==========================================
        # 4. ACCESS KEY GATE - BLOQUEA TODO
        # ==========================================
        # Si el profesional no ingresó clave de acceso, bloquea TODOS los comandos
        if session.state == ConversationState.PROF_NEED_ACCESS_KEY:
            # Permitir 'inicio' para reiniciar y elegir rol nuevamente
            if message_lower in ['inicio', 'start', 'restart', 'empezar']:
                session.reset()
                session.transition_to(ConversationState.ROLE_SELECTION)
                return common_messages.WELCOME

            # Permitir '0' para volver a selección de rol
            if message == '0':
                session.reset()
                session.transition_to(ConversationState.ROLE_SELECTION)
                return common_messages.WELCOME

            # Bloquear todo lo demás (menu, cancelar, ayuda, etc.)
            # El usuario DEBE ingresar la clave de acceso
            return professional_messages.PROF_NEED_ACCESS_KEY

        # ==========================================
        # 5. COMANDOS GLOBALES (funcionan desde cualquier lado EXCEPTO certificate gate)
        # ==========================================

        # Resetear a inicio (elegir rol nuevamente)
        if message_lower in ['inicio', 'start', 'restart', 'empezar']:
            session.reset()
            return common_messages.WELCOME

        # Volver al menú específico del rol
        if message_lower in ['menu', 'menú', 'volver']:
            return self.handle_return_to_menu(session)

        # Cancelar operación actual
        if message_lower in ['cancelar', 'cancel', 'salir']:
            return self.handle_cancel(session)

        # Ayuda
        if message_lower in ['ayuda', 'help', '?']:
            return common_messages.HELP_MESSAGE

        # ==========================================
        # 6. ENRUTAR A HANDLER SEGÚN ESTADO
        # ==========================================

        # Obtener handler apropiado según estado actual
        handler = self.get_handler_for_state(session.state)

        try:
            response = handler(session, message)
            return response
        except Exception as e:
            print(f"❌ Error procesando mensaje: {str(e)}")
            import traceback
            traceback.print_exc()
            return common_messages.ERROR_GENERIC

    def get_handler_for_state(self, state: ConversationState):
        """
        Obtiene la función handler apropiada para un estado.

        Este método mapea cada estado de conversación a su handler específico.
        Los handlers están organizados en archivos separados por responsabilidad.

        Args:
            state: Estado actual de conversación

        Returns:
            Función handler para ese estado
        """
        handlers = {
            # ===== ESTADOS INICIALES =====
            ConversationState.START: self.handle_start,
            ConversationState.ROLE_SELECTION: self.handle_role_selection,

            # ===== ESTADOS DE PROFESIONAL =====
            # TODO: Mover estos handlers a professional_handler.py
            # ConversationState.PROF_NEED_CERTIFICATE: self.handle_prof_need_certificate,
            # handlers de clave
            ConversationState.PROF_NEED_ACCESS_KEY: self.handle_prof_need_access_key,
            ConversationState.PROF_MAIN_MENU: self.handle_prof_main_menu,
            ConversationState.CLIENT_NEW_USER_MENU: self.handle_client_new_user_menu,
            ConversationState.PROF_FREE_SLOT_DATE: self.handle_prof_free_slot_date,
            ConversationState.PROF_FREE_SLOT_TIME: self.handle_prof_free_slot_time,
            ConversationState.PROF_FREE_SLOT_CONFIRM: self.handle_prof_free_slot_confirm,
            ConversationState.PROF_WEEK_SCHEDULE_QUICK: self.handle_prof_week_schedule_quick,
            ConversationState.PROF_MANAGE_FREE_SLOTS: self.handle_prof_manage_free_slots,
            ConversationState.PROF_DELETE_FREE_SLOT: self.handle_prof_delete_free_slot,
            ConversationState.PROF_VIEW_APPOINTMENTS: self.handle_prof_view_appointments,

            # Estados de información del profesional
            ConversationState.PROF_INFO_MENU: self.handle_prof_info_menu,
            ConversationState.PROF_INFO_NAME: self.handle_prof_info_name,
            ConversationState.PROF_INFO_EMAIL: self.handle_prof_info_email,
            ConversationState.PROF_INFO_ZONA: self.handle_prof_info_zona,
            ConversationState.PROF_INFO_GENERO: self.handle_prof_info_genero,
            ConversationState.PROF_INFO_PREPAGA: self.handle_prof_info_prepaga,
            ConversationState.PROF_INFO_ESPECIALIDAD: self.handle_prof_info_especialidad,
            ConversationState.PROF_INFO_QUICK: self.handle_prof_info_quick,
            ConversationState.PROF_INFO_BIO: self.handle_prof_info_bio,
            ConversationState.PROF_INFO_FEE_RANGE: self.handle_prof_info_fee_range,

            # ===== ESTADOS DE CLIENTE =====
            # TODO: Mover estos handlers a client_handler.py
            ConversationState.CLIENT_MAIN_MENU: self.handle_client_main_menu,
            ConversationState.CLIENT_NEW_USER_MENU: self.handle_client_main_menu,  # Usar el mismo handler
            ConversationState.CLIENT_FILTER_ZONA: self.handle_client_filter_zona,
            ConversationState.CLIENT_FILTER_FECHA: self.handle_client_filter_fecha,
            ConversationState.CLIENT_FILTER_HORA: self.handle_client_filter_hora,
            ConversationState.CLIENT_FILTER_PREPAGA: self.handle_client_filter_prepaga,
            ConversationState.CLIENT_FILTER_SEXO: self.handle_client_filter_sexo,
            ConversationState.CLIENT_SHOW_RESULTS: self.handle_client_show_results,
            ConversationState.CLIENT_VIEW_DETAIL: self.handle_client_view_detail,

            # Estados de reserva del cliente
            ConversationState.CLIENT_VIEW_DETAIL_WITH_BOOKING: self.client_handler.handle_client_view_detail_with_booking,
            ConversationState.CLIENT_CONFIRM_BOOKING: self.client_handler.handle_client_confirm_booking,
            ConversationState.CLIENT_BOOKING_CONFIRMED: self.client_handler.handle_client_booking_confirmed,
            

            # Estados de multi-filtro del cliente
            ConversationState.CLIENT_MULTIFILTER_MENU: self.handle_client_multifilter_menu,
            ConversationState.CLIENT_MULTIFILTER_ZONA: self.handle_client_multifilter_zona,
            ConversationState.CLIENT_MULTIFILTER_FECHA: self.handle_client_multifilter_fecha,
            ConversationState.CLIENT_MULTIFILTER_HORA: self.handle_client_multifilter_hora,
            ConversationState.CLIENT_MULTIFILTER_PREPAGA: self.handle_client_multifilter_prepaga,
            ConversationState.CLIENT_MULTIFILTER_SEXO: self.handle_client_multifilter_sexo,
            ConversationState.CLIENT_MULTIFILTER_ESPECIALIDAD: self.handle_client_multifilter_especialidad,
            ConversationState.CLIENT_SEARCH_QUICK: self.handle_client_search_quick,
            # Estados de gestión de citas del cliente
            ConversationState.CLIENT_VIEW_APPOINTMENTS: self.handle_client_view_appointments,
            ConversationState.CLIENT_APPOINTMENT_DETAIL: self.handle_client_appointment_detail,
            ConversationState.CLIENT_CANCEL_APPOINTMENT: self.handle_client_cancel_appointment,
            ConversationState.CLIENT_CANCEL_REASON: self.handle_client_cancel_reason,
            ConversationState.CLIENT_CANCEL_SUCCESS: self.handle_client_cancel_success,

            # Estados de reprogramación del cliente
            ConversationState.CLIENT_RESCHEDULE_APPOINTMENT: self.handle_client_reschedule_appointment,
            ConversationState.CLIENT_RESCHEDULE_SELECT_DATE: self.handle_client_reschedule_select_date,
            ConversationState.CLIENT_RESCHEDULE_SELECT_TIME: self.handle_client_reschedule_select_time,
            ConversationState.CLIENT_RESCHEDULE_CONFIRM: self.handle_client_reschedule_confirm,

        }

        return handlers.get(state, self.handle_unknown_state)

    # ==========================================
    # HANDLERS INICIALES (COMPARTIDOS)
    # ==========================================

    def handle_start(self, session: SessionData, message: str) -> str:
        """Maneja estado inicial - mostrar mensaje de bienvenida."""
        session.transition_to(ConversationState.ROLE_SELECTION)
        return common_messages.WELCOME

    def handle_role_selection(self, session: SessionData, message: str) -> str:
        """Handle role selection - professional or client."""
        if message == '1':
            # Cliente
            session.set_role(UserRole.CLIENT)
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return client_messages.CLIENT_MAIN_MENU

        elif message == '2':
            # Usuario seleccionó opción 2 = PROFESIONAL
            session.set_role(UserRole.PROFESSIONAL)

            # Verificar si ya tiene acceso autorizado
            from src.database.database import db
            prof = db.get_professional(session.phone_number)

            # Si existe y tiene datos completos, ir directo al menú
            if prof and prof.get('name') and prof.get('name') != 'Usuario Nuevo':
                print(
                    f"[BOT] Profesional completamente registrado: {session.phone_number}")
                session.transition_to(ConversationState.PROF_MAIN_MENU)
                return professional_messages.PROF_MAIN_MENU
            else:
                # No está registrado o está incompleto → pedir clave
                print(
                    f"[BOT] Profesional nuevo o incompleto, requiere clave: {session.phone_number}")
                session.transition_to(ConversationState.PROF_NEED_ACCESS_KEY)
                return professional_messages.PROF_NEED_ACCESS_KEY

        else:
            return common_messages.INVALID_ROLE

    # ==========================================
    # COMANDOS GLOBALES
    # ==========================================

    def handle_return_to_menu(self, session: SessionData) -> str:
        """
        Maneja comando de volver al menú.

        Limpia datos temporales y retorna al menú principal
        según el rol del usuario.
        """
        session.clear_temp()

        if session.role == UserRole.PROFESSIONAL:
            session.transition_to(ConversationState.PROF_MAIN_MENU)
            return professional_messages.PROF_MAIN_MENU
        elif session.role == UserRole.CLIENT:
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return client_messages.CLIENT_MAIN_MENU
        else:
            session.reset()
            return common_messages.WELCOME

    def handle_cancel(self, session: SessionData) -> str:
        """
        Maneja comando de cancelar.

        Cancela operación actual y vuelve al menú.
        """
        session.clear_temp()
        return self.handle_return_to_menu(session)

    def handle_unknown_state(self, session: SessionData, message: str) -> str:
        """Maneja estado desconocido/no implementado."""
        print(f"⚠️ Estado desconocido: {session.state}")
        return common_messages.ERROR_GENERIC

    # ==========================================
    # DELEGACIÓN A HANDLERS
    # ==========================================
    # Los siguientes métodos delegan a los handlers específicos

    # === PROFESIONAL ===

    # def handle_prof_need_certificate(self, session: SessionData, message: str) -> str:
    #     """Delega a professional_handler"""
    #     return self.professional_handler.handle_prof_need_certificate(session, message)

    def handle_prof_need_access_key(self, session: SessionData, message: str) -> str:
        """
        Delega a professional_handler - Validación de clave de acceso.

        El profesional DEBE ingresar una clave válida antes de acceder al sistema.
        """
        return self.professional_handler.handle_prof_need_access_key(session, message)

    def handle_prof_main_menu(self, session: SessionData, message: str) -> str:
        """Delega a professional_handler"""
        return self.professional_handler.handle_prof_main_menu(session, message)

    def handle_prof_free_slot_date(self, session: SessionData, message: str) -> str:
        """Delega a professional_handler"""
        return self.professional_handler.handle_prof_free_slot_date(session, message)

    def handle_prof_free_slot_time(self, session: SessionData, message: str) -> str:
        """Delega a professional_handler"""
        return self.professional_handler.handle_prof_free_slot_time(session, message)

    def handle_prof_free_slot_confirm(self, session: SessionData, message: str) -> str:
        """Delega a professional_handler"""
        return self.professional_handler.handle_prof_free_slot_confirm(session, message)

    def handle_prof_week_schedule_quick(self, session: SessionData, message: str) -> str:
        """Delega a professional_handler"""
        return self.professional_handler.handle_prof_week_schedule_quick(session, message)

    def handle_prof_manage_free_slots(self, session: SessionData, message: str) -> str:
        """Delega a professional_handler"""
        return self.professional_handler.handle_prof_manage_free_slots(session, message)

    def handle_prof_delete_free_slot(self, session: SessionData, message: str) -> str:
        """Delega a professional_handler"""
        return self.professional_handler.handle_prof_delete_free_slot(session, message)

    def handle_prof_view_appointments(self, session: SessionData, message: str) -> str:
        """Delega a professional_handler - Ver citas del profesional"""
        return self.professional_handler.handle_prof_view_appointments(session, message)

    def handle_prof_info_menu(self, session: SessionData, message: str) -> str:
        """Delega a professional_handler"""
        return self.professional_handler.handle_prof_info_menu(session, message)

    def handle_prof_info_name(self, session: SessionData, message: str) -> str:
        """Delega a professional_handler"""
        return self.professional_handler.handle_prof_info_name(session, message)

    def handle_prof_info_email(self, session: SessionData, message: str) -> str:
        """Delega a professional_handler"""
        return self.professional_handler.handle_prof_info_email(session, message)

    def handle_prof_info_zona(self, session: SessionData, message: str) -> str:
        """Delega a professional_handler"""
        return self.professional_handler.handle_prof_info_zona(session, message)

    def handle_prof_info_genero(self, session: SessionData, message: str) -> str:
        """Delega a professional_handler"""
        return self.professional_handler.handle_prof_info_genero(session, message)

    def handle_prof_info_prepaga(self, session: SessionData, message: str) -> str:
        """Delega a professional_handler"""
        return self.professional_handler.handle_prof_info_prepaga(session, message)

    def handle_prof_info_especialidad(self, session: SessionData, message: str) -> str:
        """Delega a professional_handler"""
        return self.professional_handler.handle_prof_info_especialidad(session, message)

    def handle_prof_info_quick(self, session: SessionData, message: str) -> str:
        """Delega a professional_handler"""
        return self.professional_handler.handle_prof_info_quick(session, message)

    def handle_prof_info_bio(self, session: SessionData, message: str) -> str:
        """Delega a professional_handler"""
        return self.professional_handler.handle_prof_info_bio(session, message)

    def handle_prof_info_fee_range(self, session: SessionData, message: str) -> str:
        """Delega a professional_handler"""
        return self.professional_handler.handle_prof_info_fee_range(session, message)

    # === CLIENTE ===
    # === CLIENTE ===

    def handle_client_main_menu(self, session: SessionData, message: str) -> str:
        """Delega a client_handler"""
        return self.client_handler.handle_client_main_menu(session, message)

    def handle_client_new_user_menu(self, session: SessionData, message: str) -> str:
        """Delega a client_handler - Menú especial para usuarios nuevos"""
        return self.client_handler.handle_client_new_user_menu(session, message)

    def handle_client_filter_zona(self, session: SessionData, message: str) -> str:
        """Delega a client_handler"""
        return self.client_handler.handle_client_filter_zona(session, message)

    def handle_client_filter_fecha(self, session: SessionData, message: str) -> str:
        """Delega a client_handler"""
        return self.client_handler.handle_client_filter_fecha(session, message)

    def handle_client_filter_hora(self, session: SessionData, message: str) -> str:
        """Delega a client_handler"""
        return self.client_handler.handle_client_filter_hora(session, message)

    def handle_client_filter_prepaga(self, session: SessionData, message: str) -> str:
        """Delega a client_handler"""
        return self.client_handler.handle_client_filter_prepaga(session, message)

    def handle_client_filter_sexo(self, session: SessionData, message: str) -> str:
        """Delega a client_handler"""
        return self.client_handler.handle_client_filter_sexo(session, message)

    def handle_client_show_results(self, session: SessionData, message: str) -> str:
        """Delega a client_handler"""
        return self.client_handler.handle_client_show_results(session, message)

    def handle_client_view_detail(self, session: SessionData, message: str) -> str:
        """Delega a client_handler"""
        return self.client_handler.handle_client_view_detail(session, message)

    def handle_client_multifilter_menu(self, session: SessionData, message: str) -> str:
        """Delega a client_handler"""
        return self.client_handler.handle_client_multifilter_menu(session, message)

    def handle_client_multifilter_zona(self, session: SessionData, message: str) -> str:
        """Delega a client_handler"""
        return self.client_handler.handle_client_multifilter_zona(session, message)

    def handle_client_multifilter_fecha(self, session: SessionData, message: str) -> str:
        """Delega a client_handler"""
        return self.client_handler.handle_client_multifilter_fecha(session, message)

    def handle_client_multifilter_hora(self, session: SessionData, message: str) -> str:
        """Delega a client_handler"""
        return self.client_handler.handle_client_multifilter_hora(session, message)

    def handle_client_multifilter_prepaga(self, session: SessionData, message: str) -> str:
        """Delega a client_handler"""
        return self.client_handler.handle_client_multifilter_prepaga(session, message)
    
    def handle_client_multifilter_especialidad(self, session: SessionData, message: str) -> str:
        """Delegar a client_handler."""
        return self.client_handler.handle_client_multifilter_especialidad(session, message)

    def handle_client_multifilter_sexo(self, session: SessionData, message: str) -> str:
        """Delega a client_handler"""
        return self.client_handler.handle_client_multifilter_sexo(session, message)

    def handle_client_search_quick(self, session: SessionData, message: str) -> str:
        """Delega a client_handler"""
        return self.client_handler.handle_client_search_quick(session, message)

    def handle_client_view_appointments(self, session: SessionData, message: str) -> str:
        """Delega a client_handler"""
        return self.client_handler.handle_client_view_appointments(session, message)

    def handle_client_appointment_detail(self, session: SessionData, message: str) -> str:
        """Delega a client_handler"""
        return self.client_handler.handle_client_appointment_detail(session, message)

    def handle_client_cancel_appointment(self, session: SessionData, message: str) -> str:
        """Delega a client_handler"""
        return self.client_handler.handle_client_cancel_appointment(session, message)

    def handle_client_cancel_reason(self, session: SessionData, message: str) -> str:
        """Delega a client_handler"""
        return self.client_handler.handle_client_cancel_reason(session, message)

    def handle_client_cancel_success(self, session: SessionData, message: str) -> str:
        """Delega a client_handler"""
        return self.client_handler.handle_client_cancel_success(session, message)

    def handle_client_reschedule_appointment(self, session: SessionData, message: str) -> str:
        """Delega a client_handler"""
        return self.client_handler.handle_client_reschedule_appointment(session, message)

    def handle_client_reschedule_select_date(self, session: SessionData, message: str) -> str:
        """Delega a client_handler"""
        return self.client_handler.handle_client_reschedule_select_date(session, message)

    def handle_client_reschedule_select_time(self, session: SessionData, message: str) -> str:
        """Delega a client_handler"""
        return self.client_handler.handle_client_reschedule_select_time(session, message)

    def handle_client_reschedule_confirm(self, session: SessionData, message: str) -> str:
        """Delega a client_handler"""
        return self.client_handler.handle_client_reschedule_confirm(session, message)


# ==========================================
# INSTANCIA GLOBAL
# ==========================================
bot_controller = BotController()
