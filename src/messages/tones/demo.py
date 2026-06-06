"""
Tono: Demo
==========
Para el número de demostración del producto.
El visitante sabe que está probando Salud Conecta.
Tono aspiracional: muestra el valor del producto en cada interacción.

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

INVALID_DATE = (
    "No reconocí esa fecha. "
    "Probá con 'mañana', 'el lunes' o una fecha tipo 25/12."
)

INVALID_TIME = "No reconocí ese horario. Probá con '9:00' o 'por la tarde'."

ERROR_GENERIC = "Algo salió mal. Escribí *menu* para volver al inicio."

ERROR_UNKNOWN_STATE = "Algo salió mal. Escribí *menu* para volver al inicio."

UNKNOWN_QUERY = (
    "Por acá manejo turnos — y lo hago bastante bien.\n\n"
    "Podés buscar un profesional, ver tus turnos o conocer más sobre Salud Conecta.\n\n"
    "¿Qué querés probar?"
)

HELP_MESSAGE = (
    "Esto es lo que puedo hacer:\n\n"
    "• Buscar profesionales disponibles\n"
    "• Agendar tu turno en segundos\n"
    "• Recordarte el turno antes de la hora\n"
    "• Mostrarte tus turnos programados\n\n"
    "Escribí lo que necesitás."
)

# ==================================================
# CLIENT — menú y búsqueda
# ==================================================

CLIENT_MAIN_MENU = (
    "¿Qué querés probar?\n\n"
    "1️⃣ Buscar profesional\n"
    "2️⃣ Ver disponibles mañana\n"
    "3️⃣ Información sobre Salud Conecta\n\n"
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
    "¿En qué zona?\n\n"
    + "\n".join(
        f"• {v}" for v in DomainConfig.ZONES.values()
    )
    + "\n\n_Escribí *0* para volver_"
)

CLIENT_ASK_PREPAGA = (
    "¿Necesitás que acepte prepaga u obra social?\n\n"
    "1️⃣ Sí\n"
    "2️⃣ No importa\n\n"
    "_Escribí *0* para volver_"
)

CLIENT_ASK_SEXO = (
    "¿Preferís el género del profesional?\n\n"
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
    "Todavía no tenés {appointment_plural} agendadas.\n\n"
    "1️⃣ Buscar profesional\n"
    "0️⃣ Volver al menú"
)

CLIENT_BOOKING_COLLECT_NAME = (
    "¿Cuál es tu nombre completo?\n\n"
    "_Escribí *0* para cancelar_"
)

# Confirmación pre-booking — el demo muestra el valor del sistema
CLIENT_CONFIRM_BOOKING = (
    "{patient_line}"
    "{emoji_prof} *{prof_name}*\n"
    "📅 {day} {date} · 🕐 {start} — {end}\n\n"
    "¿Confirmamos?\n\n"
    "1️⃣ Confirmar · 0️⃣ Volver"
)

# Post-booking — refuerza el diferencial del producto
CLIENT_BOOKING_SUCCESS = (
    "✅ ¡Así de fácil!\n\n"
    "{patient_line}"
    "{emoji_prof} *{prof_name}* te espera el {day} {date} a las {start}.\n\n"
    "Eso es todo lo que necesita el paciente. Sin llamadas. Sin esperas.\n\n"
    "1️⃣ Ver el turno · 2️⃣ Buscar otro · 0️⃣ Menú"
)

CLIENT_BOOKING_ERROR = (
    "Algo falló al agendar. Probá de nuevo."
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
    "El turno está dentro del período de cancelación.\n"
    "Faltan menos de {hours_until}hs.\n\n"
    "Para cancelar, contactá al profesional: {professional_phone}"
)

CLIENT_CANCEL_BLOCKED_CONFIRMED = (
    "{article_upper} {slot_name} ya está confirmada. "
    "Para cancelarla, contactá al profesional{contact}."
)

CLIENT_CANCEL_ERROR = (
    "Algo falló al cancelar. Probá de nuevo."
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
    "¿Para qué fecha reprogramamos?\n\n"
    "{available_dates}\n\n"
    "Podés escribir el número, el día (*el viernes*, *mañana*) o una fecha (*01/04*)\n\n"
    "_Si no reprogramás, tu turno se confirma automáticamente a las {close_time} hs_\n\n"
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
    "El turno está dentro del período de reprogramación.\n"
    "Faltan menos de {hours_until}hs.\n\n"
    "Para reprogramar, contactá al profesional: {professional_phone}"
)

CLIENT_NO_DATES_AVAILABLE = (
    "No hay fechas disponibles en los próximos días.\n\n"
    "Probá con otra fecha o escribí *menu* para volver."
)

CLIENT_NO_SLOTS_AVAILABLE = (
    "No hay horarios disponibles para esa fecha. "
    "¿Probamos con otro día?"
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
    "📅 {day} {date} · 🕐 {start} — {end}\n"
    "📱 {phone}\n\n"
    "¿Confirmamos?\n\n"
    "1️⃣ Confirmar · 0️⃣ Volver"
)

BOOKING_SUCCESS = (
    "✅ ¡Así de fácil!\n\n"
    "{patient_line}"
    "{emoji_prof} *{prof_name}* te espera el {day} {date} a las {start}.\n\n"
    "Sin llamadas. Sin esperas.\n\n"
    "1️⃣ Ver el turno · 2️⃣ Buscar otro · 0️⃣ Menú"
)

BOOKING_ERROR = (
    "Algo falló al agendar. Probá de nuevo."
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
    "Algo falló al cancelar. Probá de nuevo."
)

CANCEL_BLOCKED_TIME = (
    "El turno está dentro del período de cancelación ({hours}hs).\n\n"
    "{policy}\n\n"
    "Para cancelar, contactá al profesional directamente{contact}."
)

CANCEL_BLOCKED_CONFIRMED = (
    "{article_upper} {slot_name} ya está confirmada. "
    "Para cancelarla, contactá al profesional{contact}."
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
    "Algo falló al reprogramar. Probá de nuevo."
)

RESCHEDULE_BLOCKED_TIME = (
    "El turno ya no está dentro del período de reprogramación ({hours}hs).\n\n"
    "Para reprogramar, contactá al profesional directamente{contact}."
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
# FECHA INVÁLIDA
# ==================================================

DATE_ALREADY_PASSED = (
    "Esa fecha ya fue. ¿Qué fecha te queda bien?"
)

# ==================================================
# LÍMITES DE TURNOS — anti-abuso
# ==================================================

BOOKING_LIMIT_GLOBAL = (
    "Tenés {count} turnos activos en este momento.\n\n"
    "Para agendar uno nuevo, primero cancelá alguno de los existentes.\n\n"
    "Escribí *mis turnos* para verlos."
)

BOOKING_LIMIT_PER_PROFESSIONAL = (
    "Ya tenés {count} turno{s} agendado{s} con {prof_name}.\n\n"
    "Para agendar otro, primero cancelá uno de los existentes.\n\n"
    "Escribí *mis turnos* para verlos."
)

# ==================================================
# ── Waitlist / Adelantamiento de turno ──
# ==================================================
SLOT_OFFER_MESSAGE = (
    "✨ *¡Buenas noticias! Se liberó un turno*\n\n"
    "Tenés la oportunidad de adelantar tu cita con *{prof_name}*:\n\n"
    "📅 *Nuevo slot disponible:* {freed_date} a las {freed_time} hs\n"
    "📋 *Tu turno actual:* {current_date} a las {current_time} hs\n\n"
    "¿Te gustaría tomar este turno?\n\n"
    "1️⃣ Sí, adelanto mi turno\n"
    "2️⃣ No, prefiero mantener el mío\n\n"
    "_Esta oferta expira en {expiration_minutes} minutos._"
)

SLOT_OFFER_ACCEPTED = (
    "✅ *¡Turno adelantado con éxito!*\n\n"
    "👨‍⚕️ {prof_name}\n"
    "📅 {new_date} a las {new_time} hs\n\n"
    "Tu cita anterior fue cancelada automáticamente.\n"
    "¡Hasta pronto!"
)

SLOT_OFFER_REJECTED = (
    "👍 Entendido. Tu turno sigue confirmado:\n\n"
    "👨‍⚕️ {prof_name}\n"
    "📅 {current_date} a las {current_time} hs\n\n"
    "¡Hasta pronto!"
)

SLOT_OFFER_EXPIRED = (
    "⏰ La oferta ya no está disponible — fue tomada por otro paciente.\n\n"
    "Tu cita sigue confirmada:\n"
    "👨‍⚕️ {prof_name}\n"
    "📅 {current_date} a las {current_time} hs\n\n"
    "¡Hasta pronto!"
)

SLOT_OFFER_INVALID = (
    "No reconocí tu respuesta.\n\n"
    "1️⃣ Sí, adelanto mi turno\n"
    "2️⃣ No, prefiero el mío\n\n"
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
    "👋 ¡Bienvenido/a a Viner!\n\n"
    "Explorá el flujo completo como si fueras un paciente real."
    "y reservá tu turno para contratar el servicio\n\n"
)
WELCOME_RETURNING = (
    "¡Hola, {name}! 👋\n"
    "Estás probando Viner\n\n"
    "Explorá el flujo completo como si fueras un paciente real\n"
    "y reservá tu turno para contratar el servicio\n\n"
)

# Tagline del tono — versión aspiracional para el número de demo.
# Muestra el valor del producto en cada primer contacto.
WELCOME_TAGLINE = "Turnos sin llamadas. Agenda sin papeles. Todo desde WhatsApp"


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
    "📱 *Esto es Viner*\n\n"
 
    "Gestionamos tus turnos,\n"
    "recordamos a tus pacientes\n"
    "y recuperamos los que se pierden\n\n" 
    # "sin que tengas que hacer nada.\n\n"

    "Menos ausencias. Más consultas. Sin una sola llamada.\n\n"
 
    # Prueba — qué hace el sistema
    "*Lo que acabás de ver en acción:*\n"
    "✅ Búsqueda de profesionales por zona y especialidad\n"
    "✅ Disponibilidad en tiempo real — sincronizada con Google Calendar\n"
    "✅ Reserva y confirmación al instante\n"
    "✅ Recordatorio automático 24hs antes del turno\n"
    "✅ Reprogramación y cancelación sin llamadas\n"
    "✅ Lista de espera — si se libera un turno, el paciente lo sabe primero\n\n"
 
    # CTA
    "Tu centro podría estar funcionando así mañana.\n\n"
    "Agenda un turno para contrarlo hoy mismo.\n\n"
    # "📞 {contact_phone}\n"
    "📧 {contact_email}\n\n"
    "1️⃣ Seguir probando · 0️⃣ Volver al menú"
)