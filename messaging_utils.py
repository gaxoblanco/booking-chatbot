"""
Messaging utilities for sending delayed messages.
Updated to use Meta WhatsApp Cloud API instead of Twilio.
"""

import time
import threading
import requests
from config import Config


def send_delayed_message(to_number: str, message: str, delay_seconds: int = 3,
                         callback=None, callback_args=None):
    """
    Send a WhatsApp message after a delay (non-blocking).
    Uses Meta WhatsApp Cloud API.

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
            # Clean phone number (remove 'whatsapp:' prefix if present)
            phone_number = to_number.replace('whatsapp:', '')

            # Meta API endpoint for sending messages
            url = f"{Config.META_API_BASE_URL}/{Config.META_PHONE_NUMBER_ID}/messages"

            # Headers with access token
            headers = {
                "Authorization": f"Bearer {Config.META_WHATSAPP_TOKEN}",
                "Content-Type": "application/json"
            }

            # Message payload (Meta Cloud API format)
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": phone_number,
                "type": "text",
                "text": {
                    "preview_url": False,
                    "body": message
                }
            }

            # Send message via Meta Cloud API
            response = requests.post(
                url, headers=headers, json=payload, timeout=10)

            # Check if request was successful
            if response.status_code == 200:
                response_data = response.json()
                message_id = response_data.get('messages', [{}])[
                    0].get('id', 'unknown')

                print(f"✅ Delayed message sent (Message ID: {message_id})")
                print(f"   To: {phone_number}")
                print(f"   After: {delay_seconds}s delay")

                # Call callback if provided (for changing state)
                if callback:
                    if callback_args:
                        callback(*callback_args)
                    else:
                        callback()
            else:
                print(
                    f"❌ Error sending delayed message: HTTP {response.status_code}")
                print(f"   Response: {response.text}")

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
    Uses Meta WhatsApp Cloud API.

    Args:
        to_number: Recipient phone number (format: whatsapp:+1234567890 or +1234567890)
        message: Message text to send

    Returns:
        dict: Response from Meta API or None if failed
    """
    try:
        # Clean phone number (remove 'whatsapp:' prefix if present)
        phone_number = to_number.replace('whatsapp:', '')

        # Meta API endpoint for sending messages
        url = f"{Config.META_API_BASE_URL}/{Config.META_PHONE_NUMBER_ID}/messages"

        # Headers with access token
        headers = {
            "Authorization": f"Bearer {Config.META_WHATSAPP_TOKEN}",
            "Content-Type": "application/json"
        }

        # Message payload (Meta Cloud API format)
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone_number,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": message
            }
        }

        # Send message via Meta Cloud API
        response = requests.post(url, headers=headers,
                                 json=payload, timeout=10)

        if response.status_code == 200:
            response_data = response.json()
            message_id = response_data.get('messages', [{}])[
                0].get('id', 'unknown')
            print(f"✅ Message sent successfully (Message ID: {message_id})")
            return response_data
        else:
            print(f"❌ Error sending message: HTTP {response.status_code}")
            print(f"   Response: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Exception sending message: {e}")
        import traceback
        traceback.print_exc()
        return None
