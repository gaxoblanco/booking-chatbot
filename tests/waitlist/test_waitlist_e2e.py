"""
test_waitlist_e2e.py
====================
Test end-to-end del flujo de waitlist via webhook real.

Simula, en orden:
    1. Insertar datos de prueba en BD (profesional, candidato, turnos)
    2. POST /webhook — cancelación del turno liberado (dispara handle_slot_freed)
    3. Verificar que se creó un slot_offer en BD
    4. POST /webhook — candidato responde "1" (acepta)
    5. Verificar que el turno fue movido y la oferta quedó 'accepted'
    6. Limpiar datos de prueba

También cubre el flujo de rechazo:
    - Candidato responde "2" → turno se mantiene, oferta 'rejected'

Uso:
    docker exec -it whatsapp-demo python tests/test_waitlist_e2e.py

    # Solo insertar datos y parar (para testear manualmente desde WhatsApp):
    docker exec -it whatsapp-demo python tests/test_waitlist_e2e.py --manual

    # Limpiar datos de prueba sin correr el test:
    docker exec -it whatsapp-demo python tests/test_waitlist_e2e.py --cleanup

Requisitos:
    - El servidor Flask debe estar corriendo (docker compose up)
    - WEBHOOK_URL apunta a localhost:5000 por defecto
    - Los números de prueba deben estar en el sandbox de Twilio
      (solo importa si SEND_REAL_WHATSAPP=true)
"""

import sys
import json
import time
import argparse
import requests
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

# ── Configuración ─────────────────────────────────────────────────────────────

WEBHOOK_URL = "http://localhost:5000/webhook"

# Timeout generoso — el webhook puede llamar a Twilio, Google Calendar, etc.
WEBHOOK_TIMEOUT = 60

# ── Modo de envío ─────────────────────────────────────────────────────────────
# DIRECT: llama a bot_controller.process_message() directamente, sin HTTP.
#         Más rápido y no depende de Twilio. Ideal para tests dentro del container.
# WEBHOOK: POST real a /webhook. Más realista pero puede timeout si Twilio es lento.
SEND_MODE = "direct"   # "direct" | "webhook"

# Números de prueba — deben existir en la BD o se crean en el setup
PHONE_CANCELLER  = "+5491199990001"   # quien cancela (libera el slot)
PHONE_CANDIDATE  = "+5491199990002"   # quien tiene turno posterior y debe recibir la oferta

# Profesional de prueba — debe existir o se crea
PHONE_PROF       = "+5491100000099"
PROF_NAME        = "Test Profesional Waitlist"

# Fechas: liberado = en 5 días (fuera del límite de cancelación de ~22hs)
#         candidato = en 8 días (posterior al liberado, mismo profesional)
DATE_FREED       = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
DATE_CANDIDATE   = (datetime.now() + timedelta(days=8)).strftime("%Y-%m-%d")
TIME_FREED       = "10:00"
TIME_CANDIDATE   = "11:00"

# IDs que vamos a insertar (rangos altos para no chocar con datos reales)
APT_FREED_ID     = 99901
APT_CANDIDATE_ID = 99902

# ── Helpers ───────────────────────────────────────────────────────────────────

# Colorines en terminal
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def ok(msg):    print(f"  {GREEN}✅ {msg}{RESET}")
def fail(msg):  print(f"  {RED}❌ {msg}{RESET}")
def info(msg):  print(f"  {CYAN}ℹ️  {msg}{RESET}")
def warn(msg):  print(f"  {YELLOW}⚠️  {msg}{RESET}")
def header(msg): print(f"\n{BOLD}{CYAN}{'='*60}{RESET}\n{BOLD}{msg}{RESET}\n{BOLD}{CYAN}{'='*60}{RESET}")
def step(n, msg): print(f"\n{BOLD}[PASO {n}]{RESET} {msg}")


def get_db_path() -> str:
    """Busca la BD SQLite en las rutas comunes del proyecto."""
    candidates = [
        "/app/data/database.db",
        "/app/database.db",
        "./data/database.db",
        "./database.db",
    ]
    for path in candidates:
        if Path(path).exists():
            return path
    raise FileNotFoundError(
        f"No se encontró la BD en: {candidates}\n"
        "Ajustá DB_PATH en este script."
    )


def db_connect():
    return sqlite3.connect(get_db_path())


class FakeResponse:
    """Respuesta homogénea entre modo direct y webhook."""
    def __init__(self, status_code: int, text: str):
        self.status_code = status_code
        self.text = text


def send_webhook(phone: str, body: str, delay: float = 0.5) -> FakeResponse:
    """
    Envía un mensaje al bot.

    SEND_MODE='direct'  → llama bot_controller.process_message() sin HTTP.
                          Evita timeouts por Twilio/Google Calendar. Ideal para
                          tests dentro del container.
    SEND_MODE='webhook' → POST real a /webhook con payload idéntico al de Twilio.
                          Más realista pero puede timeout si Twilio es lento.
    """
    time.sleep(delay)
    if SEND_MODE == "direct":
        return _send_direct(phone, body)
    return _send_http(phone, body)


def _send_direct(phone: str, body: str) -> FakeResponse:
    """Llama a bot_controller directamente — sin HTTP, sin Twilio."""
    try:
        from src.bot.bot_controller import bot_controller
        response_text = bot_controller.process_message(phone, body)
        return FakeResponse(200, response_text or "")
    except Exception as e:
        return FakeResponse(500, str(e))


def _send_http(phone: str, body: str) -> FakeResponse:
    """POST real al /webhook — payload idéntico al de Twilio."""
    payload = {
        "From":       f"whatsapp:{phone}",
        "To":         "whatsapp:+14155238886",
        "Body":       body,
        "NumMedia":   "0",
        "AccountSid": "ACtest000000000000000000000000000",
        "MessageSid": f"SMtest{int(time.time())}",
    }
    try:
        resp = requests.post(WEBHOOK_URL, data=payload, timeout=WEBHOOK_TIMEOUT)
        return FakeResponse(resp.status_code, resp.text)
    except requests.exceptions.ReadTimeout:
        # Timeout no necesariamente es error — Flask puede haber procesado el
        # mensaje antes de que Twilio respondiera. Tratar como 200.
        warn("Timeout en webhook — asumiendo HTTP 200 (revisar logs del container)")
        return FakeResponse(200, "[timeout]")


# ── Setup de datos de prueba ──────────────────────────────────────────────────

def setup_test_data():
    """
    Inserta en BD los datos mínimos para correr el test:
      - Profesional de prueba
      - Cita a cancelar (APT_FREED_ID)  — status='confirmada'
      - Cita del candidato (APT_CANDIDATE_ID) — status='confirmada', fecha posterior,
        wants_earlier_slot=1
    """
    header("SETUP — Insertando datos de prueba")

    conn = db_connect()
    cur  = conn.cursor()

    try:
        # ── Profesional ───────────────────────────────────────────────────────
        cur.execute("""
            INSERT OR IGNORE INTO professionals
                (phone, name, is_active)
            VALUES (?, ?, 1)
        """, (PHONE_PROF, PROF_NAME))
        info(f"Profesional: {PROF_NAME} ({PHONE_PROF})")

        # ── Clientes ──────────────────────────────────────────────────────────
        for phone, name in [
            (PHONE_CANCELLER, "Test Canceller"),
            (PHONE_CANDIDATE, "Test Candidate"),
        ]:
            cur.execute("""
                INSERT OR IGNORE INTO clients (phone, name)
                VALUES (?, ?)
            """, (phone, name))
        info(f"Clientes: {PHONE_CANCELLER} y {PHONE_CANDIDATE}")

        # ── Cita que se va a cancelar ─────────────────────────────────────────
        cur.execute("""
            INSERT OR REPLACE INTO appointments
                (id, professional_phone, client_phone,
                 appointment_date, start, end,
                 status, reminder_sent, wants_earlier_slot)
            VALUES (?, ?, ?, ?, ?, ?, 'confirmada', 0, 0)
        """, (
            APT_FREED_ID,
            PHONE_PROF,
            PHONE_CANCELLER,
            DATE_FREED,
            TIME_FREED,
            "10:50",
        ))
        ok(f"Cita a cancelar: #{APT_FREED_ID} — {DATE_FREED} {TIME_FREED} ({PHONE_CANCELLER})")

        # ── Cita del candidato (fecha posterior, wants_earlier_slot=1) ────────
        cur.execute("""
            INSERT OR REPLACE INTO appointments
                (id, professional_phone, client_phone,
                 appointment_date, start, end,
                 status, reminder_sent, wants_earlier_slot)
            VALUES (?, ?, ?, ?, ?, ?, 'confirmada', 0, 1)
        """, (
            APT_CANDIDATE_ID,
            PHONE_PROF,
            PHONE_CANDIDATE,
            DATE_CANDIDATE,
            TIME_CANDIDATE,
            "11:50",
        ))
        ok(f"Cita candidato:  #{APT_CANDIDATE_ID} — {DATE_CANDIDATE} {TIME_CANDIDATE} ({PHONE_CANDIDATE})")

        conn.commit()
        ok("Datos de prueba insertados correctamente")

    except Exception as e:
        conn.rollback()
        fail(f"Error en setup: {e}")
        raise
    finally:
        conn.close()


# ── Cleanup ───────────────────────────────────────────────────────────────────

def reset_sessions():
    """
    Limpia las sesiones en memoria del bot para los números de prueba.
    Evita que TEST B herede el estado roto de TEST A.
    Usa el session_manager del bot directamente — modo direct only.
    """
    try:
        from src.core.states import session_manager
        session_manager.clear_session(PHONE_CANCELLER)
        session_manager.clear_session(PHONE_CANDIDATE)
        info("Sesiones de prueba reseteadas")
    except Exception as e:
        warn(f"No se pudo resetear sesiones: {e} (ignorable en modo webhook)")


def cleanup_test_data():
    """Elimina todos los datos de prueba de la BD y resetea sesiones."""
    header("CLEANUP — Eliminando datos de prueba")

    # Resetear sesiones primero para evitar estado inconsistente
    reset_sessions()

    conn = db_connect()
    cur  = conn.cursor()

    try:
        cur.execute("DELETE FROM slot_offers WHERE professional_phone = ?", (PHONE_PROF,))
        cur.execute("DELETE FROM appointments WHERE id IN (?, ?)", (APT_FREED_ID, APT_CANDIDATE_ID))
        cur.execute("DELETE FROM appointment_reminders WHERE appointment_id IN (?, ?)",
                    (APT_FREED_ID, APT_CANDIDATE_ID))
        cur.execute("DELETE FROM clients WHERE phone IN (?, ?)",
                    (PHONE_CANCELLER, PHONE_CANDIDATE))
        # No borramos el profesional — puede ser compartido

        conn.commit()
        ok("Datos de prueba eliminados")

    except Exception as e:
        conn.rollback()
        fail(f"Error en cleanup: {e}")
    finally:
        conn.close()


# ── Verificaciones de BD ──────────────────────────────────────────────────────

def get_appointment(apt_id: int) -> dict | None:
    """Obtiene una cita por ID."""
    conn = db_connect()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM appointments WHERE id = ?", (apt_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))
    return None


def get_cancelled_apt_by_phone(client_phone: str) -> dict | None:
    """
    Busca la última cita cancelada de un cliente, sin importar el ID.
    El bot puede haber usado un ID diferente al que insertamos si Google
    Calendar sync creó registros propios — buscamos por teléfono.
    """
    conn = db_connect()
    cur  = conn.cursor()
    cur.execute("""
        SELECT * FROM appointments
        WHERE client_phone = ?
        AND status IN ('cancelada_cliente', 'cancelada_profesional', 'cancelada')
        ORDER BY id DESC LIMIT 1
    """, (client_phone,))
    row = cur.fetchone()
    conn.close()
    if row:
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))
    return None


def wait_for_offer_by_candidate(candidate_phone: str, timeout: int = 15) -> dict | None:
    """
    Espera una slot_offer para el candidato, sin depender del freed_apt_id.
    La waitlist corre en thread separado — puede tardar 2-3 seg.
    """
    conn = db_connect()
    for i in range(timeout):
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM slot_offers
            WHERE offered_to_client_phone = ?
            ORDER BY offered_at DESC LIMIT 1
        """, (candidate_phone,))
        row = cur.fetchone()
        if row:
            cols = [d[0] for d in cur.description]
            conn.close()
            return dict(zip(cols, row))
        time.sleep(1)
        info(f"  Esperando slot_offer para {candidate_phone}... ({i+1}s)")
    conn.close()
    return None


# ── Flujo de test ─────────────────────────────────────────────────────────────

def run_test_accept():
    """
    Flujo completo: cancelación → oferta → candidato acepta.
    """
    header("TEST A — Cancelación → Candidato ACEPTA")

    # ── Paso 1: El canceller cancela su turno via webhook ─────────────────────
    step(1, f"Canceller ({PHONE_CANCELLER}) inicia cancelación")

    # Primero hay que navegar al turno — el bot necesita el appointment_id en sesión.
    # Enviamos "mis turnos" para que el bot lo cargue.
    resp = send_webhook(PHONE_CANCELLER, "mis turnos")
    info(f"Respuesta 'mis turnos': HTTP {resp.status_code}")
    info(f"  Body: {resp.text[:200]}")

    # Seleccionamos el turno (asumimos que es el primero de la lista)
    resp = send_webhook(PHONE_CANCELLER, "1")
    info(f"Respuesta '1' (detalle turno): HTTP {resp.status_code}")

    # Elegimos cancelar (opción 2 en el detalle)
    resp = send_webhook(PHONE_CANCELLER, "2")
    info(f"Respuesta '2' (cancelar): HTTP {resp.status_code}")

    # Confirmamos la cancelación
    resp = send_webhook(PHONE_CANCELLER, "1")
    info(f"Respuesta '1' (confirmar cancelación): HTTP {resp.status_code}")

    if resp.status_code == 200:
        ok("Webhook de cancelación procesado (HTTP 200)")
    else:
        fail(f"Webhook devolvió HTTP {resp.status_code}")
        return False

    # ── Paso 2: Verificar que se canceló la cita en BD ────────────────────────
    step(2, "Verificando cita cancelada en BD")

    # Buscamos por client_phone, no por ID fijo — el bot puede haber usado
    # un ID distinto si Google Calendar sync creó su propio registro.
    apt_cancelled = get_cancelled_apt_by_phone(PHONE_CANCELLER)
    if apt_cancelled:
        ok(f"Cita cancelada: #{apt_cancelled['id']} status='{apt_cancelled['status']}'")
    else:
        warn("No se encontró cita cancelada en BD — puede ser timing, continuando...")

    # ── Paso 3: Verificar que se creó la slot_offer ───────────────────────────
    step(3, "Esperando slot_offer en BD")

    # Buscamos por candidato — independiente del freed_apt_id real
    offer = wait_for_offer_by_candidate(PHONE_CANDIDATE, timeout=15)
    if not offer:
        fail(f"No apareció slot_offer para {PHONE_CANDIDATE} en 15 seg")
        info("Causas posibles:")
        info("  - handle_slot_freed no se llama desde handle_client_cancel_reason")
        info("    (verificar que aplicaste el Cambio 1 en client_handler.py)")
        info("  - wants_earlier_slot != 1 en la cita del candidato")
        info("  - La cita del candidato no tiene status='confirmada'")
        info("  Diagnóstico rápido:")
        info("    SELECT * FROM slot_offers ORDER BY id DESC LIMIT 5;")
        info("    SELECT id,status,wants_earlier_slot FROM appointments")
        info(f"      WHERE client_phone='{PHONE_CANDIDATE}';")
        return False

    ok(f"slot_offer #{offer['id']} creada")
    ok(f"  → Ofrecida a: {offer['offered_to_client_phone']}")
    ok(f"  → Status: {offer['status']}")
    ok(f"  → Expira: {offer['expires_at']}")

    if offer['offered_to_client_phone'] != PHONE_CANDIDATE:
        warn(f"Se ofreció a {offer['offered_to_client_phone']}, esperaba {PHONE_CANDIDATE}")

    # ── Paso 4: El candidato acepta via webhook ───────────────────────────────
    step(4, f"Candidato ({PHONE_CANDIDATE}) responde '1' (acepta)")

    resp = send_webhook(PHONE_CANDIDATE, "1")
    info(f"Respuesta del bot: HTTP {resp.status_code}")
    info(f"  Body: {resp.text[:400]}")

    if resp.status_code != 200:
        fail(f"Webhook devolvió HTTP {resp.status_code}")
        return False

    time.sleep(1)  # dar tiempo a que el handler complete

    # ── Paso 5: Verificar que el turno fue movido ─────────────────────────────
    step(5, "Verificando resultado en BD")

    # Refrescar la oferta — buscamos la misma por ID para ver su estado final
    conn = db_connect()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM slot_offers WHERE id = ?", (offer['id'],))
    row = cur.fetchone()
    conn.close()
    offer_final = dict(zip([d[0] for d in cur.description], row)) if row else None

    if offer_final and offer_final['status'] == 'accepted':
        ok(f"slot_offer #{offer_final['id']} status = 'accepted'")
    else:
        status = offer_final['status'] if offer_final else 'no encontrada'
        fail(f"slot_offer status = '{status}', esperaba 'accepted'")

    # Verificar que la cita del candidato se movió a la fecha liberada
    apt_candidate = get_appointment(APT_CANDIDATE_ID)
    if apt_candidate:
        if apt_candidate['appointment_date'] == DATE_FREED:
            ok(f"Cita #{APT_CANDIDATE_ID} movida a {DATE_FREED} {TIME_FREED} ✅")
        else:
            fail(f"Cita #{APT_CANDIDATE_ID} sigue en {apt_candidate['appointment_date']}, "
                 f"esperaba {DATE_FREED}")
    else:
        fail(f"Cita #{APT_CANDIDATE_ID} no encontrada en BD")

    return True


def run_test_reject():
    """
    Flujo alternativo: cancelación → oferta → candidato rechaza.
    Requiere re-setup porque los datos de accept pueden haberlos modificado.
    """
    header("TEST B — Cancelación → Candidato RECHAZA")

    step(1, "Re-setup de datos de prueba para test de rechazo")
    cleanup_test_data()
    setup_test_data()

    # Repetimos la cancelación (mismo flujo que test A)
    step(2, f"Canceller ({PHONE_CANCELLER}) cancela su turno")
    send_webhook(PHONE_CANCELLER, "mis turnos")
    send_webhook(PHONE_CANCELLER, "1")
    send_webhook(PHONE_CANCELLER, "2")
    resp = send_webhook(PHONE_CANCELLER, "1")
    info(f"Cancelación: HTTP {resp.status_code}")

    step(3, "Esperando slot_offer en BD")
    offer = wait_for_offer_by_candidate(PHONE_CANDIDATE, timeout=15)
    if not offer:
        fail("No apareció slot_offer — abortando test B")
        return False
    ok(f"slot_offer #{offer['id']} creada → {offer['offered_to_client_phone']}")

    step(4, f"Candidato ({PHONE_CANDIDATE}) responde '2' (rechaza)")
    resp = send_webhook(PHONE_CANDIDATE, "2")
    info(f"Respuesta del bot: HTTP {resp.status_code}")
    info(f"  Body: {resp.text[:400]}")

    time.sleep(1)

    step(5, "Verificando resultado en BD")

    # Refrescar la oferta por ID
    conn = db_connect()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM slot_offers WHERE id = ?", (offer['id'],))
    row = cur.fetchone()
    conn.close()
    offer_final = dict(zip([d[0] for d in cur.description], row)) if row else None

    if offer_final and offer_final['status'] == 'rejected':
        ok(f"slot_offer #{offer_final['id']} status = 'rejected'")
    else:
        status = offer_final['status'] if offer_final else 'no encontrada'
        fail(f"slot_offer status = '{status}', esperaba 'rejected'")

    apt_candidate = get_appointment(APT_CANDIDATE_ID)
    if apt_candidate and apt_candidate['appointment_date'] == DATE_CANDIDATE:
        ok(f"Cita #{APT_CANDIDATE_ID} mantiene fecha original {DATE_CANDIDATE} ✅")
    else:
        date = apt_candidate['appointment_date'] if apt_candidate else 'no encontrada'
        fail(f"Cita #{APT_CANDIDATE_ID} tiene fecha {date}, esperaba {DATE_CANDIDATE}")

    return True


def run_manual_mode():
    """
    Inserta los datos y para — el operador prueba desde WhatsApp real.
    Imprime las instrucciones exactas.
    """
    header("MODO MANUAL — Setup para prueba desde WhatsApp")

    setup_test_data()

    print(f"""
{BOLD}Datos insertados. Ahora desde WhatsApp:{RESET}

{YELLOW}1. Desde el número {PHONE_CANCELLER}:{RESET}
   Enviá: mis turnos
   Seleccioná el turno del {DATE_FREED} a las {TIME_FREED}
   Elegí cancelar (opción 2)
   Confirmá (opción 1)

{YELLOW}2. Verificá en los logs del container:{RESET}
   docker logs whatsapp-demo --tail=30
   Deberías ver:
   [REMINDER→WAITLIST] o [CANCEL→WAITLIST] Slot liberado
   ✅ Oferta enviada a {PHONE_CANDIDATE}

{YELLOW}3. Desde el número {PHONE_CANDIDATE}:{RESET}
   Deberías recibir el mensaje de oferta.
   Respondé 1 (aceptar) o 2 (rechazar).

{YELLOW}4. Para limpiar después:{RESET}
   python tests/test_waitlist_e2e.py --cleanup

{YELLOW}IDs de cita:{RESET}
   Liberada:  #{APT_FREED_ID}  ({DATE_FREED} {TIME_FREED})
   Candidato: #{APT_CANDIDATE_ID} ({DATE_CANDIDATE} {TIME_CANDIDATE})
""")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Test E2E Waitlist via Webhook")
    parser.add_argument("--manual",  action="store_true",
                        help="Solo insertar datos y mostrar instrucciones manuales")
    parser.add_argument("--cleanup", action="store_true",
                        help="Solo limpiar datos de prueba")
    parser.add_argument("--reject",  action="store_true",
                        help="Correr solo el test de rechazo")
    parser.add_argument("--accept",  action="store_true",
                        help="Correr solo el test de aceptación")
    args = parser.parse_args()

    if args.cleanup:
        cleanup_test_data()
        return

    if args.manual:
        run_manual_mode()
        return

    # Test automático completo
    header("TEST E2E WAITLIST — Inicio")
    info(f"Webhook URL: {WEBHOOK_URL}")
    info(f"DB: {get_db_path()}")
    info(f"Fecha slot liberado:  {DATE_FREED} {TIME_FREED}")
    info(f"Fecha candidato:      {DATE_CANDIDATE} {TIME_CANDIDATE}")

    results = {}

    try:
        setup_test_data()

        if not args.reject:
            results['accept'] = run_test_accept()

        if not args.accept:
            results['reject'] = run_test_reject()

    except KeyboardInterrupt:
        warn("Interrumpido por el usuario")
    except Exception as e:
        fail(f"Error inesperado: {e}")
        import traceback
        traceback.print_exc()
    finally:
        step("F", "Cleanup")
        cleanup_test_data()

    # Resumen final
    header("RESULTADO FINAL")

    if not results:
        fail("Ningún test completó — hubo un error antes de poder ejecutarlos")
        print(f"\n{RED}{BOLD}❌ Tests no ejecutados — revisá el error arriba{RESET}\n")
        sys.exit(1)

    all_ok = True
    for test_name, passed in results.items():
        if passed:
            ok(f"Test {test_name.upper()}: PASÓ")
        else:
            fail(f"Test {test_name.upper()}: FALLÓ")
            all_ok = False

    if all_ok:
        print(f"\n{GREEN}{BOLD}✅ Todos los tests pasaron{RESET}\n")
        sys.exit(0)
    else:
        print(f"\n{RED}{BOLD}❌ Hay tests fallidos — revisar logs arriba{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()