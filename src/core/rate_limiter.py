"""
Rate Limiter
============
Protección contra abuso en el webhook de WhatsApp.

Implementa ventana deslizante (sliding window) en memoria.
No requiere Redis — usa un dict en proceso, thread-safe con Lock.

Política:
  - Máximo N mensajes por ventana de tiempo por número
  - Si se supera: bloqueo temporal configurable
  - Bloqueos silenciosos para el atacante, loggeables para el operador

Uso:
    from src.core.rate_limiter import rate_limiter

    if rate_limiter.is_blocked(phone):
        return '', 429  # Silencioso

    rate_limiter.record(phone)
"""

import time
import threading
from typing import Dict, List
from src.config.domain_config import DomainConfig


class RateLimiter:
    """
    Rate limiter de ventana deslizante por número de teléfono.

    Estructura interna:
        _timestamps: { phone: [t1, t2, t3, ...] }  — mensajes recientes
        _blocked:    { phone: unblock_timestamp }   — bloqueos activos
    """

    def __init__(self):
        self._timestamps: Dict[str, List[float]] = {}
        self._blocked: Dict[str, float] = {}
        self._lock = threading.Lock()

    # =========================================================================
    # API PÚBLICA
    # =========================================================================

    def is_blocked(self, phone: str) -> bool:
        """
        Verifica si el número está bloqueado temporalmente.

        Debe llamarse ANTES de record() al inicio de cada request.

        Args:
            phone: Número de teléfono limpio (sin 'whatsapp:')

        Returns:
            True si el número está bloqueado y debe ignorarse el mensaje
        """
        with self._lock:
            return self._check_blocked(phone)

    def record(self, phone: str) -> bool:
        """
        Registra un mensaje entrante y evalúa si se supera el límite.

        Si se supera el límite, activa el bloqueo temporal y retorna False.
        Si está dentro del límite, registra el timestamp y retorna True.

        Args:
            phone: Número de teléfono limpio (sin 'whatsapp:')

        Returns:
            True si el mensaje puede procesarse, False si se activó el bloqueo
        """
        with self._lock:
            now = time.time()
            window = DomainConfig.RATE_LIMIT_WINDOW_SECONDS

            # Limpiar timestamps fuera de la ventana
            self._timestamps[phone] = [
                t for t in self._timestamps.get(phone, [])
                if now - t < window
            ]

            count = len(self._timestamps[phone])

            if count >= DomainConfig.RATE_LIMIT_MAX_MESSAGES_PER_WINDOW:
                # Supera el límite — activar bloqueo
                block_until = now + (DomainConfig.RATE_LIMIT_BLOCK_MINUTES * 60)
                self._blocked[phone] = block_until
                print(
                    f"[RATE_LIMIT] 🚫 Bloqueo activado: {phone} "
                    f"envió {count + 1} mensajes en {window}s. "
                    f"Bloqueado por {DomainConfig.RATE_LIMIT_BLOCK_MINUTES} min."
                )
                return False

            # Dentro del límite — registrar
            self._timestamps[phone].append(now)
            print(f"[RATE_LIMIT] ✅ {phone}: {count + 1}/{DomainConfig.RATE_LIMIT_MAX_MESSAGES_PER_WINDOW} msgs en ventana")
            return True

    def get_stats(self) -> dict:
        """
        Retorna estadísticas del estado actual del rate limiter.
        Útil para debugging y monitoreo.

        Returns:
            Dict con números activos, bloqueados y timestamps recientes
        """
        with self._lock:
            now = time.time()
            active_blocks = {
                phone: round(until - now, 1)
                for phone, until in self._blocked.items()
                if until > now
            }
            return {
                'phones_tracked': len(self._timestamps),
                'active_blocks': len(active_blocks),
                'blocked_phones': active_blocks,
            }

    # =========================================================================
    # MÉTODOS PRIVADOS
    # =========================================================================

    def _check_blocked(self, phone: str) -> bool:
        """
        Verifica bloqueo activo. Si expiró, lo limpia.
        Debe llamarse dentro del lock.
        """
        if phone not in self._blocked:
            return False

        now = time.time()
        if now < self._blocked[phone]:
            remaining = round(self._blocked[phone] - now)
            print(f"[RATE_LIMIT] 🚫 Mensaje ignorado: {phone} bloqueado ({remaining}s restantes)")
            return True

        # Bloqueo expirado — limpiar
        del self._blocked[phone]
        if phone in self._timestamps:
            del self._timestamps[phone]
        print(f"[RATE_LIMIT] ✅ Bloqueo expirado para {phone}, restaurado")
        return False


# Instancia global — mismo patrón que db, waitlist_service, etc.
rate_limiter = RateLimiter()