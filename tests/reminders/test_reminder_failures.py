#!/usr/bin/env python3
"""
Test de integración: Fallos de recordatorio y alerta al profesional
====================================================================

Llama a reminder_service directamente (mismo proceso Python)
para que patch() funcione sobre _send_twilio.

Nota: patch() no cruza procesos — no funciona sobre el webhook Flask.
La estrategia correcta es llamar al servicio directamente:

    reminder_service.send_daily_reminders()   <- llamada directa
        -> message_sender.send_with_retry()
            -> _send_twilio() <- parcheado aquí

Escenarios:
    A. Error 500 (genérico) -> encola en message_retry_queue
    B. Error 63003 (sin WhatsApp) -> alerta al profesional, sin encolar
    C. 3 fallos consecutivos -> falla definitiva + alerta al profesional
    D. Smoke test webhook (sin patch)

Uso:
    docker exec whatsapp-demo python tests/reminders/test_reminder_failures.py
    docker exec whatsapp-demo python tests/reminders/test_reminder_failures.py -v
"""

import sys
import requests
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.database.database import db
from src.core.message_sender import (
    message_sender,
    TWILIO_ERROR_NO_WHATSAPP,
)

# ── Config ────────────────────────────────────────────────────────────────────

WEBHOOK_URL   = "http://localhost:5000/webhook"
TRIGGER_PHONE = "whatsapp:+5493704969801"
CLIENT_PHONE  = "+5499999000001"
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

def _create_test_appointment(days_ahead=1) -> int:
    target_date = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    with db.get_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO appointments
                (client_phone, professional_phone, appointment_date,
                 start, end, status, reminder_sent)
            VALUES (?, ?, ?, '10:00', '10:50', 'confirmada', 0)
        """, (CLIENT_PHONE, PROF_PHONE, target_date))
        apt_id = cursor.lastrowid
    if VERBOSE:
        info(f"Cita #{apt_id} creada: {CLIENT_PHONE} -> {target_date} 10:00")
    return apt_id


def _get_appointment(apt_id: int) -> dict:
    with db.get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM appointments WHERE id = ?", (apt_id,)
        ).fetchone()
    return dict(row) if row else {}


def _get_queue() -> list:
    with db.get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM message_retry_queue WHERE to_phone = ? ORDER BY id",
            (CLIENT_PHONE,)
        ).fetchall()
    return [dict(r) for r in rows]


def _cleanup(apt_id: int = None):
    with db.get_connection() as conn:
        if apt_id:
            conn.execute("DELETE FROM appointments WHERE id = ?", (apt_id,))
        conn.execute("DELETE FROM message_retry_queue WHERE to_phone = ?", (CLIENT_PHONE,))
        conn.execute("DELETE FROM appointments WHERE client_phone = ?", (CLIENT_PHONE,))


def _run_reminders() -> dict:
    from src.services.reminder_service import reminder_service
    stats = reminder_service.send_daily_reminders()
    if VERBOSE:
        info(f"Stats: {stats}")
    return stats


# ── Escenario A ───────────────────────────────────────────────────────────────

def test_A_fallo_generico_encola():
    header("ESCENARIO A - Fallo 500 -> encolar en retry queue")
    apt_id = _create_test_appointment()
    try:
        with patch(
            'src.core.message_sender.MessageSender._send_twilio',
            return_value=(False, 500)
        ):
            stats = _run_reminders()

        info(f"Stats: {stats}")

        assert stats.get('sent', 0) == 0, (
            f"sent deberia ser 0, es {stats.get('sent')}"
        )
        ok("send_daily_reminders reporta sent=0")

        apt = _get_appointment(apt_id)
        assert apt.get('reminder_sent') == 0, (
            f"reminder_sent deberia ser 0, es {apt.get('reminder_sent')}"
        )
        ok("reminder_sent sigue en 0")

        queue = _get_queue()
        assert len(queue) >= 1, f"Deberia haber 1 item en cola, hay {len(queue)}"
        item = queue[0]
        assert item['status'] == 'pending', f"status={item['status']}, esperado 'pending'"
        assert item['attempts'] == 0, f"attempts={item['attempts']}, esperado 0"
        ok(f"Mensaje encolado (status=pending, attempts=0)")

    finally:
        _cleanup(apt_id)


# ── Escenario B ───────────────────────────────────────────────────────────────

def test_B_error_63003_alerta_profesional():
    header("ESCENARIO B - Error 63003 -> NO encolar + alerta profesional")
    apt_id = _create_test_appointment()
    alerts = []

    def mock_alert(**kwargs):
        alerts.append(kwargs)
        if VERBOSE:
            info(f"Alerta: prof={kwargs.get('professional_phone')} error={kwargs.get('error_code')}")

    try:
        with patch(
            'src.core.message_sender.MessageSender._send_twilio',
            return_value=(False, TWILIO_ERROR_NO_WHATSAPP)
        ), patch(
            'src.core.message_sender.MessageSender._alert_professional',
            side_effect=mock_alert
        ):
            stats = _run_reminders()

        info(f"Stats: {stats}")

        queue = _get_queue()
        pending = [i for i in queue if i['status'] == 'pending']
        assert len(pending) == 0, f"63003 NO debe encolar, hay {len(pending)} pendientes"
        ok("No se encolo (correcto para 63003)")

        assert len(alerts) >= 1, f"Deberia haber 1 alerta, hubo {len(alerts)}"
        alerta = alerts[0]
        assert alerta.get('professional_phone') == PROF_PHONE, (
            f"Alerta debe ir a {PROF_PHONE}, fue a {alerta.get('professional_phone')}"
        )
        assert alerta.get('error_code') == TWILIO_ERROR_NO_WHATSAPP
        ok(f"Alerta enviada a {PROF_PHONE} con error_code=63003")

        apt = _get_appointment(apt_id)
        assert apt.get('reminder_sent') == 0
        ok("reminder_sent sigue en 0")

    finally:
        _cleanup(apt_id)


# ── Escenario C ───────────────────────────────────────────────────────────────

def test_C_tres_fallos_consecutivos_alerta():
    header("ESCENARIO C - 3 fallos -> falla definitiva + alerta profesional")
    apt_id = _create_test_appointment()
    alerts = []

    def mock_alert(**kwargs):
        alerts.append(kwargs)

    try:
        max_retries = message_sender.MAX_RETRIES
        past = (datetime.now() - timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M:%S')

        with db.get_connection() as conn:
            conn.execute("""
                INSERT INTO message_retry_queue
                    (to_phone, message, professional_phone, patient_name,
                     appointment_id, attempts, next_retry_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
            """, (
                CLIENT_PHONE, "Recordatorio de prueba",
                PROF_PHONE, "Paciente Test",
                apt_id, max_retries - 1, past,
            ))

        info(f"Item insertado con attempts={max_retries - 1} (MAX={max_retries})")

        with patch(
            'src.core.message_sender.MessageSender._send_twilio',
            return_value=(False, 500)
        ), patch(
            'src.core.message_sender.MessageSender._alert_professional',
            side_effect=mock_alert
        ):
            stats = message_sender.process_retry_queue()

        info(f"Stats: {stats}")

        assert stats.get('failed', 0) >= 1, f"Deberia haber 1 fallo definitivo, stats: {stats}"
        ok(f"Fallo definitivo (stats.failed={stats['failed']})")

        queue = _get_queue()
        failed = [i for i in queue if i['status'] == 'failed']
        assert len(failed) >= 1, f"Deberia haber 1 item 'failed', hay {len(failed)}"
        ok("Item marcado como 'failed' en BD")

        assert len(alerts) >= 1, f"Deberia haber alerta, hubo {len(alerts)}"
        ok(f"Alerta enviada al profesional despues de {max_retries} fallos")

    finally:
        _cleanup(apt_id)


# ── Escenario D: Smoke test webhook ──────────────────────────────────────────

def test_D_smoke_webhook():
    header("ESCENARIO D - Smoke test webhook (sin patch)")
    try:
        payload = {
            "From":     TRIGGER_PHONE,
            "To":       "whatsapp:+5493705217649",
            "Body":     "scheduler status",
            "NumMedia": "0",
        }
        resp = requests.post(WEBHOOK_URL, data=payload, timeout=10)
        assert resp.status_code == 200, f"Status code: {resp.status_code}"
        import re
        match = re.search(r'<Message>(.*?)</Message>', resp.text, re.DOTALL)
        text = match.group(1).strip() if match else resp.text
        info(f"Respuesta: {text[:120]}")
        assert len(text) > 0
        ok("Webhook responde a 'scheduler status'")
    except requests.exceptions.ConnectionError:
        warn("Sin conexion al webhook — correr dentro del container:")
        warn("docker exec whatsapp-demo python tests/core/test_reminder_failures.py")


# ── Runner ────────────────────────────────────────────────────────────────────

def run_all():
    sep()
    print(f"{C.BOLD}  TEST INTEGRACION - Fallos de recordatorio{C.END}")
    print(f"  {C.DIM}Cliente prueba: {CLIENT_PHONE}{C.END}")
    sep()

    tests = [
        ("A", "Fallo 500 -> encolar",                 test_A_fallo_generico_encola),
        ("B", "Error 63003 -> alerta profesional",    test_B_error_63003_alerta_profesional),
        ("C", "3 fallos -> falla definitiva",         test_C_tres_fallos_consecutivos_alerta),
        ("D", "Smoke test webhook",                   test_D_smoke_webhook),
    ]

    passed = failed = 0
    for code, name, fn in tests:
        print(f"\n{C.CYAN}> Escenario {code}: {name}{C.END}")
        try:
            fn()
            passed += 1
        except AssertionError as e:
            fail(str(e)); failed += 1
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