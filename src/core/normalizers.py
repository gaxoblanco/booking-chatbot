"""
Normalizers — Centralización de respuestas de texto libre
==========================================================
Ubicación: src/core/normalizers.py

Propósito:
    Reemplaza las listas _SI/_NO/_ANY dispersas en client_handler.py,
    bot_controller.py y slot_offer_handler.py por funciones únicas
    y testeables.

Uso:
    from src.core.normalizers import normalize_yes_no, normalize_confirm

    # Normalizar sí/no binario
    result = normalize_yes_no("dale")     # → '1'
    result = normalize_yes_no("no gracias")  # → '2'
    result = normalize_yes_no("quizás")   # → None

    # Normalizar confirmación de selección única
    result = normalize_confirm("ese mismo")  # → True

Política de extensión:
    Cuando se detecte una variante nueva en producción que no esté cubierta,
    agregarla aquí — no en el handler donde se encontró.

Futura migración a ML (Opción C):
    Cuando haya suficientes datos reales, reemplazar las funciones por
    llamadas al intent_detector con intenciones 'confirm_action' / 'deny_action'.
    La interfaz pública (normalize_yes_no, etc.) no cambia — solo la
    implementación interna.
"""

import unicodedata
import re


# ── Helpers internos ──────────────────────────────────────────────────────────

def _clean(text: str) -> str:
    """
    Normaliza texto para comparación:
    - minúsculas
    - sin tildes
    - sin puntuación extra
    - strip
    """
    text = text.strip().lower()
    # Quitar tildes
    nfd = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')
    # Colapsar espacios
    text = re.sub(r'\s+', ' ', text)
    return text


# ── Sets de referencia ────────────────────────────────────────────────────────

# Afirmaciones — el usuario acepta, confirma o quiere seguir adelante
_AFIRMACIONES = {
    # Numérico
    '1',
    # Directo
    'si', 's', 'yes', 'yep', 'sip',
    # Coloquial AR
    'dale', 'va', 'va va', 'dale va', 'bueno', 'ta', 'ta bien',
    'listo', 'anda', 'anda bien', 'perfecto', 'claro', 'claro que si',
    'por supuesto', 'obvio', 'obvio que si',
    # Confirmación explícita
    'confirmo', 'confirmar', 'confirmado',
    'acepto', 'acepta', 'aceptar', 'aceptado',
    'adelante', 'proceder', 'procede',
    'quiero', 'quiero si', 'si quiero', 'si deseo',
    # Respuesta a oferta
    'me interesa', 'me sirve', 'me viene bien', 'lo tomo',
    # Inglés coloquial que se mezcla
    'ok', 'okay', 'okey',
}

# Negaciones — el usuario rechaza, cancela o quiere mantener
_NEGACIONES = {
    # Numérico
    '2',
    # Directo
    'no', 'n', 'nope', 'nop', 'nel', 'na',
    # Coloquial AR
    'ni', 'ni ahi', 'para nada', 'de ninguna manera',
    'mejor no', 'no gracias', 'gracias pero no',
    # Mantener estado actual
    'mantener', 'mantene', 'mantene asi', 'mantenerlo',
    'dejalo', 'dejalo asi', 'deja',
    'prefiero no', 'prefiero mantener', 'prefiero el mio',
    'no cambio', 'no me interesa',
    # Rechazo de oferta
    'no lo tomo', 'no me sirve', 'paso', 'paso gracias',
    # Negación explícita
    'cancelo', 'cancelar', 'no quiero', 'no deseo',
    'negativo',
}

# Indiferencia — para filtros opcionales (prepaga, zona, etc.)
_INDIFERENCIA = {
    'cualquiera', 'cualquier',
    'no importa', 'me da igual', 'da igual',
    'indiferente', 'indistinto',
    'no aplica', 'no tengo preferencia', 'sin preferencia',
    'ambos', 'cualquiera de los dos', 'lo que sea', 'lo que haya',
    'me es igual',
}

# Confirmación de selección única — "ese mismo", "esa cita", etc.
# Usado cuando hay un único resultado y el usuario lo confirma sin número
_CONFIRMAR_UNO = {
    'ese', 'esa', 'ese mismo', 'esa misma',
    'ese profesional', 'esa profesional',
    'esa cita', 'ese turno',
    'el mismo', 'la misma',
} | _AFIRMACIONES  # También acepta cualquier afirmación directa


# ── API pública ───────────────────────────────────────────────────────────────

def normalize_yes_no(message: str) -> str | None:
    """
    Normaliza texto libre a '1' (sí) o '2' (no).

    Retorna:
        '1'  si el mensaje expresa afirmación
        '2'  si el mensaje expresa negación
        None si no se reconoce (el handler debe pedir aclaración)

    Uso típico:
        normalizado = normalize_yes_no(message)
        if normalizado:
            message = normalizado
        else:
            return get_msg('INVALID_OPTION')
    """
    msg = _clean(message)

    if msg in _AFIRMACIONES:
        return '1'
    if msg in _NEGACIONES:
        return '2'

    # Matching parcial para frases más largas no cubiertas exactamente
    # Solo para afirmaciones/negaciones fuertes — evita falsos positivos
    for keyword in ('dale', 'confirmo', 'acepto', 'quiero si', 'si quiero'):
        if keyword in msg:
            return '1'
    for keyword in ('no gracias', 'para nada', 'mejor no', 'prefiero no', 'no quiero'):
        if keyword in msg:
            return '2'

    return None


def normalize_yes_no_any(message: str) -> str | None:
    """
    Normaliza texto libre a '1' (sí), '2' (no) o '3' (indiferente).

    Para filtros opcionales como prepaga o zona donde existe
    la opción "no importa".

    Retorna:
        '1'  afirmación
        '2'  negación
        '3'  indiferencia
        None si no se reconoce
    """
    msg = _clean(message)

    if msg in _INDIFERENCIA:
        return '3'

    # Primero indiferencia (parcial)
    for keyword in ('no importa', 'da igual', 'me da igual', 'cualquiera',
                    'indiferente', 'lo que sea'):
        if keyword in msg:
            return '3'

    return normalize_yes_no(message)


def normalize_confirm_single(message: str) -> bool:
    """
    Retorna True si el mensaje confirma una selección única.

    Usado cuando hay un solo resultado y el usuario puede confirmar
    con texto libre en lugar de escribir '1'.

    Ejemplo:
        if len(results) == 1 and normalize_confirm_single(message):
            message = '1'
    """
    msg = _clean(message)
    return msg in {_clean(k) for k in _CONFIRMAR_UNO}


def normalize_gender(message: str) -> str | None:
    """
    Normaliza preferencia de género del profesional.

    Retorna:
        'm'  masculino
        'f'  femenino
        'any' indiferente / sin preferencia
        None  si no se reconoce
    """
    msg = _clean(message)

    _MASC = {'masculino', 'hombre', 'varon', 'male', 'doctor',
             'prefiero hombre', 'quiero hombre', 'prefiero doctor'}
    _FEM  = {'femenino', 'mujer', 'female', 'doctora', 'medica',
             'prefiero mujer', 'quiero mujer', 'prefiero doctora'}

    if msg in _MASC or any(k in msg for k in _MASC):
        return 'm'
    if msg in _FEM or any(k in msg for k in _FEM):
        return 'f'
    if msg in _INDIFERENCIA or any(k in msg for k in _INDIFERENCIA):
        return 'any'
    return None