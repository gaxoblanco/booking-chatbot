"""
Meta Webhook Validator
======================
Ubicación: src/security/meta_validator.py

Reemplaza twilio_validator.py para la Cloud API de Meta (WhatsApp Business).

Hay dos validaciones distintas:

  1. GET /webhook  → Meta verifica que el servidor es nuestro
                     Compara hub.verify_token con META_WEBHOOK_VERIFY_TOKEN
                     Retorna hub.challenge si coincide, 403 si no

  2. POST /webhook → Meta firma cada mensaje con HMAC-SHA256
                     Header: X-Hub-Signature-256: sha256=<hex>
                     Clave:  META_APP_SECRET
                     Body:   raw bytes del JSON (NO form-encoded como Twilio)

Diferencias clave vs Twilio:
  - Twilio:  HMAC-SHA1  sobre URL + form params  → X-Twilio-Signature
  - Meta:    HMAC-SHA256 sobre raw body (bytes)  → X-Hub-Signature-256
  - Meta agrega el flujo GET de verificación inicial del webhook

Uso en whatsapp_handler.py:
    from src.security.meta_validator import (
        verify_meta_webhook_get,
        validate_meta_signature,
        validate_meta_signature_safe,
    )

    @app.route('/webhook', methods=['GET'])
    def webhook_verify():
        return verify_meta_webhook_get(request)

    @app.route('/webhook', methods=['POST'])
    def webhook():
        if os.getenv('ENVIRONMENT') == 'production':
            if not validate_meta_signature_safe(request):
                return '', 403
        # ... resto del handler
"""

import os
import hmac
import hashlib
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# 1. VERIFICACIÓN GET — Meta confirma que el servidor es nuestro
# =============================================================================

def verify_meta_webhook_get(request) -> tuple:
    """
    Maneja el GET de verificación que Meta envía al configurar el webhook.

    Meta hace este GET una sola vez cuando guardás la URL en el panel.
    Si la verificación falla, Meta no registra el webhook.

    Flujo:
        Meta GET /webhook?hub.mode=subscribe
                         &hub.verify_token=<el_que_pusiste_en_el_panel>
                         &hub.challenge=<string_aleatorio>

        Servidor → si hub.verify_token coincide con META_WEBHOOK_VERIFY_TOKEN:
                       retorna hub.challenge con status 200
                   si no coincide:
                       retorna '', 403

    Args:
        request: Flask request object (debe ser un GET con query params)

    Returns:
        Tuple (response_body, status_code) para retornar directo desde Flask
    """
    mode         = request.args.get('hub.mode', '')
    verify_token = request.args.get('hub.verify_token', '')
    challenge    = request.args.get('hub.challenge', '')

    expected_token = os.getenv('META_WEBHOOK_VERIFY_TOKEN', '').strip()

    # Validar que viene del panel de Meta y que el token coincide
    if mode != 'subscribe':
        logger.warning(
            f"[META] ⚠️ GET /webhook con hub.mode inesperado: '{mode}'"
        )
        return 'Bad Request', 400

    if not expected_token:
        logger.error(
            "[META] ❌ META_WEBHOOK_VERIFY_TOKEN no configurado en .env"
        )
        return 'Server misconfigured', 500

    if verify_token != expected_token:
        logger.warning(
            f"[META] 🚨 Token de verificación inválido: '{verify_token}' "
            f"(esperado: '{expected_token[:4]}...')"
        )
        return 'Forbidden', 403

    logger.info("[META] ✅ Webhook verificado por Meta — retornando challenge")
    return challenge, 200


# =============================================================================
# 2. VALIDACIÓN POST — firma HMAC-SHA256 de cada mensaje entrante
# =============================================================================

def validate_meta_signature(request) -> bool:
    """
    Verifica la firma HMAC-SHA256 de Meta en cada POST entrante.

    Meta firma cada request con:
        HMAC-SHA256(APP_SECRET, raw_body_bytes)
    y lo envía en el header:
        X-Hub-Signature-256: sha256=<hex_digest>

    IMPORTANTE: la firma se calcula sobre el body RAW (bytes),
    no sobre los parámetros del form como hacía Twilio.
    Flask/Werkzeug consume el body al parsear JSON, por eso
    hay que leer request.get_data() ANTES de cualquier request.json.

    Args:
        request: Flask request object con headers y body raw

    Returns:
        True  si la firma es válida (el request viene de Meta)
        False si la firma es inválida, falta el header, o falta el secret
    """
    try:
        app_secret = os.getenv('META_APP_SECRET', '').strip()
        if not app_secret:
            logger.error(
                "[META] ❌ META_APP_SECRET no configurado — "
                "no se puede validar firma"
            )
            # Sin secret en producción es error de configuración → rechazar
            return False

        # Leer el header de firma
        signature_header = request.headers.get('X-Hub-Signature-256', '')
        if not signature_header:
            logger.warning(
                f"[META] ⚠️ Request sin X-Hub-Signature-256 "
                f"desde {request.remote_addr}"
            )
            return False

        # El header tiene formato "sha256=<hex>" — extraer solo el hex
        if not signature_header.startswith('sha256='):
            logger.warning(
                f"[META] ⚠️ Formato de firma inesperado: '{signature_header}'"
            )
            return False

        received_signature = signature_header[len('sha256='):]

        # Calcular la firma esperada sobre el body raw
        raw_body = request.get_data()  # bytes, no decodificado
        expected_signature = hmac.new(
            key       = app_secret.encode('utf-8'),
            msg       = raw_body,
            digestmod = hashlib.sha256,
        ).hexdigest()

        # Comparación segura contra timing attacks
        is_valid = hmac.compare_digest(received_signature, expected_signature)

        if not is_valid:
            logger.warning(
                f"[META] 🚨 Firma INVÁLIDA desde {request.remote_addr} "
                f"— recibida: {received_signature[:16]}... "
                f"— esperada: {expected_signature[:16]}..."
            )

        return is_valid

    except Exception as e:
        logger.error(f"[META] ❌ Error validando firma: {e}")
        return False


# =============================================================================
# 3. WRAPPER — respeta ENVIRONMENT igual que el validador de Twilio
# =============================================================================

def validate_meta_signature_safe(request) -> bool:
    """
    Versión que respeta la variable ENVIRONMENT.

    En development: no valida (Meta no puede firmar requests locales)
                    loggea si el header está presente o no
    En production:  valida y retorna el resultado real

    Reemplaza validate_twilio_signature_safe() de twilio_validator.py.

    Args:
        request: Flask request object

    Returns:
        True  en development siempre
        True/False en production según la validación real
    """
    environment = os.getenv('ENVIRONMENT', 'development').lower()

    if environment != 'production':
        has_sig = bool(request.headers.get('X-Hub-Signature-256'))
        logger.debug(
            f"[META] DEV mode — firma presente: {has_sig} "
            f"(validación omitida)"
        )
        return True

    return validate_meta_signature(request)
