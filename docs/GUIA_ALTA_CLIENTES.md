# Guía de Alta de Clientes
## WhatsApp Booking Bot — Setup por tipo de instalación
**Versión 1.0 — Junio 2026**

---

## Tipos de instalación

| Tipo | Variables clave | Caso de uso |
|---|---|---|
| **Demo** | `DOMAIN_PRESET=DEMO` + `TENANT_TONE=demo` | Demostración del producto |
| **Centro multi-profesional** | `DOMAIN_PRESET=SALUD` + `TENANT_TONE=coloquial` | Clínica, consultorio con N profesionales |
| **Freelance / profesional único** | `SINGLE_PROFESSIONAL_MODE=true` + `TENANT_TONE=freelance` | Psicólogo, médico, consultor independiente |

---

## Prerequisitos comunes

Antes de cualquier tipo de instalación, estas cosas deben estar listas:

### 1. Google Cloud — Service Account

Seguir `src/integrations/google_calendar_service/SETUP_GUIDE.md` (ya existe en el proyecto). Resultado: `config/google/service-account.json` en su lugar.

### 2. Meta (WhatsApp Business API)

En [developers.facebook.com](https://developers.facebook.com):

1. Crear una App → tipo **Business**
2. Agregar producto **WhatsApp**
3. En **API Setup** copiar:
   - `META_PHONE_NUMBER_ID`
   - `META_WHATSAPP_TOKEN`
   - `META_APP_SECRET`
4. En **Webhooks** → configurar después de levantar el bot con ngrok o dominio real

### 3. Redis

```bash
# Generar password de Redis
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Guardar el valor — se usa en `REDIS_PASSWORD` y `REDIS_URL`.

---

## TIPO 1 — Demo

Para mostrar el producto a un cliente potencial. Usa datos ficticios y profesionales de prueba.

### `.env` mínimo

```dotenv
ENVIRONMENT=development
FLASK_ENV=development

# Dominio
DOMAIN_PRESET=DEMO
TENANT_TONE=demo

# Meta WhatsApp
META_PHONE_NUMBER_ID=XXXXXXX
META_WHATSAPP_TOKEN=XXXXXXX
META_APP_SECRET=XXXXXXX
META_WEBHOOK_VERIFY_TOKEN=XXXXXXX
WEBHOOK_URL=https://TU-NGROK.ngrok-free.app

# Redis
REDIS_PASSWORD=XXXXXXX
REDIS_URL=redis://:XXXXXXX@redis:6379/0

# Meet (opcional para demo)
MEET_LINK_MODE=never

# Clave admin
MASTER_ACCESS_KEY=DEMO2026
ALLOW_KEY_REUSE=true
```

### Pasos

```bash
# 1. Levantar
docker compose -f docker/docker-compose.yml up --build -d

# 2. Cargar profesionales de demo
docker exec whatsapp-demo python scripts/csv/load_professionals_from_csv.py \
  //app/data/csv_src/profesionales_demo.csv

# 3. Verificar
docker compose -f docker/docker-compose.yml logs -f whatsapp-demo
# Esperado: [CONFIG] ✅ Configuración válida
```

### Verificación

```bash
curl http://localhost:5001/
# Respuesta: {"status":"running",...}
```

---

## TIPO 2 — Centro multi-profesional

Para clínicas, consultorios o centros con varios profesionales, cada uno con su propio Google Calendar.

### `.env` completo

```dotenv
ENVIRONMENT=production
FLASK_ENV=production

# Dominio — elegir según el rubro del centro
# Opciones: SALUD | PSICOLOGIA | BELLEZA | LEGAL | FITNESS | EDUCACION | HOGAR
DOMAIN_PRESET=SALUD
TENANT_TONE=coloquial

# Meta WhatsApp
META_PHONE_NUMBER_ID=XXXXXXX
META_WHATSAPP_TOKEN=XXXXXXX
META_APP_SECRET=XXXXXXX
META_WEBHOOK_VERIFY_TOKEN=XXXXXXX
WEBHOOK_URL=https://tu-dominio.com

# Google Calendar
GOOGLE_CALENDAR_WEBHOOK_URL=https://tu-dominio.com/google-calendar/webhook

# Google OAuth2 — para Meet links
GOOGLE_OAUTH_CLIENT_ID=XXXXXXX
GOOGLE_OAUTH_CLIENT_SECRET=XXXXXXX
GOOGLE_OAUTH_REDIRECT_URI=https://tu-dominio.com/oauth/callback

# Meet links
# never  → sin Meet (centro 100% presencial)
# always → siempre Meet (centro 100% virtual)
# auto   → Meet solo si el cliente eligió modalidad virtual
MEET_LINK_MODE=auto

# OAuth setup — para autorizar Meet por profesional
# Generar con: python -c "import secrets; print(secrets.token_urlsafe(32))"
OAUTH_SETUP_KEY=XXXXXXX

# Redis
REDIS_PASSWORD=XXXXXXX
REDIS_URL=redis://:XXXXXXX@redis:6379/0

# Seguridad
MASTER_ACCESS_KEY=XXXXXXX
ALLOW_KEY_REUSE=false

# ML
ML_SERVICE_URL=http://ml-intent-service:8000
ML_API_KEY=XXXXXXX
```

### Pasos

#### Paso 1 — Preparar el CSV de profesionales

Crear `data/csv_src/profesionales.csv` con el formato:

```csv
phone,name,email,calendar_email,zone,gender,accept_prepaga,category,slot_duration,horario
+5491112345678,Dra. Ana López,ana@clinica.com,ana.lopez@gmail.com,norte,f,1,Psicóloga,50,lunes:09:00-17:00|miercoles:09:00-17:00|viernes:09:00-13:00
+5491187654321,Lic. Carlos Ruiz,carlos@clinica.com,carlos.ruiz@gmail.com,sur,m,0,Psicólogo,50,martes:10:00-18:00|jueves:10:00-18:00
```

Campos requeridos:

| Campo | Descripción | Ejemplo |
|---|---|---|
| `phone` | Teléfono del profesional (E.164) | `+5491112345678` |
| `name` | Nombre completo | `Dra. Ana López` |
| `email` | Email del profesional | `ana@clinica.com` |
| `calendar_email` | Gmail que usa en Google Calendar | `ana.lopez@gmail.com` |
| `zone` | Zona geográfica (si aplica) | `norte` / `sur` |
| `gender` | Género | `m` / `f` |
| `accept_prepaga` | Acepta prepaga | `1` / `0` |
| `category` | Especialidad | `Psicóloga` |
| `slot_duration` | Duración del turno en minutos | `50` |
| `horario` | Horario de atención por día | `lunes:09:00-17:00\|martes:09:00-17:00` |

#### Paso 2 — Cada profesional comparte su Google Calendar con la Service Account

El email de la Service Account aparece en `config/google/service-account.json` (campo `client_email`). Cada profesional debe:

1. Abrir [Google Calendar](https://calendar.google.com)
2. Engranaje → **Configuración** → su calendario → **Compartir con personas específicas**
3. Agregar el email de la Service Account con permiso **Realizar cambios en eventos**

#### Paso 3 — Levantar y cargar profesionales

```bash
# Levantar
docker compose -f docker/docker-compose.yml up --build -d

# Cargar profesionales (Windows Git Bash)
docker exec whatsapp-demo python scripts/csv/load_professionals_from_csv.py \
  //app/data/csv_src/profesionales.csv

# Cargar profesionales (Linux/Mac)
docker exec whatsapp-demo python scripts/csv/load_professionals_from_csv.py \
  /app/data/csv_src/profesionales.csv
```

El script valida el acceso a cada Google Calendar. Si alguno no tiene acceso aún, queda pendiente y envía un email con instrucciones al profesional (requiere SMTP configurado).

#### Paso 4 — Validar calendarios pendientes (si los hay)

Después de que cada profesional comparta su calendario:

```bash
docker exec whatsapp-demo python scripts/csv/validate_pending_calendars.py
```

#### Paso 5 — Autorizar Meet links por profesional (si `MEET_LINK_MODE=always` o `auto`)

Para cada profesional que ofrece sesiones virtuales:

```bash
python scripts/setup_oauth_meet.py --phone +5491112345678
```

El script abre el browser, el profesional autoriza en Google, y el token queda guardado en BD automáticamente.

#### Paso 6 — Configurar webhook de Google Calendar (opcional pero recomendado)

Para recibir notificaciones cuando un profesional cancela un turno directamente desde Calendar:

```bash
docker exec whatsapp-demo python scripts/setup_calendar_watches.py
```

#### Paso 7 — Verificación final

```bash
docker exec whatsapp-demo python tests/smoke/test_smoke_production.py
```

---

## TIPO 3 — Freelance / Profesional único

Para un profesional independiente que opera solo. El bot conoce al profesional por su número de teléfono sin que el cliente tenga que buscarlo.

### `.env` completo

```dotenv
ENVIRONMENT=production
FLASK_ENV=production

# Dominio
DOMAIN_PRESET=SALUD
TENANT_TONE=freelance

# Modo profesional único — el bot no muestra menú de búsqueda
SINGLE_PROFESSIONAL_MODE=true
SINGLE_PROFESSIONAL_PHONE=+5491112345678   # teléfono del profesional

# Meta WhatsApp
META_PHONE_NUMBER_ID=XXXXXXX
META_WHATSAPP_TOKEN=XXXXXXX
META_APP_SECRET=XXXXXXX
META_WEBHOOK_VERIFY_TOKEN=XXXXXXX
WEBHOOK_URL=https://tu-dominio.com

# Google Calendar
GOOGLE_CALENDAR_WEBHOOK_URL=https://tu-dominio.com/google-calendar/webhook

# Google OAuth2 — para Meet links
GOOGLE_OAUTH_CLIENT_ID=XXXXXXX
GOOGLE_OAUTH_CLIENT_SECRET=XXXXXXX
GOOGLE_OAUTH_REDIRECT_URI=https://tu-dominio.com/oauth/callback

# Meet links
# always → siempre genera Meet (consultor remoto)
# never  → sin Meet (atención presencial únicamente)
# auto   → Meet solo si el cliente elige virtual
MEET_LINK_MODE=always

# OAuth setup
OAUTH_SETUP_KEY=XXXXXXX

# Redis
REDIS_PASSWORD=XXXXXXX
REDIS_URL=redis://:XXXXXXX@redis:6379/0

# Seguridad
MASTER_ACCESS_KEY=XXXXXXX
ALLOW_KEY_REUSE=false

# ML
ML_SERVICE_URL=http://ml-intent-service:8000
ML_API_KEY=XXXXXXX
```

### Pasos

#### Paso 1 — Crear el profesional en BD

Crear `data/csv_src/profesional.csv` con una sola fila:

```csv
phone,name,email,calendar_email,zone,gender,accept_prepaga,category,slot_duration,horario
+5491112345678,Dr. Gastón Blanco,gaston@mail.com,gaston.blanco@gmail.com,,m,0,Psicólogo,50,lunes:09:00-18:00|martes:09:00-18:00|miercoles:09:00-18:00|jueves:09:00-18:00|viernes:09:00-14:00
```

> En modo freelance el campo `zone` puede quedar vacío — no se usa para filtrar.

#### Paso 2 — El profesional comparte su Google Calendar

Igual que en el Tipo 2, Paso 2.

#### Paso 3 — Levantar

```bash
docker compose -f docker/docker-compose.yml up --build -d
```

En el primer arranque la BD está vacía — el validador lo detecta y muestra un warning (no es un error):

```
[CONFIG] ⚠️  SINGLE_PROFESSIONAL_MODE=true pero la BD está vacía.
  Esto es normal en el primer arranque.
  Cargar el profesional con:
    docker exec whatsapp-demo python scripts/csv/load_professionals_from_csv.py ...
```

#### Paso 4 — Cargar el profesional

```bash
# Windows Git Bash
docker exec whatsapp-demo python scripts/csv/load_professionals_from_csv.py \
  //app/data/csv_src/profesional.csv

# Linux/Mac
docker exec whatsapp-demo python scripts/csv/load_professionals_from_csv.py \
  /app/data/csv_src/profesional.csv
```

#### Paso 5 — Reiniciar para que el validador pase limpio

```bash
docker compose -f docker/docker-compose.yml restart whatsapp-demo
```

Ahora el log debe mostrar:

```
[CONFIG] ✅ Modo profesional único — Dr. Gastón Blanco
[CONFIG] ✅ Configuración válida
```

#### Paso 6 — Autorizar Meet links

```bash
python scripts/setup_oauth_meet.py
# No hace falta --phone, lo lee de SINGLE_PROFESSIONAL_PHONE automáticamente
```

#### Paso 7 — Verificación final

```bash
docker exec whatsapp-demo python tests/smoke/test_smoke_production.py
```

---

## Generación de claves seguras

Todas las claves marcadas como `XXXXXXX` deben generarse antes de desplegar:

```bash
# Redis password, OAuth setup key, Master access key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Verify token (más corto está bien)
python -c "import secrets; print(secrets.token_urlsafe(16))"
```

---

## Validaciones del validador al arrancar

El bot valida la coherencia de la configuración al iniciar y explota rápido si algo está mal. Tabla de checks:

| Check | Modo que lo activa | Error / Warning |
|---|---|---|
| `MEET_LINK_MODE` valor válido | siempre | ❌ Error fatal |
| `OAUTH_SETUP_KEY` no configurada | `always` o `auto` | ⚠️ Warning |
| `ALLOW_CLIENT_CHOOSE_MODALITY=True` | `auto` | ❌ Error fatal |
| `FilterType.MODALITY` habilitado | `auto` | ❌ Error fatal |
| `SINGLE_PROFESSIONAL_PHONE` configurado | `SINGLE_PROFESSIONAL_MODE=true` | ❌ Error fatal |
| `TENANT_TONE=freelance` | `SINGLE_PROFESSIONAL_MODE=true` | ❌ Error fatal |
| Profesional existe en BD | `SINGLE_PROFESSIONAL_MODE=true` | ⚠️ Warning si BD vacía / ❌ Error si BD tiene datos pero teléfono no coincide |
| `TENANT_TONE` y `DOMAIN_PRESET` compatibles | siempre | ❌ Error fatal |

---

## Tabla resumen de configuración por tipo

| Variable | Demo | Multi-profesional | Freelance |
|---|---|---|---|
| `ENVIRONMENT` | `development` | `production` | `production` |
| `DOMAIN_PRESET` | `DEMO` | `SALUD` (u otro) | `SALUD` (u otro) |
| `TENANT_TONE` | `demo` | `coloquial` | `freelance` |
| `SINGLE_PROFESSIONAL_MODE` | — | — | `true` |
| `SINGLE_PROFESSIONAL_PHONE` | — | — | teléfono del profesional |
| `MEET_LINK_MODE` | `never` | `never` / `always` / `auto` | `always` / `never` |
| `OAUTH_SETUP_KEY` | — | si Meet activo | si Meet activo |
| `ALLOW_KEY_REUSE` | `true` | `false` | `false` |

---

## Scripts de referencia

| Script | Cuándo usarlo |
|---|---|
| `scripts/csv/load_professionals_from_csv.py` | Alta inicial de profesionales |
| `scripts/csv/validate_pending_calendars.py` | Después de que un profesional comparte su Calendar |
| `scripts/csv/send_calendar_invitations.py` | Enviar email con instrucciones de Calendar al profesional |
| `scripts/setup_oauth_meet.py` | Autorizar Meet links para un profesional |
| `scripts/setup_calendar_watches.py` | Activar notificaciones push de Google Calendar |
| `tests/smoke/test_smoke_production.py` | Verificar que todo está bien antes del go-live |
