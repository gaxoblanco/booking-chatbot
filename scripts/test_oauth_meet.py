#!/usr/bin/env python3
"""
test_oauth_meet.py
==================
Valida el flujo OAuth2 completo para Google Meet.

Pasos:
    1. Genera la URL de autorización
    2. Vos la abrís en el browser y autorizás
    3. Google redirige al callback con un código
    4. El script intercambia el código por tokens
    5. Crea un evento de prueba con Meet link
    6. Imprime el hangoutLink

Correr FUERA del Docker (necesita browser):
    python scripts/test_oauth_meet.py
"""

import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv('docker/.env')

from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

# ── Config ────────────────────────────────────────────────────────────────────

CLIENT_ID     = os.getenv('GOOGLE_OAUTH_CLIENT_ID')
CLIENT_SECRET = os.getenv('GOOGLE_OAUTH_CLIENT_SECRET')
REDIRECT_URI  = os.getenv('GOOGLE_OAUTH_REDIRECT_URI')
CALENDAR_ID   = 'gax0blanco93@gmail.com'

SCOPES = ['https://www.googleapis.com/auth/calendar.events']

# ── Paso 1: Generar URL de autorización ──────────────────────────────────────

flow = Flow.from_client_config(
    client_config={
        "web": {
            "client_id":     CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uris": [REDIRECT_URI],
            "auth_uri":      "https://accounts.google.com/o/oauth2/auth",
            "token_uri":     "https://oauth2.googleapis.com/token",
        }
    },
    scopes=SCOPES,
    redirect_uri=REDIRECT_URI
)

auth_url, state = flow.authorization_url(
    access_type='offline',
    include_granted_scopes='true',
    prompt='consent'
)

print("\n" + "="*60)
print("PASO 1 — Abrí esta URL en el browser y autorizá:")
print("="*60)
print(f"\n{auth_url}\n")

# ── Paso 2: Ingresar el código de autorización ────────────────────────────────

print("="*60)
print("PASO 2 — Después de autorizar, Google va a redirigir a:")
print(f"  {REDIRECT_URI}?code=XXXX&state=XXXX")
print("\nCopiá el valor del parámetro 'code' de la URL y pegalo acá:")
print("="*60)
raw = input("\nPegá la URL completa de redirección: ").strip()
if raw.startswith('http'):
    from urllib.parse import urlparse, parse_qs
    parsed = parse_qs(urlparse(raw).query)
    code = parsed.get('code', [raw])[0]
else:
    code = raw
print(f"Código extraído: {code[:30]}...")

# ── Paso 3: Intercambiar código por tokens ────────────────────────────────────

flow.fetch_token(code=code)
credentials = flow.credentials

print(f"   refresh_token COMPLETO: {credentials.refresh_token}")

# Guardar en archivo para copiarlo al Docker
with open('oauth_token_temp.txt', 'w') as f:
    f.write(credentials.refresh_token)
print("✅ Token guardado en oauth_token_temp.txt")

# ── Paso 4: Crear evento con Meet link ────────────────────────────────────────

service = build('calendar', 'v3', credentials=credentials)

event = service.events().insert(
    calendarId=CALENDAR_ID,
    body={
        'summary': '[TEST] Reunión con Meet',
        'start': {'dateTime': '2026-06-25T10:00:00-03:00'},
        'end':   {'dateTime': '2026-06-25T11:00:00-03:00'},
        'conferenceData': {
            'createRequest': {
                'requestId': 'test-oauth-meet-001',
                'conferenceSolutionKey': {'type': 'hangoutsMeet'}
            }
        }
    },
    conferenceDataVersion=1
).execute()

print(f"\n✅ Evento creado:")
print(f"   ID:          {event['id']}")
print(f"   hangoutLink: {event.get('hangoutLink', 'NO GENERADO')}")
print(f"   htmlLink:    {event.get('htmlLink')}")
