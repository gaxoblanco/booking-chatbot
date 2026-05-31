# 🔒 PRIVACY.md
## Política de Privacidad y Manejo de Datos
**Versión 2.0 — Mayo 2026**

---

## Índice

1. [Resumen ejecutivo](#resumen-ejecutivo)
2. [Qué datos se procesan](#qué-datos-se-procesan)
3. [Qué datos se almacenan y por cuánto tiempo](#qué-datos-se-almacenan-y-por-cuánto-tiempo)
4. [Qué datos NO se almacenan](#qué-datos-no-se-almacenan)
5. [Medidas técnicas implementadas](#medidas-técnicas-implementadas)
6. [Marco normativo](#marco-normativo)
7. [Flujo completo de un mensaje](#flujo-completo-de-un-mensaje)
8. [Preguntas frecuentes](#preguntas-frecuentes)

---

## Resumen ejecutivo

El sistema procesa mensajes de WhatsApp para gestionar turnos médicos. Durante ese procesamiento, los datos personales del paciente (número de teléfono, texto del mensaje) son necesarios para funcionar, pero **no se almacenan en su forma original**.

Desde la versión 2.0, la anonimización ocurre en el **punto de entrada** — antes de que cualquier dato toque el disco. No existe un paso posterior de limpieza porque la PII nunca llega a persistirse.

---

## Qué datos se procesan

### Datos en tránsito (no se persisten)

| Dato | Dónde se usa | Por qué | Se guarda en disco |
|------|-------------|---------|-------------------|
| Número de teléfono completo | Sesión Redis, envío de respuestas WhatsApp | Identificar al usuario y responderle | ❌ No |
| Texto del mensaje original | NLU, detección de intención | Entender qué quiere el usuario | ❌ No (se sanitiza) |
| Nombre del profesional buscado | Búsqueda en BD | Encontrar al profesional | ❌ No (se reemplaza por `[PROFESIONAL]`) |

### Datos en sesión activa (Redis, TTL 30 minutos)

| Dato | TTL | Qué contiene |
|------|-----|--------------|
| Estado de conversación | 30 min | Paso actual del flujo (menú, búsqueda, confirmación) |
| Entidades acumuladas | 30 min | Especialidad, fecha, zona seleccionados en el turno actual |
| Número de teléfono | 30 min | Como clave de sesión para Redis |

Una vez que el TTL expira, estos datos desaparecen automáticamente. No hay backup ni persistencia de sesiones.

### Datos en base de datos (SQLite — `booking.db`)

Estos datos son operacionales: son necesarios para que el sistema de turnos funcione.

| Tabla | Qué guarda | Retención |
|-------|-----------|-----------|
| `clients` | Teléfono, nombre | Mientras sea cliente activo |
| `appointments` | Turno, profesional, fecha, estado | Historial operacional |
| `professionals` | Datos del profesional | Mientras esté activo |
| `conversation_events` | Tipo de evento, intención, confianza | **7 días**, purga automática |

La tabla `conversation_events` **no guarda el texto del mensaje** — solo el tipo de acción realizada (reserva, cancelación, recordatorio enviado) e intent detectado. Sirve para que el bot recuerde si un recordatorio fue enviado cuando la sesión Redis ya expiró.

---

## Qué datos se almacenan y por cuánto tiempo

### Logs JSONL — `/app/data/conversations/`

Son los logs de ML para entrenar el detector de intenciones. Desde la v2.0, se guardan **ya anonimizados**.

**Retención: 60 días.** Script: `scripts/privacy/cleanup_conversations.py`

Formato de cada entrada en disco:

```json
{
  "timestamp":        "2026-05-13T14:30:00",
  "message":          "necesito psicólogo mañana",
  "detected_intent":  "search_professional",
  "entities":         { "especialidad": "psicología", "fecha": "mañana" },
  "confidence":       0.9,
  "shortcut_used":    true,
  "session_state":    "CLIENT_MAIN_MENU",
  "user_role":        "client",
  "human_reviewed":   false
}
```

Nótese la ausencia de `user_id` — el campo fue eliminado en v2.0.

### Dataset ML curado — `/app/dataset/`

Subconjunto de los logs anteriores, revisado manualmente y validado como correcto para entrenamiento. Sin retención definida — es el activo de entrenamiento del modelo, equivalente al código fuente. **No contiene PII** por el mismo motivo: hereda la anonimización del logger.

### CSVs de pacientes rechazados — `/app/data/rechazados/`

Archivos generados cuando una importación CSV tiene errores. Contienen nombre y teléfono del paciente que no pudo cargarse.

**Retención: 30 días.** Script: `scripts/csv/cleanup_rejected_csv.py`

---

## Qué datos NO se almacenan

Esto es explícito porque a veces genera dudas:

- ❌ El número de teléfono del paciente **no se guarda** en los logs de ML
- ❌ El texto libre del mensaje **no se guarda en su forma original** — se sanitiza antes de persistir
- ❌ Nombres de personas que aparezcan en el texto del mensaje son reemplazados por `[PROFESIONAL]`
- ❌ Números de documento (DNI, CUIL) detectados en el texto son reemplazados por `[DNI]`
- ❌ Teléfonos mencionados dentro del texto son reemplazados por `[TEL]`
- ❌ Las sesiones de Redis **no se persisten** en ningún almacenamiento secundario

---

## Medidas técnicas implementadas

### Anonimización en punto de entrada (v2.0)

**Archivo:** `src/services/message_sanitizer.py`

Antes de que cualquier dato toque el disco, `sanitize_log_entry()` aplica tres transformaciones:

```
Entrada cruda:
  user_id  = "4debb560f3d844b2"        → eliminado del log
  message  = "llamá al 1130001234"     → "llamá al [TEL]"
  entities = {professional_name: "García"} → {professional_name: "[PROFESIONAL]"}

Lo que llega al JSONL en disco:
  message  = "llamá al [TEL]"
  entities = {professional_name: "[PROFESIONAL]"}
  (sin user_id)
```

Patrones detectados y reemplazados en el texto del mensaje:

| Patrón | Token | Ejemplos detectados |
|--------|-------|---------------------|
| Teléfono argentino | `[TEL]` | `+5491130001234`, `1130001234`, `15-3000-1234` |
| DNI / CUIL / CUIT | `[DNI]` | `dni 35444123`, `35.444.123`, `cuil 20-35444123-9` |
| Nombre de profesional en entidades | `[PROFESIONAL]` | Campo `professional_name` en el dict de entidades |

Tests: `tests/security/test_message_sanitizer.py` — 32/32 pasando.

### Sanitización de PII en logs del container

**Archivo:** `src/core/logger.py`

Los logs de consola (`docker logs`) enmascaran teléfonos antes de escribir:

```
+5491112345678  →  +549****5678
```

Verificado con `tests/smoke/check_pii_logs.py` — 0 teléfonos en claro en 2000+ líneas de logs.

### Sesiones Redis con TTL

Redis configurado con TTL de 30 minutos por sesión. Configuración:

```
--maxmemory 256mb
--maxmemory-policy allkeys-lru
--requirepass ${REDIS_PASSWORD}
```

El puerto Redis no está expuesto al host (`expose:` en lugar de `ports:`).

### Retención automática con scripts de limpieza

| Componente | Script | Retención | Automático |
|-----------|--------|-----------|------------|
| Logs JSONL ML | `scripts/privacy/cleanup_conversations.py` | 60 días | Cron mensual recomendado |
| CSVs rechazados | `scripts/csv/cleanup_rejected_csv.py` | 30 días | Cron mensual recomendado |
| `conversation_events` | `event_store.purge_old_events()` | 7 días | ✅ Job diario automático |
| Sesiones Redis | TTL nativo | 30 minutos | ✅ Automático |

### Rate limiting y validación de origen

- Rate limiting por número de teléfono (sliding window)
- Validación de firma Twilio en cada webhook entrante
- Aislamiento por cliente: cada tenant solo ve sus propios datos

---

## Marco normativo

### Ley 25.326 — Protección de Datos Personales (Argentina)

| Requisito | Estado | Implementación |
|-----------|--------|----------------|
| Período de retención definido | ✅ | JSONL: 60 días / Events: 7 días / CSVs: 30 días |
| Datos mínimos necesarios | ✅ | Solo se persiste lo que usa el modelo ML |
| Medidas de seguridad técnicas | ✅ | Sanitización, Redis con auth, rate limiting |
| No transferencia a terceros | ✅ | Datos solo en infraestructura propia |

### WhatsApp Business Terms of Service

| Requisito | Estado | Notas |
|-----------|--------|-------|
| No almacenar contenido de mensajes sin consentimiento | ✅ | Los mensajes se sanitizan; el texto en disco no es el original |
| Datos usados solo para el servicio declarado | ✅ | Los logs JSONL son para mejorar el bot, no para otro fin |

### Sobre el dominio de salud mental (preset PSICOLOGÍA)

El sistema detecta **intención de búsqueda** de un profesional de salud mental, no datos clínicos. Lo que se registra es `detected_intent: "search_professional"` con entidad `especialidad: "psicología"`. Esto es equivalente a registrar que alguien buscó "psicólogo" en un buscador — no activa las restricciones de datos de salud clínicos bajo ninguno de los marcos normativos relevantes.

---

## Flujo completo de un mensaje

```
Paciente escribe: "necesito psicólogo para mañana, soy María García, tel 1130001234"
        │
        ▼
1. Twilio webhook → whatsapp_handler.py
   • Valida firma Twilio
   • Rate limiting por teléfono
        │
        ▼
2. bot_controller.py
   • Sesión cargada desde Redis (TTL 30 min)
   • NLU detecta intent: search_professional
   • Entidades: {especialidad: psicología, fecha: mañana}
        │
        ▼
3. conversation_logger.log_message()
   • Construye entry cruda con user_id (hash SHA-256 del teléfono)
   • Llama sanitize_log_entry():
       - Elimina user_id
       - message → "necesito psicólogo para mañana, soy María García, tel [TEL]"
       - entities sin professional_name → sin cambio
   • Persiste en conversations_2026-05-13.jsonl:
       {"message": "necesito psicólogo para mañana, soy María García, tel [TEL]", ...}
        │
        ▼
4. Respuesta al paciente vía Twilio
   • El teléfono real solo existe en memoria durante el request
   • Logs de consola: "+549****1234 | intent=search_professional"
        │
        ▼
5. A los 30 minutos: sesión Redis expirada automáticamente
6. A los 60 días: archivo JSONL eliminado por cleanup_conversations.py
```

---

## Preguntas frecuentes

**¿Puede un paciente pedir que se borren sus datos?**
Los datos operacionales (turnos en `booking.db`) pueden eliminarse manualmente por el administrador. Los logs ML en JSONL no contienen identificador de usuario desde la v2.0, por lo que no es posible identificar qué líneas corresponden a un paciente específico — lo cual es justamente la garantía de privacidad.

**¿Los mensajes están encriptados en disco?**
No están encriptados, pero están sanitizados: el texto que se guarda no es el mensaje original sino una versión con la PII reemplazada. El cifrado en reposo del volumen Docker queda a cargo de la infraestructura del servidor.

**¿Qué pasa si el sanitizador no detecta un teléfono?**
El sanitizador tiene tests automáticos que verifican los patrones principales. Si un formato nuevo no es detectado, el texto se guarda tal cual — sin PII reemplazada para ese patrón específico. Para agregar nuevos patrones: editar `_PHONE_PATTERNS` en `src/services/message_sanitizer.py` y agregar un test en `tests/security/test_message_sanitizer.py`.

**¿Los profesionales tienen acceso a los logs ML?**
No. Los logs en `/app/data/conversations/` solo son accesibles desde el container Docker por el administrador del sistema.

---

**Versión:** 2.0
**Última actualización:** Mayo 2026
**Documentos relacionados:** `docs/SECURITY.md`, `docs/DATOS.md`
**Scripts relacionados:** `scripts/privacy/cleanup_conversations.py`, `scripts/csv/cleanup_rejected_csv.py`
