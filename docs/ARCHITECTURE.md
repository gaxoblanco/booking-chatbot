# 🏗️ ARQUITECTURA DEL PROYECTO
## Sistema de Gestión de Turnos — WhatsApp Bot
**Versión 5.0 — Marzo 2026**

---

## 📋 ÍNDICE

1. [Visión General](#visión-general)
2. [Estructura del Proyecto](#estructura-del-proyecto)
3. [Sistema NLU/ML](#sistema-nluml)
4. [Integraciones Externas](#integraciones-externas)
5. [Seguridad](#seguridad)
6. [Flujo de Datos](#flujo-de-datos)
7. [Base de Datos](#base-de-datos)
8. [CRON Jobs](#cron-jobs)
9. [Setup y Deployment](#setup-y-deployment)
10. [Testing](#testing)
11. [Variables de Entorno](#variables-de-entorno)

---

## 📊 VISIÓN GENERAL

Bot conversacional de WhatsApp para gestión completa de turnos médicos.
Permite a clientes buscar y reservar turnos, y a profesionales gestionar
su agenda — todo desde WhatsApp, sin apps adicionales.

### Stack Tecnológico v5.0

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
│  │  ML (spaCy) 98.1%  │  │  → Redis (TTL 30min) │  │
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
| NLP/ML | spaCy 3.7.2 + es_core_news_sm (98.1% accuracy) |
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
│   ├── 📁 messages/
│   │   ├── messages_common.py
│   │   ├── messages_client.py
│   │   ├── messages_professional.py
│   │   └── messages_appointments.py
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
    ├── SECURITY.md                      # Plan y estado de seguridad completo
    ├── SETUP_INSTRUCTIONS.md            # Setup paso a paso
    ├── GOOGLE_CALENDAR_SERVICE.md       # Integración Google Calendar
    ├── INTENT_DETECTION_SYSTEM.md       # Sistema NLU/ML en detalle
    ├── ml_agenda_import_intents.md      # Spec intenciones importación agenda
    └── ml_book_for_third_party.md       # Spec intención agendar para terceros
```

---

## 🤖 SISTEMA NLU/ML

### Arquitectura

```
Mensaje del usuario
        │
        ▼
HybridIntentDetector
        │
        ├─ ML prediction (spaCy) ─── confidence ≥ 0.7 ──→ usar intent ML
        │                                                         │
        └─ Rules fallback ────────── confidence < 0.7 ──→ usar intent reglas
                                                                  │
                                                                  ▼
                                                      EntityExtractor
                                                      (especialidad, fecha,
                                                       zona, horario, etc.)
```

### Intenciones actuales

| Intent | Descripción | Estados donde aplica |
|--------|-------------|----------------------|
| `search_professional` | Buscar profesional | START, CLIENT_MAIN_MENU, filtros |
| `view_my_appointments` | Ver mis turnos | START, CLIENT_MAIN_MENU |
| `cancel_appointment` | Cancelar turno | START, CLIENT_MAIN_MENU |
| `reschedule_appointment` | Reprogramar | START, CLIENT_MAIN_MENU |
| `confirm_appointment` | Confirmar turno | AWAITING_REMINDER_RESPONSE |
| `view_tomorrow` | Ver disponibles mañana | START, CLIENT_MAIN_MENU |
| `greeting` | Saludo | Todos |
| `unknown` | No detectado | — |

### Intenciones pendientes de integración

**Grupo A — Importación de agenda** (solo en `PROF_AGENDA_IMPORT_REVIEW`):
```
AGENDA_VIEW_READY, AGENDA_VIEW_OVERLAPS, AGENDA_VIEW_EXISTING,
AGENDA_VIEW_ERRORS, AGENDA_CONFIRM_UPLOAD, AGENDA_CANCEL_UPLOAD
```
Documentación: `docs/ml_agenda_import_intents.md`

**Grupo B — Agendar para terceros** (mismos estados que `search_professional`):
```
BOOK_FOR_THIRD_PARTY
```
Documentación: `docs/ml_book_for_third_party.md`

### Servicio ML

El modelo corre en un container separado (`ml-intent-service`):
- Framework: spaCy 3.7.2
- Dataset: ~1.050 ejemplos
- Accuracy: 98.1% (epoch 19/30)
- RAM: ~647 MiB
- Endpoint: `POST http://ml-service:8000/predict`

---

## 🔗 INTEGRACIONES EXTERNAS

### Google Calendar

```
Service Account
    │
    ├── Lectura de disponibilidad (pull)
    ├── Creación de eventos (al reservar turno)
    ├── Cancelación de eventos (al cancelar turno)
    ├── Eventos recurrentes (carga masiva de pacientes)
    └── Watch channels (notificaciones push)
              │
              └── Google hace POST a /google-calendar/webhook
                  cuando hay cambios en el calendario del profesional
```

**Watch channels:**
- Cada profesional tiene un canal registrado en Google
- Expiran cada 7 días — se renuevan automáticamente en el CRON diario
- Setup inicial: `docker exec -it whatsapp-demo python scripts/setup_calendar_watches.py`
- Si el webhook no llega, el CRON hace sync como fallback (cada 24hs)

### Twilio

- Recibe mensajes de WhatsApp y hace POST a `/webhook`
- Se usa para enviar mensajes salientes (recordatorios, ofertas, notificaciones)
- Templates aprobados para recordatorios (`TWILIO_REMINDER_TEMPLATE_SID`)
- Media (CSV/Excel) se descarga con autenticación básica desde `MediaUrl0`

### Redis

- Sesiones de usuario con TTL de 30 minutos
- Si Redis no está disponible → fallback automático a memoria
- Sin autenticación en desarrollo — configurar password en producción

---

## 🔒 SEGURIDAD

Documentación completa en [`docs/SECURITY.md`](SECURITY.md).

### Resumen — todas las medidas implementadas

| Fase | Issues | Estado |
|------|--------|--------|
| Core (Issues 1-9) | Límites de booking, rate limiting, aislamiento de datos, validación E.164, ownership | ✅ |
| Fase 1 | Firma Twilio, rate limit Calendar webhook, descarga segura | ✅ |
| Fase 2 | Redis con contraseña, MASTER_ACCESS_KEY sin default, PII en logs | ✅ |
| Fase 3 | CSV/Excel injection, channel token en logs | ✅ |

### Archivos clave

| Archivo | Responsabilidad |
|---------|----------------|
| `src/security/twilio_validator.py` | Validación firma HMAC-SHA1 de Twilio |
| `src/core/rate_limiter.py` | Rate limiting webhook + Calendar webhook |
| `src/core/booking_limiter.py` | Anti-spam confirmación de booking |
| `src/core/logger.py` | SanitizedLogger — enmascara PII en logs |
| `src/integrations/file_parser/file_parser.py` | Sanitización CSV injection |

---

## 🔄 FLUJO DE DATOS

### Reserva de turno (cliente)

```
Cliente: "turno con psicóloga mañana"
    │
    ▼
HybridIntentDetector → intent: search_professional
                     → entities: {especialidad: psicología, fecha: mañana}
    │
    ▼
ClientHandler._try_intent_shortcut()
    │
    ▼
ProfessionalService.search_professionals_by_filters()
    │
    ▼
GoogleCalendarService.get_available_slots()  → disponibilidad en tiempo real
    │
    ▼
Cliente elige profesional + fecha + horario
    │
    ▼
BookingLimiter.record_attempt()  → anti-spam
    │
    ▼
AppointmentService.create_appointment()
    ├── Crea evento en Google Calendar del profesional
    └── Guarda en appointments (BD) con google_event_id
    │
    ▼
Cliente recibe confirmación + profesional recibe email de Google
```

### Cancelación del profesional (push)

```
Profesional elimina evento en Google Calendar
    │ < 1 segundo
    ▼
Google POST → /google-calendar/webhook
    │
    ▼
WatchManager.validate_notification_token()  → verifica canal
    │
    ▼
_process_calendar_change()  → hilo daemon
    │
    ▼
AppointmentCalendarService.sync_appointment_from_google()
    → status: 'cancelada_profesional'
    │
    ▼
CancellationNotifier.notify_patient()
    ├── Busca próximo slot disponible (14 días)
    ├── MessageSender.send_with_retry()
    │   └── Si falla 3 veces → alerta al profesional
    └── Marca cancellation_notified=1
```

### Importación de agenda (profesional)

```
Profesional envía CSV/Excel por WhatsApp
    │
    ▼
handle_media_upload()
    ├── identify_user() → is_active + calendar_id ✓
    ├── FileParser.parse() → List[Dict]
    └── CalendarImportService.analyze()
        ├── ready:     nuevos sin conflicto
        ├── duplicate: ya existen
        ├── overlap:   solapamiento de horario
        └── error:     datos inválidos
    │
    ▼
SessionManager.save_session() → Redis
Estado: PROF_AGENDA_IMPORT_REVIEW
    │
Profesional puede explorar subconjuntos (ver listos, solapamientos, etc.)
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

### Preview de mensajes

```bash
# Ver cómo luce el flujo de importación de agenda
docker exec -it whatsapp-demo python tests/preview_calendar_import_ux.py
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

# ── Email / SMTP (para invitaciones a profesionales) ─────────────
SMTP_HOST=mail.tudominio.com
SMTP_PORT=587
SMTP_USER=sistema@tudominio.com
SMTP_PASSWORD=xxxx
```

---

## 📚 DOCUMENTACIÓN ADICIONAL

- `docs/SECURITY.md` — detalles de cada medida de seguridad
- `docs/SETUP_INSTRUCTIONS.md` — guía paso a paso
- `docs/GOOGLE_CALENDAR_SERVICE.md` — integración con Google Calendar
- `docs/INTENT_DETECTION_SYSTEM.md` — arquitectura del sistema NLU/ML
- `docs/ml_agenda_import_intents.md` — spec intenciones importación agenda
- `docs/ml_book_for_third_party.md` — spec intención agendar para terceros
- `docs/gap4_agenda_import_spec.md` — spec flujo importación completo

---

**Versión:** 5.1
**Última actualización:** Marzo 2026