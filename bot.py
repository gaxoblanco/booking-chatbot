"""
Bot Logic
=========
Main conversation handler with state machine implementation.
Processes incoming messages and manages conversation flow.
"""

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
            ConversationState.PROF_BUSY_SLOT_DATE: self.handle_prof_busy_slot_date,
            ConversationState.PROF_BUSY_SLOT_TIME: self.handle_prof_busy_slot_time,
            ConversationState.PROF_BUSY_SLOT_CONFIRM: self.handle_prof_busy_slot_confirm,
            ConversationState.PROF_WEEK_SCHEDULE_DAY: self.handle_prof_week_day,
            ConversationState.PROF_WEEK_SCHEDULE_TIME: self.handle_prof_week_time,
            ConversationState.PROF_WEEK_SCHEDULE_MORE: self.handle_prof_week_more,

            # Client states
            ConversationState.CLIENT_MAIN_MENU: self.handle_client_main_menu,
            ConversationState.CLIENT_FILTER_ZONA: self.handle_client_filter_zona,
            ConversationState.CLIENT_FILTER_FECHA: self.handle_client_filter_fecha,
            ConversationState.CLIENT_FILTER_HORA: self.handle_client_filter_hora,
            ConversationState.CLIENT_FILTER_PREPAGA: self.handle_client_filter_prepaga,
            ConversationState.CLIENT_FILTER_SEXO: self.handle_client_filter_sexo,
            ConversationState.CLIENT_SHOW_RESULTS: self.handle_client_show_results,

            # Client multi-filter states
            ConversationState.CLIENT_MULTIFILTER_MENU: self.handle_client_multifilter_menu,
            ConversationState.CLIENT_MULTIFILTER_ZONA: self.handle_client_multifilter_zona,
            ConversationState.CLIENT_MULTIFILTER_FECHA: self.handle_client_multifilter_fecha,
            ConversationState.CLIENT_MULTIFILTER_HORA: self.handle_client_multifilter_hora,
            ConversationState.CLIENT_MULTIFILTER_PREPAGA: self.handle_client_multifilter_prepaga,
            ConversationState.CLIENT_MULTIFILTER_SEXO: self.handle_client_multifilter_sexo,

            # Professional info states
            ConversationState.PROF_INFO_MENU: self.handle_prof_info_menu,
            ConversationState.PROF_INFO_NAME: self.handle_prof_info_name,
            ConversationState.PROF_INFO_EMAIL: self.handle_prof_info_email,
            ConversationState.PROF_INFO_ZONA: self.handle_prof_info_zona,
            ConversationState.PROF_INFO_GENERO: self.handle_prof_info_genero,
            ConversationState.PROF_INFO_PREPAGA: self.handle_prof_info_prepaga,
            ConversationState.PROF_INFO_ESPECIALIDAD: self.handle_prof_info_especialidad,
            ConversationState.PROF_INFO_QUICK: self.handle_prof_info_quick,
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
            session.set_role(UserRole.PROFESSIONAL)
            return self.messages.PROF_NEED_CERTIFICATE
        elif message == '2':
            session.set_role(UserRole.CLIENT)
            return self.messages.CLIENT_MAIN_MENU
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
            # Cargar horario ocupado
            session.clear_temp()
            session.transition_to(ConversationState.PROF_BUSY_SLOT_DATE)
            return self.messages.PROF_BUSY_SLOT_ASK_DATE

        elif message == '3':
            # Cargar semana completa
            session.clear_temp()
            session.store_temp('week_schedule', {})
            session.transition_to(ConversationState.PROF_WEEK_SCHEDULE_DAY)
            return self.messages.PROF_WEEK_ASK_DAY

        elif message == '4':
            # Ver agenda (TODO: implement)
            return "📅 Ver agenda - Próximamente\n\n" + self.messages.PROF_MAIN_MENU

        elif message == '5':
            # Cargar información
            session.clear_temp()
            # Initialize info dict if not exists
            if not session.get_temp('prof_info'):
                session.store_temp('prof_info', {})
            session.transition_to(ConversationState.PROF_INFO_MENU)
            return self.format_prof_info_menu(session)

        elif message == '6':
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
            if 'zona' in prof_info:
                info_lines.append(f"📍 Zona {prof_info['zona'].capitalize()}")
            if 'genero' in prof_info:
                genero_map = {'m': 'Masculino', 'f': 'Femenino', 'o': 'Otro'}
                info_lines.append(
                    f"👥 {genero_map.get(prof_info['genero'], prof_info['genero'])}")
            if 'prepaga' in prof_info:
                info_lines.append(
                    f"💳 Prepaga: {'Sí' if prof_info['prepaga'] else 'No'}")
            if 'especialidad' in prof_info:
                info_lines.append(f"🏥 {prof_info['especialidad']}")

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

        elif message == '9':
            # Guardar información
            prof_info = session.get_temp('prof_info', {})

            # Validate required fields
            required = ['name', 'especialidad', 'zona']
            missing = [f for f in required if f not in prof_info]

            if missing:
                return self.messages.PROF_INFO_INCOMPLETE + "\n\n" + self.format_prof_info_menu(session)

            # TODO: Save to database
            print(
                f"[DB] TODO: Save professional info - {session.phone_number}, {prof_info}")

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
            if 'prepaga' in prof_info:
                summary_lines.append(
                    f"💳 Prepaga: {'Sí' if prof_info['prepaga'] else 'No'}")

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

        Format 2 (without labels, order matters):
            Juan Pérez
            juan@email.com
            norte
            masculino
            si
            dentista

        Returns:
            dict with parsed info or None if invalid
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
                elif key in ['especialidad', 'specialty', 'profesion', 'profesión']:
                    result['especialidad'] = value
        else:
            # Parse order-based format
            if len(lines) != 6:
                return None, [f"❌ Esperaba 6 líneas, recibí {len(lines)}"]

            result = {
                'name': lines[0],
                'email': lines[1],
                'zona': lines[2].lower(),
                'genero': lines[3].lower(),
                'prepaga': lines[4].lower(),
                'especialidad': lines[5]
            }

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

        # TODO: Save to database
        print(
            f"[DB] TODO: Save professional info (quick) - {session.phone_number}, {prof_info}")

        # Format summary
        genero_map = {'m': 'Masculino', 'f': 'Femenino', 'o': 'Otro'}
        summary = f"""👤 Nombre: {prof_info['name']}
    📧 Email: {prof_info['email']}
    📍 Zona: {prof_info['zona'].capitalize()}
    👥 Género: {genero_map[prof_info['genero']]}
    💳 Prepaga: {'Sí' if prof_info['prepaga'] else 'No'}
    🏥 Especialidad: {prof_info['especialidad']}"""

        session.clear_temp()
        session.transition_to(ConversationState.PROF_MAIN_MENU)

        return f"✅ ¡Información guardada!\n\n{summary}\n\n" + self.messages.PROF_MAIN_MENU
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

        # Store date and ask for time
        session.store_temp('date', date_obj)
        session.store_temp('date_str', message)
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
            # Confirmed - save to database (TODO: implement database save)
            date_str = session.get_temp('date_str')
            time_start = session.get_temp('time_start')
            time_end = session.get_temp('time_end')

            # TODO: Save to database
            # db.add_free_slot(session.phone_number, date, time_start, time_end)
            print(
                f"[DB] TODO: Save free slot - {session.phone_number}, {date_str}, {time_start}-{time_end}")

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
                date=session.get_temp('date_str'),
                time_start=session.get_temp('time_start'),
                time_end=session.get_temp('time_end')
            )

    # ==========================================
    # PROFESSIONAL - CARGAR HORARIO OCUPADO (BUSY SLOT)
    # ==========================================

    def handle_prof_busy_slot_date(self, session: SessionData, message: str) -> str:
        """Handle date input for blocking a slot."""
        # Check for back command
        if message == '0':
            session.clear_temp()
            session.transition_to(ConversationState.PROF_MAIN_MENU)
            return self.messages.PROF_MAIN_MENU

        date_obj = parse_date(message)

        if not date_obj:
            return self.messages.INVALID_DATE + "\n\n" + self.messages.PROF_BUSY_SLOT_ASK_DATE

        session.store_temp('date', date_obj)
        session.store_temp('date_str', message)
        session.transition_to(ConversationState.PROF_BUSY_SLOT_TIME)
        return self.messages.PROF_BUSY_SLOT_ASK_TIME

    def handle_prof_busy_slot_time(self, session: SessionData, message: str) -> str:
        """Handle time input for blocking a slot."""
        # Check for back command
        if message == '0':
            session.clear_temp()
            session.transition_to(ConversationState.PROF_MAIN_MENU)
            return self.messages.PROF_MAIN_MENU

        time_range = parse_time_range(message)

        if not time_range:
            return self.messages.INVALID_TIME + "\n\n" + self.messages.PROF_BUSY_SLOT_ASK_TIME

        start_time, end_time = time_range
        session.store_temp('time_start', start_time)
        session.store_temp('time_end', end_time)
        session.transition_to(ConversationState.PROF_BUSY_SLOT_CONFIRM)

        return self.messages.PROF_BUSY_SLOT_CONFIRM.format(
            date=session.get_temp('date_str'),
            time_start=start_time,
            time_end=end_time
        )

    def handle_prof_busy_slot_confirm(self, session: SessionData, message: str) -> str:
        """Handle confirmation for blocking a slot."""
        if message == '1':
            # Confirmed - save to database
            date_str = session.get_temp('date_str')
            time_start = session.get_temp('time_start')
            time_end = session.get_temp('time_end')

            # TODO: Save to database
            # db.add_busy_slot(session.phone_number, date, time_start, time_end)
            print(
                f"[DB] TODO: Save busy slot - {session.phone_number}, {date_str}, {time_start}-{time_end}")

            session.clear_temp()
            session.transition_to(ConversationState.PROF_MAIN_MENU)

            return self.messages.PROF_BUSY_SLOT_SUCCESS.format(
                date=date_str,
                time_start=time_start,
                time_end=time_end
            ) + "\n\n" + self.messages.PROF_MAIN_MENU

        elif message == '2' or message == '0':
            session.clear_temp()
            session.transition_to(ConversationState.PROF_MAIN_MENU)
            return self.messages.OPERATION_CANCELLED + "\n\n" + self.messages.PROF_MAIN_MENU

        else:
            return self.messages.INVALID_OPTION

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

            # TODO: Save to database
            # for day, data in week_schedule.items():
            #     db.add_weekly_schedule(session.phone_number, day, data['start'], data['end'])
            print(
                f"[DB] TODO: Save weekly schedule - {session.phone_number}, {len(week_schedule)} days")

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

            # Format message with today's date
            return self.messages.CLIENT_SEARCH_TODAY_CONFIRM.format(
                today_date=today.strftime("%d/%m/%Y")
            )

        elif message == '2':
            # Búsqueda con multi-filtro
            session.clear_temp()
            session.store_temp('filters', {})
            session.transition_to(ConversationState.CLIENT_MULTIFILTER_MENU)
            return self.format_multifilter_menu(session)

        elif message == '3':
            # Zona Norte directo
            session.clear_temp()
            session.store_temp('zona', 'norte')

            # TODO: Search database
            print(f"[DB] TODO: Search Zona Norte")

            session.transition_to(ConversationState.CLIENT_SHOW_RESULTS)
            return "🔍 Buscando profesionales en Zona Norte...\n\n📋 Próximamente mostraré resultados.\n\nEscribe 'menu' para volver."

        elif message == '4':
            # Zona Sur directo
            session.clear_temp()
            session.store_temp('zona', 'sur')

            # TODO: Search database
            print(f"[DB] TODO: Search Zona Sur")

            session.transition_to(ConversationState.CLIENT_SHOW_RESULTS)
            return "🔍 Buscando profesionales en Zona Sur...\n\n📋 Próximamente mostraré resultados.\n\nEscribe 'menu' para volver."

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
            session.store_temp('zona', 'norte')
        elif message == '2':
            session.store_temp('zona', 'sur')
        else:
            return self.messages.INVALID_OPTION + "\n\n" + self.messages.CLIENT_ASK_ZONA

        # TODO: Search database and show results
        # results = db.search_by_zona(session.get_temp('zona'))
        print(f"[DB] TODO: Search by zona - {session.get_temp('zona')}")

        session.transition_to(ConversationState.CLIENT_SHOW_RESULTS)
        return "🔍 Buscando profesionales en Zona " + session.get_temp('zona').capitalize() + "...\n\n📋 Próximamente mostraré resultados.\n\nEscribe 'menu' para volver."

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
        """Handle hora filter - ask for time."""
        # Check for back command
        if message == '0':
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return self.messages.CLIENT_MAIN_MENU

        # Simple time validation (HH:MM)
        if ':' not in message or len(message) != 5:
            return self.messages.INVALID_INPUT + "\n\n" + self.messages.CLIENT_ASK_HORA

        session.store_temp('hora', message)

        # TODO: Search database
        # results = db.search_by_availability(fecha, hora)
        print(
            f"[DB] TODO: Search by availability - {session.get_temp('fecha_str')} {message}")

        session.transition_to(ConversationState.CLIENT_SHOW_RESULTS)
        return f"🔍 Buscando disponibles el {session.get_temp('fecha_str')} a las {message}...\n\n📋 Próximamente mostraré resultados.\n\nEscribe 'menu' para volver."

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
        """Handle showing search results."""
        # TODO: Implement result navigation
        session.transition_to(ConversationState.CLIENT_MAIN_MENU)
        return "📋 Resultados - En desarrollo\n\n" + self.messages.CLIENT_MAIN_MENU

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
