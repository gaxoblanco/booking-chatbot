#!/usr/bin/env python3
"""
setup_oauth_meet.py
===================
Autoriza a un profesional para generar Meet links via OAuth2.
Guarda el refresh_token directamente en la BD del container Docker.

Flujo correcto:
    1. Script pide al bot que cree el state via GET /oauth/start
       → el state queda en el proceso Flask (mismo que atiende /oauth/callback)
    2. Bot redirige al browser a Google para autorizar
    3. Google redirige a /oauth/callback del bot
    4. Bot intercambia el code por tokens y los guarda en BD
    5. Script hace polling a la BD para confirmar

Requiere en docker/.env:
    OAUTH_SETUP_KEY=<token seguro>
    GOOGLE_OAUTH_CLIENT_ID=...
    GOOGLE_OAUTH_CLIENT_SECRET=...

Uso:
    python scripts/setup_oauth_meet.py
    python scripts/setup_oauth_meet.py --phone +5491112345678
    python scripts/setup_oauth_meet.py --port 5001
"""

import argparse
import sys
import time
import webbrowser
import subprocess
import requests
from pathlib import Path


DEFAULT_CONTAINER = "whatsapp-demo"
DEFAULT_PORT      = 5001


class C:
    GREEN  = '\033[92m'
    RED    = '\033[91m'
    YELLOW = '\033[93m'
    BOLD   = '\033[1m'
    END    = '\033[0m'

def ok(t):      print(f"{C.GREEN}✅ {t}{C.END}")
def err(t):     print(f"{C.RED}❌ {t}{C.END}")
def warn(t):    print(f"{C.YELLOW}⚠️  {t}{C.END}")
def info(t):    print(f"   {t}")
def sep():      print("=" * 60)
def sep_thin(): print("-" * 60)


def _load_env() -> dict:
    env = {}
    for path in [
        Path(__file__).parent.parent / 'docker' / '.env',
        Path(__file__).parent.parent / '.env',
    ]:
        if path.exists():
            for line in path.read_text(encoding='utf-8').splitlines():
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, _, v = line.partition('=')
                    env[k.strip()] = v.strip()
            return env
    return env


def _docker_exec(container: str, code: str, timeout: int = 10) -> str:
    result = subprocess.run(
        ['docker', 'exec', container, 'python', '-c', code],
        capture_output=True, text=True, timeout=timeout,
    )
    return result.stdout.strip()


def _check_container(container: str) -> bool:
    try:
        out = subprocess.run(
            ['docker', 'inspect', '--format', '{{.State.Status}}', container],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip()
        return out == 'running'
    except Exception:
        return False


def _get_professional_phone(container: str, env: dict, phone_arg: str) -> str:
    if phone_arg:
        return phone_arg.strip()
    try:
        phone = _docker_exec(
            container,
            "import os; print(os.getenv('SINGLE_PROFESSIONAL_PHONE', ''))"
        )
        if phone:
            return phone
    except Exception:
        pass
    phone = env.get('SINGLE_PROFESSIONAL_PHONE', '').strip()
    if phone:
        return phone
    print()
    return input("  Teléfono del profesional (formato +549...): ").strip()


def _verify_token_in_db(container: str, phone: str) -> bool:
    code = f"""
import sys
sys.path.insert(0, '/app')
from src.database.database import db
tokens = db.get_professional_oauth_tokens('{phone}')
print('OK' if tokens else 'MISSING')
"""
    try:
        return 'OK' in _docker_exec(container, code, timeout=10)
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Setup OAuth2 para Meet links — usa /oauth/start del bot'
    )
    parser.add_argument('--phone',     help='Teléfono del profesional (+549...)')
    parser.add_argument('--container', default=DEFAULT_CONTAINER)
    parser.add_argument('--port',      type=int, default=DEFAULT_PORT)
    args = parser.parse_args()

    sep()
    print(f"{C.BOLD}  🔑 Setup OAuth2 para Google Meet{C.END}")
    sep()

    # ── 1. Cargar config ──────────────────────────────────────────────────────
    env = _load_env()

    setup_key = env.get('OAUTH_SETUP_KEY', '').strip()
    if not setup_key:
        err("OAUTH_SETUP_KEY no está en docker/.env")
        info("Generarla con:")
        info("  python -c \"import secrets; print(secrets.token_urlsafe(32))\"")
        info("Y agregarla en docker/.env:")
        info("  OAUTH_SETUP_KEY=<el valor generado>")
        sys.exit(1)

    webhook_url = env.get('WEBHOOK_URL', '').strip()
    if not webhook_url:
        err("WEBHOOK_URL no configurada en docker/.env")
        sys.exit(1)

    # ── 2. Verificar container ────────────────────────────────────────────────
    print(f"\n  Verificando container '{args.container}'...")
    if not _check_container(args.container):
        err(f"Container '{args.container}' no está corriendo.")
        sys.exit(1)
    ok(f"Container activo")

    try:
        r = requests.get(f"http://localhost:{args.port}/", timeout=3)
        ok(f"Bot responde en localhost:{args.port}") if r.status_code == 200 else warn(f"Bot no responde en :{args.port}")
    except Exception:
        warn(f"No se pudo verificar el bot en :{args.port}")

    # ── 3. Resolver teléfono ──────────────────────────────────────────────────
    phone = _get_professional_phone(args.container, env, args.phone)
    if not phone:
        err("No se pudo determinar el teléfono del profesional.")
        sys.exit(1)
    ok(f"Profesional: {phone}")

    # ── 4. Verificar si ya tiene token ────────────────────────────────────────
    if _verify_token_in_db(args.container, phone):
        warn(f"El profesional ya tiene OAuth2 configurado.")
        info("Para renovarlo, continuar igual (Google reemplazará el token).")
        print()

    # ── 5. Construir URL de /oauth/start ─────────────────────────────────────
    # /oauth/start es el endpoint del bot que:
    #   a) Crea el state en el proceso Flask correcto
    #   b) Redirige al browser a Google
    # Así el state queda en la misma instancia que /oauth/callback
    import urllib.parse
    start_url = (
        webhook_url.rstrip('/') + '/oauth/start'
        + '?key=' + urllib.parse.quote(setup_key)
        + '&phone=' + urllib.parse.quote(phone)
    )

    sep()
    print(f"\n{C.BOLD}  PASO 1 — Abriendo browser para autorizar...{C.END}")
    sep_thin()
    print(f"\n  URL de inicio:")
    print(f"  {start_url[:80]}...")
    print(f"\n  El bot va a redirigirte a Google para autorizar.")
    sep_thin()

    try:
        webbrowser.open(start_url)
        ok("Browser abierto")
    except Exception:
        warn("No se pudo abrir el browser automáticamente.")
        info(f"Abrí esta URL manualmente: {start_url}")

    # ── 6. Esperar que /oauth/callback guarde el token ────────────────────────
    print(f"\n{C.BOLD}  PASO 2 — Completá la autorización en Google{C.END}")
    info("Después de autorizar, Google redirige al bot automáticamente.")
    info("El bot guarda el token en BD. Esperando 90 segundos...")
    sep_thin()

    deadline = time.time() + 90
    guardado  = False
    while time.time() < deadline:
        time.sleep(3)
        print(f"  ⏳ Verificando BD... ({int(deadline - time.time())}s restantes)", end='\r')
        if _verify_token_in_db(args.container, phone):
            guardado = True
            break
    print()

    # ── 7. Resultado ──────────────────────────────────────────────────────────
    sep()
    if guardado:
        ok(f"OAuth2 configurado para {phone}")
        info("")
        info("El próximo turno agendado generará Meet link automáticamente.")
    else:
        err("Token NO llegó a BD en 90 segundos.")
        print()
        warn("Revisar logs del bot:")
        info(f"  docker compose -f docker/docker-compose.yml logs --tail=40 {args.container}")
        print()
        warn("Fallback manual — si tenés el refresh_token disponible:")
        info(f"  docker exec {args.container} python -c \"")
        info(f"    from src.database.database import db")
        info(f"    db.update_professional_oauth_tokens(")
        info(f"        phone='{phone}',")
        info(f"        refresh_token='PEGAR_TOKEN_ACÁ',")
        info(f"        access_token=None, token_expiry=None)")
        info(f"  \"")
        sys.exit(1)

    sep()


if __name__ == '__main__':
    main()