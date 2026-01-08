"""
Messaging utilities for sending delayed messages.
Updated to use Twilio WhatsApp API.
"""

import time
import threading
from config import Config


def send_delayed_message(to_number: str, message: str, delay_seconds: int = 3,
                         callback=None, callback_args=None):
    """
    Send a WhatsApp message after a delay (non-blocking).
    Uses Twilio WhatsApp API.

    Args:
        to_number: Recipient phone number (format: whatsapp:+1234567890 or +1234567890)
        message: Message text to send
        delay_seconds: Seconds to wait before sending (default: 3)
        callback: Optional function to call after message is sent
        callback_args: Optional arguments for callback function
    """
    def _send():
        # Wait the specified time
        time.sleep(delay_seconds)

        try:
            from twilio.rest import Client

            # Twilio credentials
            account_sid = Config.TWILIO_ACCOUNT_SID
            auth_token = Config.TWILIO_AUTH_TOKEN
            twilio_number = Config.TWILIO_WHATSAPP_NUMBER

            # Asegurar que twilio_number tenga prefijo whatsapp:
            if not twilio_number.startswith('whatsapp:'):
                twilio_number = f'whatsapp:{twilio_number}'

            # Clean phone number and ensure whatsapp: prefix
            phone_number = to_number.replace('whatsapp:', '').strip()
            if phone_number and not phone_number.startswith('+'):
                phone_number = '+' + phone_number
            phone_number = f'whatsapp:{phone_number}'

            # Create Twilio client
            client = Client(account_sid, auth_token)

            # Send message via Twilio
            twilio_message = client.messages.create(
                body=message,
                from_=twilio_number,
                to=phone_number
            )

            print(f"✅ Delayed message sent (SID: {twilio_message.sid})")
            print(f"   To: {phone_number}")
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


def send_message_sync(to_number: str, message: str):
    """
    Send a WhatsApp message immediately (synchronous).
    Uses Twilio WhatsApp API.

    Args:
        to_number: Recipient phone number (format: whatsapp:+1234567890 or +1234567890)
        message: Message text to send

    Returns:
        dict: Response from Twilio API or None if failed
    """
    try:
        from twilio.rest import Client

        # Twilio credentials
        account_sid = Config.TWILIO_ACCOUNT_SID
        auth_token = Config.TWILIO_AUTH_TOKEN
        twilio_number = Config.TWILIO_WHATSAPP_NUMBER

        # Asegurar que twilio_number tenga prefijo whatsapp:
        if not twilio_number.startswith('whatsapp:'):
            twilio_number = f'whatsapp:{twilio_number}'

        # Clean phone number and ensure whatsapp: prefix
        phone_number = to_number.replace('whatsapp:', '').strip()
        if phone_number and not phone_number.startswith('+'):
            phone_number = '+' + phone_number
        phone_number = f'whatsapp:{phone_number}'

        # Create Twilio client
        client = Client(account_sid, auth_token)

        # Send message via Twilio
        twilio_message = client.messages.create(
            body=message,
            from_=twilio_number,
            to=phone_number
        )

        print(f"✅ Message sent successfully (SID: {twilio_message.sid})")

        # Return message info as dict
        return {
            'sid': twilio_message.sid,
            'status': twilio_message.status,
            'to': phone_number
        }

    except Exception as e:
        print(f"❌ Exception sending message: {e}")
        import traceback
        traceback.print_exc()
        return None
