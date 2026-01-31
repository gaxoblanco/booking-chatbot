"""
Bot Controller v3.0
===================
Orquestador principal del bot. Procesa mensajes entrantes y delega a handlers específicos.

CAMBIOS EN v3.0:
- ❌ Eliminado: ROLE_SELECTION (ya no preguntamos "¿Eres cliente o profesional?")
- ❌ Eliminado: Flujo de registro de profesionales (se cargan manualmente por admin)
- ❌ Eliminado: Sistema de claves de acceso para profesionales
- ✅ Simplificado: Solo flujo de CLIENTES
- ✅ Automático: Reconocimiento inteligente de usuarios
- ✅ Google Calendar: Profesionales gestionan agenda desde Google Calendar

Este archivo es el cerebro del bot:
- Recibe mensajes de WhatsApp
- Identifica usuarios automáticamente
- Detecta intenciones (cliente vs profesional)
- Maneja comandos globales
- Delega a client_handler para todo el flujo de clientes
- Profesionales registrados tienen acceso a su menú directo

Responsabilidades:
- Router principal (process_message)
- Comandos globales (hola, menu, cancelar, ayuda)
- Delegación a handlers
- Integración con user_service
"""

from src.bot.professional_handler import ProfessionalHandler
from src.bot.client_handler import ClientHandler
from src.config.filter_config import FeatureFlags
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


class BotController:
    """
    Controlador principal del bot v3.0.

    Maneja el flujo de mensajes y delega a handlers específicos.
    Integra reconocimiento inteligente de usuarios.
    
    FLUJO SIMPLIFICADO v3.0:
    - Clientes: Búsqueda, reserva, gestión de citas
    - Profesionales: Solo los registrados manualmente pueden acceder a su menú
    - No hay registro de profesionales desde el bot
    """

    def __init__(self):
        """Inicializar controlador del bot."""
        # Handlers específicos
        self.client_handler = ClientHandler()
        self.professional_handler = ProfessionalHandler()

    def process_message(self, phone_number: str, message: str) -> str:
        """
        Procesa mensaje entrante y retorna respuesta.

        Este es el método principal del bot. Recibe cada mensaje de WhatsApp
        y lo procesa según el estado actual de la conversación.

        FLUJO v3.0:
        1. Identificar usuario automáticamente → user_service
        2. Verificar comandos globales (hola, menu, cancelar)
        3. Delegar a handler específico según rol

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

        # ==========================================
        # 2.5 RESPUESTAS A RECORDATORIOS
        # ==========================================
        # if should_handle_as_reminder(session, message):
        #     return handle_reminder_response(session, message)

        # Limpiar mensaje
        message = message.strip()
        message_lower = message.lower()

        # ==========================================
        # 3. SUPER COMANDO: "HOLA" SIEMPRE RESETEA
        # ==========================================
        # Sin importar el estado, "hola" reinicia la conversación
        if message_lower in ['hola', 'hello', 'hi', 'hey', 'buenos días', 'buenas tardes', 'buenas noches']:

            # Resetear sesión
            session.reset()
            
            # ==========================================
            # CASO 1: PROFESIONAL REGISTRADO
            # ==========================================
            if user_info['user_type'] == 'professional':
                session.set_role(UserRole.PROFESSIONAL)
                session.transition_to(ConversationState.PROF_MAIN_MENU)
                
                # Mensaje personalizado
                greeting = f"¡Hola Dr/Dra. {user_info['name']}! 👋\n\n" if user_info['name'] else "¡Hola! 👋\n\n"
                return greeting + professional_messages.PROF_MAIN_MENU

            # ==========================================
            # CASO 2: CLIENTE (registrado o nuevo)
            # ==========================================
            else:
                # Siempre asumir rol de CLIENTE
                session.set_role(UserRole.CLIENT)
                session.transition_to(ConversationState.CLIENT_MAIN_MENU)
                
                # Generar mensaje de bienvenida personalizado
                user_info['phone_number'] = phone_number
                return user_service.generate_welcome_message(user_info)

        # ==========================================
        # 4. COMANDOS GLOBALES (funcionan desde cualquier estado)
        # ==========================================

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
        # 5. ENRUTAR A HANDLER SEGÚN ESTADO
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
            # ❌ ELIMINADO en v3.0: ROLE_SELECTION ya no existe

            # ===== ESTADOS DE PROFESIONAL =====
            # Solo para profesionales registrados manualmente
            ConversationState.PROF_MAIN_MENU: self.professional_handler.handle_prof_main_menu,
            ConversationState.PROF_VIEW_APPOINTMENTS: self.professional_handler.handle_prof_view_appointments,
            
            # Estados de información del profesional
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

            # ===== ESTADOS DE CLIENTE =====
            ConversationState.CLIENT_MAIN_MENU: self.client_handler.handle_client_main_menu,
            ConversationState.CLIENT_NEW_USER_MENU: self.client_handler.handle_client_main_menu,
            
            # Estados de búsqueda y filtros
            ConversationState.CLIENT_MULTIFILTER_MENU: self.client_handler.handle_client_multifilter_menu,
            ConversationState.CLIENT_FILTER_INPUT: self.client_handler.handle_client_filter_input,
            ConversationState.CLIENT_SEARCH_QUICK: self.client_handler.handle_client_search_quick,
            ConversationState.CLIENT_SHOW_RESULTS: self.client_handler.handle_client_show_results,
            ConversationState.CLIENT_VIEW_DETAIL: self.client_handler.handle_client_view_detail,

            # Estados de reserva del cliente
            ConversationState.CLIENT_VIEW_DETAIL_WITH_BOOKING: self.client_handler.handle_client_view_detail_with_booking,
            ConversationState.CLIENT_CONFIRM_BOOKING: self.client_handler.handle_client_confirm_booking,
            ConversationState.CLIENT_BOOKING_CONFIRMED: self.client_handler.handle_client_booking_confirmed,

            # Estados de gestión de citas del cliente
            ConversationState.CLIENT_VIEW_APPOINTMENTS: self.client_handler.handle_client_view_appointments,
            ConversationState.CLIENT_APPOINTMENT_DETAIL: self.client_handler.handle_client_appointment_detail,
            ConversationState.CLIENT_CANCEL_APPOINTMENT: self.client_handler.handle_client_cancel_appointment,
            ConversationState.CLIENT_CANCEL_REASON: self.client_handler.handle_client_cancel_reason,
            ConversationState.CLIENT_CANCEL_SUCCESS: self.client_handler.handle_client_cancel_success,

            # Estados de reprogramación del cliente
            ConversationState.CLIENT_RESCHEDULE_APPOINTMENT: self.client_handler.handle_client_reschedule_appointment,
            ConversationState.CLIENT_RESCHEDULE_SELECT_DATE: self.client_handler.handle_client_reschedule_select_date,
            ConversationState.CLIENT_RESCHEDULE_SELECT_TIME: self.client_handler.handle_client_reschedule_select_time,
            ConversationState.CLIENT_RESCHEDULE_CONFIRM: self.client_handler.handle_client_reschedule_confirm,
        }

        return handlers.get(state, self.handle_unknown_state)

    # ==========================================
    # HANDLERS INICIALES
    # ==========================================

    def handle_start(self, session: SessionData, message: str) -> str:
        """
        Maneja estado inicial.
        
        En v3.0 ya no preguntamos rol, asumimos CLIENTE por defecto.
        Los profesionales registrados se identifican automáticamente.
        """
        session.set_role(UserRole.CLIENT)
        session.transition_to(ConversationState.CLIENT_MAIN_MENU)
        
        user_info = user_service.identify_user(session.phone_number)
        user_info['phone_number'] = session.phone_number
        
        return user_service.generate_welcome_message(user_info)

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
        else:
            # Por defecto, asumir cliente
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            user_info = user_service.identify_user(session.phone_number)
            user_info['phone_number'] = session.phone_number
            return user_service.generate_welcome_message(user_info)

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
        return common_messages.ERROR_UNKNOWN_STATE + "\n\n" + self.handle_return_to_menu(session)


# ==========================================
# INSTANCIA GLOBAL
# ==========================================
bot_controller = BotController()