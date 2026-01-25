"""
Configuración de filtros para el dominio actual.

Este archivo permite habilitar/deshabilitar filtros y definir su orden
SIN necesidad de modificar código. Es el único archivo que debes editar
para personalizar los filtros de tu proyecto.

INSTRUCCIONES DE USO:
=====================

1. Para HABILITAR un filtro:
   - Agrégalo a ENABLED_FILTERS con enabled=True

2. Para DESHABILITAR un filtro:
   - Cambia enabled=False o elimínalo de ENABLED_FILTERS

3. Para CAMBIAR EL ORDEN en el menú:
   - Modifica el número en 'menu_position'
   - Los números más bajos aparecen primero

4. Para hacer un filtro OBLIGATORIO:
   - Agrégalo a REQUIRED_FILTERS

5. Para cambiar MENSAJES:
   - Edita los textos en FILTER_MESSAGES

EJEMPLO DE CONFIGURACIÓN:
========================

# Proyecto de Psicólogos:
ENABLED_FILTERS = {
    FilterType.DATE: {...},
    FilterType.TIME: {...},
    FilterType.SPECIALTY: {...},
    FilterType.ZONE: {...},
}

# Proyecto de Médicos Generales (sin especialidad):
ENABLED_FILTERS = {
    FilterType.DATE: {...},
    FilterType.TIME: {...},
    FilterType.ZONE: {...},
    FilterType.PREPAGA: {...},
}
"""

from filters.filter_types import FilterType, FilterCategory, FilterPriority


# ============================================================================
# CONFIGURACIÓN DE FILTROS HABILITADOS
# ============================================================================

ENABLED_FILTERS = {
    # ===== FILTROS CORE (ESENCIALES) =====
    
    FilterType.DATE: {
        'enabled': True,
        'menu_position': 1,  # Aparece primero en el menú
        'category': FilterCategory.CORE,
        'priority': FilterPriority.REQUIRED,  # Obligatorio
    },
    
    FilterType.TIME: {
        'enabled': True,
        'menu_position': 2,  # Aparece segundo
        'category': FilterCategory.CORE,
        'priority': FilterPriority.RECOMMENDED,  # Recomendado pero no obligatorio
    },
    
    FilterType.SPECIALTY: {
        'enabled': True,
        'menu_position': 3,
        'category': FilterCategory.CORE,
        'priority': FilterPriority.RECOMMENDED,
    },
    
    # ===== FILTROS OPCIONALES =====
    
    FilterType.ZONE: {
        'enabled': True,
        'menu_position': 4,
        'category': FilterCategory.OPTIONAL,
        'priority': FilterPriority.OPTIONAL,
    },
    
    FilterType.PREPAGA: {
        'enabled': True,
        'menu_position': 5,
        'category': FilterCategory.OPTIONAL,
        'priority': FilterPriority.OPTIONAL,
    },
    
    FilterType.GENDER: {
        'enabled': True,
        'menu_position': 6,
        'category': FilterCategory.OPTIONAL,
        'priority': FilterPriority.OPTIONAL,
    },
    
    FilterType.MODALITY: {
        'enabled': False,  # ⚠️ DESHABILITADO - Cambiar a True para habilitar
        'menu_position': 7,
        'category': FilterCategory.OPTIONAL,
        'priority': FilterPriority.OPTIONAL,
    },
    
    # ===== FILTROS FUTUROS (DESHABILITADOS) =====
    # Descomenta y habilita cuando estén implementados
    
    # FilterType.PROFESSIONAL: {
    #     'enabled': False,
    #     'menu_position': 8,
    #     'category': FilterCategory.OPTIONAL,
    #     'priority': FilterPriority.OPTIONAL,
    # },
    
    # FilterType.BRANCH: {
    #     'enabled': False,
    #     'menu_position': 9,
    #     'category': FilterCategory.OPTIONAL,
    #     'priority': FilterPriority.OPTIONAL,
    # },
}


# ============================================================================
# FILTROS OBLIGATORIOS
# ============================================================================
# Filtros que DEBEN completarse antes de permitir la búsqueda.
# Si el usuario intenta buscar sin estos filtros, se mostrará un error.

REQUIRED_FILTERS = [
    FilterType.DATE,  # La fecha es obligatoria
    # FilterType.SPECIALTY,  # Descomenta si quieres que especialidad sea obligatoria
]


# ============================================================================
# MENSAJES PERSONALIZABLES
# ============================================================================

FILTER_MESSAGES = {
    # Mensaje del encabezado del menú
    'menu_header': """🔍 *BUSCAR PROFESIONAL*

Selecciona los filtros que deseas aplicar:
""",
    
    # Separador entre filtros CORE y OPCIONALES
    'core_section_title': "\n━━━━ FILTROS PRINCIPALES ━━━━\n",
    'optional_section_title': "\n━━━━ FILTROS ADICIONALES ━━━━\n",
    
    # Mensajes de acción
    'search_action': "\n9️⃣ 🔍 Buscar con estos filtros",
    'back_action': "0️⃣ ⬅️ Volver al menú principal",
    
    # Mensaje cuando no hay filtros activos
    'no_filters_active': "Ninguno",
    
    # Mensaje de filtros activos
    'active_filters_header': "\n✅ *Filtros activos:*\n",
    
    # Mensaje cuando falta un filtro obligatorio
    'missing_required': """⚠️ *Filtros incompletos*

Debes completar los siguientes filtros obligatorios antes de buscar:
{missing_filters}

Por favor, selecciona estos filtros antes de continuar.
""",
    
    # Mensaje cuando no hay resultados
    'no_results': """😔 No encontramos profesionales con estos criterios.

💡 *Sugerencias:*
- Intenta quitar algunos filtros opcionales
- Prueba con otra fecha u horario
- Busca en otra zona

¿Quieres modificar los filtros?
""",
    
    # Mensaje de confirmación al agregar filtro
    'filter_added': """✅ Filtro agregado: *{filter_name}*

{menu}""",
}


# ============================================================================
# CONFIGURACIÓN DE VALIDACIONES
# ============================================================================

VALIDATION_CONFIG = {
    # ¿Validar filtros obligatorios antes de buscar?
    'enforce_required_filters': True,
    
    # ¿Permitir búsqueda sin ningún filtro? (no recomendado)
    'allow_empty_search': False,
    
    # ¿Mostrar advertencia si solo hay 1 filtro activo?
    'warn_single_filter': True,
    
    # Mensaje de advertencia para búsqueda con pocos filtros
    'single_filter_warning': """⚠️ Solo tienes 1 filtro activo.

La búsqueda puede retornar muchos resultados.
¿Quieres agregar más filtros para refinar la búsqueda?

9️⃣ Buscar de todas formas
1️⃣-6️⃣ Agregar más filtros
0️⃣ Volver
""",
}


# ============================================================================
# ORDEN DE PRIORIDAD PARA MOSTRAR FILTROS ACTIVOS
# ============================================================================
# Define el orden en que se muestran los filtros activos en el resumen.
# Si no está en esta lista, se muestra en el orden que fueron agregados.

ACTIVE_FILTERS_DISPLAY_ORDER = [
    FilterType.DATE,
    FilterType.TIME,
    FilterType.SPECIALTY,
    FilterType.ZONE,
    FilterType.PREPAGA,
    FilterType.GENDER,
    FilterType.MODALITY,
]


# ============================================================================
# CONFIGURACIÓN DE ANALYTICS (Opcional)
# ============================================================================
# Estos filtros se trackean con mayor detalle en analytics

ANALYTICS_CONFIG = {
    # Filtros que se consideran "de alta conversión"
    'high_conversion_filters': [
        FilterType.DATE,
        FilterType.SPECIALTY,
    ],
    
    # Filtros que raramente se usan (para detectar si hay que removerlos)
    'track_usage': True,
}


# ============================================================================
# FUNCIONES DE UTILIDAD
# ============================================================================

def get_enabled_filters():
    """
    Retorna solo los filtros habilitados.
    
    Returns:
        dict: Diccionario con solo los filtros donde enabled=True
    """
    return {
        filter_type: config 
        for filter_type, config in ENABLED_FILTERS.items() 
        if config.get('enabled', False)
    }


def get_filters_by_category(category: FilterCategory):
    """
    Retorna filtros habilitados de una categoría específica.
    
    Args:
        category: FilterCategory.CORE o FilterCategory.OPTIONAL
    
    Returns:
        dict: Filtros de esa categoría
    """
    enabled = get_enabled_filters()
    return {
        filter_type: config
        for filter_type, config in enabled.items()
        if config.get('category') == category
    }


def get_required_filters():
    """
    Retorna la lista de filtros obligatorios que están habilitados.
    
    Returns:
        list: Lista de FilterType obligatorios
    """
    enabled = get_enabled_filters()
    return [
        filter_type 
        for filter_type in REQUIRED_FILTERS 
        if filter_type in enabled
    ]


def is_filter_enabled(filter_type: FilterType) -> bool:
    """
    Verifica si un filtro específico está habilitado.
    
    Args:
        filter_type: El tipo de filtro a verificar
    
    Returns:
        bool: True si está habilitado, False caso contrario
    """
    return ENABLED_FILTERS.get(filter_type, {}).get('enabled', False)


# ============================================================================
# EJEMPLOS DE CONFIGURACIONES PARA DIFERENTES PROYECTOS
# ============================================================================

"""
# ===== EJEMPLO 1: PROYECTO MINIMALISTA =====
# Solo fecha, horario y zona

ENABLED_FILTERS = {
    FilterType.DATE: {'enabled': True, 'menu_position': 1, ...},
    FilterType.TIME: {'enabled': True, 'menu_position': 2, ...},
    FilterType.ZONE: {'enabled': True, 'menu_position': 3, ...},
}

REQUIRED_FILTERS = [FilterType.DATE]


# ===== EJEMPLO 2: PROYECTO COMPLETO =====
# Todos los filtros habilitados

ENABLED_FILTERS = {
    FilterType.DATE: {'enabled': True, 'menu_position': 1, ...},
    FilterType.TIME: {'enabled': True, 'menu_position': 2, ...},
    FilterType.SPECIALTY: {'enabled': True, 'menu_position': 3, ...},
    FilterType.ZONE: {'enabled': True, 'menu_position': 4, ...},
    FilterType.PREPAGA: {'enabled': True, 'menu_position': 5, ...},
    FilterType.GENDER: {'enabled': True, 'menu_position': 6, ...},
    FilterType.MODALITY: {'enabled': True, 'menu_position': 7, ...},
}

REQUIRED_FILTERS = [FilterType.DATE, FilterType.SPECIALTY]


# ===== EJEMPLO 3: SOLO FILTROS CORE =====
# Sin filtros opcionales

ENABLED_FILTERS = {
    FilterType.DATE: {'enabled': True, 'menu_position': 1, ...},
    FilterType.TIME: {'enabled': True, 'menu_position': 2, ...},
    FilterType.SPECIALTY: {'enabled': True, 'menu_position': 3, ...},
}

REQUIRED_FILTERS = [FilterType.DATE, FilterType.SPECIALTY]
"""