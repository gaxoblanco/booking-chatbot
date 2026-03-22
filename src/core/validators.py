"""
Input Validators
================
Validates and parses user input for dates, times, and other formats.
Ensures data consistency before storing in database.
"""

from datetime import datetime, date, time
import re
from typing import Optional


def validate_date(date_string: str) -> bool:
    """
    Validate if string is a valid date in DD/MM/YYYY format.

    Args:
        date_string: Date string to validate

    Returns:
        True if valid, False otherwise

    Examples:
        >>> validate_date("15/11/2025")
        True
        >>> validate_date("32/13/2025")
        False
    """
    try:
        datetime.strptime(date_string, "%d/%m/%Y")
        return True
    except ValueError:
        return False


def parse_date(date_string: str) -> date:
    """
    Parse date string to date object.

    Args:
        date_string: Date in DD/MM/YYYY format

    Returns:
        date object or None if invalid

    Examples:
        >>> parse_date("15/11/2025")
        datetime.date(2025, 11, 15)
        >>> parse_date("invalid")
        None
    """
    try:
        dt = datetime.strptime(date_string, "%d/%m/%Y")
        return dt.date()
    except ValueError:
        return None


def validate_time(time_string: str) -> bool:
    """
    Validate if string is a valid time in HH:MM format (24-hour).

    Args:
        time_string: Time string to validate

    Returns:
        True if valid, False otherwise

    Examples:
        >>> validate_time("14:30")
        True
        >>> validate_time("25:00")
        False
        >>> validate_time("9:30")
        False  # Must be zero-padded
    """
    try:
        datetime.strptime(time_string, "%H:%M")
        return True
    except ValueError:
        return False


def parse_time(time_string: str) -> time:
    """
    Parse time string to time object.

    Args:
        time_string: Time in HH:MM format

    Returns:
        time object or None if invalid

    Examples:
        >>> parse_time("14:30")
        datetime.time(14, 30)
        >>> parse_time("invalid")
        None
    """
    try:
        dt = datetime.strptime(time_string, "%H:%M")
        return dt.time()
    except ValueError:
        return None


def validate_time_range(time_range_string: str) -> bool:
    """
    Validate if string is a valid time range in HH:MM-HH:MM format.
    Also validates that end time is after start time.

    Args:
        time_range_string: Time range to validate

    Returns:
        True if valid, False otherwise

    Examples:
        >>> validate_time_range("09:00-17:00")
        True
        >>> validate_time_range("17:00-09:00")
        False  # End before start
        >>> validate_time_range("14:00-14:00")
        False  # Same time
    """
    try:
        start_str, end_str = time_range_string.split('-')
        start_str = start_str.strip()
        end_str = end_str.strip()

        # Validate both times
        if not validate_time(start_str) or not validate_time(end_str):
            return False

        # Parse to compare
        start_time = parse_time(start_str)
        end_time = parse_time(end_str)

        # End must be after start
        if end_time <= start_time:
            return False

        return True

    except (ValueError, AttributeError):
        return False


def parse_time_range(time_range_string: str) -> tuple:
    """
    Parse time range string to tuple of (start_time, end_time) strings.

    Args:
        time_range_string: Time range in HH:MM-HH:MM format

    Returns:
        Tuple of (start, end) as strings, or None if invalid

    Examples:
        >>> parse_time_range("09:00-17:00")
        ("09:00", "17:00")
        >>> parse_time_range("invalid")
        None
    """
    try:
        start_str, end_str = time_range_string.split('-')
        start_str = start_str.strip()
        end_str = end_str.strip()

        # Validate format
        if not validate_time(start_str) or not validate_time(end_str):
            return None

        # Validate end > start
        start_time = parse_time(start_str)
        end_time = parse_time(end_str)

        if end_time <= start_time:
            return None

        return (start_str, end_str)

    except (ValueError, AttributeError):
        return None


def validate_option(option: str, valid_options: list) -> bool:
    """
    Validate if option is in list of valid options.

    Args:
        option: User's input
        valid_options: List of valid option values

    Returns:
        True if valid, False otherwise

    Examples:
        >>> validate_option("1", ["1", "2", "3"])
        True
        >>> validate_option("4", ["1", "2", "3"])
        False
    """
    return option in valid_options


def validate_phone_number(phone: str) -> bool:
    """
    Validate phone number format.
    Accepts formats like: +1234567890, 1234567890, +54 9 370 4969801

    Args:
        phone: Phone number string

    Returns:
        True if valid format, False otherwise

    Examples:
        >>> validate_phone_number("+5493704969801")
        True
        >>> validate_phone_number("123")
        False
    """
    # Remove common separators
    clean_phone = re.sub(r'[\s\-\(\)]', '', phone)

    # Must start with + or digit, and be 10-15 digits
    pattern = r'^\+?\d{10,15}$'

    return bool(re.match(pattern, clean_phone))


def clean_phone_number(phone: str) -> str:
    """
    Clean and normalize phone number.
    Removes spaces, dashes, parentheses.

    Args:
        phone: Raw phone number

    Returns:
        Cleaned phone number

    Examples:
        >>> clean_phone_number("+54 9 370 496-9801")
        "+5493704969801"
        >>> clean_phone_number("(123) 456-7890")
        "1234567890"
    """
    return re.sub(r'[\s\-\(\)]', '', phone)


def validate_zona(zona: str) -> bool:
    """
    Validate zona filter value.

    Args:
        zona: Zone value

    Returns:
        True if valid, False otherwise
    """
    valid_zonas = ['norte', 'sur', 'n', 's', '1', '2']
    return zona.lower() in valid_zonas


def normalize_zona(zona: str) -> str:
    """
    Normalize zona value to standard format.

    Args:
        zona: Raw zona input

    Returns:
        Normalized zona ('norte' or 'sur')

    Examples:
        >>> normalize_zona("1")
        "norte"
        >>> normalize_zona("N")
        "norte"
        >>> normalize_zona("sur")
        "sur"
    """
    zona_lower = zona.lower()

    if zona_lower in ['norte', 'n', '1']:
        return 'norte'
    elif zona_lower in ['sur', 's', '2']:
        return 'sur'
    else:
        return zona_lower


def validate_sexo(sexo: str) -> bool:
    """
    Validate sexo filter value.

    Args:
        sexo: Sex value

    Returns:
        True if valid, False otherwise
    """
    valid_values = ['m', 'f', 'masculino', 'femenino', '1', '2', '3']
    return sexo.lower() in valid_values


def normalize_sexo(sexo: str) -> str:
    """
    Normalize sexo value to standard format.

    Args:
        sexo: Raw sexo input

    Returns:
        Normalized sexo ('m', 'f', or None)

    Examples:
        >>> normalize_sexo("1")
        "m"
        >>> normalize_sexo("masculino")
        "m"
        >>> normalize_sexo("3")
        None
    """
    sexo_lower = sexo.lower()

    if sexo_lower in ['m', 'masculino', '1']:
        return 'm'
    elif sexo_lower in ['f', 'femenino', '2']:
        return 'f'
    elif sexo_lower in ['3', 'no importa']:
        return None
    else:
        return sexo_lower


def validate_day_of_week(day: str) -> bool:
    """
    Validate day of week input (1-7 or day names).

    Args:
        day: Day input

    Returns:
        True if valid, False otherwise

    Examples:
        >>> validate_day_of_week("1")
        True
        >>> validate_day_of_week("lunes")
        True
        >>> validate_day_of_week("8")
        False
    """
    # Check numeric (1-7)
    if day.isdigit():
        return 1 <= int(day) <= 7

    # Check day names
    valid_names = [
        'lunes', 'martes', 'miercoles', 'miércoles',
        'jueves', 'viernes', 'sabado', 'sábado', 'domingo'
    ]
    return day.lower() in valid_names


def normalize_day_of_week(day: str) -> int:
    """
    Normalize day of week to number (1-7, where 1=Monday).

    Args:
        day: Day input (number or name)

    Returns:
        Day number (1-7) or None if invalid

    Examples:
        >>> normalize_day_of_week("1")
        1
        >>> normalize_day_of_week("lunes")
        1
        >>> normalize_day_of_week("domingo")
        7
    """
    # Already a number
    if day.isdigit():
        num = int(day)
        return num if 1 <= num <= 7 else None

    # Map names to numbers
    day_map = {
        'lunes': 1,
        'martes': 2,
        'miercoles': 3,
        'miércoles': 3,
        'jueves': 4,
        'viernes': 5,
        'sabado': 6,
        'sábado': 6,
        'domingo': 7
    }

    return day_map.get(day.lower())


def validate_email(email: str) -> bool:
    """
    Validate email format.
    Basic validation, not RFC-compliant.

    Args:
        email: Email address

    Returns:
        True if valid format, False otherwise

    Examples:
        >>> validate_email("user@example.com")
        True
        >>> validate_email("invalid.email")
        False
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def sanitize_input(text: str, max_length: int = 500) -> str:
    """
    Sanitize user input by removing excessive whitespace and limiting length.

    Args:
        text: Raw user input
        max_length: Maximum allowed length

    Returns:
        Sanitized text

    Examples:
        >>> sanitize_input("  hello   world  ")
        "hello world"
        >>> sanitize_input("a" * 1000, max_length=10)
        "aaaaaaaaaa"
    """
    # Remove leading/trailing whitespace
    text = text.strip()

    # Replace multiple spaces with single space
    text = re.sub(r'\s+', ' ', text)

    # Limit length
    if len(text) > max_length:
        text = text[:max_length]

    return text


def is_past_date(date_obj: date) -> bool:
    """
    Check if date is in the past.

    Args:
        date_obj: Date to check

    Returns:
        True if date is in the past, False otherwise

    Examples:
        >>> from datetime import date, timedelta
        >>> yesterday = date.today() - timedelta(days=1)
        >>> is_past_date(yesterday)
        True
        >>> tomorrow = date.today() + timedelta(days=1)
        >>> is_past_date(tomorrow)
        False
    """
    return date_obj < date.today()


def is_valid_future_date(date_string: str) -> bool:
    """
    Validate that date is valid format AND in the future.

    Args:
        date_string: Date string in DD/MM/YYYY format

    Returns:
        True if valid and future, False otherwise

    Examples:
        >>> is_valid_future_date("15/11/2030")
        True
        >>> is_valid_future_date("15/11/2020")
        False
    """
    date_obj = parse_date(date_string)

    if not date_obj:
        return False

    return not is_past_date(date_obj)


# ==========================================
# UTILITY FUNCTIONS
# ==========================================

def format_date_for_display(date_obj: date) -> str:
    """
    Format date object for display to user.

    Args:
        date_obj: Date object

    Returns:
        Formatted date string

    Examples:
        >>> from datetime import date
        >>> format_date_for_display(date(2025, 11, 15))
        "15/11/2025"
    """
    return date_obj.strftime("%d/%m/%Y")


def format_time_for_display(time_obj: time) -> str:
    """
    Format time object for display to user.

    Args:
        time_obj: Time object

    Returns:
        Formatted time string

    Examples:
        >>> from datetime import time
        >>> format_time_for_display(time(14, 30))
        "14:30"
    """
    return time_obj.strftime("%H:%M")


def validate_phone_e164(phone: str) -> bool:
    """
    Valida que un número de teléfono esté en formato E.164.

    E.164: + seguido de 8 a 15 dígitos, sin espacios ni caracteres especiales.
    Ejemplos válidos:   +5491112345678, +1234567890
    Ejemplos inválidos: None, '', '123', 'whatsapp:+54...', '+0123'

    Args:
        phone: Número de teléfono a validar

    Returns:
        True si el formato es válido, False en cualquier otro caso
    """
    if not phone or not isinstance(phone, str):
        return False
    pattern = r'^\+[1-9]\d{7,14}$'
    return bool(re.match(pattern, phone.strip()))


def normalize_whatsapp_phone(raw: str) -> Optional[str]:
    """
    Extrae y valida el número de teléfono del formato Twilio WhatsApp.

    Twilio envía el número como 'whatsapp:+54XXXXXXXXXX'.
    Esta función limpia el prefijo y valida el resultado con E.164.

    Args:
        raw: Valor crudo del campo 'From' de Twilio
             Ejemplos: 'whatsapp:+5491112345678', '+5491112345678'

    Returns:
        Número limpio en formato E.164 si es válido (ej: '+5491112345678')
        None si el formato es inválido o el número no pasa la validación
    """
    if not raw or not isinstance(raw, str):
        print(f"[VALIDATOR] ❌ normalize_whatsapp_phone: valor nulo o no-string: {raw!r}")
        return None

    cleaned = raw.strip().replace('whatsapp:', '').strip()

    if validate_phone_e164(cleaned):
        return cleaned

    print(f"[VALIDATOR] ❌ Número inválido después de limpiar: {cleaned!r} (raw: {raw!r})")
    return None