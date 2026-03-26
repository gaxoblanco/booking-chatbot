#!/usr/bin/env python3
"""
Test: Auditoría de aislamiento de datos de pacientes (Issue 5)
==============================================================

Verifica que ningún handler puede ver turnos de otro paciente,
y que la validación de ownership en cancelación funciona.

Escenarios:
    1. get_user_appointments() solo retorna turnos del número consultado
    2. cancel_appointment() rechaza cancelar turno de otro usuario
    3. get_appointment() sin ownership check — documentado como admin-scoped
    4. Validación de ownership en handle_client_cancel_appointment

Uso:
    docker exec -it whatsapp-demo python tests/test_data_isolation.py
    docker exec -it whatsapp-demo pytest tests/test_data_isolation.py -v
"""

import sys
from pathlib import Path
from datetime import date, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.database import db
from src.services.client_service import client_service


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

CLIENT_A  = "+5490000077001"   # Paciente A
CLIENT_B  = "+5490000077002"   # Paciente B (no debe ver turnos de A)
PROF_TEST = "+5490000077003"

BASE_DATE = date(2099, 9, 1)


# ─── Setup / Teardown ────────────────────────────────────────────────────────

def _cleanup():
    with db.get_connection() as conn:
        for phone in (CLIENT_A, CLIENT_B):
            conn.execute("DELETE FROM appointments WHERE client_phone = ?", (phone,))
            conn.execute("DELETE FROM clients WHERE phone = ?", (phone,))
        conn.execute("DELETE FROM professionals WHERE phone = ?", (PROF_TEST,))

def _ensure_entities():
    with db.get_connection() as conn:
        for phone, name in [(CLIENT_A, "Paciente A"), (CLIENT_B, "Paciente B")]:
            conn.execute(
                "INSERT OR IGNORE INTO clients (phone, name) VALUES (?, ?)",
                (phone, name)
            )
        conn.execute(
            "INSERT OR IGNORE INTO professionals (phone, name, is_active) VALUES (?, ?, 1)",
            (PROF_TEST, "Prof Test")
        )

def _create_appointment(client_phone: str, date_offset: int,
                        status: str = 'confirmada') -> int:
    apt_date = (BASE_DATE + timedelta(days=date_offset)).strftime("%Y-%m-%d")
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO appointments
                (client_phone, professional_phone, appointment_date,
                 start, end, duration_minutes, status)
            VALUES (?, ?, ?, '10:00', '11:00', 50, ?)
        """, (client_phone, PROF_TEST, apt_date, status))
        return cursor.lastrowid


# ─── Casos de prueba ─────────────────────────────────────────────────────────

def test_get_user_appointments_solo_retorna_turnos_propios():
    """
    get_user_appointments(CLIENT_A) no debe incluir turnos de CLIENT_B.
    """
    apt_a = _create_appointment(CLIENT_A, date_offset=0)
    apt_b = _create_appointment(CLIENT_B, date_offset=1)

    turnos_a = client_service.get_user_appointments(CLIENT_A)
    ids_a = [t['id'] for t in turnos_a]

    assert apt_a in ids_a, f"Turno #{apt_a} de A debería estar en el resultado"
    assert apt_b not in ids_a, (
        f"Turno #{apt_b} de B NO debería estar en el resultado de A"
    )
    ok(f"get_user_appointments(A) retorna solo turnos de A ({len(turnos_a)} turno/s)")

    turnos_b = client_service.get_user_appointments(CLIENT_B)
    ids_b = [t['id'] for t in turnos_b]

    assert apt_b in ids_b, f"Turno #{apt_b} de B debería estar en el resultado de B"
    assert apt_a not in ids_b, (
        f"Turno #{apt_a} de A NO debería estar en el resultado de B"
    )
    ok(f"get_user_appointments(B) retorna solo turnos de B ({len(turnos_b)} turno/s)")


def test_cancel_appointment_rechaza_turno_ajeno():
    """
    CLIENT_B no puede cancelar un turno que pertenece a CLIENT_A.
    cancel_appointment debe retornar False y no modificar el turno.
    """
    apt_id = _create_appointment(CLIENT_A, date_offset=5)

    # CLIENT_B intenta cancelar el turno de CLIENT_A
    result = client_service.cancel_appointment(
        appointment_id=apt_id,
        phone_number=CLIENT_B,  # ← teléfono incorrecto
        reason='Intento de cancelación no autorizado'
    )

    assert result is False, (
        f"cancel_appointment debería retornar False cuando el número no es el dueño"
    )

    # Verificar que el turno sigue activo
    apt = db.get_appointment(apt_id)
    assert apt is not None, "El turno no debería haberse eliminado"
    assert 'cancelada' not in apt['status'], (
        f"El turno no debería estar cancelado. Status: {apt['status']}"
    )
    ok("cancel_appointment rechaza cancelar turno ajeno → retorna False, turno intacto")


def test_cancel_appointment_acepta_turno_propio():
    """
    CLIENT_A sí puede cancelar su propio turno.
    Verifica que el flujo feliz funciona después del fix.
    """
    apt_id = _create_appointment(CLIENT_A, date_offset=10)

    result = client_service.cancel_appointment(
        appointment_id=apt_id,
        phone_number=CLIENT_A,  # ← teléfono correcto
        reason='Test de cancelación propia'
    )

    assert result is True, (
        f"cancel_appointment debería retornar True cuando el número es el dueño"
    )

    apt = db.get_appointment(apt_id)
    assert apt is not None
    assert apt['status'] == 'cancelada_cliente', (
        f"El turno debería estar cancelado. Status: {apt['status']}"
    )
    ok("cancel_appointment acepta cancelar turno propio → retorna True, turno cancelado")


def test_get_appointment_admin_scoped_documentado():
    """
    get_appointment(id) no filtra por cliente — es admin-scoped.
    Verificar que el docstring menciona esto explícitamente.
    """
    import inspect
    docstring = inspect.getdoc(db.get_appointment)

    assert docstring is not None, "get_appointment debe tener docstring"

    # Verificar que el docstring menciona el scope admin o la necesidad de verificar ownership
    keywords = ['admin', 'scope', 'ownership', 'client_phone', 'SCOPE']
    has_scope_doc = any(kw.lower() in docstring.lower() for kw in keywords)

    assert has_scope_doc, (
        f"El docstring de get_appointment debe mencionar que es admin-scoped "
        f"o la necesidad de verificar ownership.\n"
        f"Docstring actual:\n{docstring}"
    )
    ok("get_appointment tiene docstring con advertencia de scope")


def test_get_appointments_by_client_siempre_filtra():
    """
    get_appointments_by_client(phone) siempre tiene WHERE client_phone = ?
    Verifica que el método no puede retornar turnos de otro cliente
    aunque se llame con un phone que tenga 0 turnos.
    """
    # Crear 3 turnos de A, 0 de B
    for i in range(3):
        _create_appointment(CLIENT_A, date_offset=20 + i)

    # B no tiene turnos — debe retornar lista vacía, no los de A
    turnos_b = db.get_appointments_by_client(CLIENT_B)
    for t in turnos_b:
        assert t['client_phone'] == CLIENT_B, (
            f"get_appointments_by_client(B) retornó un turno de {t['client_phone']}"
        )

    ok(f"get_appointments_by_client siempre filtra correctamente "
       f"(B tiene {len(turnos_b)} turnos)")


def test_no_hay_query_sin_filtro_client_en_servicios_cliente():
    """
    Verifica que client_service.get_user_appointments pasa el phone
    como parámetro a la query y no hace SELECT * sin WHERE.
    """
    import inspect
    source = inspect.getsource(client_service.get_user_appointments)

    # Verificar que el método usa phone_number como filtro
    assert 'phone_number' in source or 'client_phone' in source, (
        "get_user_appointments debe filtrar por phone"
    )
    # Verificar que no hay SELECT sin WHERE (pattern peligroso)
    assert 'SELECT' not in source or 'WHERE' in source, (
        "get_user_appointments no debe hacer SELECT sin WHERE"
    )
    ok("get_user_appointments tiene filtro por phone en la query")


# ─── Runner ───────────────────────────────────────────────────────────────────

def run_all():
    sep()
    print(f"{C.BOLD}  TEST ISSUE 5 — Aislamiento de datos de pacientes{C.END}")
    sep()

    _cleanup()
    _ensure_entities()

    tests = [
        test_get_user_appointments_solo_retorna_turnos_propios,
        test_cancel_appointment_rechaza_turno_ajeno,
        test_cancel_appointment_acepta_turno_propio,
        test_get_appointment_admin_scoped_documentado,
        test_get_appointments_by_client_siempre_filtra,
        test_no_hay_query_sin_filtro_client_en_servicios_cliente,
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


def test_completo():
    """Entry point para pytest."""
    assert run_all(), "Uno o más tests del issue 5 fallaron"


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
