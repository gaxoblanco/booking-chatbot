"""
OAuth Invitation
================
Ubicación: src/integrations/email/oauth_invitation.py

Genera y envía el email de autorización OAuth2 a profesionales,
para que puedan crear links de Google Meet desde el sistema.

Se usa al cargar profesionales desde CSV cuando MEET_LINK_MODE=always.

Uso:
    from src.integrations.email.oauth_invitation import send_oauth_invitations

    send_oauth_invitations(professionals)
"""

import os
from src.integrations.email.email_service import send_email
from src.config.domain_config import DomainConfig


def send_oauth_invitations(professionals: list[dict]) -> dict:
    """
    Genera el state OAuth2 para cada profesional y envía el email
    con el link de autorización.

    Args:
        professionals: Lista de dicts con keys: name, email, phone

    Returns:
        { 'enviados': int, 'errores': int, 'sin_email': int }
    """
    from src.integrations.google.oauth_state_store import oauth_state_store

    import os
    from google_auth_oauthlib.flow import Flow

    client_id     = os.getenv('GOOGLE_OAUTH_CLIENT_ID', '')
    client_secret = os.getenv('GOOGLE_OAUTH_CLIENT_SECRET', '')
    redirect_uri  = os.getenv('GOOGLE_OAUTH_REDIRECT_URI', '')
    business_name = getattr(DomainConfig, 'BUSINESS_NAME', 'el sistema')

    stats = {'enviados': 0, 'errores': 0, 'sin_email': 0}

    if not all([client_id, client_secret, redirect_uri]):
        print("   ⚠️  OAuth2 no configurado — faltan GOOGLE_OAUTH_CLIENT_ID, "
              "GOOGLE_OAUTH_CLIENT_SECRET o GOOGLE_OAUTH_REDIRECT_URI en .env")
        stats['errores'] = len(professionals)
        return stats

    for prof in professionals:
        name  = prof.get('name', 'Profesional')
        email = (prof.get('email') or '').strip()
        phone = prof.get('phone', '')

        if not email:
            print(f"   ⚠️  {name} — sin email, omitido")
            stats['sin_email'] += 1
            continue

        # Crear state mapeado al teléfono (TTL 24 horas)
        state = oauth_state_store.create(phone)

        # Generar URL de autorización
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

        subject = f"{business_name} — Activá los links de Google Meet"
        html    = _build_html(name, auth_url, business_name)

        ok, msg = send_email(to=email, subject=subject, html=html)

        if ok:
            print(f"   ✅ {name} <{email}>")
            stats['enviados'] += 1
        else:
            print(f"   ❌ {name} <{email}> — {msg}")
            stats['errores'] += 1

    return stats


def _build_html(name: str, auth_url: str, business_name: str) -> str:
    """Genera el HTML del email de autorización OAuth2."""

    first_name = name.split()[0] if name else 'Profesional'

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <style>
    body       {{ font-family: Arial, sans-serif; background:#f5f5f5; margin:0; padding:20px; }}
    .wrap      {{ max-width:600px; margin:0 auto; background:#fff; border-radius:8px;
                  box-shadow:0 2px 8px rgba(0,0,0,.1); overflow:hidden; }}
    .header    {{ background:#1a73e8; color:#fff; padding:28px 40px; text-align:center; }}
    .header h1 {{ margin:0; font-size:20px; }}
    .header p  {{ margin:6px 0 0; opacity:.85; font-size:13px; }}
    .body      {{ padding:28px 40px; color:#333; line-height:1.6; }}
    .body p    {{ margin:0 0 14px; }}
    .btn-wrap  {{ text-align:center; margin:28px 0; }}
    .btn       {{ display:inline-block; background:#1a73e8; color:#fff !important;
                  padding:14px 32px; border-radius:6px; text-decoration:none;
                  font-size:15px; font-weight:bold; }}
    .note      {{ background:#e8f0fe; border-left:4px solid #1a73e8; border-radius:4px;
                  padding:12px 16px; margin:18px 0; font-size:13px; color:#444; }}
    .footer    {{ background:#f0f0f0; text-align:center; padding:14px;
                  font-size:12px; color:#999; }}
    a          {{ color:#1a73e8; }}
  </style>
</head>
<body>
<div class="wrap">

  <div class="header">
    <h1>🎥 {business_name}</h1>
    <p>Activación de Google Meet</p>
  </div>

  <div class="body">
    <p>Hola, <strong>{first_name}</strong>:</p>

    <p>
      Para que cada turno incluya automáticamente un link de
      <strong>Google Meet</strong>, necesitamos que autorices el acceso
      a tu Google Calendar con tu cuenta personal.
    </p>

    <p>Solo tenés que hacerlo <strong>una vez</strong> — después el sistema
    genera el link de Meet solo cada vez que un paciente reserva un turno.</p>

    <div class="btn-wrap">
      <a href="{auth_url}" class="btn">✅ Autorizar Google Meet</a>
    </div>

    <div class="note">
      ⏰ <strong>Este link es válido por 24 horas.</strong><br>
      Si necesitás uno nuevo, avisale al administrador del sistema.
    </div>

    <p>Al hacer click vas a ver una pantalla de Google pidiendo permiso
    para "Ver y editar eventos de Google Calendar". Es el permiso mínimo
    necesario para crear los eventos con Meet.</p>

    <p>Cualquier duda, respondé este email.</p>
  </div>

  <div class="footer">{business_name} · Sistema de Turnos Online</div>
</div>
</body>
</html>"""
