"""
Bot Messages
============
All bot messages organized by conversation flow.
Centralized message management for easy maintenance and translation.
"""

from domain_config import DomainConfig


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
    # BIENVENIDA PSIVALE
    # ==========================================

    WELCOME = """🌿 Hola, soy Vale, tu asistente de PSIVALE.

Sé que dar el primer paso no siempre es fácil, así que gracias por animarte.
Estoy acá para ayudarte a encontrar el psicólogo que mejor se adapte a vos. 💜

¿Querés que te ayudemos a encontrar un profesional para comenzar terapia?

1️⃣ Sí, quiero empezar
2️⃣ Buscar por mi cuenta

Responde con el número."""

    # ==========================================
    # PROFESSIONAL MESSAGES
    # ==========================================

    # Certificate upload (mandatory first step)
    PROF_NEED_CERTIFICATE = """📋 Registro de Psicólogo

Para comenzar, necesito que subas tu matrícula profesional.

📎 Envía una foto o PDF de tu:
- Matrícula profesional
- Título habilitante
- Documento que acredite tu profesión

⚠️ Solo profesionales verificados aparecen en búsquedas.

💡 Escribe '0' para volver"""

    # ⭐ MODIFICAR - Detección de psicólogo (sin info extra)
    PSIVALE_AUTH_DETECTED = """💼 ¡Hola! Veo que sos psicólogo.

🌿 Gracias por dar el primer paso para sumarte a PSIVALE."""

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
3️⃣ Zona (Norte/Sur/Nueva Córdoba)
4️⃣ Género
5️⃣ Enfoque Terapéutico
6️⃣ Población que atendés
7️⃣ Modalidad (Online/Presencial/Ambas)
8️⃣ Horarios disponibles
9️⃣ Biografía
🔟 Rango de Honorarios

💾 Escribí 'guardar' para guardar la información
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

    PROF_INFO_ASK_ZONA = """📍 ¿En qué zona trabajás?

1️⃣ Zona Norte
2️⃣ Zona Sur
3️⃣ Nueva Córdoba

Responde con el número."""

    PROF_INFO_ASK_GENERO = """👥 Género

Selecciona tu género:

1️⃣ Masculino
2️⃣ Femenino
3️⃣ Otro

Responde con el número."""

#     PROF_INFO_ASK_PREPAGA = """💳 Prepaga

# ¿Aceptas obras sociales/prepagas?

# 1️⃣ Sí
# 2️⃣ No

# Responde con el número."""

#     PROF_INFO_ASK_ESPECIALIDAD = f"""{DomainConfig.EMOJI_CATEGORY} {DomainConfig.CATEGORY_LABEL}

# {DomainConfig.CATEGORY_PROMPT}

# {_format_categories_list()}

# Responde con el número o escribe tu {DomainConfig.CATEGORY_LABEL_LOWER}."""

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

Envía toda la información en cualquiera de estos formatos:

━━━━━━━━━━━━━━━━━━━━
Con etiquetas:
━━━━━━━━━━━━━━━━━━━━

nombre: Dra. María González
email: maria@psivale.com
zona: norte
genero: femenino
enfoque: tcc, contextual
poblacion: adultos, parejas
modalidad: ambas
horarios: tarde, noche
bio: Psicóloga con enfoque cognitivo-conductual
honorarios: 25000-35000

━━━━━━━━━━━━━━━━━━━━
Valores aceptados:
━━━━━━━━━━━━━━━━━━━━

📍 zona: norte, sur, nueva_cordoba

👤 genero: masculino, femenino, otro (o m, f, o)

🧠 enfoque: tcc, contextual, sistemica, gestaltica, psicoanalisis, neuropsicologia, aptos
   (separar con comas si elegís múltiples enfoques)

👥 poblacion: ninos, adolescentes, adultos, parejas
   (separar con comas si atendés múltiples poblaciones)

💻 modalidad: online, presencial, ambas

📅 horarios: manana, tarde, noche, sabado
   (separar con comas)

📝 bio: texto libre (opcional)

💰 honorarios: MÍNIMO-MÁXIMO (opcional, ej: 15000-25000)

━━━━━━━━━━━━━━━━━━━━

💡 Los campos bio y honorarios son opcionales
💡 Escribe '0' para volver"""

  # ==========================================
  # CLIENT MESSAGES - MULTI-FILTER (Dynamic)
  # ==========================================

    @staticmethod
    def CLIENT_MULTIFILTER_MENU(active_filters: str = "") -> str:
        """Generate multifilter menu with active filters."""
        from domain_config import DomainConfig

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

# 💡 Escribe '0' para volver al menú"""

#     # Zona filter
#     CLIENT_ASK_ZONA = """📍 Filtrar por Zona

# ¿En qué zona buscas?

# 1️⃣ Zona Norte
# 2️⃣ Zona Sur

# Responde con el número."""

    # Disponibilidad filter
#     CLIENT_ASK_FECHA = """📅 Filtrar por Disponibilidad

# ¿Qué día necesitas?

# Formato: DD/MM/YYYY
# Ejemplo: 15/11/2025"""

#     CLIENT_ASK_HORA = """⏰ Filtrar por Disponibilidad

# ¿A qué hora necesitas?

# Formato: HH:MM
# Ejemplo: 14:00"""

    # Prepaga filter
#     CLIENT_ASK_PREPAGA = """💳 Filtrar por Prepaga

# ¿Buscas profesionales que acepten prepaga?

# 1️⃣ Sí, con prepaga
# 2️⃣ No, sin prepaga
# 3️⃣ No importa

# Responde con el número."""

    # Sexo filter
#     CLIENT_ASK_SEXO = """👥 Filtrar por genero del Profesional

# ¿Qué prefieres?

# 1️⃣ Masculino
# 2️⃣ Femenino
# 3️⃣ No importa

# Responde con el número."""

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

#     CLIENT_MULTIFILTER_MENU = """🔍 Búsqueda Avanzada

# Selecciona los filtros que desees (uno a la vez):

# 1️⃣ Zona
# 2️⃣ Disponibilidad (Fecha/Hora)
# 3️⃣ Prepaga
# 4️⃣ Genero del Profesional

# 9️⃣ Buscar con filtros actuales
# 0️⃣ Volver al menú

# ━━━━━━━━━━━━━━━━━━━━
# Filtros activos:
# {active_filters}
# ━━━━━━━━━━━━━━━━━━━━

# Responde con el número de opción."""

    # ==========================================
    # REEMPLAZAR en messages.py
    # ==========================================

    CLIENT_SEARCH_QUICK_FORMAT = """🌿 Perfecto, te ayudo a buscar por tu cuenta.

Si ya sabés qué necesitás, escribí los filtros que quieras, uno por línea.
Todos los campos son opcionales - solo escribí lo que te importa.

━━━━━━━━━━━━━━━━━━━━
💜 Ejemplo:
━━━━━━━━━━━━━━━━━━━━

tcc
adultos
online

━━━━━━━━━━━━━━━━━━━━
🎯 Opciones disponibles:
━━━━━━━━━━━━━━━━━━━━

🧠 Enfoque: tcc, contextual, sistemica, gestaltica, psicoanalisis, neuropsicologia, aptos

👥 Población: ninos, adolescentes, adultos, parejas

💻 Modalidad: online, presencial, ambas

📍 Zona: norte, sur, nueva_cordoba

📅 Horarios: manana, tarde, noche, sabado

💰 Honorarios: 1, 2, 3 o 4
   (1=hasta $15k | 2=$15-25k | 3=$25-35k | 4=+$35k)

━━━━━━━━━━━━━━━━━━━━

💡 Todos los campos son opcionales
💡 Escribí solo lo que necesites
💡 Escribe '0' para volver al menú"""

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

    # ==========================================
    # PSIVALE - MENSAJES CON TONO EMPÁTICO
    # ==========================================

    # Detección automática de psicólogo
    PSIVALE_PROF_REGISTER_CONFIRM = """💼 ¡Hola! Veo que sos psicólogo.

🌿 Gracias por dar el primer paso para sumarte a PSIVALE.

¿Querés registrarte para recibir derivaciones de pacientes?

1️⃣ Sí, quiero unirme
2️⃣ Necesito más información

Responde con el número."""

    # Info sobre PSIVALE para profesionales
    PSIVALE_PROF_INFO = """🌿 PSIVALE - Información para Profesionales

📋 ¿Qué es PSIVALE?
PSIVALE es una plataforma que conecta psicólogos con pacientes que buscan terapia, facilitando el acceso a atención psicológica de calidad.

✅ Beneficios de sumarte:
- Recibí derivaciones de pacientes que buscan tu perfil
- Mayor visibilidad profesional
- Con una suscripción accesible
- Vos decidís tus honorarios y disponibilidad
- No pierdas horas por cancelaciones de último momento

📋 Requisitos:
- Matrícula profesional activa
- Título habilitante

💜 ¿Querés registrarte?

1️⃣ Sí, quiero unirme
0️⃣ Volver al inicio

Responde con el número."""

    # ==========================================
    # PROFESIONAL - REGISTRO EXTENDIDO PSIVALE
    # ==========================================

    PROF_INFO_MENU_PSIVALE = """📋 Configurá tu Perfil Profesional

Para conectar con los pacientes adecuados, completá tu información:

1️⃣ Nombre
2️⃣ Email
3️⃣ Zona
4️⃣ Género
5️⃣ Prepaga

🌿 INFORMACIÓN PSIVALE:
6️⃣ Enfoque Terapéutico (hasta 2)
7️⃣ Población que Atendés
8️⃣ Modalidad (Online/Presencial)
9️⃣ Horarios Disponibles
🔟 Bio Profesional
1️⃣1️⃣ Rango de Honorarios

✅ Guardar y Finalizar
0️⃣ Volver al menú

━━━━━━━━━━━━━━━━━━━━
Información actual:
{current_info}
━━━━━━━━━━━━━━━━━━━━

Responde con el número."""

    # Enfoque terapéutico (nuevo campo)
    PROF_INFO_ASK_ENFOQUE = """🧠 Enfoque Terapéutico

¿Desde qué enfoque trabajás? (podés elegir hasta 2)

1️⃣ Terapia Cognitivo-Conductual (TCC)
   → Enfoque práctico en pensamientos y conductas

2️⃣ Terapias Contextuales (ACT, DBT, FAP)
   → Aceptación, mindfulness y valores personales

3️⃣ Terapia Sistémica
   → Enfoque en relaciones y contexto familiar

4️⃣ Terapia Gestáltica
   → Conciencia del presente y responsabilidad personal

5️⃣ Psicoanálisis / Psicodinámica
   → Exploración profunda del inconsciente

6️⃣ Neuropsicología / Neurorehabilitación
   → Enfoque en funciones cognitivas y cerebrales

7️⃣ Aptos psicológicos generales 
    → Evaluaciones y certificados

Responde con el número (o números separados por coma para elegir 2).
💡 Ejemplo: 1,3"""

    PROF_INFO_ASK_ENFOQUE_SECOND = """🧠 Segundo Enfoque (Opcional)

Ya seleccionaste: {first_enfoque}

¿Querés agregar un segundo enfoque?

1️⃣ Terapia Cognitivo-Conductual (TCC)
2️⃣ Terapias Contextuales (ACT, DBT, FAP)
3️⃣ Terapia Sistémica
4️⃣ Terapia Gestáltica
5️⃣ Psicoanálisis / Psicodinámica
6️⃣ Neuropsicología / Neurorehabilitación
7️⃣ Aptos psicológicos generales 

0️⃣ No, solo uno

Responde con el número."""

    # Población atendida (nuevo campo)
    PROF_INFO_ASK_POBLACION = """👥 Población que Atendés

¿Con qué tipo de pacientes trabajás habitualmente?
(podés elegir varios)

1️⃣ Niños/as
2️⃣ Adolescentes
3️⃣ Adultos
4️⃣ Parejas / Familias

Responde con el número (o números separados por coma).
💡 Ejemplo: 1,2,3"""

    # Modalidad (nuevo campo)
    PROF_INFO_ASK_MODALIDAD = """💻 Modalidad de Atención

¿Tus sesiones son online, presenciales o ambas?

1️⃣ Online (sesiones virtuales)
2️⃣ Presencial (en consultorio)
3️⃣ Ambas modalidades

Responde con el número."""

    # Horarios disponibles (nuevo campo)
    PROF_INFO_ASK_HORARIOS = """📅 Disponibilidad Horaria

¿En qué horarios solés tener disponibilidad?
(podés elegir varios)

1️⃣ Mañana (8:00 - 13:00)
2️⃣ Tarde (13:00 - 19:00)
3️⃣ Noche (19:00 - 22:00)
4️⃣ Sábados

Responde con el número (o números separados por coma).
💡 Ejemplo: 1,2"""

    # ==========================================
    # CLIENTE - FLUJO ASESORADO PSIVALE
    # ==========================================

    CLIENT_WELCOME_PSIVALE = """🌿 Perfecto, te voy a acompañar en la búsqueda.

¿Cómo preferís buscar tu psicólogo/a?

1️⃣ Quiero que me acompañes paso a paso
   (Te guío con preguntas para encontrar el mejor match)

2️⃣ Prefiero filtrado rápido
   (Enviás todos los filtros de una vez)

💡 Te recomiendo la primera opción para que te ayude a encontrar el profesional ideal."""

    # Bienvenida del flujo asesorado
    CLIENT_ASESORADO_WELCOME = """🌿 Hola, soy Vale, tu asistente de PSIVALE.

Sé que dar el primer paso no siempre es fácil, así que gracias por animarte.
Estoy acá para ayudarte a encontrar el psicólogo que mejor se adapte a vos. 💜

Te voy a hacer algunas preguntas para entender qué necesitás.
Podés escribir '0' en cualquier momento para volver al menú.

¿Empezamos? 
1️⃣ Sí, ayudame a buscar
2️⃣ Solo estoy explorando"""

    # Confirmación de intención
    CLIENT_ASESORADO_CONFIRMA = """💜 Perfecto, vamos paso a paso.

Te voy a hacer algunas preguntas para encontrar el profesional ideal.
No te preocupes, es muy simple y rápido.

Presioná cualquier tecla para continuar..."""

    # Pregunta por enfoque terapéutico
    CLIENT_ASESORADO_ASK_ENFOQUE = """🌱 Cada persona necesita algo diferente.

¿Qué tipo de terapia te gustaría probar o te interesa más?

1️⃣ Terapia Cognitivo-Conductual (TCC)
   💭 Enfoque práctico en pensamientos y conductas

2️⃣ Terapias Contextuales (ACT, DBT, FAP)
   🧘 Aceptación, mindfulness y valores

3️⃣ Terapia Sistémica
   👨‍👩‍👧 Enfoque en relaciones y familia

4️⃣ Terapia Gestáltica
   ✨ Conciencia del presente

5️⃣ Psicoanálisis / Psicodinámica
   🔍 Exploración profunda

6️⃣ Neuropsicología / Neurorehabilitación
   🧠 Funciones cognitivas

7️⃣ Aptos psicológicos generales 
    📄 Evaluaciones y certificados

8️⃣ Me da igual / No sé bien
   🤷 Te mostramos todas las opciones

Responde con el número."""

    # Pregunta por población
    CLIENT_ASESORADO_ASK_POBLACION = """👥 ¿Para quién es la terapia?

1️⃣ Para un niño/a
2️⃣ Para un adolescente
3️⃣ Para mí (adulto)
4️⃣ Para una pareja o familia

Responde con el número."""

    # Pregunta por modalidad
    CLIENT_ASESORADO_ASK_MODALIDAD = """💻 ¿Cómo preferís tener tus sesiones?

1️⃣ Online (videollamada)
   💡 Más flexible, desde tu casa

2️⃣ Presencial (en consultorio)
   💡 Encuentro cara a cara

3️⃣ Me da igual
   💡 Te mostramos ambas opciones

Responde con el número."""

    # Pregunta por zona (solo si es presencial)
    CLIENT_ASESORADO_ASK_ZONA = """📍 ¿En qué zona estás buscando?

1️⃣ Zona Norte
2️⃣ Zona Sur
3️⃣ Nueva Córdoba

Responde con el número."""

    # Pregunta por horarios
    CLIENT_ASESORADO_ASK_HORARIOS = """📅 ¿En qué horarios te resultaría más cómodo?

1️⃣ Mañana (8:00 - 13:00)
2️⃣ Tarde (13:00 - 19:00)
3️⃣ Noche (19:00 - 22:00)
4️⃣ Sábados
5️⃣ Cualquier horario

Responde con el número."""

    # Pregunta por honorarios
    CLIENT_ASESORADO_ASK_HONORARIOS = """💰 Para ayudarte mejor, ¿cuál es tu presupuesto aproximado?

1️⃣ Hasta $15.000
2️⃣ $15.000 – $25.000
3️⃣ $25.000 – $35.000
4️⃣ Más de $35.000
5️⃣ Prefiero no decirlo ahora

Responde con el número."""

    # Mensaje 1 - Resumen
    CLIENT_ASESORADO_RESUMEN = """✨ Perfecto, ya tengo toda la información.

    🌿 Estás buscando:
{resumen}

Buscando psicólogos que se ajusten a tu perfil...

💜 Gracias por compartir. Este paso vale."""

    # Mensaje 2 - Con resultados
    CLIENT_ASESORADO_RESULTADOS_INTRO = """💜 Encontré {count} psicólogo(s) que se ajustan a tu búsqueda.

{resultados}"""

    # Mensaje 2 - Sin resultados
    CLIENT_ASESORADO_SIN_RESULTADOS = """💜 Gracias por compartir. Este paso vale.

🌿 No encontré psicólogos con exactamente esos filtros.

Pero no te preocupes, esto no significa que no haya profesionales para vos.

¿Qué querés hacer?
1️⃣ Ampliar la búsqueda (menos filtros)
2️⃣ Ver todos los profesionales disponibles
3️⃣ Empezar de nuevo

Responde con el número."""

    # Cierre con resultados
    CLIENT_ASESORADO_RESULTADOS = """💜 Encontré {count} psicólogo(s) que se ajustan a tu búsqueda.

{results_list}

🌿 Cada uno de estos profesionales puede acompañarte en tu proceso.

Responde con el número para ver más detalles.
O escribí '0' para hacer una nueva búsqueda."""

    # Sin resultados
    CLIENT_ASESORADO_SIN_RESULTADOS = """🌿 No encontré psicólogos con exactamente esos filtros.

Pero no te preocupes, esto no significa que no haya profesionales para vos.

¿Qué querés hacer?
1️⃣ Ampliar la búsqueda (menos filtros)
2️⃣ Ver todos los profesionales disponibles
3️⃣ Empezar de nuevo

Responde con el número."""


# Menú cuando no hay resultados
    CLIENT_ASESORADO_NO_RESULTS_MENU = """🌿 No encontré psicólogos con exactamente esos filtros.

Pero no te preocupes, esto no significa que no haya profesionales para vos.

¿Qué querés hacer?
1️⃣ Modificar un filtro específico
2️⃣ Ver todos los profesionales disponibles
3️⃣ Empezar de nuevo
0️⃣ Volver al menú

Responde con el número."""

    # Menú para elegir qué filtro modificar
    CLIENT_ASESORADO_MODIFY_FILTER_MENU = """🔧 ¿Qué filtro querés modificar o quitar?

Tus filtros actuales:
{filtros_actuales}

Seleccioná el filtro a modificar:
1️⃣ Enfoque terapéutico
2️⃣ Población
3️⃣ Modalidad
4️⃣ Zona
5️⃣ Horarios
6️⃣ Honorarios
0️⃣ Cancelar y volver

Responde con el número."""

    # Detalle del profesional (formato Psivale)
    CLIENT_PROFESSIONAL_DETAIL_PSIVALE = """🧠 {name}

🎯 Enfoque: {enfoque}
👥 Trabaja con: {poblacion}
💻 Modalidad: {modalidad}
📍 Zona: {zona}
📅 Horarios: {horarios}
💰 Honorarios: {honorarios}

📝 Sobre el profesional:
{bio}

━━━━━━━━━━━━━━━━━━━━

¿Qué querés hacer?
1️⃣ Ver contacto
2️⃣ Volver a resultados
3️⃣ Nueva búsqueda

Responde con el número."""

    CLIENT_CONTACTO_PSIVALE = """💜 Perfecto, acá está el contacto:

📱 WhatsApp: {phone}
📧 Email: {email}

🌿 Recordá que dar el primer paso vale.
Mucha suerte en tu proceso.

¿Qué querés hacer ahora?
1️⃣ Ver otros profesionales
2️⃣ Nueva búsqueda"""

    # ==========================================
    # MENSAJES DE TRANSICIÓN EMPÁTICOS
    # ==========================================

    PSIVALE_EXPLORANDO = """🌿 Está perfecto explorar.

PSIVALE conecta pacientes con psicólogos según su enfoque, disponibilidad y presupuesto.

Cuando estés list@ para buscar, escribí 'hola' y te ayudo.

💜 Dar el primer paso vale en cualquier momento."""

    PSIVALE_CUALQUIER_MOMENTO = """💜 Sin problema, volvé cuando quieras.

Acá vamos a estar para ayudarte cuando decidas dar ese primer paso.

🌿 Escribí 'hola' cuando estés list@."""

    # ==========================================
    # VALIDACIONES CON TONO PSIVALE
    # ==========================================

    PSIVALE_OPCION_INVALIDA = """🌿 No entendí esa opción.

Por favor, elegí uno de los números del menú.

Si tenés dudas, escribí '0' para volver al inicio."""

    PSIVALE_ERROR_GENERICO = """💜 Ups, algo salió mal.

No te preocupes, intentemos de nuevo.

Escribí 'hola' para empezar de nuevo, o '0' para volver al menú."""


# Create singleton instance
messages = Messages()
