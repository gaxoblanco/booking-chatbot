"""
Tipos y enumeraciones para el sistema de filtros.

Este módulo define las estructuras de datos fundamentales que clasifican
y organizan los diferentes tipos de filtros disponibles en el sistema.
"""

from enum import Enum


class FilterType(Enum):
    """
    Tipos de filtros disponibles en el sistema.
    
    Cada tipo representa un criterio de búsqueda específico que puede
    aplicarse para filtrar profesionales.
    """
    DATE = "date"                    # Filtro por fecha de turno
    TIME = "time"                    # Filtro por horario
    SPECIALTY = "specialty"          # Filtro por especialidad médica
    ZONE = "zone"                    # Filtro por zona geográfica
    PREPAGA = "prepaga"              # Filtro por obra social/prepaga
    GENDER = "gender"                # Filtro por sexo del profesional
    MODALITY = "modality"            # Filtro por modalidad (presencial/virtual)
    PROFESSIONAL = "professional"    # Filtro por nombre del profesional
    BRANCH = "branch"                # Filtro por sucursal


class FilterCategory(Enum):
    """
    Categorías que agrupan filtros según su importancia.
    
    - CORE: Filtros esenciales para el funcionamiento básico
    - OPTIONAL: Filtros adicionales que mejoran la búsqueda
    - ADVANCED: Filtros para casos de uso avanzados (futuro)
    """
    CORE = "core"           # Filtros esenciales/obligatorios
    OPTIONAL = "optional"   # Filtros opcionales/configurables
    ADVANCED = "advanced"   # Filtros avanzados (reservado para futuro)


class FilterPriority(Enum):
    """
    Prioridad de los filtros en el menú y validación.
    
    Define qué tan importante es que el usuario complete un filtro
    antes de realizar la búsqueda.
    """
    REQUIRED = 1      # Debe completarse obligatoriamente
    RECOMMENDED = 2   # Recomendado pero no obligatorio
    OPTIONAL = 3      # Completamente opcional