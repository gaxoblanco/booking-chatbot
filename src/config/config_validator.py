"""
Config Validator
================
Valida la coherencia entre DomainConfig y FeatureFlags al arrancar.
Se llama una sola vez desde create_app() o app.py.

Si la configuración es inválida, lanza ValueError con un mensaje
que explica exactamente qué falta, en qué archivo y qué línea cambiar.
Fail fast — mejor explotar en el boot que fallar silenciosamente en producción.

Changelog:
    - 'auto' reemplaza 'virtual_only'. El modo auto genera Meet solo cuando
      el cliente eligió modalidad virtual en el flujo de búsqueda.
    - El gate ya no es FeatureFlags.ASK_MODALITY (stub deprecado) sino
      DomainConfig.ALLOW_CLIENT_CHOOSE_MODALITY + FilterType.MODALITY enabled.
"""

import os
from src.config.domain_config import DomainConfig

# Todos los modos conocidos y funcionales en esta versión.
_ALL_KNOWN_MODES = {'never', 'always', 'auto'}


def validate_config() -> None:
    """
    Valida la configuración al arrancar.
    Lanza ValueError si encuentra una combinación inválida.

    Checks que corre:
        1. MEET_LINK_MODE es un valor conocido
        2. MEET_LINK_MODE='auto' → ALLOW_CLIENT_CHOOSE_MODALITY=True
        3. MEET_LINK_MODE='auto' → FilterType.MODALITY enabled=True
        4. SINGLE_PROFESSIONAL_MODE coherente
        5. TENANT_TONE / DOMAIN_PRESET coherentes
    """
    _validate_meet_link_mode()
    _validate_oauth_redirect_uri()
    _validate_single_professional_mode()
    _validate_demo_mode()
    print("[CONFIG] ✅ Configuración válida")


def _validate_meet_link_mode() -> None:
    """
    Valida MEET_LINK_MODE y sus dependencias.

    Check 1 — valor reconocido.
    Check 2 — modo 'auto' requiere ALLOW_CLIENT_CHOOSE_MODALITY=True
               en src/config/domain_config.py
    Check 3 — modo 'auto' requiere FilterType.MODALITY con enabled=True
               en src/config/domain_filters_config.py
    """
    mode = DomainConfig.MEET_LINK_MODE

    # ── Check 1 — valor reconocido ───────────────────────────────────────────
    if mode not in _ALL_KNOWN_MODES:
        raise ValueError(
            f"[CONFIG] ❌ MEET_LINK_MODE='{mode}' no es un valor válido.\n"
            f"Valores permitidos: {_ALL_KNOWN_MODES}\n"
            f"\n"
            f"Dónde corregirlo:\n"
            f"  Archivo : .env\n"
            f"  Variable: MEET_LINK_MODE\n"
            f"  Cambiar : MEET_LINK_MODE=never  (o 'always' o 'auto')"
        )

    # ── Check 2 — OAUTH_SETUP_KEY requerida cuando Meet puede generarse ─────
    # Con never no hace falta OAuth2 — nunca se genera Meet.
    # Con always o auto sí hace falta: sin OAUTH_SETUP_KEY el endpoint
    # /oauth/start devuelve 404 y no hay forma de autorizar OAuth2
    # para el profesional en producción.
    # Es un WARNING, no un error fatal: el bot arranca igual, pero
    # el administrador necesita saberlo antes de ir a producción.
    if mode in ('always', 'auto'):
        oauth_setup_key = os.getenv('OAUTH_SETUP_KEY', '').strip()
        if not oauth_setup_key:
            print(
                f"[CONFIG] ⚠️  MEET_LINK_MODE='{mode}' pero OAUTH_SETUP_KEY no está configurada.\n"
                f"  El endpoint /oauth/start estará deshabilitado (devuelve 404).\n"
                f"  Sin él no se puede autorizar OAuth2 para el profesional → sin Meet links.\n"
                f"\n"
                f"  Dónde corregirlo:\n"
                f"  Archivo  : .env\n"
                f"  Variable : OAUTH_SETUP_KEY\n"
                f"  Generar  : python -c 'import secrets; print(secrets.token_urlsafe(32))'\n"
                f"  Agregar  : OAUTH_SETUP_KEY=<el valor generado>"
            )

    if mode != 'auto':
        # never y always no tienen dependencias adicionales más allá del check anterior
        return

    # ── Check 2 — ALLOW_CLIENT_CHOOSE_MODALITY debe estar activo ─────────────
    # Sin este flag el filtro de modalidad no aparece en el flujo y
    # modality llega siempre como None → Meet nunca se genera en modo 'auto'.
    allow_choose = getattr(DomainConfig, 'ALLOW_CLIENT_CHOOSE_MODALITY', False)
    if not allow_choose:
        raise ValueError(
            "[CONFIG] ❌ MEET_LINK_MODE='auto' requiere "
            "ALLOW_CLIENT_CHOOSE_MODALITY=True.\n"
            "Sin este flag el cliente no puede elegir modalidad y Meet\n"
            "nunca se generaría aunque el modo sea 'auto'.\n"
            "\n"
            "Dónde corregirlo:\n"
            "  Archivo  : src/config/domain_config.py\n"
            "  Variable : ALLOW_CLIENT_CHOOSE_MODALITY\n"
            "  Cambiar  : ALLOW_CLIENT_CHOOSE_MODALITY = True\n"
            "\n"
            "Alternativa: usar MEET_LINK_MODE='always' o 'never' en .env"
        )

    # ── Check 3 — FilterType.MODALITY debe estar enabled en filters config ────
    # ALLOW_CLIENT_CHOOSE_MODALITY=True es necesario pero no suficiente:
    # si el filtro está con enabled=False en domain_filters_config.py,
    # el cliente nunca ve la opción de modalidad en el menú de búsqueda
    # → modality llega None → Meet nunca se genera. Fallo silencioso sin este check.
    try:
        from src.config.domain_filters_config import is_filter_enabled
        from src.filters.filter_types import FilterType
        if not is_filter_enabled(FilterType.MODALITY):
            raise ValueError(
                "[CONFIG] ❌ MEET_LINK_MODE='auto' requiere que el filtro "
                "de modalidad esté habilitado.\n"
                "El cliente nunca verá la opción de elegir modalidad "
                "y Meet no se generaría nunca.\n"
                "\n"
                "Dónde corregirlo:\n"
                "  Archivo  : src/config/domain_filters_config.py\n"
                "  Variable : ENABLED_FILTERS[FilterType.MODALITY]['enabled']\n"
                "  Cambiar  :\n"
                "      FilterType.MODALITY: {\n"
                "          'enabled': True,   # ← era False\n"
                "          'menu_position': 7,\n"
                "          ...\n"
                "      }"
            )
    except ImportError:
        # domain_filters_config aún no existe — skip silencioso
        pass

    print("[CONFIG] ✅ MEET_LINK_MODE=auto — filtro de modalidad activo")




def _validate_oauth_redirect_uri() -> None:
    """
    Valida que GOOGLE_OAUTH_REDIRECT_URI sea coherente con WEBHOOK_URL.

    GOOGLE_OAUTH_REDIRECT_URI debe empezar con el mismo dominio base que
    WEBHOOK_URL. Si difieren, el flujo OAuth2 falla con redirect_uri_mismatch
    en Google — un error difícil de diagnosticar en producción.

    Check solo corre si MEET_LINK_MODE es 'always' o 'auto'.

    Dónde corregirlo:
      Archivo  : .env
      Variable : GOOGLE_OAUTH_REDIRECT_URI
      Valor    : <WEBHOOK_URL>/oauth/callback
    """
    mode = DomainConfig.MEET_LINK_MODE
    if mode not in ('always', 'auto'):
        return

    webhook_url    = os.getenv('WEBHOOK_URL', '').strip().rstrip('/')
    redirect_uri   = os.getenv('GOOGLE_OAUTH_REDIRECT_URI', '').strip().rstrip('/')

    if not webhook_url or not redirect_uri:
        return  # Otros checks ya cubren variables vacías

    # Extraer dominio base de cada URL
    from urllib.parse import urlparse
    webhook_base  = urlparse(webhook_url).netloc   # ej: wbot.gaxoblanco.com
    redirect_base = urlparse(redirect_uri).netloc  # ej: gaxoblanco.com

    if webhook_base != redirect_base:
        raise ValueError(
            f"[CONFIG] ❌ GOOGLE_OAUTH_REDIRECT_URI no coincide con WEBHOOK_URL.\n"
            f"  El flujo OAuth2 va a fallar con 'redirect_uri_mismatch' en Google.\n"
            f"\n"
            f"  WEBHOOK_URL             : {webhook_url}\n"
            f"  GOOGLE_OAUTH_REDIRECT_URI: {redirect_uri}\n"
            f"\n"
            f"  Dónde corregirlo:\n"
            f"  Archivo  : .env\n"
            f"  Variable : GOOGLE_OAUTH_REDIRECT_URI\n"
            f"  Cambiar  : GOOGLE_OAUTH_REDIRECT_URI={webhook_url}/oauth/callback"
        )

    print(f"[CONFIG] ✅ GOOGLE_OAUTH_REDIRECT_URI coherente con WEBHOOK_URL")


def _validate_single_professional_mode() -> None:
    """
    Valida coherencia del modo profesional único.
    Solo corre si SINGLE_PROFESSIONAL_MODE=true.

    Check 0 — dominio compatible (no DEMO).
    Check 1 — SINGLE_PROFESSIONAL_PHONE configurado.
    Check 2 — TENANT_TONE=freelance.
    Check 3 — profesional existe en BD.
    """
    import os
    from src.config.config import Config

    mode = getattr(Config, 'SINGLE_PROFESSIONAL_MODE', False)
    if not mode:
        return

    # ── Check 0 — dominio compatible ─────────────────────────────────────────
    _DOMINIOS_INCOMPATIBLES = {'DEMO'}
    domain = os.getenv('DOMAIN_PRESET', '').upper().strip()
    if domain in _DOMINIOS_INCOMPATIBLES:
        raise ValueError(
            f"[CONFIG] ❌ SINGLE_PROFESSIONAL_MODE=true es incompatible "
            f"con DOMAIN_PRESET='{domain}'.\n"
            f"\n"
            f"Dónde corregirlo:\n"
            f"  Archivo  : .env\n"
            f"  Variable : DOMAIN_PRESET\n"
            f"  Cambiar  : DOMAIN_PRESET=SALUD  (o cualquier preset no-demo)"
        )

    # ── Check 1 — teléfono configurado ───────────────────────────────────────
    phone = getattr(Config, 'SINGLE_PROFESSIONAL_PHONE', '').strip()
    if not phone:
        raise ValueError(
            "[CONFIG] ❌ SINGLE_PROFESSIONAL_MODE=true pero "
            "SINGLE_PROFESSIONAL_PHONE no está configurado.\n"
            "\n"
            "Dónde corregirlo:\n"
            "  Archivo  : .env\n"
            "  Variable : SINGLE_PROFESSIONAL_PHONE\n"
            "  Agregar  : SINGLE_PROFESSIONAL_PHONE=+5491112345678"
        )

    # ── Check 2 — tono compatible ─────────────────────────────────────────────
    _TONES_COMPATIBLES = {'freelance'}
    tone = os.getenv('TENANT_TONE', 'demo').lower().strip()
    if tone not in _TONES_COMPATIBLES:
        raise ValueError(
            f"[CONFIG] ❌ SINGLE_PROFESSIONAL_MODE=true requiere "
            f"TENANT_TONE=freelance.\n"
            f"Tono actual: '{tone}'\n"
            f"\n"
            f"Dónde corregirlo:\n"
            f"  Archivo  : .env\n"
            f"  Variable : TENANT_TONE\n"
            f"  Cambiar  : TENANT_TONE=freelance"
        )

    # ── Check 3 — profesional existe en BD ───────────────────────────────────
    # Caso especial: BD vacía = primer boot. El profesional todavía no puede
    # existir porque el sistema aún no levantó para cargarlo.
    # → WARNING y continúa. El bot arranca, el admin carga el profesional,
    #   y al próximo reinicio el check pasa normalmente.
    #
    # BD con profesionales pero el teléfono no coincide → ERROR real de config:
    # hay datos cargados y el número no matchea ninguno.
    try:
        from src.database.database import db
        prof = db.get_professional(phone)

        if prof is None:
            # Distinguir entre BD vacía (primer boot) y BD con datos pero teléfono incorrecto
            with db.get_connection() as conn:
                total = conn.execute(
                    "SELECT COUNT(*) FROM professionals"
                ).fetchone()[0]

            if total == 0:
                # Primer boot — warning, no error fatal
                print(
                    f"[CONFIG] ⚠️  SINGLE_PROFESSIONAL_MODE=true pero la BD está vacía.\n"
                    f"  Esto es normal en el primer arranque.\n"
                    f"  Cargar el profesional con:\n"
                    f"    docker exec whatsapp-demo python scripts/csv/load_professionals_from_csv.py"
                    f" /app/data/csv_src/profesionales_demo.csv\n"
                    f"  El check se valida al próximo reinicio."
                )
            else:
                # BD con datos pero el teléfono no está → error real de configuración
                raise ValueError(
                    f"[CONFIG] ❌ SINGLE_PROFESSIONAL_MODE=true pero "
                    f"'{phone}' no existe en la base de datos.\n"
                    f"La BD tiene {total} profesional(es) pero ninguno coincide con ese número.\n"
                    f"\n"
                    f"Dónde corregirlo:\n"
                    f"  Archivo  : .env\n"
                    f"  Variable : SINGLE_PROFESSIONAL_PHONE\n"
                    f"  Verificar formato E.164 (+549...) y que coincida "
                    f"exactamente con un profesional cargado en la BD."
                )
        else:
            print(f"[CONFIG] ✅ Modo profesional único — {prof.get('name', phone)}")

    except ValueError:
        raise
    except Exception as e:
        print(f"[CONFIG] ⚠️  Check BD omitido (BD no disponible aún): {e}")


def _validate_demo_mode() -> None:
    """
    Valida coherencia entre TENANT_TONE y DOMAIN_PRESET.

    Check 1 — TENANT_TONE=demo requiere DOMAIN_PRESET=DEMO.
    Check 2 — DOMAIN_PRESET=DEMO requiere TENANT_TONE=demo.

    Evita arrancar un centro real con configuración de demostración
    y viceversa — los mensajes del tono 'demo' no tienen sentido en producción.
    """
    import os

    tone   = os.getenv('TENANT_TONE', 'demo').lower().strip()
    domain = os.getenv('DOMAIN_PRESET', 'SALUD').upper().strip()

    if tone == 'demo' and domain != 'DEMO':
        raise ValueError(
            f"[CONFIG] ❌ TENANT_TONE='demo' requiere DOMAIN_PRESET=DEMO.\n"
            f"Dominio actual: '{domain}'\n"
            f"\n"
            f"Dónde corregirlo:\n"
            f"  Archivo  : .env\n"
            f"  Opciones :\n"
            f"    a) DOMAIN_PRESET=DEMO          → para demostración del producto\n"
            f"    b) TENANT_TONE=coloquial        → para producción con preset SALUD\n"
            f"       TENANT_TONE=freelance        → para modo profesional único"
        )

    if domain == 'DEMO' and tone != 'demo':
        raise ValueError(
            f"[CONFIG] ❌ DOMAIN_PRESET=DEMO requiere TENANT_TONE=demo.\n"
            f"Tono actual: '{tone}'\n"
            f"\n"
            f"Dónde corregirlo:\n"
            f"  Archivo  : .env\n"
            f"  Opciones :\n"
            f"    a) TENANT_TONE=demo             → para demostración del producto\n"
            f"    b) DOMAIN_PRESET=SALUD          → para producción con tono '{tone}'"
        )