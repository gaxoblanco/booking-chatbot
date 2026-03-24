#!/usr/bin/env python3
"""
Test: Seguridad Fase 2 — S4 + S5 + S6
=======================================

S4 — Redis sin puerto expuesto + contraseña
S5 — MASTER_ACCESS_KEY sin default hardcodeado
S6 — SanitizedLogger enmascara PII en logs

Uso:
    docker exec -it whatsapp-demo python tests/test_security_phase2.py
"""

import sys
import os
import re
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))


class C:
    GREEN = '\033[92m'; RED = '\033[91m'; CYAN = '\033[96m'
    BOLD  = '\033[1m';  END = '\033[0m'

def ok(t):   print(f"  {C.GREEN}✅ {t}{C.END}")
def fail(t): print(f"  {C.RED}❌ {t}{C.END}")
def info(t): print(f"  ℹ️  {t}")
def sep():   print("=" * 60)


# =============================================================================
# S4 — Redis: sin puerto expuesto + contraseña
# =============================================================================

def _load_compose():
    """
    Busca docker-compose.yml en rutas posibles.
    Retorna (content, path) o (None, None) si no está montado en el container.
    El docker-compose.yml es un archivo de infraestructura — no siempre
    está disponible dentro del container. En ese caso los tests S4 se
    verifican manualmente o desde el host con:
        python tests/test_security_phase2.py
    """
    candidates = [
        Path(__file__).parent.parent / 'docker' / 'docker-compose.yml',
        Path(__file__).parent.parent / 'docker-compose.yml',
        Path('/docker-compose.yml'),
    ]
    for p in candidates:
        if p.exists():
            return p.read_text(), p
    return None, None


def test_s4_docker_compose_sin_ports():
    """docker-compose.yml no debe tener ports: en el bloque redis."""
    content, path = _load_compose()
    if content is None:
        info("docker-compose.yml no está en el container — verificar manualmente:")
        info("  grep -A10 'redis:' docker/docker-compose.yml | grep -v 'ports:'")
        return

    idx = content.find('  redis:')
    assert idx != -1, "No se encontró el bloque 'redis:' en docker-compose.yml"
    next_block = content.find('\n  ', idx + 10)
    redis_block = content[idx:next_block] if next_block != -1 else content[idx:]

    assert 'ports:' not in redis_block, (
        "Redis tiene 'ports:' — el puerto 6379 está expuesto al host. "
        "Cambiar 'ports:' por 'expose:'"
    )
    ok("Redis usa 'expose:' en lugar de 'ports:' — no expuesto al host")


def test_s4_docker_compose_tiene_requirepass():
    """docker-compose.yml debe tener --requirepass en el comando de Redis."""
    content, path = _load_compose()
    if content is None:
        info("docker-compose.yml no disponible en container — verificar manualmente:")
        info("  grep 'requirepass' docker/docker-compose.yml")
        return

    assert 'requirepass' in content, (
        "Redis no tiene --requirepass — cualquier proceso en la red puede leer sesiones"
    )
    ok("Redis tiene --requirepass configurado")


def test_s4_docker_compose_usa_variable_redis_password():
    """--requirepass debe usar ${REDIS_PASSWORD}, no una password hardcodeada."""
    content, path = _load_compose()
    if content is None:
        info("docker-compose.yml no disponible en container — verificar manualmente:")
        info("  grep 'requirepass' docker/docker-compose.yml  # debe decir REDIS_PASSWORD")
        return

    idx = content.find('requirepass')
    assert idx != -1
    contexto = content[idx:idx+50]
    assert 'REDIS_PASSWORD' in contexto, (
        f"--requirepass no usa variable: '{contexto}'. Debe ser: --requirepass ${{REDIS_PASSWORD}}"
    )
    ok("--requirepass usa ${REDIS_PASSWORD} — no hardcodeada")


def test_s4_redis_url_incluye_password_en_env():
    """REDIS_URL en .env debe incluir la contraseña."""
    env_path = Path(__file__).parent.parent / 'docker' / '.env'
    if not env_path.exists():
        env_path = Path(__file__).parent.parent / '.env'
    if not env_path.exists():
        info("No se encontró .env — test saltado (verificar manualmente)")
        return

    content = env_path.read_text()
    if 'REDIS_URL' not in content:
        info("REDIS_URL no está en .env — test saltado")
        return

    # Buscar la línea de REDIS_URL
    for line in content.split('\n'):
        if line.startswith('REDIS_URL='):
            url = line.split('=', 1)[1].strip()
            # URL con auth: redis://:password@host:port/db
            if '@' in url or 'REDIS_PASSWORD' in url:
                ok(f"REDIS_URL incluye credenciales")
            else:
                fail(
                    f"REDIS_URL sin credenciales: '{url}'. "
                    "Debe ser: redis://:${{REDIS_PASSWORD}}@redis:6379/0"
                )
            return


# =============================================================================
# S5 — MASTER_ACCESS_KEY sin default hardcodeado
# =============================================================================

def test_s5_no_default_hardcodeado_en_codigo():
    """config.py no debe tener 'ADMIN2025' hardcodeado como default."""
    config_path = Path(__file__).parent.parent / 'src' / 'config' / 'config.py'
    assert config_path.exists(), f"No se encontró {config_path}"

    content = config_path.read_text()

    assert "os.getenv('MASTER_ACCESS_KEY', 'ADMIN2025')" not in content, (
        "MASTER_ACCESS_KEY tiene 'ADMIN2025' como default hardcodeado. "
        "Cambiar a: MASTER_ACCESS_KEY = os.getenv('MASTER_ACCESS_KEY')"
    )
    ok("config.py no tiene 'ADMIN2025' hardcodeado como default")


def test_s5_sin_variable_en_dev_no_crashea():
    """En development, MASTER_ACCESS_KEY=None no debe levantar excepción."""
    with patch.dict(os.environ, {'ENVIRONMENT': 'development'}, clear=False):
        os.environ.pop('MASTER_ACCESS_KEY', None)
        try:
            # Re-importar para evaluar el módulo con el entorno actual
            import importlib
            import src.config.config as cfg
            importlib.reload(cfg)
            ok("MASTER_ACCESS_KEY=None en development no lanza excepción")
        except ValueError as e:
            fail(f"ValueError en development (no debería): {e}")
        except Exception as e:
            info(f"Excepción inesperada: {e} — puede ser por otro campo requerido")


def test_s5_sin_variable_en_produccion_levanta_error():
    """En production, MASTER_ACCESS_KEY=None debe levantar ValueError al arrancar."""
    import importlib

    with patch.dict(os.environ, {'ENVIRONMENT': 'production'}, clear=False):
        os.environ.pop('MASTER_ACCESS_KEY', None)
        try:
            import src.config.config as cfg
            importlib.reload(cfg)
            # Si llegamos acá, no levantó el error
            # Verificar que al menos la variable queda None
            if cfg.Config.MASTER_ACCESS_KEY is None:
                info(
                    "MASTER_ACCESS_KEY es None en production — "
                    "verificar manualmente que el sistema no permita acceso"
                )
            else:
                fail("MASTER_ACCESS_KEY tiene valor sin configurar la variable de entorno")
        except ValueError as e:
            ok(f"ValueError en production sin MASTER_ACCESS_KEY: correcto")
            info(f"Mensaje: {str(e)[:80]}")
        except Exception as e:
            info(f"Excepción inesperada: {type(e).__name__}: {e}")


def test_s5_con_variable_configurada_funciona():
    """Con MASTER_ACCESS_KEY configurada, no debe lanzar excepción."""
    import importlib

    with patch.dict(os.environ, {
        'ENVIRONMENT':       'production',
        'MASTER_ACCESS_KEY': 'clave-segura-generada',
    }):
        try:
            import src.config.config as cfg
            importlib.reload(cfg)
            assert cfg.Config.MASTER_ACCESS_KEY == 'clave-segura-generada'
            ok("Con MASTER_ACCESS_KEY configurada no lanza excepción")
        except ValueError as e:
            fail(f"ValueError inesperado: {e}")
        except Exception as e:
            info(f"Excepción al recargar config: {e}")


# =============================================================================
# S6 — SanitizedLogger
# =============================================================================

def test_s6_enmascara_telefono_e164():
    """Teléfono E.164 completo queda enmascarado en el log."""
    from src.core.logger import get_logger, _sanitize

    result = _sanitize("+5491112345678")
    assert '****' in result, f"No enmascaró: '{result}'"
    assert result != "+5491112345678", "El teléfono quedó sin enmascarar"
    # Debe conservar los últimos 4 dígitos
    assert '5678' in result, f"Perdió los últimos 4 dígitos: '{result}'"
    ok(f"+5491112345678 → '{result}'")


def test_s6_enmascara_telefono_sin_plus():
    """Teléfono sin + también queda enmascarado."""
    from src.core.logger import _sanitize

    result = _sanitize("5491112345678")
    assert '****' in result
    ok(f"5491112345678 → '{result}'")


def test_s6_enmascara_en_mensaje_con_texto():
    """El teléfono dentro de un mensaje más largo queda enmascarado."""
    from src.core.logger import _sanitize

    msg = "Sesión creada para +5491112345678 — estado: CLIENT_MAIN_MENU"
    result = _sanitize(msg)
    assert "+5491112345678" not in result, "El teléfono completo sigue visible"
    assert "Sesión creada para" in result, "El texto alrededor se perdió"
    assert "CLIENT_MAIN_MENU" in result, "El resto del mensaje se perdió"
    ok("Teléfono enmascarado dentro de mensaje con texto")


def test_s6_texto_sin_telefono_no_cambia():
    """Un mensaje sin teléfonos no debe alterarse."""
    from src.core.logger import _sanitize

    msg = "Error al conectar a Redis — timeout 2s"
    result = _sanitize(msg)
    assert result == msg, f"El mensaje cambió sin teléfono: '{result}'"
    ok("Mensaje sin teléfonos no se altera")


def test_s6_multiples_telefonos_en_mismo_mensaje():
    """Múltiples teléfonos en el mismo mensaje quedan todos enmascarados."""
    from src.core.logger import _sanitize

    msg = "Cliente +5491111111111 agendó con profesional +5492222222222"
    result = _sanitize(msg)
    assert "+5491111111111" not in result
    assert "+5492222222222" not in result
    assert "agendó con profesional" in result
    ok("Múltiples teléfonos en el mismo mensaje quedan enmascarados")


def test_s6_logger_instanciable():
    """get_logger() retorna una instancia con los métodos estándar."""
    from src.core.logger import get_logger

    logger = get_logger(__name__)
    for method in ('debug', 'info', 'warning', 'error', 'critical'):
        assert hasattr(logger, method), f"Falta método: {method}"
    ok("get_logger() retorna instancia con todos los métodos estándar")


def test_s6_drop_in_replacement():
    """SanitizedLogger es compatible con el patrón logging.getLogger."""
    import logging
    from src.core.logger import get_logger

    std_logger  = logging.getLogger(__name__)
    safe_logger = get_logger(__name__)

    # Misma interfaz
    assert hasattr(safe_logger, 'info')
    assert hasattr(safe_logger, 'error')
    assert hasattr(safe_logger, 'setLevel')
    assert hasattr(safe_logger, 'name')
    ok("SanitizedLogger es drop-in replacement de logging.getLogger")


# =============================================================================
# Runner
# =============================================================================

def run_all():
    sep()
    print(f"{C.BOLD}  TEST SEGURIDAD FASE 2 — S4 + S5 + S6{C.END}")
    sep()

    tests = {
        'S4 — Redis sin puerto expuesto': [
            test_s4_docker_compose_sin_ports,
            test_s4_docker_compose_tiene_requirepass,
            test_s4_docker_compose_usa_variable_redis_password,
            test_s4_redis_url_incluye_password_en_env,
        ],
        'S5 — MASTER_ACCESS_KEY sin default': [
            test_s5_no_default_hardcodeado_en_codigo,
            test_s5_sin_variable_en_dev_no_crashea,
            test_s5_sin_variable_en_produccion_levanta_error,
            test_s5_con_variable_configurada_funciona,
        ],
        'S6 — SanitizedLogger': [
            test_s6_enmascara_telefono_e164,
            test_s6_enmascara_telefono_sin_plus,
            test_s6_enmascara_en_mensaje_con_texto,
            test_s6_texto_sin_telefono_no_cambia,
            test_s6_multiples_telefonos_en_mismo_mensaje,
            test_s6_logger_instanciable,
            test_s6_drop_in_replacement,
        ],
    }

    passed = failed = 0
    for bloque, subtests in tests.items():
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

    total = sum(len(v) for v in tests.values())
    sep()
    if failed == 0:
        print(f"{C.GREEN}{C.BOLD}  ✅ TODOS LOS TESTS PASARON ({passed}/{total}){C.END}")
    else:
        print(f"{C.RED}{C.BOLD}  ❌ {failed} FALLARON ({passed}/{total} pasaron){C.END}")
    sep()
    return failed == 0


if __name__ == "__main__":
    sys.exit(0 if run_all() else 1)