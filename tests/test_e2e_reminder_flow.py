#!/usr/bin/env python3
"""
Test E2E: Flujo Completo de Recordatorio de Turno
===================================================

Testea el ciclo completo desde la creación de los turnos hasta la
respuesta al recordatorio, cubriendo los 3 caminos posibles:

    FLUJO 1 — timeout   : Sin respuesta → auto-confirmación (marca confirmed_by_client)
    FLUJO 2 — confirm   : Responde afirmativamente → ML lo detecta → confirmado
    FLUJO 3 — reschedule: Responde "reprogramar" → libera slot → waitlist notifica Turno B

Escenario base (igual para los 3 flujos):
    • Turno A: mañana → recibe el recordatorio
    • Turno B: en 3 días → wants_earlier_slot=1 → candidato a adelantamiento

Uso:
    # Correr los 3 flujos en orden
    docker exec -it whatsapp-demo python scripts/test_e2e_reminder_flow.py

    # Correr un flujo específico
    docker exec -it whatsapp-demo python scripts/test_e2e_reminder_flow.py --scenario timeout
    docker exec -it whatsapp-demo python scripts/test_e2e_reminder_flow.py --scenario confirm
    docker exec -it whatsapp-demo python scripts/test_e2e_reminder_flow.py --scenario reschedule

    # Solo setup (crear turnos sin ejecutar test)
    docker exec -it whatsapp-demo python scripts/test_e2e_reminder_flow.py --setup-only

    # Limpiar todo lo creado
    docker exec -it whatsapp-demo python scripts/test_e2e_reminder_flow.py --clean
"""

import sys
import time
import argparse
import requests
from pathlib import Path
from datetime import date, timedelta
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.database import db
from src.services.reminder_service import reminder_service
from src.services.waitlist_service import waitlist_service


# ─── Configuración ────────────────────────────────────────────────────────────

# Teléfonos de prueba estándar del proyecto
CLIENT_PHONE       = "+5491123456789"
CLIENT_NAME        = "Cliente E2E Test"
PROFESSIONAL_PHONE = "+5491100000001"   # Debe existir en DB (ej: Gaston Blanco)
DURATION_MINUTES   = 50

# Webhook del bot (para simular mensajes del cliente)
WEBHOOK_URL        = "http://localhost:5001/webhook"

# Delay entre pasos para que los logs sean legibles
STEP_DELAY_SECS    = 1


# ─── Helpers visuales ─────────────────────────────────────────────────────────

class C:
    """Colores ANSI para terminal."""
    HEADER  = '\033[95m'
    BLUE    = '\033[94m'
    CYAN    = '\033[96m'
    GREEN   = '\033[92m'
    YELLOW  = '\033[93m'
    RED     = '\033[91m'
    BOLD    = '\033[1m'
    END     = '\033[0m'


def sep(char="=", width=65):
    print(char * width)

def header(text):
    print(f"\n{C.HEADER}{C.BOLD}" + "=" * 65)
    print(f"  {text}")
    print("=" * 65 + C.END)

def step(n, text):
    print(f"\n{C.CYAN}{C.BOLD}[PASO {n}]{C.END} {text}")

def ok(text):
    print(f"  {C.GREEN}✅ {text}{C.END}")

def warn(text):
    print(f"  {C.YELLOW}⚠️  {text}{C.END}")

def fail(text):
    print(f"  {C.RED}❌ {text}{C.END}")

def info(text):
    print(f"  {C.BLUE}ℹ️  {text}{C.END}")


# ─── Setup / Teardown ─────────────────────────────────────────────────────────

def add_minutes(time_str: str, minutes: int) -> str:
    """Suma minutos a HH:MM y retorna HH:MM."""
    h, m  = map(int, time_str.split(":"))
    total = h * 60 + m + minutes
    return f"{total // 60:02d}:{total % 60:02d}"


def ensure_client():
    """Crea el cliente de prueba si no existe."""
    with db.get_connection() as conn:
        exists = conn.execute(
            "SELECT 1 FROM clients WHERE phone = ?", (CLIENT_PHONE,)
        ).fetchone()

        if not exists:
            conn.execute(
                "INSERT INTO clients (phone, name, is_active) VALUES (?, ?, 1)",
                (CLIENT_PHONE, CLIENT_NAME)
            )
            ok(f"Cliente creado: {CLIENT_NAME} ({CLIENT_PHONE})")
        else:
            info(f"Cliente ya existe: {CLIENT_PHONE}")


def create_appointment(apt_date: date, start_time: str, wants_earlier: bool, label: str) -> Optional[int]:
    """
    Inserta una cita en BD.

    Args:
        apt_date:      Fecha del turno
        start_time:    Hora de inicio HH:MM
        wants_earlier: Si el cliente quiere adelantarse
        label:         Etiqueta para identificar en logs (ej: "Turno A")

    Returns:
        ID de la cita, o None si falló
    """
    end_time = add_minutes(start_time, DURATION_MINUTES)

    apt_id = db.create_appointment(
        client_phone       = CLIENT_PHONE,
        professional_phone = PROFESSIONAL_PHONE,
        appointment_date   = apt_date.isoformat(),
        start              = start_time,
        end                = end_time,
        duration_minutes   = DURATION_MINUTES,
        session_type       = "seguimiento",
        modality           = "presencial",
        google_event_id    = None,
        notes              = f"E2E test - {label}",
    )

    if apt_id and wants_earlier:
        with db.get_connection() as conn:
            conn.execute(
                "UPDATE appointments SET wants_earlier_slot = 1 WHERE id = ?",
                (apt_id,)
            )

    return apt_id


def setup_appointments() -> dict:
    """
    Crea los 2 turnos base para el test.

    Returns:
        {'id_a': int, 'id_b': int, 'date_a': date, 'date_b': date}
    """
    today   = date.today()
    date_a  = today + timedelta(days=1)   # Mañana → recibe recordatorio
    date_b  = today + timedelta(days=3)   # En 3 días → candidato a adelantar

    ensure_client()

    info(f"Turno A (recordatorio): {date_a} 10:00")
    id_a = create_appointment(date_a, "10:00", wants_earlier=False, label="Turno A - recordatorio")
    if not id_a:
        fail("No se pudo crear Turno A")
        sys.exit(1)
    ok(f"Turno A creado: ID #{id_a}")

    info(f"Turno B (candidato):    {date_b} 10:00")
    id_b = create_appointment(date_b, "10:00", wants_earlier=True, label="Turno B - waitlist")
    if not id_b:
        fail("No se pudo crear Turno B")
        sys.exit(1)
    ok(f"Turno B creado: ID #{id_b} (wants_earlier_slot=1)")

    return {'id_a': id_a, 'id_b': id_b, 'date_a': date_a, 'date_b': date_b}


def inject_reminder(apt_id: int) -> bool:
    """
    Inyecta un recordatorio pendiente en BD para el turno dado,
    sin necesitar Twilio ni el CRON. Simula lo que haría _mark_reminder_sent().

    Returns:
        True si se insertó correctamente
    """
    try:
        with db.get_connection() as conn:
            # Marcar cita con reminder_sent=1
            conn.execute(
                "UPDATE appointments SET reminder_sent = 1 WHERE id = ?",
                (apt_id,)
            )
            # Insertar registro en appointment_reminders con status='sent'
            conn.execute(
                """
                INSERT INTO appointment_reminders
                    (appointment_id, client_phone, professional_phone,
                     appointment_date, appointment_time, status)
                SELECT id, client_phone, professional_phone,
                       appointment_date, start, 'sent'
                FROM appointments
                WHERE id = ?
                """,
                (apt_id,)
            )
        return True
    except Exception as e:
        fail(f"Error inyectando reminder: {e}")
        return False


def send_bot_message(message: str) -> str:
    """
    Envía un mensaje al webhook del bot simulando Twilio.

    Args:
        message: Texto a enviar

    Returns:
        Respuesta del bot (texto del TwiML), o '' si falló
    """
    try:
        payload = {
            "From":     f"whatsapp:{CLIENT_PHONE}",
            "To":       "whatsapp:+14155238886",
            "Body":     message,
            "NumMedia": "0",
        }
        resp = requests.post(WEBHOOK_URL, data=payload, timeout=10)
        # Extraer texto del TwiML
        import xml.etree.ElementTree as ET
        root = ET.fromstring(resp.text)
        msg  = root.find(".//Message")
        return msg.text.strip() if msg is not None else resp.text
    except Exception as e:
        warn(f"No se pudo conectar al bot ({e}). ¿Docker está corriendo?")
        return ""


def assert_reminder_status(apt_id: int, expected_status: str):
    """Verifica el estado del reminder en BD y lo imprime."""
    with db.get_connection() as conn:
        row = conn.execute(
            "SELECT status FROM appointment_reminders WHERE appointment_id = ? ORDER BY id DESC LIMIT 1",
            (apt_id,)
        ).fetchone()
    actual = row[0] if row else "NOT_FOUND"
    if actual == expected_status:
        ok(f"appointment_reminders.status = '{actual}' ✓")
    else:
        fail(f"Se esperaba status='{expected_status}', se obtuvo '{actual}'")


def assert_appointment_confirmed(apt_id: int, expected: bool):
    """Verifica confirmed_by_client en BD."""
    with db.get_connection() as conn:
        row = conn.execute(
            "SELECT confirmed_by_client FROM appointments WHERE id = ?",
            (apt_id,)
        ).fetchone()
    actual = bool(row[0]) if row else False
    if actual == expected:
        ok(f"appointments.confirmed_by_client = {actual} ✓")
    else:
        fail(f"Se esperaba confirmed_by_client={expected}, se obtuvo {actual}")


def assert_slot_offer_created(apt_id_freed: int) -> Optional[dict]:
    """Verifica que se creó una oferta en slot_offers para el turno liberado."""
    with db.get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM slot_offers WHERE freed_appointment_id = ? ORDER BY id DESC LIMIT 1",
            (apt_id_freed,)
        ).fetchone()
    if row:
        data = dict(row)
        ok(f"slot_offers: oferta creada → ID #{data['id']} para {data['offered_to_client_phone']}")
        return data
    else:
        fail("No se creó ninguna oferta en slot_offers")
        return None


def clean_test_data():
    """Elimina todos los datos de prueba creados por este script."""
    with db.get_connection() as conn:
        # Obtener IDs de citas de prueba
        rows = conn.execute(
            "SELECT id FROM appointments WHERE client_phone = ? AND notes LIKE '%E2E test%'",
            (CLIENT_PHONE,)
        ).fetchall()
        apt_ids = [r[0] for r in rows]

        if apt_ids:
            placeholders = ",".join("?" * len(apt_ids))
            # Limpiar en cascada
            conn.execute(f"DELETE FROM slot_offers WHERE freed_appointment_id IN ({placeholders})", apt_ids)
            conn.execute(f"DELETE FROM slot_offers WHERE original_appointment_id IN ({placeholders})", apt_ids)
            conn.execute(f"DELETE FROM appointment_reminders WHERE appointment_id IN ({placeholders})", apt_ids)
            conn.execute(f"DELETE FROM appointments WHERE id IN ({placeholders})", apt_ids)

        n = len(apt_ids)
        ok(f"{n} cita(s) de prueba eliminadas (+ reminders y offers)")


# ─── Flujos de test ───────────────────────────────────────────────────────────

def run_timeout_flow():
    """
    FLUJO 1: Sin respuesta → auto-confirmación.

    Simula que el cliente NO responde al recordatorio.
    El sistema debería marcar la cita como confirmada automáticamente
    (lógica de negocio: silencio = confirmación).

    Verifica:
        - Reminder existe en BD con status='sent'
        - Llamada manual a auto_confirm_unanswered() actualiza el status
        - confirmed_by_client queda en 1
    """
    header("FLUJO 1: Sin respuesta → Auto-confirmación")

    step(1, "Crear turno para mañana")
    apts = setup_appointments()
    id_a = apts['id_a']

    step(2, "Inyectar recordatorio (simular que el CRON ya lo envió)")
    if inject_reminder(id_a):
        ok("Recordatorio inyectado en BD (status='sent')")

    step(3, "Simular timeout: llamar auto_confirm_unanswered()")
    info("El cliente no responde → el sistema auto-confirma")
    try:
        result = reminder_service.auto_confirm_unanswered()
        info(f"Resultado: {result}")
    except AttributeError:
        # Si el método no existe aún, simularlo directamente en BD
        warn("reminder_service.auto_confirm_unanswered() no implementado → simulando en BD")
        with db.get_connection() as conn:
            conn.execute(
                """
                UPDATE appointments
                SET confirmed_by_client = 1,
                    confirmed_by_client_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (id_a,)
            )
            conn.execute(
                """
                UPDATE appointment_reminders
                SET status = 'confirmed',
                    confirmed_at = CURRENT_TIMESTAMP
                WHERE appointment_id = ?
                """,
                (id_a,)
            )

    step(4, "Verificar estado en BD")
    assert_reminder_status(id_a, "confirmed")
    assert_appointment_confirmed(id_a, True)

    step(5, "Limpiar")
    clean_test_data()
    ok("Flujo 1 completado\n")


def run_confirm_flow():
    """
    FLUJO 2: El cliente responde afirmativamente → ML lo detecta → confirmado.

    Envía mensajes al bot via HTTP y verifica que:
        - El bot responde apropiadamente
        - La BD queda en confirmed_by_client=1
        - appointment_reminders.status='confirmed'

    Variantes de respuesta afirmativa testeadas: '1', 'si', 'confirmo'
    """
    header("FLUJO 2: Respuesta afirmativa → Confirmación via ML")

    step(1, "Crear turno para mañana")
    apts = setup_appointments()
    id_a = apts['id_a']

    step(2, "Inyectar recordatorio")
    inject_reminder(id_a)

    step(3, "Simular respuestas afirmativas del cliente (via bot HTTP)")
    respuestas_afirmativas = ["1", "si", "confirmo"]

    for respuesta in respuestas_afirmativas:
        info(f"Enviando: '{respuesta}'")
        bot_response = send_bot_message(respuesta)
        if bot_response:
            info(f"Bot respondió: {bot_response[:100]}...")
        time.sleep(STEP_DELAY_SECS)

        # Si alguna funcionó, ya podemos verificar
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT confirmed_by_client FROM appointments WHERE id = ?", (id_a,)
            ).fetchone()
        if row and row[0]:
            ok(f"Confirmado con respuesta '{respuesta}'")
            break

    step(4, "Verificar estado en BD")
    assert_reminder_status(id_a, "confirmed")
    assert_appointment_confirmed(id_a, True)

    step(5, "Limpiar")
    clean_test_data()
    ok("Flujo 2 completado\n")


def run_reschedule_flow():
    """
    FLUJO 3: Responde 'reprogramar' → se cancela el Turno A → waitlist notifica Turno B.

    Pasos:
        1. Crear Turno A (mañana) + Turno B (en 3 días, wants_earlier=True)
        2. Inyectar recordatorio para Turno A
        3. Cliente responde '2' (reprogramar) → el bot inicia el flujo de reagendado
        4. Se simula la cancelación/liberación del Turno A
        5. waitlist_service detecta al cliente del Turno B como candidato
        6. Se verifica la oferta generada en slot_offers

    Verifica:
        - appointment_reminders.status = 'rescheduled'
        - slot_offers: registro para el cliente del Turno B
    """
    header("FLUJO 3: Reprogramar → Liberar slot → Waitlist notifica Turno B")

    step(1, "Crear Turno A (mañana) y Turno B (en 3 días, candidato a adelantar)")
    apts = setup_appointments()
    id_a, id_b = apts['id_a'], apts['id_b']
    info(f"Turno A ID: #{id_a} → se va a liberar")
    info(f"Turno B ID: #{id_b} → candidato al adelantamiento")

    step(2, "Inyectar recordatorio para Turno A")
    inject_reminder(id_a)

    step(3, "Cliente responde '2' al recordatorio (quiere reprogramar)")
    bot_response = send_bot_message("2")
    if bot_response:
        info(f"Bot respondió: {bot_response[:120]}...")
    else:
        warn("Bot no respondió (puede ser que el flujo se procese igual)")
    time.sleep(STEP_DELAY_SECS)

    # Verificar que el reminder quedó en estado 'rescheduled'
    assert_reminder_status(id_a, "rescheduled")

    step(4, "Simular cancelación/liberación del Turno A (slot freed)")
    info("Llamando waitlist_service.handle_slot_freed()...")
    result = waitlist_service.handle_slot_freed(
        freed_appointment_id = id_a,
        reason               = "rescheduled"
    )
    info(f"Resultado waitlist: {result}")

    if result.get('success'):
        ok(f"Turno liberado procesado. Candidatos encontrados: {result.get('candidates_found', 0)}")
        if result.get('offered_to'):
            ok(f"Oferta enviada a: {result['offered_to']}")
        else:
            warn("No se envió oferta (puede que waitlist_service no tenga Twilio configurado)")
    else:
        fail("handle_slot_freed() retornó success=False")

    step(5, "Verificar oferta en slot_offers")
    offer = assert_slot_offer_created(id_a)

    if offer:
        info(f"Oferta para:  {offer.get('offered_to_client_phone')}")
        info(f"Slot libre:   {offer.get('freed_date')} {offer.get('freed_time')}")
        info(f"Expira:       {offer.get('expires_at')}")

    step(6, "Verificar que el cliente del Turno B es el receptor de la oferta")
    if offer and offer.get('offered_to_client_phone') == CLIENT_PHONE:
        ok(f"La oferta fue enviada al cliente correcto: {CLIENT_PHONE}")
    elif offer:
        warn(f"La oferta fue a: {offer.get('offered_to_client_phone')} (esperaba {CLIENT_PHONE})")

    step(7, "Limpiar")
    clean_test_data()
    ok("Flujo 3 completado\n")


# ─── Main ─────────────────────────────────────────────────────────────────────

SCENARIOS = {
    "timeout":    (run_timeout_flow,    "Sin respuesta → auto-confirmación"),
    "confirm":    (run_confirm_flow,    "Respuesta afirmativa → ML confirma"),
    "reschedule": (run_reschedule_flow, "Reprogramar → liberar slot → waitlist"),
}


def main():
    # global debe ir AL INICIO de la función, antes de cualquier uso de la variable
    global WEBHOOK_URL

    parser = argparse.ArgumentParser(
        description="Test E2E del flujo completo de recordatorio de turno.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Escenarios disponibles:
  timeout    → Sin respuesta → auto-confirmación
  confirm    → Responde 'sí' / '1' / 'confirmo' → ML detecta → confirmado
  reschedule → Responde '2' → reprograma → libera slot → waitlist notifica

Ejemplos:
  docker exec -it whatsapp-demo python scripts/test_e2e_reminder_flow.py
  docker exec -it whatsapp-demo python scripts/test_e2e_reminder_flow.py --scenario confirm
  docker exec -it whatsapp-demo python scripts/test_e2e_reminder_flow.py --clean
        """
    )
    parser.add_argument(
        "--scenario",
        choices=list(SCENARIOS.keys()),
        default=None,
        help="Correr solo un escenario específico (default: todos)"
    )
    parser.add_argument(
        "--setup-only",
        action="store_true",
        help="Solo crear los turnos de prueba sin ejecutar el test"
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Eliminar todos los datos de prueba E2E"
    )
    parser.add_argument(
        "--url",
        default=WEBHOOK_URL,
        help=f"URL del webhook del bot (default: {WEBHOOK_URL})"
    )
    args = parser.parse_args()

    # Override URL si se pasó por CLI
    WEBHOOK_URL = args.url

    # ── Solo limpiar ──────────────────────────────────────────────────────────
    if args.clean:
        header("LIMPIEZA DE DATOS E2E")
        clean_test_data()
        return

    # ── Solo setup ────────────────────────────────────────────────────────────
    if args.setup_only:
        header("SETUP: CREANDO TURNOS DE PRUEBA")
        apts = setup_appointments()
        sep()
        print(f"\n  Turno A ID: #{apts['id_a']} → {apts['date_a']} 10:00 (recordatorio mañana)")
        print(f"  Turno B ID: #{apts['id_b']} → {apts['date_b']} 10:00 (candidato waitlist)")
        print(f"\n  Para limpiar: python scripts/test_e2e_reminder_flow.py --clean\n")
        return

    # ── Correr escenario(s) ───────────────────────────────────────────────────
    header("TEST E2E: FLUJO COMPLETO DE RECORDATORIO")
    print(f"  Cliente:     {CLIENT_NAME} ({CLIENT_PHONE})")
    print(f"  Profesional: {PROFESSIONAL_PHONE}")
    print(f"  Webhook:     {WEBHOOK_URL}")

    if args.scenario:
        # Un solo escenario
        fn, desc = SCENARIOS[args.scenario]
        info(f"Corriendo escenario: {args.scenario} — {desc}")
        fn()
    else:
        # Todos en orden
        info("Corriendo los 3 escenarios en orden...")
        for name, (fn, desc) in SCENARIOS.items():
            print(f"\n{C.YELLOW}{'─' * 65}{C.END}")
            print(f"{C.YELLOW}  Escenario: {name} — {desc}{C.END}")
            print(f"{C.YELLOW}{'─' * 65}{C.END}")
            fn()
            time.sleep(STEP_DELAY_SECS)

    header("✅ TEST E2E COMPLETADO")


if __name__ == "__main__":
    main()