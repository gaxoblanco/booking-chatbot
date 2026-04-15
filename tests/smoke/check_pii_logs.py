#!/usr/bin/env python3
"""
check_pii_logs.py
=================
Analiza los logs del container buscando teléfonos expuestos en claro.

Corre DESDE DENTRO del container — no necesita servidor HTTP ni producción.

Uso:
    docker exec -it whatsapp-demo python check_pii_logs.py

Qué analiza:
    1. Teléfonos argentinos (+549...) en logs de Docker
    2. Qué líneas los contienen y de qué módulo vienen
    3. Si viene de print() o de logger (para saber dónde parchear)
    4. Resumen con módulos más problemáticos

Interpreta los resultados:
    ✅ 0 expuestos   → S6 completo, listo para producción
    ⚠️  1-10         → Migración incompleta, módulos específicos a parchear
    ❌  10+          → Migración S6 no aplicada
"""

import re
import sys
import subprocess
from collections import Counter

# ── Colores ───────────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def ok(msg):   print(f"  {GREEN}✅ {msg}{RESET}")
def fail(msg): print(f"  {RED}❌ {msg}{RESET}")
def warn(msg): print(f"  {YELLOW}⚠️  {msg}{RESET}")
def info(msg): print(f"  {CYAN}ℹ️  {msg}{RESET}")

# ── Patrones ──────────────────────────────────────────────────────────────────

# Teléfono argentino en claro: +549 seguido de 8+ dígitos
PATRON_EXPUESTO   = re.compile(r'\+549\d{8,}')
# Teléfono enmascarado: +549****5678 (tiene asteriscos)
PATRON_ENMASCARADO = re.compile(r'\+549[\d\*]{4,}\*+\d{4}')

# Módulos/prefijos conocidos en los logs para identificar origen
PREFIJOS_MODULOS = [
    '[SESSION]', '[CLIENT]', '[CANCEL_HANDLER]', '[REMINDER]',
    '[SLOT-OFFER]', '[WAITLIST]', '[MSG-SENDER]', '[NOTIFIER]',
    '[GCAL-SYNC]', '[LOG]', '[CTX]', '[RATE_LIMIT]', '[DB]',
    'INFO:', 'WARNING:', 'ERROR:', 'DEBUG:',
]

def identificar_modulo(linea: str) -> str:
    """Intenta identificar el módulo/origen de una línea de log."""
    for prefijo in PREFIJOS_MODULOS:
        if prefijo in linea:
            return prefijo
    if 'print' in linea.lower() or linea.strip().startswith('['):
        return '[print() directo]'
    return '[desconocido]'

# ── Obtener logs ──────────────────────────────────────────────────────────────

def obtener_logs(tail: int = 500) -> list[str]:
    """
    Intenta obtener logs via docker desde dentro del container.
    Si no está disponible, pide que se redirija el archivo.
    """
    # Intento 1: docker logs (si docker está en PATH dentro del container)
    try:
        result = subprocess.run(
            ['docker', 'logs', '--tail', str(tail), 'whatsapp-demo'],
            capture_output=True, text=True, timeout=10
        )
        lineas = (result.stdout + result.stderr).splitlines()
        if lineas:
            return lineas
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Intento 2: leer desde stdin (pipe desde fuera)
    if not sys.stdin.isatty():
        return sys.stdin.read().splitlines()

    return []

# ── Análisis principal ────────────────────────────────────────────────────────

def analizar(lineas: list[str]) -> dict:
    """
    Analiza las líneas buscando teléfonos expuestos.
    Retorna estadísticas detalladas.
    """
    expuestos       = []   # (linea_num, telefono, linea_texto)
    enmascarados    = 0
    modulos_counter = Counter()

    for i, linea in enumerate(lineas, 1):
        # Contar enmascarados (para saber que S6 funciona en algo)
        if PATRON_ENMASCARADO.search(linea):
            enmascarados += 1
            continue

        # Buscar expuestos
        matches = PATRON_EXPUESTO.findall(linea)
        for telefono in matches:
            modulo = identificar_modulo(linea)
            modulos_counter[modulo] += 1
            expuestos.append((i, telefono, linea.strip()[:120]))

    return {
        'expuestos':        expuestos,
        'enmascarados':     enmascarados,
        'modulos_counter':  modulos_counter,
        'total_lineas':     len(lineas),
    }

# ── Output ────────────────────────────────────────────────────────────────────

def imprimir_resultados(stats: dict):
    n_expuestos = len(stats['expuestos'])
    n_enmascarados = stats['enmascarados']

    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  ANÁLISIS PII EN LOGS{RESET}")
    print(f"{BOLD}{'='*60}{RESET}")
    info(f"Líneas analizadas: {stats['total_lineas']}")
    info(f"Teléfonos enmascarados (S6 activo en estos): {n_enmascarados}")

    print()

    if n_expuestos == 0:
        ok("Sin teléfonos en claro — S6 completo ✅")
        print(f"\n  {GREEN}Listo para producción.{RESET}\n")
        return

    # Hay exposiciones
    if n_expuestos <= 10:
        warn(f"{n_expuestos} teléfonos en claro — migración S6 incompleta")
    else:
        fail(f"{n_expuestos} teléfonos en claro — S6 no aplicado")

    # Módulos más problemáticos
    print(f"\n{BOLD}  Orígenes (módulos con más exposiciones):{RESET}")
    for modulo, count in stats['modulos_counter'].most_common(8):
        barra = '█' * min(count, 20)
        print(f"    {YELLOW}{modulo:30}{RESET} {count:3}x  {barra}")

    # Muestra de líneas problemáticas (máx 10)
    print(f"\n{BOLD}  Muestra de líneas con teléfonos expuestos:{RESET}")
    muestra = stats['expuestos'][:10]
    for num_linea, telefono, texto in muestra:
        print(f"    {CYAN}L{num_linea:4}{RESET}  {RED}{telefono}{RESET}")
        print(f"         {texto}")
        print()

    if len(stats['expuestos']) > 10:
        info(f"... y {len(stats['expuestos']) - 10} más")

    # Guía de acción
    print(f"\n{BOLD}  Qué hacer:{RESET}")
    modulos_a_parchear = [m for m, _ in stats['modulos_counter'].most_common(5)]

    if '[SESSION]' in modulos_a_parchear:
        warn("[SESSION] viene de states.py → transition_to() usa print() directo")
        info("  Fix: reemplazar print() en SessionData.transition_to() con get_logger()")

    if '[CLIENT]' in modulos_a_parchear or '[CANCEL_HANDLER]' in modulos_a_parchear:
        warn("[CLIENT]/[CANCEL_HANDLER] vienen de client_handler.py")
        info("  Fix: reemplazar print() con logger = get_logger(__name__)")

    if '[LOG]' in modulos_a_parchear:
        warn("[LOG] viene de whatsapp_handler.py o bot_controller.py")
        info("  Fix: migrar logging.getLogger() → get_logger() en esos módulos")

    if 'INFO:' in modulos_a_parchear or 'WARNING:' in modulos_a_parchear:
        warn("INFO:/WARNING: vienen de módulos que usan logger estándar sin sanitizar")
        info("  Fix: cambiar logging.getLogger(__name__) → get_logger(__name__)")

    print()
    info("Para parchear un módulo:")
    print(f"""
    {CYAN}# Antes:{RESET}
    import logging
    logger = logging.getLogger(__name__)

    {CYAN}# Después:{RESET}
    from src.core.logger import get_logger
    logger = get_logger(__name__)

    {CYAN}# Para print() directos con teléfonos, reemplazar:{RESET}
    print(f"[SESSION] {{_sanitize(phone)}}: ...")
    {CYAN}# por:{RESET}
    from src.core.logger import _sanitize
    print(f"[SESSION] {{_sanitize(phone)}}: ...")
""")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"\n{BOLD}Obteniendo logs del container...{RESET}")

    lineas = obtener_logs(tail=500)

    if not lineas:
        fail("No se pudieron obtener logs.")
        print("""
  Opciones:
    1. Correr desde tu máquina (tiene acceso a docker):
       docker exec -it whatsapp-demo python check_pii_logs.py

    2. Pasar los logs por pipe desde fuera del container:
       docker logs --tail 500 whatsapp-demo 2>&1 | \\
           docker exec -i whatsapp-demo python check_pii_logs.py
""")
        sys.exit(1)

    info(f"Logs obtenidos: {len(lineas)} líneas")

    stats = analizar(lineas)
    imprimir_resultados(stats)

    # Exit code para usar en CI
    sys.exit(0 if len(stats['expuestos']) == 0 else 1)


if __name__ == '__main__':
    main()
