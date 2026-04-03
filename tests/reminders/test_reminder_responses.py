#!/usr/bin/env python3
"""
Test de integración: Respuestas del cliente al recordatorio
============================================================

Simula el flujo completo via webhook real:

    1. Recordatorio enviado → appointment_reminders.status = 'sent'
    2. Cliente responde desde WhatsApp
    3. Bot procesa la respuesta vía reminder_handler
    4. BD actualizada según la acción

Escenarios:
    F. Cliente responde "1" (confirmar) → confirmed_by_client=1
    G. Cliente responde "2" (reprogramar) → estado CLIENT_RESCHEDULE_*
    H. Cliente responde "0" (cancelar) → flujo de cancelación
    I. Respuesta inválida → mensaje de error, sin cambios en BD

Uso:
    docker exec whatsapp-demo python tests/reminders/test_reminder_responses.py
    docker exec whatsapp-demo python tests/reminders/test_reminder_responses.py -v
"""

import sys
import re
import requests
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.database.database import db

# ── Config ────────────────────────────────────────────────────────────────────

WEBHOOK_URL   = "http://localhost:5000/webhook"
CLIENT_PHONE  = "+5499999000002"   # número ficticio distinto al de test_A-D
PROF_PHONE    = "+5491100000001"
VERBOSE       = "-v" in sys.argv


# ── Colores ───────────────────────────────────────────────────────────────────
class C:
    GREEN  = '\033[92m'; RED    = '\033[91m'
    CYAN   = '\033[96m'; YELLOW = '\033[93m'
    BOLD   = '\033[1m';  DIM    = '\033[2m'
    END    = '\033[0m'

def ok(t):   print(f"  {C.GREEN}OK {t}{C.END}")
def fail(t): print(f"  {C.RED}FAIL {t}{C.END}")
def info(t): print(f"  {C.DIM}... {t}{C.END}")
def warn(t): print(f"  {C.YELLOW}WARN {t}{C.END}")
def sep():   print("=" * 62)
def header(t): sep(); print(f"{C.BOLD}{C.CYAN}  {t}{C.END}"); sep()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _create_test_appointment(days_ahead=2) -> int:
    """Crea cita de prueba. days_ahead=2 para pasar el filtro de mañana."""
    target_date = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    with db.get_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO appointments
                (client_phone, professional_phone, appointment_date,
                 start, end, status, reminder_sent)
            VALUES (?, ?, ?, '10:00', '10:50', 'confirmada', 1)
        """, (CLIENT_PHONE, PROF_PHONE, target_date))
        apt_id = cursor.lastrowid
    if VERBOSE:
        info(f"Cita #{apt_id}: {CLIENT_PHONE} -> {target_date} 10:00")
    return apt_id


def _create_reminder_record(apt_id: int) -> int:
    """Inserta registro en appointment_reminders con status='sent'."""
    with db.get_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO appointment_reminders
                (appointment_id, client_phone, professional_phone,
                 appointment_date, appointment_time, status, sent_at)
            SELECT id, client_phone, professional_phone,
                   appointment_date, start, 'sent', CURRENT_TIMESTAMP
            FROM appointments WHERE id = ?
        """, (apt_id,))
        reminder_id = cursor.lastrowid
    if VERBOSE:
        info(f"Reminder #{reminder_id} insertado para cita #{apt_id} (status=sent)")
    return reminder_id


def _get_appointment(apt_id: int) -> dict:
    with db.get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM appointments WHERE id = ?", (apt_id,)
        ).fetchone()
    return dict(row) if row else {}


def _get_reminder(apt_id: int) -> dict:
    with db.get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM appointment_reminders WHERE appointment_id = ? ORDER BY id DESC LIMIT 1",
            (apt_id,)
        ).fetchone()
    return dict(row) if row else {}


def _get_session_state(phone: str) -> str:
    """Obtiene el estado de sesión desde Redis."""
    try:
        from src.core.states import SessionManager
        from src.core.session_backends import RedisSessionBackend
        import os
        backend = RedisSessionBackend(os.getenv('REDIS_URL', 'redis://redis:6379/0'))
        session = backend.get(phone)
        if session:
            return session.get('state', 'unknown')
        return 'no_session'
    except Exception as e:
        if VERBOSE:
            info(f"No se pudo leer sesión: {e}")
        return 'error'


def _cleanup(apt_id: int = None):
    with db.get_connection() as conn:
        if apt_id:
            conn.execute(
                "DELETE FROM appointment_reminders WHERE appointment_id = ?", (apt_id,)
            )
            conn.execute("DELETE FROM appointments WHERE id = ?", (apt_id,))
        conn.execute(
            "DELETE FROM appointment_reminders WHERE client_phone = ?", (CLIENT_PHONE,)
        )
        conn.execute(
            "DELETE FROM appointments WHERE client_phone = ?", (CLIENT_PHONE,)
        )
        # Limpiar sesión Redis
        try:
            import redis, os
            r = redis.from_url(os.getenv('REDIS_URL', 'redis://redis:6379/0'))
            r.delete(f"session:{CLIENT_PHONE}")
        except Exception:
            pass


def _send_whatsapp(text: str) -> dict:
    """Simula un mensaje WhatsApp entrante del cliente."""
    payload = {
        "From":     f"whatsapp:{CLIENT_PHONE}",
        "To":       "whatsapp:+5493705217649",
        "Body":     text,
        "NumMedia": "0",
    }
    resp = requests.post(WEBHOOK_URL, data=payload, timeout=15)
    resp.raise_for_status()
    match = re.search(r'<Message>(.*?)</Message>', resp.text, re.DOTALL)
    text_resp = match.group(1).strip() if match else resp.text
    if VERBOSE:
        info(f"Bot respondio: {text_resp[:120]}")
    return {"text": text_resp, "status_code": resp.status_code}


# ── Escenario F: "1" → confirmar ─────────────────────────────────────────────

def test_F_respuesta_1_confirma():
    """
    Cliente recibe recordatorio y responde "1" (confirmo asistencia).
    Esperado:
      - appointment_reminders.status = 'confirmed'
      - appointments.confirmed_by_client = 1
      - Mensaje de confirmación en respuesta
    """
    header("ESCENARIO F - Respuesta '1' -> confirmar asistencia")
    apt_id = _create_test_appointment()
    _create_reminder_record(apt_id)

    try:
        resp = _send_whatsapp("1")

        info(f"Respuesta bot: {resp['text'][:80]}")

        # Verificar mensaje de confirmación
        assert any(w in resp['text'].lower() for w in ['confirm', 'perfecto', 'turno', 'gracias']), (
            f"Respuesta no indica confirmacion: '{resp['text']}'"
        )
        ok("Bot responde con mensaje de confirmacion")

        # Verificar BD
        reminder = _get_reminder(apt_id)
        assert reminder.get('status') == 'confirmed', (
            f"reminder.status deberia ser 'confirmed', es '{reminder.get('status')}'"
        )
        ok("appointment_reminders.status = 'confirmed'")

        apt = _get_appointment(apt_id)
        assert apt.get('confirmed_by_client') == 1, (
            f"confirmed_by_client deberia ser 1, es {apt.get('confirmed_by_client')}"
        )
        ok("appointments.confirmed_by_client = 1")

    finally:
        _cleanup(apt_id)


# ── Escenario G: "2" → reprogramar ───────────────────────────────────────────

def test_G_respuesta_2_reprogramar():
    """
    Cliente responde "2" (necesito reprogramar).
    Esperado:
      - appointment_reminders.status = 'rescheduled'
      - Bot responde iniciando flujo de reprogramación
      - Sesión en estado CLIENT_RESCHEDULE_* o similar
    """
    header("ESCENARIO G - Respuesta '2' -> reprogramar")
    apt_id = _create_test_appointment()
    _create_reminder_record(apt_id)

    try:
        resp = _send_whatsapp("2")

        info(f"Respuesta bot: {resp['text'][:80]}")

        # Verificar que el bot inicia reprogramación
        assert any(w in resp['text'].lower() for w in
                   ['reprogramar', 'fecha', 'cuando', 'programar', 'horario']), (
            f"Respuesta no indica inicio de reprogramacion: '{resp['text']}'"
        )
        ok("Bot inicia flujo de reprogramacion")

        # Verificar BD
        reminder = _get_reminder(apt_id)
        assert reminder.get('status') == 'rescheduled', (
            f"reminder.status deberia ser 'rescheduled', es '{reminder.get('status')}'"
        )
        ok("appointment_reminders.status = 'rescheduled'")

    finally:
        _cleanup(apt_id)


# ── Escenario H: "0" → cancelar ──────────────────────────────────────────────

def test_H_respuesta_0_cancelar():
    """
    Cliente responde "0" (cancelar turno).
    Esperado:
      - appointment_reminders.status = 'cancelled'
      - Bot responde iniciando flujo de cancelación (pide confirmación)
    """
    header("ESCENARIO H - Respuesta '0' -> cancelar turno")
    apt_id = _create_test_appointment()
    _create_reminder_record(apt_id)

    try:
        resp = _send_whatsapp("0")

        info(f"Respuesta bot: {resp['text'][:80]}")

        # El bot pide confirmación antes de cancelar
        assert any(w in resp['text'].lower() for w in
                   ['cancel', 'segur', 'confirm', 'turno']), (
            f"Respuesta no indica inicio de cancelacion: '{resp['text']}'"
        )
        ok("Bot inicia flujo de cancelacion")

        # Verificar BD
        reminder = _get_reminder(apt_id)
        assert reminder.get('status') == 'cancelled', (
            f"reminder.status deberia ser 'cancelled', es '{reminder.get('status')}'"
        )
        ok("appointment_reminders.status = 'cancelled'")

    finally:
        _cleanup(apt_id)


# ── Escenario I: Respuesta inválida ──────────────────────────────────────────

def test_I_respuesta_invalida():
    """
    Cliente responde texto libre que no es 1/2/0.
    Esperado:
      - reminder.status sigue en 'sent'
      - Bot responde con mensaje de opciones válidas o menú
    """
    header("ESCENARIO I - Respuesta invalida -> sin cambios")
    apt_id = _create_test_appointment()
    _create_reminder_record(apt_id)

    try:
        resp = _send_whatsapp("gracias")

        info(f"Respuesta bot: {resp['text'][:80]}")

        # reminder sigue pendiente
        reminder = _get_reminder(apt_id)
        assert reminder.get('status') == 'sent', (
            f"reminder.status deberia seguir en 'sent', es '{reminder.get('status')}'"
        )
        ok("appointment_reminders.status sigue en 'sent'")

        # La cita no se modificó
        apt = _get_appointment(apt_id)
        assert apt.get('confirmed_by_client') != 1, (
            "confirmed_by_client no deberia ser 1 con respuesta invalida"
        )
        ok("appointments sin cambios")

    finally:
        _cleanup(apt_id)


# ── Escenario J: Sin reminder pendiente ──────────────────────────────────────

def test_J_sin_reminder_pendiente():
    """
    Cliente escribe "1" sin haber recibido recordatorio.
    Esperado:
      - Flujo normal del bot (no confundir con respuesta a reminder)
    """
    header("ESCENARIO J - Sin reminder pendiente -> flujo normal")
    _cleanup()  # Asegurar que no hay sesión ni reminder

    try:
        resp = _send_whatsapp("1")

        info(f"Respuesta bot: {resp['text'][:80]}")

        # No debe responder como si fuera confirmación de turno
        assert 'gracias' not in resp['text'].lower() or 'turno confirmado' not in resp['text'].lower(), (
            f"Sin reminder, '1' no deberia confirmar turno: '{resp['text']}'"
        )
        ok("Sin reminder pendiente, '1' no se interpreta como confirmacion")

    finally:
        _cleanup()


# ── Runner ────────────────────────────────────────────────────────────────────

def run_all():
    sep()
    print(f"{C.BOLD}  TEST INTEGRACION - Respuestas al recordatorio{C.END}")
    print(f"  {C.DIM}Cliente prueba: {CLIENT_PHONE}{C.END}")
    print(f"  {C.DIM}Webhook: {WEBHOOK_URL}{C.END}")
    sep()

    tests = [
        ("F", "Respuesta '1' -> confirmar",          test_F_respuesta_1_confirma),
        ("G", "Respuesta '2' -> reprogramar",         test_G_respuesta_2_reprogramar),
        ("H", "Respuesta '0' -> cancelar",            test_H_respuesta_0_cancelar),
        ("I", "Respuesta invalida -> sin cambios",    test_I_respuesta_invalida),
        ("J", "Sin reminder pendiente -> flujo normal", test_J_sin_reminder_pendiente),
    ]

    passed = failed = 0
    for code, name, fn in tests:
        print(f"\n{C.CYAN}> Escenario {code}: {name}{C.END}")
        try:
            fn()
            passed += 1
        except AssertionError as e:
            fail(str(e)); failed += 1
        except requests.exceptions.ConnectionError:
            warn("Sin conexion al webhook — correr dentro del container:")
            warn("docker exec whatsapp-demo python tests/core/test_reminder_responses.py")
            failed += 1
        except Exception as e:
            fail(f"Error inesperado: {e}")
            if VERBOSE:
                import traceback; traceback.print_exc()
            failed += 1

    sep()
    total = len(tests)
    if failed == 0:
        print(f"{C.GREEN}{C.BOLD}  TODOS LOS ESCENARIOS PASARON ({passed}/{total}){C.END}")
    else:
        print(f"{C.RED}{C.BOLD}  {failed} FALLARON ({passed}/{total} pasaron){C.END}")
    sep()
    return failed == 0


if __name__ == "__main__":
    sys.exit(0 if run_all() else 1)
