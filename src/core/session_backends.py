"""
Session Backends — Redis con fallback a memoria
================================================
Ubicación: src/core/session_backends.py

Implementa dos backends para SessionManager:

    RedisSessionBackend  — persiste sesiones en Redis con TTL de 30 min.
                           Sobrevive reinicios del container.
    MemorySessionBackend — dict en memoria (comportamiento actual).
                           Fallback automático si Redis no está disponible.

SessionManager detecta Redis al arrancar y elige el backend.
El código que usa session_manager NO cambia — misma interfaz.

Serialización:
    SessionData se serializa a JSON para Redis.
    temp_data puede contener dicts anidados — se serializa recursivamente.
    ConversationState y UserRole se guardan como strings (sus .value).

TTL:
    30 minutos desde el último acceso.
    Cada get_session() renueva el TTL automáticamente.
    Si el usuario no interactúa en 30 min, la sesión expira y se crea nueva.
"""

import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

SESSION_TTL_SECONDS = 30 * 60  # 30 minutos
REDIS_KEY_PREFIX    = "session:"


# =============================================================================
# SERIALIZACIÓN / DESERIALIZACIÓN
# =============================================================================

def _serialize_session(session) -> str:
    """
    Convierte SessionData a JSON string para almacenar en Redis.

    Guarda: phone_number, current_state, role, temp_data.
    No guarda conversation_history (es efímero, no crítico para persistencia).
    """
    data = {
        'phone_number':  session.phone_number,
        'current_state': session.current_state.value,
        'role':          session.role.value,
        'temp_data':     _serialize_temp_data(session.temp_data),
    }
    return json.dumps(data, ensure_ascii=False)


def _deserialize_session(raw: str):
    """
    Reconstruye SessionData desde JSON string.
    Importa SessionData, ConversationState y UserRole aquí para evitar
    importación circular (este módulo es importado por states.py).
    """
    from src.core.states import SessionData, ConversationState, UserRole

    data    = json.loads(raw)
    session = SessionData(data['phone_number'])

    # Restaurar estado
    try:
        session.current_state = ConversationState(data['current_state'])
    except ValueError:
        session.current_state = ConversationState.START
        logger.warning(
            f"[SESSION] Estado desconocido '{data['current_state']}' "
            f"→ reseteando a START"
        )

    # Restaurar rol
    try:
        session.role = UserRole(data['role'])
    except ValueError:
        from src.core.states import UserRole
        session.role = UserRole.UNKNOWN

    # Restaurar temp_data
    session.temp_data = _deserialize_temp_data(data.get('temp_data', {}))

    return session


def _serialize_temp_data(data: dict) -> dict:
    """
    Prepara temp_data para JSON.
    Los valores deben ser tipos JSON-serializables.
    Las fechas (date/datetime) se convierten a string ISO.
    """
    from datetime import date, datetime

    result = {}
    for k, v in data.items():
        if isinstance(v, (date, datetime)):
            result[k] = v.isoformat()
        elif isinstance(v, dict):
            result[k] = _serialize_temp_data(v)
        elif isinstance(v, list):
            result[k] = [
                _serialize_temp_data(i) if isinstance(i, dict) else i
                for i in v
            ]
        else:
            result[k] = v
    return result


def _deserialize_temp_data(data: dict) -> dict:
    """
    Restaura temp_data desde JSON.
    No intenta parsear fechas — se deja como string para que el código
    que las usa las parsee si las necesita (ya lo hacen con strptime).
    """
    return data if data else {}


# =============================================================================
# BACKEND REDIS
# =============================================================================

class RedisSessionBackend:
    """
    Backend que persiste sesiones en Redis.

    - TTL de 30 minutos renovado en cada acceso
    - Clave: "session:{phone_number}"
    - Serialización: JSON
    """

    def __init__(self, redis_url: str):
        """
        Inicializa la conexión a Redis.

        Args:
            redis_url: URL de Redis (ej: redis://localhost:6379/0)

        Raises:
            ImportError: Si redis-py no está instalado
            Exception:   Si no se puede conectar a Redis
        """
        import redis as redis_lib
        self._client = redis_lib.from_url(
            redis_url,
            decode_responses = True,
            socket_timeout   = 2,    # 2 seg — falla rápido si Redis no responde
        )
        # Verificar conexión
        self._client.ping()
        logger.info(f"[SESSION] ✅ Redis conectado: {redis_url}")

    def get(self, phone_number: str):
        """
        Lee la sesión desde Redis. Renueva el TTL.

        Returns:
            SessionData si existe, None si expiró o no existe
        """
        key = f"{REDIS_KEY_PREFIX}{phone_number}"
        raw = self._client.get(key)

        if raw is None:
            return None

        try:
            session = _deserialize_session(raw)
            # Renovar TTL en cada acceso
            self._client.expire(key, SESSION_TTL_SECONDS)
            return session
        except Exception as e:
            logger.error(f"[SESSION] ❌ Error deserializando {phone_number}: {e}")
            self._client.delete(key)
            return None

    def save(self, session) -> bool:
        """
        Guarda la sesión en Redis con TTL de 30 minutos.

        Returns:
            True si se guardó correctamente
        """
        key = f"{REDIS_KEY_PREFIX}{session.phone_number}"
        try:
            raw = _serialize_session(session)
            self._client.setex(key, SESSION_TTL_SECONDS, raw)
            return True
        except Exception as e:
            logger.error(
                f"[SESSION] ❌ Error guardando {session.phone_number}: {e}"
            )
            return False

    def delete(self, phone_number: str):
        """Elimina la sesión de Redis."""
        self._client.delete(f"{REDIS_KEY_PREFIX}{phone_number}")

    def count(self) -> int:
        """Retorna cantidad de sesiones activas. Útil para monitoreo."""
        return len(self._client.keys(f"{REDIS_KEY_PREFIX}*"))


# =============================================================================
# BACKEND MEMORIA (fallback)
# =============================================================================

class MemorySessionBackend:
    """
    Backend en memoria — comportamiento original del sistema.
    Usado cuando Redis no está disponible.
    """

    def __init__(self):
        self._sessions = {}
        logger.warning(
            "[SESSION] ⚠️  Usando sesiones en MEMORIA. "
            "Las sesiones se pierden si el container se reinicia. "
            "Configurar REDIS_URL para persistencia."
        )

    def get(self, phone_number: str):
        return self._sessions.get(phone_number)

    def save(self, session) -> bool:
        self._sessions[session.phone_number] = session
        return True

    def delete(self, phone_number: str):
        self._sessions.pop(phone_number, None)

    def count(self) -> int:
        return len(self._sessions)
