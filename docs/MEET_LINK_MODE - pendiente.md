# MEET_LINK_MODE — Google Meet como servicio configurable
**Feature branch:** `feature/meet-link-mode`
**Depende de:** `feature/meet-link` (ya mergeado)
**Estado:** Pendiente

---

## Contexto

El link de Google Meet ya se genera y persiste en BD (`appointments.meet_link`).
Esta feature lo convierte en un servicio configurable por tenant vía `DomainConfig`.

### Modos disponibles

| Modo | Descripción | Caso de uso |
|---|---|---|
| `never` | Nunca genera Meet link | Centros presenciales (coloquial) |
| `always` | Siempre genera Meet link | Freelance, consultores remotos |
| `virtual_only` | Solo en turnos virtuales | **⚠️ PENDIENTE** — requiere flujo de modalidad |

### Estado actual post-`feature/meet-link`

- `conferenceDataVersion=1` hardcodeado → siempre genera Meet
- No hay configuración por tenant
- No hay validación al arrancar

---

## Archivos a modificar — en orden de ejecución

```
src/config/domain_config.py          ← Paso 1: agregar MEET_LINK_MODE
src/config/filter_config.py          ← Paso 2: agregar ASK_MODALITY (stub)
src/config/config_validator.py       ← Paso 3: CREAR — validador al boot
app.py (o create_app())              ← Paso 4: llamar al validador
src/services/appointment_service.py  ← Paso 5: lógica de decisión
```

---

## Paso 1 — `src/config/domain_config.py`

Agregar la constante `MEET_LINK_MODE` junto a las otras configuraciones de comportamiento
(cerca de `CANCELLATION_HOURS_LIMIT` o `MAX_ACTIVE_APPOINTMENTS_GLOBAL_PER_CLIENT`).

```python
# ---------------------------------------------------------
# MEET LINK — Google Meet en confirmación de turno
# ---------------------------------------------------------
# Controla si se genera un link de videoconferencia al crear el evento
# en Google Calendar.
#
# Valores válidos:
#   'never'        → nunca genera Meet (centros presenciales)
#   'always'       → siempre genera Meet (freelance, remoto)
#   'virtual_only' → ⚠️ NO DISPONIBLE — requiere FeatureFlags.ASK_MODALITY=True
#                    Habilitarlo antes de implementar el flujo de modalidad
#                    causa un error de configuración al arrancar.
MEET_LINK_MODE: str = 'never'   # cambiar a 'always' para tono freelance
```

---

## Paso 2 — `src/config/filter_config.py`

Agregar el flag `ASK_MODALITY` en la clase `FeatureFlags`.
Por ahora es `False` — es el stub que el validador del Paso 3 necesita leer.

```python
class FeatureFlags:
    # ... flags existentes ...

    # Flujo de selección de modalidad durante el booking
    # (presencial / virtual). Requerido para MEET_LINK_MODE='virtual_only'.
    # ⚠️ NO activar hasta implementar el estado CLIENT_ASK_MODALITY
    # en client_handler.py y states.py.
    ASK_MODALITY: bool = False
```

---

## Paso 3 — CREAR `src/config/config_validator.py`

Archivo nuevo. Contiene una función que valida la coherencia de la configuración
antes de que la app levante. Si algo está mal, lanza `ValueError` con un mensaje claro.

```python
"""
Config Validator
================
Valida la coherencia entre DomainConfig y FeatureFlags al arrancar.
Se llama una sola vez desde create_app() o app.py.

Si la configuración es inválida, lanza ValueError con un mensaje
que explica exactamente qué falta y cómo corregirlo.
Fail fast — mejor explotar en el boot que fallar en producción.
"""

from src.config.domain_config import DomainConfig
from src.config.filter_config import FeatureFlags

# Modos de Meet habilitados en esta versión.
# 'virtual_only' se agrega acá cuando ASK_MODALITY esté implementado.
_MEET_MODES_ENABLED = {'never', 'always'}


def validate_config() -> None:
    """
    Valida la configuración al arrancar.
    Lanza ValueError si encuentra una combinación inválida.

    Checks:
        1. MEET_LINK_MODE es un valor conocido
        2. MEET_LINK_MODE='virtual_only' requiere ASK_MODALITY=True
           (bloqueado hasta que el flujo esté implementado)
    """
    _validate_meet_link_mode()
    print("[CONFIG] ✅ Configuración válida")


def _validate_meet_link_mode() -> None:
    mode = DomainConfig.MEET_LINK_MODE

    # Check 1 — valor conocido (incluyendo los pendientes)
    _ALL_KNOWN_MODES = {'never', 'always', 'virtual_only'}
    if mode not in _ALL_KNOWN_MODES:
        raise ValueError(
            f"[CONFIG] ❌ MEET_LINK_MODE='{mode}' no es un valor válido.\n"
            f"Valores permitidos: {_ALL_KNOWN_MODES}\n"
            f"Revisar src/config/domain_config.py"
        )

    # Check 2 — virtual_only bloqueado hasta que el flujo esté listo
    if mode == 'virtual_only':
        if not FeatureFlags.ASK_MODALITY:
            raise ValueError(
                "[CONFIG] ❌ MEET_LINK_MODE='virtual_only' requiere "
                "FeatureFlags.ASK_MODALITY=True.\n"
                "El flujo de selección de modalidad no está implementado.\n"
                "Opciones:\n"
                "  - Usar MEET_LINK_MODE='always' o 'never' por ahora\n"
                "  - Implementar CLIENT_ASK_MODALITY en client_handler.py "
                "y states.py antes de habilitar este modo"
            )
```

---

## Paso 4 — `app.py` (o `create_app()`)

Llamar al validador **antes** de registrar rutas o inicializar servicios.
Si falla, la app no arranca y el error aparece en los logs de Docker.

Agregar al inicio del archivo, después de los imports:

```python
from src.config.config_validator import validate_config

# Validar configuración al arrancar — fail fast
validate_config()
```

Si la app usa factory pattern (`create_app()`), ponerlo al inicio de esa función,
antes del primer `app.register_blueprint(...)`.

---

## Paso 5 — `src/services/appointment_service.py`

Función: `create_appointment()`

Reemplazar el bloque `# 2. Crear evento en Google Calendar` completo:

```python
            # 2. Crear evento en Google Calendar
            # conference_data_version depende de MEET_LINK_MODE:
            #   'never'   → 0 (sin Meet)
            #   'always'  → 1 (siempre Meet)
            #   'virtual_only' → 1 solo si modality='virtual' (requiere ASK_MODALITY)
            from src.config.domain_config import DomainConfig

            meet_mode = DomainConfig.MEET_LINK_MODE
            if meet_mode == 'always':
                conference_data_version = 1
            else:
                # 'never' — 'virtual_only' está bloqueado por el validador
                # si llega acá con virtual_only es porque ASK_MODALITY=True
                # y el flujo pasó la modalidad en kwargs (implementación futura)
                conference_data_version = 0

            logger.info(f"Creando evento en Google Calendar (meet_mode={meet_mode})...")
            google_event = self.calendar_service.create_appointment(
                calendar_id=calendar_id,
                start_datetime=f"{date} {start_time}",
                end_datetime=f"{date} {end_time}",
                client_name=client_name,
                client_phone=client_phone,
                appointment_type=appointment_type,
                notes=notes,
                conference_data_version=conference_data_version
            )

            google_event_id = google_event['id']
            # meet_link presente solo si conference_data_version=1
            # y Google tiene permisos de Meet en el calendario
            meet_link = google_event.get('hangoutLink') if meet_mode != 'never' else None
            logger.info(
                f"Evento creado en Google Calendar: {google_event_id} | "
                f"Meet: {meet_link or 'sin link'}"
            )
```

Para que `conference_data_version` llegue al `event_manager`, también hay que
actualizarlo en la cadena de fachadas.

### Cadena completa del parámetro

El parámetro `conference_data_version` tiene que propagarse por estas funciones
(ya preparadas con `default=0` en la feature anterior):

```
appointment_service.create_appointment()      ← Paso 5 (acá)
    └── calendar_service.create_appointment() ← google_calendar_service.py (fachada)
            └── event_manager.create_appointment()  ← ya preparado
                    └── calendar_client.create_event(conferenceDataVersion=N)  ← ya preparado
```

Las dos fachadas intermedias necesitan recibir y pasar el parámetro:

**`src/integrations/google_calendar_service/google_calendar_service.py`**
`create_appointment()` — agregar en firma y en el `return self.event_manager.create_appointment(...)`:
```python
conference_data_version: int = 0,   # ← agregar en firma
# ...
conference_data_version=conference_data_version  # ← agregar en el call
```

**`src/integrations/google_calendar_service/calendar/event_manager.py`**
`create_appointment()` — ya tiene `conferenceDataVersion` hardcodeado en `1`.
Reemplazar por el parámetro recibido:
```python
conference_data_version: int = 0,   # ← agregar en firma
# ...
# En el call a calendar_client.create_event():
conference_data_version=conference_data_version  # ← reemplazar el 1 hardcodeado
```

---

## Verificación post-deploy

```bash
# 1. Verificar que el validador corre al arrancar
docker compose logs whatsapp-demo | grep "\[CONFIG\]"
# Esperado: [CONFIG] ✅ Configuración válida

# 2. Probar configuración inválida (smoke test)
# Cambiar temporalmente MEET_LINK_MODE = 'virtual_only' en domain_config.py
# con ASK_MODALITY = False → la app NO debe arrancar

# 3. Verificar meet_link en BD después de un booking con mode='always'
docker exec -it whatsapp-demo python -c "
from src.database.database import db
apt = db.get_appointment(1)  # reemplazar con ID real
print('meet_link:', apt.get('meet_link'))
"
```

---

## Pendiente — `virtual_only`

Para habilitar este modo en el futuro, los pasos son:

1. Implementar estado `CLIENT_ASK_MODALITY` en `src/core/states.py`
2. Agregar handler en `client_handler.py` que pregunte presencial/virtual
   y guarde `modality` en `session.temp_data`
3. Pasar `modality` a `appointment_service.create_appointment()`
4. En el Paso 5 de este doc, agregar el caso:
   ```python
   elif meet_mode == 'virtual_only':
       conference_data_version = 1 if modality == 'virtual' else 0
   ```
5. Setear `FeatureFlags.ASK_MODALITY = True`
6. Mover `'virtual_only'` a `_MEET_MODES_ENABLED` en `config_validator.py`

---

## Resumen de cambios

| Archivo | Tipo | Qué |
|---|---|---|
| `domain_config.py` | Modificar | Agregar `MEET_LINK_MODE = 'never'` |
| `filter_config.py` | Modificar | Agregar `ASK_MODALITY = False` |
| `config_validator.py` | **Crear** | Validador al boot |
| `app.py` | Modificar | Llamar `validate_config()` al arrancar |
| `appointment_service.py` | Modificar | Lógica `conference_data_version` según modo |
| `google_calendar_service.py` | Modificar | Propagar `conference_data_version` (fachada) |
| `event_manager.py` | Modificar | Recibir y usar `conference_data_version` |
