"""
Bot Messages
============
All bot messages organized by conversation flow.
Centralized message management for easy maintenance and translation.
"""

from src.config.domain_config import DomainConfig


def _format_categories_list():
    """Format categories for display in messages."""
    categories_text = ""
    for key, value in DomainConfig.CATEGORIES.items():
        categories_text += f"{key}️⃣ {value}\n"
    return categories_text.strip()


class Messages:
    """
    Bot message templates.
    All user-facing text in one place.
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
    # PROFESSIONAL MESSAGES
    # ==========================================

    # Certificate upload (mandatory first step)
    PROF_NEED_CERTIFICATE = f"""{DomainConfig.EMOJI_CERTIFICATE} Registro de {DomainConfig.PROFESSIONAL_TITLE}

Para comenzar, necesito que subas tu {DomainConfig.CERTIFICATE_NAME}.

📎 Envía una foto o PDF de tu:
• Matrícula profesional
• Título habilitante
• Documento que acredite tu profesión

⚠️ Solo profesionales verificados aparecen en búsquedas.

💡 Escribe '0' para volver al menú"""

    PROF_CERTIFICATE_RECEIVED = """✅ ¡Certificado recibido!

Tu certificado ha sido guardado y verificado automáticamente.
Ya puedes gestionar tu agenda."""

    PROF_CERTIFICATE_ERROR = """❌ Error al guardar certificado.

Por favor, intenta nuevamente enviando:
• Una imagen (JPG, PNG)
• Un PDF
• Tamaño menor a 10MB"""

    # Main menu
    PROF_MAIN_MENU = f"""{DomainConfig.EMOJI_PROFESSIONAL} Menú Profesional

{DomainConfig.PROFESSIONAL_WELCOME}

¿Qué deseas hacer?

1️⃣ Gestionar Horarios Libres
   (Ver, agregar o eliminar horarios disponibles)

2️⃣ Cargar Agenda Semanal
   (Configurar horarios recurrentes ocupados)

3️⃣ Ver Mi Agenda Completa

4️⃣ Actualizar Mi Información

5️⃣ Carga Rápida de Información

0️⃣ Volver al inicio

Responde con el número de opción."""

    # Option 1: Liberar horario
    PROF_FREE_SLOT_ASK_DATE = """📅 Liberar Horario

¿Qué día tienes disponible?

Formato: DD/MM/YYYY
Ejemplo: 15/11/2025

💡 Escribe '0' para volver al menú"""

    PROF_FREE_SLOT_ASK_TIME = """⏰ Liberar Horario

¿Qué horario tienes disponible?

Formato: HH:MM-HH:MM
Ejemplo: 14:00-15:00

Este horario quedará LIBRE para reservas."""

    PROF_FREE_SLOT_CONFIRM = """✅ Confirmar Liberación

📅 Fecha: {date}
⏰ Horario: {time_start} - {time_end}

Este horario quedará disponible para clientes.

¿Confirmar?
1️⃣ Sí, liberar
2️⃣ No, cancelar"""

    PROF_FREE_SLOT_SUCCESS = """✅ ¡Horario liberado!

📅 {date}
⏰ {time_start} - {time_end}

Este horario ahora está disponible para clientes."""

    # Option 3: Cargar semana completa
    PROF_WEEK_QUICK_FORMAT = """📅 Carga Rápida de Semana

Envía tu agenda semanal ocupada en el siguiente formato:

━━━━━━━━━━━━━━━━━━━━
FORMATO:
━━━━━━━━━━━━━━━━━━━━

dia HH:MM-HH:MM+HH:MM-HH:MM
dia HH:MM-HH:MM

Cada línea = un día
Múltiples horarios separados por +

━━━━━━━━━━━━━━━━━━━━
EJEMPLO:
━━━━━━━━━━━━━━━━━━━━

lunes 09:00-10:00+11:00-11:40+16:20-17:10
martes 09:00-17:00
viernes 14:00-18:00

━━━━━━━━━━━━━━━━━━━━
DÍAS ACEPTADOS:
━━━━━━━━━━━━━━━━━━━━

lunes, martes, miércoles, miércoles, jueves, viernes, sábado, sabado, domingo

💡 Puedes enviar los días en cualquier orden
💡 Envía solo los días que estés ocupado
💡 Escribe '0' para volver al menú"""

#     PROF_WEEK_ASK_DAY = """📅 Configurar Semana

# ¿Qué día quieres configurar?

# 1️⃣ Lunes
# 2️⃣ Martes
# 3️⃣ Miércoles
# 4️⃣ Jueves
# 5️⃣ Viernes
# 6️⃣ Sábado
# 7️⃣ Domingo

# Responde con el número.
# 💡 Escribe '0' para volver al menú"""

#     PROF_WEEK_ASK_TIME = """⏰ Horario para {day}

# ¿Qué horario estás OCUPADO este día?

# Formato: HH:MM-HH:MM
# Ejemplo: 09:00-17:00

# Este será tu horario recurrente cada {day}."""

#     PROF_WEEK_ASK_MORE = """✅ {day} configurado: {time_start} - {time_end}

# ¿Quieres configurar otro día?

# 1️⃣ Sí, agregar otro día
# 2️⃣ Finalizar

# Días configurados hasta ahora:
# {configured_days}"""

#     PROF_WEEK_SUCCESS = """✅ ¡Semana configurada!

# Tu agenda semanal:
# {schedule_summary}

# Estos horarios se repetirán cada semana.

# 💡 Escribe '0' para volver al menú"""

# Option 5: Cargar información del profesional
    PROF_INFO_MENU = """📋 Cargar Información

Configura tu perfil profesional:

1️⃣ Nombre
2️⃣ Email
3️⃣ Zona (Norte/Sur)
4️⃣ Género
5️⃣ Prepaga (Sí/No)
6️⃣ Especialidad
7️⃣ Campo abierto
8️⃣ Rango de Honorarios

9️⃣ Guardar Información
0️⃣ Volver al menú

━━━━━━━━━━━━━━━━━━━━
Información actual:
{current_info}
━━━━━━━━━━━━━━━━━━━━

Responde con el número de opción."""

    PROF_INFO_ASK_NAME = """👤 Nombre

Ingresa tu nombre completo:
Ejemplo: Dr. Juan Pérez

💡 Escribe '0' para volver"""

    PROF_INFO_ASK_EMAIL = """📧 Email

Ingresa tu email de contacto:
Ejemplo: juan.perez@email.com

💡 Escribe '0' para volver"""

    PROF_INFO_ASK_ZONA = """📍 Zona

¿En qué zona trabajas?

1️⃣ Zona Norte
2️⃣ Zona Sur

Responde con el número."""

    PROF_INFO_ASK_GENERO = """👥 Género

Selecciona tu género:

1️⃣ Masculino
2️⃣ Femenino
3️⃣ Otro

Responde con el número."""

    PROF_INFO_ASK_PREPAGA = """💳 Prepaga

¿Aceptas obras sociales/prepagas?

1️⃣ Sí
2️⃣ No

Responde con el número."""

    PROF_INFO_ASK_ESPECIALIDAD = f"""{DomainConfig.EMOJI_CATEGORY} {DomainConfig.CATEGORY_LABEL}

{DomainConfig.CATEGORY_PROMPT}

{_format_categories_list()}

Responde con el número o escribe tu {DomainConfig.CATEGORY_LABEL_LOWER}."""

    PROF_INFO_ASK_BIO = f"""📝 Descripción Personal

Escribe una breve descripción sobre ti:
Ejemplo: 
    {DomainConfig.CATEGORY_CUSTOM_EXAMPLE1}
    {DomainConfig.CATEGORY_CUSTOM_EXAMPLE2}

💡 Escribe '0' para volver"""

    PROF_INFO_ASK_FEE_RANGE = """💰 Rango de Honorarios

¿Cuánto cobras por sesión/consulta?

Formato: MÍNIMO-MÁXIMO
Ejemplo: 100-150

💡 Escribe '0' para volver"""

    PROF_INFO_SAVED = """✅ ¡Información guardada!

Tu perfil profesional:
{profile_summary}

Esta información será visible para los clientes."""

    PROF_INFO_INCOMPLETE = """⚠️ Información incompleta

Debes completar al menos:
- Nombre
- Especialidad
- Zona

Antes de guardar."""

    PROF_INFO_QUICK_FORMAT = """📋 Carga Rápida de Información

Envía tu información en cualquiera de estos formatos:

━━━━━━━━━━━━━━━━━━━━
OPCIÓN 1 - Con etiquetas:
━━━━━━━━━━━━━━━━━━━━

nombre: Dr. Juan Pérez
email: juan@email.com
zona: norte
genero: masculino
prepaga: si
especialidad: dentista
bio: Especialista con 10 años de experiencia
honorarios: 100-150

━━━━━━━━━━━━━━━━━━━━
OPCIÓN 2 - Sin etiquetas (orden importante):
━━━━━━━━━━━━━━━━━━━━

Dr. Juan Pérez
juan@email.com
norte
masculino
si
dentista
Especialista con 10 años de experiencia
100-150

━━━━━━━━━━━━━━━━━━━━
Valores aceptados:
━━━━━━━━━━━━━━━━━━━━

- zona: norte, sur (o n, s)
- genero: masculino, femenino, otro (o m, f, o)
- prepaga: si, no (o s, n)
- especialidad: texto libre
- bio: texto libre (opcional)
- honorarios: MÍNIMO-MÁXIMO (opcional, ej: 100-150)

💡 Los campos bio y honorarios son opcionales
💡 Escribe '0' para volver"""

    # ==========================================
    # CLIENT MESSAGES - MULTI-FILTER (Dynamic)
    # ==========================================

    @staticmethod
    def CLIENT_MULTIFILTER_MENU(active_filters: str = "") -> str:
        """Generate multifilter menu with active filters."""
        from src.config.domain_config import DomainConfig

        filters_section = ""
        if active_filters:
            filters_section = f"""
━━━━━━━━━━━━━━━━━━━━
Filtros activos:
{active_filters}
━━━━━━━━━━━━━━━━━━━━
"""

        return f"""{DomainConfig.EMOJI_CLIENT} Menú Cliente

¿Cómo deseas buscar {DomainConfig.PROFESSIONAL_TITLE_PLURAL_LOWER}?

1️⃣ Zona
2️⃣ Disponibilidad (Fecha/Hora)
3️⃣ Prepaga
4️⃣ Genero del Profesional
5️⃣ Especialidad

0️⃣ Buscar con filtros seleccionados
{filters_section}
Responde con el número de opción."""

    @staticmethod
    def CLIENT_MULTIFILTER_ADDED(filter_name: str, menu: str) -> str:
        """Show filter added confirmation with updated menu."""
        return f"""✅ {filter_name}

{menu}"""

    @staticmethod
    def CLIENT_MULTIFILTER_SEARCH_SUMMARY(filters_list: str) -> str:
        """Show search summary with active filters."""
        return f"""🔍 Buscando profesionales con los siguientes filtros:

{filters_list}

Procesando búsqueda..."""

    # ==========================================
    # CLIENT MESSAGES
    # ==========================================

    CLIENT_MAIN_MENU = f"""{DomainConfig.EMOJI_CLIENT} Menú Cliente

{DomainConfig.CLIENT_WELCOME}

Buscar {DomainConfig.PROFESSIONAL_TITLE_PLURAL_LOWER} disponibles:

1️⃣ Buscar para Hoy
2️⃣ Búsqueda Avanzada (Paso a Paso)
3️⃣ Búsqueda Rápida (Todo en 1 mensaje)
4️⃣ Virtual
5️⃣ Precensial

0️⃣ Volver al inicio

Responde con el número de opción."""

    # Quick search - Today
    CLIENT_SEARCH_TODAY_CONFIRM = """🔍 Buscar para Hoy

Buscando profesionales disponibles HOY ({today_date})

¿En qué horario preferís?

1️⃣ Mañana (8:00 - 13:00)
2️⃣ Tarde (13:00 - 20:00)

Responde con el número o escribe el horario exacto (ej: 14:00)

💡 Escribe '0' para volver al menú"""

    # Zona filter
    CLIENT_ASK_ZONA = """📍 Filtrar por Zona

¿En qué zona buscas?

1️⃣ Zona Norte
2️⃣ Zona Sur

Responde con el número."""

    # Disponibilidad filter
    CLIENT_ASK_FECHA = """📅 Filtrar por Disponibilidad

¿Qué día necesitas?

Formato: DD/MM/YYYY
Ejemplo: 15/11/2025"""

    CLIENT_ASK_HORA = """⏰ Filtrar por Disponibilidad

¿A qué hora necesitas?

Formato: HH:MM
Ejemplo: 14:00"""

    # Prepaga filter
    CLIENT_ASK_PREPAGA = """💳 Filtrar por Prepaga

¿Buscas profesionales que acepten prepaga?

1️⃣ Sí, con prepaga
2️⃣ No, sin prepaga
3️⃣ No importa

Responde con el número."""

    # Sexo filter
    CLIENT_ASK_SEXO = """👥 Filtrar por genero del Profesional

¿Qué prefieres?

1️⃣ Masculino
2️⃣ Femenino
3️⃣ No importa

Responde con el número."""

    # Search summary before results
    CLIENT_SEARCH_SUMMARY = """🔍 Buscando con filtros:

{filters_summary}

Buscando profesionales..."""

    # Results
    CLIENT_NO_RESULTS = """❌ No se encontraron profesionales

Con los filtros seleccionados no hay profesionales disponibles.

¿Qué deseas hacer?
1️⃣ Modificar filtros
2️⃣ Ver todos los profesionales
3️⃣ Volver al menú"""

    CLIENT_RESULTS_FOUND = """✅ Encontrados {count} profesional(es)

{results_list}

Responde con el número para ver detalles.
O escribe '0' para volver al menú."""

    CLIENT_PROFESSIONAL_DETAIL = """👨‍⚕️ {name}

📍 Zona: {zona}
💳 Prepaga: {prepaga}
👤 Genero: {sexo}

📅 Disponibilidad:
{availability}

📱 Contacto: {phone}
📧 Email: {email}

¿Qué deseas hacer?
1️⃣ Contactar profesional
2️⃣ Volver a resultados
3️⃣ Nueva búsqueda"""

    CLIENT_CONTACT_LOGGED = """✅ Contacto registrado

Hemos registrado tu interés en este profesional.

Puedes contactarlo directamente:
📱 {phone}

¿Qué deseas hacer?
1️⃣ Ver otros profesionales
2️⃣ Nueva búsqueda
3️⃣ Volver al menú"""

    CLIENT_MULTIFILTER_MENU = """🔍 Búsqueda Avanzada

Selecciona los filtros que desees (uno a la vez):

1️⃣ Zona
2️⃣ Disponibilidad (Fecha/Hora)
3️⃣ Prepaga
4️⃣ Genero del Profesional

9️⃣ Buscar con filtros actuales
0️⃣ Volver al menú

━━━━━━━━━━━━━━━━━━━━
Filtros activos:
{active_filters}
━━━━━━━━━━━━━━━━━━━━

Responde con el número de opción."""

    CLIENT_SEARCH_QUICK_FORMAT = """🔍 Búsqueda Rápida

Envía tus filtros en cualquiera de estos formatos:

━━━━━━━━━━━━━━━━━━━━
OPCIÓN 1 - Con etiquetas:
━━━━━━━━━━━━━━━━━━━━

zona: norte
fecha: 15/11/2025
hora: 14:00
prepaga: si
genero: masculino

━━━━━━━━━━━━━━━━━━━━
OPCIÓN 2 - Sin etiquetas (orden importante):
━━━━━━━━━━━━━━━━━━━━

norte
15/11/2025
14:00
si
masculino

━━━━━━━━━━━━━━━━━━━━
Valores aceptados:
━━━━━━━━━━━━━━━━━━━━

- zona: norte, sur (o n, s) - OPCIONAL
- fecha: DD/MM/YYYY - OPCIONAL
- hora: HH:MM - OPCIONAL
- prepaga: si, no (o s, n) - OPCIONAL
- genero: masculino, femenino, otro (o m, f, o) - OPCIONAL

💡 Todos los campos son opcionales
💡 Puedes enviar solo los filtros que necesites
💡 Escribe '0' para volver

━━━━━━━━━━━━━━━━━━━━
Ejemplos:
━━━━━━━━━━━━━━━━━━━━

Solo zona:
zona: norte

Zona y fecha:
zona: norte
fecha: 15/11/2025

Todo:
norte
15/11/2025
14:00
si
masculino"""

    # ==========================================
    # COMMON MESSAGES
    # ==========================================

    INVALID_OPTION = "❌ Opción inválida. Por favor, selecciona una opción válida."
    BACK_TO_MENU = "Volviendo al menú principal..."

    INVALID_DATE = """❌ Fecha inválida

Formato correcto: DD/MM/YYYY
Ejemplo: 15/11/2025"""

    INVALID_TIME = """❌ Horario inválido

Formato correcto: HH:MM-HH:MM
Ejemplo: 14:00-15:00

El formato debe ser 24 horas."""

    INVALID_OPTION = """❌ Opción inválida

Por favor, selecciona una opción válida del menú."""

    OPERATION_CANCELLED = """❌ Operación cancelada

Volviendo al menú principal..."""

    ERROR_GENERIC = """❌ Error

Ocurrió un error. Por favor, intenta nuevamente.

Si el problema persiste, escribe 'ayuda'."""

    HELP_MESSAGE = """ℹ️ Ayuda - Comandos Disponibles

🏠 Navegación:
- 'inicio' - Volver al inicio (elegir rol)
- 'menu' - Volver al menú de tu rol
- 'cancelar' - Cancelar operación actual
- 'volver' - Volver al menú anterior

ℹ️ Información:
- 'ayuda' o '?' - Ver este mensaje

💡 Tip: Puedes usar estos comandos en cualquier momento."""

    # ==========================================
    # HELPER METHODS
    # ==========================================

    @staticmethod
    def format_day_name(day_number: int) -> str:
        """
        Convert day number to Spanish name.

        Args:
            day_number: Day number (1-7)

        Returns:
            Day name in Spanish
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
    def format_zona(zona: str) -> str:
        """
        Format zone name.

        Args:
            zona: Zone identifier

        Returns:
            Formatted zone name
        """
        zonas = {
            "norte": "Zona Norte",
            "sur": "Zona Sur"
        }
        return zonas.get(zona.lower(), zona)

    @staticmethod
    def format_prepaga(prepaga: bool) -> str:
        """
        Format prepaga value.

        Args:
            prepaga: Boolean value

        Returns:
            Formatted string
        """
        return "Sí" if prepaga else "No"

    @staticmethod
    def format_sexo(sexo: str) -> str:
        """
        Format sexo value.

        Args:
            sexo: Sex identifier

        Returns:
            Formatted string
        """
        sexos = {
            "m": "Masculino",
            "f": "Femenino",
            "o": "Otro"
        }
        return sexos.get(sexo.lower(), sexo)


# Create singleton instance
messages = Messages()
