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
Ejemplo: 25/01/2026 | 25/01/26 | 25/01

0️⃣ Volver al menú de filtros"""
    
    def validate_input(self, user_input: str, session_data: Dict = None) -> Tuple[bool, str]:
        """
        Valida el input del usuario.
        
        Acepta:
        - "1" o "hoy" → Hoy
        - "2" o "mañana" → Mañana
        - "DD/MM/YYYY", "DD/MM/YY", "DD/MM", "DD"
        
        Returns:
            (True, "") si válido
            (False, mensaje_error) si inválido
        """
        user_input = user_input.strip().lower()
        
        # Opciones rápidas
        if user_input in ['1', 'hoy', 'today']:
            return True, ""
        
        if user_input in ['2', 'mañana', 'mañana', 'tomorrow']:
            return True, ""
        
        # Intentar parsear fecha flexible
        try:
            parsed_date = self._parse_flexible_date(user_input)
            
            # Validar que no sea en el pasado
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            if parsed_date < today:
                return False, f"❌ La fecha {parsed_date.strftime('%d/%m/%Y')} ya pasó. Ingresa una fecha futura."
            
            # Validar que no sea más de 1 año en el futuro
            max_date = today + timedelta(days=365)
            if parsed_date > max_date:
                return False, "❌ No se pueden agendar turnos con más de 1 año de anticipación."
            
            return True, ""
            
        except ValueError as e:
            return False, f"❌ {str(e)}\n\n{self._get_format_help()}"
    
    def process_input(self, user_input: str, session_data: Dict = None) -> Dict:
        """
        Procesa el input y retorna diccionario con fecha.
        
        Returns:
            {
                'date': 'YYYY-MM-DD',     # Formato BD
                'display': 'DD/MM/YYYY'   # Formato display
            }
        """
        user_input = user_input.strip().lower()
        
        # Opciones rápidas
        if user_input in ['1', 'hoy', 'today']:
            date_obj = datetime.now()
        elif user_input in ['2', 'mañana', 'mañana', 'tomorrow']:
            date_obj = datetime.now() + timedelta(days=1)
        else:
            # Parsear fecha flexible
            date_obj = self._parse_flexible_date(user_input)
        
        return {
            'date': date_obj.strftime("%Y-%m-%d"),
            'display': date_obj.strftime("%d/%m/%Y")
        }
    
    def _parse_flexible_date(self, date_str: str) -> datetime:
        """
        Parsea fecha en múltiples formatos.
        
        Soporta:
        - DD/MM/YYYY → 25/01/2026
        - DD/MM/YY   → 25/01/26
        - DD/MM      → 25/01
        - DD         → 25
        
        Returns:
            datetime object
        
        Raises:
            ValueError si formato inválido
        """
        date_str = date_str.strip()
        today = datetime.now()
        
        # Separar por "/"
        parts = date_str.split('/')
        
        # ==========================================
        # FORMATO: DD/MM/YYYY o DD/MM/YY
        # ==========================================
        if len(parts) == 3:
            day, month, year = parts
            
            try:
                day = int(day)
                month = int(month)
                year = int(year)
                
                # Si año es corto (26), convertir a 2026
                if year < 100:
                    year += 2000
                
                # Validar rangos
                if not (1 <= month <= 12):
                    raise ValueError(f"Mes inválido: {month}. Debe estar entre 1 y 12.")
                
                if not (1 <= day <= 31):
                    raise ValueError(f"Día inválido: {day}. Debe estar entre 1 y 31.")
                
                # Intentar crear fecha
                date_obj = datetime(year, month, day)
                return date_obj
                
            except ValueError as e:
                if "day is out of range for month" in str(e):
                    raise ValueError(f"El mes {month} no tiene {day} días.")
                raise ValueError(f"Fecha inválida: {date_str}")
        
        # ==========================================
        # FORMATO: DD/MM (asume año)
        # ==========================================
        elif len(parts) == 2:
            day, month = parts
            
            try:
                day = int(day)
                month = int(month)
                
                # Validar rangos
                if not (1 <= month <= 12):
                    raise ValueError(f"Mes inválido: {month}")
                
                if not (1 <= day <= 31):
                    raise ValueError(f"Día inválido: {day}")
                
                # Intentar con año actual
                year = today.year
                try:
                    date_obj = datetime(year, month, day)
                    
                    # Si la fecha ya pasó, usar próximo año
                    if date_obj < today:
                        date_obj = datetime(year + 1, month, day)
                    
                    return date_obj
                    
                except ValueError as e:
                    if "day is out of range for month" in str(e):
                        raise ValueError(f"El mes {month} no tiene {day} días.")
                    raise
                    
            except ValueError as e:
                raise ValueError(f"Formato inválido: {date_str}. Usa DD/MM (ej: 25/01)")
        
        # ==========================================
        # FORMATO: DD (solo día, asume mes y año)
        # ==========================================
        elif len(parts) == 1:
            try:
                day = int(date_str)
                
                if not (1 <= day <= 31):
                    raise ValueError(f"Día inválido: {day}")
                
                # Intentar con mes y año actuales
                month = today.month
                year = today.year
                
                try:
                    date_obj = datetime(year, month, day)
                    
                    # Si la fecha ya pasó este mes
                    if date_obj < today:
                        # Intentar próximo mes
                        if month == 12:
                            month = 1
                            year += 1
                        else:
                            month += 1
                        
                        date_obj = datetime(year, month, day)
                    
                    return date_obj
                    
                except ValueError as e:
                    if "day is out of range for month" in str(e):
                        # El mes actual no tiene ese día, intentar siguiente mes
                        if month == 12:
                            month = 1
                            year += 1
                        else:
                            month += 1
                        
                        try:
                            date_obj = datetime(year, month, day)
                            return date_obj
                        except ValueError:
                            raise ValueError(f"Día {day} inválido para este mes y el siguiente.")
                    raise
                    
            except ValueError as e:
                raise ValueError(f"Día inválido: {date_str}. Debe ser un número entre 1 y 31.")
        
        else:
            raise ValueError(f"Formato no reconocido: {date_str}")
        
    def _get_format_help(self) -> str:
        """Mensaje de ayuda con formatos aceptados."""
        return """💡 *Formatos válidos:*

• **Completo:** 25/01/2026
• **Año corto:** 25/01/26
• **Sin año:** 25/01 (asume este o próximo año)
• **Solo día:** 25 (asume este mes o siguiente)

O selecciona:
1️⃣ Hoy
2️⃣ Mañana"""
    
    def convert_to_db_param(self, processed_value: Dict) -> Dict:
        """Convierte a parámetros de BD."""
        return {
            'date_str': processed_value['date']
        }
    
    def get_display_text(self, processed_value: Dict) -> str:
        """Texto para mostrar en el menú."""
        return processed_value['display']
    
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
    
    def validate_input(self, user_input: str, session_data: Dict = None) -> Tuple[bool, str]:
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
    
    def process_input(self, user_input: str, session_data: Dict = None) -> Dict:
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