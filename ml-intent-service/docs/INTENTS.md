# Intenciones — ML Intent Service
*Versión 2.0 — Junio 2026*

---

## Modelo actual

| Métrica | Valor |
|---------|-------|
| Intenciones | 16 |
| Ejemplos base | 558 |
| Dataset con augmentation | ~11.518 |
| Accuracy | 95.9% (mejor epoch) / 98.6% sobre dataset completo |
| Framework | spaCy 3.7.2 + TextCatEnsemble |
| Iteraciones | 50 · Dropout 0.2 · Batch size 8 |

### Métricas por intención (último entrenamiento)

| Intención | Precision | Recall | F1 |
|-----------|-----------|--------|----|
| `book_for_third_party` | 0.999 | 0.999 | 0.999 |
| `deny_action` | 0.998 | 0.967 | 0.982 |
| `agenda_confirm_upload` | 0.991 | 0.997 | 0.994 |
| `view_tomorrow` | 0.989 | 0.993 | 0.991 |
| `view_my_appointments` | 0.993 | 0.989 | 0.991 |
| `agenda_cancel_upload` | 0.994 | 0.987 | 0.990 |
| `cancel_appointment` | 0.985 | 0.993 | 0.989 |
| `agenda_view_ready` | 0.996 | 0.980 | 0.988 |
| `search_professional` | 0.989 | 0.989 | 0.989 |
| `agenda_view_overlaps` | 0.984 | 0.984 | 0.984 |
| `greeting` | 0.973 | 0.990 | 0.982 |
| `agenda_view_existing` | 0.984 | 0.980 | 0.982 |
| `confirm_action` | 0.990 | 0.962 | 0.976 |
| `agenda_view_errors` | 0.980 | 0.980 | 0.980 |
| `info_center` | 0.973 | 0.989 | 0.981 |
| `unknown` | 0.984 | 0.956 | 0.970 |

### Errores frecuentes conocidos

Los errores más comunes son sobre variantes con **typos agresivos** generadas
por el augmentation (e.g. `"nnefseito psicolgkoo mañaa"`), no sobre frases
reales de usuarios. En producción la accuracy real es mayor que el 95.9% del eval.

| Error | Causa probable |
|-------|----------------|
| `unknown → info_center` (27) | Frases fuera de scope con palabras del centro |
| `confirm_action → info_center` (10) | Augmentation genera typos que parecen preguntas |
| `deny_action → cancel_appointment` (5) | "cancelar" solo ambiguo — correcto en contexto |

---

## Convención de prefijos

Las intenciones contextuales (que solo tienen sentido en un estado específico
de la conversación) se entrenan con el estado de sesión prefixeado al mensaje.
El dispatcher en `bot_controller.py` concatena el prefijo antes de llamar al modelo:

```python
PREFIXED_STATES = {ConversationState.PROF_AGENDA_IMPORT_REVIEW}

text_for_model = (
    f"[{session.state.value.upper()}] {message}"
    if session.state in PREFIXED_STATES
    else message
)
```

Las intenciones **sin prefijo** (`confirm_action`, `deny_action` y todas las
globales) se entrenan con el mensaje limpio — el bot_controller usa el estado
de sesión para decidir qué hacer con el resultado.

---

## Intenciones globales

Sin prefijo. Aplican en cualquier estado.

### `search_professional`
El paciente quiere buscar un profesional o sacar un turno.

**Ejemplos:** "necesito psicólogo mañana", "turno con la Dra López",
"busco nutricionista para el jueves por la tarde"

**Estados donde aplica:** `START`, `CLIENT_MAIN_MENU`, filtros de búsqueda

---

### `view_my_appointments`
El paciente quiere ver sus turnos agendados.

**Ejemplos:** "ver mis turnos", "qué tengo agendado", "mis citas"

**Estados donde aplica:** `START`, `CLIENT_MAIN_MENU`

---

### `view_tomorrow`
El paciente quiere ver qué profesionales tienen disponibilidad mañana.

**Ejemplos:** "disponibles mañana", "turnos libres mañana por la tarde"

**Estados donde aplica:** `START`, `CLIENT_MAIN_MENU`

---

### `cancel_appointment`
El paciente quiere cancelar un turno existente.

**Ejemplos:** "cancelar turno", "quiero anular mi cita", "no puedo ir mañana"

**Estados donde aplica:** `START`, `CLIENT_MAIN_MENU`

**Distinción importante:** "cancelar" solo (sin objeto) se clasifica como
`deny_action`, no como `cancel_appointment`. El modelo aprendió la diferencia
por contexto léxico; el bot_controller la refuerza por estado de sesión.

---

### `book_for_third_party`
El paciente quiere agendar un turno para otra persona (familiar).

**Ejemplos:** "quiero turno para mi hijo", "es para mi mamá",
"no es para mí es para mi marido"

**Entidades:** `third_party_relation` (hijo, mamá, papá, hermana, etc.)

**Estados donde aplica:** mismos que `search_professional`

**Nota en bot_controller.py:**
```python
if intent == Intent.BOOK_FOR_THIRD_PARTY:
    session.set_temp('booking_for', 'other')
    session.set_temp('third_party_relation',
                     intent_result['entities'].get('third_party_relation'))
```

---

### `info_center`
El paciente pide información sobre el centro o consultorio.

**Ejemplos:** "información del centro", "dónde están ubicados",
"horarios de atención"

**Estados donde aplica:** `START`, `CLIENT_MAIN_MENU`

---

### `greeting`
Saludo del usuario.

**Ejemplos:** "hola", "buenos días", "buenas tardes"

**Estados donde aplica:** todos

---

### `confirm_action`
El paciente confirma una acción pendiente que el bot le propuso.
Sin prefijo de estado — aplica globalmente, pero el shortcut solo actúa
en los estados de confirmación; en cualquier otro estado se ignora.

**Ejemplos:** "sí", "dale", "ok", "va", "listo", "confirmo", "acepto",
"de una", "ese turno", "sí dale", "ta bien"

**Estados donde el shortcut actúa:**
`CLIENT_CONFIRM_BOOKING`, `CLIENT_CONFIRM_CANCEL`, `CLIENT_RESCHEDULE_CONFIRM`

**Comportamiento en bot_controller.py:**
```python
# _try_intent_shortcut
elif intent == Intent.CONFIRM_ACTION:
    _CONFIRM_STATES = {
        ConversationState.CLIENT_CONFIRM_BOOKING,
        ConversationState.CLIENT_CONFIRM_CANCEL,
        ConversationState.CLIENT_RESCHEDULE_CONFIRM,
    }
    if session.state in _CONFIRM_STATES:
        handler = self.get_handler_for_state(session.state)
        return handler(session, '1')
    return None  # fuera de estado de confirmación → ignorado
```

**Relación con normalizers.py:** `normalize_yes_no()` sigue activo como
capa rule-based de respaldo para estados que no pasan por el NLU (e.g.
`CLIENT_FILTER_INPUT`). El NLU y el normalizer son complementarios, no
excluyentes. Cuando el modelo migre completamente, la implementación
interna de `normalize_yes_no()` puede delegarse al ML sin cambiar la
interfaz pública.

**20 ejemplos en el dataset** — suficiente para el augmentation x20.

---

### `deny_action`
El paciente rechaza una acción pendiente o quiere volver atrás.
Sin prefijo de estado — misma lógica que `confirm_action`.

**Ejemplos:** "no", "nope", "nel", "para nada", "mejor no", "no gracias",
"cancelar", "volver", "salir", "me arrepentí", "prefiero no", "paso"

**Estados donde el shortcut actúa:**
`CLIENT_CONFIRM_BOOKING`, `CLIENT_CONFIRM_CANCEL`, `CLIENT_RESCHEDULE_CONFIRM`

**Comportamiento en bot_controller.py:**
```python
# _try_intent_shortcut
elif intent == Intent.DENY_ACTION:
    _DENY_STATES = {
        ConversationState.CLIENT_CONFIRM_BOOKING,
        ConversationState.CLIENT_CONFIRM_CANCEL,
        ConversationState.CLIENT_RESCHEDULE_CONFIRM,
    }
    if session.state in _DENY_STATES:
        handler = self.get_handler_for_state(session.state)
        return handler(session, '0')
    return None  # fuera de estado de confirmación → ignorado
```

**Nota:** `deny_action` NO dispara `handle_cancel()` global. "Cancelar"
como respuesta a una pregunta es un rechazo de la acción propuesta,
no una solicitud de cancelar un turno existente.

**20 ejemplos en el dataset.**

---

### `unknown`
El mensaje no corresponde a ninguna intención del sistema. Puede ser
una pregunta legítima fuera del alcance (precio, obra social, dirección)
o texto sin sentido.

**Ejemplos:** "cuánto sale la consulta", "aceptan IOMA",
"cómo llego al consultorio", "asdfasdf"

**Estados donde aplica:** todos — el bot responde con el mensaje de
"no entendí, ¿en qué te puedo ayudar?"

---

## Intenciones contextuales — importación de agenda

Solo aplican cuando el profesional está en estado `PROF_AGENDA_IMPORT_REVIEW`.
Todas se entrenan con el prefijo `[PROF_AGENDA_IMPORT_REVIEW]`.

El dispatcher traduce estas intenciones a comandos numéricos antes de
pasarlas al handler:

```python
INTENT_TO_MESSAGE = {
    Intent.AGENDA_VIEW_READY:      '2',
    Intent.AGENDA_VIEW_OVERLAPS:   '3',
    Intent.AGENDA_VIEW_EXISTING:   '4',
    Intent.AGENDA_VIEW_ERRORS:     '5',
    Intent.AGENDA_CONFIRM_UPLOAD:  '1',
    Intent.AGENDA_CANCEL_UPLOAD:   '0',
}
```

---

### `agenda_view_ready`
El profesional quiere ver los pacientes sin conflictos, listos para cargar.

**Ejemplos:** "ver listos", "mostrame los nuevos", "cuáles se pueden cargar",
"los que están bien"

---

### `agenda_view_overlaps`
El profesional quiere ver los pacientes con solapamiento de horario.

**Ejemplos:** "ver solapamientos", "mostrame los que se pisan",
"cuáles tienen conflicto de horario"

---

### `agenda_view_existing`
El profesional quiere ver los pacientes que ya estaban cargados en el sistema.

**Ejemplos:** "ver existentes", "los repetidos", "cuáles ya estaban",
"mostrame los duplicados"

---

### `agenda_view_errors`
El profesional quiere ver las filas con datos inválidos o incompletos.

**Ejemplos:** "ver errores", "qué falló", "mostrame los inválidos",
"qué no se puede cargar"

---

### `agenda_confirm_upload`
El profesional confirma que quiere proceder con la carga de pacientes listos.

**Ejemplos:** "sí", "dale", "ok", "cargar", "confirmo", "adelante", "va"

**Nota:** 15 ejemplos en el dataset (más que las otras) por alta ambigüedad
fuera de contexto. El prefijo de estado es crítico para esta intención.

---

### `agenda_cancel_upload`
El profesional decide no proceder con la carga.

**Ejemplos:** "no", "cancelar", "volver", "lo corrijo primero",
"hay muchos errores", "me arrepentí"

**Nota:** ídem `agenda_confirm_upload` — 15 ejemplos, prefijo crítico.

---

## Archivos relacionados

| Archivo | Rol |
|---------|-----|
| `scripts/ml/dataset_base.py` | Ejemplos base de cada intención |
| `ml/intent_enum.py` | Enum `Intent` con todos los valores (servicio ML) |
| `ml/ml_intent_detector.py` | `intent_map` — mapeo label → enum |
| `booking-chatbot/src/services/intent_detector.py` | Enum `Intent` en el bot |
| `booking-chatbot/src/bot/bot_controller.py` | Dispatcher + prefijo de estado + shortcut |
| `booking-chatbot/src/core/normalizers.py` | Capa rule-based de respaldo (sí/no/indiferente) |

---

## Agregar una intención nueva

Ver `docs/SETUP_INSTRUCTIONS.md` sección "Agregar intenciones nuevas".
Resumen de los pasos: editar `dataset_base.py` → editar enum `Intent` en ambos proyectos →
editar `intent_map` en `ml_intent_detector.py` → regenerar dataset → reentrenar →
evaluar → reiniciar servicio → conectar en `bot_controller.py`.