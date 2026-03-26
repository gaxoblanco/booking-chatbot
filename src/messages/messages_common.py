"""
Common Messages v3.0
====================
Mensajes compartidos entre diferentes flujos del bot.

CAMBIOS EN v3.0:
- ❌ Eliminado: WELCOME con pregunta de rol
- ❌ Eliminado: INVALID_ROLE
- ✅ Simplificado: Mensajes genéricos de error y ayuda
"""

from src.config.domain_config import DomainConfig


class CommonMessages:
    """
    Mensajes comunes del bot.
    
    Mensajes de error, validación y ayuda usados en todo el sistema.
    """

    # ==========================================
    # MENSAJES DE BIENVENIDA
    # ==========================================
    
    # ❌ DEPRECATED en v3.0 - Ya no preguntamos rol
    # WELCOME = """
    # 👋 ¡Bienvenido/a!
    # 
    # ¿Qué eres?
    # 1️⃣ Cliente
    # 2️⃣ Profesional
    # """
    
    # ✅ NUEVO - Solo para casos excepcionales de fallback
    WELCOME = f"""
👋 ¡Bienvenido/a a {DomainConfig.BUSINESS_NAME}!

{DomainConfig.WELCOME_TAGLINE}

Escribe "hola" para comenzar.
"""

    # ==========================================
    # MENSAJES DE ERROR
    # ==========================================

    ERROR_GENERIC = """
❌ Lo siento, ocurrió un error inesperado.

Por favor intenta nuevamente o escribe "ayuda" para más opciones.
"""

    ERROR_UNKNOWN_STATE = """
⚠️ Parece que algo salió mal.

Escribe "menu" para volver al menú principal.
"""

    INVALID_OPTION = """
❌ Opción no válida.

Por favor elige una de las opciones del menú.
"""

    # ==========================================
    # RESPUESTA A CONSULTAS FUERA DE ALCANCE
    # ==========================================

    UNKNOWN_QUERY = (
        "No puedo ayudarte con eso por el momento.\n\n"
        "Puedo ayudarte a:\n"
        "• Buscar un profesional y sacar turno\n"
        "• Ver tus citas programadas\n"
        "• Consultar información del centro\n\n"
        "• Hola para el menu de navegacion\n\n"
        "¿Qué querés hacer?"
    )

    # ==========================================
    # MENSAJES DE VALIDACIÓN
    # ==========================================

    INVALID_DATE = """
❌ Fecha no válida.

Por favor ingresa una fecha en formato: DD/MM/AAAA
Ejemplo: 25/12/2024
"""

    INVALID_TIME = """
❌ Horario no válido.

Por favor ingresa un horario en formato: HH:MM
Ejemplo: 14:30
"""

    INVALID_PHONE = """
❌ Teléfono no válido.

Por favor ingresa un número de teléfono con el formato:
+54 9 11 1234-5678
"""

    INVALID_EMAIL = """
❌ Email no válido.

Por favor ingresa un email válido.
Ejemplo: nombre@ejemplo.com
"""

    # ==========================================
    # COMANDOS Y AYUDA
    # ==========================================

    HELP_MESSAGE = f"""
📚 **AYUDA - {DomainConfig.BUSINESS_NAME}**

**Comandos disponibles:**
• "hola" - Volver al inicio
• "menu" - Ir al menú principal
• "cancelar" - Cancelar operación actual
• "ayuda" - Mostrar esta ayuda

**¿Qué puedes hacer?**
• Buscar profesionales disponibles
• Reservar citas
• Ver y gestionar tus citas
• Obtener información del centro

¿Necesitas más ayuda? Escribe "hola" para comenzar.
"""

    CANCEL_MESSAGE = """
✅ Operación cancelada.

Escribe "menu" para volver al menú principal.
"""

    # ==========================================
    # MENSAJES DE CONFIRMACIÓN
    # ==========================================

    CONFIRMATION_NEEDED = """
⚠️ Esta acción requiere confirmación.

Responde:
• "si" o "confirmar" para continuar
• "no" o "cancelar" para cancelar
"""

    ACTION_CANCELLED = """
❌ Acción cancelada.

Volviendo al menú anterior...
"""

    # ==========================================
    # MENSAJES DE ESTADO
    # ==========================================

    PROCESSING = """
⏳ Procesando...

Por favor espera un momento.
"""

    SUCCESS = """
✅ ¡Listo!
"""

    # ==========================================
    # MENSAJES DE NAVEGACIÓN
    # ==========================================

    BACK_TO_MENU = """
Escribe "menu" para volver al menú principal.
"""

    BACK_OR_CONTINUE = """
Opciones:
• "continuar" - Seguir con la operación
• "menu" - Volver al menú
• "cancelar" - Cancelar operación
"""


# ==========================================
# INSTANCIA GLOBAL (SINGLETON)
# ==========================================
common_messages = CommonMessages()