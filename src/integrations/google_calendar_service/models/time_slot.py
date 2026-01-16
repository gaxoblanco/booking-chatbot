"""
TimeSlot - Modelo para representar un bloque de tiempo disponible.

Representa un intervalo de tiempo que puede ser reservado para una cita.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional


@dataclass
class TimeSlot:
    """
    Representa un bloque de tiempo disponible para reservar.
    
    Attributes:
        start: Hora de inicio del slot
        end: Hora de fin del slot
        duration_minutes: Duración en minutos
        date: Fecha del slot (opcional, se puede inferir de start)
    """
    
    start: datetime
    end: datetime
    duration_minutes: int
    date: Optional[str] = None
    
    def __post_init__(self):
        """Validaciones y cálculos post-inicialización."""
        # Validar que end sea después de start
        if self.end <= self.start:
            raise ValueError("La hora de fin debe ser posterior a la hora de inicio")
        
        # Calcular duración si no se proporcionó
        calculated_duration = int((self.end - self.start).total_seconds() / 60)
        if self.duration_minutes != calculated_duration:
            # Ajustar duración basada en el cálculo real
            self.duration_minutes = calculated_duration
        
        # Inferir fecha si no se proporcionó
        if self.date is None:
            self.date = self.start.strftime('%Y-%m-%d')
    
    def to_dict(self) -> dict:
        """
        Convierte el TimeSlot a un diccionario.
        
        Returns:
            dict: Representación del slot con formato legible
        """
        return {
            'date': self.date,
            'start': self.start.strftime('%H:%M'),
            'end': self.end.strftime('%H:%M'),
            'start_datetime': self.start.isoformat(),
            'end_datetime': self.end.isoformat(),
            'duration_minutes': self.duration_minutes
        }
    
    def overlaps_with(self, other: 'TimeSlot') -> bool:
        """
        Verifica si este slot se superpone con otro.
        
        Args:
            other: Otro TimeSlot para comparar
        
        Returns:
            bool: True si hay superposición, False en caso contrario
        """
        return (self.start < other.end and self.end > other.start)
    
    def contains_time(self, dt: datetime) -> bool:
        """
        Verifica si un datetime específico está dentro de este slot.
        
        Args:
            dt: Datetime a verificar
        
        Returns:
            bool: True si el datetime está dentro del slot
        """
        return self.start <= dt < self.end
    
    @classmethod
    def from_strings(cls, date: str, start_time: str, end_time: str, timezone_str: str = None):
        """
        Crea un TimeSlot desde strings de fecha y hora.
        
        Args:
            date: Fecha en formato 'YYYY-MM-DD'
            start_time: Hora de inicio en formato 'HH:MM'
            end_time: Hora de fin en formato 'HH:MM'
            timezone_str: Zona horaria (opcional)
        
        Returns:
            TimeSlot: Nuevo slot creado
        
        Example:
            slot = TimeSlot.from_strings('2026-01-16', '09:00', '10:00')
        """
        from datetime import datetime
        import pytz
        
        # Parsear fecha y horas
        start_dt = datetime.strptime(f"{date} {start_time}", '%Y-%m-%d %H:%M')
        end_dt = datetime.strptime(f"{date} {end_time}", '%Y-%m-%d %H:%M')
        
        # Aplicar timezone si se proporciona
        if timezone_str:
            tz = pytz.timezone(timezone_str)
            start_dt = tz.localize(start_dt)
            end_dt = tz.localize(end_dt)
        
        # Calcular duración
        duration = int((end_dt - start_dt).total_seconds() / 60)
        
        return cls(
            start=start_dt,
            end=end_dt,
            duration_minutes=duration,
            date=date
        )
    
    def __str__(self) -> str:
        """Representación legible del slot."""
        return f"{self.date} {self.start.strftime('%H:%M')}-{self.end.strftime('%H:%M')} ({self.duration_minutes}min)"
    
    def __repr__(self) -> str:
        """Representación técnica del slot."""
        return f"TimeSlot(start={self.start.isoformat()}, end={self.end.isoformat()}, duration={self.duration_minutes})"
