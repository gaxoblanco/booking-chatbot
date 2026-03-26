#!/usr/bin/env python3
"""
Test: GAP 8 — SessionManager con Redis y fallback a memoria
============================================================

Verifica que:
    1. MemorySessionBackend funciona igual que antes
    2. RedisSessionBackend persiste y recupera sesiones
    3. SessionManager usa Redis si está disponible
    4. SessionManager cae a memoria si Redis no responde
    5. La sesión sobrevive a una nueva instancia de SessionManager (Redis)
    6. temp_data complejo se serializa y deserializa correctamente
    7. El TTL se renueva en cada acceso
    8. save_session() persiste cambios en Redis

No requiere Redis instalado — los tests de Redis se saltean
automáticamente si no hay conexión disponible.

Uso:
    docker exec -it whatsapp-demo python tests/test_gap8_session_manager.py
"""

import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.states import ConversationState, UserRole, SessionData
from src.core.session_backends import (
    MemorySessionBackend,
    _serialize_session,
    _deserialize_session,
)

# ── Colores ──────────────────────────────────────────────────────────────────
class C:
    GREEN = '\033[92m'; RED = '\033[91m'; CYAN = '\033[96m'
    YELLOW = '\033[93m'; BOLD = '\033[1m'; END = '\033[0m'

def ok(t):     print(f"  {C.GREEN}✅ {t}{C.END}")
def fail(t):   print(f"  {C.RED}❌ {t}{C.END}")
def info(t):   print(f"  ℹ️  {t}")
def skip(t):   print(f"  {C.YELLOW}⏭️  SALTADO: {t}{C.END}")
def sep():     print("=" * 60)

PHONE = "+5490000077001"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_session(state=ConversationState.CLIENT_MAIN_MENU,
                  role=UserRole.CLIENT) -> SessionData:
    s = SessionData(PHONE)
    s.current_state = state
    s.role          = role
    return s

def _redis_available() -> bool:
    """Verifica si hay Redis disponible para los tests."""
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    try:
        import redis
        client = redis.from_url(redis_url, socket_timeout=1)
        client.ping()
        return True
    except Exception:
        return False


# ── Tests Bloque A: Serialización ────────────────────────────────────────────

def test_serialize_estado_y_rol():
    """La sesión se serializa con estado y rol correctos."""
    import json
    s = _make_session(
        state = ConversationState.CLIENT_CONFIRM_BOOKING,
        role  = UserRole.CLIENT
    )
    raw  = _serialize_session(s)
    data = json.loads(raw)

    assert data['current_state'] == 'client_confirm_booking'
    assert data['role']          == 'client'
    assert data['phone_number']  == PHONE
    ok("Serialización incluye estado, rol y teléfono")


def test_serialize_temp_data_complejo():
    """temp_data con dicts anidados y listas se serializa correctamente."""
    import json
    s = _make_session()
    s.set_temp('selected_professional', {
        'phone': '+5491112345678',
        'name':  'Dr. García',
    })
    s.set_temp('booking_date', '2099-12-01')
    s.set_temp('lista_numeros', [1, 2, 3])

    raw  = _serialize_session(s)
    data = json.loads(raw)

    assert data['temp_data']['booking_date'] == '2099-12-01'
    assert data['temp_data']['selected_professional']['name'] == 'Dr. García'
    assert data['temp_data']['lista_numeros'] == [1, 2, 3]
    ok("temp_data complejo se serializa correctamente")


def test_deserialize_recupera_estado():
    """La deserialización reconstruye la sesión completa."""
    s = _make_session(
        state = ConversationState.CLIENT_CONFIRM_BOOKING,
        role  = UserRole.CLIENT,
    )
    s.set_temp('booking_date', '2099-12-01')
    s.set_temp('prof', {'name': 'Dr. García', 'phone': '+549111'})

    raw       = _serialize_session(s)
    recovered = _deserialize_session(raw)

    assert recovered.phone_number  == PHONE
    assert recovered.current_state == ConversationState.CLIENT_CONFIRM_BOOKING
    assert recovered.role          == UserRole.CLIENT
    assert recovered.get_temp('booking_date')       == '2099-12-01'
    assert recovered.get_temp('prof')['name']       == 'Dr. García'
    ok("Deserialización reconstruye sesión completa con temp_data")


def test_deserialize_estado_desconocido_resetea_a_start():
    """Estado desconocido en Redis → resetea a START en lugar de crashear."""
    import json
    data = {
        'phone_number':  PHONE,
        'current_state': 'estado_que_no_existe_v99',
        'role':          'client',
        'temp_data':     {},
    }
    recovered = _deserialize_session(json.dumps(data))
    assert recovered.current_state == ConversationState.START
    ok("Estado desconocido → resetea a START sin crashear")


# ── Tests Bloque B: MemorySessionBackend ─────────────────────────────────────

def test_memory_get_none_si_no_existe():
    backend = MemorySessionBackend()
    assert backend.get(PHONE) is None
    ok("MemoryBackend.get() retorna None si no existe")


def test_memory_save_y_get():
    backend = MemorySessionBackend()
    s       = _make_session()
    backend.save(s)
    recovered = backend.get(PHONE)
    assert recovered is s  # misma referencia en memoria
    ok("MemoryBackend guarda y recupera la sesión")


def test_memory_delete():
    backend = MemorySessionBackend()
    s       = _make_session()
    backend.save(s)
    backend.delete(PHONE)
    assert backend.get(PHONE) is None
    ok("MemoryBackend.delete() elimina la sesión")


def test_memory_count():
    backend = MemorySessionBackend()
    assert backend.count() == 0
    backend.save(_make_session())
    assert backend.count() == 1
    ok("MemoryBackend.count() retorna cantidad correcta")


# ── Tests Bloque C: SessionManager con memoria ────────────────────────────────

def test_session_manager_crea_nueva_sesion():
    """get_session crea una nueva sesión si no existe."""
    from src.core.session_backends import MemorySessionBackend

    with patch.dict(os.environ, {'REDIS_URL': ''}, clear=False):
        from src.core.states import SessionManager
        mgr     = SessionManager()
        session = mgr.get_session(PHONE)

    assert session is not None
    assert session.phone_number  == PHONE
    assert session.current_state == ConversationState.START
    ok("SessionManager crea sesión nueva correctamente")


def test_session_manager_reutiliza_sesion_existente():
    """get_session retorna la misma sesión en llamadas sucesivas."""
    with patch.dict(os.environ, {'REDIS_URL': ''}, clear=False):
        from src.core.states import SessionManager
        mgr = SessionManager()

        s1 = mgr.get_session(PHONE)
        s1.transition_to(ConversationState.CLIENT_CONFIRM_BOOKING)
        mgr.save_session(s1)

        s2 = mgr.get_session(PHONE)

    assert s2.current_state == ConversationState.CLIENT_CONFIRM_BOOKING
    ok("SessionManager reutiliza sesión existente entre llamadas")


def test_session_manager_clear_session():
    """clear_session elimina la sesión correctamente."""
    with patch.dict(os.environ, {'REDIS_URL': ''}, clear=False):
        from src.core.states import SessionManager
        mgr = SessionManager()
        mgr.get_session(PHONE)
        mgr.clear_session(PHONE)
        s = mgr.get_session(PHONE)

    assert s.current_state == ConversationState.START
    ok("clear_session elimina la sesión y la siguiente es nueva")


def test_session_manager_fallback_si_redis_no_disponible():
    """Si Redis no responde, SessionManager usa memoria sin crashear."""
    with patch.dict(os.environ, {'REDIS_URL': 'redis://localhost:9999/0'}):
        from src.core.states import SessionManager
        mgr     = SessionManager()
        session = mgr.get_session(PHONE)

    assert session is not None
    from src.core.session_backends import MemorySessionBackend
    assert isinstance(mgr._backend, MemorySessionBackend)
    ok("Fallback a memoria si Redis no responde")


def test_session_manager_get_stats():
    """get_stats retorna backend y cantidad de sesiones."""
    with patch.dict(os.environ, {'REDIS_URL': ''}, clear=False):
        from src.core.states import SessionManager
        mgr   = SessionManager()
        mgr.get_session(PHONE)
        stats = mgr.get_stats()

    assert 'backend'         in stats
    assert 'active_sessions' in stats
    assert stats['backend']         == 'memory'
    assert stats['active_sessions'] >= 1
    ok(f"get_stats() retorna stats correctas: {stats}")


# ── Tests Bloque D: RedisSessionBackend (solo si Redis disponible) ─────────────

def test_redis_persiste_entre_instancias():
    """La sesión en Redis sobrevive a una nueva instancia del backend."""
    if not _redis_available():
        skip("Redis no disponible — test saltado")
        return

    from src.core.session_backends import RedisSessionBackend
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

    # Instancia 1 — guardar
    b1 = RedisSessionBackend(redis_url)
    s  = _make_session(state=ConversationState.CLIENT_CONFIRM_BOOKING)
    s.set_temp('booking_date', '2099-12-01')
    b1.save(s)

    # Instancia 2 — recuperar (simula reinicio del container)
    b2        = RedisSessionBackend(redis_url)
    recovered = b2.get(PHONE)

    assert recovered is not None
    assert recovered.current_state     == ConversationState.CLIENT_CONFIRM_BOOKING
    assert recovered.get_temp('booking_date') == '2099-12-01'

    # Limpiar
    b2.delete(PHONE)
    ok("Sesión en Redis persiste entre instancias del backend")


def test_redis_session_manager_persiste():
    """SessionManager con Redis persiste la sesión entre instancias."""
    if not _redis_available():
        skip("Redis no disponible — test saltado")
        return

    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

    with patch.dict(os.environ, {'REDIS_URL': redis_url}):
        from src.core.states import SessionManager

        # Instancia 1
        mgr1    = SessionManager()
        session = mgr1.get_session(PHONE)
        session.transition_to(ConversationState.CLIENT_CONFIRM_BOOKING)
        session.set_temp('prof', 'Dr. García')
        mgr1.save_session(session)

        # Instancia 2 — simula reinicio
        mgr2      = SessionManager()
        recovered = mgr2.get_session(PHONE)

        assert recovered.current_state     == ConversationState.CLIENT_CONFIRM_BOOKING
        assert recovered.get_temp('prof')  == 'Dr. García'
        mgr2.clear_session(PHONE)

    ok("SessionManager con Redis persiste entre instancias")


# ── Runner ────────────────────────────────────────────────────────────────────

def run_all():
    sep()
    print(f"{C.BOLD}  TEST GAP 8 — SessionManager con Redis{C.END}")
    redis_ok = _redis_available()
    info(f"Redis disponible: {'✅ Sí' if redis_ok else '❌ No (tests de Redis se saltean)'}")
    sep()

    tests = [
        # Bloque A — Serialización
        test_serialize_estado_y_rol,
        test_serialize_temp_data_complejo,
        test_deserialize_recupera_estado,
        test_deserialize_estado_desconocido_resetea_a_start,
        # Bloque B — MemoryBackend
        test_memory_get_none_si_no_existe,
        test_memory_save_y_get,
        test_memory_delete,
        test_memory_count,
        # Bloque C — SessionManager con memoria
        test_session_manager_crea_nueva_sesion,
        test_session_manager_reutiliza_sesion_existente,
        test_session_manager_clear_session,
        test_session_manager_fallback_si_redis_no_disponible,
        test_session_manager_get_stats,
        # Bloque D — Redis (se saltean si no hay Redis)
        test_redis_persiste_entre_instancias,
        test_redis_session_manager_persiste,
    ]

    passed = failed = skipped = 0
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

    sep()
    if failed == 0:
        print(f"{C.GREEN}{C.BOLD}  ✅ TODOS LOS TESTS PASARON ({passed}/{len(tests)}){C.END}")
    else:
        print(f"{C.RED}{C.BOLD}  ❌ {failed} FALLARON ({passed}/{len(tests)} pasaron){C.END}")
    sep()
    return failed == 0

def test_gap8_completo():
    assert run_all()

if __name__ == "__main__":
    sys.exit(0 if run_all() else 1)
