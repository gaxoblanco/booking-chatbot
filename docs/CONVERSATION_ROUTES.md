# 🗺️ MAPA COMPLETO DE RUTAS CONVERSACIONALES v3.0
## Sistema de Agenda - WhatsApp Bot (Single Center)

---

## 📋 ÍNDICE

1. [Cambios Importantes - v3.0](#cambios-importantes---v30)
2. [Arquitectura Inteligente](#arquitectura-inteligente)
3. [Sistema de Reconocimiento de Usuarios](#sistema-de-reconocimiento-de-usuarios)
4. [Filtros Dinámicos](#filtros-dinámicos)
5. [Flujos del Cliente](#flujos-del-cliente)
6. [Flujos del Profesional](#flujos-del-profesional)
7. [Gestión de Citas](#gestión-de-citas)
8. [Testing](#testing)

---

## 🆕 CAMBIOS IMPORTANTES - v3.0

### **Mejoras Críticas Implementadas:**

#### **1. Reconocimiento Inteligente de Usuario** 🎯
```python
# ANTES (v2.0):
Usuario → "hola" → ¿Eres cliente o profesional?

# AHORA (v3.0):
Usuario → "hola" → [BUSCAR EN BD POR TELÉFONO]
  ├─→ Profesional registrado → Panel profesional directo
  ├─→ Cliente registrado → Panel cliente directo
  └─→ Usuario nuevo → Detectar intención:
        ├─→ "hola soy profesional" → Flujo profesional
        ├─→ "hola" / "busco turno" → Flujo cliente
        └─→ Mensaje ambiguo → Preguntar rol
```

#### **2. Intención Natural del Lenguaje** 💬
```python
# Detección de intención en el primer mensaje:
"hola soy profesional" → rol = PROFESSIONAL
"hola, trabajo como psicólogo" → rol = PROFESSIONAL
"buenas, quiero registrarme como terapeuta" → rol = PROFESSIONAL

"hola" → rol = CLIENT (default)
"busco turno" → rol = CLIENT
"necesito cita" → rol = CLIENT
"quiero sacar turno para mi hijo" → rol = CLIENT + tercero
```

#### **3. Filtros Dinámicos y Configurables** ⚙️
```python
# Array de filtros configurable en domain_config.py
FILTER_CONFIG = [
    {
        'id': 'especialidad',
        'name': 'Especialidad',
        'type': 'select',
        'required': False,
        'options': ['TCC', 'Psicoanalítico', 'Gestalt', ...]
    },
    {
        'id': 'fecha',
        'name': 'Fecha',
        'type': 'date',
        'required': True,
        'min': 'today',
        'max': 'today+60'
    },
    # ... más filtros
]

# Facilita:
# ✅ Agregar/quitar filtros sin cambiar código
# ✅ Cambiar orden de filtros
# ✅ Habilitar/deshabilitar filtros por dominio
```

#### **4. Gestión de Citas para Terceros** 👨‍👩‍👧
```python
# Usuario puede agendar para otra persona
temp_data['booking_for'] = 'self' | 'other'
temp_data['patient_name'] = "Juan Pérez"
temp_data['patient_phone'] = "+5491112345678"
```

#### **5. Cancelación/Reprogramación Inteligente** 🔄
```python
Usuario con citas → "hola"
  → "¡Hola María! Veo que tienes una cita el 15/12 a las 14:00"
  → Opciones:
     1. Confirmar cita
     2. Reprogramar
     3. Cancelar
     4. Agendar nueva cita
```

---

## 🧠 ARQUITECTURA INTELIGENTE

### **Flujo de Entrada Mejorado:**

```
┌─────────────────────────────────────────┐
│ Usuario envía mensaje a WhatsApp       │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ 1. BUSCAR USUARIO EN BD POR TELÉFONO   │
└────────────────┬────────────────────────┘
                 │
    ┌────────────┼────────────┐
    │            │            │
    ▼            ▼            ▼
┌─────────┐  ┌──────────┐  ┌──────────┐
│Profesional│ │ Cliente  │ │  Nuevo   │
│Registrado│  │Registrado│  │ Usuario  │
└────┬─────┘  └────┬─────┘  └────┬─────┘
     │             │              │
     ▼             ▼              ▼
┌─────────┐  ┌──────────┐  ┌──────────┐
│Verificar│  │Verificar │  │ Detectar │
│Citas    │  │Citas     │  │Intención │
│Pendientes│ │Pendientes│  │          │
└────┬─────┘  └────┬─────┘  └────┬─────┘
     │             │              │
     ▼             ▼              ▼
┌─────────────────────────────────────────┐
│ 2. GENERAR CONTEXTO PERSONALIZADO      │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ 3. MENSAJE DE BIENVENIDA CONTEXTUAL    │
│                                         │
│ • Usuario nuevo: Bienvenida + Opciones │
│ • Con citas: Resumen + Gestión         │
│ • Sin citas: Opciones de agenda        │
└─────────────────────────────────────────┘
```

---

## 👤 SISTEMA DE RECONOCIMIENTO DE USUARIOS

### **Tabla: user_registry (nueva)**

```sql
CREATE TABLE user_registry (
    phone TEXT PRIMARY KEY,
    user_type TEXT CHECK(user_type IN ('client', 'professional', 'unknown')),
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    name TEXT,
    is_active INTEGER DEFAULT 1
);
```

### **Función: identify_user(phone)**

```python
def identify_user(phone: str) -> Dict:
    """
    Identifica tipo de usuario por teléfono.
    
    Returns:
        {
            'user_type': 'client' | 'professional' | 'new',
            'name': str | None,
            'has_pending_appointments': bool,
            'pending_appointments': List[Dict],
            'is_registered': bool
        }
    """
    # 1. Buscar en professionals
    professional = db.get_professional(phone)
    if professional:
        appointments = db.get_professional_appointments(phone, status='pendiente')
        return {
            'user_type': 'professional',
            'name': professional['name'],
            'has_pending_appointments': len(appointments) > 0,
            'pending_appointments': appointments,
            'is_registered': True
        }
    
    # 2. Buscar en clients
    client = db.get_client(phone)
    if client:
        appointments = db.get_client_appointments(phone, status='confirmada')
        return {
            'user_type': 'client',
            'name': client['name'],
            'has_pending_appointments': len(appointments) > 0,
            'pending_appointments': appointments,
            'is_registered': True
        }
    
    # 3. Usuario nuevo
    return {
        'user_type': 'new',
        'name': None,
        'has_pending_appointments': False,
        'pending_appointments': [],
        'is_registered': False
    }
```

### **Función: detect_intention(message)**

```python
def detect_intention(message: str) -> str:
    """
    Detecta intención del usuario en mensaje inicial.
    
    Returns:
        'professional' | 'client' | 'ambiguous'
    """
    message_lower = message.lower()
    
    # Keywords de profesional
    professional_keywords = [
        'soy profesional', 'trabajo como', 'soy psicólogo', 
        'soy terapeuta', 'quiero registrarme como profesional',
        'trabajo en', 'atiendo pacientes'
    ]
    
    for keyword in professional_keywords:
        if keyword in message_lower:
            return 'professional'
    
    # Keywords de cliente (búsqueda de turno)
    client_keywords = [
        'turno', 'cita', 'sesión', 'consulta',
        'busco', 'necesito', 'quiero sacar'
    ]
    
    for keyword in client_keywords:
        if keyword in message_lower:
            return 'client'
    
    # Si solo dice "hola" → cliente por defecto
    greetings = ['hola', 'buenos días', 'buenas tardes', 'buenas', 'hi']
    if message_lower.strip() in greetings:
        return 'client'
    
    return 'ambiguous'
```

---

## ⚙️ FILTROS DINÁMICOS

### **Configuración en domain_config.py:**

```python
class FilterConfig:
    """Configuración dinámica de filtros de búsqueda."""
    
    # Lista ordenada de filtros disponibles
    FILTERS = [
        {
            'id': 'especialidad',
            'name': 'Especialidad / Enfoque',
            'emoji': '💼',
            'type': 'select',
            'required': False,
            'enabled': True,
            'options': [
                {'value': 'tcc', 'label': 'TCC (Cognitivo Conductual)'},
                {'value': 'psicoanalitico', 'label': 'Psicoanalítico'},
                {'value': 'sistemico', 'label': 'Sistémico'},
                {'value': 'gestalt', 'label': 'Gestalt'},
                {'value': 'contextual', 'label': 'Contextual (ACT, FAP)'},
                {'value': 'humanista', 'label': 'Humanista'},
                {'value': 'integrador', 'label': 'Integrador'}
            ]
        },
        {
            'id': 'fecha',
            'name': 'Fecha de la cita',
            'emoji': '📅',
            'type': 'date',
            'required': True,
            'enabled': True,
            'validation': {
                'min': 'today',
                'max': 'today+60',
                'format': 'DD/MM/YYYY'
            }
        },
        {
            'id': 'horario',
            'name': 'Horario preferido',
            'emoji': '⏰',
            'type': 'select',
            'required': True,
            'enabled': True,
            'options': [
                {'value': 'manana', 'label': 'Mañana (8:00 - 12:00)'},
                {'value': 'tarde', 'label': 'Tarde (12:00 - 18:00)'},
                {'value': 'noche', 'label': 'Noche (18:00 - 21:00)'},
                {'value': 'indistinto', 'label': 'Indistinto'}
            ]
        },
        {
            'id': 'modalidad',
            'name': 'Modalidad de atención',
            'emoji': '🖥️',
            'type': 'select',
            'required': True,
            'enabled': True,
            'options': [
                {'value': 'presencial', 'label': 'Presencial'},
                {'value': 'virtual', 'label': 'Virtual (videollamada)'},
                {'value': 'ambas', 'label': 'Ambas opciones'}
            ]
        },
        {
            'id': 'zona',
            'name': 'Zona de preferencia',
            'emoji': '📍',
            'type': 'select',
            'required': False,
            'enabled': True,
            'dependent_on': 'modalidad',  # Solo si modalidad incluye presencial
            'options': [
                {'value': 'norte', 'label': 'Zona Norte'},
                {'value': 'sur', 'label': 'Zona Sur'},
                {'value': 'centro', 'label': 'Centro'},
                {'value': 'indistinto', 'label': 'Indistinto'}
            ]
        },
        {
            'id': 'prepaga',
            'name': 'Obra social / Prepaga',
            'emoji': '💳',
            'type': 'select',
            'required': False,
            'enabled': True,
            'options': [
                {'value': 'si', 'label': 'Sí, acepta obra social'},
                {'value': 'no_importa', 'label': 'No importa'}
            ]
        },
        {
            'id': 'genero_profesional',
            'name': 'Género del profesional',
            'emoji': '👤',
            'type': 'select',
            'required': False,
            'enabled': True,
            'options': [
                {'value': 'masculino', 'label': 'Masculino'},
                {'value': 'femenino', 'label': 'Femenino'},
                {'value': 'indistinto', 'label': 'Indistinto'}
            ]
        },
        {
            'id': 'poblacion',
            'name': 'Población / Especialización',
            'emoji': '👥',
            'type': 'select',
            'required': False,
            'enabled': False,  # Deshabilitado por ahora
            'options': [
                {'value': 'adultos', 'label': 'Adultos'},
                {'value': 'adolescentes', 'label': 'Adolescentes'},
                {'value': 'ninos', 'label': 'Niños'},
                {'value': 'parejas', 'label': 'Parejas'},
                {'value': 'familias', 'label': 'Familias'}
            ]
        },
        {
            'id': 'honorarios',
            'name': 'Rango de honorarios',
            'emoji': '💰',
            'type': 'select',
            'required': False,
            'enabled': False,  # Deshabilitado por ahora
            'options': [
                {'value': 'hasta_15k', 'label': 'Hasta $15,000'},
                {'value': '15k_25k', 'label': '$15,000 - $25,000'},
                {'value': '25k_35k', 'label': '$25,000 - $35,000'},
                {'value': 'mas_35k', 'label': 'Más de $35,000'}
            ]
        }
    ]
    
    @classmethod
    def get_enabled_filters(cls):
        """Retorna solo filtros habilitados."""
        return [f for f in cls.FILTERS if f['enabled']]
    
    @classmethod
    def get_required_filters(cls):
        """Retorna filtros obligatorios."""
        return [f for f in cls.FILTERS if f['enabled'] and f['required']]
    
    @classmethod
    def get_filter_by_id(cls, filter_id: str):
        """Obtiene configuración de un filtro específico."""
        for f in cls.FILTERS:
            if f['id'] == filter_id:
                return f
        return None
```

### **Ventajas de Filtros Dinámicos:**

```python
# ✅ Agregar nuevo filtro
# Solo agregar entrada al array FILTERS, sin tocar código del bot

# ✅ Cambiar orden de filtros en búsqueda asistida
# Solo reordenar elementos en FILTERS

# ✅ Habilitar/deshabilitar filtros
# Cambiar 'enabled': True/False

# ✅ Filtros condicionales
# Usar 'dependent_on' para mostrar solo si otro filtro cumple condición

# ✅ Diferentes configuraciones por dominio
# Psicología vs Belleza vs Legal → distintos FILTERS
```

---

## 👥 FLUJOS DEL CLIENTE

### **FLUJO PRINCIPAL - Usuario Nuevo:**

```
┌─────────────────────────────────────────┐
│ Usuario nuevo envía "hola"              │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ 🤖 ¡Bienvenido/a a Psico Connect!       │
│                                         │
│ Te ayudamos a encontrar al profesional  │
│ indicado para vos.                      │
│                                         │
│ ¿Qué querés hacer?                      │
│ 1️⃣ Agendar una cita                    │
│ 2️⃣ Consultar disponibilidad            │
│ 3️⃣ Información sobre el centro         │
│                                         │
│ Escribí el número de tu opción          │
└─────────────────────────────────────────┘
                 │
       ┌─────────┼─────────┐
       │         │         │
       ▼         ▼         ▼
    ┌────┐   ┌────┐   ┌────┐
    │ 1  │   │ 2  │   │ 3  │
    └─┬──┘   └─┬──┘   └─┬──┘
      │        │        │
      ▼        ▼        └─→ Mostrar info
┌──────────────────┐
│ ¿Para quién es   │
│ la cita?         │
│ 1. Para mí       │
│ 2. Para otra     │
│    persona       │
└──────┬───────────┘
       │
   ┌───┴────┐
   ▼        ▼
┌─────┐  ┌─────────────┐
│Para │  │¿Nombre del  │
│ mí  │  │ paciente?   │
└──┬──┘  └──────┬──────┘
   │            │
   └────┬───────┘
        │
        ▼
┌─────────────────────────────────────────┐
│ ¿Cómo querés buscar?                    │
│                                         │
│ 1️⃣ Búsqueda rápida (yo elijo)         │
│    Seleccioná tus preferencias          │
│                                         │
│ 2️⃣ Búsqueda asistida (te guío)        │
│    Te hago preguntas paso a paso        │
│                                         │
│ 0️⃣ Volver                              │
└─────────────────────────────────────────┘
```

### **FLUJO - Usuario Registrado CON Citas:**

```
┌─────────────────────────────────────────┐
│ Usuario registrado envía "hola"         │
│ BD: Tiene cita el 15/12 a las 14:00     │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ 🤖 ¡Hola María! 👋                      │
│                                         │
│ Tenés una cita próxima:                 │
│ 📅 15 de diciembre de 2024              │
│ ⏰ 14:00 hs                             │
│ 👨‍⚕️ Con Lic. Juan Pérez                │
│ 📍 Modalidad: Presencial                │
│                                         │
│ ¿Qué querés hacer?                      │
│ 1️⃣ Confirmar cita                      │
│ 2️⃣ Reprogramar cita                    │
│ 3️⃣ Cancelar cita                       │
│ 4️⃣ Agendar otra cita                   │
│ 5️⃣ Ver todas mis citas                 │
│                                         │
│ 0️⃣ Salir                               │
└─────────────────────────────────────────┘
```

### **FLUJO - Usuario Registrado SIN Citas:**

```
┌─────────────────────────────────────────┐
│ 🤖 ¡Hola María! 👋                      │
│                                         │
│ ¿En qué puedo ayudarte?                 │
│ 1️⃣ Agendar una cita                    │
│ 2️⃣ Consultar disponibilidad            │
│ 3️⃣ Actualizar mis datos                │
│                                         │
│ 0️⃣ Salir                               │
└─────────────────────────────────────────┘
```

---

## 🔍 RUTA 1: BÚSQUEDA RÁPIDA (Multi-Filtro)

### **Estado:** `CLIENT_SEARCH_QUICK`

```
┌─────────────────────────────────────────┐
│ 🤖 Búsqueda Rápida                      │
│                                         │
│ Seleccioná los filtros que quieras      │
│ aplicar (podés elegir varios)           │
│                                         │
│ 💼 1. Especialidad                      │
│ 📅 2. Fecha (obligatorio)               │
│ ⏰ 3. Horario (obligatorio)             │
│ 🖥️ 4. Modalidad (obligatorio)           │
│ 📍 5. Zona                              │
│ 💳 6. Obra social                       │
│ 👤 7. Género del profesional            │
│                                         │
│ Filtros activos: [ninguno]              │
│                                         │
│ ✅ Buscar (cuando tengas todo listo)    │
│ 0️⃣ Volver                              │
└─────────────────────────────────────────┘
```

**Lógica:**

```python
class QuickSearchHandler:
    """Handler para búsqueda rápida con filtros dinámicos."""
    
    def __init__(self):
        self.filters = FilterConfig.get_enabled_filters()
    
    def show_filter_menu(self, session: SessionData) -> str:
        """Muestra menú de filtros disponibles."""
        applied_filters = session.get_temp('applied_filters', {})
        required_filters = FilterConfig.get_required_filters()
        
        message = "🔍 Búsqueda Rápida\n\n"
        message += "Seleccioná los filtros que quieras aplicar:\n\n"
        
        # Mostrar filtros
        for i, filter_config in enumerate(self.filters, 1):
            emoji = filter_config['emoji']
            name = filter_config['name']
            required = " (obligatorio)" if filter_config['required'] else ""
            
            # Marcar si ya está aplicado
            if filter_config['id'] in applied_filters:
                value = applied_filters[filter_config['id']]
                status = f" ✓ {value}"
            else:
                status = ""
            
            message += f"{emoji} {i}. {name}{required}{status}\n"
        
        # Mostrar filtros activos
        message += "\n📋 Filtros activos:\n"
        if applied_filters:
            for filter_id, value in applied_filters.items():
                filter_config = FilterConfig.get_filter_by_id(filter_id)
                message += f"• {filter_config['emoji']} {filter_config['name']}: {value}\n"
        else:
            message += "• Ninguno\n"
        
        # Validar si puede buscar
        can_search = all(
            f['id'] in applied_filters 
            for f in required_filters
        )
        
        if can_search:
            message += "\n✅ Buscar profesionales"
        else:
            missing = [f['name'] for f in required_filters if f['id'] not in applied_filters]
            message += f"\n⚠️ Faltan filtros obligatorios: {', '.join(missing)}"
        
        message += "\n0️⃣ Volver"
        
        return message
```

---

## 🎯 RUTA 2: BÚSQUEDA ASISTIDA (Paso a Paso)

### **Estado:** `CLIENT_SEARCH_ASSISTED`

```python
class AssistedSearchHandler:
    """Handler para búsqueda asistida con flujo guiado."""
    
    def __init__(self):
        # Filtros ordenados para flujo guiado
        self.filter_sequence = [
            f['id'] for f in FilterConfig.get_enabled_filters()
        ]
        self.current_step = 0
    
    def get_next_filter(self, session: SessionData) -> Dict:
        """Obtiene el siguiente filtro a preguntar."""
        applied_filters = session.get_temp('applied_filters', {})
        
        for filter_id in self.filter_sequence:
            if filter_id not in applied_filters:
                filter_config = FilterConfig.get_filter_by_id(filter_id)
                
                # Verificar dependencias
                if 'dependent_on' in filter_config:
                    dependency = filter_config['dependent_on']
                    if dependency not in applied_filters:
                        continue
                
                return filter_config
        
        return None  # Todos los filtros aplicados
    
    def ask_filter(self, filter_config: Dict) -> str:
        """Genera pregunta para un filtro específico."""
        emoji = filter_config['emoji']
        name = filter_config['name']
        
        message = f"{emoji} {name}\n\n"
        
        if filter_config['type'] == 'select':
            # Mostrar opciones
            for i, option in enumerate(filter_config['options'], 1):
                message += f"{i}️⃣ {option['label']}\n"
        
        elif filter_config['type'] == 'date':
            # Instrucciones para fecha
            format_str = filter_config['validation']['format']
            message += f"Formato: {format_str}\n"
            message += "Ejemplo: 15/12/2024\n"
        
        message += "\n0️⃣ Volver"
        
        return message
```

**Flujo completo:**

```
PASO 1/7: Modalidad
    ↓
PASO 2/7: Fecha
    ↓
PASO 3/7: Horario
    ↓
PASO 4/7: Especialidad (opcional - permite saltar)
    ↓
PASO 5/7: Zona (solo si modalidad = presencial)
    ↓
PASO 6/7: Obra social (opcional)
    ↓
PASO 7/7: Género profesional (opcional)
    ↓
RESUMEN → Buscar
```

**Mensaje de progreso:**

```
┌─────────────────────────────────────────┐
│ 📍 Paso 3 de 7: Horario                 │
│                                         │
│ ⏰ ¿En qué horario preferís la cita?    │
│                                         │
│ 1️⃣ Mañana (8:00 - 12:00)               │
│ 2️⃣ Tarde (12:00 - 18:00)               │
│ 3️⃣ Noche (18:00 - 21:00)               │
│ 4️⃣ Indistinto                          │
│                                         │
│ 0️⃣ Volver al paso anterior             │
└─────────────────────────────────────────┘
```

---

## 📋 RUTA 3: REGISTRO DE DATOS DEL PACIENTE

### **Estado:** `CLIENT_REGISTER`

**Cuándo se activa:**
- Usuario nuevo agenda su primera cita
- Después de confirmar profesional y horario
- Antes de confirmar la cita definitivamente

```
┌─────────────────────────────────────────┐
│ 🤖 Registro de Paciente                 │
│                                         │
│ Para completar tu cita, necesitamos     │
│ algunos datos:                          │
│                                         │
│ 📝 Paso 1 de 4: Nombre completo         │
│                                         │
│ ¿Cuál es tu nombre completo?            │
│ (o el nombre del paciente si agendás    │
│ para otra persona)                      │
│                                         │
│ Ejemplo: María González                 │
│                                         │
│ 0️⃣ Cancelar                            │
└─────────────────────────────────────────┘
```

**Secuencia de registro:**

```python
REGISTRATION_STEPS = [
    {
        'field': 'name',
        'question': '¿Cuál es tu nombre completo?',
        'validation': 'min_length:3, max_length:100',
        'required': True
    },
    {
        'field': 'email',
        'question': '¿Cuál es tu email?',
        'validation': 'email_format',
        'required': False,
        'can_skip': True
    },
    {
        'field': 'age',
        'question': '¿Cuál es tu edad?',
        'validation': 'integer, min:1, max:120',
        'required': False,
        'can_skip': True
    },
    {
        'field': 'has_prepaga',
        'question': '¿Tenés obra social o prepaga?',
        'type': 'boolean',
        'options': ['1. Sí', '2. No'],
        'required': False,
        'can_skip': True
    }
]
```

**Con opción de saltar:**

```
┌─────────────────────────────────────────┐
│ 📧 Paso 2 de 4: Email (opcional)        │
│                                         │
│ ¿Cuál es tu email?                      │
│                                         │
│ Te enviaremos confirmación de tu cita   │
│ y recordatorios.                        │
│                                         │
│ Ejemplo: maria@ejemplo.com              │
│                                         │
│ • Escribí tu email                      │
│ • o enviá "saltar" para omitir          │
│                                         │
│ 0️⃣ Volver                              │
└─────────────────────────────────────────┘
```

---

## 📅 GESTIÓN DE CITAS

### **RUTA 4: CONFIRMAR CITA**

**Estado:** `CLIENT_APPOINTMENT_CONFIRM`

```
┌─────────────────────────────────────────┐
│ ✅ Confirmar Cita                       │
│                                         │
│ Tu cita está próxima:                   │
│                                         │
│ 📅 Fecha: 15 de diciembre de 2024       │
│ ⏰ Hora: 14:00 hs                       │
│ 👨‍⚕️ Profesional: Lic. Juan Pérez       │
│ 📍 Modalidad: Presencial                │
│ 🏢 Dirección: Av. Libertador 1234       │
│                                         │
│ Estado actual: Confirmada ✓             │
│                                         │
│ 1️⃣ Agregar al calendario               │
│ 2️⃣ Obtener indicaciones                │
│ 3️⃣ Contactar al profesional            │
│ 4️⃣ Reprogramar                         │
│ 5️⃣ Cancelar                            │
│                                         │
│ 0️⃣ Volver                              │
└─────────────────────────────────────────┘
```

---

### **RUTA 5: REPROGRAMAR CITA**

**Estado:** `CLIENT_APPOINTMENT_RESCHEDULE`

```
┌─────────────────────────────────────────┐
│ 🔄 Reprogramar Cita                     │
│                                         │
│ Cita actual:                            │
│ 📅 15/12/2024 a las 14:00               │
│ 👨‍⚕️ Con Lic. Juan Pérez                │
│                                         │
│ ¿Para qué fecha querés reprogramar?     │
│                                         │
│ Formato: DD/MM/YYYY                     │
│ Ejemplo: 20/12/2024                     │
│                                         │
│ 0️⃣ Cancelar                            │
└─────────────────────────────────────────┘
        ↓ [Usuario ingresa fecha]
┌─────────────────────────────────────────┐
│ Horarios disponibles el 20/12/2024:     │
│                                         │
│ 1️⃣ 10:00 - 10:50                       │
│ 2️⃣ 14:00 - 14:50                       │
│ 3️⃣ 16:00 - 16:50                       │
│                                         │
│ ❌ No hay horarios disponibles          │
│ Probá con otra fecha                    │
│                                         │
│ 0️⃣ Volver                              │
└─────────────────────────────────────────┘
        ↓ [Usuario elige horario]
┌─────────────────────────────────────────┐
│ ⚠️ Confirmar reprogramación             │
│                                         │
│ Cita original:                          │
│ • 15/12/2024 a las 14:00                │
│                                         │
│ Nueva cita:                             │
│ • 20/12/2024 a las 14:00                │
│                                         │
│ Se notificará al profesional.           │
│                                         │
│ ¿Confirmas el cambio?                   │
│ 1️⃣ Sí, confirmar                       │
│ 2️⃣ No, cancelar                        │
└─────────────────────────────────────────┘
```

---

### **RUTA 6: CANCELAR CITA**

**Estado:** `CLIENT_APPOINTMENT_CANCEL`

```
┌─────────────────────────────────────────┐
│ ❌ Cancelar Cita                        │
│                                         │
│ Vas a cancelar:                         │
│ 📅 15/12/2024 a las 14:00               │
│ 👨‍⚕️ Con Lic. Juan Pérez                │
│                                         │
│ ⚠️ Recordá que:                         │
│ • Con menos de 24hs de anticipación     │
│   podrías ser cobrado                   │
│ • El profesional será notificado        │
│                                         │
│ ¿Por qué motivo cancelás? (opcional)    │
│                                         │
│ 1️⃣ Tengo un imprevisto                 │
│ 2️⃣ Encontré otro profesional           │
│ 3️⃣ Ya no necesito la cita              │
│ 4️⃣ Otro motivo                         │
│ 5️⃣ Prefiero no decirlo                 │
│                                         │
│ 0️⃣ No cancelar (volver)                │
└─────────────────────────────────────────┘
        ↓ [Usuario selecciona motivo]
┌─────────────────────────────────────────┐
│ ⚠️ Confirmación final                   │
│                                         │
│ ¿Estás seguro/a que querés cancelar     │
│ tu cita del 15/12/2024?                 │
│                                         │
│ Esta acción no se puede deshacer.       │
│                                         │
│ 1️⃣ Sí, cancelar definitivamente        │
│ 2️⃣ No, mantener mi cita                │
└─────────────────────────────────────────┘
        ↓ [Confirmación]
┌─────────────────────────────────────────┐
│ ✅ Cita cancelada                       │
│                                         │
│ Tu cita ha sido cancelada exitosamente. │
│ El profesional ha sido notificado.      │
│                                         │
│ ¿Querés agendar otra cita?              │
│ 1️⃣ Sí, buscar otro horario             │
│ 2️⃣ No, gracias                         │
└─────────────────────────────────────────┘
```

---

### **RUTA 7: VER TODAS LAS CITAS**

**Estado:** `CLIENT_VIEW_ALL_APPOINTMENTS`

```
┌─────────────────────────────────────────┐
│ 📋 Mis Citas                            │
│                                         │
│ PRÓXIMAS CITAS:                         │
│                                         │
│ 1️⃣ 15/12/2024 a las 14:00              │
│    👨‍⚕️ Lic. Juan Pérez                 │
│    📍 Presencial                        │
│    ✅ Confirmada                        │
│                                         │
│ 2️⃣ 22/12/2024 a las 10:00              │
│    👩‍⚕️ Dra. María González             │
│    🖥️ Virtual                           │
│    ⏳ Pendiente de confirmación         │
│                                         │
│ CITAS PASADAS:                          │
│                                         │
│ • 08/12/2024 - Lic. Juan Pérez          │
│   ✅ Completada                         │
│                                         │
│ • 01/12/2024 - Dra. María González      │
│   ✅ Completada                         │
│                                         │
│ Seleccioná el número para ver detalles  │
│ o gestionar la cita                     │
│                                         │
│ 0️⃣ Volver                              │
└─────────────────────────────────────────┘
```

---

## 👨‍⚕️ FLUJOS DEL PROFESIONAL

### **FLUJO PROFESIONAL - Usuario Nuevo:**

```
┌─────────────────────────────────────────┐
│ Usuario nuevo envía:                    │
│ "Hola, soy profesional"                 │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ 🤖 ¡Bienvenido/a a Psico Connect!       │
│                                         │
│ Gracias por unirte a nuestra red de    │
│ profesionales.                          │
│                                         │
│ Para registrarte necesitamos:           │
│ 🔒 Tu matrícula profesional             │
│ 📝 Información básica                   │
│ 📅 Tu disponibilidad horaria            │
│                                         │
│ El proceso toma ~5 minutos.             │
│                                         │
│ 1️⃣ Comenzar registro                   │
│ 2️⃣ Más información                     │
│                                         │
│ 0️⃣ Volver                              │
└─────────────────────────────────────────┘
```

### **FLUJO PROFESIONAL - Usuario Registrado:**

```
┌─────────────────────────────────────────┐
│ 🤖 ¡Hola Dr. Juan! 👋                   │
│                                         │
│ 📊 Resumen de hoy:                      │
│ • 3 citas confirmadas                   │
│ • 2 solicitudes pendientes              │
│ • 5 búsquedas recibidas                 │
│                                         │
│ ¿Qué querés hacer?                      │
│ 1️⃣ Ver mi agenda de hoy                │
│ 2️⃣ Gestionar citas pendientes          │
│ 3️⃣ Actualizar disponibilidad           │
│ 4️⃣ Ver mis estadísticas                │
│ 5️⃣ Editar mi perfil                    │
│                                         │
│ 0️⃣ Salir                               │
└─────────────────────────────────────────┘
```

---

## 🧪 TESTING ACTUALIZADO

### **Suite de Tests v3.0:**

```python
class TestUserRecognition:
    """Tests de reconocimiento inteligente de usuarios."""
    
    def test_professional_returning(self):
        """Profesional registrado vuelve a escribir."""
        # Setup: Profesional ya registrado en BD
        phone = "+5491187654321"
        db.add_professional(phone, name="Dr. Juan Pérez", ...)
        
        # Test
        response = bot.process_message(phone, "hola")
        
        # Asserts
        assert "Dr. Juan" in response
        assert "agenda de hoy" in response
        assert "citas confirmadas" in response
    
    def test_client_with_appointments(self):
        """Cliente con citas próximas."""
        # Setup
        phone = "+5491112345678"
        db.add_client(phone, name="María González")
        db.create_appointment(
            client_phone=phone,
            professional_phone="+5491187654321",
            date="2024-12-15",
            start_time="14:00"
        )
        
        # Test
        response = bot.process_message(phone, "hola")
        
        # Asserts
        assert "María" in response
        assert "cita próxima" in response
        assert "15 de diciembre" in response
        assert "14:00" in response
    
    def test_new_user_professional_intention(self):
        """Usuario nuevo con intención de ser profesional."""
        phone = "+5491199999999"
        
        # Test
        response = bot.process_message(phone, "hola soy profesional")
        
        # Asserts
        assert "registrarte" in response.lower()
        assert "matrícula" in response.lower()
    
    def test_new_user_client_default(self):
        """Usuario nuevo solo dice 'hola' → cliente por defecto."""
        phone = "+5491188888888"
        
        # Test
        response = bot.process_message(phone, "hola")
        
        # Asserts
        assert "agendar una cita" in response.lower()
        assert "encontrar al profesional" in response.lower()


class TestDynamicFilters:
    """Tests de filtros dinámicos."""
    
    def test_filter_sequence_generation(self):
        """Generar secuencia de filtros desde config."""
        handler = AssistedSearchHandler()
        
        # Debe incluir solo filtros enabled
        enabled_ids = [f['id'] for f in FilterConfig.get_enabled_filters()]
        assert handler.filter_sequence == enabled_ids
    
    def test_required_filters_validation(self):
        """Validar que no se puede buscar sin filtros obligatorios."""
        session = SessionData("+5491112345678")
        session.store_temp('applied_filters', {
            'especialidad': 'tcc'
            # Falta fecha y horario (required=True)
        })
        
        handler = QuickSearchHandler()
        can_search = handler.can_perform_search(session)
        
        assert can_search == False
    
    def test_dependent_filters(self):
        """Filtro 'zona' solo aparece si modalidad=presencial."""
        session = SessionData("+5491112345678")
        session.store_temp('applied_filters', {
            'modalidad': 'virtual'
        })
        
        handler = AssistedSearchHandler()
        next_filter = handler.get_next_filter(session)
        
        # No debe pedir 'zona' si es virtual
        assert next_filter['id'] != 'zona'


class TestAppointmentManagement:
    """Tests de gestión de citas."""
    
    def test_reschedule_flow(self):
        """Flujo completo de reprogramación."""
        # Setup
        phone = "+5491112345678"
        appointment_id = db.create_appointment(...)
        
        # Test: Iniciar reprogramación
        bot.process_message(phone, "hola")
        bot.process_message(phone, "2")  # Reprogramar
        
        response = bot.process_message(phone, "20/12/2024")
        assert "Horarios disponibles" in response
        
        response = bot.process_message(phone, "1")  # Elegir horario
        assert "Confirmar reprogramación" in response
        
        response = bot.process_message(phone, "1")  # Confirmar
        assert "reprogramada" in response.lower()
        
        # Verificar en BD
        updated = db.get_appointment(appointment_id)
        assert updated['appointment_date'] == '2024-12-20'
    
    def test_cancel_with_reason(self):
        """Cancelar cita con motivo."""
        phone = "+5491112345678"
        appointment_id = db.create_appointment(...)
        
        bot.process_message(phone, "hola")
        bot.process_message(phone, "3")  # Cancelar
        bot.process_message(phone, "1")  # Motivo: imprevisto
        response = bot.process_message(phone, "1")  # Confirmar
        
        assert "cancelada" in response.lower()
        
        # Verificar en BD
        appointment = db.get_appointment(appointment_id)
        assert appointment['status'] == 'cancelada_cliente'
        assert appointment['cancellation_reason'] == 'imprevisto'


class TestThirdPartyBooking:
    """Tests de agendamiento para terceros."""
    
    def test_booking_for_other_person(self):
        """Agendar cita para otra persona."""
        phone = "+5491112345678"
        
        bot.process_message(phone, "hola")
        bot.process_message(phone, "1")  # Agendar cita
        response = bot.process_message(phone, "2")  # Para otra persona
        
        assert "nombre del paciente" in response.lower()
        
        bot.process_message(phone, "Pedro González")
        # ... continuar flujo
        
        # Verificar que el appointment tiene booking_for='other'
```

---

## 📊 MEJORAS EN ANALYTICS

### **Nueva Tabla: user_actions**

```sql
CREATE TABLE user_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone TEXT NOT NULL,
    user_type TEXT CHECK(user_type IN ('client', 'professional')),
    action_type TEXT, -- 'search', 'book', 'cancel', 'reschedule', 'view_profile'
    action_details TEXT, -- JSON con detalles
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (phone) REFERENCES user_registry(phone)
);
```

### **Tracking de acciones:**

```python
def log_user_action(phone: str, action_type: str, details: dict = None):
    """Registra acción del usuario para analytics."""
    db.execute("""
        INSERT INTO user_actions (phone, user_type, action_type, action_details)
        VALUES (?, ?, ?, ?)
    """, (
        phone,
        identify_user(phone)['user_type'],
        action_type,
        json.dumps(details) if details else None
    ))

# Ejemplos de uso:
log_user_action(phone, 'search', {
    'filters': {'zona': 'norte', 'especialidad': 'tcc'},
    'results_count': 5
})

log_user_action(phone, 'book', {
    'professional_phone': '+549...',
    'date': '2024-12-15',
    'booking_for': 'self'
})

log_user_action(phone, 'cancel', {
    'appointment_id': 123,
    'reason': 'imprevisto',
    'hours_before': 48
})
```

---

## 📝 RESUMEN DE MEJORAS v3.0

### **1. Reconocimiento Inteligente ✅**
- BD identifica usuario automáticamente
- Contexto personalizado según historial
- Detección de intención en lenguaje natural

### **2. Filtros Dinámicos ✅**
- Configuración centralizada en domain_config
- Fácil agregar/quitar filtros
- Filtros condicionales (dependent_on)
- Búsqueda rápida y asistida

### **3. Gestión Completa de Citas ✅**
- Confirmar, reprogramar, cancelar
- Motivo de cancelación
- Notificaciones bidireccionales
- Historial de cambios

### **4. Agendamiento para Terceros ✅**
- Cliente puede agendar para otra persona
- Campos: booking_for, patient_name, patient_phone
- Validaciones específicas

### **5. UX Mejorada ✅**
- Mensajes contextuales según estado del usuario
- Progreso visible en búsqueda asistida
- Confirmaciones claras
- Opciones de saltar pasos opcionales

---

**¿Próximos pasos?**
1. Revisar y aprobar estas mejoras
2. Implementar cambios en código
3. Testing exhaustivo
4. Deploy progresivo

---

**Versión:** 3.0
**Última actualización:** Diciembre 2024
**Estado:** En revisión
