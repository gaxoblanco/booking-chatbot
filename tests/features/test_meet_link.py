#!/usr/bin/env python3
"""
test_meet_link.py
=================
Tests para la feature de Google Meet link en el flujo de booking.

Cubre:
  - Validador de configuración (config_validator)
  - MEET_LINK_MODE='never'  → conference_data_version=0, meet_link=None en BD
  - MEET_LINK_MODE='always' → conference_data_version=1, meet_link persistido
  - MEET_LINK_MODE inválido → ValueError al boot
  - MEET_LINK_MODE='virtual_only' sin ASK_MODALITY → ValueError al boot
  - Google no devuelve hangoutLink → meet_link=None, booking no rompe
  - Interpolación de {meet_line} en mensajes del tono freelance

Cómo correr:
    docker exec -it whatsapp-demo python tests/features/test_meet_link.py

No requiere credenciales reales de Google — el calendar service
se mockea en todos los tests de lógica de negocio.
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# ── Helpers de output ─────────────────────────────────────────────────────────

class C:
    GREEN  = '\033[92m'
    RED    = '\033[91m'
    CYAN   = '\033[96m'
    YELLOW = '\033[93m'
    BOLD   = '\033[1m'
    END    = '\033[0m'

def sep():
    print(f"\n{C.YELLOW}{'─' * 60}{C.END}")

def ok(msg):
    print(f"  {C.GREEN}✅ {msg}{C.END}")

def fail(msg):
    print(f"  {C.RED}❌ {msg}{C.END}")

def info(msg):
    print(f"  {C.CYAN}ℹ  {msg}{C.END}")


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_config_validator_never():
    """MEET_LINK_MODE='never' pasa la validación sin errores."""
    with patch('src.config.domain_config.DomainConfig.MEET_LINK_MODE', 'never'), \
         patch('src.config.filter_config.FeatureFlags.ASK_MODALITY', False):
        from src.config.config_validator import validate_config
        try:
            validate_config()
            ok("MEET_LINK_MODE='never' → validación OK")
        except Exception as e:
            raise AssertionError(f"No debería fallar con 'never': {e}")


def test_config_validator_always():
    """MEET_LINK_MODE='always' pasa la validación sin errores."""
    with patch('src.config.domain_config.DomainConfig.MEET_LINK_MODE', 'always'), \
         patch('src.config.filter_config.FeatureFlags.ASK_MODALITY', False):
        from src.config.config_validator import validate_config
        # Forzar recarga para que lea el mock
        import importlib, src.config.config_validator as cv
        importlib.reload(cv)
        try:
            cv.validate_config()
            ok("MEET_LINK_MODE='always' → validación OK")
        except Exception as e:
            raise AssertionError(f"No debería fallar con 'always': {e}")


def test_config_validator_invalid_mode():
    """MEET_LINK_MODE con valor desconocido lanza ValueError."""
    with patch('src.config.domain_config.DomainConfig.MEET_LINK_MODE', 'zoom_only'):
        import importlib, src.config.config_validator as cv
        importlib.reload(cv)
        try:
            cv.validate_config()
            raise AssertionError("Debería haber lanzado ValueError")
        except ValueError as e:
            assert 'zoom_only' in str(e), "El error debe mencionar el valor inválido"
            ok("MEET_LINK_MODE inválido → ValueError con mensaje claro")


def test_config_validator_virtual_only_blocked():
    """MEET_LINK_MODE='virtual_only' con ASK_MODALITY=False lanza ValueError."""
    with patch('src.config.domain_config.DomainConfig.MEET_LINK_MODE', 'virtual_only'), \
         patch('src.config.filter_config.FeatureFlags.ASK_MODALITY', False):
        import importlib, src.config.config_validator as cv
        importlib.reload(cv)
        try:
            cv.validate_config()
            raise AssertionError("Debería haber lanzado ValueError")
        except ValueError as e:
            assert 'virtual_only' in str(e), "El error debe mencionar virtual_only"
            assert 'ASK_MODALITY' in str(e), "El error debe mencionar ASK_MODALITY"
            ok("MEET_LINK_MODE='virtual_only' sin ASK_MODALITY → ValueError con guía de corrección")


def test_config_validator_virtual_only_allowed_when_flag_true():
    """MEET_LINK_MODE='virtual_only' con ASK_MODALITY=True pasa la validación."""
    with patch('src.config.domain_config.DomainConfig.MEET_LINK_MODE', 'virtual_only'), \
         patch('src.config.filter_config.FeatureFlags.ASK_MODALITY', True):
        import importlib, src.config.config_validator as cv
        importlib.reload(cv)
        try:
            cv.validate_config()
            ok("MEET_LINK_MODE='virtual_only' con ASK_MODALITY=True → validación OK (listo para futuro)")
        except ValueError as e:
            raise AssertionError(f"No debería fallar cuando ASK_MODALITY=True: {e}")


def test_appointment_service_never_mode():
    """
    Con MEET_LINK_MODE='never', appointment_service no pasa conference_data_version=1
    al calendar service y meet_link queda None en BD.
    """
    mock_calendar = MagicMock()
    # Google no devuelve hangoutLink porque no se pidió
    mock_calendar.create_appointment.return_value = {
        'id': 'google_event_abc',
        # sin 'hangoutLink'
    }

    mock_db = MagicMock()
    mock_db.get_professional.return_value = {
        'phone': '+5491100000001',
        'name': 'Dr. Test',
        'calendar_id': 'test@gmail.com'
    }
    mock_db.create_appointment.return_value = 42

    with patch('src.config.domain_config.DomainConfig.MEET_LINK_MODE', 'never'):
        from src.services.appointment_service import AppointmentCalendarService
        svc = AppointmentCalendarService.__new__(AppointmentCalendarService)
        svc.db = mock_db
        svc.calendar_service = mock_calendar

        svc.create_appointment(
            professional_phone='+5491100000001',
            client_phone='+5491199999999',
            client_name='Test Cliente',
            date='2026-08-01',
            start_time='10:00',
            end_time='11:00',
            appointment_type='Consulta',
        )

    # Verificar que se llamó con conference_data_version=0
    call_kwargs = mock_calendar.create_appointment.call_args
    version_used = call_kwargs.kwargs.get(
        'conference_data_version',
        call_kwargs.args[0] if call_kwargs.args else None
    )
    assert version_used == 0, (
        f"Con mode='never' se esperaba conference_data_version=0, "
        f"se usó: {version_used}"
    )

    # Verificar que meet_link=None fue a la BD
    db_call = mock_db.create_appointment.call_args
    meet_link_saved = db_call.kwargs.get('meet_link')
    assert meet_link_saved is None, (
        f"Con mode='never' meet_link debe ser None en BD, fue: {meet_link_saved}"
    )

    ok("MEET_LINK_MODE='never' → conference_data_version=0, meet_link=None en BD")


def test_appointment_service_always_mode():
    """
    Con MEET_LINK_MODE='always', appointment_service pasa conference_data_version=1
    y persiste el hangoutLink en BD.
    """
    mock_calendar = MagicMock()
    mock_calendar.create_appointment.return_value = {
        'id': 'google_event_xyz',
        'hangoutLink': 'https://meet.google.com/abc-defg-hij'
    }

    mock_db = MagicMock()
    mock_db.get_professional.return_value = {
        'phone': '+5491100000001',
        'name': 'Gastón Blanco',
        'calendar_id': 'gaston@gmail.com'
    }
    mock_db.create_appointment.return_value = 99

    with patch('src.config.domain_config.DomainConfig.MEET_LINK_MODE', 'always'):
        from src.services.appointment_service import AppointmentCalendarService
        svc = AppointmentCalendarService.__new__(AppointmentCalendarService)
        svc.db = mock_db
        svc.calendar_service = mock_calendar

        svc.create_appointment(
            professional_phone='+5491100000001',
            client_phone='+5491199999999',
            client_name='Test Cliente',
            date='2026-08-01',
            start_time='10:00',
            end_time='11:00',
            appointment_type='Consulta',
        )

    # Verificar conference_data_version=1
    call_kwargs = mock_calendar.create_appointment.call_args
    version_used = call_kwargs.kwargs.get('conference_data_version', None)
    assert version_used == 1, (
        f"Con mode='always' se esperaba conference_data_version=1, "
        f"se usó: {version_used}"
    )

    # Verificar que el link llegó a la BD
    db_call = mock_db.create_appointment.call_args
    meet_link_saved = db_call.kwargs.get('meet_link')
    assert meet_link_saved == 'https://meet.google.com/abc-defg-hij', (
        f"meet_link no se persistió correctamente: {meet_link_saved}"
    )

    ok("MEET_LINK_MODE='always' → conference_data_version=1, meet_link persistido en BD")


def test_google_no_returns_hangout_link():
    """
    Con MEET_LINK_MODE='always' pero Google no devuelve hangoutLink
    (ej: Service Account sin permisos de Meet), el booking no rompe
    y meet_link queda None.
    """
    mock_calendar = MagicMock()
    # Google crea el evento pero no incluye hangoutLink
    mock_calendar.create_appointment.return_value = {
        'id': 'google_event_nohangout',
        # sin 'hangoutLink' — puede pasar si la SA no tiene permisos de Meet
    }

    mock_db = MagicMock()
    mock_db.get_professional.return_value = {
        'phone': '+5491100000001',
        'name': 'Gastón Blanco',
        'calendar_id': 'gaston@gmail.com'
    }
    mock_db.create_appointment.return_value = 77

    with patch('src.config.domain_config.DomainConfig.MEET_LINK_MODE', 'always'):
        from src.services.appointment_service import AppointmentCalendarService
        svc = AppointmentCalendarService.__new__(AppointmentCalendarService)
        svc.db = mock_db
        svc.calendar_service = mock_calendar

        result = svc.create_appointment(
            professional_phone='+5491100000001',
            client_phone='+5491199999999',
            client_name='Test Cliente',
            date='2026-08-01',
            start_time='10:00',
            end_time='11:00',
            appointment_type='Consulta',
        )

    # El booking no debe fallar
    assert result == 77, "El booking debe completarse aunque no haya Meet link"

    # meet_link debe ser None, no lanzar KeyError
    db_call = mock_db.create_appointment.call_args
    meet_link_saved = db_call.kwargs.get('meet_link')
    assert meet_link_saved is None, (
        f"Sin hangoutLink, meet_link debe ser None, fue: {meet_link_saved}"
    )

    ok("Google sin hangoutLink → booking completo, meet_link=None sin errores")


def test_meet_line_interpolation_with_link():
    """
    Con meet_link presente, {meet_line} se interpola con el emoji y el link.
    El mensaje resultante no tiene llaves sin resolver.
    """
    # Importar las constantes del tono freelance directamente
    import importlib
    freelance = importlib.import_module('src.messages.tones.freelance')

    meet_link = 'https://meet.google.com/abc-defg-hij'
    meet_line = f"🎥 {meet_link}\n\n"

    result = freelance.CLIENT_BOOKING_SUCCESS.format(
        slot_name_upper='Reunión',
        slot_name_plural='reuniones',
        patient_line='',
        emoji_prof='💻',
        prof_name='Gastón Blanco',
        day='Jueves',
        date='10/07/2026',
        start='15:00',
        meet_line=meet_line,
    )

    assert 'meet.google.com' in result, "El link debe aparecer en el mensaje"
    assert '🎥' in result, "El emoji de Meet debe aparecer"
    assert '{' not in result, f"Quedaron llaves sin resolver: {result}"

    ok("meet_line con link → interpolación correcta en BOOKING_SUCCESS")
    info(f"Preview:\n{result}")


def test_meet_line_interpolation_without_link():
    """
    Sin meet_link, {meet_line} es string vacío y el mensaje queda limpio
    sin líneas vacías extra ni llaves sin resolver.
    """
    import importlib
    freelance = importlib.import_module('src.messages.tones.freelance')

    meet_line = ""  # sin link

    result = freelance.CLIENT_BOOKING_SUCCESS.format(
        slot_name_upper='Reunión',
        slot_name_plural='reuniones',
        patient_line='',
        emoji_prof='💻',
        prof_name='Gastón Blanco',
        day='Jueves',
        date='10/07/2026',
        start='15:00',
        meet_line=meet_line,
    )

    assert 'meet.google.com' not in result, "Sin link no debe aparecer la URL"
    assert '{' not in result, f"Quedaron llaves sin resolver: {result}"

    ok("meet_line vacío → mensaje limpio sin artefactos")


def test_appointment_detail_with_meet_link():
    """
    CLIENT_APPOINTMENT_DETAIL del tono freelance muestra el link
    cuando meet_line tiene contenido.
    """
    import importlib
    freelance = importlib.import_module('src.messages.tones.freelance')

    meet_line = "\n🎥 https://meet.google.com/abc-defg-hij"

    result = freelance.CLIENT_APPOINTMENT_DETAIL.format(
        id=1,
        professional_name='Gastón Blanco',
        date='Jueves 10 de Julio de 2026',
        time='15:00',
        professional_phone='+5491199999999',
        modality='💻 Virtual',
        duration=60,
        reason_display='',
        status_badge='Estado: 📅 *Agendada*',
        options='1️⃣ Reprogramar\n2️⃣ Cancelar\n0️⃣ Volver',
        meet_line=meet_line,
    )

    assert 'meet.google.com' in result, "El link debe aparecer en el detalle"
    assert '{' not in result, f"Quedaron llaves sin resolver: {result}"

    ok("CLIENT_APPOINTMENT_DETAIL con meet_line → link visible en detalle")


# ── Runner ─────────────────────────────────────────────────────────────────────

def run_all():
    sep()
    print(f"{C.BOLD}  TEST MEET LINK — Google Meet como servicio configurable{C.END}")
    sep()

    tests = [
        # Validador de config
        test_config_validator_never,
        test_config_validator_always,
        test_config_validator_invalid_mode,
        test_config_validator_virtual_only_blocked,
        test_config_validator_virtual_only_allowed_when_flag_true,
        # Lógica de negocio en appointment_service
        test_appointment_service_never_mode,
        test_appointment_service_always_mode,
        test_google_no_returns_hangout_link,
        # Interpolación de mensajes
        test_meet_line_interpolation_with_link,
        test_meet_line_interpolation_without_link,
        test_appointment_detail_with_meet_link,
    ]

    passed = failed = 0
    for t in tests:
        print(f"\n{C.CYAN}► {t.__name__}{C.END}")
        try:
            t()
            passed += 1
        except AssertionError as e:
            fail(str(e))
            failed += 1
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


def test_completo():
    assert run_all()


if __name__ == "__main__":
    sys.exit(0 if run_all() else 1)
