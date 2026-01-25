"""
Filtros OPCIONALES del sistema.

Estos filtros complementan la búsqueda principal permitiendo refinar
los resultados según preferencias adicionales del cliente.
"""

from typing import Dict, List, Tuple, Optional
import sys
import os

# Agregar el directorio raíz al path para imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from filters.base_filter import BaseFilter
from filters.filter_types import FilterType, FilterCategory, FilterPriority


class ZoneFilter(BaseFilter):
    """
    Filtro de zona geográfica.
    
    Permite al cliente seleccionar la zona donde prefiere atención.
    Las zonas disponibles son configurables según el proyecto.
    """
    
    def __init__(self):
        super().__init__(
            filter_type=FilterType.ZONE,
            category=FilterCategory.OPTIONAL,
            priority=FilterPriority.RECOMMENDED,
            display_name="Zona",
            emoji="📍"
        )
    
    def get_menu_option_text(self, is_active: bool = False, active_value: Dict = None) -> str:
        """Texto para el menú principal de filtros."""
        if is_active and active_value:
            display = active_value.get('display', '')
            return f"{self.emoji} Zona: {display}"
        return f"{self.emoji} Zona"
    
    def get_input_prompt(self, session_data: dict) -> str:
        """Mensaje que se muestra al seleccionar este filtro."""
        return """📍 *Selecciona la zona*

¿En qué zona prefieres atención?

1️⃣ Zona Norte
2️⃣ Zona Sur
3️⃣ Cualquier zona (sin filtro)

0️⃣ Volver al menú de filtros"""
    
    def validate_input(self, user_input: str, session_data: dict = None) -> Tuple[bool, Optional[str]]:
        """
        Valida la selección de zona.
        
        Acepta opciones 1, 2 o 3.
        """
        if user_input in ['1', '2', '3']:
            return (True, None)
        
        return (False, "❌ Opción inválida. Selecciona 1, 2 o 3")
    
    def process_input(self, user_input: str, session_data: dict = None) -> Dict:
        """
        Procesa la selección de zona.
        
        Returns:
            {
                'display': 'Zona Norte',
                'zone': 'norte',
                'remove': False
            }
            
            Si el usuario selecciona "Cualquier zona", se marca para remover.
        """
        if user_input == '1':
            return {
                'display': 'Norte',
                'zone': 'norte',
                'remove': False
            }
        elif user_input == '2':
            return {
                'display': 'Sur',
                'zone': 'sur',
                'remove': False
            }
        else:  # user_input == '3'
            # Marcar para remover el filtro
            return {
                'display': 'Cualquier zona',
                'zone': None,
                'remove': True
            }
    
    def convert_to_db_param(self, processed_data: Dict) -> Dict:
        """
        Convierte a parámetro de base de datos.
        
        Returns:
            {'zone': 'norte'} o {} si se removió el filtro
        """
        if processed_data.get('remove'):
            return {}
        
        return {
            'zone': processed_data['zone']
        }


class PrepagaFilter(BaseFilter):
    """
    Filtro de obra social/prepaga.
    
    Permite filtrar profesionales según si aceptan o no obra social/prepaga.
    """
    
    def __init__(self):
        super().__init__(
            filter_type=FilterType.PREPAGA,
            category=FilterCategory.OPTIONAL,
            priority=FilterPriority.OPTIONAL,
            display_name="Obra Social/Prepaga",
            emoji="💳"
        )
    
    def get_menu_option_text(self, is_active: bool = False, active_value: Dict = None) -> str:
        """Texto para el menú principal de filtros."""
        if is_active and active_value:
            display = active_value.get('display', '')
            return f"{self.emoji} Prepaga: {display}"
        return f"{self.emoji} Prepaga"
    
    def get_input_prompt(self, session_data: dict) -> str:
        """Mensaje que se muestra al seleccionar este filtro."""
        return """💳 *¿Acepta obra social/prepaga?*

¿Necesitas que acepte obra social?

1️⃣ Sí, debe aceptar prepaga
2️⃣ No, prefiero particular
3️⃣ No importa (sin filtro)

0️⃣ Volver al menú de filtros"""
    
    def validate_input(self, user_input: str, session_data: dict = None) -> Tuple[bool, Optional[str]]:
        """Valida la selección de prepaga."""
        if user_input in ['1', '2', '3']:
            return (True, None)
        
        return (False, "❌ Opción inválida. Selecciona 1, 2 o 3")
    
    def process_input(self, user_input: str, session_data: dict = None) -> Dict:
        """
        Procesa la selección de prepaga.
        
        Returns:
            {
                'display': 'Sí',
                'prepaga': True,
                'remove': False
            }
        """
        if user_input == '1':
            return {
                'display': 'Sí',
                'prepaga': True,
                'remove': False
            }
        elif user_input == '2':
            return {
                'display': 'No',
                'prepaga': False,
                'remove': False
            }
        else:  # user_input == '3'
            return {
                'display': 'Cualquiera',
                'prepaga': None,
                'remove': True
            }
    
    def convert_to_db_param(self, processed_data: Dict) -> Dict:
        """
        Convierte a parámetro de base de datos.
        
        Returns:
            {'accept_prepaga': True} o {} si se removió
        """
        if processed_data.get('remove'):
            return {}
        
        return {
            'accept_prepaga': processed_data['prepaga']
        }


class GenderFilter(BaseFilter):
    """
    Filtro de género del profesional.
    
    Permite al cliente seleccionar el género del profesional que prefiere.
    """
    
    def __init__(self):
        super().__init__(
            filter_type=FilterType.GENDER,
            category=FilterCategory.OPTIONAL,
            priority=FilterPriority.OPTIONAL,
            display_name="Género del Profesional",
            emoji="👤"
        )
    
    def get_menu_option_text(self, is_active: bool = False, active_value: Dict = None) -> str:
        """Texto para el menú principal de filtros."""
        if is_active and active_value:
            display = active_value.get('display', '')
            return f"{self.emoji} Género: {display}"
        return f"{self.emoji} Género"
    
    def get_input_prompt(self, session_data: dict) -> str:
        """Mensaje que se muestra al seleccionar este filtro."""
        return """👤 *Género del profesional*

¿Tienes preferencia por el género del profesional?

1️⃣ Masculino
2️⃣ Femenino
3️⃣ No importa (sin filtro)

0️⃣ Volver al menú de filtros"""
    
    def validate_input(self, user_input: str, session_data: dict = None) -> Tuple[bool, Optional[str]]:
        """Valida la selección de género."""
        if user_input in ['1', '2', '3']:
            return (True, None)
        
        return (False, "❌ Opción inválida. Selecciona 1, 2 o 3")
    
    def process_input(self, user_input: str, session_data: dict = None) -> Dict:
        """
        Procesa la selección de género.
        
        Returns:
            {
                'display': 'Masculino',
                'gender': 'm',
                'remove': False
            }
        """
        if user_input == '1':
            return {
                'display': 'Masculino',
                'gender': 'm',
                'remove': False
            }
        elif user_input == '2':
            return {
                'display': 'Femenino',
                'gender': 'f',
                'remove': False
            }
        else:  # user_input == '3'
            return {
                'display': 'Cualquiera',
                'gender': None,
                'remove': True
            }
    
    def convert_to_db_param(self, processed_data: Dict) -> Dict:
        """
        Convierte a parámetro de base de datos.
        
        Returns:
            {'gender': 'm'} o {} si se removió
        """
        if processed_data.get('remove'):
            return {}
        
        return {
            'gender': processed_data['gender']
        }


class ModalityFilter(BaseFilter):
    """
    Filtro de modalidad de atención.
    
    Permite seleccionar entre atención presencial, virtual o ambas.
    """
    
    def __init__(self):
        super().__init__(
            filter_type=FilterType.MODALITY,
            category=FilterCategory.OPTIONAL,
            priority=FilterPriority.OPTIONAL,
            display_name="Modalidad",
            emoji="💻"
        )
    
    def get_menu_option_text(self, is_active: bool = False, active_value: Dict = None) -> str:
        """Texto para el menú principal de filtros."""
        if is_active and active_value:
            display = active_value.get('display', '')
            return f"{self.emoji} Modalidad: {display}"
        return f"{self.emoji} Modalidad"
    
    def get_input_prompt(self, session_data: dict) -> str:
        """Mensaje que se muestra al seleccionar este filtro."""
        return """💻 *Modalidad de atención*

¿Qué modalidad prefieres?

1️⃣ Presencial
2️⃣ Virtual (videollamada)
3️⃣ Cualquier modalidad (sin filtro)

0️⃣ Volver al menú de filtros"""
    
    def validate_input(self, user_input: str, session_data: dict = None) -> Tuple[bool, Optional[str]]:
        """Valida la selección de modalidad."""
        if user_input in ['1', '2', '3']:
            return (True, None)
        
        return (False, "❌ Opción inválida. Selecciona 1, 2 o 3")
    
    def process_input(self, user_input: str, session_data: dict = None) -> Dict:
        """
        Procesa la selección de modalidad.
        
        Returns:
            {
                'display': 'Presencial',
                'modality': 'presencial',
                'remove': False
            }
        """
        if user_input == '1':
            return {
                'display': 'Presencial',
                'modality': 'presencial',
                'remove': False
            }
        elif user_input == '2':
            return {
                'display': 'Virtual',
                'modality': 'virtual',
                'remove': False
            }
        else:  # user_input == '3'
            return {
                'display': 'Cualquiera',
                'modality': None,
                'remove': True
            }
    
    def convert_to_db_param(self, processed_data: Dict) -> Dict:
        """
        Convierte a parámetro de base de datos.
        
        Returns:
            {'modality': 'presencial'} o {} si se removió
        """
        if processed_data.get('remove'):
            return {}
        
        return {
            'modality': processed_data['modality']
        }