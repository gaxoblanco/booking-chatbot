"""
User Service
============
Servicio para identificación y gestión de usuarios.
Core del sistema de reconocimiento inteligente.

VERSIÓN CON LOGS DETALLADOS PARA DEBUGGING
"""

import os
import json
from datetime import datetime
from typing import Dict, Optional, List
from src.config.domain_config import DomainConfig
from src.database.database import db
from src.messages.messages_professional import professional_messages
from src.core.logger import _sanitize

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
        Genera mensaje de bienvenida personalizado.
 
        El encabezado viene del tono activo (common_messages.WELCOME_NEW_USER
        o WELCOME_RETURNING). El menú dinámico se construye acá con
        DomainConfig para adaptarse al dominio.
 
        Args:
            user_info: debe incluir 'phone_number' para verificar citas activas.
 
        Returns:
            Encabezado del tono + menú dinámico con las opciones disponibles.
        """
        from src.database.database import db
        from datetime import datetime
        from src.messages.messages_common import common_messages
 
        user_type    = user_info.get('user_type', 'new')
        name         = user_info.get('name')           # None si usuario nuevo
        phone_number = user_info.get('phone_number', '')
 
        print(f"[USER_SERVICE] 🔍 generate_welcome_message()")
        print(f"[USER_SERVICE]    user_type: {user_type}")
        print(f"[USER_SERVICE]    name: {name!r}")
        print(f"[USER_SERVICE]    phone_number: {phone_number}")
 
        # --------------------------------------------------
        # PROFESIONAL — menú propio, no pasa por este flujo
        # --------------------------------------------------
        if user_type == 'professional':
            print(f"[USER_SERVICE] ✅ Es profesional, mostrando menú profesional")
            greeting = f"¡Hola Dr/Dra. {name}! 👋" if name else "¡Hola! 👋"
            return f"{greeting}\n\n" + professional_messages.PROF_MAIN_MENU
 
        # --------------------------------------------------
        # CLIENTE / NUEVO — verificar citas activas
        # --------------------------------------------------
        today = datetime.now().strftime("%Y-%m-%d")
        appointments = db.get_appointments_by_client(
            client_phone=phone_number,
            from_date=today
        )
        active_appointments = [
            apt for apt in appointments
            if apt['status'] in ['pendiente_confirmacion', 'confirmada']
        ]
        has_appointments = len(active_appointments) > 0
        count            = len(active_appointments)
 
        if has_appointments:
            print(f"[USER_SERVICE] ✅ Menú CON citas ({count} activas)")
        else:
            print(f"[USER_SERVICE] ℹ️ Menú SIN citas")
 
        # --------------------------------------------------
        # ENCABEZADO — viene del tono activo
        # name debe ser un string no vacío para usar WELCOME_RETURNING
        # --------------------------------------------------
        if name and name.strip():
            header = common_messages.WELCOME_RETURNING.format(name=name.strip())
            print(f"[USER_SERVICE] ✅ Bienvenida generada — usuario: con nombre")
        else:
            header = common_messages.WELCOME_NEW_USER
            print(f"[USER_SERVICE] ✅ Bienvenida generada — usuario: nuevo")
 
        # --------------------------------------------------
        # MENÚ DINÁMICO — lógica de negocio, no texto del tono
        # --------------------------------------------------
        menu  = "¿Qué querés hacer?\n\n"
        menu += f"1️⃣ Buscar {DomainConfig.PROFESSIONAL_TITLE_LOWER}\n"
        menu += f"   Búsqueda asistida paso a paso\n\n"
        menu += f"2️⃣ Ver disponibles mañana\n"
        menu += f"   {DomainConfig.PROFESSIONAL_TITLE_PLURAL} con horarios libres\n\n"
 
        if has_appointments:
            menu += f"3️⃣ Ver mis citas programadas\n"
            menu += f"   Gestionar tus {count} cita{'s' if count > 1 else ''}\n\n"
            menu += f"4️⃣ Información del centro\n"
            menu += f"   Conocer más sobre {DomainConfig.BUSINESS_NAME}\n\n"
        else:
            menu += f"3️⃣ Información del centro\n"
            menu += f"   Conocer más sobre {DomainConfig.BUSINESS_NAME}\n\n"
 
        menu += "Respondé con el número de opción."
 
        return f"{header}\n\n{menu}"
 
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
        print(f"[LOG] {_sanitize(phone)} ({user_type}): {action_type}")
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
        Genera mensaje con información del centro.
 
        El texto viene del tono activo (common_messages.CENTER_INFO_BODY).
        El contacto y los horarios se leen del .env del container.
 
        Variables de entorno usadas:
            CENTER_PHONE     — teléfono de contacto
            CENTER_EMAIL     — email de contacto
            CENTER_HOURS_WD  — horario lun-vie
            CENTER_HOURS_SAT — horario sábado
        """
        import os
        from src.messages.messages_common import common_messages
 
        contact_phone  = os.getenv("CENTER_PHONE",     "Consultá al centro directamente")
        contact_email  = os.getenv("CENTER_EMAIL",     "—")
        hours_weekday  = os.getenv("CENTER_HOURS_WD",  "9:00 - 18:00")
        hours_saturday = os.getenv("CENTER_HOURS_SAT", "9:00 - 13:00")
 
        if not contact_email:
            contact_email = "—"
 
        tagline  = common_messages.WELCOME_TAGLINE
        template = common_messages.CENTER_INFO_BODY
 
        message = template.format(
            business_name=DomainConfig.BUSINESS_NAME,
            tagline=tagline,
            professional_lower=DomainConfig.PROFESSIONAL_TITLE_LOWER,
            contact_phone=contact_phone,
            contact_email=contact_email,
            hours_weekday=hours_weekday,
            hours_saturday=hours_saturday,
        )
 
        print(f"[USER_SERVICE] ✅ Center info generada — tono activo")
        return message
    
# === SINGLETON ===
# Instancia única del servicio para usar en toda la app
user_service = UserService()