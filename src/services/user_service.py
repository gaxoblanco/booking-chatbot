"""
User Service
============
Servicio para identificación y gestión de usuarios.
Core del sistema de reconocimiento inteligente.
"""

import json
from datetime import datetime
from typing import Dict, Optional, List
from src.config.domain_config import DomainConfig
from src.database.database import db
from src.messages.messages_professional import professional_messages


class UserService:
    """
    Servicio centralizado para gestión de usuarios.

    Responsabilidades:
    - Identificar usuario por teléfono (profesional/cliente/nuevo)
    - Detectar intención en mensajes (NLP simple)
    - Registrar acciones para analytics
    - Obtener contexto completo del usuario
    """

    def identify_user(self, phone: str) -> Dict:
        """
        Identifica tipo de usuario y retorna contexto completo.

        Este es el método más importante del servicio. Se llama al inicio
        de cada conversación para determinar quién es el usuario y qué
        información mostrarle.

        Args:
            phone: Teléfono del usuario (formato: +5491112345678)

        Returns:
            {
                'user_type': 'client' | 'professional' | 'new',
                'name': str | None,
                'is_registered': bool,
                'has_pending_appointments': bool,
                'pending_appointments': List[Dict],
                'profile': Dict | None
            }

        Ejemplo:
            >>> user_info = user_service.identify_user("+5491112345678")
            >>> if user_info['user_type'] == 'client':
            >>>     print(f"Hola {user_info['name']}!")
        """
        with db.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Buscar en professionals
            cursor.execute(
                "SELECT * FROM professionals WHERE phone = ?", (phone,))
            professional = cursor.fetchone()

            if professional:
                # Es profesional registrado
                columns = [desc[0] for desc in cursor.description]
                prof_dict = dict(zip(columns, professional))

                appointments = self._get_professional_pending_appointments(
                    phone)

                return {
                    'user_type': 'professional',
                    'name': prof_dict.get('name'),
                    'is_registered': True,
                    'has_pending_appointments': len(appointments) > 0,
                    'pending_appointments': appointments,
                    'profile': prof_dict
                }

            # 2. Buscar en clients (cuando tengamos la tabla)
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='clients'")
            if cursor.fetchone():
                cursor.execute(
                    "SELECT * FROM clients WHERE phone = ?", (phone,))
                client = cursor.fetchone()

                if client:
                    # Es cliente registrado
                    columns = [desc[0] for desc in cursor.description]
                    client_dict = dict(zip(columns, client))

                    appointments = self._get_client_upcoming_appointments(
                        phone)

                    return {
                        'user_type': 'client',
                        'name': client_dict.get('name'),
                        'is_registered': True,
                        'has_pending_appointments': len(appointments) > 0,
                        'pending_appointments': appointments,
                        'profile': client_dict
                    }

            # 3. Usuario nuevo
            return {
                'user_type': 'new',
                'name': None,
                'is_registered': False,
                'has_pending_appointments': False,
                'pending_appointments': [],
                'profile': None
            }

    def detect_intention(self, message: str) -> str:
        """
        Detecta intención del usuario en el mensaje inicial.

        Usa keywords para determinar si el usuario quiere ser cliente
        o profesional. Si solo saluda, asume cliente por defecto.

        Args:
            message: Mensaje del usuario

        Returns:
            'professional' | 'client' | 'ambiguous'

        Ejemplos:
            >>> detect_intention("hola soy profesional")
            'professional'

            >>> detect_intention("hola")
            'client'

            >>> detect_intention("necesito turno")
            'client'
        """
        message_lower = message.lower().strip()

        # === KEYWORDS DE PROFESIONAL ===
        professional_keywords = [
            # Identificación directa
            'soy profesional', 'soy terapeuta', 'soy psicólogo',
            'soy psicologa', 'soy psicólogo', 'soy lic',
            'soy dr', 'soy dra', 'soy doctor', 'soy doctora',

            # Actividad profesional
            'trabajo como', 'atiendo pacientes', 'tengo consultorio',
            'tengo matrícula', 'estoy matriculado', 'estoy matriculada',

            # Intención de registro
            'quiero registrarme como profesional',
            'quiero unirme como profesional',
            'quiero ofrecer mis servicios',
            'quiero trabajar con ustedes'
        ]

        for keyword in professional_keywords:
            if keyword in message_lower:
                return 'professional'

        # === KEYWORDS DE CLIENTE ===
        client_keywords = [
            # Búsqueda de servicios
            'turno', 'cita', 'sesión', 'consulta',
            'busco', 'necesito', 'quiero sacar',
            'quiero agendar', 'reservar', 'coordinar',

            # Búsqueda de profesional
            'busco psicologo', 'busco psicóloga',
            'busco terapeuta', 'necesito terapia',
            'busco profesional',

            # Acciones de cliente
            'cancelar mi cita', 'reprogramar',
            'consultar disponibilidad'
        ]

        for keyword in client_keywords:
            if keyword in message_lower:
                return 'client'

        # === SALUDOS SIMPLES → CLIENTE POR DEFECTO ===
        # La mayoría de usuarios son clientes buscando servicios
        greetings = [
            'hola', 'buenos días', 'buenas tardes',
            'buenas noches', 'buenas', 'buen dia',
            'hi', 'hello', 'hey'
        ]

        if message_lower in greetings:
            return 'client'

        # === MENSAJE AMBIGUO ===
        return 'ambiguous'

    def generate_welcome_message(self, user_info: Dict) -> str:
        """
        Genera mensaje de bienvenida personalizado según contexto.

        Args:
            user_info: Resultado de identify_user()

        Returns:
            Mensaje de bienvenida personalizado
        """
        user_type = user_info['user_type']
        name = user_info['name']
        has_appointments = user_info['has_pending_appointments']

        # === PROFESIONAL REGISTRADO ===
        if user_type == 'professional':
            greeting = f"¡Hola Dr/Dra. {name}! 👋" if name else "¡Hola! 👋"

            if has_appointments:
                appointments = user_info['pending_appointments']
                count = len(appointments)

                message = f"{greeting}\n\n"
                message += f"📊 Resumen:\n"
                message += f"• {count} cita{'s' if count > 1 else ''} pendiente{'s' if count > 1 else ''} de confirmación\n\n"
                message += "¿Qué querés hacer?\n"
                message += "1️⃣ Ver citas pendientes\n"
                message += "2️⃣ Gestionar horarios\n"
                message += "3️⃣ Ver estadísticas\n"
                message += "4️⃣ Editar perfil\n"
                return message
            else:
                # Usar el menú completo de professional_messages
                return f"{greeting}\n\nTodo tranquilo por ahora.\n\n" + professional_messages.PROF_MAIN_MENU

        # === CLIENTE REGISTRADO ===
        elif user_type == 'client':
            from src.messages.messages_client import client_messages
            greeting = f"¡Hola {name}! 👋" if name else "¡Hola! 👋"

            if has_appointments:
                appointments = user_info['pending_appointments']
                next_appointment = appointments[0]

                message = f"{greeting}\n\n"
                message += "Tenés una cita próxima:\n"
                message += f"📅 {next_appointment['date']}\n"
                message += f"⏰ {next_appointment['time']} hs\n"
                message += f"👨‍⚕️ Con {next_appointment['professional_name']}\n\n"
                message += client_messages.CLIENT_MAIN_MENU
                return message
            else:
                # Usar el menú completo de client_messages
                return f"{greeting}\n\nTodo tranquilo por ahora.\n\n" + client_messages.CLIENT_MAIN_MENU

        # === USUARIO NUEVO ===
        else:

            message = f"👋 ¡Bienvenido/a a {DomainConfig.BUSINESS_NAME}!\n\n"
            message += f"{DomainConfig.WELCOME_TAGLINE}\n\n"
            message += "¿Qué querés hacer?\n\n"
            message += f"1️⃣ Buscar {DomainConfig.PROFESSIONAL_TITLE_LOWER}\n"
            message += f"   Búsqueda asistida paso a paso\n\n"
            message += f"2️⃣ Ver disponibles mañana\n"
            message += f"   {DomainConfig.PROFESSIONAL_TITLE_PLURAL} con horarios libres\n\n"
            message += f"3️⃣ Información del centro\n"
            message += f"   Conocer más sobre {DomainConfig.BUSINESS_NAME}\n\n"
            message += "Responde con el número de opción."

            return message

    def log_action(
        self,
        phone: str,
        action_type: str,
        details: Dict = None,
        session_id: str = None
    ):
        """
        Registra acción del usuario para analytics.

        Args:
            phone: Teléfono del usuario
            action_type: Tipo de acción realizada
            details: Detalles adicionales (se guarda como JSON)
            session_id: ID de sesión para agrupar acciones

        Tipos de acción comunes:
            - 'search': Usuario busca profesionales
            - 'book': Usuario agenda cita
            - 'cancel': Usuario cancela cita
            - 'reschedule': Usuario reprograma cita
            - 'view_profile': Usuario ve perfil de profesional
            - 'update_profile': Usuario actualiza su perfil

        Ejemplo:
            >>> user_service.log_action(
            ...     phone="+5491112345678",
            ...     action_type='search',
            ...     details={'filters': {'zona': 'norte', 'especialidad': 'tcc'}},
            ...     session_id='abc123'
            ... )
        """
        user_info = self.identify_user(phone)
        user_type = user_info['user_type']

        if user_type == 'new':
            user_type = 'client'  # Asumir cliente para nuevos

        # TODO: Implementar cuando tengamos la tabla user_actions
        # Por ahora, solo un placeholder
        print(f"[LOG] {phone} ({user_type}): {action_type}")
        if details:
            print(f"      Details: {json.dumps(details)}")

    # === MÉTODOS PRIVADOS ===

    def _get_professional_pending_appointments(self, phone: str) -> List[Dict]:
        """Obtiene citas pendientes de confirmación del profesional."""
        # TODO: Implementar cuando tengamos appointments completo
        # Por ahora retorna lista vacía
        return []

    def _get_client_upcoming_appointments(self, phone: str) -> List[Dict]:
        """Obtiene próximas citas confirmadas del cliente."""
        # TODO: Implementar cuando tengamos appointments completo
        # Por ahora retorna lista vacía
        return []

    def get_center_info(self) -> str:
        """
        Genera mensaje con información del centro/negocio.

        Usa configuración del dominio para mostrar información
        relevante del negocio.

        Returns:
            Mensaje con información del centro
        """
        from src.config.domain_config import DomainConfig

        message = f"{DomainConfig.EMOJI_PROFESSIONAL} *{DomainConfig.BUSINESS_NAME}*\n\n"

        # Información básica
        message += f"📋 *Sobre Nosotros*\n"
        message += f"{DomainConfig.WELCOME_TAGLINE}\n\n"

        # Especialidades/Categorías disponibles
        if DomainConfig.CATEGORIES:
            message += f"{DomainConfig.EMOJI_CATEGORY} *{DomainConfig.CATEGORY_LABEL_PLURAL}*\n"
            for key, value in DomainConfig.CATEGORIES.items():
                message += f"• {value}\n"
            message += "\n"

        # Zonas de atención
        if DomainConfig.ZONES:
            message += f"{DomainConfig.EMOJI_LOCATION} *Zonas de Atención*\n"
            for key, value in DomainConfig.ZONES.items():
                message += f"• {value}\n"
            message += "\n"

        # Información adicional
        if DomainConfig.CUSTOM_FIELD_1_ENABLED:
            message += f"✅ {DomainConfig.CUSTOM_FIELD_1_LABEL} disponible\n"

        if hasattr(DomainConfig, 'CUSTOM_FIELD_2_ENABLED') and DomainConfig.CUSTOM_FIELD_2_ENABLED:
            message += f"✅ {DomainConfig.CUSTOM_FIELD_2_LABEL} disponible\n"

        message += "\n"
        message += "💬 *¿Cómo funciona?*\n"
        message += f"1. Buscás {DomainConfig.PROFESSIONAL_TITLE_PLURAL_LOWER} según tus preferencias\n"
        message += f"2. Ves perfiles y {DomainConfig.SLOT_NAME_PLURAL} disponibles\n"
        message += f"3. Agendás tu {DomainConfig.APPOINTMENT_NAME}\n"
        message += "4. Recibís confirmación instantánea\n\n"

        message += "¿Querés buscar ahora?\n"
        message += "1️⃣ Sí, buscar\n"
        message += "0️⃣ Volver al menú"

        return message


# === SINGLETON ===
# Instancia única del servicio para usar en toda la app
user_service = UserService()
