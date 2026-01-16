# 🗓️ Google Calendar Service

Módulo Python para integración con Google Calendar API. Diseñado para sistemas de reservas y gestión de citas.

## 📋 Características

- ✅ Autenticación con Service Account (sin interacción del usuario)
- ✅ Listar calendarios accesibles
- ✅ Consultar eventos en rangos de tiempo
- ✅ Crear, actualizar y eliminar eventos
- ✅ Manejo de errores robusto
- ✅ Logging detallado
- ✅ Código documentado y modular

## 🚀 Inicio Rápido

### 1. Instalación

```bash
pip install -r requirements.txt
```

### 2. Configuración

Seguir la guía completa en [`SETUP_GUIDE.md`](./SETUP_GUIDE.md)

Resumen:
1. Crear proyecto en Google Cloud Console
2. Habilitar Google Calendar API
3. Crear Service Account
4. Descargar credenciales JSON como `config/google/service-account.json`
5. Compartir calendarios con la Service Account

### 3. Probar Conexión

```bash
cd tests
python test_connection.py
```

## 💻 Uso Básico

### Autenticación y Cliente

```python
from google_calendar_service.auth import AuthManager
from google_calendar_service.calendar import CalendarClient

# Autenticar
auth_manager = AuthManager()
credentials = auth_manager.get_credentials()

# Crear cliente
calendar_client = CalendarClient(credentials)
```

### Listar Calendarios

```python
# Obtener todos los calendarios accesibles
calendars = calendar_client.list_calendars()

for cal in calendars:
    print(f"Calendario: {cal['summary']}")
    print(f"ID: {cal['id']}")
    print(f"Zona horaria: {cal['timeZone']}")
```

### Consultar Eventos

```python
from datetime import datetime, timedelta

# Definir rango de tiempo (hoy)
today = datetime.now().replace(hour=0, minute=0, second=0)
tomorrow = today + timedelta(days=1)

# Obtener eventos
events = calendar_client.get_events(
    calendar_id='profesional@gmail.com',
    time_min=today.isoformat() + 'Z',
    time_max=tomorrow.isoformat() + 'Z'
)

for event in events:
    print(f"Evento: {event['summary']}")
    print(f"Inicio: {event['start']['dateTime']}")
```

### Crear Evento

```python
# Datos del evento
event_data = {
    'summary': 'Consulta - Juan Pérez',
    'description': 'Consulta inicial de psicología',
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

# Crear evento
event = calendar_client.create_event(
    calendar_id='profesional@gmail.com',
    event_data=event_data
)

print(f"Evento creado con ID: {event['id']}")
```

### Eliminar Evento

```python
# Eliminar un evento
success = calendar_client.delete_event(
    calendar_id='profesional@gmail.com',
    event_id='abc123xyz'
)

if success:
    print("Evento eliminado exitosamente")
```

## 📁 Estructura del Módulo

```
google_calendar_service/
├── auth/                     # Autenticación
│   ├── auth_manager.py       # Gestión de Service Account
│   └── __init__.py
├── calendar/                 # Operaciones con calendarios
│   ├── calendar_client.py    # Cliente base de Google Calendar API
│   └── __init__.py
├── config/                   # Configuración
│   ├── settings.py           # Parámetros configurables
│   └── __init__.py
├── tests/                    # Tests y scripts de prueba
│   └── test_connection.py    # Script para verificar conexión
├── requirements.txt          # Dependencias
├── SETUP_GUIDE.md           # Guía de configuración paso a paso
└── README.md                # Este archivo
```

## 🔧 Configuración Avanzada

### Variables de Entorno

```bash
# Ruta a credenciales (opcional, tiene default)
export GOOGLE_CREDENTIALS_PATH=/path/to/service-account.json

# Zona horaria por defecto
export DEFAULT_TIMEZONE=America/Argentina/Buenos_Aires

# Nivel de logging
export LOG_LEVEL=INFO
```

### Personalizar Configuración

```python
# En config/settings.py puedes modificar:
GOOGLE_CONFIG = {
    'credentials_path': 'tu/ruta/personalizada',
    'scopes': [...],
    'api_version': 'v3',
    'retry_attempts': 3,
    'retry_delay_seconds': 2,
    'timeout_seconds': 30,
}
```

## 🧪 Testing

```bash
# Probar conexión
python tests/test_connection.py

# Ejecutar tests unitarios (cuando estén implementados)
pytest tests/
```

## 📚 Documentación Adicional

- [Guía de Configuración Completa](./SETUP_GUIDE.md) - Setup paso a paso
- [Google Calendar API Docs](https://developers.google.com/calendar/api/v3/reference) - Documentación oficial

## 🔒 Seguridad

**IMPORTANTE:**

- ❌ NUNCA subir `service-account.json` a repositorios públicos
- ❌ NUNCA compartir las credenciales
- ✅ Agregar `service-account.json` a `.gitignore`
- ✅ Usar variables de entorno en producción
- ✅ Rotar credenciales periódicamente

```bash
# .gitignore
config/google/service-account.json
*.json
```

## 🐛 Troubleshooting

### Error: "Archivo de credenciales no encontrado"
- Verificar que `service-account.json` esté en `config/google/`
- Verificar permisos de lectura del archivo

### Error: "No se encontraron calendarios accesibles"
- Verificar que compartiste el calendario con la Service Account
- Esperar 1-2 minutos para que se propaguen los permisos
- Verificar el email de Service Account

### Error: "Insufficient Permission" (403)
- Verificar que los permisos sean "Hacer cambios en eventos"
- Re-compartir el calendario con los permisos correctos

### Error: "API not enabled"
- Habilitar Google Calendar API en Google Cloud Console
- Verificar que estás en el proyecto correcto

## 📝 Logging

El módulo usa el sistema de logging de Python. Para ver logs detallados:

```python
import logging

# Configurar nivel de logging
logging.basicConfig(level=logging.DEBUG)

# Usar el módulo normalmente
# Los logs se mostrarán en consola
```

## 🤝 Contribuir

Este es un módulo interno del proyecto. Para contribuir:

1. Mantener el código modular y bien documentado
2. Agregar docstrings a todas las funciones públicas
3. Seguir convenciones de código del proyecto
4. Probar cambios antes de integrar

## 📄 Licencia

Uso interno del proyecto.

---

**Versión:** 1.0.0  
**Última actualización:** Enero 2025
