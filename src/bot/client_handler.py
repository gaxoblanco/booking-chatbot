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
from states import ConversationState, SessionData
from messages import Messages
from validators import parse_date, validate_time
from client_service import client_service
from analytics_service import analytics_service
import validators


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
    
    def __init__(self, messages: Messages):
        """
        Inicializar handler del cliente.
        
        Args:
            messages: Instancia de Messages para acceder a mensajes predefinidos
        """
        self.messages = messages
    
    # ==========================================
    # MENÚ PRINCIPAL DEL CLIENTE
    # ==========================================
    
    def handle_client_main_menu(self, session: SessionData, message: str) -> str:
        """
        Maneja menú principal del cliente.
        
        Opciones:
        1. Buscar para hoy
        2. Búsqueda avanzada (paso a paso)
        3. Búsqueda rápida (todo en 1 mensaje)
        4. Virtual (sesiones online)
        5. Presencial (por zona)
        0. Volver
        """
        if message == '1':
            # Buscar para hoy
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
    
    # ==========================================
    # FILTROS INDIVIDUALES (Búsqueda simple)
    # ==========================================
    
    def handle_client_filter_zona(self, session: SessionData, message: str) -> str:
        """Maneja filtro de zona."""
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
        """Maneja filtro de fecha - pide fecha."""
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
        """Maneja filtro de hora - acepta hora específica o mañana/tarde."""
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
        """Maneja filtro de prepaga."""
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
        """Maneja filtro de sexo."""
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
                active_list.append(f"• Especialidad: {filters['especialidad']}")
            
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
    
    def handle_client_multifilter_menu(self, session: SessionData, message: str) -> str:
        """
        Maneja menú multi-filtro.
        
        Permite al usuario ir agregando filtros uno por uno,
        y cuando tenga los que necesita, ejecutar la búsqueda.
        """
        if message == '1':
            # Zona
            session.transition_to(ConversationState.CLIENT_MULTIFILTER_ZONA)
            return self.messages.CLIENT_ASK_ZONA
        
        elif message == '2':
            # Disponibilidad (Fecha + Hora)
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
            # Especialidad
            return "📋 Especialidad (próximamente)\n\nEscribe 'menu' para volver."
        
        elif message.lower() in ['buscar', 'search', '6']:
            # Ejecutar búsqueda con filtros aplicados
            filters = session.get_temp('filters', {})
            
            if not filters:
                return "⚠️ No hay filtros aplicados.\n\n" + self.format_multifilter_menu(session)
            
            # Build search parameters
            search_params = {}
            if 'zona' in filters:
                search_params['zone'] = filters['zona']
            if 'prepaga' in filters:
                search_params['accept_prepaga'] = filters['prepaga']
            if 'sexo' in filters:
                search_params['gender'] = filters['sexo']
            
            # Search professionals
            results = client_service.search_professionals_by_filters(**search_params, limit=10)
            
            # Log search
            search_id = analytics_service.log_search(
                client_phone=session.phone_number,
                search_type='multifilter',
                search_params=filters,
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
        
        elif message == '0':
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return self.messages.CLIENT_MAIN_MENU
        
        else:
            return self.messages.INVALID_OPTION + "\n\n" + self.format_multifilter_menu(session)
    
    def handle_client_multifilter_zona(self, session: SessionData, message: str) -> str:
        """Maneja filtro de zona en modo multi-filtro."""
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
        """Maneja filtro de fecha en modo multi-filtro."""
        date_obj = parse_date(message)
        
        if not date_obj:
            return self.messages.INVALID_DATE + "\n\n" + self.messages.CLIENT_ASK_FECHA
        
        filters = session.get_temp('filters', {})
        filters['fecha'] = message
        session.store_temp('filters', filters)
        session.transition_to(ConversationState.CLIENT_MULTIFILTER_HORA)
        return self.messages.CLIENT_ASK_HORA
    
    def handle_client_multifilter_hora(self, session: SessionData, message: str) -> str:
        """Maneja filtro de hora en modo multi-filtro."""
        # Simple time validation (HH:MM)
        if not validators.validate_time(message) and message not in ['1', '2']:
            return self.messages.INVALID_TIME + "\n\n" + self.messages.CLIENT_ASK_HORA
        
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
        
        return self.messages.CLIENT_MULTIFILTER_ADDED.format(
            filter_name=f"Horario: {filters['hora']}",
            menu=self.format_multifilter_menu(session)
        )
    
    def handle_client_multifilter_prepaga(self, session: SessionData, message: str) -> str:
        """Maneja filtro de prepaga en modo multi-filtro."""
        if message == '1':
            filters = session.get_temp('filters', {})
            filters['prepaga'] = True
            session.store_temp('filters', filters)
            session.transition_to(ConversationState.CLIENT_MULTIFILTER_MENU)
            return self.messages.CLIENT_MULTIFILTER_ADDED.format(
                filter_name="Acepta Prepaga: Sí",
                menu=self.format_multifilter_menu(session)
            )
        elif message == '2':
            filters = session.get_temp('filters', {})
            filters['prepaga'] = False
            session.store_temp('filters', filters)
            session.transition_to(ConversationState.CLIENT_MULTIFILTER_MENU)
            return self.messages.CLIENT_MULTIFILTER_ADDED.format(
                filter_name="Acepta Prepaga: No",
                menu=self.format_multifilter_menu(session)
            )
        else:
            return self.messages.INVALID_OPTION + "\n\n" + self.messages.CLIENT_ASK_PREPAGA
    
    def handle_client_multifilter_sexo(self, session: SessionData, message: str) -> str:
        """Maneja filtro de sexo en modo multi-filtro."""
        if message == '1':
            filters = session.get_temp('filters', {})
            filters['sexo'] = 'm'
            session.store_temp('filters', filters)
            session.transition_to(ConversationState.CLIENT_MULTIFILTER_MENU)
            return self.messages.CLIENT_MULTIFILTER_ADDED.format(
                filter_name="Sexo: Masculino",
                menu=self.format_multifilter_menu(session)
            )
        elif message == '2':
            filters = session.get_temp('filters', {})
            filters['sexo'] = 'f'
            session.store_temp('filters', filters)
            session.transition_to(ConversationState.CLIENT_MULTIFILTER_MENU)
            return self.messages.CLIENT_MULTIFILTER_ADDED.format(
                filter_name="Sexo: Femenino",
                menu=self.format_multifilter_menu(session)
            )
        else:
            return self.messages.INVALID_OPTION + "\n\n" + self.messages.CLIENT_ASK_SEXO
    
    # ==========================================
    # BÚSQUEDA RÁPIDA (Todo en 1 mensaje)
    # ==========================================
    
    def parse_client_search_quick(self, message: str) -> dict:
        """
        Parsea mensaje de búsqueda rápida.
        
        Formatos aceptados:
        - "zona:norte fecha:15/12/2024 hora:14:00"
        - "norte, 15/12, 14:00"
        - "15/12 14:00 norte"
        
        Returns:
            Diccionario con parámetros parseados o None si es inválido
        """
        # Implementación del parser (código original de bot.py)
        # TODO: Este método tiene ~160 líneas, copiarlo desde bot.py
        # Por ahora placeholder
        return {
            'zona': 'norte',
            'fecha': '15/12/2024',
            'hora': '14:00'
        }
    
    def handle_client_search_quick(self, session: SessionData, message: str) -> str:
        """
        Maneja búsqueda rápida - todo en un mensaje.
        
        El usuario envía todos los filtros en un solo mensaje
        siguiendo el formato especificado.
        """
        params = self.parse_client_search_quick(message)
        
        if not params:
            return self.messages.INVALID_FORMAT + "\n\n" + self.messages.CLIENT_SEARCH_QUICK_FORMAT
        
        # TODO: Realizar búsqueda con parámetros
        # TODO: Log analytics
        # TODO: Formatear y retornar resultados
        
        return "🔍 Búsqueda rápida (en desarrollo)\n\nEscribe 'menu' para volver."
    
    # ==========================================
    # MOSTRAR RESULTADOS Y DETALLE
    # ==========================================
    
    def handle_client_show_results(self, session: SessionData, message: str) -> str:
        """
        Maneja vista de resultados.
        
        El usuario puede:
        - Seleccionar un número para ver detalle
        - Volver al menú
        """
        # Check for back command
        if message == '0':
            session.clear_temp()
            session.transition_to(ConversationState.CLIENT_MAIN_MENU)
            return self.messages.CLIENT_MAIN_MENU
        
        # Validate input is a number
        try:
            selection = int(message)
        except ValueError:
            return "⚠️ Por favor, ingresá un número válido.\n\nEscribe '0' para volver."
        
        # Get results from session
        results = session.get_temp('search_results', [])
        
        if not results:
            return self.messages.CLIENT_NO_RESULTS
        
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
                contact_method='view_profile'
            )
        
        # Transition and show detail
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
                return self.messages.CLIENT_MAIN_MENU
        
        elif message == '1':
            # Contact professional
            professional = session.get_temp('selected_professional')
            
            if not professional:
                return "⚠️ Error: No hay profesional seleccionado.\n\nEscribe 'menu' para volver."
            
            # Log contact
            search_id = session.get_temp('current_search_id')
            if search_id:
                analytics_service.log_contact(
                    search_id=search_id,
                    professional_phone=professional['phone'],
                    contact_method='whatsapp'
                )
            
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
