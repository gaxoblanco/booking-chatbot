"""
Gestor Central del Sistema de Filtros.

El FilterManager es el cerebro del sistema. Se encarga de:
- Cargar y gestionar todos los filtros disponibles
- Generar menús dinámicos
- Validar filtros obligatorios
- Convertir filtros a parámetros de base de datos
- Coordinar el flujo de filtrado

Este es el ÚNICO punto de entrada que necesita client_handler.py
"""

from typing import Dict, List, Optional, Tuple
import sys
import os

# Agregar el directorio raíz al path para imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from filters.filter_types import FilterType, FilterCategory, FilterPriority
from filters.base_filter import BaseFilter
from filters.concrete_filters import (
    DateFilter,
    TimeFilter,
    SpecialtyFilter,
    ZoneFilter,
    PrepagaFilter,
    GenderFilter,
    ModalityFilter,
)
from config.domain_filters_config import (
    ENABLED_FILTERS,
    REQUIRED_FILTERS,
    FILTER_MESSAGES,
    VALIDATION_CONFIG,
    ACTIVE_FILTERS_DISPLAY_ORDER,
    get_enabled_filters,
    get_filters_by_category,
    get_required_filters,
)


class FilterManager:
    """
    Gestor central del sistema de filtros.
    
    Responsabilidades:
    - Inicializar filtros habilitados desde la configuración
    - Generar menús dinámicos
    - Validar inputs
    - Coordinar el procesamiento de filtros
    - Convertir a parámetros de BD
    
    Uso básico:
        manager = FilterManager()
        menu = manager.generate_menu(active_filters={})
        filter_obj = manager.get_filter(FilterType.DATE)
    """
    
    def __init__(self):
        """
        Inicializa el FilterManager.
        
        Carga todos los filtros disponibles y aplica la configuración
        de domain_filters_config.py para determinar cuáles están habilitados.
        """
        print(f"\n{'='*60}")
        print(f"🔧 DEBUG FilterManager.__init__")
        print(f"{'='*60}")
        
        # Registro de TODOS los filtros disponibles (implementados)
        print(f"📦 Creating all available filters...")
        self._all_filters = {
            FilterType.DATE: DateFilter(),
            FilterType.TIME: TimeFilter(),
            FilterType.SPECIALTY: SpecialtyFilter(),
            FilterType.ZONE: ZoneFilter(),
            FilterType.PREPAGA: PrepagaFilter(),
            FilterType.GENDER: GenderFilter(),
            FilterType.MODALITY: ModalityFilter(),
            # Agregar aquí nuevos filtros cuando se implementen
        }
        print(f"✅ Created {len(self._all_filters)} filter types:")
        for ft, fo in self._all_filters.items():
            print(f"   • {ft.value}: {fo.__class__.__name__}")
        
        # Filtros habilitados según configuración
        print(f"\n📋 Loading enabled filters from config...")
        self._enabled_filters = self._load_enabled_filters()
        print(f"✅ Loaded {len(self._enabled_filters)} enabled filters:")
        for ft in self._enabled_filters.keys():
            print(f"   • {ft.value}")
        
        # Filtros obligatorios
        print(f"\n📋 Loading required filters...")
        self._required_filters = get_required_filters()
        print(f"✅ Required filters: {[ft.value for ft in self._required_filters]}")
        
        print(f"{'='*60}\n")

    
    def _load_enabled_filters(self) -> Dict[FilterType, BaseFilter]:
        """
        Carga solo los filtros que están habilitados en la configuración.
        
        Returns:
            dict: {FilterType: BaseFilter} solo con filtros enabled=True
        """
        print(f"\n🔍 DEBUG _load_enabled_filters")
        print(f"="*60)
        
        enabled_config = get_enabled_filters()
        print(f"📦 got enabled_config type: {type(enabled_config)}")
        print(f"📦 enabled_config: {enabled_config}")
        
        enabled = {}
        for filter_type, config in enabled_config.items():
            # print(f"\n  Processing filter:")
            # print(f"    • filter_type: {filter_type}")
            # print(f"    • filter_type type: {type(filter_type)}")
            # print(f"    • filter_type value: {filter_type.value if hasattr(filter_type, 'value') else 'N/A'}")
            # print(f"    • config: {config}")
            
            if filter_type in self._all_filters:
                # print(f"    ✅ Found in _all_filters")
                # Agregar el filtro con su configuración
                filter_obj = self._all_filters[filter_type]
                # print(f"    ✅ Filter object: {filter_obj.__class__.__name__}")
                
                # LA CLAVE IMPORTANTE: verificar el tipo de la key
                # print(f"    💾 Storing with key type: {type(filter_type)}")
                # print(f"    💾 Key value: {filter_type}")
                
                enabled[filter_type] = filter_obj
                
                # Verificar que se guardó
                # print(f"    ✅ Stored! Dict now has {len(enabled)} items")
            else:
                print(f"    ❌ NOT found in _all_filters!")
                print(f"    📊 Available keys in _all_filters:")
                for k in self._all_filters.keys():
                    print(f"       • {k} (type: {type(k)})")
        
        # print(f"\n✅ Final enabled dict:")
        # print(f"   • Length: {len(enabled)}")
        # print(f"   • Keys: {list(enabled.keys())}")
        # print(f"   • Key types: {[type(k) for k in enabled.keys()]}")
        # print(f"="*60)
        
        return enabled
    
    def get_filter(self, filter_type: FilterType) -> Optional[BaseFilter]:
        """
        Obtiene un filtro específico si está habilitado.
        
        Args:
            filter_type: Tipo de filtro (ej: FilterType.DATE)
        
        Returns:
            BaseFilter o None si no está habilitado
        """
        # Comparar por .value para evitar problemas de identidad de Enum
        for key, value in self._enabled_filters.items():
            if key.value == filter_type.value:
                return value
        
        return None

    
    def get_filter_by_menu_number(self, menu_number: int) -> Optional[BaseFilter]:
        """
        Obtiene un filtro por su número en el menú.
        
        Args:
            menu_number: Número del menú (1, 2, 3, etc.)
        
        Returns:
            BaseFilter o None si no existe ese número
        """
        # Obtener filtros ordenados por menu_position
        ordered = self._get_ordered_filters()
        
        # El índice en la lista es menu_number - 1
        if 0 < menu_number <= len(ordered):
            return ordered[menu_number - 1]
        
        return None
    
    def _get_ordered_filters(self) -> List[BaseFilter]:
        """
        Retorna los filtros habilitados ordenados por menu_position.
        
        Returns:
            Lista de BaseFilter ordenada
        """
        enabled_config = get_enabled_filters()
        
        # Crear lista de tuplas (menu_position, filter_obj)
        filters_with_position = []
        for filter_type, filter_obj in self._enabled_filters.items():
            position = enabled_config[filter_type].get('menu_position', 999)
            filters_with_position.append((position, filter_obj))
        
        # Ordenar por position
        filters_with_position.sort(key=lambda x: x[0])
        
        # Retornar solo los filtros
        return [f[1] for f in filters_with_position]
    
    def generate_menu(self, active_filters: Dict[str, Dict]) -> str:
        """
        Genera el menú completo de filtros con checkmarks en filtros activos.
        
        Args:
            active_filters: Filtros actualmente activos desde session.temp['filters']
                           Formato: {'date': {...}, 'zone': {...}}
        
        Returns:
            String con el menú formateado
        
        Ejemplo de output:
            🔍 BUSCAR PROFESIONAL
            
            ━━━━ FILTROS PRINCIPALES ━━━━
            1️⃣ 📅 Fecha ✓
            2️⃣ 🕐 Horario
            3️⃣ 🩺 Especialidad
            
            ━━━━ FILTROS ADICIONALES ━━━━
            4️⃣ 📍 Zona ✓
            5️⃣ 💳 Prepaga
            
            ✅ Filtros activos:
            • Fecha: Hoy - 19/01/2026
            • Zona: Norte
            
            9️⃣ 🔍 Buscar con estos filtros
            0️⃣ ⬅️ Volver
        """
        menu_parts = []
        
        # Header
        menu_parts.append(FILTER_MESSAGES['menu_header'])
        
        # Separar filtros por categoría
        core_filters = self._get_filters_by_category(FilterCategory.CORE)
        optional_filters = self._get_filters_by_category(FilterCategory.OPTIONAL)
        
        # Sección de filtros CORE
        if core_filters:
            menu_parts.append(FILTER_MESSAGES['core_section_title'])
            for idx, filter_obj in enumerate(core_filters, start=1):
                filter_key = filter_obj.filter_type.value
                is_active = filter_key in active_filters
                active_value = active_filters.get(filter_key) if is_active else None
                option_text = filter_obj.get_menu_option_text(is_active, active_value)
                menu_parts.append(f"{idx}️⃣ {option_text}")

        # Sección de filtros OPCIONALES
        if optional_filters:
            menu_parts.append(FILTER_MESSAGES['optional_section_title'])
            start_num = len(core_filters) + 1
            for idx, filter_obj in enumerate(optional_filters, start=start_num):
                filter_key = filter_obj.filter_type.value
                is_active = filter_key in active_filters
                active_value = active_filters.get(filter_key) if is_active else None
                option_text = filter_obj.get_menu_option_text(is_active, active_value)
                menu_parts.append(f"{idx}️⃣ {option_text}")
        
        # Mostrar filtros activos
        if active_filters:
            menu_parts.append(FILTER_MESSAGES['active_filters_header'])
            for filter_summary in self._format_active_filters(active_filters):
                menu_parts.append(f"• {filter_summary}")
        else:
            menu_parts.append(f"\n✅ *Filtros activos:* {FILTER_MESSAGES['no_filters_active']}")
        
        # Acciones
        menu_parts.append(FILTER_MESSAGES['search_action'])
        menu_parts.append(FILTER_MESSAGES['back_action'])
        
        return "\n".join(menu_parts)
    
    def _get_filters_by_category(self, category: FilterCategory) -> List[BaseFilter]:
        """
        Obtiene filtros habilitados de una categoría específica, ordenados.
        
        Args:
            category: FilterCategory.CORE o FilterCategory.OPTIONAL
        
        Returns:
            Lista ordenada de BaseFilter de esa categoría
        """
        enabled_config = get_enabled_filters()
        
        # Filtrar por categoría
        filters_of_category = []
        for filter_type, filter_obj in self._enabled_filters.items():
            if enabled_config[filter_type].get('category') == category:
                position = enabled_config[filter_type].get('menu_position', 999)
                filters_of_category.append((position, filter_obj))
        
        # Ordenar por position
        filters_of_category.sort(key=lambda x: x[0])
        
        return [f[1] for f in filters_of_category]
    
    def _format_active_filters(self, active_filters: Dict[str, Dict]) -> List[str]:
        """
        Formatea los filtros activos para mostrar en el menú.
        
        Args:
            active_filters: Filtros activos desde session
        
        Returns:
            Lista de strings con los filtros formateados
            
        Ejemplo:
            ['📅 Hoy - 19/01/2026', '📍 Zona Norte']
        """
        summaries = []
        
        # Ordenar según ACTIVE_FILTERS_DISPLAY_ORDER
        ordered_types = [
            ft for ft in ACTIVE_FILTERS_DISPLAY_ORDER 
            if ft.value in active_filters
        ]
        
        # Agregar filtros que no están en el orden (al final)
        for filter_key in active_filters.keys():
            filter_type = FilterType(filter_key)
            if filter_type not in ordered_types:
                ordered_types.append(filter_type)
        
        # Generar summaries
        for filter_type in ordered_types:
            filter_obj = self.get_filter(filter_type)
            if filter_obj:
                filter_data = active_filters[filter_type.value]
                summary = filter_obj.get_summary(filter_data)
                summaries.append(summary)
        
        return summaries
    
    def validate_required_filters(self, active_filters: Dict[str, Dict]) -> Tuple[bool, Optional[str]]:
        """
        Valida que todos los filtros obligatorios estén presentes.
        
        Args:
            active_filters: Filtros activos desde session
        
        Returns:
            (es_valido, mensaje_error)
            - Si es válido: (True, None)
            - Si faltan filtros: (False, mensaje con filtros faltantes)
        """
        if not VALIDATION_CONFIG.get('enforce_required_filters', True):
            return (True, None)
        
        missing = []
        for filter_type in self._required_filters:
            if filter_type.value not in active_filters:
                filter_obj = self.get_filter(filter_type)
                if filter_obj:
                    missing.append(f"• {filter_obj.emoji} {filter_obj.display_name}")
        
        if missing:
            missing_text = "\n".join(missing)
            error_msg = FILTER_MESSAGES['missing_required'].format(
                missing_filters=missing_text
            )
            return (False, error_msg)
        
        return (True, None)
    
    def validate_minimum_filters(self, active_filters: Dict[str, Dict]) -> Tuple[bool, Optional[str]]:
        """
        Valida que haya al menos 1 filtro activo (opcional).
        
        Args:
            active_filters: Filtros activos desde session
        
        Returns:
            (es_valido, mensaje_warning)
        """
        if not active_filters and not VALIDATION_CONFIG.get('allow_empty_search', False):
            return (False, "⚠️ Debes seleccionar al menos 1 filtro antes de buscar.")
        
        if len(active_filters) == 1 and VALIDATION_CONFIG.get('warn_single_filter', False):
            return (False, VALIDATION_CONFIG.get('single_filter_warning'))
        
        return (True, None)
    
    def convert_to_db_params(self, active_filters: Dict[str, Dict]) -> Dict:
        """
        Convierte todos los filtros activos a parámetros de base de datos.
        
        Args:
            active_filters: Filtros activos desde session.temp['filters']
                           Formato: {'date': {...}, 'zone': {...}}
        
        Returns:
            Diccionario con parámetros para la consulta de BD
            
        Ejemplo:
            Input: {
                'date': {'date': '2026-01-19', ...},
                'zone': {'zone': 'norte', ...}
            }
            Output: {
                'available_date': '2026-01-19',
                'zone': 'norte'
            }
        """
        db_params = {}
        
        for filter_key, filter_data in active_filters.items():
            # Obtener el filtro correspondiente
            filter_type = FilterType(filter_key)
            filter_obj = self.get_filter(filter_type)
            
            if filter_obj:
                # Convertir usando el método del filtro
                params = filter_obj.convert_to_db_param(filter_data)
                db_params.update(params)
        
        return db_params
    
    def process_filter_removal(self, active_filters: Dict[str, Dict], filter_type: FilterType) -> Dict[str, Dict]:
        """
        Procesa la remoción de un filtro si tiene flag 'remove'.
        
        Algunos filtros (como Zone con opción "Cualquier zona") pueden
        marcarse para ser removidos. Este método los elimina del dict.
        
        Args:
            active_filters: Filtros activos actuales
            filter_type: Tipo de filtro a verificar
        
        Returns:
            Diccionario actualizado sin el filtro si tenía 'remove': True
        """
        filter_key = filter_type.value
        
        if filter_key in active_filters:
            filter_data = active_filters[filter_key]
            if filter_data.get('remove'):
                # Crear copia sin este filtro
                updated = active_filters.copy()
                del updated[filter_key]
                return updated
        
        return active_filters
    
    def get_total_enabled_filters(self) -> int:
        """
        Retorna el número total de filtros habilitados.
        
        Returns:
            int: Cantidad de filtros habilitados
        """
        return len(self._enabled_filters)
    
    def get_filter_statistics(self, active_filters: Dict[str, Dict]) -> Dict:
        """
        Genera estadísticas sobre los filtros activos.
        
        Útil para analytics y debugging.
        
        Args:
            active_filters: Filtros activos
        
        Returns:
            dict con estadísticas
        """
        total_enabled = self.get_total_enabled_filters()
        total_active = len(active_filters)
        required_count = len(self._required_filters)
        required_active = sum(
            1 for ft in self._required_filters 
            if ft.value in active_filters
        )
        
        return {
            'total_enabled': total_enabled,
            'total_active': total_active,
            'completion_rate': (total_active / total_enabled * 100) if total_enabled > 0 else 0,
            'required_count': required_count,
            'required_active': required_active,
            'required_complete': required_active == required_count,
        }