"""
WhatsApp Webhook Handler
=========================
Flask application that receives WhatsApp messages via Meta Cloud API webhook.
Handles both text messages and media files (images/PDFs for certificates).

Updated from Twilio to Meta WhatsApp Cloud API.
"""
import os
import importlib
import requests
from flask import Flask, request, jsonify
from config import Config
from domain_config import DomainConfig, load_preset

# ==========================================
# LOAD DOMAIN PRESET BEFORE IMPORTING BOT
# ==========================================
DOMAIN_PRESET = os.getenv('DOMAIN_PRESET', 'SALUD')
print(f"🔄 Loading domain preset: {DOMAIN_PRESET}")
load_preset(DOMAIN_PRESET)
print(f"✅ Domain loaded: {DomainConfig.BUSINESS_NAME}")

# Import bot AFTER loading preset
bot_module = importlib.import_module('bot')
bot = bot_module.bot

states_module = importlib.import_module('states')
session_manager = states_module.session_manager
ConversationState = states_module.ConversationState

prof_module = importlib.import_module('professional_service')
professional_service = prof_module.professional_service

# Initialize Flask application
app = Flask(__name__)

# Ensure certificates directory exists
os.makedirs(Config.CERTIFICATES_DIR, exist_ok=True)


@app.route('/')
def home():
    """
    Health check endpoint.
    Used to verify the server is running.
    """
    return {
        'status': 'running',
        'service': 'WhatsApp Bot Webhook (Meta Cloud API)',
        'endpoints': {
            'webhook': '/webhook (GET for verification, POST for messages)',
            'health': '/ (GET)'
        }
    }, 200


@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    """
    Main webhook endpoint for Twilio WhatsApp API.

    GET: Health check / verification endpoint
    POST: Receive incoming WhatsApp messages
    """

    if request.method == 'GET':
        # Simple health check (Twilio doesn't use GET for verification)
        return verify_webhook()

    elif request.method == 'POST':
        # Receive incoming messages from Twilio
        return handle_incoming_message()


def verify_webhook():
    """
    Webhook verification endpoint.
    Twilio doesn't require verification like Meta does.
    This endpoint is kept for compatibility but returns a simple response.
    """
    print(f"\n🔐 Webhook verification request (GET)")
    print(f"   Note: Twilio doesn't use verification tokens")

    # Return simple OK response
    return jsonify({
        "status": "ok",
        "message": "Webhook endpoint is active",
        "provider": "Twilio"
    }), 200


def handle_incoming_message():
    """
    Handle incoming WhatsApp messages from Twilio.
    Extracts message data and routes to bot for processing.
    """
    try:
        # PASO 1: Debug - Ver qué está llegando
        print(f"\n{'='*50}")
        print(f"📩 WEBHOOK RECEIVED (TWILIO)")
        print(f"{'='*50}")
        print(f"Content-Type: {request.content_type}")
        print(f"Method: {request.method}")
        print(f"{'='*50}\n")

        data = None

        # OPCIÓN 1: Intentar JSON primero
        if request.is_json or 'application/json' in request.content_type:
            data = request.get_json(force=True, silent=True)
            print("📝 Parsed as JSON")
            if data:
                print(f"JSON data: {data}")

        # OPCIÓN 2: Si no hay JSON, intentar form-data
        if not data and request.form:
            data = request.form.to_dict()
            print("📝 Parsed as form-urlencoded")
            if data:
                print(f"Form data: {data}")

        # OPCIÓN 3: Intentar parsear raw data como JSON
        if not data and request.data:
            try:
                import json
                data = json.loads(request.data.decode('utf-8'))
                print("📝 Parsed raw data as JSON")
                if data:
                    print(f"Raw JSON data: {data}")
            except:
                pass

        if not data:
            print("❌ No data could be extracted")
            print(f"   Content-Type: {request.content_type}")
            print(f"   request.data: {request.data[:200]}")
            print(f"   request.form: {request.form}")
            return jsonify({"status": "error", "message": "No data received"}), 400

        print(f"\nForm data received:")
        for key, value in data.items():
            print(f"  {key}: {value}")
        print(f"{'='*50}\n")

        # Extraer campos de Twilio (funciona tanto para JSON como form-data)
        sender = data.get('From', '').replace('whatsapp:', '').strip()
        body = data.get('Body', '')
        profile_name = data.get('ProfileName', 'Unknown')
        message_sid = data.get('MessageSid', '')
        num_media = int(data.get('NumMedia', 0))

        print(f"\n{'='*50}")
        print(f"📩 MESSAGE RECEIVED")
        print(f"{'='*50}")
        print(f"From: {sender}")
        print(f"Profile: {profile_name}")
        print(f"Body: {body}")
        print(f"Message SID: {message_sid}")
        print(f"Media count: {num_media}")
        print(f"{'='*50}\n")

        # Validar que tengamos el sender
        if not sender:
            print("❌ No sender phone number in request")
            return jsonify({"status": "error", "message": "Missing sender"}), 400

        # Handle different message types
        if num_media == 0 and body:
            # Text message
            print(f"Processing text message: {body}")

            # Process message through bot
            reply = bot.process_message(sender, body)

            # Send reply via Twilio
            send_twilio_reply(sender, reply)

        elif num_media > 0:
            # Media message (image or PDF)
            print(f"Processing media message with {num_media} attachments")

            # Handle media upload
            reply = handle_twilio_media_message(sender, data, num_media)

            # Send reply via Twilio
            send_twilio_reply(sender, reply)

        else:
            print("⚠️  Empty message (no body and no media)")

        # Always return 200 OK to Twilio
        return jsonify({"status": "ok"}), 200

    except Exception as e:
        print(f"❌ Error handling webhook: {e}")
        import traceback
        traceback.print_exc()
        # Still return 200 to prevent Twilio from retrying
        return jsonify({"status": "error", "message": str(e)}), 200


def send_twilio_reply(to_number: str, message: str):
    """
    Send a reply message via Twilio API.

    Args:
        to_number: Recipient phone number (without whatsapp: prefix)
        message: Message text to send
    """
    try:
        from twilio.rest import Client

        # Twilio credentials (deberías tenerlos en Config)
        account_sid = Config.TWILIO_ACCOUNT_SID
        auth_token = Config.TWILIO_AUTH_TOKEN
        twilio_number = Config.TWILIO_WHATSAPP_NUMBER  # ej: 'whatsapp:+14155238886'

        client = Client(account_sid, auth_token)

        # Agregar prefijo whatsapp: si no lo tiene
        if not to_number.startswith('whatsapp:'):
            to_number = f'whatsapp:{to_number}'

        # Enviar mensaje
        twilio_message = client.messages.create(
            body=message,
            from_=twilio_number,
            to=to_number
        )

        print(f"✅ Reply sent via Twilio (SID: {twilio_message.sid})")

    except Exception as e:
        print(f"❌ Exception sending Twilio reply: {e}")
        import traceback
        traceback.print_exc()


def handle_twilio_media_message(sender: str, data: dict, num_media: int):
    """
    Handle incoming media files from Twilio (images, PDFs).
    Downloads and stores files locally.

    Args:
        sender: Phone number of sender
        data: Form data from Twilio webhook
        num_media: Number of media items

    Returns:
        str: Confirmation message
    """
    try:
        # Twilio envía URLs de media como MediaUrl0, MediaUrl1, etc.
        for i in range(num_media):
            media_url = data.get(f'MediaUrl{i}')
            media_content_type = data.get(f'MediaContentType{i}')

            if not media_url:
                continue

            print(f"📎 Processing media {i+1}/{num_media}:")
            print(f"   URL: {media_url}")
            print(f"   Content-Type: {media_content_type}")

            # Download media file
            file_path = download_twilio_media(
                sender, media_url, media_content_type)

            if file_path:
                print(f"   ✅ Saved: {file_path}")
            else:
                print(f"   ❌ Failed to save")

        # Check if this is a professional uploading certificate
        return handle_certificate_upload_success(sender)

    except Exception as e:
        print(f"❌ Error handling media: {e}")
        import traceback
        traceback.print_exc()
        return "❌ Error processing media file."


def download_twilio_media(sender: str, media_url: str, content_type: str):
    """
    Download media file from Twilio and save locally.

    Args:
        sender: Phone number (used for folder structure)
        media_url: Twilio media URL
        content_type: MIME type (e.g., 'image/jpeg', 'application/pdf')

    Returns:
        str: Path to saved file, or None if failed
    """
    try:
        from twilio.rest import Client

        # Twilio credentials
        account_sid = Config.TWILIO_ACCOUNT_SID
        auth_token = Config.TWILIO_AUTH_TOKEN

        # Download file with Twilio auth
        response = requests.get(
            media_url,
            auth=(account_sid, auth_token),
            timeout=30
        )

        if response.status_code != 200:
            print(f"❌ Failed to download media: HTTP {response.status_code}")
            return None

        # Create directory for this user
        user_dir = os.path.join(Config.CERTIFICATES_DIR, sender)
        os.makedirs(user_dir, exist_ok=True)

        # Determine file extension based on MIME type
        extension = get_file_extension(content_type)

        # Generate filename with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"certificate_{timestamp}.{extension}"
        file_path = os.path.join(user_dir, filename)

        # Save file
        with open(file_path, 'wb') as f:
            f.write(response.content)

        professional_service.save_certificate(sender, file_path)

        return file_path

    except Exception as e:
        print(f"❌ Exception downloading media: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def handle_media_message(sender: str, message: dict, media_type: str):
    """
    Handle incoming media files (images, PDFs).
    Downloads and stores files locally.

    Args:
        sender: Phone number of sender
        message: Message object from Meta webhook
        media_type: Type of media ('image' or 'document')

    Returns:
        str: Confirmation message
    """
    try:
        # Get media object
        media_obj = message.get(media_type, {})
        media_id = media_obj.get('id')
        mime_type = media_obj.get('mime_type')

        print(f"📎 Processing media:")
        print(f"   Media ID: {media_id}")
        print(f"   MIME type: {mime_type}")

        # Download media file
        file_path = download_media(sender, media_id, mime_type)

        if file_path:
            print(f"   ✅ Saved: {file_path}")
            # Check if this is a professional uploading certificate
            return handle_certificate_upload_success(sender)
        else:
            print(f"   ❌ Failed to save")
            return "❌ Failed to save media file. Please try again."

    except Exception as e:
        print(f"❌ Error handling media: {e}")
        import traceback
        traceback.print_exc()
        return "❌ Error processing media file."


def download_media(sender: str, media_id: str, mime_type: str):
    """
    Download media file from Meta Cloud API and save locally.

    Args:
        sender: Phone number (used for folder structure)
        media_id: Meta media ID
        mime_type: MIME type (e.g., 'image/jpeg', 'application/pdf')

    Returns:
        str: Path to saved file, or None if failed
    """
    try:
        # Step 1: Get media URL from Meta API
        url = f"{Config.META_API_BASE_URL}/{media_id}"
        headers = {
            "Authorization": f"Bearer {Config.META_WHATSAPP_TOKEN}"
        }

        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            print(f"❌ Failed to get media URL: HTTP {response.status_code}")
            return None

        media_data = response.json()
        media_url = media_data.get('url')

        if not media_url:
            print(f"❌ No URL in media response")
            return None

        # Step 2: Download the actual file
        response = requests.get(media_url, headers=headers, timeout=30)

        if response.status_code != 200:
            print(f"❌ Failed to download media: HTTP {response.status_code}")
            return None

        # Create directory for this user
        user_dir = os.path.join(Config.CERTIFICATES_DIR, sender)
        os.makedirs(user_dir, exist_ok=True)

        # Determine file extension based on MIME type
        extension = get_file_extension(mime_type)

        # Generate filename with timestamp to avoid collisions
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"certificate_{timestamp}.{extension}"
        file_path = os.path.join(user_dir, filename)

        # Save file
        with open(file_path, 'wb') as f:
            f.write(response.content)

        professional_service.save_certificate(sender, file_path)

        return file_path

    except Exception as e:
        print(f"❌ Exception downloading media: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def handle_certificate_upload_success(sender: str):
    """
    Handle successful certificate upload for professionals.
    Updates bot state to show professional menu.

    Args:
        sender: Phone number without 'whatsapp:' prefix

    Returns:
        str: Confirmation message with menu
    """
    # Get user session
    session = session_manager.get_session(sender)

    # Check if user is in certificate upload state
    if session.state == ConversationState.PROF_NEED_CERTIFICATE:
        # Transition to main menu
        return bot.handle_prof_certificate_uploaded(session)

    # Default certificate received message
    from messages import Messages
    return Messages.PROF_CERTIFICATE_RECEIVED


def get_file_extension(mime_type: str):
    """
    Map MIME type to file extension.

    Args:
        mime_type: MIME type from Meta

    Returns:
        str: File extension (without dot)
    """
    mime_map = {
        'image/jpeg': 'jpg',
        'image/jpg': 'jpg',
        'image/png': 'png',
        'image/gif': 'gif',
        'image/webp': 'webp',
        'application/pdf': 'pdf',
    }

    return mime_map.get(mime_type, 'bin')  # 'bin' as fallback


# ==========================================
# APPLICATION ENTRY POINT
# ==========================================
if __name__ == '__main__':
    """
    Run Flask development server.
    For production, use gunicorn instead.
    """
    # Print configuration on startup
    print("\n")
    Config.print_config()
    print("\n")

    # Validate configuration
    try:
        Config.validate()
        print("✅ Configuration validated successfully\n")
    except ValueError as e:
        print(f"❌ Configuration error: {e}\n")
        print("⚠️  Running anyway for testing purposes...\n")

    # Start Flask server
    print(f"🚀 Starting WhatsApp webhook server...")
    print(f"📍 Listening on: http://0.0.0.0:{Config.FLASK_PORT}")
    print(f"📍 Webhook endpoint: http://0.0.0.0:{Config.FLASK_PORT}/webhook")
    print(f"\n💡 Configure webhook in Twilio Console:")
    print(f"   URL: {Config.WEBHOOK_URL}/webhook")
    print(f"   Method: POST")
    print(f"   Note: Twilio doesn't require a verify token\n")

    app.run(
        host='0.0.0.0',  # Listen on all interfaces (required for Docker)
        port=Config.FLASK_PORT,
        debug=Config.FLASK_DEBUG
    )
