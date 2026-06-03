"""
Config Validator
================
Valida la coherencia entre DomainConfig y FeatureFlags al arrancar.
Se llama una sola vez desde create_app() o app.py.

Si la configuración es inválida, lanza ValueError con un mensaje
que explica exactamente qué falta y cómo corregirlo.
Fail fast — mejor explotar en el boot que fallar en producción.
"""

from src.config.domain_config import DomainConfig
from src.config.filter_config import FeatureFlags

# Modos habilitados en esta versión.
# Mover 'virtual_only' acá cuando ASK_MODALITY esté implementado.
_MEET_MODES_ENABLED = {'never', 'always'}


def validate_config() -> None:
    """
    Valida la configuración al arrancar.
    Lanza ValueError si encuentra una combinación inválida.

    Checks:
        1. MEET_LINK_MODE es un valor conocido
        2. MEET_LINK_MODE='virtual_only' requiere ASK_MODALITY=True
    """
    _validate_meet_link_mode()
    print("[CONFIG] ✅ Configuración válida")


def _validate_meet_link_mode() -> None:
    mode = DomainConfig.MEET_LINK_MODE

    # Check 1 — valor conocido (incluyendo los pendientes)
    _ALL_KNOWN_MODES = {'never', 'always', 'virtual_only'}
    if mode not in _ALL_KNOWN_MODES:
        raise ValueError(
            f"[CONFIG] ❌ MEET_LINK_MODE='{mode}' no es un valor válido.\n"
            f"Valores permitidos: {_ALL_KNOWN_MODES}\n"
            f"Revisar .env o src/config/domain_config.py"
        )

    # Check 2 — virtual_only bloqueado hasta que el flujo esté listo
    if mode == 'virtual_only':
        if not FeatureFlags.ASK_MODALITY:
            raise ValueError(
                "[CONFIG] ❌ MEET_LINK_MODE='virtual_only' requiere "
                "FeatureFlags.ASK_MODALITY=True.\n"
                "El flujo de selección de modalidad no está implementado.\n"
                "Opciones:\n"
                "  - Usar MEET_LINK_MODE='always' o 'never' por ahora\n"
                "  - Implementar CLIENT_ASK_MODALITY en client_handler.py "
                "y states.py antes de habilitar este modo.\n"
                "  Ver docs/MEET_LINK_MODE.md"
            )