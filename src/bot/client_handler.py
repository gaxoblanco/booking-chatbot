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
from email.mime import message
from typing import Dict
from venv import logger
from requests import session
from src.integrations.appointment_calendar_service import AppointmentCalendarService
from src.services.user_service import user_service
from src.config.domain_config import DomainConfig
from src.core.states import ConversationState, SessionData, UserRole
from src.messages.messages_common import common_messages
from src.messages.messages_client import client_messages
from src.messages.messages_appointments import appointment_messages
from src.utils.validators import validate_name, validate_phone_ar, validate_age
from src.core.validators import parse_date, validate_time
from src.services.client_service import client_service
from src.services.analytics_service import analytics_service
from src.database.database import db
from src.core.normalizers import normalize_confirm_single
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

        Modo multi-profesional:
            CON citas: 1=Buscar, 2=Mañana, 3=Mis citas, 4=Info
            SIN citas: 1=Buscar, 2=Mañana, 3=Info

        Modo profesional único (SINGLE_PROFESSIONAL_MODE=true):
            CON citas: 1=Agendar, 2=Ver reuniones, 3=Info
            SIN citas: 1=Agendar, 2=Info
        """
        from src.services.user_service import user_service
        from src.config.config import Config
        from datetime import datetime, date, timedelta

        message_lower = message.lower().strip()
        single_mode   = getattr(Config, 'SINGLE_PROFESSIONAL_MODE', False)

        # --------------------------------------------------
        # COMANDOS ESPECIALES
        # --------------------------------------------------
        if message_lower == '0':
            return user_service.generate_welcome_message({
                'user_type': 'new', 'name': None,
                'is_registered': False, 'has_pending_appointments': False,
                'pending_appointments': [], 'profile': None,
                'phone_number': session.phone_number
            })

        if message_lower in ['hola', 'hello', 'hi', 'hey',
                            'buenos días', 'buenas tardes', 'buenas noches']:
            session.reset()
            session.set_role(UserRole.CLIENT)
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            client   = db.get_client(session.phone_number)
            greeting = f"¡Hola {client['name']}! 👋\n\n" if (
                client and client.get('name')) else "¡Hola! 👋\n\n"
            welcome_msg = user_service.generate_welcome_message({
                'user_type': 'new', 'name': None,
                'is_registered': False, 'has_pending_appointments': False,
                'pending_appointments': [], 'profile': None,
                'phone_number': session.phone_number
            })
            return greeting + welcome_msg

        if message_lower in ['menu', 'menú', 'volver']:
            return user_service.generate_welcome_message({
                'user_type': 'new', 'name': None,
                'is_registered': False, 'has_pending_appointments': False,
                'pending_appointments': [], 'profile': None,
                'phone_number': session.phone_number
            })

        # --------------------------------------------------
        # VERIFICAR CITAS ACTIVAS (necesario para opciones dinámicas)
        # --------------------------------------------------
        today = datetime.now().strftime("%Y-%m-%d")
        appointments = db.get_appointments_by_client(
            client_phone=session.phone_number,
            from_date=today
        )
        active_appointments = [
            apt for apt in appointments
            if apt['status'] in ['pendiente_confirmacion', 'confirmada']
        ]
        has_appointments = len(active_appointments) > 0

        print(f"[CLIENT_MENU] Usuario tiene citas: {has_appointments} "
            f"({len(active_appointments)} activas)")

        # --------------------------------------------------
        # OPCIÓN 1 — Agendar
        # --------------------------------------------------
        if message == '1':
            if single_mode:
                from src.bot.freelance_handler import handle_freelance_start
                return handle_freelance_start(session)
            session.transition_to(ConversationState.CLIENT_MULTIFILTER_MENU)
            return self.handle_client_multifilter_menu(session, 'start')

        # --------------------------------------------------
        # OPCIÓN 2
        #   Modo único:  Ver mis reuniones (siempre)
        #   Modo multi:  Ver disponibles mañana
        # --------------------------------------------------
        elif message == '2':
            if single_mode:
                print(f"[CLIENT] Ver mis reuniones (modo único): {session.phone_number}")
                session.clear_temp()
                session.transition_to(ConversationState.CLIENT_VIEW_APPOINTMENTS)
                return self.handle_client_view_appointments(session, '')

            # Modo multi — ver disponibles mañana
            print(f"[CLIENT] Disponibles mañana: {session.phone_number}")
            tomorrow            = date.today() + timedelta(days=1)
            tomorrow_str        = tomorrow.strftime("%Y-%m-%d")
            tomorrow_formatted  = tomorrow.strftime("%d/%m/%Y")

            session.set_temp('search_date', tomorrow_str)
            session.set_temp('search_date_formatted', tomorrow_formatted)

            results = client_service.search_professionals_by_filters(
                date_str=tomorrow_str,
                limit=10
            )
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

            return client_service.format_search_results_with_slots(
                professionals=results,
                date_str=tomorrow_str,
                show_max_slots=3
            )

        # --------------------------------------------------
        # OPCIÓN 3
        #   Modo único:  Info del servicio (siempre)
        #   Modo multi:  Ver mis citas (si tiene) | Info (si no tiene)
        # --------------------------------------------------
        elif message == '3':
            if single_mode:
                print(f"[CLIENT] Info del servicio (modo único): {session.phone_number}")
                return user_service.get_center_info()

            # Modo multi — dinámica
            if has_appointments:
                print(f"[CLIENT] Ver mis citas: {session.phone_number}")
                session.clear_temp()
                session.transition_to(ConversationState.CLIENT_VIEW_APPOINTMENTS)
                return self.handle_client_view_appointments(session, '')
            else:
                print(f"[CLIENT] Info del centro: {session.phone_number}")
                return user_service.get_center_info()

        # --------------------------------------------------
        # OPCIÓN 4 — solo modo multi con citas activas
        # --------------------------------------------------
        elif message == '4':
            if single_mode:
                # En modo único no existe opción 4
                return common_messages.INVALID_OPTION + "\n\n" + \
                    user_service.generate_welcome_message({
                        'user_type': 'new', 'name': None,
                        'is_registered': False, 'has_pending_appointments': False,
                        'pending_appointments': [], 'profile': None,
                        'phone_number': session.phone_number
                    })

            if has_appointments:
                print(f"[CLIENT] Info del centro: {session.phone_number}")
                return user_service.get_center_info()
            else:
                return common_messages.INVALID_OPTION + "\n\n" + \
                    user_service.generate_welcome_message({
                        'user_type': 'new', 'name': None,
                        'is_registered': False, 'has_pending_appointments': False,
                        'pending_appointments': [], 'profile': None,
                        'phone_number': session.phone_number
                    })

        # --------------------------------------------------
        # OPCIÓN INVÁLIDA
        # --------------------------------------------------
        else:
            return common_messages.INVALID_OPTION + "\n\n" + \
                user_service.generate_welcome_message({
                    'user_type': 'new', 'name': None,
                    'is_registered': False, 'has_pending_appointments': False,
                    'pending_appointments': [], 'profile': None,
                    'phone_number': session.phone_number
                })

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
        # Check for back — 0, volver, menu
        VOLVER_AL_MENU = {'0', 'volver', 'atrás', 'atras', 'menu', 'menú', 'inicio'}
        if message.strip().lower() in VOLVER_AL_MENU:
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            from src.services.user_service import user_service
            return user_service.generate_welcome_message({
                'user_type': 'client',
                'name': None,
                'is_registered': True,
                'has_pending_appointments': False,
                'pending_appointments': [],
                'profile': None,
                'phone_number': session.phone_number
            })

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
            return appointment_messages.DATE_ALREADY_PASSED + "\n\n" + client_messages.CLIENT_ASK_FECHA

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
                return filter_obj.get_input_prompt(session.temp_data)
            
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
        all_temp = session.temp_data
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
            session.temp_data.pop('current_filter_type', None)
            session.transition_to(ConversationState.CLIENT_MULTIFILTER_MENU)
            print(f"{'='*60}\n")
            return self.format_multifilter_menu(session)
        
        # ===== VALIDAR INPUT =====
        print(f"\n🔍 Validating input...")
        session_data = session.temp_data
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
        session.temp_data.pop('current_filter_type', None)
        session.transition_to(ConversationState.CLIENT_MULTIFILTER_MENU)
        
        print(f"{'='*60}\n")
        
        # Volver directo al menú de filtros con los filtros activos actualizados
        # Sin mensaje intermedio — el menú ya muestra los filtros activos
        return self.format_multifilter_menu(session)

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
        # Check for back command — 0, volver, menu
        VOLVER_MENU = {'0', 'volver', 'atrás', 'atras', 'menu', 'menú', 'inicio'}
        if message.strip().lower() in VOLVER_MENU:
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            from src.services.user_service import user_service
            return user_service.generate_welcome_message({
                'user_type': 'new',
                'name': None,
                'is_registered': False,
                'has_pending_appointments': False,
                'pending_appointments': [],
                'profile': None,
                'phone_number': session.phone_number
            })

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

        # FLUJO NORMAL: Hay resultados, validar selección numérica o por nombre
        msg_lower = message.strip().lower()

        # Si hay un solo resultado y el usuario confirma con lenguaje natural → seleccionar ese
        CONFIRMAR_UNO = {'dale', 'si', 'sí', 'ok', 'ese', 'esa', 'bueno', 'perfecto', 'va'}
        if len(results) == 1 and msg_lower in CONFIRMAR_UNO:
            message = '1'

        # Intentar matching por nombre si no es número
        elif not message.strip().isdigit():
            import re, unicodedata

            def _norm(s):
                """Quita tildes y pasa a minúsculas."""
                nfd = unicodedata.normalize('NFD', s)
                return ''.join(c for c in nfd if unicodedata.category(c) != 'Mn').lower()

            msg_norm = _norm(msg_lower)
            for i, prof in enumerate(results, 1):
                prof_name = prof.get('name', '')
                prof_clean = re.sub(r'^(dr\.?|dra\.?|lic\.?)\s+', '', prof_name, flags=re.IGNORECASE).strip()
                words = [_norm(w) for w in prof_clean.split()]
                # Match si el mensaje contiene alguna palabra del nombre (>= 3 letras)
                if any(w in msg_norm for w in words if len(w) >= 3):
                    message = str(i)
                    print(f"[CLIENT] 🎯 Nombre '{msg_norm}' → profesional #{i}: {prof.get('name')}")
                    # Extraer time_preference del mensaje si menciona franja horaria
                    if 'tarde' in msg_norm:
                        session.set_temp('time_preference', 'tarde')
                    elif 'mañana' in msg_norm or 'manana' in msg_norm:
                        session.set_temp('time_preference', 'mañana')
                    elif 'noche' in msg_norm:
                        session.set_temp('time_preference', 'noche')
                    break

        try:
            selection = int(message)
        except ValueError:
            # Texto libre en pantalla de resultados
            # Solo resetear si el mensaje tiene señales claras de nueva intención.
            # Si es un comentario conversacional, mantener el estado y orientar.
            BUSQUEDA_KEYWORDS = {
                'turno', 'cita', 'sesion', 'busco', 'buscar', 'necesito',
                'tarde', 'noche', 'lunes', 'martes', 'miercoles', 'jueves',
                'viernes', 'sabado', 'domingo', 'hoy', 'semana', 'cancelar',
                'ver mis', 'mis turnos', 'para mi', 'para el', 'para la',
                'mi tio', 'mi mama', 'mi papa', 'mi primo', 'mi hijo',
            }
            msg_norm_kw = msg_lower.strip()
            words = msg_norm_kw.split()
            es_nueva_busqueda = (
                len(words) >= 5 or
                any(kw in msg_norm_kw for kw in BUSQUEDA_KEYWORDS)
            )

            if es_nueva_busqueda:
                # Intención de nueva búsqueda — resetear y dejar al NLU
                session.clear_temp()
                session.transition_to(ConversationState.START)
                return None
            else:
                # Comentario conversacional — mantener estado y orientar
                n = len(results)
                return (
                    f"Respondé con el número del profesional (1 al {n}) "
                    f"para ver sus horarios.\n\n"
                    "_O escribí lo que necesitás para hacer una nueva búsqueda._"
                )

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
        # 6. SI SELECCIONÓ UN NÚMERO, NOMBRE, FECHA O CONFIRMACIÓN → IR A DETALLE
        # ==========================================
        if message and message.strip():
            msg_lower = message.strip().lower()
            matched_idx = None

            # A) Número directo
            if message.strip().isdigit() and int(message.strip()) > 0:
                idx = int(message.strip()) - 1
                if 0 <= idx < len(active_appointments):
                    matched_idx = idx
                else:
                    return f"⚠️ Número inválido. Elegí entre 1 y {len(active_appointments)} o *0* para volver."

            # B) dale/si/ese/esa → si hay una sola cita, seleccionarla
            elif normalize_confirm_single(message):
                if len(active_appointments) == 1:
                    matched_idx = 0

            # C) Matching por nombre de profesional
            elif not message.strip().isdigit():
                import re as _re
                for i, apt in enumerate(active_appointments):
                    prof = apt.get('professional_name', '').lower()
                    prof_clean = _re.sub(r'^(dr\.?|dra\.?|lic\.?)\s+', '', prof).strip()
                    words = prof_clean.split()
                    if any(w in msg_lower for w in words if len(w) > 3):
                        matched_idx = i
                        print(f"[CLIENT] 🎯 Cita por nombre '{msg_lower}' → #{i+1}: {apt.get('professional_name')}")
                        break

            # D) Matching por fecha — "el jueves", "22/04", "del lunes", "del 22/04"
            if matched_idx is None and message.strip():
                from src.core.validators import parse_date
                from datetime import date as _date
                import re as _re2

                date_obj = None

                # Intentar parseo directo (ej: "22/04", "2026-04-22")
                date_obj = parse_date(message)

                # Si no, buscar día de semana en el mensaje
                if not date_obj:
                    DIAS = {
                        'lunes': 0, 'martes': 1, 'miercoles': 2, 'miércoles': 2,
                        'jueves': 3, 'viernes': 4, 'sabado': 5, 'sábado': 5, 'domingo': 6
                    }
                    msg_norm = message.lower()
                    for dia, weekday in DIAS.items():
                        if dia in msg_norm:
                            today_wd = _date.today().weekday()
                            days_ahead = (weekday - today_wd) % 7
                            if days_ahead == 0:
                                days_ahead = 7
                            from datetime import timedelta
                            date_obj = _date.today() + timedelta(days=days_ahead)
                            break

                # Si tampoco, buscar fecha DD/MM en el mensaje
                if not date_obj:
                    m = _re2.search(r'(\d{1,2})[/\-](\d{1,2})', message)
                    if m:
                        date_obj = parse_date(m.group(0))

                if date_obj:
                    date_target = date_obj.strftime("%Y-%m-%d")
                    for i, apt in enumerate(active_appointments):
                        if apt['appointment_date'] == date_target:
                            matched_idx = i
                            print(f"[CLIENT] 🎯 Cita por fecha '{date_target}' → #{i+1}")
                            break

            if matched_idx is not None:
                session.set_temp('selected_appointment_index', matched_idx)
                session.transition_to(ConversationState.CLIENT_APPOINTMENT_DETAIL)
                return self.handle_client_appointment_detail(session, str(matched_idx + 1))

        # ==========================================
        # 7. MOSTRAR LISTA DE CITAS
        # ==========================================
        # Mapeo de días al español
        _DIAS_ES = {
            'Mon': 'Lun', 'Tue': 'Mar', 'Wed': 'Mié', 'Thu': 'Jue',
            'Fri': 'Vie', 'Sat': 'Sáb', 'Sun': 'Dom'
        }

        appointments_list = []
        for idx, apt in enumerate(active_appointments, 1):
            # Formatear fecha en español
            date_obj = datetime.strptime(apt['appointment_date'], "%Y-%m-%d")
            day_en = date_obj.strftime("%a")
            day_es = _DIAS_ES.get(day_en, day_en)
            date_str = f"{day_es} {date_obj.strftime('%d/%m/%Y')}"

            # Emoji y texto según estado
            if apt['status'] == 'pendiente_confirmacion':
                status_emoji = "⏳"
                status_text = "Pendiente"
            elif apt['status'] == 'confirmada' and apt.get('confirmed_by_client'):
                status_emoji = "✅"
                status_text = "Confirmada"
            elif apt['status'] == 'confirmada':
                status_emoji = "📅"
                status_text = "Agendada"
            else:
                status_emoji = "✅"
                status_text = "Agendada"

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
                session.transition_to(ConversationState.CLIENT_RESCHEDULE_APPOINTMENT)
                return self.handle_client_reschedule_appointment(session, '1')

            # OPCIÓN 2: CANCELAR
            elif message == '2':
                print(f"[CLIENT] Iniciando cancelación: {session.phone_number}")
                session.transition_to(ConversationState.CLIENT_CANCEL_APPOINTMENT)
                return self.handle_client_cancel_appointment(session, '1')

            elif message == '0':
                # Volver a la lista
                session.clear_temp()
                session.transition_to(ConversationState.CLIENT_VIEW_APPOINTMENTS)
                return self.handle_client_view_appointments(session, '')

            else:
                # Texto libre — si es confirmación natural, volver a mostrar el detalle
                # Si es otra intención, resetear al NLU
                CONFIRM_WORDS = {'dale', 'si', 'sí', 'ok', 'bueno', 'ver', 'mostrar'}
                if message.strip().lower() in CONFIRM_WORDS:
                    # Mostrar el detalle de la cita actual
                    apt = db.get_appointment(appointment_id)
                    if apt:
                        return self._format_appointment_detail(session, apt)
                # Texto libre con otra intención — resetear y reprocesar
                session.clear_temp()
                session.transition_to(ConversationState.START)
                return None
        
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
        # NORMALIZAR TEXTO LIBRE → 1 o 2
        # ==========================================
        from src.core.normalizers import normalize_yes_no
        normalizado = normalize_yes_no(message)
        if normalizado:
            message = normalizado

        # ==========================================
        # VERIFICAR SI VENIMOS DE UN ERROR PREVIO
        # ==========================================
        if message == '0':
            session.set_temp('cancel_error_shown', False)
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

        apt = db.get_appointment(appointment_id)

        if not apt:
            session.set_temp('cancel_error_shown', True)
            return appointment_messages.APPOINTMENT_LOAD_ERROR

        # ── Validación de ownership ─────────────────────────────────────────
        if apt.get('client_phone') != session.phone_number:
            print(f"[CLIENT] 🚨 SECURITY: {session.phone_number} intentó acceder "
                f"a la cita #{appointment_id} que pertenece a {apt.get('client_phone')}")
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return "⚠️ No podemos procesar esa solicitud.\n\nEscribí *menu* para volver al inicio."

        # ==========================================
        # VALIDAR ESTADO DE LA CITA
        # ==========================================
        if apt['status'] in ['cancelada_cliente', 'cancelada_profesional']:
            session.set_temp('cancel_error_shown', True)
            return appointment_messages.CLIENT_APPOINTMENT_ALREADY_CANCELLED + "\n\n_Escribe *0* para volver_"

        if apt['status'] == 'completada':
            session.set_temp('cancel_error_shown', True)
            return appointment_messages.APPOINTMENT_FINISHED

        # ==========================================
        # VALIDAR TIEMPO LÍMITE
        # Bypass si viene desde recordatorio — el sistema le ofreció cancelar
        # explícitamente, y la cita no está confirmada por el cliente aún.
        # ==========================================
        from_reminder = session.get_temp('from_reminder')
        already_confirmed = apt.get('confirmed_by_client', 0)

        apt_datetime = datetime.strptime(
            f"{apt['appointment_date']} {apt['start']}",
            "%Y-%m-%d %H:%M"
        )
        now = datetime.now()
        hours_until = (apt_datetime - now).total_seconds() / 3600

        from src.config.domain_config import DomainConfig
        CANCELLATION_HOURS_LIMIT = getattr(DomainConfig, 'CANCELLATION_HOURS_LIMIT', 22)

        # Bloquear solo si: NO viene del recordatorio O ya fue confirmada por el cliente
        if hours_until < CANCELLATION_HOURS_LIMIT and (not from_reminder or already_confirmed):
            session.set_temp('cancel_error_shown', True)
            return appointment_messages.CLIENT_CANCEL_TOO_LATE.format(
                hours_until=int(hours_until),
                professional_phone=apt['professional_phone']
            )

        # ==========================================
        # MOSTRAR CONFIRMACIÓN
        # '1' = confirmar cancelación
        # '2' = "No, mantener turno" — volver a opciones del recordatorio
        # ==========================================
        if message == '2' and from_reminder:
            try:
                with db.get_connection() as conn:
                    conn.execute("""
                        UPDATE appointment_reminders 
                        SET status = 'sent', response_received_at = NULL
                        WHERE appointment_id = ? AND client_phone = ?
                    """, (appointment_id, session.phone_number))
            except Exception as e:
                print(f"[CANCEL] No se pudo restaurar reminder: {e}")

            session.transition_to(ConversationState.AWAITING_REMINDER_RESPONSE)
            from src.messages.loader import get_msg
            return get_msg('REMINDER_BACK_TO_OPTIONS')

        if message == '1':
            session.set_temp('cancel_error_shown', False)

            # ── CORTOCIRCUITO: viene del recordatorio ──────────────────────────
            # El cliente ya vio profesional + fecha en el mensaje del recordatorio
            # (_initiate_cancellation lo incluye). No repetir confirmación.
            if from_reminder:
                session.transition_to(ConversationState.CLIENT_CANCEL_REASON)
                return self.handle_client_cancel_reason(session, '1')
            # ── FIN CORTOCIRCUITO ──────────────────────────────────────────────

            date_obj = datetime.strptime(apt['appointment_date'], "%Y-%m-%d")
            _dias  = ['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo']
            _meses = ['Enero','Febrero','Marzo','Abril','Mayo','Junio',
                    'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']
            date_str = f"{_dias[date_obj.weekday()]} {date_obj.day} de {_meses[date_obj.month-1]} de {date_obj.year}"
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

        # Texto no reconocido — pedir aclaración sin resetear el estado
        from src.messages.loader import get_msg
        return get_msg('CANCEL_CONFIRM_OR_KEEP')
    
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

        # '0' = volver sin cancelar
        if message == '0':
            session.transition_to(ConversationState.CLIENT_APPOINTMENT_DETAIL)
            appointment_id = session.get_temp('appointment_id')
            if appointment_id:
                apt = db.get_appointment(appointment_id)
                if apt:
                    return self._format_appointment_detail(session, apt)
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_VIEW_APPOINTMENTS)
            return self.handle_client_view_appointments(session, '')

        # '1' = confirmar cancelación
        if message == '1':
            reason = None
        else:
            # El mensaje es el motivo de cancelación
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
                return appointment_messages.CANCEL_ERROR_TECHNICAL
            
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
                return appointment_messages.CANCEL_ERROR_TECHNICAL
        
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
                return appointment_messages.CANCEL_ERROR_TECHNICAL

        print("[CANCEL_HANDLER] 🧹 Limpiando temp_data")

        # ── Disparar waitlist en background ──────────────────────────────────
        # Si hay candidatos que quieran adelantar, les enviamos la oferta.
        # Corre en thread separado para no bloquear la respuesta al cliente.
        try:
            import threading
            from src.services.waitlist_service import waitlist_service
            threading.Thread(
                target=waitlist_service.handle_slot_freed,
                kwargs={
                    'freed_appointment_id': appointment_id,
                    'reason': 'cancelled'
                },
                daemon=True
            ).start()
            print(f"[CANCEL_HANDLER] 🔔 Waitlist thread iniciado para cita #{appointment_id}")
        except Exception as wl_err:
            # No interrumpir el flujo de cancelación si waitlist falla
            print(f"[CANCEL_HANDLER] ⚠️ Waitlist no disparada: {wl_err}")
        # ── Fin waitlist ──────────────────────────────────────────────────────

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
            # Buscar nuevo turno → menú principal de búsqueda
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return client_messages.CLIENT_MAIN_MENU

        elif message == '0':
            # Menú principal
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return client_messages.CLIENT_MAIN_MENU

        else:
            # Texto libre — resetear y reprocesar por NLU
            session.clear_temp()
            session.transition_to(ConversationState.START)
            return None

    # ==========================================
    # REPROGRAMACIÓN DE CITAS
    # ==========================================
    def handle_client_reschedule_appointment(self, session: SessionData, message: str) -> str:
        """
        Inicio del flujo de reprogramación.

        Valida que se pueda reprogramar según RESCHEDULE_HOURS_LIMIT del .env:
            - 0       → sin restricción de tiempo
            - N > 0   → mínimo N horas de anticipación
            - from_reminder=True en session → bypass siempre (el recordatorio
            habilita reprogramar aunque sea tarde)

        No permite reprogramar si el turno ya fue confirmado explícitamente
        por el cliente (confirmed_by_client=1) fuera del flujo de recordatorio.
        """
        from datetime import datetime
        import os

        # Back command
        if message == '0':
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return client_messages.CLIENT_MAIN_MENU

        appointment_id = session.get_temp('appointment_id')
        if not appointment_id:
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return "❌ Error: No hay cita seleccionada\n\n" + client_messages.CLIENT_MAIN_MENU

        apt = db.get_appointment(appointment_id)
        if not apt:
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return appointment_messages.APPOINTMENT_LOAD_ERROR

        # Validar estado de la cita
        if apt['status'] in ['cancelada_cliente', 'cancelada_profesional', 'completada']:
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return appointment_messages.APPOINTMENT_CANT_RESCHEDULE.format(
                status=apt['status']
            )

        # Calcular horas hasta la cita
        apt_datetime = datetime.strptime(
            f"{apt['appointment_date']} {apt['start']}",
            "%Y-%m-%d %H:%M"
        )
        hours_until = (apt_datetime - datetime.now()).total_seconds() / 3600

        # Leer límite desde .env — 0 = sin restricción
        _raw = os.getenv('RESCHEDULE_HOURS_LIMIT', '22').strip()
        try:
            RESCHEDULE_HOURS_LIMIT = int(_raw)
        except ValueError:
            RESCHEDULE_HOURS_LIMIT = 22

        # TESTING: skip time validation
        if os.getenv('TESTING_SKIP_TIME_VALIDATION', '').lower() == 'true':
            print(f"[TEST] ⚠️ Skipping time validation — original hours_until: {hours_until:.1f}")
            hours_until = 48

        # Bypass desde recordatorio — el paciente tiene derecho a reprogramar
        # aunque el turno esté próximo, porque fue el sistema quien lo notificó
        from_reminder = session.get_temp('from_reminder', False)

        # Validar tiempo límite
        # Condiciones para bloquear:
        #   - NO viene del recordatorio
        #   - El límite es > 0 (0 = sin restricción)
        #   - Quedan menos horas que el límite
        if not from_reminder and RESCHEDULE_HOURS_LIMIT > 0 and hours_until < RESCHEDULE_HOURS_LIMIT:
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return appointment_messages.CLIENT_RESCHEDULE_TOO_LATE.format(
                hours_until=int(hours_until),
                limit=RESCHEDULE_HOURS_LIMIT,
                professional_phone=apt['professional_phone']
            )

        # Guardar datos originales
        session.set_temp('original_date', apt['appointment_date'])
        session.set_temp('original_start_time', apt['start'])
        session.set_temp('original_end_time', apt['end'])
        session.set_temp('professional_phone', apt['professional_phone'])
        session.set_temp('professional_name', apt['professional_name'])
        session.set_temp('duration', apt['duration_minutes'])
        session.set_temp('modality', apt['modality'])
        session.transition_to(ConversationState.CLIENT_RESCHEDULE_SELECT_DATE)
        return self.handle_client_reschedule_select_date(session, 'start')
    
    def handle_client_reschedule_select_date(self, session: SessionData, message: str) -> str:
        """
        Maneja selección de nueva fecha para reprogramación.
        """
        from datetime import datetime
        from src.services.professional_service import professional_service
        import os

        close_time = os.getenv('REMINDER_CLOSE_TIME', '20:30')
        dates_shown = session.get_temp('reschedule_dates_shown', False)
        print(f"[DEBUG RESCHEDULE] message='{message}' dates_shown={dates_shown} available_dates={bool(session.get_temp('available_dates'))}")

        # Check for back command
        if message == '0':
            # si viene del recordatorio, volver a las opciones:
            from_reminder = session.get_temp('from_reminder')
            if from_reminder:
                # Restaurar reminder a 'sent' para que pueda confirmar/cancelar
                try:
                    appointment_id = session.get_temp('appointment_id')
                    with db.get_connection() as conn:
                        conn.execute("""
                            UPDATE appointment_reminders 
                            SET status = 'sent', response_received_at = NULL
                            WHERE appointment_id = ? AND client_phone = ?
                        """, (appointment_id, session.phone_number))
                except Exception as e:
                    print(f"[RESCHEDULE] No se pudo restaurar reminder: {e}")
                session.transition_to(ConversationState.AWAITING_REMINDER_RESPONSE)
                from src.messages.loader import get_msg
                return get_msg('REMINDER_BACK_TO_OPTIONS')
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
            # Persistir — el próximo mensaje necesita leer estos temps
            from src.core.states import session_manager
            session_manager.save_session(session)

            # Formatear fecha original
            original_time = session.get_temp('original_start_time')
            old_date_obj = datetime.strptime(original_date, "%Y-%m-%d")
            old_date_str = old_date_obj.strftime("%d/%m/%Y")

            return appointment_messages.CLIENT_RESCHEDULE_SELECT_DATE.format(
                old_date=old_date_str,
                old_time=original_time,
                available_dates=formatted_dates,
                close_time=close_time,
            )

        # ✅ Si llegó aquí, el usuario está seleccionando una fecha
        available_dates = session.get_temp('available_dates')

        # Intentar primero como número de lista
        try:
            selection = int(message)
            if not available_dates or selection < 1 or selection > len(available_dates):
                return "⚠️ Opción inválida.\n\n_Escribe el número de la fecha o *0* para volver_"
            selected_date = available_dates[selection - 1]

        except ValueError:
            # No es número — intentar parsear como fecha natural ("el viernes", "mañana", "01/04")
            from src.core.validators import parse_date
            from datetime import date as _date, timedelta
            import re as _re

            date_obj = parse_date(message)

            # Si no parseó directo, buscar día de semana
            if not date_obj:
                DIAS = {
                    'lunes': 0, 'martes': 1, 'miercoles': 2, 'miércoles': 2,
                    'jueves': 3, 'viernes': 4, 'sabado': 5, 'sábado': 5, 'domingo': 6
                }
                msg_norm = message.strip().lower()
                for dia, weekday in DIAS.items():
                    if dia in msg_norm:
                        today_wd = _date.today().weekday()
                        days_ahead = (weekday - today_wd) % 7 or 7
                        date_obj = _date.today() + timedelta(days=days_ahead)
                        break

            # Intentar también "mañana" / "hoy" de forma directa
            if not date_obj:
                msg_low = message.strip().lower()
                if msg_low in ('mañana', 'manana'):
                    date_obj = _date.today() + timedelta(days=1)
                elif msg_low == 'hoy':
                    date_obj = _date.today()
                elif msg_low == 'pasado mañana' or msg_low == 'pasado manana':
                    date_obj = _date.today() + timedelta(days=2)

            # Intentar DD/MM sin año → asumir año actual o siguiente
            if not date_obj:
                import re as _re2
                m = _re2.match(r'^(\d{1,2})/(\d{1,2})$', message.strip())
                if m:
                    from datetime import date as _d2
                    day, month = int(m.group(1)), int(m.group(2))
                    year = _d2.today().year
                    try:
                        candidate = _date(year, month, day)
                        if candidate < _date.today():
                            candidate = _date(year + 1, month, day)
                        date_obj = candidate
                    except ValueError:
                        pass

            # Intentar DD/MM/YY con año de 2 dígitos
            if not date_obj:
                m = _re2.match(r'^(\d{1,2})/(\d{1,2})/(\d{2})$', message.strip())
                if m:
                    day, month, year_2d = int(m.group(1)), int(m.group(2)), int(m.group(3))
                    year = 2000 + year_2d
                    try:
                        date_obj = _date(year, month, day)
                    except ValueError:
                        pass

            if date_obj and available_dates:
                # Primero buscar en la lista pre-cargada
                date_str_match = date_obj.strftime("%Y-%m-%d")
                matched = next(
                    (d for d in available_dates if d['date_db'] == date_str_match),
                    None
                )
                if matched:
                    selected_date = matched
                elif date_obj < _date.today():
                    return "Esa fecha ya paso. Elegi una fecha futura.\n\n_Escribi *0* para volver_"
                else:
                    # Fecha fuera de la lista pre-cargada — consultar disponibilidad
                    professional_phone = session.get_temp('professional_phone')
                    appointment_id = session.get_temp('appointment_id')
                    slots = professional_service.get_available_slots(
                        professional_phone=professional_phone,
                        date=date_str_match,
                        exclude_appointment_id=appointment_id,
                    )
                    if slots:
                        dias = ['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo']
                        day_name = dias[date_obj.weekday()]
                        date_str_fmt = date_obj.strftime("%d/%m/%Y")
                        selected_date = {
                            'date_db':    date_str_match,
                            'date_str':   date_str_fmt,
                            'day_name':   day_name,
                            'slots_count': len(slots),
                        }
                    else:
                        date_fmt = date_obj.strftime("%d/%m/%Y")
                        return (
                            f"No hay disponibilidad para el {date_fmt}.\n\n"
                            "Elegi otra fecha o un numero de la lista.\n\n"
                            "_Escribi *0* para volver_"
                        )
            else:
                # No se pudo interpretar — pedir de nuevo sin resetear
                return (
                    "⚠️ No entendí la fecha. Escribí el número de la opción "
                    "o una fecha como *el viernes*, *mañana*, *01/04*.\n\n"
                    "_Escribí *0* para volver_"
                )

        # Guardar fecha seleccionada
        session.set_temp('new_date', selected_date['date_db'])
        session.set_temp('new_date_str', selected_date['date_str'])
        session.set_temp('reschedule_dates_shown', False)
        session.transition_to(ConversationState.CLIENT_RESCHEDULE_SELECT_TIME)
        return self.handle_client_reschedule_select_time(session, 'start')

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
        available_slots = session.get_temp('available_slots')

        # Intentar primero como número
        try:
            selection = int(message)
            if not available_slots or selection < 1 or selection > len(available_slots):
                return "⚠️ Opción inválida.\n\n_Escribí el número del horario o *0* para volver_"
            selected_slot = available_slots[selection - 1]

        except ValueError:
            # No es número — intentar matchear como hora (ej: "15:40")
            if available_slots:
                matched = next(
                    (s for s in available_slots if s['start'] == message.strip()),
                    None
                )
                if matched:
                    selected_slot = matched
                else:
                    # No matcheó — pedir de nuevo SIN resetear sesión
                    return "⚠️ No entendí. Escribí el número del horario o la hora exacta (ej: *15:40*).\n\n_Escribí *0* para volver_"
            else:
                return "⚠️ Error al cargar horarios. Escribí *0* para volver."

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

    def handle_client_reschedule_confirm(self, session: SessionData, message: str) -> str:
        """
        Confirma y ejecuta la reprogramación de la cita.
        """
        from datetime import datetime

        # Normalizar texto libre → 1 o 0
        _msg = message.strip().lower()
        if _msg in ['1', 'si', 'sí', 'confirmar', 'confirmado', 'dale', 'ok', 'listo', 'va']:
            message = '1'
        elif _msg in ['0', 'no', 'volver', 'cancelar', 'no confirmar']:
            message = '0'

        # Volver a selección de horario
        if message == '0':
            session.transition_to(ConversationState.CLIENT_RESCHEDULE_SELECT_TIME)
            return self.handle_client_reschedule_select_time(session, '')

        # No reconocido — pedir de nuevo sin resetear estado
        if message != '1':
            return "⚠️ No entendí tu respuesta.\n\nRespondé con:\n1️⃣ *1* — Confirmar el cambio\n0️⃣ *0* — Volver a los horarios"

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
            appointment_id=int(appointment_id),  # ← fix Pylance
            new_date=new_date,
            new_start_time=new_start_time,
            new_end_time=new_end_time
        )

        if not success:
            return "❌ Error al reprogramar la cita. Intentá nuevamente.\n\n_Escribí *0* para volver_"

        session.transition_to(ConversationState.CLIENT_CANCEL_SUCCESS)

        return appointment_messages.CLIENT_RESCHEDULE_SUCCESS.format(
            new_date=new_date_str,
            new_time=new_start_time,
            professional_name=professional_name
        )
    
    # ========================================
    # MÉTODO PARA HANDLERS DE CONFIRMACIÓN
    # ========================================

    def handle_confirm_cancel(self, session: SessionData, message: str) -> str:
        """
        Handler para confirmación de cancelación de turno.
        
        Estado: CLIENT_CONFIRM_CANCEL
        """
        from src.services.client_service import client_service
        
        message_lower = message.lower().strip()
        
        from src.core.normalizers import normalize_yes_no
        if normalize_yes_no(message) == '1':
            appointment = session.get_temp('appointment_to_cancel')
            
            if not appointment:
                return "⚠️ Hubo un error. Por favor intenta de nuevo."
            
            # Cancelar turno
            result = client_service.cancel_appointment(
                appointment_id=appointment['id'],
                phone_number=session.phone_number,
                reason='Cancelado por el cliente vía WhatsApp',
                bypass_policy  = True,
            )
            
            if result.get('success'):
                session.clear_temp()
                session.transition_to(ConversationState.CLIENT_MAIN_MENU)
                
                return (f"✅ Turno cancelado exitosamente\n\n"
                    f"👨‍⚕️ {appointment['professional_name']}\n"
                    f"📅 {appointment['date_formatted']}\n"
                    f"🕐 {appointment['time']}\n\n"
                    f"Si deseas agendar un nuevo turno, escribe 'buscar'.")
            else:
                return ("⚠️ No se pudo cancelar el turno.\n\n"
                    "Por favor contacta al centro directamente.")
        
        # Cancelar la cancelación
        elif message_lower in ['no', 'volver', 'cancelar', 'atrás', 'atras']:
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            
            user_info = user_service.identify_user(session.phone_number)
            user_info['phone_number'] = session.phone_number
            return user_service.generate_welcome_message(user_info)
        
        # Opción inválida
        else:
            return ("⚠️ Por favor responde:\n"
                "• 'sí' para confirmar la cancelación\n"
                "• 'no' para volver al menú")


    def handle_select_cancel(self, session: SessionData, message: str) -> str:
        """
        Handler para seleccionar qué turno cancelar (cuando hay múltiples).
        
        Estado: CLIENT_SELECT_CANCEL
        """
        
        appointments = session.get_temp('appointments_list')
        
        if not appointments:
            return "⚠️ Hubo un error. Por favor intenta de nuevo."
        
        # Opción 0: Volver
        if message == '0':
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            
            user_info = user_service.identify_user(session.phone_number)
            user_info['phone_number'] = session.phone_number
            return user_service.generate_welcome_message(user_info)
        
        # Validar número
        try:
            selection = int(message)
            
            if 1 <= selection <= len(appointments):
                # Turno seleccionado
                appointment = appointments[selection - 1]
                
                # Guardar y pedir confirmación
                session.set_temp('appointment_to_cancel', appointment)
                session.transition_to(ConversationState.CLIENT_CONFIRM_CANCEL)
                
                from src.messages.loader import get_msg

                return get_msg('CLIENT_CONFIRM_CANCEL_SELECTION').format(
                    professional_name=appointment['professional_name'],
                    date_formatted=appointment['date_formatted'],
                    time=appointment['time'],
                    modality=appointment.get('modality', 'presencial').title()
                )
            else:
                return f"⚠️ Por favor ingresa un número entre 1 y {len(appointments)}, o '0' para volver."
                
        except ValueError:
            return f"⚠️ Por favor ingresa un número entre 1 y {len(appointments)}, o '0' para volver."



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
            status_badge = "Estado: ⏳ *Pendiente*"
        elif apt['status'] == 'confirmada' and apt.get('confirmed_by_client'):
            status_badge = "Estado: ✅ *Confirmada*"
        elif apt['status'] == 'confirmada':
            status_badge = "Estado: 📅 *Agendada*"
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

        # Meet link — solo si existe en la cita
        meet_line = ""
        # Refrescar meet_link desde BD — el dict en session.temp puede estar desactualizado
        if not apt.get('meet_link') and apt.get('id'):
            fresh = db.get_appointment(apt['id'])
            if fresh and fresh.get('meet_link'):
                apt['meet_link'] = fresh['meet_link']
        if apt.get('meet_link'):
            # Como puede o no existir, el salto de linea lo manejo aca.
            meet_line = f"\n🎥 {apt['meet_link']}\n" if apt.get('meet_link') else ""

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
            options=options,
            meet_line=meet_line,
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
        
        # Check for back — acepta número o lenguaje natural
        VOLVER = {'0', 'volver', 'atrás', 'atras', 'back', 'salir', 'cancelar', 'no'}
        if message.strip().lower() in VOLVER:
            message = '0'

        if message == '0':
            # Modo freelance — volver a preguntar horario
            if session.get_temp('flow_context') == 'freelance':
                session.set_temp('freelance_filters_shown', False)
                session.transition_to(ConversationState.CLIENT_FREELANCE_BOOK_TIME)
                from src.messages.loader import get_msg
                return get_msg('CLIENT_ASK_HORA')
            
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
                
                session.transition_to(ConversationState.CLIENT_SHOW_RESULTS)
                return formatted
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
        
        # Cargar los mismos slots que se mostraron en pantalla
        # (aplicando el mismo filtro de franja horaria)
        time_preference = session.get_temp('time_preference')
        all_slots = professional_service.get_available_slots(
            professional['phone'],
            search_date,
            duration_minutes=50
        )

        # Filtrar por franja si aplica — para que los números coincidan con lo mostrado
        if time_preference and all_slots:
            from datetime import datetime as _dt
            FRANJAS = {
                'mañana': (6, 13),
                'tarde':  (13, 20),
                'noche':  (20, 24),
            }
            rango = FRANJAS.get(time_preference)
            if rango:
                slots = [
                    s for s in all_slots
                    if rango[0] <= _dt.strptime(s['start'], '%H:%M').hour < rango[1]
                ]
            else:
                slots = all_slots
        else:
            slots = all_slots

        if not slots:
            return "❌ No hay horarios disponibles.\n\nEscribí *0* para volver."

        # Intentar como número directo
        try:
            selection = int(message)

        except ValueError:
            # No es número — intentar como hora natural: "a las 9", "09:00", "las 10:40"
            import re as _re
            time_match = _re.search(r'(\d{1,2})(?:[:h](\d{2}))?', message)
            selection = None

            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2)) if time_match.group(2) else 0
                time_str = f"{hour:02d}:{minute:02d}"

                # Buscar el slot que empiece con ese horario
                for i, slot in enumerate(slots, 1):
                    if slot['start'].startswith(f"{hour:02d}:"):
                        selection = i
                        print(f"[CLIENT] 🕐 Hora natural '{message}' → slot #{i}: {slot['start']}")
                        break

            if selection is None:
                # En CLIENT_VIEW_DETAIL_WITH_BOOKING el usuario ya eligió profesional
                # y está viendo horarios. Solo salir si hay señales explícitas de
                # NUEVA búsqueda — no basta con longitud o keywords ambiguas.
                #
                # Keywords ACCIONABLES: implican cambio de fecha, franja, profesional o
                # intención distinta (cancelar, ver citas). No incluir palabras que
                # el usuario puede usar para comentar lo que ve ("horarios", "trabaja", etc.)
                NUEVA_BUSQUEDA_KW = {
                    # Días de semana — quiere otra fecha
                    'lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo',
                    # Expresiones de fecha
                    'para el', 'para la', 'este ', 'próximo', 'proximo', 'semana que',
                    # Cambio de franja explícito con intención
                    'por la tarde', 'por la mañana', 'por la noche',
                    'a la tarde', 'a la mañana',
                    # Intenciones distintas
                    'cancelar', 'ver mis', 'mis turnos', 'para mi', 'para un',
                    'mi tio', 'mi mama', 'mi papa', 'mi primo', 'mi hijo',
                    # Verbos de acción de búsqueda explícita
                    'busco otro', 'buscar otro', 'quiero otro', 'busco un',
                    'quiero buscar', 'necesito otro',
                }
                msg_lower_kw = message.strip().lower()

                es_nueva_busqueda = any(kw in msg_lower_kw for kw in NUEVA_BUSQUEDA_KW)

                if es_nueva_busqueda:
                    # Dejar pasar al NLU — puede ser search_professional, book_for_third_party, etc.
                    session.clear_temp()
                    session.transition_to(ConversationState.START)
                    return None
                else:
                    # Comentario sobre los horarios — mantener estado y orientar
                    return (
                        "Para elegir el horario respondé con el número de la lista.\n\n"
                        "_Escribí *0* para volver a los resultados_"
                    )

        # Validate selection range
        if selection < 1 or selection > len(slots):
            return f"⚠️ Elegí un número entre 1 y {len(slots)}.\n\nEscribí *0* para volver."
        
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

        # GAP 6 — Línea de paciente
        from src.config.filter_config import FeatureFlags
        booking_for_info = ""
        if FeatureFlags.THIRD_PARTY_BOOKING and session.get_temp('booking_for') == 'other':
            relation = session.get_temp('third_party_relation') or 'familiar'
            tp_name  = session.get_temp('third_party_name')
            name_str = f" — {tp_name}" if tp_name else ""
            booking_for_info = f"👤 Paciente: tu {relation}{name_str}\n"
        else:
            # Flujo normal — mostrar nombre del cliente si está registrado
            client = db.get_client(session.phone_number)
            client_name = client.get('name') if client else None
            if client_name:
                booking_for_info = f"👤 Paciente: {client_name}\n"

        return appointment_messages.CONFIRM_BOOKING_HEADER.format(
            patient_line=booking_for_info,
            emoji_prof=DomainConfig.EMOJI_PROFESSIONAL,
            prof_name=prof_name,
            day=day_name,
            date=date_formatted,
            start=selected_slot['start'],
            end=selected_slot['end'],
            phone=prof_phone,
        )

    def handle_client_confirm_booking(self, session: SessionData, message: str) -> str:
        """
        Handle booking confirmation.
        User must confirm with '1' or cancel with '0'.
        """
        from datetime import datetime
        from src.services.appointment_service import appointment_service
        from src.config.domain_config import DomainConfig

        # Check for cancellation
        # Acepta número o lenguaje natural
        CONFIRMAR = {'1', 'si', 'sí', 'dale', 'ok', 'confirmo', 'confirmar',
                     'bueno', 'perfecto', 'quiero', 'acepto', 'va', 'listo'}
        CANCELAR  = {'0', 'no', 'cancelar', 'volver', 'atrás', 'atras',
                     'nope', 'no quiero', 'salir'}
        msg_lower = message.strip().lower()
        if msg_lower in CONFIRMAR:
            message = '1'
        elif msg_lower in CANCELAR:
            message = '0'

        if message == '0':
            professional = session.get_temp('selected_professional')
            search_date = session.get_temp('search_date')

            session.transition_to(ConversationState.CLIENT_VIEW_DETAIL_WITH_BOOKING)
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
        
        # ── Anti-spam en booking ──────────────────────────────────────────────
        from src.core.booking_limiter import booking_limiter
        if not booking_limiter.record_attempt(session.phone_number):
            logger.warning(
                f"[BOOKING] 🚨 Anti-spam activado para {session.phone_number}"
            )
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            from src.config.domain_config import DomainConfig
            return (
                f"⚠️ Realizaste demasiados intentos de reserva en poco tiempo.\n\n"
                f"Por favor esperá {DomainConfig.BOOKING_ATTEMPT_BLOCK_MINUTES} minutos "
                f"e intentá de nuevo."
            )
        # ── Fin anti-spam ─────────────────────────────────────────────────────

        # Get booking data
        professional = session.get_temp('selected_professional')
        booking_date = session.get_temp('booking_date')
        booking_start_time = session.get_temp('booking_start_time')
        booking_end_time = session.get_temp('booking_end_time')

        if not all([professional, booking_date, booking_start_time, booking_end_time]):
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return "❌ Error: Información incompleta.\n\n" + client_messages.CLIENT_MAIN_MENU

        # Obtener nombre del cliente
        client = db.get_client(session.phone_number)
        client_name = client.get('name') if client else None

        # GAP 0 — Pedir nombre SOLO si el turno es para sí mismo y no tiene nombre
        # Si es para un tercero, el nombre del paciente se captura en el GAP 2
        from src.config.filter_config import FeatureFlags
        booking_for_other = (FeatureFlags.THIRD_PARTY_BOOKING
                             and session.get_temp('booking_for') == 'other')
        if not client_name and not booking_for_other:
            session.set_temp('pending_action', 'confirm_booking')
            session.transition_to(ConversationState.CLIENT_COLLECT_OWN_NAME)
            return appointment_messages.CLIENT_BOOKING_COLLECT_NAME

        client_name = client_name or 'Cliente'

        # GAP 2 — Si es para un tercero y aún no recolectamos sus datos, hacerlo ahora
        if (booking_for_other and not session.get_temp('third_party_data_collected')):
            relation = session.get_temp('third_party_relation') or 'familiar'
            session.transition_to(ConversationState.CLIENT_THIRD_PARTY_NAME)
            return (
                f"El turno es para tu {relation}.\n\n"
                f"👤 *Nombre del paciente*\n\n"
                f"¿Cuál es el nombre completo de tu {relation}?\n\n"
                f"Ejemplo: Juan Pérez\n\n"
                f"_Escribe *0* para cancelar_"
            )

        professional_phone = professional['phone']

        # ── Validación global: límite de turnos en todo el sistema ──────────────
        # Se ejecuta primero — consulta más barata (sin filtro por profesional).
        global_count = db.count_active_appointments_for_client(
            client_phone=session.phone_number
        )

        if global_count >= DomainConfig.MAX_ACTIVE_APPOINTMENTS_GLOBAL_PER_CLIENT:
            print(f"[CLIENT] ⚠️ Límite global alcanzado: {session.phone_number} "
                f"tiene {global_count} turnos activos en total")
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return appointment_messages.BOOKING_LIMIT_GLOBAL.format(
                count=global_count,
                s='s' if global_count > 1 else '',
            )
        # ── Fin validación global ────────────────────────────────────────────────

        # ── Validación por profesional: protege agenda individual ───────────────
        active_count = db.count_active_appointments_for_client_with_professional(
            client_phone=session.phone_number,
            professional_phone=professional_phone
        )

        if active_count >= DomainConfig.MAX_ACTIVE_APPOINTMENTS_PER_CLIENT_PER_PROFESSIONAL:
            print(f"[CLIENT] ⚠️ Límite por profesional alcanzado: {session.phone_number} "
                f"tiene {active_count} turnos activos con {professional_phone}")
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            prof_name = professional.get('name', 'este profesional')
            return appointment_messages.BOOKING_LIMIT_PER_PROFESSIONAL.format(
                count=active_count,
                s='s' if active_count > 1 else '',
                prof_name=prof_name,
            )
        # ── Fin validación por profesional ───────────────────────────────────────

        try:
            # GAP 3 — Construir notes estructurado con datos del tercero
            notes = None
            patient_phone = None
            if session.get_temp('booking_for') == 'other':
                from src.config.filter_config import FeatureFlags
                if FeatureFlags.THIRD_PARTY_BOOKING:
                    relation  = session.get_temp('third_party_relation') or 'tercero'
                    tp_name   = session.get_temp('third_party_name')
                    tp_age    = session.get_temp('third_party_age')
                    parts     = [f"Turno para: {relation}"]
                    if tp_name: parts.append(f"Nombre: {tp_name}")
                    if tp_age:  parts.append(f"Edad: {tp_age}")
                    notes = " | ".join(parts)
                    # GAP 4 — patient_phone para notificación dual y cancelación
                    patient_phone = session.get_temp('third_party_phone')
                    print(f"[CLIENT] 📋 Tercero: {notes} | patient_phone: {patient_phone}")

            # Crear en Google Calendar
            google_event_id = appointment_service.create_appointment(
                client_phone=session.phone_number,
                client_name=client_name,
                professional_phone=professional['phone'],
                date=booking_date,
                start_time=booking_start_time,
                end_time=booking_end_time,
                appointment_type="Consulta",
                notes=notes,
                patient_phone=patient_phone
            )
            appointment_id = google_event_id

            # ── Slot concurrente — otro usuario tomó este horario ──────────
            if appointment_id == -1:
                session.clear_temp()
                session.transition_to(ConversationState.CLIENT_MAIN_MENU)
                return (
                    "⚠️ Ese horario acaba de ser tomado por otro paciente "
                    "mientras confirmabas.\n\n"
                    "Escribí *buscar* para ver los horarios disponibles actualizados."
                )

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
            return appointment_messages.BOOKING_ERROR

        session.set_temp('appointment_id', appointment_id)
        session.transition_to(ConversationState.CLIENT_BOOKING_CONFIRMED)

        # Format success message
        date_obj = datetime.strptime(booking_date, "%Y-%m-%d")
        date_formatted = date_obj.strftime("%d/%m/%Y")
        day_names = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        day_name = day_names[date_obj.weekday()]

        prof_name = professional.get('name', 'Profesional')
        prof_phone = professional.get('phone', '')

        # GAP 6 — Línea de paciente en el mensaje de éxito
        from src.config.filter_config import FeatureFlags
        booking_for_info = ""
        if FeatureFlags.THIRD_PARTY_BOOKING and session.get_temp('booking_for') == 'other':
            relation = session.get_temp('third_party_relation') or 'familiar'
            tp_name  = session.get_temp('third_party_name')
            name_str = f" — {tp_name}" if tp_name else ""
            booking_for_info = f"\n    👤 Paciente: tu {relation}{name_str}"

        # Leer meet_link del appointment recién creado
        apt_data = db.get_appointment(int(appointment_id)) if appointment_id else None
        meet_link = apt_data.get('meet_link') if apt_data else None
        meet_line = f"🎥 {meet_link}\n\n" if meet_link else ""

        return appointment_messages.BOOKING_SUCCESS.format(
            slot_name_upper=DomainConfig.APPOINTMENT_NAME_UPPER,
            slot_name_plural=DomainConfig.APPOINTMENT_NAME_PLURAL,
            patient_line=booking_for_info,
            emoji_prof=DomainConfig.EMOJI_PROFESSIONAL,
            prof_name=prof_name,
            day=day_name,
            date=date_formatted,
            start=booking_start_time,
            meet_line=meet_line,
        )
    
    def _handle_third_party_escape(self, session: SessionData, message: str):
        """
        Helper compartido — detecta si el usuario quiere escapar del flujo de tercero.

        Retorna:
            str  → respuesta a enviar (escape activado)
            None → no es escape, continuar el handler normal

        Reglas:
            0 / volver / atrás  → volver UN paso (el handler decide a dónde)
            cancelar / menu / menú / salir / ir al menu → menú principal
        """
        msg = message.strip().lower()
        IR_AL_MENU = {'cancelar', 'menu', 'menú', 'salir', 'ir al menu', 'ir al menú', 'inicio'}
        if msg in IR_AL_MENU:
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return client_messages.CLIENT_MAIN_MENU
        return None  # no es escape global

    def handle_client_third_party_choice(self, session: SessionData, message: str) -> str:
        """
        GAP 2 — Paso 1: recolectar datos del paciente real.

        Siempre pedimos al menos el nombre del paciente.
        El teléfono es opcional pero habilita el recordatorio dual.
        """
        # Escape global
        escape = self._handle_third_party_escape(session, message)
        if escape: return escape

        relation = session.get_temp('third_party_relation') or 'familiar'
        msg = message.strip().lower()

        if msg in {'0', 'volver', 'atrás', 'atras'}:
            session.transition_to(ConversationState.CLIENT_VIEW_DETAIL_WITH_BOOKING)
            professional = session.get_temp('selected_professional')
            search_date  = session.get_temp('search_date')
            time_pref    = session.get_temp('time_preference')
            return client_service.format_professional_detail_with_slots(
                professional=professional,
                date_str=search_date,
                time_preference=time_pref
            )

        # Cualquier otra entrada avanza al nombre
        if len(msg) > 0:
            session.transition_to(ConversationState.CLIENT_THIRD_PARTY_NAME)
            return appointment_messages.THIRD_PARTY_INTRO.format(relation=relation)

    def handle_client_third_party_name(self, session: SessionData, message: str) -> str:
        """
        GAP 2 — Paso 2: nombre completo del tercero (obligatorio).
        """
        # Escape global
        escape = self._handle_third_party_escape(session, message)
        if escape: return escape

        if message.strip().lower() in {'0', 'volver', 'atrás', 'atras'}:
            # Volver un paso — a los horarios del profesional
            session.set_temp('third_party_data_collected', None)
            session.transition_to(ConversationState.CLIENT_VIEW_DETAIL_WITH_BOOKING)
            professional = session.get_temp('selected_professional')
            search_date  = session.get_temp('search_date')
            time_preference = session.get_temp('time_preference')
            return client_service.format_professional_detail_with_slots(
                professional=professional,
                date_str=search_date,
                time_preference=time_preference
            )

        validation = validate_name(message)
        if not validation.valid:
            return (
                f"⚠️ {validation.error}\n\n"
                "Ejemplo: Juan Pérez\n\n"
                "_Escribe *0* para volver · *cancelar* para salir_"
            )
        name = validation.value  # normalizado en Title Case
        session.set_temp('third_party_name', name)
        session.transition_to(ConversationState.CLIENT_THIRD_PARTY_PHONE)
        relation = session.get_temp('third_party_relation') or 'familiar'
        return appointment_messages.THIRD_PARTY_PHONE.format(name=name, relation=relation)

    def handle_client_third_party_phone(self, session: SessionData, message: str) -> str:
        """
        GAP 2 — Paso 3: teléfono del tercero (opcional).
        """
        # Escape global
        escape = self._handle_third_party_escape(session, message)
        if escape: return escape

        name = session.get_temp('third_party_name', 'el paciente')

        if message.strip().lower() in {'0', 'volver', 'atrás', 'atras'}:
            # Volver al nombre
            session.transition_to(ConversationState.CLIENT_THIRD_PARTY_NAME)
            relation = session.get_temp('third_party_relation') or 'familiar'
            return appointment_messages.THIRD_PARTY_INTRO.format(relation=relation)

        if message.lower() == 'saltar':
            session.set_temp('third_party_phone', None)
        else:
            phone_validation = validate_phone_ar(message)
            if not phone_validation.valid:
                return (
                    f"⚠️ {phone_validation.error}\n\n"
                    "• Escribí el teléfono (ej: 1112345678)\n"
                    "• O enviá *saltar* para omitir\n\n"
                    "_Escribe *0* para volver · *cancelar* para salir_"
                )
            session.set_temp('third_party_phone', phone_validation.value)  # normalizado

        session.transition_to(ConversationState.CLIENT_THIRD_PARTY_AGE)
        return appointment_messages.THIRD_PARTY_AGE.format(name=name)

    def handle_client_third_party_age(self, session: SessionData, message: str) -> str:
        """
        GAP 2 — Paso 4: edad del tercero (opcional).
        Último paso — retoma confirmación del turno.
        """
        # Escape global
        escape = self._handle_third_party_escape(session, message)
        if escape: return escape

        name = session.get_temp('third_party_name', 'el paciente')

        if message.strip().lower() in {'0', 'volver', 'atrás', 'atras'}:
            # Volver al teléfono
            session.transition_to(ConversationState.CLIENT_THIRD_PARTY_PHONE)
            relation = session.get_temp('third_party_relation') or 'familiar'
            return appointment_messages.THIRD_PARTY_PHONE.format(name=name, relation=relation)

        if message.lower() == 'saltar':
            session.set_temp('third_party_age', None)
        else:
            age_validation = validate_age(message)
            if not age_validation.valid:
                return (
                    f"⚠️ {age_validation.error}\n\n"
                    "• Escribí la edad (ej: 12)\n"
                    "• O enviá *saltar* para omitir\n\n"
                    "_Escribe *0* para volver · *cancelar* para salir_"
                )
            session.set_temp('third_party_age', int(age_validation.value))

        # Todos los datos recolectados — marcar y retomar confirmación
        session.set_temp('third_party_data_collected', True)
        print(
            f"[CLIENT] ✅ Datos tercero: "
            f"nombre={session.get_temp('third_party_name')} | "
            f"phone={session.get_temp('third_party_phone')} | "
            f"age={session.get_temp('third_party_age')}"
        )
        session.transition_to(ConversationState.CLIENT_CONFIRM_BOOKING)
        return self.handle_client_confirm_booking(session, '1')


    def handle_client_collect_own_name(self, session: SessionData, message: str) -> str:
        """
        GAP 0 — Captura el nombre del cliente antes de confirmar el turno.

        Se activa cuando el cliente llega a CLIENT_CONFIRM_BOOKING sin nombre
        registrado en BD. Después de guardar el nombre, retoma la confirmación.

        Flujo:
            CLIENT_CONFIRM_BOOKING (sin nombre)
                → CLIENT_COLLECT_OWN_NAME  ← acá
                → CLIENT_CONFIRM_BOOKING   (retoma con '1')
                → CLIENT_BOOKING_CONFIRMED
        """

        # Cancelar — volver al detalle del profesional
        if message == '0':
            session.transition_to(ConversationState.CLIENT_VIEW_DETAIL_WITH_BOOKING)
            professional = session.get_temp('selected_professional')
            search_date = session.get_temp('search_date')
            time_preference = session.get_temp('time_preference')
            return client_service.format_professional_detail_with_slots(
                professional=professional,
                date_str=search_date,
                time_preference=time_preference
            )

        # Validar nombre
        validation = validate_name(message)
        if not validation.valid:
            return (
                f"⚠️ {validation.error}\n\n"
                "Ejemplo: María González\n\n"
                "_Escribe *0* para cancelar_"
            )
        name = validation.value  # normalizado en Title Case

        # Guardar en BD — add_client usa ON CONFLICT DO UPDATE, seguro si ya existe
        db.add_client(phone=session.phone_number, name=name)
        print(f"[CLIENT] ✅ Nombre guardado: {session.phone_number} → {name}")

        # Retomar confirmación del turno — simular que el usuario presionó '1'
        session.transition_to(ConversationState.CLIENT_CONFIRM_BOOKING)
        return self.handle_client_confirm_booking(session, '1')

    def handle_client_booking_confirmed(self, session: SessionData, message: str) -> str:
        """
        Handle post-booking options.
        """
        if message == '1':
            # Ver mis citas
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_VIEW_APPOINTMENTS)
            return self.handle_client_view_appointments(session, 'start')
        
        elif message in ('2', '0'):
            # Nueva búsqueda o menú principal — usar menú dinámico
            # para que las opciones (con/sin "Ver mis citas") sean consistentes
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            from src.services.user_service import user_service
            return user_service.generate_welcome_message({
                'user_type': 'new',
                'name': None,
                'is_registered': False,
                'has_pending_appointments': False,
                'pending_appointments': [],
                'profile': None,
                'phone_number': session.phone_number
            })
        
        else:
            # Texto libre — resetear y reprocesar por NLU
            session.clear_temp()
            session.transition_to(ConversationState.START)
            return None