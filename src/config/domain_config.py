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
        "BUSINESS_NAME": "Belleza Connect",
        "PROFESSIONAL_TITLE": "Profesional",
        "CERTIFICATE_NAME": "credencial profesional",
        "CERTIFICATE_EXAMPLES": [
            "Certificado de capacitación",
            "Credencial profesional",
            "Documento que acredite tu experiencia"
        ],
        "CATEGORY_LABEL": "Servicio",
        "CATEGORIES": {
            "1": "Peluquería",
            "2": "Manicura",
            "3": "Maquillaje",
            "4": "Masajes",
            "5": "Depilación",
            "6": "Otro"
        },
        "CUSTOM_FIELD_1_LABEL": "Acepta Tarjetas",
        "EMOJI_PROFESSIONAL": "💇‍♀️",
        "EMOJI_CATEGORY": "💅",
        "WELCOME_TAGLINE": "Conectamos profesionales de belleza con clientes"
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
        "BUSINESS_NAME": "Fitness Connect",
        "PROFESSIONAL_TITLE": "Instructor",
        "CERTIFICATE_NAME": "certificación",
        "CERTIFICATE_EXAMPLES": [
            "Certificación de instructor",
            "Título de entrenador",
            "Credencial profesional"
        ],
        "CATEGORY_LABEL": "Especialidad",
        "CATEGORIES": {
            "1": "Personal Trainer",
            "2": "Yoga",
            "3": "Pilates",
            "4": "Crossfit",
            "5": "Nutrición Deportiva",
            "6": "Otro"
        },
        "CUSTOM_FIELD_1_LABEL": "Entrenamiento Online",
        "EMOJI_PROFESSIONAL": "💪",
        "EMOJI_CATEGORY": "🏋️",
        "WELCOME_TAGLINE": "Conectamos instructores con deportistas"
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
