#!/usr/bin/env python3
"""
Test: Ventana horaria de recordatorios
========================================

Valida que should_handle_as_reminder() solo intercepte mensajes
dentro de la franja REMINDER_SEND_TIME → REMINDER_CLOSE_TIME,
y que fuera de ella el flujo sea normal.

Escenarios:
    K. Confirmar DENTRO de la franja  → interceptado como reminder
    L. Confirmar FUERA de la franja   → flujo normal (no interceptado)
    M. Reprogramar DENTRO             → dispara flujo de reprogramación
    N. Reprogramar FUERA              → flujo normal
    O. Cancelar DENTRO                → dispara flujo de cancelación

Para reprogramar y cancelar (M, N, O) solo validamos que
should_handle_as_reminder() devuelva el valor correcto — la lógica
interna del bucle ya está cubierta por test_reminder_responses.py.

Uso:
    docker exec -w /app whatsapp-demo python tests/reminders/test_reminder_window.py
    docker exec -w /app whatsapp-demo python tests/reminders/test_reminder_window.py -v
"""

import sys
import os
import re
import requests
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.database.database import db
from src.core.states import SessionData, ConversationState

# ── Config ────────────────────────────────────────────────────────────────────

WEBHOOK_URL  = "http://localhost:5000/webhook"
CLIENT_PHONE = "+5499999000099"   # número ficticio exclusivo para este test
PROF_PHONE   = "+5491100000001"
VERBOSE      = "-v" in sys.argv

# Leer franja del .env (con defaults seguros)
_send_raw  = os.getenv("REMINDER_SEND_TIME",  "17:30")
_close_raw = os.getenv("REMINDER_CLOSE_TIME", "20:30")

def _to_minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)

SEND_MINUTES  = _to_minutes(_send_raw)
CLOSE_MINUTES = _to_minutes(_close_raw)

# Hora DENTRO de la franja para mockear (send + 30 min)
INSIDE_H  = (SEND_MINUTES + 30) // 60
INSIDE_M  = (SEND_MINUTES + 30) % 60

# Hora FUERA de la franja para mockear (close + 60 min)
OUTSIDE_H = (CLOSE_MINUTES + 60) // 60 % 24
OUTSIDE_M = (CLOSE_MINUTES + 60) % 60


# ── Colores ───────────────────────────────────────────────────────────────────

class C:
    GREEN  = '\033[92m'; RED    = '\033[91m'
    CYAN   = '\033[96m'; YELLOW = '\033[93m'
    BOLD   = '\033[1m';  DIM    = '\033[2m'
    END    = '\033[0m'

def ok(t):     print(f"  {C.GREEN}✓ {t}{C.END}")
def fail(t):   print(f"  {C.RED}✗ {t}{C.END}")
def info(t):   print(f"  {C.DIM}→ {t}{C.END}")
def warn(t):   print(f"  {C.YELLOW}⚠ {t}{C.END}")
def sep():     print("=" * 62)
def header(t): sep(); print(f"{C.BOLD}{C.CYAN}  {t}{C.END}"); sep()


# ── Helpers de BD ─────────────────────────────────────────────────────────────

def _create_test_appointment(slot: str = "10:00") -> int:
    """
    Crea cita para pasado mañana.
    Recibe 'slot' para variar el horario entre escenarios y evitar
    el UNIQUE constraint (professional_phone, appointment_date, start).
    """
    target_date = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
    start = slot
    h, m  = slot.split(":")
    end   = f"{int(h):02d}:{int(m)+50:02d}"   # 50 min de duración
    with db.get_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO appointments
                (client_phone, professional_phone, appointment_date,
                 start, end, status, reminder_sent)
            VALUES (?, ?, ?, ?, ?, 'confirmada', 1)
        """, (CLIENT_PHONE, PROF_PHONE, target_date, start, end))
        apt_id = cursor.lastrowid
    if VERBOSE:
        info(f"Cita #{apt_id} creada: {CLIENT_PHONE} → {target_date} {start}")
    return apt_id


def _create_reminder_record(apt_id: int) -> None:
    """
    Inserta reminder con status='sent' simulando que ya fue enviado.
    Desnormaliza appointment_date y appointment_time desde la cita (NOT NULL en schema).
    """
    with db.get_connection() as conn:
        row = conn.execute(
            "SELECT appointment_date, start FROM appointments WHERE id = ?", (apt_id,)
        ).fetchone()
        apt_date = row["appointment_date"]
        apt_time = row["start"]
        conn.execute("""
            INSERT INTO appointment_reminders
                (appointment_id, client_phone, professional_phone,
                 appointment_date, appointment_time, status, sent_at)
            VALUES (?, ?, ?, ?, ?, 'sent', CURRENT_TIMESTAMP)
        """, (apt_id, CLIENT_PHONE, PROF_PHONE, apt_date, apt_time))
    if VERBOSE:
        info(f"Reminder inyectado para cita #{apt_id} ({apt_date} {apt_time})")


def _get_reminder(apt_id: int) -> dict:
    with db.get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM appointment_reminders WHERE appointment_id = ? ORDER BY id DESC LIMIT 1",
            (apt_id,)
        ).fetchone()
    return dict(row) if row else {}


def _cleanup(apt_id: int = None) -> None:
    with db.get_connection() as conn:
        if apt_id:
            conn.execute("DELETE FROM appointment_reminders WHERE appointment_id = ?", (apt_id,))
            conn.execute("DELETE FROM appointments WHERE id = ?", (apt_id,))
        else:
            conn.execute("DELETE FROM appointments WHERE client_phone = ?", (CLIENT_PHONE,))
            conn.execute("DELETE FROM appointment_reminders WHERE client_phone = ?", (CLIENT_PHONE,))


# ── Helper de detección directa (sin webhook) ─────────────────────────────────

def _check_should_handle(message: str, mock_hour: int, mock_minute: int) -> bool:
    """
    Llama should_handle_as_reminder() con la hora mockeada.
    No pasa por webhook — prueba la función directamente.

    Como reminder_handler importa datetime localmente dentro de la función,
    mockeamos os.getenv para simular una franja que siempre incluya o excluya
    la hora actual real, en lugar de mockear datetime.
    """
    from src.bot.reminder_handler import should_handle_as_reminder

    session = SessionData(CLIENT_PHONE)
    session.current_state = ConversationState.START

    now = datetime.now()
    now_minutes = now.hour * 60 + now.minute

    # Calculamos una franja ficticia que contenga o excluya la hora actual
    # según lo que queremos testear con mock_hour:mock_minute
    mock_minutes = mock_hour * 60 + mock_minute

    if mock_minutes >= SEND_MINUTES and mock_minutes <= CLOSE_MINUTES:
        # Queremos simular DENTRO: ajustamos la franja para que la hora
        # real del sistema caiga dentro de ella
        delta = now_minutes - SEND_MINUTES
        fake_send  = f"{(now.hour - 1) % 24:02d}:00"
        fake_close = f"{(now.hour + 1) % 24:02d}:00"
    else:
        # Queremos simular FUERA: la hora real cae fuera de la franja
        fake_send  = f"{(now.hour + 2) % 24:02d}:00"
        fake_close = f"{(now.hour + 3) % 24:02d}:00"

    env_overrides = {
        "REMINDER_SEND_TIME":  fake_send,
        "REMINDER_CLOSE_TIME": fake_close,
    }

    original_getenv = os.getenv

    def patched_getenv(key, default=None):
        if key in env_overrides:
            return env_overrides[key]
        return original_getenv(key, default)

    with patch("os.getenv", side_effect=patched_getenv):
        result = should_handle_as_reminder(session, message)

    if VERBOSE:
        info(f"should_handle('{message}', franja {fake_send}→{fake_close}) → {result}")
    return result


# ── Helper webhook (para escenario K completo) ────────────────────────────────

def _send_whatsapp(text: str) -> dict:
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
        info(f"Bot respondió: {text_resp[:120]}")
    return {"text": text_resp, "status_code": resp.status_code}


# ── Escenarios ────────────────────────────────────────────────────────────────

def test_K_confirmar_dentro_franja():
    """
    Escenario K — Confirmar DENTRO de la franja horaria.

    Crea reminder en BD, mockea hora dentro de la ventana,
    y verifica via webhook que el bot confirma el turno.
    """
    header(f"ESCENARIO K — Confirmar DENTRO ({INSIDE_H:02d}:{INSIDE_M:02d})")
    apt_id = _create_test_appointment(slot="10:00")
    _create_reminder_record(apt_id)

    try:
        # Verificar detección directa primero
        for msg in ['Si', 'confirmo', 'Confirmar', '1', 'dale']:
            result = _check_should_handle(msg, INSIDE_H, INSIDE_M)
            assert result is True, f"'{msg}' dentro de franja debería ser interceptado"
            ok(f"'{msg}' → interceptado como reminder")

        # Verificar BD después de envío via webhook
        # (el webhook corre con la hora real — si estamos dentro de la franja, pasa completo)
        now_minutes = datetime.now().hour * 60 + datetime.now().minute
        if SEND_MINUTES <= now_minutes <= CLOSE_MINUTES:
            info("Hora real dentro de la franja — probando webhook completo")
            resp = _send_whatsapp("confirmo")
            assert any(w in resp['text'].lower() for w in ['confirm', 'perfecto', 'turno', 'gracias']), (
                f"Respuesta no indica confirmación: '{resp['text']}'"
            )
            ok("Webhook: bot responde como confirmación de turno")

            reminder = _get_reminder(apt_id)
            assert reminder.get('status') == 'confirmed', (
                f"reminder.status debería ser 'confirmed', es '{reminder.get('status')}'"
            )
            ok("BD: appointment_reminders.status = 'confirmed'")
        else:
            warn("Hora real fuera de franja — solo validación directa (sin webhook)")

    finally:
        _cleanup(apt_id)


def test_L_confirmar_fuera_franja():
    """
    Escenario L — Confirmar FUERA de la franja horaria.

    Mismo setup, pero hora mockeada fuera de la ventana.
    should_handle_as_reminder() debe devolver False.
    """
    header(f"ESCENARIO L — Confirmar FUERA ({OUTSIDE_H:02d}:{OUTSIDE_M:02d})")
    apt_id = _create_test_appointment(slot="11:00")
    _create_reminder_record(apt_id)

    try:
        for msg in ['Si', 'confirmo', '1', 'dale']:
            result = _check_should_handle(msg, OUTSIDE_H, OUTSIDE_M)
            assert result is False, (
                f"'{msg}' fuera de franja NO debería ser interceptado como reminder"
            )
            ok(f"'{msg}' → NO interceptado (flujo normal)")

    finally:
        _cleanup(apt_id)


def test_M_reprogramar_dentro_franja():
    """
    Escenario M — Reprogramar DENTRO de la franja.

    Valida que should_handle_as_reminder() retorne True
    para variantes de reprogramación dentro de la ventana.
    La lógica del bucle de reprogramación está cubierta en test_reminder_responses.py.
    """
    header(f"ESCENARIO M — Reprogramar DENTRO ({INSIDE_H:02d}:{INSIDE_M:02d})")
    apt_id = _create_test_appointment(slot="12:00")
    _create_reminder_record(apt_id)

    try:
        for msg in ['2', 'cambiar', 'reprogramar', 'otro horario', 'mover']:
            result = _check_should_handle(msg, INSIDE_H, INSIDE_M)
            assert result is True, (
                f"'{msg}' dentro de franja debería ser interceptado como reminder"
            )
            ok(f"'{msg}' → interceptado (dispara flujo de reprogramación)")

    finally:
        _cleanup(apt_id)


def test_N_reprogramar_fuera_franja():
    """
    Escenario N — Reprogramar FUERA de la franja.

    Fuera de la ventana, ningún mensaje debe ser interceptado
    como respuesta a recordatorio.
    """
    header(f"ESCENARIO N — Reprogramar FUERA ({OUTSIDE_H:02d}:{OUTSIDE_M:02d})")
    apt_id = _create_test_appointment(slot="13:00")
    _create_reminder_record(apt_id)

    try:
        for msg in ['2', 'cambiar', 'reprogramar']:
            result = _check_should_handle(msg, OUTSIDE_H, OUTSIDE_M)
            assert result is False, (
                f"'{msg}' fuera de franja NO debería ser interceptado"
            )
            ok(f"'{msg}' → NO interceptado (flujo normal)")

    finally:
        _cleanup(apt_id)


def test_O_cancelar_dentro_franja():
    """
    Escenario O — Cancelar DENTRO de la franja.

    Valida que should_handle_as_reminder() retorne True
    para variantes de cancelación dentro de la ventana.
    """
    header(f"ESCENARIO O — Cancelar DENTRO ({INSIDE_H:02d}:{INSIDE_M:02d})")
    apt_id = _create_test_appointment(slot="14:00")
    _create_reminder_record(apt_id)

    try:
        for msg in ['0', 'cancelar', 'no voy', 'no puedo', 'cancelo']:
            result = _check_should_handle(msg, INSIDE_H, INSIDE_M)
            assert result is True, (
                f"'{msg}' dentro de franja debería ser interceptado como reminder"
            )
            ok(f"'{msg}' → interceptado (dispara flujo de cancelación)")

    finally:
        _cleanup(apt_id)


# ── Runner ────────────────────────────────────────────────────────────────────

def run_all():
    # Limpieza inicial por si quedaron datos de runs anteriores
    _cleanup()

    sep()
    print(f"{C.BOLD}  TEST VENTANA HORARIA — Recordatorios{C.END}")
    print(f"  {C.DIM}Franja: {_send_raw} → {_close_raw}{C.END}")
    print(f"  {C.DIM}Dentro:  {INSIDE_H:02d}:{INSIDE_M:02d}  |  Fuera: {OUTSIDE_H:02d}:{OUTSIDE_M:02d}{C.END}")
    print(f"  {C.DIM}Cliente prueba: {CLIENT_PHONE}{C.END}")
    sep()

    tests = [
        ("K", "Confirmar DENTRO de la franja",    test_K_confirmar_dentro_franja),
        ("L", "Confirmar FUERA de la franja",      test_L_confirmar_fuera_franja),
        ("M", "Reprogramar DENTRO de la franja",   test_M_reprogramar_dentro_franja),
        ("N", "Reprogramar FUERA de la franja",    test_N_reprogramar_fuera_franja),
        ("O", "Cancelar DENTRO de la franja",      test_O_cancelar_dentro_franja),
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
            warn("Sin conexión al webhook — solo validación directa disponible")
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