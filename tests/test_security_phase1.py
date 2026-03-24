#!/usr/bin/env python3
"""
Test: Seguridad Fase 1 — S1 + S2 + S3
=======================================

S1 — Validación de firma Twilio en /webhook
S2 — Rate limiting en /google-calendar/webhook
S3 — Límite de tamaño + validación de dominio en descarga

No requiere Twilio ni Google reales — todo mockeado.

Uso:
    docker exec -it whatsapp-demo python tests/test_security_phase1.py
"""

import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))


# ── Colores ──────────────────────────────────────────────────────────────────
class C:
    GREEN = '\033[92m'; RED = '\033[91m'; CYAN = '\033[96m'
    YELLOW = '\033[93m'; BOLD = '\033[1m'; END = '\033[0m'

def ok(t):   print(f"  {C.GREEN}✅ {t}{C.END}")
def fail(t): print(f"  {C.RED}❌ {t}{C.END}")
def info(t): print(f"  ℹ️  {t}")
def sep():   print("=" * 60)


# =============================================================================
# S1 — Validación firma Twilio
# =============================================================================

def test_s1_firma_valida_retorna_true():
    """Firma válida → validate_twilio_signature retorna True."""
    from src.security.twilio_validator import validate_twilio_signature

    mock_request = MagicMock()
    mock_request.headers = {'X-Twilio-Signature': 'firma_valida'}
    mock_request.form    = {'Body': 'hola', 'From': 'whatsapp:+5491112345678'}
    mock_request.remote_addr = '127.0.0.1'

    with patch.dict(os.environ, {
        'TWILIO_AUTH_TOKEN': 'test_token',
        'WEBHOOK_URL':       'https://psivale.com.ar',
    }):
        with patch(
            'twilio.request_validator.RequestValidator.validate',
            return_value=True
        ):
            result = validate_twilio_signature(mock_request)

    assert result is True
    ok("Firma válida → retorna True")


def test_s1_firma_invalida_retorna_false():
    """Firma inválida → validate_twilio_signature retorna False."""
    from src.security.twilio_validator import validate_twilio_signature

    mock_request = MagicMock()
    mock_request.headers = {'X-Twilio-Signature': 'firma_maliciosa'}
    mock_request.form    = {'Body': 'hola'}
    mock_request.remote_addr = '1.2.3.4'

    with patch.dict(os.environ, {
        'TWILIO_AUTH_TOKEN': 'test_token',
        'WEBHOOK_URL':       'https://psivale.com.ar',
    }):
        with patch(
            'twilio.request_validator.RequestValidator.validate',
            return_value=False
        ):
            result = validate_twilio_signature(mock_request)

    assert result is False
    ok("Firma inválida → retorna False")


def test_s1_sin_header_firma_retorna_false():
    """Sin header X-Twilio-Signature → retorna False."""
    from src.security.twilio_validator import validate_twilio_signature

    mock_request = MagicMock()
    mock_request.headers = {}  # sin firma
    mock_request.form    = {}
    mock_request.remote_addr = '1.2.3.4'

    with patch.dict(os.environ, {
        'TWILIO_AUTH_TOKEN': 'test_token',
        'WEBHOOK_URL':       'https://psivale.com.ar',
    }):
        result = validate_twilio_signature(mock_request)

    assert result is False
    ok("Sin header X-Twilio-Signature → retorna False")


def test_s1_sin_auth_token_retorna_false():
    """Sin TWILIO_AUTH_TOKEN configurado → retorna False."""
    from src.security.twilio_validator import validate_twilio_signature

    mock_request = MagicMock()
    mock_request.headers = {'X-Twilio-Signature': 'algo'}
    mock_request.form    = {}
    mock_request.remote_addr = '1.2.3.4'

    with patch.dict(os.environ, {}, clear=True):
        # Sin TWILIO_AUTH_TOKEN en el entorno
        os.environ.pop('TWILIO_AUTH_TOKEN', None)
        result = validate_twilio_signature(mock_request)

    assert result is False
    ok("Sin TWILIO_AUTH_TOKEN → retorna False")


def test_s1_modo_desarrollo_siempre_true():
    """En development, validate_twilio_signature_safe siempre retorna True."""
    from src.security.twilio_validator import validate_twilio_signature_safe

    mock_request = MagicMock()
    mock_request.headers = {}  # sin firma
    mock_request.form    = {}

    with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
        result = validate_twilio_signature_safe(mock_request)

    assert result is True
    ok("ENVIRONMENT=development → validate_safe retorna True sin validar firma")


def test_s1_modo_produccion_valida_firma():
    """En production, validate_twilio_signature_safe sí valida la firma."""
    from src.security.twilio_validator import validate_twilio_signature_safe

    mock_request = MagicMock()
    mock_request.headers = {'X-Twilio-Signature': 'firma_invalida'}
    mock_request.form    = {}
    mock_request.remote_addr = '1.2.3.4'

    with patch.dict(os.environ, {
        'ENVIRONMENT':       'production',
        'TWILIO_AUTH_TOKEN': 'test_token',
        'WEBHOOK_URL':       'https://psivale.com.ar',
    }):
        with patch(
            'twilio.request_validator.RequestValidator.validate',
            return_value=False
        ):
            result = validate_twilio_signature_safe(mock_request)

    assert result is False
    ok("ENVIRONMENT=production → validate_safe valida firma real")


# =============================================================================
# S2 — Rate limiting Calendar webhook
# =============================================================================

def test_s2_rate_limiter_instancia_valida():
    """_CalendarRateLimiter debe instanciarse correctamente."""
    from src.api.whatsapp_handler import _calendar_rate_limiter

    assert hasattr(_calendar_rate_limiter, 'is_blocked')
    assert hasattr(_calendar_rate_limiter, 'record')
    ok("_calendar_rate_limiter instanciado correctamente en whatsapp_handler")


def test_s2_30_requests_pasan():
    """30 requests en 60s deben pasar."""
    from src.api.whatsapp_handler import _CalendarRateLimiter

    limiter = _CalendarRateLimiter()
    ip = "34.102.0.1"  # IP de Google

    for i in range(30):
        assert not limiter.is_blocked(ip), f"No debería estar bloqueado en intento {i+1}"
        limiter.record(ip)

    ok("30 requests de la misma IP pasan sin bloqueo")


def test_s2_request_31_activa_bloqueo():
    """El request 31 en la misma ventana activa el bloqueo."""
    from src.api.whatsapp_handler import _CalendarRateLimiter

    limiter = _CalendarRateLimiter()
    ip = "1.2.3.4"  # IP sospechosa

    for i in range(30):
        if not limiter.is_blocked(ip):
            limiter.record(ip)

    # El 31vo — debería quedar bloqueado
    limiter.record(ip)
    assert limiter.is_blocked(ip)
    ok("Request 31 activa bloqueo de 5 minutos")


def test_s2_ips_distintas_son_independientes():
    """IPs distintas tienen contadores independientes."""
    from src.api.whatsapp_handler import _CalendarRateLimiter

    limiter = _CalendarRateLimiter()
    ip_a = "1.1.1.1"
    ip_b = "2.2.2.2"

    # Bloquear ip_a superando el límite
    for _ in range(35):
        limiter.record(ip_a)

    # ip_b no debería estar bloqueada
    assert not limiter.is_blocked(ip_b)
    ok("IPs distintas tienen contadores independientes")


# =============================================================================
# S3 — Descarga segura
# =============================================================================

def test_s3_url_dominio_invalido_retorna_none():
    """URL de dominio distinto a api.twilio.com → retorna None."""
    from src.services.calendar_import_service import CalendarImportService

    svc = CalendarImportService()
    result = svc._download("https://evil.com/malware.csv")

    assert result is None
    ok("URL de dominio inválido → retorna None sin descargar")


def test_s3_url_http_sin_https_retorna_none():
    """URL con http:// en lugar de https:// → retorna None."""
    from src.services.calendar_import_service import CalendarImportService

    svc = CalendarImportService()
    result = svc._download("http://api.twilio.com/archivo.csv")

    assert result is None
    ok("URL sin HTTPS → retorna None")


def test_s3_url_valida_descarga_contenido():
    """URL válida de Twilio → descarga el contenido."""
    from src.services.calendar_import_service import CalendarImportService

    svc = CalendarImportService()
    contenido_mock = b"phone,name,weekday\n+5491111,Juan,lunes\n"

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers     = {'Content-Length': str(len(contenido_mock))}
    mock_resp.iter_content = lambda chunk_size: [contenido_mock]

    with patch('src.services.calendar_import_service.requests.get', return_value=mock_resp):
        result = svc._download(
            "https://api.twilio.com/2010-04-01/Accounts/AC123/Messages/MM456/Media/ME789"
        )

    assert result == contenido_mock
    ok("URL válida de Twilio → descarga el contenido correctamente")


def test_s3_archivo_mayor_5mb_retorna_none():
    """Archivo mayor a 5 MB (por Content-Length) → retorna None."""
    from src.services.calendar_import_service import CalendarImportService

    svc = CalendarImportService()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers     = {'Content-Length': str(6 * 1024 * 1024)}  # 6 MB
    mock_resp.iter_content = lambda chunk_size: []

    with patch('src.services.calendar_import_service.requests.get', return_value=mock_resp):
        result = svc._download(
            "https://api.twilio.com/media/archivo_grande.xlsx"
        )

    assert result is None
    ok("Content-Length > 5 MB → retorna None sin descargar")


def test_s3_archivo_mayor_5mb_en_streaming_retorna_none():
    """Archivo que supera 5 MB durante la descarga → se corta y retorna None."""
    from src.services.calendar_import_service import CalendarImportService

    svc = CalendarImportService()

    # Chunk de 6 MB — supera el límite durante la descarga
    chunk_grande = b'x' * (6 * 1024 * 1024)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers     = {}  # sin Content-Length — el servidor no lo informa
    mock_resp.iter_content = lambda chunk_size: [chunk_grande]

    with patch('src.services.calendar_import_service.requests.get', return_value=mock_resp):
        result = svc._download(
            "https://api.twilio.com/media/archivo_trampa.xlsx"
        )

    assert result is None
    ok("Archivo supera 5 MB en streaming → descarga cortada, retorna None")


def test_s3_http_error_retorna_none():
    """Error HTTP (no 200) → retorna None."""
    from src.services.calendar_import_service import CalendarImportService

    svc = CalendarImportService()

    mock_resp = MagicMock()
    mock_resp.status_code = 403
    mock_resp.headers     = {}

    with patch('src.services.calendar_import_service.requests.get', return_value=mock_resp):
        result = svc._download(
            "https://api.twilio.com/media/archivo.csv"
        )

    assert result is None
    ok("HTTP 403 → retorna None")


def test_s3_timeout_retorna_none():
    """Timeout en la descarga → retorna None."""
    from src.services.calendar_import_service import CalendarImportService
    import requests as req_lib

    svc = CalendarImportService()

    with patch('src.services.calendar_import_service.requests.get', side_effect=req_lib.exceptions.Timeout):
        result = svc._download(
            "https://api.twilio.com/media/archivo.csv"
        )

    assert result is None
    ok("Timeout en descarga → retorna None")


# =============================================================================
# Runner
# =============================================================================

def run_all():
    sep()
    print(f"{C.BOLD}  TEST SEGURIDAD FASE 1 — S1 + S2 + S3{C.END}")
    sep()

    tests = [
        # S1
        test_s1_firma_valida_retorna_true,
        test_s1_firma_invalida_retorna_false,
        test_s1_sin_header_firma_retorna_false,
        test_s1_sin_auth_token_retorna_false,
        test_s1_modo_desarrollo_siempre_true,
        test_s1_modo_produccion_valida_firma,
        # S2
        test_s2_rate_limiter_instancia_valida,
        test_s2_30_requests_pasan,
        test_s2_request_31_activa_bloqueo,
        test_s2_ips_distintas_son_independientes,
        # S3
        test_s3_url_dominio_invalido_retorna_none,
        test_s3_url_http_sin_https_retorna_none,
        test_s3_url_valida_descarga_contenido,
        test_s3_archivo_mayor_5mb_retorna_none,
        test_s3_archivo_mayor_5mb_en_streaming_retorna_none,
        test_s3_http_error_retorna_none,
        test_s3_timeout_retorna_none,
    ]

    bloques = {
        'S1 — Firma Twilio':         tests[:6],
        'S2 — Rate limit Calendar':  tests[6:10],
        'S3 — Descarga segura':      tests[10:],
    }

    passed = failed = 0
    for bloque, subtests in bloques.items():
        print(f"\n{C.CYAN}── {bloque} ──{C.END}")
        for t in subtests:
            print(f"\n  {C.CYAN}► {t.__name__}{C.END}")
            try:
                t()
                passed += 1
            except AssertionError as e:
                fail(str(e)); failed += 1
            except Exception as e:
                fail(f"Error inesperado: {e}")
                import traceback; traceback.print_exc()
                failed += 1

    sep()
    if failed == 0:
        print(f"{C.GREEN}{C.BOLD}  ✅ TODOS LOS TESTS PASARON ({passed}/{len(tests)}){C.END}")
    else:
        print(f"{C.RED}{C.BOLD}  ❌ {failed} FALLARON ({passed}/{len(tests)} pasaron){C.END}")
    sep()
    return failed == 0


if __name__ == "__main__":
    sys.exit(0 if run_all() else 1)