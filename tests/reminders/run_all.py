#!/usr/bin/env python3
"""
Runner: Todos los tests del servicio de recordatorio
=====================================================

Corre en orden:
    1. test_failures.py   — Fallos de Twilio (A-D)
    2. test_retry.py      — Reintentos (E)
    3. test_responses.py  — Respuestas del cliente (F-J)

Uso:
    docker exec whatsapp-demo python tests/reminders/run_all.py
    docker exec whatsapp-demo python tests/reminders/run_all.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

VERBOSE = "-v" in sys.argv


class C:
    GREEN  = '\033[92m'; RED    = '\033[91m'
    CYAN   = '\033[96m'; YELLOW = '\033[93m'
    BOLD   = '\033[1m';  DIM    = '\033[2m'
    END    = '\033[0m'

def sep(c='='): print(c * 62)


def run_suite(name: str, module_path: str) -> bool:
    """Corre un módulo de tests y retorna True si todos pasan."""
    sep()
    print(f"\n{C.BOLD}{C.CYAN}  SUITE: {name}{C.END}\n")
    sep()

    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("suite", module_path)
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.run_all()
    except Exception as e:
        print(f"  {C.RED}ERROR cargando {module_path}: {e}{C.END}")
        if VERBOSE:
            import traceback; traceback.print_exc()
        return False


def main():
    base = Path(__file__).parent

    suites = [
        ("Fallos de Twilio (A-D)",          str(base / "test_reminder_failures.py")),
        ("Reintentos (E)",                   str(base / "test_retry.py")),
        ("Respuestas del cliente (F-J)",     str(base / "test_reminder_responses.py")),
    ]

    sep()
    print(f"{C.BOLD}  SERVICIO DE RECORDATORIOS — TEST SUITE COMPLETA{C.END}")
    sep()

    results = []
    for name, path in suites:
        passed = run_suite(name, path)
        results.append((name, passed))
        print()

    # Resumen final
    sep()
    print(f"\n{C.BOLD}  RESUMEN FINAL{C.END}\n")
    total_ok = 0
    for name, passed in results:
        icon = f"{C.GREEN}✅" if passed else f"{C.RED}❌"
        print(f"  {icon} {name}{C.END}")
        if passed:
            total_ok += 1

    print()
    total = len(results)
    if total_ok == total:
        print(f"{C.GREEN}{C.BOLD}  TODAS LAS SUITES PASARON ({total_ok}/{total}){C.END}")
    else:
        print(f"{C.RED}{C.BOLD}  {total - total_ok} SUITES FALLARON ({total_ok}/{total} pasaron){C.END}")
    sep()

    return total_ok == total


if __name__ == "__main__":
    sys.exit(0 if main() else 1)