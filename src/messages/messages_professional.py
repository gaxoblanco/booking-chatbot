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

1️⃣ Ver Mi Agenda

2️⃣ Actualizar Mi Información

3️⃣ Carga Rápida de Información

4️⃣ Mis {DomainConfig.APPOINTMENT_NAME_PLURAL.title()}

0️⃣ Volver al inicio

Responde con el número de opción."""



    # ==========================================
    # PROFESSIONAL - VIEW FULL SCHEDULE
    # ==========================================

    PROF_VIEW_SCHEDULE = f"""📅 *Mi Agenda Completa*

━━━━━━━━━━━━━━━━━━━━
Horario Semanal Configurado:
━━━━━━━━━━━━━━━━━━━━
{{working_hours_summary}}

━━━━━━━━━━━━━━━━━━━━
{DomainConfig.APPOINTMENT_NAME_PLURAL.title()} Próximas:
━━━━━━━━━━━━━━━━━━━━
{{appointments}}

💡 Para modificar tu disponibilidad, bloqueá eventos en Google Calendar.

_Escribe *0* para volver al menú_"""
    
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

    
# Singleton instance
professional_messages = ProfessionalMessages()
