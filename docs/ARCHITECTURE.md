# 🏗️ ARQUITECTURA DEL PROYECTO
## Sistema de Agenda y Reservas - WhatsApp Bot

---

## 📋 ÍNDICE

1. [Visión General](#visión-general)
2. [Estructura del Proyecto](#estructura-del-proyecto)
3. [Sistema NLU/ML](#sistema-nluml) ⭐ NUEVO
4. [Integraciones Externas](#integraciones-externas)
5. [Capas de la Aplicación](#capas-de-la-aplicación)
6. [Performance y Métricas](#performance-y-métricas) ⭐ NUEVO
7. [Flujo de Datos](#flujo-de-datos)
8. [Base de Datos](#base-de-datos)
9. [Guía de Desarrollo](#guía-de-desarrollo)
10. [Setup y Deployment](#setup-y-deployment)
11. [Testing](#testing)
12. [Roadmap](#roadmap)
---

## 📊 VISIÓN GENERAL

### **¿Qué es este proyecto?**

Sistema de gestión de citas y reservas para centros de salud, implementado como un bot conversacional de WhatsApp. Permite:

- **Clientes**: Buscar profesionales con disponibilidad en tiempo real y reservar citas
- **Profesionales**: Gestionar horarios a través de Google Calendar
- **Centro**: Analytics y gestión centralizada

### **Stack Tecnológico v4.0**
```
┌─────────────────────────────────────┐
│     WhatsApp (Twilio API)           │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│     Flask Webhook (Python)          │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│   ⭐ NLU/ML Layer (v4.0)            │
│   ┌────────────────────────────┐   │
│   │ Hybrid Intent Detector     │   │
│   │ - ML (spaCy) 98.1% acc ⭐  │   │
│   │ - Rules fallback           │   │
│   │ - Text normalization       │   │
│   └────────────────────────────┘   │
│                                    │
│   ┌────────────────────────────┐   │
│   │ Entity Extractor           │   │
│   │ - Extrae entidades         │   │
│   │ - Fuzzy name matching ⭐   │   │
│   │ - Validaciones             │   │
│   └────────────────────────────┘   │
│                                    │
│   ┌────────────────────────────┐   │
│   │ Context Manager            │   │
│   │ - Acumula entidades        │   │
│   │ - Mantiene historial       │   │
│   │ - Provee contexto a ML     │   │
│   └────────────────────────────┘   │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│     Bot Logic (State Machine)       │
└──────────────┬──────────────────────┘
               │
    ┌──────────┴──────────┐
    │                     │
┌───▼─────────┐   ┌──────▼──────────────┐
│  Services   │   │  Google Calendar    │
│   Layer     │   │   Integration       │
│             │   │  ┌───────────────┐  │
│ ⭐ Cache   │   │  │ Availability  │  │
│  Manager    │←──┼──│ Checker       │  │
│ (15min TTL) │   │  └───────────────┘  │
│             │   │  ┌───────────────┐  │
│             │   │  │ Event Manager │  │
│             │   │  └───────────────┘  │
└───┬─────────┘   └──────┬──────────────┘
    │                     │
┌───▼─────────────────────▼──────────┐
│     SQLite Database                │
└────────────────────────────────────┘
```

**Tecnologías:**
- **Backend**: Python 3.10+
- **Framework**: Flask (webhook)
- **Messaging**: Twilio WhatsApp API
- **Database**: SQLite
- **Calendar**: Google Calendar API (Service Account)
- **ML/NLP**: spaCy 3.7.2 + es_core_news_sm ⭐
- **Cache**: Thread-safe in-memory cache (15min TTL) ⭐
- **Container**: Docker + Docker Compose
- **Testing**: pytest

**Componentes v4.0:**
- **Hybrid Intent Detection**: 98.1% accuracy (ML + Rules)
- **Fuzzy Name Matching**: 85% similarity threshold
- **Cache Manager**: 15min TTL, 80-90% hit rate
- **Text Normalization**: Contracciones, typos, títulos
- **Parallel Queries**: ThreadPoolExecutor para calendarios

---

## 📂 ESTRUCTURA DEL PROYECTO

```
booking-chatbot/
│
├── 📁 src/                              # Código de la aplicación
│   │
│   ├── 📁 bot/                          # Lógica conversacional del bot
│   │   ├── __init__.py
│   │   ├── bot_controller.py            # Orquestador principal (~300 líneas)
│   │   ├── client_handler.py            # Handler de flujo de clientes (~2280 líneas)
│   │   ├── professional_handler.py      # Handler de flujo de profesionales (~800 líneas)
│   │   └── admin_handler.py             # Handler de administración (~200 líneas)
│   ├── 📁 cron/                         # Tareas programadas
│   │   ├── __init__.py
│   │   └── daily_reminder_job.py        # Job diario de recordatorios (17:30)
│   │
│   ├── 📁 services/                     # Servicios de lógica de negocio
│   │   ├── __init__.py
│   │   ├── intent_detector.py           # Detección de intenciones (NLU)
│   │   ├── user_service.py              # Identificación y contexto de usuarios
│   │   ├── client_service.py            # Búsqueda con filtro por nombre
│   │   ├── professional_service.py      # Gestión de profesionales y horarios
│   │   ├── analytics_service.py         # Métricas y analytics
│   │   └── appointment_service.py       # Gestión de citas (CRUD, confirmaciones)
│   │
│   ├── 📁 filters/                      # Sistema de filtros modular
│   │   ├── __init__.py
│   │   ├── filter_types.py              # Enums y tipos de filtros
│   │   ├── base_filter.py               # Clase base abstracta para filtros
│   │   ├── filter_manager.py            # Gestor central de filtros
│   │   │
│   │   └── 📁 concrete_filters/         # Implementaciones de filtros
│   │       ├── __init__.py
│   │       ├── core_filters.py          # DateFilter, TimeFilter, SpecialtyFilter
│   │       └── optional_filters.py      # ZoneFilter, PrepagaFilter, GenderFilter, etc.
│   │
│   ├── 📁 integrations/                 # Integraciones externas
│   │   ├── 📁 ml/
│   │   │   ├── ml_intent_detec.py
│   │   │   └── hybrid_intent_detector.py
│   │   │
│   │   └── 📁 google_calendar_service/  # Google Calendar Integration
│   │       ├── __init__.py
│   │       ├── google_calendar_service.py      # Interfaz principal
│   │       │
│   │       ├── 📁 auth/                 # Autenticación
│   │       │   ├── __init__.py
│   │       │   └── auth_manager.py      # Gestión de Service Account
│   │       │
│   │       ├── 📁 calendar/             # Operaciones de calendario
│   │       │   ├── __init__.py
│   │       │   ├── calendar_client.py   # Cliente base de Google Calendar API
│   │       │   ├── availability_checker.py  # Cálculo de disponibilidad
│   │       │   └── event_manager.py     # Gestión de eventos (crear/cancelar)
│   │       │
│   │       ├── 📁 config/               # Configuración
│   │       │   ├── __init__.py
│   │       │   └── settings.py          # Parámetros de Google Calendar
│   │       │
│   │       ├── 📁 models/               # Modelos de datos
│   │       │   ├── __init__.py
│   │       │   └── time_slot.py         # Representación de slots de tiempo
│   │       │
│   │       ├── 📁 utils/                # Utilidades
│   │       │   ├── __init__.py
│   │       │   └── timezone_helper.py   # Manejo de zonas horarias
│   │       │
│   │       ├── 📁 tests/                # Tests del módulo
│   │       │   ├── __init__.py
│   │       │   ├── test_connection.py
│   │       │   └── test_availability.py
│   │       │
│   │       └── requirements.txt         # Dependencias específicas
│   │
│   ├── 📁 database/                     # Capa de acceso a datos
│   │   ├── __init__.py
│   │   └── database.py                  # Conexión y operaciones de BD (~1481 líneas)
│   │
│   ├── 📁 api/                          # Capa de presentación (webhooks)
│   │   ├── __init__.py
│   │   └── whatsapp_handler.py          # Flask webhook + Twilio integration
│   │
│   ├── 📁 config/                       # Configuración
│   │   ├── __init__.py
│   │   ├── settings.py                  # Settings generales (env vars, etc.)
│   │   ├── domain_config.py             # Configuración de dominios/presets
│   │   ├── domain_filters_config.py     # Configuración de filtros (habilitados/orden)
│   │   │
│   │   └── 📁 google/                   # Configuración de Google Calendar
│   │       ├── service-account.json     # Credenciales de Service Account (gitignored)
│   │       └── service-account.json.example  # Template de credenciales
│   │
│   ├── 📁 messages/                     # Templates de mensajes
│   │   ├── __init__.py
│   │   ├── messages_common.py           # Mensajes comunes
│   │   ├── messages_client.py           # Flujo cliente
│   │   ├── messages_professional.py     # Flujo profesional
│   │   └── messages_appointments.py     # Sistema de citas
│   │
│   └── 📁 core/                         # Componentes core compartidos
│       ├── __init__.py
│       ├── states.py                    # Estados de cancelación agregados
│       ├── conversation_context.py      # Context Manager para acumulación
│       └── validators.py                # Validaciones de entrada
│
├── 📁 tests/                            # Tests automatizados
│   ├── __init__.py
│   ├── test_bot.py                      # Tests del bot
│   ├── test_database.py                 # Tests de base de datos
│   ├── test_services.py                 # Tests de servicios
│   ├── test_integration.py              # Tests de integración
│   └── test_bot_interactive.py          # Tests interactivos manuales
│
├── 📁 scripts/                          # Scripts de utilidad
│   ├── init_db.py                       # Inicializar base de datos
│   ├── migrate_db.py                    # Migraciones de BD
│   ├── verify_db.py                     # Verificar estructura de BD
│   ├── setup_domain.py                  # Configurar dominio
│   ├── seed_professionals.py            # Datos de prueba de profesionales
│   ├── load_professionals_from_csv.py   # Carga masiva desde CSV
│   └── configure_google_calendar.py     # Configurar Google Calendar para profesionales
│
├── 📁 docker/                           # Configuración Docker
│   ├── Dockerfile                       # Imagen Docker
│   ├── docker-compose.yml               # Orquestación de servicios
│   └── docker-entrypoint.sh             # Script de inicio (carga automática de CSV)
│
├── 📁 data/                             # Datos persistentes
│   ├── booking.db                       # Base de datos SQLite
│   └── certificates/                    # Certificados de profesionales
│       └── {phone}/                     # Un directorio por profesional
│
├── 📁 docs/                             # Documentación
│   ├── ARCHITECTURE.md                  # Este archivo
│   ├── GOOGLE_CALENDAR_SERVICE.md       # Documentación de Google Calendar
│   ├── DATABASE.md                      # Esquema de base de datos
│   ├── API.md                           # Documentación de API
│   ├── README_WHATSAPP.md               # Guía de WhatsApp/Twilio
│   └── DEPLOYMENT.md                    # Guía de deployment
│
├── profesionales_demo.csv               # CSV con profesionales de prueba (raíz)
├── .env                                 # Variables de entorno (gitignored)
├── .env.example                         # Template de variables de entorno
├── .gitignore                           # Archivos ignorados por git
├── requirements.txt                     # Dependencias de Python
├── pytest.ini                           # Configuración de pytest
└── README.md                            # Documentación principal
```

### **Métricas del Proyecto:**

**Código:**
- **Total líneas de código**: ~15,000+ (+3,000 desde v3.1)
- **Archivos Python**: ~40+ (+5 nuevos)
- **Archivo más grande**: ~2,280 líneas (client_handler.py)
- **Nuevo en v3.2**: 
  - intent_detector.py: ~715 líneas
  - conversation_context.py: ~200 líneas
  - Modificaciones: ~150 líneas

**Modularidad:** 
- Alta separación de concerns
- NLU independiente de lógica de negocio
- Preparado para migración a ML

**Integraciones:**
- Google Calendar API
- Twilio WhatsApp API
- ⭐ Sistema NLU (preparado para GPT-4)

**Performance v3.2:**
- Búsquedas 4x más rápidas (con filtro de nombre)
- 3x menos mensajes (con shortcuts)
- 100% validación de fechas pasadas

---

## 🔗 INTEGRACIONES EXTERNAS

### **1. Google Calendar API**

**Propósito:** Gestión de disponibilidad y reservas en tiempo real

**Ubicación:** `src/integrations/google_calendar_service/`

**Flujo de integración:**
```
1. Cliente busca profesionales disponibles
   ↓
2. client_service consulta availability_checker
   ↓
3. availability_checker obtiene eventos de Google Calendar
   ↓
4. Calcula slots libres (horario laboral - eventos ocupados)
   ↓
5. Retorna slots disponibles al cliente
   ↓
6. Cliente selecciona slot y confirma
   ↓
7. event_manager crea evento en Google Calendar
   ↓
8. Profesional recibe notificación automática de Google
```

**Componentes principales:**
- **GoogleCalendarService**: Interfaz unificada (fachada)
- **AuthManager**: Autenticación con Service Account
- **CalendarClient**: Cliente base de Google Calendar API
- **AvailabilityChecker**: Cálculo de disponibilidad en tiempo real
- **EventManager**: Creación y gestión de eventos (citas)

**Configuración requerida:**
1. Proyecto en Google Cloud Console
2. Google Calendar API habilitada
3. Service Account creada
4. Archivo `config/google/service-account.json`
5. Calendarios compartidos con Service Account

**Ver documentación completa:** `docs/GOOGLE_CALENDAR_SERVICE.md`

---

### **2. Twilio WhatsApp API**

**Propósito:** Interfaz conversacional con usuarios

**Ubicación:** `src/api/whatsapp_handler.py`

**Configuración requerida:**
- Account SID
- Auth Token  
- WhatsApp Sandbox Number (desarrollo)
- WhatsApp Business Number (producción)

**Ver documentación completa:** `docs/README_WHATSAPP.md`

---

## 🧠 SISTEMA NLU/ML (NATURAL LANGUAGE UNDERSTANDING) ⭐ v4.0

### **Propósito:**
Permitir que el bot entienda lenguaje natural y extraiga información automáticamente, reduciendo pasos conversacionales mediante un sistema híbrido de Machine Learning + Reglas.

### **Ubicación:**
- **ML Intent Detector:** `src/integrations/ml/hybrid_intent_detector.py` (~400 líneas) ⭐
- **Entity Extractor:** `src/services/intent_detector.py` (~715 líneas)
- **Context Manager:** `src/services/conversation_context.py` (~200 líneas)

---

### **1. Hybrid Intent Detector** ⭐ NUEVO v4.0

**Responsabilidades:**
- Detectar intención usando modelo ML (spaCy) con 98.1% accuracy
- Fallback a reglas si confidence < 0.7
- Normalizar texto (contracciones, typos, títulos)
- Integrar con extractor de entidades

**Arquitectura:**
```
Mensaje → Normalización → ML Prediction (spaCy)
   ↓
confidence ≥ 0.7 → Use ML intent
confidence < 0.7 → Fallback to Rules
   ↓
Entity Extraction → Context Integration → Return
```

**Modelo ML:**
- Framework: spaCy 3.7.2
- Dataset: 80 base + ~970 augmented = 1,050 ejemplos
- Accuracy: 98.1% (best epoch 19/30)
- Training time: ~3-4 minutos

**Intenciones soportadas:**
```python
class Intent(Enum):
    SEARCH_PROFESSIONAL = "search_professional"  # Buscar profesional
    VIEW_TOMORROW = "view_tomorrow"              # Ver disponibles mañana
    VIEW_MY_APPOINTMENTS = "view_my_appointments" # Ver mis turnos
    CANCEL_APPOINTMENT = "cancel_appointment"    # Cancelar turno
    RESCHEDULE_APPOINTMENT = "reschedule_appointment" # Reprogramar
    CONFIRM_APPOINTMENT = "confirm_appointment"  # Confirmar turno
    UNKNOWN = "unknown"                          # No detectado
```

**Normalización de texto:** ⭐
```python
# Input: "teno q ver al dotor blanco xa mañana"
# Después de normalización: "tengo que ver al doctor blanco para mañana"

Contracciones:
- teno q → tengo que
- xa → para
- pa → para
- xq → porque

Títulos:
- dotor → doctor
- lic → licenciado
- dr → doctor
- dra → doctora

Días:
- lune → lunes
- mier → miércoles
```

**Ejemplo de uso:**
```python
from src.integrations.ml.hybrid_intent_detector import HybridIntentDetector

detector = HybridIntentDetector()
result = detector.detect("necesito psicóloga mujer para mañana", context)

# Output:
{
    'intent': Intent.SEARCH_PROFESSIONAL,
    'confidence': 0.98,  # ML prediction
    'source': 'ml',      # 'ml' o 'rules'
    'entities': {...}    # Extraídas por intent_detector.py
}
```

---

### **2. Entity Extractor**

**Responsabilidades:**
- Extraer entidades del mensaje normalizado
- Fuzzy matching de nombres profesionales (85% threshold) ⭐
- Validar fechas (rechazar fechas pasadas)
- Convertir formatos (fecha → YYYY-MM-DD)

**Entidades extraídas:**
| Entidad | Tipo | Ejemplos | v4.0 |
|---------|------|----------|------|
| `especialidad` | string | 'psicología', 'nutrición' | ✅ |
| `fecha` | string | 'hoy', 'mañana', '2026-02-15' | ✅ |
| `horario` | string | 'mañana', 'tarde', 'noche' | ✅ |
| `zona` | string | 'norte', 'sur', 'centro' | ✅ |
| `modalidad` | string | 'presencial', 'virtual' | ✅ |
| `genero` | string | 'masculino', 'femenino' | ✅ |
| `prepaga` | boolean | True si menciona obra social | ✅ |
| `professional_name` | string | 'gaston blanco' (fuzzy) | ⭐ NUEVO |

**Fuzzy Name Matching:** ⭐ NUEVO
```python
# Input: "quiero turno con fernandes"
# DB: ["Dr. Roberto García", "Lic. Juan Fernández", "Gaston Blanco"]

1. Normalizar: "fernandes" → "fernandes" (sin acentos)
2. Comparar con DB:
   - "roberto garcia" → 45% similar ❌
   - "juan fernandez" → 89% similar ✅
   - "gaston blanco" → 25% similar ❌
3. Mejor match: "Lic. Juan Fernández" (89% > 85% threshold)

# Output: professional_name = "juan fernandez"
```

**Técnicas de detección:**
- **ML Intent:** spaCy model con 98.1% accuracy ⭐
- **Keywords:** Lista de palabras clave por entidad
- **Regex:** Fechas (DD/MM/YYYY), horarios (HH:MM)
- **Fuzzy matching:** Nombres profesionales (85% threshold) ⭐
- **Normalización:** Ignora acentos, mayúsculas, contracciones ⭐

**Ejemplo completo:**
```python
# Usuario: "teno q ver al dotor blanco xa mañana tarde"

result = intent_detector.detect(message, context)

# Output:
{
    'intent': Intent.SEARCH_PROFESSIONAL,
    'confidence': 0.98,
    'entities': {
        'professional_name': 'gaston blanco',  # ⭐ Fuzzy match
        'fecha': '2026-02-09',                 # Convertido a YYYY-MM-DD
        'horario': 'tarde'
    },
    'can_shortcut': True
}
```

---

### **3. Context Manager**

**Responsabilidades:**
- Acumular entidades entre múltiples mensajes
- Mantener historial conversacional (últimos 10 mensajes)
- Proveer contexto para ML model
- Resetear contexto cuando cambia de intención

**Clase principal: `ConversationContext`**
```python
class ConversationContext:
    def __init__(self, phone_number: str):
        self.phone_number = phone_number
        self.accumulated_entities = {}      # Entidades acumuladas
        self.conversation_history = []      # Historial de mensajes
        self.current_intent = None          # Intent activo
        self.last_search_filters = {}       # Última búsqueda
```

**API pública:**
```python
# Obtener contexto
conv_context = context_manager.get_context(phone_number)

# Acumular entidades (merge=True combina, merge=False reemplaza)
conv_context.update_entities({'especialidad': 'nutrición'}, merge=True)
conv_context.update_entities({'fecha': 'mañana'}, merge=True)

# Obtener todas las entidades acumuladas
entities = conv_context.get_entities()  
# → {'especialidad': 'nutrición', 'fecha': 'mañana'}

# Obtener historial para ML
history = conv_context.get_history_text(last_n=5)
# → "User: busco nutricionista\nIntent: search_professional\n..."

# Limpiar entidades
conv_context.clear_entities()

# Resetear todo
conv_context.reset()
```

**Ejemplo de flujo con acumulación:**
```python
# Mensaje 1
Usuario: "busco nutricionista"
conv_context.update_entities({'especialidad': 'nutrición'})
# Acumulado: {'especialidad': 'nutrición'}

# Mensaje 2
Usuario: "para mañana"
conv_context.update_entities({'fecha': 'mañana'})
# Acumulado: {'especialidad': 'nutrición', 'fecha': 'mañana'}

# Mensaje 3
Usuario: "por la tarde"
conv_context.update_entities({'horario': 'tarde'})
# Acumulado: {'especialidad': 'nutrición', 'fecha': 'mañana', 'horario': 'tarde'}

# ✅ Suficiente información → Ejecutar búsqueda
```

---

### **4. Integración en bot_controller.py**

**Flujo de procesamiento v4.0:**
```python
def process_message(self, phone_number: str, message: str) -> str:
    # 1. Obtener sesión
    session = session_manager.get_session(phone_number)
    
    # 2. Obtener contexto conversacional
    conv_context = context_manager.get_context(phone_number)
    
    # 3. ⭐ NUEVO v4.0: Detectar intent con ML híbrido
    if session.state in nlu_enabled_states:
        intent_result = hybrid_detector.detect(message, context={
            'conversation_history': conv_context.get_history_text()
        })
        
        # Logs de debug
        print(f"[ML] Intent: {intent_result['intent']} (conf: {intent_result['confidence']:.2f})")
        print(f"[ML] Source: {intent_result['source']}")  # 'ml' o 'rules'
        print(f"[ML] Entities: {intent_result['entities']}")
        
        # 4. Acumular entidades
        if intent_result['entities']:
            conv_context.update_entities(intent_result['entities'], merge=True)
            accumulated = conv_context.get_entities()
            
            # 5. Decidir si ejecutar shortcut
            if self._can_execute_search(accumulated):
                return self._execute_smart_search(session, accumulated)
            else:
                return self._ask_for_missing_entity(session, accumulated)
    
    # 6. Flujo tradicional si no hay shortcut
    handler = self.get_handler_for_state(session.state)
    return handler(session, message)
```

**Estados donde NLU está activo:**
```python
nlu_enabled_states = [
    ConversationState.START,
    ConversationState.CLIENT_MAIN_MENU,
    ConversationState.CLIENT_NEW_USER_MENU,
    ConversationState.CLIENT_MULTIFILTER_MENU,
    ConversationState.CLIENT_SHOW_RESULTS,
    ConversationState.CLIENT_FILTER_INPUT,
]
```

---

### **5. Optimización: Búsqueda por Nombre + Cache** ⭐

**Ubicación:** `client_service.search_professionals_by_filters()`

**Mejoras implementadas v4.0:**

#### **A. Filtrado en BD antes de Google Calendar**
Cuando el usuario busca un profesional específico por nombre:
1. **Filtra en BD** con fuzzy matching (85% threshold)
2. **Reduce API calls** drásticamente
3. **Cache de disponibilidad** (15min TTL)

**Ejemplo:**
```python
Usuario: "quiero turno con gastón blanco"

# Sin optimización (v3.2):
[CLIENT] Found 4 professionals in DB
[CLIENT] Checking 4 calendars... → 4 API calls × 8 seg = 32 seg

# Con optimización (v4.0):
[CLIENT] Found 4 professionals in DB
[CLIENT] 🎯 Fuzzy match: 'gastón blanco' → 'Gaston Blanco' (100%)
[CLIENT] 🚀 Reduced to 1 professional
[CACHE] ❌ MISS: checking Google Calendar...
[CLIENT] Checking 1 calendar... → 1 API call × 8 seg = 8 seg

# Segunda consulta (cache hit):
[CACHE] ✅ HIT: returning cached slots → ~50ms

# Mejora: 4x más rápido (primera vez), 640x más rápido (cache hit) ✅
```

#### **B. Normalización y Fuzzy Matching**
```python
import unicodedata
from difflib import SequenceMatcher

def normalize_text(text):
    """Quita acentos y convierte a minúsculas."""
    nfd = unicodedata.normalize('NFD', text)
    without_accents = ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')
    return without_accents.lower()

def similarity(a: str, b: str) -> float:
    """Retorna similaridad 0.0-1.0"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

# Matching:
normalize_text("Gastón Blanco") == normalize_text("gaston blanco")  # ✅ True
similarity("fernandes", "fernandez") >= 0.85  # ✅ True (89%)
```

---

### **6. Validaciones P0 Implementadas**

#### **A. Validación de Fechas Pasadas**

**Ubicación:** `intent_detector._extract_fecha()`
```python
# Detecta "ayer" y lo marca como fecha pasada
if fecha_key == 'ayer':
    print(f"[NLU] ⚠️ 'ayer' es fecha pasada, rechazando")
    return 'fecha_pasada'

# Valida fechas absolutas
if date_obj.date() < datetime.now().date():
    print(f"[NLU] ⚠️ Fecha en el pasado rechazada: {date_str}")
    return 'fecha_pasada'
```

**Respuesta al usuario:**
```python
if fecha_entity == 'fecha_pasada':
    return ("⚠️ La fecha que ingresaste ya pasó.\n\n"
           "Por favor elige una fecha futura:\n"
           "• 'hoy'\n"
           "• 'mañana'\n"
           "• 'DD/MM/YYYY'")
```

#### **B. Sistema de Cancelación Completo**

**Nuevos estados agregados en `states.py`:**
```python
CLIENT_CONFIRM_CANCEL = "client_confirm_cancel"  # Confirmar cancelación
CLIENT_SELECT_CANCEL = "client_select_cancel"     # Seleccionar turno a cancelar
```

**Handlers conectados en `bot_controller.py`:**
```python
handlers = {
    # ... handlers existentes ...
    ConversationState.CLIENT_CONFIRM_CANCEL: self.client_service.handle_confirm_cancel,
    ConversationState.CLIENT_SELECT_CANCEL: self.client_service.handle_select_cancel,
}
```

**Flujos soportados:**
1. **Un solo turno:** Confirmación directa
2. **Múltiples turnos:** Selección numérica
3. **Sin turnos:** Mensaje informativo

**Backend ya implementado:**
- `get_user_appointments(phone_number)` - Obtiene turnos del usuario
- `cancel_appointment(appointment_id, reason)` - Cancela en BD
- `delete_calendar_event(event_id)` - Elimina de Google Calendar

---

### **7. Performance y Métricas**

**Mejoras de v4.0 (ML + Optimizaciones):**

| Métrica | v3.2 (Rules) | v4.0 (ML) | Mejora |
|---------|--------------|-----------|--------|
| API calls (búsqueda por nombre) | 4 calls | 1 call | **4x más rápido** |
| Mensajes para búsqueda completa | 4-6 | 1-2 | **3x menos** |
| Tiempo de interacción | ~2 min | ~30 seg | **4x más rápido** |
| Cobertura de validaciones | 60% | 100% | **+40%** |
| **Intent detection accuracy** | **85% (rules)** | **98.1% (ML)** | **+13%** ⭐ |
| **Consultas Google Calendar** | **32 seg** | **8-10 seg (miss)** | **3-4x más rápido** ⭐ |
| **Cache hit (segunda consulta)** | **N/A** | **~50ms** | **640x más rápido** ⭐ |
| **Cache hit rate** | **0%** | **80-90%** | **Nuevo** ⭐ |

**Mejoras ML v4.0:**
- ✅ **Hybrid System**: ML (70% threshold) + Rules fallback
- ✅ **Fuzzy Name Matching**: 85% similarity threshold vs DB
- ✅ **Text Normalization**: Contracciones, typos, títulos abreviados
- ✅ **Cache Manager**: 15min TTL, thread-safe, parallel queries
- ✅ **Dataset**: 80 base examples → ~1,050 with augmentation
- ✅ **Accuracy**: 98.1% (best epoch 19/30)
- ✅ **Training time**: ~3-4 minutos

**Líneas de código agregadas v4.0:**

| Componente | Líneas | Descripción |
|------------|--------|-------------|
| `hybrid_intent_detector.py` | ~400 | Sistema híbrido ML + Rules ⭐ |
| `intent_detector.py` (entities) | ~715 | Extracción de entidades |
| `conversation_context.py` | ~200 | Gestor de contexto |
| `cache_manager.py` | ~250 | Cache de disponibilidad ⭐ |
| `dataset_base.py` | ~320 | 80 ejemplos de entrenamiento ⭐ |
| `data_augmentation_v3.py` | ~982 | Generador de variaciones ⭐ |
| `train_spacy_model.py` | ~180 | Script de entrenamiento ⭐ |
| Modificaciones `bot_controller.py` | ~150 | Integración ML |
| **Total nuevo código v4.0** | **~3,197 líneas** | |

---
## 📊 CARGA DE DATOS

### **CSV de Profesionales** ⭐ NUEVO

**Ubicación:** `profesionales_demo.csv` (raíz del proyecto)

**Formato del CSV:**
```csv
phone,name,email,zone,gender,calendar_id,working_hours,slot_duration,specialties
+5491112345678,Dra. María González,maria@example.com,norte,f,maria.gonzalez@gmail.com,"{""start"": ""09:00"", ""end"": ""18:00""}",50,TCC|Ansiedad|Depresión
+5491187654321,Lic. Juan Pérez,juan@example.com,sur,m,juan.perez@gmail.com,"{""start"": ""10:00"", ""end"": ""19:00""}",60,Terapia de Pareja|Familia
```

**Campos obligatorios:**
- `phone`: Teléfono con código de país (+549...)
- `name`: Nombre completo
- `email`: Email de contacto
- `calendar_id`: Email del calendario de Google ⭐ CRÍTICO
- `zone`: norte|sur|este|oeste|centro
- `gender`: m|f|otro

**Campos opcionales:**
- `working_hours`: JSON con horario laboral
- `slot_duration`: Duración de slots en minutos (default: 50)
- `specialties`: Especialidades separadas por |
- `prepagas`: Obras sociales aceptadas
- `address`: Dirección física
- `bio`: Biografía

**Carga automática en Docker:**

El script `docker-entrypoint.sh` detecta automáticamente el CSV en modo desarrollo:

```bash
# 1. Montar CSV en docker-compose.yml
volumes:
  - ./profesionales_demo.csv:/app/data/profesionales_demo.csv

# 2. Iniciar contenedor (carga automática)
docker-compose up

# 3. Verificar carga
docker exec whatsapp-demo sqlite3 /app/data/booking.db \
  "SELECT phone, name, calendar_id FROM professionals;"
```

**Carga manual:**
```bash
# Copiar CSV al contenedor
docker cp profesionales_demo.csv whatsapp-demo:/app/data/

# Ejecutar script de carga
docker exec whatsapp-demo python scripts/load_professionals_from_csv.py \
  /app/data/profesionales_demo.csv
```

**Script de carga:** `scripts/load_professionals_from_csv.py`

---

## 🔄 CAPAS DE LA APLICACIÓN

### **1. Capa API (Presentación)**
**Ubicación:** `src/api/`
**Responsabilidad:** Recibir mensajes de WhatsApp y enviar respuestas

**Componentes:**
- `whatsapp_handler.py`: Flask webhook que recibe POST requests de Twilio

**Flujo:**
```
1. Usuario envía mensaje en WhatsApp
   ↓
2. Twilio recibe mensaje y hace POST a /webhook
   ↓
3. whatsapp_handler.py parsea el request
   ↓
4. Extrae phone y message
   ↓
5. Llama a bot_controller.process_message()
   ↓
6. Retorna respuesta a Twilio (TwiML)
   ↓
7. Twilio envía respuesta a usuario en WhatsApp
```

---

### **2. Capa de Inteligencia (NLU/ML)** ⭐
**Ubicación:** `src/integrations/ml/` + `src/services/`
**Responsabilidad:** Detectar intención y extraer entidades

**Componentes:**
- `hybrid_intent_detector.py`: Sistema híbrido ML + Rules (98.1% accuracy)
- `intent_detector.py`: Extracción de entidades (fecha, nombre, horario, etc.)
- `conversation_context.py`: Gestor de contexto conversacional

**Flujo:**
```
Mensaje: "teno q ver al dotor blanco xa mañana"
   ↓
1. Normalización de texto
   - Contracciones: "teno q" → "tengo que", "xa" → "para"
   - Títulos: "dotor" → "doctor"
   ↓
2. Extracción de entidades
   - Fecha: "mañana" → 2026-02-09
   - Profesional: "blanco" → fuzzy match DB → "Gaston Blanco"
   ↓
3. Detección de intent (ML)
   - spaCy model: confidence ≥ 0.7 → Use ML
   - confidence < 0.7 → Fallback to Rules
   ↓
4. Integración con contexto
   - Merge con entidades previas
   - Verificar info completa
   ↓
Return: {
    intent: "search_professional",
    confidence: 0.98,
    entities: {fecha: "2026-02-09", professional_name: "gaston blanco"},
    can_shortcut: true
}
```

**Intents Soportados:** search_professional, view_tomorrow, view_my_appointments, cancel_appointment, reschedule_appointment, confirm_appointment, unknown

---

### **3. Capa Bot (Lógica Conversacional)**

**Ubicación:** `src/bot/`

**Responsabilidad:** Gestionar el flujo de conversación y estados

**Componentes:**

#### **bot_controller.py** (Orquestador)
- Punto de entrada único: `process_message(phone, message)`
- Identifica tipo de usuario con `user_service`
- Delega a handler correspondiente según rol

#### **client_handler.py** (Flujo Clientes)
- Maneja búsqueda de profesionales con disponibilidad en tiempo real ⭐
- Estados: `CLIENT_SEARCH_*`, `CLIENT_BOOKING_*`, `CLIENT_VIEW_*`
- Usa `client_service` para búsquedas con Google Calendar

#### **professional_handler.py** (Flujo Profesionales)
- Maneja registro y configuración de profesionales
- Configuración de Google Calendar
- Estados: `PROF_*`

**State Machine:**
```
Estados del Cliente (con Google Calendar):
IDLE 
  → CLIENT_MAIN_MENU
  → CLIENT_SEARCH_DATE (¿Para cuándo?)
  → CLIENT_SEARCH_TIME (¿Mañana/Tarde/Noche?)
  → CLIENT_SEARCH_ZONA (¿Dónde?)
  → CLIENT_SHOW_RESULTS (Lista con slots disponibles) ⭐
  → CLIENT_VIEW_DETAIL (Detalle + todos los horarios) ⭐
  → CLIENT_BOOKING_CONFIRM_NAME
  → CLIENT_BOOKING_CONFIRM_EMAIL
  → CLIENT_BOOKING_FINAL_CONFIRMATION
  → [Crear evento en Google Calendar] ⭐

Estados del Profesional:
IDLE 
  → PROF_MENU 
  → PROF_REGISTER 
  → PROF_SETUP_CALENDAR (Configurar Google Calendar) ⭐
  → PROF_SCHEDULE 
  → ...
```

---

### **4. Capa Services (Lógica de Negocio)**

**Ubicación:** `src/services/`

**Responsabilidad:** Implementar lógica de negocio y orquestar operaciones

**Servicios principales:**

#### **user_service.py**
- Identificación de usuarios (profesional/cliente/nuevo)
- Detección de intención en mensajes
- Generación de mensajes de bienvenida contextuales

#### **client_service.py** ⭐ ACTUALIZADO
- Búsqueda de profesionales con disponibilidad en tiempo real
- Integración con Google Calendar vía `professional_service`
- Formateo de resultados con slots disponibles
- **Cache de disponibilidad (15min TTL)** ⭐
- **Consultas paralelas (ThreadPoolExecutor)** ⭐
- **Fuzzy matching de nombres (85% threshold)** ⭐
- Métodos principales:
  - `search_professionals_by_filters()` - Busca y filtra por disponibilidad
  - `format_search_results_with_slots()` - Formatea lista con horarios
  - `format_professional_detail_with_slots()` - Muestra detalle completo

#### **professional_service.py** ⭐ ACTUALIZADO
- Gestión de profesionales y perfiles
- Integración directa con GoogleCalendarService
- Métodos principales:
  - `get_available_slots()` - Obtiene slots desde Google Calendar con cache ⭐
  - `setup_google_calendar()` - Configura calendario para profesional
  - `validate_calendar_access()` - Verifica acceso al calendario

#### **appointment_service.py** (Pendiente FASE 2)
- Creación de citas en Google Calendar
- Sincronización bidireccional
- Cancelaciones y reprogramaciones

#### **cache_manager.py** ⭐ NUEVO
- Cache thread-safe de disponibilidad
- TTL: 15 minutos
- Invalidación automática
- Métodos:
  - `get(calendar_id, date)` - Obtener slots cacheados
  - `set(calendar_id, date, slots)` - Guardar en cache
  - `invalidate(calendar_id, date)` - Limpiar cache

---

### **5. Capa Integrations (Servicios Externos)**

**Ubicación:** `src/integrations/`

**Responsabilidad:** Integración con APIs externas

#### **google_calendar_service/**

**Estructura modular:**
```
google_calendar_service/
├── google_calendar_service.py    # Fachada/Interfaz principal
├── auth/
│   └── auth_manager.py            # Service Account authentication
├── calendar/
│   ├── calendar_client.py         # Cliente base de Calendar API
│   ├── availability_checker.py    # Cálculo de disponibilidad
│   └── event_manager.py           # Crear/cancelar eventos
├── models/
│   └── time_slot.py               # Modelo de slot de tiempo
└── utils/
    └── timezone_helper.py         # Manejo de zonas horarias
```

**Uso desde servicios:**
```python
from src.integrations.google_calendar_service import GoogleCalendarService

calendar_service = GoogleCalendarService()

# Obtener slots disponibles
slots = calendar_service.get_available_slots(
    calendar_id='profesional@gmail.com',
    date='2025-01-17',
    working_hours={'start': '09:00', 'end': '18:00'},
    slot_duration_minutes=50
)

# Crear cita
event = calendar_service.create_appointment(
    calendar_id='profesional@gmail.com',
    start_datetime='2025-01-17T14:00:00-03:00',
    end_datetime='2025-01-17T14:50:00-03:00',
    client_name='Juan Pérez',
    client_phone='+5491112345678'
)
```

#### **ml/** ⭐ NUEVO

**Ubicación:** `src/integrations/ml/`

**Componentes:**
- `hybrid_intent_detector.py`: Sistema híbrido ML + Rules
  - Modelo spaCy (98.1% accuracy)
  - Fallback a rules si confidence < 0.7
  - 7 intents soportados

**Scripts de entrenamiento:**

**Ubicación:** `scripts/ml/`
- `dataset_base.py`: 80 ejemplos base
- `data_augmentation_v3.py`: Generador de variaciones (~970)
- `generate_training_dataset.py`: Combina base + augmentation
- `train_spacy_model.py`: Entrena modelo spaCy
- `evaluate_spacy_model.py`: Evalúa accuracy
- `README.md`: Documentación completa de entrenamiento

---

### **6. Sistema de Filtros Modular** ⭐

**Ubicación:** `src/filters/`

**Propósito:** Sistema extensible y configurable para filtrar búsquedas de profesionales

**Arquitectura:**

```
┌─────────────────────────────────────────────────────────┐
│  domain_filters_config.py (Configuración)               │
│  - Define qué filtros están habilitados                 │
│  - Orden de aparición en menús                          │
│  - Filtros obligatorios vs opcionales                   │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────┐
│  FilterManager (Gestor Central)                         │
│  - Carga filtros desde configuración                    │
│  - Genera menús dinámicamente                           │
│  - Valida filtros obligatorios                          │
│  - Convierte a parámetros de BD                         │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────┐
│  BaseFilter (Clase Abstracta)                           │
│  - get_menu_option_text()                               │
│  - get_input_prompt()                                   │
│  - validate_input()                                     │
│  - process_input()                                      │
│  - convert_to_db_param()                                │
└──────────────────┬──────────────────────────────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
┌───────▼────────┐   ┌────────▼──────────┐
│ Core Filters   │   │ Optional Filters  │
│ - DateFilter   │   │ - ZoneFilter      │
│ - TimeFilter   │   │ - PrepagaFilter   │
│ - SpecialtyF.  │   │ - GenderFilter    │
└────────────────┘   │ - ModalityFilter  │
                     └───────────────────┘
```

**Componentes:**

#### **filter_types.py**
Define enums y tipos base:
```python
class FilterType(Enum):
    DATE = "date"
    TIME = "time"
    SPECIALTY = "specialty"
    ZONE = "zone"
    PREPAGA = "prepaga"
    GENDER = "gender"
    MODALITY = "modality"

class FilterCategory(Enum):
    CORE = "core"           # Filtros esenciales
    OPTIONAL = "optional"   # Filtros opcionales
    ADVANCED = "advanced"   # Filtros avanzados

class FilterPriority(Enum):
    REQUIRED = 1      # Debe completarse antes de buscar
    RECOMMENDED = 2   # Recomendado pero no obligatorio
    OPTIONAL = 3      # Completamente opcional
```

#### **base_filter.py**
Clase abstracta que define la interfaz común para todos los filtros.

#### **filter_manager.py**
Gestor central que:
- Carga filtros habilitados desde configuración
- Genera menús dinámicos con checkmarks
- Valida filtros obligatorios antes de buscar
- Convierte filtros a parámetros de BD

#### **concrete_filters/core_filters.py**
Filtros esenciales:
- **DateFilter**: Fecha del turno (Hoy/Mañana/DD/MM/YYYY directa)
- **TimeFilter**: Horario (Mañana/Tarde/HH:MM directa)
- **SpecialtyFilter**: Especialidad (dinámico desde DomainConfig)

#### **concrete_filters/optional_filters.py**
Filtros opcionales:
- **ZoneFilter**: Zona geográfica (Norte/Sur/Cualquiera)
- **PrepagaFilter**: Obra social (Sí/No/Cualquiera)
- **GenderFilter**: Género del profesional (M/F/Cualquiera)
- **ModalityFilter**: Presencial/Virtual (deshabilitado por defecto)

**Configuración en `config/domain_filters_config.py`:**

```python
ENABLED_FILTERS = {
    FilterType.DATE: {
        'enabled': True,
        'menu_position': 1,
        'category': FilterCategory.CORE,
        'priority': FilterPriority.REQUIRED,
    },
    FilterType.MODALITY: {
        'enabled': False,  # ✅ Deshabilitar sin tocar código
        'menu_position': 7,
        # ...
    }
}

REQUIRED_FILTERS = [FilterType.DATE]  # Obligatorios antes de buscar
```

**Integración con client_handler.py:**

Antes (6+ handlers repetitivos):
```python
def handle_client_multifilter_zona(...): # ~30 líneas
def handle_client_multifilter_fecha(...): # ~30 líneas
def handle_client_multifilter_hora(...): # ~30 líneas
def handle_client_multifilter_prepaga(...): # ~30 líneas
def handle_client_multifilter_sexo(...): # ~30 líneas
def handle_client_multifilter_especialidad(...): # ~30 líneas
```

Ahora (1 handler genérico):
```python
def handle_client_filter_input(self, session, message):
    """Handler genérico para TODOS los filtros."""
    filter_manager = FilterManager()
    filter_obj = filter_manager.get_filter(filter_type)
    
    # Validar, procesar y guardar
    is_valid, error = filter_obj.validate_input(message)
    if is_valid:
        processed = filter_obj.process_input(message)
        session.store_temp('filters', {filter_type.value: processed})
```

**Ventajas:**
- ✅ Agregar/quitar filtros editando solo configuración
- ✅ Reducción de ~180 líneas a ~40 líneas
- ✅ Validaciones centralizadas por filtro
- ✅ Fácil testear filtros individuales
- ✅ Reutilizable en otros proyectos
- ✅ UX mejorado (entrada directa de fecha/hora)

**Ejemplo de flujo completo:**
```
Usuario: 1 (selecciona búsqueda)
Bot: Muestra menú con filtros habilitados desde config

Usuario: 1 (selecciona Fecha)
Bot: DateFilter.get_input_prompt()
     "1️⃣ Hoy  2️⃣ Mañana  💡 O ingresa DD/MM/YYYY directamente"

Usuario: 30/01/2026 (entrada directa, sin paso extra)
Bot: DateFilter.validate_input() ✓
     DateFilter.process_input() → {'date': '2026-01-30', 'display': '30/01/2026'}
     Guarda en session.temp['filters']['date']
     Vuelve al menú mostrando "📅 Fecha: 30/01/2026"

Usuario: 2 (selecciona Horario)
Bot: TimeFilter.get_input_prompt()

Usuario: 14:30 (entrada directa)
Bot: Guarda y muestra "🕐 Horario: A las 14:30"

Usuario: 9 (buscar)
Bot: FilterManager.validate_required_filters() ✓
     FilterManager.convert_to_db_params() 
     → {'available_date': '2026-01-30', 'specific_time': '14:30'}
     client_service.search_professionals_by_filters(**params)
```

---

### **7. Capa Database (Persistencia)**

**Ubicación:** `src/database/`

**Responsabilidad:** Acceso a datos y operaciones CRUD

**Base de datos:** SQLite (`data/booking.db`)

**Tablas principales:**
- `professionals` - Datos de profesionales + `calendar_id` ⭐
- `clients` - Datos de clientes
- `appointments` - Citas (con `google_event_id` para sincronización) ⭐
- `client_searches` - Analytics de búsquedas
- `weekly_schedule` - Horarios semanales (DEPRECADO en favor de Google Calendar)
- `specific_free_slots` - Slots específicos (DEPRECADO)

**Campos nuevos en `professionals`:**
```sql
calendar_id TEXT,              -- Email del calendario de Google ⭐
working_hours TEXT,            -- JSON: {"start": "09:00", "end": "18:00"}
slot_duration INTEGER,         -- Duración de slots en minutos
timezone TEXT,                 -- Zona horaria (America/Argentina/Buenos_Aires)
```

**Campos nuevos en `appointments` (Pendiente FASE 2):**
```sql
google_event_id TEXT,          -- ID del evento en Google Calendar ⭐
status TEXT,                   -- confirmed|cancelled|rescheduled
```

## 🔔 SISTEMA DE RECORDATORIOS AUTOMÁTICOS

### **Descripción**

Sistema automatizado que envía recordatorios de citas 24 horas antes por WhatsApp, permite confirmar/reprogramar, y registra todas las interacciones.

### **Arquitectura**
```
CRON (17:30) → ReminderService → Twilio WhatsApp
                      ↓
                  Database
                      ↓
            Cliente recibe mensaje
                      ↓
            Bot procesa respuesta
```

### **Componentes**

**1. `src/services/reminder_service.py`**
- `send_daily_reminders()` - Ejecutada por CRON
- `handle_reminder_response()` - Procesa respuestas (1/2/0)
- `_send_reminder()` - Envía WhatsApp
- `_format_reminder_message()` - Formatea mensaje

**2. `src/cron/daily_reminder_job.py`**
- Script ejecutado diariamente a las 17:30
- Configuración CRON:
```bash
  30 17 * * * docker exec whatsapp-demo python -m src.cron.daily_reminder_job
```

**3. `src/bot/reminder_handler.py`**
- `should_handle_as_reminder()` - Detecta respuesta a recordatorio
- `handle_reminder_response()` - Procesa y enruta
- Integrado en `bot_controller.py` con prioridad máxima

### **Base de Datos**

**Nueva tabla:**
```sql
CREATE TABLE appointment_reminders (
    id INTEGER PRIMARY KEY,
    appointment_id INTEGER NOT NULL,
    sent_at TIMESTAMP,
    status TEXT,  -- sent | confirmed | rescheduled | cancelled
    confirmed_at TIMESTAMP,
    FOREIGN KEY (appointment_id) REFERENCES appointments(id)
);
```

**Columnas agregadas a `appointments`:**
```sql
reminder_sent BOOLEAN DEFAULT 0
confirmed_by_client BOOLEAN DEFAULT 0
confirmed_by_client_at TIMESTAMP
```

### **Flujo de Uso**

1. **17:30** - CRON ejecuta, busca citas para mañana
2. **Cliente recibe:** "🔔 RECORDATORIO... 1️⃣ Confirmar 2️⃣ Reprogramar 0️⃣ Cancelar"
3. **Cliente responde "1"** - Sistema marca `confirmed_by_client=1`
4. **Cliente recibe:** "✅ ¡Perfecto! Tu turno está confirmado."

### **Testing**
```bash
# Ejecutar manualmente
docker exec whatsapp-demo python -m src.services.reminder_service

# Ver logs
tail -f /var/log/reminders.log

# Métricas
docker exec whatsapp-demo sqlite3 /app/data/booking.db \
  "SELECT status, COUNT(*) FROM appointment_reminders GROUP BY status;"
```

### **Configuración**

Variables de entorno (ya existen):
```bash
TWILIO_ACCOUNT_SID=ACxxxx
TWILIO_AUTH_TOKEN=xxxx
TWILIO_WHATSAPP_NUMBER=+14155238886
```

### **Archivos del Sistema**

- ✅ `src/services/reminder_service.py` (~450 líneas)
- ✅ `src/cron/daily_reminder_job.py` (~60 líneas)  
- ✅ `src/bot/reminder_handler.py` (~120 líneas)

**Archivos modificados:**
- `src/bot/bot_controller.py` (+5 líneas)
- `src/session/session.py` (+1 estado)
- `src/database/database.py` (+20 líneas método)

---

## 🚀 SETUP Y DEPLOYMENT

### **Desarrollo Local con Docker**

#### **1. Configurar Google Calendar:**
```bash
# Copiar credenciales de Service Account
cp service-account.json config/google/

# Verificar que los profesionales compartan sus calendarios
# con: booking-service@proyecto.iam.gserviceaccount.com
```

#### **2. Preparar CSV de profesionales:**
```bash
# Asegurarse que profesionales_demo.csv tiene calendar_id
# Ejemplo:
# phone,name,email,calendar_id,...
# +5491112345678,María González,maria@ex.com,maria.gonzalez@gmail.com,...
```

#### **3. Entrenar modelo ML (opcional):** ⭐ NUEVO
```bash
# Si quieres re-entrenar el modelo desde cero
cd scripts/ml

# 1. Generar dataset
python generate_training_dataset.py
# Output: dataset_training.jsonl (~1,050 ejemplos)

# 2. Entrenar modelo
python train_spacy_model.py --data ../../dataset/dataset_training.jsonl
# Output: model/model-best/ (~50MB)

# 3. Verificar accuracy
cat training_report.json | grep "best_accuracy"
# Esperado: 0.98 o superior

# NOTA: El modelo pre-entrenado ya viene incluido en el repo
# Solo re-entrena si modificaste dataset_base.py
```

#### **4. Configurar docker-compose.yml:**
```yaml
services:
  whatsapp-demo:
    environment:
      - FLASK_ENV=development  # Activa carga automática de CSV
      - ML_CONFIDENCE_THRESHOLD=0.7  # ⭐ Threshold para ML vs Rules
    volumes:
      - ./data:/app/data
      - ./config:/app/config
      - ./profesionales_demo.csv:/app/data/profesionales_demo.csv
      - ./scripts/ml/intent_classifier/model:/app/scripts/ml/intent_classifier/model  # ⭐ Modelo ML
```

#### **5. Iniciar:**
```bash
cd docker
docker-compose up --build
```

**El entrypoint automáticamente:**
1. Inicializa la BD
2. Carga profesionales desde CSV (si BD vacía)
3. Valida configuración de Google Calendar
4. **Carga modelo ML (spaCy)** ⭐
5. **Inicializa cache manager** ⭐
6. Muestra estadísticas

#### **6. Verificar:**
```bash
# Ver profesionales cargados
docker exec whatsapp-demo sqlite3 /app/data/booking.db \
  "SELECT phone, name, calendar_id FROM professionals;"

# Verificar que modelo ML se cargó correctamente
docker-compose logs | grep "ML model loaded"
# Esperado: [ML] ✅ Model loaded: 98.1% accuracy

# Verificar cache inicializado
docker-compose logs | grep "CACHE"
# Esperado: [CACHE] 🚀 Initialized with TTL=15min

# Ver logs completos
docker-compose logs -f
```

---

### **Dependencias y Requirements**

#### **requirements.txt actualizado:** ⭐
```txt
# API & Web
Flask==3.0.0
twilio==8.10.0
python-dotenv==1.0.0

# Google Calendar
google-auth==2.23.4
google-auth-oauthlib==1.1.0
google-api-python-client==2.108.0

# Machine Learning ⭐ NUEVO
spacy==3.7.2
es-core-news-sm @ https://github.com/explosion/spacy-models/releases/download/es_core_news_sm-3.7.0/es_core_news_sm-3.7.0-py3-none-any.whl

# Database
# (SQLite viene incluido en Python)
```

#### **Instalación:**
```bash
# Opción 1: Docker (recomendado)
docker-compose up --build

# Opción 2: Local
pip install -r requirements.txt
python -m spacy download es_core_news_sm
```

---

### **Variables de Entorno (.env)**

```env
# Twilio
TWILIO_ACCOUNT_SID=xxx
TWILIO_AUTH_TOKEN=xxx
TWILIO_PHONE_NUMBER=+14155238886

# Google Calendar
GOOGLE_CALENDAR_CREDENTIALS_PATH=./config/google/service-account.json

# Flask
FLASK_ENV=development
PORT=5000

# Machine Learning ⭐ NUEVO
ML_CONFIDENCE_THRESHOLD=0.7          # Threshold para usar ML vs Rules
SPACY_MODEL_PATH=scripts/ml/intent_classifier/model/model-best
ML_ENABLED=true                       # Habilitar/deshabilitar ML

# Cache ⭐ NUEVO
CACHE_TTL_MINUTES=15                  # Tiempo de vida del cache
CACHE_ENABLED=true                    # Habilitar/deshabilitar cache
```

---

### **Troubleshooting**

#### **Problema: "ML model not found"**
```bash
# Verificar que existe el modelo
ls scripts/ml/intent_classifier/model/model-best/

# Si no existe, entrenar:
cd scripts/ml
python generate_training_dataset.py
python train_spacy_model.py --data ../../dataset/dataset_training.jsonl
```

#### **Problema: "spaCy model es_core_news_sm not found"**
```bash
# Instalar modelo base
python -m spacy download es_core_news_sm

# O en Docker, rebuild:
docker-compose down
docker-compose up --build
```

#### **Problema: Cache no funciona**
```bash
# Verificar logs de cache
docker-compose logs | grep CACHE

# Verificar que esté habilitado en .env
CACHE_ENABLED=true
```

#### **Problema: Accuracy del modelo <95%**
```bash
# Re-entrenar con más épocas
cd scripts/ml
# Editar config.cfg: max_epochs = 50
python train_spacy_model.py --data ../../dataset/dataset_training.jsonl

# Agregar más ejemplos a dataset_base.py
# Ver scripts/ml/README.md para detalles
```

---

### **Logs y Monitoreo**

```bash
# Ver logs en tiempo real
docker-compose logs -f

# Filtrar por componente
docker-compose logs -f | grep "ML"      # Solo ML
docker-compose logs -f | grep "CACHE"   # Solo cache
docker-compose logs -f | grep "NLU"     # Solo NLU/entity extraction

# Ver estadísticas de cache
docker exec whatsapp-demo python -c "
from src.services.cache_manager import cache_manager
print(cache_manager.get_stats())
"
```

---

### **Testing**

#### **Test completo del flujo:**
```bash
# 1. Enviar mensaje de prueba
curl -X POST http://localhost:5000/webhook \
  -d "From=whatsapp:+5491112345678" \
  -d "Body=turno con psicólogo mañana"

# 2. Verificar logs
docker-compose logs | tail -50

# Esperado:
# [NLU] Intent: search_professional (conf: 0.98)
# [NLU] Entities: {fecha: 'mañana', especialidad: 'psicología'}
# [CACHE] ❌ MISS: professional@gmail.com_2026-02-09_all
# [CLIENT] ✅ 3 professionals available
```

#### **Test de ML accuracy:**
```bash
cd scripts/ml
python evaluate_spacy_model.py

# Output esperado:
# Accuracy: 98.1%
# Precision: 97.8%
# Recall: 98.4%
```

#### **Test de cache:**
```bash
# Primera consulta (cache miss)
time curl -X POST http://localhost:5000/webhook \
  -d "From=whatsapp:+5491112345678" \
  -d "Body=disponibilidad mañana"

# Segunda consulta (cache hit - debería ser ~50ms)
time curl -X POST http://localhost:5000/webhook \
  -d "From=whatsapp:+5491112345678" \
  -d "Body=disponibilidad mañana"
```
---

## 🧪 TESTING

### **Tests de Google Calendar:**

```bash
# Tests unitarios (no requieren API)
pytest tests/integrations/google_calendar/ -m "not integration"

# Tests de integración (requieren credenciales)
pytest tests/integrations/google_calendar/ -m integration

# Script de prueba manual
docker exec whatsapp-demo python \
  src/integrations/google_calendar_service/tests/test_availability.py
```

### **Tests del bot:**

```bash
# Todos los tests
pytest tests/

# Tests específicos
pytest tests/test_services.py

# Con coverage
pytest --cov=src tests/
```

---

## 📝 PRÓXIMOS PASOS (ROADMAP)

### **FASE 1: Mostrar Horarios Disponibles** ✅ COMPLETADO
- [x] Implementar `get_available_slots()` en GoogleCalendarService
- [x] Integrar con `client_service.search_professionals_by_filters()`
- [x] Formatear resultados con slots en `client_handler`
- [x] Testing de búsqueda con disponibilidad real

### **FASE 2: Crear Turnos** 🚧 EN PROGRESO
- [ ] Implementar `create_appointment()` en GoogleCalendarService
- [ ] Crear `appointment_service.py`
- [ ] Agregar tabla `appointments` con `google_event_id`
- [ ] Flujo completo de reserva en `client_handler`
- [ ] Sincronización bidireccional

### **FASE 3: Gestión de Turnos**
- [ ] Cancelar turnos (BD + Google Calendar)
- [ ] Reprogramar turnos
- [ ] Vista "Mis Turnos" para clientes
- [ ] Vista de agenda para profesionales

### **FASE 4: Notificaciones**
- [ ] Email de confirmación
- [ ] Recordatorios automáticos (24hs, 1hr antes)
- [ ] Notificaciones por WhatsApp

---

## 🔑 VARIABLES DE ENTORNO

```bash
# Twilio WhatsApp
TWILIO_ACCOUNT_SID=ACxxxx
TWILIO_AUTH_TOKEN=xxxx
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

# Dominio
DOMAIN_PRESET=PSICOLOGIA  # o SALUD, BELLEZA, etc.

# Ambiente
FLASK_ENV=development  # Activa carga automática de CSV
ENVIRONMENT=development

# Google Calendar (opcional, se usa service-account.json)
# GOOGLE_CREDENTIALS_PATH=config/google/service-account.json
```

---

## 📚 DOCUMENTACIÓN ADICIONAL

- **Google Calendar Integration:** `docs/GOOGLE_CALENDAR_SERVICE.md`
- **WhatsApp/Twilio Setup:** `docs/README_WHATSAPP.md`
- **Database Schema:** `docs/DATABASE.md` (pendiente actualizar)
- **API Reference:** `docs/API.md`

---

**Versión:** 2.0  
**Última actualización:** 2025-01-16  
**Autor:** Booking Chatbot Project