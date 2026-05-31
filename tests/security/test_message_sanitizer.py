"""
Tests — Message Sanitizer + Conversation Logger v2.0
=====================================================
Ubicación: tests/test_message_sanitizer.py

Cubre:
- Detección y reemplazo de cada patrón PII en texto libre
- Casos borde: mensaje vacío, sin PII, PII múltiple
- sanitize_entities: professional_name y campos que NO deben tocarse
- sanitize_log_entry: eliminación de user_id, inmutabilidad del original
- Integración: lo que llega al disco desde conversation_logger

Correr:
    pytest tests/test_message_sanitizer.py -v
"""

import json
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch

from src.services.message_sanitizer import (
    sanitize_message,
    sanitize_entities,
    sanitize_log_entry,
)
from src.services.conversation_logger import ConversationLogger


# =============================================================================
# sanitize_message — teléfonos
# =============================================================================

class TestSanitizeMessagePhones:

    def test_telefono_internacional_con_plus(self):
        assert sanitize_message("+5491130001234") == "[TEL]"

    def test_telefono_internacional_sin_plus(self):
        assert sanitize_message("5491130001234") == "[TEL]"

    def test_telefono_en_oracion(self):
        result = sanitize_message("llamá al 1130001234 para confirmar")
        assert "[TEL]" in result
        assert "1130001234" not in result

    def test_telefono_con_guiones(self):
        result = sanitize_message("mi número es 1130-001234")
        assert "1130001234" not in result

    def test_telefono_con_prefijo_15(self):
        result = sanitize_message("llamame al 15-3000-1234")
        assert "3000" not in result or "[TEL]" in result

    def test_telefono_con_parentesis(self):
        result = sanitize_message("(011) 3000-1234 es mi fijo")
        assert "3000-1234" not in result


# =============================================================================
# sanitize_message — DNI / CUIL
# =============================================================================

class TestSanitizeMessageDNI:

    def test_dni_precedido_por_palabra(self):
        result = sanitize_message("mi dni es 35444123")
        assert "35444123" not in result
        assert "[DNI]" in result

    def test_cuil_con_formato(self):
        result = sanitize_message("cuil 20-35444123-9")
        assert "35444123" not in result

    def test_dni_con_puntos(self):
        result = sanitize_message("DNI: 35.444.123")
        assert "35.444.123" not in result

    def test_numero_de_7_digitos(self):
        # DNI viejo de 7 dígitos
        result = sanitize_message("dni 3544412")
        assert "3544412" not in result


# =============================================================================
# sanitize_message — casos que NO deben modificarse
# =============================================================================

class TestSanitizeMessagePreservation:

    def test_mensaje_sin_pii(self):
        msg = "necesito psicólogo mañana por la tarde"
        assert sanitize_message(msg) == msg

    def test_mensaje_vacio(self):
        assert sanitize_message("") == ""

    def test_numero_de_4_digitos_no_es_dni(self):
        # "turno 3" o "opción 1234" no deben tocarse
        msg = "quiero turno para el 1234"
        result = sanitize_message(msg)
        assert "1234" in result

    def test_anio_no_es_dni(self):
        msg = "turno en 2026"
        assert sanitize_message(msg) == msg

    def test_idempotente(self):
        # Aplicar dos veces da el mismo resultado
        msg = "llamá al +5491130001234"
        once = sanitize_message(msg)
        twice = sanitize_message(once)
        assert once == twice


# =============================================================================
# sanitize_entities
# =============================================================================

class TestSanitizeEntities:

    def test_professional_name_reemplazado(self):
        entities = {'especialidad': 'psicología', 'professional_name': 'Juan Pérez'}
        result = sanitize_entities(entities)
        assert result['professional_name'] == '[PROFESIONAL]'
        assert result['especialidad'] == 'psicología'

    def test_sin_professional_name_no_cambia(self):
        entities = {'especialidad': 'nutrición', 'fecha': 'mañana'}
        result = sanitize_entities(entities)
        assert result == entities

    def test_original_no_mutado(self):
        entities = {'professional_name': 'María González'}
        sanitize_entities(entities)
        assert entities['professional_name'] == 'María González'  # original intacto

    def test_entities_vacio(self):
        assert sanitize_entities({}) == {}

    def test_entities_none(self):
        assert sanitize_entities(None) is None

    def test_campos_ml_preservados(self):
        """Los campos que usa el ML no deben tocarse."""
        entities = {
            'especialidad': 'kinesiología',
            'fecha': 'mañana',
            'horario': 'tarde',
            'zona': 'norte',
            'prepaga': True,
            'modalidad': 'presencial',
            'genero': 'femenino',
        }
        result = sanitize_entities(entities)
        assert result == entities


# =============================================================================
# sanitize_log_entry
# =============================================================================

class TestSanitizeLogEntry:

    def _make_entry(self, message="hola", phone_hash="abc123", professional_name=None):
        entities = {'especialidad': 'psicología'}
        if professional_name:
            entities['professional_name'] = professional_name
        return {
            'timestamp': '2026-01-01T10:00:00',
            'user_id': phone_hash,
            'message': message,
            'detected_intent': 'search_professional',
            'entities': entities,
            'confidence': 0.9,
            'shortcut_used': False,
            'session_state': 'CLIENT_MAIN_MENU',
        }

    def test_user_id_eliminado(self):
        entry = self._make_entry()
        result = sanitize_log_entry(entry)
        assert 'user_id' not in result

    def test_user_id_ausente_no_falla(self):
        entry = self._make_entry()
        del entry['user_id']
        result = sanitize_log_entry(entry)  # no debe lanzar excepción
        assert 'user_id' not in result

    def test_message_sanitizado(self):
        entry = self._make_entry(message="llamá al +5491130001234")
        result = sanitize_log_entry(entry)
        assert "+5491130001234" not in result['message']
        assert "[TEL]" in result['message']

    def test_professional_name_sanitizado(self):
        entry = self._make_entry(professional_name="Carlos López")
        result = sanitize_log_entry(entry)
        assert result['entities']['professional_name'] == '[PROFESIONAL]'

    def test_original_no_mutado(self):
        entry = self._make_entry(message="mi dni es 35444123")
        original_msg = entry['message']
        sanitize_log_entry(entry)
        assert entry['message'] == original_msg  # el original no cambia

    def test_campos_ml_preservados(self):
        entry = self._make_entry()
        result = sanitize_log_entry(entry)
        assert result['detected_intent'] == 'search_professional'
        assert result['confidence'] == 0.9
        assert result['session_state'] == 'CLIENT_MAIN_MENU'


# =============================================================================
# Integración — lo que realmente llega al disco
# =============================================================================

class TestConversationLoggerIntegration:
    """
    Verifica que ConversationLogger v2.0 nunca persiste PII.
    Usa un directorio temporal — no toca /app/data/conversations/.
    """

    def _make_logger(self, tmp_path):
        return ConversationLogger(data_dir=str(tmp_path))

    def test_user_id_no_en_disco(self, tmp_path):
        logger = self._make_logger(tmp_path)
        logger.log_message(
            phone="+5491130001234",
            message="hola",
            detected_intent="greeting",
            detected_entities={},
            confidence=0.95,
            shortcut_used=False,
            session_state="CLIENT_MAIN_MENU",
        )
        entry = self._read_last_entry(tmp_path)
        assert 'user_id' not in entry

    def test_telefono_en_mensaje_reemplazado(self, tmp_path):
        logger = self._make_logger(tmp_path)
        logger.log_message(
            phone="+5491130001234",
            message="llamame al 1130001234",
            detected_intent="greeting",
            detected_entities={},
            confidence=0.8,
            shortcut_used=False,
            session_state="CLIENT_MAIN_MENU",
        )
        entry = self._read_last_entry(tmp_path)
        assert "1130001234" not in entry['message']
        assert "[TEL]" in entry['message']

    def test_professional_name_reemplazado_en_disco(self, tmp_path):
        logger = self._make_logger(tmp_path)
        logger.log_message(
            phone="+5491130001234",
            message="quiero turno con la dra García",
            detected_intent="search_professional",
            detected_entities={'professional_name': 'García'},
            confidence=0.85,
            shortcut_used=False,
            session_state="CLIENT_MAIN_MENU",
        )
        entry = self._read_last_entry(tmp_path)
        assert entry['entities']['professional_name'] == '[PROFESIONAL]'

    def test_mensaje_sin_pii_no_cambia(self, tmp_path):
        logger = self._make_logger(tmp_path)
        msg = "necesito psicólogo mañana por la tarde"
        logger.log_message(
            phone="+5491130001234",
            message=msg,
            detected_intent="search_professional",
            detected_entities={'especialidad': 'psicología', 'fecha': 'mañana'},
            confidence=0.9,
            shortcut_used=True,
            session_state="CLIENT_MAIN_MENU",
        )
        entry = self._read_last_entry(tmp_path)
        assert entry['message'] == msg

    def test_intent_y_confidence_preservados(self, tmp_path):
        logger = self._make_logger(tmp_path)
        logger.log_message(
            phone="+5491130001234",
            message="cancelar turno",
            detected_intent="cancel_appointment",
            detected_entities={},
            confidence=0.93,
            shortcut_used=False,
            session_state="CLIENT_MAIN_MENU",
        )
        entry = self._read_last_entry(tmp_path)
        assert entry['detected_intent'] == "cancel_appointment"
        assert entry['confidence'] == 0.93

    # ── helpers ───────────────────────────────────────────────────────────────

    def _read_last_entry(self, tmp_path: Path) -> dict:
        files = list(tmp_path.glob("conversations_*.jsonl"))
        assert files, "No se creó ningún archivo JSONL"
        with open(files[0], encoding='utf-8') as f:
            lines = [l for l in f if l.strip()]
        assert lines, "El archivo JSONL está vacío"
        return json.loads(lines[-1])
