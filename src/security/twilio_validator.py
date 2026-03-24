"""
Twilio Signature Validator — S1
================================
Ubicación: src/security/twilio_validator.py

Verifica que los requests al /webhook vienen realmente de Twilio
usando HMAC-SHA1 sobre la URL + parámetros del form.

Sin esta validación, cualquiera que conozca la URL del webhook puede
enviar mensajes simulando ser cualquier número de teléfono.

Uso en whatsapp_handler.py:
    from src.security.twilio_validator import validate_twilio_signature

    @app.route('/webhook', methods=['POST'])
    def webhook():
        if os.getenv('ENVIRONMENT') == 'production':
            if not validate_twilio_signature(request):
                return '', 403
        # ... resto del handler
"""

import os
import logging

logger = logging.getLogger(__name__)


def validate_twilio_signature(request) -> bool:
    """
    Verifica la firma HMAC-SHA1 de Twilio en el request entrante.

    Twilio firma cada POST con:
        HMAC-SHA1(AUTH_TOKEN, URL + sorted(params))
    y lo envía en el header X-Twilio-Signature.

    Args:
        request: Flask request object con headers y form data

    Returns:
        True  si la firma es válida (el request viene de Twilio)
        False si la firma es inválida, falta el header, o falta el token
    """
    try:
        from twilio.request_validator import RequestValidator

        auth_token = os.getenv('TWILIO_AUTH_TOKEN', '').strip()
        if not auth_token:
            logger.error(
                "[SECURITY] ❌ TWILIO_AUTH_TOKEN no configurado — "
                "no se puede validar firma"
            )
            # En producción sin token es un error de configuración
            # Rechazar el request para no operar sin seguridad
            return False

        signature = request.headers.get('X-Twilio-Signature', '')
        if not signature:
            logger.warning(
                f"[SECURITY] ⚠️ Request sin X-Twilio-Signature "
                f"desde {request.remote_addr}"
            )
            return False

        # La URL debe ser exactamente la que Twilio tiene configurada
        # incluyendo el esquema https://
        webhook_url = os.getenv('WEBHOOK_URL', '').strip().rstrip('/') + '/webhook'

        validator = RequestValidator(auth_token)
        is_valid  = validator.validate(
            uri        = webhook_url,
            params     = request.form,
            signature  = signature,
        )

        if not is_valid:
            logger.warning(
                f"[SECURITY] 🚨 Firma Twilio INVÁLIDA "
                f"desde {request.remote_addr} "
                f"— URL usada: {webhook_url}"
            )

        return is_valid

    except ImportError:
        logger.error(
            "[SECURITY] ❌ twilio no instalado — "
            "no se puede validar firma. "
            "Instalar con: pip install twilio"
        )
        return False

    except Exception as e:
        logger.error(f"[SECURITY] ❌ Error validando firma Twilio: {e}")
        return False


def validate_twilio_signature_safe(request) -> bool:
    """
    Versión que solo loggea en desarrollo, bloquea en producción.
    Útil para hacer rollout gradual.

    En development: loggea la validación pero siempre retorna True
    En production:  valida y retorna el resultado real
    """
    environment = os.getenv('ENVIRONMENT', 'development').lower()

    if environment != 'production':
        # En desarrollo no tenemos firma real — solo loggeamos
        has_sig = bool(request.headers.get('X-Twilio-Signature'))
        logger.debug(
            f"[SECURITY] DEV mode — firma presente: {has_sig} "
            f"(validación omitida)"
        )
        return True

    return validate_twilio_signature(request)
