# 🏗️ ARQUITECTURA DEL PROYECTO
## Sistema de Agenda y Reservas - WhatsApp Bot

---

## 📋 ÍNDICE

1. [Visión General](#visión-general)
2. [Estructura del Proyecto](#estructura-del-proyecto)
3. [Integraciones Externas](#integraciones-externas)
4. [Capas de la Aplicación](#capas-de-la-aplicación)
5. [Flujo de Datos](#flujo-de-datos)
6. [Base de Datos](#base-de-datos)
7. [Guía de Desarrollo](#guía-de-desarrollo)
8. [Convenciones de Código](#convenciones-de-código)
9. [Testing](#testing)
10. [Deployment](#deployment)

---

## 📊 VISIÓN GENERAL

### **¿Qué es este proyecto?**

Sistema de gestión de citas y reservas para centros de salud, implementado como un bot conversacional de WhatsApp. Permite:

- **Clientes**: Buscar profesionales con disponibilidad en tiempo real y reservar citas
- **Profesionales**: Gestionar horarios a través de Google Calendar
- **Centro**: Analytics y gestión centralizada

### **Stack Tecnológico**

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
│     Bot Logic (State Machine)       │
└──────────────┬──────────────────────┘
               │
    ┌──────────┴──────────┐
    │                     │
┌───▼─────────┐   ┌──────▼──────────┐
│  Services   │   │  Google Calendar │
│   Layer     │   │   Integration    │
└───┬─────────┘   └──────┬──────────┘
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
- **Container**: Docker + Docker Compose
- **Testing**: pytest

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
│   │
│   ├── 📁 services/                     # Servicios de lógica de negocio
│   │   ├── __init__.py
│   │   ├── user_service.py              # Identificación y contexto de usuarios
│   │   ├── client_service.py            # Búsqueda de profesionales con Google Calendar
│   │   ├── professional_service.py      # Gestión de profesionales y horarios
│   │   ├── analytics_service.py         # Métricas y analytics
│   │   └── appointment_service.py       # Gestión de citas (CRUD, confirmaciones)
│   │
│   ├── 📁 filters/                      # ⭐ Sistema de filtros modular
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
│   ├── 📁 integrations/                 # ⭐ Integraciones externas
│   │   │
│   │   └── 📁 google_calendar_service/  # ⭐ Google Calendar Integration
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
│   │   ├── domain_filters_config.py     # ⭐ Configuración de filtros (habilitados/orden)
│   │   │
│   │   └── 📁 google/                   # ⭐ Configuración de Google Calendar
│   │       ├── service-account.json     # ⭐ Credenciales de Service Account (gitignored)
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
│       ├── states.py                    # State machine y gestión de sesiones
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
│   ├── load_professionals_from_csv.py   # ⭐ Carga masiva desde CSV
│   └── configure_google_calendar.py     # ⭐ Configurar Google Calendar para profesionales
│
├── 📁 docker/                           # Configuración Docker
│   ├── Dockerfile                       # Imagen Docker
│   ├── docker-compose.yml               # Orquestación de servicios
│   └── docker-entrypoint.sh             # ⭐ Script de inicio (carga automática de CSV)
│
├── 📁 data/                             # Datos persistentes
│   ├── booking.db                       # Base de datos SQLite
│   └── certificates/                    # Certificados de profesionales
│       └── {phone}/                     # Un directorio por profesional
│
├── 📁 docs/                             # Documentación
│   ├── ARCHITECTURE.md                  # Este archivo
│   ├── GOOGLE_CALENDAR_SERVICE.md       # ⭐ Documentación de Google Calendar
│   ├── DATABASE.md                      # Esquema de base de datos
│   ├── API.md                           # Documentación de API
│   ├── README_WHATSAPP.md               # Guía de WhatsApp/Twilio
│   └── DEPLOYMENT.md                    # Guía de deployment
│
├── profesionales_demo.csv               # ⭐ CSV con profesionales de prueba (raíz)
├── .env                                 # Variables de entorno (gitignored)
├── .env.example                         # Template de variables de entorno
├── .gitignore                           # Archivos ignorados por git
├── requirements.txt                     # Dependencias de Python
├── pytest.ini                           # Configuración de pytest
└── README.md                            # Documentación principal
```

### **Métricas del Proyecto:**
- **Total líneas de código**: ~12,000+
- **Archivos Python**: ~35+
- **Archivo más grande**: ~2,280 líneas (client_handler.py)
- **Modularidad**: Alta (separación de concerns)
- **Integraciones**: Google Calendar API, Twilio WhatsApp API

---

## 🔗 INTEGRACIONES EXTERNAS

### **1. Google Calendar API** ⭐ NUEVO

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
6. Retorna respuesta a Twilio
   ↓
7. Twilio envía respuesta a usuario en WhatsApp
```

---

### **2. Capa Bot (Lógica Conversacional)**

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

### **3. Capa Services (Lógica de Negocio)**

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
- Métodos principales:
  - `search_professionals_by_filters()` - Busca y filtra por disponibilidad
  - `format_search_results_with_slots()` - Formatea lista con horarios
  - `format_professional_detail_with_slots()` - Muestra detalle completo

#### **professional_service.py** ⭐ ACTUALIZADO
- Gestión de profesionales y perfiles
- Integración directa con GoogleCalendarService
- Métodos principales:
  - `get_available_slots()` - Obtiene slots desde Google Calendar
  - `setup_google_calendar()` - Configura calendario para profesional
  - `validate_calendar_access()` - Verifica acceso al calendario

#### **appointment_service.py** (Pendiente FASE 2)
- Creación de citas en Google Calendar
- Sincronización bidireccional
- Cancelaciones y reprogramaciones

---

### **4. Capa Integrations (Servicios Externos)** ⭐ NUEVO

**Ubicación:** `src/integrations/`

**Responsabilidad:** Integración con APIs externas

#### **google_calendar_service/** ⭐

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

---

### **5. Sistema de Filtros Modular** ⭐ NUEVO

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

### **6. Capa Database (Persistencia)**

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

#### **3. Configurar docker-compose.yml:**
```yaml
services:
  whatsapp-demo:
    environment:
      - FLASK_ENV=development  # Activa carga automática de CSV
    volumes:
      - ./data:/app/data
      - ./config:/app/config
      - ./profesionales_demo.csv:/app/data/profesionales_demo.csv  # ⭐
```

#### **4. Iniciar:**
```bash
cd docker
docker-compose up --build
```

**El entrypoint automáticamente:**
1. Inicializa la BD
2. Carga profesionales desde CSV (si BD vacía)
3. Valida configuración de Google Calendar
4. Muestra estadísticas

#### **5. Verificar:**
```bash
# Ver profesionales cargados
docker exec whatsapp-demo sqlite3 /app/data/booking.db \
  "SELECT phone, name, calendar_id FROM professionals;"

# Ver logs
docker-compose logs -f
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