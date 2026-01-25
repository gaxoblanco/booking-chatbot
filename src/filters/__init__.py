"""
Módulo principal del sistema de filtros.

Exporta los componentes principales para uso en otros módulos.
"""

from .filter_types import FilterType, FilterCategory, FilterPriority
from .base_filter import BaseFilter
from .filter_manager import FilterManager

__all__ = [
    'FilterType',
    'FilterCategory',
    'FilterPriority',
    'BaseFilter',
    'FilterManager',
]