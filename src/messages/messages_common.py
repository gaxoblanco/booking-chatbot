"""
Common Messages
===============
Mensajes compartidos entre flujos. Leen del tono activo.
La estructura de clase se mantiene para compatibilidad con imports existentes.
"""

from src.config.domain_config import DomainConfig
from src.messages.loader import get_msg


class CommonMessages:

    @property
    def WELCOME(self):
        return get_msg("WELCOME", f"Hola, soy {DomainConfig.ASSISTANT_NAME if hasattr(DomainConfig, 'ASSISTANT_NAME') else 'tu asistente'}. Escribí *hola* para comenzar.")

    @property
    def ERROR_GENERIC(self):
        return get_msg("ERROR_GENERIC")

    @property
    def ERROR_UNKNOWN_STATE(self):
        return get_msg("ERROR_UNKNOWN_STATE")

    @property
    def INVALID_OPTION(self):
        return get_msg("INVALID_OPTION")

    @property
    def UNKNOWN_QUERY(self):
        return get_msg("UNKNOWN_QUERY")

    @property
    def INVALID_DATE(self):
        return get_msg("INVALID_DATE")

    @property
    def INVALID_TIME(self):
        return get_msg("INVALID_TIME")

    @property
    def HELP_MESSAGE(self):
        return get_msg("HELP_MESSAGE")


common_messages = CommonMessages()