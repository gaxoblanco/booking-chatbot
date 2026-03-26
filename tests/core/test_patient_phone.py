#!/usr/bin/env python3
"""
Test: Issue 8 — patient_phone para cancelación por el paciente
==============================================================

Verifica que:
    1. La columna patient_phone existe en appointments
    2. create_appointment() acepta y guarda patient_phone
    3. El dueño (client_phone) puede cancelar — flujo feliz sin cambios
    4. El paciente (patient_phone) puede cancelar su propio turno
    5. Un número ajeno NO puede cancelar aunque conozca el id del turno
    6. Turno sin patient_phone → solo client_phone puede cancelar

Uso:
    docker exec -it whatsapp-demo python tests/test_issue8_patient_phone.py
"""

import sys
from pathlib import Path
from datetime import date, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.database import db
from src.services.client_service import client_service

# ── Colores ──────────────────────────────────────────────────────────────────
class C:
    GREEN = '\033[92m'; RED = '\033[91m'; CYAN = '\033[96m'
    BOLD  = '\033[1m';  END = '\033[0m'

def ok(t):   print(f"  {C.GREEN}✅ {t}{C.END}")
def fail(t): print(f"  {C.RED}❌ {t}{C.END}")
def info(t): print(f"  ℹ️  {t}")
def sep():   print("=" * 60)

# ── Datos fijos ───────────────────────────────────────────────────────────────
BOOKER    = "+5490000044001"   # Quien agenda (client_phone)
PATIENT   = "+5490000044002"   # El paciente real (patient_phone)
STRANGER  = "+5490000044003"   # Tercero sin relación con el turno
PROF      = "+5490000044004"
BASE_DATE = date(2099, 12, 1)

# ── Contador para slots únicos ────────────────────────────────────────────────
_counter = 0

def _next_date():
    global _counter
    _counter += 1
    return (BASE_DATE + timedelta(days=_counter)).strftime("%Y-%m-%d")

# ── Setup / Teardown ──────────────────────────────────────────────────────────
def _cleanup():
    global _counter
    _counter = 0
    with db.get_connection() as conn:
        for phone in (BOOKER, PATIENT, STRANGER):
            conn.execute("DELETE FROM appointments WHERE client_phone = ?", (phone,))
            conn.execute("DELETE FROM clients WHERE phone = ?", (phone,))
        # También limpiar por patient_phone
        conn.execute("DELETE FROM appointments WHERE patient_phone IN (?, ?, ?)",
                     (BOOKER, PATIENT, STRANGER))
        conn.execute("DELETE FROM professionals WHERE phone = ?", (PROF,))

def _ensure():
    with db.get_connection() as conn:
        for phone, name in [
            (BOOKER,   "Quien Agenda"),
            (PATIENT,  "El Paciente"),
            (STRANGER, "Desconocido"),
        ]:
            conn.execute(
                "INSERT OR IGNORE INTO clients (phone, name) VALUES (?, ?)",
                (phone, name)
            )
        conn.execute(
            "INSERT OR IGNORE INTO professionals (phone, name, is_active) VALUES (?, ?, 1)",
            (PROF, "Prof Test")
        )

def _create_apt(client_phone=BOOKER, patient_phone=None, status='confirmada') -> int:
    """Crea una cita con slot único. Retorna el appointment_id."""
    d = _next_date()
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO appointments
                (client_phone, professional_phone, appointment_date,
                 start, end, duration_minutes, status, patient_phone)
            VALUES (?, ?, ?, '10:00', '11:00', 50, ?, ?)
        """, (client_phone, PROF, d, status, patient_phone))
        return cur.lastrowid

# ── Tests ─────────────────────────────────────────────────────────────────────

def test_columna_patient_phone_existe():
    """La columna patient_phone debe existir en la tabla appointments."""
    apt_id = _create_apt()
    with db.get_connection() as conn:
        row = conn.execute(
            "SELECT patient_phone FROM appointments WHERE id = ?", (apt_id,)
        ).fetchone()
    assert row is not None, "Columna patient_phone no encontrada en appointments"
    ok("Columna patient_phone existe en appointments")


def test_create_appointment_guarda_patient_phone():
    """db.create_appointment() debe persistir patient_phone en BD."""
    d = _next_date()
    apt_id = db.create_appointment(
        client_phone      = BOOKER,
        professional_phone= PROF,
        appointment_date  = d,
        start             = '14:00',
        end               = '15:00',
        duration_minutes  = 50,
        patient_phone     = PATIENT,
    )
    assert apt_id is not None, "create_appointment retornó None"

    apt = db.get_appointment(apt_id)
    assert apt is not None
    assert apt.get('patient_phone') == PATIENT, (
        f"Esperado patient_phone={PATIENT}, obtenido {apt.get('patient_phone')}"
    )
    ok(f"create_appointment guarda patient_phone correctamente")


def test_create_appointment_sin_patient_phone():
    """Sin patient_phone el campo queda NULL — retrocompatibilidad."""
    d = _next_date()
    apt_id = db.create_appointment(
        client_phone      = BOOKER,
        professional_phone= PROF,
        appointment_date  = d,
        start             = '15:00',
        end               = '16:00',
        duration_minutes  = 50,
        # patient_phone no se pasa
    )
    apt = db.get_appointment(apt_id)
    assert apt.get('patient_phone') is None, (
        f"patient_phone debería ser NULL, obtenido {apt.get('patient_phone')}"
    )
    ok("Sin patient_phone el campo queda NULL (retrocompatible)")


def test_owner_puede_cancelar_turno_propio():
    """El dueño (client_phone) puede cancelar — flujo feliz sin cambios."""
    apt_id = _create_apt(client_phone=BOOKER, patient_phone=None)
    result = client_service.cancel_appointment(
        appointment_id = apt_id,
        phone_number   = BOOKER,
        reason         = 'Test owner cancela'
    )
    assert result is True, f"El dueño debería poder cancelar, obtenido {result}"
    apt = db.get_appointment(apt_id)
    assert apt['status'] == 'cancelada_cliente'
    ok("El dueño (client_phone) puede cancelar su turno")


def test_patient_puede_cancelar_su_turno():
    """El paciente (patient_phone) puede cancelar el turno agendado para él."""
    apt_id = _create_apt(client_phone=BOOKER, patient_phone=PATIENT)

    result = client_service.cancel_appointment(
        appointment_id = apt_id,
        phone_number   = PATIENT,   # ← el paciente, no quien agendó
        reason         = 'Test paciente cancela'
    )
    assert result is True, (
        f"El paciente debería poder cancelar su propio turno, obtenido {result}"
    )
    apt = db.get_appointment(apt_id)
    assert apt['status'] == 'cancelada_cliente', (
        f"Status esperado 'cancelada_cliente', obtenido {apt['status']}"
    )
    ok("El paciente (patient_phone) puede cancelar su propio turno")


def test_stranger_no_puede_cancelar():
    """Un número ajeno no puede cancelar aunque conozca el appointment_id."""
    apt_id = _create_apt(client_phone=BOOKER, patient_phone=PATIENT)

    result = client_service.cancel_appointment(
        appointment_id = apt_id,
        phone_number   = STRANGER,   # ← ni dueño ni paciente
        reason         = 'Intento no autorizado'
    )
    assert result is False, (
        f"Un extraño NO debería poder cancelar, obtenido {result}"
    )
    apt = db.get_appointment(apt_id)
    assert 'cancelada' not in apt['status'], (
        f"El turno no debería estar cancelado, status: {apt['status']}"
    )
    ok("Un número ajeno NO puede cancelar el turno")


def test_sin_patient_phone_solo_owner_cancela():
    """Turno sin patient_phone: solo client_phone puede cancelar."""
    apt_id = _create_apt(client_phone=BOOKER, patient_phone=None)

    # Stranger intenta cancelar → debe fallar
    result_stranger = client_service.cancel_appointment(
        appointment_id = apt_id,
        phone_number   = STRANGER,
    )
    assert result_stranger is False

    # Dueño cancela → debe funcionar
    result_owner = client_service.cancel_appointment(
        appointment_id = apt_id,
        phone_number   = BOOKER,
    )
    assert result_owner is True
    ok("Sin patient_phone: solo el dueño puede cancelar")


def test_booker_sigue_pudiendo_cancelar_turno_de_tercero():
    """
    Incluso con patient_phone registrado, quien agendó (BOOKER)
    sigue pudiendo cancelar — el cambio es aditivo, no restrictivo.
    """
    apt_id = _create_apt(client_phone=BOOKER, patient_phone=PATIENT)

    result = client_service.cancel_appointment(
        appointment_id = apt_id,
        phone_number   = BOOKER,   # ← quien agendó, aunque hay patient_phone
        reason         = 'Test booker cancela turno de tercero'
    )
    assert result is True, (
        f"El booker debería poder cancelar aunque haya patient_phone, obtenido {result}"
    )
    ok("Quien agendó (booker) sigue pudiendo cancelar aunque haya patient_phone")


# ── Runner ────────────────────────────────────────────────────────────────────

def run_all():
    sep()
    print(f"{C.BOLD}  TEST ISSUE 8 — patient_phone para cancelación{C.END}")
    sep()

    _cleanup()
    _ensure()

    tests = [
        test_columna_patient_phone_existe,
        test_create_appointment_guarda_patient_phone,
        test_create_appointment_sin_patient_phone,
        test_owner_puede_cancelar_turno_propio,
        test_patient_puede_cancelar_su_turno,
        test_stranger_no_puede_cancelar,
        test_sin_patient_phone_solo_owner_cancela,
        test_booker_sigue_pudiendo_cancelar_turno_de_tercero,
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

    _cleanup()
    sep()
    if failed == 0:
        print(f"{C.GREEN}{C.BOLD}  ✅ TODOS LOS TESTS PASARON ({passed}/{len(tests)}){C.END}")
    else:
        print(f"{C.RED}{C.BOLD}  ❌ {failed} FALLARON ({passed}/{len(tests)} pasaron){C.END}")
    sep()
    return failed == 0

def test_issue8_completo():
    assert run_all()

if __name__ == "__main__":
    sys.exit(0 if run_all() else 1)
