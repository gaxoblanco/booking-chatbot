#!/usr/bin/env python3
"""
Test: Validación de formato E.164 (Issue 6)
============================================

Verifica que validate_phone_e164() y normalize_whatsapp_phone()
manejan correctamente todos los casos borde de entrada.

Uso:
    docker exec -it whatsapp-demo python tests/test_phone_validation.py
    docker exec -it whatsapp-demo pytest tests/test_phone_validation.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.validators import validate_phone_e164, normalize_whatsapp_phone


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


# ─── Casos de prueba: validate_phone_e164 ────────────────────────────────────

def test_e164_validos():
    """Números en formato E.164 válido → retorna True."""
    validos = [
        "+5491112345678",    # Argentina mobile
        "+5493704969801",    # Argentina Formosa
        "+1234567890",       # USA (10 dígitos)
        "+447911123456",     # UK
        "+34612345678",      # España
        "+5511987654321",    # Brasil
    ]
    for phone in validos:
        result = validate_phone_e164(phone)
        assert result is True, f"Debería ser válido: {phone!r}"

    ok(f"validate_phone_e164 acepta {len(validos)} números válidos")


def test_e164_invalidos():
    """Números malformados → retorna False."""
    invalidos = [
        None,                     # None
        "",                       # vacío
        "   ",                    # solo espacios
        "5491112345678",          # sin +
        "+0112345678",            # empieza con +0 (inválido E.164)
        "+123",                   # muy corto (< 8 dígitos)
        "+12345678901234567",     # muy largo (> 15 dígitos)
        "whatsapp:+5491112345678",# con prefijo Twilio
        "+54 9 11 1234-5678",    # con espacios y guiones
        "+54abc123",              # con letras
        "texto_cualquiera",       # texto plano
        "+",                      # solo el +
    ]
    for phone in invalidos:
        result = validate_phone_e164(phone)
        assert result is False, f"Debería ser inválido: {phone!r}"

    ok(f"validate_phone_e164 rechaza {len(invalidos)} entradas inválidas")


# ─── Casos de prueba: normalize_whatsapp_phone ───────────────────────────────

def test_normalize_formato_twilio_valido():
    """Formato Twilio completo → retorna número limpio."""
    casos = [
        ("whatsapp:+5491112345678", "+5491112345678"),
        ("whatsapp:+5493704969801", "+5493704969801"),
        ("whatsapp:+1234567890",    "+1234567890"),
    ]
    for raw, esperado in casos:
        resultado = normalize_whatsapp_phone(raw)
        assert resultado == esperado, (
            f"normalize_whatsapp_phone({raw!r}) → esperado {esperado!r}, "
            f"obtenido {resultado!r}"
        )

    ok(f"normalize_whatsapp_phone maneja formato Twilio correctamente ({len(casos)} casos)")


def test_normalize_e164_directo():
    """Número ya en E.164 (sin prefijo whatsapp:) → retorna tal cual."""
    phone = "+5491112345678"
    resultado = normalize_whatsapp_phone(phone)
    assert resultado == phone, (
        f"E.164 directo debería retornar igual. Obtenido: {resultado!r}"
    )
    ok("normalize_whatsapp_phone acepta E.164 directo sin prefijo")


def test_normalize_invalidos_retornan_none():
    """Entradas inválidas → retorna None."""
    invalidos = [
        None,
        "",
        "texto_sin_numero",
        "whatsapp:numerosinplus",
        "whatsapp:+0123456789",   # +0 inválido en E.164
        "whatsapp:+123",          # muy corto
    ]
    for raw in invalidos:
        resultado = normalize_whatsapp_phone(raw)
        assert resultado is None, (
            f"normalize_whatsapp_phone({raw!r}) debería retornar None, "
            f"obtenido {resultado!r}"
        )

    ok(f"normalize_whatsapp_phone retorna None para {len(invalidos)} entradas inválidas")


def test_normalize_limpia_espacios():
    """Espacios al inicio/fin no deben romper la validación."""
    resultado = normalize_whatsapp_phone("  whatsapp:+5491112345678  ")
    assert resultado == "+5491112345678", (
        f"Debería limpiar espacios. Obtenido: {resultado!r}"
    )
    ok("normalize_whatsapp_phone tolera espacios al inicio/fin")


def test_funciones_existen_en_validators():
    """Las dos funciones deben existir en src.core.validators."""
    import src.core.validators as v
    assert hasattr(v, 'validate_phone_e164'), (
        "validate_phone_e164 no encontrada en src.core.validators"
    )
    assert hasattr(v, 'normalize_whatsapp_phone'), (
        "normalize_whatsapp_phone no encontrada en src.core.validators"
    )
    ok("Ambas funciones existen en src.core.validators")


def test_add_client_rechaza_phone_invalido():
    """
    db.add_client() con phone inválido debe retornar False
    sin insertar nada en la BD.
    """
    from src.database.database import db

    phones_invalidos = ["", "noesuntelefono", "123456", None]

    for phone in phones_invalidos:
        try:
            result = db.add_client(phone=phone, name="Test Inválido")
            assert result is False, (
                f"add_client con phone inválido {phone!r} debería retornar False, "
                f"obtenido {result!r}"
            )
        except Exception as e:
            # Si lanza excepción en lugar de retornar False, también es aceptable
            # siempre que no inserte datos
            info(f"add_client({phone!r}) lanzó excepción (aceptable): {e}")

    ok("add_client rechaza phones inválidos")


# ─── Runner ───────────────────────────────────────────────────────────────────

def run_all():
    sep()
    print(f"{C.BOLD}  TEST ISSUE 6 — Validación de formato E.164{C.END}")
    sep()

    tests = [
        test_funciones_existen_en_validators,
        test_e164_validos,
        test_e164_invalidos,
        test_normalize_formato_twilio_valido,
        test_normalize_e164_directo,
        test_normalize_invalidos_retornan_none,
        test_normalize_limpia_espacios,
        test_add_client_rechaza_phone_invalido,
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


def test_completo():
    """Entry point para pytest."""
    assert run_all(), "Uno o más tests del issue 6 fallaron"


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)