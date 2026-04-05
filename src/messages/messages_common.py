"""
Common Messages
===============
Mensajes compartidos entre flujos. Leen del tono activo.
La estructura de clase se mantiene para compatibilidad con imports existentes.

Constantes de bienvenida e info del centro:
  WELCOME_NEW_USER   — primer contacto, sin nombre
  WELCOME_RETURNING  — usuario conocido, recibe {name}
  WELCOME_TAGLINE    — línea descriptiva del centro, versionada por tono
  CENTER_INFO_BODY   — bloque completo de info del centro, con variables

El WELCOME original se mantiene como fallback para cualquier
handler que aún lo use antes de migrar a las constantes nuevas.
"""

from src.config.domain_config import DomainConfig
from src.messages.loader import get_msg


class CommonMessages:

    # --------------------------------------------------
    # ERRORES Y VALIDACIONES GENÉRICAS
    # --------------------------------------------------

    @property
    def ERROR_GENERIC(self):
        return get_msg("ERROR_GENERIC")

    @property
    def ERROR_UNKNOWN_STATE(self):
        return get_msg("ERROR_UNKNOWN_STATE")

    @property
    def INVALID_OPTION(self):
        return get_msg("INVALID_OPTION")

    @property
    def INVALID_DATE(self):
        return get_msg("INVALID_DATE")

    @property
    def INVALID_TIME(self):
        return get_msg("INVALID_TIME")

    @property
    def UNKNOWN_QUERY(self):
        return get_msg("UNKNOWN_QUERY")

    @property
    def HELP_MESSAGE(self):
        return get_msg("HELP_MESSAGE")

    # --------------------------------------------------
    # WELCOME — saludo inicial
    # --------------------------------------------------

# --------------------------------------------------
    # HELPERS DE INTERPOLACIÓN — variables de dominio
    # --------------------------------------------------
    # Estas properties leen la constante del tono e interpolan
    # las variables de dominio ({appointment_plural}, etc.)
    # para que los tonos no dependan de DomainConfig directamente.

    def _interpolate_domain(self, key: str, default: str = "") -> str:
        """
        Lee la constante del tono activo e interpola variables de dominio.
        Llamado por properties que tienen {appointment_*}, {tagline}, etc.

        Hace dos pasadas:
          1. Resuelve el tagline (que puede tener {professional_plural})
          2. Interpola el template principal con el tagline ya resuelto
        """
        # Paso 1 — resolver el tagline con sus propias variables
        tagline_raw = get_msg("WELCOME_TAGLINE", DomainConfig.WELCOME_TAGLINE)
        professional_plural = getattr(
            DomainConfig, 'PROFESSIONAL_TITLE_PLURAL_LOWER',
            DomainConfig.PROFESSIONAL_TITLE_LOWER + 's'
        )
        try:
            tagline = tagline_raw.format(professional_plural=professional_plural)
        except KeyError:
            tagline = tagline_raw

        # Paso 2 — interpolar el template principal
        template = get_msg(key, default)
        try:
            return template.format(
                appointment_name    = DomainConfig.APPOINTMENT_NAME,
                appointment_plural  = DomainConfig.APPOINTMENT_NAME_PLURAL,
                appointment_upper   = DomainConfig.APPOINTMENT_NAME_UPPER,
                professional_plural = professional_plural,
                tagline             = tagline,
            )
        except KeyError:
            return template

    @property
    def WELCOME_NEW_USER(self):
        return self._interpolate_domain(
            "WELCOME_NEW_USER",
            f"👋 ¡Bienvenido/a a {DomainConfig.BUSINESS_NAME}!\n\n"
            f"{DomainConfig.WELCOME_TAGLINE}.\n\n"
            "¿Qué necesitás?"
        )

    @property
    def WELCOME_RETURNING(self):
        """
        Usuario conocido. El handler interpola {name} antes de enviar.
        Fallback: saludo genérico con nombre del negocio.
        """
        return get_msg(
            "WELCOME_RETURNING",
            "¡Hola, {name}! 👋\n\n"
            "¿Qué necesitás?"
        )

    @property
    def WELCOME_TAGLINE(self):
        """
        Línea descriptiva del centro para el canal WhatsApp.
        Interpola {professional_plural} si el tono lo usa.
        Fallback: WELCOME_TAGLINE de DomainConfig.
        """
        template = get_msg("WELCOME_TAGLINE", DomainConfig.WELCOME_TAGLINE)
        professional_plural = getattr(
            DomainConfig, 'PROFESSIONAL_TITLE_PLURAL_LOWER',
            DomainConfig.PROFESSIONAL_TITLE_LOWER + 's'
        )
        try:
            return template.format(professional_plural=professional_plural)
        except KeyError:
            return template

    # --------------------------------------------------
    # CENTER_INFO — información del centro
    # --------------------------------------------------

    @property
    def CENTER_INFO_BODY(self):
        """
        Bloque completo de información del centro.
        El handler interpola las variables antes de enviar:
          {business_name}   → DomainConfig.BUSINESS_NAME
          {tagline}         → WELCOME_TAGLINE del tono activo
          {professional_lower} → DomainConfig.PROFESSIONAL_TITLE_LOWER
          {contact_phone}   → settings o DomainConfig
          {contact_email}   → settings o DomainConfig
          {hours_weekday}   → settings o DomainConfig
          {hours_saturday}  → settings o DomainConfig
        Fallback: bloque genérico neutro.
        """
        return get_msg(
            "CENTER_INFO_BODY",
            "📋 *{business_name}*\n\n"
            "{tagline}.\n\n"
            "*¿Cómo funciona?*\n"
            "1. Elegís el {professional_lower} que necesitás\n"
            "2. Seleccionás fecha y horario\n"
            "3. Confirmás tu turno\n\n"
            "*Horarios de atención*\n"
            "📅 Lun–Vie: {hours_weekday}\n"
            "📅 Sáb: {hours_saturday}\n\n"
            "*Contacto*\n"
            "📞 {contact_phone}\n"
            "📧 {contact_email}\n\n"
            "¿Querés buscar turno ahora?\n\n"
            "1️⃣ Sí · 0️⃣ Volver al menú"
        )

    # --------------------------------------------------
    # WELCOME legacy — compatibilidad con handlers viejos
    # --------------------------------------------------

    @property
    def WELCOME(self):
        """
        Compatibilidad con handlers que aún usen WELCOME directamente.
        Redirige a WELCOME_NEW_USER.
        Migrar los handlers a WELCOME_NEW_USER / WELCOME_RETURNING.
        """
        return self.WELCOME_NEW_USER


common_messages = CommonMessages()