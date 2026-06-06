"""
Tono: freelance
===============
Mensajes para el número personal de Gastón Blanco.
Uso: freelancer Fullstack Developer · ML & AI · RAG & AI Agent Systems

Diferencias clave respecto a los otros tonos:
  - "turno" → "reunión"
  - "paciente" → "cliente"
  - Sin referencias a "centro", "consultorio", ni "zona"
  - Sin prepaga, sin modalidad presencial obligatoria
  - Voz directa, técnica, sin calidez forzada
  - Tuteo natural (vos/tu)
  - Frases cortas — una idea por mensaje

Activar: TENANT_TONE=freelance en el .env del container.
"""

# ==================================================
# ERRORES Y VALIDACIONES GENÉRICAS
# ==================================================

INVALID_OPTION = (
    "No reconocí esa opción.\n\n"
    "Respondé con el número que corresponda."
)

INVALID_DATE = (
    "No entendí la fecha.\n\n"
    "Probá con un formato como *lunes*, *mañana* o *15/07*."
)

INVALID_TIME = (
    "No reconocí el horario.\n\n"
    "Usá un formato como *10:00* o *14:30*."
)

ERROR_GENERIC = (
    "Algo falló del lado técnico.\n\n"
    "Intentá de nuevo en un momento."
)

ERROR_UNKNOWN_STATE = (
    "Algo salió mal en el flujo.\n\n"
    "Escribí *menu* para empezar de nuevo."
)

UNKNOWN_QUERY = (
    "No entendí la consulta.\n\n"
    "Podés escribir *menu* para ver las opciones."
)

HELP_MESSAGE = (
    "Comandos disponibles:\n\n"
    "• *menu* — volver al inicio\n"
    "• *mis reuniones* — ver tus reuniones activas\n"
    "• *cancelar* — cancelar el flujo actual\n\n"
    "¿En qué puedo ayudarte?"
)

# ==================================================
# WELCOME — saludo inicial y bienvenida
# ==================================================
# Variables disponibles:
#   {name}   → nombre del usuario (solo en WELCOME_RETURNING)
#   {count}  → cantidad de reuniones activas (solo en WELCOME_RETURNING)
# Nota: el menú dinámico lo arma el handler usando estas constantes
#       como encabezado. El tono define la personalidad del saludo.

WELCOME_NEW_USER = (
    "👋 Hola. Soy Gastón Blanco.\n\n"
    "{tagline}.\n\n"
    "¿En qué estás trabajando?"
)

WELCOME_RETURNING = (
    "Hola, {name}. 👋\n\n"
    "¿Qué necesitás?"
)

# Tagline del tono — línea breve que define el servicio.
# Sin corporativismo, sin exageración.
WELCOME_TAGLINE = "Fullstack · ML/AI · RAG & Agentes — del diseño al deploy"

# ==================================================
# CENTER_INFO — información del servicio
# ==================================================
# Variables disponibles:
#   {business_name}     → DomainConfig.BUSINESS_NAME
#   {tagline}           → WELCOME_TAGLINE del tono activo
#   {contact_phone}     → teléfono de contacto
#   {contact_email}     → email de contacto
#   {hours_weekday}     → disponibilidad lunes a viernes
#   {hours_saturday}    → disponibilidad sábado
# Nota: las variables se interpolan en user_service.get_center_info()

CENTER_INFO_BODY = (
    "👤 *Gastón Blanco*\n"
    "Fullstack Dev · ML/AI · RAG & AI Agents\n\n"
    "{tagline}.\n\n"
    "*Servicios*\n"
    "• Apps web y mobile (React, Angular, Python)\n"
    "• Sistemas ML/AI en producción\n"
    "• RAG, agentes y pipelines de datos\n"
    "• Integraciones de API y automatizaciones\n\n"
    "*Disponibilidad*\n"
    "📅 Lun–Vie: {hours_weekday}\n\n"
    "*Contacto*\n"
    "📧 {contact_email}\n\n"
    "¿Agendamos una llamada?\n\n"
    "1️⃣ Sí · 0️⃣ Volver al menú"
)

# ==================================================
# CLIENT MAIN MENU — menú principal
# ==================================================

CLIENT_MAIN_MENU = (
    "1️⃣ Agendar reunión\n"
    "2️⃣ Ver mis reuniones\n"
    "3️⃣ Info del servicio\n"
    "0️⃣ Salir"
)

# ==================================================
# BÚSQUEDA — filtros y resultados
# ==================================================

CLIENT_ASK_FECHA = (
    "¿Qué fecha te viene bien?\n\n"
    "Podés escribir *mañana*, *el jueves* o una fecha como *20/07*.\n\n"
    "_Escribí *0* para cancelar_"
)

CLIENT_ASK_HORA = (
    "¿Tenés preferencia de horario?\n\n"
    "1️⃣ Mañana (hasta las 13hs)\n"
    "2️⃣ Tarde (desde las 13hs)\n"
    "3️⃣ Me da igual\n\n"
    "_Escribí *0* para cancelar_"
)

# ------------------------------------------------------------------
# FLUJO FREELANCE — pantalla de filtros activos
# Mensaje modificable para casos que no sea promocionar el proyecto
# ------------------------------------------------------------------
 
CLIENT_FREELANCE_FILTERS_INFO = (
    "📅 *{date_label}* · 🕐 *{time_label}*\n\n"
    "─────────────────────\n"
    "ℹ️ *Cómo funcionan los filtros*\n\n"
    "Este sistema permite configurar filtros dinámicos según el tipo de servicio: "
    "zona, modalidad, especialidad, prepaga y más.\n\n"
    "Para esta agenda los filtros activos son:\n\n"
    "{filters_preview}\n\n"
    "─────────────────────\n"
    "1️⃣ Ver horarios disponibles\n"
    "0️⃣ Cambiar fecha u horario"
)
 
# Líneas individuales del bloque {filters_preview}
# El handler las une con \n
CLIENT_FREELANCE_FILTER_LINE_ONLINE   = "✅ Modalidad: *online* (Google Meet)"
CLIENT_FREELANCE_FILTER_LINE_PRESENCIAL = "✅ Modalidad: *presencial*"
CLIENT_FREELANCE_FILTER_LINE_BOTH     = "✅ Modalidad: *online y presencial*"
CLIENT_FREELANCE_FILTER_LINE_DATE     = "✅ Fecha: *{date_label}*"
CLIENT_FREELANCE_FILTER_LINE_TIME     = "✅ Horario: *{time_label}*"

# Zona y prepaga no aplican para freelance.
# Se definen como strings vacíos para no romper el sistema
# si algún handler los usa como fallback.
CLIENT_ASK_ZONA = ""
CLIENT_ASK_PREPAGA = ""
CLIENT_ASK_SEXO = ""

CLIENT_NO_RESULTS = (
    "No hay horarios disponibles para esa fecha.\n\n"
    "Probá con otro día o escribí *menu* para volver."
)

CLIENT_MULTIFILTER_ADDED = (
    "Filtro agregado. ¿Agregás otro o buscamos ahora?"
)

CLIENT_SEARCH_QUICK_FORMAT = (
    "{emoji} *{name}*\n"
    "📅 {date} — 🕐 {first_slot} a {last_slot}\n"
)

# ==================================================
# APPOINTMENTS — reuniones y cancelaciones
# ==================================================

CLIENT_VIEW_APPOINTMENTS = (
    "📅 Tus reuniones:\n\n"
    "{appointments_list}\n\n"
    "_Enviá el número para ver detalles_\n"
    "_Escribí *0* para volver al menú_"
)

CLIENT_NO_APPOINTMENTS = (
    "No tenés {appointment_plural} programadas.\n\n"
    "1️⃣ Agendar reunión\n"
    "0️⃣ Volver al menú"
)

CLIENT_BOOKING_COLLECT_NAME = (
    "¿Cuál es tu nombre?\n\n"
    "_Escribí *0* para cancelar_"
)

# Confirmación pre-booking
CLIENT_CONFIRM_BOOKING = (
    "{patient_line}"
    "{emoji_prof} *{prof_name}*\n"
    "📅 {day} {date}\n"
    "🕐 {start} — {end}\n\n"
    "¿Confirmamos?\n\n"
    "1️⃣ Sí · 0️⃣ Volver"
)

# Confirmación post-booking
CLIENT_BOOKING_SUCCESS = (
    "✅ *Reunión confirmada.*\n\n"
    "{patient_line}"
    "{emoji_prof} {day} {date} a las {start}.\n"
    "{meet_line}"
    "1️⃣ Ver mis {slot_name_plural}\n"
    "2️⃣ Agendar otra\n"
    "0️⃣ Menú"
)

CLIENT_BOOKING_ERROR = (
    "No se pudo agendar. Intentá de nuevo o escribí *menu* para volver."
)

# Detalle de reunión
CLIENT_APPOINTMENT_DETAIL = (
    "📋 *{professional_name}*\n"
    "📅 {date}\n"
    "🕐 {time}"
    "{meet_line}" # Salto de linea dentro del meet_line para que solo aparezca si hay link
    "📞 {professional_phone}\n"
    "{reason_display}\n"
    "{status_badge}\n\n"
    "{options}\n\n"
    "_Escribí *0* para volver_"
)

CLIENT_APPOINTMENT_OPTIONS_CONFIRMED = (
    "¿Qué querés hacer?\n\n"
    "1️⃣ Reprogramar\n"
    "2️⃣ Cancelar\n"
    "0️⃣ Volver"
)

CLIENT_APPOINTMENT_OPTIONS_PENDING = (
    "¿Qué querés hacer?\n\n"
    "1️⃣ Reprogramar\n"
    "2️⃣ Cancelar\n"
    "0️⃣ Volver"
)

# Cancelación
CLIENT_CANCEL_APPOINTMENT_CONFIRM = (
    "¿Cancelamos la reunión del {date} a las {time}?\n\n"
    "{policy_info}\n\n"
    "1️⃣ Sí, cancelar · 0️⃣ No, volver"
)

CLIENT_CANCEL_POLICY_INFO = (
    "_{policy}_"
)

CLIENT_CANCEL_TOO_LATE = (
    "Ya no se puede cancelar — la reunión es en menos de {hours_until}hs.\n\n"
    "Escribime directo: {professional_phone}"
)

CLIENT_CANCEL_BLOCKED_CONFIRMED = (
    "Esa {slot_name} ya fue confirmada. "
    "Para cancelarla escribime{contact}."
)

CLIENT_CANCEL_ERROR = (
    "No se pudo cancelar. Intentá de nuevo en un momento."
)

CLIENT_CONFIRM_CANCEL_SELECTION = (
    "🗑️ *Cancelación:*\n\n"
    "📅 {date_formatted}\n"
    "🕐 {time}\n\n"
    "¿Confirmás?\n\n"
    "1️⃣ Sí, cancelar\n"
    "0️⃣ No, volver"
)

REMINDER_BACK_TO_OPTIONS = (
    "Tu reunión sigue en pie. 👍\n\n"
    "1️⃣ Confirmar\n"
    "2️⃣ Reprogramar\n"
    "0️⃣ Cancelar"
)

CLIENT_APPOINTMENT_CANCELLED = (
    "✅ Reunión cancelada.\n\n"
    "1️⃣ Agendar otra · 0️⃣ Menú"
)

CLIENT_APPOINTMENT_ALREADY_CANCELLED = (
    "Esa {slot_name} ya estaba cancelada."
)

CLIENT_APPOINTMENT_FINISHED = (
    "Esa {slot_name} ya pasó, no se puede cancelar."
)

# ==================================================
# REPROGRAMACIÓN
# ==================================================

CLIENT_RESCHEDULE_SELECT_DATE = (
    "📅 *Reunión actual:* {old_date} a las {old_time}\n\n"
    "¿Para qué fecha la movemos?\n\n"
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
    "📋 *Cambio de reunión*\n\n"
    "❌ Actual: {old_date} a las {old_time}\n"
    "✅ Nueva: {new_date} a las {new_time}\n\n"
    "¿Confirmamos?\n\n"
    "1️⃣ Sí · 0️⃣ No"
)

CLIENT_RESCHEDULE_SUCCESS = (
    "✅ *Reunión reprogramada.*\n\n"
    "📅 {new_date}\n"
    "🕐 {new_time}\n\n"
    "Nos vemos ahí."
)

CLIENT_RESCHEDULE_TOO_LATE = (
    "Ya no se puede reprogramar — la reunión es en menos de {hours_until}hs.\n\n"
    "Escribime directo: {professional_phone}"
)

CLIENT_NO_DATES_AVAILABLE = (
    "No hay fechas disponibles en los próximos días.\n\n"
    "Probá más adelante o escribí *menu* para volver."
)

CLIENT_NO_SLOTS_AVAILABLE = (
    "No hay horarios disponibles para esa fecha.\n\n"
    "¿Probamos otro día?"
)

# ==================================================
# PROFESSIONAL — menú de agenda (vista de Gastón)
# ==================================================

PROF_MAIN_MENU = (
    "¿Qué necesitás?\n\n"
    "1️⃣ Ver agenda\n"
    "2️⃣ Cargar agenda desde Excel\n"
    "0️⃣ Salir"
)

# ==================================================
# CONFIRMACIÓN DE REUNIÓN — pantalla pre y post booking
# (aliases usados por algunos handlers via messages_appointments)
# ==================================================

CONFIRM_BOOKING_HEADER = (
    "{patient_line}"
    "{emoji_prof} *{prof_name}*\n"
    "📅 {day} {date}\n"
    "🕐 {start} — {end}\n"
    "📱 {phone}\n\n"
    "¿Confirmamos?\n\n"
    "1️⃣ Sí · 0️⃣ Volver"
)

BOOKING_SUCCESS = (
    "✅ *Reunión confirmada.*\n\n"
    "{patient_line}"
    "{emoji_prof} {day} {date} a las {start}.\n\n"
    "1️⃣ Ver mis {slot_name_plural}\n"
    "2️⃣ Agendar otra\n"
    "0️⃣ Menú"
)

BOOKING_ERROR = (
    "No se pudo agendar. Intentá de nuevo o escribí *menu* para volver."
)

# ==================================================
# FLUJO DE TERCERO — datos del cliente (no aplica
# conceptualmente, pero se mantiene para no romper
# el flujo si se activa book_for_third_party)
# ==================================================

THIRD_PARTY_INTRO = (
    "La reunión es para tu {relation}.\n\n"
    "👤 *Nombre*\n\n"
    "¿Cuál es el nombre completo de tu {relation}?\n\n"
    "_Escribí *0* para volver · *cancelar* para salir_"
)

THIRD_PARTY_PHONE = (
    "📞 *Teléfono de {name}* (opcional)\n\n"
    "Si tenés el número de WhatsApp de tu {relation}, "
    "le mandamos la confirmación directo.\n\n"
    "Formato: +5491112345678\n\n"
    "• Escribí el teléfono\n"
    "• O enviá *saltar* para omitir\n\n"
    "_Escribí *0* para volver · *cancelar* para salir_"
)

THIRD_PARTY_AGE = (
    "🎂 *Edad de {name}* (opcional)\n\n"
    "¿Cuántos años tiene?\n\n"
    "• Escribí la edad\n"
    "• O enviá *saltar* para omitir\n\n"
    "_Escribí *0* para volver · *cancelar* para salir_"
)

# ==================================================
# ERRORES DE CANCELACIÓN — 3 casos
# ==================================================

CANCEL_ERROR_TECHNICAL = (
    "No se pudo cancelar. Intentá de nuevo en un momento."
)

CANCEL_BLOCKED_TIME = (
    "Ya no podés cancelar — {article} {slot_name} es en menos de {hours}hs.\n\n"
    "{policy}\n\n"
    "Para cancelar escribime directo{contact}."
)

CANCEL_BLOCKED_CONFIRMED = (
    "{article_upper} {slot_name} ya fue confirmada. "
    "Para cancelarla escribime{contact}."
)

CANCEL_CONFIRM_OR_KEEP = (
    "No entendí tu respuesta.\n\n"
    "1️⃣ Sí, cancelar\n"
    "2️⃣ No, mantener"
)

# ==================================================
# ERRORES DE REPROGRAMACIÓN
# ==================================================

RESCHEDULE_ERROR_TECHNICAL = (
    "No se pudo reprogramar. Intentá de nuevo en un momento."
)

RESCHEDULE_BLOCKED_TIME = (
    "Ya no podés reprogramar — {article} {slot_name} es en menos de {hours}hs.\n\n"
    "Para reprogramar escribime directo{contact}."
)

# ==================================================
# ERRORES DE NAVEGACIÓN
# ==================================================

APPOINTMENT_LOAD_ERROR = (
    "No se pudo cargar la reunión. Escribí *0* para volver."
)

APPOINTMENT_FINISHED = (
    "Esa reunión ya pasó, no se puede cancelar."
)

APPOINTMENT_CANT_RESCHEDULE = (
    "No se puede reprogramar una reunión con estado: {status}.\n\n"
    "_Escribí *0* para volver_"
)

# ==================================================
# FECHA INVÁLIDA
# ==================================================

DATE_ALREADY_PASSED = (
    "Esa fecha ya pasó. Ingresá una fecha de hoy en adelante."
)

# ==================================================
# LÍMITES DE REUNIONES — anti-abuso
# ==================================================

BOOKING_LIMIT_GLOBAL = (
    "Ya tenés {count} reuniones activas.\n\n"
    "Para agendar otra, primero cancelá alguna.\n\n"
    "Escribí *mis reuniones* para verlas."
)

BOOKING_LIMIT_PER_PROFESSIONAL = (
    "Ya tenés {count} reunión{s} activa{s} agendada{s}.\n\n"
    "Si necesitás otro horario, primero cancelá una.\n\n"
    "Escribí *mis reuniones* para verlas."
)

# ==================================================
# RECORDATORIOS — mensajes automáticos pre-reunión
# ==================================================
# Variables: {prof_name}, {date}, {time}, {phone}

REMINDER_MESSAGE = (
    "🔔 *Recordatorio*\n\n"
    "Tenés una reunión mañana:\n"
    "📅 {date} · 🕐 {time}\n\n"
    "1️⃣ Confirmo · 2️⃣ Reprogramar · 0️⃣ Cancelar"
)

REMINDER_CONFIRMED = (
    "✅ Confirmado. Nos vemos mañana a las {time}."
)

REMINDER_ALREADY_CONFIRMED = (
    "Ya estaba confirmada. Nos vemos mañana a las {time}."
)

# ==================================================
# WAITLIST / ADELANTAMIENTO DE REUNIÓN
# ==================================================
# Variables: ver docs/WAITLIST_INTEGRATION.md

SLOT_OFFER_MESSAGE = (
    "✨ *Horario disponible antes de lo previsto*\n\n"
    "Se liberó un lugar:\n"
    "📅 {freed_date} a las {freed_time} hs\n\n"
    "Tu reunión actual es el {current_date} a las {current_time} hs.\n\n"
    "¿La adelantamos?\n\n"
    "1️⃣ Sí, me quedo con ese horario\n"
    "2️⃣ No, mantengo el mío\n\n"
    "_Si no respondés en {expiration_minutes} min, el slot pasa al siguiente._"
)

SLOT_OFFER_ACCEPTED = (
    "✅ *Reunión adelantada.*\n\n"
    "📅 {new_date} a las {new_time} hs\n\n"
    "La anterior quedó cancelada automáticamente.\n"
    "Nos vemos ahí."
)

SLOT_OFFER_REJECTED = (
    "👍 Perfecto. Mantenemos la reunión:\n\n"
    "📅 {current_date} a las {current_time} hs\n\n"
    "Nos vemos ahí."
)

SLOT_OFFER_EXPIRED = (
    "⏰ El horario ya fue tomado.\n\n"
    "Tu reunión sigue en pie:\n"
    "📅 {current_date} a las {current_time} hs\n\n"
    "Nos vemos ahí."
)

SLOT_OFFER_INVALID = (
    "No entendí tu respuesta.\n\n"
    "1️⃣ Sí, adelanto\n"
    "2️⃣ No, mantengo\n\n"
    "_La oferta vence en {minutes_left} min._"
)

