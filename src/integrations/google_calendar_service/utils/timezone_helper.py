"""
Timezone Helper - Utilidades para manejo de zonas horarias.

Funciones auxiliares para trabajar con fechas y horas en diferentes
zonas horarias, especialmente para Argentina.
"""

import pytz
from datetime import datetime, time, timedelta
from typing import Optional


# Zona horaria por defecto (Argentina)
DEFAULT_TIMEZONE = 'America/Argentina/Buenos_Aires'


def get_timezone(timezone_str: Optional[str] = None):
    """
    Obtiene un objeto timezone de pytz.
    
    Args:
        timezone_str: Nombre de la zona horaria (ej: 'America/Argentina/Buenos_Aires')
                     Si es None, usa la zona horaria por defecto
    
    Returns:
        pytz.timezone: Objeto de zona horaria
    """
    tz_name = timezone_str or DEFAULT_TIMEZONE
    return pytz.timezone(tz_name)


def localize_datetime(dt: datetime, timezone_str: Optional[str] = None) -> datetime:
    """
    Agrega información de zona horaria a un datetime naive.
    
    Args:
        dt: Datetime sin timezone (naive)
        timezone_str: Zona horaria a aplicar
    
    Returns:
        datetime: Datetime con timezone (aware)
    """
    tz = get_timezone(timezone_str)
    
    # Si ya tiene timezone, convertir a la nueva
    if dt.tzinfo is not None:
        return dt.astimezone(tz)
    
    # Si es naive, localizarlo
    return tz.localize(dt)


def parse_time_string(time_str: str) -> time:
    """
    Parsea un string de hora en formato HH:MM.
    
    Args:
        time_str: Hora en formato 'HH:MM' (ej: '09:00', '14:30')
    
    Returns:
        time: Objeto time de Python
    
    Raises:
        ValueError: Si el formato es inválido
    """
    try:
        hour, minute = map(int, time_str.split(':'))
        return time(hour=hour, minute=minute)
    except (ValueError, AttributeError):
        raise ValueError(f"Formato de hora inválido: {time_str}. Use 'HH:MM'")


def combine_date_time(date_str: str, time_str: str, timezone_str: Optional[str] = None) -> datetime:
    """
    Combina una fecha y hora en un datetime con timezone.
    
    Args:
        date_str: Fecha en formato 'YYYY-MM-DD'
        time_str: Hora en formato 'HH:MM'
        timezone_str: Zona horaria a aplicar
    
    Returns:
        datetime: Datetime completo con timezone
    
    Example:
        dt = combine_date_time('2026-01-16', '14:00', 'America/Argentina/Buenos_Aires')
    """
    # Parsear fecha
    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
    
    # Parsear hora
    time_obj = parse_time_string(time_str)
    
    # Combinar
    dt = datetime.combine(date_obj, time_obj)
    
    # Agregar timezone
    return localize_datetime(dt, timezone_str)


def to_iso_format(dt: datetime) -> str:
    """
    Convierte un datetime a formato ISO 8601 para Google Calendar API.
    
    Args:
        dt: Datetime a convertir
    
    Returns:
        str: String en formato ISO 8601 (ej: '2026-01-16T14:00:00-03:00')
    """
    return dt.isoformat()


def parse_google_datetime(datetime_str: str, timezone_str: Optional[str] = None) -> datetime:
    """
    Parsea un datetime de Google Calendar API.
    
    Google Calendar puede retornar fechas en formato ISO con o sin timezone.
    
    Args:
        datetime_str: String de datetime de Google Calendar
        timezone_str: Timezone a usar si el string no lo incluye
    
    Returns:
        datetime: Datetime parseado con timezone
    """
    try:
        # Intentar parsear con timezone incluido
        dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        
        # Si tiene timezone, convertir a la zona horaria deseada
        if dt.tzinfo is not None and timezone_str:
            target_tz = get_timezone(timezone_str)
            dt = dt.astimezone(target_tz)
        
        return dt
        
    except ValueError:
        # Si falla, intentar formato sin timezone
        dt = datetime.fromisoformat(datetime_str)
        return localize_datetime(dt, timezone_str)


def get_day_start_end(date_str: str, timezone_str: Optional[str] = None) -> tuple[datetime, datetime]:
    """
    Obtiene el inicio (00:00) y fin (23:59:59) de un día específico.
    
    Args:
        date_str: Fecha en formato 'YYYY-MM-DD'
        timezone_str: Zona horaria
    
    Returns:
        tuple: (datetime_inicio, datetime_fin) del día
    
    Example:
        start, end = get_day_start_end('2026-01-16')
        # start = 2026-01-16 00:00:00-03:00
        # end   = 2026-01-16 23:59:59-03:00
    """
    start = combine_date_time(date_str, '00:00', timezone_str)
    end = combine_date_time(date_str, '23:59', timezone_str) + timedelta(seconds=59)
    
    return start, end


def generate_time_slots(
    start_time: str,
    end_time: str,
    slot_duration_minutes: int,
    break_duration_minutes: int = 0
) -> list[tuple[str, str]]:
    """
    Genera una lista de slots de tiempo entre dos horas.
    
    Args:
        start_time: Hora de inicio en formato 'HH:MM'
        end_time: Hora de fin en formato 'HH:MM'
        slot_duration_minutes: Duración de cada slot en minutos
        break_duration_minutes: Minutos de descanso entre slots (opcional)
    
    Returns:
        list: Lista de tuplas (hora_inicio, hora_fin) en formato 'HH:MM'
    
    Example:
        slots = generate_time_slots('09:00', '12:00', 60)
        # [('09:00', '10:00'), ('10:00', '11:00'), ('11:00', '12:00')]
    """
    start = parse_time_string(start_time)
    end = parse_time_string(end_time)
    
    slots = []
    current = datetime.combine(datetime.today(), start)
    end_dt = datetime.combine(datetime.today(), end)
    
    while current + timedelta(minutes=slot_duration_minutes) <= end_dt:
        slot_start = current.time()
        slot_end = (current + timedelta(minutes=slot_duration_minutes)).time()
        
        slots.append((
            slot_start.strftime('%H:%M'),
            slot_end.strftime('%H:%M')
        ))
        
        # Avanzar al siguiente slot (incluye break si existe)
        current += timedelta(minutes=slot_duration_minutes + break_duration_minutes)
    
    return slots


def is_within_working_hours(
    dt: datetime,
    working_hours: dict,
    timezone_str: Optional[str] = None
) -> bool:
    """
    Verifica si un datetime está dentro del horario laboral.
    
    Args:
        dt: Datetime a verificar
        working_hours: Dict con 'start' y 'end' en formato 'HH:MM'
                      Ej: {'start': '09:00', 'end': '18:00'}
        timezone_str: Zona horaria
    
    Returns:
        bool: True si está dentro del horario laboral
    """
    # Asegurar que dt tenga timezone
    if dt.tzinfo is None:
        dt = localize_datetime(dt, timezone_str)
    
    # Obtener hora del datetime
    time_to_check = dt.time()
    
    # Parsear horario laboral
    start_time = parse_time_string(working_hours['start'])
    end_time = parse_time_string(working_hours['end'])
    
    return start_time <= time_to_check < end_time
