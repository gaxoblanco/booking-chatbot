"""
OAuth Health Checker
====================
Ubicación: src/integrations/google/oauth_health_checker.py

Verifica que los refresh_tokens OAuth2 de los profesionales sigan
siendo válidos. Si detecta uno revocado, genera la URL de reautorización
y envía un email al profesional.

Cuándo se ejecuta:
    - Como job diario en APScheduler (engine.py) → job_check_oauth_health
    - Como script manual desde el VPS → scripts/check_oauth_health.py

Lógica de detección:
    El único test confiable es intentar un refresh real contra Google.
    Si responde 'invalid_grant' → token revocado.
    Cualquier otro error (red, timeout) → no se considera revocado,
    se loguea y se continúa.

Cooldown de emails:
    Se mantiene un dict en memoria { phone: datetime } para no reenviar
    el aviso si pasaron menos de 24 horas desde el último envío.
    Se reinicia al reiniciar el proceso — suficiente para evitar spam
    en el ciclo diario normal.

Dependencias:
    - google.oauth2.credentials.Credentials
    - google.auth.transport.requests.Request
    - google_auth_oauthlib.flow.Flow
    - src.database.database.db
    - src.integrations.google.oauth_state_store.oauth_state_store
    - src.integrations.email.email_service.send_email
"""

import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Cooldown en memoria: { phone: datetime_ultimo_envio }
# ──────────────────────────────────────────────────────────────────────────────
_alert_sent_at: dict[str, datetime] = {}
ALERT_COOLDOWN_HOURS = 24


class OAuthHealthChecker:
    """
    Verifica tokens OAuth2 de todos los profesionales activos
    y notifica a los que tienen tokens revocados.
    """

    def __init__(self):
        # Leídas una vez al instanciar para evitar llamadas repetidas a os.getenv
        self.client_id     = os.getenv('GOOGLE_OAUTH_CLIENT_ID', '')
        self.client_secret = os.getenv('GOOGLE_OAUTH_CLIENT_SECRET', '')
        self.redirect_uri  = os.getenv('GOOGLE_OAUTH_REDIRECT_URI', '')
        self.webhook_url   = os.getenv('WEBHOOK_URL', '').rstrip('/')
        self.setup_key     = os.getenv('OAUTH_SETUP_KEY', '')

    # ──────────────────────────────────────────────────────────────────────────
    # Punto de entrada principal
    # ──────────────────────────────────────────────────────────────────────────

    def run(self) -> dict:
        """
        Corre el ciclo completo de verificación para todos los profesionales
        activos que tienen oauth_refresh_token configurado.

        Returns:
            {
                'checked':  int,   # profesionales verificados
                'ok':       int,   # tokens válidos
                'revoked':  int,   # tokens revocados (email enviado)
                'error':    int,   # errores de red u otros (no accionables)
                'notified': int,   # emails enviados exitosamente
            }
        """
        stats = {'checked': 0, 'ok': 0, 'revoked': 0, 'error': 0, 'notified': 0}

        professionals = self._get_professionals_with_oauth()

        if not professionals:
            logger.info("[OAUTH_HEALTH] No hay profesionales con OAuth configurado.")
            return stats

        logger.info(f"[OAUTH_HEALTH] Verificando {len(professionals)} profesional(es)...")

        for prof in professionals:
            stats['checked'] += 1
            phone         = prof['phone']
            name          = prof['name']
            refresh_token = prof['oauth_refresh_token']

            # 1. Verificar el token contra Google
            result = self._verify_token(refresh_token)

            if result == 'ok':
                logger.info(f"[OAUTH_HEALTH] ✅ {name} ({phone}) — token válido")
                stats['ok'] += 1

            elif result == 'revoked':
                logger.warning(f"[OAUTH_HEALTH] ⚠️  {name} ({phone}) — token REVOCADO")
                stats['revoked'] += 1

                # 2. Verificar cooldown antes de notificar
                if self._should_notify(phone):
                    sent = self._notify_professional(prof)
                    if sent:
                        stats['notified'] += 1
                        _alert_sent_at[phone] = datetime.now()
                        logger.info(f"[OAUTH_HEALTH] 📧 Email enviado a {name} ({prof.get('email')})")
                    else:
                        logger.error(f"[OAUTH_HEALTH] ❌ No se pudo enviar email a {name}")
                else:
                    logger.info(f"[OAUTH_HEALTH] ⏳ {name} — cooldown activo, no se reenvía")

            else:  # 'error'
                logger.warning(f"[OAUTH_HEALTH] ⚠️  {name} ({phone}) — error de red, se omite")
                stats['error'] += 1

        logger.info(
            f"[OAUTH_HEALTH] Resultado: "
            f"{stats['ok']} ok, {stats['revoked']} revocados, "
            f"{stats['notified']} notificados, {stats['error']} errores"
        )
        return stats

    # ──────────────────────────────────────────────────────────────────────────
    # Consulta a BD
    # ──────────────────────────────────────────────────────────────────────────

    def _get_professionals_with_oauth(self) -> list[dict]:
        """
        Retorna todos los profesionales activos que tienen
        oauth_refresh_token configurado en BD.

        Returns:
            Lista de dicts con: phone, name, email, oauth_refresh_token
        """
        try:
            from src.database.database import db
            with db.get_connection() as conn:
                rows = conn.execute("""
                    SELECT phone, name, email, oauth_refresh_token
                    FROM professionals
                    WHERE is_active = 1
                      AND oauth_refresh_token IS NOT NULL
                      AND oauth_refresh_token != ''
                    ORDER BY name
                """).fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"[OAUTH_HEALTH] Error consultando BD: {e}")
            return []

    # ──────────────────────────────────────────────────────────────────────────
    # Verificación del token contra Google
    # ──────────────────────────────────────────────────────────────────────────

    def _verify_token(self, refresh_token: str) -> str:
        """
        Intenta hacer un refresh real del token contra Google.

        Returns:
            'ok'      — token válido, refresh exitoso
            'revoked' — Google respondió invalid_grant (token revocado)
            'error'   — cualquier otro error (red, timeout, config)
        """
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            from google.auth.exceptions import RefreshError

            # Construir credenciales solo con el refresh_token
            # (access_token = None fuerza el refresh inmediato)
            creds = Credentials(
                token         = None,
                refresh_token = refresh_token,
                token_uri     = "https://oauth2.googleapis.com/token",
                client_id     = self.client_id,
                client_secret = self.client_secret,
                scopes        = ['https://www.googleapis.com/auth/calendar.events'],
            )

            # Intentar refresh — lanza RefreshError si está revocado
            creds.refresh(Request())
            return 'ok'

        except Exception as e:
            error_str = str(e).lower()
            if 'invalid_grant' in error_str or 'token has been expired or revoked' in error_str:
                return 'revoked'
            # Cualquier otro error: red, config incorrecta, timeout, etc.
            logger.warning(f"[OAUTH_HEALTH] Error inesperado en verify_token: {e}")
            return 'error'

    # ──────────────────────────────────────────────────────────────────────────
    # Cooldown
    # ──────────────────────────────────────────────────────────────────────────

    def _should_notify(self, phone: str) -> bool:
        """
        Retorna True si no se envió alerta en las últimas ALERT_COOLDOWN_HOURS.
        """
        last = _alert_sent_at.get(phone)
        if last is None:
            return True
        return datetime.now() - last > timedelta(hours=ALERT_COOLDOWN_HOURS)

    # ──────────────────────────────────────────────────────────────────────────
    # Notificación al profesional
    # ──────────────────────────────────────────────────────────────────────────

    def _notify_professional(self, prof: dict) -> bool:
        """
        Genera la URL de reautorización y envía el email al profesional.

        Args:
            prof: dict con phone, name, email

        Returns:
            True si el email se envió correctamente
        """
        phone = prof['phone']
        name  = prof['name']
        email = (prof.get('email') or '').strip()

        if not email:
            logger.warning(f"[OAUTH_HEALTH] {name} no tiene email en BD, no se puede notificar")
            return False

        # Generar URL de reautorización via /oauth/start del bot
        reauth_url = self._generate_reauth_url(phone)
        if not reauth_url:
            return False

        # Construir y enviar email
        from src.integrations.email.email_service import send_email
        from src.config.domain_config import DomainConfig

        business_name = getattr(DomainConfig, 'BUSINESS_NAME', 'el sistema')
        subject = f"{business_name} — Reautorizá Google Meet (acción requerida)"
        html    = _build_reauth_email(name, reauth_url, business_name)

        ok, msg = send_email(to=email, subject=subject, html=html)
        if not ok:
            logger.error(f"[OAUTH_HEALTH] Error enviando email a {email}: {msg}")
        return ok

    def _generate_reauth_url(self, phone: str) -> str | None:
        """
        Genera la URL de inicio del flujo OAuth2 via el endpoint /oauth/start
        del bot. El bot crea el state y redirige a Google.

        Returns:
            URL string o None si faltan variables de entorno
        """
        if not self.webhook_url or not self.setup_key:
            logger.error(
                "[OAUTH_HEALTH] Faltan WEBHOOK_URL o OAUTH_SETUP_KEY en .env. "
                "No se puede generar URL de reautorización."
            )
            return None

        import urllib.parse
        url = (
            self.webhook_url + '/oauth/start'
            + '?key='   + urllib.parse.quote(self.setup_key)
            + '&phone=' + urllib.parse.quote(phone)
        )
        return url


# ──────────────────────────────────────────────────────────────────────────────
# HTML del email
# ──────────────────────────────────────────────────────────────────────────────

def _build_reauth_email(name: str, reauth_url: str, business_name: str) -> str:
    """Genera el HTML del email de reautorización."""
    first_name = name.split()[0] if name else 'Profesional'

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <style>
    body       {{ font-family: Arial, sans-serif; background:#f5f5f5; margin:0; padding:20px; }}
    .wrap      {{ max-width:600px; margin:0 auto; background:#fff; border-radius:8px;
                  box-shadow:0 2px 8px rgba(0,0,0,.1); overflow:hidden; }}
    .header    {{ background:#D32F2F; color:#fff; padding:28px 40px; text-align:center; }}
    .header h1 {{ margin:0; font-size:20px; }}
    .header p  {{ margin:6px 0 0; opacity:.85; font-size:13px; }}
    .body      {{ padding:28px 40px; color:#333; line-height:1.6; }}
    .body p    {{ margin:0 0 14px; }}
    .alert     {{ background:#FFEBEE; border-left:4px solid #D32F2F; border-radius:4px;
                  padding:14px 18px; margin:18px 0; font-size:14px; color:#B71C1C; }}
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
    <h1>⚠️ {business_name}</h1>
    <p>Reautorización de Google Meet requerida</p>
  </div>

  <div class="body">
    <p>Hola, <strong>{first_name}</strong>:</p>

    <div class="alert">
      <strong>Los pacientes no pueden reservar turnos con Meet en este momento.</strong><br>
      Tu autorización de Google Calendar venció o fue revocada.
    </div>

    <p>
      Para que el sistema vuelva a generar links de Google Meet automáticamente,
      necesitamos que renueves la autorización. Solo toma 30 segundos:
    </p>

    <div class="btn-wrap">
      <a href="{reauth_url}" class="btn">🔄 Renovar autorización</a>
    </div>

    <div class="note">
      ⏰ <strong>Este link es válido por 24 horas.</strong><br>
      Si ya lo usaste o expiró, respondé este email para que te enviemos uno nuevo.
    </div>

    <p>
      <strong>¿Por qué pasó esto?</strong><br>
      Google revoca el acceso automáticamente si la cuenta no se usa por varios meses,
      o si cambiaste tu contraseña de Google. Es un mecanismo de seguridad estándar.
    </p>

    <p>Cualquier duda, respondé este email.</p>
  </div>

  <div class="footer">{business_name} · Sistema de Turnos Online</div>
</div>
</body>
</html>"""


# ──────────────────────────────────────────────────────────────────────────────
# Instancia global (mismo patrón que el resto del proyecto)
# ──────────────────────────────────────────────────────────────────────────────
oauth_health_checker = OAuthHealthChecker()
