"""
Professional Messages
=====================
Mensajes del flujo de PROFESIONAL.
Incluye: certificado, registro, horarios, gestión de agenda.
"""

from src.config.domain_config import DomainConfig


def _format_categories_list():
    """Format categories for display in messages."""
    categories_text = ""
    for key, value in DomainConfig.CATEGORIES.items():
        categories_text += f"{key}️⃣ {value}\n"
    return categories_text.strip()


class ProfessionalMessages:
    """
    Mensajes del flujo de profesional.
    Registro, carga de certificado, horarios, gestión de perfil.
    """

    # ==========================================
    # PROFESSIONAL - CERTIFICATE UPLOAD
    # ==========================================

#     PROF_NEED_CERTIFICATE = f"""{DomainConfig.EMOJI_CERTIFICATE} *Registro de {DomainConfig.PROFESSIONAL_TITLE}*

# Para comenzar, necesito que subas tu {DomainConfig.CERTIFICATE_NAME}.

# 📎 Envía una foto o PDF de tu:
# • Matrícula profesional
# • Título habilitante
# • Documento que acredite tu profesión

# ⚠️ Solo {DomainConfig.PROFESSIONAL_TITLE_PLURAL_LOWER} verificados aparecen en búsquedas.

# _Escribe *0* para volver al menú_"""

#     PROF_UPLOADING_CERTIFICATE = """📎 *Subiendo Certificado*

# Procesando tu archivo...

# Por favor espera un momento."""

#     PROF_CERTIFICATE_RECEIVED = """✅ *¡Certificado recibido!*

# Tu certificado ha sido guardado y verificado.

# Ya puedes gestionar tu agenda y perfil profesional.

# _Presiona cualquier tecla para continuar_"""

#     PROF_CERTIFICATE_ERROR = """❌ *Error al guardar certificado*

# No pudimos procesar el archivo.

# Por favor, intenta nuevamente enviando:
# • Una imagen (JPG, PNG)
# • Un PDF
# • Tamaño menor a 10MB

# _Escribe *0* para volver_"""

#     PROF_CERTIFICATE_INVALID_FORMAT = """❌ *Formato no válido*

# Solo se aceptan:
# • Imágenes: JPG, PNG
# • Documentos: PDF

# Por favor, envía un archivo válido."""

    # ==========================================
    # PROFESSIONAL - ACCESS KEY VERIFICATION
    # ==========================================

    PROF_NEED_ACCESS_KEY = f"""🔑 *Acceso de {DomainConfig.PROFESSIONAL_TITLE}*

Para acceder al sistema, necesitas una clave de acceso.

Esta clave es proporcionada por la administración.

Por favor, ingresa tu clave de acceso:

_Escribe *0* para volver al menú_"""

    PROF_VERIFY_KEY = """🔄 *Verificando clave...*

Por favor espera un momento."""

    PROF_KEY_VALID = """✅ *¡Acceso autorizado!*

Bienvenido al sistema de gestión.

Ya puedes gestionar tu agenda y perfil profesional.

_Presiona cualquier tecla para continuar al menú_"""

    PROF_KEY_INVALID = """❌ *Clave inválida*

La clave ingresada no es correcta.

Por favor:
- Verifica que hayas ingresado la clave correctamente
- Contacta a la administración si no tienes una clave
- Intenta nuevamente

_Escribe *0* para volver_"""

    PROF_KEY_EXPIRED = """⏰ *Clave expirada*

Esta clave ya no es válida.

Por favor contacta a la administración para obtener una nueva clave.

_Escribe *0* para volver_"""

    PROF_KEY_ALREADY_USED = """⚠️ *Clave ya utilizada*

Esta clave ya fue usada por otro profesional.

Cada clave solo puede usarse una vez.

Por favor contacta a la administración para obtener una nueva clave.

_Escribe *0* para volver_"""
    # ==========================================
    # PROFESSIONAL - MAIN MENU
    # ==========================================

    PROF_MAIN_MENU = f"""{DomainConfig.EMOJI_PROFESSIONAL} *Menú Profesional*

{DomainConfig.PROFESSIONAL_WELCOME}

¿Qué deseas hacer?

1️⃣ Gestionar Horarios Libres
   (Ver, agregar o eliminar horarios disponibles)

2️⃣ Cargar Agenda Semanal
   (Configurar horarios recurrentes ocupados)

3️⃣ Ver Mi Agenda Completa

4️⃣ Actualizar Mi Información

5️⃣ Carga Rápida de Información

6️⃣ Mis {DomainConfig.APPOINTMENT_NAME_PLURAL.title()}

0️⃣ Volver al inicio

Responde con el número de opción."""

    PROF_WELCOME_WITH_PENDING = f"""👋 ¡Hola {{name}}!

Tienes {{count}} {DomainConfig.APPOINTMENT_NAME}(s) pendiente(s) de confirmación.

¿Qué deseas hacer?
1️⃣ Ver {DomainConfig.APPOINTMENT_NAME_PLURAL} pendientes
2️⃣ Ver todas mis {DomainConfig.APPOINTMENT_NAME_PLURAL}
3️⃣ Gestionar horarios
0️⃣ Menú principal"""

    # ==========================================
    # PROFESSIONAL - FREE SLOTS (Liberar horarios)
    # ==========================================

    PROF_FREE_SLOT_ASK_DATE = """📅 *Liberar Horario*

¿Qué día tienes disponible?

Formato: DD/MM/YYYY
Ejemplo: 15/12/2024

_Escribe *0* para volver al menú_"""

    PROF_FREE_SLOT_ASK_TIME = """⏰ *Liberar Horario*

¿Qué horario tienes disponible?

Formato: HH:MM-HH:MM
Ejemplo: 14:00-15:00

Este horario quedará LIBRE para reservas.

_Escribe *0* para volver_"""

    PROF_FREE_SLOT_CONFIRM = """✅ *Confirmar Liberación*

📅 Fecha: {date}
⏰ Horario: {time_start} - {time_end}

Este horario quedará disponible para clientes.

¿Confirmar?
1️⃣ Sí, liberar
0️⃣ No, cancelar"""

    PROF_FREE_SLOT_SUCCESS = """✅ *¡Horario liberado!*

📅 {date}
⏰ {time_start} - {time_end}

Este horario ahora está disponible para clientes.

_Escribe *0* para volver al menú_"""

    PROF_FREE_SLOT_ERROR = """❌ *Error al liberar horario*

No se pudo guardar el horario.

Verifica:
• Que la fecha sea futura
• Que el formato sea correcto
• Que no se solape con otro horario

_Escribe *0* para volver_"""

    # ==========================================
    # PROFESSIONAL - MANAGE FREE SLOTS
    # ==========================================

    PROF_MANAGE_FREE_SLOTS = """📅 *Gestionar Horarios Libres*

Tus horarios libres actuales:

{free_slots_list}

¿Qué deseas hacer?
1️⃣ Agregar nuevo horario libre
2️⃣ Eliminar un horario
0️⃣ Volver al menú"""

    PROF_NO_FREE_SLOTS = """📅 *Gestionar Horarios Libres*

No tienes horarios libres configurados.

¿Deseas agregar uno?
1️⃣ Sí, agregar horario
0️⃣ Volver al menú"""

    PROF_DELETE_FREE_SLOT = """🗑️ *Eliminar Horario*

Selecciona el horario a eliminar:

{free_slots_list}

Envía el número del horario.
_Escribe *0* para cancelar_"""

    PROF_DELETE_FREE_SLOT_CONFIRM = """⚠️ *Confirmar Eliminación*

¿Estás seguro que deseas eliminar este horario?

📅 {date}
⏰ {time_start} - {time_end}

1️⃣ Sí, eliminar
0️⃣ No, cancelar"""

    PROF_FREE_SLOT_DELETED = """✅ *Horario eliminado*

El horario ha sido eliminado de tu agenda.

_Escribe *0* para volver_"""

    # ==========================================
    # PROFESSIONAL - WEEKLY SCHEDULE
    # ==========================================

    PROF_WEEK_QUICK_FORMAT = """📅 *Carga Rápida de Semana*

Envía tu agenda semanal OCUPADA en el siguiente formato:

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

lunes, martes, miércoles, jueves, viernes, sábado, domingo

💡 Puedes enviar los días en cualquier orden
💡 Envía solo los días que estés ocupado
💡 Los horarios NO incluidos quedarán libres

_Escribe *0* para volver al menú_"""

    PROF_WEEK_PROCESSING = """⏳ *Procesando agenda semanal...*

Guardando tus horarios ocupados."""

    PROF_WEEK_SUCCESS = """✅ *¡Semana configurada!*

Tu agenda semanal ha sido guardada:

{schedule_summary}

Estos horarios se repetirán cada semana.
Los horarios NO incluidos quedarán libres para reservas.

_Escribe *0* para volver al menú_"""

    PROF_WEEK_ERROR = """❌ *Error al procesar agenda*

No se pudo procesar tu agenda semanal.

Verifica:
• El formato de días (lunes, martes, etc.)
• El formato de horarios (HH:MM-HH:MM)
• Que no haya espacios extra

_Escribe *0* para volver_"""

    # ==========================================
    # PROFESSIONAL - WEEKLY SCHEDULE (Step by Step)
    # ==========================================

    PROF_WEEK_ASK_DAY = f"""📅 *Configurar Semana*

¿Qué día quieres configurar?

1️⃣ Lunes
2️⃣ Martes
3️⃣ Miércoles
4️⃣ Jueves
5️⃣ Viernes
6️⃣ Sábado
7️⃣ Domingo

Responde con el número.
_Escribe *0* para volver al menú_"""

    PROF_WEEK_ASK_TIME = """⏰ *Horario para {day}*

¿Qué horario estás OCUPADO este día?

Formato: HH:MM-HH:MM
Ejemplo: 09:00-17:00

Este será tu horario recurrente cada {day}.

_Escribe *0* para volver_"""

    PROF_WEEK_ASK_MORE = """✅ *{day} configurado*

{day}: {time_start} - {time_end}

¿Quieres configurar otro día?

1️⃣ Sí, agregar otro día
2️⃣ Finalizar y guardar

━━━━━━━━━━━━━━━━━━━━
Días configurados:
{configured_days}
━━━━━━━━━━━━━━━━━━━━

_Escribe *0* para cancelar_"""

    # ==========================================
    # PROFESSIONAL - WEEKLY SCHEDULE
    # ==========================================

    # Quick format (todo en un mensaje)
    PROF_WEEK_QUICK_FORMAT = """📅 *Carga Rápida de Semana*

Envía tu agenda semanal OCUPADA en el siguiente formato:

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

lunes, martes, miércoles, jueves, viernes, sábado, domingo

💡 Puedes enviar los días en cualquier orden
💡 Envía solo los días que estés ocupado
💡 Los horarios NO incluidos quedarán libres

_Escribe *0* para volver al menú_"""

    PROF_WEEK_PROCESSING = """⏳ *Procesando agenda semanal...*

Guardando tus horarios ocupados."""

    PROF_WEEK_SUCCESS = """✅ *¡Semana configurada!*

Tu agenda semanal ha sido guardada:

{schedule_summary}

Estos horarios se repetirán cada semana.
Los horarios NO incluidos quedarán libres para reservas.

_Escribe *0* para volver al menú_"""

    PROF_WEEK_ERROR = """❌ *Error al procesar agenda*

No se pudo procesar tu agenda semanal.

Verifica:
- El formato de días (lunes, martes, etc.)
- El formato de horarios (HH:MM-HH:MM)
- Que no haya espacios extra

_Escribe *0* para volver_"""

    # ==========================================
    # PROFESSIONAL - WEEKLY SCHEDULE (Step by Step)
    # ==========================================

    PROF_WEEK_ASK_DAY = f"""📅 *Configurar Semana*

¿Qué día quieres configurar?

1️⃣ Lunes
2️⃣ Martes
3️⃣ Miércoles
4️⃣ Jueves
5️⃣ Viernes
6️⃣ Sábado
7️⃣ Domingo

Responde con el número.
_Escribe *0* para volver al menú_"""

    PROF_WEEK_ASK_TIME = """⏰ *Horario para {day}*

¿Qué horario estás OCUPADO este día?

Formato: HH:MM-HH:MM
Ejemplo: 09:00-17:00

Este será tu horario recurrente cada {day}.

_Escribe *0* para volver_"""

    PROF_WEEK_ASK_MORE = """✅ *{day} configurado*

{day}: {time_start} - {time_end}

¿Quieres configurar otro día?

1️⃣ Sí, agregar otro día
2️⃣ Finalizar y guardar

━━━━━━━━━━━━━━━━━━━━
Días configurados:
{configured_days}
━━━━━━━━━━━━━━━━━━━━

_Escribe *0* para cancelar_"""

    # ==========================================
    # PROFESSIONAL - VIEW FULL SCHEDULE
    # ==========================================

    PROF_VIEW_SCHEDULE = """📅 *Mi Agenda Completa*

━━━━━━━━━━━━━━━━━━━━
Horarios Semanales (Ocupados):
━━━━━━━━━━━━━━━━━━━━
{weekly_schedule}

━━━━━━━━━━━━━━━━━━━━
Horarios Específicos (Libres):
━━━━━━━━━━━━━━━━━━━━
{specific_slots}

━━━━━━━━━━━━━━━━━━━━
{DomainConfig.APPOINTMENT_NAME_PLURAL.title()} Próximas:
━━━━━━━━━━━━━━━━━━━━
{appointments}

_Escribe *0* para volver al menú_"""

    PROF_NO_SCHEDULE_CONFIGURED = """📅 *Mi Agenda Completa*

No tienes horarios configurados aún.

¿Qué deseas hacer?
1️⃣ Configurar agenda semanal
2️⃣ Agregar horarios libres
0️⃣ Volver al menú"""

    # ==========================================
    # PROFESSIONAL - UPDATE INFO (Menu)
    # ==========================================

    PROF_INFO_MENU = f"""📋 *Actualizar Información*

Configura tu perfil profesional:

1️⃣ Nombre
2️⃣ Email
3️⃣ Zona (Norte/Sur)
4️⃣ Género
5️⃣ {DomainConfig.CUSTOM_FIELD_1_LABEL if DomainConfig.CUSTOM_FIELD_1_ENABLED else 'Prepaga'} (Sí/No)
6️⃣ {DomainConfig.CATEGORY_LABEL}
7️⃣ Descripción Personal
8️⃣ Rango de Honorarios

9️⃣ Guardar Información
0️⃣ Volver al menú

━━━━━━━━━━━━━━━━━━━━
Información actual:
{{current_info}}
━━━━━━━━━━━━━━━━━━━━

Responde con el número de opción."""

    # ==========================================
    # PROFESSIONAL - UPDATE INFO (Individual fields)
    # ==========================================

    PROF_INFO_ASK_NAME = """👤 *Nombre*

Ingresa tu nombre completo:
Ejemplo: Dr. Juan Pérez

_Escribe *0* para volver_"""

    PROF_INFO_ASK_EMAIL = """📧 *Email*

Ingresa tu email de contacto:
Ejemplo: juan.perez@email.com

_Escribe *0* para volver_"""

    PROF_INFO_ASK_ZONA = """📍 *Zona*

¿En qué zona trabajas?

1️⃣ Zona Norte
2️⃣ Zona Sur

Responde con el número.
_Escribe *0* para volver_"""

    PROF_INFO_ASK_GENERO = """👥 *Género*

Selecciona tu género:

1️⃣ Masculino
2️⃣ Femenino

Responde con el número.
_Escribe *0* para volver_"""

    PROF_INFO_ASK_PREPAGA = f"""💳 *{DomainConfig.CUSTOM_FIELD_1_LABEL if DomainConfig.CUSTOM_FIELD_1_ENABLED else 'Prepaga'}*

¿Aceptas {DomainConfig.CUSTOM_FIELD_1_LABEL.lower() if DomainConfig.CUSTOM_FIELD_1_ENABLED else 'obras sociales/prepagas'}?

1️⃣ Sí
2️⃣ No

Responde con el número.
_Escribe *0* para volver_"""

    PROF_INFO_ASK_ESPECIALIDAD = f"""{DomainConfig.EMOJI_CATEGORY} *{DomainConfig.CATEGORY_LABEL}*

{DomainConfig.CATEGORY_PROMPT}

{_format_categories_list()}

Responde con el número o escribe tu {DomainConfig.CATEGORY_LABEL_LOWER}.
_Escribe *0* para volver_"""

    PROF_INFO_ASK_BIO = f"""📝 *Descripción Personal*

Escribe una breve descripción sobre ti:

Ejemplo:
• {DomainConfig.CATEGORY_CUSTOM_EXAMPLE1}
• {DomainConfig.CATEGORY_CUSTOM_EXAMPLE2}

_Escribe *0* para volver_"""

    PROF_INFO_ASK_FEE_RANGE = f"""💰 *Rango de Honorarios*

¿Cuánto cobras por {DomainConfig.APPOINTMENT_NAME}?

Formato: MÍNIMO-MÁXIMO
Ejemplo: 100-150

_Escribe *0* para volver_"""

# ==========================================
# PROFESSIONAL - INFO SAVED/ERROR
# ==========================================

    PROF_INFO_FIELD_SAVED = """✅ *Guardado*

{field_name}: {value}

Volviendo al menú de información..."""

    PROF_INFO_SAVED = """✅ *¡Información guardada!*

Tu perfil profesional:
{profile_summary}

Esta información será visible para los clientes.

_Escribe *0* para volver al menú_"""

    PROF_INFO_INCOMPLETE = """⚠️ *Información incompleta*

Debes completar al menos:
• Nombre
• {category_label}
• Zona

Antes de guardar.

_Volviendo al menú..._"""

    # ==========================================
    # PROFESSIONAL - QUICK INFO FORMAT
    # ==========================================

    PROF_INFO_QUICK_FORMAT = f"""📋 *Carga Rápida de Información*

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
- genero: masculino, femenino (m, f)
- prepaga: si, no (o s, n)
- especialidad: texto libre
- bio: texto libre (opcional)
- honorarios: MÍNIMO-MÁXIMO (opcional, ej: 100-150)

💡 Los campos bio y honorarios son opcionales

_Escribe *0* para volver_"""

    PROF_INFO_QUICK_PROCESSING = """⏳ *Procesando información...*

Guardando tus datos profesionales."""

    PROF_INFO_QUICK_SUCCESS = """✅ *¡Información cargada!*

Tu perfil ha sido actualizado exitosamente.

{profile_summary}

_Escribe *0* para volver al menú_"""

    PROF_INFO_QUICK_ERROR = """❌ *Error al procesar información*

No se pudo procesar tu información.

Verifica:
• El formato (con o sin etiquetas)
• Los valores de zona, género, prepaga
• Que todos los campos requeridos estén completos

_Escribe *0* para volver_"""

 # ==========================================
 # PROFESSIONAL - STATISTICS/METRICS
 # ==========================================

    PROF_VIEW_STATS = f"""📊 *Mis Estadísticas*

━━━━━━━━━━━━━━━━━━━━
Visibilidad:
━━━━━━━━━━━━━━━━━━━━
👁️ Vistas en búsquedas: {{total_views}}
👤 Vistas de perfil: {{profile_views}}
📞 Contactos: {{total_contacts}}

━━━━━━━━━━━━━━━━━━━━
{DomainConfig.APPOINTMENT_NAME_PLURAL.title()}:
━━━━━━━━━━━━━━━━━━━━
✅ Confirmadas: {{confirmed}}
⏳ Pendientes: {{pending}}
✔️ Completadas: {{completed}}
❌ Canceladas: {{cancelled}}

━━━━━━━━━━━━━━━━━━━━
Última actualización: {{last_updated}}
━━━━━━━━━━━━━━━━━━━━

_Escribe *0* para volver_"""

    # ==========================================
    # HELPER METHODS
    # ==========================================

    @staticmethod
    def format_schedule_summary(schedule: dict) -> str:
        """
        Formatear resumen de horarios semanales.

        Args:
            schedule: Diccionario con horarios por día

        Returns:
            String formateado con resumen
        """
        from messages_common import common_messages

        if not schedule:
            return "Sin horarios configurados"

        summary_lines = []
        for day_num, times in sorted(schedule.items()):
            day_name = common_messages.format_day_name(day_num)
            times_str = ", ".join([f"{t['start']}-{t['end']}" for t in times])
            summary_lines.append(f"• {day_name}: {times_str}")

        return "\n".join(summary_lines)

    @staticmethod
    def format_free_slots_list(slots: list) -> str:
        """
        Formatear lista de horarios libres.

        Args:
            slots: Lista de slots libres

        Returns:
            String formateado para mostrar
        """
        from messages_common import common_messages

        if not slots:
            return "Sin horarios libres configurados"

        slots_lines = []
        for i, slot in enumerate(slots, 1):
            date_formatted = common_messages.format_date_natural(slot['date'])
            time_str = f"{slot['start_time']}-{slot['end_time']}"
            slots_lines.append(f"{i}. {date_formatted} | {time_str}")

        return "\n".join(slots_lines)

    @staticmethod
    def format_profile_summary(professional: dict) -> str:
        """
        Formatear resumen de perfil profesional.

        Args:
            professional: Diccionario con datos del profesional

        Returns:
            String formateado con resumen del perfil
        """
        from messages_common import common_messages

        lines = []

        if professional.get('name'):
            lines.append(f"👤 Nombre: {professional['name']}")

        if professional.get('email'):
            lines.append(f"📧 Email: {professional['email']}")

        if professional.get('zone'):
            zona = common_messages.format_zona(professional['zone'])
            lines.append(f"📍 Zona: {zona}")

        if professional.get('gender'):
            gender = common_messages.format_gender(professional['gender'])
            lines.append(f"👥 Género: {gender}")

        if 'accept_prepaga' in professional:
            prepaga = common_messages.format_boolean(
                professional['accept_prepaga'])
            label = DomainConfig.CUSTOM_FIELD_1_LABEL if DomainConfig.CUSTOM_FIELD_1_ENABLED else 'Prepaga'
            lines.append(f"💳 {label}: {prepaga}")

        if professional.get('category'):
            lines.append(
                f"💼 {DomainConfig.CATEGORY_LABEL}: {professional['category']}")

        if professional.get('bio'):
            bio_truncated = common_messages.truncate_text(
                professional['bio'], 80)
            lines.append(f"📝 Bio: {bio_truncated}")

        if professional.get('fee_range'):
            lines.append(f"💰 Honorarios: ${professional['fee_range']}")

        return "\n".join(lines) if lines else "Sin información cargada"


# Singleton instance
professional_messages = ProfessionalMessages()
