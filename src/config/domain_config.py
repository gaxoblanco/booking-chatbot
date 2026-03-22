"""
Domain Configuration
====================
Configure the bot for different business domains.
Change this file to adapt the bot to different industries without modifying core code.

Supported domains: salud, belleza, legal, educacion, fitness, hogar, etc.
"""


class DomainConfig:
    """
    Configuration for the business domain.
    Modify these values to adapt the bot to your specific industry.

    These are DEFAULT values (SALUD domain).
    Use load_preset() to switch to another domain configuration.
    """

    # ==========================================
    # DOMAIN SETTINGS
    # ==========================================

    # Domain identifier (internal use)
    DOMAIN_ID = "salud"  # salud, belleza, legal, educacion, fitness, hogar

    # Business name
    BUSINESS_NAME = "Salud Conecta"

    # ==========================================
    # TERMINOLOGY
    # ==========================================

    # How to call the service providers
    PROFESSIONAL_TITLE = "Profesional"
    PROFESSIONAL_TITLE_PLURAL = "Profesionales"
    PROFESSIONAL_TITLE_LOWER = "profesional"
    PROFESSIONAL_TITLE_PLURAL_LOWER = "profesionales"

    # How to call the credential/certificate
    CERTIFICATE_NAME = "certificado profesional"
    CERTIFICATE_NAME_PLURAL = "certificados profesionales"

    # Examples for certificate upload
    CERTIFICATE_EXAMPLES = [
        "Matrícula profesional",
        "Título habilitante",
        "Documento que acredite tu profesión"
    ]

    # ==========================================
    # CATEGORIES (Main services)
    # ==========================================

    CATEGORY_LABEL = "Especialidad"
    CATEGORY_LABEL_LOWER = "especialidad"

    CATEGORIES = {
        "1": "Médico General",
        "2": "Dentista",
        "3": "Psicólogo",
        "4": "Kinesiólogo",
        "5": "Nutricionista",
        "6": "Otro"
    }

    # Allow custom category input
    ALLOW_CUSTOM_CATEGORY = True

    # ==========================================
    # SEARCH FILTERS
    # ==========================================

    # Zone filter configuration
    ZONE_ENABLED = True
    ZONE_LABEL = "Zona"
    ZONES = {
        "norte": "Zona Norte",
        "sur": "Zona Sur"
    }

    # Gender filter configuration
    GENDER_ENABLED = True
    GENDER_LABEL = "Género"
    GENDERS = {
        "m": "Masculino",
        "f": "Femenino",
        "otro": "Otro"
    }

    # Custom field 1: Prepaga (health insurance)
    CUSTOM_FIELD_1_ENABLED = True
    CUSTOM_FIELD_1_KEY = "accept_prepaga"
    CUSTOM_FIELD_1_LABEL = "Acepta Prepaga"
    CUSTOM_FIELD_1_TYPE = "boolean"  # boolean, text, select

    # Custom field 2: (Optional - not used in base SALUD config)
    CUSTOM_FIELD_2_ENABLED = False
    CUSTOM_FIELD_2_KEY = "custom_field_2"
    CUSTOM_FIELD_2_LABEL = "Campo Personalizado 2"
    CUSTOM_FIELD_2_TYPE = "boolean"

    # ==========================================
    # REQUIRED FIELDS FOR REGISTRATION
    # ==========================================

    REQUIRED_FIELDS = ['name', 'category', 'zone']

    # ==========================================
    # AVAILABILITY SETTINGS
    # ==========================================

    # How to refer to available time slots
    SLOT_NAME = "turno"
    SLOT_NAME_PLURAL = "turnos"

    # Default search limit
    DEFAULT_SEARCH_LIMIT = 10

    # ==========================================
    # UI/UX CUSTOMIZATION
    # ==========================================

    # Emojis for branding
    EMOJI_PROFESSIONAL = "👨‍⚕️"
    EMOJI_CLIENT = "👤"
    EMOJI_CALENDAR = "📅"
    EMOJI_CERTIFICATE = "📋"
    EMOJI_LOCATION = "📍"
    EMOJI_CATEGORY = "🏥"

    # Welcome message customization
    WELCOME_TAGLINE = "Conectamos profesionales de la salud con pacientes"

    # ==========================================
    # FLOW MESSAGES CUSTOMIZATION
    # ==========================================
    # These messages are used in the conversation flow.
    # They can be overridden by domain presets.

    # Initial role selection
    ROLE_QUESTION = "¿Qué eres?"
    ROLE_OPTIONS = "1️⃣ Profesional\n2️⃣ Cliente"

    # Client menu welcome message
    CLIENT_WELCOME = "¡Hola! Te ayudo a encontrar profesionales de la salud"

    # Professional menu welcome message
    PROFESSIONAL_WELCOME = "¡Bienvenido/a! Registrá tu perfil profesional para conectar con pacientes 👋"

    # Category selection prompt (step 6 of registration)
    CATEGORY_PROMPT = "Selecciona tu especialidad:"

    # Custom category input prompt (step 7 of registration)
    CATEGORY_CUSTOM_PROMPT = "Escribí tu especialidad:"

    # Examples for custom category field
    CATEGORY_CUSTOM_EXAMPLE1 = "Traumatología deportiva"
    CATEGORY_CUSTOM_EXAMPLE2 = "Medicina general con enfoque preventivo"

    # ==========================================
    # APPOINTMENT CONFIGURATION (Sistema de Citas)
    # ==========================================

    # Terminología de citas
    APPOINTMENT_NAME = "cita"
    APPOINTMENT_NAME_PLURAL = "citas"
    APPOINTMENT_NAME_UPPER = "Cita"
    APPOINTMENT_EMOJI = "📅"

    # Duración de sesiones
    DEFAULT_DURATION_MINUTES = 50  # Duración por defecto
    ALLOW_VARIABLE_DURATION = False  # ¿Permitir diferentes duraciones?
    DURATION_OPTIONS = None  # [30, 45, 60, 90] o None si no aplica

    # Modalidad de atención
    MODALITY_OPTIONS = ['presencial', 'virtual']  # Opciones disponibles
    DEFAULT_MODALITY = 'presencial'
    ALLOW_CLIENT_CHOOSE_MODALITY = True  # ¿Cliente puede elegir?
    MODALITY_LABELS = {
        'presencial': '🏢 Presencial',
        'virtual': '💻 Virtual',
        'ambas': '🔄 Ambas'
    }

    # Restricciones de tiempo
    MIN_HOURS_ADVANCE = 24  # Mínimo anticipación para agendar (horas)
    MAX_DAYS_ADVANCE = 60   # Máximo días hacia adelante que se puede agendar
    CANCELLATION_HOURS_LIMIT = 22  # Horas mínimas de anticipación para cancelar
    RESCHEDULE_HOURS_LIMIT = 22  # Horas mínimas de anticipación para reprogramar

    # Límites de abuso — protección de agenda
    # Máximo de turnos activos simultáneos que un mismo número puede tener
    # con el mismo profesional (status: pendiente_confirmacion o confirmada)
    MAX_ACTIVE_APPOINTMENTS_PER_CLIENT_PER_PROFESSIONAL = 2
    # Máximo de turnos activos totales en todo el sistema para un mismo número
    MAX_ACTIVE_APPOINTMENTS_GLOBAL_PER_CLIENT = 5
    
    # Rate limiting — protección del webhook contra abuso
    # Máximo de mensajes permitidos por número en la ventana de tiempo
    RATE_LIMIT_MAX_MESSAGES_PER_WINDOW = 10
    # Tamaño de la ventana en segundos (60 = 1 minuto)
    RATE_LIMIT_WINDOW_SECONDS = 60
    # Minutos de bloqueo cuando se supera el límite
    RATE_LIMIT_BLOCK_MINUTES = 5

    # Agendamiento para terceros
    ALLOW_BOOKING_FOR_OTHERS = True  # ¿Permitir agendar para otra persona?
    REQUIRE_PATIENT_DATA = True  # Si es para terceros, ¿pedir datos del paciente?
    PATIENT_LABEL = "paciente"  # Cómo llamar a quien recibe el servicio
    PATIENT_LABEL_UPPER = "Paciente"

    # Recopilación de datos del cliente
    COLLECT_CLIENT_DATA = True  # ¿Pedir datos al cliente?
    REQUIRED_CLIENT_FIELDS = ['name']  # Campos obligatorios
    # Campos opcionales (pueden saltarse)
    OPTIONAL_CLIENT_FIELDS = ['email', 'age']
    CLIENT_FIELDS_LABELS = {
        'name': 'Nombre completo',
        'email': 'Email',
        'age': 'Edad',
        'gender': 'Género'
    }

    # Información adicional de la cita
    ASK_APPOINTMENT_REASON = False  # ¿Preguntar motivo de la cita?
    REASON_PROMPT = "¿Cuál es el motivo de la consulta? (opcional)"
    REASON_LABEL = "Motivo"
    REASON_REQUIRED = False  # Si True, el motivo es obligatorio

    # Confirmación de citas
    AUTO_CONFIRM_APPOINTMENTS = False  # Si True, citas se confirman automáticamente
    REQUIRE_PROFESSIONAL_APPROVAL = True  # Profesional debe confirmar manualmente

    # Mensajes de confirmación
    APPOINTMENT_PENDING_MESSAGE = "El profesional recibirá tu solicitud y la confirmará pronto."
    APPOINTMENT_CONFIRMED_MESSAGE = "Tu cita está confirmada. Te enviaremos un recordatorio."
    APPOINTMENT_CANCELLED_MESSAGE = "Tu cita ha sido cancelada exitosamente."

    # Recordatorios
    SEND_REMINDERS = True  # ¿Enviar recordatorios automáticos?
    REMINDER_24H_BEFORE = True  # Recordatorio 24 horas antes
    REMINDER_1H_BEFORE = True   # Recordatorio 1 hora antes

    # Políticas
    NO_SHOW_POLICY = "Si no asistes sin avisar, podrías perder futuros turnos."
    CANCELLATION_POLICY = f"Puedes cancelar hasta {CANCELLATION_HOURS_LIMIT} horas antes sin costo."


# ==========================================
# DOMAIN PRESETS
# ==========================================
# Quick configurations for common domains


class DomainPresets:
    """
    Pre-configured settings for common business domains.
    Copy and paste to DomainConfig to quickly switch domains.
    """

    PSICOLOGIA = {
        # ==========================================
        # IDENTIFICACIÓN DEL DOMINIO
        # ==========================================
        "DOMAIN_ID": "psicologia",
        "BUSINESS_NAME": "Psico Connect",

        # ==========================================
        # TÍTULOS PROFESIONALES
        # ==========================================
        # Cómo referirse a los proveedores del servicio
        "PROFESSIONAL_TITLE": "Psicólogo",
        "PROFESSIONAL_TITLE_PLURAL": "Psicólogos",
        "PROFESSIONAL_TITLE_LOWER": "psicólogo",
        "PROFESSIONAL_TITLE_PLURAL_LOWER": "psicólogos",

        # ==========================================
        # CREDENCIALES
        # ==========================================
        # Cómo llamar a los certificados/credenciales
        "CERTIFICATE_NAME": "matrícula profesional",
        "CERTIFICATE_NAME_PLURAL": "matrículas profesionales",
        "CERTIFICATE_EXAMPLES": [
            "Matrícula del colegio de psicólogos",
            "Título de Licenciado en Psicología",
            "Certificado de especialización"
        ],

        # ==========================================
        # CATEGORÍAS (Orientaciones terapéuticas)
        # ==========================================
        "CATEGORY_LABEL": "Orientación",
        "CATEGORY_LABEL_LOWER": "orientación",
        "CATEGORIES": {
            "1": "Psicología Clínica",
            "2": "Psicología Infantil",
            "3": "Terapia de Pareja",
            "4": "Psicología Laboral",
            "5": "Psicopedagogía",
            "6": "Neuropsicología",
            "7": "Terapia Familiar",
            "8": "Psicoanálisis",
            "9": "Terapia Cognitivo-Conductual",
            "10": "Otro"
        },
        "ALLOW_CUSTOM_CATEGORY": True,

        # ==========================================
        # FILTROS DE BÚSQUEDA
        # ==========================================
        # Filtro por zona geográfica
        "ZONE_ENABLED": True,
        "ZONE_LABEL": "Zona",
        "ZONES": {
            "norte": "Zona Norte",
            "sur": "Zona Sur",
        },

        # Filtro por género del profesional
        "GENDER_ENABLED": True,
        "GENDER_LABEL": "Género del profesional",
        "GENDERS": {
            "m": "Masculino",
            "f": "Femenino",
            "otro": "Indistinto"
        },

        # ==========================================
        # CAMPOS PERSONALIZADOS
        # ==========================================
        # Campo personalizado 1: Acepta obra social
        "CUSTOM_FIELD_1_ENABLED": False,
        "CUSTOM_FIELD_1_KEY": "accept_prepaga",
        "CUSTOM_FIELD_1_LABEL": "Acepta Obra Social",
        "CUSTOM_FIELD_1_TYPE": "boolean",

        # Campo personalizado 2: Sesiones online
        "CUSTOM_FIELD_2_ENABLED": True,
        "CUSTOM_FIELD_2_KEY": "online_sessions",
        "CUSTOM_FIELD_2_LABEL": "Sesiones Online",
        "CUSTOM_FIELD_2_TYPE": "boolean",

        # ==========================================
        # CAMPOS REQUERIDOS EN REGISTRO
        # ==========================================
        "REQUIRED_FIELDS": ['name', 'category', 'zone'],

        # ==========================================
        # CONFIGURACIÓN DE DISPONIBILIDAD
        # ==========================================
        # Cómo referirse a los turnos/espacios disponibles
        "SLOT_NAME": "sesión",
        "SLOT_NAME_PLURAL": "sesiones",
        "DEFAULT_SEARCH_LIMIT": 10,

        # ==========================================
        # PERSONALIZACIÓN UI/UX
        # ==========================================
        # Emojis para branding
        "EMOJI_PROFESSIONAL": "🧠",
        "EMOJI_CLIENT": "👤",
        "EMOJI_CALENDAR": "📅",
        "EMOJI_CERTIFICATE": "📋",
        "EMOJI_LOCATION": "📍",
        "EMOJI_CATEGORY": "🎯",

        # Mensaje de bienvenida
        "WELCOME_TAGLINE": "Conectamos psicólogos con pacientes de forma simple y rápida",

        # ==========================================
        # MENSAJES PERSONALIZADOS DEL FLUJO
        # ==========================================
        # Pregunta inicial: ¿Qué eres?
        "ROLE_QUESTION": "¿Sos paciente o psicólogo/a?",
        "ROLE_OPTIONS": "1️⃣ Paciente\n2️⃣ Psicólogo/a",

        # Saludo menú cliente
        "CLIENT_WELCOME": "¡Hola! Te ayudo a encontrar el psicólogo ideal para vos 🧠",

        # Saludo menú profesional
        "PROFESSIONAL_WELCOME": "¡Bienvenido/a! Registrá tu perfil profesional para conectar con pacientes 👋",

        # Mensaje para seleccionar especialidad (paso 6 del registro)
        "CATEGORY_PROMPT": "¿Cuál es tu orientación terapéutica principal?",

        # Mensaje para especialidad personalizada (paso 7)
        "CATEGORY_CUSTOM_EXAMPLE1": "- Trabajo infailt +10",
        "CATEGORY_CUSTOM_EXAMPLE2": "- Terapia de parejas",

        # ==========================================
        # CONFIGURACIÓN DE CITAS (Específico Psicología)
        # ==========================================
        "APPOINTMENT_NAME": "sesión",
        "APPOINTMENT_NAME_PLURAL": "sesiones",
        "APPOINTMENT_NAME_UPPER": "Sesión",
        "APPOINTMENT_EMOJI": "🧠",

        # Duración de sesiones (fija en psicología)
        "DEFAULT_DURATION_MINUTES": 50,
        "ALLOW_VARIABLE_DURATION": False,
        "DURATION_OPTIONS": None,

        # Modalidad (presencial o virtual)
        "MODALITY_OPTIONS": ['presencial', 'virtual'],
        "DEFAULT_MODALITY": 'presencial',
        "ALLOW_CLIENT_CHOOSE_MODALITY": True,
        "MODALITY_LABELS": {
            'presencial': '🏢 Presencial',
            'virtual': '💻 Virtual (Videollamada)',
            'ambas': '🔄 Ambas modalidades'
        },

        # Restricciones (24hs anticipación típico en psicología)
        "MIN_HOURS_ADVANCE": 24,
        "MAX_DAYS_ADVANCE": 45,
        "CANCELLATION_HOURS_LIMIT": 24,
        "RESCHEDULE_HOURS_LIMIT": 24,

        # Común agendar para hijos/familiares
        "ALLOW_BOOKING_FOR_OTHERS": True,
        "REQUIRE_PATIENT_DATA": True,
        "PATIENT_LABEL": "paciente",
        "PATIENT_LABEL_UPPER": "Paciente",

        # Datos del cliente
        "COLLECT_CLIENT_DATA": True,
        "REQUIRED_CLIENT_FIELDS": ['name'],
        "OPTIONAL_CLIENT_FIELDS": ['email', 'age'],

        # Motivo de consulta (útil en psicología)
        "ASK_APPOINTMENT_REASON": True,
        "REASON_PROMPT": "¿Cuál es el motivo de la consulta? Esto ayuda al profesional a prepararse mejor. (opcional)",
        "REASON_LABEL": "Motivo de consulta",
        "REASON_REQUIRED": False,

        # Confirmación manual
        "AUTO_CONFIRM_APPOINTMENTS": False,
        "REQUIRE_PROFESSIONAL_APPROVAL": True,

        # Mensajes
        "APPOINTMENT_PENDING_MESSAGE": "El psicólogo recibirá tu solicitud y la confirmará en breve.",
        "APPOINTMENT_CONFIRMED_MESSAGE": "Tu sesión está confirmada. Te recordaremos antes del turno.",
        "APPOINTMENT_CANCELLED_MESSAGE": "Tu sesión ha sido cancelada.",

        # Recordatorios
        "SEND_REMINDERS": True,
        "REMINDER_24H_BEFORE": True,
        "REMINDER_1H_BEFORE": True,

        # Políticas
        "NO_SHOW_POLICY": "Si no asistes sin avisar, se considerará como sesión tomada.",
        "CANCELLATION_POLICY": "Puedes cancelar hasta 24 horas antes. Cancelaciones con menos anticipación pueden tener cargo.",
    }

    SALUD = {
        "DOMAIN_ID": "salud",
        "BUSINESS_NAME": "Salud Conecta",
        "PROFESSIONAL_TITLE": "Profesional",
        "CERTIFICATE_NAME": "certificado profesional",
        "CERTIFICATE_EXAMPLES": [
            "Matrícula profesional",
            "Título habilitante",
            "Documento que acredite tu profesión"
        ],
        "CATEGORY_LABEL": "Especialidad",
        "CATEGORIES": {
            "1": "Médico General",
            "2": "Dentista",
            "3": "Psicólogo",
            "4": "Kinesiólogo",
            "5": "Nutricionista",
            "6": "Otro"
        },
        "CUSTOM_FIELD_1_LABEL": "Acepta Prepaga",
        "EMOJI_PROFESSIONAL": "👨‍⚕️",
        "EMOJI_CATEGORY": "🏥",
        "WELCOME_TAGLINE": "Conectamos profesionales de la salud con pacientes"
    }

    BELLEZA = {
        "DOMAIN_ID": "belleza",
        "BUSINESS_NAME": "Beauty Connect",

        # Terminología
        "PROFESSIONAL_TITLE": "Profesional",
        "PROFESSIONAL_TITLE_PLURAL": "Profesionales",
        "PROFESSIONAL_TITLE_LOWER": "profesional",
        "PROFESSIONAL_TITLE_PLURAL_LOWER": "profesionales",

        "CERTIFICATE_NAME": "certificado profesional",
        "CERTIFICATE_EXAMPLES": [
            "Certificado de cosmetología",
            "Título de estilista",
            "Licencia de manicura"
        ],

        # Categorías (servicios)
        "CATEGORY_LABEL": "Servicio",
        "CATEGORY_LABEL_LOWER": "servicio",
        "CATEGORIES": {
            "1": "Corte de cabello",
            "2": "Coloración",
            "3": "Tratamiento capilar",
            "4": "Manicura",
            "5": "Pedicura",
            "6": "Maquillaje",
            "7": "Depilación",
            "8": "Tratamiento facial",
            "9": "Otro"
        },

        # Filtros
        "ZONE_ENABLED": True,
        "GENDER_ENABLED": True,
        "CUSTOM_FIELD_1_ENABLED": False,

        # ===== CONFIGURACIÓN DE CITAS (BELLEZA) =====
        "APPOINTMENT_NAME": "turno",
        "APPOINTMENT_NAME_PLURAL": "turnos",
        "APPOINTMENT_NAME_UPPER": "Turno",
        "APPOINTMENT_EMOJI": "💇",

        # Duración VARIABLE (cada servicio dura diferente)
        "DEFAULT_DURATION_MINUTES": 60,
        "ALLOW_VARIABLE_DURATION": True,
        "DURATION_OPTIONS": [30, 45, 60, 90, 120, 180],  # Según servicio

        # Solo presencial
        "MODALITY_OPTIONS": ['presencial'],
        "DEFAULT_MODALITY": 'presencial',
        "ALLOW_CLIENT_CHOOSE_MODALITY": False,
        "MODALITY_LABELS": {
            'presencial': '🏢 En el local'
        },

        # Menos anticipación requerida (2 horas)
        "MIN_HOURS_ADVANCE": 2,
        "MAX_DAYS_ADVANCE": 30,
        "CANCELLATION_HOURS_LIMIT": 2,
        "RESCHEDULE_HOURS_LIMIT": 2,

        # Raro agendar para otros
        "ALLOW_BOOKING_FOR_OTHERS": False,
        "REQUIRE_PATIENT_DATA": False,
        "PATIENT_LABEL": "cliente",

        # Datos mínimos
        "COLLECT_CLIENT_DATA": True,
        "REQUIRED_CLIENT_FIELDS": ['name'],
        "OPTIONAL_CLIENT_FIELDS": ['email'],

        # No preguntar motivo (es obvio: el servicio elegido)
        "ASK_APPOINTMENT_REASON": False,

        # Auto-confirmar (común en belleza)
        "AUTO_CONFIRM_APPOINTMENTS": True,
        "REQUIRE_PROFESSIONAL_APPROVAL": False,

        "APPOINTMENT_PENDING_MESSAGE": "Tu turno ha sido agendado.",
        "APPOINTMENT_CONFIRMED_MESSAGE": "Tu turno está confirmado. Te esperamos!",

        "SEND_REMINDERS": True,
        "REMINDER_24H_BEFORE": True,
        "REMINDER_1H_BEFORE": False,

        "CANCELLATION_POLICY": "Puedes cancelar hasta 2 horas antes.",
    }

    LEGAL = {
        "DOMAIN_ID": "legal",
        "BUSINESS_NAME": "Legal Connect",
        "PROFESSIONAL_TITLE": "Abogado",
        "CERTIFICATE_NAME": "matrícula profesional",
        "CERTIFICATE_EXAMPLES": [
            "Matrícula de abogado",
            "Título de abogado",
            "Credencial profesional"
        ],
        "CATEGORY_LABEL": "Especialización",
        "CATEGORIES": {
            "1": "Derecho Penal",
            "2": "Derecho Civil",
            "3": "Derecho Laboral",
            "4": "Derecho de Familia",
            "5": "Derecho Comercial",
            "6": "Otro"
        },
        "CUSTOM_FIELD_1_LABEL": "Consulta Gratuita",
        "EMOJI_PROFESSIONAL": "⚖️",
        "EMOJI_CATEGORY": "📜",
        "WELCOME_TAGLINE": "Conectamos abogados con clientes"
    }

    FITNESS = {
        "DOMAIN_ID": "fitness",
        "BUSINESS_NAME": "Fit Connect",

        "PROFESSIONAL_TITLE": "Entrenador",
        "PROFESSIONAL_TITLE_PLURAL": "Entrenadores",
        "PROFESSIONAL_TITLE_LOWER": "entrenador",
        "PROFESSIONAL_TITLE_PLURAL_LOWER": "entrenadores",

        "CERTIFICATE_NAME": "certificación",
        "CERTIFICATE_EXAMPLES": [
            "Certificación de entrenador personal",
            "Título de profesor de educación física"
        ],

        "CATEGORY_LABEL": "Especialidad",
        "CATEGORIES": {
            "1": "Entrenamiento funcional",
            "2": "Musculación",
            "3": "CrossFit",
            "4": "Yoga",
            "5": "Pilates",
            "6": "Running",
            "7": "Otro"
        },

        # ===== CONFIGURACIÓN DE CITAS (FITNESS) =====
        "APPOINTMENT_NAME": "clase",
        "APPOINTMENT_NAME_PLURAL": "clases",
        "APPOINTMENT_NAME_UPPER": "Clase",
        "APPOINTMENT_EMOJI": "💪",

        "DEFAULT_DURATION_MINUTES": 60,
        "ALLOW_VARIABLE_DURATION": True,
        "DURATION_OPTIONS": [45, 60, 90],

        "MODALITY_OPTIONS": ['presencial', 'virtual'],
        "ALLOW_CLIENT_CHOOSE_MODALITY": True,

        # Menos anticipación (1 hora)
        "MIN_HOURS_ADVANCE": 1,
        "MAX_DAYS_ADVANCE": 30,
        "CANCELLATION_HOURS_LIMIT": 1,
        "RESCHEDULE_HOURS_LIMIT": 2,

        # Personal (raro para otros)
        "ALLOW_BOOKING_FOR_OTHERS": False,

        "COLLECT_CLIENT_DATA": True,
        "REQUIRED_CLIENT_FIELDS": ['name', 'age'],  # Edad importante
        "OPTIONAL_CLIENT_FIELDS": ['email'],

        "ASK_APPOINTMENT_REASON": False,

        # Auto-confirmar
        "AUTO_CONFIRM_APPOINTMENTS": True,
        "REQUIRE_PROFESSIONAL_APPROVAL": False,

        "SEND_REMINDERS": True,
        "REMINDER_24H_BEFORE": False,
        "REMINDER_1H_BEFORE": True,  # Solo 1h antes

        "CANCELLATION_POLICY": "Puedes cancelar hasta 1 hora antes.",
    }

    EDUCACION = {
        "DOMAIN_ID": "educacion",
        "BUSINESS_NAME": "Educa Connect",
        "PROFESSIONAL_TITLE": "Profesor",
        "CERTIFICATE_NAME": "título docente",
        "CERTIFICATE_EXAMPLES": [
            "Título docente",
            "Certificado de enseñanza",
            "Credencial educativa"
        ],
        "CATEGORY_LABEL": "Materia",
        "CATEGORIES": {
            "1": "Matemática",
            "2": "Lengua",
            "3": "Inglés",
            "4": "Física",
            "5": "Química",
            "6": "Otro"
        },
        "CUSTOM_FIELD_1_LABEL": "Clases Online",
        "EMOJI_PROFESSIONAL": "👨‍🏫",
        "EMOJI_CATEGORY": "📚",
        "WELCOME_TAGLINE": "Conectamos profesores con estudiantes"
    }

    HOGAR = {
        "DOMAIN_ID": "hogar",
        "BUSINESS_NAME": "Hogar Services",
        "PROFESSIONAL_TITLE": "Profesional",
        "CERTIFICATE_NAME": "credencial",
        "CERTIFICATE_EXAMPLES": [
            "Certificado de capacitación",
            "Credencial profesional",
            "Referencias laborales"
        ],
        "CATEGORY_LABEL": "Servicio",
        "CATEGORIES": {
            "1": "Plomería",
            "2": "Electricidad",
            "3": "Carpintería",
            "4": "Pintura",
            "5": "Limpieza",
            "6": "Otro"
        },
        "CUSTOM_FIELD_1_LABEL": "Servicio de Urgencia",
        "EMOJI_PROFESSIONAL": "🔧",
        "EMOJI_CATEGORY": "🏠",
        "WELCOME_TAGLINE": "Conectamos profesionales del hogar con clientes"
    }


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def get_category_name(category_key: str) -> str:
    """
    Get category display name from key.

    Args:
        category_key: Category key (e.g., "1", "medico_general")

    Returns:
        Category display name
    """
    return DomainConfig.CATEGORIES.get(category_key, category_key)


def get_zone_name(zone_key: str) -> str:
    """
    Get zone display name from key.

    Args:
        zone_key: Zone key (e.g., "norte", "sur")

    Returns:
        Zone display name
    """
    return DomainConfig.ZONES.get(zone_key, zone_key)


def get_gender_name(gender_key: str) -> str:
    """
    Get gender display name from key.

    Args:
        gender_key: Gender key (e.g., "m", "f", "otro")

    Returns:
        Gender display name
    """
    return DomainConfig.GENDERS.get(gender_key, gender_key)


def format_custom_field_1(value: bool) -> str:
    """
    Format custom field 1 value for display.

    Args:
        value: Boolean value

    Returns:
        Formatted string
    """
    return "Sí" if value else "No"

# ==========================================
# AUTO-LOAD PRESET
# ==========================================


def load_preset(preset_name: str):
    """
    Load a preset configuration into DomainConfig and persist it.

    Args:
        preset_name: Name of preset (e.g., 'PSICOLOGIA', 'SALUD')

    Usage:
        load_preset('PSICOLOGIA')
    """
    if not hasattr(DomainPresets, preset_name):
        available = [p for p in dir(DomainPresets) if not p.startswith('_')]
        raise ValueError(
            f"Preset '{preset_name}' not found. Available: {', '.join(available)}")

    preset = getattr(DomainPresets, preset_name)

    # Apply to DomainConfig class
    for key, value in preset.items():
        setattr(DomainConfig, key, value)

    print(f"✅ Loaded preset: {preset_name}")
