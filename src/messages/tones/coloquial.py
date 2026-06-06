"""
Tono: Coloquial
===============
Para centros de salud locales. Formosa y NOA.
Vecinal, directo, sin corporativismo.

Guía de estilo aplicada:
  R1 — terminar en positivo (acción o beneficio)
  R2 — determinados y posesivos (tu turno, el profesional)
  R3 — una idea por mensaje
  R4 — power words
  R5 — sin gerundios encadenados
  R6 — oraciones cortas, verbos de acción
"""

from src.config.domain_config import DomainConfig

# ==================================================
# COMMON — errores y validaciones genéricas
# ==================================================

INVALID_OPTION = "Opción no válida. Elegí una de las opciones del menú."

INVALID_DATE = "No reconocí esa fecha. Probá con 'mañana', 'el lunes' o una fecha tipo 25/12."

INVALID_TIME = "No reconocí ese horario. Probá con '9:00' o 'por la tarde'."

ERROR_GENERIC = "Algo salió mal. Escribí *menu* para volver al inicio."

ERROR_UNKNOWN_STATE = "Algo salió mal. Escribí *menu* para volver al inicio."

UNKNOWN_QUERY = (
    "Por acá puedo ayudarte con turnos.\n\n"
    "Podés buscar un profesional, ver tus turnos o consultar info del centro.\n\n"
    "¿Qué necesitás?"
)

HELP_MESSAGE = (
    "Puedo ayudarte a:\n\n"
    "• Buscar un profesional y sacar turno\n"
    "• Ver tus turnos programados\n"
    "• Consultar información del centro\n\n"
    "Escribí lo que necesitás o elegí una opción del menú."
)

# ==================================================
# CLIENT — menú y búsqueda
# ==================================================

CLIENT_MAIN_MENU = (
    "¿Qué necesitás?\n\n"
    "1️⃣ Buscar profesional\n"
    "2️⃣ Ver disponibles mañana\n"
    "3️⃣ Información del centro\n\n"
    "Respondé con el número."
)

CLIENT_ASK_FECHA = (
    "¿Para qué fecha necesitás el turno?\n\n"
    "Podés escribir 'mañana', 'el lunes' o una fecha como 25/12.\n\n"
    "_Escribí *0* para volver_"
)

CLIENT_ASK_HORA = (
    "¿A qué hora preferís?\n\n"
    "Podés escribir 'mañana', 'tarde', 'noche' o un horario como '10:00'.\n\n"
    "_Escribí *0* para volver_"
)

CLIENT_ASK_ZONA = (
    "¿En qué zona preferís?\n\n"
    + "\n".join(
        f"• {v}" for v in DomainConfig.ZONES.values()
    )
    + "\n\n_Escribí *0* para volver_"
)

CLIENT_ASK_PREPAGA = (
    "¿Necesitás que acepte obra social o prepaga?\n\n"
    "1️⃣ Sí\n"
    "2️⃣ No importa\n\n"
    "_Escribí *0* para volver_"
)

CLIENT_ASK_SEXO = (
    "¿Tenés preferencia por el género del profesional?\n\n"
    "1️⃣ Masculino\n"
    "2️⃣ Femenino\n"
    "3️⃣ No importa\n\n"
    "_Escribí *0* para volver_"
)

CLIENT_NO_RESULTS = (
    "No encontramos profesionales para esos filtros.\n\n"
    "1️⃣ Modificar filtros\n"
    "2️⃣ Ver todos sin filtros\n"
    "0️⃣ Volver al menú"
)

CLIENT_MULTIFILTER_ADDED = "Filtro agregado. ¿Querés agregar otro o buscar ahora?"

CLIENT_SEARCH_QUICK_FORMAT = (
    "{emoji} *{name}*\n"
    "📅 {date} — 🕐 {first_slot} a {last_slot}\n"
)

# ==================================================
# APPOINTMENTS — citas y cancelaciones
# ==================================================

CLIENT_VIEW_APPOINTMENTS = (
    "📅 Tus turnos:\n\n"
    "{appointments_list}\n\n"
    "_Enviá el número para ver detalles_\n"
    "_Escribí *0* para volver al menú_"
)

CLIENT_NO_APPOINTMENTS = (
    "No tenés {appointment_plural} programadas.\n\n"
    "1️⃣ Buscar profesional\n"
    "0️⃣ Volver al menú"
)

CLIENT_BOOKING_COLLECT_NAME = (
    "¿Cuál es tu nombre completo?\n\n"
    "_Escribí *0* para cancelar_"
)

# Confirmación pre-booking
CLIENT_CONFIRM_BOOKING = (
    "{patient_line}"
    "{emoji_prof} *{prof_name}*\n"
    "📅 {day} {date}\n"
    "🕐 {start} — {end}\n\n"
    "¿Lo confirmamos?\n\n"
    "1️⃣ Sí · 0️⃣ Volver"
)

# Confirmación post-booking
CLIENT_BOOKING_SUCCESS = (
    "✅ ¡{slot_name_upper} confirmada!\n\n"
    "{patient_line}"
    "{emoji_prof} *{prof_name}* te espera el {day} {date} a las {start}.\n\n"
    "1️⃣ Ver mis {slot_name_plural}\n"
    "2️⃣ Nueva búsqueda\n"
    "0️⃣ Menú"
)

CLIENT_BOOKING_ERROR = (
    "No se pudo agendar. Intentá de nuevo o escribí *menu* para volver."
)

# Detalle de cita
CLIENT_APPOINTMENT_DETAIL = (
    "📋 *{professional_name}*\n"
    "📅 {date}\n"
    "🕐 {time}\n"
    "{meet_line}" # Salto de linea dentro del meet_line para que solo aparezca si hay link
    "📞 {professional_phone}\n"
    "{reason_display}\n"
    "{status_badge}\n\n"
    "{options}\n\n"
    "_Escribí *0* para volver_"
)

CLIENT_APPOINTMENT_OPTIONS_CONFIRMED = (
    "¿Qué querés hacer con el {appointment_name}?\n\n"
    "1️⃣ Reprogramar\n"
    "2️⃣ Cancelar\n"
    "0️⃣ Volver"
)

CLIENT_APPOINTMENT_OPTIONS_PENDING = (
    "¿Qué querés hacer con el {appointment_name}?\n\n"
    "1️⃣ Reprogramar\n"
    "2️⃣ Cancelar\n"
    "0️⃣ Volver"
)

# Cancelación
CLIENT_CANCEL_APPOINTMENT_CONFIRM = (
    "¿Cancelamos el turno con {professional_name} del {date} a las {time}?\n\n"
    "{policy_info}\n\n"
    "1️⃣ Sí, cancelar · 0️⃣ No, volver"
)

CLIENT_CANCEL_POLICY_INFO = (
    "Política de cancelación:\n"
    "_{policy}_"
)

CLIENT_CANCEL_TOO_LATE = (
    "Ya no podés cancelar — el turno es en menos de {hours_until}hs.\n\n"
    "Para cancelar escribile al profesional: {professional_phone}"
)

CLIENT_CANCEL_BLOCKED_CONFIRMED = (
    "{article_upper} {slot_name} ya fue confirmada. "
    "Para cancelarla escribile al profesional{contact}."
)

CLIENT_CANCEL_ERROR = (
    "No se pudo cancelar. Intentá de nuevo en unos minutos."
)

CLIENT_CONFIRM_CANCEL_SELECTION = (
    "🗑️ *Cancelación de turno:*\n\n"
    "👨‍⚕️ {professional_name}\n"
    "📅 {date_formatted}\n"
    "🕐 {time}\n"
    "📍 {modality}\n\n"
    "¿Confirmás la cancelación?\n\n"
    "1️⃣ Sí, cancelar\n"
    "0️⃣ No, volver"
)

REMINDER_BACK_TO_OPTIONS = (
    "Tu turno sigue en pie. 👍\n\n"
    "Respondé con:\n"
    "1️⃣ Confirmar que vas\n"
    "2️⃣ Cambiar el día\n"
    "0️⃣ Cancelar el turno"
)

CLIENT_APPOINTMENT_CANCELLED = (
    "✅ {appointment_upper} cancelada.\n\n"
    "1️⃣ Buscar nuevo turno · 0️⃣ Menú"
)

CLIENT_APPOINTMENT_ALREADY_CANCELLED = (
    "Esa {slot_name} ya estaba cancelada."
)

CLIENT_APPOINTMENT_FINISHED = (
    "Esa {slot_name} ya pasó, no se puede cancelar."
)

# Reprogramación
CLIENT_RESCHEDULE_SELECT_DATE = (
    "📅 *Tu turno actual:* {old_date} a las {old_time}\n\n"
    "¿Para qué fecha querés reprogramar?\n\n"
    "{available_dates}\n\n"
    "Podés escribir el número, el día (*el viernes*, *mañana*) o una fecha (*01/04*)\n\n"
    "_Escribí *0* para volver_"
)

CLIENT_RESCHEDULE_SELECT_TIME = (
    "🕐 *Horarios disponibles para {new_date}:*\n\n"
    "{available_slots}\n\n"
    "Respondé con el número del horario.\n\n"
    "_Escribí *0* para volver_"
)

CLIENT_RESCHEDULE_CONFIRM = (
    "📋 *Cambio de turno*\n\n"
    "❌ Turno actual: {old_date} a las {old_time}\n"
    "✅ Nuevo turno: {new_date} a las {new_time}\n"
    "👨\u200d⚕️ {professional_name}\n\n"
    "¿Confirmamos el cambio?\n\n"
    "1️⃣ Sí · 0️⃣ No"
)

CLIENT_RESCHEDULE_SUCCESS = (
    "✅ ¡Turno reprogramado!\n\n"
    "👨‍⚕️ {professional_name}\n"
    "📅 {new_date}\n"
    "🕐 {new_time}\n\n"
    "Te esperamos. ¡Hasta pronto!"
)

CLIENT_RESCHEDULE_TOO_LATE = (
    "Ya no podés reprogramar — el turno es en menos de {hours_until}hs.\n\n"
    "Para reprogramar escribile al profesional: {professional_phone}"
)

CLIENT_NO_DATES_AVAILABLE = (
    "No hay fechas disponibles en los próximos días.\n\n"
    "Probá con otra fecha o escribí *menu* para volver."
)

CLIENT_NO_SLOTS_AVAILABLE = (
    "No hay horarios disponibles para esa fecha.\n\n"
    "¿Querés probar otro día?"
)

# ==================================================
# PROFESSIONAL — menú profesional
# ==================================================

PROF_MAIN_MENU = (
    "¡Hola! ¿Qué necesitás?\n\n"
    "1️⃣ Ver mi agenda\n"
    "2️⃣ Cargar agenda desde Excel\n"
    "0️⃣ Salir"
)

# ==================================================
# CONFIRMACIÓN DE TURNO — pantalla pre y post booking
# ==================================================

CONFIRM_BOOKING_HEADER = (
    "{patient_line}"
    "{emoji_prof} *{prof_name}*\n"
    "📅 {day} {date}\n"
    "🕐 {start} — {end}\n"
    "📱 {phone}\n\n"
    "¿Lo confirmamos?\n\n"
    "1️⃣ Sí · 0️⃣ Volver"
)

BOOKING_SUCCESS = (
    "✅ ¡{slot_name_upper} confirmada!\n\n"
    "{patient_line}"
    "{emoji_prof} *{prof_name}* te espera el {day} {date} a las {start}.\n\n"
    "1️⃣ Ver mis {slot_name_plural}\n"
    "2️⃣ Nueva búsqueda\n"
    "0️⃣ Menú"
)

BOOKING_ERROR = (
    "No se pudo agendar. Intentá de nuevo o escribí *menu* para volver."
)

# ==================================================
# FLUJO DE TERCERO — recolección de datos del paciente
# ==================================================

THIRD_PARTY_INTRO = (
    "El turno es para tu {relation}.\n\n"
    "👤 *Nombre del paciente*\n\n"
    "¿Cuál es el nombre completo de tu {relation}?\n\n"
    "Ejemplo: Juan Pérez\n\n"
    "_Escribe *0* para volver · *cancelar* para salir_"
)

THIRD_PARTY_PHONE = (
    "📞 *Teléfono de {name}* (opcional)\n\n"
    "Si tenés el número de WhatsApp de tu {relation}, "
    "le enviamos un recordatorio directo.\n\n"
    "Formato: +5491112345678\n\n"
    "• Escribí el teléfono\n"
    "• O enviá *saltar* para omitir\n\n"
    "_Escribe *0* para volver · *cancelar* para salir_"
)

THIRD_PARTY_AGE = (
    "🎂 *Edad de {name}* (opcional)\n\n"
    "¿Cuántos años tiene?\n\n"
    "Ejemplo: 12\n\n"
    "• Escribí la edad\n"
    "• O enviá *saltar* para omitir\n\n"
    "_Escribe *0* para volver · *cancelar* para salir_"
)

# ==================================================
# ERRORES DE CANCELACIÓN — 3 casos distintos
# ==================================================

CANCEL_ERROR_TECHNICAL = (
    "No se pudo cancelar. Intentá de nuevo en unos minutos."
)

CANCEL_BLOCKED_TIME = (
    "Ya no podés cancelar — {article} {slot_name} es en menos de {hours}hs.\n\n"
    "{policy}\n\n"
    "Para cancelar escribile al profesional directamente{contact}."
)

CANCEL_BLOCKED_CONFIRMED = (
    "{article_upper} {slot_name} ya fue confirmada. "
    "Para cancelarla escribile al profesional{contact}."
)

CANCEL_CONFIRM_OR_KEEP = (
    "No entendí tu respuesta. 😕\n\n"
    "Respondé con:\n"
    "1️⃣ Sí, cancelar el turno\n"
    "2️⃣ No, mantener el turno"
)

# ==================================================
# ERRORES DE REPROGRAMACIÓN
# ==================================================

RESCHEDULE_ERROR_TECHNICAL = (
    "No se pudo reprogramar. Intentá de nuevo en unos minutos."
)

RESCHEDULE_BLOCKED_TIME = (
    "Ya no podés reprogramar — {article} {slot_name} es en menos de {hours}hs.\n\n"
    "Para reprogramar escribile al profesional directamente{contact}."
)

# ==================================================
# ERRORES DE NAVEGACIÓN
# ==================================================

APPOINTMENT_LOAD_ERROR = (
    "No se pudo cargar el turno. Escribí *0* para volver."
)

APPOINTMENT_FINISHED = (
    "Ese turno ya pasó, no se puede cancelar."
)

APPOINTMENT_CANT_RESCHEDULE = (
    "No se puede reprogramar un turno con estado: {status}.\n\n"
    "_Escribí *0* para volver_"
)

# ==================================================
# FECHA INVÁLIDA — inline en el flujo de filtros
# ==================================================

DATE_ALREADY_PASSED = (
    "Esa fecha ya pasó. Ingresá una fecha de hoy en adelante."
)

# ==================================================
# LÍMITES DE TURNOS — anti-abuso
# ==================================================

BOOKING_LIMIT_GLOBAL = (
    "Ya tenés {count} turnos activos.\n\n"
    "Para sacar uno nuevo, primero cancelá alguno.\n\n"
    "Escribí *mis turnos* para verlos."
)

BOOKING_LIMIT_PER_PROFESSIONAL = (
    "Ya tenés {count} turno{s} activo{s} con {prof_name}.\n\n"
    "Si necesitás otro horario, primero cancelá uno.\n\n"
    "Escribí *mis turnos* para verlos."
)

# ==================================================
# ── Waitlist / Adelantamiento de turno ──
# ==================================================

SLOT_OFFER_MESSAGE = (
    "✨ *Turno disponible antes de lo previsto*\n\n"
    "Se liberó un lugar con *{prof_name}*:\n"
    "📅 {freed_date} a las {freed_time} hs\n\n"
    "Tu turno actual es el {current_date} a las {current_time} hs.\n\n"
    "¿Querés adelantarlo?\n\n"
    "1️⃣ Sí, me quedo con este turno\n"
    "2️⃣ No, mantengo el mío\n\n"
    "_Si no respondés en {expiration_minutes} min, el turno pasa al siguiente en lista._"
)

SLOT_OFFER_ACCEPTED = (
    "✅ *Turno adelantado*\n\n"
    "👨‍⚕️ {prof_name}\n"
    "📅 {new_date} a las {new_time} hs\n\n"
    "Tu turno anterior quedó cancelado automáticamente.\n"
    "¡Te esperamos!"
)

SLOT_OFFER_REJECTED = (
    "👍 Perfecto. Mantenemos tu turno:\n\n"
    "👨‍⚕️ {prof_name}\n"
    "📅 {current_date} a las {current_time} hs\n\n"
    "¡Te esperamos!"
)

SLOT_OFFER_EXPIRED = (
    "⏰ El turno ya fue tomado por otro paciente.\n\n"
    "Tu turno sigue en pie:\n"
    "👨‍⚕️ {prof_name}\n"
    "📅 {current_date} a las {current_time} hs\n\n"
    "¡Te esperamos!"
)

SLOT_OFFER_INVALID = (
    "No entendí tu respuesta.\n\n"
    "1️⃣ Sí, adelanto el turno\n"
    "2️⃣ No, mantengo el mío\n\n"
    "_La oferta vence en {minutes_left} min._"
)

# ==================================================
# WELCOME — saludo inicial y bienvenida
# ==================================================
# Variables disponibles:
#   {name}   → nombre del usuario (solo en WELCOME_RETURNING)
#   {count}  → cantidad de citas activas (solo en WELCOME_RETURNING)
# Nota: el menú dinámico lo arma el handler usando estas constantes
#       como encabezado. El tono define la personalidad del saludo.

WELCOME_NEW_USER = (
    "👋 ¡Hola! Bienvenido/a al centro.\n\n"
    "{tagline}.\n\n"
    "¿Qué necesitás?"
)

WELCOME_RETURNING = (
    "¡Hola, {name}! 👋\n\n"
    "¿Qué necesitás hoy?"
)

# Tagline del tono — reemplaza DomainConfig.WELCOME_TAGLINE en el canal WhatsApp.
# Versión breve, directa, sin corporativismo.
WELCOME_TAGLINE = "Turnos con {professional_plural} del centro, sin llamadas"

# ==================================================
# CENTER_INFO — información del centro
# ==================================================
# Variables disponibles:
#   {business_name}     → DomainConfig.BUSINESS_NAME
#   {tagline}           → WELCOME_TAGLINE del tono activo
#   {contact_phone}     → teléfono de contacto del centro
#   {contact_email}     → email de contacto del centro
#   {hours_weekday}     → horario lunes a viernes
#   {hours_saturday}    → horario sábado
# Nota: las variables se interpolan en user_service.get_center_info()

CENTER_INFO_BODY = (
    "📋 *{business_name}*\n\n"
    "{tagline}.\n\n"
    "*¿Cómo funciona?*\n"
    "1. Elegís el {professional_lower} que necesitás\n"
    "2. Seleccionás fecha y horario\n"
    "3. Confirmás tu turno\n\n"
    "*Horarios de atención*\n"
    "📅 Lun–Vie: {hours_weekday}\n"
    "📅 Sáb: {hours_saturday}\n\n"
    "*Contacto directo*\n"
    "📞 {contact_phone}\n"
    "📧 {contact_email}\n\n"
    "¿Querés buscar turno ahora?\n\n"
    "1️⃣ Sí · 0️⃣ Volver al menú"
)