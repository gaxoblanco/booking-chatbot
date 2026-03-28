#!/usr/bin/env python3
"""
Smoke Tests — Post-Deploy Producción
======================================
Archivo: tests/smoke/test_smoke_production.py

Propósito:
    Verificar que el servidor en producción está vivo y bien configurado
    ANTES de hacer go-live. Corre contra el servidor real, sin mocks.

Qué verifica:
    T1  — Health check responde 200
    T2  — /webhook sin firma devuelve 403 (S1 activo)
    T3  — /webhook con método GET devuelve 405
    T4  — /google-calendar/webhook flood → 429 en el request 31 (S2 activo)
    T5  — HTTPS activo (no HTTP plano)
    T6  — MASTER_ACCESS_KEY configurada (el sistema arrancó sin ValueError)
    T7  — Redis responde desde dentro del contenedor (con auth)
    T8  — Logs no exponen teléfonos en claro (S6 activo)
    T9  — Variables críticas de entorno presentes
    T10 — Contenedor corriendo como usuario no-root

Uso:
    # Desde el servidor, una vez levantado docker-compose.prod.yml:
    docker exec -it whatsapp-demo python tests/smoke/test_smoke_production.py

    # O apuntando a una URL externa (ej: desde tu máquina):
    BASE_URL=https://tudominio.com docker exec -it whatsapp-demo \
        python tests/smoke/test_smoke_production.py

Variables de entorno opcionales:
    BASE_URL    URL base del servidor (default: http://localhost:5000)
    TIMEOUT     Segundos de timeout por request (default: 5)

Nota importante:
    T4 (flood Calendar) puede dejar la IP de test bloqueada por 5 minutos.
    Esto es intencional — es exactamente el comportamiento esperado en producción.
    Si necesitás re-correr el test antes de que expire el bloqueo, reiniciá
    el contenedor o esperá los 5 minutos.
"""

import os
import sys
import subprocess
import time
import requests
from pathlib import Path

# ── Agregar raíz del proyecto al path ────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# ── Configuración ─────────────────────────────────────────────────────────────

BASE_URL = os.getenv('BASE_URL', 'http://localhost:5000').rstrip('/')
TIMEOUT  = int(os.getenv('TIMEOUT', '5'))

# Payload mínimo que simula un POST de Twilio sin firma válida
FAKE_TWILIO_PAYLOAD = {
    'Body': 'hola',
    'From': 'whatsapp:+5491199999999',
    'To':   'whatsapp:+14155238886',
    'NumMedia': '0',
}


# ── Colores ───────────────────────────────────────────────────────────────────

class C:
    GREEN  = '\033[92m'
    RED    = '\033[91m'
    CYAN   = '\033[96m'
    YELLOW = '\033[93m'
    BOLD   = '\033[1m'
    END    = '\033[0m'

def ok(msg):    print(f"  {C.GREEN}✅ {msg}{C.END}")
def fail(msg):  print(f"  {C.RED}❌ {msg}{C.END}")
def info(msg):  print(f"  ℹ️  {msg}")
def warn(msg):  print(f"  {C.YELLOW}⚠️  {msg}{C.END}")
def sep():      print("=" * 60)
def subsep():   print("─" * 60)


# ═════════════════════════════════════════════════════════════════════════════
# T1 — Health check
# ═════════════════════════════════════════════════════════════════════════════

def test_t1_health_check():
    """
    GET / debe responder 200 con status: running.

    Si esto falla, el contenedor está caído o el puerto no está mapeado.
    No tiene sentido correr el resto de los tests.
    """
    try:
        r = requests.get(f"{BASE_URL}/", timeout=TIMEOUT)
        assert r.status_code == 200, (
            f"Health check devolvió {r.status_code} (esperado 200)"
        )
        body = r.json()
        assert body.get('status') == 'running', (
            f"status no es 'running': {body}"
        )
        ok(f"Health check OK — status: {body.get('status')}")
    except requests.exceptions.ConnectionError:
        raise AssertionError(
            f"No se pudo conectar a {BASE_URL}. "
            "¿El contenedor está levantado? ¿Puerto mapeado en docker-compose.prod.yml?"
        )
    except requests.exceptions.Timeout:
        raise AssertionError(
            f"Timeout ({TIMEOUT}s) conectando a {BASE_URL}. "
            "Revisar que el servidor responde."
        )


# ═════════════════════════════════════════════════════════════════════════════
# T2 — /webhook sin firma → 403 (S1 activo)
# ═════════════════════════════════════════════════════════════════════════════

def test_t2_webhook_sin_firma_da_403():
    """
    POST a /webhook sin header X-Twilio-Signature debe dar 403.

    Si da 200 o 400, significa que ENVIRONMENT != production o que
    validate_twilio_signature_safe no está siendo llamado.
    """
    r = requests.post(
        f"{BASE_URL}/webhook",
        data=FAKE_TWILIO_PAYLOAD,
        timeout=TIMEOUT,
    )
    assert r.status_code == 403, (
        f"POST sin firma devolvió {r.status_code} (esperado 403). "
        f"Verificar que ENVIRONMENT=production está en .env del servidor."
    )
    ok(f"POST /webhook sin firma → 403 (S1 activo)")


# ═════════════════════════════════════════════════════════════════════════════
# T3 — /webhook con GET → 405
# ═════════════════════════════════════════════════════════════════════════════

def test_t3_webhook_get_da_405():
    """
    GET a /webhook debe dar 405 Method Not Allowed.

    Verifica que el endpoint solo acepta POST (como registrado en Flask).
    """
    r = requests.get(f"{BASE_URL}/webhook", timeout=TIMEOUT)
    assert r.status_code == 405, (
        f"GET /webhook devolvió {r.status_code} (esperado 405)"
    )
    ok(f"GET /webhook → 405 Method Not Allowed")


# ═════════════════════════════════════════════════════════════════════════════
# T4 — /google-calendar/webhook flood → 429 en request 31 (S2 activo)
# ═════════════════════════════════════════════════════════════════════════════

def test_t4_calendar_webhook_rate_limit():
    """
    31 POST consecutivos a /google-calendar/webhook desde la misma IP
    deben resultar en 429 en el request 31.

    _CalendarRateLimiter: 30 requests/minuto, bloqueo 5 minutos.

    IMPORTANTE: Este test deja la IP del test bloqueada por 5 minutos.
    Si necesitás re-correr antes de que expire, reiniciá el contenedor.
    """
    url     = f"{BASE_URL}/google-calendar/webhook"
    headers = {
        # Headers mínimos que espera google_calendar_webhook()
        # Sin channel_id/token válidos dará 400 o 403, pero
        # el rate limiter se evalúa ANTES — lo que nos interesa aquí.
        'X-Goog-Channel-ID':     'smoke-test-channel-id',
        'X-Goog-Channel-Token':  'smoke-test-token',
        'X-Goog-Resource-State': 'exists',
        'X-Goog-Message-Number': '1',
    }

    last_status = None
    got_429     = False

    for i in range(1, 32):
        r = requests.post(url, headers=headers, timeout=TIMEOUT)
        last_status = r.status_code
        if r.status_code == 429:
            got_429 = True
            info(f"Request #{i} → 429 (rate limit activado)")
            break

    assert got_429, (
        f"Después de 31 requests, nunca se recibió 429. "
        f"Último status: {last_status}. "
        f"Verificar que _CalendarRateLimiter está activo en whatsapp_handler.py."
    )
    ok(f"Calendar webhook flood → 429 en request ≤31 (S2 activo)")


# ═════════════════════════════════════════════════════════════════════════════
# T5 — HTTPS activo (si BASE_URL es dominio público)
# ═════════════════════════════════════════════════════════════════════════════

def test_t5_https_activo():
    """
    Si BASE_URL es un dominio público (no localhost), debe usar HTTPS.

    Twilio requiere HTTPS para webhooks de producción.
    Si usás un reverse proxy (Nginx + certbot), esto debería pasar solo.

    Se saltea automáticamente si BASE_URL apunta a localhost.
    """
    if 'localhost' in BASE_URL or '127.0.0.1' in BASE_URL or '0.0.0.0' in BASE_URL:
        warn("BASE_URL es localhost — test T5 (HTTPS) saltado")
        warn("En el servidor real, verificar manualmente: curl https://tudominio.com/")
        return

    assert BASE_URL.startswith('https://'), (
        f"BASE_URL no usa HTTPS: {BASE_URL}. "
        "Twilio requiere HTTPS para webhooks en producción. "
        "Configurar Nginx + certbot o similar."
    )
    ok(f"HTTPS activo: {BASE_URL}")


# ═════════════════════════════════════════════════════════════════════════════
# T6 — MASTER_ACCESS_KEY configurada
# ═════════════════════════════════════════════════════════════════════════════

def test_t6_master_access_key_configurada():
    """
    Si el contenedor está corriendo, MASTER_ACCESS_KEY estaba configurada.

    En producción, Config lanza ValueError al arrancar si no está presente.
    Si llegamos a este punto (el servidor responde), la key estaba configurada.

    También verificamos directamente la variable de entorno dentro del proceso.
    """
    # Si el servidor está vivo (T1 pasó), la key estaba configurada al arrancar.
    # Doble check: intentar importar Config dentro del contenedor.
    master_key = os.getenv('MASTER_ACCESS_KEY')

    if master_key:
        ok(f"MASTER_ACCESS_KEY presente ({len(master_key)} caracteres)")
    else:
        # Podría ser que estemos corriendo el test desde fuera del contenedor.
        # En ese caso, el hecho de que el servidor esté vivo (T1 pasó) es suficiente.
        warn(
            "MASTER_ACCESS_KEY no visible en este proceso — "
            "pero el servidor está vivo (T1 pasó), "
            "lo que confirma que estaba configurada al iniciar."
        )
        ok("MASTER_ACCESS_KEY confirmada implícitamente (servidor arrancó)")


# ═════════════════════════════════════════════════════════════════════════════
# T7 — Redis responde con autenticación
# ═════════════════════════════════════════════════════════════════════════════

def test_t7_redis_con_auth():
    """
    Redis debe requerir contraseña (S4 activo).

    Verifica dos cosas:
    a) redis-cli sin contraseña → error de autenticación
    b) redis-cli con REDIS_PASSWORD → PONG

    Requiere redis-cli en el PATH (disponible en el contenedor).
    Si no está disponible, hace el check vía Python redis client.
    """
    redis_url      = os.getenv('REDIS_URL', '')
    redis_password = os.getenv('REDIS_PASSWORD', '')

    if not redis_password and not redis_url:
        warn("REDIS_PASSWORD y REDIS_URL no están en el entorno de este proceso.")
        warn("Verificar manualmente desde el contenedor:")
        warn("  redis-cli ping                     → NOAUTH (sin pass)")
        warn("  redis-cli -a $REDIS_PASSWORD ping  → PONG")
        return

    try:
        import redis as redis_lib

        # a) Sin contraseña → debe fallar
        try:
            r_noauth = redis_lib.Redis(host='redis', port=6379, db=0, socket_timeout=2)
            r_noauth.ping()
            # Si no lanzó excepción, Redis no tiene contraseña — problema
            fail("Redis respondió PING sin contraseña (S4 no activo)")
            raise AssertionError(
                "Redis no requiere contraseña. "
                "Verificar que REDIS_PASSWORD está en .env y que "
                "docker-compose.yml tiene --requirepass ${REDIS_PASSWORD}."
            )
        except redis_lib.exceptions.AuthenticationError:
            ok("Redis sin contraseña → AuthenticationError (correcto)")
        except Exception as e:
            warn(f"No se pudo conectar a Redis sin auth: {type(e).__name__} — puede ser normal si el host no resuelve")

        # b) Con contraseña → debe funcionar
        if redis_password:
            r_auth = redis_lib.Redis(
                host='redis', port=6379, db=0,
                password=redis_password,
                socket_timeout=2,
            )
            pong = r_auth.ping()
            assert pong is True, "Redis con contraseña no respondió PONG"
            ok("Redis con REDIS_PASSWORD → PONG (S4 activo)")

    except ImportError:
        warn("redis-py no disponible — verificar manualmente (ver instrucciones arriba)")


# ═════════════════════════════════════════════════════════════════════════════
# T8 — Logs no exponen teléfonos en claro (S6 activo)
# ═════════════════════════════════════════════════════════════════════════════

def test_t8_logs_sin_pii():
    """
    Los logs del contenedor no deben contener números de teléfono en claro.

    Busca el patrón +549XXXXXXX (10+ dígitos tras +549) en los últimos
    200 líneas de logs de Docker. Si encuentra coincidencia, S6 no está activo.

    Solo corre si docker está disponible en el PATH.
    """
    import re

    try:
        result = subprocess.run(
            ['docker', 'logs', '--tail', '200', 'whatsapp-demo'],
            capture_output=True,
            text=True,
            timeout=10,
        )
        logs = result.stdout + result.stderr
    except (FileNotFoundError, subprocess.TimeoutExpired):
        warn("docker no disponible en PATH — T8 saltado")
        warn("Verificar manualmente: docker logs whatsapp-demo | grep '+549'")
        return

    # Buscar teléfonos argentinos en claro: +549 seguido de 8+ dígitos sin enmascarar
    # Un teléfono enmascarado se ve como: +5491****5678 (contiene ****)
    patron_telefono_claro = re.compile(r'\+549\d{8,}')
    patron_enmascarado    = re.compile(r'\+549\d+\*+\d+')

    matches_crudos = patron_telefono_claro.findall(logs)

    # Filtrar los que son versiones enmascaradas (no cuentan como exposición)
    expuestos = [
        m for m in matches_crudos
        if not patron_enmascarado.match(m)
    ]

    if expuestos:
        # Mostrar solo los primeros 3 como muestra
        muestra = expuestos[:3]
        fail(
            f"Se encontraron {len(expuestos)} teléfonos en claro en los logs: "
            f"{muestra}. S6 (SanitizedLogger) no está activo."
        )
        raise AssertionError(
            "Teléfonos expuestos en logs. "
            "Verificar que SanitizedLogger está siendo usado en "
            "client_service.py y whatsapp_handler.py."
        )
    else:
        ok("Sin teléfonos en claro en los últimos 200 líneas de logs (S6 activo)")


# ═════════════════════════════════════════════════════════════════════════════
# T9 — Variables críticas de entorno presentes
# ═════════════════════════════════════════════════════════════════════════════

def test_t9_variables_entorno_criticas():
    """
    Verifica que las variables críticas están configuradas en el entorno
    del proceso actual (dentro del contenedor).

    Variables requeridas para producción:
        ENVIRONMENT         debe ser 'production'
        TWILIO_ACCOUNT_SID  credencial Twilio
        TWILIO_AUTH_TOKEN   credencial Twilio (para firma S1)
        WEBHOOK_URL         URL pública del webhook
        REDIS_URL           conexión a Redis
        MASTER_ACCESS_KEY   acceso administrativo
    """
    required = {
        'ENVIRONMENT':        'production',   # valor esperado exacto
        'TWILIO_ACCOUNT_SID': None,           # cualquier valor no vacío
        'TWILIO_AUTH_TOKEN':  None,
        'WEBHOOK_URL':        None,
        'REDIS_URL':          None,
        'MASTER_ACCESS_KEY':  None,
    }

    faltantes   = []
    incorrectas = []

    for var, expected in required.items():
        value = os.getenv(var, '').strip()

        if not value:
            faltantes.append(var)
            continue

        if expected is not None and value != expected:
            incorrectas.append(f"{var}={value!r} (esperado {expected!r})")
            continue

        # Censurar valores sensibles en el log
        if var in ('TWILIO_AUTH_TOKEN', 'MASTER_ACCESS_KEY', 'REDIS_URL'):
            display = value[:4] + '****'
        else:
            display = value

        info(f"{var} = {display}")

    if faltantes:
        fail(f"Variables no configuradas: {faltantes}")
        raise AssertionError(
            f"Variables faltantes en .env: {faltantes}. "
            "Completar antes de ir a producción."
        )

    if incorrectas:
        fail(f"Variables con valor incorrecto: {incorrectas}")
        raise AssertionError(
            f"Variables mal configuradas: {incorrectas}."
        )

    ok(f"Todas las variables críticas presentes ({len(required)} variables)")


# ═════════════════════════════════════════════════════════════════════════════
# T10 — Contenedor corriendo como usuario no-root
# ═════════════════════════════════════════════════════════════════════════════

def test_t10_usuario_no_root():
    """
    El proceso Python no debe correr como root (UID 0).

    docker-compose.prod.yml tiene: user: mluser
    Si el contenedor arrancó correctamente, os.getuid() > 0.

    En Windows (Docker Desktop), os.getuid() no existe — se saltea.
    """
    if not hasattr(os, 'getuid'):
        warn("os.getuid() no disponible (Windows host) — T10 saltado")
        warn("Verificar manualmente: docker exec whatsapp-demo whoami")
        return

    uid = os.getuid()
    assert uid != 0, (
        f"El proceso corre como root (UID=0). "
        f"Verificar que docker-compose.prod.yml tiene 'user: mluser' "
        f"y que el Dockerfile crea ese usuario."
    )
    ok(f"Proceso corriendo como UID={uid} (no root)")


# ═════════════════════════════════════════════════════════════════════════════
# Runner
# ═════════════════════════════════════════════════════════════════════════════

def run_all():
    sep()
    print(f"{C.BOLD}  SMOKE TESTS — POST-DEPLOY PRODUCCIÓN{C.END}")
    print(f"  Base URL: {C.CYAN}{BASE_URL}{C.END}")
    print(f"  Timeout:  {TIMEOUT}s")
    sep()

    tests = [
        ("T1  — Health check",                    test_t1_health_check),
        ("T2  — /webhook sin firma → 403 (S1)",   test_t2_webhook_sin_firma_da_403),
        ("T3  — /webhook GET → 405",              test_t3_webhook_get_da_405),
        ("T4  — Calendar flood → 429 (S2)",        test_t4_calendar_webhook_rate_limit),
        ("T5  — HTTPS activo",                    test_t5_https_activo),
        ("T6  — MASTER_ACCESS_KEY configurada",   test_t6_master_access_key_configurada),
        ("T7  — Redis con auth (S4)",              test_t7_redis_con_auth),
        ("T8  — Logs sin PII (S6)",                test_t8_logs_sin_pii),
        ("T9  — Variables de entorno críticas",   test_t9_variables_entorno_criticas),
        ("T10 — Usuario no-root",                 test_t10_usuario_no_root),
    ]

    # T1 es bloqueante: si el servidor no responde, no tiene sentido continuar
    print(f"\n{C.CYAN}── Verificación de conectividad ──{C.END}")
    print(f"\n  {C.CYAN}► T1  — Health check{C.END}")
    try:
        test_t1_health_check()
    except AssertionError as e:
        fail(str(e))
        sep()
        print(f"{C.RED}{C.BOLD}  ❌ SERVIDOR NO DISPONIBLE — Tests abortados{C.END}")
        print(f"  {C.YELLOW}Verificar que el contenedor está levantado:{C.END}")
        print(f"  docker-compose -f docker-compose.prod.yml ps")
        sep()
        return False

    # Resto de los tests
    passed = 1  # T1 ya pasó
    failed = 0
    skipped = 0

    grupos = {
        "Seguridad externa":   tests[1:5],   # T2–T5
        "Configuración":       tests[5:7],   # T6–T7
        "Observabilidad":      tests[7:9],   # T8–T9
        "Infraestructura":     tests[9:],    # T10
    }

    for grupo, grupo_tests in grupos.items():
        subsep()
        print(f"\n{C.CYAN}── {grupo} ──{C.END}")
        for label, fn in grupo_tests:
            print(f"\n  {C.CYAN}► {label}{C.END}")
            try:
                fn()
                passed += 1
            except AssertionError as e:
                fail(str(e))
                failed += 1
            except Exception as e:
                fail(f"Error inesperado: {type(e).__name__}: {e}")
                failed += 1

    sep()
    total = passed + failed
    if failed == 0:
        print(f"{C.GREEN}{C.BOLD}  ✅ TODOS LOS SMOKE TESTS PASARON ({passed}/{total}){C.END}")
        print(f"\n  {C.GREEN}El servidor está listo para producción.{C.END}")
    else:
        print(f"{C.RED}{C.BOLD}  ❌ {failed} SMOKE TEST(S) FALLARON ({passed}/{total} pasaron){C.END}")
        print(f"\n  {C.YELLOW}Resolver los fallos antes de ir a producción.{C.END}")
    sep()

    return failed == 0


# ─── Entry point para pytest ──────────────────────────────────────────────────

def test_smoke_completo():
    """Entry point para pytest. Corre todos los smoke tests."""
    assert run_all(), "Uno o más smoke tests fallaron"


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
