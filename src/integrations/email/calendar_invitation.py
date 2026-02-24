"""
Calendar Invitation
===================
Ubicación: src/integrations/email/calendar_invitation.py

Genera y envía el email de bienvenida a profesionales,
explicando cómo compartir su Google Calendar con el sistema.

Se usa UNA SOLA VEZ al cargar los profesionales desde CSV.

Uso:
    from src.integrations.email.calendar_invitation import send_calendar_invitations

    send_calendar_invitations(professionals, service_account_email)
"""

from src.integrations.email.email_service import send_email
from src.config.domain_config import DomainConfig


def send_calendar_invitations(
    professionals: list[dict],
    service_account_email: str,
) -> dict:
    """
    Envía email de invitación a cada profesional de la lista.

    Args:
        professionals:        Lista de dicts con keys: name, email
        service_account_email: Email del Service Account de Google

    Returns:
        { 'enviados': int, 'errores': int, 'sin_email': int }
    """
    business_name = getattr(DomainConfig, 'BUSINESS_NAME', 'el sistema')
    stats = {'enviados': 0, 'errores': 0, 'sin_email': 0}

    for prof in professionals:
        name  = prof.get('name', 'Profesional')
        email = (prof.get('email') or '').strip()

        if not email:
            print(f"   ⚠️  {name} — sin email, omitido")
            stats['sin_email'] += 1
            continue

        subject = f"Bienvenido/a a {business_name} — Configurá tu Google Calendar"
        html    = _build_html(name, email, service_account_email, business_name)

        ok, msg = send_email(to=email, subject=subject, html=html)

        if ok:
            print(f"   ✅ {name} <{email}>")
            stats['enviados'] += 1
        else:
            print(f"   ❌ {name} <{email}> — {msg}")
            stats['errores'] += 1

    return stats


def _build_html(name: str, email: str, service_account: str, business_name: str) -> str:
    """Genera el HTML del email de invitación."""

    first_name = name.split()[0] if name else 'Profesional'

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
    .footer    {{ background:#f0f0f0; text-align:center; padding:14px;
                  font-size:12px; color:#999; }}
    a          {{ color:#2E7D32; }}
  </style>
</head>
<body>
<div class="wrap">

  <div class="header">
    <h1>📅 {business_name}</h1>
    <p>Configuración de Google Calendar</p>
  </div>

  <div class="body">
    <p>Hola, <strong>{first_name}</strong>:</p>

    <p>
      Tu perfil ya fue creado en <strong>{business_name}</strong>.
      Para que los pacientes puedan ver tu disponibilidad y reservar turnos,
      necesitamos que compartas tu Google Calendar con nuestra cuenta de servicio.
    </p>

    <p>Solo tenés que hacerlo <strong>una vez</strong>.</p>

    <div class="sa-box">
      <p class="sa-label">Compartí tu calendario con esta dirección:</p>
      <p class="sa-email">{service_account}</p>
    </div>

    <div class="steps">
      <h3>🔧 Pasos para compartir:</h3>
      <ol>
        <li>Abrí <a href="https://calendar.google.com">Google Calendar</a> con la cuenta <strong>{email}</strong></li>
        <li>En <em>"Mis calendarios"</em>, hacé clic en <strong>⋮</strong> junto a tu calendario</li>
        <li>Seleccioná <strong>"Configuración y uso compartido"</strong></li>
        <li>Bajá a <em>"Compartir con personas específicas"</em> → <strong>"+ Agregar personas"</strong></li>
        <li>Pegá: <code>{service_account}</code></li>
        <li>Permisos: <strong>"Hacer cambios en eventos"</strong></li>
        <li>Hacé clic en <strong>"Enviar"</strong></li>
        <li>¡Listo! Esperá 1–2 minutos para que se propaguen los permisos.</li>
      </ol>
    </div>

    <p>Cualquier duda, respondé este email.</p>
  </div>

  <div class="footer">{business_name} · Sistema de Turnos Online</div>
</div>
</body>
</html>"""
