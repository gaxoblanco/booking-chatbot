#!/usr/bin/env python3
"""
Test: Issue 7 — Notificación al paciente cuando el profesional cancela desde Calendar
"""
import sys
from pathlib import Path
from datetime import date, timedelta, datetime, timezone
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.database import db
from src.services.cancellation_notifier import CancellationNotifier

# ── Colores ──────────────────────────────────────────────────────────────────
class C:
    GREEN = '\033[92m'; RED = '\033[91m'; CYAN = '\033[96m'
    BOLD  = '\033[1m';  END = '\033[0m'

def ok(t):   print(f"  {C.GREEN}✅ {t}{C.END}")
def fail(t): print(f"  {C.RED}❌ {t}{C.END}")
def info(t): print(f"  ℹ️  {t}")
def sep():   print("=" * 60)

# ── Datos fijos ───────────────────────────────────────────────────────────────
CLIENT    = "+5490000055001"
PROF      = "+5490000055002"
BASE_DATE = date(2099, 11, 1)

# ── Contador global — slot único por test ─────────────────────────────────────
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
        conn.execute("DELETE FROM appointments     WHERE client_phone = ?",       (CLIENT,))
        conn.execute("DELETE FROM calendar_watches WHERE professional_phone = ?", (PROF,))
        conn.execute("DELETE FROM clients          WHERE phone = ?",              (CLIENT,))
        conn.execute("DELETE FROM professionals    WHERE phone = ?",              (PROF,))

def _ensure():
    with db.get_connection() as conn:
        conn.execute("INSERT OR IGNORE INTO clients (phone, name) VALUES (?, ?)",
                     (CLIENT, "Paciente Test"))
        conn.execute("INSERT OR IGNORE INTO professionals "
                     "(phone, name, is_active, calendar_id) VALUES (?, ?, 1, ?)",
                     (PROF, "Dr. Test", "dr.test@gmail.com"))

def _apt(status='confirmada', notified=False, evt_id=None):
    """Crea una cita con fecha única garantizada."""
    d    = _next_date()
    eid  = evt_id or f"evt_{d}"
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO appointments
                (client_phone, professional_phone, appointment_date,
                 start, end, duration_minutes, status,
                 google_event_id, cancellation_notified)
            VALUES (?, ?, ?, '10:00', '11:00', 50, ?, ?, ?)
        """, (CLIENT, PROF, d, status, eid, 1 if notified else 0))
        return cur.lastrowid

def _watch(channel_id, token, status='active'):
    expires = (datetime.now(timezone.utc) + timedelta(days=6)).isoformat()
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO calendar_watches
                (professional_phone, calendar_id, channel_id,
                 resource_id, channel_token, expires_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (PROF, "dr.test@gmail.com", channel_id, "res_abc", token, expires, status))
        return cur.lastrowid

# ── Tests Bloque A: WatchManager ─────────────────────────────────────────────

def test_tabla_calendar_watches_existe():
    with db.get_connection() as conn:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='calendar_watches'"
        ).fetchone()
    assert row is not None, "Tabla calendar_watches no existe"
    ok("Tabla calendar_watches existe en BD")

def test_columna_cancellation_notified_existe():
    apt_id = _apt()
    with db.get_connection() as conn:
        row = conn.execute(
            "SELECT cancellation_notified FROM appointments WHERE id = ?", (apt_id,)
        ).fetchone()
    assert row is not None
    ok("Columna cancellation_notified existe en appointments")

def test_validate_token_valido():
    from src.integrations.google_calendar_service.watch_manager import WatchManager
    ch_id = "ch-valid-001"
    token = "token_valido_001"
    _watch(ch_id, token)
    wm = WatchManager(MagicMock(), db, "https://test.example.com")
    result = wm.validate_notification_token(ch_id, token)
    assert result == PROF, f"Esperado {PROF}, obtenido {result}"
    ok("validate_notification_token retorna professional con token válido")

def test_validate_token_invalido():
    from src.integrations.google_calendar_service.watch_manager import WatchManager
    ch_id = "ch-invalid-002"
    _watch(ch_id, "token_real")
    wm = WatchManager(MagicMock(), db, "https://test.example.com")
    result = wm.validate_notification_token(ch_id, "token_INCORRECTO")
    assert result is None
    ok("validate_notification_token retorna None con token incorrecto")

def test_get_professional_by_channel():
    from src.integrations.google_calendar_service.watch_manager import WatchManager
    ch_id = "ch-by-prof-003"
    _watch(ch_id, "token003")
    wm = WatchManager(MagicMock(), db, "https://test.example.com")
    assert wm.get_professional_by_channel(ch_id) == PROF
    ok("get_professional_by_channel retorna professional correcto")

# ── Tests Bloque B: CancellationNotifier ─────────────────────────────────────

def test_skip_si_ya_notificada():
    apt_id = _apt(status='cancelada_profesional', notified=True)
    n = CancellationNotifier()
    r = n.notify_patient(apt_id)
    assert r['action'] == 'already_notified', f"Obtenido: {r}"
    ok("skip si cancellation_notified=1")

def test_skip_si_status_incorrecto():
    apt_id = _apt(status='confirmada', notified=False)
    n = CancellationNotifier()
    r = n.notify_patient(apt_id)
    assert r['success'] is False and r['action'] == 'error'
    ok("skip si status != cancelada_profesional")

def test_marca_notified_tras_envio():
    apt_id = _apt(status='cancelada_profesional', notified=False)
    n = CancellationNotifier()
    with patch.object(n, '_send_whatsapp', return_value=True), \
         patch.object(n, '_find_next_slot', return_value=None):
        r = n.notify_patient(apt_id)
    assert r['success'] is True, f"Obtenido: {r}"
    updated = db.get_appointment(apt_id)
    assert updated['cancellation_notified'] == 1
    ok("marca cancellation_notified=1 tras envío exitoso")

def test_no_doble_envio():
    apt_id  = _apt(status='cancelada_profesional', notified=False)
    n       = CancellationNotifier()
    envios  = 0

    def mock_send(phone, msg):
        nonlocal envios
        envios += 1
        return True

    with patch.object(n, '_send_whatsapp', side_effect=mock_send), \
         patch.object(n, '_find_next_slot', return_value=None):
        n.notify_patient(apt_id)
        r2 = n.notify_patient(apt_id)

    assert envios == 1, f"Se esperaba 1 envío, se hicieron {envios}"
    assert r2['action'] == 'already_notified'
    ok("no doble envío — segundo intento es already_notified")

def test_formato_mensaje_con_slot():
    n = CancellationNotifier()
    apt_mock  = {'professional_name': 'Dra. García', 'appointment_date': '2099-11-05',
                 'start': '10:00', 'client_name': 'Juan Pérez', 'client_phone': CLIENT}
    next_slot = {'date': '2099-11-07', 'start': '11:00', 'end': '12:00'}
    msg = n._format_message(apt_mock, next_slot)
    assert '1️⃣' in msg and '2️⃣' in msg
    assert 'Dra. García' in msg
    ok("mensaje con next_slot incluye opciones de reagendado")

def test_formato_mensaje_sin_slot():
    n = CancellationNotifier()
    apt_mock = {'professional_name': 'Dr. López', 'appointment_date': '2099-11-05',
                'start': '14:00', 'client_name': '', 'client_phone': CLIENT}
    msg = n._format_message(apt_mock, next_slot=None)
    assert 'buscar' in msg.lower() or 'disponib' in msg.lower()
    ok("mensaje sin slot invita a consultar disponibilidad")

# ── Test Bloque C: Integración ────────────────────────────────────────────────

def test_flujo_completo():
    apt_id = _apt(status='confirmada', notified=False, evt_id='evt_flujo_completo')

    # Simular que sync detectó la cancelación
    with db.get_connection() as conn:
        conn.execute(
            "UPDATE appointments SET status='cancelada_profesional' WHERE id=?", (apt_id,)
        )

    apt_intermedio = db.get_appointment(apt_id)
    assert apt_intermedio['status'] == 'cancelada_profesional'
    assert apt_intermedio['cancellation_notified'] == 0

    n = CancellationNotifier()
    with patch.object(n, '_send_whatsapp', return_value=True), \
         patch.object(n, '_find_next_slot', return_value={
             'date': '2099-11-10', 'start': '09:00', 'end': '10:00'}):
        r = n.notify_patient(apt_id)

    assert r['success'] is True, f"Falló: {r}"
    assert r['action']  == 'notified'
    assert db.get_appointment(apt_id)['cancellation_notified'] == 1
    ok("flujo completo: sync → notificación → marca en BD ✓")

# ── Runner ────────────────────────────────────────────────────────────────────

def run_all():
    sep()
    print(f"{C.BOLD}  TEST ISSUE 7 — Notificación cancelación desde Calendar{C.END}")
    sep()

    _cleanup()
    _ensure()

    tests = [
        test_tabla_calendar_watches_existe,
        test_columna_cancellation_notified_existe,
        test_validate_token_valido,
        test_validate_token_invalido,
        test_get_professional_by_channel,
        test_skip_si_ya_notificada,
        test_skip_si_status_incorrecto,
        test_marca_notified_tras_envio,
        test_no_doble_envio,
        test_formato_mensaje_con_slot,
        test_formato_mensaje_sin_slot,
        test_flujo_completo,
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