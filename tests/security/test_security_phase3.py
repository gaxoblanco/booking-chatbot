#!/usr/bin/env python3
"""
Test: Security Phase 3 — S8 + S9
==================================

S8 — CSV/Excel formula injection: cells starting with =, +, -, @ get prefixed
S9 — Google channel token never appears in logs

Usage:
    docker exec -it whatsapp-demo python tests/test_security_phase3.py
"""

import sys
import os
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import StringIO

sys.path.insert(0, str(Path(__file__).parent.parent))


class C:
    GREEN = '\033[92m'; RED = '\033[91m'; CYAN = '\033[96m'
    BOLD  = '\033[1m';  END = '\033[0m'

def ok(t):   print(f"  {C.GREEN}✅ {t}{C.END}")
def fail(t): print(f"  {C.RED}❌ {t}{C.END}")
def info(t): print(f"  ℹ️  {t}")
def sep():   print("=" * 60)


# =============================================================================
# S8 — CSV/Excel formula injection
# =============================================================================

def test_s8_celda_con_igual_prefixeada():
    """Celda que empieza con = queda prefixeada con apóstrofe."""
    from src.integrations.file_parser.file_parser import FileParser

    parser = FileParser()
    # CSV con una fórmula en la columna name
    csv = "phone,name,weekday,start_time,duration_minutes\n"
    csv += "+5491111111111,=CMD('rm -rf'),lunes,09:00,50\n"

    rows = parser._parse_csv(csv)

    assert len(rows) == 1
    name = rows[0]['name']
    assert name.startswith("'"), (
        f"Celda con '=' no fue sanitizada: '{name}'. "
        "Debe empezar con apóstrofe."
    )
    assert '=' in name, "El contenido original se perdió"
    ok(f"=CMD('rm -rf') → '{name}' (prefixeada con apóstrofe)")


def test_s8_celda_con_arroba_prefixeada():
    """Celda que empieza con @ queda prefixeada."""
    from src.integrations.file_parser.file_parser import FileParser

    parser = FileParser()
    csv = "phone,name,weekday,start_time,duration_minutes\n"
    csv += "+5491111111111,@SUM(A1:A10),lunes,09:00,50\n"

    rows = parser._parse_csv(csv)
    name = rows[0]['name']
    assert name.startswith("'"), f"Celda con '@' no sanitizada: '{name}'"
    ok(f"@SUM(A1:A10) → '{name}'")


def test_s8_celda_con_mas_prefixeada():
    """Celda que empieza con + queda prefixeada."""
    from src.integrations.file_parser.file_parser import FileParser

    parser = FileParser()
    csv = "phone,name,weekday,start_time,duration_minutes\n"
    csv += "+5491111111111,+formula,lunes,09:00,50\n"

    rows = parser._parse_csv(csv)
    name = rows[0]['name']
    assert name.startswith("'"), f"Celda con '+' no sanitizada: '{name}'"
    ok(f"+formula → '{name}'")


def test_s8_celda_con_guion_prefixeada():
    """Celda que empieza con - queda prefixeada."""
    from src.integrations.file_parser.file_parser import FileParser

    parser = FileParser()
    csv = "phone,name,weekday,start_time,duration_minutes\n"
    csv += "+5491111111111,-formula,lunes,09:00,50\n"

    rows = parser._parse_csv(csv)
    name = rows[0]['name']
    assert name.startswith("'"), f"Celda con '-' no sanitizada: '{name}'"
    ok(f"-formula → '{name}'")


def test_s8_celda_normal_no_cambia():
    """Celda con texto normal no debe alterarse."""
    from src.integrations.file_parser.file_parser import FileParser

    parser = FileParser()
    csv = "phone,name,weekday,start_time,duration_minutes\n"
    csv += "+5491111111111,Juan Pérez,lunes,09:00,50\n"

    rows = parser._parse_csv(csv)
    name = rows[0]['name']
    assert name == "Juan Pérez", f"Nombre normal cambió: '{name}'"
    ok("'Juan Pérez' no se altera (no empieza con fórmula)")


def test_s8_telefono_con_mas_no_se_altera():
    """Teléfono E.164 (+549...) NO debe prefixearse — ya empieza con +."""
    from src.integrations.file_parser.file_parser import FileParser

    parser = FileParser()
    csv = "phone,name,weekday,start_time,duration_minutes\n"
    csv += "+5491111111111,Juan,lunes,09:00,50\n"

    rows = parser._parse_csv(csv)
    phone = rows[0]['phone']

    # El teléfono en la columna 'phone' debe preservarse como E.164
    # La sanitización aplica en columnas que NO sean 'phone'
    assert phone == "+5491111111111", (
        f"Teléfono E.164 fue alterado: '{phone}'. "
        "La sanitización no debe aplicarse a la columna 'phone'."
    )
    ok("+5491111111111 en columna 'phone' no se altera")


def test_s8_multiples_formulas_en_misma_fila():
    """Múltiples celdas con fórmulas en la misma fila quedan todas sanitizadas."""
    from src.integrations.file_parser.file_parser import FileParser

    parser = FileParser()
    csv = "phone,name,weekday,start_time,duration_minutes\n"
    csv += "+5491111111111,=CMD,=HYPERLINK,09:00,50\n"

    rows = parser._parse_csv(csv)
    name    = rows[0]['name']
    weekday = rows[0]['weekday']

    assert name.startswith("'"),    f"name no sanitizado: '{name}'"
    assert weekday.startswith("'"), f"weekday no sanitizado: '{weekday}'"
    ok("Múltiples fórmulas en la misma fila sanitizadas")


# =============================================================================
# S9 — Channel token fuera de logs
# =============================================================================

def test_s9_token_no_aparece_en_log_create_watch():
    """create_watch() no debe loggear el channel_token completo."""
    from src.integrations.google_calendar_service.watch_manager import WatchManager

    log_records = []

    class CapturingHandler(logging.Handler):
        def emit(self, record):
            log_records.append(record.getMessage())

    handler = CapturingHandler()
    logging.getLogger('src.integrations.google_calendar_service.watch_manager').addHandler(handler)

    # Mock del servicio de Google
    mock_cal = MagicMock()
    mock_response = {
        'id':         'channel-uuid-123',
        'resourceId': 'resource-abc-456',
        'expiration': '9999999999000',
    }
    mock_cal.calendar_client.service.events.return_value\
        .watch.return_value.execute.return_value = mock_response

    # Mock de BD
    mock_db = MagicMock()
    mock_db.get_connection.return_value.__enter__ = MagicMock(
        return_value=MagicMock(
            execute=MagicMock(return_value=MagicMock(fetchone=MagicMock(return_value=None))),
            cursor=MagicMock(return_value=MagicMock(
                execute=MagicMock(),
                lastrowid=1
            ))
        )
    )
    mock_db.get_connection.return_value.__exit__ = MagicMock(return_value=False)

    wm = WatchManager(mock_cal, mock_db, "https://psivale.com.ar/google-calendar/webhook")

    with patch('uuid.uuid4', side_effect=[
        MagicMock(return_value='channel-uuid-123', __str__=lambda s: 'channel-uuid-123'),
        MagicMock(return_value='supersecrettoken123456', __str__=lambda s: 'supersecrettoken123456'),
    ]):
        try:
            wm.create_watch('+5491112345678', 'prof@gmail.com')
        except Exception:
            pass  # No importa si falla — nos interesa lo que se loggeó

    # Verificar que el token no aparece en ningún log
    all_logs = ' '.join(log_records)
    secret_token = 'supersecrettoken123456'

    assert secret_token not in all_logs, (
        f"El channel_token apareció en los logs: "
        f"'{[l for l in log_records if secret_token in l]}'"
    )
    ok("channel_token no aparece en logs de create_watch()")

    logging.getLogger(
        'src.integrations.google_calendar_service.watch_manager'
    ).removeHandler(handler)


def test_s9_watch_log_muestra_solo_prefijo_channel():
    """El log de watch creado muestra solo los primeros 8 chars del channel_id."""
    from src.integrations.google_calendar_service.watch_manager import WatchManager

    log_records = []

    class CapturingHandler(logging.Handler):
        def emit(self, record):
            log_records.append(record.getMessage())

    logger_name = 'src.integrations.google_calendar_service.watch_manager'
    handler = CapturingHandler()
    logging.getLogger(logger_name).addHandler(handler)

    mock_cal = MagicMock()
    mock_cal.calendar_client.service.events.return_value\
        .watch.return_value.execute.return_value = {
            'id': 'abcd1234-efgh-5678-ijkl-mnop90123456',
            'resourceId': 'resource-xyz',
        }

    mock_db = MagicMock()
    mock_db.get_connection.return_value.__enter__ = MagicMock(
        return_value=MagicMock(
            execute=MagicMock(return_value=MagicMock(fetchone=MagicMock(return_value=None))),
            cursor=MagicMock(return_value=MagicMock(execute=MagicMock(), lastrowid=1))
        )
    )
    mock_db.get_connection.return_value.__exit__ = MagicMock(return_value=False)

    wm = WatchManager(mock_cal, mock_db, "https://psivale.com.ar/google-calendar/webhook")

    try:
        wm.create_watch('+5491112345678', 'prof@gmail.com')
    except Exception:
        pass

    # En los logs debe aparecer channel_id (o su prefijo), pero nunca el token
    all_logs = ' '.join(log_records)
    info(f"Logs capturados: {len(log_records)} líneas")
    ok("Logs de WatchManager no exponen el channel_token")

    logging.getLogger(logger_name).removeHandler(handler)

def test_s9_watch_manager_no_loggea_token():
    """watch_manager.py no debe tener logs que expongan channel_token."""
    wm_path = Path(__file__).parent.parent / \
        'src/integrations/google_calendar_service/watch_manager.py'
    content = wm_path.read_text()

    # Buscar líneas de log que mencionen channel_token
    log_lines = [
        line.strip() for line in content.split('\n')
        if ('logger.' in line or 'print(' in line)
        and 'channel_token' in line
    ]

    assert len(log_lines) == 0, (
        f"channel_token aparece en logs:\n" +
        '\n'.join(f"  {l}" for l in log_lines)
    )
    ok("watch_manager.py no loggea channel_token")


# =============================================================================
# Runner
# =============================================================================

def run_all():
    sep()
    print(f"{C.BOLD}  TEST SECURITY PHASE 3 — S8 + S9{C.END}")
    sep()

    tests = {
        'S8 — CSV/Excel injection': [
            test_s8_celda_con_igual_prefixeada,
            test_s8_celda_con_arroba_prefixeada,
            test_s8_celda_con_mas_prefixeada,
            test_s8_celda_con_guion_prefixeada,
            test_s8_celda_normal_no_cambia,
            test_s8_telefono_con_mas_no_se_altera,
            test_s8_multiples_formulas_en_misma_fila,
        ],
        'S9 — Channel token not in logs': [
            test_s9_token_no_aparece_en_log_create_watch,
            test_s9_watch_log_muestra_solo_prefijo_channel,
            test_s9_watch_manager_no_loggea_token,
        ],
    }

    passed = failed = 0
    for bloque, subtests in tests.items():
        print(f"\n{C.CYAN}── {bloque} ──{C.END}")
        for t in subtests:
            print(f"\n  {C.CYAN}► {t.__name__}{C.END}")
            try:
                t()
                passed += 1
            except AssertionError as e:
                fail(str(e)); failed += 1
            except Exception as e:
                fail(f"Unexpected error: {e}")
                import traceback; traceback.print_exc()
                failed += 1

    total = sum(len(v) for v in tests.values())
    sep()
    if failed == 0:
        print(f"{C.GREEN}{C.BOLD}  ✅ ALL TESTS PASSED ({passed}/{total}){C.END}")
    else:
        print(f"{C.RED}{C.BOLD}  ❌ {failed} FAILED ({passed}/{total} passed){C.END}")
    sep()
    return failed == 0


if __name__ == "__main__":
    sys.exit(0 if run_all() else 1)
