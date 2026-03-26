#!/usr/bin/env python3
"""
Test: Límite global de turnos activos por número de teléfono (Issue 2)
=======================================================================

Verifica que count_active_appointments_for_client() retorna el conteo
correcto considerando turnos con TODOS los profesionales del sistema.

Uso:
    docker exec -it whatsapp-demo python tests/test_issue2_global_booking_limit.py
    docker exec -it whatsapp-demo pytest tests/test_issue2_global_booking_limit.py -v
"""

import sys
from pathlib import Path
from datetime import date, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.database import db
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


# ─── Datos de prueba ─────────────────────────────────────────────────────────

CLIENT_TEST = "+5490000099010"   # Exclusivo de este test
PROF_A      = "+5490000099011"   # Profesional A
PROF_B      = "+5490000099012"   # Profesional B
PROF_C      = "+5490000099013"   # Profesional C

BASE_DATE   = date(2099, 7, 1)   # Fecha futura para no afectar agenda real


# ─── Setup / Teardown ────────────────────────────────────────────────────────

def _cleanup():
    with db.get_connection() as conn:
        conn.execute(
            "DELETE FROM appointments WHERE client_phone = ?",
            (CLIENT_TEST,)
        )
        conn.execute(
            "DELETE FROM clients WHERE phone = ?",
            (CLIENT_TEST,)
        )

def _ensure_entities():
    """Crea cliente y profesionales de prueba si no existen."""
    with db.get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO clients (phone, name) VALUES (?, ?)",
            (CLIENT_TEST, "Cliente Test Issue2")
        )
        for phone in (PROF_A, PROF_B, PROF_C):
            conn.execute(
                "INSERT OR IGNORE INTO professionals (phone, name, is_active) VALUES (?, ?, 1)",
                (phone, f"Prof {phone[-4:]}")
            )

def _insert_appointment(prof_phone: str, date_offset: int, status: str) -> int:
    """Inserta un turno y retorna su ID."""
    apt_date = (BASE_DATE + timedelta(days=date_offset)).strftime("%Y-%m-%d")
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO appointments
                (client_phone, professional_phone, appointment_date,
                 start, end, duration_minutes, status)
            VALUES (?, ?, ?, '10:00', '11:00', 50, ?)
        """, (CLIENT_TEST, prof_phone, apt_date, status))
        return cursor.lastrowid


# ─── Casos de prueba ─────────────────────────────────────────────────────────

def test_sin_turnos_retorna_cero():
    """Sin turnos → debe retornar 0."""
    count = db.count_active_appointments_for_client(CLIENT_TEST)
    assert count == 0, f"Esperado 0, obtenido {count}"
    ok("Sin turnos → retorna 0")


def test_un_turno_un_profesional():
    """1 turno confirmado con Prof A → retorna 1."""
    _insert_appointment(PROF_A, date_offset=0, status="confirmada")

    count = db.count_active_appointments_for_client(CLIENT_TEST)
    assert count == 1, f"Esperado 1, obtenido {count}"
    ok("1 turno con Prof A → retorna 1")


def test_turnos_multiples_profesionales_se_suman():
    """
    1 turno con Prof A + 1 turno con Prof B → retorna 2.
    Verifica que el conteo es global (no por profesional).
    """
    _insert_appointment(PROF_B, date_offset=1, status="confirmada")

    count = db.count_active_appointments_for_client(CLIENT_TEST)
    assert count == 2, f"Esperado 2 (A+B), obtenido {count}"
    ok("1 turno Prof A + 1 turno Prof B → retorna 2")


def test_pendiente_confirmacion_cuenta():
    """Turno pendiente_confirmacion también cuenta como activo."""
    _insert_appointment(PROF_C, date_offset=2, status="pendiente_confirmacion")

    count = db.count_active_appointments_for_client(CLIENT_TEST)
    assert count == 3, f"Esperado 3 (A+B+C pendiente), obtenido {count}"
    ok("Turno pendiente_confirmacion cuenta como activo → retorna 3")


def test_cancelados_y_completados_no_cuentan():
    """
    Turnos cancelados o completados no deben contarse.
    Agrega 2 turnos inactivos → el conteo no debe cambiar.
    """
    _insert_appointment(PROF_A, date_offset=10, status="cancelada_cliente")
    _insert_appointment(PROF_B, date_offset=11, status="completada")

    count = db.count_active_appointments_for_client(CLIENT_TEST)
    assert count == 3, (
        f"Cancelados y completados no deben contar. "
        f"Esperado 3, obtenido {count}"
    )
    ok("Cancelados y completados no afectan el conteo → sigue siendo 3")


def test_limite_domain_config_existe():
    """
    Verifica que DomainConfig tiene MAX_ACTIVE_APPOINTMENTS_GLOBAL_PER_CLIENT
    definido y que es un entero positivo mayor al límite por profesional.
    """
    global_limit = getattr(
        DomainConfig, 'MAX_ACTIVE_APPOINTMENTS_GLOBAL_PER_CLIENT', None
    )
    per_prof_limit = getattr(
        DomainConfig, 'MAX_ACTIVE_APPOINTMENTS_PER_CLIENT_PER_PROFESSIONAL', None
    )

    assert global_limit is not None, (
        "DomainConfig no tiene MAX_ACTIVE_APPOINTMENTS_GLOBAL_PER_CLIENT"
    )
    assert isinstance(global_limit, int) and global_limit > 0, (
        f"El límite global debe ser un entero positivo, obtenido: {global_limit}"
    )
    assert per_prof_limit is not None, (
        "DomainConfig no tiene MAX_ACTIVE_APPOINTMENTS_PER_CLIENT_PER_PROFESSIONAL "
        "(debería estar del issue 1)"
    )
    assert global_limit >= per_prof_limit, (
        f"El límite global ({global_limit}) debería ser >= "
        f"al límite por profesional ({per_prof_limit})"
    )

    ok(f"MAX_ACTIVE_APPOINTMENTS_GLOBAL_PER_CLIENT = {global_limit}")
    ok(f"MAX_ACTIVE_APPOINTMENTS_PER_CLIENT_PER_PROFESSIONAL = {per_prof_limit}")
    info(f"Un cliente puede tener hasta {per_prof_limit} turnos por profesional "
         f"y {global_limit} en total")


# ─── Runner ───────────────────────────────────────────────────────────────────

def run_all():
    sep()
    print(f"{C.BOLD}  TEST ISSUE 2 — Límite global de turnos por número{C.END}")
    sep()

    _cleanup()
    _ensure_entities()

    tests = [
        test_limite_domain_config_existe,
        test_sin_turnos_retorna_cero,
        test_un_turno_un_profesional,
        test_turnos_multiples_profesionales_se_suman,
        test_pendiente_confirmacion_cuenta,
        test_cancelados_y_completados_no_cuentan,
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

    _cleanup()

    sep()
    if failed == 0:
        print(f"{C.GREEN}{C.BOLD}  ✅ TODOS LOS TESTS PASARON ({passed}/{len(tests)}){C.END}")
    else:
        print(f"{C.RED}{C.BOLD}  ❌ {failed} TEST(S) FALLARON ({passed}/{len(tests)} pasaron){C.END}")
    sep()

    return failed == 0


def test_issue2_completo():
    """Entry point para pytest."""
    assert run_all(), "Uno o más tests del issue 2 fallaron"


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
