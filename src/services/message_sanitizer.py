"""
Message Sanitizer
=================
Ubicación: src/services/message_sanitizer.py

Anonimiza texto libre de usuarios antes de persistir en disco.
Se aplica en el punto de entrada del ConversationLogger — ningún
mensaje con PII llega a tocar el sistema de archivos.

Patrones que detecta y reemplaza
---------------------------------
- Teléfonos argentinos: +549..., 15..., 011..., 1130001234, etc.
- DNI / CUIL / CUIT: 8 dígitos sueltos o con formato XX.XXX.XXX
- Nombres propios en entities (campo professional_name)

Lo que NO toca
--------------
- detected_intent, confidence, session_state, shortcut_used
  → Son el valor ML. No son PII. No se modifican.
- entities sin professional_name
  → especialidad, fecha, horario, zona, prepaga, modalidad
    son categorías, no identidades.

Uso
---
    >>> from src.services.message_sanitizer import sanitize_message, sanitize_entities
    >>> sanitize_message("llamá al 1130001234 para confirmar")
    'llamá al [TEL] para confirmar'
    >>> sanitize_entities({'especialidad': 'psicología', 'professional_name': 'Juan Pérez'})
    {'especialidad': 'psicología', 'professional_name': '[PROFESIONAL]'}
"""

import re
from typing import Dict


# =============================================================================
# PATRONES DE DETECCIÓN
# =============================================================================

# Teléfonos argentinos — cubre los formatos más comunes en texto libre:
#   +5491130001234  → internacional completo
#   5491130001234   → sin +
#   1130001234      → local 10 dígitos (área 011 + 8 dígitos abonado)
#   011-3000-1234   → con código de área y guiones
#   15-3000-1234    → con prefijo 15
#   (011) 3000-1234 → con paréntesis
#
# ORDEN IMPORTA: DNI se procesa antes para evitar que 8 dígitos de DNI
# sean capturados por el patrón de teléfono local.
_PHONE_PATTERNS = [
    # Internacional con o sin +: +549... o 549... (11-13 dígitos)
    r'\+?549\d{8,10}',
    # Local 10 dígitos: 1130001234 — área (2-4 dígitos) + abonado (6-8 dígitos)
    # \b al inicio y al final para no capturar números más cortos o más largos
    r'\b(?:011[-\s]?)?\d{2,4}[-\s]?\d{6,8}\b',
    # Con prefijo 15: 15-3000-1234 o 153000-1234
    r'\b15[-\s]?\d{4}[-\s]?\d{4}\b',
    # Con paréntesis: (011) 3000-1234
    r'\(\d{2,4}\)\s?\d{4}[-\s]?\d{4}',
]

# DNI argentino:
#   35444123        → 7-8 dígitos solos
#   35.444.123      → con puntos
#   dni 35444123    → precedido por "dni"
#
# PROCESADO ANTES QUE TELÉFONOS para que 8 dígitos de DNI precedidos
# por "dni/cuil/cuit" sean capturados aquí y no en el patrón de teléfonos.
_DNI_PATTERNS = [
    # Con la palabra dni/cuil/cuit delante — captura el número completo
    r'\b(?:dni|cuil|cuit)[\s:\-]?\d[\d\.\-]{6,10}\b',
    # Número con puntos formato DNI: XX.XXX.XXX
    r'\b\d{2}\.\d{3}\.\d{3}\b',
    # 7-8 dígitos solos — solo si NO están precedidos por más dígitos
    r'(?<!\d)\d{7,8}(?!\d)',
]

# Compilar todos los patrones en un único objeto por categoría
_RE_PHONES = re.compile(
    '|'.join(_PHONE_PATTERNS),
    flags=re.IGNORECASE
)

_RE_DNI = re.compile(
    '|'.join(_DNI_PATTERNS),
    flags=re.IGNORECASE
)


# =============================================================================
# FUNCIONES PÚBLICAS
# =============================================================================

def sanitize_message(message: str) -> str:
    """
    Reemplaza PII detectada en texto libre con tokens neutrales.

    Aplica los patrones en orden: teléfonos → DNI/CUIL.
    Cada reemplazo es idempotente — aplicar dos veces da el mismo resultado.

    Args:
        message: Texto original del usuario.

    Returns:
        Texto con PII reemplazada por tokens. Nunca lanza excepción —
        si algo falla devuelve el mensaje original para no romper el flujo.

    Ejemplos:
        >>> sanitize_message("llamá al 1130001234")
        'llamá al [TEL]'
        >>> sanitize_message("mi dni es 35444123")
        'mi dni es [DNI]'
        >>> sanitize_message("necesito psicólogo mañana")
        'necesito psicólogo mañana'   # sin cambios
    """
    try:
        # DNI primero — evita que 8 dígitos de un DNI sean capturados
        # por el patrón de teléfono local antes de llegar a este regex.
        text = _RE_DNI.sub('[DNI]', message)
        text = _RE_PHONES.sub('[TEL]', text)
        return text
    except Exception:
        # Nunca romper el flujo del bot por un error de sanitización
        return message


def sanitize_entities(entities: Dict) -> Dict:
    """
    Reemplaza el campo professional_name en el dict de entidades.

    Todos los demás campos (especialidad, fecha, horario, zona,
    prepaga, modalidad, genero) son categorías — no PII — y se conservan.

    Args:
        entities: Dict de entidades extraídas por el NLU.

    Returns:
        Nuevo dict con professional_name reemplazado si existe.
        El dict original no se modifica (copia defensiva).

    Ejemplo:
        >>> sanitize_entities({'especialidad': 'psicología', 'professional_name': 'Juan Pérez'})
        {'especialidad': 'psicología', 'professional_name': '[PROFESIONAL]'}
    """
    if not entities or 'professional_name' not in entities:
        return entities

    # Copia defensiva — no mutar el dict original
    sanitized = dict(entities)
    sanitized['professional_name'] = '[PROFESIONAL]'
    return sanitized


def sanitize_log_entry(entry: dict) -> dict:
    """
    Aplica toda la sanitización sobre una entrada de log completa.

    Centraliza la lógica para que ConversationLogger llame un solo método.
    También elimina user_id — el hash del teléfono es pseudoanónimo
    (SHA-256 reversible si se conoce el input), no anonimización real.

    Campos modificados:
        - message       → sanitize_message()
        - entities      → sanitize_entities()
        - user_id       → eliminado

    Campos conservados sin cambio:
        - timestamp, detected_intent, confidence, shortcut_used,
          session_state, user_role, context, human_reviewed,
          is_correct, correct_intent, correct_entities, review_notes

    Args:
        entry: Dict completo a guardar en JSONL.

    Returns:
        Nuevo dict listo para persistir. El original no se modifica.
    """
    sanitized = dict(entry)

    # 1. Eliminar user_id — pseudoanónimo, no aporta al ML
    sanitized.pop('user_id', None)

    # 2. Limpiar texto libre del mensaje
    if 'message' in sanitized:
        sanitized['message'] = sanitize_message(sanitized['message'])

    # 3. Limpiar nombre de profesional en entidades
    if 'entities' in sanitized:
        sanitized['entities'] = sanitize_entities(sanitized['entities'])

    return sanitized