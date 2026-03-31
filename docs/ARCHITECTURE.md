# 🏗️ ARQUITECTURA DEL PROYECTO
## Sistema de Gestión de Turnos — WhatsApp Bot
**Versión 6.0 — Marzo 2026**

---

## 📋 ÍNDICE

1. [Visión General](#visión-general)
2. [Estructura del Proyecto](#estructura-del-proyecto)
3. [Sistema de Mensajes y Tonos](#sistema-de-mensajes-y-tonos)
4. [Sistema NLU/ML](#sistema-nluml)
5. [Integraciones Externas](#integraciones-externas)
6. [Seguridad](#seguridad)
7. [Flujo de Datos](#flujo-de-datos)
8. [Base de Datos](#base-de-datos)
9. [CRON Jobs](#cron-jobs)
10. [Setup y Deployment](#setup-y-deployment)
11. [Testing](#testing)
12. [Variables de Entorno](#variables-de-entorno)

---

## 📊 VISIÓN GENERAL

Bot conversacional de WhatsApp para gestión completa de turnos médicos.
Permite a clientes buscar y reservar turnos, y a profesionales gestionar
su agenda — todo desde WhatsApp, sin apps adicionales.

### Stack Tecnológico v6.0

```
WhatsApp (Twilio API)
        │
        ▼
Flask Webhook (Python 3.10)
  ├── /webhook                    ← mensajes de pacientes/profesionales
  └── /google-calendar/webhook   ← notificaciones push de Google
        │
        ▼
┌─────────────────────────────────────────────────────┐
│  BotController (State Machine)                      │
│                                                     │
│  ┌─────────────────────┐  ┌──────────────────────┐  │
│  │  HybridIntentDetect │  │  SessionManager      │  │
│  │  ML (spaCy) 99.2%  │  │  → Redis (TTL 30min) │  │
│  │  + Rules fallback  │  │  → Memory fallback   │  │
│  └─────────────────────┘  └──────────────────────┘  │
│                                                     │
│  ┌─────────────────────┐  ┌──────────────────────┐  │
│  │  ClientHandler      │  │  ProfessionalHandler │  │
│  │  - Búsqueda         │  │  - Ver agenda        │  │
│  │  - Reservas         │  │  - Editar perfil     │  │
│  │  - Cancelaciones    │  │  - Cargar agenda     │  │
│  │  - Reprogramación   │  │    (CSV/Excel)       │  │
│  └─────────────────────┘  └──────────────────────┘  │
└────────────────────────┬────────────────────────────┘
                         │
          ┌──────────────┼──────────────┐
          │              │              │
          ▼              ▼              ▼
      Services       Database      Google Calendar
    (negocio)        (SQLite)       (Service Account)
          │
    ┌─────┴──────────────┐
    │ MessageSender      │  ← reintentos + alerta profesional
    │ CalendarImportSvc  │  ← carga agenda desde WhatsApp
    │ CancellationNotif  │  ← avisa al paciente si prof cancela
    │ WaitlistService    │  ← cubre turnos cancelados
    │ ReminderService    │  ← recordatorios automáticos
    └────────────────────┘
```

### Tecnologías

| Componente | Tecnología |
|---|---|
| Backend | Python 3.10 |
| Framework | Flask |
| Mensajería | Twilio WhatsApp API |
| Base de datos | SQLite |
| Calendario | Google Calendar API (Service Account) |
| NLP/ML | spaCy 3.7.2 + TextCatEnsemble (99.2% accuracy) |
| Sesiones | Redis 7 (fallback: memoria) |
| Container | Docker + Docker Compose |
| Archivos | FileParser (CSV + Excel via openpyxl) |

---

## 📂 ESTRUCTURA DEL PROYECTO

```
booking-chatbot/
│
├── 📁 src/
│   │
│   ├── 📁 api/
│   │   └── whatsapp_handler.py          # Flask webhook, media upload, Calendar webhook
│   │
│   ├── 📁 bot/
│   │   ├── bot_controller.py            # Orquestador principal, NLU dispatch
│   │   ├── client_handler.py            # Flujo del cliente (búsqueda → reserva → gestión)
│   │   ├── professional_handler.py      # Flujo del profesional + importación de agenda
│   │   └── reminder_handler.py          # Manejo de respuestas a recordatorios
│   │
│   ├── 📁 core/
│   │   ├── states.py                    # ConversationState enum + SessionManager
│   │   ├── session_backends.py          # RedisSessionBackend + MemorySessionBackend
│   │   ├── conversation_context.py      # Acumulación de entidades entre mensajes
│   │   ├── validators.py                # E.164, email, fecha
│   │   ├── rate_limiter.py              # Rate limiting webhook (ventana deslizante)
│   │   ├── booking_limiter.py           # Anti-spam en confirmación de booking
│   │   └── message_sender.py            # Envíos centralizados con reintentos
│   │
│   ├── 📁 services/
│   │   ├── user_service.py              # Identificación cliente/profesional/nuevo
│   │   ├── client_service.py            # Búsqueda, cancel (is_owner OR is_patient)
│   │   ├── professional_service.py      # Gestión profesionales, horarios, Calendar
│   │   ├── appointment_service.py       # CRUD citas Google Calendar + BD
│   │   ├── reminder_service.py          # Recordatorios automáticos
│   │   ├── waitlist_service.py          # Sistema waitlist + cascada de ofertas
│   │   ├── cancellation_notifier.py     # Notifica paciente cuando prof cancela
│   │   ├── calendar_import_service.py   # Importación agenda CSV/Excel
│   │   └── intent_detector.py           # Detección de intenciones (reglas, fallback)
│   │
│   ├── 📁 integrations/
│   │   ├── 📁 google_calendar_service/
│   │   │   ├── google_calendar_service.py  # Fachada principal
│   │   │   ├── watch_manager.py            # Watch channels push notifications
│   │   │   ├── appointment_calendar_service.py  # Sync BD ↔ Calendar
│   │   │   ├── 📁 auth/                    # Autenticación Service Account
│   │   │   ├── 📁 calendar/                # Cliente base, availability, events
│   │   │   ├── 📁 config/
│   │   │   ├── 📁 models/
│   │   │   └── 📁 utils/
│   │   │
│   │   ├── 📁 file_parser/
│   │   │   ├── __init__.py
│   │   │   └── file_parser.py           # CSV + Excel → List[Dict]
│   │   │
│   │   └── 📁 ml/
│   │       ├── hybrid_intent_detector.py   # ML + fallback a reglas
│   │       └── ml_intent_detector.py        # Cliente HTTP al ml-intent-service
│   │
│   ├── 📁 database/
│   │   └── database.py                  # SQLite, _init_db, migraciones defensivas
│   │
│   ├── 📁 config/
│   │   ├── domain_config.py             # Presets: SALUD, PSICOLOGIA, BELLEZA, etc.
│   │   ├── domain_filters_config.py     # Filtros habilitados por dominio
│   │   └── settings.py                  # Variables de entorno
│   │
│   ├── 📁 messages/                     # ← Sistema de tonos multi-tenant
│   │   ├── loader.py                    # Carga tono según TENANT_TONE (singleton)
│   │   ├── messages_common.py           # Wrapper @property → loader.get_msg()
│   │   ├── messages_client.py           # Wrapper @property → loader.get_msg()
│   │   ├── messages_appointments.py     # Wrapper @property + helpers estáticos
│   │   ├── messages_professional.py     # Wrapper @property → loader.get_msg()
│   │   └── 📁 tones/
│   │       ├── demo.py                  # Tono aspiracional (número de demostración)
│   │       └── coloquial.py             # Tono vecinal (centros locales, Formosa/NOA)
│   │
│   ├── 📁 utils/
│   │   └── validators.py                # Validación nombre, teléfono AR, edad
│   │
│   ├── 📁 filters/                      # Sistema de filtros modular
│   │   ├── filter_manager.py
│   │   ├── filter_types.py
│   │   ├── base_filter.py
│   │   └── 📁 concrete_filters/
│   │       ├── core_filters.py          # DateFilter, TimeFilter, SpecialtyFilter
│   │       └── optional_filters.py      # ZoneFilter, PrepagaFilter, GenderFilter
│   │
│   └── 📁 cron/
│       └── daily_reminder_job.py        # 5 pasos diarios (ver sección CRON)
│
├── 📁 scripts/
│   ├── setup_calendar_watches.py        # Registra watches para todos los profesionales
│   ├── 📁 csv/
│   │   ├── load_professionals_from_csv.py
│   │   ├── load_patients_from_csv.py    # Crea eventos recurrentes en Calendar
│   │   ├── delete_patients_from_csv.py
│   │   ├── validate_pending_calendars.py
│   │   └── send_calendar_invitations.py
│   └── 📁 ml/
│       ├── generate_training_dataset.py
│       ├── train_spacy_model.py
│       └── evaluate_spacy_model.py
│
├── 📁 tests/
│   ├── test_issue1_booking_limits.py
│   ├── test_issue2_global_booking_limit.py
│   ├── test_issue3_rate_limiter.py
│   ├── test_issue4_expired_offers.py
│   ├── test_issue5_data_isolation.py
│   ├── test_issue6_phone_validation.py
│   ├── test_issue7_cancellation_notifier.py
│   ├── test_issue8_patient_phone.py
│   ├── test_issue9_booking_spam.py
│   ├── test_gap2_message_sender.py
│   ├── test_gap4_file_parser.py
│   ├── test_gap4_calendar_import.py
│   ├── test_gap6_cancellation_policy.py
│   ├── test_gap8_session_manager.py
│   ├── test_gap9_concurrent_booking.py
│   ├── preview_calendar_import_ux.py    # Preview mensajes WhatsApp en terminal
│   └── test_bot_interactive.py          # Test E2E interactivo
│
├── 📁 docker/
│   ├── Dockerfile
│   ├── docker-compose.yml               # whatsapp-demo + redis
│   └── docker-entrypoint.sh
│
├── 📁 data/
│   ├── db/booking.db                    # SQLite (montado como volumen)
│   ├── csv/                             # CSVs de carga
│   └── rechazados/                      # CSVs de pacientes no cargados
│
└── 📁 docs/
    ├── ARCHITECTURE.md                  # Este archivo — índice del sistema
    ├── TONE_SYSTEM.md                   # Sistema de tonos: cómo crear y registrar
    ├── SECURITY.md                      # Plan y estado de seguridad completo
    ├── SETUP_INSTRUCTIONS.md            # Setup paso a paso
    ├── GOOGLE_CALENDAR_SERVICE.md       # Integración Google Calendar
    ├── INTENT_DETECTION_SYSTEM.md       # Sistema NLU/ML en detalle
    ├── ml_agenda_import_intents.md      # Spec intenciones importación agenda
    └── ml_book_for_third_party.md       # Spec intención agendar para terceros
```

---

## 🎨 SISTEMA DE MENSAJES Y TONOS

### Concepto

Cada instancia del bot puede hablar con una personalidad distinta (tono)
sin modificar el código. El tono se configura por variable de entorno.

```env
TENANT_TONE=coloquial   # o: demo
```

### Flujo de carga

```
TENANT_TONE (env)
      │
      ▼
src/messages/loader.py  ← singleton, carga una vez al arrancar
      │
      ├── get_msg("CLAVE") → devuelve el string del tono activo
      │
      ▼
src/messages/messages_*.py  ← wrappers con @property
      │
      ▼
client_handler.py / bot_controller.py  ← usan appointment_messages.CLAVE
```

### Tonos disponibles

| Tono | Uso | Personalidad |
|---|---|---|
| `demo` | Número de demostración | Aspiracional, muestra el valor del producto |
| `coloquial` | Centros locales (Formosa/NOA) | Vecinal, directo, sin corporativismo |

### Agregar un tono nuevo

1. Copiar `src/messages/tones/coloquial.py` → `src/messages/tones/nuevo_tono.py`
2. Editar los strings
3. Registrar en `src/messages/loader.py`: agregar al set `REGISTERED`
4. Configurar en `.env`: `TENANT_TONE=nuevo_tono`

**Documentación completa:** `docs/TONE_SYSTEM.md`

---

## 🤖 SISTEMA NLU/ML

### Arquitectura

```
Mensaje del usuario
        │
        ▼
HybridIntentDetector
  ├── RuleBasedDetector (reglas explícitas)
  └── MLIntentDetector (HTTP → ml-intent-service)
        │
        ├── Si ML confidence >= 0.7 → usar ML
        └── Si ML confidence < 0.7  → usar Rules (fallback)
```

### Intenciones (14)

| Intención | Descripción |
|---|---|
| `search_professional` | Buscar y agendar turno |
| `book_for_third_party` | Agendar para familiar/tercero |
| `view_my_appointments` | Ver mis citas |
| `view_tomorrow` | Ver disponibles mañana |
| `cancel_appointment` | Cancelar turno |
| `info_center` | Información del centro |
| `greeting` | Saludo |
| `unknown` | Fuera de alcance |
| `agenda_view_ready` | Revisar agenda importada (sin errores) |
| `agenda_view_overlaps` | Ver solapamientos de agenda |
| `agenda_view_existing` | Ver pacientes existentes |
| `agenda_view_errors` | Ver errores de importación |
| `agenda_confirm_upload` | Confirmar carga de agenda |
| `agenda_cancel_upload` | Cancelar carga de agenda |

### Estados con NLU habilitado

El NLU solo corre en estados donde el usuario puede escribir texto libre.
En estados de selección numérica (resultados, horarios) se interceptan
los números directamente para evitar clasificaciones erróneas.

```python
nlu_enabled_states = [
    START, CLIENT_MAIN_MENU, CLIENT_NEW_USER_MENU,
    CLIENT_MULTIFILTER_MENU, CLIENT_FILTER_INPUT,
    CLIENT_VIEW_APPOINTMENTS, CLIENT_APPOINTMENT_DETAIL,
    CLIENT_BOOKING_CONFIRMED, PROF_MAIN_MENU, PROF_AGENDA_IMPORT_REVIEW,
]
```

### Cambio de intención en estados numéricos

Si el usuario escribe texto libre en un estado de selección numérica,
el handler devuelve `None`. El `BotController` detecta el `None`,
resetea el estado a `START` y reprocesa el mensaje por el NLU en el
mismo turno — sin pedirle al usuario que repita.

---

## 🔗 INTEGRACIONES EXTERNAS

### Twilio WhatsApp

- Recibe mensajes via webhook POST `/webhook`
- Envía mensajes via TwiML XML
- Usa templates aprobados para recordatorios y ofertas de waitlist
- Valida firma HMAC en producción

### Google Calendar

- Service Account con acceso delegado a calendarios de profesionales
- Push notifications via watch channels (renuevan cada 7 días)
- Sync bidireccional: booking bot ↔ Google Calendar
- Slot calculation: `working_hours - booked_events = available_slots`

### ml-intent-service

- Container separado (puerto 8000, red Docker interna)
- spaCy 3.7.2 + TextCatEnsemble
- Accuracy: 99.2% (344 ejemplos base → 6964 con augmentation)
- Autenticado via `ML_API_KEY`

---

## 🔒 SEGURIDAD

Ver `docs/SECURITY.md` para el detalle completo.

### Medidas activas

- Validación de firma Twilio (HMAC) en producción
- Rate limiting: 10 msgs/min por número, bloqueo 5 min
- Anti-spam en booking: 5 intentos/hora por número
- Límite de turnos activos: 2 por profesional, 5 global
- Validación de ownership: cliente solo puede cancelar sus propias citas
- Validación de inputs: nombre (max 60 chars, sin números), teléfono AR, edad

---

## 🔄 FLUJO DE DATOS

### Búsqueda y reserva de turno

```
Usuario: "turno con gaston el jueves"
    │
    ▼
NLU → search_professional
    │   entities: {fecha, professional_name}
    ▼
ConversationContext.update_entities()
    │   (reset si viene desde START/MAIN_MENU)
    ▼
_execute_smart_search()
    │
    ├── client_service.search_professionals_by_filters()
    │       └── professional_service.get_available_slots() [cache 15min]
    │
    └── format_search_results_with_slots() → CLIENT_SHOW_RESULTS
            │
            ▼ (usuario selecciona número o nombre)
        CLIENT_VIEW_DETAIL_WITH_BOOKING
            │
            ▼ (usuario selecciona horario)
        CLIENT_CONFIRM_BOOKING
            │
            ▼ (usuario confirma)
        AppointmentCalendarService.create_appointment()
            ├── GoogleCalendarService.create_event()
            └── db.create_appointment()
```

### Importación de agenda (profesional)

```
Profesional sube CSV/Excel via WhatsApp
    │
    ▼
FileParser → List[Dict] de pacientes
    │
    ▼
CalendarImportService.preview()
    │   analiza solapamientos, existentes, errores
    ▼
Profesional puede explorar subconjuntos
    │
    ▼
Profesional confirma → CalendarImportService.execute()
    ├── db.add_client() por cada paciente
    ├── GoogleCalendarService.create_recurring_appointment()
    └── db.create_appointment() primera ocurrencia
```

---

## 🗄️ BASE DE DATOS

### Tablas principales

```sql
professionals           -- profesionales registrados + calendar_id
clients                 -- pacientes registrados
appointments            -- turnos (google_event_id, patient_phone,
                        --  cancellation_notified, last_google_sync)
appointment_history     -- historial de cambios de status
appointment_reminders   -- recordatorios enviados
slot_offers             -- ofertas de waitlist
calendar_watches        -- watch channels de Google Calendar
message_retry_queue     -- cola de reintentos de mensajes fallidos
notifications           -- notificaciones del sistema
```

### Columnas agregadas recientemente

```sql
-- appointments:
patient_phone TEXT DEFAULT NULL          -- Issue 8: paciente real
cancellation_notified BOOLEAN DEFAULT 0  -- Issue 7: evita doble notif
last_google_sync TIMESTAMP               -- Issue 7: última sync

-- message_retry_queue (tabla nueva):
to_phone, message, professional_phone, patient_name,
appointment_id, content_sid, content_variables,
attempts, next_retry_at, status
```

### Migraciones defensivas

En `_init_db()`, al final del método, hay un bloque de `ALTER TABLE`
con `try/except` silencioso para agregar columnas en BD existentes
sin romper instalaciones previas.

---

## ⏰ CRON JOBS

El CRON corre diariamente a las 17:30 via:
```bash
30 17 * * * docker exec whatsapp-demo python -m src.cron.daily_reminder_job
```

### Pasos en orden

```
Paso 0: MessageSender.process_retry_queue()
        → reintenta mensajes que fallaron en las últimas horas

Paso 1: ReminderService.send_daily_reminders()
        → busca citas de mañana → envía recordatorio WhatsApp
        → paciente puede confirmar (1), reprogramar (2) o cancelar (0)

Paso 2: WaitlistService.process_expired_offers()
        → limpia ofertas expiradas
        → reintenta cascada con siguiente candidato

Paso 3: run_cancellation_sync()
        → fallback del webhook push
        → sincroniza citas confirmadas de los próximos 7 días
        → detecta cancelaciones no notificadas

Paso 4: WatchManager.renew_all_expiring()
        → renueva watch channels que vencen en las próximas 24hs
        → los watches expiran cada 7 días
```

---

## 🚀 SETUP Y DEPLOYMENT

### Requisitos

- Docker + Docker Compose
- Cuenta Twilio con número WhatsApp Business
- Proyecto Google Cloud con Calendar API habilitada
- Service Account con acceso a calendarios de los profesionales
- Dominio HTTPS público (para webhooks de Twilio y Google)

### Primera vez

```bash
# 1. Clonar y configurar
cp docker/.env.example docker/.env
# Editar .env con credenciales reales

# 2. Levantar
docker compose -f docker/docker-compose.yml up --build -d

# 3. Cargar profesionales
docker exec -it whatsapp-demo python scripts/csv/load_professionals_from_csv.py \
    /app/data/csv/profesionales.csv

# 4. Registrar watches de Google Calendar
docker exec -it whatsapp-demo python scripts/setup_calendar_watches.py

# 5. Verificar
docker exec -it whatsapp-demo python -c "
from src.core.states import session_manager
print(session_manager.get_stats())
"
```

### Agregar nuevo profesional

```bash
# 1. Agregar al CSV y recargar
docker exec -it whatsapp-demo python scripts/csv/load_professionals_from_csv.py \
    /app/data/csv/profesionales.csv

# 2. Registrar su watch de Calendar
docker exec -it whatsapp-demo python scripts/setup_calendar_watches.py
```

---

## 🧪 TESTING

### Tests de seguridad (issues 1-9)

```bash
docker exec -it whatsapp-demo python tests/test_issue1_booking_limits.py
docker exec -it whatsapp-demo python tests/test_issue2_global_booking_limit.py
docker exec -it whatsapp-demo python tests/test_issue3_rate_limiter.py
docker exec -it whatsapp-demo python tests/test_issue4_expired_offers.py
docker exec -it whatsapp-demo python tests/test_issue5_data_isolation.py
docker exec -it whatsapp-demo python tests/test_issue6_phone_validation.py
docker exec -it whatsapp-demo python tests/test_issue7_cancellation_notifier.py
docker exec -it whatsapp-demo python tests/test_issue8_patient_phone.py
docker exec -it whatsapp-demo python tests/test_issue9_booking_spam.py
```

### Tests de funcionalidades (GAPs)

```bash
docker exec -it whatsapp-demo python tests/test_gap2_message_sender.py
docker exec -it whatsapp-demo python tests/test_gap4_file_parser.py
docker exec -it whatsapp-demo python tests/test_gap4_calendar_import.py
docker exec -it whatsapp-demo python tests/test_gap6_cancellation_policy.py
docker exec -it whatsapp-demo python tests/test_gap8_session_manager.py
docker exec -it whatsapp-demo python tests/test_gap9_concurrent_booking.py
```

### Test E2E interactivo

```bash
python tests/test_bot_interactive.py

# Escenarios automatizados
python tests/test_bot_interactive.py --scenario filters
python tests/test_bot_interactive.py --scenario quick
```

### Verificar tono activo

```bash
docker exec -it whatsapp-demo python -c "
import os; os.environ['TENANT_TONE'] = 'coloquial'
from src.messages.loader import get_msg, reload_tone
reload_tone()
print(get_msg('CLIENT_MAIN_MENU'))
"
```

---

## 🔑 VARIABLES DE ENTORNO

```bash
# ── Twilio ──────────────────────────────────────────────────────
TWILIO_ACCOUNT_SID=ACxxxx
TWILIO_AUTH_TOKEN=xxxx
TWILIO_WHATSAPP_NUMBER=whatsapp:+549...
TWILIO_REMINDER_TEMPLATE_SID=HXxxxx   # Template aprobado para recordatorios
TWILIO_SLOT_OFFER_TEMPLATE_SID=HXxxxx # Template para ofertas de waitlist

# ── Google Calendar ──────────────────────────────────────────────
GOOGLE_CALENDAR_WEBHOOK_URL=https://tu-dominio.com/google-calendar/webhook

# ── Dominio ─────────────────────────────────────────────────────
DOMAIN_PRESET=SALUD   # SALUD | PSICOLOGIA | BELLEZA | LEGAL | FITNESS
                      # Afecta: terminología, políticas de cancelación, filtros

# ── Tono de mensajes ─────────────────────────────────────────────
TENANT_TONE=coloquial # demo | coloquial
                      # Ver docs/TONE_SYSTEM.md para crear tonos nuevos

# ── Redis ────────────────────────────────────────────────────────
REDIS_URL=redis://redis:6379/0
# REDIS_URL=redis://:password@redis:6379/0   ← con auth (recomendado en prod)

# ── ML ───────────────────────────────────────────────────────────
ML_SERVICE_URL=http://ml-service:8000
ML_API_KEY=xxxx

# ── Flask ────────────────────────────────────────────────────────
FLASK_ENV=development
FLASK_PORT=5000
ENVIRONMENT=development

# ── Rate limiting (opcional, override del DomainConfig) ──────────
RATE_LIMIT_MAX_MESSAGES_PER_WINDOW=100  # dev: subir límite para testing
RATE_LIMIT_BLOCK_MINUTES=0              # dev: sin bloqueo

# ── Email / SMTP (para invitaciones a profesionales) ─────────────
SMTP_HOST=mail.tudominio.com
SMTP_PORT=587
SMTP_USER=sistema@tudominio.com
SMTP_PASSWORD=xxxx
```

---

## 📚 DOCUMENTACIÓN ADICIONAL

- `docs/TONE_SYSTEM.md` — sistema de tonos: crear, registrar y verificar
- `docs/SECURITY.md` — detalles de cada medida de seguridad
- `docs/SETUP_INSTRUCTIONS.md` — guía paso a paso
- `docs/GOOGLE_CALENDAR_SERVICE.md` — integración con Google Calendar
- `docs/INTENT_DETECTION_SYSTEM.md` — arquitectura del sistema NLU/ML
- `docs/ml_agenda_import_intents.md` — spec intenciones importación agenda
- `docs/ml_book_for_third_party.md` — spec intención agendar para terceros
- `docs/gap4_agenda_import_spec.md` — spec flujo importación completo

---

**Versión:** 6.0
**Última actualización:** Marzo 2026