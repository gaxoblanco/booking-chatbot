# MEET_LINK_MODE — Google Meet como servicio configurable
**Feature branch:** `feature/meet-link`
**Estado:** ✅ Implementado (Junio 2026)

---

## Contexto

El link de Google Meet se genera al crear el evento en Google Calendar y se persiste
en BD (`appointments.meet_link`). La generación es configurable por tenant vía
`MEET_LINK_MODE` en `.env`.

### Modos disponibles

| Modo | Descripción | Caso de uso | Estado |
|---|---|---|---|
| `never` | Nunca genera Meet link | Centros presenciales | ✅ Funcional |
| `always` | Siempre genera Meet link | Freelance, consultores remotos | ✅ Funcional |
| `virtual_only` | Solo en turnos virtuales | **⚠️ PENDIENTE** — requiere flujo de modalidad | ❌ Bloqueado |

### Limitación con Gmail gratuito — resuelta via OAuth2

Google Calendar no permite crear Meet links cuando la operación se realiza mediante
Service Account en calendarios de cuentas Gmail gratuitas. El error que devuelve es:

```
HttpError 400: Invalid conference type value
```

**Solución implementada:** OAuth2 por profesional. Cuando el profesional tiene
`oauth_refresh_token` en BD y `MEET_LINK_MODE=always`, el sistema usa las credenciales
OAuth2 del profesional en lugar de la Service Account para crear el evento.
Esto permite generar Meet links en cuentas Gmail gratuitas.

La Service Account sigue usándose para lectura de disponibilidad (slots). Solo la
**creación de eventos** usa OAuth2 cuando está disponible.

---

## Arquitectura implementada

### Cadena de creación de eventos

```
appointment_calendar_service.create_appointment()
    │
    ├── db.get_professional_oauth_tokens(professional_phone)
    │
    ├── Si tiene oauth_refresh_token Y meet_mode == 'always':
    │       _create_appointment_with_oauth()
    │           ├── Reconstruir Credentials desde refresh_token
    │           ├── Renovar access_token si expiró (automático)
    │           ├── Guardar nuevo access_token en BD
    │           └── service.events().insert(conferenceDataVersion=1)
    │                   └── hangoutLink en la respuesta ✅
    │
    └── Si no tiene oauth_refresh_token O meet_mode == 'never':
            calendar_service.create_appointment() (Service Account)
                └── event_manager.create_appointment(conference_data_version)
                        └── calendar_client.create_event(conferenceDataVersion=N)
```

### BD — columnas OAuth en `professionals`

```sql
oauth_refresh_token TEXT DEFAULT NULL   -- token larga duración
oauth_access_token  TEXT DEFAULT NULL   -- token corto (1 hora), se renueva auto
oauth_token_expiry  TIMESTAMP DEFAULT NULL
```

### Nuevos archivos

```
src/integrations/google/oauth_state_store.py   -- state → phone durante flujo OAuth2
src/api/whatsapp_handler.py GET /oauth/callback -- recibe código, guarda tokens en BD
scripts/test_oauth_meet.py                      -- script de autorización inicial
```

---

## Setup OAuth2 para profesional nuevo

### 1. Crear credenciales OAuth2 en Google Cloud Console

1. APIs & Services → Credenciales → Crear → ID de cliente OAuth 2.0
2. Tipo: **Aplicación web**
3. URIs de redirección autorizados:
   ```
   https://TU-DOMINIO/oauth/callback
   ```
4. Descargar JSON → extraer `client_id` y `client_secret`

### 2. Configurar `.env`

```env
GOOGLE_OAUTH_CLIENT_ID=...
GOOGLE_OAUTH_CLIENT_SECRET=...
GOOGLE_OAUTH_REDIRECT_URI=https://TU-DOMINIO/oauth/callback
```

### 3. Autorizar al profesional

```bash
# Correr fuera del Docker (necesita browser)
python scripts/test_oauth_meet.py
```

El script genera una URL de autorización, el profesional la abre, aprueba,
y el script guarda el `refresh_token` directamente en la BD del Docker.

### 4. Verificar

```bash
docker exec whatsapp-demo python -c "
from src.database.database import db
tokens = db.get_professional_oauth_tokens('+549XXXXXXXXXX')
print('OAuth configurado:', tokens is not None)
"
```

---

## Archivos implementados — resumen de cambios

| Archivo | Cambio |
|---|---|
| `src/config/domain_config.py` | `MEET_LINK_MODE` configurable |
| `src/config/filter_config.py` | `ASK_MODALITY = False` (stub) |
| `src/config/config_validator.py` | Validador al boot |
| `src/integrations/appointment_calendar_service.py` | Lógica OAuth2 vs Service Account |
| `src/integrations/google_calendar_service/calendar/event_manager.py` | `conference_data_version` + `conferenceData` en body |
| `src/integrations/google_calendar_service/calendar/calendar_client.py` | Fallback silencioso si Google rechaza Meet |
| `src/integrations/google/oauth_state_store.py` | **Nuevo** — state store en memoria |
| `src/api/whatsapp_handler.py` | **Nuevo** endpoint `GET /oauth/callback` |
| `src/database/database.py` | Columnas OAuth en `professionals` |
| `scripts/test_oauth_meet.py` | **Nuevo** — script de autorización |

---

## Verificación

```bash
# 1. Verificar que el validador corre al arrancar
docker compose logs whatsapp-demo | grep "\[CONFIG\]"
# Esperado: [CONFIG] ✅ Configuración válida

# 2. Verificar OAuth configurado para un profesional
docker exec whatsapp-demo python -c "
from src.database.database import db
tokens = db.get_professional_oauth_tokens('+549XXXXXXXXXX')
print('OAuth:', 'configurado' if tokens else 'NO configurado')
"

# 3. Verificar meet_link guardado después de un booking
docker exec whatsapp-demo python -c "
from src.database.database import db
with db.get_connection() as conn:
    rows = conn.execute('''
        SELECT id, appointment_date, start, meet_link
        FROM appointments
        WHERE google_event_id IS NOT NULL
        ORDER BY created_at DESC LIMIT 3
    ''').fetchall()
    for r in rows: print(dict(r))
"
```

---

## Pendiente — `virtual_only`

Para habilitar este modo en el futuro:

1. Implementar estado `CLIENT_ASK_MODALITY` en `src/core/states.py`
2. Agregar handler en `client_handler.py` que pregunte presencial/virtual
3. Pasar `modality` a `appointment_service.create_appointment()`
4. Agregar lógica en `appointment_calendar_service`:
   ```python
   elif meet_mode == 'virtual_only':
       usar_oauth = modality == 'virtual' and oauth_tokens
   ```
5. Setear `FeatureFlags.ASK_MODALITY = True`
6. Mover `'virtual_only'` a `_MEET_MODES_ENABLED` en `config_validator.py`