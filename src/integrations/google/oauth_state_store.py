"""
OAuth State Store
================
Mapea el parámetro 'state' de OAuth2 al teléfono del profesional
que inició el flujo de autorización.

El state es un string aleatorio que Google devuelve intacto en el callback.
Lo usamos para saber qué profesional autorizó.

TTL: 10 minutos — suficiente para completar el flujo OAuth2.
"""

import secrets
import threading
from datetime import datetime, timedelta


class OAuthStateStore:
    """
    Store en memoria para el mapeo state → phone durante el flujo OAuth2.
    Thread-safe via Lock.
    """

    def __init__(self, ttl_minutes: int = 10):
        self._store: dict[str, dict] = {}
        self._lock  = threading.Lock()
        self._ttl   = timedelta(minutes=ttl_minutes)

    def create(self, phone: str) -> str:
        """
        Crea un nuevo state para el profesional y lo guarda.

        Args:
            phone: Teléfono del profesional

        Returns:
            str: state aleatorio para incluir en la URL de autorización
        """
        state = secrets.token_urlsafe(24)
        with self._lock:
            self._purge_expired()
            self._store[state] = {
                'phone':      phone,
                'created_at': datetime.now()
            }
        return state

    def get_phone(self, state: str) -> str | None:
        """
        Retorna el teléfono asociado al state, o None si no existe o expiró.
        """
        with self._lock:
            entry = self._store.get(state)
            if not entry:
                return None
            if datetime.now() - entry['created_at'] > self._ttl:
                del self._store[state]
                return None
            return entry['phone']

    def delete(self, state: str) -> None:
        """Elimina el state después de usarlo."""
        with self._lock:
            self._store.pop(state, None)

    def _purge_expired(self) -> None:
        """Limpia states vencidos. Llamar con el lock tomado."""
        now = datetime.now()
        expired = [
            s for s, e in self._store.items()
            if now - e['created_at'] > self._ttl
        ]
        for s in expired:
            del self._store[s]


# Singleton
oauth_state_store = OAuthStateStore()