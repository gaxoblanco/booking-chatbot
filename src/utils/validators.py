"""
Input Validators
================
Validación y normalización de datos ingresados por el usuario.

Contexto: Argentina. Números siempre se normalizan a +549XXXXXXXXXX.
Flexible con formatos de entrada — el usuario no sabe de formatos.
"""

import re
from dataclasses import dataclass
from typing import Optional


# ==================================================
# RESULTADO DE VALIDACIÓN
# ==================================================

@dataclass
class ValidationResult:
    """Resultado de una validación."""
    valid: bool
    value: Optional[str]   # valor normalizado si válido, None si no
    error: Optional[str]   # mensaje de error para mostrar al usuario


# ==================================================
# NOMBRE
# ==================================================

# Caracteres permitidos en nombres: letras unicode, espacios, guiones, apostrofes
_NAME_PATTERN = re.compile(
    r"^[\w\s\-'\.]+$",
    re.UNICODE
)

# Palabras que indican que no es un nombre real
_NAME_BLACKLIST = re.compile(
    r"http|www\.|\.com|script|select|insert|drop|<|>|\d{4,}",
    re.IGNORECASE
)

NAME_MIN = 2
NAME_MAX = 60


def validate_name(raw: str) -> ValidationResult:
    """
    Valida un nombre de persona.

    Acepta: 'Juan', 'María José', 'O\'Brien', 'García-López'
    Rechaza: strings muy largos, URLs, código, números largos

    Returns:
        ValidationResult con nombre en Title Case si válido
    """
    value = raw.strip()

    # Longitud mínima
    if len(value) < NAME_MIN:
        return ValidationResult(
            valid=False,
            value=None,
            error=f"El nombre es muy corto. Ingresá el nombre completo."
        )

    # Longitud máxima — posible ataque o error
    if len(value) > NAME_MAX:
        return ValidationResult(
            valid=False,
            value=None,
            error=f"Ese nombre es demasiado largo ({len(value)} caracteres). "
                  f"Ingresá solo el nombre y apellido."
        )

    # Blacklist — URLs, SQL, código
    if _NAME_BLACKLIST.search(value):
        return ValidationResult(
            valid=False,
            value=None,
            error="Ese no parece un nombre válido. Ingresá el nombre completo."
        )

    # Solo letras, espacios y caracteres válidos en nombres
    if not _NAME_PATTERN.match(value):
        return ValidationResult(
            valid=False,
            value=None,
            error="El nombre solo puede tener letras, espacios y guiones. "
                  "Ingresá el nombre completo."
        )

    # No puede tener dígitos — un nombre no tiene números
    if any(c.isdigit() for c in value):
        return ValidationResult(
            valid=False,
            value=None,
            error="El nombre no puede tener números. Ingresá solo letras."
        )

    # Debe tener al menos una letra
    if not any(c.isalpha() for c in value):
        return ValidationResult(
            valid=False,
            value=None,
            error="Ingresá un nombre válido con letras."
        )

    # Normalizar: Title Case
    normalized = value.title()

    return ValidationResult(valid=True, value=normalized, error=None)


# ==================================================
# TELÉFONO — Argentina
# ==================================================

def validate_phone_ar(raw: str) -> ValidationResult:
    """
    Valida y normaliza un número de teléfono argentino.

    Formatos aceptados (todos se normalizan a +549XXXXXXXXXX):
        - +5491112345678      → ya normalizado
        - +54 9 11 1234-5678  → con espacios
        - 1112345678          → solo número local (10 dígitos)
        - 01112345678         → con 0 adelante
        - 91112345678         → con 9 adelante
        - 011-1234-5678       → con guiones y 0
        - 11-1234-5678        → sin 0
        - 351-123-4567        → interior (córdoba)
        - 3511234567          → interior sin guión

    Rechaza:
        - Menos de 10 dígitos locales
        - Más de 11 dígitos locales
        - Texto que no sea un número

    Returns:
        ValidationResult con número en formato +549XXXXXXXXXX si válido
    """
    value = raw.strip()

    # Quitar todo lo que no sea dígito o +
    digits_only = re.sub(r'[^\d+]', '', value)

    # Si tiene letras (después de limpiar) → no es teléfono
    letters = re.sub(r'[\d\s\+\-\(\)\.]+', '', value)
    if letters:
        return ValidationResult(
            valid=False,
            value=None,
            error="Ese no parece un número de teléfono válido. "
                  "Ingresá solo números, por ejemplo: 1112345678"
        )

    # Extraer solo dígitos para trabajar
    digits = re.sub(r'\D', '', digits_only)

    # Casos por longitud de dígitos
    # Argentina: código de área (2-4 dígitos) + número (6-8 dígitos) = 10 dígitos locales

    if digits.startswith('549') and len(digits) == 13:
        # 549XXXXXXXXXX (13 dígitos) → +549 + 10 dígitos locales
        # Ejemplo: 5491112345678 → local = 91112345678
        local = '9' + digits[3:]   # prefijo 9 + 10 dígitos

    elif digits.startswith('54') and len(digits) == 12:
        # 54XXXXXXXXXX (12 dígitos, sin el 9 móvil)
        # Ejemplo: 541112345678 → agregar 9
        local = '9' + digits[2:]

    elif digits.startswith('9') and len(digits) == 11:
        # 9XXXXXXXXXX (11 dígitos) → ya tiene el 9
        local = digits

    elif digits.startswith('0') and len(digits) == 11:
        # 0XXXXXXXXXX → reemplazar 0 por 9
        local = '9' + digits[1:]

    elif len(digits) == 10:
        # XXXXXXXXXX (10 dígitos sin prefijo) → agregar 9
        local = '9' + digits

    else:
        # Longitud inválida
        n = len(digits)
        if n < 8:
            return ValidationResult(
                valid=False,
                value=None,
                error="El número es muy corto. "
                      "Ingresá el número completo, por ejemplo: 1112345678"
            )
        else:
            return ValidationResult(
                valid=False,
                value=None,
                error="No reconocí ese número. "
                      "Ingresá un número argentino, por ejemplo: 1112345678"
            )

    # Verificar que local tenga 11 dígitos (9 + 10 locales)
    if len(local) != 11:
        return ValidationResult(
            valid=False,
            value=None,
            error="No reconocí ese número. "
                  "Ingresá un número argentino, por ejemplo: 1112345678"
        )

    normalized = f"+54{local}"

    return ValidationResult(valid=True, value=normalized, error=None)


# ==================================================
# EDAD
# ==================================================

def validate_age(raw: str) -> ValidationResult:
    """
    Valida una edad.

    Acepta: '5', '28', '100'
    Rechaza: negativos, > 120, texto

    Returns:
        ValidationResult con edad como string si válida
    """
    value = raw.strip()

    if not value.isdigit():
        return ValidationResult(
            valid=False,
            value=None,
            error="Ingresá la edad como número, por ejemplo: 28"
        )

    age = int(value)

    if age < 0 or age > 120:
        return ValidationResult(
            valid=False,
            value=None,
            error="La edad debe ser entre 0 y 120 años."
        )

    return ValidationResult(valid=True, value=str(age), error=None)
