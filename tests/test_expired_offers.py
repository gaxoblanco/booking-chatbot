#!/usr/bin/env python3
"""
Test: Procesamiento de ofertas de waitlist expiradas (Issue 4)
==============================================================

Verifica que process_expired_offers() limpia correctamente las ofertas
sin respuesta y reintenta la cascada con el siguiente candidato.

Escenarios:
    1. Sin ofertas expiradas → stats vacías, sin efectos
    2. Oferta expirada + candidato disponible → nueva oferta enviada
    3. Oferta expirada + sin candidatos → slot queda libre
    4. Múltiples ofertas expiradas → procesadas todas correctamente

Uso:
    docker exec -it whatsapp-demo python tests/test_expired_offers.py
    docker exec -it whatsapp-demo pytest tests/test_expired_offers.py -v
"""

import sys
from pathlib import Path
from datetime import date, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.database import db
from src.services.waitlist_service import waitlist_service


# ─── Helpers de color ────────────────────────────────────────────────────────

class C:
    GREEN  = '\033[92m'
    RED    = '\033[91m'
    CYAN   = '\033[96m'
    BOLD   = '\033[1m'
    END    = '\033[0m'

def ok(t):   print(f"  {C.GREEN}✅ {t}{C.END}")
def fail(t): print(f"  {C.RED}❌ {t}{C.END}")
def info(t): print(f"  ℹ️  {t}")
def sep():   print("=" * 60)


# ─── Datos de prueba ─────────────────────────────────────────────────────────

CLIENT_A    = "+5490000088001"
CLIENT_B    = "+5490000088002"
PROF_TEST   = "+5490000088003"

BASE_DATE   = date(2099, 8, 1)


# ─── Setup / Teardown ────────────────────────────────────────────────────────

def _cleanup():
    with db.get_connection() as conn:
        for phone in (CLIENT_A, CLIENT_B):
            conn.execute("DELETE FROM appointments WHERE client_phone = ?", (phone,))
            conn.execute("DELETE FROM slot_offers WHERE offered_to_client_phone = ?", (phone,))
            conn.execute("DELETE FROM clients WHERE phone = ?", (phone,))
        conn.execute(
            "DELETE FROM appointments WHERE professional_phone = ?", (PROF_TEST,)
        )
        conn.execute("DELETE FROM professionals WHERE phone = ?", (PROF_TEST,))

def _ensure_entities():
    with db.get_connection() as conn:
        for phone, name in [(CLIENT_A, "Cliente A"), (CLIENT_B, "Cliente B")]:
            conn.execute(
                "INSERT OR IGNORE INTO clients (phone, name) VALUES (?, ?)",
                (phone, name)
            )
        conn.execute(
            "INSERT OR IGNORE INTO professionals (phone, name, is_active) VALUES (?, ?, 1)",
            (PROF_TEST, "Prof Test")
        )

def _create_appointment(client_phone: str, date_offset: int,
                        status: str = 'confirmada',
                        wants_earlier: bool = True) -> int:
    apt_date = (BASE_DATE + timedelta(days=date_offset)).strftime("%Y-%m-%d")
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO appointments
                (client_phone, professional_phone, appointment_date,
                 start, end, duration_minutes, status, wants_earlier_slot)
            VALUES (?, ?, ?, '10:00', '11:00', 50, ?, ?)
        """, (client_phone, PROF_TEST, apt_date, status, 1 if wants_earlier else 0))
        return cursor.lastrowid

def _create_expired_offer(freed_apt_id: int, client_phone: str,
                          original_apt_id: int) -> int:
    """Crea una oferta que ya expiró (expires_at en el pasado)."""
    freed_date = (BASE_DATE + timedelta(days=1)).strftime("%Y-%m-%d")
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO slot_offers
                (freed_appointment_id, offered_to_client_phone, original_appointment_id,
                 freed_date, freed_time, professional_phone, status, expires_at)
            VALUES (?, ?, ?, ?, '09:00', ?, 'pending', datetime('now', '-1 hour'))
        """, (freed_apt_id, client_phone, original_apt_id, freed_date, PROF_TEST))
        return cursor.lastrowid

def _get_offer_status(offer_id: int) -> str:
    with db.get_connection() as conn:
        row = conn.execute(
            "SELECT status FROM slot_offers WHERE id = ?", (offer_id,)
        ).fetchone()
        return row[0] if row else None

def _count_offers_for_freed(freed_apt_id: int) -> int:
    with db.get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM slot_offers WHERE freed_appointment_id = ?",
            (freed_apt_id,)
        ).fetchone()
        return row[0] if row else 0


# ─── Casos de prueba ─────────────────────────────────────────────────────────

def test_sin_ofertas_expiradas():
    """Sin ofertas expiradas → stats vacías, sin efectos secundarios."""
    # Limpiar cualquier oferta previa
    with db.get_connection() as conn:
        conn.execute(
            "DELETE FROM slot_offers WHERE offered_to_client_phone IN (?, ?)",
            (CLIENT_A, CLIENT_B)
        )

    stats = waitlist_service.process_expired_offers()

    assert stats['processed'] == 0, f"Esperado 0 processed, obtenido {stats['processed']}"
    assert stats['errors'] == 0, f"No debería haber errores, obtenido {stats['errors']}"
    ok(f"Sin ofertas expiradas → stats correctas: {stats}")


def test_oferta_expirada_queda_marcada_como_expired():
    """
    Una oferta expirada debe quedar con status='expired' después del procesamiento.
    """
    freed_apt_id  = _create_appointment(CLIENT_A, date_offset=1)
    original_id   = _create_appointment(CLIENT_A, date_offset=10, wants_earlier=True)
    offer_id      = _create_expired_offer(freed_apt_id, CLIENT_A, original_id)

    info(f"Oferta #{offer_id} creada con expires_at en el pasado")

    waitlist_service.process_expired_offers()

    status = _get_offer_status(offer_id)
    assert status == 'expired', f"Esperado 'expired', obtenido '{status}'"
    ok(f"Oferta #{offer_id} correctamente marcada como 'expired'")

    # Cleanup parcial
    with db.get_connection() as conn:
        conn.execute("DELETE FROM slot_offers WHERE id = ?", (offer_id,))
        conn.execute("DELETE FROM appointments WHERE id IN (?, ?)",
                     (freed_apt_id, original_id))


def test_oferta_expirada_con_candidato_genera_nueva_oferta():
    """
    Oferta expirada + hay candidato disponible → se genera una nueva oferta.
    """
    # Freed slot
    freed_apt_id = _create_appointment(CLIENT_A, date_offset=1, status='confirmada')

    # CLIENT_A expiró — su oferta queda marcada como expired
    original_a   = _create_appointment(CLIENT_A, date_offset=10, wants_earlier=True)
    offer_id     = _create_expired_offer(freed_apt_id, CLIENT_A, original_a)

    # CLIENT_B es candidato (turno posterior, quiere adelantar)
    original_b   = _create_appointment(CLIENT_B, date_offset=15, wants_earlier=True)

    offers_antes = _count_offers_for_freed(freed_apt_id)
    info(f"Ofertas antes: {offers_antes}")

    stats = waitlist_service.process_expired_offers()

    offers_despues = _count_offers_for_freed(freed_apt_id)
    info(f"Ofertas después: {offers_despues}, stats: {stats}")

    # La oferta de A debe estar expired
    assert _get_offer_status(offer_id) == 'expired', "Oferta de A debe estar 'expired'"

    # Debe haber al menos una oferta más (para B)
    assert offers_despues > offers_antes, (
        f"Se esperaba una nueva oferta para B. "
        f"Antes: {offers_antes}, después: {offers_despues}"
    )

    assert stats['reoffered'] >= 1, f"Esperado reoffered >= 1, obtenido {stats['reoffered']}"
    assert stats['errors'] == 0, f"No debería haber errores"

    ok(f"Oferta expirada + candidato disponible → nueva oferta generada ✓")

    # Cleanup
    with db.get_connection() as conn:
        conn.execute(
            "DELETE FROM slot_offers WHERE freed_appointment_id = ?", (freed_apt_id,)
        )
        conn.execute(
            "DELETE FROM appointments WHERE id IN (?, ?, ?)",
            (freed_apt_id, original_a, original_b)
        )


def test_oferta_expirada_sin_candidatos_slot_queda_libre():
    """
    Oferta expirada + sin más candidatos → slot queda libre, stats.freed += 1.
    """
    freed_apt_id = _create_appointment(CLIENT_A, date_offset=2, status='confirmada')
    original_a   = _create_appointment(CLIENT_A, date_offset=20,
                                       wants_earlier=False)  # No quiere adelantar
    offer_id     = _create_expired_offer(freed_apt_id, CLIENT_A, original_a)

    # No hay CLIENT_B con wants_earlier=True → sin candidatos

    stats = waitlist_service.process_expired_offers()

    assert _get_offer_status(offer_id) == 'expired', "Oferta debe estar 'expired'"
    assert stats['freed'] >= 1, f"Esperado freed >= 1, obtenido {stats['freed']}"
    assert stats['errors'] == 0, "No debería haber errores"

    ok(f"Oferta expirada sin candidatos → slot queda libre ✓ (stats: {stats})")

    # Cleanup
    with db.get_connection() as conn:
        conn.execute(
            "DELETE FROM slot_offers WHERE freed_appointment_id = ?", (freed_apt_id,)
        )
        conn.execute(
            "DELETE FROM appointments WHERE id IN (?, ?)", (freed_apt_id, original_a)
        )


def test_metodo_get_expired_pending_offers_existe():
    """Verifica que database.py tiene el método get_expired_pending_offers."""
    assert hasattr(db, 'get_expired_pending_offers'), (
        "db no tiene el método get_expired_pending_offers"
    )
    result = db.get_expired_pending_offers()
    assert isinstance(result, list), "get_expired_pending_offers debe retornar una lista"
    ok(f"get_expired_pending_offers() existe y retorna lista ({len(result)} items)")


def test_process_expired_offers_retorna_estructura_correcta():
    """process_expired_offers() retorna dict con las 4 claves esperadas."""
    stats = waitlist_service.process_expired_offers()

    for key in ('processed', 'reoffered', 'freed', 'errors'):
        assert key in stats, f"Falta '{key}' en el dict de stats"
        assert isinstance(stats[key], int), f"'{key}' debe ser int"

    ok(f"Estructura de stats correcta: {stats}")


# ─── Runner ───────────────────────────────────────────────────────────────────

def run_all():
    sep()
    print(f"{C.BOLD}  TEST ISSUE 4 — Ofertas de waitlist expiradas{C.END}")
    sep()

    _cleanup()
    _ensure_entities()

    tests = [
        test_metodo_get_expired_pending_offers_existe,
        test_process_expired_offers_retorna_estructura_correcta,
        test_sin_ofertas_expiradas,
        test_oferta_expirada_queda_marcada_como_expired,
        test_oferta_expirada_con_candidato_genera_nueva_oferta,
        test_oferta_expirada_sin_candidatos_slot_queda_libre,
    ]

    passed = 0
    failed = 0

    for t in tests:
        print(f"\n{C.CYAN}► {t.__name__}{C.END}")
        try:
            t()
            passed += 1
        except AssertionError as e:
            fail(str(e))
            failed += 1
        except Exception as e:
            fail(f"Error inesperado: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    _cleanup()

    sep()
    if failed == 0:
        print(f"{C.GREEN}{C.BOLD}  ✅ TODOS LOS TESTS PASARON ({passed}/{len(tests)}){C.END}")
    else:
        print(f"{C.RED}{C.BOLD}  ❌ {failed} TEST(S) FALLARON ({passed}/{len(tests)} pasaron){C.END}")
    sep()

    return failed == 0


def test_completo():
    """Entry point para pytest."""
    assert run_all(), "Uno o más tests del issue 4 fallaron"


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
