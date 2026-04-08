# 🧠 CONVERSATION CONTEXT SERVICE
## Sistema de Contexto Conversacional Entre Sesiones
**Versión 1.0 — Abril 2026**

---

## 📋 ÍNDICE

1. [Propósito](#propósito)
2. [Problema que resuelve](#problema-que-resuelve)
3. [Arquitectura](#arquitectura)
4. [Tabla: conversation_events](#tabla-conversation_events)
5. [EventStore](#eventstore)
6. [ContextService](#contextservice)
7. [Integración en el sistema](#integración-en-el-sistema)
8. [Reminder handler v1.1](#reminder-handler-v11)
9. [Política de datos y ética](#política-de-datos-y-ética)
10. [Variables de entorno](#variables-de-entorno)
11. [Testing](#testing)
12. [Pendiente](#pendiente)

---

## 🎯 Propósito

Inferir el contexto de conversación de un usuario entre sesiones, sin depender del estado de Redis (que expira a los 30 minutos) y sin guardar el texto de los mensajes.

Permite responder preguntas como:
- ¿Este usuario tiene un recordatorio pendiente de respuesta?
- ¿Estaba en medio de una reserva cuando expiró su sesión?
- ¿Qué fue lo último que hizo en las últimas 3 horas?

---

## 🔍 Problema que resuelve

### Caso concreto: recordatorios

El sistema envía recordatorios a las 17:30. El paciente puede responder hasta las 20:30. Ese período supera el TTL de sesión de Redis (30 minutos).

Cuando el paciente responde "Confirmo" a las 18:45:

**Antes (v1.0):**
```
[SESSION] Nueva sesión creada → state = START
[NLU] "Confirmo" → Intent.GREETING (confianza 0.75)
→ Bot muestra menú principal. Recordatorio perdido.
```

**Después (v1.1):**
```
[REMINDER] Ventana activa (17:30 → 20:30) ✓
[REMINDER] Sesión en estado neutral ✓
[REMINDER] Reminder pendiente en BD ✓
[REMINDER] "Confirmo" → normalizado a '1' ✓
→ Bot confirma el turno correctamente.
```

---

## 🏗️ Arquitectura

```
bot_controller._process_message()
        │
        ├── Sección 4.2 — ANTES del NLU
        │       should_handle_as_reminder(session, message)
        │           │
        │           ├── Capa 1: ventana horaria (.env)
        │           ├── Capa 2: estado de sesión neutral
        │           └── Capa 3: reminder en BD + normalize_reminder_response()
        │
        ├── Sección NLU (si no es reminder)
        │       hybrid_intent_detector.detect()
        │       │
        │       └── event_store.record(event_type='message', intent, state_before)
        │               ↓
        │           conversation_events (SQLite)
        │
        └── Handler según estado


reminder_service._send_reminder()
        └── event_store.record(event_type='reminder_sent')

reminder_service.handle_reminder_response()
        └── event_store.record(event_type='reminder_response', intent)

reminder_service.auto_confirm_unanswered()
        └── event_store.record(event_type='reminder_response',
                               intent='reminder_auto_confirmed')
```

---

## 🗄️ Tabla: `conversation_events`

```sql
CREATE TABLE conversation_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Quién
    client_phone    TEXT NOT NULL,      -- sin anonimizar, necesario para lookup
    session_id      TEXT,               -- Redis key (= teléfono actualmente)

    -- Qué pasó
    event_type      TEXT NOT NULL CHECK(event_type IN (
                        'message',              -- mensaje procesado por el bot
                        'reminder_sent',        -- recordatorio enviado por WhatsApp
                        'reminder_response',    -- paciente respondió al recordatorio
                        'booking',              -- turno reservado
                        'cancel',               -- turno cancelado
                        'reschedule',           -- turno reprogramado
                        'flow_interrupted'      -- flujo abandonado (futuro)
                    )),

    -- Contexto NLU
    intent          TEXT,               -- valor de Intent enum
    confidence      REAL,               -- confianza 0.0 - 1.0

    -- Contexto de sesión
    state_before    TEXT,               -- ConversationState antes del mensaje
    state_after     TEXT,               -- ConversationState después (pendiente)

    -- Relación con cita
    appointment_id  INTEGER,

    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (client_phone) REFERENCES clients(phone),
    FOREIGN KEY (appointment_id) REFERENCES appointments(id)
)
```

### Índices

```sql
-- Lookup principal: eventos recientes de un usuario
idx_conv_events_phone_time  ON conversation_events(client_phone, created_at DESC)

-- Filtro por tipo de evento
idx_conv_events_type        ON conversation_events(client_phone, event_type, created_at DESC)
```

### Política de retención

Eventos de más de 7 días se eliminan con `event_store.purge_old_events()`.
Pendiente: integrar como job diario en `engine.py`.

---

## 📦 EventStore

**Ubicación:** `src/integrations/conversation_context_service/event_store.py`

Capa de acceso a datos. Stateless, sin lógica de inferencia.

### `record()`

```python
event_store.record(
    client_phone   = "+5491112345678",
    event_type     = "message",          # ver CHECK constraint arriba
    session_id     = phone_number,       # Redis key
    intent         = "search_professional",
    confidence     = 0.92,
    state_before   = "client_main_menu",
    appointment_id = None,               # opcional
)
# Retorna: int (event_id) | None si falla
```

### `get_recent()`

```python
events = event_store.get_recent(
    client_phone   = "+5491112345678",
    window_minutes = 180,   # default: 3 horas
    limit          = 20,
)
# Retorna: List[dict] ordenada ASC (más antiguo primero)
```

### `get_last_event()`

```python
last = event_store.get_last_event(
    client_phone   = "+5491112345678",
    event_type     = "reminder_sent",   # opcional
    window_minutes = 180,
)
# Retorna: dict | None
```

### `purge_old_events()`

```python
deleted = event_store.purge_old_events()
# Retorna: int (filas eliminadas)
# Política: elimina eventos con created_at < (ahora - 7 días)
```

---

## 🔍 ContextService

**Ubicación:** `src/integrations/conversation_context_service/context_service.py`

Inferencia de alto nivel. Solo lectura — no escribe en BD.

### `get_recent_context()`

```python
ctx = context_service.get_recent_context(
    client_phone   = "+5491112345678",
    window_minutes = 180,
)

# Retorna:
{
    'has_recent_activity': True,
    'last_event_type':     'message',
    'last_intent':         'search_professional',
    'last_state':          'client_main_menu',
    'pending_reminder':    False,
    'interrupted_flow':    None,    # 'booking' | 'cancel' | 'reschedule' | 'search' | None
    'minutes_since_last':  12,
}
```

### `had_reminder_sent()`

```python
pending = context_service.had_reminder_sent(client_phone)
# True si hay reminder_sent sin reminder_response posterior
# dentro de la ventana REMINDER_SEND_TIME → REMINDER_CLOSE_TIME
```

### `get_interrupted_flow()`

```python
flow = context_service.get_interrupted_flow(client_phone)
# 'booking' | 'cancel' | 'reschedule' | 'search' | None
# Analiza el último state_after registrado y lo mapea a un flujo
```

### Detección de flujo interrumpido

El servicio mapea estados de sesión a flujos:

| Estados | Flujo |
|---|---|
| `client_confirm_booking`, `client_collect_own_name`, `client_third_party_*` | `booking` |
| `client_cancel_appointment`, `client_cancel_reason`, `client_confirm_cancel` | `cancel` |
| `client_reschedule_*` | `reschedule` |
| `client_multifilter_menu`, `client_filter_input`, `client_show_results`, `client_view_detail` | `search` |
| `awaiting_reminder_response` | `reminder` |
| `start`, `client_main_menu`, `client_booking_confirmed`, `client_cancel_success` | `None` (neutral) |

---

## 🔗 Integración en el sistema

### En `bot_controller.py`

```python
# Sección 4.2 — ANTES del NLU (ya implementado)
if (session.state in _REMINDER_ALLOWED_STATES
        and should_handle_as_reminder(session, message)):
    return handle_reminder_response(session, message)

# Después del NLU — registrar evento (ya implementado)
event_store.record(
    client_phone = phone_number,
    session_id   = phone_number,
    event_type   = 'message',
    intent       = intent_result['intent'].value,
    confidence   = intent_result['confidence'],
    state_before = session.state.value,
)
```

### En `reminder_service.py`

Tres puntos de integración ya implementados:

```python
# 1. Al enviar el recordatorio
event_store.record(client_phone=apt['client_phone'],
                   event_type='reminder_sent',
                   appointment_id=apt['id'])

# 2. Al procesar respuesta del paciente
event_store.record(client_phone=client_phone,
                   event_type='reminder_response',
                   intent=f"reminder_{action}",   # confirmed|rescheduled|cancelled
                   appointment_id=appointment_id)

# 3. Al auto-confirmar por timeout
event_store.record(client_phone=client,
                   event_type='reminder_response',
                   intent='reminder_auto_confirmed',
                   appointment_id=apt_id)
```

---

## 📱 Reminder handler v1.1

### `normalize_reminder_response(message)`

Convierte texto libre a código canónico antes de pasarlo al `reminder_service`.

```python
normalize_reminder_response("Sí, confirmo")  # → '1'
normalize_reminder_response("quiero cambiar el horario")  # → '2'
normalize_reminder_response("no puedo ir")   # → '0'
normalize_reminder_response("gracias")       # → None
```

**Prioridad de matching:** reprogramar > confirmar > cancelar

Razón: "no, quiero reprogramar" contiene `'no'` (cancelar) pero la intención es reprogramar.

### `should_handle_as_reminder(session, message)` — tres capas

```
Capa 1 — Ventana de tiempo
    now_minutes entre REMINDER_SEND_TIME y REMINDER_CLOSE_TIME
    → Fuera: return False inmediato

Capa 2 — Estado de sesión neutral
    session.state en {START, CLIENT_MAIN_MENU,
                      CLIENT_NEW_USER_MENU, AWAITING_REMINDER_RESPONSE}
    → Estado activo: return False (no interrumpir flujo en curso)

Capa 3 — Reminder en BD + mensaje reconocible
    reminder_service._get_pending_reminder(phone) is not None
    AND normalize_reminder_response(message) is not None
    → Ambas condiciones: return True
```

---

## ⚖️ Política de datos y ética

| Dato | Almacenamiento | Justificación |
|---|---|---|
| Teléfono + intent + estado + timestamp | BD (`conversation_events`) | Lookup en tiempo real. Sin texto del mensaje |
| Mensaje + intent + confianza (anonimizado SHA-256) | JSONL (`data/conversations/`) | Solo entrenamiento ML. No recuperable |
| Texto del mensaje | **No se persiste** | Expectativa del usuario: conversación efímera |
| Eventos > 7 días | Purga automática | Minimización de datos |

El teléfono en `conversation_events` no está anonimizado porque es necesario para el lookup. No se expone al exterior ni se cruza con datos clínicos.

---

## 🔑 Variables de entorno

```bash
# Controlan la ventana de respuesta a recordatorios
REMINDER_SEND_TIME=17:30    # hora de envío — también controla jobs APScheduler
REMINDER_CLOSE_TIME=20:30   # hora de cierre — after this: no reminder interception
```

Ambas se leen en `should_handle_as_reminder()` y en `context_service.had_reminder_sent()`.

---

## 🧪 Testing

```bash
# Ventana horaria — 5 escenarios (K-O)
docker exec -w /app whatsapp-demo python tests/reminders/test_reminder_window.py -v

# Respuestas al recordatorio — escenarios existentes (F-J)
docker exec -w /app whatsapp-demo python tests/reminders/test_reminder_responses.py -v
```

| Escenario | Qué valida |
|---|---|
| K | Confirmar (texto libre) dentro de la franja → interceptado |
| L | Confirmar fuera de la franja → flujo normal |
| M | Reprogramar dentro de la franja → interceptado |
| N | Reprogramar fuera de la franja → flujo normal |
| O | Cancelar dentro de la franja → interceptado |

### Verificar eventos en BD

```powershell
# Desde PowerShell (Windows)
'from src.database.database import db
with db.get_connection() as conn:
    rows = conn.execute("SELECT * FROM conversation_events ORDER BY created_at DESC LIMIT 10").fetchall()
    for r in rows: print(dict(r))' | Out-File -Encoding utf8 check_events.py

docker cp check_events.py whatsapp-demo:/app/check_events.py
docker exec -w /app whatsapp-demo python check_events.py
```

---

## 🔮 Pendiente

- **`state_after`** — registrar el estado de destino desde los handlers, no solo `state_before`
- **Purga como job diario** — integrar `event_store.purge_old_events()` en `engine.py`
- **`get_recent_context()` en bot_controller** — usar al inicio de sesión nueva para orientar routing sin depender de Redis
- **`flow_interrupted` event_type** — registrar explícitamente cuando un flujo activo expira sin completarse

---

**Versión:** 1.0
**Fecha:** Abril 2026
**Referencia:** `docs/ARCHITECTURE.md` v6.2
