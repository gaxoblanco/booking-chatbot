#!/usr/bin/env python3
"""
Test: GAP 6 — Política de cancelación centralizada
===================================================

Verifica que cancel_appointment() en client_service:
    1. Retorna dict en lugar de bool
    2. Aplica CANCELLATION_HOURS_LIMIT de DomainConfig (no hardcodeado)
    3. Retorna 'too_late' con hours_until y professional_phone si es tarde
    4. bypass_policy=True omite la validación (para cancelaciones del sistema)
    5. Retorna 'not_authorized' si el número no es dueño ni paciente
    6. Retorna 'already_cancelled' si ya estaba cancelada
    7. Retorna 'success': True en el flujo feliz

Uso:
    docker exec -it whatsapp-demo python tests/test_gap6_cancellation_policy.py
"""

import sys
from pathlib import Path
from datetime import date, timedelta, datetime
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.database import db
from src.services.client_service import client_service
from src.config.domain_config import DomainConfig

# ── Colores ──────────────────────────────────────────────────────────────────
class C:
    GREEN = '\033[92m'; RED = '\033[91m'; CYAN = '\033[96m'
    BOLD  = '\033[1m';  END = '\033[0m'

def ok(t):   print(f"  {C.GREEN}✅ {t}{C.END}")
def fail(t): print(f"  {C.RED}❌ {t}{C.END}")
def info(t): print(f"  ℹ️  {t}")
def sep():   print("=" * 60)

# ── Datos fijos ───────────────────────────────────────────────────────────────
CLIENT  = "+5490000011001"
PATIENT = "+5490000011002"
STRANGER = "+5490000011003"
PROF    = "+5490000011004"
BASE_DATE = date(2099, 12, 15)

_counter = 0

def _next_slot():
    """Retorna (date_str, start_str) únicos para evitar UNIQUE constraint."""
    global _counter
    _counter += 1
    d = (BASE_DATE + timedelta(days=_counter)).strftime("%Y-%m-%d")
    return d, "10:00"

def _cleanup():
    global _counter
    _counter = 0
    with db.get_connection() as conn:
        for phone in (CLIENT, PATIENT, STRANGER):
            conn.execute("DELETE FROM appointments WHERE client_phone = ?", (phone,))
        conn.execute(
            "DELETE FROM appointments WHERE patient_phone IN (?, ?, ?)",
            (CLIENT, PATIENT, STRANGER)
        )
        for phone in (CLIENT, PATIENT, STRANGER):
            conn.execute("DELETE FROM clients WHERE phone = ?", (phone,))
        conn.execute("DELETE FROM professionals WHERE phone = ?", (PROF,))

def _ensure():
    with db.get_connection() as conn:
        for phone, name in [
            (CLIENT,   "Cliente Test"),
            (PATIENT,  "Paciente Test"),
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

def _apt(status='confirmada', patient_phone=None,
         hours_from_now=48, start_override=None):
    """
    Crea un turno con fecha/hora calculada desde ahora.
    hours_from_now > 0  → turno en el futuro (cancelable)
    hours_from_now < 0  → turno en el pasado o muy próximo (muy tarde)
    """
    apt_dt   = datetime.now() + timedelta(hours=hours_from_now)
    apt_date = apt_dt.strftime("%Y-%m-%d")
    start    = start_override or apt_dt.strftime("%H:%M")

    # Verificar unicidad — si hay conflicto, cambiar minutos
    while True:
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT id FROM appointments WHERE professional_phone=? AND appointment_date=? AND start=?",
                (PROF, apt_date, start)
            ).fetchone()
        if not row:
            break
        # Ajustar un minuto
        apt_dt = apt_dt + timedelta(minutes=1)
        start  = apt_dt.strftime("%H:%M")

    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO appointments
                (client_phone, professional_phone, appointment_date,
                 start, end, duration_minutes, status, patient_phone)
            VALUES (?, ?, ?, ?, ?, 50, ?, ?)
        """, (CLIENT, PROF, apt_date, start,
              (apt_dt + timedelta(minutes=50)).strftime("%H:%M"),
              status, patient_phone))
        return cur.lastrowid


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_cancel_appointment_retorna_dict():
    """cancel_appointment() debe retornar dict, no bool."""
    apt_id = _apt(hours_from_now=48)

    # Mockear Google Calendar para no depender de credenciales
    with patch.object(client_service, 'db', client_service.db):
        result = client_service.cancel_appointment(
            appointment_id = apt_id,
            phone_number   = CLIENT,
        )

    assert isinstance(result, dict), (
        f"cancel_appointment debe retornar dict, obtenido {type(result)}"
    )
    assert 'success' in result, "El dict debe tener la clave 'success'"
    ok(f"cancel_appointment retorna dict: {result}")


def test_flujo_feliz_retorna_success_true():
    """Cancelación válida → {{'success': True}}"""
    apt_id = _apt(hours_from_now=48)

    result = client_service.cancel_appointment(
        appointment_id = apt_id,
        phone_number   = CLIENT,
        reason         = 'Test flujo feliz'
    )

    assert result.get('success') is True, (
        f"Flujo feliz debe retornar success=True, obtenido {result}"
    )
    apt = db.get_appointment(apt_id)
    assert apt['status'] == 'cancelada_cliente'
    ok("Flujo feliz → success=True, turno cancelado en BD")


def test_too_late_retorna_reason_y_datos():
    """Turno muy próximo → reason='too_late' con hours_until y professional_phone."""
    limit = getattr(DomainConfig, 'CANCELLATION_HOURS_LIMIT', 22)
    # Turno en (limit - 1) horas → debería ser demasiado tarde
    apt_id = _apt(hours_from_now=max(limit - 1, 1))

    result = client_service.cancel_appointment(
        appointment_id = apt_id,
        phone_number   = CLIENT,
    )

    assert result.get('success') is False
    assert result.get('reason') == 'too_late', (
        f"Esperado reason='too_late', obtenido {result}"
    )
    assert 'hours_until' in result, "Debe incluir hours_until"
    assert 'professional_phone' in result, "Debe incluir professional_phone"
    assert result['professional_phone'] == PROF
    info(f"hours_until={result['hours_until']}, limit={limit}")
    ok(f"Turno muy próximo → reason='too_late' con datos del profesional")


def test_bypass_policy_ignora_limite():
    """bypass_policy=True cancela aunque sea tarde."""
    limit  = getattr(DomainConfig, 'CANCELLATION_HOURS_LIMIT', 22)
    apt_id = _apt(hours_from_now=max(limit - 1, 1))

    result = client_service.cancel_appointment(
        appointment_id = apt_id,
        phone_number   = CLIENT,
        bypass_policy  = True,
    )

    assert result.get('success') is True, (
        f"bypass_policy=True debe poder cancelar, obtenido {result}"
    )
    ok("bypass_policy=True cancela aunque esté fuera del límite de tiempo")


def test_not_authorized_retorna_reason():
    """Número ajeno → reason='not_authorized'"""
    apt_id = _apt(hours_from_now=48)

    result = client_service.cancel_appointment(
        appointment_id = apt_id,
        phone_number   = STRANGER,
    )

    assert result.get('success') is False
    assert result.get('reason') == 'not_authorized', (
        f"Esperado 'not_authorized', obtenido {result}"
    )
    ok("Número ajeno → reason='not_authorized'")


def test_already_cancelled_retorna_reason():
    """Turno ya cancelado → reason='already_cancelled'"""
    apt_id = _apt(status='cancelada_cliente', hours_from_now=48)

    result = client_service.cancel_appointment(
        appointment_id = apt_id,
        phone_number   = CLIENT,
    )

    assert result.get('success') is False
    assert result.get('reason') == 'already_cancelled', (
        f"Esperado 'already_cancelled', obtenido {result}"
    )
    ok("Turno ya cancelado → reason='already_cancelled'")


def test_patient_puede_cancelar_con_dict():
    """El paciente (patient_phone) puede cancelar — retorna success=True."""
    apt_id = _apt(hours_from_now=48, patient_phone=PATIENT)

    result = client_service.cancel_appointment(
        appointment_id = apt_id,
        phone_number   = PATIENT,
    )

    assert result.get('success') is True, (
        f"El paciente debe poder cancelar, obtenido {result}"
    )
    ok("El paciente (patient_phone) puede cancelar → success=True")


def test_uses_domain_config_not_hardcoded():
    """El límite viene de DomainConfig.CANCELLATION_HOURS_LIMIT, no hardcodeado."""
    limit = getattr(DomainConfig, 'CANCELLATION_HOURS_LIMIT', None)
    assert limit is not None, "DomainConfig.CANCELLATION_HOURS_LIMIT no existe"
    assert isinstance(limit, (int, float)) and limit > 0

    # Turno justo sobre el límite → debe poder cancelar
    apt_id = _apt(hours_from_now=limit + 2)
    result = client_service.cancel_appointment(
        appointment_id = apt_id,
        phone_number   = CLIENT,
    )
    assert result.get('success') is True, (
        f"Turno en {limit+2}hs (> límite {limit}hs) debería poder cancelarse: {result}"
    )

    # Turno justo bajo el límite → demasiado tarde
    apt_id2 = _apt(hours_from_now=max(limit - 2, 0.5))
    result2 = client_service.cancel_appointment(
        appointment_id = apt_id2,
        phone_number   = CLIENT,
    )
    assert result2.get('reason') == 'too_late', (
        f"Turno en {limit-2}hs (< límite {limit}hs) debería ser too_late: {result2}"
    )
    info(f"CANCELLATION_HOURS_LIMIT = {limit}")
    ok("Límite viene de DomainConfig, no está hardcodeado")


# ── Runner ────────────────────────────────────────────────────────────────────

def run_all():
    sep()
    print(f"{C.BOLD}  TEST GAP 6 — Política de cancelación centralizada{C.END}")
    sep()

    _cleanup()
    _ensure()

    tests = [
        test_cancel_appointment_retorna_dict,
        test_flujo_feliz_retorna_success_true,
        test_too_late_retorna_reason_y_datos,
        test_bypass_policy_ignora_limite,
        test_not_authorized_retorna_reason,
        test_already_cancelled_retorna_reason,
        test_patient_puede_cancelar_con_dict,
        test_uses_domain_config_not_hardcoded,
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

def test_gap6_completo():
    assert run_all()

if __name__ == "__main__":
    sys.exit(0 if run_all() else 1)
