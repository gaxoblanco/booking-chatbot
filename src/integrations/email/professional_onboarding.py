"""
Professional Onboarding Email
==============================
Ubicación: src/integrations/email/professional_onboarding.py

Envía UN SOLO email por profesional con las secciones que aplican
según su estado de configuración.

Casos posibles:
    needs_calendar=True,  needs_oauth=False  → solo sección Calendar
    needs_calendar=False, needs_oauth=True   → solo sección OAuth2/Meet
    needs_calendar=True,  needs_oauth=True   → ambas secciones en un email

Reemplaza a calendar_invitation.py y oauth_invitation.py para el flujo
de carga desde CSV. Esos módulos se mantienen para uso independiente.

Uso:
    from src.integrations.email.professional_onboarding import send_onboarding_emails

    send_onboarding_emails(pendientes, service_account_email)
"""

import os
from src.integrations.email.email_service import send_email
from src.config.domain_config import DomainConfig


def send_onboarding_emails(
    pendientes: list[dict],
    service_account_email: str,
) -> dict:
    """
    Envía un email de onboarding a cada profesional con las secciones
    que necesita según su estado (Calendar, OAuth2/Meet, o ambas).

    Args:
        pendientes: Lista de dicts con keys:
                        name, email, phone, calendar_email,
                        needs_calendar (bool), needs_oauth (bool)
        service_account_email: Email del Service Account de Google

    Returns:
        { 'enviados': int, 'errores': int, 'sin_email': int }
    """
    business_name = getattr(DomainConfig, 'BUSINESS_NAME', 'el sistema')
    stats = {'enviados': 0, 'errores': 0, 'sin_email': 0}

    # Config OAuth2 — necesaria solo si algún prof necesita Meet
    client_id     = os.getenv('GOOGLE_OAUTH_CLIENT_ID', '')
    client_secret = os.getenv('GOOGLE_OAUTH_CLIENT_SECRET', '')
    redirect_uri  = os.getenv('GOOGLE_OAUTH_REDIRECT_URI', '')
    oauth_ready   = all([client_id, client_secret, redirect_uri])

    for prof in pendientes:
        name           = prof.get('name', 'Profesional')
        email          = (prof.get('email') or '').strip()
        phone          = prof.get('phone', '')
        calendar_email = prof.get('calendar_email', '')
        needs_calendar = prof.get('needs_calendar', False)
        needs_oauth    = prof.get('needs_oauth', False)

        if not email:
            print(f"   ⚠️  {name} — sin email, omitido")
            stats['sin_email'] += 1
            continue

        # Generar URL OAuth2 si es necesario
        auth_url = None
        if needs_oauth:
            if not oauth_ready:
                print(f"   ⚠️  {name} — OAuth2 no configurado en .env, se omite sección Meet")
                needs_oauth = False
            else:
                auth_url = _generate_oauth_url(
                    phone, client_id, client_secret, redirect_uri
                )
                if not auth_url:
                    print(f"   ⚠️  {name} — error generando URL OAuth2, se omite sección Meet")
                    needs_oauth = False

        # Construir asunto y HTML según combinación
        if needs_calendar and needs_oauth:
            subject = f"{business_name} — Configurá tu calendario y activá Google Meet"
        elif needs_calendar:
            subject = f"{business_name} — Configurá tu Google Calendar"
        else:
            subject = f"{business_name} — Activá los links de Google Meet"

        html = _build_html(
            name=name,
            calendar_email=calendar_email,
            service_account_email=service_account_email,
            auth_url=auth_url,
            needs_calendar=needs_calendar,
            needs_oauth=needs_oauth,
            business_name=business_name,
        )

        ok, msg = send_email(to=email, subject=subject, html=html)

        if ok:
            secciones = []
            if needs_calendar: secciones.append("Calendar")
            if needs_oauth:    secciones.append("Meet OAuth2")
            print(f"   ✅ {name} <{email}> ({' + '.join(secciones)})")
            stats['enviados'] += 1
        else:
            print(f"   ❌ {name} <{email}> — {msg}")
            stats['errores'] += 1

    return stats


# =========================================================================
# HELPERS PRIVADOS
# =========================================================================

def _generate_oauth_url(
    phone: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> str | None:
    """
    Genera la URL de autorización OAuth2 para el profesional.
    Crea el state en oauth_state_store (TTL 24 horas).

    Returns:
        URL string o None si falla.
    """
    try:
        from google_auth_oauthlib.flow import Flow
        from src.integrations.google.oauth_state_store import oauth_state_store

        state = oauth_state_store.create(phone)

        flow = Flow.from_client_config(
            client_config={
                "web": {
                    "client_id":     client_id,
                    "client_secret": client_secret,
                    "redirect_uris": [redirect_uri],
                    "auth_uri":      "https://accounts.google.com/o/oauth2/auth",
                    "token_uri":     "https://oauth2.googleapis.com/token",
                }
            },
            scopes=['https://www.googleapis.com/auth/calendar.events'],
            redirect_uri=redirect_uri,
            state=state,
        )
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent',
        )
        return auth_url
    except Exception as e:
        print(f"      ⚠️  Error generando URL OAuth2: {e}")
        return None


def _build_html(
    name: str,
    calendar_email: str,
    service_account_email: str,
    auth_url: str | None,
    needs_calendar: bool,
    needs_oauth: bool,
    business_name: str,
) -> str:
    """
    Genera el HTML del email con las secciones que aplican.
    Siempre tiene header y footer. El cuerpo varía según los flags.
    """
    first_name = name.split()[0] if name else 'Profesional'

    # ── Sección Calendar ───────────────────────────────────────────────────
    section_calendar = ""
    if needs_calendar:
        section_calendar = f"""
    <p>
      Para que los pacientes puedan ver tu disponibilidad y reservar turnos,
      necesitamos que compartas tu Google Calendar con nuestra cuenta de servicio.
    </p>

    <div class="sa-box">
      <p class="sa-label">Compartí tu calendario con esta dirección:</p>
      <p class="sa-email">{service_account_email}</p>
    </div>

    <div class="steps">
      <h3>🔧 Pasos para compartir:</h3>
      <ol>
        <li>Abrí <a href="https://calendar.google.com">Google Calendar</a>
            con la cuenta <strong>{calendar_email}</strong></li>
        <li>En <em>"Mis calendarios"</em>, hacé clic en <strong>⋮</strong>
            junto a tu calendario</li>
        <li>Seleccioná <strong>"Configuración y uso compartido"</strong></li>
        <li>Bajá a <em>"Compartir con personas específicas"</em>
            → <strong>"+ Agregar personas"</strong></li>
        <li>Pegá: <code>{service_account_email}</code></li>
        <li>Permisos: <strong>"Hacer cambios en eventos"</strong></li>
        <li>Hacé clic en <strong>"Enviar"</strong></li>
        <li>¡Listo! Esperá 1–2 minutos para que se propaguen los permisos.</li>
      </ol>
    </div>
"""

    # ── Separador (solo si hay las dos secciones) ──────────────────────────
    section_divider = ""
    if needs_calendar and needs_oauth:
        section_divider = '<hr style="border:none;border-top:1px solid #eee;margin:28px 0;">'

    # ── Sección OAuth2/Meet ────────────────────────────────────────────────
    section_oauth = ""
    if needs_oauth and auth_url:
        section_oauth = f"""
    <p>
      Además, para que cada turno incluya automáticamente un link de
      <strong>Google Meet</strong>, necesitamos que autorices el acceso
      a tu calendario con tu cuenta personal.
    </p>

    <p>Solo tenés que hacerlo <strong>una vez</strong> — después el sistema
    genera el link de Meet solo cada vez que un paciente reserva un turno.</p>

    <div class="btn-wrap">
      <a href="{auth_url}" class="btn">✅ Autorizar Google Meet</a>
    </div>

    <div class="note">
      ⏰ <strong>Este link es válido por 24 horas.</strong><br>
      Si lo necesitás nuevo, avisale al administrador del sistema.
    </div>
"""

    # ── Intro dinámica ─────────────────────────────────────────────────────
    if needs_calendar and needs_oauth:
        intro = (f"Tu perfil ya fue creado en <strong>{business_name}</strong>. "
                 f"Para completar la configuración, necesitamos dos cosas:")
    elif needs_calendar:
        intro = (f"Tu perfil ya fue creado en <strong>{business_name}</strong>. "
                 f"Para que los pacientes puedan reservar turnos, "
                 f"solo falta un paso:")
    else:
        intro = (f"Tu perfil en <strong>{business_name}</strong> ya está listo. "
                 f"Para activar los links de Google Meet en tus turnos, "
                 f"necesitamos tu autorización:")

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <style>
    body       {{ font-family: Arial, sans-serif; background:#f5f5f5; margin:0; padding:20px; }}
    .wrap      {{ max-width:600px; margin:0 auto; background:#fff; border-radius:8px;
                  box-shadow:0 2px 8px rgba(0,0,0,.1); overflow:hidden; }}
    .header    {{ background:#2E7D32; color:#fff; padding:28px 40px; text-align:center; }}
    .header h1 {{ margin:0; font-size:20px; }}
    .header p  {{ margin:6px 0 0; opacity:.85; font-size:13px; }}
    .body      {{ padding:28px 40px; color:#333; line-height:1.6; }}
    .body p    {{ margin:0 0 14px; }}
    .sa-box    {{ background:#E8F5E9; border-left:4px solid #2E7D32; border-radius:4px;
                  padding:12px 16px; margin:18px 0; }}
    .sa-label  {{ font-size:11px; color:#555; margin:0 0 4px; text-transform:uppercase; }}
    .sa-email  {{ font-family:monospace; font-size:15px; font-weight:bold;
                  color:#1B5E20; word-break:break-all; margin:0; }}
    .steps     {{ background:#f9f9f9; border-radius:6px; padding:18px 22px; margin:18px 0; }}
    .steps h3  {{ margin:0 0 12px; font-size:14px; }}
    .steps ol  {{ margin:0; padding-left:20px; }}
    .steps li  {{ margin-bottom:8px; font-size:14px; }}
    .steps code {{ background:#e0e0e0; padding:1px 5px; border-radius:3px; font-size:12px; }}
    .btn-wrap  {{ text-align:center; margin:24px 0; }}
    .btn       {{ display:inline-block; background:#1a73e8; color:#fff !important;
                  padding:14px 32px; border-radius:6px; text-decoration:none;
                  font-size:15px; font-weight:bold; }}
    .note      {{ background:#e8f0fe; border-left:4px solid #1a73e8; border-radius:4px;
                  padding:12px 16px; margin:18px 0; font-size:13px; color:#444; }}
    .footer    {{ background:#f0f0f0; text-align:center; padding:14px;
                  font-size:12px; color:#999; }}
    a          {{ color:#2E7D32; }}
  </style>
</head>
<body>
<div class="wrap">

  <div class="header">
    <h1>📅 {business_name}</h1>
    <p>Configuración de tu cuenta</p>
  </div>

  <div class="body">
    <p>Hola, <strong>{first_name}</strong>:</p>
    <p>{intro}</p>
    {section_calendar}
    {section_divider}
    {section_oauth}
    <p>Cualquier duda, respondé este email.</p>
  </div>

  <div class="footer">{business_name} · Sistema de Turnos Online</div>
</div>
</body>
</html>"""
