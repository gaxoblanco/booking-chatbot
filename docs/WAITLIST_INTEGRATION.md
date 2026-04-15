# Waitlist Integration Service
## Adelantamiento Automático de Turnos
**Versión 1.0 — Abril 2026**

---

## Índice

1. [Propósito](#propósito)
2. [Ubicación en el proyecto](#ubicación-en-el-proyecto)
3. [Ciclo completo](#ciclo-completo)
4. [Componentes](#componentes)
5. [Flujo de datos](#flujo-de-datos)
6. [Cascada de ofertas](#cascada-de-ofertas)
7. [Expiración y job nocturno](#expiración-y-job-nocturno)
8. [Tablas de base de datos](#tablas-de-base-de-datos)
9. [Mensajes y tonos](#mensajes-y-tonos)
10. [Testing](#testing)

---

## Propósito

Cuando un turno se cancela o reprograma, este módulo busca automáticamente
clientes con turnos posteriores con el mismo profesional y les ofrece adelantar.

El objetivo es minimizar slots vacíos en la agenda del profesional y dar al
paciente la oportunidad de una fecha más cercana sin intervención manual.

---

## Ubicación en el proyecto

```
src/integrations/waitlist/
    __init__.py
    slot_offer_handler.py       # Intercepta respuestas de clientes a ofertas

src/services/
    waitlist_service.py         # Lógica de negocio completa
```

Archivos modificados como parte de esta integración:

```
src/bot/bot_controller.py           # intercepción before NLU + routing table
src/bot/client_handler.py           # handle_client_cancel_reason() dispara waitlist
src/bot/reminder_handler.py         # cancelación desde recordatorio dispara waitlist
src/core/states.py                  # agrega AWAITING_SLOT_OFFER
src/messages/tones/coloquial.py     # constantes SLOT_OFFER_*
src/messages/tones/demo.py          # constantes SLOT_OFFER_*
src/database/database.py            # migración índice parcial appointments
```

---

## Ciclo completo

```
Cliente cancela turno (desde menú o desde recordatorio)
    │
    ▼
handle_client_cancel_reason()  /  reminder_handler handle "0"
    │   cita cancelada en BD + Google Calendar
    │
    ▼  [threading.Thread — no bloquea respuesta al cliente]
waitlist_service.handle_slot_freed(freed_appointment_id)
    │
    ├── Obtiene datos del turno liberado
    │
    ├── _find_candidates()
    │       busca clientes con:
    │       - mismo profesional
    │       - turno en días POSTERIORES (próximos 30 días)
    │       - status = 'confirmada'
    │       - wants_earlier_slot = 1
    │       - sin oferta pending activa
    │       - sin 3+ rechazos en 30 días con este profesional (anti-spam)
    │       - no rechazó este slot específico antes (cascada)
    │       ordenados por fecha más cercana primero
    │
    ├── Sin candidatos → fin del ciclo
    │
    └── Con candidatos → _send_offer(primer candidato)
            │
            ├── _create_offer_record() → slot_offers INSERT (status='pending')
            ├── _format_offer_message() → usa tono activo (get_msg)
            │       incluye: turno disponible + turno actual + tiempo expiración
            └── message_sender.send_with_retry() → WhatsApp via Twilio


Cliente recibe la oferta y responde
    │
    ▼
bot_controller._process_message()
    │
    ├── should_handle_as_slot_offer()
    │       consulta slot_offers WHERE status='pending' AND expires_at > now
    │       fuerza estado → AWAITING_SLOT_OFFER si hay oferta activa
    │
    └── handle_slot_offer_response()
            │
            ├── "1" (acepta)
            │       _accept_offer()
            │           1. UPDATE appointments status='cancelada_cliente',
            │                  start='cancelled_<id>'  ← libera UNIQUE constraint
            │           2. UPDATE slot_offers status='accepted'
            │           3. UPDATE appointments date/start/end  ← mueve el turno
            │           4. AppointmentCalendarService.reschedule_appointment()
            │       → mensaje SLOT_OFFER_ACCEPTED (nuevo turno con fecha formateada)
            │       → sesión → CLIENT_MAIN_MENU
            │
            ├── "2" (rechaza)
            │       _reject_offer()
            │           1. UPDATE slot_offers status='rejected'
            │           2. _find_candidates() excluyendo quien rechazó
            │           3. Si hay siguiente → _send_offer(siguiente candidato)
            │       → mensaje SLOT_OFFER_REJECTED (datos turno original)
            │       → sesión → CLIENT_MAIN_MENU
            │
            ├── Oferta expirada (responde tarde)
            │       _mark_offer_expired()
            │       → mensaje SLOT_OFFER_EXPIRED (datos turno original)
            │       → sesión → CLIENT_MAIN_MENU
            │
            └── Texto libre no reconocido
                    → mensaje SLOT_OFFER_INVALID (repregunta + minutos restantes)
                    → estado permanece en AWAITING_SLOT_OFFER


17:33 — APScheduler dispara job_waitlist
    │
    ▼
WaitlistService.process_expired_offers()
    │   busca slot_offers WHERE status='pending' AND expires_at <= now
    │   por cada una:
    │       1. _mark_offer_expired()
    │       2. _find_candidates() excluyendo quien no respondió
    │       3. Si hay candidato → _send_offer(siguiente)
    │       4. Si no hay → slot queda libre, fin de cascada
```

---

## Componentes

### `WaitlistService`

Ubicación: `src/services/waitlist_service.py`

Contiene toda la lógica de negocio. Instancia global: `waitlist_service`.

| Método | Descripción |
|---|---|
| `handle_slot_freed(freed_appointment_id, reason)` | Punto de entrada cuando se libera un turno |
| `_find_candidates(...)` | Query con filtros anti-spam y exclusión de cascada |
| `_send_offer(freed_appointment_id, candidate, freed_apt)` | Crea registro + envía WhatsApp |
| `_format_offer_message(freed_apt, candidate)` | Formato via tono activo |
| `handle_offer_response(client_phone, response)` | Procesa "1" o "2" del cliente |
| `_accept_offer(offer)` | Mueve el turno en BD + Google Calendar |
| `_reject_offer(offer)` | Marca rechazada + continúa cascada |
| `process_expired_offers()` | Job diario — procesa ofertas sin respuesta |

---

### `slot_offer_handler`

Ubicación: `src/integrations/waitlist/slot_offer_handler.py`

Intercepta mensajes entrantes antes del NLU. Análogo en estructura a
`reminder_handler.py`.

| Función | Descripción |
|---|---|
| `should_handle_as_slot_offer(session, message)` | Devuelve `True` si hay oferta `status='pending'` para el número |
| `handle_slot_offer_response(session, message)` | Procesa la respuesta, actualiza BD y maneja sesión |

La conexión con el bot en `bot_controller.py`:

```python
# Prioridad 1: recordatorio
if should_handle_as_reminder(session, message):
    return handle_reminder_response(session, message)

# Prioridad 2: oferta waitlist
if should_handle_as_slot_offer(session, message):
    response = handle_slot_offer_response(session, message)
    if response is not None:
        return response
```

Entrada en el routing table:

```python
ConversationState.AWAITING_SLOT_OFFER: lambda s, m: handle_slot_offer_response(s, m),
```

---

## Flujo de datos

### Tablas escritas durante el ciclo

```
handle_slot_freed()
    slot_offers           → INSERT status='pending', expires_at=now+30min

_accept_offer()
    appointments          → UPDATE status='cancelada_cliente',
                                   start='cancelled_<id>'
                            (turno liberado — libera UNIQUE constraint)
    slot_offers           → UPDATE status='accepted'
    appointments          → UPDATE appointment_date, start, end, moved_from_offer_id
                            (turno del candidato — movido al slot liberado)

_reject_offer()
    slot_offers           → UPDATE status='rejected'
    slot_offers           → INSERT nuevo registro (siguiente candidato)

_mark_offer_expired()
    slot_offers           → UPDATE status='expired'
    slot_offers           → INSERT nuevo registro (siguiente candidato)
```

---

## Cascada de ofertas

Cuando un candidato rechaza o no responde, la oferta pasa al siguiente
candidato. Protecciones contra spam:

**Anti-spam (por profesional):**
Si un cliente rechazó 3+ veces en 30 días con el mismo profesional,
no aparece más como candidato en ese período. Si tiene turno con otro
profesional, sigue siendo candidato para ese.

**Exclusión de cascada:**
Todos los que ya rechazaron el slot específico en la ronda actual quedan
excluidos aunque no hayan llegado al límite anti-spam.
El parámetro `freed_apt_id` en `_find_candidates()` cubre este caso.

**Ejemplo:**

```
Slot liberado: Lunes 10:00 con Dr. García

Candidato 1 (turno Miércoles) → rechaza
    slot_offers #1 → rejected
    _find_candidates(exclude: candidato1, freed_apt_id: slot)

Candidato 2 (turno Jueves) → no responde en 30 min
    slot_offers #2 → expired (job_waitlist 17:33)
    _find_candidates(exclude: candidato2, freed_apt_id: slot)

Candidato 3 (turno Viernes) → acepta
    slot_offers #3 → accepted
    turno de candidato3 movido a Lunes 10:00
    fin de cascada
```

---

## Expiración y job nocturno

`job_waitlist` corre a las **17:33** via APScheduler.

Procesa todas las ofertas con `status='pending'` y `expires_at <= now`.
Por cada una continúa la cascada al siguiente candidato.

En `FLASK_ENV=development` el job está pausado. Para dispararlo manualmente:

```bash
docker exec -it whatsapp-demo python -c "
from src.services.waitlist_service import waitlist_service
result = waitlist_service.process_expired_offers()
print(result)
"
```

---

## Tablas de base de datos

### `slot_offers`

```sql
CREATE TABLE slot_offers (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    freed_appointment_id    INTEGER NOT NULL,
    offered_to_client_phone TEXT NOT NULL,
    original_appointment_id INTEGER NOT NULL,
    freed_date              DATE NOT NULL,
    freed_time              TEXT NOT NULL,
    professional_phone      TEXT NOT NULL,
    professional_name       TEXT,
    status TEXT CHECK(status IN ('pending','accepted','rejected','expired'))
           DEFAULT 'pending',
    offered_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at              TIMESTAMP NOT NULL,
    response_received_at    TIMESTAMP
)
```

Estados posibles de `slot_offers.status`:

```
pending   → enviada, esperando respuesta (TTL: 30 minutos)
accepted  → cliente aceptó, turno movido
rejected  → cliente rechazó, cascada al siguiente
expired   → no respondió en 30 min, cascada al siguiente
```

### Índice parcial en `appointments`

El UNIQUE constraint original sin filtro de status impedía mover un turno
al slot de uno cancelado. La migración en `_init_db()` lo reemplaza:

```sql
CREATE UNIQUE INDEX idx_appointments_slot_active
ON appointments(professional_phone, appointment_date, start)
WHERE status NOT IN ('cancelada_cliente', 'cancelada_profesional')
```

La migración corre automáticamente al arrancar y es idempotente —
detecta si `sqlite_autoindex_appointments_1` sigue presente antes de actuar.

---

## Mensajes y tonos

Constantes requeridas en `coloquial.py` y `demo.py`:

| Constante | Variables | Descripción |
|---|---|---|
| `SLOT_OFFER_MESSAGE` | `{prof_name}`, `{freed_date}`, `{freed_time}`, `{current_date}`, `{current_time}`, `{expiration_minutes}` | Oferta al candidato |
| `SLOT_OFFER_ACCEPTED` | `{prof_name}`, `{new_date}`, `{new_time}` | Turno adelantado exitosamente |
| `SLOT_OFFER_REJECTED` | `{prof_name}`, `{current_date}`, `{current_time}` | Turno original mantenido |
| `SLOT_OFFER_EXPIRED` | `{prof_name}`, `{current_date}`, `{current_time}` | Oferta ya no disponible |
| `SLOT_OFFER_INVALID` | `{minutes_left}` | Respuesta no reconocida — repregunta |

Todas las fechas se muestran en formato humano (`Lunes 20 de Abril de 2026`).
La conversión de `YYYY-MM-DD` → texto se hace en `slot_offer_handler._fmt_date()`.

---

## Testing

```bash
# Test E2E completo (acepta + rechaza)
docker exec -it whatsapp-demo python tests/waitlist/test_waitlist_e2e.py

# Solo aceptación
docker exec -it whatsapp-demo python tests/waitlist/test_waitlist_e2e.py --accept

# Solo rechazo
docker exec -it whatsapp-demo python tests/waitlist/test_waitlist_e2e.py --reject

# Setup manual — probar desde WhatsApp real
docker exec -it whatsapp-demo python tests/waitlist/test_waitlist_e2e.py --manual

# Limpiar datos de prueba sin correr tests
docker exec -it whatsapp-demo python tests/waitlist/test_waitlist_e2e.py --cleanup
```

El modo `--manual` inserta dos citas de prueba en BD e imprime instrucciones
paso a paso. Los números de prueba (`+5491199990001`, `+5491199990002`) deben
estar en el sandbox de Twilio para recibir el WhatsApp real.

---

## Documentos relacionados

- `docs/ARCHITECTURE.md` — arquitectura general del sistema
- `docs/REMINDER_INTEGRATION.md` — ciclo de recordatorios (patrón análogo)
- `docs/TONE_SYSTEM.md` — cómo agregar constantes a los tonos
