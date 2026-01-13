"""
Client Handler
==============
Maneja todo el flujo de conversación del cliente/paciente.

Responsabilidades:
- Menú principal del cliente
- Búsqueda de profesionales (3 modos: hoy, avanzada, rápida)
- Filtros (zona, fecha, hora, prepaga, sexo, especialidad)
- Multi-filtro (búsqueda paso a paso)
- Mostrar resultados
- Ver detalle de profesional
- Contactar profesional

Este archivo contiene ~800 líneas de lógica específica del cliente.
"""

from datetime import date

from requests import session
from src.services.user_service import user_service
from src.config.domain_config import DomainConfig
from src.core.states import ConversationState, SessionData, UserRole
from src.messages.messages_common import common_messages
from src.messages.messages_client import client_messages
from src.messages.messages_appointments import appointment_messages
from src.core.validators import parse_date, validate_time
from src.services.client_service import client_service
from src.services.analytics_service import analytics_service
from src.database.database import db


class ClientHandler:
    """
    Handler para gestión del flujo del cliente.

    El cliente puede buscar profesionales de 3 formas:
    1. Búsqueda para HOY → filtro rápido por horario
    2. Búsqueda AVANZADA → multi-filtro paso a paso
    3. Búsqueda RÁPIDA → todo en un mensaje
    4. Búsqueda VIRTUAL → sesiones online directamente
    5. Búsqueda PRESENCIAL → filtro por zona
    """

    def __init__(self):
        """
        Inicializar handler del cliente.

        Los mensajes se importan directamente desde los módulos:
        - common_messages: Validaciones, errores, ayuda
        - client_messages: Búsqueda, filtros, resultados
        - appointment_messages: Sistema de citas
        """
        pass

    # ==========================================
    # MENÚ PRINCIPAL DEL CLIENTE
    # ==========================================

    def handle_client_main_menu(self, session: SessionData, message: str) -> str:
        """
        Maneja menú principal del cliente.
        
        NOTA: Ahora usa el mismo menú que CLIENT_NEW_USER_MENU para consistencia.
        
        Opciones:
        1. Buscar profesional (Búsqueda asistida paso a paso)
        2. Ver disponibles mañana
        3. Información del centro
        0. Volver al inicio
        """
        from src.services.user_service import user_service
        
        # Validar comandos especiales
        message_lower = message.lower().strip()

        if message_lower in ['hola', 'hello', 'hi', 'hey', 'buenos días', 'buenas tardes', 'buenas noches']:
            session.reset()
            session.set_role(UserRole.CLIENT)
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)

            from src.database.database import db
            client = db.get_client(session.phone_number)

            if client and client.get('name'):
                greeting = f"¡Hola {client['name']}! 👋\n\n"
            else:
                greeting = "¡Hola! 👋\n\n"

            welcome_msg = user_service.generate_welcome_message({
                'user_type': 'new',
                'name': None,
                'is_registered': False,
                'has_pending_appointments': False,
                'pending_appointments': [],
                'profile': None
            })
            
            return greeting + welcome_msg

        if message_lower in ['menu', 'menú', 'volver']:
            welcome_msg = user_service.generate_welcome_message({
                'user_type': 'new',
                'name': None,
                'is_registered': False,
                'has_pending_appointments': False,
                'pending_appointments': [],
                'profile': None
            })
            return welcome_msg

        # === OPCIONES DEL MENÚ ===
        
        if message == '1':
            # Opción 1: Búsqueda asistida paso a paso
            print(f"[CLIENT] Búsqueda asistida: {session.phone_number}")
            
            session.clear_temp()
            session.store_temp('filters', {})
            session.transition_to(ConversationState.CLIENT_MULTIFILTER_MENU)
            return self.format_multifilter_menu(session)

        elif message == '2':
            # Opción 2: Ver disponibles mañana
            print(f"[CLIENT] Disponibles mañana: {session.phone_number}")
            
            from datetime import date, timedelta

            tomorrow = date.today() + timedelta(days=1)
            tomorrow_str = tomorrow.strftime("%Y-%m-%d")
            tomorrow_formatted = tomorrow.strftime("%d/%m/%Y")

            session.store_temp('search_date', tomorrow_str)
            session.store_temp('search_date_formatted', tomorrow_formatted)

            # ✅ CORRECCIÓN: Usar el método correcto con date_str
            results = client_service.search_professionals_by_filters(
                date_str=tomorrow_str,
                limit=10
            )

            # Log search
            search_id = analytics_service.log_search(
                client_phone=session.phone_number,
                search_type='tomorrow',
                search_params={'fecha': tomorrow_formatted},
                result_count=len(results),
                session_id=session.phone_number
            )
            session.store_temp('current_search_id', search_id)
            session.store_temp('search_results', results)

            # Transicionar al estado de resultados
            session.transition_to(ConversationState.CLIENT_SHOW_RESULTS)

            # Si no hay resultados
            if len(results) == 0:
                return client_messages.CLIENT_NO_RESULTS

            # Formatear y mostrar resultados
            formatted = client_service.format_results_list(results)
            return formatted
        
        elif message == '3':
            # Opción 3: Información del centro
            print(f"[CLIENT] Info del centro: {session.phone_number}")

            info_message = user_service.get_center_info()
            return info_message

        elif message == '0':
            # Volver al inicio - regenerar el mismo menú
            welcome_msg = user_service.generate_welcome_message({
                'user_type': 'new',
                'name': None,
                'is_registered': False,
                'has_pending_appointments': False,
                'pending_appointments': [],
                'profile': None
            })
            return welcome_msg

        else:
            # Opción inválida
            invalid_msg = common_messages.INVALID_OPTION + "\n\n"
            welcome_msg = user_service.generate_welcome_message({
                'user_type': 'new',
                'name': None,
                'is_registered': False,
                'has_pending_appointments': False,
                'pending_appointments': [],
                'profile': None
            })
            return invalid_msg + welcome_msg
    def handle_client_new_user_menu(self, session: SessionData, message: str) -> str:
        """
        Maneja menú especial para usuarios nuevos.

        Opciones optimizadas:
        1. Búsqueda asistida paso a paso
        2. Ver disponibles mañana (búsqueda rápida)
        3. Información del centro

        Args:
            session: Sesión del usuario
            message: Opción seleccionada

        Returns:
            Respuesta según la opción
        """
        if message == '1':
            # Opción 1: Búsqueda asistida paso a paso
            print(
                f"[CLIENT] Usuario nuevo → Búsqueda asistida: {session.phone_number}")

            session.temp_data.clear()
            session.transition_to(ConversationState.CLIENT_MULTIFILTER_MENU)

            # Iniciar flujo de filtros paso a paso
            return self.handle_client_multifilter_menu(session, "start")

        elif message == '2':
            # Opción 2: Búsqueda rápida para mañana
            print(
                f"[CLIENT] Usuario nuevo → Disponibles mañana: {session.phone_number}")

            from datetime import date, timedelta

            tomorrow = date.today() + timedelta(days=1)
            tomorrow_str = tomorrow.strftime("%Y-%m-%d")
            tomorrow_formatted = tomorrow.strftime("%d/%m/%Y")

            # Guardar fecha en sesión
            session.temp_data['search_date'] = tomorrow_str
            session.temp_data['search_filters'] = {'fecha': tomorrow_formatted}

            # Buscar profesionales disponibles mañana
            results = client_service.search_professionals(
                available_date=tomorrow_str
            )

            if not results:
                # No hay resultados
                message = f"😔 No encontramos {DomainConfig.PROFESSIONAL_TITLE_PLURAL_LOWER} "
                message += f"disponibles para mañana ({tomorrow_formatted}).\n\n"
                message += "¿Qué querés hacer?\n\n"
                message += "1️⃣ Búsqueda asistida (elegir fecha y filtros)\n"
                message += "2️⃣ Buscar para otra fecha\n"
                message += "0️⃣ Volver al menú"

                # Mantener en el mismo estado
                return message

            # Hay resultados - mostrarlos
            session.transition_to(ConversationState.CLIENT_SHOW_RESULTS)
            session.temp_data['search_results'] = results

            return self.format_search_results(results, session)

        elif message == '3':
            # Opción 3: Información del centro
            print(
                f"[CLIENT] Usuario nuevo → Info del centro: {session.phone_number}")

            from src.services.user_service import user_service

            info_message = user_service.get_center_info()

            # Mantener en el mismo estado para que puedan volver a elegir
            return info_message

        elif message == '0':
            # Volver al menú de bienvenida (regenerar mensaje)
            print(
                f"[CLIENT] Usuario nuevo → Volver inicio: {session.phone_number}")
            
            from src.services.user_service import user_service
            
            # Mantener el rol de cliente, solo regenerar el mensaje de bienvenida
            welcome_msg = user_service.generate_welcome_message({
                'user_type': 'new',
                'name': None,
                'is_registered': False,
                'has_pending_appointments': False,
                'pending_appointments': [],
                'profile': None
            })
            
            # Mantener en el mismo estado CLIENT_NEW_USER_MENU
            return welcome_msg

        else:
            # Opción inválida - volver a mostrar el menú
            from src.services.user_service import user_service

            invalid_msg = common_messages.INVALID_OPTION + "\n\n"

            # Regenerar mensaje de bienvenida
            welcome_msg = user_service.generate_welcome_message({
                'user_type': 'new',
                'name': None,
                'is_registered': False,
                'has_pending_appointments': False,
                'pending_appointments': [],
                'profile': None
            })

            return invalid_msg + welcome_msg
    # ==========================================
    # FILTROS INDIVIDUALES (Búsqueda simple)
    # ==========================================

    def handle_client_filter_zona(self, session: SessionData, message: str) -> str:
        """Maneja filtro de zona."""
        # Check for back command
        if message == '0':
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return client_messages.CLIENT_MAIN_MENU

        if message == '1':
            zona = 'norte'
        elif message == '2':
            zona = 'sur'
        else:
            return common_messages.INVALID_OPTION + "\n\n" + client_messages.CLIENT_ASK_ZONA

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
            return client_messages.CLIENT_NO_RESULTS

        formatted = client_service.format_results_list(results)
        session.transition_to(ConversationState.CLIENT_SHOW_RESULTS)
        return formatted

    def handle_client_filter_fecha(self, session: SessionData, message: str) -> str:
        """Maneja filtro de fecha - pide fecha."""
        # Check for back command
        if message == '0':
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return client_messages.CLIENT_MAIN_MENU

        date_obj = parse_date(message)

        if not date_obj:
            return common_messages.INVALID_DATE + "\n\n" + client_messages.CLIENT_ASK_FECHA

        # Validate date is not in the past
        from datetime import date
        today = date.today()

        if date_obj < today:
            return f"""❌ *Fecha inválida*

    La fecha ingresada ({message}) ya pasó.

    Por favor, ingresa una fecha de hoy en adelante.

    {client_messages.CLIENT_ASK_FECHA}"""

        session.store_temp('fecha', date_obj)
        session.store_temp('fecha_str', message)
        session.transition_to(ConversationState.CLIENT_FILTER_HORA)
        return client_messages.CLIENT_ASK_HORA

    def handle_client_filter_hora(self, session: SessionData, message: str) -> str:
        """Maneja filtro de hora - acepta hora específica o mañana/tarde."""
        # Check for back command
        if message == '0':
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return client_messages.CLIENT_MAIN_MENU

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
        elif message == '3' or message.lower() in ['cualquier', 'cualquiera', 'any', 'todo']:
            # Any time: 8:00 - 20:00 (full day)
            time_start = "08:00"
            time_end = "20:00"
            time_range = True
        else:
            # User entered specific time
            if not validate_time(message):
                return common_messages.INVALID_TIME
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
        """Maneja filtro de prepaga."""
        # Check for back command
        if message == '0':
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return client_messages.CLIENT_MAIN_MENU

        if message == '1':
            session.store_temp('prepaga', True)
        elif message == '2':
            session.store_temp('prepaga', False)
        elif message == '3':
            session.store_temp('prepaga', None)
        else:
            return common_messages.INVALID_OPTION + "\n\n" + client_messages.CLIENT_ASK_PREPAGA

        # TODO: Search database
        print(f"[DB] TODO: Search by prepaga - {session.get_temp('prepaga')}")

        session.transition_to(ConversationState.CLIENT_SHOW_RESULTS)
        return "🔍 Buscando...\n\n📋 Próximamente mostraré resultados.\n\nEscribe 'menu' para volver."

    def handle_client_filter_sexo(self, session: SessionData, message: str) -> str:
        """Maneja filtro de sexo."""
        # Check for back command
        if message == '0':
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return client_messages.CLIENT_MAIN_MENU

        if message == '1':
            session.store_temp('sexo', 'm')
        elif message == '2':
            session.store_temp('sexo', 'f')
        elif message == '3':
            session.store_temp('sexo', None)
        else:
            return common_messages.INVALID_OPTION + "\n\n" + client_messages.CLIENT_ASK_SEXO

        # TODO: Search database
        print(f"[DB] TODO: Search by sexo - {session.get_temp('sexo')}")

        session.transition_to(ConversationState.CLIENT_SHOW_RESULTS)
        return "🔍 Buscando...\n\n📋 Próximamente mostraré resultados.\n\nEscribe 'menu' para volver."

    # ==========================================
    # MULTI-FILTRO (Búsqueda avanzada)
    # ==========================================

    def format_multifilter_menu(self, session: SessionData) -> str:
        """Formatea menú multi-filtro con filtros activos."""
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
        menu = client_messages.CLIENT_MULTIFILTER_MENU(active_filters)

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

    def handle_client_multifilter_menu(self, session: SessionData, message: str) -> str:
        """
        Maneja menú multi-filtro.

        Permite al usuario ir agregando filtros uno por uno,
        y cuando tenga los que necesita, ejecutar la búsqueda.
        """
        # Mostrar menú inicial si es start
        if message == 'start':
            return self.format_multifilter_menu(session)

        # Opción 9: Buscar con filtros actuales
        if message == '9':
            filters = session.get_temp('filters', {})

            if not filters:
                return "⚠️ No has seleccionado ningún filtro.\n\n" + self.format_multifilter_menu(session)

            # Construir parámetros de búsqueda
            search_params = {}
            if 'zona' in filters:
                search_params['zone'] = filters['zona']
            if 'prepaga' in filters:
                search_params['accept_prepaga'] = filters['prepaga']
            if 'sexo' in filters:
                search_params['gender'] = filters['sexo']
            if 'fecha' in filters:
                search_params['available_date'] = filters['fecha']

            # Buscar profesionales
            results = client_service.search_professionals_by_filters(
                **search_params, limit=10)

            # Log de búsqueda
            search_id = analytics_service.log_search(
                client_phone=session.phone_number,
                search_type='multifilter',
                search_params=filters,
                result_count=len(results),
                session_id=session.phone_number
            )
            session.store_temp('current_search_id', search_id)

            # Guardar resultados
            session.store_temp('search_results', results)
            session.transition_to(ConversationState.CLIENT_SHOW_RESULTS)

            # Formatear y retornar
            if len(results) == 0:
                return client_messages.CLIENT_NO_RESULTS

            formatted = client_service.format_results_list(results)
            return formatted

        # Opción 0: Volver al menú cliente
        elif message == '0':
            
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            
            welcome_msg = user_service.generate_welcome_message({
                'user_type': 'new',
                'name': None,
                'is_registered': False,
                'has_pending_appointments': False,
                'pending_appointments': [],
                'profile': None
            })
            
            return welcome_msg

        # Opción 1: Zona
        elif message == '1':
            session.transition_to(ConversationState.CLIENT_MULTIFILTER_ZONA)
            return client_messages.CLIENT_ASK_ZONA

        # Opción 2: Disponibilidad
        elif message == '2':
            session.transition_to(ConversationState.CLIENT_MULTIFILTER_FECHA)
            return client_messages.CLIENT_ASK_FECHA

        # Opción 3: Prepaga
        elif message == '3':
            session.transition_to(ConversationState.CLIENT_MULTIFILTER_PREPAGA)
            return client_messages.CLIENT_ASK_PREPAGA

        # Opción 4: Sexo/Género
        elif message == '4':
            session.transition_to(ConversationState.CLIENT_MULTIFILTER_SEXO)
            return client_messages.CLIENT_ASK_SEXO

        # Opción 5: Especialidad (TODO: implement)
        elif message == '5':
            session.transition_to(ConversationState.CLIENT_MULTIFILTER_ESPECIALIDAD)
            category_options = client_messages.format_category_options()
            return client_messages.CLIENT_ASK_ESPECIALIDAD.format(
                category_options=category_options
            )
        else:
            return common_messages.INVALID_OPTION + "\n\n" + self.format_multifilter_menu(session)

    def handle_client_multifilter_zona(self, session: SessionData, message: str) -> str:
        """Maneja filtro de zona en modo multi-filtro."""
        # Check for back command
        if message == '0':
            session.transition_to(ConversationState.CLIENT_MULTIFILTER_MENU)
            return self.format_multifilter_menu(session)

        filters = session.get_temp('filters', {})

        if message == '1':
            filters['zona'] = 'norte'
            filter_display = "Zona: Norte"
        elif message == '2':
            filters['zona'] = 'sur'
            filter_display = "Zona: Sur"
        else:
            zone_options = client_messages.format_zone_options()
            return common_messages.INVALID_OPTION + "\n\n" + client_messages.CLIENT_ASK_ZONA.format(
                zone_options=zone_options
            )

        session.store_temp('filters', filters)
        session.transition_to(ConversationState.CLIENT_MULTIFILTER_MENU)
        return client_messages.CLIENT_MULTIFILTER_ADDED.format(
            filter_name=filter_display,
            menu=self.format_multifilter_menu(session)
        )

    def handle_client_multifilter_fecha(self, session: SessionData, message: str) -> str:
        """Maneja filtro de fecha en modo multi-filtro."""
        # Check for back command FIRST
        if message == '0':
            session.transition_to(ConversationState.CLIENT_MULTIFILTER_MENU)
            return self.format_multifilter_menu(session)

        date_obj = parse_date(message)

        if not date_obj:
            return common_messages.INVALID_DATE + "\n\n" + client_messages.CLIENT_ASK_FECHA

        # Validate date is not in the past
        from datetime import date
        today = date.today()

        if date_obj < today:
            return f"""❌ *Fecha inválida*

    La fecha ingresada ({message}) ya pasó.

    Por favor, ingresa una fecha de hoy en adelante.

    {client_messages.CLIENT_ASK_FECHA}"""

        filters = session.get_temp('filters', {})
        filters['fecha'] = message
        session.store_temp('filters', filters)
        session.transition_to(ConversationState.CLIENT_MULTIFILTER_HORA)
        return client_messages.CLIENT_ASK_HORA

    def handle_client_multifilter_hora(self, session: SessionData, message: str) -> str:
        """Maneja filtro de hora en modo multi-filtro."""
        if message == '0':
            session.transition_to(ConversationState.CLIENT_MULTIFILTER_MENU)
            return self.format_multifilter_menu(session)

        # Simple time validation (HH:MM)
        if not validate_time(message) and message not in ['1', '2']:
            return common_messages.INVALID_TIME + "\n\n" + client_messages.CLIENT_ASK_HORA

        filters = session.get_temp('filters', {})

        # Convert option to time description
        if message == '1':
            filters['hora'] = 'Mañana (8:00-13:00)'
        elif message == '2':
            filters['hora'] = 'Tarde (13:00-20:00)'
        else:
            filters['hora'] = message

        session.store_temp('filters', filters)
        session.transition_to(ConversationState.CLIENT_MULTIFILTER_MENU)

        return client_messages.CLIENT_MULTIFILTER_ADDED.format(
            filter_name=f"Horario: {filters['hora']}",
            menu=self.format_multifilter_menu(session)
        )

    def handle_client_multifilter_prepaga(self, session: SessionData, message: str) -> str:
        """Maneja filtro de prepaga en modo multi-filtro."""
        # Check for back command FIRST
        if message == '0':
            session.transition_to(ConversationState.CLIENT_MULTIFILTER_MENU)
            return self.format_multifilter_menu(session)

        filters = session.get_temp('filters', {})

        if message == '1':
            filters['prepaga'] = True
            filter_display = "Acepta Prepaga: Sí"
        elif message == '2':
            filters['prepaga'] = False
            filter_display = "Acepta Prepaga: No"
        elif message == '3':
            # No importa = no aplicar filtro de prepaga
            # Si ya existía el filtro, lo removemos
            if 'prepaga' in filters:
                del filters['prepaga']
            session.store_temp('filters', filters)
            session.transition_to(ConversationState.CLIENT_MULTIFILTER_MENU)
            return client_messages.CLIENT_MULTIFILTER_ADDED.format(
                filter_name="Prepaga: Cualquiera (filtro removido)",
                menu=self.format_multifilter_menu(session)
            )
        else:
            return common_messages.INVALID_OPTION + "\n\n" + client_messages.CLIENT_ASK_PREPAGA

        session.store_temp('filters', filters)
        session.transition_to(ConversationState.CLIENT_MULTIFILTER_MENU)
        return client_messages.CLIENT_MULTIFILTER_ADDED.format(
            filter_name=filter_display,
            menu=self.format_multifilter_menu(session)
        )

    def handle_client_multifilter_sexo(self, session: SessionData, message: str) -> str:
        """Maneja filtro de sexo en modo multi-filtro."""
        # Check for back command FIRST
        if message == '0':
            session.transition_to(ConversationState.CLIENT_MULTIFILTER_MENU)
            return self.format_multifilter_menu(session)

        filters = session.get_temp('filters', {})

        if message == '1':
            filters['sexo'] = 'm'
            filter_display = "Género: Masculino"
        elif message == '2':
            filters['sexo'] = 'f'
            filter_display = "Género: Femenino"
        elif message == '3':
            # No importa = no aplicar filtro de género
            # Si ya existía el filtro, lo removemos
            if 'sexo' in filters:
                del filters['sexo']
            session.store_temp('filters', filters)
            session.transition_to(ConversationState.CLIENT_MULTIFILTER_MENU)
            return client_messages.CLIENT_MULTIFILTER_ADDED.format(
                filter_name="Género: Cualquiera (filtro removido)",
                menu=self.format_multifilter_menu(session)
            )
        else:
            return common_messages.INVALID_OPTION + "\n\n" + client_messages.CLIENT_ASK_SEXO

        session.store_temp('filters', filters)
        session.transition_to(ConversationState.CLIENT_MULTIFILTER_MENU)
        return client_messages.CLIENT_MULTIFILTER_ADDED.format(
            filter_name=filter_display,
            menu=self.format_multifilter_menu(session)
        )

    def handle_client_multifilter_especialidad(self, session: SessionData, message: str) -> str:
        """Maneja filtro de especialidad en modo multi-filtro."""
        # Check for back command FIRST
        if message == '0':
            session.transition_to(ConversationState.CLIENT_MULTIFILTER_MENU)
            return self.format_multifilter_menu(session)

        filters = session.get_temp('filters', {})

        # Obtener las opciones de categorías desde DomainConfig
        from src.config.domain_config import DomainConfig
        categories = DomainConfig.CATEGORIES

        # Validar que el mensaje sea un número válido
        if message in categories:
            especialidad_label = categories[message]
            filters['especialidad'] = especialidad_label
            filter_display = f"{DomainConfig.CATEGORY_LABEL}: {especialidad_label}"
        else:
            return common_messages.INVALID_OPTION + "\n\n" + client_messages.CLIENT_ASK_ESPECIALIDAD.format(
                category_options=client_messages.format_category_options()
            )

        session.store_temp('filters', filters)
        session.transition_to(ConversationState.CLIENT_MULTIFILTER_MENU)
        return client_messages.CLIENT_MULTIFILTER_ADDED.format(
            filter_name=filter_display,
            menu=self.format_multifilter_menu(session)
        )

    # ==========================================
    # BÚSQUEDA RÁPIDA (Todo en 1 mensaje)
    # ==========================================

    def parse_client_search_quick(self, message: str) -> tuple:
        """
        Parsea mensaje de búsqueda rápida.
        Soporta dos formatos:

        Formato 1 (con etiquetas):
            zona: norte
            fecha: 15/11/2025
            hora: 14:00
            prepaga: si
            genero: masculino

        Formato 2 (sin etiquetas, orden importa):
            norte
            15/11/2025
            14:00
            si
            masculino

        Todos los campos son opcionales.

        Returns:
            tuple: (dict con filtros parseados, lista de errores)
        """
        import re
        from src.core.validators import validate_email, parse_date, validate_time

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

                # Zona
                if line_lower in ['norte', 'n', 'sur', 's', 'este', 'e', 'oeste', 'o']:
                    if 'zona' not in result:
                        result['zona'] = line_lower

                # Fecha (DD/MM/YYYY or DD/MM)
                elif '/' in line:
                    if 'fecha_str' not in result:
                        result['fecha_str'] = line

                # Hora (HH:MM)
                elif ':' in line and len(line) <= 5:
                    if 'hora' not in result:
                        result['hora'] = line

                # Prepaga
                elif line_lower in ['si', 'sí', 's', 'no', 'n', 'yes', 'y']:
                    if 'prepaga' not in result:
                        result['prepaga'] = line_lower

                # Genero
                elif line_lower in ['masculino', 'm', 'male', 'hombre',
                                    'femenino', 'f', 'female', 'mujer',
                                    'otro', 'o', 'other']:
                    if 'genero' not in result:
                        result['genero'] = line_lower

        if not result:
            return None, ["❌ No se detectaron filtros válidos en tu mensaje"]

        # Validate parsed values
        validated = {}

        # Zona
        if 'zona' in result:
            zona_map = {
                'norte': 'norte', 'n': 'norte',
                'sur': 'sur', 's': 'sur',
                'este': 'este', 'e': 'este',
                'oeste': 'oeste', 'o': 'oeste'
            }
            if result['zona'] not in zona_map:
                errors.append(
                    f"❌ Zona inválida: {result['zona']} (usa: norte, sur, este, oeste)")
            else:
                validated['zona'] = zona_map[result['zona']]

        # Fecha
        if 'fecha_str' in result:
            fecha_obj = parse_date(result['fecha_str'])
            if not fecha_obj:
                errors.append(
                    f"❌ Fecha inválida: {result['fecha_str']} (usa: DD/MM/YYYY)")
            else:
                # Validate date is not in the past
                from datetime import date
                today = date.today()

                if fecha_obj < today:
                    errors.append(
                        f"❌ La fecha {result['fecha_str']} ya pasó. Usa una fecha de hoy en adelante.")
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
        """
        Maneja búsqueda rápida - todo en un mensaje.

        El usuario envía todos los filtros en un solo mensaje
        siguiendo el formato especificado.
        """
        # Check for back command
        if message == '0':
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return client_messages.CLIENT_MAIN_MENU

        # Parse the message
        filters, errors = self.parse_client_search_quick(message)

        if errors:
            error_msg = "\n".join(errors)
            return f"{error_msg}\n\n{client_messages.CLIENT_SEARCH_QUICK_FORMAT}"

        # Store filters
        session.store_temp('filters', filters)

        # Map parsed filters to service parameters
        search_params = {}

        if 'zona' in filters:
            search_params['zone'] = filters['zona']
        if 'genero' in filters:
            search_params['gender'] = filters['genero']
        if 'prepaga' in filters:
            search_params['accept_prepaga'] = filters['prepaga']
        if 'fecha' in filters:
            # Convert to YYYY-MM-DD format
            fecha_obj = filters['fecha']
            search_params['date_str'] = fecha_obj.strftime("%Y-%m-%d")

        # Search database with mapped parameters
        from src.services.client_service import client_service

        results = client_service.search_professionals_by_filters(
            **search_params, limit=10)

        # Log analytics
        from src.services.analytics_service import analytics_service

        # Convert datetime objects to strings for JSON serialization
        filters_for_log = {}
        for key, value in filters.items():
            if hasattr(value, 'strftime'):  # Es un objeto date/datetime
                filters_for_log[key] = value.strftime("%Y-%m-%d")
            else:
                filters_for_log[key] = value

        search_id = analytics_service.log_search(
            client_phone=session.phone_number,
            search_type='quick',
            search_params=filters_for_log,  # ← Usar el dict serializable
            result_count=len(results),
            session_id=session.phone_number
        )
        session.store_temp('current_search_id', search_id)

        # Store results
        session.store_temp('search_results', results)

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

        filters_text = "\n".join(filter_lines) if filter_lines else "Ninguno"

        # Format results
        if len(results) == 0:
            return f"""🔍 *Búsqueda Rápida*

    Filtros aplicados:
    {filters_text}

    {client_messages.CLIENT_NO_RESULTS}"""

        # Format results list
        formatted_results = client_service.format_results_list(results)

        session.transition_to(ConversationState.CLIENT_SHOW_RESULTS)

        return f"""🔍 *Búsqueda Rápida*

    Filtros aplicados:
    {filters_text}

    {formatted_results}"""

    # ==========================================
    # MOSTRAR RESULTADOS Y DETALLE
    # ==========================================

    def handle_client_show_results(self, session: SessionData, message: str) -> str:
        """
        Maneja vista de resultados.

        El usuario puede:
        - Seleccionar un número para ver detalle
        - Volver al menú
        - Si no hay resultados: modificar filtros o ver todos
        """
        # Check for back command
        if message == '0':
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return client_messages.CLIENT_MAIN_MENU

        # Get results from session
        results = session.get_temp('search_results', [])

        # Si NO hay resultados, manejar opciones especiales
        if not results or len(results) == 0:
            if message == '1':
                # Modificar filtros - volver al menú de filtros
                session.transition_to(ConversationState.CLIENT_MULTIFILTER_MENU)
                return self.format_multifilter_menu(session)
            
            elif message == '2':
                # Ver todos los profesionales (sin filtros)
                print("[CLIENT] User requested: Show all professionals (no filters)")
                
                # Buscar SIN filtros
                all_results = client_service.search_professionals_by_filters(limit=10)
                
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
                if len(all_results) == 0:
                    return "😔 No hay profesionales registrados en el sistema.\n\nEscribe '0' para volver al menú."
                
                formatted = client_service.format_results_list(all_results)
                return formatted
            
            else:
                # Opción inválida cuando no hay resultados
                return client_messages.CLIENT_NO_RESULTS

        # FLUJO NORMAL: Hay resultados, validar selección numérica
        try:
            selection = int(message)
        except ValueError:
            return "⚠️ Por favor, ingresá un número válido.\n\nEscribe '0' para volver."

        # Validate selection
        if selection < 1 or selection > len(results):
            return f"⚠️ Número inválido. Elegí entre 1 y {len(results)}.\n\nEscribe '0' para volver."

        # Get selected professional (adjust for 0-indexing)
        professional = results[selection - 1]

        # Store selected professional
        session.store_temp('selected_professional', professional)

        # Log contact
        search_id = session.get_temp('current_search_id')
        if search_id:
            analytics_service.log_contact(
                search_id=search_id,
                professional_phone=professional['phone'],
                result_position=selection
            )

        search_date = session.get_temp('search_date')
    
        if search_date:
            # Hay fecha específica → Mostrar horarios para agendar
            session.transition_to(ConversationState.CLIENT_VIEW_DETAIL_WITH_BOOKING)
            return client_service.format_professional_detail(
                professional,
                target_date=search_date,
                show_booking=True
            )
        else:
            # No hay fecha → Mostrar detalle normal
            session.transition_to(ConversationState.CLIENT_VIEW_DETAIL)
            return client_service.format_professional_detail(professional)


    def handle_client_view_detail(self, session: SessionData, message: str) -> str:
        """
        Maneja vista de detalle de profesional.

        Muestra información completa del profesional seleccionado.
        """
        # Check for back command
        if message == '0':
            # Go back to results
            results = session.get_temp('search_results', [])
            if results:
                formatted = client_service.format_results_list(results)
                session.transition_to(ConversationState.CLIENT_SHOW_RESULTS)
                return formatted
            else:
                session.clear_temp()
                session.transition_to(ConversationState.CLIENT_MAIN_MENU)
                return client_messages.CLIENT_MAIN_MENU

        elif message == '1':
            # Contact professional
            professional = session.get_temp('selected_professional')

            if not professional:
                return "⚠️ Error: No hay profesional seleccionado.\n\nEscribe 'menu' para volver."

            # Return contact info
            contact_message = f"📱 Contacto:\n\n"
            contact_message += f"Teléfono: {professional['phone']}\n"
            if professional.get('email'):
                contact_message += f"Email: {professional['email']}\n"
            contact_message += f"\n💬 Podés escribirle directamente por WhatsApp.\n"
            contact_message += f"\nEscribe '0' para volver o 'menu' para ir al menú principal."

            return contact_message

        else:
            return "⚠️ Opción inválida.\n\n1️⃣ Contactar\n0️⃣ Volver"

    # ==========================================
    # MIS CITAS (Appointments Management)
    # ==========================================

    def handle_client_view_appointments(self, session: SessionData, message: str) -> str:
        """
        Maneja vista de lista de citas del cliente.

        Muestra todas las citas activas (pendientes y confirmadas) del cliente.

        Args:
            message: '' = carga inicial, 'número' = selección de cita
        """
        from datetime import datetime

        # ✅ NUEVO: Si message tiene valor (no vacío), delegar a detalle
        if message and message != '0':
            return self.handle_client_appointment_detail(session, message)

        # Check for back command
        if message == '0':
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return client_messages.CLIENT_MAIN_MENU

        # Obtener citas del cliente desde la BD
        today = datetime.now().strftime("%Y-%m-%d")
        appointments = db.get_appointments_by_client(
            client_phone=session.phone_number,
            from_date=today
        )

        # Filtrar solo citas activas (no canceladas ni completadas)
        active_appointments = [
            apt for apt in appointments
            if apt['status'] in ['pendiente_confirmacion', 'confirmada']
        ]

        # Si no hay citas
        if not active_appointments:
            return appointment_messages.CLIENT_NO_APPOINTMENTS

        # Guardar lista en temp_data
        session.store_temp('appointment_list', active_appointments)

        # Formatear lista
        appointments_list = []
        for idx, apt in enumerate(active_appointments, 1):
            # Formatear fecha
            date_obj = datetime.strptime(apt['appointment_date'], "%Y-%m-%d")
            date_str = date_obj.strftime("%a %d/%m/%Y")

            # Emoji según estado
            if apt['status'] == 'pendiente_confirmacion':
                status_emoji = "⏳"
                status_text = "Pendiente confirmación"
            else:
                status_emoji = "✅"
                status_text = "Confirmada"

            appointments_list.append(
                f"{idx}️⃣ {status_emoji} {date_str} - {apt['start_time']}hs\n"
                f"   {apt['professional_name']}\n"
                f"   {status_text}"
            )

        formatted_list = "\n\n".join(appointments_list)

        return appointment_messages.CLIENT_VIEW_APPOINTMENTS.format(
            appointments_list=formatted_list
        )

    def handle_client_appointment_detail(self, session: SessionData, message: str) -> str:
        """
        Maneja detalle de una cita específica.

        Muestra información completa y opciones según el estado.

        Args:
            message: número de cita seleccionada o acción (1=cancelar/reprogramar, 2=cancelar, 0=volver)
        """
        from datetime import datetime

        # Check for back command
        if message == '0':
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return client_messages.CLIENT_MAIN_MENU

        # Si viene con opción de reprogramar/cancelar (estando ya en detalle de una cita)
        if message in ['1', '2', '3']:
            # Estas son las opciones del menú de detalle
            appointment_id = session.get_temp('appointment_id')

            if appointment_id:
                apt = db.get_appointment(appointment_id)

                if apt:
                    # ===== PARA CITAS PENDIENTES =====
                    if apt['status'] == 'pendiente_confirmacion':
                        if message == '1':
                            # Reprogramar
                            session.transition_to(
                                ConversationState.CLIENT_RESCHEDULE_APPOINTMENT)
                            return self.handle_client_reschedule_appointment(session, '1')
                        elif message == '2':
                            # Cancelar
                            session.transition_to(
                                ConversationState.CLIENT_CANCEL_APPOINTMENT)
                            return self.handle_client_cancel_appointment(session, '1')

                    # ===== PARA CITAS CONFIRMADAS =====
                    elif apt['status'] == 'confirmada':
                        if message == '1':
                            # Reprogramar
                            session.transition_to(
                                ConversationState.CLIENT_RESCHEDULE_APPOINTMENT)
                            return self.handle_client_reschedule_appointment(session, '1')
                        elif message == '2':
                            # Cancelar
                            session.transition_to(
                                ConversationState.CLIENT_CANCEL_APPOINTMENT)
                            return self.handle_client_cancel_appointment(session, '1')
        # Si es primera vez (viene de lista de citas), obtener cita por índice
        appointment_list = session.get_temp('appointment_list')

        if not appointment_list:
            # NO limpiar temp_data todavía - lo necesitamos para saber qué cita fue
            # session.clear_temp()  # ← Comentar esto

            # Transicionar a estado de éxito con opciones
            session.transition_to(ConversationState.CLIENT_CANCEL_SUCCESS)

            return appointment_messages.CLIENT_APPOINTMENT_CANCELLED

        # Validar que el número esté en rango
        try:
            selection = int(message)
            if selection < 1 or selection > len(appointment_list):
                return f"⚠️ Número inválido. Elige entre 1 y {len(appointment_list)}\n\n_Escribe *0* para volver al menú_"
        except ValueError:
            return "⚠️ Por favor, ingresa un número válido.\n\n_Escribe *0* para volver_"

        # Obtener cita seleccionada
        selected_apt = appointment_list[selection - 1]
        appointment_id = selected_apt['id']

        # Transicionar al detalle
        session.transition_to(ConversationState.CLIENT_APPOINTMENT_DETAIL)

        # Guardar ID en temp_data para acciones futuras
        session.store_temp('appointment_id', appointment_id)
        # Guardar también el número de selección para mostrarlo al usuario
        session.store_temp('selected_appointment_number', selection)

        # Obtener detalles completos de la cita
        apt = db.get_appointment(appointment_id)

        if not apt:
            return "❌ Error al cargar la cita.\n\n_Escribe *0* para volver_"

        # Formatear fecha completa
        date_obj = datetime.strptime(apt['appointment_date'], "%Y-%m-%d")

        # Mapeo manual de días en español
        dias = ['Lunes', 'Martes', 'Miércoles',
                'Jueves', 'Viernes', 'Sábado', 'Domingo']
        meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']

        dia_semana = dias[date_obj.weekday()]
        dia_numero = date_obj.day
        mes = meses[date_obj.month - 1]
        anio = date_obj.year

        date_full = f"{dia_semana} {dia_numero} de {mes} de {anio}"

        # Badge de estado
        if apt['status'] == 'pendiente_confirmacion':
            status_badge = "Estado: ⏳ *Pendiente de confirmación*"
        elif apt['status'] == 'confirmada':
            status_badge = "Estado: ✅ *Confirmada*"
        elif apt['status'] == 'completada':
            status_badge = "Estado: ✔️ *Completada*"
        else:
            status_badge = "Estado: ❌ *Cancelada*"

        # Modalidad
        modality_icons = {
            'presencial': '🏥 Presencial',
            'virtual': '💻 Virtual',
            'ambas': '🏥💻 Presencial o Virtual'
        }
        modality = modality_icons.get(apt['modality'], apt['modality'])

        # Opciones según estado
        if apt['status'] == 'pendiente_confirmacion':
            options = appointment_messages.CLIENT_APPOINTMENT_OPTIONS_PENDING
        elif apt['status'] == 'confirmada':
            options = appointment_messages.CLIENT_APPOINTMENT_OPTIONS_CONFIRMED
        elif apt['status'] == 'completada':
            options = appointment_messages.CLIENT_APPOINTMENT_FINISHED
        else:
            options = appointment_messages.CLIENT_APPOINTMENT_ALREADY_CANCELLED

        # Razón (si existe)
        reason_display = ""
        if apt.get('reason'):
            reason_display = f"\n📝 Motivo: {apt['reason']}"

        return appointment_messages.CLIENT_APPOINTMENT_DETAIL.format(
            id=session.get_temp('selected_appointment_number', apt['id']),
            date=date_full,
            time=apt['start_time'],
            professional_name=apt['professional_name'],
            professional_phone=apt['professional_phone'],
            modality=modality,
            duration=apt['duration_minutes'],
            reason_display=reason_display,
            status_badge=status_badge,
            options=options
        )

    def handle_client_cancel_appointment(self, session: SessionData, message: str) -> str:
        """
        Maneja confirmación de cancelación de cita.

        Valida que se pueda cancelar y pide confirmación.
        """
        from datetime import datetime, timedelta

        # Check for back command
        if message == '0':
            # Volver al detalle de la cita
            session.transition_to(ConversationState.CLIENT_APPOINTMENT_DETAIL)
            return self.handle_client_appointment_detail(session, '0')

        # Si message es '1', viene del detalle pidiendo cancelar
        # Si message es confirmación, procesar cancelación
        appointment_id = session.get_temp('appointment_id')

        if not appointment_id:
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return "❌ Error: No hay cita seleccionada\n\n" + client_messages.CLIENT_MAIN_MENU

        # Obtener datos de la cita
        apt = db.get_appointment(appointment_id)

        if not apt:
            return "❌ Error al cargar la cita.\n\n_Escribe *0* para volver_"

        # Validar que no esté ya cancelada
        if apt['status'] in ['cancelada_cliente', 'cancelada_profesional']:
            return appointment_messages.CLIENT_APPOINTMENT_ALREADY_CANCELLED

        # Validar que no esté completada
        if apt['status'] == 'completada':
            return "❌ No puedes cancelar una cita que ya finalizó.\n\n_Escribe *0* para volver_"

        # Calcular horas hasta la cita
        apt_datetime = datetime.strptime(
            f"{apt['appointment_date']} {apt['start_time']}",
            "%Y-%m-%d %H:%M"
        )
        now = datetime.now()
        hours_until = (apt_datetime - now).total_seconds() / 3600

        # Validar tiempo mínimo (24 horas por defecto)
        CANCELLATION_HOURS_LIMIT = 24

        if hours_until < CANCELLATION_HOURS_LIMIT:
            # Muy tarde para cancelar
            return appointment_messages.CLIENT_CANCEL_TOO_LATE.format(
                hours_until=int(hours_until),
                professional_phone=apt['professional_phone']
            )

        # Si es primera vez (viene desde detalle), mostrar confirmación
        if message == '1':
            # Formatear fecha
            date_obj = datetime.strptime(apt['appointment_date'], "%Y-%m-%d")
            date_str = date_obj.strftime("%A %d de %B de %Y").title()

            # Mostrar política si existe
            policy_info = ""
            if hasattr(DomainConfig, 'CANCELLATION_POLICY') and DomainConfig.CANCELLATION_POLICY:
                policy_info = appointment_messages.CLIENT_CANCEL_POLICY_INFO

            session.transition_to(ConversationState.CLIENT_CANCEL_REASON)

            return appointment_messages.CLIENT_CANCEL_APPOINTMENT_CONFIRM.format(
                date=date_str,
                time=apt['start_time'],
                professional_name=apt['professional_name'],
                policy_info=policy_info
            )

        # Si llegó aquí sin ser '1', es inválido
        return "⚠️ Opción inválida.\n\n_Escribe *1* para cancelar o *0* para volver_"

    def handle_client_cancel_reason(self, session: SessionData, message: str) -> str:
        """
        Maneja motivo de cancelación y ejecuta la cancelación.

        El motivo es opcional.
        """

        appointment_id = session.get_temp('appointment_id')

        if not appointment_id:
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return client_messages.CLIENT_MAIN_MENU

        # Si es '0', significa cancelar sin motivo
        if message == '0':
            reason = None
        elif message == '1':
            # Confirmando cancelación sin motivo
            reason = None
        else:
            # El mensaje es el motivo
            reason = message

        # Ejecutar cancelación en BD
        success = db.update_appointment_status(
            appointment_id=appointment_id,
            new_status='cancelada_cliente',
            changed_by='client',
            reason=reason
        )

        if not success:
            return "❌ Error al cancelar la cita. Intenta nuevamente.\n\n_Escribe *0* para volver_"

        # TODO: Crear notificación para el profesional
        # db.create_notification(...)

        # Limpiar temp_data
        session.clear_temp()
        session.transition_to(ConversationState.CLIENT_CANCEL_SUCCESS)

        return appointment_messages.CLIENT_APPOINTMENT_CANCELLED

    def handle_client_cancel_success(self, session: SessionData, message: str) -> str:
        """
        Maneja opciones después de cancelar exitosamente una cita.

        Opciones:
        1 = Ver mis citas
        2 = Buscar nuevo profesional
        0 = Menú principal
        """
        if message == '1':
            # Ver mis citas
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_VIEW_APPOINTMENTS)
            return self.handle_client_view_appointments(session, '')

        elif message == '2':
            # Buscar nuevo profesional
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return client_messages.CLIENT_MAIN_MENU

        elif message == '0':
            # Menú principal
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return client_messages.CLIENT_MAIN_MENU

        else:
            # Opción inválida
            return "⚠️ Opción inválida.\n\n" + appointment_messages.CLIENT_APPOINTMENT_CANCELLED

    # ==========================================
    # REPROGRAMACIÓN DE CITAS
    # ==========================================
    def handle_client_reschedule_appointment(self, session: SessionData, message: str) -> str:
        """
        Inicio del flujo de reprogramación.

        Valida que se pueda reprogramar (>24hs) y muestra fechas disponibles directamente.
        """
        from datetime import datetime, timedelta, date as date_type
        import os

        # Check for back command
        if message == '0':
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return client_messages.CLIENT_MAIN_MENU

        # Obtener appointment_id del temp_data
        appointment_id = session.get_temp('appointment_id')

        if not appointment_id:
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return "❌ Error: No hay cita seleccionada\n\n" + client_messages.CLIENT_MAIN_MENU

        # Obtener datos de la cita
        apt = db.get_appointment(appointment_id)

        if not apt:
            return "❌ Error al cargar la cita.\n\n_Escribe *0* para volver_"

        # Validar que no esté cancelada o completada
        if apt['status'] in ['cancelada_cliente', 'cancelada_profesional', 'completada']:
            return f"❌ No puedes reprogramar una cita con estado: {apt['status']}\n\n_Escribe *0* para volver_"

        # Calcular horas hasta la cita
        apt_datetime = datetime.strptime(
            f"{apt['appointment_date']} {apt['start_time']}",
            "%Y-%m-%d %H:%M"
        )
        now = datetime.now()
        hours_until = (apt_datetime - now).total_seconds() / 3600

        # Validar tiempo mínimo (24 horas por defecto)
        RESCHEDULE_HOURS_LIMIT = 24

        # TESTING: Skip time validation if env var is set
        if os.getenv('TESTING_SKIP_TIME_VALIDATION', '').lower() == 'true':
            print(
                f"[TEST] ⚠️ Skipping time validation for reschedule - original hours_until: {hours_until:.1f}")
            hours_until = 48  # Simular suficiente tiempo

        if hours_until < RESCHEDULE_HOURS_LIMIT:
            # Muy tarde para reprogramar
            return appointment_messages.CLIENT_RESCHEDULE_TOO_LATE.format(
                hours_until=int(hours_until),
                limit=RESCHEDULE_HOURS_LIMIT,
                professional_phone=apt['professional_phone']
            )

        # Guardar datos originales de la cita
        session.store_temp('original_date', apt['appointment_date'])
        session.store_temp('original_start_time', apt['start_time'])
        session.store_temp('original_end_time', apt['end_time'])
        session.store_temp('professional_phone', apt['professional_phone'])
        session.store_temp('professional_name', apt['professional_name'])
        session.store_temp('duration', apt['duration_minutes'])
        session.store_temp('modality', apt['modality'])

        # ✅ CAMBIO: Transicionar directamente a selección de fecha
        session.transition_to(ConversationState.CLIENT_RESCHEDULE_SELECT_DATE)

        # ✅ CAMBIO: Llamar directamente al handler de selección de fecha
        # Esto carga y muestra las fechas disponibles inmediatamente
        return self.handle_client_reschedule_select_date(session, 'start')

    def handle_client_reschedule_select_date(self, session: SessionData, message: str) -> str:
        """
        Maneja selección de nueva fecha para reprogramación.
        """
        from datetime import datetime
        from src.services.professional_service import professional_service

        # Check for back command
        if message == '0':
            # Volver al detalle de la cita
            session.transition_to(ConversationState.CLIENT_APPOINTMENT_DETAIL)
            appointment_id = session.get_temp('appointment_id')
            if appointment_id:
                apt = db.get_appointment(appointment_id)
                if apt:
                    return self._format_appointment_detail(session, apt)
            return "❌ Error al volver.\n\n_Escribe *0* para menú_"

        professional_phone = session.get_temp('professional_phone')
        original_date = session.get_temp('original_date')
        appointment_id = session.get_temp('appointment_id')

        if not professional_phone or not original_date:
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return "❌ Error: Sesión expirada\n\n" + client_messages.CLIENT_MAIN_MENU

        # ✅ CAMBIO: Verificar si ya se mostraron las fechas
        dates_shown = session.get_temp('reschedule_dates_shown', False)

        # ✅ Si es primer ingreso (viene de otro handler), mostrar fechas
        if message == 'start' or not dates_shown:

            # Buscar fechas disponibles
            dates = professional_service.get_available_dates_for_reschedule(
                professional_phone=professional_phone,
                current_appointment_date=original_date,
                current_appointment_id=appointment_id,
                days_to_search=7,
                max_dates=7
            )

            if not dates:
                return appointment_messages.CLIENT_NO_DATES_AVAILABLE.format(days=7)

            # Formatear lista de fechas
            dates_list = []
            for idx, date_info in enumerate(dates, 1):
                # Etiqueta especial para hoy/mañana
                day_label = date_info['day_name_short']
                if date_info['is_today']:
                    day_label = "HOY"
                elif date_info['is_tomorrow']:
                    day_label = "Mañana"

                dates_list.append(
                    f"{idx}️⃣ {day_label} {date_info['date_str']} "
                    f"({date_info['slots_count']} horarios)"
                )

            formatted_dates = "\n".join(dates_list)

            # ✅ CAMBIO: Guardar fechas Y marcar que ya se mostraron
            session.store_temp('available_dates', dates)
            session.store_temp('reschedule_dates_shown', True)

            # Formatear fecha original
            original_time = session.get_temp('original_start_time')
            old_date_obj = datetime.strptime(original_date, "%Y-%m-%d")
            old_date_str = old_date_obj.strftime("%d/%m/%Y")

            return appointment_messages.CLIENT_RESCHEDULE_SELECT_DATE.format(
                old_date=old_date_str,
                old_time=original_time,
                available_dates=formatted_dates
            )

        # ✅ Si llegó aquí, el usuario está seleccionando una fecha
        try:
            selection = int(message)
            available_dates = session.get_temp('available_dates')

            if not available_dates or selection < 1 or selection > len(available_dates):
                return "⚠️ Opción inválida.\n\n_Escribe el número de la fecha o *0* para volver_"

            selected_date = available_dates[selection - 1]

            # Guardar fecha seleccionada
            session.store_temp('new_date', selected_date['date_db'])
            session.store_temp('new_date_str', selected_date['date_str'])

            # ✅ IMPORTANTE: Limpiar el flag de fechas mostradas
            session.store_temp('reschedule_dates_shown', False)

            # Transicionar a selección de horario
            session.transition_to(
                ConversationState.CLIENT_RESCHEDULE_SELECT_TIME)

            # Llamar directamente al handler de selección de horario
            return self.handle_client_reschedule_select_time(session, 'start')

        except ValueError:
            return "⚠️ Por favor, ingresa el número de la fecha.\n\n_Escribe *0* para volver_"

    def handle_client_reschedule_select_time(self, session: SessionData, message: str) -> str:
        """
        Maneja selección de nuevo horario para reprogramación.
        """
        from datetime import datetime, timedelta
        from src.services.professional_service import professional_service

        # Check for back command
        if message == '0':
            # Volver a selección de fecha
            session.transition_to(
                ConversationState.CLIENT_RESCHEDULE_SELECT_DATE)
            return self.handle_client_reschedule_select_date(session, 'start')

        professional_phone = session.get_temp('professional_phone')
        new_date = session.get_temp('new_date')
        new_date_str = session.get_temp('new_date_str')

        if not professional_phone or not new_date:
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return "❌ Error: Sesión expirada\n\n" + client_messages.CLIENT_MAIN_MENU

        # ✅ CAMBIO: Si viene del inicio O es primer ingreso, mostrar horarios
        if message == 'start' or not message or message == '':

            # Obtener slots disponibles para la fecha
            slots = professional_service.get_available_slots(
                professional_phone,
                new_date,
                exclude_appointment_id=session.get_temp(
                    'appointment_id')  # Excluir cita actual
            )

            if not slots:
                return appointment_messages.CLIENT_NO_SLOTS_AVAILABLE

            # Formatear lista de horarios
            slots_list = []
            for idx, slot in enumerate(slots, 1):
                slots_list.append(
                    f"{idx}️⃣ {slot['start_time']} - {slot['end_time']}")

            formatted_slots = "\n".join(slots_list)

            # Guardar slots en temp
            session.store_temp('available_slots', slots)

            return appointment_messages.CLIENT_RESCHEDULE_SELECT_TIME.format(
                new_date=new_date_str,
                available_slots=formatted_slots
            )

        # Usuario seleccionó un horario
        try:
            selection = int(message)
            available_slots = session.get_temp('available_slots')

            if not available_slots or selection < 1 or selection > len(available_slots):
                return "⚠️ Opción inválida.\n\n_Escribe el número del horario o *0* para volver_"

            selected_slot = available_slots[selection - 1]

            # Guardar horario seleccionado
            session.store_temp('new_start_time', selected_slot['start_time'])
            session.store_temp('new_end_time', selected_slot['end_time'])

            # Transicionar a confirmación
            session.transition_to(ConversationState.CLIENT_RESCHEDULE_CONFIRM)

            # Formatear fechas para confirmación
            original_date = session.get_temp('original_date')
            original_time = session.get_temp('original_start_time')

            old_date_obj = datetime.strptime(original_date, "%Y-%m-%d")
            old_date_formatted = old_date_obj.strftime("%d/%m/%Y")

            professional_name = session.get_temp('professional_name')

            return appointment_messages.CLIENT_RESCHEDULE_CONFIRM.format(
                old_date=old_date_formatted,
                old_time=original_time,
                new_date=new_date_str,
                new_time=selected_slot['start_time'],
                professional_name=professional_name
            )

        except ValueError:
            return "⚠️ Por favor, ingresa el número del horario.\n\n_Escribe *0* para volver_"

    def handle_client_reschedule_confirm(self, session: SessionData, message: str) -> str:
        """
        Confirma y ejecuta la reprogramación de la cita.
        """
        from datetime import datetime

        # Check for back/cancel
        if message == '0':
            # Volver a selección de horario
            session.transition_to(
                ConversationState.CLIENT_RESCHEDULE_SELECT_TIME)
            return self.handle_client_reschedule_select_time(session, '')

        if message != '1':
            return "⚠️ Por favor, ingresa *1* para confirmar o *0* para cancelar."

        # Obtener datos de temp
        appointment_id = session.get_temp('appointment_id')
        new_date = session.get_temp('new_date')
        new_start_time = session.get_temp('new_start_time')
        new_end_time = session.get_temp('new_end_time')
        new_date_str = session.get_temp('new_date_str')
        professional_name = session.get_temp('professional_name')

        if not all([appointment_id, new_date, new_start_time, new_end_time]):
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return "❌ Error: Datos incompletos\n\n" + client_messages.CLIENT_MAIN_MENU

        # Actualizar cita en BD
        success = db.update_appointment_datetime(
            appointment_id=appointment_id,
            new_date=new_date,
            new_start_time=new_start_time,
            new_end_time=new_end_time,
            changed_by='client'
        )

        if not success:
            return "❌ Error al reprogramar la cita. Intenta nuevamente.\n\n_Escribe *0* para volver_"

        # TODO: Crear notificación para el profesional
        # db.create_notification(...)

        # NO limpiar temp_data - se usará en el estado de éxito
        # Transicionar a estado de éxito (reutilizamos CLIENT_CANCEL_SUCCESS)
        session.transition_to(ConversationState.CLIENT_CANCEL_SUCCESS)

        # Retornar mensaje de éxito
        return appointment_messages.CLIENT_RESCHEDULE_SUCCESS.format(
            new_date=new_date_str,
            new_time=new_start_time,
            professional_name=professional_name
        )

    # Helper method para formatear detalle de cita
    def _format_appointment_detail(self, session: SessionData, apt: dict) -> str:
        """
        Helper para formatear el detalle de una cita.
        Reutilizable desde múltiples handlers.
        """
        from datetime import datetime

        # Formatear fecha completa
        date_obj = datetime.strptime(apt['appointment_date'], "%Y-%m-%d")

        dias = ['Lunes', 'Martes', 'Miércoles',
                'Jueves', 'Viernes', 'Sábado', 'Domingo']
        meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']

        dia_semana = dias[date_obj.weekday()]
        dia_numero = date_obj.day
        mes = meses[date_obj.month - 1]
        anio = date_obj.year

        date_full = f"{dia_semana} {dia_numero} de {mes} de {anio}"

        # Badge de estado
        if apt['status'] == 'pendiente_confirmacion':
            status_badge = "Estado: ⏳ *Pendiente de confirmación*"
        elif apt['status'] == 'confirmada':
            status_badge = "Estado: ✅ *Confirmada*"
        elif apt['status'] == 'completada':
            status_badge = "Estado: ✔️ *Completada*"
        else:
            status_badge = "Estado: ❌ *Cancelada*"

        # Modalidad
        modality_icons = {
            'presencial': '🏥 Presencial',
            'virtual': '💻 Virtual',
            'ambas': '🏥💻 Presencial o Virtual'
        }
        modality = modality_icons.get(apt['modality'], apt['modality'])

        # Opciones según estado
        if apt['status'] == 'pendiente_confirmacion':
            options = appointment_messages.CLIENT_APPOINTMENT_OPTIONS_PENDING
        elif apt['status'] == 'confirmada':
            options = appointment_messages.CLIENT_APPOINTMENT_OPTIONS_CONFIRMED
        elif apt['status'] == 'completada':
            options = appointment_messages.CLIENT_APPOINTMENT_FINISHED
        else:
            options = appointment_messages.CLIENT_APPOINTMENT_ALREADY_CANCELLED

        # Razón (si existe)
        reason_display = ""
        if apt.get('reason'):
            reason_display = f"\n📝 Motivo: {apt['reason']}"

        return appointment_messages.CLIENT_APPOINTMENT_DETAIL.format(
            id=session.get_temp('selected_appointment_number', apt['id']),
            date=date_full,
            time=apt['start_time'],
            professional_name=apt['professional_name'],
            professional_phone=apt['professional_phone'],
            modality=modality,
            duration=apt['duration_minutes'],
            reason_display=reason_display,
            status_badge=status_badge,
            options=options
        )

    # ==========================================
    # CLIENT - BOOKING FLOW
    # ==========================================

    def handle_client_view_detail_with_booking(self, session: SessionData, message: str) -> str:
        """
        Handle detail view with specific time slots for booking.
        User can select a numbered time slot or go back.
        """
        from src.services.professional_service import professional_service
        
        # Check for back
        if message == '0':
            results = session.get_temp('search_results', [])
            if results:
                formatted = client_service.format_results_list(results)
                session.transition_to(ConversationState.CLIENT_SHOW_RESULTS)
                
                search_date_formatted = session.get_temp('search_date_formatted', '')
                return f"""Volviendo a los resultados...

✅ Profesionales disponibles para {search_date_formatted}:

{formatted}

Responde con el número para ver detalles.
O escribe '0' para volver al menú."""
            else:
                session.clear_temp()
                session.transition_to(ConversationState.CLIENT_MAIN_MENU)
                return client_messages.CLIENT_MAIN_MENU
        
        # Get data
        professional = session.get_temp('selected_professional')
        search_date = session.get_temp('search_date')
        
        if not professional or not search_date:
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return "❌ Error: Sesión expirada.\n\n" + client_messages.CLIENT_MAIN_MENU
        
        # Validate numeric input
        try:
            selection = int(message)
        except ValueError:
            return "⚠️ Por favor, ingresa el número del horario que deseas agendar.\n\nEscribe '0' para volver."
        
        # Get available slots
        slots = professional_service.get_available_slots(
            professional['phone'],
            search_date,
            duration_minutes=50
        )
        
        if not slots:
            return "❌ No hay horarios disponibles.\n\nEscribe '0' para volver."
        
        # Validate selection
        if selection < 1 or selection > len(slots):
            return f"⚠️ Número inválido. Elegí entre 1 y {len(slots)}.\n\nEscribe '0' para volver."
        
        # Get selected slot
        selected_slot = slots[selection - 1]
        
        # Store booking info
        session.store_temp('selected_slot', selected_slot)
        session.store_temp('booking_date', search_date)
        session.store_temp('booking_start_time', selected_slot['start_time'])
        session.store_temp('booking_end_time', selected_slot['end_time'])
        
        # Transition to confirmation
        session.transition_to(ConversationState.CLIENT_CONFIRM_BOOKING)
        
        # Format confirmation message
        from datetime import datetime
        date_obj = datetime.strptime(search_date, "%Y-%m-%d")
        date_formatted = date_obj.strftime("%d/%m/%Y")
        day_names = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        day_name = day_names[date_obj.weekday()]
        
        prof_name = professional.get('name', 'Profesional')
        prof_phone = professional.get('phone', '')
        
        return f"""✅ CONFIRMAR AGENDAMIENTO
{'=' * 40}

👨‍⚕️ Profesional: {prof_name}
📅 Fecha: {day_name} {date_formatted}
⏰ Horario: {selected_slot['start_time']} - {selected_slot['end_time']}
📱 Contacto: {prof_phone}

¿Confirmas esta cita?

1️⃣ Sí, confirmar agendamiento
0️⃣ No, volver atrás

⚠️ El profesional recibirá tu solicitud y deberá confirmarla."""

    def handle_client_confirm_booking(self, session: SessionData, message: str) -> str:
        """
        Handle booking confirmation.
        User must confirm with '1' or cancel with '0'.
        """
        from datetime import datetime
        
        # Check for cancellation
        if message == '0':
            professional = session.get_temp('selected_professional')
            search_date = session.get_temp('search_date')
            
            session.transition_to(ConversationState.CLIENT_VIEW_DETAIL_WITH_BOOKING)
            return client_service.format_professional_detail(
                professional,
                target_date=search_date,
                show_booking=True
            )
        
        # Validate confirmation
        if message != '1':
            return "⚠️ Por favor, ingresa:\n\n1️⃣ Para confirmar\n0️⃣ Para cancelar"
        
        # Get booking data
        professional = session.get_temp('selected_professional')
        booking_date = session.get_temp('booking_date')
        booking_start_time = session.get_temp('booking_start_time')
        booking_end_time = session.get_temp('booking_end_time')
        
        if not all([professional, booking_date, booking_start_time, booking_end_time]):
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return "❌ Error: Información incompleta.\n\n" + client_messages.CLIENT_MAIN_MENU
        
        # TODO: Aquí crear el appointment en la BD cuando implementes persistencia
        # from src.services.appointment_service import appointment_service
        # appointment_id = appointment_service.create_appointment(...)
        
        # Por ahora, solo simulamos
        appointment_id = "DEMO_" + datetime.now().strftime("%Y%m%d%H%M%S")
        
        print(f"[CLIENT] ✅ Agendamiento simulado:")
        print(f"         Cliente: {session.phone}")
        print(f"         Profesional: {professional['phone']}")
        print(f"         Fecha: {booking_date}")
        print(f"         Horario: {booking_start_time} - {booking_end_time}")
        print(f"         ID: {appointment_id}")
        
        session.store_temp('appointment_id', appointment_id)
        session.transition_to(ConversationState.CLIENT_BOOKING_CONFIRMED)
        
        # Format success message
        date_obj = datetime.strptime(booking_date, "%Y-%m-%d")
        date_formatted = date_obj.strftime("%d/%m/%Y")
        day_names = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        day_name = day_names[date_obj.weekday()]
        
        prof_name = professional.get('name', 'Profesional')
        prof_phone = professional.get('phone', '')
        
        return f"""✅ ¡CITA AGENDADA CON ÉXITO!
{'=' * 40}

Tu solicitud ha sido enviada al profesional.

📋 RESUMEN DE LA CITA:

👨‍⚕️ Profesional: {prof_name}
📅 Fecha: {day_name} {date_formatted}
⏰ Horario: {booking_start_time} - {booking_end_time}
📱 Contacto: {prof_phone}

📌 Estado: Pendiente de confirmación

El profesional recibirá tu solicitud y te confirmará la cita en breve.

¿Qué deseas hacer?

1️⃣ Ver mis citas
2️⃣ Nueva búsqueda
0️⃣ Menú principal"""

    def handle_client_booking_confirmed(self, session: SessionData, message: str) -> str:
        """
        Handle post-booking options.
        """
        if message == '1':
            # Ver mis citas
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_VIEW_APPOINTMENTS)
            return self.handle_client_view_appointments(session, 'start')
        
        elif message == '2':
            # Nueva búsqueda
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return client_messages.CLIENT_MAIN_MENU
        
        elif message == '0':
            # Menú principal
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return client_messages.CLIENT_MAIN_MENU
        
        else:
            return "⚠️ Opción inválida.\n\n1️⃣ Ver mis citas\n2️⃣ Nueva búsqueda\n0️⃣ Menú principal"