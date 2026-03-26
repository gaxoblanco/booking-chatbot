#!/usr/bin/env python3
"""
Test: Issue 9 — Anti-spam en booking inicial
=============================================

Verifica que BookingLimiter:
    1. Permite intentos dentro del límite
    2. Bloquea cuando se supera el límite
    3. El bloqueo se levanta al expirar
    4. Reset funciona (para tests)
    5. Números distintos tienen contadores independientes
    6. get_attempts() y is_blocked() reportan correctamente
    7. Instancia global importable desde booking_limiter

Uso:
    docker exec -it whatsapp-demo python tests/test_booking_spam.py
"""

import sys
import time
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))


# ── Colores ──────────────────────────────────────────────────────────────────
class C:
    GREEN = '\033[92m'; RED = '\033[91m'; CYAN = '\033[96m'
    BOLD  = '\033[1m';  END = '\033[0m'

def ok(t):   print(f"  {C.GREEN}✅ {t}{C.END}")
def fail(t): print(f"  {C.RED}❌ {t}{C.END}")
def info(t): print(f"  ℹ️  {t}")
def sep():   print("=" * 60)

# ── Teléfonos de prueba ───────────────────────────────────────────────────────
PHONE_A = "+5490000033001"
PHONE_B = "+5490000033002"

# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_limiter(max_attempts=3, window_minutes=60, block_minutes=5):
    """Crea un BookingLimiter con config customizada para tests."""
    from src.core.booking_limiter import BookingLimiter
    limiter = BookingLimiter()
    limiter._max_attempts   = max_attempts
    limiter._window_minutes = window_minutes
    limiter._block_minutes  = block_minutes
    return limiter


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_instancia_global_importable():
    """La instancia global booking_limiter debe ser importable."""
    from src.core.booking_limiter import booking_limiter
    assert booking_limiter is not None
    assert hasattr(booking_limiter, 'record_attempt')
    assert hasattr(booking_limiter, 'reset')
    ok("booking_limiter importable y tiene los métodos requeridos")


def test_intentos_dentro_del_limite_permitidos():
    """Hasta max_attempts intentos deben retornar True."""
    limiter = _make_limiter(max_attempts=3)
    limiter.reset(PHONE_A)

    resultados = [limiter.record_attempt(PHONE_A) for _ in range(3)]

    assert all(resultados), (
        f"Los primeros 3 intentos deberían ser True, obtenido {resultados}"
    )
    ok(f"3/3 intentos dentro del límite → True")


def test_intento_que_supera_limite_es_bloqueado():
    """El intento N+1 debe retornar False y activar el bloqueo."""
    limiter = _make_limiter(max_attempts=3)
    limiter.reset(PHONE_A)

    # Llenar el límite
    for _ in range(3):
        limiter.record_attempt(PHONE_A)

    # El 4to intento debe ser rechazado
    result = limiter.record_attempt(PHONE_A)
    assert result is False, (
        f"El 4to intento debería ser False (bloqueado), obtenido {result}"
    )
    ok("El intento que supera el límite retorna False")


def test_numero_queda_bloqueado_tras_superar_limite():
    """Después del bloqueo, is_blocked() debe retornar True."""
    limiter = _make_limiter(max_attempts=2, block_minutes=5)
    limiter.reset(PHONE_A)

    limiter.record_attempt(PHONE_A)
    limiter.record_attempt(PHONE_A)
    limiter.record_attempt(PHONE_A)  # Este activa el bloqueo

    assert limiter.is_blocked(PHONE_A) is True, (
        "Después de superar el límite, is_blocked() debe ser True"
    )
    ok("is_blocked() retorna True después de superar el límite")


def test_intentos_subsiguientes_bloqueados():
    """Todos los intentos posteriores al bloqueo deben retornar False."""
    limiter = _make_limiter(max_attempts=2, block_minutes=5)
    limiter.reset(PHONE_A)

    for _ in range(2):
        limiter.record_attempt(PHONE_A)
    limiter.record_attempt(PHONE_A)  # activa bloqueo

    # Todos los siguientes deben ser False
    for i in range(3):
        result = limiter.record_attempt(PHONE_A)
        assert result is False, (
            f"Intento {i+1} post-bloqueo debería ser False, obtenido {result}"
        )

    ok("Todos los intentos post-bloqueo retornan False")


def test_reset_limpia_estado():
    """reset() debe limpiar contadores y bloqueos."""
    limiter = _make_limiter(max_attempts=2, block_minutes=5)
    limiter.reset(PHONE_A)

    # Llenar y bloquear
    for _ in range(3):
        limiter.record_attempt(PHONE_A)

    assert limiter.is_blocked(PHONE_A) is True

    # Reset
    limiter.reset(PHONE_A)

    assert limiter.is_blocked(PHONE_A) is False, "Después del reset no debe estar bloqueado"
    assert limiter.get_attempts(PHONE_A) == 0, "Después del reset los intentos deben ser 0"

    # Debe poder hacer intentos normalmente
    result = limiter.record_attempt(PHONE_A)
    assert result is True, "Después del reset debe poder hacer intentos"

    ok("reset() limpia contadores y bloqueos correctamente")


def test_numeros_distintos_son_independientes():
    """PHONE_A bloqueado no afecta a PHONE_B."""
    limiter = _make_limiter(max_attempts=2, block_minutes=5)
    limiter.reset(PHONE_A)
    limiter.reset(PHONE_B)

    # Bloquear A
    for _ in range(3):
        limiter.record_attempt(PHONE_A)

    assert limiter.is_blocked(PHONE_A) is True

    # B no debe estar bloqueado
    result_b = limiter.record_attempt(PHONE_B)
    assert result_b is True, (
        f"PHONE_B no debería estar bloqueado por las acciones de PHONE_A, "
        f"obtenido {result_b}"
    )
    ok("Números distintos tienen contadores independientes")


def test_get_attempts_cuenta_correctamente():
    """get_attempts() debe reflejar la cantidad actual en ventana."""
    limiter = _make_limiter(max_attempts=5)
    limiter.reset(PHONE_A)

    assert limiter.get_attempts(PHONE_A) == 0

    limiter.record_attempt(PHONE_A)
    assert limiter.get_attempts(PHONE_A) == 1

    limiter.record_attempt(PHONE_A)
    assert limiter.get_attempts(PHONE_A) == 2

    ok("get_attempts() cuenta correctamente los intentos en ventana")


def test_bloqueo_expira_con_el_tiempo():
    """El bloqueo debe liberarse una vez que pasa el tiempo configurado."""
    limiter = _make_limiter(max_attempts=2, block_minutes=1)
    limiter.reset(PHONE_A)

    # Bloquear
    for _ in range(3):
        limiter.record_attempt(PHONE_A)

    assert limiter.is_blocked(PHONE_A) is True

    # Simular que pasó el tiempo de bloqueo manipulando _blocked_until
    limiter._blocked_until[PHONE_A] = datetime.now() - timedelta(seconds=1)

    assert limiter.is_blocked(PHONE_A) is False, (
        "El bloqueo debería haber expirado"
    )

    # Debe poder hacer intentos nuevamente
    # (reseteamos también los intentos viejos para que entre en ventana)
    limiter.reset(PHONE_A)
    result = limiter.record_attempt(PHONE_A)
    assert result is True, "Después de expirar el bloqueo debe poder intentar"

    ok("El bloqueo expira correctamente con el tiempo")


def test_get_stats_estructura():
    """get_stats() debe retornar la estructura esperada."""
    from src.core.booking_limiter import booking_limiter

    stats = booking_limiter.get_stats()

    for key in ('tracked_numbers', 'blocked_numbers', 'config'):
        assert key in stats, f"Falta '{key}' en stats"

    for cfg_key in ('max_attempts', 'window_minutes', 'block_minutes'):
        assert cfg_key in stats['config'], f"Falta config.{cfg_key}"

    assert isinstance(stats['tracked_numbers'], int)
    assert isinstance(stats['blocked_numbers'], int)

    ok(f"get_stats() retorna estructura correcta: {stats}")


def test_constantes_en_domain_config():
    """DomainConfig debe tener las 3 constantes del issue 9."""
    from src.config.domain_config import DomainConfig

    for const in (
        'MAX_BOOKING_ATTEMPTS_PER_WINDOW',
        'BOOKING_ATTEMPT_WINDOW_MINUTES',
        'BOOKING_ATTEMPT_BLOCK_MINUTES',
    ):
        val = getattr(DomainConfig, const, None)
        assert val is not None, f"DomainConfig.{const} no existe"
        assert isinstance(val, int) and val > 0, (
            f"DomainConfig.{const} debe ser int positivo, obtenido {val}"
        )
        info(f"{const} = {val}")

    ok("Las 3 constantes de booking anti-spam están en DomainConfig")


# ── Runner ────────────────────────────────────────────────────────────────────

def run_all():
    sep()
    print(f"{C.BOLD}  TEST ISSUE 9 — Anti-spam en booking{C.END}")
    sep()

    tests = [
        test_instancia_global_importable,
        test_intentos_dentro_del_limite_permitidos,
        test_intento_que_supera_limite_es_bloqueado,
        test_numero_queda_bloqueado_tras_superar_limite,
        test_intentos_subsiguientes_bloqueados,
        test_reset_limpia_estado,
        test_numeros_distintos_son_independientes,
        test_get_attempts_cuenta_correctamente,
        test_bloqueo_expira_con_el_tiempo,
        test_get_stats_estructura,
        test_constantes_en_domain_config,
    ]

    passed = failed = 0
    for t in tests:
        print(f"\n{C.CYAN}► {t.__name__}{C.END}")
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

def test_completo():
    assert run_all()

if __name__ == "__main__":
    sys.exit(0 if run_all() else 1)
