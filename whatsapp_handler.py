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
    Main webhook endpoint for Meta WhatsApp Cloud API.

    GET: Webhook verification (Meta sends this to verify the endpoint)
    POST: Receive incoming WhatsApp messages
    """

    if request.method == 'GET':
        # ==========================================
        # WEBHOOK VERIFICATION (Meta Cloud API)
        # ==========================================
        # Meta sends a verification request when you configure the webhook
        return verify_webhook()

    elif request.method == 'POST':
        # ==========================================
        # RECEIVE INCOMING MESSAGES
        # ==========================================
        return handle_incoming_message()


def verify_webhook():
    """
    Verify webhook endpoint for Meta Cloud API.
    Meta sends GET request with hub.mode, hub.verify_token, and hub.challenge.
    We must return hub.challenge if verify_token matches.
    """
    # Get verification parameters
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    print(f"\n🔐 Webhook verification request:")
    print(f"   Mode: {mode}")
    print(f"   Token: {token}")
    print(f"   Challenge: {challenge}")

    # Check if mode and token are correct
    if mode == 'subscribe' and token == Config.META_WEBHOOK_VERIFY_TOKEN:
        print("✅ Webhook verified successfully")
        # Return challenge to complete verification
        return challenge, 200
    else:
        print("❌ Webhook verification failed")
        return 'Forbidden', 403


def handle_incoming_message():
    """
    Handle incoming WhatsApp messages from Meta Cloud API.
    Extracts message data and routes to bot for processing.
    """
    try:
        # Get webhook payload
        data = request.get_json()

        print(f"\n{'='*50}")
        print(f"📩 WEBHOOK RECEIVED")
        print(f"{'='*50}")
        print(f"Payload: {data}")
        print(f"{'='*50}\n")

        # Extract entry data (Meta webhook structure)
        if not data.get('entry'):
            print("⚠️  No entry in payload, ignoring")
            return jsonify({"status": "ok"}), 200

        entry = data['entry'][0]
        changes = entry.get('changes', [])

        if not changes:
            print("⚠️  No changes in entry, ignoring")
            return jsonify({"status": "ok"}), 200

        change = changes[0]
        value = change.get('value', {})

        # Check if this is a message event
        if 'messages' not in value:
            print("⚠️  No messages in value, might be status update")
            return jsonify({"status": "ok"}), 200

        messages = value['messages']
        message = messages[0]

        # Extract message data
        message_type = message.get('type')
        sender = message.get('from')  # Phone number
        message_id = message.get('id')
        timestamp = message.get('timestamp')

        print(f"\n{'='*50}")
        print(f"📩 MESSAGE RECEIVED")
        print(f"{'='*50}")
        print(f"From: {sender}")
        print(f"Type: {message_type}")
        print(f"Message ID: {message_id}")
        print(f"Timestamp: {timestamp}")

        # Handle different message types
        if message_type == 'text':
            # Text message
            text_content = message.get('text', {}).get('body', '')
            print(f"Text: {text_content}")
            print(f"{'='*50}\n")

            # Process message through bot
            reply = bot.process_message(sender, text_content)

            # Send reply via Meta API
            send_reply(sender, reply)

        elif message_type in ['image', 'document']:
            # Media message (image or PDF)
            print(f"Media type: {message_type}")
            print(f"{'='*50}\n")

            # Handle media upload
            reply = handle_media_message(sender, message, message_type)

            # Send reply via Meta API
            send_reply(sender, reply)

        else:
            print(f"⚠️  Unsupported message type: {message_type}")

        # Always return 200 OK to Meta
        return jsonify({"status": "ok"}), 200

    except Exception as e:
        print(f"❌ Error handling webhook: {e}")
        import traceback
        traceback.print_exc()
        # Still return 200 to prevent Meta from retrying
        return jsonify({"status": "error", "message": str(e)}), 200


def send_reply(to_number: str, message: str):
    """
    Send a reply message via Meta WhatsApp Cloud API.

    Args:
        to_number: Recipient phone number
        message: Message text to send
    """
    try:
        url = f"{Config.META_API_BASE_URL}/{Config.META_PHONE_NUMBER_ID}/messages"

        headers = {
            "Authorization": f"Bearer {Config.META_WHATSAPP_TOKEN}",
            "Content-Type": "application/json"
        }

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_number,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": message
            }
        }

        response = requests.post(url, headers=headers,
                                 json=payload, timeout=10)

        if response.status_code == 200:
            response_data = response.json()
            message_id = response_data.get('messages', [{}])[
                0].get('id', 'unknown')
            print(f"✅ Reply sent (Message ID: {message_id})")
        else:
            print(f"❌ Error sending reply: HTTP {response.status_code}")
            print(f"   Response: {response.text}")

    except Exception as e:
        print(f"❌ Exception sending reply: {e}")
        import traceback
        traceback.print_exc()


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
    print(f"\n💡 Configure webhook in Meta:")
    print(f"   URL: {Config.WEBHOOK_URL}/webhook")
    print(f"   Verify Token: {Config.META_WEBHOOK_VERIFY_TOKEN}\n")

    app.run(
        host='0.0.0.0',  # Listen on all interfaces (required for Docker)
        port=Config.FLASK_PORT,
        debug=Config.FLASK_DEBUG
    )
