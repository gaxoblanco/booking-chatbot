"""
SanitizedLogger — S6
=====================
Ubicación: src/core/logger.py

Logger que enmascara números de teléfono (PII) antes de escribir
en cualquier destino de log.

Problema que resuelve:
    Los logs del container tienen cientos de print() con teléfonos
    completos. En producción eso queda accesible via `docker logs`
    y cualquier sistema de log aggregation.

Qué enmascara:
    - Números E.164: +5491112345678 → +549****5678
    - Números sin +: 5491112345678  → 549****5678

Uso:
    # En lugar de:
    logger = logging.getLogger(__name__)

    # Usar:
    from src.core.logger import get_logger
    logger = get_logger(__name__)

    # Misma interfaz — ningún otro cambio en el código
    logger.info(f"Sesión creada para {phone}")   # teléfono queda enmascarado
    logger.error(f"Error cancelando {phone}")    # ídem
"""

import re
import logging

# Patrón E.164 con o sin + inicial
# Captura: +549XXXXXXXX, 549XXXXXXXX, +1XXXXXXXXXX, etc.
_PHONE_PATTERN = re.compile(r'(\+?\d{2,4})\d{4,7}(\d{4})')


def _sanitize(text: str) -> str:
    """
    Enmascara teléfonos en el texto.

    Conserva el prefijo de país y los últimos 4 dígitos.
    Reemplaza el cuerpo con ****.

    Ejemplos:
        +5491112345678  →  +549****5678
        5491112345678   →  549****5678
        +1-800-555-1234 →  no afecta (formato con guiones, no E.164)
    """
    return _PHONE_PATTERN.sub(r'\1****\2', str(text))


class SanitizedLogger:
    """
    Wrapper de logging.Logger que sanitiza PII antes de escribir.

    Interfaz idéntica a logging.Logger para que sea un drop-in replacement.
    """

    def __init__(self, name: str):
        self._log = logging.getLogger(name)

    def debug(self, msg, *args, **kwargs):
        self._log.debug(_sanitize(msg), *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self._log.info(_sanitize(msg), *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self._log.warning(_sanitize(msg), *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self._log.error(_sanitize(msg), *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        self._log.critical(_sanitize(msg), *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        self._log.exception(_sanitize(msg), *args, **kwargs)

    # Pasar atributos del logger subyacente que otros módulos puedan necesitar
    @property
    def level(self):
        return self._log.level

    @property
    def name(self):
        return self._log.name

    def setLevel(self, level):
        self._log.setLevel(level)

    def isEnabledFor(self, level):
        return self._log.isEnabledFor(level)


def get_logger(name: str) -> SanitizedLogger:
    """
    Factory function — reemplaza logging.getLogger() en módulos sensibles.

    Uso:
        from src.core.logger import get_logger
        logger = get_logger(__name__)
    """
    return SanitizedLogger(name)
