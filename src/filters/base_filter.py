"""
Clase base abstracta para el sistema de filtros.

Define la interfaz común que deben implementar todos los filtros concretos,
garantizando consistencia en la validación, procesamiento y presentación.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Optional
from .filter_types import FilterType, FilterCategory, FilterPriority


class BaseFilter(ABC):
    """
    Clase base abstracta para todos los filtros del sistema.
    
    Cada filtro concreto (DateFilter, ZoneFilter, etc.) debe heredar de esta
    clase e implementar todos los métodos abstractos.
    
    Atributos:
        filter_type: Tipo específico del filtro (DATE, ZONE, etc.)
        category: Categoría del filtro (CORE, OPTIONAL, ADVANCED)
        priority: Prioridad del filtro (REQUIRED, RECOMMENDED, OPTIONAL)
        display_name: Nombre legible para mostrar al usuario
        emoji: Emoji opcional para mejorar la presentación visual
    """
    
    def __init__(
        self,
        filter_type: FilterType,
        category: FilterCategory,
        priority: FilterPriority,
        display_name: str,
        emoji: str = ""
    ):
        """
        Inicializa un filtro con sus propiedades básicas.
        
        Args:
            filter_type: Tipo del filtro (ej: FilterType.DATE)
            category: Categoría (ej: FilterCategory.CORE)
            priority: Prioridad (ej: FilterPriority.REQUIRED)
            display_name: Nombre para mostrar (ej: "Fecha y Horario")
            emoji: Emoji decorativo (ej: "📅")
        """
        self.filter_type = filter_type
        self.category = category
        self.priority = priority
        self.display_name = display_name
        self.emoji = emoji
    
    @abstractmethod
    def get_menu_option_text(self, is_active: bool = False) -> str:
        """
        Genera el texto de la opción en el menú de filtros.
        
        Args:
            is_active: Indica si el filtro ya está aplicado/seleccionado
        
        Returns:
            Texto formateado para mostrar en el menú
            
        Ejemplo:
            "📅 Fecha y Horario" (sin aplicar)
            "📅 Fecha y Horario ✓" (aplicado)
        """
        pass
    
    @abstractmethod
    def get_input_prompt(self, session_data: dict) -> str:
        """
        Genera el mensaje que se muestra al usuario cuando selecciona este filtro.
        
        Este mensaje debe incluir:
        - Instrucciones claras de qué ingresar
        - Opciones disponibles (si aplica)
        - Formato esperado
        - Opción de volver (0)
        
        Args:
            session_data: Datos de la sesión actual (puede contener filtros previos)
        
        Returns:
            Mensaje completo con instrucciones y opciones
            
        Ejemplo:
            "📅 Selecciona la fecha:\n"
            "1️⃣ Hoy\n"
            "2️⃣ Mañana\n"
            "0️⃣ Volver al menú de filtros"
        """
        pass
    
    @abstractmethod
    def validate_input(self, user_input: str, session_data: dict = None) -> Tuple[bool, Optional[str]]:
        """
        Valida que el input del usuario sea correcto para este filtro.
        
        Debe verificar:
        - Formato correcto
        - Valores dentro de rangos permitidos
        - Opciones válidas
        
        Args:
            user_input: Texto ingresado por el usuario
            session_data: Datos de sesión (opcional, para validaciones contextuales)
        
        Returns:
            Tupla (es_valido, mensaje_error)
            - Si es válido: (True, None)
            - Si es inválido: (False, "Mensaje explicando el error")
            
        Ejemplo:
            (True, None) → Input válido
            (False, "❌ Opción inválida. Ingresa un número del 1 al 5") → Input inválido
        """
        pass
    
    @abstractmethod
    def process_input(self, user_input: str, session_data: dict = None) -> Dict:
        """
        Procesa el input válido y lo convierte al formato requerido.
        
        Este método se llama SOLO si validate_input() retornó True.
        Debe convertir el input del usuario en la estructura de datos
        que se guardará en session.temp['filters'].
        
        Args:
            user_input: Input del usuario (ya validado)
            session_data: Datos de sesión (opcional)
        
        Returns:
            Diccionario con el filtro procesado y listo para guardar
            
        Ejemplo para DateFilter:
            Input: "1" (Hoy)
            Output: {
                'display': 'Hoy - 19/01/2026',
                'date': '2026-01-19',
                'date_obj': datetime(2026, 1, 19)
            }
        """
        pass
    
    @abstractmethod
    def convert_to_db_param(self, processed_data: Dict) -> Dict:
        """
        Convierte el filtro procesado a parámetros de base de datos.
        
        Transforma la estructura guardada en session.temp['filters']
        al formato que espera la consulta a la base de datos.
        
        Args:
            processed_data: Datos del filtro (retornados por process_input)
        
        Returns:
            Diccionario con parámetros para la consulta de BD
            
        Ejemplo para DateFilter:
            Input: {'date': '2026-01-19', ...}
            Output: {'fecha': '2026-01-19'}
        """
        pass
    
    def get_summary(self, processed_data: Dict) -> str:
        """
        Genera un resumen legible del filtro aplicado.
        
        Este método tiene una implementación por defecto que usa
        el campo 'display' si existe, pero puede ser sobrescrito.
        
        Args:
            processed_data: Datos del filtro procesado
        
        Returns:
            Texto resumen del filtro
            
        Ejemplo:
            "📅 Hoy - 19/01/2026"
            "📍 Zona Norte"
        """
        if 'display' in processed_data:
            return f"{self.emoji} {processed_data['display']}"
        return f"{self.emoji} {self.display_name}"