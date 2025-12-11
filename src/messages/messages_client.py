"""
Client Messages
===============
Mensajes del flujo de CLIENTE.
Incluye: menú principal, búsqueda, filtros, resultados, detalle de profesional.
"""

from src.config.domain_config import DomainConfig


class ClientMessages:
    """
    Mensajes del flujo de cliente.
    Búsqueda de profesionales y visualización de resultados.
    """

    # ==========================================
    # CLIENT - MAIN MENU
    # ==========================================

    CLIENT_MAIN_MENU = f"""{DomainConfig.EMOJI_CLIENT} *Menú Cliente*

{DomainConfig.CLIENT_WELCOME}

Buscar {DomainConfig.PROFESSIONAL_TITLE_PLURAL_LOWER} disponibles:

1️⃣ Buscar para Hoy
2️⃣ Búsqueda Avanzada (Paso a Paso)
3️⃣ Búsqueda Rápida (Todo en 1 mensaje)
4️⃣ Mis {DomainConfig.APPOINTMENT_NAME_PLURAL}

0️⃣ Volver al inicio

Responde con el número de opción."""

    CLIENT_WELCOME_WITH_APPOINTMENTS = f"""👋 ¡Hola {{name}}!

Tienes {DomainConfig.APPOINTMENT_NAME_PLURAL} próximas:

{{appointments_preview}}

¿Qué deseas hacer?
1️⃣ Ver mis {DomainConfig.APPOINTMENT_NAME_PLURAL}
2️⃣ Buscar nuevo {DomainConfig.PROFESSIONAL_TITLE_LOWER}
0️⃣ Salir"""

    # ==========================================
    # CLIENT - QUICK SEARCH (Today)
    # ==========================================

    CLIENT_SEARCH_TODAY_CONFIRM = f"""🔍 *Buscar para Hoy*

Buscando {DomainConfig.PROFESSIONAL_TITLE_PLURAL_LOWER} disponibles HOY ({{today_date}})

¿En qué horario preferís?

1️⃣ Mañana (8:00 - 13:00)
2️⃣ Tarde (13:00 - 20:00)
3️⃣ Cualquier horario

Responde con el número o escribe el horario exacto (ej: 14:00)

_Escribe *0* para volver al menú_"""

    CLIENT_SEARCH_TODAY_NO_RESULTS = f"""😔 *Sin disponibilidad para hoy*

No encontramos {DomainConfig.PROFESSIONAL_TITLE_PLURAL_LOWER} disponibles para hoy en ese horario.

¿Qué deseas hacer?
1️⃣ Buscar para otra fecha
2️⃣ Ver todos los {DomainConfig.PROFESSIONAL_TITLE_PLURAL_LOWER}
0️⃣ Volver al menú"""

    # ==========================================
    # CLIENT - ADVANCED SEARCH (Multi-filter)
    # ==========================================

    @staticmethod
    def CLIENT_MULTIFILTER_MENU(active_filters: str = "") -> str:
        """
        Generate multifilter menu with active filters.

        Args:
            active_filters: String with currently active filters

        Returns:
            Formatted menu string
        """
        filters_section = ""
        if active_filters:
            filters_section = f"""
━━━━━━━━━━━━━━━━━━━━
Filtros activos:
{active_filters}
━━━━━━━━━━━━━━━━━━━━
"""

        return f"""{DomainConfig.EMOJI_CLIENT} *Búsqueda Avanzada*

Selecciona los filtros que desees (uno a la vez):

1️⃣ Zona
2️⃣ Disponibilidad (Fecha/Hora)
3️⃣ {DomainConfig.CUSTOM_FIELD_1_LABEL if DomainConfig.CUSTOM_FIELD_1_ENABLED else 'Prepaga'}
4️⃣ Género del {DomainConfig.PROFESSIONAL_TITLE}
5️⃣ {DomainConfig.CATEGORY_LABEL}

9️⃣ Buscar con filtros actuales
0️⃣ Volver al menú
{filters_section}
Responde con el número de opción."""

    @staticmethod
    def CLIENT_MULTIFILTER_ADDED(filter_name: str, menu: str) -> str:
        """Show filter added confirmation with updated menu."""
        return f"""✅ Filtro agregado: {filter_name}

{menu}"""

    CLIENT_CLEAR_FILTERS_CONFIRM = """🗑️ *Limpiar Filtros*

¿Deseas limpiar todos los filtros?

1️⃣ Sí, limpiar
0️⃣ No, volver"""

    CLIENT_FILTERS_CLEARED = """✅ *Filtros Limpiados*

Todos los filtros han sido eliminados.

Volviendo al menú de búsqueda..."""

    # ==========================================
    # CLIENT - FILTER: ZONA
    # ==========================================

    CLIENT_ASK_ZONA = f"""📍 *Filtrar por Zona*

¿En qué zona buscas?

{{zone_options}}

Responde con el número.
_Escribe *0* para volver_"""

    CLIENT_ZONA_SELECTED = """✅ Zona seleccionada: {zona}

Volviendo al menú de filtros..."""

    # ==========================================
    # CLIENT - FILTER: DISPONIBILIDAD
    # ==========================================

    CLIENT_ASK_FECHA = """📅 *Filtrar por Disponibilidad - Fecha*

¿Qué día necesitas?

Formato: DD/MM/YYYY
Ejemplo: 15/12/2024

_Escribe *0* para volver_"""

    CLIENT_FECHA_SELECTED = """✅ Fecha seleccionada: {fecha}

Ahora selecciona el horario..."""

    CLIENT_ASK_HORA = """⏰ *Filtrar por Disponibilidad - Horario*

¿A qué hora necesitas?

1️⃣ Mañana (8:00 - 13:00)
2️⃣ Tarde (13:00 - 18:00)
3️⃣ Noche (18:00 - 21:00)
4️⃣ Cualquier horario

O escribe la hora exacta (formato HH:MM, ej: 14:00)

_Escribe *0* para volver_"""

    CLIENT_HORA_SELECTED = """✅ Horario seleccionado: {hora}

Volviendo al menú de filtros..."""

    # ==========================================
    # CLIENT - FILTER: PREPAGA
    # ==========================================

    CLIENT_ASK_PREPAGA = f"""💳 *Filtrar por {DomainConfig.CUSTOM_FIELD_1_LABEL if DomainConfig.CUSTOM_FIELD_1_ENABLED else 'Prepaga'}*

¿Buscas {DomainConfig.PROFESSIONAL_TITLE_PLURAL_LOWER} que acepten {DomainConfig.CUSTOM_FIELD_1_LABEL.lower() if DomainConfig.CUSTOM_FIELD_1_ENABLED else 'prepaga'}?

1️⃣ Sí, con {DomainConfig.CUSTOM_FIELD_1_LABEL.lower() if DomainConfig.CUSTOM_FIELD_1_ENABLED else 'prepaga'}
2️⃣ No, sin {DomainConfig.CUSTOM_FIELD_1_LABEL.lower() if DomainConfig.CUSTOM_FIELD_1_ENABLED else 'prepaga'}
3️⃣ No importa

Responde con el número.
_Escribe *0* para volver_"""

    CLIENT_PREPAGA_SELECTED = """✅ {filter_name} seleccionado: {value}

Volviendo al menú de filtros..."""

    # ==========================================
    # CLIENT - FILTER: GENERO
    # ==========================================

    CLIENT_ASK_SEXO = f"""👥 *Filtrar por Género del {DomainConfig.PROFESSIONAL_TITLE}*

¿Qué prefieres?

1️⃣ Masculino
2️⃣ Femenino
3️⃣ Otro
4️⃣ No importa

Responde con el número.
_Escribe *0* para volver_"""

    CLIENT_SEXO_SELECTED = """✅ Género seleccionado: {sexo}

Volviendo al menú de filtros..."""

    # ==========================================
    # CLIENT - FILTER: ESPECIALIDAD/CATEGORIA
    # ==========================================

    CLIENT_ASK_ESPECIALIDAD = f"""💼 *Filtrar por {DomainConfig.CATEGORY_LABEL}*

¿Qué {DomainConfig.CATEGORY_LABEL_LOWER} buscas?

{{category_options}}

Responde con el número.
_Escribe *0* para volver_"""

    CLIENT_ESPECIALIDAD_SELECTED = """✅ {category_label} seleccionada: {especialidad}

Volviendo al menú de filtros..."""

    # ==========================================
    # CLIENT - SEARCH EXECUTION
    # ==========================================

    CLIENT_SEARCH_SUMMARY = """🔍 *Buscando con filtros:*

{filters_summary}

Buscando {professional_plural}..."""

    @staticmethod
    def CLIENT_MULTIFILTER_SEARCH_SUMMARY(filters_list: str) -> str:
        """Show search summary with active filters."""
        return f"""🔍 Buscando {DomainConfig.PROFESSIONAL_TITLE_PLURAL_LOWER} con los siguientes filtros:

{filters_list}

Procesando búsqueda..."""

    CLIENT_SEARCHING = f"""⏳ Buscando...

Estamos buscando los mejores {DomainConfig.PROFESSIONAL_TITLE_PLURAL_LOWER} para ti."""

    # ==========================================
    # CLIENT - SEARCH RESULTS
    # ==========================================

    CLIENT_NO_RESULTS = f"""😔 *No se encontraron {DomainConfig.PROFESSIONAL_TITLE_PLURAL_LOWER}*

Con los filtros seleccionados no hay {DomainConfig.PROFESSIONAL_TITLE_PLURAL_LOWER} disponibles.

¿Qué deseas hacer?
1️⃣ Modificar filtros
2️⃣ Ver todos los {DomainConfig.PROFESSIONAL_TITLE_PLURAL_LOWER}
0️⃣ Volver al menú"""

    CLIENT_RESULTS_FOUND = f"""✅ *Encontrados {{count}} {DomainConfig.PROFESSIONAL_TITLE_LOWER}(es)*

{{results_list}}

Responde con el número para ver detalles.
_Escribe *0* para volver al menú_"""

    CLIENT_RESULTS_ITEM = """{{number}}. {{name}}
   📍 {{zona}} | {{category}}
   {{availability_preview}}"""

    # ==========================================
    # CLIENT - PROFESSIONAL DETAIL
    # ==========================================

    CLIENT_PROFESSIONAL_DETAIL = f"""👨‍⚕️ *{{name}}*

💼 {DomainConfig.CATEGORY_LABEL}: {{category}}
📍 Zona: {{zona}}
👤 Género: {{gender}}
{{custom_field_1}}
{{bio}}
{{fee_range}}

📅 *Disponibilidad:*
{{availability}}

📞 Contacto: {{phone}}
{{email}}

¿Qué deseas hacer?
1️⃣ Agendar {DomainConfig.APPOINTMENT_NAME}
2️⃣ Contactar por WhatsApp
3️⃣ Volver a resultados
0️⃣ Menú principal"""

    CLIENT_PROFESSIONAL_DETAIL_NO_AVAILABILITY = """⏰ *Disponibilidad:*
Sin horarios cargados aún.
Contacta al {professional_title} para coordinar."""

    # ==========================================
    # CLIENT - CONTACT PROFESSIONAL
    # ==========================================

    CLIENT_CONTACT_LOGGED = f"""✅ *Contacto registrado*

Hemos registrado tu interés en este {DomainConfig.PROFESSIONAL_TITLE_LOWER}.

Puedes contactarlo directamente:
📞 {{phone}}

¿Qué deseas hacer?
1️⃣ Ver otros {DomainConfig.PROFESSIONAL_TITLE_PLURAL_LOWER}
2️⃣ Nueva búsqueda
0️⃣ Volver al menú"""

    CLIENT_CONTACT_OPENING_WHATSAPP = f"""📱 *Abriendo WhatsApp*

Te redirigiremos a WhatsApp para contactar con:
{{name}}

{{phone}}

_Escribe *0* si prefieres volver_"""

    # ==========================================
    # CLIENT - QUICK SEARCH FORMAT
    # ==========================================

    CLIENT_SEARCH_QUICK_FORMAT = f"""🔍 *Búsqueda Rápida*

Envía tus filtros en cualquiera de estos formatos:

━━━━━━━━━━━━━━━━━━━━
OPCIÓN 1 - Con etiquetas:
━━━━━━━━━━━━━━━━━━━━

zona: norte
fecha: 15/12/2024
hora: 14:00
prepaga: si
genero: masculino

━━━━━━━━━━━━━━━━━━━━
OPCIÓN 2 - Sin etiquetas (orden importante):
━━━━━━━━━━━━━━━━━━━━

norte
15/12/2024
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

━━━━━━━━━━━━━━━━━━━━
Ejemplos:
━━━━━━━━━━━━━━━━━━━━

Solo zona:
zona: norte

Zona y fecha:
zona: norte
fecha: 15/12/2024

Todo:
norte
15/12/2024
14:00
si
masculino

_Escribe *0* para volver_"""

    CLIENT_SEARCH_QUICK_PARSING = """⏳ Procesando búsqueda rápida...

Analizando tus filtros..."""

    CLIENT_SEARCH_QUICK_ERROR = """❌ *Formato incorrecto*

No pudimos procesar tu búsqueda rápida.

Por favor:
• Verifica el formato
• O usa la búsqueda avanzada paso a paso

_Escribe *0* para volver_"""

    # ==========================================
    # CLIENT - MODALITY SELECTION
    # ==========================================

    CLIENT_SELECT_MODALITY = f"""📍 *Modalidad de Búsqueda*

¿Cómo prefieres la atención?

1️⃣ Presencial (En consultorio)
2️⃣ Virtual (Videollamada)
3️⃣ Ambas modalidades

Responde con el número.
_Escribe *0* para volver_"""

    CLIENT_MODALITY_SELECTED = """✅ Modalidad seleccionada: {modality}

Continuando búsqueda..."""

    # ==========================================
    # HELPER METHODS
    # ==========================================

    @staticmethod
    def format_professional_card(professional: dict) -> str:
        """
        Formatear tarjeta de profesional para lista de resultados.

        Args:
            professional: Diccionario con datos del profesional

        Returns:
            String formateado para mostrar en lista
        """
        from messages_common import common_messages

        name = professional.get('name', 'Sin nombre')
        zona = common_messages.format_zona(professional.get('zone', ''))
        category = professional.get('category', DomainConfig.CATEGORY_LABEL)

        # Disponibilidad preview (simplificado)
        availability = "Ver disponibilidad"

        return f"""📍 {zona} | 💼 {category}
⏰ {availability}"""

    @staticmethod
    def format_availability_preview(professional: dict) -> str:
        """
        Formatear preview de disponibilidad para lista.

        Args:
            professional: Diccionario con datos del profesional

        Returns:
            Preview de disponibilidad
        """
        # Esto se puede expandir para mostrar próximo horario disponible
        return "Consultar disponibilidad"

    @staticmethod
    def format_filters_summary(filters: dict) -> str:
        """
        Formatear resumen de filtros activos.

        Args:
            filters: Diccionario con filtros activos

        Returns:
            String formateado con resumen de filtros
        """
        from messages_common import common_messages

        summary_parts = []

        if 'zona' in filters and filters['zona']:
            zona_formatted = common_messages.format_zona(filters['zona'])
            summary_parts.append(f"📍 Zona: {zona_formatted}")

        if 'fecha' in filters and filters['fecha']:
            summary_parts.append(f"📅 Fecha: {filters['fecha']}")

        if 'hora' in filters and filters['hora']:
            summary_parts.append(f"⏰ Hora: {filters['hora']}")

        if 'prepaga' in filters and filters['prepaga'] is not None:
            prepaga_formatted = common_messages.format_boolean(
                filters['prepaga'])
            label = DomainConfig.CUSTOM_FIELD_1_LABEL if DomainConfig.CUSTOM_FIELD_1_ENABLED else 'Prepaga'
            summary_parts.append(f"💳 {label}: {prepaga_formatted}")

        if 'genero' in filters and filters['genero']:
            gender_formatted = common_messages.format_gender(filters['genero'])
            summary_parts.append(f"👤 Género: {gender_formatted}")

        if 'especialidad' in filters and filters['especialidad']:
            summary_parts.append(
                f"💼 {DomainConfig.CATEGORY_LABEL}: {filters['especialidad']}")

        return "\n".join(summary_parts) if summary_parts else "Sin filtros aplicados"

    @staticmethod
    def format_zone_options() -> str:
        """
        Formatear opciones de zona dinámicamente desde config.

        Returns:
            String con opciones de zona numeradas
        """
        options = []
        for i, (key, value) in enumerate(DomainConfig.ZONES.items(), 1):
            options.append(f"{i}️⃣ {value}")
        options.append(f"{len(DomainConfig.ZONES) + 1}️⃣ Cualquier zona")
        return "\n".join(options)

    @staticmethod
    def format_category_options() -> str:
        """
        Formatear opciones de categoría dinámicamente desde config.

        Returns:
            String con opciones de categoría numeradas
        """
        options = []
        for key, value in DomainConfig.CATEGORIES.items():
            options.append(f"{key}. {value}")
        return "\n".join(options)


# Singleton instance
client_messages = ClientMessages()
