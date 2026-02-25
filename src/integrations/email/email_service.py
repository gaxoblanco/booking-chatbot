"""
Email Service - SMTP
====================
Ubicación: src/integrations/email/email_service.py

Envía emails via SMTP estándar. Compatible con cualquier
proveedor (@miweb.com, Gmail, Outlook, etc.)

Variables requeridas en .env:
    SMTP_HOST=mail.miweb.com
    SMTP_PORT=587
    SMTP_USER=sistema@miweb.com
    SMTP_PASSWORD=tu_password
    SMTP_FROM_NAME=Mi Sistema
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_email(to: str, subject: str, html: str) -> tuple[bool, str]:
    """
    Envía un email HTML via SMTP.

    Args:
        to:      Email del destinatario
        subject: Asunto
        html:    Cuerpo en HTML

    Returns:
        (True, 'OK') o (False, 'mensaje de error')
    """
    host      = os.getenv('SMTP_HOST', '')
    port      = int(os.getenv('SMTP_PORT', 587))
    user      = os.getenv('SMTP_USER', '')
    password  = os.getenv('SMTP_PASSWORD', '')
    from_name = os.getenv('SMTP_FROM_NAME', 'Sistema')

    if not all([host, user, password]):
        return False, "SMTP no configurado. Revisar SMTP_HOST, SMTP_USER, SMTP_PASSWORD en .env"

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From']    = f"{from_name} <{user}>"
        msg['To']      = to

        # Texto plano simple como fallback
        plain = html.replace('<br>', '\n').replace('<br/>', '\n')
        import re
        plain = re.sub(r'<[^>]+>', '', plain)
        msg.attach(MIMEText(plain.strip(), 'plain', 'utf-8'))
        msg.attach(MIMEText(html,          'html',  'utf-8'))

        with smtplib.SMTP_SSL(host, port) as server:
            server.ehlo()
            server.login(user, password)
            server.sendmail(user, to, msg.as_string())

        return True, 'OK'

    except smtplib.SMTPAuthenticationError:
        return False, "Credenciales incorrectas"
    except Exception as e:
        return False, str(e)


def is_configured() -> bool:
    """Retorna True si las variables SMTP están completas."""
    return all([
        os.getenv('SMTP_HOST'),
        os.getenv('SMTP_USER'),
        os.getenv('SMTP_PASSWORD'),
    ])
