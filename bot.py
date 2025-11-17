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
    parse_time_range
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

        Args:
            phone_number: User's WhatsApp number
            message: Text message from user

        Returns:
            Bot's response message
        """
        # Get or create session
        session = session_manager.get_session(phone_number)

        # Clean message
        message = message.strip()
        message_lower = message.lower()

        # ==========================================
        # SUPER COMMAND: "HOLA" ALWAYS RESETS
        # ==========================================
        # No matter what state, "hola" restarts conversation
        if message_lower in ['hola', 'hello', 'hi', 'hey']:
            session.reset()
            session.transition_to(ConversationState.ROLE_SELECTION)
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
        """
        Get the appropriate handler function for a state.

        Args:
            state: Current conversation state

        Returns:
            Handler function
        """
        handlers = {
            # Initial states
            ConversationState.START: self.handle_start,
            ConversationState.ROLE_SELECTION: self.handle_role_selection,

            # Professional states
            ConversationState.PROF_NEED_CERTIFICATE: self.handle_prof_need_certificate,
            ConversationState.PROF_MAIN_MENU: self.handle_prof_main_menu,
            ConversationState.PROF_FREE_SLOT_DATE: self.handle_prof_free_slot_date,
            ConversationState.PROF_FREE_SLOT_TIME: self.handle_prof_free_slot_time,
            ConversationState.PROF_FREE_SLOT_CONFIRM: self.handle_prof_free_slot_confirm,
            ConversationState.PROF_WEEK_SCHEDULE_QUICK: self.handle_prof_week_schedule_quick,

            # Client states
            ConversationState.CLIENT_MAIN_MENU: self.handle_client_main_menu,
            ConversationState.CLIENT_FILTER_ZONA: self.handle_client_filter_zona,
            ConversationState.CLIENT_FILTER_FECHA: self.handle_client_filter_fecha,
            ConversationState.CLIENT_FILTER_HORA: self.handle_client_filter_hora,
            ConversationState.CLIENT_FILTER_PREPAGA: self.handle_client_filter_prepaga,
            ConversationState.CLIENT_FILTER_SEXO: self.handle_client_filter_sexo,
            ConversationState.CLIENT_SHOW_RESULTS: self.handle_client_show_results,
            ConversationState.CLIENT_VIEW_DETAIL: self.handle_client_view_detail,

            # Client multi-filter states
            ConversationState.CLIENT_MULTIFILTER_MENU: self.handle_client_multifilter_menu,
            ConversationState.CLIENT_MULTIFILTER_ZONA: self.handle_client_multifilter_zona,
            ConversationState.CLIENT_MULTIFILTER_FECHA: self.handle_client_multifilter_fecha,
            ConversationState.CLIENT_MULTIFILTER_HORA: self.handle_client_multifilter_hora,
            ConversationState.CLIENT_MULTIFILTER_PREPAGA: self.handle_client_multifilter_prepaga,
            ConversationState.CLIENT_MULTIFILTER_SEXO: self.handle_client_multifilter_sexo,
            ConversationState.CLIENT_SEARCH_QUICK: self.handle_client_search_quick,

            # Professional info states
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
        }

        return handlers.get(state, self.handle_unknown_state)

    # ==========================================
    # INITIAL HANDLERS
    # ==========================================

    def handle_start(self, session: SessionData, message: str) -> str:
        """Handle start state - show welcome message."""
        session.transition_to(ConversationState.ROLE_SELECTION)
        return self.messages.WELCOME

    def handle_role_selection(self, session: SessionData, message: str) -> str:
        """Handle role selection - professional or client."""
        if message == '1':
            # Usuario seleccionó opción 1 = CLIENTE/PACIENTE
            session.set_role(UserRole.CLIENT)
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return self.messages.CLIENT_MAIN_MENU

        elif message == '2':
            # Usuario seleccionó opción 2 = PROFESIONAL
            session.set_role(UserRole.PROFESSIONAL)

            # Check if professional already has certificate
            if professional_service.has_certificate(session.phone_number):
                # Already has certificate - go directly to main menu
                print(
                    f"[BOT] Professional {session.phone_number} already has certificate, skipping upload")
                session.transition_to(ConversationState.PROF_MAIN_MENU)
                return self.messages.PROF_MAIN_MENU
            else:
                # No certificate - ask for upload
                print(
                    f"[BOT] Professional {session.phone_number} needs to upload certificate")
                session.transition_to(ConversationState.PROF_NEED_CERTIFICATE)
                return self.messages.PROF_NEED_CERTIFICATE

        else:
            return self.messages.INVALID_ROLE
    # ==========================================
    # PROFESSIONAL HANDLERS
    # ==========================================

    def handle_prof_need_certificate(self, session: SessionData, message: str) -> str:
        """
        Handle certificate requirement state.
        Professional MUST upload certificate before accessing any menu.
        Block all text inputs until file is uploaded.
        Note: File upload is handled separately in whatsapp_handler.py
        """
        # Block '0' and any other text input
        # User must upload certificate file to continue
        return self.messages.PROF_NEED_CERTIFICATE

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
            # Initialize info dict if not exists
            if not session.get_temp('prof_info'):
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

    def handle_prof_info_menu(self, session: SessionData, message: str) -> str:
        """Handle professional info menu."""

        if message == '1':
            # Nombre
            session.transition_to(ConversationState.PROF_INFO_NAME)
            return self.messages.PROF_INFO_ASK_NAME

        elif message == '2':
            # Email
            session.transition_to(ConversationState.PROF_INFO_EMAIL)
            return self.messages.PROF_INFO_ASK_EMAIL

        elif message == '3':
            # Zona
            session.transition_to(ConversationState.PROF_INFO_ZONA)
            return self.messages.PROF_INFO_ASK_ZONA

        elif message == '4':
            # Género
            session.transition_to(ConversationState.PROF_INFO_GENERO)
            return self.messages.PROF_INFO_ASK_GENERO

        elif message == '5':
            # Prepaga
            session.transition_to(ConversationState.PROF_INFO_PREPAGA)
            return self.messages.PROF_INFO_ASK_PREPAGA

        elif message == '6':
            # Especialidad
            session.transition_to(ConversationState.PROF_INFO_ESPECIALIDAD)
            return self.messages.PROF_INFO_ASK_ESPECIALIDAD

        elif message == '7':
            # Bio
            session.transition_to(ConversationState.PROF_INFO_BIO)
            return self.messages.PROF_INFO_ASK_BIO

        elif message == '8':
            # Honorarios
            session.transition_to(ConversationState.PROF_INFO_FEE_RANGE)
            return self.messages.PROF_INFO_ASK_FEE_RANGE

        elif message == '9':
            # Guardar información
            prof_info = session.get_temp('prof_info', {})

            # Type check
            if not isinstance(prof_info, dict):
                prof_info = {}

            # Validate required fields
            required = ['name', 'especialidad', 'zona']
            missing = [f for f in required if f not in prof_info]

            if missing:
                return self.messages.PROF_INFO_INCOMPLETE + "\n\n" + self.format_prof_info_menu(session)

            # Save to database using professional_service
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
            summary_lines = []
            summary_lines.append(f"👤 Nombre: {prof_info.get('name', 'N/A')}")
            summary_lines.append(
                f"🏥 Especialidad: {prof_info.get('especialidad', 'N/A')}")
            summary_lines.append(
                f"📍 Zona: {prof_info.get('zona', 'N/A').capitalize()}")

            if 'email' in prof_info:
                summary_lines.append(f"📧 Email: {prof_info['email']}")
            if 'genero' in prof_info:
                genero_map = {'m': 'Masculino', 'f': 'Femenino', 'o': 'Otro'}
                summary_lines.append(
                    f"👥 Género: {genero_map.get(prof_info['genero'], prof_info['genero'])}")
            if 'bio' in prof_info:
                bio_preview = prof_info['bio'][:50] + \
                    "..." if len(prof_info['bio']) > 50 else prof_info['bio']
                summary_lines.append(f"📝 Bio: {bio_preview}")
            if 'fee_range' in prof_info:
                summary_lines.append(
                    f"💰 Honorarios: ${prof_info['fee_range']}")

            profile_summary = "\n".join(summary_lines)

            session.clear_temp()
            session.transition_to(ConversationState.PROF_MAIN_MENU)

            return self.messages.PROF_INFO_SAVED.format(
                profile_summary=profile_summary
            ) + "\n\n" + self.messages.PROF_MAIN_MENU

        elif message == '0':
            # Volver al menú
            session.clear_temp()
            session.transition_to(ConversationState.PROF_MAIN_MENU)
            return self.messages.PROF_MAIN_MENU

        else:
            return self.messages.INVALID_OPTION + "\n\n" + self.format_prof_info_menu(session)

    def handle_prof_info_name(self, session: SessionData, message: str) -> str:
        """Handle name input."""
        if message == '0':
            session.transition_to(ConversationState.PROF_INFO_MENU)
            return self.format_prof_info_menu(session)

        # Store name
        prof_info = session.get_temp('prof_info', {})
        prof_info['name'] = message
        session.store_temp('prof_info', prof_info)

        session.transition_to(ConversationState.PROF_INFO_MENU)
        return f"✅ Nombre guardado: {message}\n\n" + self.format_prof_info_menu(session)

    def handle_prof_info_email(self, session: SessionData, message: str) -> str:
        """Handle email input."""
        if message == '0':
            session.transition_to(ConversationState.PROF_INFO_MENU)
            return self.format_prof_info_menu(session)

        # Validate email format
        from validators import validate_email
        if not validate_email(message):
            return "❌ Email inválido. Intenta nuevamente:\nEjemplo: juan@email.com"

        # Store email
        prof_info = session.get_temp('prof_info', {})
        prof_info['email'] = message
        session.store_temp('prof_info', prof_info)

        session.transition_to(ConversationState.PROF_INFO_MENU)
        return f"✅ Email guardado: {message}\n\n" + self.format_prof_info_menu(session)

    def handle_prof_info_zona(self, session: SessionData, message: str) -> str:
        """Handle zona input."""
        if message == '0':
            session.transition_to(ConversationState.PROF_INFO_MENU)
            return self.format_prof_info_menu(session)

        if message == '1':
            zona = 'norte'
        elif message == '2':
            zona = 'sur'
        else:
            return self.messages.INVALID_OPTION + "\n\n" + self.messages.PROF_INFO_ASK_ZONA

        # Store zona
        prof_info = session.get_temp('prof_info', {})
        prof_info['zona'] = zona
        session.store_temp('prof_info', prof_info)

        session.transition_to(ConversationState.PROF_INFO_MENU)
        return f"✅ Zona guardada: {zona.capitalize()}\n\n" + self.format_prof_info_menu(session)

    def handle_prof_info_genero(self, session: SessionData, message: str) -> str:
        """Handle genero input."""
        if message == '0':
            session.transition_to(ConversationState.PROF_INFO_MENU)
            return self.format_prof_info_menu(session)

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
        prof_info['genero'] = genero
        session.store_temp('prof_info', prof_info)

        genero_map = {'m': 'Masculino', 'f': 'Femenino', 'o': 'Otro'}
        session.transition_to(ConversationState.PROF_INFO_MENU)
        return f"✅ Género guardado: {genero_map[genero]}\n\n" + self.format_prof_info_menu(session)

    def handle_prof_info_prepaga(self, session: SessionData, message: str) -> str:
        """Handle prepaga input."""
        if message == '0':
            session.transition_to(ConversationState.PROF_INFO_MENU)
            return self.format_prof_info_menu(session)

        if message == '1':
            prepaga = True
        elif message == '2':
            prepaga = False
        else:
            return self.messages.INVALID_OPTION + "\n\n" + self.messages.PROF_INFO_ASK_PREPAGA

        # Store prepaga
        prof_info = session.get_temp('prof_info', {})
        prof_info['prepaga'] = prepaga
        session.store_temp('prof_info', prof_info)

        session.transition_to(ConversationState.PROF_INFO_MENU)
        return f"✅ Prepaga: {'Sí' if prepaga else 'No'}\n\n" + self.format_prof_info_menu(session)

    def handle_prof_info_especialidad(self, session: SessionData, message: str) -> str:
        """Handle especialidad input."""
        if message == '0':
            session.transition_to(ConversationState.PROF_INFO_MENU)
            return self.format_prof_info_menu(session)

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
        return f"✅ Especialidad guardada: {especialidad}\n\n" + self.format_prof_info_menu(session)

    def handle_prof_info_bio(self, session: SessionData, message: str) -> str:
        """Handle bio input."""
        if message == '0':
            session.transition_to(ConversationState.PROF_INFO_MENU)
            return self.format_prof_info_menu(session)

        # Guardar bio en temp
        session.store_temp('bio', message)

        # Volver al menú
        session.transition_to(ConversationState.PROF_INFO_MENU)
        return f"✅ Descripción guardada.\n\n{self.format_prof_info_menu(session)}"

    def handle_prof_info_fee_range(self, session: SessionData, message: str) -> str:
        """Handle fee range input."""
        if message == '0':
            session.transition_to(ConversationState.PROF_INFO_MENU)
            return self.format_prof_info_menu(session)

        # Validar formato: XXX-YYY
        import re
        match = re.match(r'^(\d+)-(\d+)$', message.strip())

        if not match:
            return "❌ Formato incorrecto.\n\nUsa: MÍNIMO-MÁXIMO\nEjemplo: 100-150\n\n💡 Escribe '0' para volver"

        min_fee, max_fee = match.groups()

        if int(min_fee) >= int(max_fee):
            return "❌ El mínimo debe ser menor que el máximo.\n\n💡 Escribe '0' para volver"

        # Guardar en temp
        session.store_temp('fee_range', message)

        # Volver al menú
        session.transition_to(ConversationState.PROF_INFO_MENU)
        return f"✅ Honorarios guardados: ${min_fee} - ${max_fee}\n\n{self.format_prof_info_menu(session)}"

    def parse_prof_info_quick(self, message: str) -> dict:
        """
        Parse professional info from message.
        Supports two formats:

        Format 1 (with labels):
            nombre: Juan Pérez
            email: juan@email.com
            zona: norte
            genero: masculino
            prepaga: si
            especialidad: dentista
            bio: Descripción (opcional)
            honorarios: 100-150 (opcional)

        Format 2 (without labels, order matters):
            Juan Pérez
            juan@email.com
            norte
            masculino
            si
            dentista
            Descripción (opcional - línea 7)
            100-150 (opcional - línea 8)

        Returns:
            (dict with parsed info, list of errors)
        """
        import re

        lines = [line.strip()
                 for line in message.strip().split('\n') if line.strip()]

        # Check if using labeled format (has ':')
        has_labels = any(':' in line for line in lines)

        result = {}
        errors = []

        if has_labels:
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
                    result['zona'] = value.lower()
                elif key in ['genero', 'género', 'sexo', 'gender']:
                    result['genero'] = value.lower()
                elif key in ['prepaga', 'obra social', 'os']:
                    result['prepaga'] = value.lower()
                elif key in ['especialidad', 'specialty', 'profesion', 'profesión', 'category']:
                    result['especialidad'] = value
                elif key in ['bio', 'descripcion', 'descripción', 'about']:  # ← AGREGAR
                    result['bio'] = value
                elif key in ['honorarios', 'fee', 'precio', 'costo']:  # ← AGREGAR
                    result['fee_range'] = value
        else:
            # Parse order-based format
            if len(lines) < 6:
                return None, [f"❌ Esperaba al menos 6 líneas, recibí {len(lines)}"]

            result = {
                'name': lines[0],
                'email': lines[1],
                'zona': lines[2].lower(),
                'genero': lines[3].lower(),
                'prepaga': lines[4].lower(),
                'especialidad': lines[5]
            }

            # Optional fields (líneas 7 y 8)
            if len(lines) >= 7 and lines[6]:  # ← AGREGAR
                result['bio'] = lines[6]
            if len(lines) >= 8 and lines[7]:  # ← AGREGAR
                result['fee_range'] = lines[7]

        # Validate required fields
        required = ['name', 'email', 'zona',
                    'genero', 'prepaga', 'especialidad']
        missing = [f for f in required if f not in result or not result[f]]

        if missing:
            errors.append(f"❌ Faltan campos: {', '.join(missing)}")
            return None, errors

        # Validate and normalize each field
        from validators import validate_email

        # Email
        if not validate_email(result['email']):
            errors.append(f"❌ Email inválido: {result['email']}")

        # Zona
        zona_map = {
            'norte': 'norte', 'n': 'norte', 'north': 'norte',
            'sur': 'sur', 's': 'sur', 'south': 'sur'
        }
        if result['zona'] not in zona_map:
            errors.append(
                f"❌ Zona inválida: {result['zona']} (usa: norte o sur)")
        else:
            result['zona'] = zona_map[result['zona']]

        # Género
        genero_map = {
            'm': 'm', 'masculino': 'm', 'male': 'm', 'hombre': 'm',
            'f': 'f', 'femenino': 'f', 'female': 'f', 'mujer': 'f',
            'o': 'o', 'otro': 'o', 'other': 'o', 'nobinario': 'o', 'no binario': 'o'
        }
        if result['genero'] not in genero_map:
            errors.append(
                f"❌ Género inválido: {result['genero']} (usa: masculino, femenino, otro)")
        else:
            result['genero'] = genero_map[result['genero']]

        # Prepaga
        prepaga_map = {
            'si': True, 'sí': True, 's': True, 'yes': True, 'y': True,
            'no': False, 'n': False
        }
        if result['prepaga'] not in prepaga_map:
            errors.append(
                f"❌ Prepaga inválida: {result['prepaga']} (usa: si o no)")
        else:
            result['prepaga'] = prepaga_map[result['prepaga']]

        # Validar fee_range si existe (opcional)  # ← AGREGAR
        if 'fee_range' in result:
            match = re.match(r'^(\d+)-(\d+)$', result['fee_range'].strip())
            if not match:
                errors.append(
                    f"❌ Honorarios inválidos: {result['fee_range']} (usa formato: 100-150)")
            else:
                min_fee, max_fee = match.groups()
                if int(min_fee) >= int(max_fee):
                    errors.append(
                        f"❌ Honorarios: el mínimo debe ser menor que el máximo")

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
    # CLIENT HANDLERS
    # ==========================================

    def handle_client_main_menu(self, session: SessionData, message: str) -> str:
        """Handle client main menu."""
        if message == '1':
            # Buscar para hoy
            from datetime import date
            today = date.today()
            session.clear_temp()
            session.store_temp('fecha', today)
            session.store_temp('fecha_str', today.strftime("%d/%m/%Y"))
            session.transition_to(ConversationState.CLIENT_FILTER_HORA)

            return self.messages.CLIENT_SEARCH_TODAY_CONFIRM.format(
                today_date=today.strftime("%d/%m/%Y")
            )

        elif message == '2':
            # Búsqueda avanzada (paso a paso)
            session.clear_temp()
            session.store_temp('filters', {})
            session.transition_to(ConversationState.CLIENT_MULTIFILTER_MENU)
            return self.format_multifilter_menu(session)

        elif message == '3':
            # Búsqueda rápida (todo en 1 mensaje)
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_SEARCH_QUICK)
            return self.messages.CLIENT_SEARCH_QUICK_FORMAT

        elif message == '4':
            # Virtual - BÚSQUEDA DIRECTA
            # Buscar profesionales con sesiones online
            results = client_service.search_professionals_by_filters(
                online_sessions=True,
                limit=10
            )

            # Log search
            search_id = analytics_service.log_search(
                client_phone=session.phone_number,
                search_type='virtual',
                search_params={'online_sessions': True},
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

        elif message == '5':
            # Presencial - PREGUNTAR ZONA
            session.clear_temp()
            session.store_temp('modality', 'presencial')
            session.transition_to(ConversationState.CLIENT_FILTER_ZONA)
            return self.messages.CLIENT_ASK_ZONA
        elif message == '0':
            session.reset()
            return self.messages.WELCOME

        else:
            return self.messages.INVALID_OPTION + "\n\n" + self.messages.CLIENT_MAIN_MENU

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

    def handle_client_show_results(self, session: SessionData, message: str) -> str:
        """Handle client viewing search results and selecting a professional."""

        # Get stored results
        results = session.get_temp('search_results', [])

        # Check if no results and user is choosing an option
        if len(results) == 0:
            if message == '1':
                # Modificar búsqueda - volver al menú cliente
                session.clear_temp()
                session.transition_to(ConversationState.CLIENT_MAIN_MENU)
                return self.messages.CLIENT_MAIN_MENU

            elif message == '2':
                # Ver todos los profesionales (sin filtros)
                # Search without filters
                all_results = client_service.search_professionals_by_filters(
                    limit=10)

                # Log search
                search_id = analytics_service.log_search(
                    client_phone=session.phone_number,
                    search_type='all',
                    search_params={},
                    result_count=len(all_results),
                    session_id=session.phone_number
                )
                session.store_temp('current_search_id', search_id)
                session.store_temp('search_results', all_results)

                # Format and return
                formatted = client_service.format_results_list(all_results)
                return formatted

            elif message == '0':
                # Volver al menú cliente
                session.clear_temp()
                session.transition_to(ConversationState.CLIENT_MAIN_MENU)
                return self.messages.CLIENT_MAIN_MENU

            else:
                # Invalid option - show no results message again
                formatted = client_service.format_results_list([])
                return self.messages.INVALID_OPTION + "\n\n" + formatted

        # Normal flow - has results
        if message == '0':
            # Volver al menú
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return self.messages.CLIENT_MAIN_MENU

        # Check if user selected a number
        try:
            selection = int(message)

            if 1 <= selection <= len(results):
                # Valid selection - show professional detail
                selected_prof = results[selection - 1]

                # Store selected professional and position
                session.store_temp('selected_professional', selected_prof)
                session.store_temp('selected_position', selection)

                # Log analytics: profile view + contact intent
                from analytics_service import analytics_service

                # Increment profile views
                analytics_service.log_profile_view(selected_prof['phone'])

                # Log contact
                search_id = session.get_temp('current_search_id')
                analytics_service.log_contact(
                    search_id=search_id,
                    professional_phone=selected_prof['phone'],
                    result_position=selection
                )

                # Get detailed info
                from client_service import client_service
                prof_detail = client_service.get_professional_detail(
                    selected_prof['phone'])

                # Format and show detail
                formatted = client_service.format_professional_detail(
                    prof_detail)
                session.transition_to(ConversationState.CLIENT_VIEW_DETAIL)

                return formatted
            else:
                return f"❌ Opción inválida. Selecciona un número entre 1 y {len(results)}, o '0' para volver."

        except ValueError:
            return "❌ Por favor, ingresa el número del profesional que deseas ver.\nO '0' para volver al menú."

    def parse_client_search_quick(self, message: str) -> dict:
        """
        Parse client search filters from message.
        Supports two formats:

        Format 1 (with labels):
            zona: norte
            fecha: 15/11/2025
            hora: 14:00
            prepaga: si
            genero: masculino

        Format 2 (without labels, order matters):
            norte
            15/11/2025
            14:00
            si
            masculino

        All fields are optional.

        Returns:
            dict with parsed filters and list of errors
        """
        import re
        from validators import validate_email, parse_date, validate_time

        lines = [line.strip()
                 for line in message.strip().split('\n') if line.strip()]

        if not lines:
            return None, ["❌ Debes enviar al menos un filtro"]

        # Check if using labeled format (has ':')
        has_labels = any(':' in line for line in lines)

        result = {}
        errors = []

        if has_labels:
            # Parse labeled format - fields can be in any order
            for line in lines:
                if ':' not in line:
                    continue

                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()

                if not value:
                    continue

                # Map variations to standard keys
                if key in ['zona', 'zone', 'area']:
                    result['zona'] = value.lower()
                elif key in ['fecha', 'date', 'dia', 'día']:
                    result['fecha_str'] = value
                elif key in ['hora', 'time', 'horario']:
                    result['hora'] = value
                elif key in ['prepaga', 'obra social', 'os']:
                    result['prepaga'] = value.lower()
                elif key in ['genero', 'género', 'sexo', 'gender']:
                    result['genero'] = value.lower()
        else:
            # Parse order-based format
            # Order: zona, fecha, hora, prepaga, genero
            # But all are optional, so we need to be smart

            # Try to detect what each line is
            for line in lines:
                line_lower = line.lower()

                # Detect zona (norte/sur)
                if line_lower in ['norte', 'sur', 'n', 's'] and 'zona' not in result:
                    result['zona'] = line_lower

                # Detect fecha (DD/MM/YYYY)
                elif '/' in line and 'fecha_str' not in result:
                    result['fecha_str'] = line

                # Detect hora (HH:MM)
                elif ':' in line and len(line) == 5 and 'hora' not in result:
                    result['hora'] = line

                # Detect prepaga (si/no)
                elif line_lower in ['si', 'sí', 's', 'no', 'n'] and 'prepaga' not in result:
                    result['prepaga'] = line_lower

                # Detect genero
                elif line_lower in ['masculino', 'femenino', 'otro', 'm', 'f', 'o'] and 'genero' not in result:
                    result['genero'] = line_lower

        # Check if at least one filter was provided
        if not result:
            return None, ["❌ No se detectaron filtros válidos"]

        # Validate and normalize each field
        validated = {}

        # Zona
        if 'zona' in result:
            zona_map = {
                'norte': 'norte', 'n': 'norte', 'north': 'norte',
                'sur': 'sur', 's': 'sur', 'south': 'sur'
            }
            if result['zona'] not in zona_map:
                errors.append(
                    f"❌ Zona inválida: {result['zona']} (usa: norte o sur)")
            else:
                validated['zona'] = zona_map[result['zona']]

        # Fecha
        if 'fecha_str' in result:
            fecha_obj = parse_date(result['fecha_str'])
            if not fecha_obj:
                errors.append(
                    f"❌ Fecha inválida: {result['fecha_str']} (usa: DD/MM/YYYY)")
            else:
                validated['fecha'] = fecha_obj
                validated['fecha_str'] = result['fecha_str']

        # Hora
        if 'hora' in result:
            if not validate_time(result['hora']):
                errors.append(
                    f"❌ Hora inválida: {result['hora']} (usa: HH:MM)")
            else:
                validated['hora'] = result['hora']

        # Prepaga
        if 'prepaga' in result:
            prepaga_map = {
                'si': True, 'sí': True, 's': True, 'yes': True, 'y': True,
                'no': False, 'n': False
            }
            if result['prepaga'] not in prepaga_map:
                errors.append(
                    f"❌ Prepaga inválida: {result['prepaga']} (usa: si o no)")
            else:
                validated['prepaga'] = prepaga_map[result['prepaga']]

        # Género
        if 'genero' in result:
            genero_map = {
                'm': 'm', 'masculino': 'm', 'male': 'm', 'hombre': 'm',
                'f': 'f', 'femenino': 'f', 'female': 'f', 'mujer': 'f',
                'o': 'o', 'otro': 'o', 'other': 'o'
            }
            if result['genero'] not in genero_map:
                errors.append(
                    f"❌ Género inválido: {result['genero']} (usa: masculino, femenino, otro)")
            else:
                validated['genero'] = genero_map[result['genero']]

        if errors:
            return None, errors

        if not validated:
            return None, ["❌ No se pudieron validar los filtros"]

        return validated, []

    def handle_client_search_quick(self, session: SessionData, message: str) -> str:
        """Handle quick search input (all filters in one message)."""

        if message == '0':
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return self.messages.CLIENT_MAIN_MENU

        # Parse the message
        filters, errors = self.parse_client_search_quick(message)

        if errors:
            error_msg = "\n".join(errors)
            return f"{error_msg}\n\n{self.messages.CLIENT_SEARCH_QUICK_FORMAT}"

        # Store filters
        session.store_temp('filters', filters)

        # TODO: Search database with filters
        print(f"[DB] TODO: Quick search with filters - {filters}")

        # Format filters for display
        filter_lines = []
        if 'zona' in filters:
            filter_lines.append(f"📍 Zona: {filters['zona'].capitalize()}")
        if 'fecha_str' in filters:
            filter_lines.append(f"📅 Fecha: {filters['fecha_str']}")
        if 'hora' in filters:
            filter_lines.append(f"⏰ Hora: {filters['hora']}")
        if 'prepaga' in filters:
            filter_lines.append(
                f"💳 Prepaga: {'Sí' if filters['prepaga'] else 'No'}")
        if 'genero' in filters:
            genero_map = {'m': 'Masculino', 'f': 'Femenino', 'o': 'Otro'}
            filter_lines.append(f"👥 Género: {genero_map[filters['genero']]}")

        filters_text = "\n".join(filter_lines)

        session.transition_to(ConversationState.CLIENT_SHOW_RESULTS)

        return f"""🔍 Búsqueda Rápida

Filtros aplicados:
{filters_text}

📋 Buscando profesionales...

Próximamente mostraré resultados.

Escribe 'menu' para volver."""

    def handle_client_view_detail(self, session: SessionData, message: str) -> str:
        """Handle client viewing professional detail and navigation."""

        selected_prof = session.get_temp('selected_professional')

        if not selected_prof:
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return "❌ Error. Volviendo al menú...\n\n" + self.messages.CLIENT_MAIN_MENU

        if message == '1':
            # Nueva búsqueda - volver al menú cliente
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return self.messages.CLIENT_MAIN_MENU

        elif message == '0':
            # Volver al menú cliente (mismo que opción 1)
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return self.messages.CLIENT_MAIN_MENU

        else:
            # Invalid option - show detail again
            prof_detail = client_service.get_professional_detail(
                selected_prof['phone'])
            formatted = client_service.format_professional_detail(prof_detail)
            return self.messages.INVALID_OPTION + "\n\n" + formatted

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


# Global bot instance
bot = Bot()
