"""
Bot Logic
=========
Main conversation handler with state machine implementation.
Processes incoming messages and manages conversation flow.
"""
from domain_config import DomainConfig
from states import (
    ConversationState,
    UserRole,
    session_manager,
    SessionData
)
from messages import Messages
from validators import (
    validate_date,
    validate_time_range,
    validate_option,
    parse_date,
    parse_time_range,
    # IMPORTS PSIVALE
    validate_enfoque,
    normalize_enfoque,
    parse_enfoque_list,
    validate_poblacion,
    normalize_poblacion,
    parse_poblacion_list,
    validate_modalidad,
    normalize_modalidad,
    validate_horarios,
    normalize_horario,
    parse_horarios_list,
    validate_fee_range,
    normalize_fee_range,
    validate_zona_psivale,
    normalize_zona_psivale,
)
from client_service import client_service
from professional_service import professional_service
from analytics_service import analytics_service
from client_service import client_service
from analytics_service import analytics_service
import validators


class Bot:
    """
    Main bot logic handler.
    Implements state machine for conversation management.
    """

    def __init__(self):
        """Initialize bot."""
        self.messages = Messages()

    def process_message(self, phone_number: str, message: str) -> str:
        """
        Process incoming message and return response.
        """
        # Get or create session
        session = session_manager.get_session(phone_number)

        # Clean message
        message = message.strip()
        message_lower = message.lower()

        # ==========================================
        # ⭐ PSIVALE: DETECCIÓN "SOY PSICÓLOGO" (PRIMERO)
        # ==========================================
        if any(phrase in message_lower for phrase in [
            'soy psicologo', 'soy psicólogo',
            'soy psico', 'psicologo aqui', 'psicólogo aquí',
            'hola soy psicologo', 'hola soy psicólogo', 'soy psicologa', 'soy psicóloga', 'psicologo aqui', 'psicólogo aquí',
            'hola soy psicologa', 'hola soy psicóloga'
        ]):
            session.reset()
            session.set_role(UserRole.PROFESSIONAL)

            # ⭐ NUEVO: Verificar si ya tiene certificado
            if professional_service.has_certificate(phone_number):
                # Ya está registrado - ir a menú
                session.transition_to(ConversationState.PROF_MAIN_MENU)
                return "💚 ¡Hola de nuevo! Ya estás registrado en PSIVALE.\n\n" + self.messages.PROF_MAIN_MENU
            else:
                # ⭐ NO registrado - ir a confirmación de registro
                session.transition_to(ConversationState.PROF_REGISTER_CONFIRM)
                return self.messages.PSIVALE_PROF_REGISTER_CONFIRM
        # ==========================================
        # SUPER COMMAND: "HOLA" ALWAYS RESETS
        # ==========================================
        if message_lower in ['hola', 'hello', 'hi', 'hey']:
            session.reset()
            # Asumir que es paciente por defecto
            session.set_role(UserRole.CLIENT)
            session.transition_to(ConversationState.CLIENT_ASESORADO_WELCOME)
            return self.messages.WELCOME

        # ==========================================
        # CERTIFICATE GATE - BLOCKS EVERYTHING
        # ==========================================
        # If professional hasn't uploaded certificate, block ALL commands
        if session.state == ConversationState.PROF_NEED_CERTIFICATE:
            # Allow 'inicio' to restart and choose role again
            if message_lower in ['inicio', 'start', 'restart', 'empezar']:
                session.reset()
                session.transition_to(ConversationState.ROLE_SELECTION)
                return self.messages.WELCOME

            # Allow '0' to go back to role selection
            if message == '0':
                session.reset()
                session.transition_to(ConversationState.ROLE_SELECTION)
                return self.messages.WELCOME

            # Block everything else (menu, cancelar, ayuda, etc.)
            return self.messages.PROF_NEED_CERTIFICATE

        # ==========================================
        # GLOBAL COMMANDS (work from anywhere EXCEPT certificate gate)
        # ==========================================

        # Reset to start (choose role again)
        if message_lower in ['inicio', 'start', 'restart', 'empezar']:
            session.reset()
            return self.messages.WELCOME

        # Return to role-specific menu
        if message_lower in ['menu', 'menú', 'volver']:
            return self.handle_return_to_menu(session)

        # Cancel current operation
        if message_lower in ['cancelar', 'cancel', 'salir']:
            return self.handle_cancel(session)

        # Help
        if message_lower in ['ayuda', 'help', '?']:
            return self.messages.HELP_MESSAGE

        # ==========================================
        # ROUTE TO STATE HANDLER
        # ==========================================

        # Route to appropriate handler based on current state
        handler = self.get_handler_for_state(session.state)

        try:
            response = handler(session, message)
            return response
        except Exception as e:
            print(f"❌ Error processing message: {str(e)}")
            import traceback
            traceback.print_exc()
            return self.messages.ERROR_GENERIC

    def get_handler_for_state(self, state: ConversationState):
        """Get the appropriate handler function for a state."""
        handlers = {
            # Initial states
            ConversationState.START: self.handle_start,
            # ConversationState.ROLE_SELECTION: self.handle_role_selection,

            # Professional states
            ConversationState.PROF_REGISTER_CONFIRM: self.handle_prof_register_confirm,
            ConversationState.PROF_NEED_CERTIFICATE: self.handle_prof_need_certificate,
            ConversationState.PROF_MAIN_MENU: self.handle_prof_main_menu,
            ConversationState.PROF_FREE_SLOT_DATE: self.handle_prof_free_slot_date,
            ConversationState.PROF_FREE_SLOT_TIME: self.handle_prof_free_slot_time,
            ConversationState.PROF_FREE_SLOT_CONFIRM: self.handle_prof_free_slot_confirm,
            ConversationState.PROF_WEEK_SCHEDULE_QUICK: self.handle_prof_week_schedule_quick,

            # Professional info states
            ConversationState.PROF_INFO_MENU: self.handle_prof_info_menu,
            ConversationState.PROF_INFO_NAME: self.handle_prof_info_name,
            ConversationState.PROF_INFO_EMAIL: self.handle_prof_info_email,
            ConversationState.PROF_INFO_ZONA: self.handle_prof_info_zona,
            ConversationState.PROF_INFO_GENERO: self.handle_prof_info_genero,
            # ConversationState.PROF_INFO_PREPAGA: self.handle_prof_info_prepaga,
            # ConversationState.PROF_INFO_ESPECIALIDAD: self.handle_prof_info_especialidad,
            ConversationState.PROF_INFO_QUICK: self.handle_prof_info_quick,
            ConversationState.PROF_INFO_BIO: self.handle_prof_info_bio,
            ConversationState.PROF_INFO_FEE_RANGE: self.handle_prof_info_fee_range,

            # ⭐ NUEVOS HANDLERS PSIVALE - PROFESIONAL
            ConversationState.PROF_INFO_ENFOQUE: self.handle_prof_info_enfoque,
            ConversationState.PROF_INFO_POBLACION: self.handle_prof_info_poblacion,
            ConversationState.PROF_INFO_MODALIDAD: self.handle_prof_info_modalidad,
            ConversationState.PROF_INFO_HORARIOS: self.handle_prof_info_horarios,

            # Client states (existentes)
            # ConversationState.CLIENT_MAIN_MENU: self.handle_client_main_menu,
            # ConversationState.CLIENT_FILTER_ZONA: self.handle_client_filter_zona,
            # ConversationState.CLIENT_FILTER_FECHA: self.handle_client_filter_fecha,
            # ConversationState.CLIENT_FILTER_HORA: self.handle_client_filter_hora,
            # ConversationState.CLIENT_FILTER_PREPAGA: self.handle_client_filter_prepaga,
            # ConversationState.CLIENT_FILTER_SEXO: self.handle_client_filter_sexo,
            ConversationState.CLIENT_SHOW_RESULTS: self.handle_client_show_results,
            ConversationState.CLIENT_VIEW_DETAIL: self.handle_client_view_detail,

            # Client multi-filter
            ConversationState.CLIENT_MULTIFILTER_MENU: self.handle_client_multifilter_menu,
            ConversationState.CLIENT_MULTIFILTER_ZONA: self.handle_client_multifilter_zona,
            ConversationState.CLIENT_MULTIFILTER_FECHA: self.handle_client_multifilter_fecha,
            ConversationState.CLIENT_MULTIFILTER_HORA: self.handle_client_multifilter_hora,
            ConversationState.CLIENT_MULTIFILTER_PREPAGA: self.handle_client_multifilter_prepaga,
            ConversationState.CLIENT_MULTIFILTER_SEXO: self.handle_client_multifilter_sexo,
            ConversationState.CLIENT_SEARCH_QUICK: self.handle_client_search_quick,

            # ⭐ NUEVOS HANDLERS PSIVALE - CLIENTE (FLUJO ASESORADO)
            ConversationState.CLIENT_ASESORADO_WELCOME: self.handle_client_asesorado_welcome,
            # ConversationState.CLIENT_ASESORADO_INTENCION: self.handle_client_asesorado_intencion,
            ConversationState.CLIENT_ASESORADO_ENFOQUE: self.handle_client_asesorado_enfoque,
            ConversationState.CLIENT_ASESORADO_POBLACION: self.handle_client_asesorado_poblacion,
            ConversationState.CLIENT_ASESORADO_MODALIDAD: self.handle_client_asesorado_modalidad,
            ConversationState.CLIENT_ASESORADO_ZONA: self.handle_client_asesorado_zona,
            ConversationState.CLIENT_ASESORADO_HORARIOS: self.handle_client_asesorado_horarios,
            ConversationState.CLIENT_ASESORADO_HONORARIOS: self.handle_client_asesorado_honorarios,
            ConversationState.CLIENT_ASESORADO_RESUMEN: self.handle_client_asesorado_resumen,
            ConversationState.CLIENT_ASESORADO_BUSCANDO: self.handle_client_asesorado_buscando,
        }

        return handlers.get(state, self.handle_unknown_state)
    # ==========================================
    # INITIAL HANDLERS
    # ==========================================

    def handle_start(self, session: SessionData, message: str) -> str:
        """Handle start state - mostrar bienvenida Vale directamente."""
        session.set_role(UserRole.CLIENT)  # Por defecto es paciente
        session.transition_to(ConversationState.CLIENT_ASESORADO_WELCOME)
        return self.messages.WELCOME

    # def handle_role_selection(self, session: SessionData, message: str) -> str:
    #     """Handle role selection - professional or client."""
    #     if message == '1':
    #         # Usuario seleccionó opción 1 = CLIENTE/PACIENTE
    #         session.set_role(UserRole.CLIENT)
    #         session.transition_to(ConversationState.CLIENT_MAIN_MENU)
    #         return self.messages.CLIENT_MAIN_MENU

    #     elif message == '2':
    #         # Usuario seleccionó opción 2 = PROFESIONAL
    #         session.set_role(UserRole.PROFESSIONAL)

    #         # Check if professional already has certificate
    #         if professional_service.has_certificate(session.phone_number):
    #             # Already has certificate - go directly to main menu
    #             print(
    #                 f"[BOT] Professional {session.phone_number} already has certificate, skipping upload")
    #             session.transition_to(ConversationState.PROF_MAIN_MENU)
    #             return self.messages.PROF_MAIN_MENU
    #         else:
    #             # No certificate - ask for upload
    #             print(
    #                 f"[BOT] Professional {session.phone_number} needs to upload certificate")
    #             session.transition_to(ConversationState.PROF_NEED_CERTIFICATE)
    #             return self.messages.PROF_NEED_CERTIFICATE

    #     else:
    #         return self.messages.INVALID_ROLE

    # ==========================================
    # PROFESSIONAL HANDLERS
    # ==========================================

    def handle_prof_register_confirm(self, session: SessionData, message: str) -> str:
        """Handle professional registration confirmation."""

        if message == '1':
            # Sí, quiero unirme → Solicitar certificado
            session.transition_to(ConversationState.PROF_NEED_CERTIFICATE)
            return self.messages.PROF_NEED_CERTIFICATE

        elif message == '2':
            # Necesito más información
            # ⭐ MANTENER en mismo estado (PROF_REGISTER_CONFIRM)
            # No cambiar de estado, solo mostrar info
            return self.messages.PSIVALE_PROF_INFO

        elif message == '0':
            # Volver al inicio
            session.reset()
            session.set_role(UserRole.CLIENT)  # ⭐ Resetear a cliente
            session.transition_to(ConversationState.CLIENT_ASESORADO_WELCOME)
            return self.messages.WELCOME

        else:
            # Opción inválida
            return self.messages.PSIVALE_OPCION_INVALIDA + "\n\n" + self.messages.PSIVALE_PROF_REGISTER_CONFIRM

    def handle_prof_need_certificate(self, session: SessionData, message: str) -> str:
        """Handle professional certificate requirement."""

        if message == '0':
            # Volver a confirmación de registro
            session.transition_to(ConversationState.PROF_REGISTER_CONFIRM)
            return self.messages.PSIVALE_PROF_REGISTER_CONFIRM

        # Si escribe cualquier cosa (excepto 0), recordar que debe subir archivo
        return """📎 Por favor, envía el archivo de tu matrícula.
        
        ⚠️ Debes subir una imagen o PDF (no texto).

        💡 Escribe '0' para volver"""

    def handle_prof_certificate_uploaded(self, session: SessionData) -> str:
        """
        Called from whatsapp_handler when certificate is uploaded.
        Transitions to main menu.
        """
        session.transition_to(ConversationState.PROF_MAIN_MENU)
        return self.messages.PROF_CERTIFICATE_RECEIVED + "\n\n" + self.messages.PROF_MAIN_MENU

    def handle_prof_main_menu(self, session: SessionData, message: str) -> str:
        """Handle professional main menu."""
        if message == '1':
            # Liberar horario
            session.clear_temp()
            session.transition_to(ConversationState.PROF_FREE_SLOT_DATE)
            return self.messages.PROF_FREE_SLOT_ASK_DATE

        elif message == '2':
            # Cargar semana completa
            session.clear_temp()
            session.store_temp('week_schedule', {})
            session.transition_to(ConversationState.PROF_WEEK_SCHEDULE_QUICK)
            return self.messages.PROF_WEEK_QUICK_FORMAT

        elif message == '3':
            schedule_info = professional_service.get_complete_schedule(
                session.phone_number)
            return schedule_info['formatted'] + "\n\n" + self.messages.PROF_MAIN_MENU

        elif message == '4':
            # Cargar información
            session.clear_temp()
            from database import db

            # ✅ Pre-cargar información existente de la DB
            existing_prof = db.get_professional(session.phone_number)
            if existing_prof:
                # Convertir los datos de DB a formato de prof_info
                prof_info = {
                    'name': existing_prof.get('name'),
                    'email': existing_prof.get('email'),
                    'zone': existing_prof.get('zone'),
                    'gender': existing_prof.get('gender'),
                    'enfoque_terapeutico': existing_prof.get('enfoque_terapeutico', []),
                    'poblacion': existing_prof.get('poblacion', []),
                    'modalidad': existing_prof.get('modalidad'),
                    'horarios_disponibles': existing_prof.get('horarios_disponibles', []),
                    'bio': existing_prof.get('bio'),
                    'fee_range': existing_prof.get('fee_range')
                }
                session.store_temp('prof_info', prof_info)
            else:
                # Si no existe, inicializar vacío
                session.store_temp('prof_info', {})

            session.transition_to(ConversationState.PROF_INFO_MENU)
            return self.format_prof_info_menu(session)

        elif message == '5':
            # Carga rápida
            session.clear_temp()
            session.transition_to(ConversationState.PROF_INFO_QUICK)
            return self.messages.PROF_INFO_QUICK_FORMAT

        elif message == '0':
            session.reset()
            return self.messages.WELCOME

        else:
            return self.messages.INVALID_OPTION + "\n\n" + self.messages.PROF_MAIN_MENU

    def format_prof_info_menu(self, session: SessionData) -> str:
        """Format professional info menu with current data."""
        prof_info = session.get_temp('prof_info', {})

        if not prof_info:
            current_info = "(ninguno)"
        else:
            info_lines = []
            if 'name' in prof_info:
                info_lines.append(f"👤 {prof_info['name']}")
            if 'email' in prof_info:
                info_lines.append(f"📧 {prof_info['email']}")
            if 'zone' in prof_info:  # ← CAMBIAR: era 'zona'
                info_lines.append(f"📍 Zona {prof_info['zone'].capitalize()}")
            if 'gender' in prof_info:  # ← CAMBIAR: era 'genero'
                genero_map = {'m': 'Masculino', 'f': 'Femenino', 'o': 'Otro'}
                info_lines.append(
                    f"👥 {genero_map.get(prof_info['gender'], prof_info['gender'])}")
            if 'accept_prepaga' in prof_info:  # ← CAMBIAR: era 'prepaga'
                info_lines.append(
                    f"💳 Prepaga: {'Sí' if prof_info['accept_prepaga'] else 'No'}")
            if 'especialidad' in prof_info:
                info_lines.append(f"🏥 {prof_info['especialidad']}")
            if 'bio' in prof_info:  # ← AGREGAR
                bio_preview = prof_info['bio'][:40] + \
                    "..." if len(prof_info['bio']) > 40 else prof_info['bio']
                info_lines.append(f"📝 {bio_preview}")
            if 'fee_range' in prof_info:  # ← AGREGAR
                info_lines.append(f"💰 ${prof_info['fee_range']}")

            current_info = "\n".join(info_lines) if info_lines else "(ninguno)"

        return self.messages.PROF_INFO_MENU.format(current_info=current_info)

    # handle_prof_info_menu para incluir opciones Psivale:
    def handle_prof_info_menu(self, session: SessionData, message: str) -> str:
        """Handle professional info menu selection."""

        # Comando especial: guardar
        if message.lower() == 'guardar':
            return self._save_professional_info(session)

        # Opciones del menú
        if message == '1':
            session.transition_to(ConversationState.PROF_INFO_NAME)
            return self.messages.PROF_INFO_ASK_NAME

        elif message == '2':
            session.transition_to(ConversationState.PROF_INFO_EMAIL)
            return self.messages.PROF_INFO_ASK_EMAIL

        elif message == '3':
            session.transition_to(ConversationState.PROF_INFO_ZONA)
            return self.messages.PROF_INFO_ASK_ZONA

        elif message == '4':
            session.transition_to(ConversationState.PROF_INFO_GENERO)
            return self.messages.PROF_INFO_ASK_GENERO

        elif message == '5':
            # ⭐ ENFOQUE (antes era prepaga)
            session.transition_to(ConversationState.PROF_INFO_ENFOQUE)
            return self.messages.PROF_INFO_ASK_ENFOQUE

        elif message == '6':
            # ⭐ POBLACIÓN (antes era especialidad)
            session.transition_to(ConversationState.PROF_INFO_POBLACION)
            return self.messages.PROF_INFO_ASK_POBLACION

        elif message == '7':
            # ⭐ MODALIDAD (antes era campo abierto/bio)
            session.transition_to(ConversationState.PROF_INFO_MODALIDAD)
            return self.messages.PROF_INFO_ASK_MODALIDAD

        elif message == '8':
            # ⭐ HORARIOS (antes era honorarios)
            session.transition_to(ConversationState.PROF_INFO_HORARIOS)
            return self.messages.PROF_INFO_ASK_HORARIOS

        elif message == '9':
            # ⭐ BIO (campo abierto)
            session.transition_to(ConversationState.PROF_INFO_BIO)
            return self.messages.PROF_INFO_ASK_BIO

        elif message == '10':
            # ⭐ HONORARIOS
            session.transition_to(ConversationState.PROF_INFO_FEE_RANGE)
            return self.messages.PROF_INFO_ASK_FEE_RANGE

        elif message == '0':
            session.transition_to(ConversationState.PROF_MAIN_MENU)
            return self.messages.PROF_MAIN_MENU

        else:
            return "❌ Opción inválida.\n\n" + self.format_prof_info_menu_psivale(session)

    def handle_prof_info_name(self, session: SessionData, message: str) -> str:
        """Handle name input."""
        if message == '0':
            session.transition_to(ConversationState.PROF_INFO_MENU)
            return self.format_prof_info_menu_psivale(session)

        # Validar longitud
        from validators import validate_name_length, validate_text_not_empty

        if not validate_text_not_empty(message):
            return "❌ El nombre no puede estar vacío.\n\n💡 Escribe '0' para volver"

        if not validate_name_length(message):
            return "❌ El nombre debe tener entre 3 y 100 caracteres.\n\n💡 Escribe '0' para volver"

        # Store name
        prof_info = session.get_temp('prof_info', {})
        prof_info['name'] = message.strip()
        session.store_temp('prof_info', prof_info)

        session.transition_to(ConversationState.PROF_INFO_MENU)
        return f"✅ Nombre guardado: {message.strip()}\n\n" + self.format_prof_info_menu_psivale(session)

    def handle_prof_info_email(self, session: SessionData, message: str) -> str:
        """Handle email input."""
        if message == '0':
            session.transition_to(ConversationState.PROF_INFO_MENU)
            return self.format_prof_info_menu_psivale(session)

        # Validar formato de email
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

        from validators import validate_email_length, validate_text_not_empty

        if not validate_text_not_empty(message):
            return "❌ El email no puede estar vacío.\n\n💡 Escribe '0' para volver"

        if not validate_email_length(message):
            return "❌ El email debe tener entre 5 y 100 caracteres.\n\n💡 Escribe '0' para volver"

        if not re.match(email_pattern, message.strip()):
            return "❌ Email inválido. Intenta nuevamente:\nEjemplo: juan@email.com"

        # Store email
        prof_info = session.get_temp('prof_info', {})
        prof_info['email'] = message.strip()
        session.store_temp('prof_info', prof_info)

        session.transition_to(ConversationState.PROF_INFO_MENU)
        return f"✅ Email guardado: {message.strip()}\n\n" + self.format_prof_info_menu_psivale(session)

    def handle_prof_info_zona(self, session: SessionData, message: str) -> str:
        """Handle zona input."""
        if message == '0':
            session.transition_to(ConversationState.PROF_INFO_MENU)
            return self.format_prof_info_menu_psivale(session)

        if message == '1':
            zona = 'norte'
        elif message == '2':
            zona = 'sur'
        elif message == '3':
            zona = 'nueva_cordoba'
        else:
            return self.messages.INVALID_OPTION + "\n\n" + self.messages.PROF_INFO_ASK_ZONA

        # Store zona
        prof_info = session.get_temp('prof_info', {})
        prof_info['zone'] = zona
        session.store_temp('prof_info', prof_info)

        session.transition_to(ConversationState.PROF_INFO_MENU)
        return f"✅ Zona guardada: {zona.capitalize()}\n\n" + self.format_prof_info_menu_psivale(session)

    def handle_prof_info_genero(self, session: SessionData, message: str) -> str:
        """Handle genero input."""
        if message == '0':
            session.transition_to(ConversationState.PROF_INFO_MENU)
            return self.format_prof_info_menu_psivale(session)

        if message == '1':
            genero = 'm'
        elif message == '2':
            genero = 'f'
        elif message == '3':
            genero = 'o'
        else:
            return self.messages.INVALID_OPTION + "\n\n" + self.messages.PROF_INFO_ASK_GENERO

        # Store genero
        prof_info = session.get_temp('prof_info', {})
        prof_info['gender'] = genero
        session.store_temp('prof_info', prof_info)

        genero_map = {'m': 'Masculino', 'f': 'Femenino', 'o': 'Otro'}
        session.transition_to(ConversationState.PROF_INFO_MENU)
        return f"✅ Género guardado: {genero_map[genero]}\n\n" + self.format_prof_info_menu_psivale(session)

    def handle_prof_info_especialidad(self, session: SessionData, message: str) -> str:
        """Handle especialidad input."""
        if message == '0':
            session.transition_to(ConversationState.PROF_INFO_MENU)
            return self.format_prof_info_menu_psivale(session)

        # Map number to specialty or use custom text
        especialidades = {
            '1': 'Médico General',
            '2': 'Dentista',
            '3': 'Psicólogo',
            '4': 'Kinesiólogo',
            '5': 'Nutricionista',
            '6': 'Otro'
        }

        if message in especialidades:
            if message == '6':
                # Ask for custom specialty
                return "🏥 Escribe tu especialidad:"
            especialidad = especialidades[message]
        else:
            # Custom specialty text
            especialidad = message

        # Store especialidad
        prof_info = session.get_temp('prof_info', {})
        prof_info['especialidad'] = especialidad
        session.store_temp('prof_info', prof_info)

        session.transition_to(ConversationState.PROF_INFO_MENU)
        return f"✅ Especialidad guardada: {especialidad}\n\n" + self.format_prof_info_menu_psivale(session)

    def handle_prof_info_bio(self, session: SessionData, message: str) -> str:
        """Handle bio input."""
        if message == '0':
            session.transition_to(ConversationState.PROF_INFO_MENU)
            return self.format_prof_info_menu_psivale(session)

        # Validar longitud
        from validators import validate_bio_length, validate_text_not_empty

        if not validate_text_not_empty(message):
            return "❌ La biografía no puede estar vacía.\n\n💡 Escribe '0' para volver"

        if not validate_bio_length(message):
            char_count = len(message.strip())
            if char_count < 10:
                return f"❌ La biografía es muy corta ({char_count} caracteres).\nMínimo: 10 caracteres\n\n💡 Escribe '0' para volver"
            else:
                return f"❌ La biografía es muy larga ({char_count} caracteres).\nMáximo: 500 caracteres\n\n💡 Escribe '0' para volver"

        # Guardar bio en prof_info
        prof_info = session.get_temp('prof_info', {})
        prof_info['bio'] = message.strip()
        session.store_temp('prof_info', prof_info)

        session.transition_to(ConversationState.PROF_INFO_MENU)
        return f"✅ Descripción guardada.\n\n{self.format_prof_info_menu_psivale(session)}"

    def handle_prof_info_fee_range(self, session: SessionData, message: str) -> str:
        """Handle fee range input."""
        if message == '0':
            session.transition_to(ConversationState.PROF_INFO_MENU)
            return self.format_prof_info_menu_psivale(session)

        # Validar formato: XXX-YYY
        import re
        match = re.match(r'^(\d+)-(\d+)$', message.strip())

        if not match:
            return "❌ Formato incorrecto.\n\nUsa: MÍNIMO-MÁXIMO\nEjemplo: 100-150\n\n💡 Escribe '0' para volver"

        min_fee, max_fee = match.groups()

        if int(min_fee) >= int(max_fee):
            return "❌ El mínimo debe ser menor que el máximo.\n\n💡 Escribe '0' para volver"

        # Guardar en temp
        prof_info = session.get_temp('prof_info', {})
        prof_info['fee_range'] = message
        session.store_temp('prof_info', prof_info)

        # Volver al menú
        session.transition_to(ConversationState.PROF_INFO_MENU)
        return f"✅ Honorarios guardados: ${min_fee} - ${max_fee}\n\n{self.format_prof_info_menu_psivale(session)}"

    def parse_prof_info_quick(self, message: str) -> dict:
        """
        Parse professional info from message (PSIVALE VERSION).

        Format (with labels):
            nombre: Dra. María González
            email: maria@psivale.com
            zona: norte
            genero: femenino
            enfoque: tcc, contextual
            poblacion: adultos, parejas
            modalidad: ambas
            horarios: tarde, noche
            bio: Psicóloga con enfoque cognitivo-conductual (opcional)
            honorarios: 25000-35000 (opcional)

        Returns:
            (dict with parsed info, list of errors)
        """
        import re
        from validators import (
            validate_email, normalize_zona_psivale, normalize_sexo,
            parse_enfoque_list, parse_poblacion_list, normalize_modalidad,
            parse_horarios_list, validate_fee_range, normalize_fee_range
        )

        lines = [line.strip()
                 for line in message.strip().split('\n') if line.strip()]

        # Check if using labeled format (has ':')
        has_labels = any(':' in line for line in lines)

        if not has_labels:
            return None, ["❌ Por favor usa el formato con etiquetas (nombre:, email:, etc.)"]

        result = {}
        errors = []

        # Parse labeled format
        for line in lines:
            if ':' not in line:
                continue

            key, value = line.split(':', 1)
            key = key.strip().lower()
            value = value.strip()

            # Map variations to standard keys
            if key in ['nombre', 'name', 'nom']:
                result['name'] = value
            elif key in ['email', 'correo', 'mail']:
                result['email'] = value
            elif key in ['zona', 'zone', 'area']:
                result['zone'] = value.lower()
            elif key in ['genero', 'género', 'sexo', 'gender']:
                result['gender'] = value.lower()
            elif key in ['enfoque', 'enfoques', 'approach']:
                result['enfoque'] = value.lower()
            elif key in ['poblacion', 'población', 'population']:
                result['poblacion'] = value.lower()
            elif key in ['modalidad', 'modality', 'modo']:
                result['modalidad'] = value.lower()
            elif key in ['horarios', 'horario', 'schedule']:
                result['horarios'] = value.lower()
            elif key in ['bio', 'descripcion', 'descripción', 'about']:
                result['bio'] = value
            elif key in ['honorarios', 'fee', 'precio', 'costo']:
                result['fee_range'] = value

        # ✅ VALIDAR CAMPOS OBLIGATORIOS PSIVALE
        required = ['name', 'email', 'zone', 'gender',
                    'enfoque', 'poblacion', 'modalidad']
        missing = [f for f in required if f not in result or not result[f]]

        if missing:
            missing_map = {
                'name': 'nombre',
                'email': 'email',
                'zone': 'zona',
                'gender': 'genero',
                'enfoque': 'enfoque',
                'poblacion': 'poblacion',
                'modalidad': 'modalidad'
            }
            missing_labels = [missing_map.get(f, f) for f in missing]
            errors.append(
                f"❌ Faltan campos obligatorios: {', '.join(missing_labels)}")
            return None, errors

        # ✅ VALIDAR Y NORMALIZAR CADA CAMPO

        # Email
        if not validate_email(result['email']):
            errors.append(f"❌ Email inválido: {result['email']}")

        # Zona (PSIVALE: incluye nueva_cordoba)
        normalized_zone = normalize_zona_psivale(result['zone'])
        if normalized_zone not in ['norte', 'sur', 'nueva_cordoba']:
            errors.append(
                f"❌ Zona inválida: {result['zone']} (usa: norte, sur, nueva_cordoba)")
        else:
            result['zone'] = normalized_zone

        # Género
        normalized_gender = normalize_sexo(result['gender'])
        if not normalized_gender:
            errors.append(
                f"❌ Género inválido: {result['gender']} (usa: masculino, femenino, otro)")
        else:
            result['gender'] = normalized_gender

        # Enfoque terapéutico (máximo 2)
        enfoque_list = parse_enfoque_list(result['enfoque'])
        if not enfoque_list:
            errors.append(f"❌ Enfoque inválido: {result['enfoque']}")
        else:
            result['enfoque_terapeutico'] = enfoque_list

        # Población
        poblacion_list = parse_poblacion_list(result['poblacion'])
        if not poblacion_list:
            errors.append(f"❌ Población inválida: {result['poblacion']}")
        else:
            result['poblacion'] = poblacion_list

        # Modalidad
        normalized_modalidad = normalize_modalidad(result['modalidad'])
        if normalized_modalidad not in ['online', 'presencial', 'ambas']:
            errors.append(
                f"❌ Modalidad inválida: {result['modalidad']} (usa: online, presencial, ambas)")
        else:
            result['modalidad'] = normalized_modalidad

        # Horarios (opcional, pero si viene validar)
        if 'horarios' in result and result['horarios']:
            horarios_list = parse_horarios_list(result['horarios'])
            if not horarios_list:
                errors.append(f"❌ Horarios inválidos: {result['horarios']}")
            else:
                result['horarios_disponibles'] = horarios_list
        else:
            result['horarios_disponibles'] = []

        # Validar honorarios si existe (opcional)
        if 'fee_range' in result and result['fee_range']:
            if not validate_fee_range(result['fee_range']):
                errors.append(
                    f"❌ Honorarios inválidos: {result['fee_range']} (usa formato: 15000-25000)")
            else:
                normalized_fee = normalize_fee_range(result['fee_range'])
                if normalized_fee:
                    result['fee_range'] = normalized_fee

        if errors:
            return None, errors

        return result, []

    def handle_prof_info_quick(self, session: SessionData, message: str) -> str:
        """Handle quick info input (all in one message)."""

        if message == '0':
            session.transition_to(ConversationState.PROF_MAIN_MENU)
            return self.messages.PROF_MAIN_MENU

        # Parse the message
        prof_info, errors = self.parse_prof_info_quick(message)

        if errors:
            error_msg = "\n".join(errors)
            return f"{error_msg}\n\n{self.messages.PROF_INFO_QUICK_FORMAT}"

        # Save to database
        professional_service.register_or_update_professional(
            phone=session.phone_number,
            name=prof_info.get('name'),
            email=prof_info.get('email'),
            zone=prof_info.get('zona'),
            gender=prof_info.get('genero'),
            accept_prepaga=prof_info.get('prepaga', False),
            category=prof_info.get('especialidad'),
            bio=prof_info.get('bio'),
            fee_range=prof_info.get('fee_range')
        )

        # Format summary
        genero_map = {'m': 'Masculino', 'f': 'Femenino', 'o': 'Otro'}
        summary_lines = [
            f"👤 Nombre: {prof_info['name']}",
            f"📧 Email: {prof_info['email']}",
            f"📍 Zona: {prof_info['zona'].capitalize()}",
            f"👥 Género: {genero_map[prof_info['genero']]}",
            f"💳 Prepaga: {'Sí' if prof_info['prepaga'] else 'No'}",
            f"🏥 Especialidad: {prof_info['especialidad']}"
        ]

        # Agregar opcionales si existen
        if 'bio' in prof_info:
            bio_preview = prof_info['bio'][:50] + \
                "..." if len(prof_info['bio']) > 50 else prof_info['bio']
            summary_lines.append(f"📝 Bio: {bio_preview}")
        if 'fee_range' in prof_info:
            summary_lines.append(f"💰 Honorarios: ${prof_info['fee_range']}")

        summary = "\n".join(summary_lines)

        session.clear_temp()
        session.transition_to(ConversationState.PROF_MAIN_MENU)

        return f"✅ ¡Información guardada!\n\n{summary}\n\n" + self.messages.PROF_MAIN_MENU

    def _save_professional_info(self, session: SessionData) -> str:
        """
        Save professional information (PSIVALE VERSION).
        Validates required fields before saving.
        """
        prof_info = session.get_temp('prof_info', {})
        phone = session.phone_number

        # ⭐ VALIDAR CAMPOS OBLIGATORIOS PSIVALE
        required_fields = {
            'name': 'Nombre',
            'email': 'Email',
            'zone': 'Zona',
            'gender': 'Género',
            'enfoque_terapeutico': 'Enfoque Terapéutico',
            'poblacion': 'Población',
            'modalidad': 'Modalidad'
        }

        missing = []
        for field, label in required_fields.items():
            if field not in prof_info or not prof_info[field]:
                missing.append(label)

        if missing:
            missing_str = ", ".join(missing)
            return f"""❌ Faltan campos obligatorios:

    {missing_str}

    Por favor, completá toda la información antes de guardar.

    Escribí el número de la opción para completar los campos faltantes."""

        # ⭐ GUARDAR CON CAMPOS PSIVALE
        success = professional_service.register_or_update_professional(
            phone=phone,
            name=prof_info.get('name'),
            email=prof_info.get('email'),
            zone=prof_info.get('zone'),
            gender=prof_info.get('gender'),
            enfoque_terapeutico=prof_info.get('enfoque_terapeutico'),
            poblacion=prof_info.get('poblacion'),
            modalidad=prof_info.get('modalidad'),
            horarios_disponibles=prof_info.get('horarios_disponibles'),
            bio=prof_info.get('bio'),
            fee_range=prof_info.get('fee_range')
        )

        if success:
            # Clear temp data
            session.clear_temp()

            # Show formatted profile
            formatted_profile = professional_service.format_professional_profile_psivale(
                phone)

            # ✅ Cambiar al menú principal después de guardar exitosamente
            session.transition_to(ConversationState.PROF_MAIN_MENU)

            return f"""✅ Información guardada exitosamente!

    {formatted_profile}

    {self.messages.PROF_MAIN_MENU}"""
        else:
            return """❌ Error al guardar la información.

    Por favor, intentá nuevamente o contactá soporte.

    Escribí '0' para volver al menú."""

    def parse_week_schedule_quick(self, message: str) -> tuple:
        """
        Parse weekly schedule from message.

        Format:
            lunes 09:00-10:00+11:00-11:40
            martes 09:00-17:00

        Returns:
            (schedules_list, errors_list)
            schedules_list: [{'day': 0, 'start': '09:00', 'end': '10:00'}, ...]
            errors_list: ['Error message', ...]
        """
        import re

        lines = [line.strip()
                 for line in message.strip().split('\n') if line.strip()]

        schedules = []
        errors = []

        # Day name to number mapping
        day_map = {
            'lunes': 0, 'lun': 0,
            'martes': 1, 'mar': 1,
            'miércoles': 2, 'miercoles': 2, 'mie': 2, 'mié': 2,
            'jueves': 3, 'jue': 3,
            'viernes': 4, 'vie': 4,
            'sábado': 5, 'sabado': 5, 'sab': 5,
            'domingo': 6, 'dom': 6
        }

        for line_num, line in enumerate(lines, 1):
            # Expected format: "dia HH:MM-HH:MM+HH:MM-HH:MM"
            parts = line.lower().split(maxsplit=1)

            if len(parts) != 2:
                errors.append(
                    f"Línea {line_num}: Formato inválido. Debe ser: dia HH:MM-HH:MM")
                continue

            day_name, times_str = parts

            # Validate day
            if day_name not in day_map:
                errors.append(
                    f"Línea {line_num}: Día '{day_name}' no reconocido")
                continue

            day_num = day_map[day_name]

            # Parse time ranges (separated by +)
            time_ranges = times_str.split('+')

            for time_range in time_ranges:
                # Validate format HH:MM-HH:MM
                match = re.match(
                    r'^(\d{2}):(\d{2})-(\d{2}):(\d{2})$', time_range.strip())

                if not match:
                    errors.append(
                        f"Línea {line_num}: Horario '{time_range}' inválido. Debe ser HH:MM-HH:MM")
                    continue

                start_h, start_m, end_h, end_m = match.groups()

                # Validate hours and minutes
                if not (0 <= int(start_h) <= 23 and 0 <= int(start_m) <= 59):
                    errors.append(
                        f"Línea {line_num}: Hora de inicio inválida: {start_h}:{start_m}")
                    continue

                if not (0 <= int(end_h) <= 23 and 0 <= int(end_m) <= 59):
                    errors.append(
                        f"Línea {line_num}: Hora de fin inválida: {end_h}:{end_m}")
                    continue

                start_time = f"{start_h}:{start_m}"
                end_time = f"{end_h}:{end_m}"

                # Validate end > start
                if end_time <= start_time:
                    errors.append(
                        f"Línea {line_num}: La hora de fin debe ser mayor que la de inicio")
                    continue

                # Add to schedules
                schedules.append({
                    'day': day_num,
                    'day_name': day_name.capitalize(),
                    'start': start_time,
                    'end': end_time
                })

        return schedules, errors

    def handle_prof_week_schedule_quick(self, session: SessionData, message: str) -> str:
        """Handle quick weekly schedule input (all in one message)."""

        if message == '0':
            session.transition_to(ConversationState.PROF_MAIN_MENU)
            return self.messages.PROF_MAIN_MENU

        # Parse the message
        schedules, errors = self.parse_week_schedule_quick(message)

        if errors:
            error_msg = "❌ Errores encontrados:\n\n"
            error_msg += "\n".join(errors)
            error_msg += "\n\n" + self.messages.PROF_WEEK_QUICK_FORMAT
            return error_msg

        if not schedules:
            return "❌ No se encontraron horarios válidos.\n\n" + self.messages.PROF_WEEK_QUICK_FORMAT

        # Save to database
        from professional_service import professional_service

        schedules_list = [
            {
                'day_of_week': s['day'],
                'start_time': s['start'],
                'end_time': s['end']
            }
            for s in schedules
        ]

        success_count, total = professional_service.add_multiple_weekly_schedules(
            session.phone_number,
            schedules_list
        )

        # Format summary
        summary_lines = []
        day_names = ['Lunes', 'Martes', 'Miércoles',
                     'Jueves', 'Viernes', 'Sábado', 'Domingo']

        # Group by day
        by_day = {}
        for s in schedules:
            day = s['day']
            if day not in by_day:
                by_day[day] = []
            by_day[day].append(f"{s['start']}-{s['end']}")

        for day in sorted(by_day.keys()):
            times = ', '.join(by_day[day])
            summary_lines.append(f"• {day_names[day]}: {times}")

        schedule_summary = "\n".join(summary_lines)

        session.clear_temp()
        session.transition_to(ConversationState.PROF_MAIN_MENU)

        return f"""✅ ¡Semana configurada exitosamente!

    Guardados {success_count}/{total} horarios:

    {schedule_summary}

    Estos horarios se repetirán cada semana.

    """ + self.messages.PROF_MAIN_MENU

    # ==========================================
    # PROFESSIONAL - LIBERAR HORARIO (FREE SLOT)
    # ==========================================

    def handle_prof_free_slot_date(self, session: SessionData, message: str) -> str:
        """Handle date input for freeing a slot."""
        # Check for back command
        if message == '0':
            session.clear_temp()
            session.transition_to(ConversationState.PROF_MAIN_MENU)
            return self.messages.PROF_MAIN_MENU

        date_obj = parse_date(message)

        if not date_obj:
            return self.messages.INVALID_DATE + "\n\n" + self.messages.PROF_FREE_SLOT_ASK_DATE

        # Store date in YYYY-MM-DD format for database
        date_str_db = date_obj.strftime("%Y-%m-%d")

        session.store_temp('date', date_obj)
        # Guardar en formato correcto
        session.store_temp('date_str', date_str_db)
        # Guardar formato original para mostrar
        session.store_temp('date_display', message)
        session.transition_to(ConversationState.PROF_FREE_SLOT_TIME)

        return self.messages.PROF_FREE_SLOT_ASK_TIME

    def handle_prof_free_slot_time(self, session: SessionData, message: str) -> str:
        """Handle time input for freeing a slot."""
        # Check for back command
        if message == '0':
            session.clear_temp()
            session.transition_to(ConversationState.PROF_MAIN_MENU)
            return self.messages.PROF_MAIN_MENU

        time_range = parse_time_range(message)

        if not time_range:
            return self.messages.INVALID_TIME + "\n\n" + self.messages.PROF_FREE_SLOT_ASK_TIME

        start_time, end_time = time_range

        # Store time and ask for confirmation
        session.store_temp('time_start', start_time)
        session.store_temp('time_end', end_time)
        session.transition_to(ConversationState.PROF_FREE_SLOT_CONFIRM)

        return self.messages.PROF_FREE_SLOT_CONFIRM.format(
            date=session.get_temp('date_str'),
            time_start=start_time,
            time_end=end_time
        )

    def handle_prof_free_slot_confirm(self, session: SessionData, message: str) -> str:
        """Handle confirmation for freeing a slot."""
        if message == '1':
            # Confirmed - save to database
            date_str = session.get_temp('date_str')
            time_start = session.get_temp('time_start')
            time_end = session.get_temp('time_end')

            # Use date_str directly (it's already in correct format from user input)
            professional_service.mark_slot_as_free(
                session.phone_number,
                date_str,
                time_start,
                time_end
            )

            # Clear temp data and return to menu
            session.clear_temp()
            session.transition_to(ConversationState.PROF_MAIN_MENU)

            return self.messages.PROF_FREE_SLOT_SUCCESS.format(
                date=date_str,
                time_start=time_start,
                time_end=time_end
            ) + "\n\n" + self.messages.PROF_MAIN_MENU

        elif message == '2' or message == '0':
            # Cancelled
            session.clear_temp()
            session.transition_to(ConversationState.PROF_MAIN_MENU)
            return self.messages.OPERATION_CANCELLED + "\n\n" + self.messages.PROF_MAIN_MENU

        else:
            return self.messages.INVALID_OPTION + "\n\n" + self.messages.PROF_FREE_SLOT_CONFIRM.format(
                date=session.get_temp('date_str', ''),
                time_start=session.get_temp('time_start', ''),
                time_end=session.get_temp('time_end', '')
            )
    # ==========================================
    # PROFESSIONAL - CARGAR HORARIO OCUPADO (BUSY SLOT)
    # ==========================================

    def handle_prof_manage_free_slots(self, session: SessionData, message: str) -> str:
        """Show menu to manage free slots."""
        from professional_service import professional_service

        if message == '1':
            # Add new free slot
            session.transition_to(ConversationState.PROF_FREE_SLOT_DATE)
            return self.messages.PROF_FREE_SLOT_ASK_DATE

        elif message == '2':
            # Delete free slot
            free_slots = professional_service.get_free_slots(
                session.phone_number, future_only=True)

            if not free_slots:
                return "❌ No tienes horarios libres activos.\n\n" + self.messages.PROF_MAIN_MENU

            # Show slots with numbers
            msg = "📅 ELIMINAR HORARIO LIBRE\n\n"
            msg += "Horarios libres activos:\n\n"
            for idx, slot in enumerate(free_slots, 1):
                msg += f"{idx}️⃣ {slot['date']} {slot['start_time']}-{slot['end_time']}\n"
            msg += "\n0️⃣ Cancelar\n\n"
            msg += "Selecciona el número del horario a eliminar:"

            session.store_temp('free_slots_list', free_slots)
            session.transition_to(ConversationState.PROF_DELETE_FREE_SLOT)
            return msg

        elif message == '0':
            session.transition_to(ConversationState.PROF_MAIN_MENU)
            return self.messages.PROF_MAIN_MENU

        else:
            return self.messages.INVALID_OPTION

    def handle_prof_delete_free_slot(self, session: SessionData, message: str) -> str:
        """Handle deleting a free slot."""

        if message == '0':
            session.clear_temp()
            session.transition_to(ConversationState.PROF_MAIN_MENU)
            return self.messages.PROF_MAIN_MENU

        try:
            selection = int(message)
            free_slots = session.get_temp('free_slots_list', [])

            if 1 <= selection <= len(free_slots):
                slot = free_slots[selection - 1]

                from professional_service import professional_service
                success = professional_service.remove_free_slot(
                    session.phone_number,
                    slot['date'],
                    slot['start_time'],
                    slot['end_time']
                )

                if success:
                    msg = f"✅ Horario eliminado:\n📅 {slot['date']} {slot['start_time']}-{slot['end_time']}\n\n"
                    msg += "Este horario ya no está disponible para clientes."
                else:
                    msg = "❌ Error al eliminar horario."

                session.clear_temp()
                session.transition_to(ConversationState.PROF_MAIN_MENU)
                return msg + "\n\n" + self.messages.PROF_MAIN_MENU
            else:
                return f"❌ Opción inválida. Selecciona un número entre 1 y {len(free_slots)}."

        except ValueError:
            return "❌ Por favor, ingresa el número del horario a eliminar."
    # ==========================================
    # PROFESSIONAL - CARGAR SEMANA (WEEKLY SCHEDULE)
    # ==========================================

    def handle_prof_week_day(self, session: SessionData, message: str) -> str:
        """Handle day selection for weekly schedule."""
        # Check for back command
        if message == '0':
            session.clear_temp()
            session.transition_to(ConversationState.PROF_MAIN_MENU)
            return self.messages.PROF_MAIN_MENU

        if message not in ['1', '2', '3', '4', '5', '6', '7']:
            return self.messages.INVALID_OPTION + "\n\n" + self.messages.PROF_WEEK_ASK_DAY

        day_number = int(message)
        day_name = self.messages.format_day_name(day_number)

        session.store_temp('current_day', day_number)
        session.store_temp('current_day_name', day_name)
        session.transition_to(ConversationState.PROF_WEEK_SCHEDULE_TIME)

        return self.messages.PROF_WEEK_ASK_TIME.format(day=day_name)

    def handle_prof_week_time(self, session: SessionData, message: str) -> str:
        """Handle time input for weekly schedule."""
        # Check for back command
        if message == '0':
            session.clear_temp()
            session.transition_to(ConversationState.PROF_MAIN_MENU)
            return self.messages.PROF_MAIN_MENU

        time_range = parse_time_range(message)

        if not time_range:
            day_name = session.get_temp('current_day_name')
            return self.messages.INVALID_TIME + "\n\n" + self.messages.PROF_WEEK_ASK_TIME.format(day=day_name)

        start_time, end_time = time_range
        day_number = session.get_temp('current_day')
        day_name = session.get_temp('current_day_name')

        # Store in week schedule
        week_schedule = session.get_temp('week_schedule', {})
        week_schedule[day_number] = {
            'day_name': day_name,
            'start': start_time,
            'end': end_time
        }
        session.store_temp('week_schedule', week_schedule)

        # Format configured days
        configured_days = "\n".join([
            f"• {data['day_name']}: {data['start']} - {data['end']}"
            for day, data in sorted(week_schedule.items())
        ])

        session.transition_to(ConversationState.PROF_WEEK_SCHEDULE_MORE)

        return self.messages.PROF_WEEK_ASK_MORE.format(
            day=day_name,
            time_start=start_time,
            time_end=end_time,
            configured_days=configured_days
        )

    def handle_prof_week_more(self, session: SessionData, message: str) -> str:
        """Handle whether to add more days to weekly schedule."""
        if message == '1':
            # Add another day
            session.transition_to(ConversationState.PROF_WEEK_SCHEDULE_DAY)
            return self.messages.PROF_WEEK_ASK_DAY

        elif message == '2':
            # Finish and save
            week_schedule = session.get_temp('week_schedule', {})

            # Type check to satisfy Pylance
            if not isinstance(week_schedule, dict):
                week_schedule = {}

            # Build schedules list
            schedules = []
            for day, data in week_schedule.items():
                schedules.append({
                    'day_of_week': day,
                    'start_time': data['start'],
                    'end_time': data['end']
                })

            # Save to database
            professional_service.add_multiple_weekly_schedules(
                session.phone_number,
                schedules
            )

            # Format summary
            schedule_summary = "\n".join([
                f"• {data['day_name']}: {data['start']} - {data['end']}"
                for day, data in sorted(week_schedule.items())
            ])

            session.clear_temp()
            session.transition_to(ConversationState.PROF_MAIN_MENU)

            return self.messages.PROF_WEEK_SUCCESS.format(
                schedule_summary=schedule_summary
            ) + "\n\n" + self.messages.PROF_MAIN_MENU

        elif message == '0':
            # Cancel and go back to menu
            session.clear_temp()
            session.transition_to(ConversationState.PROF_MAIN_MENU)
            return self.messages.OPERATION_CANCELLED + "\n\n" + self.messages.PROF_MAIN_MENU

        else:
            return self.messages.INVALID_OPTION

    # ==========================================
    # ⭐ NUEVOS HANDLERS - PROFESIONAL PSIVALE
    # ==========================================

    def handle_prof_info_enfoque(self, session: SessionData, message: str) -> str:
        """Handle enfoque terapéutico input."""
        if message == '0':
            session.transition_to(ConversationState.PROF_INFO_MENU)
            return self.format_prof_info_menu_psivale(session)

        # Parse enfoque list (puede ser "1" o "1,3")
        enfoque_list = parse_enfoque_list(message)

        if not enfoque_list:
            return "❌ Opción inválida. Por favor elige 1 o 2 enfoques válidos.\n\n" + self.messages.PROF_INFO_ASK_ENFOQUE

        # Store enfoques
        prof_info = session.get_temp('prof_info', {})
        prof_info['enfoque_terapeutico'] = enfoque_list
        session.store_temp('prof_info', prof_info)

        # Format display
        from professional_service import professional_service
        enfoque_display = professional_service._format_enfoques(enfoque_list)

        session.transition_to(ConversationState.PROF_INFO_MENU)
        return f"✅ Enfoque guardado: {enfoque_display}\n\n" + self.format_prof_info_menu_psivale(session)

    def handle_prof_info_poblacion(self, session: SessionData, message: str) -> str:
        """Handle población input."""
        if message == '0':
            session.transition_to(ConversationState.PROF_INFO_MENU)
            return self.format_prof_info_menu_psivale(session)

        # Parse población list (puede ser "1,2,3")
        poblacion_list = parse_poblacion_list(message)

        if not poblacion_list:
            return "❌ Opción inválida. Por favor elige al menos una población.\n\n" + self.messages.PROF_INFO_ASK_POBLACION

        # Store población
        prof_info = session.get_temp('prof_info', {})
        prof_info['poblacion'] = poblacion_list
        session.store_temp('prof_info', prof_info)

        # Format display
        from professional_service import professional_service
        poblacion_display = professional_service._format_poblaciones(
            poblacion_list)

        session.transition_to(ConversationState.PROF_INFO_MENU)
        return f"✅ Población guardada: {poblacion_display}\n\n" + self.format_prof_info_menu_psivale(session)

    def handle_prof_info_modalidad(self, session: SessionData, message: str) -> str:
        """Handle modalidad input."""
        if message == '0':
            session.transition_to(ConversationState.PROF_INFO_MENU)
            return self.format_prof_info_menu_psivale(session)

        if not validate_modalidad(message):
            return "❌ Opción inválida.\n\n" + self.messages.PROF_INFO_ASK_MODALIDAD

        modalidad = normalize_modalidad(message)

        # Store modalidad
        prof_info = session.get_temp('prof_info', {})
        prof_info['modalidad'] = modalidad
        session.store_temp('prof_info', prof_info)

        modalidad_display = {'online': '💻 Online',
                             'presencial': '🏢 Presencial', 'ambas': '🔀 Ambas'}

        session.transition_to(ConversationState.PROF_INFO_MENU)
        return f"✅ Modalidad guardada: {modalidad_display[modalidad]}\n\n" + self.format_prof_info_menu_psivale(session)

    def handle_prof_info_horarios(self, session: SessionData, message: str) -> str:
        """Handle horarios disponibles input."""
        if message == '0':
            session.transition_to(ConversationState.PROF_INFO_MENU)
            return self.format_prof_info_menu_psivale(session)

        # Parse horarios list (puede ser "1,2,3")
        horarios_list = parse_horarios_list(message)

        if not horarios_list:
            return "❌ Opción inválida. Por favor elige al menos un horario.\n\n" + self.messages.PROF_INFO_ASK_HORARIOS

        # Store horarios
        prof_info = session.get_temp('prof_info', {})
        prof_info['horarios_disponibles'] = horarios_list
        session.store_temp('prof_info', prof_info)

        # Format display
        from professional_service import professional_service
        horarios_display = professional_service._format_horarios(horarios_list)

        session.transition_to(ConversationState.PROF_INFO_MENU)
        return f"✅ Horarios guardados: {horarios_display}\n\n" + self.format_prof_info_menu_psivale(session)

    # ==========================================
    # FORMATTING - PROFESIONAL PSIVALE
    # ==========================================

    def format_prof_info_menu_psivale(self, session: SessionData) -> str:
        """
        Format professional info menu with current data (PSIVALE VERSION).
        Shows ONLY the fields that have been filled in (incremental display).

        IMPORTANTE: Prioriza datos temporales (temp_data) sobre datos de BD
        para mostrar cambios mientras el usuario está editando.
        """
        from database import db
        phone = session.phone_number

        # Primero obtener datos temp (lo que está editando ahora)
        prof_temp = session.get_temp('prof_info', {})

        # Luego obtener datos de BD (lo ya guardado)
        prof_db = db.get_professional(phone) or {}

        # Merge: temp_data tiene prioridad sobre BD
        prof = {**prof_db, **prof_temp}

        if not prof:
            current_info = "(ninguno)"
        else:
            # Format current information - SOLO mostrar campos con datos
            info_lines = []

            # Nombre
            if prof.get('name'):
                info_lines.append(f"👤 {prof['name']}")

            # Email
            if prof.get('email'):
                info_lines.append(f"📧 {prof['email']}")

            # Zona
            zona = prof.get('zone')
            if zona:
                zona_map = {
                    'norte': 'Zona Norte',
                    'sur': 'Zona Sur',
                    'nueva_cordoba': 'Nueva Córdoba'
                }
                info_lines.append(f"📍 {zona_map.get(zona, zona)}")

            # Género
            gender = prof.get('gender')
            if gender:
                gender_map = {
                    'm': 'Masculino',
                    'f': 'Femenino',
                    'otro': 'Otro'
                }
                info_lines.append(f"👥 {gender_map.get(gender, gender)}")

            # Enfoque terapéutico
            enfoque = prof.get('enfoque_terapeutico')
            if enfoque:
                from professional_service import professional_service
                enfoque_display = professional_service._format_enfoques(
                    enfoque)
                info_lines.append(f"🧠 {enfoque_display}")

            # Población
            poblacion = prof.get('poblacion')
            if poblacion:
                from professional_service import professional_service
                poblacion_display = professional_service._format_poblaciones(
                    poblacion)
                info_lines.append(f"👥 {poblacion_display}")

            # Modalidad
            modalidad = prof.get('modalidad')
            if modalidad:
                modalidad_map = {
                    'online': '💻 Online',
                    'presencial': '🏢 Presencial',
                    'ambas': '🔀 Ambas modalidades'
                }
                info_lines.append(f"{modalidad_map.get(modalidad, modalidad)}")

            # Horarios disponibles
            horarios = prof.get('horarios_disponibles')
            if horarios:
                from professional_service import professional_service
                horarios_display = professional_service._format_horarios(
                    horarios)
                info_lines.append(f"📅 {horarios_display}")

            # Bio
            bio = prof.get('bio')
            if bio:
                bio_short = bio[:50] + "..." if len(bio) > 50 else bio
                info_lines.append(f"📝 {bio_short}")

            # Honorarios
            fee_range = prof.get('fee_range')
            if fee_range:
                from validators import get_fee_range_display
                info_lines.append(f"💰 {get_fee_range_display(fee_range)}")

            current_info = "\n".join(info_lines) if info_lines else "(ninguno)"

        return self.messages.PROF_INFO_MENU.format(current_info=current_info)
    # ==========================================
    # CLIENT HANDLERS
    # ==========================================

    # handle_client_main_menu para Psivale:
    # def handle_client_main_menu(self, session: SessionData, message: str) -> str:
    #     """Handle client main menu (PSIVALE VERSION)."""

    #     if message == '1':
    #         # Flujo asesorado (recomendado)
    #         session.transition_to(ConversationState.CLIENT_ASESORADO_WELCOME)
    #         return self.messages.CLIENT_ASESORADO_WELCOME

    #     elif message == '2':
    #         # Filtrado rápido
    #         session.clear_temp()
    #         session.transition_to(ConversationState.CLIENT_SEARCH_QUICK)
    #         return self.messages.CLIENT_SEARCH_QUICK_FORMAT

    #     elif message == '0':
    #         # Volver al inicio
    #         session.reset()
    #         session.transition_to(ConversationState.ROLE_SELECTION)
    #         return self.messages.WELCOME

    #     else:
    #         return self.messages.INVALID_OPTION + "\n\n" + self.messages.CLIENT_WELCOME_PSIVALE

    def handle_client_filter_zona(self, session: SessionData, message: str) -> str:
        """Handle zona filter."""
        # Check for back command
        if message == '0':
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return self.messages.CLIENT_MAIN_MENU

        if message == '1':
            zona = 'norte'
        elif message == '2':
            zona = 'sur'
        elif message == '3':
            zona = 'nueva_cordoba'
        else:
            return self.messages.INVALID_OPTION + "\n\n" + self.messages.CLIENT_ASK_ZONA

        # Buscar profesionales con la zona seleccionada
        results = client_service.search_professionals_by_filters(
            zone=zona,
            limit=10
        )

        # Log search
        search_id = analytics_service.log_search(
            client_phone=session.phone_number,
            search_type='zona',
            search_params={'zone': zona},
            result_count=len(results),
            session_id=session.phone_number
        )
        session.store_temp('current_search_id', search_id)

        # Store results
        session.store_temp('search_results', results)

        # Format and return
        if len(results) == 0:
            return self.messages.CLIENT_NO_RESULTS

        formatted = client_service.format_results_list(results)
        session.transition_to(ConversationState.CLIENT_SHOW_RESULTS)
        return formatted

    def handle_client_filter_fecha(self, session: SessionData, message: str) -> str:
        """Handle fecha filter - ask for date."""
        # Check for back command
        if message == '0':
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return self.messages.CLIENT_MAIN_MENU

        date_obj = parse_date(message)

        if not date_obj:
            return self.messages.INVALID_DATE + "\n\n" + self.messages.CLIENT_ASK_FECHA

        session.store_temp('fecha', date_obj)
        session.store_temp('fecha_str', message)
        session.transition_to(ConversationState.CLIENT_FILTER_HORA)
        return self.messages.CLIENT_ASK_HORA

    def handle_client_filter_hora(self, session: SessionData, message: str) -> str:
        """Handle hora filter - accepts specific time or morning/afternoon."""
        # Check for back command
        if message == '0':
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return self.messages.CLIENT_MAIN_MENU

        # Check if user selected morning or afternoon
        if message == '1' or message.lower() in ['mañana', 'manana', 'morning']:
            # Morning: 8:00 - 13:00
            time_start = "08:00"
            time_end = "13:00"
            time_range = True
        elif message == '2' or message.lower() in ['tarde', 'afternoon']:
            # Afternoon: 13:00 - 20:00
            time_start = "13:00"
            time_end = "20:00"
            time_range = True
        else:
            # User entered specific time
            if not validators.validate_time(message):
                return self.messages.INVALID_TIME
            time_start = message
            time_end = None
            time_range = False

        # Get date from temp storage
        fecha = session.get_temp('fecha')
        fecha_str = session.get_temp('fecha_str')

        # Store time info
        if time_range:
            session.store_temp('time_range', f"{time_start}-{time_end}")
            session.store_temp('time_start', time_start)
            session.store_temp('time_end', time_end)
        else:
            session.store_temp('hora', time_start)

        # Search professionals
        if time_range:
            # Search for professionals available in the time range
            results = client_service.search_professionals_in_time_range(
                date_str=fecha.strftime("%Y-%m-%d"),
                time_start=time_start,
                time_end=time_end
            )
        else:
            # Search for specific time
            results = client_service.search_professionals_by_filters(
                date_str=fecha.strftime("%Y-%m-%d"),
                time_str=time_start
            )

        # Log search
        search_params = {
            'date': fecha_str,
        }
        if time_range:
            search_params['time_range'] = f"{time_start}-{time_end}"
        else:
            search_params['time'] = time_start

        search_id = analytics_service.log_search(
            client_phone=session.phone_number,
            search_type='today' if time_range else 'datetime',
            search_params=search_params,
            result_count=len(results),
            session_id=session.phone_number
        )
        session.store_temp('current_search_id', search_id)

        # Store results
        session.store_temp('search_results', results)

        # Format and return
        formatted = client_service.format_results_list(results)
        session.transition_to(ConversationState.CLIENT_SHOW_RESULTS)

        return formatted

    def handle_client_filter_prepaga(self, session: SessionData, message: str) -> str:
        """Handle prepaga filter."""
        # Check for back command
        if message == '0':
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return self.messages.CLIENT_MAIN_MENU

        if message == '1':
            session.store_temp('prepaga', True)
        elif message == '2':
            session.store_temp('prepaga', False)
        elif message == '3':
            session.store_temp('prepaga', None)
        else:
            return self.messages.INVALID_OPTION + "\n\n" + self.messages.CLIENT_ASK_PREPAGA

        # TODO: Search database
        print(f"[DB] TODO: Search by prepaga - {session.get_temp('prepaga')}")

        session.transition_to(ConversationState.CLIENT_SHOW_RESULTS)
        return "🔍 Buscando...\n\n📋 Próximamente mostraré resultados.\n\nEscribe 'menu' para volver."

    def handle_client_filter_sexo(self, session: SessionData, message: str) -> str:
        """Handle sexo filter."""
        # Check for back command
        if message == '0':
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return self.messages.CLIENT_MAIN_MENU

        if message == '1':
            session.store_temp('sexo', 'm')
        elif message == '2':
            session.store_temp('sexo', 'f')
        elif message == '3':
            session.store_temp('sexo', None)
        else:
            return self.messages.INVALID_OPTION + "\n\n" + self.messages.CLIENT_ASK_SEXO

        # TODO: Search database
        print(f"[DB] TODO: Search by sexo - {session.get_temp('sexo')}")

        session.transition_to(ConversationState.CLIENT_SHOW_RESULTS)
        return "🔍 Buscando...\n\n📋 Próximamente mostraré resultados.\n\nEscribe 'menu' para volver."

    def format_multifilter_menu(self, session: SessionData) -> str:
        """Format multi-filter menu with active filters."""
        filters = session.get_temp('filters', {})

        # Build active filters list
        if not filters:
            active_filters = "Ninguno"
        else:
            active_list = []
            if 'zona' in filters:
                active_list.append(f"• Zona: {filters['zona'].capitalize()}")
            if 'fecha' in filters:
                active_list.append(f"• Fecha: {filters['fecha']}")
            if 'hora' in filters:
                active_list.append(f"• Hora: {filters['hora']}")
            if 'prepaga' in filters:
                prepaga_text = "Sí" if filters['prepaga'] else "No"
                active_list.append(f"• Prepaga: {prepaga_text}")
            if 'sexo' in filters:
                sexo_text = "Masculino" if filters['sexo'] == 'm' else "Femenino"
                active_list.append(f"• Sexo: {sexo_text}")
            if 'especialidad' in filters:
                active_list.append(
                    f"• Especialidad: {filters['especialidad']}")

            active_filters = "\n".join(active_list)

        # Add checkmarks to selected options
        menu = self.messages.CLIENT_MULTIFILTER_MENU.format(
            active_filters=active_filters
        )

        # Add checkmarks
        if 'zona' in filters:
            menu = menu.replace("1️⃣ Zona", "1️⃣ Zona ✓")
        if 'fecha' in filters and 'hora' in filters:
            menu = menu.replace("2️⃣ Disponibilidad", "2️⃣ Disponibilidad ✓")
        if 'prepaga' in filters:
            menu = menu.replace("3️⃣ Prepaga", "3️⃣ Prepaga ✓")
        if 'sexo' in filters:
            menu = menu.replace("4️⃣ Sexo", "4️⃣ Sexo ✓")
        if 'especialidad' in filters:
            menu = menu.replace("5️⃣ Especialidad", "5️⃣ Especialidad ✓")

        return menu

    def handle_client_multifilter_zona(self, session: SessionData, message: str) -> str:
        """Handle zona filter in multi-filter mode."""
        if message == '1':
            filters = session.get_temp('filters', {})
            filters['zona'] = 'norte'
            session.store_temp('filters', filters)
            session.transition_to(ConversationState.CLIENT_MULTIFILTER_MENU)
            return self.messages.CLIENT_MULTIFILTER_ADDED.format(
                filter_name="Zona Norte",
                menu=self.format_multifilter_menu(session)
            )
        elif message == '2':
            filters = session.get_temp('filters', {})
            filters['zona'] = 'sur'
            session.store_temp('filters', filters)
            session.transition_to(ConversationState.CLIENT_MULTIFILTER_MENU)
            return self.messages.CLIENT_MULTIFILTER_ADDED.format(
                filter_name="Zona Sur",
                menu=self.format_multifilter_menu(session)
            )
        else:
            return self.messages.INVALID_OPTION + "\n\n" + self.messages.CLIENT_ASK_ZONA

    def handle_client_multifilter_fecha(self, session: SessionData, message: str) -> str:
        """Handle fecha filter in multi-filter mode."""
        date_obj = parse_date(message)

        if not date_obj:
            return self.messages.INVALID_DATE + "\n\n" + self.messages.CLIENT_ASK_FECHA

        filters = session.get_temp('filters', {})
        filters['fecha'] = message
        session.store_temp('filters', filters)
        session.transition_to(ConversationState.CLIENT_MULTIFILTER_HORA)
        return self.messages.CLIENT_ASK_HORA

    def handle_client_multifilter_hora(self, session: SessionData, message: str) -> str:
        """Handle hora filter in multi-filter mode."""
        # Simple time validation (HH:MM)
        if ':' not in message or len(message) != 5:
            return self.messages.INVALID_INPUT + "\n\n" + self.messages.CLIENT_ASK_HORA

        filters = session.get_temp('filters', {})
        filters['hora'] = message
        session.store_temp('filters', filters)
        session.transition_to(ConversationState.CLIENT_MULTIFILTER_MENU)

        fecha = filters.get('fecha', '')
        return self.messages.CLIENT_MULTIFILTER_ADDED.format(
            filter_name=f"Disponibilidad: {fecha} a las {message}",
            menu=self.format_multifilter_menu(session)
        )

    def handle_client_multifilter_prepaga(self, session: SessionData, message: str) -> str:
        """Handle prepaga filter in multi-filter mode."""
        filters = session.get_temp('filters', {})

        if message == '1':
            filters['prepaga'] = True
            filter_name = "Con Prepaga"
        elif message == '2':
            filters['prepaga'] = False
            filter_name = "Sin Prepaga"
        elif message == '3':
            filters['prepaga'] = None
            filter_name = "Prepaga: No importa"
        else:
            return self.messages.INVALID_OPTION + "\n\n" + self.messages.CLIENT_ASK_PREPAGA

        session.store_temp('filters', filters)
        session.transition_to(ConversationState.CLIENT_MULTIFILTER_MENU)
        return self.messages.CLIENT_MULTIFILTER_ADDED.format(
            filter_name=filter_name,
            menu=self.format_multifilter_menu(session)
        )

    def handle_client_multifilter_sexo(self, session: SessionData, message: str) -> str:
        """Handle sexo filter in multi-filter mode."""
        filters = session.get_temp('filters', {})

        if message == '1':
            filters['sexo'] = 'm'
            filter_name = "Sexo: Masculino"
        elif message == '2':
            filters['sexo'] = 'f'
            filter_name = "Sexo: Femenino"
        elif message == '3':
            filters['sexo'] = None
            filter_name = "Sexo: No importa"
        else:
            return self.messages.INVALID_OPTION + "\n\n" + self.messages.CLIENT_ASK_SEXO

        session.store_temp('filters', filters)
        session.transition_to(ConversationState.CLIENT_MULTIFILTER_MENU)
        return self.messages.CLIENT_MULTIFILTER_ADDED.format(
            filter_name=filter_name,
            menu=self.format_multifilter_menu(session)
        )

    def handle_client_multifilter_menu(self, session: SessionData, message: str) -> str:
        """Handle multi-filter menu selection."""
        if message == '9':
            # Ejecutar búsqueda con filtros actuales
            filters = session.get_temp('filters', {})

            if not filters:
                return "⚠️ No has seleccionado ningún filtro.\n\n" + self.format_multifilter_menu(session)

            # TODO: Buscar en base de datos con múltiples filtros
            # results = db.search_professionals(filters)

            # Format filters for display
            filters_list = []
            if 'zona' in filters:
                filters_list.append(f"• Zona: {filters['zona'].capitalize()}")
            if 'fecha' in filters and 'hora' in filters:
                filters_list.append(
                    f"• Disponibilidad: {filters['fecha']} a las {filters['hora']}")
            if 'prepaga' in filters:
                prepaga_text = "Sí" if filters['prepaga'] else "No"
                filters_list.append(f"• Prepaga: {prepaga_text}")
            if 'sexo' in filters:
                sexo_text = "Masculino" if filters['sexo'] == 'm' else "Femenino"
                filters_list.append(f"• Sexo: {sexo_text}")
            if 'especialidad' in filters:
                filters_list.append(
                    f"• Especialidad: {filters['especialidad']}")

            session.transition_to(ConversationState.CLIENT_SHOW_RESULTS)
            return self.messages.CLIENT_MULTIFILTER_SEARCH_SUMMARY.format(
                filters_list="\n".join(filters_list)
            ) + "\n\n[Próximamente: resultados de búsqueda]"
        elif message == '0':
            # Volver al menú cliente (búsqueda inicial)
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return self.messages.CLIENT_MAIN_MENU
        elif message == '1':
            # Zona
            session.transition_to(ConversationState.CLIENT_MULTIFILTER_ZONA)
            return self.messages.CLIENT_ASK_ZONA

        elif message == '2':
            # Disponibilidad
            session.transition_to(ConversationState.CLIENT_MULTIFILTER_FECHA)
            return self.messages.CLIENT_ASK_FECHA

        elif message == '3':
            # Prepaga
            session.transition_to(ConversationState.CLIENT_MULTIFILTER_PREPAGA)
            return self.messages.CLIENT_ASK_PREPAGA

        elif message == '4':
            # Sexo
            session.transition_to(ConversationState.CLIENT_MULTIFILTER_SEXO)
            return self.messages.CLIENT_ASK_SEXO

        elif message == '5':
            # Especialidad (TODO: implement)
            return "🏥 Selección de especialidad - Próximamente\n\n" + self.format_multifilter_menu(session)

        else:
            return self.messages.INVALID_OPTION + "\n\n" + self.format_multifilter_menu(session)

    # ==========================================
    # Paciente - VER DETALLE PROFESIONAL
    # ==========================================

    def handle_client_show_results(self, session: SessionData, message: str) -> str:
        """Handle results list - user selecting a professional or going back."""

        if message == '0':
            # ✅ Volver al inicio (bienvenida Vale)
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_ASESORADO_WELCOME)
            return self.messages.WELCOME

        # Try to parse as professional selection
        try:
            choice = int(message)
            results = session.get_temp('search_results', [])

            if 1 <= choice <= len(results):
                # Valid selection - show professional detail
                selected_prof = results[choice - 1]

                # Store selected professional
                session.store_temp('selected_professional', selected_prof)
                session.store_temp('selected_position', choice)

                # Log profile view
                from analytics_service import analytics_service
                analytics_service.log_profile_view(selected_prof['phone'])

                # Format and show detail
                detail = client_service.format_professional_detail_psivale(
                    selected_prof)
                contact = client_service.format_contact_info_psivale(
                    selected_prof)

                session.transition_to(ConversationState.CLIENT_VIEW_DETAIL)

                return f"""{detail}

    {contact}

    ¿Qué querés hacer ahora?
    1️⃣ Ver otros profesionales
    2️⃣ Nueva búsqueda
    0️⃣ Volver al menú

    Responde con el número."""

            else:
                return f"❌ Opción inválida. Elegí un número entre 1 y {len(results)}, o '0' para volver."

        except ValueError:
            return "❌ Por favor, elegí un número de la lista o '0' para volver."

    def parse_client_search_quick(self, message: str) -> tuple:
        """
        Parse client search filters from message (PSIVALE VERSION - SMART PARSER).

        Supports multiple formats:

        Format 1 (with colons):
            enfoque: tcc
            poblacion: adultos

        Format 2 (without colons):
            enfoque tcc
            poblacion adultos

        Format 3 (just values):
            tcc
            adultos
            online

        All fields are optional.

        Returns:
            (filters_dict, errors_list)
        """

        lines = [line.strip()
                 for line in message.strip().split('\n') if line.strip()]

        if not lines:
            return {}, ["No se detectaron filtros. Por favor intenta nuevamente."]

        filters = {}
        errors = []
        unassigned_values = []

        # First pass: Parse each line
        for line in lines:
            filter_type, filter_value = self.parse_filter_line_smart(line)

            if filter_type:
                # We know the filter type - validate and store
                if filter_type == 'enfoque':
                    if validate_enfoque(filter_value):
                        filters['enfoque'] = normalize_enfoque(filter_value)
                    else:
                        errors.append(f"❌ Enfoque inválido: {filter_value}")

                elif filter_type in ['poblacion', 'población']:
                    if validate_poblacion(filter_value):
                        filters['poblacion'] = normalize_poblacion(
                            filter_value)
                    else:
                        errors.append(f"❌ Población inválida: {filter_value}")

                elif filter_type == 'modalidad':
                    if validate_modalidad(filter_value):
                        filters['modalidad'] = normalize_modalidad(
                            filter_value)
                    else:
                        errors.append(f"❌ Modalidad inválida: {filter_value}")

                elif filter_type == 'zona':
                    if validate_zona_psivale(filter_value):
                        filters['zone'] = normalize_zona_psivale(filter_value)
                    else:
                        errors.append(f"❌ Zona inválida: {filter_value}")

                elif filter_type == 'horarios':
                    if validate_horarios(filter_value):
                        filters['horarios'] = normalize_horario(filter_value)
                    else:
                        errors.append(f"❌ Horario inválido: {filter_value}")

                elif filter_type == 'honorarios':
                    if validate_fee_range(filter_value):
                        filters['fee_range'] = normalize_fee_range(
                            filter_value)
                    else:
                        errors.append(
                            f"❌ Honorarios inválidos: {filter_value}")

            else:
                # No filter type specified - try to detect from value
                detected_type = self.detect_value_type(filter_value)

                if detected_type:
                    # Auto-detected the type
                    if detected_type == 'enfoque' and 'enfoque' not in filters:
                        if validate_enfoque(filter_value):
                            filters['enfoque'] = normalize_enfoque(
                                filter_value)

                    elif detected_type == 'poblacion' and 'poblacion' not in filters:
                        if validate_poblacion(filter_value):
                            filters['poblacion'] = normalize_poblacion(
                                filter_value)

                    elif detected_type == 'modalidad' and 'modalidad' not in filters:
                        if validate_modalidad(filter_value):
                            filters['modalidad'] = normalize_modalidad(
                                filter_value)

                    elif detected_type == 'zona' and 'zone' not in filters:
                        if validate_zona_psivale(filter_value):
                            filters['zone'] = normalize_zona_psivale(
                                filter_value)

                    elif detected_type == 'horarios' and 'horarios' not in filters:
                        if validate_horarios(filter_value):
                            filters['horarios'] = normalize_horario(
                                filter_value)

                    elif detected_type == 'honorarios' and 'fee_range' not in filters:
                        if validate_fee_range(filter_value):
                            filters['fee_range'] = normalize_fee_range(
                                filter_value)

                else:
                    # Could not detect type
                    unassigned_values.append(filter_value)

        # Report unassigned values
        if unassigned_values and not filters:
            errors.append(
                f"❌ No pude identificar estos valores: {', '.join(unassigned_values)}")

        return filters, errors

    def handle_client_search_quick(self, session: SessionData, message: str) -> str:
        """Handle client quick search input (PSIVALE VERSION)."""

        if message == '0':
            session.transition_to(ConversationState.CLIENT_ASESORADO_WELCOME)
            return self.messages.WELCOME

        # Parse the message
        filters, errors = self.parse_client_search_quick(message)

        if errors:
            error_msg = "\n".join(errors)
            return f"{error_msg}\n\n{self.messages.CLIENT_SEARCH_QUICK_FORMAT}"

        if not filters:
            return f"❌ No se detectaron filtros válidos.\n\n{self.messages.CLIENT_SEARCH_QUICK_FORMAT}"

        # Store filters
        session.store_temp('filters', filters)

        # ⭐ EJECUTAR BÚSQUEDA
        results = client_service.search_professionals_psivale(
            enfoque=filters.get('enfoque'),
            poblacion=filters.get('poblacion'),
            modalidad=filters.get('modalidad'),
            zone=filters.get('zone'),
            horarios=filters.get('horarios'),
            fee_range=filters.get('fee_range'),
            limit=5
        )

        # Log search
        from analytics_service import analytics_service
        search_id = analytics_service.log_search(
            client_phone=session.phone_number,
            search_type='psivale_quick',
            search_params=filters,
            result_count=len(results),
            session_id=session.phone_number
        )
        session.store_temp('current_search_id', search_id)
        session.store_temp('search_results', results)

        # Format filters for display
        filter_lines = []
        if 'enfoque' in filters:
            enfoque_map = {
                'tcc': 'TCC',
                'contextual': 'Contextuales',
                'sistemica': 'Sistémica',
                'gestaltica': 'Gestáltica',
                'psicoanalisis': 'Psicoanálisis',
                'neuropsicologia': 'Neuropsicología'
            }
            filter_lines.append(
                f"🧠 Enfoque: {enfoque_map.get(filters['enfoque'], filters['enfoque'])}")

        if 'poblacion' in filters:
            poblacion_map = {
                'ninos_adolescentes': 'Niños/Adolescentes',
                'adultos': 'Adultos',
                'parejas': 'Parejas/Familias'
            }
            filter_lines.append(
                f"👥 Población: {poblacion_map.get(filters['poblacion'], filters['poblacion'])}")

        if 'modalidad' in filters:
            modalidad_map = {
                'online': '💻 Online',
                'presencial': '🏢 Presencial',
                'ambas': '🔀 Ambas'
            }
            filter_lines.append(
                f"💻 Modalidad: {modalidad_map.get(filters['modalidad'], filters['modalidad'])}")

        if 'zone' in filters:
            zone_map = {
                'norte': 'Zona Norte',
                'sur': 'Zona Sur',
                'nueva_cordoba': 'Nueva Córdoba'
            }
            filter_lines.append(
                f"📍 Zona: {zone_map.get(filters['zone'], filters['zone'])}")

        if 'horarios' in filters:
            horarios_map = {
                'manana': 'Mañana',
                'tarde': 'Tarde',
                'noche': 'Noche',
                'sabado': 'Sábados'
            }
            filter_lines.append(
                f"📅 Horarios: {horarios_map.get(filters['horarios'], filters['horarios'])}")

        if 'fee_range' in filters:
            from validators import get_fee_range_display
            filter_lines.append(
                f"💰 Honorarios: {get_fee_range_display(filters['fee_range'])}")

        filters_text = "\n".join(filter_lines)

        # ⭐ PREPARAR MENSAJE 2 (resultados)
        if len(results) > 0:
            formatted = client_service.format_results_list_psivale(results)
            message_2 = f"""💚 Encontré profesionales para vos.

    {formatted}"""
        else:
            message_2 = """💚 No encontré psicólogos con esos filtros.

    ¿Qué querés hacer?
    1️⃣ Intentar con menos filtros
    2️⃣ Ver todos los profesionales
    3️⃣ Volver al inicio

    Responde con el número."""

        # ⭐ CALLBACK PARA CAMBIAR ESTADO
        def change_state_after_send():
            session.transition_to(ConversationState.CLIENT_SHOW_RESULTS)
            print(
                f"[BOT] ✅ State changed to CLIENT_SHOW_RESULTS after delayed message")

        # ⭐ PROGRAMAR ENVÍO CON CALLBACK
        from messaging_utils import send_delayed_message
        send_delayed_message(
            to_number=f'whatsapp:{session.phone_number}',
            message=message_2,
            delay_seconds=3,
            callback=change_state_after_send
        )

        # ⭐ RETORNAR MENSAJE 1 (confirmación) INMEDIATAMENTE
        return f"""🔍 Búsqueda Rápida

    Filtros aplicados:
    {filters_text}

    Buscando psicólogos..."""

    # handle_client_view_detail para usar formato Psivale:

    # ==========================================
    # Detalle de profesional + return o restart - PSIVALE VERSION
    # ==========================================

    def handle_client_view_detail(self, session: SessionData, message: str) -> str:
        """Handle professional detail view and contact actions."""

        results = session.get_temp('search_results', [])

        if message == '1':
            # ✅ Ver otros profesionales → Volver a la lista
            session.transition_to(ConversationState.CLIENT_SHOW_RESULTS)

            if not results:
                return """🌿 No hay más profesionales para mostrar.

    ¿Qué querés hacer?
    1️⃣ Nueva búsqueda
    0️⃣ Volver al menú

    Responde con el número."""

            # Volver a mostrar la lista
            formatted = client_service.format_results_list_psivale(results)
            return f"""💚 Acá están los profesionales disponibles:

    {formatted}"""

        elif message == '2':
            # ✅ Nueva búsqueda → Volver al inicio (bienvenida Vale)
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_ASESORADO_WELCOME)
            return self.messages.WELCOME

        elif message == '0':
            # Volver al menú principal
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_ASESORADO_WELCOME)
            return self.messages.WELCOME

        else:
            # Opción inválida
            return """❌ Opción inválida.

    ¿Qué querés hacer ahora?
    1️⃣ Ver otros profesionales
    2️⃣ Nueva búsqueda
    0️⃣ Volver al menú

    Responde con el número."""
    # ==========================================
    # ⭐ NUEVOS HANDLERS - CLIENTE ASESORADO PSIVALE
    # ==========================================

    def handle_client_asesorado_welcome(self, session: SessionData, message: str) -> str:
        """Handle bienvenida del flujo asesorado (respuesta a WELCOME)."""

        if message == '1':
            # Sí, quiero empezar → IR A ENFOQUE
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_ASESORADO_ENFOQUE)
            return self.messages.CLIENT_ASESORADO_ASK_ENFOQUE

        elif message == '2':
            # Buscar por mi cuenta → FILTRADO RÁPIDO
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_SEARCH_QUICK)
            return self.messages.CLIENT_SEARCH_QUICK_FORMAT

        elif message == '0':
            # Volver (reiniciar)
            session.reset()
            session.transition_to(ConversationState.START)
            return self.messages.WELCOME

        else:
            return self.messages.INVALID_OPTION + "\n\n" + self.messages.WELCOME

    # def handle_client_asesorado_intencion(self, session: SessionData, message: str) -> str:
    #     """Handle confirmación de intención - continuar al flujo."""
    #     # Cualquier tecla continúa
    #     session.clear_temp()
    #     session.transition_to(ConversationState.CLIENT_ASESORADO_ENFOQUE)
    #     return self.messages.CLIENT_ASESORADO_ASK_ENFOQUE

    def handle_client_asesorado_enfoque(self, session: SessionData, message: str) -> str:
        """Handle selección de enfoque terapéutico."""
        if message == '0':
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return self.messages.CLIENT_WELCOME_PSIVALE

        # Validar enfoque
        if message == '7':
            # No sabe / Me da igual - no filtrar por enfoque
            enfoque = None
            enfoque_display = "Cualquier enfoque"
        else:
            if not validate_enfoque(message):
                return self.messages.PSIVALE_OPCION_INVALIDA + "\n\n" + self.messages.CLIENT_ASESORADO_ASK_ENFOQUE

            enfoque = normalize_enfoque(message)

            # Get display name
            enfoque_map = {
                'tcc': 'TCC',
                'contextual': 'Contextuales (ACT, DBT)',
                'sistemica': 'Sistémica',
                'gestaltica': 'Gestáltica',
                'psicoanalisis': 'Psicoanálisis',
                'neuropsicologia': 'Neuropsicología'
            }
            enfoque_display = enfoque_map.get(enfoque, enfoque)

        # Store filter
        filters = session.get_temp('filters', {})
        if enfoque:
            filters['enfoque'] = enfoque
        filters['enfoque_display'] = enfoque_display
        session.store_temp('filters', filters)

        # Next: población
        session.transition_to(ConversationState.CLIENT_ASESORADO_POBLACION)
        return self.messages.CLIENT_ASESORADO_ASK_POBLACION

    def handle_client_asesorado_poblacion(self, session: SessionData, message: str) -> str:
        """Handle selección de población."""
        if message == '0':
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return self.messages.CLIENT_WELCOME_PSIVALE

        if not validate_poblacion(message):
            return self.messages.PSIVALE_OPCION_INVALIDA + "\n\n" + self.messages.CLIENT_ASESORADO_ASK_POBLACION

        poblacion = normalize_poblacion(message)

        # Get display name
        poblacion_map = {
            'ninos': 'Niño/a',
            'adolescentes': 'Adolescente',
            'adultos': 'Adulto',
            'parejas': 'Pareja/Familia'
        }
        poblacion_display = poblacion_map.get(poblacion, poblacion)

        # Store filter
        filters = session.get_temp('filters', {})
        filters['poblacion'] = poblacion
        filters['poblacion_display'] = poblacion_display
        session.store_temp('filters', filters)

        # Next: modalidad
        session.transition_to(ConversationState.CLIENT_ASESORADO_MODALIDAD)
        return self.messages.CLIENT_ASESORADO_ASK_MODALIDAD

    def handle_client_asesorado_modalidad(self, session: SessionData, message: str) -> str:
        """Handle selección de modalidad."""
        if message == '0':
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return self.messages.CLIENT_WELCOME_PSIVALE

        if message == '3':
            # Me da igual - no filtrar por modalidad
            modalidad = None
            modalidad_display = "Cualquier modalidad"
            skip_zone = True
        else:
            if not validate_modalidad(message):
                return self.messages.PSIVALE_OPCION_INVALIDA + "\n\n" + self.messages.CLIENT_ASESORADO_ASK_MODALIDAD

            modalidad = normalize_modalidad(message)

            # Get display name
            modalidad_map = {
                'online': '💻 Online',
                'presencial': '🏢 Presencial',
                'ambas': 'Online o Presencial'
            }
            modalidad_display = modalidad_map.get(modalidad, modalidad)
            skip_zone = (modalidad == 'online')  # Si es online, skip zona

        # Store filter
        filters = session.get_temp('filters', {})
        if modalidad:
            filters['modalidad'] = modalidad
        filters['modalidad_display'] = modalidad_display
        session.store_temp('filters', filters)

        # Next: zona (solo si es presencial o ambas)
        if skip_zone:
            session.transition_to(ConversationState.CLIENT_ASESORADO_HORARIOS)
            return self.messages.CLIENT_ASESORADO_ASK_HORARIOS
        else:
            session.transition_to(ConversationState.CLIENT_ASESORADO_ZONA)
            return self.messages.CLIENT_ASESORADO_ASK_ZONA

    def handle_client_asesorado_zona(self, session: SessionData, message: str) -> str:
        """Handle selección de zona (solo si presencial)."""
        if message == '0':
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return self.messages.CLIENT_WELCOME_PSIVALE

        if not validate_zona_psivale(message):
            return self.messages.PSIVALE_OPCION_INVALIDA + "\n\n" + self.messages.CLIENT_ASESORADO_ASK_ZONA

        zone = normalize_zona_psivale(message)

        # Get display name
        zone_map = {
            'norte': 'Zona Norte',
            'sur': 'Zona Sur',
            'nueva_cordoba': 'Nueva Córdoba'
        }
        zone_display = zone_map.get(zone, zone)

        # Store filter
        filters = session.get_temp('filters', {})
        filters['zone'] = zone
        filters['zone_display'] = zone_display
        session.store_temp('filters', filters)

        # Next: horarios
        session.transition_to(ConversationState.CLIENT_ASESORADO_HORARIOS)
        return self.messages.CLIENT_ASESORADO_ASK_HORARIOS

    def handle_client_asesorado_horarios(self, session: SessionData, message: str) -> str:
        """Handle selección de horarios."""
        if message == '0':
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return self.messages.CLIENT_WELCOME_PSIVALE

        if message == '5':
            # Cualquier horario - no filtrar
            horarios = None
            horarios_display = "Cualquier horario"
        else:
            if not validate_horarios(message):
                return self.messages.PSIVALE_OPCION_INVALIDA + "\n\n" + self.messages.CLIENT_ASESORADO_ASK_HORARIOS

            horarios = normalize_horario(message)

            # Get display name
            horarios_map = {
                'manana': 'Mañana',
                'tarde': 'Tarde',
                'noche': 'Noche',
                'sabado': 'Sábados'
            }
            horarios_display = horarios_map.get(horarios, horarios)

        # Store filter
        filters = session.get_temp('filters', {})
        if horarios:
            filters['horarios'] = horarios
        filters['horarios_display'] = horarios_display
        session.store_temp('filters', filters)

        # Next: honorarios
        session.transition_to(ConversationState.CLIENT_ASESORADO_HONORARIOS)
        return self.messages.CLIENT_ASESORADO_ASK_HONORARIOS

    def handle_client_asesorado_honorarios(self, session: SessionData, message: str) -> str:
        """Handle selección de rango de honorarios."""
        if message == '0':
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return self.messages.CLIENT_WELCOME_PSIVALE

        if message == '5':
            # Prefiero no decirlo - no filtrar
            fee_range = None
            fee_display = "No especificado"
        else:
            if not validate_fee_range(message):
                return self.messages.PSIVALE_OPCION_INVALIDA + "\n\n" + self.messages.CLIENT_ASESORADO_ASK_HONORARIOS

            fee_range = normalize_fee_range(message)

            # Get display name
            from validators import get_fee_range_display
            fee_display = get_fee_range_display(fee_range)

        # Store filter
        filters = session.get_temp('filters', {})
        if fee_range:
            filters['fee_range'] = fee_range
        filters['fee_display'] = fee_display
        session.store_temp('filters', filters)

        # ⭐ EJECUTAR BÚSQUEDA AHORA
        results = client_service.search_professionals_psivale(
            enfoque=filters.get('enfoque'),
            poblacion=filters.get('poblacion'),
            modalidad=filters.get('modalidad'),
            zone=filters.get('zone'),
            horarios=filters.get('horarios'),
            fee_range=filters.get('fee_range'),
            limit=5
        )

        # Log search in analytics
        from analytics_service import analytics_service
        search_id = analytics_service.log_search(
            client_phone=session.phone_number,
            search_type='psivale_asesorado',
            search_params=filters,
            result_count=len(results),
            session_id=session.phone_number
        )
        session.store_temp('current_search_id', search_id)
        session.store_temp('search_results', results)

        # ⭐ PREPARAR MENSAJE 2 (resultados)
        if len(results) > 0:
            formatted = client_service.format_results_list_psivale(results)
            message_2 = f"""💚 Gracias por compartir. Este paso vale.

    {formatted}"""
        else:
            message_2 = """💚 Gracias por compartir. Este paso vale.

    🌿 No encontré psicólogos con exactamente esos filtros.

    Pero no te preocupes, esto no significa que no haya profesionales para vos.

    ¿Qué querés hacer?
    1️⃣ Ampliar la búsqueda (menos filtros)
    2️⃣ Ver todos los profesionales disponibles
    3️⃣ Empezar de nuevo

    Responde con el número."""

        # ⭐ CREAR FUNCIÓN CALLBACK PARA CAMBIAR ESTADO
        def change_state_after_send():
            """Change session state after second message is sent."""
            session.transition_to(ConversationState.CLIENT_SHOW_RESULTS)
            print(
                f"[BOT] ✅ State changed to CLIENT_SHOW_RESULTS after delayed message")

        from messaging_utils import send_delayed_message
        send_delayed_message(
            to_number=f'whatsapp:{session.phone_number}',
            message=message_2,
            delay_seconds=3,
            callback=change_state_after_send  # ⭐ Cambiar estado después de enviar
        )

        # Build summary
        resumen_lines = []
        if filters.get('enfoque_display'):
            resumen_lines.append(f"🧠 {filters['enfoque_display']}")
        if filters.get('poblacion_display'):
            resumen_lines.append(f"👥 Para: {filters['poblacion_display']}")
        if filters.get('modalidad_display'):
            resumen_lines.append(f"💻 {filters['modalidad_display']}")
        if filters.get('zone_display'):
            resumen_lines.append(f"📍 {filters['zone_display']}")
        if filters.get('horarios_display'):
            resumen_lines.append(f"📅 {filters['horarios_display']}")
        if filters.get('fee_display'):
            resumen_lines.append(f"💰 {filters['fee_display']}")

        resumen_text = "\n".join(resumen_lines)

        # Usar el mensaje de messages.py
        return self.messages.CLIENT_ASESORADO_RESUMEN.format(resumen=resumen_text)

    def handle_client_asesorado_resumen(self, session: SessionData, message: str) -> str:
        """
        ⚠️ DEPRECADO: Este handler ya no se usa en el flujo principal.
        La búsqueda ahora se ejecuta desde handle_client_asesorado_honorarios.

        Mantener solo por compatibilidad.
        """
        # Redirigir al welcome
        session.clear_temp()
        session.transition_to(ConversationState.CLIENT_ASESORADO_WELCOME)
        return self.messages.WELCOME

    def handle_client_asesorado_buscando(self, session: SessionData, message: str) -> str:
        """
        Handle ejecución de búsqueda y mostrar resultados.
        Este handler se ejecuta después de mostrar el resumen.
        """

        filters = session.get_temp('filters', {})

        # Execute search using Psivale search
        results = client_service.search_professionals_psivale(
            enfoque=filters.get('enfoque'),
            poblacion=filters.get('poblacion'),
            modalidad=filters.get('modalidad'),
            zone=filters.get('zone'),
            horarios=filters.get('horarios'),
            fee_range=filters.get('fee_range'),
            limit=5  # Solo 5 resultados
        )

        # Log search in analytics
        search_id = analytics_service.log_search(
            client_phone=session.phone_number,
            search_type='psivale_asesorado',
            search_params=filters,
            result_count=len(results),
            session_id=session.phone_number
        )
        session.store_temp('current_search_id', search_id)
        session.store_temp('search_results', results)

        # Transition to results
        session.transition_to(ConversationState.CLIENT_SHOW_RESULTS)

        # ⭐ MENSAJE 2: Resultados o sin resultados
        if len(results) > 0:
            formatted = client_service.format_results_list_psivale(results)
            return f"""💚 Gracias por compartir. Este paso vale.

    {formatted}"""
        else:
            return """💚 Gracias por compartir. Este paso vale.

    🌿 No encontré psicólogos con exactamente esos filtros.

    Pero no te preocupes, esto no significa que no haya profesionales para vos.

    ¿Qué querés hacer?
    1️⃣ Ampliar la búsqueda (menos filtros)
    2️⃣ Ver todos los profesionales disponibles
    3️⃣ Empezar de nuevo

    Responde con el número."""

    # ==========================================
    # UTILITY HANDLERS
    # ==========================================

    def handle_return_to_menu(self, session: SessionData) -> str:
        """Handle return to menu command."""
        session.clear_temp()

        if session.role == UserRole.PROFESSIONAL:
            session.transition_to(ConversationState.PROF_MAIN_MENU)
            return self.messages.PROF_MAIN_MENU
        elif session.role == UserRole.CLIENT:
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return self.messages.CLIENT_MAIN_MENU
        else:
            session.reset()
            return self.messages.WELCOME

    def handle_cancel(self, session: SessionData) -> str:
        """Handle cancel command."""
        session.clear_temp()
        return self.handle_return_to_menu(session)

    def handle_unknown_state(self, session: SessionData, message: str) -> str:
        """Handle unknown/unimplemented state."""
        print(f"⚠️ Unknown state: {session.state}")
        return self.messages.ERROR_GENERIC

    # ==========================================
    # Filtro flexible - parser inteligente
    # ==========================================

    def parse_filter_line_smart(self, line: str) -> tuple:
        """
        Parse a single filter line intelligently.
        Supports both formats:
        - "zona: norte" (with colon)
        - "zona norte" (without colon)

        Args:
            line: Single line from user input

        Returns:
            (filter_type, filter_value) or (None, None) if not recognized
        """
        line = line.strip().lower()

        # Try format with colon first
        if ':' in line:
            parts = line.split(':', 1)
            key = parts[0].strip()
            value = parts[1].strip()
            return (key, value)

        # Try format without colon - split by space
        words = line.split()
        if len(words) < 2:
            # Single word - might be a direct value
            return (None, words[0])

        # Check if first word(s) match a filter keyword
        filter_keywords = {
            'enfoque': ['enfoque', 'terapia', 'tipo'],
            'poblacion': ['poblacion', 'población', 'para', 'paciente'],
            'modalidad': ['modalidad', 'modo', 'formato'],
            'zona': ['zona', 'barrio', 'lugar', 'ubicacion', 'ubicación'],
            'horarios': ['horarios', 'horario', 'disponibilidad', 'cuando'],
            'honorarios': ['honorarios', 'honorario', 'precio', 'costo', 'presupuesto']
        }

        # Try to match first word(s) to a filter type
        for filter_type, keywords in filter_keywords.items():
            for keyword in keywords:
                if line.startswith(keyword + ' '):
                    # Found match - rest is the value
                    value = line[len(keyword):].strip()
                    return (filter_type, value)

        # No filter keyword found - treat as direct value
        return (None, line)

    # ==========================================
    # Utilidad para detectar tipo de valor
    # ==========================================

    def detect_value_type(self, value: str) -> str:
        """
        Detect which filter type a value belongs to.

        Args:
            value: Value to classify

        Returns:
            Filter type ('enfoque', 'poblacion', etc.) or None
        """
        value = value.lower().strip()

        # Define value patterns for each filter
        value_patterns = {
            'enfoque': ['tcc', 'contextual', 'sistemica', 'sistémica', 'gestaltica',
                        'gestáltica', 'psicoanalisis', 'psicoanálisis', 'neuropsicologia',
                        'neuropsicología', 'aptos', 'apto', 'evaluaciones', 'certificados'],
            'poblacion': ['ninos', 'niños', 'adolescentes', 'adultos', 'parejas',
                          'pareja', 'familia', 'familias'],
            'modalidad': ['online', 'presencial', 'ambas', 'virtual', 'remoto',
                          'casa', 'videollamada'],
            'zona': ['norte', 'sur', 'nueva_cordoba', 'nueva cordoba', 'centro',
                     'nueva córdoba'],
            'horarios': ['manana', 'mañana', 'tarde', 'noche', 'sabado', 'sábado',
                         'finde', 'fines de semana'],
            'honorarios': ['1', '2', '3', '4']
        }

        # Check each filter type
        for filter_type, patterns in value_patterns.items():
            if value in patterns:
                return filter_type

        return None


# Global bot instance
bot = Bot()
