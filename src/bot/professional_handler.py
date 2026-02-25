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
from src.core.states import ConversationState, SessionData, UserRole
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
    # def handle_prof_need_certificate(self, session: SessionData, message: str) -> str:
    #     """
    #     Handle certificate requirement state.
    #     Professional MUST upload certificate before accessing any menu.
    #     Block all text inputs until file is uploaded.
    #     Note: File upload is handled separately in whatsapp_handler.py
    #     """
    #     # Block '0' and any other text input
    #     # User must upload certificate file to continue
    #     return professional_messages.PROF_NEED_CERTIFICATE

    # def handle_prof_certificate_uploaded(self, session: SessionData) -> str:
    #     """
    #     Called from whatsapp_handler when certificate is uploaded.
    #     Transitions to main menu.
    #     """
    #     session.transition_to(ConversationState.PROF_MAIN_MENU)
    #     return professional_messages.PROF_CERTIFICATE_RECEIVED + "\n\n" + professional_messages.PROF_MAIN_MENU

    # ==========================================
    # VERIFICACIÓN DE CLAVE DE ACCESO
    # ==========================================

    def handle_prof_need_access_key(self, session: SessionData, message: str) -> str:
        """
        Handler para validación de clave de acceso.
        El profesional DEBE ingresar una clave válida antes de acceder al sistema.
        """
        if message == '0':
            session.reset()
            session.transition_to(ConversationState.ROLE_SELECTION)
            return common_messages.WELCOME

        # Validar clave de acceso
        is_valid, key_info = self._validate_access_key(message)

        if is_valid:
            # Clave válida - activar profesional
            return self._activate_professional_access(session, message, key_info.get('is_master', False))
        else:
            # Clave inválida
            error_type = key_info.get('error', 'invalid')

            if error_type == 'key_already_used':
                return professional_messages.PROF_KEY_ALREADY_USED + "\n\n" + professional_messages.PROF_NEED_ACCESS_KEY
            elif error_type == 'key_expired':
                return professional_messages.PROF_KEY_EXPIRED + "\n\n" + professional_messages.PROF_NEED_ACCESS_KEY
            else:
                return professional_messages.PROF_KEY_INVALID + "\n\n" + professional_messages.PROF_NEED_ACCESS_KEY

    def _validate_access_key(self, key: str) -> tuple:
        """
        Valida una clave de acceso.

        Args:
            key: Clave ingresada por el usuario

        Returns:
            (is_valid: bool, key_info: dict)
        """
        from src.config.config import Config

        # Verificar master key
        if hasattr(Config, 'MASTER_ACCESS_KEY') and key == Config.MASTER_ACCESS_KEY:
            return True, {'is_master': True}

        # Verificar claves de profesionales
        if hasattr(Config, 'PROFESSIONAL_ACCESS_KEYS'):
            keys = Config.PROFESSIONAL_ACCESS_KEYS
            if key in keys:
                key_data = keys[key]

                # Verificar si ya fue usada
                if key_data.get('used', False):
                    allow_reuse = getattr(Config, 'ALLOW_KEY_REUSE', False)
                    if not allow_reuse:
                        return False, {'error': 'key_already_used'}

                # Verificar expiración
                if key_data.get('expires'):
                    from datetime import datetime
                    try:
                        expires_str = key_data['expires']
                        # Asegurar formato ISO
                        if 'T' not in expires_str:
                            expires_str += 'T00:00:00'
                        expires = datetime.fromisoformat(expires_str)
                        if datetime.now() > expires:
                            return False, {'error': 'key_expired'}
                    except:
                        pass  # Si hay error parseando fecha, ignorar expiración

                return True, {'is_master': False, 'key_data': key_data}

        return False, {'error': 'key_not_found'}

    def _activate_professional_access(self, session: SessionData, key: str, is_master: bool = False) -> str:
        """
        Activa el acceso del profesional después de validar la clave.

        Args:
            session: Sesión del profesional
            key: Clave validada
            is_master: Si es la master key

        Returns:
            Mensaje de confirmación + menú principal
        """
        from src.config.config import Config
        from src.database.database import db
        from datetime import datetime

        # Marcar clave como usada (si no es master)
        if not is_master and hasattr(Config, 'PROFESSIONAL_ACCESS_KEYS'):
            keys = Config.PROFESSIONAL_ACCESS_KEYS
            if key in keys:
                keys[key]['used'] = True
                keys[key]['used_by'] = session.phone_number
                keys[key]['used_at'] = datetime.now().isoformat()

        # Crear o activar profesional en la base de datos
        prof = db.get_professional(session.phone_number)
        if not prof:
            # Crear registro básico
            db.add_professional(
                phone=session.phone_number,
                name="Usuario Nuevo",
                email=None,
                zone=None,
                gender=None,
                accept_prepaga=False,
                category=None
            )
            print(f"[PROF] ✅ Nuevo profesional creado: {session.phone_number}")
        else:
            print(
                f"[PROF] ✅ Profesional existente activado: {session.phone_number}")

        # Transicionar al menú principal
        session.transition_to(ConversationState.PROF_MAIN_MENU)
        return professional_messages.PROF_KEY_VALID + "\n\n" + professional_messages.PROF_MAIN_MENU

    def handle_prof_main_menu(self, session: SessionData, message: str) -> str:
        """
        Maneja menú principal del profesional.
        Opciones:
        1. Ver Mi Agenda
        2. Actualizar Mi Información
        3. Carga Rápida de Información
        4. Mis Citas
        0. Volver al inicio

        Nota: La gestión de horarios libres y carga de agenda semanal
        fueron eliminadas en V2. La disponibilidad se calcula
        automáticamente desde Google Calendar.
        """
        message_lower = message.lower().strip()

        # Detectar saludos → resetear y saludar
        if message_lower in ['hola', 'hello', 'hi', 'hey', 'buenos días', 'buenas tardes', 'buenas noches']:
            session.reset()
            session.set_role(UserRole.PROFESSIONAL)
            session.transition_to(ConversationState.PROF_MAIN_MENU)
            from src.database.database import db
            prof = db.get_professional(session.phone_number)
            if prof and prof.get('name') and prof.get('name') != 'Usuario Nuevo':
                greeting = f"¡Hola Dr/Dra. {prof['name']}! 👋\n\n"
            else:
                greeting = "¡Hola! 👋\n\n"
            return greeting + professional_messages.PROF_MAIN_MENU

        # Detectar "menu" o "volver"
        if message_lower in ['menu', 'menú', 'volver']:
            return professional_messages.PROF_MAIN_MENU

        # Opciones del menú
        if message == '1':
            schedule_info = professional_service.get_complete_schedule(session.phone_number)
            return schedule_info['formatted'] + "\n\n" + professional_messages.PROF_MAIN_MENU

        elif message == '2':
            session.clear_temp()
            if not session.get_temp('prof_info'):
                session.store_temp('prof_info', {})
            session.transition_to(ConversationState.PROF_INFO_MENU)
            return self.format_prof_info_menu(session)

        elif message == '3':
            session.clear_temp()
            session.transition_to(ConversationState.PROF_INFO_QUICK)
            return professional_messages.PROF_INFO_QUICK_FORMAT

        elif message == '4':
            session.transition_to(ConversationState.PROF_VIEW_APPOINTMENTS)
            return self.handle_prof_view_appointments(session, message)

        elif message == '0':
            session.reset()
            return common_messages.WELCOME

        else:
            return "❌ Opción inválida. Selecciona un número del menú.\n\n" + professional_messages.PROF_MAIN_MENU

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
                from src.config.domain_config import DomainConfig

                incomplete_msg = professional_messages.PROF_INFO_INCOMPLETE.format(
                    category_label=DomainConfig.CATEGORY_LABEL
                )

                return incomplete_msg + "\n\n" + self.format_prof_info_menu(session)

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

        # Check for back command
        if message == '0':
            session.clear_temp()
            session.transition_to(ConversationState.PROF_MAIN_MENU)
            return professional_messages.PROF_MAIN_MENU

        # Obtener citas del profesional
        appointments = db.get_appointments_by_professional(
            professional_phone=session.phone_number,
            status=None,  # Todas
            from_date=None  # Desde hoy
        )

        if not appointments or len(appointments) == 0:
            # También aquí, solo el mensaje de "no hay citas"
            return appointment_messages.PROF_NO_APPOINTMENTS

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

        # Guardar lista para siguiente selección
        session.store_temp('appointment_list', appointments)

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

    def parse_prof_info_quick(self, message: str) -> tuple:
        """
        Parse professional info from message.

        Supports two formats:
        1. With labels (key: value)
        2. Without labels (line by line in order)

        Returns:
            tuple: (result_dict, errors_list)
        """
        import re

        lines = [line.strip()
                 for line in message.strip().split('\n') if line.strip()]
        result = {}
        errors = []

        # ✅ AGREGAR: Validar mínimo de líneas
        if len(lines) < 6:
            errors.append(
                f"❌ Información incompleta: Se recibieron {len(lines)} línea(s), se requieren mínimo 6"
            )
            errors.append(
                "📋 Campos requeridos: nombre, email, zona, género, prepaga, especialidad"
            )
            errors.append(
                "💡 Los campos bio y honorarios son opcionales"
            )
            return None, errors

        # Check if using labeled format (key: value)
        has_labels = any(':' in line for line in lines)

        if has_labels:
            # ===== FORMATO CON ETIQUETAS =====
            # nombre: Dr. Juan Pérez
            # email: juan@email.com
            # etc.

            label_map = {
                'nombre': 'name',
                'name': 'name',
                'email': 'email',
                'correo': 'email',
                'zona': 'zona',
                'zone': 'zona',
                'genero': 'genero',
                'género': 'genero',
                'gender': 'genero',
                'sexo': 'genero',
                'prepaga': 'prepaga',
                'especialidad': 'especialidad',
                'specialty': 'especialidad',
                'categoria': 'especialidad',
                'bio': 'bio',
                'descripcion': 'bio',
                'descripción': 'bio',
                'honorarios': 'fee_range',
                'fee': 'fee_range',
                'precio': 'fee_range'
            }

            for line in lines:
                if ':' not in line:
                    continue

                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()

                if key in label_map:
                    field = label_map[key]
                    result[field] = value

            # ✅ MEJORAR: Validar campos requeridos con mensajes específicos
            required_fields = {
                'name': 'nombre',
                'email': 'email',
                'zona': 'zona',
                'genero': 'género',
                'prepaga': 'prepaga',
                'especialidad': 'especialidad'
            }

            missing_fields = []
            for field, label in required_fields.items():
                if field not in result or not result[field]:
                    missing_fields.append(label)

            if missing_fields:
                errors.append(
                    f"❌ Faltan campos requeridos: {', '.join(missing_fields)}")
                errors.append(
                    "💡 Asegúrate de incluir todos los campos obligatorios")
                return None, errors

        else:
            # ===== FORMATO SIN ETIQUETAS =====
            # Orden: nombre, email, zona, genero, prepaga, especialidad, [bio], [honorarios]

            # ✅ VALIDAR: Mínimo 6 líneas
            if len(lines) < 6:
                errors.append(
                    f"❌ Faltan datos: Se recibieron {len(lines)} línea(s), se requieren mínimo 6"
                )
                errors.append(
                    "\n📋 Orden correcto:"
                )
                errors.append("1. Nombre")
                errors.append("2. Email")
                errors.append("3. Zona (norte/sur)")
                errors.append("4. Género (masculino/femenino/otro)")
                errors.append("5. Prepaga (si/no)")
                errors.append("6. Especialidad")
                errors.append("7. Bio (opcional)")
                errors.append("8. Honorarios (opcional, ej: 100-150)")
                return None, errors

            result = {
                'name': lines[0],
                'email': lines[1],
                'zona': lines[2].lower().strip(),
                'genero': lines[3].lower().strip(),
                'prepaga': lines[4].lower().strip(),
                'especialidad': lines[5]
            }

            # Opcionales
            if len(lines) >= 7:
                result['bio'] = lines[6]
            if len(lines) >= 8:
                result['fee_range'] = lines[7]

        # ===== VALIDACIONES =====

        # Email
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, result['email']):
            errors.append(
                f"❌ Email inválido: {result['email']}"
            )

        # Zona
        zona_map = {
            'norte': 'norte', 'n': 'norte', 'north': 'norte',
            'sur': 'sur', 's': 'sur', 'south': 'sur'
        }
        if result['zona'] not in zona_map:
            errors.append(
                f"❌ Zona inválida: '{result['zona']}' (usa: norte o sur)"
            )
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
                f"❌ Género inválido: '{result['genero']}' (usa: masculino, femenino, otro)"
            )
        else:
            result['genero'] = genero_map[result['genero']]

        # Prepaga
        prepaga_map = {
            'si': True, 'sí': True, 's': True, 'yes': True, 'y': True,
            'no': False, 'n': False
        }
        if result['prepaga'] not in prepaga_map:
            errors.append(
                f"❌ Prepaga inválida: '{result['prepaga']}' (usa: si o no)"
            )
        else:
            result['prepaga'] = prepaga_map[result['prepaga']]

        # Validar fee_range si existe (opcional)
        if 'fee_range' in result and result['fee_range']:
            match = re.match(r'^(\d+)-(\d+)$', result['fee_range'].strip())
            if not match:
                errors.append(
                    f"❌ Honorarios inválidos: '{result['fee_range']}' (usa formato: 100-150)"
                )
            else:
                min_fee, max_fee = match.groups()
                if int(min_fee) >= int(max_fee):
                    errors.append(
                        "❌ Honorarios: el mínimo debe ser menor que el máximo"
                    )

        # ✅ AGREGAR: Si hay errores, incluir sugerencia
        if errors:
            errors.append("\n💡 Revisa tu información e inténtalo nuevamente")
            errors.append("💡 Escribe *0* para volver al menú")
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
            # Mensaje de error más claro
            error_msg = "\n".join(errors)

            # Encabezado de error
            response = "⚠️ *Error en la información*\n\n"
            response += error_msg
            response += "\n\n" + "─" * 40 + "\n\n"
            response += professional_messages.PROF_INFO_QUICK_FORMAT

            return response

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

        return f"✅ ¡Información guardada!\n\n{summary}\n\n" + professional_messages.PROF_MAIN_MENU

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

    def _format_next_available_days(self, phone: str, days_to_check: int = 7, max_to_show: int = 5) -> str:
        """
        Format next available days with slot counts.
        Uses Google Calendar to check real availability.
        
        Args:
            phone: Professional's phone
            days_to_check: How many days ahead to check (default 7)
            max_to_show: Maximum days to display (default 5)
        
        Returns:
            Formatted string with available days
        """
        from datetime import datetime, timedelta
        
        try:
            prof = self.db.get_professional(phone)
            if not prof or not prof.get('calendar_id'):
                return "   Consultar disponibilidad directamente\n"
            
            today = datetime.now().date()
            available_days = []
            
            day_names = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
            
            # Buscar próximos días con disponibilidad
            for day_offset in range(days_to_check):
                check_date = today + timedelta(days=day_offset)
                date_str = check_date.strftime("%Y-%m-%d")
                
                # Contar slots disponibles ese día
                from src.services.professional_service import professional_service
                slots = professional_service.get_available_slots(
                    professional_phone=phone,
                    date=date_str,
                    duration_minutes=50
                )
                
                if slots:
                    day_name = day_names[check_date.weekday()]
                    date_formatted = f"{check_date.day:02d}/{check_date.month:02d}"
                    slot_count = len(slots)
                    
                    available_days.append({
                        'day_name': day_name,
                        'date': date_formatted,
                        'slot_count': slot_count,
                        'date_str': date_str
                    })
                    
                    # Limitar cantidad mostrada
                    if len(available_days) >= max_to_show:
                        break
            
            # Formatear salida
            if not available_days:
                return "   No hay horarios disponibles en los próximos días\n"
            
            output = "📅 PRÓXIMOS DÍAS DISPONIBLES:\n"
            for day_info in available_days:
                output += f"   ✅ {day_info['day_name']} {day_info['date']} - {day_info['slot_count']} horarios\n"
            
            return output
            
        except Exception as e:
            print(f"[CLIENT] ⚠️ Error formatting next available days: {e}")
            return "   Consultar disponibilidad directamente\n"