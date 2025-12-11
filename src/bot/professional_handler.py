"""
Professional Handler
===================
Maneja todo el flujo de conversación del profesional.

Responsabilidades:
- Gate de certificado (upload obligatorio)
- Menú principal del profesional
- Gestión de información personal (perfil)
- Carga de horarios (slot individual, semana completa)
- Gestión de slots libres
- Carga rápida de información

Este archivo contiene ~1000 líneas de lógica específica del profesional.
"""

from datetime import datetime, timedelta
from src.core.states import ConversationState, SessionData
from src.messages.messages_common import common_messages
from src.messages.messages_professional import professional_messages
from src.messages.messages_appointments import appointment_messages
from src.core.validators import parse_time_range, validate_date, validate_time, parse_date
from src.services.professional_service import professional_service
from src.config.domain_config import DomainConfig


class ProfessionalHandler:
    """
    Handler para gestión del flujo del profesional.

    El profesional puede:
    1. Subir certificado (obligatorio)
    2. Cargar información personal
    3. Gestionar horarios disponibles
    4. Ver agenda y estadísticas
    """

    def __init__(self):
        """
        Inicializar handler del profesional.

        Los mensajes se importan directamente desde los módulos:
        - common_messages: Validaciones, errores, ayuda
        - professional_messages: Certificado, horarios, perfil
        - appointment_messages: Sistema de citas
        """
        pass

    # ==========================================
    # CERTIFICADO Y MENÚ PRINCIPAL
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
        return professional_messages.PROF_NEED_CERTIFICATE

    def handle_prof_certificate_uploaded(self, session: SessionData) -> str:
        """
        Called from whatsapp_handler when certificate is uploaded.
        Transitions to main menu.
        """
        session.transition_to(ConversationState.PROF_MAIN_MENU)
        return professional_messages.PROF_CERTIFICATE_RECEIVED + "\n\n" + professional_messages.PROF_MAIN_MENU

    def handle_prof_main_menu(self, session: SessionData, message: str) -> str:
        """Handle professional main menu."""
        if message == '1':
            # Liberar horario
            session.clear_temp()
            session.transition_to(ConversationState.PROF_FREE_SLOT_DATE)
            return professional_messages.PROF_FREE_SLOT_ASK_DATE

        elif message == '2':
            # Cargar semana completa
            session.clear_temp()
            session.store_temp('week_schedule', {})
            session.transition_to(ConversationState.PROF_WEEK_SCHEDULE_QUICK)
            return professional_messages.PROF_WEEK_QUICK_FORMAT

        elif message == '3':
            schedule_info = professional_service.get_complete_schedule(
                session.phone_number)
            return schedule_info['formatted'] + "\n\n" + professional_messages.PROF_MAIN_MENU

        elif message == '4':
            # Cargar informaciÃ³n
            session.clear_temp()
            # Initialize info dict if not exists
            if not session.get_temp('prof_info'):
                session.store_temp('prof_info', {})
            session.transition_to(ConversationState.PROF_INFO_MENU)
            return self.format_prof_info_menu(session)

        elif message == '5':
            # Carga rÃ¡pida
            session.clear_temp()
            session.transition_to(ConversationState.PROF_INFO_QUICK)
            return professional_messages.PROF_INFO_QUICK_FORMAT

        elif message == '6':
            # Mis Citas
            session.transition_to(ConversationState.PROF_VIEW_APPOINTMENTS)
            return self.handle_prof_view_appointments(session, message)

        elif message == '0':
            session.reset()
            return common_messages.WELCOME

        else:
            return common_messages.INVALID_OPTION + "\n\n" + professional_messages.PROF_MAIN_MENU

    def format_prof_info_menu(self, session: SessionData) -> str:
        """Format professional info menu with current data."""
        prof_info = session.get_temp('prof_info', {})

        if not prof_info:
            current_info = "(ninguno)"
        else:
            info_lines = []
            if 'name' in prof_info:
                info_lines.append(f"ðŸ‘¤ {prof_info['name']}")
            if 'email' in prof_info:
                info_lines.append(f"ðŸ“§ {prof_info['email']}")
            if 'zone' in prof_info:  # â† CAMBIAR: era 'zona'
                info_lines.append(
                    f"ðŸ“ Zona {prof_info['zone'].capitalize()}")
            if 'gender' in prof_info:  # â† CAMBIAR: era 'genero'
                genero_map = {'m': 'Masculino', 'f': 'Femenino', 'o': 'Otro'}
                info_lines.append(
                    f"ðŸ‘¥ {genero_map.get(prof_info['gender'], prof_info['gender'])}")
            if 'accept_prepaga' in prof_info:  # â† CAMBIAR: era 'prepaga'
                info_lines.append(
                    f"ðŸ’³ Prepaga: {'SÃ­' if prof_info['accept_prepaga'] else 'No'}")
            if 'especialidad' in prof_info:
                info_lines.append(f"ðŸ¥ {prof_info['especialidad']}")
            if 'bio' in prof_info:  # â† AGREGAR
                bio_preview = prof_info['bio'][:40] + \
                    "..." if len(prof_info['bio']) > 40 else prof_info['bio']
                info_lines.append(f"ðŸ“ {bio_preview}")
            if 'fee_range' in prof_info:  # â† AGREGAR
                info_lines.append(f"ðŸ’° ${prof_info['fee_range']}")

            current_info = "\n".join(info_lines) if info_lines else "(ninguno)"

        return professional_messages.PROF_INFO_MENU.format(current_info=current_info)

    def handle_prof_info_menu(self, session: SessionData, message: str) -> str:
        """Handle professional info menu."""

        if message == '1':
            # Nombre
            session.transition_to(ConversationState.PROF_INFO_NAME)
            return professional_messages.PROF_INFO_ASK_NAME

        elif message == '2':
            # Email
            session.transition_to(ConversationState.PROF_INFO_EMAIL)
            return professional_messages.PROF_INFO_ASK_EMAIL

        elif message == '3':
            # Zona
            session.transition_to(ConversationState.PROF_INFO_ZONA)
            return professional_messages.PROF_INFO_ASK_ZONA

        elif message == '4':
            # GÃ©nero
            session.transition_to(ConversationState.PROF_INFO_GENERO)
            return professional_messages.PROF_INFO_ASK_GENERO

        elif message == '5':
            # Prepaga
            session.transition_to(ConversationState.PROF_INFO_PREPAGA)
            return professional_messages.PROF_INFO_ASK_PREPAGA

        elif message == '6':
            # Especialidad
            session.transition_to(ConversationState.PROF_INFO_ESPECIALIDAD)
            return professional_messages.PROF_INFO_ASK_ESPECIALIDAD

        elif message == '7':
            # Bio
            session.transition_to(ConversationState.PROF_INFO_BIO)
            return professional_messages.PROF_INFO_ASK_BIO

        elif message == '8':
            # Honorarios
            session.transition_to(ConversationState.PROF_INFO_FEE_RANGE)
            return professional_messages.PROF_INFO_ASK_FEE_RANGE

        elif message == '9':
            # Guardar informaciÃ³n
            prof_info = session.get_temp('prof_info', {})

            # Type check
            if not isinstance(prof_info, dict):
                prof_info = {}

            # Validate required fields
            required = ['name', 'especialidad', 'zona']
            missing = [f for f in required if f not in prof_info]

            if missing:
                return professional_messages.PROF_INFO_INCOMPLETE + "\n\n" + self.format_prof_info_menu(session)

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
            summary_lines.append(
                f"ðŸ‘¤ Nombre: {prof_info.get('name', 'N/A')}")
            summary_lines.append(
                f"ðŸ¥ Especialidad: {prof_info.get('especialidad', 'N/A')}")
            summary_lines.append(
                f"ðŸ“ Zona: {prof_info.get('zona', 'N/A').capitalize()}")

            if 'email' in prof_info:
                summary_lines.append(f"ðŸ“§ Email: {prof_info['email']}")
            if 'genero' in prof_info:
                genero_map = {'m': 'Masculino', 'f': 'Femenino', 'o': 'Otro'}
                summary_lines.append(
                    f"ðŸ‘¥ GÃ©nero: {genero_map.get(prof_info['genero'], prof_info['genero'])}")
            if 'bio' in prof_info:
                bio_preview = prof_info['bio'][:50] + \
                    "..." if len(prof_info['bio']) > 50 else prof_info['bio']
                summary_lines.append(f"ðŸ“ Bio: {bio_preview}")
            if 'fee_range' in prof_info:
                summary_lines.append(
                    f"ðŸ’° Honorarios: ${prof_info['fee_range']}")

            profile_summary = "\n".join(summary_lines)

            session.clear_temp()
            session.transition_to(ConversationState.PROF_MAIN_MENU)

            return professional_messages.PROF_INFO_SAVED.format(
                profile_summary=profile_summary
            ) + "\n\n" + professional_messages.PROF_MAIN_MENU

        elif message == '0':
            # Volver al menÃº
            session.clear_temp()
            session.transition_to(ConversationState.PROF_MAIN_MENU)
            return professional_messages.PROF_MAIN_MENU

        else:
            return common_messages.INVALID_OPTION + "\n\n" + self.format_prof_info_menu(session)

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
        return f"âœ… Nombre guardado: {message}\n\n" + self.format_prof_info_menu(session)

    def handle_prof_info_email(self, session: SessionData, message: str) -> str:
        """Handle email input."""
        if message == '0':
            session.transition_to(ConversationState.PROF_INFO_MENU)
            return self.format_prof_info_menu(session)

        # Validate email format
        from src.core.validators import validate_email
        if not validate_email(message):
            return "âŒ Email invÃ¡lido. Intenta nuevamente:\nEjemplo: juan@email.com"

        # Store email
        prof_info = session.get_temp('prof_info', {})
        prof_info['email'] = message
        session.store_temp('prof_info', prof_info)

        session.transition_to(ConversationState.PROF_INFO_MENU)
        return f"âœ… Email guardado: {message}\n\n" + self.format_prof_info_menu(session)

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
            return common_messages.INVALID_OPTION + "\n\n" + professional_messages.PROF_INFO_ASK_ZONA

        # Store zona
        prof_info = session.get_temp('prof_info', {})
        prof_info['zona'] = zona
        session.store_temp('prof_info', prof_info)

        session.transition_to(ConversationState.PROF_INFO_MENU)
        return f"âœ… Zona guardada: {zona.capitalize()}\n\n" + self.format_prof_info_menu(session)

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
            return common_messages.INVALID_OPTION + "\n\n" + professional_messages.PROF_INFO_ASK_GENERO

        # Store genero
        prof_info = session.get_temp('prof_info', {})
        prof_info['genero'] = genero
        session.store_temp('prof_info', prof_info)

        genero_map = {'m': 'Masculino', 'f': 'Femenino', 'o': 'Otro'}
        session.transition_to(ConversationState.PROF_INFO_MENU)
        return f"âœ… GÃ©nero guardado: {genero_map[genero]}\n\n" + self.format_prof_info_menu(session)

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
            return common_messages.INVALID_OPTION + "\n\n" + professional_messages.PROF_INFO_ASK_PREPAGA

        # Store prepaga
        prof_info = session.get_temp('prof_info', {})
        prof_info['prepaga'] = prepaga
        session.store_temp('prof_info', prof_info)

        session.transition_to(ConversationState.PROF_INFO_MENU)
        return f"âœ… Prepaga: {'SÃ­' if prepaga else 'No'}\n\n" + self.format_prof_info_menu(session)

    def handle_prof_view_appointments(self, session: SessionData, message: str) -> str:
        """Ver lista de citas del profesional."""
        from src.database.database import db

        # Obtener citas del profesional
        appointments = db.get_appointments_by_professional(
            professional_phone=session.phone_number,
            status=None,  # Todas
            from_date=None  # Desde hoy
        )

        if not appointments or len(appointments) == 0:
            return appointment_messages.PROF_NO_APPOINTMENTS + "\n\n" + professional_messages.PROF_MAIN_MENU

        # Usar el mensaje que SÍ existe
        response = appointment_messages.PROF_VIEW_APPOINTMENTS

        # Agregar lista de citas
        for idx, apt in enumerate(appointments[:10], 1):
            status_emoji = appointment_messages.format_status_emoji(
                apt['status'])
            response += f"\n{idx}️⃣ {status_emoji} {apt['appointment_date']} - {apt['start_time']}"
            response += f"\n   Paciente: {apt.get('client_phone', 'N/A')}"

        # Footer simple
        response += "\n\n_Escribe el número para ver detalle_"
        response += "\n_0️⃣ Volver al menú_"
        response += "\n\n" + professional_messages.PROF_MAIN_MENU

        return response

    def handle_prof_info_especialidad(self, session: SessionData, message: str) -> str:
        """Handle especialidad input."""
        if message == '0':
            session.transition_to(ConversationState.PROF_INFO_MENU)
            return self.format_prof_info_menu(session)

        # Map number to specialty or use custom text
        especialidades = {
            '1': 'MÃ©dico General',
            '2': 'Dentista',
            '3': 'PsicÃ³logo',
            '4': 'KinesiÃ³logo',
            '5': 'Nutricionista',
            '6': 'Otro'
        }

        if message in especialidades:
            if message == '6':
                # Ask for custom specialty
                return "ðŸ¥ Escribe tu especialidad:"
            especialidad = especialidades[message]
        else:
            # Custom specialty text
            especialidad = message

        # Store especialidad
        prof_info = session.get_temp('prof_info', {})
        prof_info['especialidad'] = especialidad
        session.store_temp('prof_info', prof_info)

        session.transition_to(ConversationState.PROF_INFO_MENU)
        return f"âœ… Especialidad guardada: {especialidad}\n\n" + self.format_prof_info_menu(session)

    def handle_prof_info_bio(self, session: SessionData, message: str) -> str:
        """Handle bio input."""
        if message == '0':
            session.transition_to(ConversationState.PROF_INFO_MENU)
            return self.format_prof_info_menu(session)

        # Guardar bio en temp
        session.store_temp('bio', message)

        # Volver al menÃº
        session.transition_to(ConversationState.PROF_INFO_MENU)
        return f"âœ… DescripciÃ³n guardada.\n\n{self.format_prof_info_menu(session)}"

    def handle_prof_info_fee_range(self, session: SessionData, message: str) -> str:
        """Handle fee range input."""
        if message == '0':
            session.transition_to(ConversationState.PROF_INFO_MENU)
            return self.format_prof_info_menu(session)

        # Validar formato: XXX-YYY
        import re
        match = re.match(r'^(\d+)-(\d+)$', message.strip())

        if not match:
            return "âŒ Formato incorrecto.\n\nUsa: MÃNIMO-MÃXIMO\nEjemplo: 100-150\n\nðŸ’¡ Escribe '0' para volver"

        min_fee, max_fee = match.groups()

        if int(min_fee) >= int(max_fee):
            return "âŒ El mÃ­nimo debe ser menor que el mÃ¡ximo.\n\nðŸ’¡ Escribe '0' para volver"

        # Guardar en temp
        session.store_temp('fee_range', message)

        # Volver al menÃº
        session.transition_to(ConversationState.PROF_INFO_MENU)
        return f"âœ… Honorarios guardados: ${min_fee} - ${max_fee}\n\n{self.format_prof_info_menu(session)}"

    def parse_prof_info_quick(self, message: str) -> dict:
        """
        Parse professional info from message.
        Supports two formats:

        Format 1 (with labels):
            nombre: Juan PÃ©rez
            email: juan@email.com
            zona: norte
            genero: masculino
            prepaga: si
            especialidad: dentista
            bio: DescripciÃ³n (opcional)
            honorarios: 100-150 (opcional)

        Format 2 (without labels, order matters):
            Juan PÃ©rez
            juan@email.com
            norte
            masculino
            si
            dentista
            DescripciÃ³n (opcional - lÃ­nea 7)
            100-150 (opcional - lÃ­nea 8)

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
                elif key in ['genero', 'gÃ©nero', 'sexo', 'gender']:
                    result['genero'] = value.lower()
                elif key in ['prepaga', 'obra social', 'os']:
                    result['prepaga'] = value.lower()
                elif key in ['especialidad', 'specialty', 'profesion', 'profesiÃ³n', 'category']:
                    result['especialidad'] = value
                elif key in ['bio', 'descripcion', 'descripciÃ³n', 'about']:  # â† AGREGAR
                    result['bio'] = value
                elif key in ['honorarios', 'fee', 'precio', 'costo']:  # â† AGREGAR
                    result['fee_range'] = value
        else:
            # Parse order-based format
            if len(lines) < 6:
                return None, [f"âŒ Esperaba al menos 6 lÃ­neas, recibÃ­ {len(lines)}"]

            result = {
                'name': lines[0],
                'email': lines[1],
                'zona': lines[2].lower(),
                'genero': lines[3].lower(),
                'prepaga': lines[4].lower(),
                'especialidad': lines[5]
            }

            # Optional fields (lÃ­neas 7 y 8)
            if len(lines) >= 7 and lines[6]:  # â† AGREGAR
                result['bio'] = lines[6]
            if len(lines) >= 8 and lines[7]:  # â† AGREGAR
                result['fee_range'] = lines[7]

        # Validate required fields
        required = ['name', 'email', 'zona',
                    'genero', 'prepaga', 'especialidad']
        missing = [f for f in required if f not in result or not result[f]]

        if missing:
            errors.append(f"âŒ Faltan campos: {', '.join(missing)}")
            return None, errors

        # Validate and normalize each field
        from src.core.validators import validate_email

        # Email
        if not validate_email(result['email']):
            errors.append(f"âŒ Email invÃ¡lido: {result['email']}")

        # Zona
        zona_map = {
            'norte': 'norte', 'n': 'norte', 'north': 'norte',
            'sur': 'sur', 's': 'sur', 'south': 'sur'
        }
        if result['zona'] not in zona_map:
            errors.append(
                f"âŒ Zona invÃ¡lida: {result['zona']} (usa: norte o sur)")
        else:
            result['zona'] = zona_map[result['zona']]

        # GÃ©nero
        genero_map = {
            'm': 'm', 'masculino': 'm', 'male': 'm', 'hombre': 'm',
            'f': 'f', 'femenino': 'f', 'female': 'f', 'mujer': 'f',
            'o': 'o', 'otro': 'o', 'other': 'o', 'nobinario': 'o', 'no binario': 'o'
        }
        if result['genero'] not in genero_map:
            errors.append(
                f"âŒ GÃ©nero invÃ¡lido: {result['genero']} (usa: masculino, femenino, otro)")
        else:
            result['genero'] = genero_map[result['genero']]

        # Prepaga
        prepaga_map = {
            'si': True, 'sÃ­': True, 's': True, 'yes': True, 'y': True,
            'no': False, 'n': False
        }
        if result['prepaga'] not in prepaga_map:
            errors.append(
                f"âŒ Prepaga invÃ¡lida: {result['prepaga']} (usa: si o no)")
        else:
            result['prepaga'] = prepaga_map[result['prepaga']]

        # Validar fee_range si existe (opcional)  # â† AGREGAR
        if 'fee_range' in result:
            match = re.match(r'^(\d+)-(\d+)$', result['fee_range'].strip())
            if not match:
                errors.append(
                    f"âŒ Honorarios invÃ¡lidos: {result['fee_range']} (usa formato: 100-150)")
            else:
                min_fee, max_fee = match.groups()
                if int(min_fee) >= int(max_fee):
                    errors.append(
                        f"âŒ Honorarios: el mÃ­nimo debe ser menor que el mÃ¡ximo")

        if errors:
            return None, errors

        return result, []

    def handle_prof_info_quick(self, session: SessionData, message: str) -> str:
        """Handle quick info input (all in one message)."""

        if message == '0':
            session.transition_to(ConversationState.PROF_MAIN_MENU)
            return professional_messages.PROF_MAIN_MENU

        # Parse the message
        prof_info, errors = self.parse_prof_info_quick(message)

        if errors:
            error_msg = "\n".join(errors)
            return f"{error_msg}\n\n{professional_messages.PROF_INFO_QUICK_FORMAT}"

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
            f"ðŸ‘¤ Nombre: {prof_info['name']}",
            f"ðŸ“§ Email: {prof_info['email']}",
            f"ðŸ“ Zona: {prof_info['zona'].capitalize()}",
            f"ðŸ‘¥ GÃ©nero: {genero_map[prof_info['genero']]}",
            f"ðŸ’³ Prepaga: {'SÃ­' if prof_info['prepaga'] else 'No'}",
            f"ðŸ¥ Especialidad: {prof_info['especialidad']}"
        ]

        # Agregar opcionales si existen
        if 'bio' in prof_info:
            bio_preview = prof_info['bio'][:50] + \
                "..." if len(prof_info['bio']) > 50 else prof_info['bio']
            summary_lines.append(f"ðŸ“ Bio: {bio_preview}")
        if 'fee_range' in prof_info:
            summary_lines.append(f"ðŸ’° Honorarios: ${prof_info['fee_range']}")

        summary = "\n".join(summary_lines)

        session.clear_temp()
        session.transition_to(ConversationState.PROF_MAIN_MENU)

        return f"âœ… Â¡InformaciÃ³n guardada!\n\n{summary}\n\n" + professional_messages.PROF_MAIN_MENU

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
            'miÃ©rcoles': 2, 'miercoles': 2, 'mie': 2, 'miÃ©': 2,
            'jueves': 3, 'jue': 3,
            'viernes': 4, 'vie': 4,
            'sÃ¡bado': 5, 'sabado': 5, 'sab': 5,
            'domingo': 6, 'dom': 6
        }

        for line_num, line in enumerate(lines, 1):
            # Expected format: "dia HH:MM-HH:MM+HH:MM-HH:MM"
            parts = line.lower().split(maxsplit=1)

            if len(parts) != 2:
                errors.append(
                    f"LÃ­nea {line_num}: Formato invÃ¡lido. Debe ser: dia HH:MM-HH:MM")
                continue

            day_name, times_str = parts

            # Validate day
            if day_name not in day_map:
                errors.append(
                    f"LÃ­nea {line_num}: DÃ­a '{day_name}' no reconocido")
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
                        f"LÃ­nea {line_num}: Horario '{time_range}' invÃ¡lido. Debe ser HH:MM-HH:MM")
                    continue

                start_h, start_m, end_h, end_m = match.groups()

                # Validate hours and minutes
                if not (0 <= int(start_h) <= 23 and 0 <= int(start_m) <= 59):
                    errors.append(
                        f"LÃ­nea {line_num}: Hora de inicio invÃ¡lida: {start_h}:{start_m}")
                    continue

                if not (0 <= int(end_h) <= 23 and 0 <= int(end_m) <= 59):
                    errors.append(
                        f"LÃ­nea {line_num}: Hora de fin invÃ¡lida: {end_h}:{end_m}")
                    continue

                start_time = f"{start_h}:{start_m}"
                end_time = f"{end_h}:{end_m}"

                # Validate end > start
                if end_time <= start_time:
                    errors.append(
                        f"LÃ­nea {line_num}: La hora de fin debe ser mayor que la de inicio")
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
            return professional_messages.PROF_MAIN_MENU

        # Parse the message
        schedules, errors = self.parse_week_schedule_quick(message)

        if errors:
            error_msg = "âŒ Errores encontrados:\n\n"
            error_msg += "\n".join(errors)
            error_msg += "\n\n" + professional_messages.PROF_WEEK_QUICK_FORMAT
            return error_msg

        if not schedules:
            return "âŒ No se encontraron horarios vÃ¡lidos.\n\n" + professional_messages.PROF_WEEK_QUICK_FORMAT

        # Save to database
        from src.services.professional_service import professional_service

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
        day_names = ['Lunes', 'Martes', 'MiÃ©rcoles',
                     'Jueves', 'Viernes', 'SÃ¡bado', 'Domingo']

        # Group by day
        by_day = {}
        for s in schedules:
            day = s['day']
            if day not in by_day:
                by_day[day] = []
            by_day[day].append(f"{s['start']}-{s['end']}")

        for day in sorted(by_day.keys()):
            times = ', '.join(by_day[day])
            summary_lines.append(f"â€¢ {day_names[day]}: {times}")

        schedule_summary = "\n".join(summary_lines)

        session.clear_temp()
        session.transition_to(ConversationState.PROF_MAIN_MENU)

        return f"""âœ… Â¡Semana configurada exitosamente!

    Guardados {success_count}/{total} horarios:

    {schedule_summary}

    Estos horarios se repetirÃ¡n cada semana.

    """ + professional_messages.PROF_MAIN_MENU

    # ==========================================
    # PROFESSIONAL - LIBERAR HORARIO (FREE SLOT)
    # ==========================================

    def handle_prof_free_slot_date(self, session: SessionData, message: str) -> str:
        """Handle date input for freeing a slot."""
        # Check for back command
        if message == '0':
            session.clear_temp()
            session.transition_to(ConversationState.PROF_MAIN_MENU)
            return professional_messages.PROF_MAIN_MENU

        date_obj = parse_date(message)

        if not date_obj:
            return common_messages.INVALID_DATE + "\n\n" + professional_messages.PROF_FREE_SLOT_ASK_DATE

        # Store date in YYYY-MM-DD format for database
        date_str_db = date_obj.strftime("%Y-%m-%d")

        session.store_temp('date', date_obj)
        # Guardar en formato correcto
        session.store_temp('date_str', date_str_db)
        # Guardar formato original para mostrar
        session.store_temp('date_display', message)
        session.transition_to(ConversationState.PROF_FREE_SLOT_TIME)

        return professional_messages.PROF_FREE_SLOT_ASK_TIME

    def handle_prof_free_slot_time(self, session: SessionData, message: str) -> str:
        """Handle time input for freeing a slot."""
        # Check for back command
        if message == '0':
            session.clear_temp()
            session.transition_to(ConversationState.PROF_MAIN_MENU)
            return professional_messages.PROF_MAIN_MENU

        time_range = parse_time_range(message)

        if not time_range:
            return common_messages.INVALID_TIME + "\n\n" + professional_messages.PROF_FREE_SLOT_ASK_TIME

        start_time, end_time = time_range

        # Store time and ask for confirmation
        session.store_temp('time_start', start_time)
        session.store_temp('time_end', end_time)
        session.transition_to(ConversationState.PROF_FREE_SLOT_CONFIRM)

        return professional_messages.PROF_FREE_SLOT_CONFIRM.format(
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

            return professional_messages.PROF_FREE_SLOT_SUCCESS.format(
                date=date_str,
                time_start=time_start,
                time_end=time_end
            ) + "\n\n" + professional_messages.PROF_MAIN_MENU

        elif message == '2' or message == '0':
            # Cancelled
            session.clear_temp()
            session.transition_to(ConversationState.PROF_MAIN_MENU)
            return common_messages.OPERATION_CANCELLED + "\n\n" + professional_messages.PROF_MAIN_MENU

        else:
            return common_messages.INVALID_OPTION + "\n\n" + professional_messages.PROF_FREE_SLOT_CONFIRM.format(
                date=session.get_temp('date_str', ''),
                time_start=session.get_temp('time_start', ''),
                time_end=session.get_temp('time_end', '')
            )
    # ==========================================
    # PROFESSIONAL - CARGAR HORARIO OCUPADO (BUSY SLOT)
    # ==========================================

    def handle_prof_manage_free_slots(self, session: SessionData, message: str) -> str:
        """Show menu to manage free slots."""
        from src.services.professional_service import professional_service

        if message == '1':
            # Add new free slot
            session.transition_to(ConversationState.PROF_FREE_SLOT_DATE)
            return professional_messages.PROF_FREE_SLOT_ASK_DATE

        elif message == '2':
            # Delete free slot
            free_slots = professional_service.get_free_slots(
                session.phone_number, future_only=True)

            if not free_slots:
                return "âŒ No tienes horarios libres activos.\n\n" + professional_messages.PROF_MAIN_MENU

            # Show slots with numbers
            msg = "ðŸ“… ELIMINAR HORARIO LIBRE\n\n"
            msg += "Horarios libres activos:\n\n"
            for idx, slot in enumerate(free_slots, 1):
                msg += f"{idx}ï¸âƒ£ {slot['date']} {slot['start_time']}-{slot['end_time']}\n"
            msg += "\n0ï¸âƒ£ Cancelar\n\n"
            msg += "Selecciona el nÃºmero del horario a eliminar:"

            session.store_temp('free_slots_list', free_slots)
            session.transition_to(ConversationState.PROF_DELETE_FREE_SLOT)
            return msg

        elif message == '0':
            session.transition_to(ConversationState.PROF_MAIN_MENU)
            return professional_messages.PROF_MAIN_MENU

        else:
            return common_messages.INVALID_OPTION

    def handle_prof_delete_free_slot(self, session: SessionData, message: str) -> str:
        """Handle deleting a free slot."""

        if message == '0':
            session.clear_temp()
            session.transition_to(ConversationState.PROF_MAIN_MENU)
            return professional_messages.PROF_MAIN_MENU

        try:
            selection = int(message)
            free_slots = session.get_temp('free_slots_list', [])

            if 1 <= selection <= len(free_slots):
                slot = free_slots[selection - 1]

                from src.services.professional_service import professional_service
                success = professional_service.remove_free_slot(
                    session.phone_number,
                    slot['date'],
                    slot['start_time'],
                    slot['end_time']
                )

                if success:
                    msg = f"âœ… Horario eliminado:\nðŸ“… {slot['date']} {slot['start_time']}-{slot['end_time']}\n\n"
                    msg += "Este horario ya no estÃ¡ disponible para clientes."
                else:
                    msg = "âŒ Error al eliminar horario."

                session.clear_temp()
                session.transition_to(ConversationState.PROF_MAIN_MENU)
                return msg + "\n\n" + professional_messages.PROF_MAIN_MENU
            else:
                return f"âŒ OpciÃ³n invÃ¡lida. Selecciona un nÃºmero entre 1 y {len(free_slots)}."

        except ValueError:
            return "âŒ Por favor, ingresa el nÃºmero del horario a eliminar."
    # ==========================================
    # PROFESSIONAL - CARGAR SEMANA (WEEKLY SCHEDULE)
    # ==========================================

    def handle_prof_week_day(self, session: SessionData, message: str) -> str:
        """Handle day selection for weekly schedule."""
        # Check for back command
        if message == '0':
            session.clear_temp()
            session.transition_to(ConversationState.PROF_MAIN_MENU)
            return professional_messages.PROF_MAIN_MENU

        if message not in ['1', '2', '3', '4', '5', '6', '7']:
            return common_messages.INVALID_OPTION + "\n\n" + professional_messages.PROF_WEEK_ASK_DAY

        day_number = int(message)
        day_name = common_messages.format_day_name(day_number)

        session.store_temp('current_day', day_number)
        session.store_temp('current_day_name', day_name)
        session.transition_to(ConversationState.PROF_WEEK_SCHEDULE_TIME)

        return professional_messages.PROF_WEEK_ASK_TIME.format(day=day_name)

    def handle_prof_week_time(self, session: SessionData, message: str) -> str:
        """Handle time input for weekly schedule."""
        # Check for back command
        if message == '0':
            session.clear_temp()
            session.transition_to(ConversationState.PROF_MAIN_MENU)
            return professional_messages.PROF_MAIN_MENU

        time_range = parse_time_range(message)

        if not time_range:
            day_name = session.get_temp('current_day_name')
            return common_messages.INVALID_TIME + "\n\n" + professional_messages.PROF_WEEK_ASK_TIME.format(day=day_name)

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
            f"â€¢ {data['day_name']}: {data['start']} - {data['end']}"
            for day, data in sorted(week_schedule.items())
        ])

        session.transition_to(ConversationState.PROF_WEEK_SCHEDULE_MORE)

        return professional_messages.PROF_WEEK_ASK_MORE.format(
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
            return professional_messages.PROF_WEEK_ASK_DAY

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
                f"â€¢ {data['day_name']}: {data['start']} - {data['end']}"
                for day, data in sorted(week_schedule.items())
            ])

            session.clear_temp()
            session.transition_to(ConversationState.PROF_MAIN_MENU)

            return professional_messages.PROF_WEEK_SUCCESS.format(
                schedule_summary=schedule_summary
            ) + "\n\n" + professional_messages.PROF_MAIN_MENU

        elif message == '0':
            # Cancel and go back to menu
            session.clear_temp()
            session.transition_to(ConversationState.PROF_MAIN_MENU)
            return common_messages.OPERATION_CANCELLED + "\n\n" + professional_messages.PROF_MAIN_MENU

        else:
            return common_messages.INVALID_OPTION
