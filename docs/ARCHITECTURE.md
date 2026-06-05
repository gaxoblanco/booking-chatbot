# 🏗️ ARQUITECTURA DEL PROYECTO
## Sistema de Gestión de Turnos — WhatsApp Bot
**Versión 7.0 — Junio 2026**

---

## 📋 ÍNDICE

1. [Visión General](#visión-general)
2. [Estructura del Proyecto](#estructura-del-proyecto)
3. [Modos de Operación](#modos-de-operación)
4. [Sistema de Mensajes y Tonos](#sistema-de-mensajes-y-tonos)
5. [Sistema NLU/ML](#sistema-nluml)
6. [Integraciones Externas](#integraciones-externas)
7. [Seguridad](#seguridad)
8. [Flujo de Datos](#flujo-de-datos)
9. [Base de Datos](#base-de-datos)
10. [CRON Jobs](#cron-jobs)
11. [Setup y Deployment](#setup-y-deployment)
12. [Testing](#testing)
13. [Variables de Entorno](#variables-de-entorno)

---

## 📊 VISIÓN GENERAL

Bot conversacional de WhatsApp para gestión completa de turnos. Permite a clientes
buscar y reservar turnos con profesionales, y a profesionales gestionar su agenda —
todo desde WhatsApp, sin apps adicionales.

Soporta dos modos de operación: **multi-profesional** (centro con N profesionales,
búsqueda con filtros) y **profesional único** (freelancer o consultorio unipersonal,
flujo directo sin filtros).

### Stack Tecnológico v7.0

```
WhatsApp (Meta Cloud API)
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
│  │  - Búsqueda multi   │  │  - Ver agenda        │  │
│  │  - Flujo freelance  │  │  - Editar perfil     │  │
│  │  - Reservas         │  │  - Cargar agenda     │  │
│  │  - Cancelaciones    │  │    (CSV/Excel)       │  │
│  │  - Reprogramación   │  │                      │  │
│  └─────────────────────┘  └──────────────────────┘  │
│                                                     │
│  ┌─────────────────────┐                            │
│  │  FreelanceHandler   │  ← sub-flujo profesional  │
│  │  ReminderHandler    │    único + recordatorios  │
│  └─────────────────────┘                            │
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
          │
    ┌─────┴──────────────────────────┐
    │ ConversationContextService     │  ← inferencia de contexto entre sesiones
    │   EventStore   (BD)            │  ← escritura/lectura conversation_events
    │   ContextService (inferencia)  │  ← had_reminder_sent, interrupted_flow
    └────────────────────────────────┘
```

### Tecnologías

| Componente | Tecnología |
|---|---|
| Backend | Python 3.10 |
| Framework | Flask |
| Mensajería | Meta Cloud API (WhatsApp Business) |
| Base de datos | SQLite |
| Calendario | Google Calendar API (Service Account) |
| NLP/ML | spaCy 3.7.2 + TextCatEnsemble (98.1% accuracy) |
| Sesiones | Redis 7 (fallback: memoria) |
| Container | Docker + Docker Compose |
| Archivos | FileParser (CSV + Excel via openpyxl) |

> **Migración Twilio → Meta:** A partir de v7.0 el bot usa Meta Cloud API directamente.
> No hay intermediario. Ver sección [Meta Cloud API](#meta-cloud-api).

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
│   │   ├── freelance_handler.py         # Sub-flujo profesional único (SINGLE_PROFESSIONAL_MODE)
│   │   └── reminder_handler.py          # Manejo de respuestas a recordatorios
│   │
│   ├── 📁 core/
│   │   ├── states.py                    # ConversationState enum + SessionManager
│   │   │                                #   incluye: CLIENT_FREELANCE_BOOK_DATE/TIME
│   │   │                                #            AWAITING_REMINDER_RESPONSE
│   │   │                                #            AWAITING_SLOT_OFFER (waitlist)
│   │   ├── session_backends.py          # RedisSessionBackend + MemorySessionBackend
│   │   ├── conversation_context.py      # Acumulación de entidades entre mensajes
│   │   ├── validators.py                # E.164, email, fecha
│   │   ├── rate_limiter.py              # Rate limiting webhook (ventana deslizante)
│   │   ├── booking_limiter.py           # Anti-spam en confirmación de booking
│   │   └── message_sender.py            # Envíos centralizados con reintentos
│   │
│   ├── 📁 services/
│   │   ├── user_service.py              # Identificación cliente/profesional/nuevo
│   │   │                                #   generate_welcome_message() es modo-aware
│   │   ├── client_service.py            # Búsqueda, cancel (is_owner OR is_patient)
│   │   │                                #   search_professionals() acepta professional_phone_filter
│   │   ├── professional_service.py      # Gestión profesionales, horarios, Calendar
│   │   ├── appointment_service.py       # CRUD citas Google Calendar + BD
│   │   │                                #   MEET_LINK_MODE controla conferenceDataVersion
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
│   │   ├── 📁 reminder/                 # Ciclo completo de recordatorios
│   │   │   ├── __init__.py
│   │   │   └── reminder_integration_service.py  # Orquesta envío + auto-confirm
│   │   │
│   │   ├── 📁 waitlist/                 # Flujo de adelantamiento de turnos
│   │   │   ├── __init__.py
│   │   │   └── slot_offer_handler.py    # Intercepta respuestas a ofertas de slot
│   │   │
│   │   ├── 📁 scheduler/
│   │   │   └── engine.py                # APScheduler — 7 jobs registrados
│   │   │
│   │   ├── 📁 conversation_context_service/
│   │   │   ├── event_store.py           # Escritura/lectura conversation_events
│   │   │   └── context_service.py       # Inferencia: pending_reminder, interrupted_flow
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
│   │                                    #   search_professionals() acepta professional_phone_filter
│   │
│   ├── 📁 config/
│   │   ├── domain_config.py             # Presets: SALUD, PSICOLOGIA, BELLEZA, etc.
│   │   │                                #   MEET_LINK_MODE: never|always|virtual_only(⚠️pendiente)
│   │   ├── domain_filters_config.py     # Filtros habilitados por dominio
│   │   ├── filter_config.py             # FeatureFlags (ASK_MODALITY stub)
│   │   └── config_validator.py          # Validación de config al boot (fail fast)
│   │                                    #   _validate_meet_link_mode()
│   │                                    #   _validate_single_professional_mode()
│   │                                    #   _validate_demo_mode()
│   │
│   ├── 📁 messages/                     # ← Sistema de tonos multi-tenant
│   │   ├── loader.py                    # Carga tono según TENANT_TONE (singleton)
│   │   ├── messages_common.py           # Wrapper @property → loader.get_msg()
│   │   ├── messages_client.py           # Wrapper @property → loader.get_msg()
│   │   ├── messages_appointments.py     # Wrapper @property + helpers estáticos
│   │   ├── messages_professional.py     # Wrapper @property → loader.get_msg()
│   │   └── 📁 tones/
│   │       ├── demo.py                  # Tono aspiracional (DOMAIN_PRESET=DEMO)
│   │       ├── coloquial.py             # Tono vecinal (centros locales)
│   │       └── freelance.py             # Tono profesional único (SINGLE_PROFESSIONAL_MODE)
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
│   ├── chat.py                           # ⭐ Terminal chat interactivo (desarrollo)
│   ├── 📁 core/
│   ├── 📁 features/
│   │   ├── preview_calendar_import_ux.py
│   │   ├── test_appointments_flow.py
│   │   ├── test_bot_interactive.py        # ⭐ Terminal chat interactivo  - requiere webhook
│   │   ├── test_calendar_import.py
│   │   ├── test_e2e_reminder_flow.py
│   │   ├── test_e2e_waitlist.py
│   │   ├── test_integration.py
│   │   ├── test_meet_link.py            # ⭐ NUEVO — 11 tests para MEET_LINK_MODE
│   │   └── test_user_service_interactive.py
│   ├── 📁 reminders/
│   │   ├── run_all.py
│   │   ├── test_reminder_failures.py
│   │   ├── test_reminder_responses.py
│   │   ├── test_reminder_window.py
│   │   └── test_retry.py
│   ├── 📁 security/
│   │   ├── test_message_sanitizer.py
│   │   ├── test_security_phase1.py
│   │   ├── test_security_phase2.py
│   │   └── test_security_phase3.py
│   ├── 📁 smoke/
│   │   ├── check_pii_logs.py
│   │   └── test_smoke_production.py
│   └── 📁 waitlist/
│       └── test_waitlist_e2e.py
│
├── 📁 docker/
│   ├── Dockerfile
│   ├── docker-compose.yml               # whatsapp-demo + redis
│   ├── .env.example                     # Template completo con todos los modos
│   └── docker-entrypoint.sh
│
├── 📁 data/
│   ├── db/booking.db                    # SQLite (montado como volumen)
│   ├── csv/                             # CSVs de carga
│   └── rechazados/                      # CSVs de pacientes no cargados
│
└── 📁 docs/
    ├── ARCHITECTURE.md                  # Este archivo
    ├── TONE_SYSTEM.md                   # Sistema de tonos: crear, registrar y verificar
    ├── SECURITY.md                      # Plan y estado de seguridad completo
    ├── SETUP_INSTRUCTIONS.md            # Setup paso a paso
    ├── SERVER_CONFIG.md                 # Configuración del VPS (Donweb)
    ├── GOOGLE_CALENDAR_SERVICE.md       # Integración Google Calendar
    ├── INTENT_DETECTION_SYSTEM.md       # Arquitectura del sistema NLU/ML
    ├── REMINDER_INTEGRATION.md          # Ciclo completo de recordatorios automáticos
    ├── WAITLIST_INTEGRATION.md          # Ciclo completo de adelantamiento de turnos
    ├── CONVERSATION_CONTEXT_SERVICE.md  # Sistema de contexto conversacional entre sesiones
    ├── CONVERSATION_ROUTES.md           # Mapa de rutas conversacionales
    ├── MEET_LINK_MODE.md                # Feature MEET_LINK_MODE (⚠️ parcialmente implementado)
    ├── ml_agenda_import_intents.md      # Spec intenciones importación agenda
    └── ml_book_for_third_party.md       # Spec intención agendar para terceros
```

---

## 🔀 MODOS DE OPERACIÓN

El sistema soporta dos modos que se configuran íntegramente desde el `.env`.
No hay cambios de código al cambiar de modo.

### Modo multi-profesional (default)

Centro con N profesionales. El cliente busca con filtros (zona, fecha, especialidad, etc.),
ve una lista de resultados y elige.

```env
SINGLE_PROFESSIONAL_MODE=false
DOMAIN_PRESET=SALUD          # o PSICOLOGIA, BELLEZA, etc.
TENANT_TONE=coloquial
MEET_LINK_MODE=never
```

### Modo profesional único (freelance)

Freelancer o consultorio unipersonal. No hay búsqueda ni filtros de selección —
el sistema va directo a fecha, horario y slots del profesional configurado.

```env
SINGLE_PROFESSIONAL_MODE=true
SINGLE_PROFESSIONAL_PHONE=+5491112345678   # debe existir en BD
DOMAIN_PRESET=SALUD
TENANT_TONE=freelance
MEET_LINK_MODE=always                       # típico para remoto
```

### Reglas de compatibilidad

| Combinación | Válida | Motivo |
|---|---|---|
| `DOMAIN_PRESET=DEMO` + `TENANT_TONE=demo` | ✅ | Demo del producto |
| `DOMAIN_PRESET=DEMO` + `TENANT_TONE=freelance` | ❌ | El validador lo bloquea |
| `SINGLE_PROFESSIONAL_MODE=true` + `TENANT_TONE=coloquial` | ❌ | El validador lo bloquea |
| `SINGLE_PROFESSIONAL_MODE=true` + `DOMAIN_PRESET=DEMO` | ❌ | El validador lo bloquea |
| `MEET_LINK_MODE=virtual_only` | ❌ | Pendiente — requiere ASK_MODALITY |

El `config_validator.py` valida estas reglas al arrancar — fail fast, el servidor
no levanta si la configuración es incoherente.

### Flujo del modo profesional único

```
Cliente: "hola"
    │
    ▼ handle_client_main_menu → switch SINGLE_PROFESSIONAL_MODE
    │
    ▼ handle_freelance_start()          [CLIENT_FREELANCE_BOOK_DATE]
    │   "¿Qué fecha te viene bien?"
    │
    ▼ handle_freelance_book_date()
    │   parse_date() → guardar en session.temp
    │
    ▼ handle_freelance_book_time()      [CLIENT_FREELANCE_BOOK_TIME]
    │   "¿Mañana / tarde / me da igual?"
    │
    ▼ pantalla de filtros activos (vitrina del sistema)
    │   muestra: fecha, horario, modalidad — solo informativos
    │   1 sola opción: "Ver horarios disponibles"
    │
    ▼ _load_professional_and_show_detail()
    │   search_professionals(professional_phone_filter=SINGLE_PROFESSIONAL_PHONE)
    │
    ▼ CLIENT_VIEW_DETAIL_WITH_BOOKING   ← punto de reunificación con flujo normal
    │
    ▼ ... booking, confirmación, recordatorios, cancelación (sin cambios)
```

---

## 🎨 SISTEMA DE MENSAJES Y TONOS

Cada instancia habla con una personalidad distinta sin modificar código.
El tono se configura por variable de entorno y se valida al arrancar.

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
```

### Tonos disponibles

| Tono | Uso | Requiere | Personalidad |
|---|---|---|---|
| `coloquial` | Centros locales | `SINGLE_PROFESSIONAL_MODE=false` | Vecinal, directo |
| `freelance` | Profesional único | `SINGLE_PROFESSIONAL_MODE=true` | Personal, técnico |
| `demo` | Demostración del producto | `DOMAIN_PRESET=DEMO` | Aspiracional |

### Constantes específicas del tono freelance

```python
CLIENT_FREELANCE_FILTERS_INFO      # Pantalla de filtros activos (vitrina)
CLIENT_FREELANCE_FILTER_LINE_*     # Líneas individuales de filtros
```

### Agregar un tono nuevo

1. Copiar `src/messages/tones/coloquial.py` → `src/messages/tones/nuevo_tono.py`
2. Editar los strings
3. Registrar en `src/messages/loader.py`: agregar al set `REGISTERED`
4. Configurar en `.env`: `TENANT_TONE=nuevo_tono`
5. Si requiere validación cruzada con otros flags, agregar en `config_validator.py`

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
| `info_center` | Información del centro/servicio |
| `greeting` | Saludo |
| `unknown` | Fuera de alcance |
| `agenda_view_ready` | Revisar agenda importada (sin errores) |
| `agenda_view_overlaps` | Ver solapamientos de agenda |
| `agenda_view_existing` | Ver pacientes existentes |
| `agenda_view_errors` | Ver errores de importación |
| `agenda_confirm_upload` | Confirmar carga de agenda |
| `agenda_cancel_upload` | Cancelar carga de agenda |

### Estados con NLU habilitado

```python
nlu_enabled_states = [
    START, CLIENT_MAIN_MENU, CLIENT_NEW_USER_MENU,
    CLIENT_MULTIFILTER_MENU, CLIENT_FILTER_INPUT,
    CLIENT_VIEW_APPOINTMENTS, PROF_MAIN_MENU,
    PROF_AGENDA_IMPORT_REVIEW,
    CLIENT_FREELANCE_BOOK_DATE,  # acepta fecha en texto libre
    # CLIENT_FREELANCE_BOOK_TIME excluido: solo acepta 1/2/3
]
```

---

## 🔗 INTEGRACIONES EXTERNAS

### Meta Cloud API

A partir de v7.0 el bot usa Meta Cloud API directamente (sin Twilio).

- Recibe mensajes via webhook `POST /webhook`
- Verifica firma `X-Hub-Signature-256` (HMAC-SHA256 con APP_SECRET)
- Envía mensajes via `POST https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages`
- Usa templates aprobados para recordatorios y ofertas de waitlist
- Verificación del webhook via `GET /webhook` con `hub.verify_token`

Credenciales requeridas:

```env
META_PHONE_NUMBER_ID=...
META_WHATSAPP_TOKEN=...          # token permanente (no el temporal de 24hs)
META_APP_SECRET=...
META_WEBHOOK_VERIFY_TOKEN=...
META_API_VERSION=v22.0
```

### Google Calendar

- Service Account con acceso delegado a calendarios de profesionales
- Push notifications via watch channels (renuevan cada 7 días)
- Sync bidireccional: booking bot ↔ Google Calendar
- Slot calculation: `working_hours - booked_events = available_slots`
- `MEET_LINK_MODE` controla si se genera link de Meet (ver más abajo)

### MEET_LINK_MODE ⚠️ Parcialmente implementado

Controla si se genera link de Google Meet al crear la cita en Calendar.

| Modo | Comportamiento | Estado |
|---|---|---|
| `never` | Sin Meet link | ✅ Funcional |
| `always` | Siempre genera Meet | ✅ Funcional |
| `virtual_only` | Solo turnos virtuales | ⚠️ Bloqueado — requiere `ASK_MODALITY` |

El validador bloquea `virtual_only` hasta que el flujo de modalidad esté implementado.
Ver `docs/MEET_LINK_MODE.md` para el plan completo de implementación.

### ml-intent-service

- Container separado (puerto 8000, red Docker interna)
- spaCy 3.7.2 + TextCatEnsemble
- Accuracy: 98.1%
- Autenticado via `ML_API_KEY`

---

## 🔒 SEGURIDAD

Ver `docs/SECURITY.md` y `docs/SERVER_CONFIG.md` para el detalle completo.

### Medidas activas

- Validación de firma Meta (HMAC-SHA256) en producción
- Rate limiting: ventana deslizante por número, bloqueo configurable
- Anti-spam en booking: límite por hora por número
- Límite de turnos activos: 2 por profesional, 5 global
- Validación de ownership: cliente solo puede cancelar sus propias citas
- Validación de inputs: nombre, teléfono AR E.164, edad

### Infraestructura (VPS Donweb)

- Nginx como proxy inverso con SSL (Let's Encrypt)
- UFW con política deny-by-default
- SSH en puerto no estándar con clave pública
- Fail2ban activo
- ml-service solo accesible por red Docker interna

---

## 🔄 FLUJO DE DATOS

### Búsqueda y reserva — modo multi-profesional

```
Usuario: "turno con gaston el jueves"
    │
    ▼
NLU → search_professional + entities: {fecha, professional_name}
    │
    ▼
ConversationContext.update_entities()
    │
    ▼
_execute_smart_search()
    ├── client_service.search_professionals_by_filters()
    │       └── professional_service.get_available_slots() [cache 15min]
    └── format_search_results_with_slots() → CLIENT_SHOW_RESULTS
            │
            ▼ (usuario selecciona número)
        CLIENT_VIEW_DETAIL_WITH_BOOKING
            │
            ▼ (usuario selecciona horario)
        CLIENT_CONFIRM_BOOKING
            │
            ▼ (usuario confirma)
        AppointmentCalendarService.create_appointment()
            ├── GoogleCalendarService.create_event() [MEET_LINK_MODE]
            └── db.create_appointment()
```

### Búsqueda y reserva — modo profesional único

```
Cliente: "hola" → menú simplificado (sin "buscar", sin "mañana")
    │
    ▼ opción 1 → FreelanceHandler
    ├── Paso 1: fecha libre (parse_date)
    ├── Paso 2: horario preferido (mañana/tarde/cualquiera)
    ├── Paso 3: vitrina de filtros activos + confirmar
    └── search_professionals(professional_phone_filter=PHONE)
            │
            ▼ (1 resultado, directo al detalle)
        CLIENT_VIEW_DETAIL_WITH_BOOKING  ← mismo flujo de booking que multi
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
appointments            -- turnos (google_event_id, patient_phone, meet_link,
                        --  cancellation_notified, last_google_sync)
appointment_history     -- historial de cambios de status
appointment_reminders   -- recordatorios enviados
slot_offers             -- ofertas de waitlist
calendar_watches        -- watch channels de Google Calendar
message_retry_queue     -- cola de reintentos de mensajes fallidos
notifications           -- notificaciones del sistema
conversation_events     -- eventos de conversación por usuario
                        --  event_type, intent, confidence, state_before/after
                        --  retención: 7 días, purga automática
```

### Columnas agregadas recientemente

```sql
-- appointments:
patient_phone TEXT DEFAULT NULL          -- Issue 8: paciente real
cancellation_notified BOOLEAN DEFAULT 0  -- Issue 7: evita doble notif
last_google_sync TIMESTAMP               -- Issue 7: última sync
meet_link TEXT DEFAULT NULL              -- MEET_LINK_MODE=always

-- message_retry_queue (tabla nueva):
to_phone, message, professional_phone, patient_name,
appointment_id, content_sid, content_variables,
attempts, next_retry_at, status
```

### Migraciones defensivas

En `_init_db()`, al final del método, hay un bloque de `ALTER TABLE`
con `try/except` silencioso para agregar columnas en BD existentes
sin romper instalaciones previas.

El índice parcial de appointments evita que el sistema de waitlist falle
al reusar slots cancelados:

```sql
CREATE UNIQUE INDEX idx_appointments_slot_active
ON appointments(professional_phone, appointment_date, start)
WHERE status NOT IN ('cancelada_cliente', 'cancelada_profesional')
```

---

## ⏰ CRON JOBS

Los jobs corren via **APScheduler** dentro del proceso Flask.
En `FLASK_ENV=development` los jobs automáticos están pausados —
se disparan manualmente via comando secreto del bot.

### Jobs registrados (7)

```
job_reminders     → cron 17:30  — ReminderIntegrationService.run_send_cycle()
job_auto_confirm  → cron 20:30  — ReminderIntegrationService.run_confirm_cycle()
job_retry_queue   → interval 1h — MessageSender.process_retry_queue()
job_calendar_sync → cron 17:31  — sync cancelaciones desde Google Calendar
job_watches       → cron 17:32  — WatchManager.renew_all_expiring()
job_waitlist      → cron 17:33  — WaitlistService.process_expired_offers()
job_purge_events  → cron diario — event_store.purge_old_events() (>7 días)
```

### Comandos secretos (solo development)

```
enviar recordatorio   → dispara job_reminders ahora
enviar recordatorios  → idem
scheduler status      → muestra estado y próxima ejecución de cada job
```

### Fallback CLI

```bash
docker exec whatsapp-demo python -m src.cron.daily_reminder_job
```

---

## 🚀 SETUP Y DEPLOYMENT

### Requisitos

- Docker + Docker Compose
- App de Meta con WhatsApp Business API habilitada
- Proyecto Google Cloud con Calendar API habilitada
- Service Account con acceso a calendarios de los profesionales
- Dominio HTTPS público (para webhooks de Meta y Google)

### Primera vez

```bash
# 1. Clonar y configurar
cp docker/.env.example docker/.env
# Editar .env con credenciales reales

# 2. Levantar
docker compose -f docker/docker-compose.yml up --build -d

# 3. Verificar que arrancó correctamente
docker compose logs whatsapp-demo | grep "\[CONFIG\]"
# Esperado: [CONFIG] ✅ Configuración válida

# 4. Cargar profesionales
docker exec -it whatsapp-demo python scripts/csv/load_professionals_from_csv.py \
    /app/data/csv/profesionales.csv

# 5. Registrar watches de Google Calendar
docker exec -it whatsapp-demo python scripts/setup_calendar_watches.py
```

### Agregar nuevo profesional

```bash
# 1. Agregar al CSV y recargar
docker exec -it whatsapp-demo python scripts/csv/load_professionals_from_csv.py \
    /app/data/csv/profesionales.csv

# 2. Registrar su watch de Calendar
docker exec -it whatsapp-demo python scripts/setup_calendar_watches.py
```

### Modo profesional único — setup inicial

```bash
# En docker/.env:
SINGLE_PROFESSIONAL_MODE=true
SINGLE_PROFESSIONAL_PHONE=+5491112345678
TENANT_TONE=freelance
DOMAIN_PRESET=SALUD
MEET_LINK_MODE=always  # si el profesional trabaja remoto

# El validador verifica al arrancar que:
# - SINGLE_PROFESSIONAL_PHONE esté configurado
# - El teléfono exista en la BD
# - TENANT_TONE=freelance
# - DOMAIN_PRESET != DEMO
```

---

## 🧪 TESTING

### Terminal chat (principal para desarrollo)

```bash
docker exec -it whatsapp-demo python tests/chat.py
```

Comandos disponibles dentro del chat:

| Comando | Acción |
|---|---|
| `/switch` | Alterna entre cliente y profesional |
| `/new` | Reinicia la sesión del número activo |
| `/info` | Muestra estado actual de la sesión |
| `/phone XXXX` | Cambia el número manualmente |
| `/exit` | Salir |

### Tests de seguridad (issues 1-9)

```bash
docker exec -it whatsapp-demo python tests/test_issue1_booking_limits.py
# ... test_issue2 a test_issue9
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

### Tests de waitlist y recordatorios

```bash
# Waitlist E2E
docker exec -it whatsapp-demo python tests/waitlist/test_waitlist_e2e.py
docker exec -it whatsapp-demo python tests/waitlist/test_waitlist_e2e.py --accept
docker exec -it whatsapp-demo python tests/waitlist/test_waitlist_e2e.py --reject

# Recordatorios
docker exec -it whatsapp-demo python tests/reminders/test_reminder_window.py
docker exec -it whatsapp-demo python tests/reminders/test_reminder_responses.py
```

### Verificar tono activo

```bash
docker exec whatsapp-demo python -c "
import os; os.environ['TENANT_TONE'] = 'freelance'
from src.messages.loader import get_msg, reload_tone
reload_tone()
print(get_msg('CLIENT_FREELANCE_FILTERS_INFO'))
"
```

### Verificar modo activo al arrancar

```bash
docker compose logs whatsapp-demo | grep "\[CONFIG\]"
# Modo multi:    [CONFIG] ✅ Configuración válida
# Modo único:    [CONFIG] ✅ Modo profesional único — Gaston Blanco
#                [CONFIG] ✅ Configuración válida
```

---

## 🔑 VARIABLES DE ENTORNO

```bash
# ── Meta Cloud API ───────────────────────────────────────
META_PHONE_NUMBER_ID=...          # ID del número (no el número en sí)
META_WHATSAPP_TOKEN=...           # Token permanente de la app
META_APP_SECRET=...               # App Secret (para validar firma HMAC)
META_WEBHOOK_VERIFY_TOKEN=...     # Token de verificación del webhook
META_API_VERSION=v22.0

# Templates aprobados en Meta Business Suite
META_REMINDER_TEMPLATE_NAME=recordatorio_turno
META_REMINDER_TEMPLATE_LANG=es_AR
META_SLOT_OFFER_TEMPLATE_NAME=oferta_turno_adelantado
META_SLOT_OFFER_TEMPLATE_LANG=es_AR

# ── Google Calendar ──────────────────────────────────────
GOOGLE_CALENDAR_WEBHOOK_URL=https://tu-dominio.com/google-calendar/webhook

# ── Dominio y modo ───────────────────────────────────────
DOMAIN_PRESET=SALUD               # SALUD|PSICOLOGIA|BELLEZA|LEGAL|FITNESS|DEMO
TENANT_TONE=coloquial             # coloquial|freelance|demo
MEET_LINK_MODE=never              # never|always  (virtual_only: pendiente)

# Modo profesional único
SINGLE_PROFESSIONAL_MODE=false
SINGLE_PROFESSIONAL_PHONE=        # obligatorio si SINGLE_PROFESSIONAL_MODE=true

# ── Redis ────────────────────────────────────────────────
REDIS_URL=redis://redis:6379/0

# ── ML ───────────────────────────────────────────────────
ML_SERVICE_URL=http://ml-intent-service:8000
ML_API_KEY=...

# ── Flask ────────────────────────────────────────────────
FLASK_ENV=development
FLASK_PORT=5000
ENVIRONMENT=development
WEBHOOK_URL=https://tu-dominio.com

# ── Recordatorios ────────────────────────────────────────
REMINDER_SEND_TIME=17:30
REMINDER_CLOSE_TIME=20:30
RESCHEDULE_HOURS_LIMIT=22

# ── Notificaciones y contacto ────────────────────────────
NOTIFY_PROFESSIONAL=true
CENTER_EMAIL=contacto@tu-dominio.com
CENTER_HOURS_WD=9:00 - 18:00
CENTER_HOURS_SAT=9:00 - 13:00
CENTER_PHONE=+54 11 0000-0000

# ── Administración ───────────────────────────────────────
MASTER_ACCESS_KEY=...             # obligatorio en production
ALLOW_KEY_REUSE=false

# ── SMTP ─────────────────────────────────────────────────
SMTP_HOST=mail.tu-dominio.com
SMTP_PORT=465
SMTP_USER=sistema@tu-dominio.com
SMTP_PASSWORD=...
SMTP_FROM_NAME=Agenda Asistida
```

---

## 📚 DOCUMENTACIÓN ADICIONAL

- `docs/TONE_SYSTEM.md` — sistema de tonos: crear, registrar y verificar
- `docs/SECURITY.md` — detalles de cada medida de seguridad
- `docs/SERVER_CONFIG.md` — configuración del VPS, Nginx, SSL, Fail2ban
- `docs/SETUP_INSTRUCTIONS.md` — guía paso a paso
- `docs/GOOGLE_CALENDAR_SERVICE.md` — integración con Google Calendar
- `docs/INTENT_DETECTION_SYSTEM.md` — arquitectura del sistema NLU/ML
- `docs/REMINDER_INTEGRATION.md` — ciclo completo de recordatorios automáticos
- `docs/WAITLIST_INTEGRATION.md` — ciclo completo de adelantamiento de turnos
- `docs/CONVERSATION_CONTEXT_SERVICE.md` — contexto conversacional entre sesiones
- `docs/CONVERSATION_ROUTES.md` — mapa de rutas conversacionales
- `docs/MEET_LINK_MODE.md` — feature Google Meet (⚠️ parcialmente implementado)
- `docs/ml_agenda_import_intents.md` — spec intenciones importación agenda
- `docs/ml_book_for_third_party.md` — spec intención agendar para terceros

---

**Versión:** 7.0
**Última actualización:** Junio 2026