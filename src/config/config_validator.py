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
    _validate_single_professional_mode()
    _validate_demo_mode()
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
        
def _validate_single_professional_mode() -> None:
    """
    Valida coherencia del modo profesional único.
    Solo corre si SINGLE_PROFESSIONAL_MODE=true.

    Checks:
        1. SINGLE_PROFESSIONAL_PHONE configurado
        2. TENANT_TONE compatible (freelance)
        3. Profesional existe en BD (skip si BD no disponible aún)
    """
    import os
    from src.config.config import Config

    mode = getattr(Config, 'SINGLE_PROFESSIONAL_MODE', False)
    if not mode:
        return
    
    # Check 0 — dominio compatible
    _DOMAINS_INCOMPATIBLES = {'DEMO'}
    domain = os.getenv('DOMAIN_PRESET', '').upper().strip()
    if domain in _DOMAINS_INCOMPATIBLES:
        raise ValueError(
            f"[CONFIG] ❌ SINGLE_PROFESSIONAL_MODE=true es incompatible con "
            f"DOMAIN_PRESET='{domain}'.\n"
            f"Cambiar en .env: DOMAIN_PRESET=SALUD  (o cualquier preset no-demo)"
        )

    # Check 1 — teléfono
    phone = getattr(Config, 'SINGLE_PROFESSIONAL_PHONE', '').strip()
    if not phone:
        raise ValueError(
            "[CONFIG] ❌ SINGLE_PROFESSIONAL_MODE=true pero "
            "SINGLE_PROFESSIONAL_PHONE no configurado.\n"
            "Agregar al .env: SINGLE_PROFESSIONAL_PHONE=+5491112345678"
        )

    # Check 2 — tono compatible
    _TONES_COMPATIBLES = {'freelance'}
    tone = os.getenv('TENANT_TONE', 'demo').lower().strip()
    if tone not in _TONES_COMPATIBLES:
        raise ValueError(
            f"[CONFIG] ❌ SINGLE_PROFESSIONAL_MODE=true requiere "
            f"TENANT_TONE=freelance.\n"
            f"Tono actual: '{tone}'. Cambiar en .env: TENANT_TONE=freelance"
        )

    # Check 3 — profesional en BD (fallo silencioso si BD no está lista)
    try:
        from src.database.database import db
        prof = db.get_professional(phone)
        if prof is None:
            raise ValueError(
                f"[CONFIG] ❌ SINGLE_PROFESSIONAL_MODE=true pero "
                f"'{phone}' no existe en la BD.\n"
                f"Verificar SINGLE_PROFESSIONAL_PHONE o cargar el profesional primero."
            )
        print(f"[CONFIG] ✅ Modo profesional único — {prof.get('name', phone)}")
    except ValueError:
        raise
    except Exception as e:
        print(f"[CONFIG] ⚠️  Check BD omitido (BD no disponible aún): {e}")

def _validate_demo_mode() -> None:
    """
    Valida coherencia de la configuración demo.

    Checks:
        1. TENANT_TONE=demo requiere DOMAIN_PRESET=DEMO
           (el tono demo tiene mensajes específicos del producto
           que no tienen sentido en producción)
        2. DOMAIN_PRESET=DEMO requiere TENANT_TONE=demo
           (evita arrancar un centro real con preset de demostración)
    """
    import os

    tone   = os.getenv('TENANT_TONE', 'demo').lower().strip()
    domain = os.getenv('DOMAIN_PRESET', 'SALUD').upper().strip()

    if tone == 'demo' and domain != 'DEMO':
        raise ValueError(
            f"[CONFIG] ❌ TENANT_TONE='demo' requiere DOMAIN_PRESET=DEMO.\n"
            f"Dominio actual: '{domain}'\n"
            f"Opciones:\n"
            f"  - Cambiar DOMAIN_PRESET=DEMO  (para demostración del producto)\n"
            f"  - Cambiar TENANT_TONE=coloquial o freelance  (para producción)"
        )

    if domain == 'DEMO' and tone != 'demo':
        raise ValueError(
            f"[CONFIG] ❌ DOMAIN_PRESET=DEMO requiere TENANT_TONE=demo.\n"
            f"Tono actual: '{tone}'\n"
            f"Opciones:\n"
            f"  - Cambiar TENANT_TONE=demo  (para demostración del producto)\n"
            f"  - Cambiar DOMAIN_PRESET=SALUD u otro  (para producción)"
        )