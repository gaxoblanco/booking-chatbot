# ==========================================
# CREAR NUEVO ARCHIVO: messaging_utils.py
# ==========================================

"""
Messaging utilities for sending delayed messages.
"""

import time
import threading
from twilio.rest import Client
from config import Config


def send_delayed_message(to_number: str, message: str, delay_seconds: int = 3,
                         callback=None, callback_args=None):
    """
    Send a WhatsApp message after a delay (non-blocking).

    Args:
        to_number: Recipient phone number (format: whatsapp:+1234567890)
        message: Message text to send
        delay_seconds: Seconds to wait before sending (default: 3)
        callback: Optional function to call after message is sent
        callback_args: Optional arguments for callback function
    """
    def _send():
        # Wait the specified time
        time.sleep(delay_seconds)

        try:
            # Initialize Twilio client
            client = Client(Config.TWILIO_ACCOUNT_SID,
                            Config.TWILIO_AUTH_TOKEN)

            # Send message
            message_sent = client.messages.create(
                body=message,
                from_=f'whatsapp:{Config.TWILIO_WHATSAPP_NUMBER}',
                to=to_number
            )

            print(f"✅ Delayed message sent (SID: {message_sent.sid})")
            print(f"   To: {to_number}")
            print(f"   After: {delay_seconds}s delay")

            # Call callback if provided (for changing state)
            if callback:
                if callback_args:
                    callback(*callback_args)
                else:
                    callback()

        except Exception as e:
            print(f"❌ Error sending delayed message: {e}")
            import traceback
            traceback.print_exc()

    # Run in background thread (non-blocking)
    thread = threading.Thread(target=_send)
    thread.daemon = True
    thread.start()

    print(f"⏰ Scheduled message to {to_number} in {delay_seconds}s")
