"""
Common Messages
===============
Mensajes base y comunes del bot.
Incluye: bienvenida, validaciones, errores, helpers generales.
"""

from src.config.domain_config import DomainConfig


class CommonMessages:
    """
    Mensajes comunes y base del bot.
    Usados por todos los flujos.
    """

    # ==========================================
    # WELCOME & ROLE SELECTION
    # ==========================================

    WELCOME = f"""👋 ¡Bienvenido a {DomainConfig.BUSINESS_NAME}!

{DomainConfig.WELCOME_TAGLINE}

{DomainConfig.ROLE_QUESTION}
{DomainConfig.ROLE_OPTIONS}
Responde con 1 o 2."""

    INVALID_ROLE = f"""❌ Opción inválida.

Por favor responde:
{DomainConfig.ROLE_OPTIONS}"""

    # ==========================================
    # NAVIGATION & SYSTEM MESSAGES
    # ==========================================

    BACK_TO_MENU = "Volviendo al menú principal..."

    OPERATION_CANCELLED = """❌ Operación cancelada

Volviendo al menú principal..."""

    SESSION_RESET = """🔄 Sesión reiniciada

Volviendo al inicio..."""

    # ==========================================
    # VALIDATION MESSAGES
    # ==========================================

    INVALID_OPTION = """❌ Opción inválida

Por favor, selecciona una opción válida del menú."""

    INVALID_INPUT = """❌ Entrada inválida

Por favor, verifica tu respuesta e intenta nuevamente."""

    INVALID_DATE = """❌ Fecha inválida

Formato correcto: DD/MM/YYYY
Ejemplo: 15/12/2024

Por favor, ingresa una fecha válida."""

    INVALID_TIME = """❌ Horario inválido

Formato correcto: HH:MM-HH:MM
Ejemplo: 14:00-15:00

El formato debe ser 24 horas.
Por favor, ingresa un horario válido."""

    INVALID_EMAIL = """❌ Email inválido

Formato correcto: usuario@ejemplo.com
Ejemplo: maria@gmail.com

Por favor, ingresa un email válido."""

    INVALID_PHONE = """❌ Número de teléfono inválido

Formato correcto: +5491112345678
Debe incluir código de país.

Por favor, ingresa un número válido."""

    INVALID_NUMBER = """❌ Número inválido

Por favor, ingresa un número válido."""

    DATE_IN_PAST = """❌ Fecha inválida

La fecha debe ser futura.
No se pueden agendar fechas pasadas."""

    DATE_TOO_FAR = f"""❌ Fecha demasiado lejana

Solo se pueden agendar {DomainConfig.APPOINTMENT_NAME_PLURAL} hasta {{max_days}} días adelante.

Por favor, elige una fecha más cercana."""

    TIME_SLOT_UNAVAILABLE = """❌ Horario no disponible

Este horario ya no está disponible.
Por favor, elige otro horario."""

    # ==========================================
    # ERROR MESSAGES
    # ==========================================

    ERROR_GENERIC = """❌ Error

Ocurrió un error inesperado. Por favor, intenta nuevamente.

Si el problema persiste, escribe 'ayuda'."""

    ERROR_DATABASE = """❌ Error de Base de Datos

Hubo un problema al guardar los datos.
Por favor, intenta nuevamente en unos momentos.

Si el problema persiste, contacta al administrador."""

    ERROR_FILE_UPLOAD = """❌ Error al subir archivo

No se pudo procesar el archivo.

Por favor:
• Verifica que sea una imagen (JPG, PNG, PDF)
• Verifica que no sea muy grande (máx 5MB)
• Intenta nuevamente"""

    ERROR_NETWORK = """❌ Error de Conexión

Hubo un problema de conexión.
Por favor, intenta nuevamente en unos momentos."""

    # ==========================================
    # HELP & INFO
    # ==========================================

    HELP_MESSAGE = """ℹ️ Ayuda - Comandos Disponibles

🏠 Navegación:
• 'inicio' - Volver al inicio (elegir rol)
• 'menu' - Volver al menú de tu rol
• 'cancelar' - Cancelar operación actual
• 'volver' - Volver al paso anterior

ℹ️ Información:
• 'ayuda' o '?' - Ver este mensaje

💡 Tip: Puedes usar estos comandos en cualquier momento."""

    ABOUT_SERVICE = f"""ℹ️ Acerca de {DomainConfig.BUSINESS_NAME}

{DomainConfig.WELCOME_TAGLINE}

📞 Contacto:
• WhatsApp: Este chat
• Email: info@{DomainConfig.DOMAIN_ID}.com

🕐 Horario de atención:
• Lunes a Viernes: 9:00 - 18:00hs
• Sábados: 9:00 - 13:00hs

_Escribe *0* para volver_"""

    # ==========================================
    # CONFIRMATION MESSAGES
    # ==========================================

    CONFIRM_ACTION = """⚠️ Confirmar Acción

¿Estás seguro que deseas continuar?

1️⃣ Sí, continuar
0️⃣ No, cancelar"""

    ACTION_CONFIRMED = """✅ Confirmado

Procesando tu solicitud..."""

    ACTION_CANCELLED = """❌ Cancelado

Operación cancelada. Volviendo al menú..."""

    # ==========================================
    # LOADING & PROCESSING
    # ==========================================

    LOADING = """⏳ Procesando...

Por favor espera un momento."""

    SEARCHING = """🔍 Buscando...

Estamos buscando los mejores resultados para ti."""

    SAVING = """💾 Guardando...

Guardando tus datos."""

    # ==========================================
    # SUCCESS MESSAGES
    # ==========================================

    SAVED_SUCCESSFULLY = """✅ Guardado exitosamente

Tus datos han sido guardados correctamente."""

    UPDATED_SUCCESSFULLY = """✅ Actualizado exitosamente

Tus datos han sido actualizados correctamente."""

    DELETED_SUCCESSFULLY = """✅ Eliminado exitosamente

El registro ha sido eliminado."""

    # ==========================================
    # HELPER METHODS - FORMATTERS
    # ==========================================

    @staticmethod
    def format_day_name(day_number: int) -> str:
        """
        Convertir número de día a nombre en español.

        Args:
            day_number: Número del día (1-7, donde 1=Lunes)

        Returns:
            Nombre del día en español
        """
        days = {
            1: "Lunes",
            2: "Martes",
            3: "Miércoles",
            4: "Jueves",
            5: "Viernes",
            6: "Sábado",
            7: "Domingo"
        }
        return days.get(day_number, "Día inválido")

    @staticmethod
    def format_month_name(month_number: int) -> str:
        """
        Convertir número de mes a nombre en español.

        Args:
            month_number: Número del mes (1-12)

        Returns:
            Nombre del mes en español
        """
        months = {
            1: "Enero",
            2: "Febrero",
            3: "Marzo",
            4: "Abril",
            5: "Mayo",
            6: "Junio",
            7: "Julio",
            8: "Agosto",
            9: "Septiembre",
            10: "Octubre",
            11: "Noviembre",
            12: "Diciembre"
        }
        return months.get(month_number, "Mes inválido")

    @staticmethod
    def format_date_natural(date_str: str) -> str:
        """
        Formatear fecha en formato natural legible.

        Args:
            date_str: Fecha en formato YYYY-MM-DD o DD/MM/YYYY

        Returns:
            Fecha formateada (ej: "Lunes 15 de Diciembre de 2024")
        """
        from datetime import datetime

        try:
            # Intentar parsear diferentes formatos
            if '/' in date_str:
                date_obj = datetime.strptime(date_str, "%d/%m/%Y")
            elif '-' in date_str:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            else:
                return date_str

            day_name = CommonMessages.format_day_name(date_obj.isoweekday())
            month_name = CommonMessages.format_month_name(date_obj.month)

            return f"{day_name} {date_obj.day} de {month_name} de {date_obj.year}"
        except:
            return date_str

    @staticmethod
    def format_time_12h(time_str: str) -> str:
        """
        Formatear hora a formato 12 horas con AM/PM.

        Args:
            time_str: Hora en formato HH:MM (24h)

        Returns:
            Hora formateada en 12h (ej: "2:00 PM")
        """
        from datetime import datetime

        try:
            time_obj = datetime.strptime(time_str, "%H:%M")
            return time_obj.strftime("%I:%M %p").lstrip('0')
        except:
            return time_str

    @staticmethod
    def format_time_24h(time_str: str) -> str:
        """
        Formatear hora con sufijo 'hs'.

        Args:
            time_str: Hora en formato HH:MM

        Returns:
            Hora formateada (ej: "14:00hs")
        """
        return f"{time_str}hs"

    @staticmethod
    def format_zona(zona: str) -> str:
        """
        Formatear nombre de zona.

        Args:
            zona: Identificador de zona

        Returns:
            Nombre formateado de la zona
        """
        zonas = {
            "norte": "Zona Norte",
            "sur": "Zona Sur",
            "indistinto": "Cualquier zona"
        }
        return zonas.get(zona.lower(), zona.title())

    @staticmethod
    def format_gender(gender: str) -> str:
        """
        Formatear género.

        Args:
            gender: Código de género

        Returns:
            Género formateado
        """
        genders = {
            "m": "Masculino",
            "f": "Femenino",
            "otro": "Otro",
            "prefiero_no_decir": "Prefiero no decir"
        }
        return genders.get(gender.lower(), gender.title())

    @staticmethod
    def format_boolean(value: bool) -> str:
        """
        Formatear valor booleano.

        Args:
            value: Valor booleano

        Returns:
            "Sí" o "No"
        """
        return "Sí" if value else "No"

    @staticmethod
    def truncate_text(text: str, max_length: int = 100) -> str:
        """
        Truncar texto a longitud máxima.

        Args:
            text: Texto a truncar
            max_length: Longitud máxima

        Returns:
            Texto truncado con "..." si excede la longitud
        """
        if len(text) <= max_length:
            return text
        return text[:max_length - 3] + "..."

    # ==========================================
    # HELPER METHODS - VALIDATORS
    # ==========================================

    @staticmethod
    def validate_date_format(date_str: str) -> bool:
        """
        Validar formato de fecha DD/MM/YYYY.

        Args:
            date_str: Fecha a validar

        Returns:
            True si es válida, False si no
        """
        from datetime import datetime

        try:
            datetime.strptime(date_str, "%d/%m/%Y")
            return True
        except:
            return False

    @staticmethod
    def validate_time_format(time_str: str) -> bool:
        """
        Validar formato de hora HH:MM.

        Args:
            time_str: Hora a validar

        Returns:
            True si es válida, False si no
        """
        from datetime import datetime

        try:
            datetime.strptime(time_str, "%H:%M")
            return True
        except:
            return False

    @staticmethod
    def validate_email_format(email: str) -> bool:
        """
        Validar formato de email.

        Args:
            email: Email a validar

        Returns:
            True si es válido, False si no
        """
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))


# Singleton instance
common_messages = CommonMessages()
