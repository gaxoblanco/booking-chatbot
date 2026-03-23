"""
BookingLimiter
==============
Ubicación: src/core/booking_limiter.py

Limita la cantidad de intentos de confirmación de booking por número
en una ventana de tiempo. Complementa el rate_limiter del webhook
(que limita mensajes totales) con uno específico para la acción de crear citas.

Diferencia con rate_limiter:
    - rate_limiter:    limita CUALQUIER mensaje (hasta 10/min)
    - booking_limiter: limita solo el momento de CONFIRMAR un booking
                       (presionar '1' en la pantalla de confirmación)

Un usuario legítimo confirma 1-2 bookings por hora como máximo.
Si un número confirma 5+ veces en 60 minutos algo raro está pasando.

Usa el mismo patrón de ventana deslizante que RateLimiter (issue 3).
Thread-safe con threading.Lock.

Instancia global:
    from src.core.booking_limiter import booking_limiter
"""

import threading
import logging
from collections import defaultdict, deque
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class BookingLimiter:
    """
    Limita intentos de confirmación de booking por número de teléfono.

    Algoritmo: ventana deslizante.
    - Guarda timestamps de los últimos intentos por número
    - Al llegar un nuevo intento, descarta los que cayeron fuera de la ventana
    - Si los que quedan superan el límite → bloquear

    Bloqueo suave: no es permanente, se levanta cuando la ventana avanza.
    """

    def __init__(self):
        # timestamps de intentos por número: {phone: deque([datetime, ...])}
        self._attempts: dict = defaultdict(deque)

        # Números bloqueados hasta un timestamp: {phone: datetime}
        self._blocked_until: dict = {}

        self._lock = threading.Lock()

        # Leer config desde DomainConfig con fallback a valores seguros
        try:
            from src.config.domain_config import DomainConfig
            self._max_attempts = getattr(
                DomainConfig, 'MAX_BOOKING_ATTEMPTS_PER_WINDOW', 5
            )
            self._window_minutes = getattr(
                DomainConfig, 'BOOKING_ATTEMPT_WINDOW_MINUTES', 60
            )
            self._block_minutes = getattr(
                DomainConfig, 'BOOKING_ATTEMPT_BLOCK_MINUTES', 30
            )
        except Exception:
            self._max_attempts    = 5
            self._window_minutes  = 60
            self._block_minutes   = 30

    # =========================================================================
    # API PÚBLICA
    # =========================================================================

    def record_attempt(self, phone: str) -> bool:
        """
        Registra un intento de booking para el número dado.

        Llamar en handle_client_confirm_booking() cuando el usuario
        presiona '1' para confirmar.

        Args:
            phone: Número de teléfono en formato E.164

        Returns:
            True  → intento permitido, continuar con el booking
            False → límite superado, mostrar mensaje de espera
        """
        with self._lock:
            now = datetime.now()

            # ── Verificar si está en bloqueo explícito ────────────────────────
            if phone in self._blocked_until:
                if now < self._blocked_until[phone]:
                    remaining = int(
                        (self._blocked_until[phone] - now).total_seconds() / 60
                    ) + 1
                    logger.warning(
                        f"[BOOKING-LIMITER] 🚫 {phone} bloqueado "
                        f"({remaining} min restantes)"
                    )
                    return False
                else:
                    # Bloqueo expiró — limpiar
                    del self._blocked_until[phone]

            # ── Limpiar timestamps fuera de la ventana ────────────────────────
            window_start = now - timedelta(minutes=self._window_minutes)
            attempts     = self._attempts[phone]

            while attempts and attempts[0] < window_start:
                attempts.popleft()

            # ── Verificar límite ─────────────────────────────────────────────
            if len(attempts) >= self._max_attempts:
                # Activar bloqueo explícito
                self._blocked_until[phone] = now + timedelta(
                    minutes=self._block_minutes
                )
                logger.warning(
                    f"[BOOKING-LIMITER] 🚨 {phone} superó "
                    f"{self._max_attempts} intentos en "
                    f"{self._window_minutes} min — bloqueado "
                    f"{self._block_minutes} min"
                )
                return False

            # ── Registrar intento ────────────────────────────────────────────
            attempts.append(now)
            logger.debug(
                f"[BOOKING-LIMITER] ✅ {phone} — "
                f"intento {len(attempts)}/{self._max_attempts}"
            )
            return True

    def get_attempts(self, phone: str) -> int:
        """
        Retorna la cantidad de intentos activos (dentro de la ventana)
        para un número. Útil para tests y debugging.

        Args:
            phone: Número de teléfono

        Returns:
            Cantidad de intentos en la ventana actual
        """
        with self._lock:
            now          = datetime.now()
            window_start = now - timedelta(minutes=self._window_minutes)
            attempts     = self._attempts[phone]

            while attempts and attempts[0] < window_start:
                attempts.popleft()

            return len(attempts)

    def is_blocked(self, phone: str) -> bool:
        """
        Verifica si un número está actualmente bloqueado.

        Args:
            phone: Número de teléfono

        Returns:
            True si está bloqueado, False si puede hacer bookings
        """
        with self._lock:
            if phone not in self._blocked_until:
                return False
            if datetime.now() < self._blocked_until[phone]:
                return True
            del self._blocked_until[phone]
            return False

    def reset(self, phone: str):
        """
        Resetea el contador y bloqueo de un número.
        Usado en tests para limpiar estado entre casos.

        Args:
            phone: Número de teléfono
        """
        with self._lock:
            self._attempts.pop(phone, None)
            self._blocked_until.pop(phone, None)

    def get_stats(self) -> dict:
        """
        Retorna estadísticas del limiter.
        Útil para monitoreo y debugging.

        Returns:
            {
                'tracked_numbers': int,
                'blocked_numbers': int,
                'config': {
                    'max_attempts':   int,
                    'window_minutes': int,
                    'block_minutes':  int,
                }
            }
        """
        with self._lock:
            now     = datetime.now()
            blocked = sum(
                1 for exp in self._blocked_until.values() if exp > now
            )
            return {
                'tracked_numbers': len(self._attempts),
                'blocked_numbers': blocked,
                'config': {
                    'max_attempts':   self._max_attempts,
                    'window_minutes': self._window_minutes,
                    'block_minutes':  self._block_minutes,
                }
            }


# Instancia global — importar así:
#   from src.core.booking_limiter import booking_limiter
booking_limiter = BookingLimiter()
