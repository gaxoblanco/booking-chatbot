"""
Filter Configuration
====================
Sistema de filtros dinámicos y configurables para búsqueda de profesionales.

Este módulo permite agregar, quitar, ordenar y configurar filtros sin modificar
código del bot. Ideal para adaptar el sistema a diferentes dominios.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta


class FilterConfig:
    """
    Configuración dinámica de filtros de búsqueda.

    Cada filtro es un diccionario con:
    - id: Identificador único
    - name: Nombre descriptivo
    - emoji: Emoji para UI
    - type: 'select', 'date', 'text', 'number', 'boolean'
    - required: Si es obligatorio
    - enabled: Si está activo
    - order: Orden de presentación
    - options: Lista de opciones (para type='select')
    - validation: Reglas de validación
    - dependent_on: Filtro del que depende
    - help_text: Texto de ayuda
    - can_skip: Si se puede saltar en búsqueda asistida
    """

    # =====================================================
    # CONFIGURACIÓN DE FILTROS
    # =====================================================
    # Para agregar/quitar filtros, solo edita este array
    # Para cambiar orden, cambia el valor de 'order'
    # Para habilitar/deshabilitar, cambia 'enabled'

    FILTERS = [
        # FILTRO 1: Modalidad (OBLIGATORIO)
        {
            'id': 'modalidad',
            'name': 'Modalidad de atención',
            'emoji': '🖥️',
            'type': 'select',
            'required': True,
            'enabled': True,
            'order': 1,
            'options': [
                {'value': 'presencial', 'label': 'Presencial'},
                {'value': 'virtual', 'label': 'Virtual (videollamada)'},
                {'value': 'ambas', 'label': 'Ambas opciones'}
            ],
            'help_text': '¿Preferís atención presencial o virtual?',
            'can_skip': False
        },

        # FILTRO 2: Fecha (OBLIGATORIO)
        {
            'id': 'fecha',
            'name': 'Fecha de la cita',
            'emoji': '📅',
            'type': 'date',
            'required': True,
            'enabled': True,
            'order': 2,
            'validation': {
                'min': 'today',
                'max': 'today+60',
                'format': 'DD/MM/YYYY',
                'formats_accepted': ['DD/MM/YYYY', 'YYYY-MM-DD']
            },
            'help_text': '¿Para qué fecha buscás disponibilidad?\nFormato: DD/MM/YYYY (ejemplo: 15/12/2024)',
            'can_skip': False
        },

        # FILTRO 3: Horario (OBLIGATORIO)
        {
            'id': 'horario',
            'name': 'Horario preferido',
            'emoji': '⏰',
            'type': 'select',
            'required': True,
            'enabled': True,
            'order': 3,
            'options': [
                {'value': 'manana',
                    'label': 'Mañana (8:00 - 12:00)', 'time_range': ('08:00', '12:00')},
                {'value': 'tarde',
                    'label': 'Tarde (12:00 - 18:00)', 'time_range': ('12:00', '18:00')},
                {'value': 'noche',
                    'label': 'Noche (18:00 - 21:00)', 'time_range': ('18:00', '21:00')},
                {'value': 'indistinto', 'label': 'Indistinto',
                    'time_range': ('08:00', '21:00')}
            ],
            'help_text': '¿En qué horario preferís la cita?',
            'can_skip': False
        },

        # FILTRO 4: Zona (CONDICIONAL - solo si presencial)
        {
            'id': 'zona',
            'name': 'Zona de preferencia',
            'emoji': '📍',
            'type': 'select',
            'required': False,
            'enabled': True,
            'order': 4,
            'dependent_on': {
                'filter': 'modalidad',
                # Solo mostrar si eligió presencial/ambas
                'values': ['presencial', 'ambas']
            },
            'options': [
                {'value': 'norte', 'label': 'Zona Norte'},
                {'value': 'sur', 'label': 'Zona Sur'},
                {'value': 'centro', 'label': 'Centro'},
                {'value': 'oeste', 'label': 'Zona Oeste'},
                {'value': 'indistinto', 'label': 'Indistinto'}
            ],
            'help_text': '¿En qué zona preferís atenderte?',
            'can_skip': True
        },

        # FILTRO 5: Especialidad (OPCIONAL)
        {
            'id': 'especialidad',
            'name': 'Especialidad / Enfoque',
            'emoji': '💼',
            'type': 'select',
            'required': False,
            'enabled': True,
            'order': 5,
            'multiple': True,  # Permite selección múltiple
            'options': [
                {'value': 'tcc', 'label': 'TCC (Cognitivo Conductual)'},
                {'value': 'psicoanalitico', 'label': 'Psicoanalítico'},
                {'value': 'sistemico', 'label': 'Sistémico'},
                {'value': 'gestalt', 'label': 'Gestalt'},
                {'value': 'contextual', 'label': 'Contextual (ACT, FAP)'},
                {'value': 'humanista', 'label': 'Humanista'},
                {'value': 'integrador', 'label': 'Integrador'},
                {'value': 'indistinto', 'label': 'Indistinto'}
            ],
            'help_text': '¿Buscás algún enfoque terapéutico específico?\n(Opcional - podés saltar)',
            'can_skip': True
        },

        # FILTRO 6: Obra Social (OPCIONAL)
        {
            'id': 'prepaga',
            'name': 'Obra social / Prepaga',
            'emoji': '💳',
            'type': 'select',
            'required': False,
            'enabled': True,
            'order': 6,
            'options': [
                {'value': 'si', 'label': 'Sí, que acepte obra social'},
                {'value': 'no_importa', 'label': 'No importa'}
            ],
            'help_text': '¿Buscás profesionales que acepten obra social?\n(Opcional - podés saltar)',
            'can_skip': True
        },

        # FILTRO 7: Género del Profesional (OPCIONAL)
        {
            'id': 'genero_profesional',
            'name': 'Género del profesional',
            'emoji': '👤',
            'type': 'select',
            'required': False,
            'enabled': True,
            'order': 7,
            'options': [
                {'value': 'masculino', 'label': 'Masculino'},
                {'value': 'femenino', 'label': 'Femenino'},
                {'value': 'indistinto', 'label': 'Indistinto'}
            ],
            'help_text': '¿Tenés preferencia por el género del profesional?\n(Opcional - podés saltar)',
            'can_skip': True
        },

        # FILTRO 8: Población (DESHABILITADO - ejemplo)
        {
            'id': 'poblacion',
            'name': 'Población / Especialización',
            'emoji': '👥',
            'type': 'select',
            'required': False,
            'enabled': False,  # ⚠️ DESHABILITADO - Para habilitar, cambiar a True
            'order': 8,
            'multiple': True,
            'options': [
                {'value': 'adultos', 'label': 'Adultos'},
                {'value': 'adolescentes', 'label': 'Adolescentes'},
                {'value': 'ninos', 'label': 'Niños'},
                {'value': 'parejas', 'label': 'Parejas'},
                {'value': 'familias', 'label': 'Familias'},
                {'value': 'tercera_edad', 'label': 'Tercera edad'}
            ],
            'help_text': '¿Para qué población buscás atención?',
            'can_skip': True
        },

        # FILTRO 9: Honorarios (DESHABILITADO - ejemplo)
        {
            'id': 'honorarios',
            'name': 'Rango de honorarios',
            'emoji': '💰',
            'type': 'select',
            'required': False,
            'enabled': False,  # ⚠️ DESHABILITADO
            'order': 9,
            'options': [
                {'value': 'hasta_15k', 'label': 'Hasta $15,000'},
                {'value': '15k_25k', 'label': '$15,000 - $25,000'},
                {'value': '25k_35k', 'label': '$25,000 - $35,000'},
                {'value': 'mas_35k', 'label': 'Más de $35,000'},
                {'value': 'no_importa', 'label': 'No importa'}
            ],
            'help_text': '¿Cuál es tu presupuesto aproximado?',
            'can_skip': True
        }
    ]

    # =====================================================
    # MÉTODOS DE ACCESO
    # =====================================================

    @classmethod
    def get_all_filters(cls) -> List[Dict]:
        """Retorna todos los filtros (habilitados y deshabilitados)."""
        return cls.FILTERS.copy()

    @classmethod
    def get_enabled_filters(cls) -> List[Dict]:
        """Retorna solo filtros habilitados, ordenados."""
        enabled = [f for f in cls.FILTERS if f['enabled']]
        return sorted(enabled, key=lambda x: x['order'])

    @classmethod
    def get_required_filters(cls) -> List[Dict]:
        """Retorna filtros obligatorios (habilitados)."""
        return [f for f in cls.get_enabled_filters() if f['required']]

    @classmethod
    def get_optional_filters(cls) -> List[Dict]:
        """Retorna filtros opcionales (habilitados)."""
        return [f for f in cls.get_enabled_filters() if not f['required']]

    @classmethod
    def get_filter_by_id(cls, filter_id: str) -> Optional[Dict]:
        """Obtiene configuración de un filtro por ID."""
        for f in cls.FILTERS:
            if f['id'] == filter_id:
                return f.copy()
        return None

    @classmethod
    def get_filter_by_order(cls, order: int) -> Optional[Dict]:
        """Obtiene filtro por su orden."""
        enabled = cls.get_enabled_filters()
        if 0 <= order < len(enabled):
            return enabled[order]
        return None

    # =====================================================
    # VALIDACIÓN Y DEPENDENCIAS
    # =====================================================

    @classmethod
    def is_filter_applicable(cls, filter_id: str, applied_filters: Dict) -> bool:
        """
        Verifica si un filtro es aplicable dado el estado actual.

        Args:
            filter_id: ID del filtro a verificar
            applied_filters: Dict con filtros ya aplicados {filter_id: value}

        Returns:
            True si el filtro es aplicable

        Ejemplo:
            >>> applied = {'modalidad': 'virtual'}
            >>> FilterConfig.is_filter_applicable('zona', applied)
            False  # zona solo para presencial
        """
        filter_config = cls.get_filter_by_id(filter_id)

        if not filter_config or not filter_config['enabled']:
            return False

        # Verificar dependencias
        if 'dependent_on' in filter_config:
            dep = filter_config['dependent_on']
            dep_filter = dep['filter']
            dep_values = dep['values']

            # Si el filtro del que depende no está aplicado → no aplicable
            if dep_filter not in applied_filters:
                return False

            # Si el valor no cumple la condición → no aplicable
            if applied_filters[dep_filter] not in dep_values:
                return False

        return True

    @classmethod
    def get_applicable_filters(cls, applied_filters: Dict) -> List[Dict]:
        """
        Obtiene lista de filtros aplicables según estado actual.

        Args:
            applied_filters: Filtros ya aplicados

        Returns:
            Lista de filtros aplicables
        """
        applicable = []

        for filter_config in cls.get_enabled_filters():
            filter_id = filter_config['id']

            # Si ya está aplicado, saltar
            if filter_id in applied_filters:
                continue

            # Verificar si es aplicable
            if cls.is_filter_applicable(filter_id, applied_filters):
                applicable.append(filter_config)

        return applicable

    @classmethod
    def get_next_filter(cls, applied_filters: Dict) -> Optional[Dict]:
        """
        Obtiene el siguiente filtro a aplicar en búsqueda asistida.

        Args:
            applied_filters: Filtros ya aplicados

        Returns:
            Configuración del siguiente filtro o None si ya están todos

        Ejemplo:
            >>> applied = {'modalidad': 'presencial'}
            >>> next_filter = FilterConfig.get_next_filter(applied)
            >>> print(next_filter['id'])
            'fecha'
        """
        applicable = cls.get_applicable_filters(applied_filters)

        if applicable:
            return applicable[0]  # Retornar el primero por orden

        return None

    @classmethod
    def validate_filters(cls, applied_filters: Dict) -> Dict:
        """
        Valida que todos los filtros obligatorios estén presentes.

        Args:
            applied_filters: Filtros aplicados por el usuario

        Returns:
            {
                'valid': bool,
                'missing_required': List[str],
                'can_search': bool,
                'missing_count': int
            }

        Ejemplo:
            >>> applied = {'modalidad': 'virtual'}
            >>> result = FilterConfig.validate_filters(applied)
            >>> print(result)
            {
                'valid': False,
                'missing_required': ['Fecha de la cita', 'Horario preferido'],
                'can_search': False,
                'missing_count': 2
            }
        """
        required = cls.get_required_filters()
        missing = []

        for filter_config in required:
            filter_id = filter_config['id']

            # Verificar si es aplicable
            if not cls.is_filter_applicable(filter_id, applied_filters):
                continue

            # Verificar si está presente
            if filter_id not in applied_filters:
                missing.append(filter_config['name'])

        return {
            'valid': len(missing) == 0,
            'missing_required': missing,
            'can_search': len(missing) == 0,
            'missing_count': len(missing)
        }

    # =====================================================
    # GENERACIÓN DE MENSAJES
    # =====================================================

    @classmethod
    def format_filter_menu(cls, applied_filters: Dict = None) -> str:
        """
        Genera menú de filtros para búsqueda rápida.

        Args:
            applied_filters: Filtros ya aplicados (opcional)

        Returns:
            Mensaje formateado con menú de filtros
        """
        if applied_filters is None:
            applied_filters = {}

        message = "🔍 *Búsqueda Rápida*\n\n"
        message += "Seleccioná los filtros que quieras aplicar:\n\n"

        # Listar filtros
        enabled = cls.get_enabled_filters()
        for i, filter_config in enumerate(enabled, 1):
            emoji = filter_config['emoji']
            name = filter_config['name']
            filter_id = filter_config['id']
            required = " *(obligatorio)*" if filter_config['required'] else ""

            # Verificar si es aplicable
            is_applicable = cls.is_filter_applicable(
                filter_id, applied_filters)

            if not is_applicable:
                continue  # No mostrar filtros no aplicables

            # Marcar si ya está aplicado
            if filter_id in applied_filters:
                value = applied_filters[filter_id]
                # Buscar label
                label = value
                if 'options' in filter_config:
                    for opt in filter_config['options']:
                        if opt['value'] == value:
                            label = opt['label']
                            break
                status = f" ✅ *{label}*"
            else:
                status = ""

            message += f"{emoji} {i}. {name}{required}{status}\n"

        # Mostrar resumen de filtros activos
        message += "\n📋 *Filtros activos:*\n"
        if applied_filters:
            for filter_id, value in applied_filters.items():
                filter_config = cls.get_filter_by_id(filter_id)
                if filter_config:
                    emoji = filter_config['emoji']
                    name = filter_config['name']

                    # Buscar label
                    label = value
                    if 'options' in filter_config:
                        for opt in filter_config['options']:
                            if opt['value'] == value:
                                label = opt['label']
                                break

                    message += f"• {emoji} {name}: {label}\n"
        else:
            message += "• Ninguno\n"

        # Validar si puede buscar
        validation = cls.validate_filters(applied_filters)

        message += "\n"
        if validation['can_search']:
            message += "✅ *Buscar profesionales*\n"
        else:
            missing = ', '.join(validation['missing_required'])
            message += f"⚠️ Faltan filtros obligatorios: {missing}\n"

        message += "0️⃣ Volver"

        return message

    @classmethod
    def format_filter_question(cls, filter_config: Dict, step: int = None, total: int = None) -> str:
        """
        Genera pregunta para un filtro específico.

        Args:
            filter_config: Configuración del filtro
            step: Número de paso actual (para búsqueda asistida)
            total: Total de pasos

        Returns:
            Mensaje formateado con la pregunta
        """
        emoji = filter_config['emoji']
        name = filter_config['name']
        help_text = filter_config.get('help_text', '')
        can_skip = filter_config.get('can_skip', False)

        # Header con progreso (si aplica)
        if step and total:
            message = f"📍 *Paso {step} de {total}*: {name}\n\n"
        else:
            message = f"{emoji} *{name}*\n\n"

        # Texto de ayuda
        if help_text:
            message += f"{help_text}\n\n"

        # Opciones (si es tipo select)
        if filter_config['type'] == 'select':
            for i, option in enumerate(filter_config['options'], 1):
                message += f"{i}️⃣ {option['label']}\n"

        # Indicar si se puede saltar
        if can_skip:
            message += "\n💡 Escribí 'saltar' para omitir este paso\n"

        message += "0️⃣ Volver"

        return message


# =====================================================
# FEATURE FLAGS
# =====================================================

class FeatureFlags:
    """
    Flags para activar/desactivar features en desarrollo.
    Útil para deploy gradual de nuevas funcionalidades.
    """

    # Core features
    INTELLIGENT_USER_RECOGNITION = True   # Reconocimiento automático por teléfono
    DYNAMIC_FILTERS = True                # Filtros dinámicos configurables

    # Features en desarrollo
    APPOINTMENT_MANAGEMENT = False        # Gestión completa de citas
    THIRD_PARTY_BOOKING = False           # Agendamiento para terceros
    APPOINTMENT_REMINDERS = False         # Recordatorios automáticos

    # Analytics
    ANALYTICS_TRACKING = True             # Tracking de acciones
    ADVANCED_ANALYTICS = False            # Analytics avanzado

    # Experimental
    AI_RECOMMENDATIONS = False            # Recomendaciones con IA
    VOICE_MESSAGES = False                # Mensajes de voz
    VIDEO_CONSULTATIONS = False           # Videollamadas integradas


# =====================================================
# EJEMPLOS DE USO
# =====================================================

if __name__ == "__main__":
    print("=" * 60)
    print("EJEMPLOS DE USO - FilterConfig")
    print("=" * 60)

    # Ejemplo 1: Obtener filtros habilitados
    print("\n1. Filtros habilitados:")
    enabled = FilterConfig.get_enabled_filters()
    for f in enabled:
        status = "⚠️ OBLIGATORIO" if f['required'] else "✅ Opcional"
        print(f"  {f['emoji']} {f['name']} - {status}")

    # Ejemplo 2: Validar filtros
    print("\n2. Validación de filtros:")
    applied = {'modalidad': 'virtual'}
    validation = FilterConfig.validate_filters(applied)
    print(f"  ¿Válido? {validation['valid']}")
    print(f"  Faltan: {validation['missing_required']}")

    # Ejemplo 3: Siguiente filtro en búsqueda asistida
    print("\n3. Siguiente filtro:")
    next_filter = FilterConfig.get_next_filter(applied)
    if next_filter:
        print(f"  → {next_filter['emoji']} {next_filter['name']}")

    # Ejemplo 4: Menú de filtros
    print("\n4. Menú de búsqueda rápida:")
    print(FilterConfig.format_filter_menu(applied))
