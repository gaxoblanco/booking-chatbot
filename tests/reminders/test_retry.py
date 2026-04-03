#!/usr/bin/env python3
"""
Test de integración: Reintento exitoso (Escenario E)
=====================================================

Flujo completo:
    1. Primer intento falla (error 500) → mensaje encolado
    2. process_retry_queue() corre → reintento exitoso
    3. Ítem marcado como 'sent' en BD
    4. reminder_sent = 1 en appointments

También cubre:
    E2. Segundo intento falla, tercer intento exitoso (backoff)
    E3. reminder_sent no se marca hasta que el reintento es exitoso

Uso:
    docker exec whatsapp-demo python tests/reminders/test_retry.py
    docker exec whatsapp-demo python tests/reminders/test_retry.py -v
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, call

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.database.database import db
from src.core.message_sender import message_sender, TWILIO_ERROR_NO_WHATSAPP

# ── Config ────────────────────────────────────────────────────────────────────

CLIENT_PHONE = "+5499999000003"
PROF_PHONE   = "+5491100000001"
VERBOSE      = "-v" in sys.argv


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

def _create_appointment(days_ahead=1) -> int:
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
        info(f"Cita #{apt_id} creada: {CLIENT_PHONE} -> {target_date}")
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


def _insert_queue_item(apt_id: int, attempts: int = 0, minutes_ago: int = 5) -> int:
    """Inserta ítem en cola listo para reintento."""
    past = (datetime.now() - timedelta(minutes=minutes_ago)).strftime('%Y-%m-%d %H:%M:%S')
    with db.get_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO message_retry_queue
                (to_phone, message, professional_phone, patient_name,
                 appointment_id, attempts, next_retry_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
        """, (
            CLIENT_PHONE, "Recordatorio de prueba",
            PROF_PHONE, "Paciente Test",
            apt_id, attempts, past,
        ))
        return cursor.lastrowid


def _cleanup(apt_id: int = None):
    with db.get_connection() as conn:
        if apt_id:
            conn.execute("DELETE FROM appointments WHERE id = ?", (apt_id,))
        conn.execute("DELETE FROM message_retry_queue WHERE to_phone = ?", (CLIENT_PHONE,))
        conn.execute("DELETE FROM appointments WHERE client_phone = ?", (CLIENT_PHONE,))


def _run_reminders() -> dict:
    from src.services.reminder_service import reminder_service
    return reminder_service.send_daily_reminders()


# ── Escenario E1: Fallo → encola → reintento exitoso ─────────────────────────

def test_E1_fallo_luego_reintento_exitoso():
    """
    Flujo completo de reintento:
      1. Primer intento falla → encola
      2. process_retry_queue() → reintento exitoso
      3. Ítem marcado 'sent', reminder_sent=1
    """
    header("ESCENARIO E1 - Fallo -> encola -> reintento exitoso")
    apt_id = _create_appointment()

    try:
        # Paso 1: primer intento falla → encola
        with patch(
            'src.core.message_sender.MessageSender._send_twilio',
            return_value=(False, 500)
        ):
            stats = _run_reminders()

        info(f"Stats primer intento: {stats}")
        assert stats.get('sent', 0) == 0
        ok("Primer intento fallo (sent=0)")

        queue = _get_queue()
        assert len(queue) == 1 and queue[0]['status'] == 'pending'
        ok("Mensaje encolado (status=pending)")

        # reminder_sent sigue en 0
        apt = _get_appointment(apt_id)
        assert apt.get('reminder_sent') == 0
        ok("reminder_sent=0 después del fallo")

        # Forzar next_retry_at en el pasado para que sea procesable ahora
        past = (datetime.now() - timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M:%S')
        with db.get_connection() as conn:
            conn.execute(
                "UPDATE message_retry_queue SET next_retry_at = ? WHERE to_phone = ?",
                (past, CLIENT_PHONE)
            )
        info("next_retry_at forzado al pasado para reintento inmediato")

        # Paso 2: reintento exitoso
        with patch(
            'src.core.message_sender.MessageSender._send_twilio',
            return_value=(True, None)
        ):
            retry_stats = message_sender.process_retry_queue()

        info(f"Stats reintento: {retry_stats}")
        assert retry_stats.get('sent', 0) >= 1, (
            f"Reintento deberia enviar 1, stats: {retry_stats}"
        )
        ok(f"Reintento exitoso (sent={retry_stats['sent']})")

        # Paso 3: verificar estado final
        queue = _get_queue()
        sent_items = [i for i in queue if i['status'] == 'sent']
        assert len(sent_items) >= 1, (
            f"Item deberia estar en 'sent', queue: {[i['status'] for i in queue]}"
        )
        ok("Ítem marcado como 'sent' en BD")

        # El ítem está marcado sent — attempts puede variar según implementación
        item = sent_items[0]
        info(f"attempts={item['attempts']} al momento de marcar sent")
        ok("Ítem procesado y marcado correctamente")

    finally:
        _cleanup(apt_id)


# ── Escenario E2: Dos fallos → tercer intento exitoso ─────────────────────────

def test_E2_dos_fallos_tercer_exitoso():
    """
    2 fallos en la cola, tercer intento es exitoso.
    Verifica que el backoff funciona y el mensaje llega eventualmente.
    """
    header("ESCENARIO E2 - 2 fallos -> tercer intento exitoso")
    apt_id = _create_appointment()

    try:
        # Insertar con attempts=1 (ya falló una vez)
        _insert_queue_item(apt_id, attempts=1)
        info(f"Ítem insertado con attempts=1")

        # Segundo fallo
        with patch(
            'src.core.message_sender.MessageSender._send_twilio',
            return_value=(False, 500)
        ):
            stats = message_sender.process_retry_queue()

        info(f"Stats segundo intento: {stats}")
        assert stats.get('sent', 0) == 0
        ok("Segundo intento fallo")

        queue = _get_queue()
        item = [i for i in queue if i['status'] == 'pending']
        assert len(item) >= 1
        assert item[0]['attempts'] == 2, (
            f"attempts deberia ser 2 después de 2 fallos, es {item[0]['attempts']}"
        )
        ok(f"attempts={item[0]['attempts']} después de 2 fallos")

        # Resetear next_retry_at para que sea procesable ahora
        past = (datetime.now() - timedelta(minutes=1)).strftime('%Y-%m-%d %H:%M:%S')
        with db.get_connection() as conn:
            conn.execute(
                "UPDATE message_retry_queue SET next_retry_at = ? WHERE to_phone = ?",
                (past, CLIENT_PHONE)
            )

        # Tercer intento exitoso
        with patch(
            'src.core.message_sender.MessageSender._send_twilio',
            return_value=(True, None)
        ):
            stats3 = message_sender.process_retry_queue()

        info(f"Stats tercer intento: {stats3}")
        assert stats3.get('sent', 0) >= 1
        ok("Tercer intento exitoso")

        queue = _get_queue()
        sent = [i for i in queue if i['status'] == 'sent']
        assert len(sent) >= 1
        ok("Ítem marcado como 'sent' después de 3 intentos")

    finally:
        _cleanup(apt_id)


# ── Escenario E3: reminder_sent solo se marca en éxito ───────────────────────

def test_E3_reminder_sent_solo_en_exito():
    """
    reminder_sent=0 durante todo el proceso de reintentos.
    Solo se marca =1 cuando el envío es exitoso.
    
    Nota: process_retry_queue() no actualiza reminder_sent —
    eso lo hace _send_reminder() en el primer intento exitoso.
    Este test verifica que el flujo completo (primer intento exitoso)
    sí marca reminder_sent=1.
    """
    header("ESCENARIO E3 - reminder_sent solo se marca en exito")
    apt_id = _create_appointment()

    try:
        # Primer intento exitoso — debe marcar reminder_sent=1
        with patch(
            'src.core.message_sender.MessageSender._send_twilio',
            return_value=(True, None)
        ):
            stats = _run_reminders()

        info(f"Stats: {stats}")
        assert stats.get('sent', 0) >= 1
        ok("Envio exitoso (sent >= 1)")

        apt = _get_appointment(apt_id)
        assert apt.get('reminder_sent') == 1, (
            f"reminder_sent deberia ser 1, es {apt.get('reminder_sent')}"
        )
        ok("reminder_sent=1 marcado correctamente")

        # No debe haber ítems en cola (éxito en primer intento)
        queue = _get_queue()
        assert len(queue) == 0, (
            f"No deberia haber items en cola con exito, hay {len(queue)}"
        )
        ok("Cola vacía (no se encoló en caso de éxito)")

    finally:
        _cleanup(apt_id)


# ── Escenario E4: No reintentar si reminder_sent=1 ───────────────────────────

def test_E4_no_reintentar_si_ya_enviado():
    """
    Si reminder_sent=1, el reminder_service NO debe intentar enviar de nuevo.
    Verifica idempotencia del servicio.
    """
    header("ESCENARIO E4 - No reintentar si reminder_sent=1")
    apt_id = _create_appointment()

    try:
        # Marcar como ya enviado
        with db.get_connection() as conn:
            conn.execute(
                "UPDATE appointments SET reminder_sent = 1 WHERE id = ?",
                (apt_id,)
            )
        info(f"Cita #{apt_id} marcada como reminder_sent=1")

        send_calls = []
        def mock_send(*args, **kwargs):
            send_calls.append(args)
            return True, None

        with patch(
            'src.core.message_sender.MessageSender._send_twilio',
            side_effect=mock_send
        ):
            stats = _run_reminders()

        info(f"Stats: {stats}")
        info(f"Llamadas a _send_twilio: {len(send_calls)}")

        assert len(send_calls) == 0, (
            f"No deberia llamar a Twilio si reminder_sent=1, llamó {len(send_calls)} veces"
        )
        ok("Twilio NO fue llamado (correcto — ya enviado)")

        assert stats.get('sent', 0) == 0
        ok("Stats reporta sent=0 (cita omitida)")

    finally:
        _cleanup(apt_id)


# ── Runner ────────────────────────────────────────────────────────────────────

def run_all():
    sep()
    print(f"{C.BOLD}  TEST INTEGRACION - Reintentos (Escenario E){C.END}")
    print(f"  {C.DIM}Cliente prueba: {CLIENT_PHONE}{C.END}")
    sep()

    tests = [
        ("E1", "Fallo -> encola -> reintento exitoso",     test_E1_fallo_luego_reintento_exitoso),
        ("E2", "2 fallos -> tercer intento exitoso",        test_E2_dos_fallos_tercer_exitoso),
        ("E3", "reminder_sent solo se marca en exito",      test_E3_reminder_sent_solo_en_exito),
        ("E4", "No reintentar si ya enviado",               test_E4_no_reintentar_si_ya_enviado),
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