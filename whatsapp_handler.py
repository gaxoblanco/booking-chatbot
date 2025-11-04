"""
WhatsApp Webhook Handler
=========================
Flask application that receives WhatsApp messages via Twilio webhook.
Handles both text messages and media files (images/PDFs for certificates).

For testing: Bot echoes back received messages.
Production: Connect to bot.py for actual logic.
"""

import os
import requests
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from config import Config
from bot import bot
from states import session_manager, ConversationState

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
        'service': 'WhatsApp Bot Webhook',
        'endpoints': {
            'webhook': '/webhook (POST)',
            'health': '/ (GET)'
        }
    }, 200


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

    # Extract message data from Twilio request
    incoming_msg = request.values.get('Body', '').strip()
    sender = request.values.get('From', '')  # Format: whatsapp:+1234567890
    sender_clean = sender.replace('whatsapp:', '')  # Remove prefix for storage

    # Check if message contains media (images, PDFs, etc.)
    num_media = int(request.values.get('NumMedia', 0))

    # Log received message (for debugging)
    print(f"\n{'='*50}")
    print(f"📩 MESSAGE RECEIVED")
    print(f"{'='*50}")
    print(f"From: {sender}")
    print(f"Text: {incoming_msg}")
    print(f"Media files: {num_media}")
    print(f"{'='*50}\n")

    # Determine response based on message type
    if num_media > 0:
        # Handle media upload (certificate)
        reply = handle_media_upload(sender_clean, num_media)
    else:
        # Handle text message (echo for testing)
        reply = handle_text_message(sender_clean, incoming_msg)

    # Create TwiML response
    response = MessagingResponse()
    response.message(reply)

    # Log outgoing response
    # DEBUG: Print TwiML XML being sent to Twilio
    twiml_response = str(response)
    print(f" TwiML XML:")
    print(twiml_response)
    print(f" TwiML Length: {len(twiml_response)}\n")

    return twiml_response


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

    # Process message through bot
    reply = bot.process_message(sender, message)

    return reply


def handle_media_upload(sender, num_media):
    """
    Handle incoming media files (images, PDFs).
    Downloads and stores files locally.

    Args:
        sender (str): Phone number without 'whatsapp:' prefix
        num_media (int): Number of media files attached

    Returns:
        str: Confirmation message
    """

    saved_files = []

    # Process each media file
    for i in range(num_media):
        try:
            # Get media metadata from Twilio request
            media_url = request.values.get(f'MediaUrl{i}', '')
            media_type = request.values.get(f'MediaContentType{i}', '')

            print(f"📎 Processing media {i+1}/{num_media}")
            print(f"   URL: {media_url}")
            print(f"   Type: {media_type}")

            # Download media file
            file_path = download_media(sender, media_url, media_type)

            if file_path:
                saved_files.append(file_path)
                print(f"   ✅ Saved: {file_path}")
            else:
                print(f"   ❌ Failed to save")

        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            continue

    # Generate response message
    if saved_files:
        # Check if this is a professional uploading certificate
        reply = handle_certificate_upload_success(sender)
    else:
        reply = "❌ Failed to save media files. Please try again."

    return reply


def handle_certificate_upload_success(sender):
    """
    Handle successful certificate upload for professionals.
    Updates bot state to show professional menu.

    Args:
        sender (str): Phone number without 'whatsapp:' prefix

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
        # Authenticate with Twilio to download media
        auth = (Config.TWILIO_ACCOUNT_SID, Config.TWILIO_AUTH_TOKEN)
        response = requests.get(media_url, auth=auth, timeout=10)

        if response.status_code != 200:
            print(f"❌ Failed to download: HTTP {response.status_code}")
            return None

        # Create directory for this user
        user_dir = os.path.join(Config.CERTIFICATES_DIR, sender)
        os.makedirs(user_dir, exist_ok=True)

        # Determine file extension based on MIME type
        extension = get_file_extension(media_type)

        # Generate filename with timestamp to avoid collisions
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"certificate_{timestamp}.{extension}"
        file_path = os.path.join(user_dir, filename)

        # Save file
        with open(file_path, 'wb') as f:
            f.write(response.content)

        return file_path

    except Exception as e:
        print(f"❌ Exception downloading media: {str(e)}")
        return None


def get_file_extension(media_type):
    """
    Map MIME type to file extension.

    Args:
        media_type (str): MIME type from Twilio

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

    return mime_map.get(media_type, 'bin')  # 'bin' as fallback


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
    print(f"\n💡 Use ngrok to expose this server to the internet:")
    print(f"   ngrok http {Config.FLASK_PORT}\n")

    app.run(
        host='0.0.0.0',  # Listen on all interfaces (required for Docker)
        port=Config.FLASK_PORT,
        debug=Config.FLASK_DEBUG
    )
