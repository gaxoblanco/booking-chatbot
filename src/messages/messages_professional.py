"""
Professional Messages
=====================
Mensajes del flujo de profesional. Leen del tono activo.
Los mensajes de registro/acceso no cambian entre tonos — son operativos.
"""

from src.config.domain_config import DomainConfig
from src.messages.loader import get_msg


class ProfessionalMessages:

    # --- Menú principal ---

    @property
    def PROF_MAIN_MENU(self):
        return get_msg("PROF_MAIN_MENU",
            f"{DomainConfig.EMOJI_PROFESSIONAL} *Menú Profesional*\n\n"
            "¿Qué necesitás?\n\n"
            "1️⃣ Ver mi agenda\n"
            "2️⃣ Actualizar mi información\n"
            "3️⃣ Carga rápida de información\n"
            f"4️⃣ Mis {DomainConfig.APPOINTMENT_NAME_PLURAL}\n"
            "5️⃣ Cargar agenda (CSV/Excel)\n\n"
            "0️⃣ Volver al inicio"
        )

    # --- Acceso con clave ---
    # Estos mensajes son operativos — no varían por tono

    PROF_NEED_ACCESS_KEY = (
        f"🔑 *Acceso de {DomainConfig.PROFESSIONAL_TITLE}*\n\n"
        "Para acceder al sistema necesitás una clave de acceso.\n"
        "La clave la proporciona la administración.\n\n"
        "Ingresá tu clave:\n\n"
        "_Escribí *0* para volver_"
    )

    PROF_KEY_VALID = (
        "✅ ¡Acceso autorizado!\n\n"
        "Ya podés gestionar tu agenda y perfil."
    )

    PROF_KEY_INVALID = (
        "❌ Clave inválida.\n\n"
        "Verificá que hayas ingresado la clave correctamente "
        "o contactá a la administración.\n\n"
        "_Escribí *0* para volver_"
    )

    PROF_KEY_EXPIRED = (
        "⏰ Clave expirada.\n\n"
        "Contactá a la administración para obtener una nueva clave.\n\n"
        "_Escribí *0* para volver_"
    )

    PROF_KEY_ALREADY_USED = (
        "⚠️ Clave ya utilizada.\n\n"
        "Cada clave solo puede usarse una vez. "
        "Contactá a la administración para obtener una nueva.\n\n"
        "_Escribí *0* para volver_"
    )

    # --- Info del profesional ---

    PROF_INFO_SAVED = (
        "✅ Información guardada.\n\n"
        "{profile_summary}\n\n"
        "_Escribí *0* para volver al menú_"
    )

    PROF_INFO_INCOMPLETE = (
        "⚠️ Información incompleta.\n\n"
        "Necesitás completar: Nombre, {category_label} y Zona.\n\n"
        "_Volviendo al menú..._"
    )


professional_messages = ProfessionalMessages()