"""
Conversation Logger v2.0
========================
Ubicación: src/services/conversation_logger.py

Sistema automático de recolección de conversaciones para futuro entrenamiento ML.

Cambios respecto a v1.0
------------------------
- Sanitización en punto de entrada (via message_sanitizer).
  Ningún mensaje con PII toca el disco.
- user_id eliminado del log. El hash SHA-256 del teléfono es
  pseudoanónimo (reversible si se conoce el input) — no cumple
  anonimización real bajo Ley 25.326. El campo ya no se persiste.
- _anonymize_phone() conservada internamente pero no se escribe en el log.

Lo que se guarda en disco
--------------------------
  timestamp       — hora del mensaje (sin identidad asociada)
  message         — texto libre del usuario con PII reemplazada
  detected_intent — valor ML principal
  entities        — categorías extraídas (sin nombres propios)
  confidence      — confianza del NLU
  shortcut_used   — si saltó el menú
  session_state   — estado de la conversación
  user_role       — client / professional / null
  context         — datos adicionales de sesión

Lo que NO se guarda
--------------------
  user_id         — eliminado (era hash del teléfono)
  teléfonos en texto → reemplazados por [TEL]
  DNI/CUIL en texto  → reemplazados por [DNI]
  professional_name  → reemplazado por [PROFESIONAL]

Uso
---
    >>> from src.services.conversation_logger import conversation_logger
    >>> conversation_logger.log_message(
    ...     phone="+5491112345678",
    ...     message="necesito psicólogo mañana",
    ...     detected_intent="search_professional",
    ...     detected_entities={'especialidad': 'psicología', 'fecha': 'mañana'},
    ...     confidence=0.9,
    ...     shortcut_used=True,
    ...     session_state="CLIENT_MAIN_MENU"
    ... )
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from src.services.message_sanitizer import sanitize_log_entry


class ConversationLogger:
    """
    Logger automático de conversaciones para dataset de ML.

    Guarda cada mensaje procesado en archivos diarios JSONL.
    Toda la PII es eliminada o reemplazada antes de tocar el disco.
    """

    def __init__(self, data_dir: str = "data/conversations"):
        """
        Inicializar logger.

        Args:
            data_dir: Directorio donde guardar los logs.
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._create_readme_if_not_exists()

    # =========================================================================
    # API PÚBLICA — sin cambios de firma respecto a v1.0
    # =========================================================================

    def log_message(
        self,
        phone: str,
        message: str,
        detected_intent: str,
        detected_entities: Dict,
        confidence: float,
        shortcut_used: bool,
        session_state: str,
        user_role: Optional[str] = None,
        context_data: Optional[Dict] = None
    ):
        """
        Registra un mensaje procesado.

        La firma es idéntica a v1.0 — ningún caller necesita cambios.
        La sanitización ocurre internamente antes de _save_to_file().

        Args:
            phone:              Número de teléfono. Solo se usa para logs
                                de debug enmascarados — NO se persiste.
            message:            Texto original. Se sanitiza antes de guardar.
            detected_intent:    Intent detectado por el sistema.
            detected_entities:  Entidades extraídas. professional_name se reemplaza.
            confidence:         Nivel de confianza (0.0-1.0).
            shortcut_used:      Si se hizo shortcut (omitió menú).
            session_state:      Estado de la conversación.
            user_role:          Rol del usuario (client/professional).
            context_data:       Datos adicionales de contexto.
        """
        # Construir entrada — todavía con datos crudos
        raw_entry = {
            'timestamp':        datetime.now().isoformat(),
            'user_id':          self._anonymize_phone(phone),  # se eliminará en sanitize
            'message':          message,
            'detected_intent':  detected_intent,
            'entities':         detected_entities,
            'confidence':       round(confidence, 3),
            'shortcut_used':    shortcut_used,
            'session_state':    session_state,
            'user_role':        user_role,
            'context':          context_data or {},

            # Campos para revisión manual
            'human_reviewed':   False,
            'is_correct':       None,
            'correct_intent':   None,
            'correct_entities': None,
            'review_notes':     None,
        }

        # Sanitizar ANTES de persistir
        # - Elimina user_id
        # - Reemplaza teléfonos/DNI en message
        # - Reemplaza professional_name en entities
        clean_entry = sanitize_log_entry(raw_entry)

        self._save_to_file(clean_entry)

        # Debug: teléfono enmascarado, nunca completo
        masked = self._mask_phone_for_log(phone)
        print(
            f"[CONV_LOG] {masked} | intent={detected_intent} "
            f"conf={confidence:.2f} entities={list(detected_entities.keys())}"
        )

    def mark_for_review(
        self,
        phone: str,
        message: str,
        detected_intent: str,
        user_says_wrong: bool = False,
        priority: str = "normal"
    ):
        """
        Marca un mensaje para revisión manual prioritaria.

        Útil cuando:
        - El usuario dice que la respuesta fue incorrecta.
        - La confianza es muy baja.
        - Comportamiento inesperado del NLU.

        Args:
            phone:           Número de teléfono. No se persiste.
            message:         Mensaje original. Se sanitiza antes de guardar.
            detected_intent: Intent detectado.
            user_says_wrong: Si el usuario indicó que estuvo mal.
            priority:        'high', 'normal', 'low'.
        """
        raw_entry = {
            'timestamp':      datetime.now().isoformat(),
            'user_id':        self._anonymize_phone(phone),  # se eliminará
            'message':        message,
            'detected_intent': detected_intent,
            'user_feedback':  'wrong' if user_says_wrong else 'needs_review',
            'priority':       priority,
            'reviewed':       False,
        }

        clean_entry = sanitize_log_entry(raw_entry)

        review_file = self.data_dir / "needs_review.jsonl"
        with open(review_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(clean_entry, ensure_ascii=False) + '\n')

        print(f"[CONV_LOG] ⚠️ Marcado para revisión: {message[:50]}...")

    def get_stats(self) -> Dict:
        """
        Obtiene estadísticas de los datos recopilados.

        Returns:
            {
                'total_messages': int,
                'by_intent':      dict,
                'avg_confidence': float,
                'needs_review':   int,
            }
        """
        stats = {
            'total_messages': 0,
            'by_intent':      {},
            'total_confidence': 0.0,
            'needs_review':   0,
        }

        for file in self.data_dir.glob("conversations_*.jsonl"):
            with open(file, encoding='utf-8') as f:
                for line in f:
                    entry = json.loads(line)
                    stats['total_messages'] += 1

                    intent = entry['detected_intent']
                    stats['by_intent'][intent] = stats['by_intent'].get(intent, 0) + 1
                    stats['total_confidence'] += entry['confidence']

        if stats['total_messages'] > 0:
            stats['avg_confidence'] = (
                stats['total_confidence'] / stats['total_messages']
            )

        review_file = self.data_dir / "needs_review.jsonl"
        if review_file.exists():
            with open(review_file, encoding='utf-8') as f:
                for line in f:
                    entry = json.loads(line)
                    if not entry.get('reviewed', False):
                        stats['needs_review'] += 1

        return stats

    # =========================================================================
    # INTERNOS
    # =========================================================================

    def _save_to_file(self, log_entry: Dict):
        """
        Persiste una entrada ya sanitizada en el archivo diario JSONL.

        Args:
            log_entry: Dict limpio, sin PII. Solo se llama desde log_message()
                       y mark_for_review(), nunca con datos crudos.
        """
        date_str = datetime.now().strftime('%Y-%m-%d')
        filepath = self.data_dir / f"conversations_{date_str}.jsonl"

        with open(filepath, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

    def _anonymize_phone(self, phone: str) -> str:
        """
        Hash SHA-256 del teléfono.

        Se conserva para uso interno (mark_for_review lo pasaba a user_id
        en v1.0). En v2.0 sanitize_log_entry elimina user_id antes de
        persistir, así que este valor nunca llega al disco.

        Args:
            phone: Número de teléfono original.

        Returns:
            Hash de 16 caracteres.
        """
        return hashlib.sha256(phone.encode()).hexdigest()[:16]

    def _mask_phone_for_log(self, phone: str) -> str:
        """
        Enmascara teléfono para mensajes de debug en consola.
        Nunca se persiste — solo para print().

        Ejemplo: +5491130001234 → +549****1234

        Args:
            phone: Número original.

        Returns:
            Versión enmascarada.
        """
        if len(phone) > 6:
            return phone[:4] + '****' + phone[-4:]
        return '****'

    def _create_readme_if_not_exists(self):
        """Crea archivo README en el directorio de datos."""
        readme_path = self.data_dir / "README.md"
        if readme_path.exists():
            return

        readme_content = """\
# Conversaciones Recopiladas

Datos recopilados automáticamente para entrenamiento ML del detector de intenciones.

## Privacidad (v2.0)

- ✅ user_id eliminado — no se persiste ningún identificador de usuario
- ✅ Teléfonos en texto reemplazados por [TEL]
- ✅ DNI/CUIL en texto reemplazados por [DNI]
- ✅ Nombres de profesionales en entidades reemplazados por [PROFESIONAL]
- ✅ Anonimización en punto de entrada — la PII nunca toca el disco
- ✅ Retención máxima: 60 días (script: scripts/privacy/cleanup_conversations.py)
Ver política completa: docs/PRIVACY.md
OBSOLETO (eliminar):

⚠️ Los mensajes de texto NO están encriptados (contienen lo que el usuario escribió)
→ Ya no aplica desde v2.0: el texto guardado es la versión sanitizada, no el original.

## Estructura de archivos

- `conversations_YYYY-MM-DD.jsonl` — mensajes del día (sin PII)
- `needs_review.jsonl`             — mensajes marcados para revisión manual
- `README.md`                      — este archivo

## Formato de cada entrada (JSONL)

```json
{
  "timestamp":        "2026-02-05T14:30:00",
  "message":          "necesito psicólogo mañana",
  "detected_intent":  "search_professional",
  "entities":         { "especialidad": "psicología", "fecha": "mañana" },
  "confidence":       0.9,
  "shortcut_used":    true,
  "session_state":    "CLIENT_MAIN_MENU",
  "user_role":        "client",
  "context":          {},
  "human_reviewed":   false,
  "is_correct":       null,
  "correct_intent":   null,
  "correct_entities": null,
  "review_notes":     null
}
```

## Comandos útiles

```bash
# Estadísticas
docker exec whatsapp-demo python scripts/review_conversations.py --stats

# Revisión manual
docker exec whatsapp-demo python scripts/review_conversations.py

# Limpieza + TTL 60 días
docker exec whatsapp-demo python scripts/privacy/cleanup_conversations.py
```
"""
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)


# =============================================================================
# INSTANCIA GLOBAL
# =============================================================================
conversation_logger = ConversationLogger()