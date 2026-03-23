#!/usr/bin/env python3
"""
Test: GAP 2+5 — MessageSender con reintentos y alerta al profesional
=====================================================================

Verifica que MessageSender:
    1. Envía correctamente cuando Twilio responde OK
    2. Encola el mensaje si Twilio falla (primer intento)
    3. Alerta al profesional inmediatamente en error 63003
    4. No reintenta en error 63003 (número sin WhatsApp)
    5. process_retry_queue() reintenta mensajes pendientes
    6. Alerta al profesional después de MAX_RETRIES fallidos
    7. Marca correctamente sent/failed en BD
    8. Tabla message_retry_queue existe en BD
    9. Instancia global importable

Uso:
    docker exec -it whatsapp-demo python tests/test_gap2_message_sender.py
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.database import db
from src.core.message_sender import MessageSender, message_sender
from src.core.message_sender import TWILIO_ERROR_NO_WHATSAPP

# ── Colores ──────────────────────────────────────────────────────────────────
class C:
    GREEN = '\033[92m'; RED = '\033[91m'; CYAN = '\033[96m'
    BOLD  = '\033[1m';  END = '\033[0m'

def ok(t):   print(f"  {C.GREEN}✅ {t}{C.END}")
def fail(t): print(f"  {C.RED}❌ {t}{C.END}")
def info(t): print(f"  ℹ️  {t}")
def sep():   print("=" * 60)

# ── Datos fijos ───────────────────────────────────────────────────────────────
CLIENT = "+5490000022001"
PROF   = "+5490000022002"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _cleanup_queue():
    with db.get_connection() as conn:
        conn.execute(
            "DELETE FROM message_retry_queue WHERE to_phone IN (?, ?)",
            (CLIENT, PROF)
        )

def _get_queue_items():
    with db.get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM message_retry_queue WHERE to_phone = ? ORDER BY id",
            (CLIENT,)
        ).fetchall()
    return [dict(r) for r in rows]

def _make_sender(max_retries=3, backoff=None):
    """Crea un MessageSender con config customizada para tests."""
    s = MessageSender()
    s.MAX_RETRIES     = max_retries
    s.BACKOFF_MINUTES = backoff or [0, 0, 0]  # 0 min para tests instantáneos
    return s


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_tabla_message_retry_queue_existe():
    """La tabla message_retry_queue debe existir en BD."""
    with db.get_connection() as conn:
        row = conn.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='message_retry_queue'
        """).fetchone()
    assert row is not None, "Tabla message_retry_queue no existe — agregar en _init_db()"
    ok("Tabla message_retry_queue existe en BD")


def test_instancia_global_importable():
    """La instancia global message_sender debe ser importable."""
    assert message_sender is not None
    assert hasattr(message_sender, 'send_with_retry')
    assert hasattr(message_sender, 'process_retry_queue')
    ok("message_sender importable y tiene los métodos requeridos")


def test_envio_exitoso_retorna_true():
    """Si Twilio acepta el mensaje, send_with_retry retorna True."""
    _cleanup_queue()
    sender = _make_sender()

    with patch.object(sender, '_send_twilio', return_value=(True, None)):
        result = sender.send_with_retry(
            to_phone           = CLIENT,
            message            = "Mensaje de prueba",
            professional_phone = PROF,
            patient_name       = "Paciente Test",
        )

    assert result is True, f"Esperado True, obtenido {result}"
    # No debe haber encolado nada
    items = _get_queue_items()
    assert len(items) == 0, f"No debería haber ítems en cola, hay {len(items)}"
    ok("Envío exitoso retorna True sin encolar")


def test_fallo_encola_para_reintento():
    """Si Twilio falla (error genérico), el mensaje se encola."""
    _cleanup_queue()
    sender = _make_sender()

    with patch.object(sender, '_send_twilio', return_value=(False, 500)):
        result = sender.send_with_retry(
            to_phone           = CLIENT,
            message            = "Mensaje que falla",
            professional_phone = PROF,
            patient_name       = "Paciente Test",
            appointment_id     = 999,
        )

    assert result is False
    items = _get_queue_items()
    assert len(items) == 1, f"Debería haber 1 ítem en cola, hay {len(items)}"
    assert items[0]['status']    == 'pending'
    assert items[0]['attempts']  == 0
    assert items[0]['to_phone']  == CLIENT
    ok("Fallo genérico encola el mensaje para reintento")


def test_error_63003_no_encola_alerta_directo():
    """Error 63003 → alerta al profesional sin encolar para reintento."""
    _cleanup_queue()
    sender        = _make_sender()
    alerts_sent   = []

    def mock_alert(professional_phone, patient_phone, patient_name,
                   appointment_id, error_code=None):
        alerts_sent.append({
            'professional': professional_phone,
            'error_code':   error_code
        })

    with patch.object(sender, '_send_twilio',
                      return_value=(False, TWILIO_ERROR_NO_WHATSAPP)), \
         patch.object(sender, '_alert_professional', side_effect=mock_alert):
        result = sender.send_with_retry(
            to_phone           = CLIENT,
            message            = "Mensaje sin WhatsApp",
            professional_phone = PROF,
        )

    assert result is False
    # No debe haber encolado
    items = _get_queue_items()
    assert len(items) == 0, f"Error 63003 no debería encolar, hay {len(items)} ítems"
    # Debe haber alertado al profesional
    assert len(alerts_sent) == 1, f"Debería haber 1 alerta, hubo {len(alerts_sent)}"
    assert alerts_sent[0]['error_code'] == TWILIO_ERROR_NO_WHATSAPP
    ok("Error 63003 alerta al profesional sin encolar")


def test_process_retry_queue_envia_pendiente():
    """process_retry_queue() reintenta y envía un mensaje pendiente."""
    _cleanup_queue()
    sender = _make_sender()

    # Insertar con timestamp Python (hora local) — evita desfase UTC vs local
    past = (datetime.now() - timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M:%S')
    with db.get_connection() as conn:
        conn.execute("""
            INSERT INTO message_retry_queue
                (to_phone, message, professional_phone, patient_name,
                 attempts, next_retry_at, status)
            VALUES (?, ?, ?, ?, 0, ?, 'pending')
        """, (CLIENT, "Mensaje a reintentar", PROF, "Paciente Test", past))

    with patch.object(sender, '_send_twilio', return_value=(True, None)):
        stats = sender.process_retry_queue()

    assert stats['sent'] >= 1, f"Debería haber enviado al menos 1, stats: {stats}"

    items = _get_queue_items()
    sent_items = [i for i in items if i['status'] == 'sent']
    assert len(sent_items) >= 1, "El ítem debe estar marcado como 'sent'"
    ok(f"process_retry_queue() reintenta y envía correctamente — stats: {stats}")


def test_process_retry_queue_alerta_al_agotar_reintentos():
    """Después de MAX_RETRIES fallidos, alerta al profesional."""
    _cleanup_queue()
    sender      = _make_sender(max_retries=2, backoff=[0, 0])
    alerts_sent = []

    def mock_alert(**kwargs):
        alerts_sent.append(kwargs)

    # Insertar con timestamp Python en el pasado
    past = (datetime.now() - timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M:%S')
    with db.get_connection() as conn:
        conn.execute("""
            INSERT INTO message_retry_queue
                (to_phone, message, professional_phone, patient_name,
                 attempts, next_retry_at, status)
            VALUES (?, ?, ?, ?, 1, ?, 'pending')
        """, (CLIENT, "Mensaje fallido", PROF, "Paciente Test", past))

    with patch.object(sender, '_send_twilio', return_value=(False, 500)), \
         patch.object(sender, '_alert_professional', side_effect=mock_alert):
        stats = sender.process_retry_queue()

    assert stats['failed'] >= 1, f"Debería haber 1 fallido, stats: {stats}"
    assert len(alerts_sent) >= 1, "Debería haber enviado alerta al profesional"

    items = _get_queue_items()
    failed_items = [i for i in items if i['status'] == 'failed']
    assert len(failed_items) >= 1, "El ítem debe estar marcado como 'failed'"
    ok("Agotados MAX_RETRIES → alerta al profesional + marca 'failed'")


def test_alerta_profesional_mensaje_sin_whatsapp():
    """El mensaje de alerta para error 63003 menciona 'WhatsApp activo'."""
    sender          = _make_sender()
    mensajes_alerta = []

    def mock_send(to_phone, message, **kwargs):
        mensajes_alerta.append(message)
        return True, None

    with patch.object(sender, '_send_twilio', side_effect=mock_send):
        sender._alert_professional(
            professional_phone = PROF,
            patient_phone      = CLIENT,
            patient_name       = "Juan Pérez",
            appointment_id     = 100,
            error_code         = TWILIO_ERROR_NO_WHATSAPP,
        )

    assert len(mensajes_alerta) == 1
    msg = mensajes_alerta[0].lower()
    assert 'whatsapp' in msg, "El mensaje de alerta debe mencionar WhatsApp"
    ok("Alerta 63003 menciona 'WhatsApp' en el texto")


def test_alerta_profesional_mensaje_generico():
    """El mensaje de alerta genérico menciona cantidad de intentos."""
    sender          = _make_sender()
    mensajes_alerta = []

    def mock_send(to_phone, message, **kwargs):
        mensajes_alerta.append(message)
        return True, None

    with patch.object(sender, '_send_twilio', side_effect=mock_send):
        sender._alert_professional(
            professional_phone = PROF,
            patient_phone      = CLIENT,
            patient_name       = "María García",
            appointment_id     = 200,
            error_code         = 500,
        )

    assert len(mensajes_alerta) == 1
    msg = mensajes_alerta[0]
    assert 'María García' in msg or 'marí' in msg.lower(), \
        "El mensaje de alerta debe incluir el nombre del paciente"
    ok("Alerta genérica incluye nombre del paciente")


def test_sin_professional_phone_no_falla():
    """Si no hay professional_phone, la alerta se omite sin excepción."""
    sender = _make_sender()

    # No debe lanzar excepción aunque no haya professional_phone
    try:
        sender._alert_professional(
            professional_phone = None,
            patient_phone      = CLIENT,
            patient_name       = "Test",
            appointment_id     = None,
        )
        ok("Sin professional_phone la alerta se omite sin excepción")
    except Exception as e:
        raise AssertionError(f"No debería lanzar excepción: {e}")


# ── Runner ────────────────────────────────────────────────────────────────────

def run_all():
    sep()
    print(f"{C.BOLD}  TEST GAP 2+5 — MessageSender{C.END}")
    sep()

    _cleanup_queue()

    tests = [
        test_tabla_message_retry_queue_existe,
        test_instancia_global_importable,
        test_envio_exitoso_retorna_true,
        test_fallo_encola_para_reintento,
        test_error_63003_no_encola_alerta_directo,
        test_process_retry_queue_envia_pendiente,
        test_process_retry_queue_alerta_al_agotar_reintentos,
        test_alerta_profesional_mensaje_sin_whatsapp,
        test_alerta_profesional_mensaje_generico,
        test_sin_professional_phone_no_falla,
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

    _cleanup_queue()
    sep()
    if failed == 0:
        print(f"{C.GREEN}{C.BOLD}  ✅ TODOS LOS TESTS PASARON ({passed}/{len(tests)}){C.END}")
    else:
        print(f"{C.RED}{C.BOLD}  ❌ {failed} FALLARON ({passed}/{len(tests)} pasaron){C.END}")
    sep()
    return failed == 0

def test_gap2_completo():
    assert run_all()

if __name__ == "__main__":
    sys.exit(0 if run_all() else 1)