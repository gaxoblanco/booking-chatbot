"""
Message Loader
==============
Carga el módulo de tono correcto según TENANT_TONE.

Agregar un tono nuevo:
    1. Crear src/messages/tones/nuevo_tono.py con las mismas constantes
    2. Registrarlo en REGISTERED abajo
    3. Cambiar TENANT_TONE=nuevo_tono en el .env del container
"""

import os
import importlib
from types import ModuleType
from typing import Any

REGISTERED = {"demo", "coloquial", "freelance"}

_tone_module = None


def _load_tone() -> ModuleType:
    global _tone_module
    if _tone_module is not None:
        return _tone_module

    tone = os.getenv("TENANT_TONE", "demo").lower().strip()

    if tone not in REGISTERED:
        import warnings
        warnings.warn(
            f"[MESSAGES] Tono '{tone}' no registrado. "
            f"Disponibles: {REGISTERED}. Usando 'demo'."
        )
        tone = "demo"

    _tone_module = importlib.import_module(f"src.messages.tones.{tone}")
    print(f"[MESSAGES] Tono cargado: {tone}")
    return _tone_module


def get_msg(key: str, default: Any = None) -> Any:
    """
    Obtiene un mensaje del tono activo por nombre de constante.

    Args:
        key:     Nombre de la constante (ej: "CLIENT_MAIN_MENU")
        default: Valor por defecto si no existe en el tono activo

    Returns:
        El string o valor del mensaje
    """
    module = _load_tone()
    return getattr(module, key, default)


def reload_tone():
    """Fuerza recarga del tono (útil en tests)."""
    global _tone_module
    _tone_module = None
    _load_tone()
