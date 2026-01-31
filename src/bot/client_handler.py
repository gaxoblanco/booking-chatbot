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
from typing import Dict
from requests import session
from src.integrations.appointment_calendar_service import AppointmentCalendarService
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

from src.filters.filter_manager import FilterManager
from src.filters.filter_types import FilterType


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
        
        Opciones DINÁMICAS según si tiene citas:
        - CON citas: 1=Buscar, 2=Mañana, 3=Mis citas, 4=Info
        - SIN citas: 1=Buscar, 2=Mañana, 3=Info
        """
        from src.services.user_service import user_service
        from datetime import datetime, date, timedelta
        from src.database.database import db 
        
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
                'profile': None,
                'phone_number': session.phone_number  # ⭐ IMPORTANTE
            })
            
            return greeting + welcome_msg

        if message_lower in ['menu', 'menú', 'volver']:
            welcome_msg = user_service.generate_welcome_message({
                'user_type': 'new',
                'name': None,
                'is_registered': False,
                'has_pending_appointments': False,
                'pending_appointments': [],
                'profile': None,
                'phone_number': session.phone_number  # ⭐ IMPORTANTE
            })
            return welcome_msg

        # ==========================================
        # VERIFICAR SI TIENE CITAS (para manejar opciones 3 y 4)
        # ==========================================
        today = datetime.now().strftime("%Y-%m-%d")
        appointments = db.get_appointments_by_client(
            client_phone=session.phone_number,
            from_date=today
        )
        
        # Filtrar solo citas activas
        active_appointments = [
            apt for apt in appointments
            if apt['status'] in ['pendiente_confirmacion', 'confirmada']
        ]
        
        has_appointments = len(active_appointments) > 0
        
        print(f"[CLIENT_MENU] Usuario tiene citas: {has_appointments} ({len(active_appointments)} activas)")

        # ==========================================
        # OPCIÓN 1: Búsqueda asistida
        # ==========================================
        if message == '1':
            print(f"[CLIENT] Búsqueda asistida: {session.phone_number}")
            
            session.clear_temp()
            session.set_temp('filters', {})
            session.transition_to(ConversationState.CLIENT_MULTIFILTER_MENU)
            return self.format_multifilter_menu(session)

        # ==========================================
        # OPCIÓN 2: Ver disponibles mañana
        # ==========================================
        elif message == '2':
            print(f"[CLIENT] Disponibles mañana: {session.phone_number}")
            
            tomorrow = date.today() + timedelta(days=1)
            tomorrow_str = tomorrow.strftime("%Y-%m-%d")
            tomorrow_formatted = tomorrow.strftime("%d/%m/%Y")

            session.set_temp('search_date', tomorrow_str)
            session.set_temp('search_date_formatted', tomorrow_formatted)

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
            session.set_temp('current_search_id', search_id)
            session.set_temp('search_results', results)

            session.transition_to(ConversationState.CLIENT_SHOW_RESULTS)

            if len(results) == 0:
                return client_messages.CLIENT_NO_RESULTS

            search_date = session.get_temp('search_date')
            formatted = client_service.format_search_results_with_slots(
                professionals=results,
                date_str=search_date,
                show_max_slots=3
            )
            return formatted
        
        # ==========================================
        # OPCIÓN 3: DINÁMICA (Ver citas O Info)
        # ==========================================
        elif message == '3':
            if has_appointments:
                # TIENE CITAS → Opción 3 = Ver mis citas
                print(f"[CLIENT] Ver mis citas: {session.phone_number}")
                session.clear_temp()
                session.transition_to(ConversationState.CLIENT_VIEW_APPOINTMENTS)
                return self.handle_client_view_appointments(session, '')
            else:
                # NO TIENE CITAS → Opción 3 = Información del centro
                print(f"[CLIENT] Info del centro: {session.phone_number}")
                info_message = user_service.get_center_info()
                return info_message

        # ==========================================
        # OPCIÓN 4: SOLO SI TIENE CITAS
        # ==========================================
        elif message == '4':
            if has_appointments:
                # TIENE CITAS → Opción 4 = Información del centro
                print(f"[CLIENT] Info del centro: {session.phone_number}")
                info_message = user_service.get_center_info()
                return info_message
            else:
                # NO TIENE CITAS → Opción 4 no existe, es inválida
                invalid_msg = common_messages.INVALID_OPTION + "\n\n"
                welcome_msg = user_service.generate_welcome_message({
                    'user_type': 'new',
                    'name': None,
                    'is_registered': False,
                    'has_pending_appointments': False,
                    'pending_appointments': [],
                    'profile': None,
                    'phone_number': session.phone_number  # ⭐ IMPORTANTE
                })
                return invalid_msg + welcome_msg

        # ==========================================
        # OPCIÓN 0: Volver al inicio
        # ==========================================
        elif message == '0':
            welcome_msg = user_service.generate_welcome_message({
                'user_type': 'new',
                'name': None,
                'is_registered': False,
                'has_pending_appointments': False,
                'pending_appointments': [],
                'profile': None,
                'phone_number': session.phone_number  # ⭐ IMPORTANTE
            })
            return welcome_msg

        # ==========================================
        # OPCIÓN INVÁLIDA
        # ==========================================
        else:
            invalid_msg = common_messages.INVALID_OPTION + "\n\n"
            welcome_msg = user_service.generate_welcome_message({
                'user_type': 'new',
                'name': None,
                'is_registered': False,
                'has_pending_appointments': False,
                'pending_appointments': [],
                'profile': None,
                'phone_number': session.phone_number  # ⭐ IMPORTANTE
            })
            return invalid_msg + welcome_msg


    def generate_welcome_message(self, user_info: Dict) -> str:
        """
        Genera mensaje de bienvenida personalizado.
        
        Lógica simple:
        - Verificar si tiene citas agendadas
        - Mostrar menú de 3 opciones (sin citas) o 4 opciones (con citas)
        
        Args:
            user_info: Debe incluir 'phone_number' para verificar citas
        
        Returns:
            Mensaje de bienvenida con menú dinámico
        """
        from src.database.database import db
        from datetime import datetime
        
        name = user_info.get('name')
        phone_number = user_info.get('phone_number', '')
        
        # ==========================================
        # 1. VERIFICAR CITAS ACTIVAS
        # ==========================================
        today = datetime.now().strftime("%Y-%m-%d")
        appointments = db.get_appointments_by_client(
            client_phone=phone_number,
            from_date=today
        )
        
        # Filtrar solo citas activas (pendientes o confirmadas)
        active_appointments = [
            apt for apt in appointments
            if apt['status'] in ['pendiente_confirmacion', 'confirmada']
        ]
        
        has_appointments = len(active_appointments) > 0
        count = len(active_appointments)
        
        # ==========================================
        # 2. CONSTRUIR MENSAJE
        # ==========================================
        
        # Saludo personalizado o genérico
        if name:
            greeting = f"¡Hola {name}! 👋\n\n"
        else:
            greeting = f"👋 ¡Bienvenido/a a {DomainConfig.BUSINESS_NAME}!\n\n"
        
        # Mensaje base
        message = greeting
        message += f"{DomainConfig.WELCOME_TAGLINE}\n\n"
        message += "¿Qué querés hacer?\n\n"
        
        # ==========================================
        # 3. MENÚ DINÁMICO
        # ==========================================
        
        # Opción 1: Siempre presente
        message += f"1️⃣ Buscar {DomainConfig.PROFESSIONAL_TITLE_LOWER}\n"
        message += f"   Búsqueda asistida paso a paso\n\n"
        
        # Opción 2: Siempre presente
        message += f"2️⃣ Ver disponibles mañana\n"
        message += f"   {DomainConfig.PROFESSIONAL_TITLE_PLURAL} con horarios libres\n\n"
        
        # Opción 3 y 4: Dinámicas según citas
        if has_appointments:
            # TIENE CITAS → 4 opciones
            message += f"3️⃣ Ver mis citas programadas\n"
            message += f"   Gestionar tus {count} cita{'s' if count > 1 else ''}\n\n"
            
            message += f"4️⃣ Información del centro\n"
            message += f"   Conocer más sobre {DomainConfig.BUSINESS_NAME}\n\n"
        else:
            # NO TIENE CITAS → 3 opciones
            message += f"3️⃣ Información del centro\n"
            message += f"   Conocer más sobre {DomainConfig.BUSINESS_NAME}\n\n"
        
        message += "Responde con el número de opción."
        
        return message
    
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
        session.set_temp('current_search_id', search_id)

        # Store results
        session.set_temp('search_results', results)

        # Format and return
        if len(results) == 0:
            return client_messages.CLIENT_NO_RESULTS

        # Format results with available slots


        search_date = session.get_temp('search_date')


        formatted = client_service.format_search_results_with_slots(


            professionals=results,


            date_str=search_date,


            show_max_slots=3


        )
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

        session.set_temp('fecha', date_obj)
        session.set_temp('fecha_str', message)
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
            session.set_temp('time_range', f"{time_start}-{time_end}")
            session.set_temp('time_start', time_start)
            session.set_temp('time_end', time_end)
        else:
            session.set_temp('hora', time_start)

        # Search professionals
        # Determinar time_preference basado en el rango seleccionado
        time_preference = None
        if time_range:
            if time_start == "08:00" and time_end == "13:00":
                time_preference = "mañana"
            elif time_start == "13:00" and time_end == "20:00":
                time_preference = "tarde"
            # Si es cualquier horario (08:00-20:00), no especificamos preference
        
        # Buscar profesionales con disponibilidad
        results = client_service.search_professionals_by_filters(
            date_str=fecha.strftime("%Y-%m-%d"),
            time_preference=time_preference if time_range else None,
            limit=10
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
        session.set_temp('current_search_id', search_id)

        # Store results
        session.set_temp('search_results', results)

        # Format and return
        # Format results with available slots

        search_date = session.get_temp('search_date')

        formatted = client_service.format_search_results_with_slots(

            professionals=results,

            date_str=search_date,

            show_max_slots=3

        )
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
            session.set_temp('prepaga', True)
        elif message == '2':
            session.set_temp('prepaga', False)
        elif message == '3':
            session.set_temp('prepaga', None)
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
            session.set_temp('sexo', 'm')
        elif message == '2':
            session.set_temp('sexo', 'f')
        elif message == '3':
            session.set_temp('sexo', None)
        else:
            return common_messages.INVALID_OPTION + "\n\n" + client_messages.CLIENT_ASK_SEXO

        # TODO: Search database
        print(f"[DB] TODO: Search by sexo - {session.get_temp('sexo')}")

        session.transition_to(ConversationState.CLIENT_SHOW_RESULTS)
        return "🔍 Buscando...\n\n📋 Próximamente mostraré resultados.\n\nEscribe 'menu' para volver."

    # ==========================================
    # MULTI-FILTRO (Búsqueda avanzada) - SISTEMA MODULAR
    # ==========================================

    def format_multifilter_menu(self, session: SessionData) -> str:
        """
        Genera menú multi-filtro usando FilterManager.
        
        Esta versión reemplaza el menú hardcodeado anterior.
        Ahora el menú se genera dinámicamente desde la configuración.
        
        Returns:
            Menú formateado con filtros habilitados y checkmarks en activos
        """
        print(f"\n{'='*60}")
        print(f"📋 DEBUG format_multifilter_menu")
        print(f"{'='*60}")
        print(f"📞 Phone: {session.phone_number}")
        
        # Obtener filtros activos desde la sesión
        active_filters = session.get_temp('filters', {})
        print(f"📊 Active filters from session: {active_filters}")
        print(f"📊 Number of active filters: {len(active_filters)}")
        
        if active_filters:
            print(f"📝 Filter details:")
            for key, value in active_filters.items():
                display = value.get('display', 'N/A') if isinstance(value, dict) else str(value)
                print(f"   • {key}: {display}")
        else:
            print(f"⚠️ No active filters found in session")
        
        # Usar FilterManager para generar el menú
        filter_manager = FilterManager()
        print(f"✅ FilterManager created")
        
        menu = filter_manager.generate_menu(active_filters)
        print(f"✅ Menu generated ({len(menu)} chars)")
        print(f"{'='*60}\n")
        
        return menu

    
    def handle_client_multifilter_menu(self, session: SessionData, message: str) -> str:
        """
        Maneja el menú multi-filtro usando el sistema modular.
        
        Permite al usuario:
        - Seleccionar filtros dinámicamente (según configuración)
        - Ver filtros activos con checkmarks
        - Buscar cuando esté listo (opción 9)
        - Volver al menú principal (opción 0)
        
        Este handler REEMPLAZA la versión anterior que tenía opciones hardcodeadas.
        """
        filter_manager = FilterManager()
        
        # Mostrar menú inicial si es start
        if message == 'start':
            return self.format_multifilter_menu(session)
        
        # ===== OPCIÓN 9: BUSCAR =====
        if message == '9':
            active_filters = session.get_temp('filters', {})
            
            # Validar que haya al menos un filtro
            if not active_filters:
                return "⚠️ No has seleccionado ningún filtro.\n\n" + self.format_multifilter_menu(session)
            
            # Validar filtros obligatorios
            is_valid, error_msg = filter_manager.validate_required_filters(active_filters)
            
            if not is_valid:
                return error_msg + "\n\n" + self.format_multifilter_menu(session)
            
            # Convertir filtros a parámetros de BD
            db_params = filter_manager.convert_to_db_params(active_filters)
            
            # ⭐ NUEVO: Guardar date_str y time_preference en sesión
            if 'date_str' in db_params:
                session.set_temp('search_date', db_params['date_str'])
            if 'time_preference' in db_params:
                session.set_temp('time_preference', db_params['time_preference'])
            
            # Buscar profesionales
            results = client_service.search_professionals_by_filters(
                **db_params, 
                limit=10
            )
            
            # ⭐ NUEVO: Log de búsqueda (solo valores display, JSON serializable)
            search_params_for_log = {
                key: value.get('display', str(value)) if isinstance(value, dict) else value
                for key, value in active_filters.items()
            }
            
            search_id = analytics_service.log_search(
                client_phone=session.phone_number,
                search_type='multifilter',
                search_params=search_params_for_log,
                result_count=len(results),
                session_id=session.phone_number
            )
            session.set_temp('current_search_id', search_id)
            
            # Guardar resultados
            session.set_temp('search_results', results)
            session.transition_to(ConversationState.CLIENT_SHOW_RESULTS)
            
            # Formatear y retornar
            if len(results) == 0:
                return client_messages.CLIENT_NO_RESULTS
            
            # Format results with available slots
            search_date = session.get_temp('search_date')
            
            formatted = client_service.format_search_results_with_slots(
                professionals=results,
                date_str=search_date,
                show_max_slots=3
            )
            return formatted
        
        # ===== OPCIÓN 0: VOLVER =====
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
        
        # ===== OPCIONES 1-N: SELECCIONAR FILTRO =====
        else:
            try:
                option_num = int(message)
                filter_obj = filter_manager.get_filter_by_menu_number(option_num)
                
                if not filter_obj:
                    return "⚠️ Opción inválida\n\n" + self.format_multifilter_menu(session)
                
                # Guardar filtro actual en temp
                session.set_temp('current_filter_type', filter_obj.filter_type.value)
                
                # Transicionar a estado de input de filtro
                session.transition_to(ConversationState.CLIENT_FILTER_INPUT)
                
                # Mostrar prompt del filtro seleccionado
                return filter_obj.get_input_prompt(session.get_temp_all())
            
            except ValueError:
                return "⚠️ Opción inválida\n\n" + self.format_multifilter_menu(session)


    def handle_client_filter_input(self, session: SessionData, message: str) -> str:
        """
        Maneja el input genérico de CUALQUIER filtro.
        
        Este handler ÚNICO reemplaza a todos los handle_client_multifilter_* individuales:
        - handle_client_multifilter_zona()
        - handle_client_multifilter_fecha()
        - handle_client_multifilter_hora()
        - handle_client_multifilter_prepaga()
        - handle_client_multifilter_sexo()
        - handle_client_multifilter_especialidad()
        
        Flujo:
        1. Obtiene el filtro actual desde session.temp
        2. Valida el input usando el método del filtro
        3. Procesa y guarda el filtro
        4. Vuelve al menú de filtros
        """
        print(f"\n{'='*60}")
        print(f"🔍 DEBUG handle_client_filter_input")
        print(f"{'='*60}")
        print(f"📞 Phone: {session.phone_number}")
        print(f"💬 Message: '{message}'")
        print(f"📊 Current State: {session.state}")
        
        filter_manager = FilterManager()
        
        # Obtener tipo de filtro actual desde session
        filter_type_str = session.get_temp('current_filter_type')
        print(f"🎯 Current filter type from session: '{filter_type_str}'")
        
        # Mostrar TODO el contenido de temp
        all_temp = session.get_temp_all()
        print(f"📦 ALL session.temp data: {all_temp}")
        
        if not filter_type_str:
            # Error: no hay filtro en progreso
            print(f"❌ ERROR: No current_filter_type in session!")
            print(f"{'='*60}\n")
            session.transition_to(ConversationState.CLIENT_MULTIFILTER_MENU)
            return self.format_multifilter_menu(session)
        
        # Convertir string a FilterType enum
        try:
            filter_type = FilterType(filter_type_str)
            print(f"✅ Filter type converted: {filter_type}")
        except Exception as e:
            print(f"❌ ERROR converting filter type: {e}")
            print(f"{'='*60}\n")
            session.transition_to(ConversationState.CLIENT_MULTIFILTER_MENU)
            return self.format_multifilter_menu(session)
        
        filter_obj = filter_manager.get_filter(filter_type)
        print(f"🔧 Filter object: {filter_obj.__class__.__name__ if filter_obj else 'None'}")
        
        if not filter_obj:
            # Error: filtro no existe
            print(f"❌ ERROR: Filter object not found for type {filter_type}!")
            print(f"{'='*60}\n")
            session.transition_to(ConversationState.CLIENT_MULTIFILTER_MENU)
            return self.format_multifilter_menu(session)
        
        # ===== OPCIÓN 0: VOLVER SIN GUARDAR =====
        if message == '0':
            print(f"↩️ User pressed 0 (back)")
            session.remove_temp('current_filter_type')
            session.transition_to(ConversationState.CLIENT_MULTIFILTER_MENU)
            print(f"{'='*60}\n")
            return self.format_multifilter_menu(session)
        
        # ===== VALIDAR INPUT =====
        print(f"\n🔍 Validating input...")
        session_data = session.get_temp_all()
        is_valid, error_msg = filter_obj.validate_input(message, session_data)
        print(f"✅ Validation result: {is_valid}")
        if not is_valid:
            print(f"❌ Validation error: {error_msg}")
            print(f"{'='*60}\n")
        
        if not is_valid:
            # Input inválido - mostrar error y volver a preguntar
            return f"{error_msg}\n\n{filter_obj.get_input_prompt(session_data)}"
        
        # ===== PROCESAR INPUT VÁLIDO =====
        print(f"\n⚙️ Processing input...")
        processed_filter = filter_obj.process_input(message, session_data)
        print(f"📦 Processed filter result: {processed_filter}")
        
        # ===== GUARDAR FILTRO =====
        print(f"\n💾 Saving filter...")
        filters = session.get_temp('filters', {})
        print(f"📊 Current filters BEFORE save: {filters}")
        print(f"📊 Filter count BEFORE: {len(filters)}")
        
        # Si el filtro tiene flag 'remove', eliminarlo en lugar de guardarlo
        if processed_filter.get('remove'):
            print(f"🗑️ Filter marked for removal")
            if filter_type.value in filters:
                del filters[filter_type.value]
            filter_name = f"{processed_filter.get('display', filter_obj.display_name)} (filtro removido)"
        else:
            # Guardar filtro normalmente
            print(f"💾 Saving filter with key: '{filter_type.value}'")
            filters[filter_type.value] = processed_filter
            filter_name = processed_filter.get('display', filter_obj.display_name)
        
        print(f"📊 Filters AFTER update: {filters}")
        print(f"📊 Filter count AFTER: {len(filters)}")
        
        # Guardar en sesión
        print(f"💾 Calling session.set_temp('filters', ...)")
        session.set_temp('filters', filters)
        
        # Verificar que se guardó
        print(f"✅ Verifying storage...")
        verify_filters = session.get_temp('filters', {})
        print(f"✅ Filters retrieved from session: {verify_filters}")
        print(f"✅ Filter count retrieved: {len(verify_filters)}")
        
        if len(verify_filters) != len(filters):
            print(f"⚠️ WARNING: Filter count mismatch!")
            print(f"   Expected: {len(filters)}, Got: {len(verify_filters)}")
        
        # ===== LIMPIAR TEMP Y VOLVER AL MENÚ =====
        print(f"\n🧹 Cleaning up...")
        session.remove_temp('current_filter_type')
        session.transition_to(ConversationState.CLIENT_MULTIFILTER_MENU)
        
        print(f"{'='*60}\n")
        
        # Mostrar confirmación + menú actualizado
        return client_messages.CLIENT_MULTIFILTER_ADDED.format(
            filter_name=filter_name,
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
        session.set_temp('filters', filters)

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
        session.set_temp('current_search_id', search_id)

        # Store results
        session.set_temp('search_results', results)

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
        # Format results with available slots

        search_date = session.get_temp('search_date')

        formatted_results = client_service.format_search_results_with_slots(

            professionals=results,

            date_str=search_date,

            show_max_slots=3

        )

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
        Maneja vista de resultados de búsqueda.
        ACTUALIZADO: Ahora muestra slots disponibles por profesional.

        El usuario puede:
        - Seleccionar un número para ver detalle del profesional
        - Volver al menú principal con '0'
        """
        # Check for back command
        if message == '0':
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return client_messages.CLIENT_MAIN_MENU

        # Get results from session
        results = session.get_temp('search_results', [])
        search_date = session.get_temp('search_date')  # Fecha de búsqueda

        # Si NO hay resultados, mostrar mensaje de ayuda
        if not results or len(results) == 0:
            if message == '1':
                # Modificar filtros - volver al menú de filtros
                session.transition_to(ConversationState.CLIENT_MULTIFILTER_MENU)
                return self.format_multifilter_menu(session)
            
            elif message == '2':
                # Ver todos los profesionales (sin filtros)
                print("[CLIENT] User requested: Show all professionals (no filters)")
                
                # Buscar SIN filtros pero CON fecha si se había especificado
                all_results = client_service.search_professionals_by_filters(
                    date_str=search_date,
                    limit=10
                )
                
                # Log search
                search_id = analytics_service.log_search(
                    client_phone=session.phone_number,
                    search_type='all',
                    search_params={'date': search_date} if search_date else {},
                    result_count=len(all_results),
                    session_id=session.phone_number
                )
                session.set_temp('current_search_id', search_id)
                session.set_temp('search_results', all_results)
                
                # Format with slots if date exists
                if len(all_results) == 0:
                    return "😔 No hay profesionales disponibles.\n\nEscribe '0' para volver al menú."
                
                # ⭐ NUEVO: Usar formato con slots
                formatted = client_service.format_search_results_with_slots(
                    professionals=all_results,
                    date_str=search_date,
                    show_max_slots=3
                )
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
        session.set_temp('selected_professional', professional)

        # Log contact
        search_id = session.get_temp('current_search_id')
        if search_id:
            analytics_service.log_contact(
                search_id=search_id,
                professional_phone=professional['phone'],
                result_position=selection
            )

        # ⭐ NUEVO: Transición a detalle con slots
        session.transition_to(ConversationState.CLIENT_VIEW_DETAIL_WITH_BOOKING)
        
        # ⭐ NUEVO: Obtener time_preference de la sesión
        search_date = session.get_temp('search_date')
        time_preference = session.get_temp('time_preference')
        
        # Usar el nuevo formatter que muestra todos los slots
        return client_service.format_professional_detail_with_slots(
            professional=professional,
            date_str=search_date,
            time_preference=time_preference
        )


    def handle_client_view_detail(self, session: SessionData, message: str) -> str:
        """
        Maneja vista de detalle de profesional.
        ACTUALIZADO: Ahora permite seleccionar slot de horario para reservar.
        
        Estados posibles:
        - CLIENT_VIEW_DETAIL: Solo info, sin slots (búsqueda sin fecha)
        - CLIENT_VIEW_DETAIL_WITH_BOOKING: Info + slots (búsqueda con fecha)
        """
        # Check for back command
        if message == '0':
            # Go back to results
            results = session.get_temp('search_results', [])
            if results:
                search_date = session.get_temp('search_date')
                formatted = client_service.format_search_results_with_slots(
                    professionals=results,
                    date_str=search_date,
                    show_max_slots=3
                )
                session.transition_to(ConversationState.CLIENT_SHOW_RESULTS)
                return formatted
            else:
                session.clear_temp()
                session.transition_to(ConversationState.CLIENT_MAIN_MENU)
                return client_messages.CLIENT_MAIN_MENU

        # ⭐ NUEVO: Manejar selección de horario
        professional = session.get_temp('selected_professional')
        
        if not professional:
            return "⚠️ Error: No hay profesional seleccionado.\n\nEscribe 'menu' para volver."
        
        # Si el profesional tiene slots disponibles, el usuario puede seleccionar uno
        available_slots = professional.get('available_slots', [])
        
        if available_slots:
            try:
                slot_selection = int(message)
            except ValueError:
                return "⚠️ Por favor, ingresá un número de horario válido.\n\nEscribe '0' para volver."
            
            # Validate slot selection
            if slot_selection < 1 or slot_selection > len(available_slots):
                return f"⚠️ Número inválido. Elegí entre 1 y {len(available_slots)}.\n\nEscribe '0' para volver."
            
            # ⭐ Usuario seleccionó un horario → Iniciar flujo de reserva
            selected_slot = available_slots[slot_selection - 1]
            
            # Guardar slot seleccionado
            session.set_temp('selected_slot', selected_slot)
            
            # Transición a confirmación de datos
            session.transition_to(ConversationState.CLIENT_BOOKING_CONFIRM_NAME)
            
            # Solicitar nombre del cliente
            return """📝 *Confirmación de Turno*

    Para confirmar tu turno necesito algunos datos:

    ¿Cuál es tu *nombre completo*?

    _(Escribe '0' para cancelar)_"""
        
        # Si no hay slots, mostrar solo opción de contacto
        elif message == '1':
            # Contact professional
            contact_message = f"📱 *Contacto:*\n\n"
            contact_message += f"Teléfono: {professional['phone']}\n"
            if professional.get('email'):
                contact_message += f"Email: {professional['email']}\n"
            contact_message += f"\n💬 Podés escribirle directamente por WhatsApp.\n"
            contact_message += f"\nEscribe '0' para volver o 'menu' para ir al menú principal."
            
            return contact_message
        
        else:
            return "⚠️ Opción inválida.\n\nEscribe '0' para volver."

    # ==========================================
    # MIS CITAS (Appointments Management)
    # ==========================================

    def handle_client_view_appointments(self, session: SessionData, message: str) -> str:
        """
        Maneja vista de lista de citas del cliente.

        Muestra todas las citas activas (pendientes y confirmadas) del cliente.
        
        ⭐ NUEVA FUNCIONALIDAD: Sincroniza citas desde Google Calendar antes de mostrar.

        Args:
            message: '' = carga inicial, 'número' = selección de cita, '0' = volver
        """
        from datetime import datetime, timedelta

        # ==========================================
        # 1. VERIFICAR SI QUIERE VOLVER
        # ==========================================
        if message == '0':
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            
            # Regenerar menú con phone_number
            from src.services.user_service import user_service
            welcome_msg = user_service.generate_welcome_message({
                'user_type': 'new',
                'name': None,
                'is_registered': False,
                'has_pending_appointments': False,
                'pending_appointments': [],
                'profile': None,
                'phone_number': session.phone_number
            })
            return welcome_msg

        # ==========================================
        # 2. OBTENER CITAS DESDE LA BD
        # ==========================================
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
            # MANEJAR RESPUESTA DEL USUARIO
            if message == '1':
                # Usuario quiere buscar
                session.transition_to(ConversationState.CLIENT_MULTIFILTER_MENU)
                return self.format_multifilter_menu(session)
            
            elif message == '0':
                # Ya manejado arriba, pero por si acaso
                session.clear_temp()
                session.transition_to(ConversationState.CLIENT_MAIN_MENU)
                from src.services.user_service import user_service
                welcome_msg = user_service.generate_welcome_message({
                    'user_type': 'new',
                    'name': None,
                    'is_registered': False,
                    'has_pending_appointments': False,
                    'pending_appointments': [],
                    'profile': None,
                    'phone_number': session.phone_number
                })
                return welcome_msg
            
            # Mostrar mensaje con opciones
            return appointment_messages.CLIENT_NO_APPOINTMENTS

        # ==========================================
        # 3. ⭐ SINCRONIZAR DESDE GOOGLE CALENDAR
        # ==========================================
        # Solo sincronizar citas próximas (próximos 7 días) para performance
        
        print(f"[CLIENT] 🔄 Sincronizando citas desde Google Calendar...")
        
        try:
            from src.integrations.appointment_calendar_service import AppointmentCalendarService
            calendar_service = AppointmentCalendarService(db)
            
            # Calcular fecha límite (7 días desde hoy)
            today_dt = datetime.now()
            limit_date = (today_dt + timedelta(days=7)).strftime("%Y-%m-%d")
            
            # Filtrar citas próximas que tengan google_event_id
            appointments_to_sync = [
                apt for apt in active_appointments
                if apt.get('google_event_id') and apt['appointment_date'] <= limit_date
            ]
            
            if appointments_to_sync:
                print(f"[CLIENT] 🔄 Sincronizando {len(appointments_to_sync)} citas próximas...")
                
                # Sincronizar cada cita
                synced_count = 0
                for apt in appointments_to_sync:
                    try:
                        success = calendar_service.sync_appointment_from_google(apt['id'])
                        if success:
                            synced_count += 1
                    except Exception as e:
                        print(f"[CLIENT] ⚠️ Error sincronizando cita #{apt['id']}: {e}")
                
                print(f"[CLIENT] ✅ {synced_count}/{len(appointments_to_sync)} citas sincronizadas")
                
                # ==========================================
                # 4. RE-CONSULTAR BD DESPUÉS DE SINCRONIZAR
                # ==========================================
                # Ahora que sincronizamos, volver a leer de BD para obtener datos actualizados
                appointments = db.get_appointments_by_client(
                    client_phone=session.phone_number,
                    from_date=today
                )
                
                # Re-filtrar citas activas
                active_appointments = [
                    apt for apt in appointments
                    if apt['status'] in ['pendiente_confirmacion', 'confirmada']
                ]
                
                # Verificar de nuevo si hay citas (por si se cancelaron en Google)
                if not active_appointments:
                    return appointment_messages.CLIENT_NO_APPOINTMENTS
            else:
                print(f"[CLIENT] ℹ️ No hay citas próximas para sincronizar")
        
        except Exception as e:
            # Si falla la sincronización, continuar con datos locales
            print(f"[CLIENT] ⚠️ Error en sincronización, usando datos locales: {e}")
            import traceback
            traceback.print_exc()

        # ==========================================
        # 5. GUARDAR LISTA EN TEMP_DATA
        # ==========================================
        session.set_temp('appointment_list', active_appointments)

        # ==========================================
        # 6. SI SELECCIONÓ UN NÚMERO, IR A DETALLE
        # ==========================================
        if message and message.isdigit() and int(message) > 0:
            idx = int(message) - 1
            
            # Validar que el índice esté en rango
            if 0 <= idx < len(active_appointments):
                # Guardar índice seleccionado
                session.set_temp('selected_appointment_index', idx)
                
                # Transicionar a detalle
                session.transition_to(ConversationState.CLIENT_APPOINTMENT_DETAIL)
                
                # Llamar al handler de detalle
                return self.handle_client_appointment_detail(session, message)
            else:
                # Número fuera de rango
                return f"⚠️ Número inválido. Elige entre 1 y {len(active_appointments)} o *0* para volver."

        # ==========================================
        # 7. MOSTRAR LISTA DE CITAS
        # ==========================================
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
                f"{idx}️⃣ {status_emoji} {date_str} - {apt['start']}hs\n"
                f"   {apt['professional_name']}\n"
                f"   {status_text}"
            )

        formatted_list = "\n\n".join(appointments_list)

        return appointment_messages.CLIENT_VIEW_APPOINTMENTS.format(
            appointments_list=formatted_list
        )

    def handle_client_appointment_detail(self, session: SessionData, message: str) -> str:
        """
        Maneja detalle de una cita específica y sus opciones.

        Distingue entre:
        - Seleccionar cita #N desde la lista
        - Ejecutar opciones (1=Reprogramar, 2=Cancelar) desde el detalle
        
        Args:
            message: Número de cita, opción seleccionada, o '0' para volver
        """
        from datetime import datetime
        
        # ==========================================
        # OPCIÓN 0: VOLVER
        # ==========================================
        if message == '0':
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            
            # Regenerar menú con phone_number
            from src.services.user_service import user_service
            welcome_msg = user_service.generate_welcome_message({
                'user_type': 'new',
                'name': None,
                'is_registered': False,
                'has_pending_appointments': False,
                'pending_appointments': [],
                'profile': None,
                'phone_number': session.phone_number
            })
            return welcome_msg
        
        # ==========================================
        # VERIFICAR SI YA ESTAMOS EN DETALLE
        # ==========================================
        # Si appointment_id existe, significa que ya mostramos el detalle
        # y el usuario está eligiendo una OPCIÓN (1=Reprogramar, 2=Cancelar)
        appointment_id = session.get_temp('appointment_id')
        
        if appointment_id:
            # ✅ YA ESTAMOS EN DETALLE → message es una OPCIÓN
            
            # OPCIÓN 1: REPROGRAMAR
            if message == '1':
                print(f"[CLIENT] Iniciando reprogramación: {session.phone_number}")
                
                # Transicionar a reprogramación
                session.transition_to(ConversationState.CLIENT_RESCHEDULE_APPOINTMENT)
                
                # Llamar al handler de reprogramación
                return self.handle_client_reschedule_appointment(session, '1')
            
            # OPCIÓN 2: CANCELAR
            elif message == '2':
                print(f"[CLIENT] Iniciando cancelación: {session.phone_number}")
                
                # Transicionar a cancelación
                session.transition_to(ConversationState.CLIENT_CANCEL_APPOINTMENT)
                
                # Llamar al handler de cancelación
                return self.handle_client_cancel_appointment(session, '1')
            
            else:
                # Opción inválida desde el detalle
                return "⚠️ Opción inválida.\n\n1️⃣ Reprogramar cita\n2️⃣ Cancelar cita\n0️⃣ Volver al menú"
        
        # ==========================================
        # NO ESTAMOS EN DETALLE → SELECCIONAR CITA
        # ==========================================
        # El usuario está en la LISTA y está seleccionando una cita
        
        # Recuperar lista de citas del temp_data
        active_appointments = session.get_temp('appointment_list', [])
        
        if not active_appointments:
            # Si no hay lista guardada, volver a cargarla
            session.transition_to(ConversationState.CLIENT_VIEW_APPOINTMENTS)
            return self.handle_client_view_appointments(session, message)
        
        # Validar que message sea un número
        try:
            idx = int(message) - 1  # Convertir a índice (1-indexed → 0-indexed)
        except ValueError:
            return "⚠️ Opción inválida. Envía el número de la cita o *0* para volver."
        
        # Validar que el índice esté en rango
        if not (0 <= idx < len(active_appointments)):
            return f"⚠️ Número inválido. Elige entre 1 y {len(active_appointments)} o *0* para volver."
        
        # Obtener la cita seleccionada
        selected_apt = active_appointments[idx]
        
        # Guardar datos de la cita en temp_data para siguientes pasos
        session.set_temp('appointment_id', selected_apt['id'])
        session.set_temp('selected_appointment_number', idx + 1)  # 1-indexed para mostrar
        session.set_temp('professional_phone', selected_apt['professional_phone'])
        session.set_temp('professional_name', selected_apt.get('professional_name', 'Profesional'))
        session.set_temp('original_date', selected_apt['appointment_date'])
        session.set_temp('original_start', selected_apt['start'])
        session.set_temp('original_end', selected_apt['end'])
        
        # Mantener en estado de detalle
        session.transition_to(ConversationState.CLIENT_APPOINTMENT_DETAIL)
        
        # Formatear y mostrar detalle completo
        return self._format_appointment_detail(session, selected_apt)
    
    def handle_client_cancel_appointment(self, session: SessionData, message: str) -> str:
        """
        Maneja confirmación de cancelación de cita.

        Valida que se pueda cancelar y pide confirmación.
        """
        from datetime import datetime, timedelta

        # ==========================================
        # VERIFICAR SI VENIMOS DE UN ERROR PREVIO
        # ==========================================
        # Si mostramos un error (no se puede cancelar) y el usuario presiona 0
        if message == '0':
            # Limpiar cualquier flag de error
            session.set_temp('cancel_error_shown', False)
            
            # Volver a la lista de citas
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_VIEW_APPOINTMENTS)
            return self.handle_client_view_appointments(session, '')

        # ==========================================
        # VALIDACIONES INICIALES
        # ==========================================
        appointment_id = session.get_temp('appointment_id')

        if not appointment_id:
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            
            from src.services.user_service import user_service
            welcome_msg = user_service.generate_welcome_message({
                'user_type': 'new',
                'name': None,
                'is_registered': False,
                'has_pending_appointments': False,
                'pending_appointments': [],
                'profile': None,
                'phone_number': session.phone_number
            })
            return welcome_msg

        # Obtener datos de la cita
        apt = db.get_appointment(appointment_id)

        if not apt:
            # Error al cargar - pero permitir volver con 0
            session.set_temp('cancel_error_shown', True)
            return "❌ Error al cargar la cita.\n\n_Escribe *0* para volver_"

        # ==========================================
        # VALIDAR ESTADO DE LA CITA
        # ==========================================
        
        # Validar que no esté ya cancelada
        if apt['status'] in ['cancelada_cliente', 'cancelada_profesional']:
            session.set_temp('cancel_error_shown', True)
            return appointment_messages.CLIENT_APPOINTMENT_ALREADY_CANCELLED + "\n\n_Escribe *0* para volver_"

        # Validar que no esté completada
        if apt['status'] == 'completada':
            session.set_temp('cancel_error_shown', True)
            return "❌ No puedes cancelar una cita que ya finalizó.\n\n_Escribe *0* para volver_"

        # ==========================================
        # VALIDAR TIEMPO LÍMITE (24 HORAS)
        # ==========================================
        
        # Calcular horas hasta la cita
        apt_datetime = datetime.strptime(
            f"{apt['appointment_date']} {apt['start']}",
            "%Y-%m-%d %H:%M"
        )
        now = datetime.now()
        hours_until = (apt_datetime - now).total_seconds() / 3600

        # Validar tiempo mínimo (24 horas por defecto)
        CANCELLATION_HOURS_LIMIT = 24

        if hours_until < CANCELLATION_HOURS_LIMIT:
            # Muy tarde para cancelar
            # ✅ Guardar flag para permitir volver
            session.set_temp('cancel_error_shown', True)
            
            return appointment_messages.CLIENT_CANCEL_TOO_LATE.format(
                hours_until=int(hours_until),
                professional_phone=apt['professional_phone']
            )

        # ==========================================
        # MOSTRAR CONFIRMACIÓN
        # ==========================================
        
        # Si es primera vez (viene desde detalle), mostrar confirmación
        if message == '1':
            # Limpiar flag de error (si existía)
            session.set_temp('cancel_error_shown', False)
            
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
                time=apt['start'],
                professional_name=apt['professional_name'],
                policy_info=policy_info
            )

        # Si llegó aquí sin ser '1', es inválido
        return "⚠️ Opción inválida.\n\n_Escribe *1* para cancelar o *0* para volver_"

    def handle_client_cancel_reason(self, session: SessionData, message: str) -> str:
        """
        Maneja motivo de cancelación y ejecuta la cancelación.

        El motivo es opcional.
        
        ✅ VERSIÓN CON LOGS DETALLADOS PARA DEBUGGING
        """
        print("=" * 70)
        print("[CANCEL_HANDLER] 🚀 Iniciando handle_client_cancel_reason")
        print("=" * 70)

        appointment_id = session.get_temp('appointment_id')
        print(f"[CANCEL_HANDLER] 📋 Appointment ID: {appointment_id}")

        if not appointment_id:
            print("[CANCEL_HANDLER] ❌ No hay appointment_id en session")
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

        print(f"[CANCEL_HANDLER] 💬 Motivo: {reason or 'Sin motivo'}")

        # ==========================================
        # ⭐ CANCELAR EN GOOGLE CALENDAR Y BD
        # ==========================================
        try:
            print("[CANCEL_HANDLER] 📦 Importando AppointmentCalendarService...")
            from src.integrations.appointment_calendar_service import AppointmentCalendarService
            print("[CANCEL_HANDLER] ✅ Import exitoso")
            
            print(f"[CANCEL_HANDLER] 🔄 Creando instancia de AppointmentCalendarService...")
            calendar_service = AppointmentCalendarService(db)
            print("[CANCEL_HANDLER] ✅ Instancia creada")
            
            print(f"[CANCEL_HANDLER] 🎯 Llamando a calendar_service.cancel_appointment...")
            print(f"[CANCEL_HANDLER]    appointment_id: {appointment_id}")
            print(f"[CANCEL_HANDLER]    cancellation_reason: {reason or 'Cancelado por el cliente'}")
            
            success = calendar_service.cancel_appointment(
                appointment_id=appointment_id,
                cancellation_reason=reason or "Cancelado por el cliente"
            )
            
            print(f"[CANCEL_HANDLER] 📊 Resultado de cancel_appointment: {success}")
            
            if not success:
                print(f"[CANCEL_HANDLER] ❌ cancel_appointment retornó False")
                return "❌ Error al cancelar la cita. Intenta nuevamente.\n\n_Escribe *0* para volver_"
            
            print(f"[CANCEL_HANDLER] ✅ Cita cancelada exitosamente")
            
        except ImportError as e:
            print(f"[CANCEL_HANDLER] ❌ Error de import: {e}")
            import traceback
            traceback.print_exc()
            
            # Fallback a BD local
            print(f"[CANCEL_HANDLER] ⚠️ FALLBACK: Usando db.update_appointment_status")
            success = db.update_appointment_status(
                appointment_id=appointment_id,
                new_status='cancelada_cliente',
                changed_by='client',
                reason=reason
            )
            
            if not success:
                return "❌ Error al cancelar la cita. Intenta nuevamente.\n\n_Escribe *0* para volver_"
        
        except Exception as e:
            print(f"[CANCEL_HANDLER] ❌ Error inesperado: {e}")
            print(f"[CANCEL_HANDLER] 📝 Tipo de error: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            
            # Fallback a BD local
            print(f"[CANCEL_HANDLER] ⚠️ FALLBACK: Usando db.update_appointment_status")
            success = db.update_appointment_status(
                appointment_id=appointment_id,
                new_status='cancelada_cliente',
                changed_by='client',
                reason=reason
            )
            
            if not success:
                return "❌ Error al cancelar la cita. Intenta nuevamente.\n\n_Escribe *0* para volver_"

        print("[CANCEL_HANDLER] 🧹 Limpiando temp_data")
        # Limpiar temp_data
        session.clear_temp()
        session.transition_to(ConversationState.CLIENT_CANCEL_SUCCESS)

        print("[CANCEL_HANDLER] 📤 Retornando mensaje de éxito")
        print("=" * 70)
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
            f"{apt['appointment_date']} {apt['start']}",
            "%Y-%m-%d %H:%M"
        )
        now = datetime.now()
        hours_until = (apt_datetime - now).total_seconds() / 3600

        # Validar tiempo mínimo (22 horas por defecto)
        RESCHEDULE_HOURS_LIMIT = 22

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
        session.set_temp('original_date', apt['appointment_date'])
        session.set_temp('original_start_time', apt['start'])
        session.set_temp('original_end_time', apt['end'])
        session.set_temp('professional_phone', apt['professional_phone'])
        session.set_temp('professional_name', apt['professional_name'])
        session.set_temp('duration', apt['duration_minutes'])
        session.set_temp('modality', apt['modality'])

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
            session.set_temp('available_dates', dates)
            session.set_temp('reschedule_dates_shown', True)

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
            session.set_temp('new_date', selected_date['date_db'])
            session.set_temp('new_date_str', selected_date['date_str'])

            # ✅ IMPORTANTE: Limpiar el flag de fechas mostradas
            session.set_temp('reschedule_dates_shown', False)

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
                    f"{idx}️⃣ {slot['start']} - {slot['end']}")

            formatted_slots = "\n".join(slots_list)

            # Guardar slots en temp
            session.set_temp('available_slots', slots)

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
            session.set_temp('new_start_time', selected_slot['start'])
            session.set_temp('new_end_time', selected_slot['end'])

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
                new_time=selected_slot['start'],
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
        calendar_service = AppointmentCalendarService(db)
        success = calendar_service.reschedule_appointment(
            appointment_id=appointment_id,
            new_date=new_date,
            new_start_time=new_start_time,
            new_end_time=new_end_time
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
            time=apt['start'],
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
                # Format results with available slots

                search_date = session.get_temp('search_date')

                formatted = client_service.format_search_results_with_slots(

                    professionals=results,

                    date_str=search_date,

                    show_max_slots=3

                )
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
        session.set_temp('selected_slot', selected_slot)
        session.set_temp('booking_date', search_date)
        session.set_temp('booking_start_time', selected_slot['start'])
        session.set_temp('booking_end_time', selected_slot['end'])
        
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
⏰ Horario: {selected_slot['start']} - {selected_slot['end']}
📱 Contacto: {prof_phone}

¿Confirmas esta cita?

1️⃣ Sí, confirmar turno
0️⃣ No, volver atrás"""

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
            # Format professional detail with slots
            search_date = session.get_temp('search_date')
            time_preference = session.get_temp('time_preference')
            
            return client_service.format_professional_detail_with_slots(
                professional=professional,
                date_str=search_date,
                time_preference=time_preference
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
        
        # ✅ CREAR CITA EN GOOGLE CALENDAR
        from src.services.appointment_service import appointment_service
        from src.database.database import db
        
        # Obtener nombre del cliente
        client = db.get_client(session.phone_number)
        client_name = client.get('name', 'Cliente') if client else 'Cliente'
        
        try:
            # Crear en Google Calendar
            google_event_id = appointment_service.create_appointment(
                client_phone=session.phone_number,
                client_name=client_name,
                professional_phone=professional['phone'],
                date=booking_date,
                start_time=booking_start_time,
                end_time=booking_end_time,
                appointment_type="Consulta"
            )
            appointment_id = google_event_id
            
            print(f"[CLIENT] ✅ Cita creada en Google Calendar:")
            print(f"         Event ID: {google_event_id}")
            print(f"         Cliente: {session.phone_number} ({client_name})")
            print(f"         Profesional: {professional['phone']}")
            print(f"         Fecha: {booking_date}")
            print(f"         Horario: {booking_start_time} - {booking_end_time}")
            
        except Exception as e:
            print(f"[CLIENT] ❌ Error al crear cita en Google Calendar: {e}")
            import traceback
            traceback.print_exc()
            
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return f"""❌ Error al agendar la cita.

    Por favor, intenta nuevamente o contacta al profesional directamente.

    {client_messages.CLIENT_MAIN_MENU}"""
        
        session.set_temp('appointment_id', appointment_id)
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

    Tu cita ha sido registrada en el calendario del profesional.

    📋 RESUMEN DE LA CITA:

    👨‍⚕️ Profesional: {prof_name}
    📅 Fecha: {day_name} {date_formatted}
    ⏰ Horario: {booking_start_time} - {booking_end_time}
    📱 Contacto: {prof_phone}

    📌 Estado: Confirmada

    El profesional ha recibido tu reserva automáticamente.

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
        
    def handle_client_booking_confirm_name(self, session: SessionData, message: str) -> str:
        """
        Solicita y guarda el nombre del cliente para la reserva.
        """
        if message == '0':
            # Cancelar reserva
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return "Reserva cancelada.\n\n" + client_messages.CLIENT_MAIN_MENU
        
        # Validar nombre (al menos 2 palabras)
        name_parts = message.strip().split()
        if len(name_parts) < 2:
            return "⚠️ Por favor, ingresá tu nombre completo (nombre y apellido).\n\n_(Escribe '0' para cancelar)_"
        
        # Guardar nombre
        client_name = message.strip()
        session.set_temp('client_name', client_name)
        
        # Transicionar a solicitud de email
        session.transition_to(ConversationState.CLIENT_BOOKING_CONFIRM_EMAIL)
        
        return f"""✅ Perfecto, *{client_name}*

    Ahora necesito tu *email* para enviarte la confirmación del turno.

    ¿Cuál es tu email?

    _(Escribe '0' para cancelar)_"""


    def handle_client_booking_confirm_email(self, session: SessionData, message: str) -> str:
        """
        Solicita y guarda el email del cliente para la reserva.
        """
        if message == '0':
            # Cancelar reserva
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return "Reserva cancelada.\n\n" + client_messages.CLIENT_MAIN_MENU
        
        # Validar email básico
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(email_pattern, message.strip()):
            return "⚠️ Email inválido. Por favor, ingresá un email válido.\n\nEjemplo: nombre@ejemplo.com\n\n_(Escribe '0' para cancelar)_"
        
        # Guardar email
        client_email = message.strip().lower()
        session.set_temp('client_email', client_email)
        
        # Transicionar a confirmación final
        session.transition_to(ConversationState.CLIENT_BOOKING_FINAL_CONFIRMATION)
        
        # Obtener todos los datos guardados
        professional = session.get_temp('selected_professional')
        selected_slot = session.get_temp('selected_slot')
        search_date = session.get_temp('search_date')
        client_name = session.get_temp('client_name')
        
        # Formatear fecha
        from datetime import datetime
        try:
            date_obj = datetime.strptime(search_date, "%Y-%m-%d")
            day_names = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
            day_name = day_names[date_obj.weekday()]
            formatted_date = f"{day_name} {date_obj.strftime('%d de %B de %Y')}"
        except:
            formatted_date = search_date
        
        # Mostrar resumen
        message = "📋 *RESUMEN DE TU CITA*\n\n"
        message += f"👤 *Paciente:* {client_name}\n"
        message += f"📧 *Email:* {client_email}\n\n"
        message += f"👨‍⚕️ *Profesional:* {professional.get('title', '')} {professional.get('name')}\n"
        
        if professional.get('address'):
            message += f"📍 {professional['address']}\n"
        
        message += f"\n📅 *Fecha:* {formatted_date}\n"
        message += f"⏰ *Horario:* {selected_slot['start']} - {selected_slot['end']}\n\n"
        
        if professional.get('price'):
            message += f"💰 *Valor:* ${professional['price']:,}\n\n"
        
        message += "─" * 40 + "\n"
        message += "*¿Confirmas el turno?*\n\n"
        message += "1️⃣ Sí, confirmar turno\n"
        message += "0️⃣ Cancelar\n"
        
        return message


    def handle_client_booking_final_confirmation(self, session: SessionData, message: str) -> str:
        """
        Confirma y crea el turno en Google Calendar.
        """
        if message == '0':
            # Cancelar reserva
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return "Reserva cancelada.\n\n" + client_messages.CLIENT_MAIN_MENU
        
        if message != '1':
            return "⚠️ Por favor, elegí una opción:\n\n1️⃣ Confirmar\n0️⃣ Cancelar"
        
        # ⭐ CREAR EL TURNO
        try:
            # TODO: Implementar en FASE 2
            # Por ahora, solo simulamos la creación
            
            professional = session.get_temp('selected_professional')
            selected_slot = session.get_temp('selected_slot')
            search_date = session.get_temp('search_date')
            client_name = session.get_temp('client_name')
            client_email = session.get_temp('client_email')
            
            # Mensaje de éxito
            message = "✅ *¡TURNO CONFIRMADO!*\n\n"
            message += "📋 *Detalles de tu cita:*\n\n"
            message += f"📅 {search_date}\n"
            message += f"⏰ {selected_slot['start']} - {selected_slot['end']}\n\n"
            message += f"👨‍⚕️ {professional.get('title', '')} {professional.get('name')}\n"
            
            if professional.get('address'):
                message += f"📍 {professional['address']}\n"
            
            if professional.get('phone'):
                message += f"📞 {professional['phone']}\n"
            
            message += "\n💡 *Recordatorios:*\n"
            message += "• Llega 10 minutos antes\n"
            message += "• Trae tu DNI y carnet de prepaga (si corresponde)\n"
            message += "• Si necesitas cancelar, avísanos con 24hs de anticipación\n\n"
            message += "📧 Te enviamos la confirmación por email\n\n"
            message += "─" * 40 + "\n"
            message += "*¿Qué querés hacer ahora?*\n\n"
            message += "1️⃣ Ver mis turnos\n"
            message += "2️⃣ Buscar otro profesional\n"
            message += "0️⃣ Volver al menú\n"
            
            # Limpiar temporales y volver al menú
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            
            return message
            
        except Exception as e:
            print(f"[CLIENT] ❌ Error creating appointment: {e}")
            import traceback
            traceback.print_exc()
            
            return """❌ Hubo un error al crear el turno.

    Por favor, intenta nuevamente más tarde o contacta directamente al profesional.

    Escribe 'menu' para volver al menú principal."""