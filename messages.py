"""
Bot Messages
============
All bot messages organized by conversation flow.
Centralized message management for easy maintenance and translation.
"""


class Messages:
    """
    Bot message templates.
    All user-facing text in one place.
    """

    # ==========================================
    # WELCOME & ROLE SELECTION
    # ==========================================

    WELCOME = """👋 ¡Bienvenido!

Soy un bot para conectar profesionales con clientes.

¿Qué eres?
1️⃣ Profesional
2️⃣ Cliente

Responde con 1 o 2."""

    INVALID_ROLE = """❌ Opción inválida.

Por favor responde:
1️⃣ para Profesional
2️⃣ para Cliente"""

    # ==========================================
    # PROFESSIONAL MESSAGES
    # ==========================================

    # Certificate upload (mandatory first step)
    PROF_NEED_CERTIFICATE = """📋 Registro de Profesional

Para comenzar, necesito que subas tu certificado profesional.

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
    PROF_MAIN_MENU = """👨‍⚕️ Menú Profesional

¿Qué deseas hacer?

1️⃣ Liberar Horario
   (Marcar un horario como disponible)

2️⃣ Cargar Horario Ocupado
   (Bloquear un horario específico)

3️⃣ Cargar Semana Completa
   (Configurar tu agenda semanal)

4️⃣ Ver Mi Agenda

5️⃣ Cargar Información
   (Completar tu perfil profesional)

6️⃣ Carga Rápida de Información
   (Todo en un mensaje)

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

    # Option 2: Cargar horario ocupado
    PROF_BUSY_SLOT_ASK_DATE = """📅 Bloquear Horario

¿Qué día quieres bloquear?

Formato: DD/MM/YYYY
Ejemplo: 15/11/2025

💡 Escribe '0' para volver al menú"""

    PROF_BUSY_SLOT_ASK_TIME = """⏰ Bloquear Horario

¿Qué horario quieres bloquear?

Formato: HH:MM-HH:MM
Ejemplo: 09:00-17:00

Este horario quedará OCUPADO.
💡 Escribe '0' para volver al menú"""

    PROF_BUSY_SLOT_CONFIRM = """✅ Confirmar Bloqueo

📅 Fecha: {date}
⏰ Horario: {time_start} - {time_end}

Este horario NO estará disponible para clientes.


¿Confirmar?
1️⃣ Sí, bloquear
2️⃣ No, cancelar

💡 Escribe '0' para volver al menú"""

    PROF_BUSY_SLOT_SUCCESS = """✅ ¡Horario bloqueado!

📅 {date}
⏰ {time_start} - {time_end}

Este horario ahora está ocupado."""

    # Option 3: Cargar semana completa
    PROF_WEEK_ASK_DAY = """📅 Configurar Semana

¿Qué día quieres configurar?

1️⃣ Lunes
2️⃣ Martes
3️⃣ Miércoles
4️⃣ Jueves
5️⃣ Viernes
6️⃣ Sábado
7️⃣ Domingo

Responde con el número.
💡 Escribe '0' para volver al menú"""

    PROF_WEEK_ASK_TIME = """⏰ Horario para {day}

¿Qué horario estás OCUPADO este día?

Formato: HH:MM-HH:MM
Ejemplo: 09:00-17:00

Este será tu horario recurrente cada {day}."""

    PROF_WEEK_ASK_MORE = """✅ {day} configurado: {time_start} - {time_end}

¿Quieres configurar otro día?

1️⃣ Sí, agregar otro día
2️⃣ No, finalizar

Días configurados hasta ahora:
{configured_days}"""

    PROF_WEEK_SUCCESS = """✅ ¡Semana configurada!

Tu agenda semanal:
{schedule_summary}

Estos horarios se repetirán cada semana.

💡 Escribe '0' para volver al menú"""

# Option 5: Cargar información del profesional
    PROF_INFO_MENU = """📋 Cargar Información

Configura tu perfil profesional:

1️⃣ Nombre
2️⃣ Email
3️⃣ Zona (Norte/Sur)
4️⃣ Género
5️⃣ Prepaga (Sí/No)
6️⃣ Especialidad

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

    PROF_INFO_ASK_ESPECIALIDAD = """🏥 Especialidad

Selecciona tu especialidad:

1️⃣ Médico General
2️⃣ Dentista
3️⃣ Psicólogo
4️⃣ Kinesiólogo
5️⃣ Nutricionista
6️⃣ Otro

Responde con el número o escribe tu especialidad."""

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

━━━━━━━━━━━━━━━━━━━━
OPCIÓN 2 - Sin etiquetas (orden importante):
━━━━━━━━━━━━━━━━━━━━

Dr. Juan Pérez
juan@email.com
norte
masculino
si
dentista

━━━━━━━━━━━━━━━━━━━━
Valores aceptados:
━━━━━━━━━━━━━━━━━━━━

- zona: norte, sur (o n, s)
- genero: masculino, femenino, otro (o m, f, o)
- prepaga: si, no (o s, n)
- especialidad: texto libre

💡 Escribe '0' para volver"""
    # ==========================================
    # CLIENT MESSAGES - MULTI-FILTER
    # ==========================================

    CLIENT_MULTIFILTER_MENU = """🔍 Búsqueda Avanzada

Selecciona los filtros que desees (uno a la vez):

1️⃣ Zona
2️⃣ Disponibilidad (Fecha/Hora)
3️⃣ Prepaga
4️⃣ Sexo del Profesional
5️⃣ Especialidad

0️⃣ Buscar con filtros seleccionados

━━━━━━━━━━━━━━━━━━━━
Filtros activos:
{active_filters}
━━━━━━━━━━━━━━━━━━━━

Responde con el número de opción."""

    CLIENT_MULTIFILTER_ADDED = """✅ {filter_name}

    {menu}"""

    CLIENT_MULTIFILTER_SEARCH_SUMMARY = """🔍 Buscando profesionales con los siguientes filtros:

    {filters_list}

Procesando búsqueda..."""

    # ==========================================
    # CLIENT MESSAGES
    # ==========================================

    CLIENT_MAIN_MENU = """👤 Menú Cliente

Buscar profesionales disponibles:

1️⃣ Buscar para Hoy
2️⃣ Buscar con Multi-Filtro
3️⃣ Zona Norte
4️⃣ Zona Sur

0️⃣ Volver al inicio

Responde con el número de opción."""

    # Quick search - Today
    CLIENT_SEARCH_TODAY_CONFIRM = """🔍 Buscar para Hoy

Buscando profesionales disponibles HOY ({today_date})...

¿A qué hora necesitas?

Formato: HH:MM
Ejemplo: 14:00

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
    CLIENT_ASK_SEXO = """👥 Filtrar por Sexo del Profesional

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
👤 Sexo: {sexo}

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

    # ==========================================
    # COMMON MESSAGES
    # ==========================================

    INVALID_INPUT = """❌ Entrada inválida

Por favor, verifica el formato e intenta nuevamente."""

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
