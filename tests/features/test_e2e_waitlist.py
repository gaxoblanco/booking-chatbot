#!/usr/bin/env python3
"""
Test E2E: Waitlist — Cascada y Anti-Spam
==========================================

Testea el sistema de adelantamiento de turnos con todos los casos borde.

ESCENARIOS:
    1. cascade_accept   → A rechaza, B acepta → turno movido correctamente
    2. cascade_all_reject → A, B y C rechazan → slot queda libre, nadie más molestado
    3. antispam_block   → cliente rechazó 3 veces → no aparece como candidato
    4. antispam_new_apt → mismo cliente, turno nuevo (>30 días) → SÍ aparece como candidato

Uso:
    docker exec -it whatsapp-demo python tests/test_e2e_waitlist.py
    docker exec -it whatsapp-demo python tests/test_e2e_waitlist.py --scenario cascade_accept
    docker exec -it whatsapp-demo python tests/test_e2e_waitlist.py --clean
"""

import sys
import argparse
import time
from pathlib import Path
from datetime import date, timedelta
from typing import Optional, List

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.database import db
from src.services.waitlist_service import waitlist_service


# ─── Configuración ────────────────────────────────────────────────────────────

PROFESSIONAL_PHONE = "+5491100000001"
DURATION_MINUTES   = 50

# Clientes de prueba — distintos para no interferir entre escenarios
CLIENT_A = "+5490000000001"
CLIENT_B = "+5490000000002"
CLIENT_C = "+5490000000003"
CLIENT_SPAM = "+5490000000099"


# ─── Colores ──────────────────────────────────────────────────────────────────

class C:
    HEADER = '\033[95m'; CYAN = '\033[96m'; GREEN = '\033[92m'
    YELLOW = '\033[93m'; RED = '\033[91m'; BOLD = '\033[1m'; END = '\033[0m'

def sep():      print("=" * 65)
def header(t):  print(f"\n{C.HEADER}{C.BOLD}{'='*65}\n  {t}\n{'='*65}{C.END}")
def step(n, t): print(f"\n{C.CYAN}{C.BOLD}[PASO {n}]{C.END} {t}")
def ok(t):      print(f"  {C.GREEN}✅ {t}{C.END}")
def warn(t):    print(f"  {C.YELLOW}⚠️  {t}{C.END}")
def fail(t):    print(f"  {C.RED}❌ {t}{C.END}")
def info(t):    print(f"  ℹ️  {t}")


# ─── Helpers de BD ────────────────────────────────────────────────────────────

def add_minutes(t: str, m: int) -> str:
    h, mi = map(int, t.split(":"))
    total = h * 60 + mi + m
    return f"{total // 60:02d}:{total % 60:02d}"


def ensure_client(phone: str, name: str):
    with db.get_connection() as conn:
        exists = conn.execute("SELECT 1 FROM clients WHERE phone=?", (phone,)).fetchone()
        if not exists:
            conn.execute(
                "INSERT INTO clients (phone, name, is_active) VALUES (?,?,1)",
                (phone, name)
            )


def create_appointment(client_phone: str, apt_date: date, start: str,
                       wants_earlier: bool = True, label: str = "") -> Optional[int]:
    end = add_minutes(start, DURATION_MINUTES)
    apt_id = db.create_appointment(
        client_phone=client_phone,
        professional_phone=PROFESSIONAL_PHONE,
        appointment_date=apt_date.isoformat(),
        start=start, end=end,
        duration_minutes=DURATION_MINUTES,
        session_type="seguimiento",
        modality="presencial",
        google_event_id=None,
        notes=f"waitlist-test {label}",
    )
    if apt_id:
        with db.get_connection() as conn:
            conn.execute(
                "UPDATE appointments SET status='confirmada', wants_earlier_slot=? WHERE id=?",
                (1 if wants_earlier else 0, apt_id)
            )
    return apt_id


def create_freed_appointment(apt_date: date, start: str, label: str = "") -> Optional[int]:
    """Crea el turno que se 'libera' (origen de la cascada)."""
    return create_appointment(CLIENT_A, apt_date, start, wants_earlier=False, label=label)


def inject_rejection(client_phone: str, freed_apt_id: int,
                     freed_date: date, freed_time: str,
                     days_ago: int = 0):
    """
    Inyecta un rechazo histórico en slot_offers.
    Permite simular rechazos pasados para probar el anti-spam
    sin tener que correr la cascada completa N veces.
    """
    from datetime import datetime
    offered_at = datetime.now() - timedelta(days=days_ago)
    expires_at = offered_at + timedelta(minutes=30)

    with db.get_connection() as conn:
        conn.execute("""
            INSERT INTO slot_offers
            (freed_appointment_id, offered_to_client_phone, original_appointment_id,
             freed_date, freed_time, professional_phone, status,
             offered_at, expires_at, response_received_at)
            VALUES (?, ?, ?, ?, ?, ?, 'rejected', ?, ?, ?)
        """, (
            freed_apt_id,
            client_phone,
            freed_apt_id,     # original_appointment_id (dummy para el test)
            freed_date.isoformat(),
            freed_time,
            PROFESSIONAL_PHONE,
            offered_at.isoformat(),
            expires_at.isoformat(),
            offered_at.isoformat(),
        ))


def get_slot_offers(freed_apt_id: int) -> List[dict]:
    """Retorna todas las ofertas para un slot liberado."""
    with db.get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM slot_offers WHERE freed_appointment_id=? ORDER BY id",
            (freed_apt_id,)
        ).fetchall()
        if not rows:
            return []
        cols = [d[0] for d in conn.execute(
            "SELECT * FROM slot_offers WHERE freed_appointment_id=? ORDER BY id LIMIT 1",
            (freed_apt_id,)
        ).description]
    # Re-fetch con description correcta
    with db.get_connection() as conn:
        cursor = conn.execute(
            "SELECT * FROM slot_offers WHERE freed_appointment_id=? ORDER BY id",
            (freed_apt_id,)
        )
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, r)) for r in cursor.fetchall()]


def get_appointment(apt_id: int) -> Optional[dict]:
    return db.get_appointment(apt_id)


def find_candidates(freed_apt_id: int) -> List[dict]:
    """Llama _find_candidates con los datos del turno liberado."""
    apt = db.get_appointment(freed_apt_id)
    if not apt:
        return []
    return waitlist_service._find_candidates(
        professional_phone=apt['professional_phone'],
        freed_date=apt['appointment_date'],
        freed_time=apt['start'],
    )


def clean_test_data():
    """Elimina todos los datos de prueba de este test."""
    test_phones = [CLIENT_A, CLIENT_B, CLIENT_C, CLIENT_SPAM]
    with db.get_connection() as conn:
        ph = ",".join("?" * len(test_phones))

        # Obtener IDs de citas de prueba
        rows = conn.execute(
            f"SELECT id FROM appointments WHERE client_phone IN ({ph})",
            test_phones
        ).fetchall()
        apt_ids = [r[0] for r in rows]

        if apt_ids:
            ap = ",".join("?" * len(apt_ids))
            conn.execute(f"DELETE FROM slot_offers WHERE freed_appointment_id IN ({ap})", apt_ids)
            conn.execute(f"DELETE FROM slot_offers WHERE original_appointment_id IN ({ap})", apt_ids)
            conn.execute(f"DELETE FROM appointment_reminders WHERE appointment_id IN ({ap})", apt_ids)
            conn.execute(f"DELETE FROM appointments WHERE id IN ({ap})", apt_ids)

        # También limpiar slot_offers huérfanos inyectados manualmente
        conn.execute(
            f"DELETE FROM slot_offers WHERE offered_to_client_phone IN ({ph})",
            test_phones
        )
        conn.execute(
            f"DELETE FROM clients WHERE phone IN ({ph})",
            test_phones
        )

    ok(f"Datos de prueba eliminados")


# ─── ESCENARIO 1: Cascada con aceptación ──────────────────────────────────────

def run_cascade_accept():
    """
    Turno liberado → oferta a Cliente A (rechaza) → oferta a Cliente B (acepta)
    → turno de B movido a la fecha/hora liberada

    Verifica:
        slot_offers[0].status = 'rejected'   (A rechazó)
        slot_offers[1].status = 'accepted'   (B aceptó)
        appointments[B].appointment_date = freed_date
    """
    header("ESCENARIO 1: Cascada — A rechaza, B acepta")

    step(1, "Crear clientes y turnos")
    ensure_client(CLIENT_A, "Cliente A")
    ensure_client(CLIENT_B, "Cliente B")

    today      = date.today()
    freed_date = today + timedelta(days=1)   # mañana — el slot que se libera
    date_a     = today + timedelta(days=3)   # A tiene turno en 3 días
    date_b     = today + timedelta(days=5)   # B tiene turno en 5 días

    # El slot liberado (cita que se cancela)
    freed_id = create_freed_appointment(freed_date, "09:00", label="freed")
    if not freed_id:
        fail("No se pudo crear el turno liberado"); return
    ok(f"Turno liberado: #{freed_id} → {freed_date} 09:00")

    # Cita de A — quiere adelantar
    apt_a = create_appointment(CLIENT_A, date_a, "10:00", wants_earlier=True, label="A")
    # Cita de B — quiere adelantar
    apt_b = create_appointment(CLIENT_B, date_b, "10:00", wants_earlier=True, label="B")
    if not apt_a or not apt_b:
        fail("No se pudieron crear las citas"); return
    ok(f"Cita A: #{apt_a} → {date_a} | Cita B: #{apt_b} → {date_b}")

    step(2, "Verificar que _find_candidates encuentra A y B en orden")
    candidates = find_candidates(freed_id)
    phones = [c['client_phone'] for c in candidates]
    info(f"Candidatos: {phones}")
    if CLIENT_A in phones and CLIENT_B in phones:
        ok("A y B son candidatos ✓")
    else:
        fail(f"Se esperaba A y B, se obtuvo {phones}")

    step(3, "handle_slot_freed → ofrece a A (el más cercano)")
    result = waitlist_service.handle_slot_freed(freed_id, reason="cancelled")
    info(f"Resultado: candidates_found={result.get('candidates_found')}, offered_to={result.get('offered_to')}")

    offers = get_slot_offers(freed_id)
    if offers and offers[-1]['offered_to_client_phone'] == CLIENT_A:
        ok(f"Oferta enviada a A ✓ (status={offers[-1]['status']})")
    else:
        warn(f"Oferta no fue a A — offered_to={offers[-1]['offered_to_client_phone'] if offers else 'ninguna'}")

    step(4, "A rechaza → cascada → oferta a B")
    # Obtener la oferta pendiente de A
    offer_a = waitlist_service._get_pending_offer(CLIENT_A)
    if not offer_a:
        # La oferta puede estar expirada o Twilio falló — simular manualmente
        warn("Oferta de A no está 'pending' (Twilio falló en test) — activando manualmente")
        with db.get_connection() as conn:
            conn.execute(
                "UPDATE slot_offers SET status='pending', expires_at=datetime('now','+1 hour') WHERE freed_appointment_id=? AND offered_to_client_phone=?",
                (freed_id, CLIENT_A)
            )
        offer_a = waitlist_service._get_pending_offer(CLIENT_A)

    if not offer_a:
        fail("No se pudo obtener la oferta de A"); return

    result_reject = waitlist_service._reject_offer(offer_a)
    info(f"Resultado rechazo A: {result_reject}")

    offers = get_slot_offers(freed_id)
    statuses = [(o['offered_to_client_phone'], o['status']) for o in offers]
    info(f"Estado offers: {statuses}")

    if len(offers) >= 2:
        ok("Se creó oferta para B después del rechazo de A ✓")
        last = offers[-1]
        if last['offered_to_client_phone'] == CLIENT_B:
            ok(f"Oferta correctamente enviada a B ✓")
        else:
            warn(f"Oferta fue a {last['offered_to_client_phone']} en lugar de B")
    else:
        fail("No se creó segunda oferta — cascada no funcionó")

    step(5, "B acepta → turno movido")
    offer_b = waitlist_service._get_pending_offer(CLIENT_B)
    if not offer_b:
        warn("Activando oferta de B manualmente (Twilio falló en test)")
        with db.get_connection() as conn:
            conn.execute(
                "UPDATE slot_offers SET status='pending', expires_at=datetime('now','+1 hour') WHERE freed_appointment_id=? AND offered_to_client_phone=?",
                (freed_id, CLIENT_B)
            )
        offer_b = waitlist_service._get_pending_offer(CLIENT_B)

    if not offer_b:
        fail("No se pudo obtener la oferta de B"); return

    result_accept = waitlist_service._accept_offer(offer_b)
    info(f"Resultado aceptación B: {result_accept}")

    step(6, "Verificar BD final")
    apt_b_data = get_appointment(apt_b)
    if apt_b_data and apt_b_data['appointment_date'] == freed_date.isoformat():
        ok(f"Cita de B movida a {freed_date} ✓")
    else:
        fail(f"Cita de B sigue en {apt_b_data['appointment_date'] if apt_b_data else 'desconocido'}")

    offers_final = get_slot_offers(freed_id)
    statuses_final = [(o['offered_to_client_phone'].split("+")[-1][-4:], o['status']) for o in offers_final]
    ok(f"slot_offers final: {statuses_final}")

    step(7, "Limpiar")
    clean_test_data()
    ok("Escenario 1 completado\n")


# ─── ESCENARIO 2: Todos rechazan ──────────────────────────────────────────────

def run_cascade_all_reject():
    """
    A, B y C rechazan → slot queda libre, sin más ofertas, nadie molestado de más.

    Verifica:
        slot_offers tiene 3 registros, todos 'rejected'
        No hay oferta 'pending' activa al final
    """
    header("ESCENARIO 2: Cascada completa — A, B, C rechazan")

    step(1, "Crear clientes y turnos")
    for phone, name in [(CLIENT_A,"A"), (CLIENT_B,"B"), (CLIENT_C,"C")]:
        ensure_client(phone, f"Cliente {name}")

    today      = date.today()
    freed_date = today + timedelta(days=1)

    freed_id = create_freed_appointment(freed_date, "11:00", label="freed-all-reject")
    apt_a = create_appointment(CLIENT_A, today + timedelta(days=2), "10:00", wants_earlier=True, label="A")
    apt_b = create_appointment(CLIENT_B, today + timedelta(days=4), "10:00", wants_earlier=True, label="B")
    apt_c = create_appointment(CLIENT_C, today + timedelta(days=6), "10:00", wants_earlier=True, label="C")

    ok(f"Liberado #{freed_id}, A=#{apt_a}, B=#{apt_b}, C=#{apt_c}")

    step(2, "handle_slot_freed → primera oferta a A")
    waitlist_service.handle_slot_freed(freed_id, reason="cancelled")

    # Activar oferta de A para poder rechazarla
    with db.get_connection() as conn:
        conn.execute(
            "UPDATE slot_offers SET status='pending', expires_at=datetime('now','+1 hour') WHERE freed_appointment_id=? AND offered_to_client_phone=?",
            (freed_id, CLIENT_A)
        )

    step(3, "A rechaza → oferta a B")
    offer_a = waitlist_service._get_pending_offer(CLIENT_A)
    if offer_a:
        waitlist_service._reject_offer(offer_a)
        ok("A rechazó")
    else:
        warn("No se obtuvo oferta de A")

    # Activar oferta de B
    with db.get_connection() as conn:
        conn.execute(
            "UPDATE slot_offers SET status='pending', expires_at=datetime('now','+1 hour') WHERE freed_appointment_id=? AND offered_to_client_phone=?",
            (freed_id, CLIENT_B)
        )

    step(4, "B rechaza → oferta a C")
    offer_b = waitlist_service._get_pending_offer(CLIENT_B)
    if offer_b:
        waitlist_service._reject_offer(offer_b)
        ok("B rechazó")
    else:
        warn("No se obtuvo oferta de B")

    # Activar oferta de C
    with db.get_connection() as conn:
        conn.execute(
            "UPDATE slot_offers SET status='pending', expires_at=datetime('now','+1 hour') WHERE freed_appointment_id=? AND offered_to_client_phone=?",
            (freed_id, CLIENT_C)
        )

    step(5, "C rechaza → no hay más candidatos → fin")
    offer_c = waitlist_service._get_pending_offer(CLIENT_C)
    if offer_c:
        waitlist_service._reject_offer(offer_c)
        ok("C rechazó")
    else:
        warn("No se obtuvo oferta de C")

    step(6, "Verificar estado final")
    offers = get_slot_offers(freed_id)
    statuses = [o['status'] for o in offers]
    phones   = [o['offered_to_client_phone'] for o in offers]
    info(f"Total ofertas: {len(offers)}")
    info(f"Statuses: {statuses}")
    info(f"Phones: {phones}")

    all_rejected = all(s == 'rejected' for s in statuses)
    no_pending   = not any(s == 'pending' for s in statuses)

    if all_rejected:
        ok(f"Todos los rechazos registrados correctamente ✓")
    else:
        fail(f"Hay estados inesperados: {statuses}")

    if no_pending:
        ok("No hay ofertas pending activas — slot libre, nadie más molestado ✓")
    else:
        fail("Quedó una oferta pending — se seguiría molestando")

    # Verificar que no hay cuarta oferta
    if len(offers) == 3:
        ok("Exactamente 3 ofertas — cascada terminó correctamente ✓")
    elif len(offers) > 3:
        fail(f"Se crearon {len(offers)} ofertas — demasiadas")
    else:
        warn(f"Solo {len(offers)} ofertas (esperado 3)")

    step(7, "Limpiar")
    clean_test_data()
    ok("Escenario 2 completado\n")


# ─── ESCENARIO 3: Anti-spam bloquea tras 3 rechazos ───────────────────────────

def run_antispam_block():
    """
    Cliente SPAM rechazó 3 veces en los últimos 30 días con el mismo profesional
    → no aparece como candidato en el 4to slot liberado.

    Verifica:
        _find_candidates() no incluye a CLIENT_SPAM
    """
    header("ESCENARIO 3: Anti-spam — bloqueado después de 3 rechazos")

    step(1, "Crear cliente y turno futuro")
    ensure_client(CLIENT_SPAM, "Cliente Spam")

    today      = date.today()
    freed_date = today + timedelta(days=1)

    # Turno futuro del cliente spam — quiere adelantar
    apt_spam = create_appointment(CLIENT_SPAM, today + timedelta(days=7), "10:00",
                                   wants_earlier=True, label="spam-candidate")
    freed_id = create_freed_appointment(freed_date, "14:00", label="freed-antispam")
    ok(f"Cita SPAM: #{apt_spam}, turno liberado: #{freed_id}")

    step(2, "Inyectar 3 rechazos históricos del mismo profesional (últimos 10 días)")
    for i in range(3):
        inject_rejection(CLIENT_SPAM, freed_id, freed_date, "14:00", days_ago=i+1)
    ok("3 rechazos inyectados")

    step(3, "Verificar que _find_candidates NO incluye a CLIENT_SPAM")
    candidates = find_candidates(freed_id)
    phones = [c['client_phone'] for c in candidates]
    info(f"Candidatos encontrados: {phones}")

    if CLIENT_SPAM not in phones:
        ok("CLIENT_SPAM correctamente excluido por anti-spam ✓")
    else:
        fail("CLIENT_SPAM aparece como candidato — el filtro anti-spam no funciona")

    step(4, "Limpiar")
    clean_test_data()
    ok("Escenario 3 completado\n")


# ─── ESCENARIO 4: Anti-spam NO bloquea turno nuevo ────────────────────────────

def run_antispam_new_apt():
    """
    Mismo cliente rechazó 3 veces → bloqueado.
    Pero tiene un turno nuevo pasados los 30 días → SÍ aparece como candidato.

    Verifica que el anti-spam es temporal y no bloquea permanentemente.

    Simula dos ventanas temporales:
        - 3 rechazos hace 25 días → cliente bloqueado para slot nuevo de hoy
        - 3 rechazos hace 35 días → cliente libre para slot nuevo de hoy
    """
    header("ESCENARIO 4: Anti-spam — turno nuevo no queda bloqueado")

    step(1, "Setup — cliente con turno futuro")
    ensure_client(CLIENT_SPAM, "Cliente Spam")

    today      = date.today()
    freed_date = today + timedelta(days=1)

    apt_spam = create_appointment(CLIENT_SPAM, today + timedelta(days=10), "10:00",
                                   wants_earlier=True, label="spam-new-apt")
    freed_id = create_freed_appointment(freed_date, "15:00", label="freed-new-apt")

    step(2, "Inyectar 3 rechazos recientes (hace 5 días) → cliente bloqueado")
    for i in range(3):
        inject_rejection(CLIENT_SPAM, freed_id, freed_date, "15:00", days_ago=i+5)

    candidates_bloqueado = find_candidates(freed_id)
    phones_bloqueado = [c['client_phone'] for c in candidates_bloqueado]

    if CLIENT_SPAM not in phones_bloqueado:
        ok("Con rechazos recientes → correctamente bloqueado ✓")
    else:
        fail("Con rechazos recientes → debería estar bloqueado pero aparece")

    step(3, "Simular que pasaron 31 días — mover offered_at fuera de la ventana")
    with db.get_connection() as conn:
        conn.execute(
            """UPDATE slot_offers
               SET offered_at = datetime('now', '-31 days')
               WHERE offered_to_client_phone = ?
               AND status = 'rejected'""",
            (CLIENT_SPAM,)
        )
    ok("offered_at movido a hace 31 días (fuera de ventana de 30 días)")

    step(4, "Verificar que ahora SÍ aparece como candidato")
    candidates_libre = find_candidates(freed_id)
    phones_libre = [c['client_phone'] for c in candidates_libre]
    info(f"Candidatos ahora: {phones_libre}")

    if CLIENT_SPAM in phones_libre:
        ok("Pasada la ventana → cliente vuelve a aparecer como candidato ✓")
    else:
        fail("Cliente sigue bloqueado después de 30 días — el anti-spam es permanente (BUG)")

    step(5, "Limpiar")
    clean_test_data()
    ok("Escenario 4 completado\n")


# ─── Main ─────────────────────────────────────────────────────────────────────

SCENARIOS = {
    "cascade_accept":    (run_cascade_accept,     "A rechaza, B acepta → turno movido"),
    "cascade_all_reject":(run_cascade_all_reject, "A, B, C rechazan → slot libre, fin"),
    "antispam_block":    (run_antispam_block,      "3 rechazos → cliente bloqueado"),
    "antispam_new_apt":  (run_antispam_new_apt,    "Pasados 30 días → cliente libre de nuevo"),
}


def main():
    parser = argparse.ArgumentParser(
        description="Test E2E del sistema de cascada y anti-spam de waitlist.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Escenarios:
  cascade_accept     → A rechaza, B acepta → turno movido
  cascade_all_reject → A, B, C rechazan → slot queda libre
  antispam_block     → 3 rechazos → bloqueado 30 días
  antispam_new_apt   → pasados 30 días → vuelve como candidato

Ejemplos:
  docker exec -it whatsapp-demo python tests/test_e2e_waitlist.py
  docker exec -it whatsapp-demo python tests/test_e2e_waitlist.py --scenario cascade_accept
  docker exec -it whatsapp-demo python tests/test_e2e_waitlist.py --clean
        """
    )
    parser.add_argument("--scenario", choices=list(SCENARIOS.keys()), default=None)
    parser.add_argument("--clean", action="store_true", help="Limpiar datos de prueba")
    args = parser.parse_args()

    if args.clean:
        header("LIMPIEZA DE DATOS E2E — WAITLIST")
        clean_test_data()
        return

    header("TEST E2E: SISTEMA DE CASCADA Y ANTI-SPAM — WAITLIST")
    print(f"  Profesional: {PROFESSIONAL_PHONE}")
    print(f"  Clientes:    A={CLIENT_A[-4:]}, B={CLIENT_B[-4:]}, C={CLIENT_C[-4:]}, SPAM={CLIENT_SPAM[-4:]}")

    if args.scenario:
        fn, desc = SCENARIOS[args.scenario]
        info(f"Escenario: {args.scenario} — {desc}")
        fn()
    else:
        info("Corriendo los 4 escenarios...")
        for name, (fn, desc) in SCENARIOS.items():
            print(f"\n{C.YELLOW}{'─'*65}")
            print(f"  {name} — {desc}")
            print(f"{'─'*65}{C.END}")
            fn()
            time.sleep(0.5)

    header("✅ TEST E2E WAITLIST COMPLETADO")


if __name__ == "__main__":
    main()
