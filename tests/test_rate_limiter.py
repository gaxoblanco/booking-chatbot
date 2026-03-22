#!/usr/bin/env python3
"""
Test: Rate limiting en webhook de WhatsApp (Issue 3)
=====================================================

Verifica que RateLimiter bloquea correctamente números que superan
el límite de mensajes por ventana de tiempo.

Uso:
    docker exec -it whatsapp-demo python tests/test_issue3_rate_limiter.py
    docker exec -it whatsapp-demo pytest tests/test_issue3_rate_limiter.py -v
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.rate_limiter import RateLimiter
from src.config.domain_config import DomainConfig


# ─── Helpers de color ────────────────────────────────────────────────────────

class C:
    GREEN  = '\033[92m'
    RED    = '\033[91m'
    CYAN   = '\033[96m'
    BOLD   = '\033[1m'
    END    = '\033[0m'

def ok(t):   print(f"  {C.GREEN}✅ {t}{C.END}")
def fail(t): print(f"  {C.RED}❌ {t}{C.END}")
def info(t): print(f"  ℹ️  {t}")
def sep():   print("=" * 60)


# ─── Casos de prueba ─────────────────────────────────────────────────────────

def test_domain_config_parametros():
    """Verifica que DomainConfig tiene los 3 parámetros de rate limiting."""
    for attr in [
        'RATE_LIMIT_MAX_MESSAGES_PER_WINDOW',
        'RATE_LIMIT_WINDOW_SECONDS',
        'RATE_LIMIT_BLOCK_MINUTES',
    ]:
        val = getattr(DomainConfig, attr, None)
        assert val is not None, f"DomainConfig no tiene {attr}"
        assert isinstance(val, (int, float)) and val > 0, (
            f"{attr} debe ser un número positivo, obtenido: {val}"
        )
        info(f"{attr} = {val}")
    ok("Todos los parámetros de rate limiting están en DomainConfig")


def test_mensajes_dentro_del_limite():
    """
    Dentro del límite → record() retorna True en todos los mensajes.
    Usa instancia propia para no afectar el rate_limiter global.
    """
    rl = RateLimiter()
    # Sobreescribir parámetros para test rápido sin importar DomainConfig
    # Inyectamos directamente vía monkey-patch temporal en DomainConfig
    original_max = DomainConfig.RATE_LIMIT_MAX_MESSAGES_PER_WINDOW
    original_win = DomainConfig.RATE_LIMIT_WINDOW_SECONDS
    DomainConfig.RATE_LIMIT_MAX_MESSAGES_PER_WINDOW = 5
    DomainConfig.RATE_LIMIT_WINDOW_SECONDS = 10

    try:
        phone = "+5490001110001"
        for i in range(5):
            result = rl.record(phone)
            assert result is True, f"Mensaje {i+1} debería pasar, retornó False"

        assert not rl.is_blocked(phone), "No debería estar bloqueado dentro del límite"
        ok("5 mensajes dentro del límite → todos pasan, no bloqueado")
    finally:
        DomainConfig.RATE_LIMIT_MAX_MESSAGES_PER_WINDOW = original_max
        DomainConfig.RATE_LIMIT_WINDOW_SECONDS = original_win


def test_superar_limite_activa_bloqueo():
    """
    Al superar el límite → record() retorna False y is_blocked() retorna True.
    """
    rl = RateLimiter()
    original_max = DomainConfig.RATE_LIMIT_MAX_MESSAGES_PER_WINDOW
    original_win = DomainConfig.RATE_LIMIT_WINDOW_SECONDS
    original_block = DomainConfig.RATE_LIMIT_BLOCK_MINUTES
    DomainConfig.RATE_LIMIT_MAX_MESSAGES_PER_WINDOW = 3
    DomainConfig.RATE_LIMIT_WINDOW_SECONDS = 10
    DomainConfig.RATE_LIMIT_BLOCK_MINUTES = 1

    try:
        phone = "+5490001110002"

        # Enviar hasta el límite
        for i in range(3):
            rl.record(phone)

        # El siguiente mensaje supera el límite
        result = rl.record(phone)
        assert result is False, "El 4to mensaje debería retornar False (límite superado)"
        assert rl.is_blocked(phone), "El número debería estar bloqueado ahora"
        ok("Superar el límite → record() retorna False y número queda bloqueado")
    finally:
        DomainConfig.RATE_LIMIT_MAX_MESSAGES_PER_WINDOW = original_max
        DomainConfig.RATE_LIMIT_WINDOW_SECONDS = original_win
        DomainConfig.RATE_LIMIT_BLOCK_MINUTES = original_block


def test_is_blocked_retorna_true_durante_bloqueo():
    """
    Número bloqueado → is_blocked() retorna True en llamadas subsiguientes.
    """
    rl = RateLimiter()
    original_max = DomainConfig.RATE_LIMIT_MAX_MESSAGES_PER_WINDOW
    original_win = DomainConfig.RATE_LIMIT_WINDOW_SECONDS
    original_block = DomainConfig.RATE_LIMIT_BLOCK_MINUTES
    DomainConfig.RATE_LIMIT_MAX_MESSAGES_PER_WINDOW = 2
    DomainConfig.RATE_LIMIT_WINDOW_SECONDS = 10
    DomainConfig.RATE_LIMIT_BLOCK_MINUTES = 1

    try:
        phone = "+5490001110003"

        # Superar límite
        rl.record(phone)
        rl.record(phone)
        rl.record(phone)  # Este activa el bloqueo

        # Múltiples checks seguidos — todos deben retornar True
        for i in range(3):
            assert rl.is_blocked(phone), f"is_blocked() debería ser True (intento {i+1})"

        ok("is_blocked() retorna True consistentemente durante el bloqueo")
    finally:
        DomainConfig.RATE_LIMIT_MAX_MESSAGES_PER_WINDOW = original_max
        DomainConfig.RATE_LIMIT_WINDOW_SECONDS = original_win
        DomainConfig.RATE_LIMIT_BLOCK_MINUTES = original_block


def test_numeros_distintos_son_independientes():
    """
    Bloquear un número no afecta a otros números.
    """
    rl = RateLimiter()
    original_max = DomainConfig.RATE_LIMIT_MAX_MESSAGES_PER_WINDOW
    original_win = DomainConfig.RATE_LIMIT_WINDOW_SECONDS
    original_block = DomainConfig.RATE_LIMIT_BLOCK_MINUTES
    DomainConfig.RATE_LIMIT_MAX_MESSAGES_PER_WINDOW = 2
    DomainConfig.RATE_LIMIT_WINDOW_SECONDS = 10
    DomainConfig.RATE_LIMIT_BLOCK_MINUTES = 1

    try:
        phone_malo  = "+5490001110004"
        phone_bueno = "+5490001110005"

        # Bloquear phone_malo
        rl.record(phone_malo)
        rl.record(phone_malo)
        rl.record(phone_malo)  # Bloqueo activado

        assert rl.is_blocked(phone_malo), "phone_malo debería estar bloqueado"
        assert not rl.is_blocked(phone_bueno), "phone_bueno NO debería estar bloqueado"

        # phone_bueno puede seguir enviando mensajes
        result = rl.record(phone_bueno)
        assert result is True, "phone_bueno debería poder enviar mensajes"

        ok("Bloquear un número no afecta a otros")
    finally:
        DomainConfig.RATE_LIMIT_MAX_MESSAGES_PER_WINDOW = original_max
        DomainConfig.RATE_LIMIT_WINDOW_SECONDS = original_win
        DomainConfig.RATE_LIMIT_BLOCK_MINUTES = original_block


def test_ventana_deslizante_limpia_mensajes_viejos():
    """
    Mensajes fuera de la ventana de tiempo no cuentan.
    Simula ventana de 1 segundo para que el test sea rápido.
    """
    rl = RateLimiter()
    original_max = DomainConfig.RATE_LIMIT_MAX_MESSAGES_PER_WINDOW
    original_win = DomainConfig.RATE_LIMIT_WINDOW_SECONDS
    DomainConfig.RATE_LIMIT_MAX_MESSAGES_PER_WINDOW = 3
    DomainConfig.RATE_LIMIT_WINDOW_SECONDS = 1  # 1 segundo para test rápido

    try:
        phone = "+5490001110006"

        # Enviar 2 mensajes
        rl.record(phone)
        rl.record(phone)

        # Esperar que la ventana expire
        info("Esperando 1.1s para que la ventana expire...")
        time.sleep(1.1)

        # Ahora los mensajes viejos no cuentan
        # Podemos enviar 3 nuevos sin bloquearnos
        for i in range(3):
            result = rl.record(phone)
            assert result is True, (
                f"Mensaje {i+1} post-ventana debería pasar, retornó False"
            )

        assert not rl.is_blocked(phone), "No debería estar bloqueado (ventana expiró)"
        ok("Mensajes fuera de la ventana no cuentan — ventana deslizante funciona")
    finally:
        DomainConfig.RATE_LIMIT_MAX_MESSAGES_PER_WINDOW = original_max
        DomainConfig.RATE_LIMIT_WINDOW_SECONDS = original_win


def test_get_stats_retorna_estructura_correcta():
    """get_stats() retorna dict con las claves esperadas."""
    rl = RateLimiter()
    stats = rl.get_stats()

    assert 'phones_tracked' in stats, "Falta 'phones_tracked' en stats"
    assert 'active_blocks' in stats, "Falta 'active_blocks' en stats"
    assert 'blocked_phones' in stats, "Falta 'blocked_phones' en stats"
    assert isinstance(stats['phones_tracked'], int), "phones_tracked debe ser int"
    assert isinstance(stats['active_blocks'], int), "active_blocks debe ser int"

    ok(f"get_stats() retorna estructura correcta: {stats}")


# ─── Runner ───────────────────────────────────────────────────────────────────

def run_all():
    sep()
    print(f"{C.BOLD}  TEST ISSUE 3 — Rate limiter del webhook{C.END}")
    sep()

    tests = [
        test_domain_config_parametros,
        test_mensajes_dentro_del_limite,
        test_superar_limite_activa_bloqueo,
        test_is_blocked_retorna_true_durante_bloqueo,
        test_numeros_distintos_son_independientes,
        test_ventana_deslizante_limpia_mensajes_viejos,
        test_get_stats_retorna_estructura_correcta,
    ]

    passed = 0
    failed = 0

    for t in tests:
        print(f"\n{C.CYAN}► {t.__name__}{C.END}")
        try:
            t()
            passed += 1
        except AssertionError as e:
            fail(str(e))
            failed += 1
        except Exception as e:
            fail(f"Error inesperado: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    sep()
    if failed == 0:
        print(f"{C.GREEN}{C.BOLD}  ✅ TODOS LOS TESTS PASARON ({passed}/{len(tests)}){C.END}")
    else:
        print(f"{C.RED}{C.BOLD}  ❌ {failed} TEST(S) FALLARON ({passed}/{len(tests)} pasaron){C.END}")
    sep()

    return failed == 0


def test_issue3_completo():
    """Entry point para pytest."""
    assert run_all(), "Uno o más tests del issue 3 fallaron"


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
