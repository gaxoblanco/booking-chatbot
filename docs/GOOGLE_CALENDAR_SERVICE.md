# 🗓️ GOOGLE CALENDAR SERVICE
## Módulo de Gestión de Disponibilidad y Reservas

---

## 📋 ÍNDICE

1. [Visión General](#visión-general)
2. [Estructura del Módulo](#estructura-del-módulo)
3. [Componentes Principales](#componentes-principales)
4. [Flujo de Integración](#flujo-de-integración)
5. [Configuración Google API](#configuración-google-api)
6. [Guía de Desarrollo](#guía-de-desarrollo)
7. [Testing](#testing)
8. [Troubleshooting](#troubleshooting)

---

## 📊 VISIÓN GENERAL

### **¿Qué es este módulo?**

Servicio Python independiente que gestiona la sincronización bidireccional entre el sistema de reservas del chatbot y Google Calendar de los profesionales.

**Funcionalidades:**
- Consultar disponibilidad en tiempo real de profesionales
- Crear eventos de citas automáticamente
- Sincronizar cambios (cancelaciones, reprogramaciones)
- Evitar conflictos de doble reserva
- Manejo de múltiples calendarios (uno por profesional)

### **Stack Tecnológico**

```
┌─────────────────────────────────────┐
│     Chatbot (WhatsApp Bot)          │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│  Google Calendar Service (Este)     │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│     Google Calendar API              │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│  Calendarios de Profesionales       │
└─────────────────────────────────────┘
```

**Tecnologías:**
- **Python**: 3.10+
- **Google API Client**: `google-api-python-client`
- **Autenticación**: Service Account (OAuth 2.0)
- **Storage**: JSON local para cache de tokens
- **Testing**: pytest + pytest-mock

### **Principios de Diseño**

- ✅ **Simple**: Solo funciones esenciales
- ✅ **Desacoplado**: No depende del chatbot, se puede usar standalone
- ✅ **Sin costo**: Solo Google Calendar API (gratuita)
- ✅ **Testeable**: Cada componente mockeable
- ✅ **Resiliente**: Manejo de errores y reintentos

---

## 📂 ESTRUCTURA DEL MÓDULO

```
src/integrations/google_calendar/
│
├── __init__.py                      # Exporta interfaces públicas
│
├── 📁 auth/                         # Autenticación y credenciales
│   ├── __init__.py
│   ├── auth_manager.py              # Gestión de Service Account (~150 líneas)
│   └── credentials_loader.py        # Carga de credenciales desde archivos
│
├── 📁 calendar/                     # Operaciones de calendario
│   ├── __init__.py
│   ├── calendar_client.py           # Cliente base de Google Calendar API (~200 líneas)
│   ├── availability_checker.py      # Consulta de horarios disponibles (~250 líneas)
│   └── event_manager.py             # CRUD de eventos (crear, modificar, cancelar) (~300 líneas)
│
├── 📁 models/                       # Clases de datos
│   ├── __init__.py
│   ├── time_slot.py                 # Modelo de slot de tiempo
│   ├── appointment.py               # Modelo de cita
│   └── professional_config.py       # Configuración por profesional
│
├── 📁 config/                       # Configuración del servicio
│   ├── __init__.py
│   └── settings.py                  # Parámetros configurables
│
└── 📁 utils/                        # Utilidades
    ├── __init__.py
    ├── timezone_helper.py           # Manejo de zonas horarias (~100 líneas)
    └── retry_handler.py             # Lógica de reintentos para API calls
```

### **Métricas del Módulo:**
- **Total líneas de código estimado**: ~1,500
- **Archivos Python**: ~15
- **Archivo más grande**: ~300 líneas
- **Dependencias externas**: 3 (google-api-python-client, google-auth, pytz)

---

## 🔧 COMPONENTES PRINCIPALES

### **1. Auth Manager** (`auth/auth_manager.py`)

**Responsabilidad:** Gestionar autenticación con Google API usando Service Account

**Funcionalidades:**
- Cargar credenciales de Service Account
- Generar tokens de acceso
- Refrescar tokens expirados
- Validar permisos sobre calendarios

**Uso:**
```python
from src.integrations.google_calendar.auth import AuthManager

# Inicializar con archivo de credenciales
auth_manager = AuthManager(credentials_path='config/service-account.json')

# Obtener credenciales autenticadas
credentials = auth_manager.get_credentials()
```

**Configuración requerida:**
```json
// service-account.json (desde Google Cloud Console)
{
  "type": "service_account",
  "project_id": "tu-proyecto",
  "private_key_id": "...",
  "private_key": "...",
  "client_email": "service-account@tu-proyecto.iam.gserviceaccount.com",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token"
}
```

---

### **2. Calendar Client** (`calendar/calendar_client.py`)

**Responsabilidad:** Cliente base para interactuar con Google Calendar API

**Funcionalidades:**
- Conexión a la API
- Listar calendarios
- Operaciones básicas de lectura/escritura

**Uso:**
```python
from src.integrations.google_calendar.calendar import CalendarClient

# Inicializar cliente
client = CalendarClient(credentials)

# Listar calendarios del profesional
calendars = client.list_calendars()

# Obtener eventos de un calendario
events = client.get_events(
    calendar_id='profesional@gmail.com',
    time_min='2024-12-15T09:00:00Z',
    time_max='2024-12-15T18:00:00Z'
)
```

**Métodos principales:**
```python
class CalendarClient:
    def __init__(self, credentials)
    def list_calendars(self) -> List[Dict]
    def get_events(self, calendar_id, time_min, time_max) -> List[Dict]
    def create_event(self, calendar_id, event_data) -> Dict
    def update_event(self, calendar_id, event_id, event_data) -> Dict
    def delete_event(self, calendar_id, event_id) -> bool
```

---

### **3. Availability Checker** (`calendar/availability_checker.py`)

**Responsabilidad:** Calcular slots disponibles según eventos existentes

**Funcionalidades:**
- Consultar eventos en un rango de tiempo
- Calcular bloques libres según horario laboral
- Filtrar slots según duración de consulta
- Excluir horarios bloqueados

**Uso:**
```python
from src.integrations.google_calendar.calendar import AvailabilityChecker

checker = AvailabilityChecker(calendar_client)

# Obtener slots disponibles
available_slots = checker.get_available_slots(
    calendar_id='profesional@gmail.com',
    date='2024-12-15',
    working_hours={'start': '09:00', 'end': '18:00'},
    slot_duration_minutes=60  # Consultas de 1 hora
)

# Resultado:
# [
#   {'start': '09:00', 'end': '10:00'},
#   {'start': '14:00', 'end': '15:00'},
#   ...
# ]
```

**Lógica de disponibilidad:**
```python
class AvailabilityChecker:
    def get_available_slots(self, calendar_id, date, working_hours, slot_duration_minutes):
        """
        1. Obtener eventos existentes del día
        2. Crear lista de todos los slots posibles (ej: cada hora de 9 a 18)
        3. Eliminar slots que coinciden con eventos existentes
        4. Retornar lista de slots disponibles
        """
        pass
    
    def check_slot_available(self, calendar_id, start_time, end_time) -> bool:
        """
        Verificar si un slot específico está disponible
        """
        pass
```

---

### **4. Event Manager** (`calendar/event_manager.py`)

**Responsabilidad:** Crear y gestionar eventos de citas

**Funcionalidades:**
- Crear evento de cita con datos del cliente
- Cancelar cita (eliminar evento)
- Reprogramar cita (mover evento)
- Añadir descripción y recordatorios

**Uso:**
```python
from src.integrations.google_calendar.calendar import EventManager

event_manager = EventManager(calendar_client)

# Crear cita
event = event_manager.create_appointment(
    calendar_id='profesional@gmail.com',
    start_datetime='2024-12-15T14:00:00-03:00',
    end_datetime='2024-12-15T15:00:00-03:00',
    client_name='Juan Pérez',
    client_phone='+5491112345678',
    appointment_type='Consulta inicial'
)

# Cancelar cita
event_manager.cancel_appointment(
    calendar_id='profesional@gmail.com',
    event_id='abc123xyz'
)

# Reprogramar cita
event_manager.reschedule_appointment(
    calendar_id='profesional@gmail.com',
    event_id='abc123xyz',
    new_start='2024-12-16T10:00:00-03:00',
    new_end='2024-12-16T11:00:00-03:00'
)
```

**Formato de evento:**
```python
event_data = {
    'summary': 'Consulta - Juan Pérez',
    'description': f'Cliente: Juan Pérez\nTeléfono: +5491112345678\nTipo: Consulta inicial',
    'start': {
        'dateTime': '2024-12-15T14:00:00-03:00',
        'timeZone': 'America/Argentina/Buenos_Aires'
    },
    'end': {
        'dateTime': '2024-12-15T15:00:00-03:00',
        'timeZone': 'America/Argentina/Buenos_Aires'
    },
    'reminders': {
        'useDefault': False,
        'overrides': [
            {'method': 'email', 'minutes': 24 * 60},  # 1 día antes
            {'method': 'popup', 'minutes': 60}         # 1 hora antes
        ]
    }
}
```

---

### **5. Models** (`models/`)

**Clases de datos para estructurar información:**

```python
# models/time_slot.py
from dataclasses import dataclass
from datetime import datetime

@dataclass
class TimeSlot:
    """Representa un bloque de tiempo disponible"""
    start: datetime
    end: datetime
    duration_minutes: int
    
    def to_dict(self) -> dict:
        return {
            'start': self.start.isoformat(),
            'end': self.end.isoformat(),
            'duration_minutes': self.duration_minutes
        }


# models/appointment.py
@dataclass
class Appointment:
    """Representa una cita agendada"""
    event_id: str
    calendar_id: str
    start: datetime
    end: datetime
    client_name: str
    client_phone: str
    appointment_type: str
    status: str  # 'confirmed', 'cancelled', 'rescheduled'


# models/professional_config.py
@dataclass
class ProfessionalConfig:
    """Configuración de calendario del profesional"""
    calendar_id: str  # Email del calendario
    phone: str         # Teléfono del profesional en el sistema
    working_hours: dict  # {'monday': {'start': '09:00', 'end': '18:00'}, ...}
    slot_duration: int   # Duración de consulta en minutos
    timezone: str        # Ej: 'America/Argentina/Buenos_Aires'
```

---

## 🔄 FLUJO DE INTEGRACIÓN

### **Flujo 1: Cliente busca disponibilidad**

```
1. Cliente solicita horarios disponibles
   ↓
2. Chatbot llama a AvailabilityChecker.get_available_slots()
   ↓
3. Service consulta Google Calendar del profesional
   ↓
4. Se calculan slots libres según eventos existentes
   ↓
5. Service retorna lista de slots al chatbot
   ↓
6. Chatbot muestra opciones al cliente
```

**Código de integración:**
```python
# En el chatbot (client_handler.py)
from src.integrations.google_calendar import GoogleCalendarService

calendar_service = GoogleCalendarService()

# Obtener configuración del profesional
prof_config = db.get_professional_calendar_config(professional_phone)

# Consultar disponibilidad
slots = calendar_service.get_available_slots(
    calendar_id=prof_config['calendar_id'],
    date='2024-12-15',
    working_hours=prof_config['working_hours'],
    slot_duration=prof_config['slot_duration']
)

# Mostrar al cliente
for i, slot in enumerate(slots, 1):
    print(f"{i}. {slot['start']} - {slot['end']}")
```

---

### **Flujo 2: Cliente confirma cita**

```
1. Cliente elige horario
   ↓
2. Chatbot llama a EventManager.create_appointment()
   ↓
3. Service crea evento en Google Calendar
   ↓
4. Google Calendar notifica al profesional (email automático)
   ↓
5. Service retorna event_id al chatbot
   ↓
6. Chatbot guarda event_id en BD y confirma al cliente
```

**Código de integración:**
```python
# En el chatbot (appointment_service.py)
from src.integrations.google_calendar import GoogleCalendarService

calendar_service = GoogleCalendarService()

# Crear evento
event = calendar_service.create_appointment(
    calendar_id=prof_config['calendar_id'],
    start_datetime='2024-12-15T14:00:00-03:00',
    end_datetime='2024-12-15T15:00:00-03:00',
    client_name=client_name,
    client_phone=client_phone,
    appointment_type='Consulta inicial'
)

# Guardar en BD local
db.create_appointment(
    client_phone=client_phone,
    professional_phone=professional_phone,
    datetime='2024-12-15 14:00',
    google_event_id=event['id']  # Importante: guardar para sincronización
)
```

---

### **Flujo 3: Cancelación de cita**

```
1. Cliente cancela cita
   ↓
2. Chatbot obtiene event_id de BD
   ↓
3. Chatbot llama a EventManager.cancel_appointment()
   ↓
4. Service elimina evento de Google Calendar
   ↓
5. Google Calendar notifica al profesional
   ↓
6. Chatbot actualiza estado en BD
```

---

## ⚙️ CONFIGURACIÓN GOOGLE API

### **Paso 1: Crear Proyecto en Google Cloud**

1. Ir a [Google Cloud Console](https://console.cloud.google.com/)
2. Crear nuevo proyecto: "Booking-System-Calendar"
3. Habilitar Google Calendar API:
   - APIs & Services > Library
   - Buscar "Google Calendar API"
   - Click en "Enable"

### **Paso 2: Crear Service Account**

1. APIs & Services > Credentials
2. Create Credentials > Service Account
3. Nombre: "booking-system-service"
4. Rol: Sin rol (acceso solo a calendarios compartidos)
5. Done

### **Paso 3: Generar Clave JSON**

1. Click en la Service Account creada
2. Keys > Add Key > Create new key
3. Tipo: JSON
4. Descargar archivo `service-account.json`
5. Guardar en: `config/google/service-account.json`

### **Paso 4: Compartir Calendarios**

**Cada profesional debe:**
1. Abrir Google Calendar
2. Configuración > Mis calendarios > [Su calendario]
3. Compartir con personas específicas
4. Agregar email de Service Account: `booking-system-service@proyecto.iam.gserviceaccount.com`
5. Permisos: "Hacer cambios en eventos" (no "Propietario")

### **Paso 5: Configurar en el Sistema**

```python
# src/integrations/google_calendar/config/settings.py
import os

GOOGLE_CONFIG = {
    'credentials_path': os.getenv(
        'GOOGLE_CREDENTIALS_PATH',
        'config/google/service-account.json'
    ),
    'scopes': [
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/calendar.events'
    ],
    'api_version': 'v3',
    'retry_attempts': 3,
    'retry_delay_seconds': 2
}
```

### **Variables de Entorno:**

```bash
# .env
GOOGLE_CREDENTIALS_PATH=config/google/service-account.json
DEFAULT_TIMEZONE=America/Argentina/Buenos_Aires
```

---

## 🛠️ GUÍA DE DESARROLLO

### **Instalación de Dependencias:**

```bash
# Instalar librerías de Google
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib pytz

# O agregar a requirements.txt
google-api-python-client==2.108.0
google-auth==2.25.2
google-auth-httplib2==0.2.0
google-auth-oauthlib==1.2.0
pytz==2023.3
```

### **Inicialización del Servicio:**

```python
# src/integrations/google_calendar/__init__.py
from .auth.auth_manager import AuthManager
from .calendar.calendar_client import CalendarClient
from .calendar.availability_checker import AvailabilityChecker
from .calendar.event_manager import EventManager

class GoogleCalendarService:
    """
    Interfaz principal del servicio de Google Calendar.
    Fachada que simplifica el uso de los componentes internos.
    """
    
    def __init__(self, credentials_path=None):
        # Inicializar autenticación
        self.auth_manager = AuthManager(credentials_path)
        credentials = self.auth_manager.get_credentials()
        
        # Inicializar cliente base
        self.calendar_client = CalendarClient(credentials)
        
        # Inicializar componentes especializados
        self.availability = AvailabilityChecker(self.calendar_client)
        self.events = EventManager(self.calendar_client)
    
    # Métodos de conveniencia que delegan a los componentes
    def get_available_slots(self, calendar_id, date, working_hours, slot_duration):
        return self.availability.get_available_slots(
            calendar_id, date, working_hours, slot_duration
        )
    
    def create_appointment(self, calendar_id, start, end, client_name, client_phone, type):
        return self.events.create_appointment(
            calendar_id, start, end, client_name, client_phone, type
        )
    
    def cancel_appointment(self, calendar_id, event_id):
        return self.events.cancel_appointment(calendar_id, event_id)

# Exportar interfaz pública
__all__ = ['GoogleCalendarService']
```

### **Uso desde el Chatbot:**

```python
# En el bot (src/bot/client_handler.py o appointment_service.py)
from src.integrations.google_calendar import GoogleCalendarService

# Instanciar una vez (puede ser singleton)
calendar_service = GoogleCalendarService()

# Usar en flujos del bot
def handle_show_availability(professional_phone, date):
    # Obtener config del profesional
    prof = db.get_professional(professional_phone)
    
    # Consultar disponibilidad
    slots = calendar_service.get_available_slots(
        calendar_id=prof['calendar_id'],
        date=date,
        working_hours=prof['working_hours'],
        slot_duration=prof['slot_duration']
    )
    
    return slots
```

---

## ✅ TESTING

### **Estructura de Tests:**

```
tests/integrations/google_calendar/
│
├── __init__.py
├── test_auth_manager.py              # Tests de autenticación
├── test_calendar_client.py           # Tests del cliente base
├── test_availability_checker.py      # Tests de disponibilidad
├── test_event_manager.py             # Tests de gestión de eventos
└── test_integration.py               # Tests end-to-end (con API real)
```

### **Mocking de Google API:**

```python
# tests/integrations/google_calendar/test_availability_checker.py
import pytest
from unittest.mock import Mock, patch
from src.integrations.google_calendar.calendar import AvailabilityChecker

@pytest.fixture
def mock_calendar_client():
    """Mock del cliente de Google Calendar"""
    client = Mock()
    
    # Simular respuesta de eventos existentes
    client.get_events.return_value = [
        {
            'start': {'dateTime': '2024-12-15T10:00:00-03:00'},
            'end': {'dateTime': '2024-12-15T11:00:00-03:00'}
        }
    ]
    
    return client

def test_get_available_slots_excludes_busy_times(mock_calendar_client):
    """Debe excluir horarios ocupados"""
    checker = AvailabilityChecker(mock_calendar_client)
    
    slots = checker.get_available_slots(
        calendar_id='test@gmail.com',
        date='2024-12-15',
        working_hours={'start': '09:00', 'end': '12:00'},
        slot_duration_minutes=60
    )
    
    # Debería retornar 2 slots: 09:00-10:00 y 11:00-12:00
    # (excluye 10:00-11:00 que está ocupado)
    assert len(slots) == 2
    assert slots[0]['start'] == '09:00'
    assert slots[1]['start'] == '11:00'
```

### **Test de Integración (requiere credenciales reales):**

```python
# tests/integrations/google_calendar/test_integration.py
import pytest
from src.integrations.google_calendar import GoogleCalendarService

@pytest.mark.integration  # Marcar como test de integración
def test_create_and_delete_event():
    """Test end-to-end con Google Calendar real"""
    # Requiere: TEST_CALENDAR_ID en variables de entorno
    # Y credenciales válidas en config/
    
    service = GoogleCalendarService()
    calendar_id = os.getenv('TEST_CALENDAR_ID')
    
    # Crear evento de prueba
    event = service.create_appointment(
        calendar_id=calendar_id,
        start_datetime='2099-12-31T10:00:00-03:00',  # Fecha futura
        end_datetime='2099-12-31T11:00:00-03:00',
        client_name='Test Client',
        client_phone='+5491100000000',
        appointment_type='Test'
    )
    
    assert event['id'] is not None
    
    # Limpiar: eliminar evento
    success = service.cancel_appointment(calendar_id, event['id'])
    assert success is True
```

### **Ejecutar Tests:**

```bash
# Solo tests unitarios (rápidos, no requieren API)
pytest tests/integrations/google_calendar/ -m "not integration"

# Tests de integración (requieren credenciales)
pytest tests/integrations/google_calendar/ -m integration

# Todos los tests
pytest tests/integrations/google_calendar/

# Con coverage
pytest tests/integrations/google_calendar/ --cov=src/integrations/google_calendar
```

---

## 🔧 TROUBLESHOOTING

### **Problema: Error 403 "Insufficient Permission"**

```
Error: The caller does not have permission to access calendar
```

**Solución:**
1. Verificar que el profesional compartió su calendario con la Service Account
2. Revisar que los permisos sean "Hacer cambios en eventos"
3. Esperar 1-2 minutos para que se propaguen los permisos

```python
# Script de diagnóstico
from src.integrations.google_calendar import GoogleCalendarService

service = GoogleCalendarService()
calendars = service.calendar_client.list_calendars()

print("Calendarios accesibles:")
for cal in calendars:
    print(f"- {cal['id']}: {cal.get('summary', 'Sin nombre')}")
```

---

### **Problema: Error 401 "Invalid Credentials"**

```
Error: Request had invalid authentication credentials
```

**Solución:**
1. Verificar que `service-account.json` existe y es válido
2. Revisar que la API de Calendar está habilitada
3. Regenerar credenciales si es necesario

```bash
# Verificar archivo de credenciales
cat config/google/service-account.json | python -m json.tool

# Debe contener campos: type, project_id, private_key, client_email
```

---

### **Problema: Slots incorrectos (zona horaria)**

**Síntoma:** Los horarios disponibles no coinciden con la realidad

**Solución:**
```python
# Verificar que todas las fechas usan la misma zona horaria
import pytz

tz = pytz.timezone('America/Argentina/Buenos_Aires')

# Al crear datetimes, siempre especificar timezone
from datetime import datetime
dt = tz.localize(datetime(2024, 12, 15, 14, 0))

# O usar ISO format con offset
start = '2024-12-15T14:00:00-03:00'  # -03:00 = GMT-3
```

---

### **Problema: Cuotas excedidas (429 Too Many Requests)**

```
Error: Rate limit exceeded
```

**Solución:**
1. Implementar backoff exponencial en `retry_handler.py`
2. Cachear resultados de disponibilidad por algunos minutos
3. Revisar límites en Google Cloud Console

```python
# utils/retry_handler.py
import time
from functools import wraps

def retry_with_backoff(max_attempts=3, initial_delay=1):
    """Decorador para reintentar con backoff exponencial"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    if '429' in str(e):  # Rate limit
                        time.sleep(delay)
                        delay *= 2  # Backoff exponencial
                    else:
                        raise
        return wrapper
    return decorator
```

---

## 📚 RECURSOS ADICIONALES

### **Documentación Relacionada:**
- `README.md` - Guía principal del proyecto
- `docs/ARCHITECTURE.md` - Arquitectura completa del sistema
- `docs/DATABASE.md` - Esquema de BD (incluye campo `google_event_id`)

### **Enlaces Externos:**
- [Google Calendar API Docs](https://developers.google.com/calendar/api/v3/reference)
- [Service Accounts Guide](https://cloud.google.com/iam/docs/service-accounts)
- [Google API Python Client](https://github.com/googleapis/google-api-python-client)
- [pytz Timezone List](https://gist.github.com/heyalexej/8bf688fd67d7199be4a1682b3eec7568)

---

## 🎯 MEJORES PRÁCTICAS

### **DO:**
✅ Usar Service Account (no OAuth de usuario individual)
✅ Guardar `event_id` en BD para sincronización
✅ Manejar zonas horarias explícitamente
✅ Implementar reintentos con backoff
✅ Cachear disponibilidad por algunos minutos
✅ Validar que el calendar_id existe antes de operar
✅ Loggear todas las operaciones para debugging

### **DON'T:**
❌ Hardcodear calendar IDs en el código
❌ Asumir que eventos siempre se crean exitosamente
❌ Ignorar errores de permisos
❌ Usar datetime sin timezone
❌ Hacer requests sin rate limiting
❌ Guardar credenciales en el repositorio
❌ Olvidar sincronizar cancelaciones

---

## ✅ CHECKLIST DE IMPLEMENTACIÓN

### **Configuración Inicial:**
- [ ] Crear proyecto en Google Cloud Console
- [ ] Habilitar Google Calendar API
- [ ] Crear Service Account y descargar JSON
- [ ] Compartir calendarios de profesionales con Service Account
- [ ] Agregar campo `google_event_id` a tabla `appointments` en BD
- [ ] Configurar variables de entorno

### **Desarrollo:**
- [ ] Implementar `AuthManager`
- [ ] Implementar `CalendarClient`
- [ ] Implementar `AvailabilityChecker`
- [ ] Implementar `EventManager`
- [ ] Crear modelos de datos
- [ ] Escribir tests unitarios (con mocks)

### **Integración:**
- [ ] Integrar en flujo de búsqueda de disponibilidad
- [ ] Integrar en creación de citas
- [ ] Integrar en cancelación de citas
- [ ] Probar con calendario real

### **Testing:**
- [ ] Tests unitarios pasan
- [ ] Tests de integración con calendar de prueba
- [ ] Prueba end-to-end completa (cliente reserva y se crea en Calendar)

---

**Última actualización:** Enero 2025  
**Versión:** 1.0  
**Estado:** Diseño
