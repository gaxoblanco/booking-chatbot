"""
Filtros CORE del sistema.

Estos son filtros esenciales para el funcionamiento básico del sistema de búsqueda.
Implementan los criterios principales de disponibilidad y especialidad.
"""

from datetime import datetime, date, timedelta
from typing import Dict, List, Tuple, Optional
import sys
import os

# Agregar el directorio raíz al path para imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from filters.base_filter import BaseFilter
from filters.filter_types import FilterType, FilterCategory, FilterPriority
from config.domain_config import DomainConfig


class DateFilter(BaseFilter):
    """
    Filtro de fecha para búsqueda de turnos.
    
    Permite seleccionar la fecha en que el cliente desea atención.
    Ofrece opciones rápidas (Hoy, Mañana) o entrada manual directa (DD/MM/YYYY).
    """
    
    def __init__(self):
        super().__init__(
            filter_type=FilterType.DATE,
            category=FilterCategory.CORE,
            priority=FilterPriority.REQUIRED,
            display_name="Fecha",
            emoji="📅"
        )
    
    def get_menu_option_text(self, is_active: bool = False, active_value: Dict = None) -> str:
        """Texto para el menú principal de filtros."""
        if is_active and active_value:
            display = active_value.get('display', '')
            return f"{self.emoji} Fecha: {display}"
        return f"{self.emoji} Fecha"
    
    def get_input_prompt(self, session_data: dict) -> str:
        """Mensaje que se muestra al seleccionar este filtro."""
        today = date.today()
        tomorrow = today + timedelta(days=1)
        
        return f"""📅 *Selecciona la fecha*

¿Cuándo necesitas el turno?

1️⃣ Hoy ({today.strftime('%d/%m/%Y')})
2️⃣ Mañana ({tomorrow.strftime('%d/%m/%Y')})

💡 *O ingresa la fecha directamente en formato DD/MM/YYYY*
Ejemplo: 25/01/2026

0️⃣ Volver al menú de filtros"""
    
    def validate_input(self, user_input: str, session_data: dict = None) -> Tuple[bool, Optional[str]]:
        """
        Valida el input de fecha.
        
        Acepta:
        - "1" para Hoy
        - "2" para Mañana
        - Fecha directa en formato DD/MM/YYYY
        
        Valida que:
        - La fecha no sea del pasado
        - El formato sea correcto
        """
        # Opciones rápidas (Hoy o Mañana)
        if user_input in ['1', '2']:
            return (True, None)
        
        # Intentar parsear fecha manual directamente
        date_obj = self._parse_date(user_input)
        
        if not date_obj:
            return (False, "❌ Formato de fecha inválido. Usa DD/MM/YYYY (ejemplo: 25/12/2026) o selecciona 1 (Hoy) o 2 (Mañana)")
        
        # Validar que no sea del pasado
        if date_obj < date.today():
            return (False, f"❌ La fecha {user_input} ya pasó. Ingresa una fecha de hoy en adelante.")
        
        return (True, None)
    
    def process_input(self, user_input: str, session_data: dict = None) -> Dict:
        """
        Procesa el input y retorna la estructura del filtro.
        
        Returns:
            {
                'display': 'Hoy - 19/01/2026',
                'date': '2026-01-19',
                'date_obj': datetime.date(2026, 1, 19)
            }
        """
        today = date.today()
        tomorrow = today + timedelta(days=1)
        
        if user_input == '1':
            # Hoy
            return {
                'display': f"Hoy - {today.strftime('%d/%m/%Y')}",
                'date': today.strftime('%Y-%m-%d'),
                'date_obj': today
            }
        elif user_input == '2':
            # Mañana
            return {
                'display': f"Mañana - {tomorrow.strftime('%d/%m/%Y')}",
                'date': tomorrow.strftime('%Y-%m-%d'),
                'date_obj': tomorrow
            }
        else:
            # Fecha manual (DD/MM/YYYY) - entrada directa
            date_obj = self._parse_date(user_input)
            return {
                'display': date_obj.strftime('%d/%m/%Y'),
                'date': date_obj.strftime('%Y-%m-%d'),
                'date_obj': date_obj
            }
    
    def convert_to_db_param(self, processed_data: Dict) -> Dict:
        """
        Convierte a parámetro de base de datos.
        
        Returns:
            {'available_date': '2026-01-19'}
        """
        return {
            'date_str': processed_data['date'] 
        }
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """
        Parsea una fecha en formato DD/MM/YYYY.
        
        Args:
            date_str: Fecha como string (ej: "25/12/2026")
        
        Returns:
            datetime.date object o None si es inválida
        """
        try:
            return datetime.strptime(date_str, '%d/%m/%Y').date()
        except ValueError:
            return None


class TimeFilter(BaseFilter):
    """
    Filtro de horario para búsqueda de turnos.
    
    Permite seleccionar el rango horario deseado (Mañana/Tarde)
    o ingresar una hora específica directamente.
    """
    
    def __init__(self):
        super().__init__(
            filter_type=FilterType.TIME,
            category=FilterCategory.CORE,
            priority=FilterPriority.RECOMMENDED,
            display_name="Horario",
            emoji="🕐"
        )
    
    def get_menu_option_text(self, is_active: bool = False, active_value: Dict = None) -> str:
        """Texto para el menú principal de filtros."""
        if is_active and active_value:
            display = active_value.get('display', '')
            return f"{self.emoji} Horario: {display}"
        return f"{self.emoji} Horario"
    
    def get_input_prompt(self, session_data: dict) -> str:
        """Mensaje que se muestra al seleccionar este filtro."""
        return """🕐 *Selecciona el horario*

¿En qué horario prefieres el turno?

1️⃣ Mañana (8:00 - 13:00)
2️⃣ Tarde (13:00 - 20:00)

💡 *O ingresa una hora específica en formato HH:MM*
Ejemplo: 14:30

0️⃣ Volver al menú de filtros"""
    
    def validate_input(self, user_input: str, session_data: dict = None) -> Tuple[bool, Optional[str]]:
        """
        Valida el input de horario.
        
        Acepta:
        - "1" o "2" para rangos rápidos
        - Hora directa en formato HH:MM (ej: 14:30)
        """
        # Opciones rápidas
        if user_input in ['1', '2']:
            return (True, None)
        
        # Validar formato HH:MM directamente
        if self._validate_time_format(user_input):
            return (True, None)
        
        return (False, "❌ Formato inválido. Usa HH:MM (ejemplo: 14:30) o selecciona 1 (Mañana) o 2 (Tarde)")
    
    def process_input(self, user_input: str, session_data: dict = None) -> Dict:
        """
        Procesa el input de horario.
        
        Returns:
            {
                'display': 'Mañana (8:00-13:00)',
                'time': 'morning'  # o 'afternoon' o '14:30'
            }
        """
        if user_input == '1':
            return {
                'display': 'Mañana (8:00-13:00)',
                'time': 'morning',
                'range': (8, 13)
            }
        elif user_input == '2':
            return {
                'display': 'Tarde (13:00-20:00)',
                'time': 'afternoon',
                'range': (13, 20)
            }
        else:
            # Hora específica ingresada directamente
            return {
                'display': f"A las {user_input}",
                'time': user_input,
                'specific': True
            }
    
    def convert_to_db_param(self, processed_data: Dict) -> Dict:
        """
        Convierte a parámetro de base de datos.
        
        Returns:
            {'time_preference': 'morning'} o {'specific_time': '14:30'}
        """
        if 'specific' in processed_data:
            return {'specific_time': processed_data['time']}
        else:
            return {'time_preference': processed_data['time']}
    
    def _validate_time_format(self, time_str: str) -> bool:
        """
        Valida formato HH:MM.
        
        Args:
            time_str: Hora como string (ej: "14:30")
        
        Returns:
            True si es válido, False caso contrario
        """
        try:
            time_obj = datetime.strptime(time_str, '%H:%M').time()
            # Validar rango horario razonable (6:00 - 22:00)
            return 6 <= time_obj.hour <= 22
        except ValueError:
            return False


class SpecialtyFilter(BaseFilter):
    """
    Filtro de especialidad médica.
    
    Permite seleccionar la especialidad/categoría del profesional que se busca.
    Las opciones se cargan dinámicamente desde DomainConfig.
    """
    
    def __init__(self):
        super().__init__(
            filter_type=FilterType.SPECIALTY,
            category=FilterCategory.CORE,
            priority=FilterPriority.RECOMMENDED,
            display_name=DomainConfig.CATEGORY_LABEL,  # "Especialidad" o similar
            emoji="🩺"
        )
    
    def get_menu_option_text(self, is_active: bool = False, active_value: Dict = None) -> str:
        """Texto para el menú principal de filtros."""
        if is_active and active_value:
            display = active_value.get('display', '')
            return f"{self.emoji} {self.display_name}: {display}"
        return f"{self.emoji} {self.display_name}"
    
    def get_input_prompt(self, session_data: dict) -> str:
        """
        Mensaje que se muestra al seleccionar este filtro.
        
        Genera opciones dinámicamente desde DomainConfig.CATEGORIES
        """
        categories = DomainConfig.CATEGORIES
        
        # Generar opciones dinámicamente
        options = []
        for key, label in categories.items():
            options.append(f"{key}️⃣ {label}")
        
        options_text = "\n".join(options)
        
        return f"""🩺 *Selecciona {self.display_name.lower()}*

{options_text}

0️⃣ Volver al menú de filtros"""
    
    def validate_input(self, user_input: str, session_data: dict = None) -> Tuple[bool, Optional[str]]:
        """
        Valida que la opción seleccionada exista en DomainConfig.
        
        Args:
            user_input: Número de opción ingresado
        
        Returns:
            (True, None) si es válido
            (False, mensaje_error) si es inválido
        """
        categories = DomainConfig.CATEGORIES
        
        if user_input in categories:
            return (True, None)
        
        valid_options = ", ".join(categories.keys())
        return (False, f"❌ Opción inválida. Opciones válidas: {valid_options}")
    
    def process_input(self, user_input: str, session_data: dict = None) -> Dict:
        """
        Procesa la selección de especialidad.
        
        Returns:
            {
                'display': 'Psicología',
                'category_key': '1',
                'category_label': 'Psicología'
            }
        """
        categories = DomainConfig.CATEGORIES
        category_label = categories[user_input]
        
        return {
            'display': category_label,
            'category_key': user_input,
            'category_label': category_label
        }
    
    def convert_to_db_param(self, processed_data: Dict) -> Dict:
        """
        Convierte a parámetro de base de datos.
        
        Returns:
            {'specialty': 'Psicología'}  o {'category': 'Psicología'}
        """
        # Usamos category_label para la búsqueda en BD
        return {
            'specialty': processed_data['category_label']
        }