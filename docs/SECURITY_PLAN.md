# Plan de Seguridad — Bot de Turnos por WhatsApp
## Arquitectura y orden de implementación
*Versión: 1.0 — Marzo 2026*

---

## MODELO DE AMENAZAS

El sistema tiene tres superficies de ataque principales:

```
Internet
    │
    ├──→ /webhook                    ← cualquier usuario de WhatsApp
    ├──→ /google-calendar/webhook    ← supuestamente solo Google
    │
    └── Docker network
            ├── Redis :6379           ← supuestamente solo containers
            └── ml-service :8000      ← supuestamente solo whatsapp-demo
```

Un atacante externo puede llegar a los dos primeros endpoints.
Un atacante con acceso al servidor (o a la red Docker) llega a los últimos dos.

---

## INVENTARIO DE ISSUES

### 🔴 CRÍTICO — exploitable desde internet sin credenciales

| # | Issue | Superficie | Impacto |
|---|-------|-----------|---------|
| S1 | Sin validación de firma Twilio en `/webhook` | Externo | Cualquiera puede simular mensajes de cualquier número |
| S2 | Sin rate limiting en `/google-calendar/webhook` | Externo | Flood de notificaciones falsas satura el proceso |
| S3 | Sin límite de tamaño en descarga de archivos | Externo | Archivo de 100MB bloquea el hilo Flask |

### 🟡 IMPORTANTE — exploitable con acceso al servidor o red

| # | Issue | Superficie | Impacto |
|---|-------|-----------|---------|
| S4 | Redis sin contraseña y puerto expuesto al host | Red interna | Lectura/escritura de sesiones de todos los usuarios |
| S5 | `MASTER_ACCESS_KEY=ADMIN2025` hardcodeada | Código fuente | Si el repo es público, la clave queda expuesta |
| S6 | PII en logs sin sanitización | Logs del container | Teléfonos y nombres visibles en `docker logs` |

### 🟢 MEJORA — riesgo bajo, buena práctica

| # | Issue | Superficie | Impacto |
|---|-------|-----------|---------|
| S7 | Sin validación de dominio en URL de descarga | Externo | Redirección a servidor externo si Twilio es comprometido |
| S8 | CSV/Excel injection en archivos generados | Local | Fórmulas ejecutables si el profesional abre el CSV de rechazados |
| S9 | Channel token de Google en logs | Logs del container | Token visible si los logs se exportan |
| S10 | Session fixation posible si Redis es accesible | Red interna | Requiere acceso previo a Redis (combinado con S4) |

---

## PLAN DE IMPLEMENTACIÓN

### Fase 1 — CRÍTICOS (esta semana)

Los tres issues críticos son independientes entre sí. Se pueden implementar
en cualquier orden. Estimación: 1-2 horas total.

---

#### S1 — Validación de firma Twilio

**Archivo:** `src/api/whatsapp_handler.py`

**Por qué es crítico:** Sin esto, cualquier persona que conozca la URL del webhook
puede enviar mensajes simulando ser cualquier número de teléfono. Podría agendar
o cancelar turnos en nombre de otro usuario.

**Cómo funciona la firma:**
Twilio firma cada request con HMAC-SHA1 usando el `AUTH_TOKEN` y la URL completa
del webhook. El header `X-Twilio-Signature` contiene el resultado.

**Implementación:**

```python
# src/api/whatsapp_handler.py
# Agregar al inicio del archivo:
from twilio.request_validator import RequestValidator

def _validate_twilio_signature(request) -> bool:
    """
    Verifica que el request viene realmente de Twilio.
    Usa HMAC-SHA1 sobre la URL + parámetros del form.
    """
    auth_token = os.getenv('TWILIO_AUTH_TOKEN', '')
    if not auth_token:
        logger.error("[SECURITY] TWILIO_AUTH_TOKEN no configurado")
        return False

    validator  = RequestValidator(auth_token)
    signature  = request.headers.get('X-Twilio-Signature', '')
    url        = os.getenv('WEBHOOK_URL', '') + '/webhook'

    return validator.validate(url, request.form, signature)


# En el handler /webhook, agregar al principio:
@app.route('/webhook', methods=['POST'])
def webhook():
    # En producción, verificar firma de Twilio
    if os.getenv('ENVIRONMENT') == 'production':
        if not _validate_twilio_signature(request):
            logger.warning(
                f"[SECURITY] 🚨 Firma Twilio inválida desde "
                f"{request.remote_addr}"
            )
            return "Unauthorized", 403

    # ... resto del handler
```

**Variable de entorno necesaria:**
`WEBHOOK_URL` ya existe en `.env` — debe ser la URL pública completa
(ej: `https://psivale.com.ar`).

**Nota sobre desarrollo:**
En `development`, saltar la validación (Twilio no puede firmar requests locales
sin un dominio real). Usar la variable `ENVIRONMENT` que ya existe.

**Test:**
```bash
# Sin firma (debe dar 403 en producción):
curl -X POST https://psivale.com.ar/webhook \
  -d "Body=hola" -d "From=whatsapp:+5491112345678"

# Con firma válida (debe funcionar):
# Twilio lo hace automáticamente al enviar mensajes reales
```

---

#### S2 — Rate limiting en `/google-calendar/webhook`

**Archivo:** `src/api/whatsapp_handler.py`

**Por qué es crítico:** El endpoint es público. Un atacante puede hacer flood
de POST con `channel_id` válidos (que aparecen en los logs) y saturar el sistema
con syncs innecesarios.

**Implementación:**
El `rate_limiter` del Issue 3 ya existe en `src/core/rate_limiter.py`.
Solo hay que instanciar uno específico para este endpoint.

```python
# src/api/whatsapp_handler.py
# Agregar junto a las otras importaciones:
from src.core.rate_limiter import RateLimiter

# Limiter específico para Calendar webhook
# Más permisivo que el de WhatsApp — Google puede enviar ráfagas legítimas
_calendar_rate_limiter = RateLimiter(
    max_messages = 30,    # máx 30 notificaciones
    window_seconds = 60,  # por minuto
    block_minutes  = 5,   # bloqueo si supera
)

# En el handler /google-calendar/webhook:
@app.route('/google-calendar/webhook', methods=['POST'])
def google_calendar_webhook():
    # Rate limiting por IP
    client_ip = request.remote_addr or 'unknown'
    if not _calendar_rate_limiter.is_allowed(client_ip):
        logger.warning(
            f"[SECURITY] 🚨 Rate limit Calendar webhook: {client_ip}"
        )
        return "Too Many Requests", 429

    # ... resto del handler
```

---

#### S3 — Límite de tamaño en descarga de archivos

**Archivo:** `src/services/calendar_import_service.py`

**Por qué es crítico:** `_download()` no limita el tamaño. Un archivo de 100MB
bloquea el hilo de Flask durante la descarga (Flask es single-threaded por defecto).

**Implementación:**

```python
# En CalendarImportService._download():
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
TWILIO_MEDIA_DOMAIN = 'api.twilio.com'

def _download(self, file_url: str) -> Optional[bytes]:
    """
    Descarga el archivo con validaciones de seguridad:
    - Solo acepta URLs del dominio de Twilio
    - Límite de 5 MB
    - Timeout de 30 segundos
    """
    # Validar dominio — solo Twilio
    from urllib.parse import urlparse
    parsed = urlparse(file_url)
    if parsed.netloc != TWILIO_MEDIA_DOMAIN:
        logger.error(
            f"[SECURITY] 🚨 URL de descarga rechazada: {parsed.netloc} "
            f"(solo se acepta {TWILIO_MEDIA_DOMAIN})"
        )
        return None

    try:
        import requests
        resp = requests.get(
            file_url,
            auth    = (os.getenv('TWILIO_ACCOUNT_SID'),
                       os.getenv('TWILIO_AUTH_TOKEN')),
            timeout = 30,
            stream  = True,   # ← no descargar todo de golpe
        )

        if resp.status_code != 200:
            logger.error(f"[AGENDA-IMPORT] ❌ HTTP {resp.status_code}")
            return None

        # Verificar Content-Length si está disponible
        content_length = int(resp.headers.get('Content-Length', 0))
        if content_length > MAX_FILE_SIZE_BYTES:
            logger.warning(
                f"[SECURITY] ⚠️ Archivo muy grande: "
                f"{content_length / 1024 / 1024:.1f} MB > 5 MB límite"
            )
            return None

        # Descargar con límite de tamaño
        content = b''
        for chunk in resp.iter_content(chunk_size=8192):
            content += chunk
            if len(content) > MAX_FILE_SIZE_BYTES:
                logger.warning(
                    f"[SECURITY] ⚠️ Archivo superó 5 MB durante descarga "
                    f"— abortando"
                )
                return None

        logger.info(
            f"[AGENDA-IMPORT] ✅ Descargado "
            f"({len(content) / 1024:.1f} KB)"
        )
        return content

    except Exception as e:
        logger.error(f"[AGENDA-IMPORT] ❌ Error descargando: {e}")
        return None
```

---

### Fase 2 — IMPORTANTES (semana 2)

---

#### S4 — Redis con contraseña y sin puerto expuesto al host

**Archivos:** `docker/docker-compose.yml`, `docker/.env`

**Dos cambios independientes:**

**4a. Quitar el puerto expuesto al host:**
```yaml
# ANTES — Redis accesible desde fuera del servidor:
redis:
  ports:
    - "6379:6379"

# DESPUÉS — Solo accesible entre containers:
redis:
  expose:
    - "6379"
  # Sin 'ports' → no hay binding al host
```

**4b. Agregar contraseña:**
```yaml
# docker-compose.yml:
redis:
  command: >
    redis-server
    --maxmemory 256mb
    --maxmemory-policy allkeys-lru
    --requirepass ${REDIS_PASSWORD}
  expose:
    - "6379"
  networks:
    - whatsapp-demo-network
```

```bash
# docker/.env — agregar:
REDIS_PASSWORD=genera-una-password-larga-aqui
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
```

**Generar una password segura:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

#### S5 — Eliminar `MASTER_ACCESS_KEY` hardcodeada

**Archivo:** `src/config/config.py`

**El problema:** `MASTER_ACCESS_KEY = os.getenv('MASTER_ACCESS_KEY', 'ADMIN2025')`
tiene un valor por defecto hardcodeado. Si alguien olvida configurar la variable,
la clave 'ADMIN2025' funciona en producción.

**Fix:**
```python
# ANTES:
MASTER_ACCESS_KEY = os.getenv('MASTER_ACCESS_KEY', 'ADMIN2025')

# DESPUÉS:
MASTER_ACCESS_KEY = os.getenv('MASTER_ACCESS_KEY')
if not MASTER_ACCESS_KEY and os.getenv('ENVIRONMENT') == 'production':
    raise ValueError(
        "MASTER_ACCESS_KEY debe estar configurada en producción. "
        "No tiene valor por defecto para evitar accesos no autorizados."
    )
```

---

#### S6 — Sanitización de PII en logs

**Archivos:** `src/core/logger.py` (nuevo) + todos los módulos que usan `print()`

**El problema:** Hay cientos de `print()` que incluyen teléfonos, nombres y datos
de turnos. En producción esos logs son accesibles via `docker logs`.

**Estrategia:** Crear un wrapper de logging que sanitiza automáticamente.

```python
# src/core/logger.py (nuevo)
import re
import logging

# Patrón E.164: +549...
PHONE_PATTERN = re.compile(r'\+\d{7,15}')

def sanitize(text: str) -> str:
    """
    Reemplaza teléfonos con versión parcial para logs.
    +5491112345678 → +549****5678
    """
    def mask_phone(m):
        p = m.group(0)
        return p[:4] + '****' + p[-4:]
    return PHONE_PATTERN.sub(mask_phone, str(text))


class SanitizedLogger:
    """
    Logger que sanitiza PII antes de escribir.
    Wrappea el logger estándar de Python.
    """
    def __init__(self, name: str):
        self._log = logging.getLogger(name)

    def info(self, msg, *args, **kwargs):
        self._log.info(sanitize(msg), *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self._log.warning(sanitize(msg), *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self._log.error(sanitize(msg), *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        self._log.debug(sanitize(msg), *args, **kwargs)
```

**Migración gradual:** Reemplazar `logger = logging.getLogger(__name__)` por
`logger = SanitizedLogger(__name__)` en cada módulo. Empezar por los que
manejan más PII: `client_service.py`, `whatsapp_handler.py`, `session_backends.py`.

---

### Fase 3 — MEJORAS (semana 3+)

---

#### S7 — Validación de dominio en descarga

Ya incluido en la implementación de S3 (`TWILIO_MEDIA_DOMAIN = 'api.twilio.com'`).
No requiere trabajo adicional si S3 se implementó correctamente.

---

#### S8 — Sanitización de CSV/Excel injection

**Archivo:** `src/integrations/file_parser/file_parser.py`

**El riesgo:** Celdas que empiezan con `=`, `+`, `-`, `@` son fórmulas en Excel.
El bot no las ejecuta, pero si el profesional abre el CSV de rechazados generado
por el sistema, Excel las ejecuta.

```python
# En FileParser._parse_csv(), después de normalizar los valores:

FORMULA_PREFIXES = ('=', '+', '-', '@', '\t', '\r')

def _sanitize_cell(self, value: str) -> str:
    """
    Neutraliza posibles fórmulas CSV/Excel.
    Prefixea con apóstrofe para que Excel las trate como texto.
    """
    if value and value[0] in FORMULA_PREFIXES:
        return "'" + value  # El apóstrofe hace que Excel lo trate como texto
    return value
```

Aplicar en `_parse_csv()` al normalizar cada valor del row.

---

#### S9 — Channel token de Google fuera de logs normales

**Archivo:** `src/integrations/google_calendar_service/watch_manager.py`

El `channel_token` es el secreto que valida las notificaciones de Google.
Si aparece en logs normales, puede ser capturado por monitoreo de logs.

```python
# En WatchManager, reemplazar cualquier log que incluya el token:

# ANTES:
logger.info(f"Watch creado: channel_id={channel_id}, token={token}")

# DESPUÉS:
logger.info(
    f"Watch creado: channel_id={channel_id[:8]}..., "
    f"token=***[{len(token)} chars]"
)
```

---

#### S10 — Session fixation

Dependiente de S4. Si Redis tiene contraseña y no está expuesto al host,
este issue queda mitigado sin trabajo adicional.

Si se quiere protección adicional, al crear una sesión nueva se puede
incluir un HMAC de la sesión usando el `AUTH_TOKEN` de Twilio como llave.
Esto hace que las sesiones sean infalsificables incluso con acceso a Redis.

Esto es overkill para el escenario actual — dejar como backlog.

---

## CHECKLIST DE DEPLOY A PRODUCCIÓN

```
Fase 1 — Críticos:
  [ ] S1: _validate_twilio_signature() en /webhook
  [ ] S1: ENVIRONMENT=production en .env del servidor
  [ ] S2: _calendar_rate_limiter en /google-calendar/webhook
  [ ] S3: Límite 5MB + validación dominio en _download()

Fase 2 — Importantes:
  [ ] S4a: Redis expose: en lugar de ports: en docker-compose.yml
  [ ] S4b: REDIS_PASSWORD generada y en .env
  [ ] S4b: REDIS_URL actualizada con password
  [ ] S5: MASTER_ACCESS_KEY sin valor por defecto
  [ ] S6: SanitizedLogger en client_service.py y whatsapp_handler.py

Fase 3 — Mejoras:
  [ ] S8: _sanitize_cell() en FileParser
  [ ] S9: Channel token fuera de logs normales

Verificación post-deploy:
  [ ] POST a /webhook sin firma → 403
  [ ] POST a /webhook con firma Twilio válida → 200
  [ ] POST a /google-calendar/webhook 31 veces en 60s → 429
  [ ] Envío de archivo >5MB → mensaje de error
  [ ] docker logs | grep "+549" → teléfonos enmascarados
  [ ] redis-cli -a PASSWORD ping → PONG (con password)
  [ ] redis-cli ping (sin password) → error de autenticación
```

---

## ORDEN RECOMENDADO DE IMPLEMENTACIÓN

```
DÍA 1 (2-3 horas):
    S3 → más simple, no requiere cambios en infra
    S2 → reutiliza rate_limiter existente, 15 líneas
    S1 → requiere probar con Twilio real en staging primero

DÍA 2 (1-2 horas):
    S4a + S4b → docker-compose + .env, rebuild
    S5 → 5 líneas en config.py

DÍA 3 (2-3 horas):
    S6 → crear SanitizedLogger, migrar gradualmente

SEMANA SIGUIENTE:
    S8, S9 → mejoras, no urgentes
```

---

## TESTS DE SEGURIDAD A CREAR

```bash
tests/
    test_security_twilio_signature.py   # S1: firma válida/inválida
    test_security_calendar_ratelimit.py # S2: flood de requests
    test_security_file_download.py      # S3: tamaño + dominio
    test_security_pii_logs.py           # S6: teléfonos enmascarados
    test_security_csv_injection.py      # S8: fórmulas neutralizadas
```

Patrón de cada test: mismo esquema que los issues 1-9 ya existentes —
función por caso, runner al final, colores, cleanup.
