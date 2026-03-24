# Seguridad
## Bot de Gestión de Turnos por WhatsApp
*Versión 1.0 — Marzo 2026*

---

## Modelo de amenazas

Tres superficies de ataque:

```
Internet
    ├── /webhook                     ← cualquier usuario de WhatsApp
    └── /google-calendar/webhook     ← supuestamente solo Google

Red Docker
    ├── Redis :6379                  ← supuestamente solo containers
    └── ml-service :8000             ← supuestamente solo whatsapp-demo
```

Un atacante externo puede llegar directamente a los dos primeros endpoints.
Un atacante con acceso al servidor o a la red Docker puede llegar a los últimos dos.

---

## Implementado — Core (Issues 1–9)

Protecciones de lógica de negocio. Todos tienen tests pasando en `tests/test_issue*.py`.

| # | Protección | Archivo | Descripción |
|---|-----------|---------|-------------|
| 1 | Límite de turnos por par | `database.py` | Máx 2 turnos activos por cliente+profesional |
| 2 | Límite global de turnos | `database.py` | Máx 5 turnos activos por número de teléfono |
| 3 | Rate limiting webhook | `core/rate_limiter.py` | Ventana deslizante, 10 msg/min, bloqueo 5 min |
| 4 | Limpieza de ofertas waitlist | `waitlist_service.py` | Ofertas expiradas limpiadas + reintento en cascada |
| 5 | Aislamiento de datos | `client_service.py` | El cliente solo ve sus propios turnos |
| 6 | Validación E.164 | `core/validators.py` | Todos los teléfonos entrantes validados |
| 7 | Notificación de cancelación | `cancellation_notifier.py` | Paciente notificado cuando el profesional cancela |
| 8 | Ownership del paciente | `database.py` | `patient_phone` guardado — el paciente puede cancelar su propio turno |
| 9 | Anti-spam de booking | `core/booking_limiter.py` | Máx 5 intentos de confirmación por hora |

---

## Implementado — Fase 1 (Endpoints externos)

Tests: `tests/test_security_phase1.py` — 17/17 pasando.

### S1 — Validación de firma Twilio

**Archivos:** `src/security/twilio_validator.py` + `src/api/whatsapp_handler.py`

**Problema:** Sin esta validación, cualquiera que conozca la URL del webhook puede
enviar mensajes haciéndose pasar por cualquier número — agendando o cancelando
turnos en nombre de usuarios reales.

**Solución:** Validación HMAC-SHA1 usando el header `X-Twilio-Signature` antes de
procesar cualquier mensaje. Solo activa con `ENVIRONMENT=production`.

```python
# whatsapp_handler.py — primer check en /webhook
if os.getenv('ENVIRONMENT') == 'production':
    if not validate_twilio_signature(request):
        return '', 403
```

**Clave:** Usa `TWILIO_AUTH_TOKEN` + `WEBHOOK_URL` del `.env`. Ambos deben coincidir
exactamente con lo que Twilio tiene configurado.

---

### S2 — Rate limiting en `/google-calendar/webhook`

**Archivo:** `src/api/whatsapp_handler.py` (`_CalendarRateLimiter`)

**Problema:** El endpoint es público. Un atacante que descubra un `channel_id` válido
puede inundarlo con notificaciones falsas, disparando syncs innecesarios con
Google Calendar.

**Solución:** Instancia dedicada `_CalendarRateLimiter` — 30 requests/minuto por IP,
bloqueo de 5 minutos. Más permisivo que el limiter de WhatsApp porque Google puede
enviar ráfagas legítimas.

```python
_calendar_rate_limiter = _CalendarRateLimiter()  # 30/min, bloqueo 5 min

# Primer check en google_calendar_webhook()
if _calendar_rate_limiter.is_blocked(client_ip):
    return '', 429
```

---

### S3 — Descarga segura de archivos

**Archivo:** `src/services/calendar_import_service.py` (`_download()`)

**Problema:** El `_download()` original no tenía límite de tamaño — un archivo de
100MB bloquearía el hilo de Flask. Tampoco validaba el dominio de la URL.

**Solución:** Tres validaciones antes de descargar:
1. El dominio de la URL debe ser `api.twilio.com` (solo HTTPS)
2. El header `Content-Length` se valida contra el límite de 5 MB
3. La descarga en streaming se corta si el contenido supera 5 MB a mitad de bajada

```python
MAX_FILE_SIZE_BYTES  = 5 * 1024 * 1024
ALLOWED_MEDIA_DOMAIN = 'api.twilio.com'
```

---

## Implementado — Fase 2 (Infraestructura)

Tests: `tests/test_security_phase2.py` — 15/15 pasando.

### S4 — Hardening de Redis

**Archivo:** `docker/docker-compose.yml`

**Problema:** Redis tenía `ports: 6379:6379` — expuesto al host. Cualquiera que
pudiera llegar al puerto del servidor podía leer o escribir todas las sesiones
de usuarios.

**Solución:**
- Cambiado `ports:` por `expose:` — Redis solo accesible dentro de la red Docker
- Agregado `--requirepass ${REDIS_PASSWORD}` — autenticación requerida

```yaml
redis:
  expose:
    - "6379"
  command: >
    redis-server
    --maxmemory 256mb
    --maxmemory-policy allkeys-lru
    --requirepass ${REDIS_PASSWORD}
```

**Requerido en `.env`:**
```
REDIS_PASSWORD=<generar con: python -c "import secrets; print(secrets.token_urlsafe(32))">
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
```

---

### S5 — Sin MASTER_ACCESS_KEY hardcodeada

**Archivo:** `src/config/config.py`

**Problema:** `MASTER_ACCESS_KEY = os.getenv('MASTER_ACCESS_KEY', 'ADMIN2025')`
— si alguien olvidaba configurar la variable, `ADMIN2025` funcionaba en producción.

**Solución:** Sin valor por defecto. Levanta `ValueError` al arrancar en producción
si no está configurada.

```python
MASTER_ACCESS_KEY = os.getenv('MASTER_ACCESS_KEY')
if not MASTER_ACCESS_KEY and os.getenv('ENVIRONMENT') == 'production':
    raise ValueError("[CONFIG] MASTER_ACCESS_KEY no configurada en producción.")
```

**También eliminado:** El dict `PROFESSIONAL_ACCESS_KEYS` con claves hardcodeadas
(`PSICO2025`, `DEMO12345`) — remanente de un flujo de auto-registro que nunca se
usó. Los profesionales se cargan via CSV por el administrador.

---

### S6 — Sanitización de PII en logs

**Archivo:** `src/core/logger.py` (nuevo)

**Problema:** Cientos de `print()` y llamadas a `logger` exponían números de
teléfono completos en los logs del container (`docker logs`).

**Solución:** `SanitizedLogger` envuelve el logger estándar y enmascara teléfonos
antes de escribir. Es un reemplazo directo de `logging.getLogger()`.

```python
# Antes:
logger = logging.getLogger(__name__)

# Después:
from src.core.logger import get_logger
logger = get_logger(__name__)

# +5491112345678  →  +549****5678
# 5491112345678   →  549****5678
```

**Migración:** Reemplazar `logging.getLogger(__name__)` gradualmente en los módulos
que manejan PII. Prioridad: `client_service.py`, `whatsapp_handler.py`,
`session_backends.py`.

---

## Implementado — Fase 3 (Contenido y secretos)

Tests: `tests/test_security_phase3.py` — 10/10 pasando.

### S8 — Inyección de fórmulas CSV/Excel

**Archivo:** `src/integrations/file_parser/file_parser.py` (`_sanitize_cell()`)

**Problema:** Excel ejecuta celdas que empiezan con `=`, `+`, `-`, `@` como fórmulas
al abrir el archivo. Si el sistema genera un `rechazados.csv` y el profesional lo
abre, fórmulas maliciosas podrían ejecutarse.

**Solución:** `_sanitize_cell()` prefixea celdas con fórmulas con un apóstrofe,
haciendo que Excel las trate como texto plano. Omite la columna `phone` donde
el `+` es parte del formato E.164.

```python
_FORMULA_PREFIXES = ('=', '+', '-', '@')

def _sanitize_cell(self, value: str, column: str = '') -> str:
    if not value or column == 'phone':
        return value
    if value[0] in self._FORMULA_PREFIXES:
        return "'" + value
    return value
```

---

### S9 — Channel token fuera de logs

**Archivo:** `src/integrations/google_calendar_service/watch_manager.py`

**Problema:** El `channel_token` es el secreto que valida las notificaciones push de
Google Calendar. Si apareciera en logs, podría ser capturado por sistemas de
agregación de logs.

**Verificado:** `watch_manager.py` solo loggea `channel_id[:8]...` — el token nunca
se escribe en ningún log. Se agregó un test de análisis estático para prevenir
regresiones.

---

## Pendiente

Todavía no implementado. Ver `SECURITY_PLAN.md` para el análisis completo.

| # | Issue | Prioridad | Notas |
|---|-------|-----------|-------|
| S10 | Session fixation | Baja | Mitigado por S4 (auth Redis). Fix completo: HMAC en las keys de sesión. |
| — | Firma Twilio en staging | Media | S1 solo está activo en production. Agregar entorno staging con firmas reales para testing pre-prod. |
| — | Rotación de REDIS_PASSWORD | Baja | Documentar procedimiento para rotar sin downtime. |
| — | Log de auditoría | Baja | Sin registro de acciones del admin (qué CSV cargó, cuándo). |

---

## Checklist pre-deploy a producción

```
[ ] ENVIRONMENT=production en el .env del servidor
[ ] TWILIO_AUTH_TOKEN configurado (requerido para validación de firma S1)
[ ] WEBHOOK_URL coincide exactamente con lo configurado en Twilio
[ ] MASTER_ACCESS_KEY configurada (el sistema no arranca sin ella)
[ ] REDIS_PASSWORD configurada + REDIS_URL incluye la contraseña
[ ] docker-compose.yml tiene expose: en lugar de ports: para redis
[ ] Test: POST /webhook sin firma → 403
[ ] Test: POST /webhook con firma Twilio válida → 200
[ ] Test: 31 POST a /google-calendar/webhook en 60s → 429
[ ] Test: subir archivo >5MB → mensaje de error
[ ] Test: docker logs | grep "+549" → teléfonos enmascarados
```

---

## Ejecutar todos los tests de seguridad

```bash
# Core (Issues 1-9)
docker exec -it whatsapp-demo python tests/test_booking_limits.py
docker exec -it whatsapp-demo python tests/test_global_booking_limit.py
docker exec -it whatsapp-demo python tests/test_rate_limiter.py
docker exec -it whatsapp-demo python tests/test_expired_offers.py
docker exec -it whatsapp-demo python tests/test_data_isolation.py
docker exec -it whatsapp-demo python tests/test_phone_validation.py
docker exec -it whatsapp-demo python tests/test_cancellation_notifier.py
docker exec -it whatsapp-demo python tests/test_patient_phone.py
docker exec -it whatsapp-demo python tests/test_booking_spam.py

# Fases 1-3
docker exec -it whatsapp-demo python tests/test_security_phase1.py
docker exec -it whatsapp-demo python tests/test_security_phase2.py
docker exec -it whatsapp-demo python tests/test_security_phase3.py
```

---

## Documentos relacionados

- `docs/ARCHITECTURE.md` — resumen del sistema con tabla de seguridad por fases
- `docs/SECURITY_PLAN.md` — análisis de amenazas original y plan de implementación
- `docker/.env.example` — todas las variables de entorno documentadas