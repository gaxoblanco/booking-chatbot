#!/usr/bin/env python3
"""
Test: GAP 9 — Manejo amigable de booking concurrente
=====================================================

Verifica que cuando dos usuarios intentan agendar el mismo slot:
    1. create_appointment() retorna -1 en lugar de None o excepción
    2. El mensaje al usuario es claro y sugiere buscar de nuevo
    3. La sesión queda limpia después del error concurrente
    4. El slot sí existe en BD (fue tomado por el primero)
    5. Errores genéricos siguen retornando None (sin regresión)

Uso:
    docker exec -it whatsapp-demo python tests/test_concurrent_booking.py
"""

import sys
from pathlib import Path
from datetime import date, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.database import db
from src.core.states import ConversationState, SessionData

# ── Colores ──────────────────────────────────────────────────────────────────
class C:
    GREEN = '\033[92m'; RED = '\033[91m'; CYAN = '\033[96m'
    BOLD  = '\033[1m';  END = '\033[0m'

def ok(t):   print(f"  {C.GREEN}✅ {t}{C.END}")
def fail(t): print(f"  {C.RED}❌ {t}{C.END}")
def info(t): print(f"  ℹ️  {t}")
def sep():   print("=" * 60)

# ── Datos de prueba ───────────────────────────────────────────────────────────
CLIENT_A  = "+5490000066001"
CLIENT_B  = "+5490000066002"
PROF      = "+5490000066003"
APT_DATE  = (date.today() + timedelta(days=10)).strftime("%Y-%m-%d")
APT_START = "10:00"
APT_END   = "10:50"

def _cleanup():
    with db.get_connection() as conn:
        conn.execute(
            "DELETE FROM appointments WHERE professional_phone = ? AND appointment_date = ?",
            (PROF, APT_DATE)
        )
        for phone in (CLIENT_A, CLIENT_B):
            conn.execute("DELETE FROM clients WHERE phone = ?", (phone,))
        conn.execute("DELETE FROM professionals WHERE phone = ?", (PROF,))

def _ensure():
    with db.get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO clients (phone, name) VALUES (?, ?)",
            (CLIENT_A, "Cliente A")
        )
        conn.execute(
            "INSERT OR IGNORE INTO clients (phone, name) VALUES (?, ?)",
            (CLIENT_B, "Cliente B")
        )
        conn.execute(
            "INSERT OR IGNORE INTO professionals (phone, name, is_active) VALUES (?, ?, 1)",
            (PROF, "Prof Test")
        )


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_primer_booking_exitoso():
    """El primer usuario en confirmar obtiene el slot — retorna appointment_id > 0."""
    apt_id = db.create_appointment(
        client_phone       = CLIENT_A,
        professional_phone = PROF,
        appointment_date   = APT_DATE,
        start              = APT_START,
        end                = APT_END,
        duration_minutes   = 50,
    )
    assert apt_id is not None, "create_appointment retornó None"
    assert apt_id != -1,       "create_appointment retornó -1 en el primer booking"
    assert apt_id > 0,         f"Se esperaba ID > 0, obtenido {apt_id}"
    info(f"Slot tomado por Cliente A → appointment_id={apt_id}")
    ok("Primer booking exitoso → retorna appointment_id positivo")


def test_segundo_booking_mismo_slot_retorna_menos_uno():
    """
    El segundo usuario que intenta el mismo slot obtiene -1.
    El slot ya fue tomado por Cliente A en el test anterior.
    """
    result = db.create_appointment(
        client_phone       = CLIENT_B,
        professional_phone = PROF,
        appointment_date   = APT_DATE,
        start              = APT_START,
        end                = APT_END,
        duration_minutes   = 50,
    )
    assert result == -1, (
        f"Slot concurrente debe retornar -1, obtenido {result}"
    )
    ok("Segundo booking del mismo slot → retorna -1 (slot tomado)")


def test_slot_tomado_solo_tiene_una_cita():
    """Después del conflicto, el slot tiene exactamente 1 cita en BD."""
    with db.get_connection() as conn:
        rows = conn.execute("""
            SELECT id, client_phone FROM appointments
            WHERE professional_phone = ?
              AND appointment_date   = ?
              AND start              = ?
              AND status NOT IN ('cancelada_cliente', 'cancelada_profesional')
        """, (PROF, APT_DATE, APT_START)).fetchall()

    assert len(rows) == 1, (
        f"Debe haber exactamente 1 cita en el slot, hay {len(rows)}"
    )
    assert dict(rows[0])['client_phone'] == CLIENT_A, (
        "La cita debe pertenecer al primer usuario (Cliente A)"
    )
    ok("El slot tiene exactamente 1 cita — sin duplicados")


def test_error_generico_sigue_retornando_none():
    """
    Un error genérico (no UNIQUE constraint) sigue retornando None.
    Forzamos un error pasando una fecha con formato inválido que
    rompe el CHECK constraint de la BD.
    """
    # Insertar una cita con date inválida via SQL directo para
    # forzar un error que NO sea UNIQUE constraint
    import sqlite3
    from unittest.mock import patch

    # Mockear get_connection para que lance una excepción genérica
    original_get_connection = db.get_connection

    class FakeConn:
        def __enter__(self):
            raise sqlite3.OperationalError("disk I/O error simulado")
        def __exit__(self, *args):
            pass

    with patch.object(db, 'get_connection', return_value=FakeConn()):
        result = db.create_appointment(
            client_phone       = CLIENT_A,
            professional_phone = PROF,
            appointment_date   = APT_DATE,
            start              = "11:00",
            end                = "11:50",
            duration_minutes   = 50,
        )

    assert result is None, (
        f"Error genérico debe retornar None, obtenido {result}"
    )
    ok("Error genérico sigue retornando None (sin regresión)")


def test_handler_mensaje_slot_tomado():
    """
    Cuando create_appointment retorna -1, el handler devuelve
    un mensaje claro con sugerencia de buscar de nuevo.
    """
    from unittest.mock import patch, MagicMock
    from src.bot.client_handler import ClientHandler

    handler = ClientHandler()
    session = SessionData(CLIENT_B)
    session.set_temp('selected_professional', {
        'phone': PROF, 'name': 'Prof Test'
    })
    session.set_temp('booking_date',       APT_DATE)
    session.set_temp('booking_start_time', APT_START)
    session.set_temp('booking_end_time',   APT_END)
    session.transition_to(ConversationState.CLIENT_CONFIRM_BOOKING)

    # Mock: appointment_service retorna -1 (slot tomado)
    with patch(
        'src.services.appointment_service.appointment_service.create_appointment',
        return_value=-1
    ):
        response = handler.handle_client_confirm_booking(session, '1')

    assert response is not None
    assert (
        'tomado' in response.lower()
        or 'horario' in response.lower()
        or 'buscar' in response.lower()
    ), f"El mensaje debe mencionar el problema y sugerir buscar: {response}"

    # La sesión debe quedar limpia
    assert session.get_temp('booking_date') is None, \
        "temp_data debe limpiarse después del error concurrente"

    ok(f"Handler muestra mensaje amigable para slot tomado")
    info(f"Mensaje: {response[:80]}...")


def test_handler_sesion_limpia_tras_conflicto():
    """
    Después del error concurrente, la sesión vuelve a CLIENT_MAIN_MENU.
    El usuario puede empezar una nueva búsqueda sin reiniciar.
    """
    from unittest.mock import patch
    from src.bot.client_handler import ClientHandler

    handler = ClientHandler()
    session = SessionData(CLIENT_B)
    session.set_temp('selected_professional', {'phone': PROF, 'name': 'Prof'})
    session.set_temp('booking_date',       APT_DATE)
    session.set_temp('booking_start_time', APT_START)
    session.set_temp('booking_end_time',   APT_END)
    session.transition_to(ConversationState.CLIENT_CONFIRM_BOOKING)

    with patch(
        'src.services.appointment_service.appointment_service.create_appointment',
        return_value=-1
    ):
        handler.handle_client_confirm_booking(session, '1')

    assert session.state == ConversationState.CLIENT_MAIN_MENU, (
        f"Estado debe ser CLIENT_MAIN_MENU, es {session.state}"
    )
    ok("Sesión vuelve a CLIENT_MAIN_MENU después del conflicto")


# ── Runner ────────────────────────────────────────────────────────────────────

def run_all():
    sep()
    print(f"{C.BOLD}  TEST GAP 9 — Booking concurrente{C.END}")
    sep()

    _cleanup()
    _ensure()

    tests = [
        test_primer_booking_exitoso,
        test_segundo_booking_mismo_slot_retorna_menos_uno,
        test_slot_tomado_solo_tiene_una_cita,
        test_error_generico_sigue_retornando_none,
        test_handler_mensaje_slot_tomado,
        test_handler_sesion_limpia_tras_conflicto,
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

def test_completo():
    assert run_all()

if __name__ == "__main__":
    sys.exit(0 if run_all() else 1)