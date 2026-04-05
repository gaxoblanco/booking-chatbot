# Reminder Integration Service
## Integración de Recordatorios Automáticos
**Versión 1.0 — Abril 2026**

---

## Índice

1. [Propósito](#propósito)
2. [Ubicación en el proyecto](#ubicación-en-el-proyecto)
3. [Ciclo completo de un recordatorio](#ciclo-completo-de-un-recordatorio)
4. [Componentes](#componentes)
5. [Flujo de datos](#flujo-de-datos)
6. [Scheduler: cómo se disparan los jobs](#scheduler-cómo-se-disparan-los-jobs)
7. [Comando secreto del bot](#comando-secreto-del-bot)
8. [Relación con daily_reminder_job.py](#relación-con-daily_reminder_jobpy)
9. [Tablas de base de datos involucradas](#tablas-de-base-de-datos-involucradas)
10. [Testing](#testing)

---

## Propósito

Este módulo encapsula el ciclo completo de recordatorios de turnos como un
servicio de integración autónomo, desacoplado del flujo conversacional principal.

Antes de esta integración, las responsabilidades estaban dispersas:

- El envío lo disparaba el crontab del sistema operativo
- El auto-confirm era un job separado sin relación explícita con el envío
- Cuando un paciente cancelaba desde el recordatorio, la waitlist
  no se activaba automáticamente — requería intervención manual

El módulo resuelve los tres problemas y agrupa todo bajo una única
responsabilidad mantenible.

---

## Ubicación en el proyecto

```
src/integrations/reminder/
    __init__.py                        # exporta reminder_integration_service
    reminder_integration_service.py    # orquestador del ciclo
```

Archivos modificados como parte de esta integración:

```
src/bot/reminder_handler.py            # conecta cancelación → waitlist
src/bot/bot_controller.py              # comando secreto usa el nuevo servicio
src/integrations/scheduler/engine.py   # job_reminders y job_auto_confirm
                                       # delegan al integration service
src/services/professional_service.py   # agrega get_active_professionals_with_calendar()
```

---

## Ciclo completo de un recordatorio

```
17:30 — APScheduler dispara job_reminders
    │
    ▼
ReminderIntegrationService.run_send_cycle()
    │
    ▼
reminder_service.send_daily_reminders()
    │   busca citas confirmadas para mañana
    │   envía WhatsApp via Twilio template
    │   marca reminder_sent = 1 en appointments
    │   inserta registro en appointment_reminders (status='sent')
    │
    ▼
Paciente recibe el mensaje y responde 1 / 2 / 0
    │
    ▼
bot_controller.py — intercepta el mensaje entrante
    │
    ▼
reminder_handler.should_handle_as_reminder()
    │   detecta: mensaje es 1/2/0 + hay reminder status='sent' en BD
    │
    ▼
reminder_handler.handle_reminder_response()
    │
    ├── "1" → confirmar
    │       reminder_service._confirm_appointment()
    │       appointment_reminders.status = 'confirmed'
    │       appointments.confirmed_by_client = 1
    │       sesión → CLIENT_MAIN_MENU
    │
    ├── "2" → reprogramar
    │       appointment_reminders.status = 'rescheduled'
    │       sesión → CLIENT_RESCHEDULE_APPOINTMENT
    │       │
    │       ▼  (hilo separado)
    │       _trigger_waitlist(appointment_id, reason="rescheduled")
    │           └── waitlist_service.handle_slot_freed()
    │
    └── "0" → cancelar
            appointment_reminders.status = 'cancelled'
            sesión → CLIENT_CANCEL_APPOINTMENT
            │
            ▼
        waitlist_service.handle_slot_freed()
            │   busca candidatos con wants_earlier_slot = 1
            │   ofrece el slot al primero de la lista
            └── slot_offers ← registro de la oferta


20:30 — APScheduler dispara job_auto_confirm (+3 horas)
    │
    ▼
ReminderIntegrationService.run_confirm_cycle()
    │
    ▼
reminder_service.auto_confirm_unanswered(timeout_hours=3)
    │   busca reminders con status='sent' enviados hace >3h
    │   llama _confirm_appointment() por cada uno
    └── sin enviar WhatsApp adicional (evita spam)
```

---

## Componentes

### `ReminderIntegrationService`

Ubicación: `src/integrations/reminder/reminder_integration_service.py`

Orquesta el ciclo. No contiene lógica de negocio propia — delega a los
servicios existentes y centraliza el punto de entrada para el scheduler
y el comando del bot.

| Método | Llamado por | Descripción |
|---|---|---|
| `run_send_cycle()` | `engine.job_reminders` | Envío de recordatorios diarios |
| `run_confirm_cycle()` | `engine.job_auto_confirm` | Auto-confirm sin respuesta |
| `trigger_now()` | `bot_controller` comando secreto | Disparo manual con mensaje formateado |

---

### `reminder_handler`

Ubicación: `src/bot/reminder_handler.py`

Intercepta mensajes entrantes del flujo conversacional y detecta si
corresponden a una respuesta a un recordatorio pendiente.

| Función | Descripción |
|---|---|
| `should_handle_as_reminder(session, message)` | Devuelve `True` si hay reminder `status='sent'` para el número y el mensaje es 1, 2 o 0 |
| `handle_reminder_response(session, message)` | Procesa la respuesta, actualiza BD, maneja la sesión y dispara waitlist si cancela |
| `_trigger_waitlist(appointment_id)` | Función interna — corre en `threading.Thread` para no bloquear la respuesta a Twilio |

La conexión con el bot se hace en `bot_controller.py`, antes del routing normal:

```python
if should_handle_as_reminder(session, message):
    return handle_reminder_response(session, message)
```

---

### `engine.py` — jobs del scheduler

Los jobs `job_reminders` y `job_auto_confirm` en el scheduler ya no contienen
lógica — solo importan y llaman al integration service:

```python
def job_reminders() -> Dict:
    from src.integrations.reminder import reminder_integration_service
    return reminder_integration_service.run_send_cycle()

def job_auto_confirm() -> Dict:
    from src.integrations.reminder import reminder_integration_service
    return reminder_integration_service.run_confirm_cycle()
```

---

### `professional_service.get_active_professionals_with_calendar()`

Método agregado a `ProfessionalService` para uso del job de calendar sync.
Retorna profesionales con `is_active = 1` y `calendar_id` configurado.

---

## Flujo de datos

### Tablas escritas durante el ciclo

```
send_daily_reminders()
    appointments          → reminder_sent = 1
    appointment_reminders → INSERT status='sent'

handle_reminder_response() — "1"
    appointment_reminders → status='confirmed', confirmed_at
    appointments          → confirmed_by_client = 1, confirmed_by_client_at

handle_reminder_response() — "2"
    appointment_reminders → status='rescheduled', response_received_at

handle_reminder_response() — "0"
    appointment_reminders → status='cancelled', response_received_at
    slot_offers           → INSERT (via waitlist_service.handle_slot_freed)

auto_confirm_unanswered()
    appointment_reminders → status='confirmed', confirmed_at
    appointments          → confirmed_by_client = 1, confirmed_by_client_at
```

---

## Scheduler: cómo se disparan los jobs

El sistema usa APScheduler corriendo dentro del proceso Flask —
no hay crontab del sistema operativo activo.

El scheduler se inicia una sola vez al arrancar la app:

```python
# whatsapp_handler.py
from src.integrations.scheduler.engine import scheduler_engine
scheduler_engine.start()
atexit.register(scheduler_engine.stop)
```

Configuración relevante del scheduler en `engine.py`:

```
job_reminders    → cron, hora = REMINDER_TIME (default 17:30)
job_auto_confirm → cron, hora = REMINDER_TIME + 3h
```

La variable de entorno `REMINDER_TIME` controla el horario base:

```bash
REMINDER_TIME=17:30   # default — HH:MM
```

En `FLASK_ENV=development` los jobs se registran pero no se disparan
automáticamente. Solo corren via `trigger_job()` manual o el comando
secreto del bot.

---

## Comando secreto del bot

Solo disponible en `FLASK_ENV != production`.

| Comando | Acción |
|---|---|
| `enviar recordatorio` / `enviar recordatorios` | Llama `reminder_integration_service.trigger_now()` |
| `scheduler status` / `estado scheduler` | Muestra estado y próxima ejecución de cada job |

Ejemplo de respuesta al comando de envío:

```
✅ Recordatorios enviados: 8/10.
⚠️ Errores: 1.
```

```
📭 No hay citas para mañana.
```

---

## Relación con `daily_reminder_job.py`

`src/cron/daily_reminder_job.py` es el pipeline CLI original. Sigue existiendo
pero ya no es el mecanismo de producción.

| | `daily_reminder_job.py` | `ReminderIntegrationService` |
|---|---|---|
| Disparador | crontab del OS (desactivado) | APScheduler dentro de Flask |
| Uso actual | testing manual, emergencias | producción |
| Cómo ejecutar | `docker exec whatsapp-demo python -m src.cron.daily_reminder_job` | automático |
| Cubre waitlist | no | sí (via `reminder_handler`) |

Para correr el pipeline completo manualmente en casos de emergencia:

```bash
docker exec whatsapp-demo python -m src.cron.daily_reminder_job
```

---

## Tablas de base de datos involucradas

| Tabla | Rol |
|---|---|
| `appointments` | fuente de citas a recordar; campos `reminder_sent`, `confirmed_by_client` |
| `appointment_reminders` | registro de cada recordatorio enviado y su estado |
| `slot_offers` | ofertas generadas por waitlist cuando se cancela desde un recordatorio |
| `message_retry_queue` | reintentos de envío fallidos (gestionados por `message_sender`) |

Estados posibles de `appointment_reminders.status`:

```
sent        → recordatorio enviado, esperando respuesta
confirmed   → paciente confirmó (1) o auto-confirmado por timeout
rescheduled → paciente quiere reprogramar (2)
cancelled   → paciente canceló (0)
```

---

## Testing

Tests de integración existentes para este flujo:

```bash
# Respuestas al recordatorio (escenarios F, G, H, I, J)
docker exec -it whatsapp-demo python tests/reminders/test_reminder_responses.py

# Flujo E2E: recordatorio → cancelación → waitlist
docker exec -it whatsapp-demo python tests/features/test_e2e_reminder_flow.py
```

Para probar el envío manualmente sin esperar el horario del scheduler:

```
# Desde WhatsApp con el número de admin:
enviar recordatorios
```

---

## Documentos relacionados

- `docs/ARCHITECTURE.md` — arquitectura general del sistema
- `docs/SECURITY.md` — rate limiting y validaciones de seguridad
