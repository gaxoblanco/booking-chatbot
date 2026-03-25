# Intenciones — ML Intent Service
*Versión 1.0 — Marzo 2026*

---

## Modelo actual

| Métrica | Valor |
|---------|-------|
| Intenciones | 14 |
| Ejemplos base | 196 |
| Dataset con augmentation | ~4.116 |
| Accuracy | 95.3% (mejor epoch) |
| Framework | spaCy 3.7.2 + TextCatEnsemble |

---

## Convención de prefijos

Las intenciones contextuales (que solo tienen sentido en un estado
específico de la conversación) se entrenan con el estado de sesión
prefixeado al mensaje. El dispatcher en `bot_controller.py` concatena
el prefijo antes de llamar al modelo:

```python
PREFIXED_STATES = {ConversationState.PROF_AGENDA_IMPORT_REVIEW}

text_for_model = (
    f"[{session.state.value.upper()}] {message}"
    if session.state in PREFIXED_STATES
    else message
)
```

Esto permite que frases ambiguas como "sí", "no", "ver errores"
sean detectadas correctamente según el contexto del profesional.

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
| `ml/intent_enum.py` | Enum `Intent` con todos los valores |
| `ml/ml_intent_detector.py` | `intent_map` — mapeo label → enum |
| `booking-chatbot/src/services/intent_detector.py` | Enum `Intent` en el bot |
| `booking-chatbot/src/bot/bot_controller.py` | Dispatcher + prefijo de estado |

---

## Agregar una intención nueva

Ver `docs/SETUP_INSTRUCTIONS.md` sección "Agregar intenciones nuevas".
Resumen de los 10 pasos: editar dataset → editar enums en ambos proyectos →
editar intent_map → regenerar → reentrenar → evaluar → reiniciar → conectar en bot.
