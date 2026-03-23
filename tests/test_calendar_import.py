#!/usr/bin/env python3
"""
Test: GAP 4 — Flujo de análisis y confirmación de agenda
=========================================================

Verifica el flujo completo de importación SIN llamar a Twilio ni Google Calendar.
Todos los externos están mockeados.

Flujo testeado:
    1. analyze() clasifica filas en ready/duplicate/overlap/error
    2. format_review_menu() genera el menú de confirmación
    3. format_detail() genera el detalle de cada subconjunto
    4. execute() llama a Calendar y BD solo con los 'ready'
    5. format_execute_result() genera el mensaje final
    6. handle_prof_agenda_import_review() maneja las opciones del profesional
    7. handle_prof_agenda_import_detail() vuelve al menú desde el detalle

Uso:
    docker exec -it whatsapp-demo python tests/test_gap4_agenda_flow.py
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.calendar_import_service import CalendarImportService
from src.core.states import ConversationState, SessionData

# ── Colores ──────────────────────────────────────────────────────────────────
class C:
    GREEN = '\033[92m'; RED = '\033[91m'; CYAN = '\033[96m'
    BOLD  = '\033[1m';  END = '\033[0m'

def ok(t):   print(f"  {C.GREEN}✅ {t}{C.END}")
def fail(t): print(f"  {C.RED}❌ {t}{C.END}")
def info(t): print(f"  ℹ️  {t}")
def sep():   print("=" * 60)

# ── Datos de prueba ───────────────────────────────────────────────────────────
PROF_PHONE = "+5490000099001"

# Filas simuladas (como si vinieran de FileParser)
ROWS_MIXED = [
    # Válido — debe ir a 'ready'
    {
        'phone': '+5491111111111', 'name': 'Juan Pérez',
        'weekday': 'lunes', 'start_time': '09:00',
        'duration_minutes': '50', 'modality': 'presencial',
    },
    # Válido — debe ir a 'ready'
    {
        'phone': '+5492222222222', 'name': 'María García',
        'weekday': 'martes', 'start_time': '10:00',
        'duration_minutes': '50',
    },
    # Teléfono inválido — debe ir a 'error'
    {
        'phone': '11-1234-5678', 'name': 'Carlos Error',
        'weekday': 'miércoles', 'start_time': '11:00',
        'duration_minutes': '50',
    },
    # Día inválido — debe ir a 'error'
    {
        'phone': '+5493333333333', 'name': 'Ana Día Inválido',
        'weekday': 'funday', 'start_time': '12:00',
        'duration_minutes': '50',
    },
    # Datos incompletos — debe ir a 'error'
    {
        'phone': '', 'name': 'Sin Teléfono',
        'weekday': 'viernes', 'start_time': '13:00',
        'duration_minutes': '50',
    },
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_session(phone=PROF_PHONE) -> SessionData:
    return SessionData(phone)

def _make_service() -> CalendarImportService:
    return CalendarImportService()


# ── Tests Bloque A: analyze() ─────────────────────────────────────────────────

def test_analyze_clasifica_ready():
    """Las filas válidas sin solapamiento van a 'ready'."""
    svc = _make_service()

    # check_overlap retorna None → sin conflicto
    with patch('src.services.calendar_import_service.CalendarImportService.analyze',
               wraps=svc.analyze):
        with patch(
            'scripts.csv.load_patients_from_csv.check_overlap',
            return_value=None
        ):
            result = svc.analyze(ROWS_MIXED, PROF_PHONE)

    assert len(result['ready']) == 2, (
        f"Esperado 2 ready, obtenido {len(result['ready'])}"
    )
    nombres = [r['name'] for r in result['ready']]
    assert 'Juan Pérez'   in nombres
    assert 'María García' in nombres
    ok(f"analyze() clasifica 2 filas como 'ready': {nombres}")


def test_analyze_clasifica_errors():
    """Filas con datos inválidos van a 'error'."""
    svc = _make_service()

    with patch('scripts.csv.load_patients_from_csv.check_overlap', return_value=None):
        result = svc.analyze(ROWS_MIXED, PROF_PHONE)

    assert len(result['error']) == 3, (
        f"Esperado 3 errores, obtenido {len(result['error'])}"
    )
    razones = [e['error_reason'] for e in result['error']]
    info(f"Razones de error: {razones}")
    ok(f"analyze() clasifica 3 filas como 'error'")


def test_analyze_clasifica_overlap():
    """Fila con solapamiento de horario va a 'overlap'."""
    svc = _make_service()

    conflicto_mock = {
        'tipo':        'solapado',
        'ocupado_por': 'Pedro Existente',
        'inicio':      '09:00',
        'fin':         '09:50',
    }

    # Solo la primera fila válida tiene solapamiento
    call_count = [0]
    def mock_overlap(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return conflicto_mock
        return None

    with patch('scripts.csv.load_patients_from_csv.check_overlap',
               side_effect=mock_overlap):
        result = svc.analyze(ROWS_MIXED, PROF_PHONE)

    assert len(result['overlap']) >= 1, (
        f"Esperado al menos 1 overlap, obtenido {len(result['overlap'])}"
    )
    assert result['overlap'][0]['conflict_with'] == 'Pedro Existente'
    ok("analyze() clasifica solapamiento correctamente")


def test_analyze_clasifica_duplicate():
    """Fila duplicada (mismo paciente + mismo horario) va a 'duplicate'."""
    svc = _make_service()

    dup_mock = {
        'tipo':        'duplicado',
        'ocupado_por': 'Juan Pérez (mismo paciente)',
        'inicio':      '09:00',
        'fin':         '09:50',
    }

    with patch('scripts.csv.load_patients_from_csv.check_overlap',
               return_value=dup_mock):
        result = svc.analyze(ROWS_MIXED[:1], PROF_PHONE)

    assert len(result['duplicate']) == 1
    ok("analyze() clasifica duplicado correctamente")


def test_analyze_tiene_timestamp():
    """El resultado incluye 'analyzed_at'."""
    svc = _make_service()

    with patch('scripts.csv.load_patients_from_csv.check_overlap', return_value=None):
        result = svc.analyze(ROWS_MIXED, PROF_PHONE)

    assert 'analyzed_at' in result
    assert result['analyzed_at']  # no vacío
    ok(f"analyze() incluye analyzed_at: {result['analyzed_at'][:19]}")


# ── Tests Bloque B: format_review_menu() ─────────────────────────────────────

def test_format_review_menu_con_ready():
    """El menú incluye opción 1 cuando hay pacientes listos."""
    svc      = _make_service()
    analysis = {
        'ready': [{'name': 'Juan'}],
        'duplicate': [],
        'overlap': [{'name': 'María'}],
        'error': [],
    }
    msg = svc.format_review_menu(analysis)

    assert '1️⃣' in msg,   "Debe incluir opción 1 (confirmar carga)"
    assert '2️⃣' in msg,   "Debe incluir opción 2 (ver listos)"
    assert '0️⃣' in msg,   "Debe incluir opción 0 (cancelar)"
    assert '1' in msg,     "Debe mencionar 1 listo para cargar"
    ok("format_review_menu() incluye todas las opciones con ready > 0")


def test_format_review_menu_sin_ready():
    """El menú NO incluye opción 1 cuando no hay pacientes listos."""
    svc      = _make_service()
    analysis = {'ready': [], 'duplicate': [], 'overlap': [], 'error': []}
    msg      = svc.format_review_menu(analysis)

    assert 'No hay pacientes nuevos' in msg
    ok("format_review_menu() avisa cuando no hay pacientes listos")


# ── Tests Bloque C: format_detail() ──────────────────────────────────────────

def test_format_detail_ready():
    """format_detail muestra los pacientes listos."""
    svc      = _make_service()
    analysis = {
        'ready': [
            {'name': 'Juan Pérez', 'phone': '+5491111111111',
             'weekday': 'lunes', 'start_time': '09:00'},
            {'name': 'María García', 'phone': '+5492222222222',
             'weekday': 'martes', 'start_time': '10:00'},
        ],
        'duplicate': [], 'overlap': [], 'error': [],
    }
    msg = svc.format_detail(analysis, 'ready')

    assert 'Juan Pérez'   in msg
    assert 'María García' in msg
    assert 'volver' in msg.lower()
    ok("format_detail('ready') lista los pacientes listos")


def test_format_detail_vacio():
    """format_detail avisa cuando el subconjunto está vacío."""
    svc      = _make_service()
    analysis = {'ready': [], 'duplicate': [], 'overlap': [], 'error': []}
    msg      = svc.format_detail(analysis, 'overlap')

    assert 'No hay pacientes' in msg
    ok("format_detail() avisa cuando el subconjunto está vacío")


def test_format_detail_overlap_muestra_conflicto():
    """format_detail de overlap muestra con quién hay solapamiento."""
    svc      = _make_service()
    analysis = {
        'ready': [], 'duplicate': [], 'error': [],
        'overlap': [{
            'name': 'Ana López', 'phone': '+5494444444444',
            'weekday': 'jueves', 'start_time': '14:00',
            'conflict_with': 'Pedro Gómez',
            'conflict_start': '14:00', 'conflict_end': '14:50',
        }],
    }
    msg = svc.format_detail(analysis, 'overlap')

    assert 'Ana López'    in msg
    assert 'Pedro Gómez'  in msg
    ok("format_detail('overlap') muestra el conflicto con quién")


# ── Tests Bloque D: execute() ─────────────────────────────────────────────────

def test_execute_solo_carga_ready():
    """execute() solo procesa los 'ready', ignora los demás."""
    svc = _make_service()

    analysis = {
        'ready': [{
            'phone': '+5491111111111', 'name': 'Juan Pérez',
            'weekday': 'lunes', 'start_time': '09:00', 'end_time': '09:50',
            'duration_minutes': 50, 'weekday_idx': 0,
            'first_date': '2099-12-01',
            'email': None, 'modality': 'presencial', 'notes': None,
        }],
        'duplicate': [{'name': 'Ignorado', 'phone': '+5499999999999'}],
        'overlap':   [{'name': 'Ignorado2', 'phone': '+5498888888888'}],
        'error':     [{'name': 'Ignorado3', 'phone': 'invalido'}],
    }

    add_client_calls   = []
    create_event_calls = []
    create_apt_calls   = []

    def mock_add_client(**kwargs):
        add_client_calls.append(kwargs['phone'])

    def mock_create_event(**kwargs):
        create_event_calls.append(kwargs['client_phone'])
        return {'id': 'evt_test_123'}

    def mock_create_apt(**kwargs):
        create_apt_calls.append(kwargs['client_phone'])
        return 1

    with patch('src.database.database.db.add_client',
               side_effect=mock_add_client), \
         patch(
             'src.integrations.google_calendar_service.GoogleCalendarService'
             '.create_recurring_appointment',
             side_effect=mock_create_event
         ), \
         patch('src.database.database.db.create_appointment',
               side_effect=mock_create_apt):

        stats = svc.execute(
            analysis           = analysis,
            professional_phone = PROF_PHONE,
            calendar_id        = 'cal_test@gmail.com',
        )

    assert stats['creados'] == 1, f"Esperado 1 creado, obtenido {stats}"
    assert stats['errores'] == 0
    assert len(create_event_calls) == 1
    assert create_event_calls[0] == '+5491111111111'
    ok("execute() solo procesa ready, ignora duplicate/overlap/error")


def test_execute_vacio_no_llama_calendar():
    """execute() con ready vacío no llama a Google Calendar."""
    svc      = _make_service()
    analysis = {'ready': [], 'duplicate': [], 'overlap': [], 'error': []}

    with patch(
        'src.integrations.google_calendar_service.GoogleCalendarService'
        '.create_recurring_appointment'
    ) as mock_cal:
        stats = svc.execute(
            analysis           = analysis,
            professional_phone = PROF_PHONE,
            calendar_id        = 'cal_test@gmail.com',
        )

    mock_cal.assert_not_called()
    assert stats['creados'] == 0
    ok("execute() con ready vacío no llama a Calendar")


# ── Tests Bloque E: handlers ──────────────────────────────────────────────────

def test_handler_review_opcion_0_cancela():
    """Opción 0 en REVIEW limpia sesión y vuelve al menú principal."""
    from src.bot.professional_handler import ProfessionalHandler

    handler  = ProfessionalHandler()
    session  = _make_session()
    analysis = {'ready': [], 'duplicate': [], 'overlap': [], 'error': []}
    session.set_temp('agenda_analysis', analysis)
    session.transition_to(ConversationState.PROF_AGENDA_IMPORT_REVIEW)

    with patch(
        'src.messages.messages_professional.professional_messages.PROF_MAIN_MENU',
        'MENU_PRINCIPAL'
    ):
        resp = handler.handle_prof_agenda_import_review(session, '0')

    assert session.state == ConversationState.PROF_MAIN_MENU
    assert session.get_temp('agenda_analysis') is None
    ok("Opción 0 en REVIEW → cancela, limpia sesión, vuelve al menú")


def test_handler_review_opcion_2_muestra_detalle():
    """Opción 2 en REVIEW transiciona a DETAIL y muestra los listos."""
    from src.bot.professional_handler import ProfessionalHandler

    handler  = ProfessionalHandler()
    session  = _make_session()
    analysis = {
        'ready': [
            {'name': 'Juan', 'phone': '+5491111111111',
             'weekday': 'lunes', 'start_time': '09:00'},
        ],
        'duplicate': [], 'overlap': [], 'error': [],
    }
    session.set_temp('agenda_analysis', analysis)
    session.transition_to(ConversationState.PROF_AGENDA_IMPORT_REVIEW)

    resp = handler.handle_prof_agenda_import_review(session, '2')

    assert session.state == ConversationState.PROF_AGENDA_IMPORT_DETAIL
    assert 'Juan' in resp
    ok("Opción 2 en REVIEW → DETAIL con lista de listos")


def test_handler_detail_cualquier_mensaje_vuelve_a_review():
    """Cualquier mensaje en DETAIL vuelve al menú de revisión."""
    from src.bot.professional_handler import ProfessionalHandler

    handler  = ProfessionalHandler()
    session  = _make_session()
    analysis = {'ready': [], 'duplicate': [], 'overlap': [], 'error': []}
    session.set_temp('agenda_analysis', analysis)
    session.transition_to(ConversationState.PROF_AGENDA_IMPORT_DETAIL)

    resp = handler.handle_prof_agenda_import_detail(session, 'hola')

    assert session.state == ConversationState.PROF_AGENDA_IMPORT_REVIEW
    ok("Cualquier mensaje en DETAIL vuelve a REVIEW")


def test_handler_review_sin_analisis_vuelve_al_menu():
    """Si no hay análisis en sesión, REVIEW vuelve al menú principal."""
    from src.bot.professional_handler import ProfessionalHandler

    handler = ProfessionalHandler()
    session = _make_session()
    # No hay agenda_analysis en sesión
    session.transition_to(ConversationState.PROF_AGENDA_IMPORT_REVIEW)

    with patch(
        'src.messages.messages_professional.professional_messages.PROF_MAIN_MENU',
        'MENU_PRINCIPAL'
    ):
        resp = handler.handle_prof_agenda_import_review(session, '1')

    assert session.state == ConversationState.PROF_MAIN_MENU
    ok("REVIEW sin análisis en sesión → vuelve al menú principal")


# ── Tests Bloque F: format_execute_result() ───────────────────────────────────

def test_format_result_exitoso():
    svc = _make_service()
    msg = svc.format_execute_result({'creados': 5, 'errores': 0, 'detalles': []})
    assert '5' in msg and ('exitosamente' in msg.lower() or '✅' in msg)
    ok("format_execute_result() mensaje exitoso")

def test_format_result_con_errores():
    svc = _make_service()
    msg = svc.format_execute_result({
        'creados': 3, 'errores': 2,
        'detalles': ['Juan — error Calendar', 'María — error Calendar']
    })
    assert '3' in msg and '2' in msg
    ok("format_execute_result() mensaje con errores parciales")

def test_format_result_todo_fallido():
    svc = _make_service()
    msg = svc.format_execute_result({'creados': 0, 'errores': 3, 'detalles': []})
    assert '❌' in msg or 'ningún' in msg.lower()
    ok("format_execute_result() mensaje cuando todo falla")


# ── Runner ────────────────────────────────────────────────────────────────────

def run_all():
    sep()
    print(f"{C.BOLD}  TEST GAP 4 — Flujo de análisis y confirmación{C.END}")
    sep()

    tests = [
        # Bloque A — analyze()
        test_analyze_clasifica_ready,
        test_analyze_clasifica_errors,
        test_analyze_clasifica_overlap,
        test_analyze_clasifica_duplicate,
        test_analyze_tiene_timestamp,
        # Bloque B — format_review_menu()
        test_format_review_menu_con_ready,
        test_format_review_menu_sin_ready,
        # Bloque C — format_detail()
        test_format_detail_ready,
        test_format_detail_vacio,
        test_format_detail_overlap_muestra_conflicto,
        # Bloque D — execute()
        test_execute_solo_carga_ready,
        test_execute_vacio_no_llama_calendar,
        # Bloque E — handlers
        test_handler_review_opcion_0_cancela,
        test_handler_review_opcion_2_muestra_detalle,
        test_handler_detail_cualquier_mensaje_vuelve_a_review,
        test_handler_review_sin_analisis_vuelve_al_menu,
        # Bloque F — format_execute_result()
        test_format_result_exitoso,
        test_format_result_con_errores,
        test_format_result_todo_fallido,
    ]

    passed = failed = 0
    for t in tests:
        print(f"\n{C.CYAN}► {t.__name__}{C.END}")
        try:
            t()
            passed += 1
        except AssertionError as e:
            fail(str(e)); failed += 1
        except Exception as e:
            fail(f"Error inesperado: {e}")
            import traceback; traceback.print_exc()
            failed += 1

    sep()
    if failed == 0:
        print(f"{C.GREEN}{C.BOLD}  ✅ TODOS LOS TESTS PASARON ({passed}/{len(tests)}){C.END}")
    else:
        print(f"{C.RED}{C.BOLD}  ❌ {failed} FALLARON ({passed}/{len(tests)} pasaron){C.END}")
    sep()
    return failed == 0

def test_gap4_agenda_flow():
    assert run_all()

if __name__ == "__main__":
    sys.exit(0 if run_all() else 1)
