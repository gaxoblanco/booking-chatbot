"""
WhatsApp Webhook Handler
=========================
Flask application que recibe mensajes de WhatsApp via Meta Cloud API (sin Twilio).

Cambios respecto a la versión Twilio:
  - GET  /webhook → verificación inicial del webhook por Meta (hub.challenge)
  - POST /webhook → body JSON (no form-encoded), firma X-Hub-Signature-256
  - Respuesta al POST → HTTP 200 vacío (no TwiML)
                        el bot responde de forma proactiva via message_sender.py

Endpoints:
  GET  /webhook                  → verificación Meta (una sola vez al configurar)
  POST /webhook                  → mensajes entrantes de usuarios
  POST /google-calendar/webhook  → push notifications de Google Calendar
  GET  /                         → health check
"""
import os
import importlib
import threading
import requests
from flask import Flask, request, jsonify
from src.config.config import Config
from src.config.domain_config import DomainConfig, load_preset
from src.core.rate_limiter import rate_limiter, RateLimiter
from src.core.logger import _sanitize

# ── Validador Meta (reemplaza twilio_validator) ───────────────────────────────
from src.security.meta_validator import (
    verify_meta_webhook_get,
    validate_meta_signature_safe,
)

# S2 — Rate limiter específico para /google-calendar/webhook
# Más permisivo que el de WhatsApp — Google puede enviar ráfagas legítimas
# Usa una subclase para tener límites propios sin tocar RateLimiter
class _CalendarRateLimiter(RateLimiter):
    """Rate limiter con parámetros fijos para el webhook de Google Calendar."""
    MAX_MESSAGES   = 1000   # máx 30 notificaciones por minuto
    WINDOW_SECONDS = 60
    BLOCK_MINUTES  = 5

    def record(self, phone: str) -> bool:
        import time
        with self._lock:
            now = time.time()
            self._timestamps[phone] = [
                t for t in self._timestamps.get(phone, [])
                if now - t < self.WINDOW_SECONDS
            ]
            count = len(self._timestamps[phone])
            if count >= self.MAX_MESSAGES:
                block_until = now + (self.BLOCK_MINUTES * 60)
                self._blocked[phone] = block_until
                return False
            self._timestamps[phone].append(now)
            return True

_calendar_rate_limiter = _CalendarRateLimiter()

# ==========================================
# LOAD DOMAIN PRESET BEFORE IMPORTING BOT
# ==========================================
DOMAIN_PRESET = os.getenv('DOMAIN_PRESET', 'SALUD')
print(f"🔄 Loading domain preset: {DOMAIN_PRESET}")
load_preset(DOMAIN_PRESET)
print(f"✅ Domain loaded: {DomainConfig.BUSINESS_NAME}")

# Validar configuración — fail fast antes de levantar el bot
from src.config.config_validator import validate_config
validate_config()

# Import bot AFTER loading preset
bot_module = importlib.import_module('src.bot.bot_wrapper')
bot = bot_module.bot

states_module = importlib.import_module('src.core.states')
session_manager = states_module.session_manager
ConversationState = states_module.ConversationState

prof_module = importlib.import_module('src.services.professional_service')
professional_service = prof_module.professional_service

# Initialize Flask application
app = Flask(__name__)

# Ensure certificates directory exists
os.makedirs(Config.CERTIFICATES_DIR, exist_ok=True)


# ==========================================
# WATCH MANAGER — lazy init
# Evita import circular al momento del startup.
# Se inicializa la primera vez que llega una
# notificación de Google Calendar.
# ==========================================
_watch_manager = None


def get_watch_manager():
    """Retorna la instancia global de WatchManager, creándola si no existe."""
    global _watch_manager
    if _watch_manager is None:
        from src.integrations.google_calendar_service import GoogleCalendarService
        from src.integrations.google_calendar_service.watch_manager import WatchManager
        from src.database.database import db
        calendar_service = GoogleCalendarService()
        webhook_url = os.getenv('GOOGLE_CALENDAR_WEBHOOK_URL', '')
        if not webhook_url:
            print("[WATCH] ⚠️ GOOGLE_CALENDAR_WEBHOOK_URL no configurada en .env")
        _watch_manager = WatchManager(calendar_service, db, webhook_url)
    return _watch_manager


# ==========================================
# HEALTH CHECK
# ==========================================

@app.route('/')
def home():
    """Health check endpoint."""
    return {
        'status':    'running',
        'service':   'WhatsApp Bot Webhook',
        'provider':  'Meta Cloud API',
        'endpoints': {
            'webhook_verify':  'GET  /webhook',
            'webhook_msg':     'POST /webhook',
            'google_calendar': 'POST /google-calendar/webhook',
            'health':          'GET  /',
        }
    }, 200


# ==========================================
# WHATSAPP WEBHOOK — GET (verificación Meta)
# ==========================================

@app.route('/webhook', methods=['GET'])
def webhook_verify():
    """
    Verificación inicial del webhook por Meta.

    Meta hace este GET una sola vez cuando guardás la URL en el panel:
        developers.facebook.com → App → WhatsApp → Configuración → Webhooks

    Parámetros que Meta envía:
        hub.mode         = 'subscribe'
        hub.verify_token = el token que pusiste en el panel (META_WEBHOOK_VERIFY_TOKEN)
        hub.challenge    = string aleatorio que hay que devolver

    Si el token coincide → retorna challenge con 200
    Si no coincide → 403
    """
    body, status = verify_meta_webhook_get(request)
    return body, status


# ==========================================
# WHATSAPP WEBHOOK — POST (mensajes entrantes)
# ==========================================

@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Recibe mensajes de WhatsApp enviados por usuarios via Meta Cloud API.

    Diferencias clave vs Twilio:
    - Body JSON (no form-encoded)
    - Firma: X-Hub-Signature-256 con HMAC-SHA256 (no X-Twilio-Signature)
    - Respuesta: siempre HTTP 200 vacío (no TwiML)
      El bot responde de forma proactiva via message_sender.py (Graph API)
    - Meta reintenta si no recibe 200 en menos de 20 segundos

    Tipos de mensaje manejados:
    - text     → handle_text_message()
    - image / document / video / audio → handle_media_upload_meta()
    - statuses → ignorados (confirmaciones de entrega de Meta)
    """
    # ── 1. Validar firma Meta ─────────────────────────────────────────────────
    # CRÍTICO: get_data() debe leerse ANTES de request.get_json()
    # Flask consume el body al parsear JSON → la firma se calcularía sobre bytes vacíos
    if os.getenv('ENVIRONMENT') == 'production':
        if not validate_meta_signature_safe(request):
            return '', 403

    # ── 2. Parsear JSON de Meta ───────────────────────────────────────────────
    # Estructura Meta Cloud API:
    # {
    #   "entry": [{
    #     "changes": [{
    #       "value": {
    #         "messages": [{
    #           "from": "5491112345678",   ← sin prefijo whatsapp:, sin +
    #           "type": "text",
    #           "text": { "body": "Hola" }
    #         }],
    #         "statuses": [...]            ← confirmaciones de entrega (ignorar)
    #       }
    #     }]
    #   }]
    # }
    try:
        data = request.get_json(force=True, silent=True)
    except Exception:
        data = None

    if not data:
        print("[WEBHOOK] ⚠️ Body vacío o JSON inválido")
        return '', 400

    # ── 3. Extraer mensaje del payload ────────────────────────────────────────
    try:
        entry    = data.get('entry', [{}])[0]
        change   = entry.get('changes', [{}])[0]
        value    = change.get('value', {})
        messages = value.get('messages', [])
    except (IndexError, AttributeError, KeyError):
        return '', 200

    # Sin mensajes en este evento (puede ser un status update de entrega)
    if not messages:
        return '', 200

    msg      = messages[0]
    msg_type = msg.get('type', '')       # 'text', 'image', 'document', etc.
    sender_raw = msg.get('from', '')     # '5491112345678' (sin + ni whatsapp:)

    # Normalizar a E.164: Meta manda sin '+', hay que agregarlo
    sender = f"+{sender_raw}" if sender_raw and not sender_raw.startswith('+') else sender_raw

    # ── 4. Validación de formato E.164 ────────────────────────────────────────
    from src.core.validators import validate_phone_e164
    if not validate_phone_e164(sender):
        print(f"[WEBHOOK] ⚠️ Mensaje ignorado: número inválido '{sender_raw}'")
        return '', 200  # 200 para que Meta no reintente

    # ── 5. Rate limiting ──────────────────────────────────────────────────────
    if rate_limiter.is_blocked(sender):
        return '', 200

    if not rate_limiter.record(sender):
        return '', 200

    # ── 6. Log ───────────────────────────────────────────────────────────────
    print(f"\n{'='*50}")
    print(f"📩 MESSAGE RECEIVED (Meta Cloud API)")
    print(f"{'='*50}")
    print(f"From: {_sanitize(sender)}")
    print(f"Type: {msg_type}")
    print(f"{'='*50}\n")

    # ── 7. Despachar según tipo ───────────────────────────────────────────────
    if msg_type == 'text':
        incoming_msg = msg.get('text', {}).get('body', '').strip()
        print(f"Text: {incoming_msg}")
        handle_text_message(sender, incoming_msg)

    elif msg_type in ('image', 'document', 'video', 'audio'):
        # Meta no incluye la URL directamente — hay que pedirla a la Graph API con el media_id
        media_id = msg.get(msg_type, {}).get('id', '')
        handle_media_upload_meta(sender, media_id, msg_type)

    else:
        # Tipo no soportado (location, sticker, reaction, etc.)
        print(f"[WEBHOOK] ℹ️ Tipo '{msg_type}' no manejado — ignorando")

    # Meta requiere 200 para no reintentar el envío
    return '', 200

@app.route('/oauth/callback')
def oauth_callback():
    """
    Endpoint que recibe el código de autorización OAuth2 de Google.
    Google redirige acá después de que el profesional aprueba los permisos.
    
    Flujo:
        1. Recibe code + state de Google
        2. Intercambia code por access_token + refresh_token
        3. Identifica al profesional por el state (phone guardado en sesión)
        4. Guarda los tokens en BD
        5. Retorna página de éxito
    """
    import os
    from google_auth_oauthlib.flow import Flow

    code  = request.args.get('code')
    state = request.args.get('state')
    error = request.args.get('error')

    # Usuario rechazó la autorización
    if error:
        return f"<h2>❌ Autorización rechazada</h2><p>{error}</p>", 400

    if not code:
        return "<h2>❌ Código de autorización faltante</h2>", 400

    try:
        # Reconstruir el flow con el mismo state
        flow = Flow.from_client_config(
            client_config={
                "web": {
                    "client_id":     os.getenv('GOOGLE_OAUTH_CLIENT_ID'),
                    "client_secret": os.getenv('GOOGLE_OAUTH_CLIENT_SECRET'),
                    "redirect_uris": [os.getenv('GOOGLE_OAUTH_REDIRECT_URI')],
                    "auth_uri":      "https://accounts.google.com/o/oauth2/auth",
                    "token_uri":     "https://oauth2.googleapis.com/token",
                }
            },
            scopes=['https://www.googleapis.com/auth/calendar.events'],
            redirect_uri=os.getenv('GOOGLE_OAUTH_REDIRECT_URI'),
            state=state
        )

        # Intercambiar código por tokens
        flow.fetch_token(code=code)
        credentials = flow.credentials

        # Recuperar el teléfono del profesional desde el state
        # El state lo generamos nosotros al crear la URL — contiene el phone
        from src.integrations.google.oauth_state_store import oauth_state_store
        phone = oauth_state_store.get_phone(state)

        if not phone:
            return "<h2>❌ Estado inválido o expirado</h2><p>El link de autorización expiró. Solicitá uno nuevo.</p>", 400

        # Guardar tokens en BD
        from src.database.database import db
        from datetime import datetime
        expiry = credentials.expiry.isoformat() if credentials.expiry else None

        db.update_professional_oauth_tokens(
            phone=phone,
            refresh_token=credentials.refresh_token,
            access_token=credentials.token,
            token_expiry=expiry
        )

        oauth_state_store.delete(state)

        print(f"[OAUTH] ✅ Tokens guardados para {phone}")

        return """
            <h2>✅ Autorización completada</h2>
            <p>Tu agenda está conectada correctamente.</p>
            <p>Ya podés cerrar esta ventana.</p>
        """, 200

    except Exception as e:
        print(f"[OAUTH] ❌ Error en callback: {e}")
        return f"<h2>❌ Error procesando autorización</h2><p>{e}</p>", 500


# ==========================================
# GOOGLE CALENDAR PUSH WEBHOOK
# ==========================================

@app.route('/google-calendar/webhook', methods=['POST'])
def google_calendar_webhook():
    """
    Endpoint para recibir push notifications de Google Calendar.

    Google hace POST aquí cada vez que detecta cambios en un calendario
    que tiene un watch activo (creado por WatchManager).

    Retorna 200 OK inmediatamente — el sync real corre en hilo separado
    porque Google exige respuesta en menos de 3 segundos.

    Headers relevantes que envía Google:
        X-Goog-Channel-ID:     UUID del canal (generado por nosotros)
        X-Goog-Channel-Token:  Token secreto para validar autenticidad
        X-Goog-Resource-State: 'sync' (al crear watch) | 'exists' (hay cambios)
        X-Goog-Message-Number: Número secuencial del mensaje
    """
    # ── S2: Rate limiting ────────────────────────────────────────────────────
    client_ip = request.remote_addr or 'unknown'
    if _calendar_rate_limiter.is_blocked(client_ip):
        print(f"[SECURITY] 🚨 Rate limit Calendar webhook: {client_ip}")
        return '', 429
    _calendar_rate_limiter.record(client_ip)
    # ── Fin S2 ───────────────────────────────────────────────────────────────

    # ── 1. Extraer headers ───────────────────────────────────────────────────
    channel_id     = request.headers.get('X-Goog-Channel-ID', '')
    channel_token  = request.headers.get('X-Goog-Channel-Token', '')
    resource_state = request.headers.get('X-Goog-Resource-State', '')
    message_number = request.headers.get('X-Goog-Message-Number', '0')

    print(
        f"\n[GCAL-WEBHOOK] 📬 Notificación recibida "
        f"— channel: {channel_id[:8]}... "
        f"state: {resource_state} "
        f"msg#: {message_number}"
    )

    # ── 2. Ignorar el sync inicial ───────────────────────────────────────────
    # Google envía resource_state='sync' al crear el watch — no hay cambios reales
    if resource_state == 'sync':
        print(f"[GCAL-WEBHOOK] ℹ️  Mensaje de sync inicial — ignorado")
        return '', 200

    if resource_state != 'exists':
        print(f"[GCAL-WEBHOOK] ⚠️  resource_state desconocido: '{resource_state}' — ignorado")
        return '', 200

    # ── 3. Validar headers mínimos ───────────────────────────────────────────
    if not channel_id or not channel_token:
        print(f"[GCAL-WEBHOOK] ❌ Headers faltantes — rechazado")
        return '', 400

    # ── 4. Validar que el token coincide con lo que tenemos en BD ────────────
    # Esto previene que alguien externo dispare syncs enviando POST a este endpoint
    watch_mgr          = get_watch_manager()
    professional_phone = watch_mgr.validate_notification_token(
        channel_id=channel_id,
        token=channel_token,
    )

    if not professional_phone:
        print(
            f"[GCAL-WEBHOOK] 🚨 Token inválido para channel {channel_id[:8]}... "
            f"— rechazado"
        )
        return '', 403

    print(
        f"[GCAL-WEBHOOK] ✅ Notificación válida "
        f"— profesional: {professional_phone}"
    )

    # ── 5. Procesar en hilo separado y responder 200 inmediatamente ──────────
    thread = threading.Thread(
        target=_process_calendar_change,
        args=(professional_phone,),
        daemon=True,
        name=f"gcal-sync-{professional_phone[-4:]}"
    )
    thread.start()

    return '', 200


def _process_calendar_change(professional_phone: str):
    """
    Sincroniza las citas del profesional contra Google Calendar
    y notifica al paciente si alguna fue cancelada.

    Corre en hilo separado para no bloquear el response al webhook.

    Flujo:
        1. Obtener citas confirmadas del profesional (próximos 60 días)
        2. Sincronizar cada una contra Google Calendar
        3. Las que pasaron a 'cancelada_profesional' → notificar al paciente

    Args:
        professional_phone: Teléfono del profesional cuyo calendario cambió
    """
    from src.database.database import db
    from src.integrations.appointment_calendar_service import AppointmentCalendarService
    from src.services.cancellation_notifier import cancellation_notifier
    from datetime import datetime, timedelta

    print(
        f"[GCAL-SYNC] 🔄 Iniciando sync para {professional_phone} "
        f"(hilo: {threading.current_thread().name})"
    )

    try:
        calendar_service = AppointmentCalendarService(db)

        # Solo futuro — lo pasado no puede cancelarse
        today  = datetime.now().strftime("%Y-%m-%d")
        future = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")

        appointments = db.get_appointments_by_professional(
            professional_phone=professional_phone,
            status='confirmada',
            from_date=today,
        )

        # Solo las que tienen google_event_id y están dentro del rango
        to_sync = [
            apt for apt in appointments
            if apt.get('google_event_id')
            and apt.get('appointment_date', '') <= future
        ]

        if not to_sync:
            print(f"[GCAL-SYNC] ℹ️  Sin citas para sincronizar para {professional_phone}")
            return

        print(f"[GCAL-SYNC] 📋 Sincronizando {len(to_sync)} citas de {professional_phone}")

        cancelled_ids = []

        for apt in to_sync:
            apt_id        = apt['id']
            status_before = apt['status']

            try:
                success = calendar_service.sync_appointment_from_google(apt_id)
                if not success:
                    print(f"[GCAL-SYNC] ⚠️  Sync fallido para cita #{apt_id}")
                    continue

                apt_updated  = db.get_appointment(apt_id)
                if not apt_updated:
                    continue

                status_after = apt_updated.get('status', '')

                # Cancelada por el profesional + no notificada aún
                if (
                    status_after  == 'cancelada_profesional'
                    and status_before == 'confirmada'
                    and not apt_updated.get('cancellation_notified', False)
                ):
                    cancelled_ids.append(apt_id)
                    print(
                        f"[GCAL-SYNC] 🔴 Cita #{apt_id} cancelada por profesional "
                        f"— agendando notificación al paciente"
                    )

            except Exception as e:
                print(f"[GCAL-SYNC] ❌ Error sincronizando cita #{apt_id}: {e}")

        # Notificar al paciente por cada cita cancelada detectada
        for apt_id in cancelled_ids:
            try:
                result = cancellation_notifier.notify_patient(apt_id)
                if result.get('success'):
                    print(f"[GCAL-SYNC] ✅ Paciente notificado para cita #{apt_id}")
                else:
                    print(
                        f"[GCAL-SYNC] ⚠️  Fallo al notificar paciente "
                        f"para cita #{apt_id}: {result.get('error')}"
                    )
            except Exception as e:
                print(f"[GCAL-SYNC] ❌ Error notificando paciente para cita #{apt_id}: {e}")

        print(
            f"[GCAL-SYNC] ✅ Sync completado para {professional_phone} — "
            f"{len(to_sync)} sincronizadas, "
            f"{len(cancelled_ids)} cancelaciones detectadas"
        )

    except Exception as e:
        print(f"[GCAL-SYNC] ❌ Error crítico en sync de {professional_phone}: {e}")
        import traceback
        traceback.print_exc()


# ==========================================
# HANDLERS DE TEXTO Y MEDIA
# ==========================================

def handle_text_message(sender: str, message: str) -> None:
    """
    Procesa un mensaje de texto y envía la respuesta via message_sender.

    A diferencia de Twilio (donde se devolvía TwiML en el response HTTP),
    con Meta la respuesta se envía de forma proactiva con un POST separado
    a la Graph API, manejado por message_sender.py.

    Args:
        sender:  Número en formato E.164 (ej: +5491112345678)
        message: Texto del mensaje recibido
    """
    reply = bot.process_message(sender, message)
    if reply:
        _send_reply(sender, reply)


def _send_reply(phone: str, message: str) -> None:
    """
    Envía una respuesta al usuario via Meta Graph API.

    Delega en message_sender para manejar reintentos y logging.

    Args:
        phone:   Número en formato E.164
        message: Texto a enviar
    """
    from src.core.message_sender import message_sender
    message_sender.send_message(phone, message)


def handle_media_upload_meta(sender: str, media_id: str, media_type: str) -> None:
    """
    Procesa archivos recibidos por WhatsApp via Meta Cloud API.

    Diferencia clave vs Twilio:
    - Twilio incluía MediaUrl0 directamente en el POST del webhook
    - Meta solo incluye un media_id; la URL real hay que pedirla
      a la Graph API con ese ID y descargarla con el token Bearer

    Flujo:
        1. Resolver URL real del archivo (GET graph.facebook.com/<media_id>)
        2. Verificar identidad del remitente ANTES de descargar
        3. Descargar y parsear si es CSV/Excel
        4. Analizar y presentar menú de confirmación al profesional

    Args:
        sender:     Número en formato E.164 (ej: +5491112345678)
        media_id:   ID del archivo en los servidores de Meta
        media_type: 'image', 'document', 'video', 'audio'
    """
    from src.services.user_service import user_service
    from src.services.calendar_import_service import calendar_import_service
    from src.core.states import ConversationState, session_manager

    token       = os.getenv('META_WHATSAPP_TOKEN', '')
    api_version = os.getenv('META_API_VERSION', 'v22.0')

    try:
        # ── Paso 1: resolver la URL real del archivo ──────────────────────────
        media_info_resp = requests.get(
            f"https://graph.facebook.com/{api_version}/{media_id}",
            headers={'Authorization': f'Bearer {token}'},
            timeout=10,
        )
        media_info   = media_info_resp.json()
        media_url    = media_info.get('url', '')
        content_type = media_info.get('mime_type', '')

        print(f"[MEDIA] 📎 {content_type} — {media_url[:60]}...")

        if not media_url:
            print(f"[MEDIA] ❌ No se pudo obtener URL para media_id={media_id}")
            _send_reply(sender, "❌ No pude acceder al archivo. Intentá de nuevo.")
            return

        # ── Paso 2: verificar identidad ANTES de descargar nada ──────────────
        user_info = user_service.identify_user(sender)
        profile   = user_info.get('profile', {}) or {}

        if not calendar_import_service.is_spreadsheet(content_type):
            # No es CSV/Excel — no hay nada que procesar por ahora
            return

        if user_info.get('user_type') != 'professional':
            _send_reply(sender, "📎 Archivo recibido, pero no tenés permisos para cargar agendas.")
            return

        if not profile.get('is_active'):
            _send_reply(sender, "❌ Tu cuenta no está activa. Contactá al administrador.")
            return

        if not profile.get('calendar_id'):
            _send_reply(sender, (
                "⚠️ Tu Google Calendar no está conectado todavía.\n\n"
                "Una vez que lo configures podrás cargar tu agenda desde aquí."
            ))
            return

        # ── Paso 3: descargar y parsear — con token Bearer de Meta ───────────
        # Meta requiere Authorization header para descargar el archivo
        print(f"[MEDIA] 📋 Profesional activo {sender} envió agenda")

        rows, error = calendar_import_service.download_and_parse(
            file_url     = media_url,
            content_type = content_type,
            auth_headers = {'Authorization': f'Bearer {token}'},
        )
        if error:
            _send_reply(sender, error)
            return

        # ── Paso 4: analizar y presentar menú ────────────────────────────────
        analysis = calendar_import_service.analyze(
            rows               = rows,
            professional_phone = sender,
        )

        session = session_manager.get_session(sender)
        session.set_temp('agenda_analysis', analysis)
        session.transition_to(ConversationState.PROF_AGENDA_IMPORT_REVIEW)

        _send_reply(sender, calendar_import_service.format_review_menu(analysis))

    except Exception as e:
        print(f"[MEDIA] ❌ Error procesando media {media_id}: {e}")
        import traceback
        traceback.print_exc()

# ==========================================
# APPLICATION ENTRY POINT
# ==========================================
if __name__ == '__main__':
    """Run Flask development server. For production, use gunicorn."""

    print("\n")
    Config.print_config()
    print("\n")

    try:
        Config.validate()
        print("✅ Configuration validated successfully\n")
    except ValueError as e:
        print(f"❌ Configuration error: {e}\n")
        print("⚠️  Running anyway for testing purposes...\n")

    print(f"🚀 Starting WhatsApp webhook server (Meta Cloud API)...")
    print(f"📍 Listening on:      http://0.0.0.0:{Config.FLASK_PORT}")
    print(f"📍 Webhook verify:    GET  http://0.0.0.0:{Config.FLASK_PORT}/webhook")
    print(f"📍 Webhook msgs:      POST http://0.0.0.0:{Config.FLASK_PORT}/webhook")
    print(f"📍 Google Calendar:   POST http://0.0.0.0:{Config.FLASK_PORT}/google-calendar/webhook")
    print(f"\n💡 Configurar en Meta: developers.facebook.com → App → WhatsApp → Webhooks")
    print(f"   URL: {os.getenv('WEBHOOK_URL', 'https://gaxoblanco.com')}/webhook\n")

    # ── Scheduler ──────────────────────────────────────────────────────────
    # Corre en background thread. En development los jobs no se disparan solos
    # (solo via comando secreto del bot). En production corren según REMINDER_TIME.
    from src.integrations.scheduler.engine import scheduler_engine
    import atexit
    scheduler_engine.start()
    atexit.register(scheduler_engine.stop)
    # ───────────────────────────────────────────────────────────────────────

    app.run(
        host='0.0.0.0',
        port=Config.FLASK_PORT,
        debug=Config.FLASK_DEBUG,
        threaded=False  # Un request a la vez — evita condiciones de carrera en sesiones Redis
    )