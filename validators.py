"""
Input Validators
================
Validates and parses user input for dates, times, and other formats.
Ensures data consistency before storing in database.
"""

from datetime import datetime, date, time
import re


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


# ==========================================
# PSIVALE - VALIDADORES ESPECÍFICOS
# ==========================================

def validate_enfoque(enfoque: str) -> bool:
    """
    Validate enfoque terapéutico value.

    Args:
        enfoque: Therapeutic approach value

    Returns:
        True if valid, False otherwise

    Examples:
        >>> validate_enfoque("1")
        True
        >>> validate_enfoque("tcc")
        True
        >>> validate_enfoque("7")
        False
    """
    valid_values = [
        '1', '2', '3', '4', '5', '6',  # Numeric options
        'tcc', 'contextual', 'sistemica', 'gestaltica',
        'psicoanalisis', 'neuropsicologia',  # Text values
        'cognitivo', 'act', 'dbt', 'psicodinamica'  # Aliases
    ]
    return enfoque.lower() in valid_values


def normalize_enfoque(enfoque: str) -> str:
    """
    Normalize enfoque value to standard key.

    Args:
        enfoque: Raw enfoque input

    Returns:
        Normalized enfoque key

    Examples:
        >>> normalize_enfoque("1")
        "tcc"
        >>> normalize_enfoque("cognitivo")
        "tcc"
        >>> normalize_enfoque("2")
        "contextual"
    """
    enfoque_lower = enfoque.lower().strip()

    # Map from options
    enfoque_map = {
        '1': 'tcc',
        'tcc': 'tcc',
        'cognitivo': 'tcc',
        'cognitiva': 'tcc',
        'conductual': 'tcc',

        '2': 'contextual',
        'contextual': 'contextual',
        'contextuales': 'contextual',
        'act': 'contextual',
        'dbt': 'contextual',
        'fap': 'contextual',

        '3': 'sistemica',
        'sistemica': 'sistemica',
        'sistémica': 'sistemica',
        'sistemico': 'sistemica',

        '4': 'gestaltica',
        'gestaltica': 'gestaltica',
        'gestáltica': 'gestaltica',
        'gestalt': 'gestaltica',

        '5': 'psicoanalisis',
        'psicoanalisis': 'psicoanalisis',
        'psicoanálisis': 'psicoanalisis',
        'psicodinamica': 'psicoanalisis',
        'psicodinámica': 'psicoanalisis',
        'analitico': 'psicoanalisis',

        '6': 'neuropsicologia',
        'neuropsicologia': 'neuropsicologia',
        'neuropsicología': 'neuropsicologia',
        'neuro': 'neuropsicologia',
        'neurorehabilitacion': 'neuropsicologia',
    }

    return enfoque_map.get(enfoque_lower, enfoque_lower)


def parse_enfoque_list(input_text: str) -> list:
    """
    Parse list of enfoques from comma-separated string.
    Maximum 2 enfoques allowed.

    Args:
        input_text: Comma-separated enfoques or single value

    Returns:
        List of normalized enfoque keys (max 2)

    Examples:
        >>> parse_enfoque_list("1,3")
        ['tcc', 'sistemica']
        >>> parse_enfoque_list("1")
        ['tcc']
        >>> parse_enfoque_list("1,2,3")
        ['tcc', 'contextual']  # Only first 2
    """
    if not input_text:
        return []

    # Split by comma
    parts = [p.strip() for p in input_text.split(',')]

    # Normalize each and filter valid
    normalized = []
    for part in parts[:2]:  # Max 2
        if validate_enfoque(part):
            norm = normalize_enfoque(part)
            if norm not in normalized:  # Avoid duplicates
                normalized.append(norm)

    return normalized


def validate_poblacion(poblacion: str) -> bool:
    """
    Validate población value.

    Args:
        poblacion: Population value

    Returns:
        True if valid, False otherwise

    Examples:
        >>> validate_poblacion("1")
        True
        >>> validate_poblacion("adultos")
        True
        >>> validate_poblacion("5")
        False
    """
    valid_values = [
        '1', '2', '3', '4',  # Numeric options
        'ninos', 'niños', 'adolescentes', 'adultos',
        'parejas', 'familias', 'pareja'
    ]
    return poblacion.lower() in valid_values


def normalize_poblacion(poblacion: str) -> str:
    """
    Normalize población value to standard key.

    Args:
        poblacion: Raw población input

    Returns:
        Normalized población key

    Examples:
        >>> normalize_poblacion("1")
        "ninos"
        >>> normalize_poblacion("niños")
        "ninos"
        >>> normalize_poblacion("3")
        "adultos"
    """
    poblacion_lower = poblacion.lower().strip()

    poblacion_map = {
        '1': 'ninos',
        'ninos': 'ninos',
        'niños': 'ninos',
        'nino': 'ninos',
        'niño': 'ninos',
        'infantil': 'ninos',
        'infancia': 'ninos',

        '2': 'adolescentes',
        'adolescentes': 'adolescentes',
        'adolescente': 'adolescentes',
        'adolecencia': 'adolescentes',
        'joven': 'adolescentes',
        'jovenes': 'adolescentes',

        '3': 'adultos',
        'adultos': 'adultos',
        'adulto': 'adultos',
        'adultez': 'adultos',

        '4': 'parejas',
        'parejas': 'parejas',
        'pareja': 'parejas',
        'familias': 'parejas',
        'familia': 'parejas',
        'familiar': 'parejas',
    }

    return poblacion_map.get(poblacion_lower, poblacion_lower)


def parse_poblacion_list(input_text: str) -> list:
    """
    Parse list of poblaciones from comma-separated string.

    Args:
        input_text: Comma-separated poblaciones or single value

    Returns:
        List of normalized población keys

    Examples:
        >>> parse_poblacion_list("1,3")
        ['ninos', 'adultos']
        >>> parse_poblacion_list("adultos")
        ['adultos']
    """
    if not input_text:
        return []

    # Split by comma
    parts = [p.strip() for p in input_text.split(',')]

    # Normalize each and filter valid
    normalized = []
    for part in parts:
        if validate_poblacion(part):
            norm = normalize_poblacion(part)
            if norm not in normalized:  # Avoid duplicates
                normalized.append(norm)

    return normalized


def validate_modalidad(modalidad: str) -> bool:
    """
    Validate modalidad value.

    Args:
        modalidad: Modality value

    Returns:
        True if valid, False otherwise

    Examples:
        >>> validate_modalidad("1")
        True
        >>> validate_modalidad("online")
        True
        >>> validate_modalidad("4")
        False
    """
    valid_values = [
        '1', '2', '3',  # Numeric options
        'online', 'presencial', 'ambas', 'ambos',
        'virtual', 'consultorio'
    ]
    return modalidad.lower() in valid_values


def normalize_modalidad(modalidad: str) -> str:
    """
    Normalize modalidad value to standard key.

    Args:
        modalidad: Raw modalidad input

    Returns:
        Normalized modalidad ('online', 'presencial', or 'ambas')

    Examples:
        >>> normalize_modalidad("1")
        "online"
        >>> normalize_modalidad("virtual")
        "online"
        >>> normalize_modalidad("3")
        "ambas"
    """
    modalidad_lower = modalidad.lower().strip()

    modalidad_map = {
        '1': 'online',
        'online': 'online',
        'virtual': 'online',
        'videollamada': 'online',
        'remoto': 'online',

        '2': 'presencial',
        'presencial': 'presencial',
        'consultorio': 'presencial',
        'persona': 'presencial',
        'fisico': 'presencial',

        '3': 'ambas',
        'ambas': 'ambas',
        'ambos': 'ambas',
        'ambas modalidades': 'ambas',
        'las dos': 'ambas',
        'cualquiera': 'ambas',
    }

    return modalidad_map.get(modalidad_lower, modalidad_lower)


def validate_horarios(horario: str) -> bool:
    """
    Validate horario value.

    Args:
        horario: Schedule value

    Returns:
        True if valid, False otherwise

    Examples:
        >>> validate_horarios("1")
        True
        >>> validate_horarios("manana")
        True
        >>> validate_horarios("5")
        False
    """
    valid_values = [
        '1', '2', '3', '4', '5',  # Numeric options
        'manana', 'mañana', 'tarde', 'noche',
        'sabado', 'sábado', 'sabados', 'cualquiera'
    ]
    return horario.lower() in valid_values


def normalize_horario(horario: str) -> str:
    """
    Normalize horario value to standard key.

    Args:
        horario: Raw horario input

    Returns:
        Normalized horario key

    Examples:
        >>> normalize_horario("1")
        "manana"
        >>> normalize_horario("mañana")
        "manana"
        >>> normalize_horario("4")
        "sabado"
    """
    horario_lower = horario.lower().strip()

    horario_map = {
        '1': 'manana',
        'manana': 'manana',
        'mañana': 'manana',
        'morning': 'manana',

        '2': 'tarde',
        'tarde': 'tarde',
        'afternoon': 'tarde',

        '3': 'noche',
        'noche': 'noche',
        'nocturno': 'noche',
        'evening': 'noche',
        'night': 'noche',

        '4': 'sabado',
        'sabado': 'sabado',
        'sábado': 'sabado',
        'sabados': 'sabado',
        'sábados': 'sabado',
        'fin de semana': 'sabado',
        'weekend': 'sabado',

        '5': 'cualquiera',
        'cualquiera': 'cualquiera',
        'cualquier': 'cualquiera',
        'todos': 'cualquiera',
        'flexible': 'cualquiera',
    }

    return horario_map.get(horario_lower, horario_lower)


def parse_horarios_list(input_text: str) -> list:
    """
    Parse list of horarios from comma-separated string.

    Args:
        input_text: Comma-separated horarios or single value

    Returns:
        List of normalized horario keys

    Examples:
        >>> parse_horarios_list("1,2")
        ['manana', 'tarde']
        >>> parse_horarios_list("noche")
        ['noche']
        >>> parse_horarios_list("5")
        ['manana', 'tarde', 'noche', 'sabado']  # Cualquiera = all
    """
    if not input_text:
        return []

    # Split by comma
    parts = [p.strip() for p in input_text.split(',')]

    # Normalize each and filter valid
    normalized = []
    for part in parts:
        if validate_horarios(part):
            norm = normalize_horario(part)

            # Special case: "cualquiera" = all schedules
            if norm == 'cualquiera':
                return ['manana', 'tarde', 'noche', 'sabado']

            if norm not in normalized:  # Avoid duplicates
                normalized.append(norm)

    return normalized


def validate_fee_range(fee_range: str) -> bool:
    """
    Validate fee range value.

    Args:
        fee_range: Fee range value

    Returns:
        True if valid, False otherwise

    Examples:
        >>> validate_fee_range("1")
        True
        >>> validate_fee_range("25000-35000")
        True
        >>> validate_fee_range("6")
        False
    """
    # Numeric option (1-5)
    if fee_range.isdigit():
        return 1 <= int(fee_range) <= 5

    # Range format: XXXX-YYYY
    if '-' in fee_range:
        try:
            parts = fee_range.split('-')
            if len(parts) == 2:
                min_val = int(parts[0].strip())
                max_val = int(parts[1].strip())
                return min_val > 0 and max_val > min_val
        except ValueError:
            return False

    return False


def normalize_fee_range(fee_range: str) -> str:
    """
    Normalize fee range value to standard format.

    Args:
        fee_range: Raw fee range input

    Returns:
        Normalized fee range key or None for "prefiero no decir"

    Examples:
        >>> normalize_fee_range("1")
        "0-15000"
        >>> normalize_fee_range("3")
        "25000-35000"
        >>> normalize_fee_range("5")
        None  # Prefiere no decir
    """
    fee_range = fee_range.strip()

    # Numeric options
    if fee_range.isdigit():
        fee_map = {
            '1': '0-15000',
            '2': '15000-25000',
            '3': '25000-35000',
            '4': '35000-99999999',
            '5': None,  # Prefiero no decirlo
        }
        return fee_map.get(fee_range)

    # Already in range format
    if '-' in fee_range:
        try:
            parts = fee_range.split('-')
            if len(parts) == 2:
                min_val = int(parts[0].strip())
                max_val = int(parts[1].strip())
                if min_val > 0 and max_val > min_val:
                    return f"{min_val}-{max_val}"
        except ValueError:
            pass

    return None


def get_fee_range_display(fee_key: str) -> str:
    """
    Get display text for fee range key.

    Args:
        fee_key: Fee range key (e.g., "0-15000")

    Returns:
        Display text for the range

    Examples:
        >>> get_fee_range_display("0-15000")
        "Hasta $15.000"
        >>> get_fee_range_display("25000-35000")
        "$25.000 – $35.000"
    """
    if not fee_key:
        return "No especificado"

    display_map = {
        '0-15000': 'Hasta $15.000',
        '15000-25000': '$15.000 – $25.000',
        '25000-35000': '$25.000 – $35.000',
        '35000-99999999': 'Más de $35.000',
    }

    return display_map.get(fee_key, fee_key)


# ==========================================
# PSIVALE - VALIDACIONES DE ZONA EXTENDIDA
# ==========================================

def validate_zona_psivale(zona: str) -> bool:
    """
    Validate zona for Psivale (includes nueva_cordoba).

    Args:
        zona: Zone value

    Returns:
        True if valid, False otherwise
    """
    valid_zonas = ['norte', 'sur', 'nueva_cordoba',
                   'nueva', 'cordoba', 'n', 's', 'nc', '1', '2', '3']
    return zona.lower() in valid_zonas


def normalize_zona_psivale(zona: str) -> str:
    """
    Normalize zona value for Psivale.

    Args:
        zona: Raw zona input

    Returns:
        Normalized zona ('norte', 'sur', or 'nueva_cordoba')

    Examples:
        >>> normalize_zona_psivale("1")
        "norte"
        >>> normalize_zona_psivale("3")
        "nueva_cordoba"
        >>> normalize_zona_psivale("nueva")
        "nueva_cordoba"
    """
    zona_lower = zona.lower().strip()

    zona_map = {
        '1': 'norte',
        'norte': 'norte',
        'n': 'norte',
        'north': 'norte',

        '2': 'sur',
        'sur': 'sur',
        's': 'sur',
        'south': 'sur',

        '3': 'nueva_cordoba',
        'nueva_cordoba': 'nueva_cordoba',
        'nueva córdoba': 'nueva_cordoba',
        'nueva': 'nueva_cordoba',
        'cordoba': 'nueva_cordoba',
        'nc': 'nueva_cordoba',
    }

    return zona_map.get(zona_lower, zona_lower)
