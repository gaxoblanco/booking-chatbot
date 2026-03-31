# 🎨 SISTEMA DE TONOS — Mensajes Multi-Tenant

**Versión 1.0 — Marzo 2026**

---

## ¿Qué es el sistema de tonos?

El sistema de tonos permite que cada instancia del bot hable con una personalidad
distinta sin tocar el código. Un centro de psicología en Formosa habla diferente
a una plataforma de demostración de producto — el mismo flujo, palabras distintas.

El tono se configura por variable de entorno. El código nunca cambia.

---

## Arquitectura

```
TENANT_TONE=coloquial   ← .env del container
        │
        ▼
src/messages/loader.py  ← singleton, carga al arrancar
        │
        ▼
src/messages/tones/
  ├── coloquial.py       ← vecinal, directo (Formosa/NOA)
  └── demo.py            ← aspiracional (número de demostración)
        │
        ▼
src/messages/
  ├── messages_common.py       ← wrapper con @property
  ├── messages_client.py       ← wrapper con @property
  ├── messages_appointments.py ← wrapper + helpers estáticos
  └── messages_professional.py ← wrapper con @property
```

Los archivos `messages_*.py` no contienen strings — son wrappers que redirigen
cada atributo al módulo de tono activo via `get_msg()`. Los helpers estáticos
(`format_appointment_status`, `format_zone_options`, etc.) no cambian entre tonos.

---

## Crear un tono nuevo

### Paso 1 — Crear el archivo del tono

```
src/messages/tones/nuevo_tono.py
```

El archivo debe definir **todas** las constantes de los tonos existentes.
La forma más rápida es copiar `coloquial.py` y editar los strings.

```bash
cp src/messages/tones/coloquial.py src/messages/tones/nuevo_tono.py
```

### Paso 2 — Registrarlo en el loader

En `src/messages/loader.py`, agregar el nombre al set `REGISTERED`:

```python
REGISTERED = {"demo", "coloquial", "nuevo_tono"}
```

### Paso 3 — Activarlo en el container

En el `.env` del container que usará el tono nuevo:

```env
TENANT_TONE=nuevo_tono
```

Reiniciar el container:
```bash
docker compose restart whatsapp-demo
```

---

## Guía de estilo aplicada

Los tonos siguen estas reglas extraídas de la guía de estilo del proyecto:

| Regla | Descripción |
|---|---|
| R1 | Terminar en positivo — acción o beneficio |
| R2 | Artículos determinados y posesivos (`tu turno`, `el profesional`) |
| R3 | Una idea por mensaje |
| R4 | Power words — verbos de acción |
| R5 | Sin gerundios encadenados |
| R6 | Oraciones cortas |

---

## Constantes requeridas

Todo tono nuevo debe definir estas constantes. Si falta alguna, `get_msg()`
devuelve `None` y el mensaje queda vacío — verificar con el test al final.

### COMMON

| Constante | Descripción |
|---|---|
| `INVALID_OPTION` | Opción no válida en menú |
| `INVALID_DATE` | Fecha no reconocida |
| `INVALID_TIME` | Horario no reconocido |
| `ERROR_GENERIC` | Error técnico genérico |
| `ERROR_UNKNOWN_STATE` | Estado desconocido |
| `UNKNOWN_QUERY` | Consulta fuera de alcance |
| `HELP_MESSAGE` | Mensaje de ayuda |

### CLIENT — menú y búsqueda

| Constante | Descripción |
|---|---|
| `CLIENT_MAIN_MENU` | Menú principal del cliente |
| `CLIENT_ASK_FECHA` | Pedir fecha |
| `CLIENT_ASK_HORA` | Pedir horario |
| `CLIENT_ASK_ZONA` | Pedir zona |
| `CLIENT_ASK_PREPAGA` | Pedir preferencia prepaga |
| `CLIENT_ASK_SEXO` | Pedir preferencia de género |
| `CLIENT_NO_RESULTS` | Sin resultados para los filtros |
| `CLIENT_MULTIFILTER_ADDED` | Filtro agregado (no se usa, pero debe existir) |
| `CLIENT_SEARCH_QUICK_FORMAT` | Formato de resultado rápido |

### APPOINTMENTS — flujo de citas

| Constante | Variables requeridas | Descripción |
|---|---|---|
| `CLIENT_VIEW_APPOINTMENTS` | `{appointments_list}` | Listado de citas |
| `CLIENT_NO_APPOINTMENTS` | — | Sin citas activas |
| `CLIENT_BOOKING_COLLECT_NAME` | — | Pedir nombre propio |
| `CONFIRM_BOOKING_HEADER` | `{patient_line}`, `{emoji_prof}`, `{prof_name}`, `{day}`, `{date}`, `{start}`, `{end}`, `{phone}` | Pantalla de confirmación pre-booking |
| `BOOKING_SUCCESS` | `{slot_name_upper}`, `{slot_name_plural}`, `{patient_line}`, `{emoji_prof}`, `{prof_name}`, `{day}`, `{date}`, `{start}` | Turno confirmado |
| `BOOKING_ERROR` | — | Error al agendar |
| `CLIENT_APPOINTMENT_DETAIL` | `{professional_name}`, `{date}`, `{time}`, `{professional_phone}`, `{reason_display}`, `{status_badge}`, `{options}` | Detalle de cita |
| `CLIENT_APPOINTMENT_OPTIONS_CONFIRMED` | — | Opciones en cita confirmada |
| `CLIENT_APPOINTMENT_OPTIONS_PENDING` | — | Opciones en cita pendiente |
| `CLIENT_APPOINTMENT_FINISHED` | — | Cita ya pasó |
| `CLIENT_APPOINTMENT_ALREADY_CANCELLED` | — | Ya estaba cancelada |
| `CLIENT_CANCEL_APPOINTMENT_CONFIRM` | `{professional_name}`, `{date}`, `{time}`, `{policy_info}` | Confirmar cancelación |
| `CLIENT_CANCEL_POLICY_INFO` | — | Info de política de cancelación |
| `CLIENT_CANCEL_TOO_LATE` | `{hours_until}`, `{professional_phone}` | No se puede cancelar |
| `CLIENT_CANCEL_BLOCKED_CONFIRMED` | `{article_upper}`, `{slot_name}`, `{contact}` | Cita ya confirmada, no cancelable |
| `CLIENT_CANCEL_ERROR` | — | Error técnico al cancelar |
| `CLIENT_APPOINTMENT_CANCELLED` | — | Cita cancelada exitosamente (usa f-string con `DomainConfig`) |
| `CLIENT_RESCHEDULE_SELECT_DATE` | `{old_date}`, `{old_time}`, `{available_dates}` | Seleccionar fecha |
| `CLIENT_RESCHEDULE_SELECT_TIME` | `{new_date}`, `{available_slots}` | Seleccionar horario |
| `CLIENT_RESCHEDULE_CONFIRM` | `{old_date}`, `{old_time}`, `{new_date}`, `{new_time}`, `{professional_name}` | Confirmar reprogramación |
| `CLIENT_RESCHEDULE_SUCCESS` | `{new_date}`, `{new_time}`, `{professional_name}` | Reprogramación exitosa |
| `CLIENT_RESCHEDULE_TOO_LATE` | `{hours_until}`, `{limit}`, `{professional_phone}` | No se puede reprogramar |
| `CLIENT_NO_DATES_AVAILABLE` | `{days}` | Sin fechas disponibles |
| `CLIENT_NO_SLOTS_AVAILABLE` | — | Sin horarios en esa fecha |

### APPOINTMENTS — flujo de tercero

| Constante | Variables requeridas | Descripción |
|---|---|---|
| `THIRD_PARTY_INTRO` | `{relation}` | Pedir nombre del paciente |
| `THIRD_PARTY_PHONE` | `{name}`, `{relation}` | Pedir teléfono del paciente |
| `THIRD_PARTY_AGE` | `{name}` | Pedir edad del paciente |

### APPOINTMENTS — errores y límites

| Constante | Variables requeridas | Descripción |
|---|---|---|
| `CANCEL_ERROR_TECHNICAL` | — | Error técnico al cancelar |
| `CANCEL_BLOCKED_TIME` | `{hours_until}`, `{professional_phone}` | Ventana de cancelación cerrada |
| `CANCEL_BLOCKED_CONFIRMED` | `{article_upper}`, `{slot_name}`, `{contact}` | Ya confirmada por el sistema |
| `RESCHEDULE_ERROR_TECHNICAL` | — | Error técnico al reprogramar |
| `RESCHEDULE_BLOCKED_TIME` | `{hours_until}`, `{professional_phone}` | Ventana de reprogramación cerrada |
| `APPOINTMENT_LOAD_ERROR` | — | No se pudo cargar la cita |
| `APPOINTMENT_FINISHED` | — | Cita ya terminó |
| `APPOINTMENT_CANT_RESCHEDULE` | `{status}` | Estado no permite reprogramar |
| `DATE_ALREADY_PASSED` | — | Fecha ingresada ya pasó |
| `BOOKING_LIMIT_GLOBAL` | `{count}`, `{s}` | Límite global de turnos activos |
| `BOOKING_LIMIT_PER_PROFESSIONAL` | `{count}`, `{s}`, `{prof_name}` | Límite por profesional |

### PROFESSIONAL

| Constante | Descripción |
|---|---|
| `PROF_MAIN_MENU` | Menú principal del profesional |

---

## Variables de DomainConfig disponibles en los tonos

Los tonos pueden usar `DomainConfig` para adaptar el lenguaje al dominio:

```python
from src.config.domain_config import DomainConfig

# Ejemplos comunes
DomainConfig.APPOINTMENT_NAME          # "cita", "sesión", "turno", "clase"
DomainConfig.APPOINTMENT_NAME_PLURAL   # "citas", "sesiones", "turnos"
DomainConfig.APPOINTMENT_NAME_UPPER    # "Cita", "Sesión", "Turno"
DomainConfig.APPOINTMENT_EMOJI         # "📅", "🧠", "💪"
DomainConfig.PROFESSIONAL_TITLE        # "Profesional", "Psicólogo", "Entrenador"
DomainConfig.PATIENT_LABEL             # "paciente", "cliente"
DomainConfig.CANCELLATION_HOURS_LIMIT  # 24, 2, 1
DomainConfig.CANCELLATION_POLICY       # Texto de política
DomainConfig.EMOJI_PROFESSIONAL        # "👨‍⚕️", "🧠", "💪"
DomainConfig.ZONES                     # {"norte": "Zona Norte", ...}
```

---

## Verificar un tono nuevo

```bash
# Verificar que el tono carga y tiene todas las constantes
docker exec -it whatsapp-demo python -c "
import os
os.environ['TENANT_TONE'] = 'nuevo_tono'
from src.messages.loader import get_msg, reload_tone
reload_tone()

required = [
    'INVALID_OPTION', 'ERROR_GENERIC', 'UNKNOWN_QUERY',
    'CLIENT_MAIN_MENU', 'CLIENT_NO_RESULTS',
    'CONFIRM_BOOKING_HEADER', 'BOOKING_SUCCESS',
    'CLIENT_APPOINTMENT_CANCELLED', 'THIRD_PARTY_INTRO',
    'BOOKING_LIMIT_GLOBAL', 'PROF_MAIN_MENU',
]

missing = [k for k in required if get_msg(k) is None]
if missing:
    print(f'❌ Faltan: {missing}')
else:
    print('✅ Tono completo')
"
```

---

## Tonos activos

| Nombre | Uso | Descripción |
|---|---|---|
| `demo` | Número de demostración del producto | Aspiracional, muestra el valor del sistema en cada interacción |
| `coloquial` | Centros de salud locales (Formosa/NOA) | Vecinal, directo, sin corporativismo |

---

## Política de textos

- Los mensajes **no deben hardcodearse** en `client_handler.py` ni `bot_controller.py`
- Todo string visible al usuario va en el tono correspondiente
- Los helpers estáticos (`format_appointment_status`, etc.) son neutros — no cambian entre tonos
- Al agregar un mensaje nuevo al flujo: agregarlo a **ambos** tonos antes de usarlo en el handler
