# 🏗️ ARQUITECTURA DEL PROYECTO
## Sistema de Agenda y Reservas - WhatsApp Bot

---

## 📋 ÍNDICE

1. [Visión General](#visión-general)
2. [Estructura del Proyecto](#estructura-del-proyecto)
3. [Capas de la Aplicación](#capas-de-la-aplicación)
4. [Flujo de Datos](#flujo-de-datos)
5. [Base de Datos](#base-de-datos)
6. [Guía de Desarrollo](#guía-de-desarrollo)
7. [Convenciones de Código](#convenciones-de-código)
8. [Testing](#testing)
9. [Deployment](#deployment)
10. [Troubleshooting](#troubleshooting)

---

## 📊 VISIÓN GENERAL

### **¿Qué es este proyecto?**

Sistema de gestión de citas y reservas para un centro de psicología, implementado como un bot conversacional de WhatsApp. Permite:

- **Clientes**: Buscar y reservar citas con profesionales
- **Profesionales**: Gestionar horarios y disponibilidad
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
┌──────────────▼──────────────────────┐
│     Services Layer                  │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│     SQLite Database                 │
└─────────────────────────────────────┘
```

**Tecnologías:**
- **Backend**: Python 3.10+
- **Framework**: Flask (webhook)
- **Messaging**: Twilio WhatsApp API
- **Database**: SQLite
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
│   │   ├── client_handler.py            # Handler de flujo de clientes (~500 líneas)
│   │   ├── professional_handler.py      # Handler de flujo de profesionales (~800 líneas)
│   │   └── admin_handler.py             # Handler de administración (~200 líneas)
│   │
│   ├── 📁 services/                     # Servicios de lógica de negocio
│   │   ├── __init__.py
│   │   ├── client_service.py            # Servicios para clientes (búsqueda)
│   │   ├── professional_service.py      # Servicios para profesionales (registro, horarios)
│   │   ├── analytics_service.py         # Métricas y analytics
│   │   └── appointment_service.py       # Gestión de citas (CRUD, confirmaciones)
│   │
│   ├── 📁 database/                     # Capa de acceso a datos
│   │   ├── __init__.py
│   │   └── database.py                  # Conexión y operaciones de BD
│   │
│   ├── 📁 api/                          # Capa de presentación (webhooks)
│   │   ├── __init__.py
│   │   └── whatsapp_handler.py          # Flask webhook + Twilio integration
│   │
│   ├── 📁 config/                       # Configuración
│   │   ├── __init__.py
│   │   ├── settings.py                  # Settings generales (env vars, etc.)
│   │   ├── domain_config.py             # Configuración de dominios/presets
|   |   ├── filter_config.py             # Configuración de filtros de búsqueda
│   │   └── setup_domain.py              # Script de configuración de dominio
│   │
│   └── 📁 core/                         # Componentes core compartidos
│       ├── __init__.py
│       ├── states.py                    # State machine y gestión de sesiones
│       ├── messages.py                  # Templates de mensajes
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
│   └── seed_data.py                     # Datos de prueba
│
├── 📁 docker/                           # Configuración Docker
│   ├── Dockerfile                       # Imagen Docker
│   ├── docker-compose.yml               # Orquestación de servicios
│   └── docker-entrypoint.sh             # Script de inicio del container
│
├── 📁 data/                             # Datos persistentes
│   ├── database.db                      # Base de datos SQLite
│   └── certificates/                    # Certificados de profesionales
│       └── {phone}/                     # Un directorio por profesional
│
├── 📁 docs/                             # Documentación
│   ├── ARCHITECTURE.md                  # Este archivo
│   ├── DATABASE.md                      # Esquema de base de datos
│   ├── API.md                           # Documentación de API
│   └── DEPLOYMENT.md                    # Guía de deployment
│
├── .env                                 # Variables de entorno (gitignored)
├── .env.example                         # Template de variables de entorno
├── .gitignore                           # Archivos ignorados por git
├── requirements.txt                     # Dependencias de Python
├── pytest.ini                           # Configuración de pytest
└── README.md                            # Documentación principal
```

### **Métricas del Proyecto:**
- **Total líneas de código**: ~10,000
- **Archivos Python**: ~25
- **Archivo más grande**: ~800 líneas
- **Modularidad**: Alta (archivos pequeños y enfocados)

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

**Ejemplo de código:**
```python
@app.route('/webhook', methods=['POST'])
def webhook():
    phone = request.form.get('From')
    message = request.form.get('Body')
    
    # Llamar al bot
    response = bot.process_message(phone, message)
    
    # Enviar respuesta
    return send_whatsapp_message(phone, response)
```

---

### **2. Capa Bot (Lógica Conversacional)**

**Ubicación:** `src/bot/`

**Responsabilidad:** Gestionar el flujo de conversación y estados

**Componentes:**

#### **bot_controller.py** (Orquestador)
- Punto de entrada único: `process_message(phone, message)`
- Decide qué handler usar según el rol del usuario
- Gestiona la sesión del usuario

```python
class Bot:
    def process_message(self, phone, message):
        session = session_manager.get_session(phone)
        
        if session.role == UserRole.CLIENT:
            return self.client_handler.handle(phone, message, session)
        elif session.role == UserRole.PROFESSIONAL:
            return self.professional_handler.handle(phone, message, session)
        else:
            return self._identify_user(phone, message)
```

#### **client_handler.py** (Flujo Clientes)
- Maneja todos los estados relacionados con clientes
- Estados: `CLIENT_SEARCH_*`, `CLIENT_BOOKING_*`
- Usa `client_service` para operaciones

#### **professional_handler.py** (Flujo Profesionales)
- Maneja todos los estados relacionados con profesionales
- Estados: `PROF_*`
- Usa `professional_service` para operaciones

#### **admin_handler.py** (Funciones Admin)
- Funciones administrativas (verificación, stats, etc.)

**State Machine:**
```
Estados del Cliente:
IDLE → CLIENT_SEARCH_TYPE → CLIENT_SEARCH_ZONE → CLIENT_VIEW_RESULTS → ...

Estados del Profesional:
IDLE → PROF_MENU → PROF_REGISTER → PROF_INFO_* → PROF_SCHEDULE → ...
```

---

### **3. Capa Services (Lógica de Negocio)**

**Ubicación:** `src/services/`

**Responsabilidad:** Implementar casos de uso y lógica de negocio

**Componentes:**

#### **client_service.py**
```python
class ClientService:
    def search_professionals(filters) -> List[Dict]
    def get_professional_details(phone) -> Dict
    def calculate_availability(professional, date) -> List[TimeSlot]
```

#### **professional_service.py**
```python
class ProfessionalService:
    def register_professional(data) -> bool
    def update_schedule(phone, schedule) -> bool
    def save_certificate(phone, file_path) -> bool
    def get_profile(phone) -> Dict
```

#### **appointment_service.py** (Nuevo)
```python
class AppointmentService:
    def create_appointment(client, professional, datetime) -> int
    def confirm_appointment(appointment_id) -> bool
    def cancel_appointment(appointment_id, reason) -> bool
    def get_upcoming_appointments(phone, role) -> List[Dict]
    def send_reminder(appointment_id) -> bool
```

#### **analytics_service.py**
```python
class AnalyticsService:
    def log_search(client_phone, search_params) -> None
    def log_contact(client_phone, professional_phone) -> None
    def get_professional_metrics(phone) -> Dict
    def get_system_stats() -> Dict
```

**Principio:** Los servicios NO conocen detalles de WhatsApp, solo lógica de negocio.

---

### **4. Capa Database (Persistencia)**

**Ubicación:** `src/database/`

**Responsabilidad:** Acceso a datos, CRUD operations

**Componentes:**

#### **database.py**
- Clase `Database` con métodos CRUD
- Gestión de conexiones SQLite
- Context manager para transacciones

```python
class Database:
    def get_connection(self):
        """Context manager para conexiones"""
        
    def add_professional(phone, name, ...) -> bool
    def get_professional(phone) -> Dict
    def update_professional(...) -> bool
    
    def create_appointment(...) -> int
    def get_appointment(id) -> Dict
    def update_appointment_status(...) -> bool
    
    # ... más métodos CRUD
```

**Patrón de uso:**
```python
with db.get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ...")
    result = cursor.fetchall()
```

---

### **5. Capa Core (Componentes Compartidos)**

**Ubicación:** `src/core/`

**Responsabilidad:** Componentes usados por todas las capas

#### **states.py**
```python
class ConversationState(Enum):
    IDLE = "idle"
    CLIENT_SEARCH_TYPE = "client_search_type"
    PROF_MENU = "prof_menu"
    # ... más estados

class UserRole(Enum):
    UNKNOWN = "unknown"
    CLIENT = "client"
    PROFESSIONAL = "professional"
    ADMIN = "admin"

class SessionManager:
    def get_session(phone) -> SessionData
    def update_state(phone, new_state) -> None
```

#### **messages.py**
```python
class Messages:
    WELCOME = "¡Hola! Soy el asistente de {business_name}..."
    CLIENT_SEARCH_MENU = "¿Cómo quieres buscar?..."
    # ... templates de mensajes
```

#### **validators.py**
```python
def validate_phone(phone) -> bool
def validate_email(email) -> bool
def validate_date(date_str) -> bool
def validate_time_range(time_str) -> Tuple[str, str]
```

---

### **6. Capa Config (Configuración)**

**Ubicación:** `src/config/`

**Responsabilidad:** Configuración y settings

#### **settings.py**
```python
class Config:
    TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
    WHATSAPP_NUMBER = os.getenv('WHATSAPP_NUMBER')
    DATABASE_PATH = 'data/database.db'
    CERTIFICATES_DIR = 'data/certificates'
```

#### **domain_config.py**
- Presets de configuración por dominio (PSICOLOGIA, SALUD, etc.)
- Personalización de mensajes y terminología

---

## 🔄 FLUJO DE DATOS

### **Flujo Completo: Cliente busca y reserva cita**

```
1. USUARIO (WhatsApp)
   ↓ "Hola, busco psicólogo"
   
2. TWILIO API
   ↓ POST /webhook
   
3. whatsapp_handler.py
   ↓ Extrae phone + message
   
4. bot_controller.py
   ↓ process_message(phone, message)
   ↓ Identifica rol: CLIENT
   
5. client_handler.py
   ↓ handle(phone, message, session)
   ↓ Estado actual: IDLE
   ↓ Cambiar a: CLIENT_SEARCH_TYPE
   
6. client_service.py
   ↓ get_search_options()
   
7. messages.py
   ↓ Formatear menú de búsqueda
   
8. whatsapp_handler.py
   ↓ Enviar respuesta
   
9. TWILIO API
   ↓ Mensaje a WhatsApp
   
10. USUARIO (WhatsApp)
    ↓ Ve menú de opciones
```

### **Flujo de Reserva de Cita:**

```
Usuario selecciona profesional + fecha/hora
   ↓
client_handler.py (valida disponibilidad)
   ↓
appointment_service.py (crea cita)
   ↓
database.py (INSERT en appointments)
   ↓
appointment_service.py (envía notificación al profesional)
   ↓
analytics_service.py (log de contacto)
   ↓
Respuesta al cliente: "Cita creada, pendiente confirmación"
```

---

## 🗄️ BASE DE DATOS

### **Esquema Actual (8 tablas):**

#### **1. professionals**
```sql
Campos principales:
- phone (PK)
- name, email, zone, gender
- certificate_path
- bio, fee_range
- session_duration_minutes, buffer_time_minutes
- is_active, is_accepting_new_patients
- Métricas: total_views, total_contacts
```

#### **2. clients**
```sql
Campos principales:
- phone (PK)
- name, email, age, gender
- preferred_zone, preferred_gender
- has_prepaga, prepaga_name
- first_time_patient, is_active
```

#### **3. appointments**
```sql
Campos principales:
- id (PK)
- client_phone (FK), professional_phone (FK)
- appointment_date, start_time, end_time
- session_type, modality
- status (pendiente_confirmacion, confirmada, completada, cancelada, etc.)
- notes, cancellation_reason
- reminder_sent
```

#### **4. appointment_history**
```sql
Auditoría de cambios en appointments
- appointment_id (FK)
- previous_status, new_status
- previous_date, new_date
- changed_by, change_reason
```

#### **5. notifications**
```sql
Registro de notificaciones enviadas
- recipient_phone, recipient_type
- notification_type (reminder, confirmation, etc.)
- status (pending, sent, delivered, failed)
- appointment_id (FK)
```

#### **6. weekly_schedule**
```sql
Horarios ocupados recurrentes
- professional_phone (FK)
- day_of_week (0-6)
- start_time, end_time
- is_busy
```

#### **7. specific_free_slots**
```sql
Horarios libres específicos
- professional_phone (FK)
- date, start_time, end_time
```

#### **8. client_searches**
```sql
Analytics de búsquedas
- client_phone
- search_type, search_params
- result_count
- professional_contacted (FK)
```

**Ver más detalles en:** `docs/DATABASE.md`

---

## 💻 GUÍA DE DESARROLLO

### **Setup del Ambiente Local**

```bash
# 1. Clonar repositorio
git clone <repo-url>
cd booking-chatbot

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate  # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales

# 5. Inicializar base de datos
python scripts/init_db.py

# 6. Verificar instalación
python scripts/verify_db.py
pytest tests/
```

### **Desarrollo con Docker (Recomendado)**

```bash
# 1. Construir y levantar
docker-compose -f docker/docker-compose.yml up --build

# 2. Ver logs
docker-compose -f docker/docker-compose.yml logs -f

# 3. Ejecutar comandos dentro del container
docker-compose exec whatsapp-bot python scripts/verify_db.py

# 4. Detener
docker-compose -f docker/docker-compose.yml down
```

### **Agregar Nueva Funcionalidad**

**Ejemplo: Agregar sistema de reviews**

1. **Crear tabla en database.py:**
```python
cursor.execute("""
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY,
        client_phone TEXT,
        professional_phone TEXT,
        rating INTEGER CHECK(rating BETWEEN 1 AND 5),
        comment TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_phone) REFERENCES clients(phone),
        FOREIGN KEY (professional_phone) REFERENCES professionals(phone)
    )
""")
```

2. **Crear servicio en src/services/review_service.py:**
```python
class ReviewService:
    def create_review(self, client_phone, professional_phone, rating, comment):
        # Lógica de negocio
        pass
    
    def get_professional_reviews(self, professional_phone):
        pass
```

3. **Agregar estados en src/core/states.py:**
```python
class ConversationState(Enum):
    # ... estados existentes
    CLIENT_REVIEW_RATING = "client_review_rating"
    CLIENT_REVIEW_COMMENT = "client_review_comment"
```

4. **Agregar handler en src/bot/client_handler.py:**
```python
def _handle_review_flow(self, phone, message, session):
    if session.state == ConversationState.CLIENT_REVIEW_RATING:
        # Manejar rating
        pass
    elif session.state == ConversationState.CLIENT_REVIEW_COMMENT:
        # Manejar comentario
        pass
```

5. **Agregar tests en tests/test_review_service.py:**
```python
def test_create_review():
    # Test unitario
    pass

def test_review_flow_integration():
    # Test de integración
    pass
```

---

## 📏 CONVENCIONES DE CÓDIGO

### **Estilo de Código:**

```python
# 1. Imports ordenados
from datetime import datetime  # Standard library
import os

from flask import Flask, request  # Third party

from src.core.states import session_manager  # Local imports
from src.services.client_service import client_service

# 2. Naming conventions
class ClientService:  # PascalCase para clases
    def search_professionals(self):  # snake_case para funciones
        pass

CONSTANT_VALUE = "value"  # UPPER_CASE para constantes

# 3. Docstrings
def process_message(phone: str, message: str) -> str:
    """
    Process incoming message from user.
    
    Args:
        phone: User's phone number
        message: Text message from user
        
    Returns:
        Bot's response message
    """
    pass

# 4. Type hints
def create_appointment(
    client_phone: str,
    professional_phone: str,
    date: datetime
) -> int:
    pass

# 5. Max line length: 100 caracteres
```

### **Estructura de Archivos:**

```python
"""
Module docstring explaining purpose.
"""

# Imports
import ...

# Constants
CONSTANT_1 = "value"

# Classes
class MyClass:
    pass

# Functions
def my_function():
    pass

# Main execution
if __name__ == "__main__":
    pass
```

### **Git Commit Messages:**

```
feat: Add appointment reminder system
fix: Resolve timezone issue in scheduling
docs: Update architecture documentation
refactor: Split bot.py into handlers
test: Add integration tests for booking flow
chore: Update dependencies
```

---

## 🧪 TESTING

### **Estructura de Tests:**

```
tests/
├── test_bot.py              # Tests del bot
├── test_database.py         # Tests de BD
├── test_services.py         # Tests de servicios
├── test_integration.py      # Tests de integración
└── test_bot_interactive.py  # Tests manuales interactivos
```

### **Ejecutar Tests:**

```bash
# Todos los tests
pytest tests/

# Tests específicos
pytest tests/test_services.py

# Con coverage
pytest --cov=src tests/

# Verbose
pytest -v tests/

# Solo tests que fallan
pytest --lf tests/
```

### **Escribir Tests:**

```python
# tests/test_appointment_service.py
import pytest
from src.services.appointment_service import AppointmentService

@pytest.fixture
def appointment_service():
    return AppointmentService()

def test_create_appointment(appointment_service):
    # Arrange
    client_phone = "+5491112345678"
    professional_phone = "+5491187654321"
    date = "2024-12-15"
    
    # Act
    appointment_id = appointment_service.create_appointment(
        client_phone, professional_phone, date, "14:00", "15:00"
    )
    
    # Assert
    assert appointment_id > 0
    assert appointment_service.get_appointment(appointment_id) is not None
```

### **Coverage Objetivo:**

- **Unit tests**: >80%
- **Integration tests**: Flujos críticos completos
- **Manual tests**: Flows de usuario end-to-end

---

## 🚀 DEPLOYMENT

### **Ambiente de Desarrollo:**

```bash
# Local con Flask dev server
python src/api/whatsapp_handler.py

# Docker development
docker-compose -f docker/docker-compose.yml up
```

### **Ambiente de Producción:**

**1. Preparar imagen:**
```bash
docker build -f docker/Dockerfile -t whatsapp-bot:latest .
```

**2. Configurar variables de entorno:**
```bash
# Crear .env con credenciales de producción
TWILIO_ACCOUNT_SID=<prod-sid>
TWILIO_AUTH_TOKEN=<prod-token>
DOMAIN_PRESET=PSICOLOGIA
FLASK_ENV=production
```

**3. Usar Gunicorn (production server):**

En `docker/Dockerfile`, cambiar:
```dockerfile
# Comentar:
# CMD ["bash", "docker/docker-entrypoint.sh"]

# Descomentar:
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "60", "src.api.whatsapp_handler:app"]
```

**4. Deploy a servidor:**
```bash
# Ejemplo con docker-compose en servidor
scp -r . user@server:/opt/whatsapp-bot/
ssh user@server
cd /opt/whatsapp-bot
docker-compose -f docker/docker-compose.yml up -d
```

**5. Configurar Twilio webhook:**
- Ir a Twilio Console
- Configurar webhook URL: `https://tu-dominio.com/webhook`
- Método: POST

### **Monitoreo:**

```bash
# Ver logs
docker-compose logs -f whatsapp-bot

# Verificar salud del container
docker-compose ps
docker inspect whatsapp-webhook

# Entrar al container
docker-compose exec whatsapp-bot bash

# Verificar BD
docker-compose exec whatsapp-bot python scripts/verify_db.py
```

---

## 🔧 TROUBLESHOOTING

### **Problema: Bot no responde**

```bash
# 1. Verificar que el container está corriendo
docker-compose ps

# 2. Ver logs del container
docker-compose logs -f whatsapp-bot

# 3. Verificar webhook de Twilio
# - Revisar que la URL esté correcta
# - Verificar que el servidor sea accesible públicamente

# 4. Probar endpoint manualmente
curl -X POST http://localhost:5000/webhook \
  -d "From=whatsapp:+5491112345678" \
  -d "Body=Hola"
```

### **Problema: Error de imports**

```python
# Error: ModuleNotFoundError: No module named 'src'

# Solución 1: Verificar PYTHONPATH
export PYTHONPATH=/app:$PYTHONPATH

# Solución 2: Ejecutar con -m
python -m src.api.whatsapp_handler

# Solución 3: Verificar __init__.py
# Asegurar que todas las carpetas tienen __init__.py
```

### **Problema: Base de datos corrupta**

```bash
# 1. Backup de BD actual
cp data/database.db data/database.db.backup

# 2. Verificar integridad
sqlite3 data/database.db "PRAGMA integrity_check"

# 3. Si está corrupta, recrear
rm data/database.db
python scripts/init_db.py

# 4. Si necesitas recuperar datos
# Usar el backup y migrar manualmente
```

### **Problema: Estado de sesión incorrecto**

```python
# Limpiar sesión de un usuario específico
from src.core.states import session_manager

phone = "+5491112345678"
session_manager.reset_session(phone)
```

### **Logs útiles:**

```bash
# Logs de aplicación
docker-compose logs -f whatsapp-bot | grep ERROR

# Logs de BD
docker-compose exec whatsapp-bot sqlite3 data/database.db ".log on"

# Logs de Twilio
# Ver en Twilio Console > Monitor > Logs
```

---

## 📚 RECURSOS ADICIONALES

### **Documentación Relacionada:**

- `README.md` - Guía de inicio rápido
- `docs/DATABASE.md` - Esquema detallado de BD
- `docs/API.md` - Documentación de endpoints
- `docs/DEPLOYMENT.md` - Guía completa de deployment

### **Enlaces Externos:**

- [Twilio WhatsApp API](https://www.twilio.com/docs/whatsapp)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [SQLite Documentation](https://www.sqlite.org/docs.html)
- [pytest Documentation](https://docs.pytest.org/)

---

## ✅ CHECKLIST DE MANTENIMIENTO

### **Diario:**
- [ ] Revisar logs de errores
- [ ] Monitorear uso de recursos (CPU, memoria)
- [ ] Verificar que el bot responde

### **Semanal:**
- [ ] Backup de base de datos
- [ ] Revisar métricas de uso (analytics)
- [ ] Actualizar dependencias si hay vulnerabilidades

### **Mensual:**
- [ ] Ejecutar suite completa de tests
- [ ] Revisar y actualizar documentación
- [ ] Planificar nuevas features según feedback

### **Trimestral:**
- [ ] Auditoría de seguridad
- [ ] Optimización de performance
- [ ] Refactoring de código legacy

---

## 🎯 MEJORES PRÁCTICAS

### **DO:**
✅ Mantener archivos pequeños (<800 líneas)
✅ Usar type hints en funciones públicas
✅ Escribir tests para nueva funcionalidad
✅ Documentar decisiones de arquitectura
✅ Hacer commits atómicos y descriptivos
✅ Revisar logs regularmente
✅ Hacer backups antes de cambios mayores

### **DON'T:**
❌ Hardcodear credenciales en el código
❌ Hacer cambios sin tests
❌ Ignorar warnings de dependencias
❌ Mezclar lógica de negocio con presentación
❌ Commit de código sin probar
❌ Dejar TODOs sin ticket asociado
❌ Modificar BD en producción sin backup

---

## 📞 CONTACTO Y SOPORTE

**Mantenedores:**
- Equipo de Desarrollo: dev@psivale.com.ar

**Reportar Issues:**
- GitHub Issues: [repo-url]/issues
- Email urgencias: urgencias@psivale.com.ar

**Contribuir:**
Ver `docs/CONTRIBUTING.md` para guías de contribución

---

**Última actualización:** Diciembre 2024
**Versión:** 2.0
**Estado:** Producción
