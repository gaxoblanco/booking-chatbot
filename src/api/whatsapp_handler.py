"""
WhatsApp Webhook Handler
=========================
Flask application that receives WhatsApp messages via Twilio webhook.
Handles both text messages and media files (images/PDFs for certificates).

For testing: Bot echoes back received messages.
Production: Connect to bot.py for actual logic.
"""
import os
import importlib
import threading
import requests
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from src.config.config import Config
from src.config.domain_config import DomainConfig, load_preset
from src.core.rate_limiter import rate_limiter

# ==========================================
# LOAD DOMAIN PRESET BEFORE IMPORTING BOT
# ==========================================
DOMAIN_PRESET = os.getenv('DOMAIN_PRESET', 'SALUD')
print(f"🔄 Loading domain preset: {DOMAIN_PRESET}")
load_preset(DOMAIN_PRESET)
print(f"✅ Domain loaded: {DomainConfig.BUSINESS_NAME}")

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
        'status': 'running',
        'service': 'WhatsApp Bot Webhook',
        'endpoints': {
            'webhook': '/webhook (POST)',
            'google_calendar': '/google-calendar/webhook (POST)',
            'health': '/ (GET)'
        }
    }, 200


# ==========================================
# WHATSAPP WEBHOOK
# ==========================================

@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Main webhook endpoint for receiving WhatsApp messages.
    Twilio sends POST requests here with message data.

    Handles:
    - Text messages
    - Media files (images, PDFs)

    Returns:
    - TwiML response with bot's reply
    """
    # Extraer datos del request de Twilio
    incoming_msg = request.values.get('Body', '').strip()
    sender       = request.values.get('From', '')
    num_media    = int(request.values.get('NumMedia', 0))

    # ── Validación de formato E.164 ──────────────────────────────────────────
    from src.core.validators import normalize_whatsapp_phone
    sender_clean = normalize_whatsapp_phone(sender)

    if sender_clean is None:
        print(f"[WEBHOOK] ⚠️ Mensaje ignorado: número inválido '{sender}'")
        return '', 400
    # ── Fin validación E.164 ─────────────────────────────────────────────────

    # ── Rate limiting ────────────────────────────────────────────────────────
    if rate_limiter.is_blocked(sender_clean):
        return '', 200

    if not rate_limiter.record(sender_clean):
        return '', 200
    # ── Fin rate limiting ────────────────────────────────────────────────────

    # Log del mensaje recibido
    print(f"\n{'='*50}")
    print(f"📩 MESSAGE RECEIVED")
    print(f"{'='*50}")
    print(f"From: {sender}")
    print(f"Text: {incoming_msg}")
    print(f"Media files: {num_media}")
    print(f"{'='*50}\n")

    # Determinar tipo de respuesta
    if num_media > 0:
        reply = handle_media_upload(sender_clean, num_media)
    else:
        reply = handle_text_message(sender_clean, incoming_msg)

    # Crear respuesta TwiML
    response = MessagingResponse()
    response.message(reply)

    twiml_response = str(response)
    print(f"📤 TwiML XML:")
    print(twiml_response)
    print(f"📊 TwiML Length: {len(twiml_response)}\n")

    return twiml_response


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

def handle_text_message(sender, message):
    """
    Handle incoming text messages.
    Routes message to bot for processing.

    Args:
        sender (str): Phone number without 'whatsapp:' prefix
        message (str): Text content of the message

    Returns:
        str: Reply message to send back
    """
    reply = bot.process_message(sender, message)
    return reply


def handle_media_upload(sender, num_media):
    """
    Procesa archivos recibidos por WhatsApp.
    Si el remitente es un profesional activo con Calendar configurado
    y el archivo es CSV/Excel, analiza la agenda y presenta el menú
    de confirmación.
    """
    from src.services.user_service import user_service
    from src.services.calendar_import_service import calendar_import_service  # ← src.
    from src.core.states import ConversationState, session_manager

    for i in range(num_media):
        try:
            media_url    = request.values.get(f'MediaUrl{i}', '')
            content_type = request.values.get(f'MediaContentType{i}', '')

            print(f"[MEDIA] 📎 {content_type} — {media_url[:60]}...")

            # ── Verificar identidad ANTES de descargar nada ───────────────
            user_info = user_service.identify_user(sender)
            profile   = user_info.get('profile', {}) or {}

            if not calendar_import_service.is_spreadsheet(content_type):
                continue  # No es CSV/Excel — ignorar este archivo

            if user_info.get('user_type') != 'professional':
                return "📎 Archivo recibido, pero no tenés permisos para cargar agendas."

            if not profile.get('is_active'):
                return "❌ Tu cuenta no está activa. Contactá al administrador."

            if not profile.get('calendar_id'):
                return (
                    "⚠️ Tu Google Calendar no está conectado todavía.\n\n"
                    "Una vez que lo configures podrás cargar tu agenda desde aquí."
                )

            # ── Todas las validaciones pasaron — procesar ─────────────────
            print(f"[MEDIA] 📋 Profesional activo {sender} envió agenda")

            rows, error = calendar_import_service.download_and_parse(
                file_url     = media_url,
                content_type = content_type,
            )
            if error:
                return error

            analysis = calendar_import_service.analyze(
                rows               = rows,
                professional_phone = sender,
            )

            session = session_manager.get_session(sender)
            session.set_temp('agenda_analysis', analysis)
            session.transition_to(ConversationState.PROF_AGENDA_IMPORT_REVIEW)

            return calendar_import_service.format_review_menu(analysis)

        except Exception as e:
            print(f"[MEDIA] ❌ Error procesando media {i}: {e}")
            import traceback
            traceback.print_exc()

    return (
        "📎 Archivo recibido. Solo proceso archivos CSV y Excel "
        "para carga de agenda."
    )

def handle_certificate_upload_success(sender):
    """
    Handle successful certificate upload for professionals.

    Args:
        sender (str): Phone number without 'whatsapp:' prefix

    Returns:
        str: Confirmation message with menu
    """
    session = session_manager.get_session(sender)

    if session.state == ConversationState.PROF_NEED_ACCESS_KEY:
        return bot.handle_prof_certificate_uploaded(session)

    from src.core.messages import Messages
    return Messages.PROF_CERTIFICATE_RECEIVED


def download_media(sender, media_url, media_type):
    """
    Download media file from Twilio and save locally.

    Args:
        sender (str): Phone number (used for folder structure)
        media_url (str): Twilio URL to download media
        media_type (str): MIME type (e.g., 'image/jpeg', 'application/pdf')

    Returns:
        str: Path to saved file, or None if failed
    """
    try:
        auth     = (Config.TWILIO_ACCOUNT_SID, Config.TWILIO_AUTH_TOKEN)
        response = requests.get(media_url, auth=auth, timeout=10)

        if response.status_code != 200:
            print(f"❌ Failed to download: HTTP {response.status_code}")
            return None

        user_dir = os.path.join(Config.CERTIFICATES_DIR, sender)
        os.makedirs(user_dir, exist_ok=True)

        extension = get_file_extension(media_type)

        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename  = f"certificate_{timestamp}.{extension}"
        file_path = os.path.join(user_dir, filename)

        with open(file_path, 'wb') as f:
            f.write(response.content)

        professional_service.save_certificate(sender, file_path)

        return file_path

    except Exception as e:
        print(f"❌ Exception downloading media: {str(e)}")
        return None


def get_file_extension(media_type):
    """Map MIME type to file extension."""
    mime_map = {
        'image/jpeg':      'jpg',
        'image/jpg':       'jpg',
        'image/png':       'png',
        'image/gif':       'gif',
        'image/webp':      'webp',
        'application/pdf': 'pdf',
    }
    return mime_map.get(media_type, 'bin')


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

    print(f"🚀 Starting WhatsApp webhook server...")
    print(f"📍 Listening on: http://0.0.0.0:{Config.FLASK_PORT}")
    print(f"📍 Webhook endpoint: http://0.0.0.0:{Config.FLASK_PORT}/webhook")
    print(f"📍 Google Calendar webhook: http://0.0.0.0:{Config.FLASK_PORT}/google-calendar/webhook")
    print(f"\n💡 Use ngrok to expose this server to the internet:")
    print(f"   ngrok http {Config.FLASK_PORT}\n")

    app.run(
        host='0.0.0.0',
        port=Config.FLASK_PORT,
        debug=Config.FLASK_DEBUG
    )