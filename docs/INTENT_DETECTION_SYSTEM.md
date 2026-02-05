# 🧠 SISTEMA DE DETECCIÓN DE INTENCIONES
## Estado Actual y Roadmap hacia Machine Learning

**Última actualización:** 4 de Febrero, 2026  
**Versión del Sistema:** v3.1 (Rule-based)  
**Próxima versión planeada:** v4.0 (ML/Hybrid)

---

## 📋 ÍNDICE

1. [Visión General](#visión-general)
2. [Sistema Actual: Basado en Reglas](#sistema-actual-basado-en-reglas)
3. [Arquitectura del Intent Detector](#arquitectura-del-intent-detector)
4. [Intenciones Soportadas](#intenciones-soportadas)
5. [Extracción de Entidades](#extracción-de-entidades)
6. [Integración con Bot Controller](#integración-con-bot-controller)
7. [Limitaciones Actuales](#limitaciones-actuales)
8. [Roadmap: Migración a ML](#roadmap-migración-a-ml)
9. [Plan de Implementación](#plan-de-implementación)
10. [Comparativa: Reglas vs ML](#comparativa-reglas-vs-ml)

---

## 🎯 VISIÓN GENERAL

### **¿Qué es el Sistema de Detección de Intenciones?**

El sistema de detección de intenciones es el **cerebro conversacional** del bot. Su función es:

1. **Entender qué quiere el usuario** sin preguntarle explícitamente
2. **Extraer información clave** del mensaje (fecha, especialidad, horario, etc.)
3. **Decidir si puede hacer "shortcuts"** (ir directo a resultados sin mostrar menús)
4. **Acumular contexto** para conversaciones multi-turno

### **Ejemplos de Uso**

```
Usuario: "necesito psicólogo mañana por la tarde"
Sistema detecta:
  ├─ Intent: SEARCH_PROFESSIONAL (90% confianza)
  ├─ Entidades: {especialidad: psicología, fecha: mañana, horario: tarde}
  └─ Acción: Buscar directamente (shortcut ✅)

Usuario: "hola"
Sistema detecta:
  ├─ Intent: GREETING (100% confianza)
  ├─ Entidades: {}
  └─ Acción: Mostrar menú principal
```

### **Beneficios para el Usuario**

- ✅ **Conversación natural**: No necesita seguir menús rígidos
- ✅ **Menos clicks**: Va directo a lo que busca
- ✅ **Contexto acumulativo**: No repite información ya dada
- ✅ **Flexibilidad**: Puede escribir como habla naturalmente

---

## 🔧 SISTEMA ACTUAL: BASADO EN REGLAS

### **Estado:** ✅ IMPLEMENTADO Y EN PRODUCCIÓN

El sistema actual (`src/services/intent_detector.py`) utiliza **reglas y patrones** para detectar intenciones.

### **Características Principales**

| Componente | Descripción | Estado |
|------------|-------------|--------|
| **Intent Detection** | Clasificación basada en keywords | ✅ Implementado |
| **Entity Extraction** | Regex + diccionarios de palabras clave | ✅ Implementado |
| **Confidence Scoring** | Scoring heurístico (0.0 - 1.0) | ✅ Implementado |
| **Shortcut Logic** | Decide si omitir menús | ✅ Implementado |
| **Context Accumulation** | Acumula entidades multi-turno | ✅ Implementado |
| **Professional Name Detection** | Detecta "con Dr. Juan Pérez" | ✅ Implementado |
| **Fallback to Menu** | Si no hay confianza → menú | ✅ Implementado |

### **Tecnología Utilizada**

```python
# Stack actual
- Python 3.10+
- Regex (re module)
- String matching
- Custom heuristics
- No dependencias externas de ML
```

### **Ventajas del Sistema Actual**

✅ **Rápido**: No requiere GPU ni modelos pesados  
✅ **Predecible**: Comportamiento consistente  
✅ **Sin dependencias**: No requiere librerías de ML  
✅ **Fácil de debuggear**: Lógica transparente  
✅ **Sin datos de entrenamiento**: No necesita dataset etiquetado  

### **Desventajas del Sistema Actual**

❌ **Limitado**: Solo funciona con patrones conocidos  
❌ **Frágil**: Typos o sinónimos no previstos lo rompen  
❌ **Mantenimiento manual**: Cada nueva frase requiere nueva regla  
❌ **No aprende**: No mejora con el uso  
❌ **Confianza artificial**: El scoring es heurístico, no probabilístico  

---

## 🏗️ ARQUITECTURA DEL INTENT DETECTOR

### **Ubicación**
```
src/services/intent_detector.py  (~600 líneas)
```

### **Clase Principal**

```python
class IntentDetector:
    """
    Detector de intenciones basado en reglas.
    
    Pipeline de procesamiento:
    1. Normalización del texto
    2. Detección de intent (keywords + patterns)
    3. Extracción de entidades (regex + diccionarios)
    4. Scoring de confianza (heurístico)
    5. Decisión de shortcut
    """
    
    def __init__(self):
        """Carga keywords y patrones."""
        self._setup_patterns()
    
    def detect(self, message: str, context: Optional[Dict] = None) -> Dict:
        """
        Punto de entrada principal.
        
        Args:
            message: Texto del usuario
            context: Información de sesión (rol, estado, historial)
            
        Returns:
            {
                'intent': Intent (enum),
                'confidence': float (0.0-1.0),
                'entities': dict,
                'can_shortcut': bool,
                'missing_entities': list
            }
        """
        pass
```

### **Método de Detección**

```python
def _detect_intent(self, message: str) -> tuple:
    """
    Detecta intent usando keyword matching.
    
    Retorna: (Intent, confidence_score)
    """
    
    # 1. Ver mis citas (highest priority)
    if self._contains_any(message, self.appointments_keywords):
        return Intent.VIEW_MY_APPOINTMENTS, 0.95
    
    # 2. Cancelar turno
    if self._contains_any(message, self.cancel_keywords):
        return Intent.CANCEL_APPOINTMENT, 0.9
    
    # 3. Ver disponibles mañana
    if self._contains_any(message, self.tomorrow_keywords):
        return Intent.VIEW_TOMORROW, 0.9
    
    # 4. Buscar profesional
    if self._contains_any(message, self.search_keywords):
        return Intent.SEARCH_PROFESSIONAL, 0.85
    
    # 5. Información del centro
    if self._contains_any(message, self.info_keywords):
        return Intent.INFO_CENTER, 0.8
    
    # 6. Saludo simple
    if self._is_greeting(message):
        return Intent.GREETING, 1.0
    
    # Default: Unknown
    return Intent.UNKNOWN, 0.0
```

### **Keywords por Intent**

```python
# SEARCH_PROFESSIONAL
self.search_keywords = [
    'buscar', 'busco', 'necesito', 'quiero', 'quisiera',
    'buscando', 'encontrar', 'conseguir', 'agendar',
    'reservar', 'turno', 'cita', 'sesión', 'consulta',
    'sacar turno', 'pedir turno', 'coordinar'
]

# VIEW_MY_APPOINTMENTS
self.appointments_keywords = [
    'mis turnos', 'mis citas', 'ver mis turnos',
    'ver mis citas', 'mis reservas', 'turnos agendados',
    'citas programadas', 'agenda', 'agendados',
    'ver turnos', 'ver citas', 'mis consultas'
]

# CANCEL_APPOINTMENT
self.cancel_keywords = [
    'cancelar', 'anular', 'borrar turno', 'eliminar turno',
    'borrar cita', 'eliminar cita', 'cancelar turno',
    'cancelar cita', 'no voy a ir', 'no puedo ir'
]

# VIEW_TOMORROW
self.tomorrow_keywords = [
    'disponibles mañana', 'disponibles manana',
    'horarios mañana', 'horarios manana', 
    'turnos mañana', 'turnos manana',
    'libres mañana', 'libres manana'
]
```

---

## 📌 INTENCIONES SOPORTADAS

### **1. SEARCH_PROFESSIONAL** 🔍
**Descripción:** Usuario quiere buscar profesional con filtros

**Ejemplos:**
```
✅ "necesito psicólogo mañana"
✅ "busco nutricionista en zona norte"
✅ "quiero turno con kinesióloga"
✅ "agendar consulta para el jueves"
```

**Entidades asociadas:**
- `especialidad`: psicología, nutrición, kinesiología
- `fecha`: hoy, mañana, DD/MM
- `horario`: mañana, tarde, noche
- `zona`: norte, sur, centro, online
- `genero`: masculino, femenino
- `prepaga`: true/false
- `professional_name`: "Juan Pérez"

**Shortcut:** ✅ Sí, si tiene al menos `fecha`

---

### **2. VIEW_TOMORROW** 📅
**Descripción:** Usuario quiere ver disponibles para mañana

**Ejemplos:**
```
✅ "quiénes tienen disponible mañana"
✅ "disponibles mañana por la tarde"
✅ "turnos libres mañana"
```

**Entidades asociadas:**
- `horario`: (opcional) mañana, tarde, noche

**Shortcut:** ✅ Siempre (fecha ya está implícita)

---

### **3. VIEW_MY_APPOINTMENTS** 📋
**Descripción:** Usuario quiere ver sus citas agendadas

**Ejemplos:**
```
✅ "ver mis turnos"
✅ "mis citas"
✅ "qué tengo agendado"
✅ "consultar mis reservas"
```

**Entidades asociadas:** Ninguna

**Shortcut:** ✅ Siempre

---

### **4. CANCEL_APPOINTMENT** ❌
**Descripción:** Usuario quiere cancelar un turno

**Ejemplos:**
```
✅ "cancelar turno"
✅ "quiero anular mi cita"
✅ "no puedo ir mañana"
```

**Entidades asociadas:** Ninguna (se maneja con menú posterior)

**Shortcut:** ✅ Si solo tiene 1 cita

---

### **5. INFO_CENTER** ℹ️
**Descripción:** Usuario quiere información del centro

**Ejemplos:**
```
✅ "información del centro"
✅ "dónde están ubicados"
✅ "horarios de atención"
```

**Entidades asociadas:** Ninguna

**Shortcut:** ✅ Siempre

---

### **6. GREETING** 👋
**Descripción:** Saludo simple sin intención clara

**Ejemplos:**
```
✅ "hola"
✅ "buenos días"
✅ "hey"
```

**Entidades asociadas:** Ninguna

**Shortcut:** ❌ Muestra menú principal

---

### **7. UNKNOWN** ❓
**Descripción:** No se pudo detectar intención

**Ejemplos:**
```
❓ "asdfasdf"
❓ "???"
```

**Acción:** Mostrar menú o pedir clarificación

---

## 🔍 EXTRACCIÓN DE ENTIDADES

### **Proceso de Extracción**

El sistema extrae entidades en **dos pasadas**:

1. **Extracción General** (`_extract_all_entities`): Siempre se ejecuta
2. **Extracción Específica** (`_extract_entities`): Solo para ciertos intents

### **Entidades Detectables**

#### **1. FECHA** 📅

**Método:** Regex + keywords

```python
def _extract_fecha(self, message: str) -> Optional[str]:
    """
    Detecta fechas en formato:
    - Relativo: hoy, mañana, pasado mañana
    - Absoluto: 15/12, 15/12/24
    """
    
    # Fechas relativas
    if 'hoy' in message:
        return 'hoy'
    if 'mañana' in message or 'manana' in message:
        return 'mañana'
    if 'pasado mañana' in message:
        return 'pasado_mañana'
    
    # Fechas absolutas (DD/MM o DD/MM/YY)
    date_pattern = r'\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b'
    match = re.search(date_pattern, message)
    if match:
        day, month, year = match.groups()
        # Normalizar a formato DD/MM/YYYY
        return f"{day.zfill(2)}/{month.zfill(2)}"
```

**Ejemplos:**
```
"necesito turno hoy" → fecha: "hoy"
"para mañana" → fecha: "mañana"
"el 15/12" → fecha: "15/12"
```

---

#### **2. HORARIO** ⏰

**Método:** Keyword matching

```python
self.horarios = {
    'mañana': ['por la mañana', 'en la mañana', 'temprano', 'am'],
    'tarde': ['tarde', 'por la tarde', 'después del mediodía', 'pm'],
    'noche': ['noche', 'por la noche', 'nocturno', 'después de las 6']
}
```

**Ejemplos:**
```
"por la mañana" → horario: "mañana"
"tarde" → horario: "tarde"
"después de las 6" → horario: "noche"
```

---

#### **3. ESPECIALIDAD** 🩺

**Método:** Keyword + stemming manual

```python
self.especialidades = {
    'psicología': [
        'psicólogo', 'psicóloga', 'psicologo', 'psicologa',
        'psicología', 'terapeuta', 'terapia psicológica', 'psico'
    ],
    'nutrición': [
        'nutricionista', 'nutri', 'nutrición', 'dietista'
    ],
    'kinesiología': [
        'kinesiólogo', 'kinesióloga', 'kine', 'fisioterapia'
    ]
}
```

**Ejemplos:**
```
"necesito psicólogo" → especialidad: "psicología"
"busco nutri" → especialidad: "nutrición"
"quiero kine" → especialidad: "kinesiología"
```

---

#### **4. ZONA** 🗺️

**Método:** Keyword matching

```python
self.zonas = {
    'norte': ['palermo', 'belgrano', 'nuñez', 'zona norte'],
    'sur': ['barracas', 'pompeya', 'zona sur'],
    'centro': ['centro', 'microcentro', 'retiro'],
    'online': ['online', 'virtual', 'videollamada', 'zoom']
}
```

**Ejemplos:**
```
"en palermo" → zona: "norte"
"zona sur" → zona: "sur"
"por zoom" → zona: "online"
```

---

#### **5. GÉNERO** 👤

**Método:** Keyword matching

```python
self.generos = {
    'femenino': ['mujer', 'femenino', 'doctora', 'dra', 'licenciada'],
    'masculino': ['hombre', 'masculino', 'doctor', 'dr', 'licenciado']
}
```

**Ejemplos:**
```
"necesito doctora mujer" → genero: "femenino"
"con un dr hombre" → genero: "masculino"
```

---

#### **6. PREPAGA** 💳

**Método:** Keyword matching

```python
self.prepaga_keywords = [
    'prepaga', 'obra social', 'osde', 'swiss medical',
    'galeno', 'que acepte', 'acepta prepaga'
]
```

**Ejemplos:**
```
"que acepte OSDE" → prepaga: true
"con obra social" → prepaga: true
```

---

#### **7. PROFESSIONAL_NAME** 👨‍⚕️

**Método:** Regex con filtrado de stopwords

```python
def _extract_professional_name(self, message: str) -> Optional[str]:
    """
    Detecta nombres de profesionales en patrones como:
    - "con Dr. Juan Pérez"
    - "turno con María González"
    
    Limitaciones:
    - Solo extrae 2 palabras (nombre + apellido)
    - Filtra stopwords para evitar falsos positivos
    """
    
    # Patrón: "con [título opcional] [Nombre] [Apellido]"
    con_pattern = r'con\s+(?:dr\.?|dra\.?|lic\.?)?\s*([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?)'
    
    match = re.search(con_pattern, message, re.IGNORECASE)
    if match:
        name = match.group(1).strip()
        return name.lower()
```

**Ejemplos:**
```
"turno con Dr. Juan Pérez" → professional_name: "juan pérez"
"con María González" → professional_name: "maría gonzález"
```

---

### **Acumulación de Entidades (Multi-turno)**

El sistema **acumula entidades** a través de múltiples mensajes:

```python
# src/core/conversation_context.py

class ConversationContext:
    """Contexto acumulativo de conversación."""
    
    def update_entities(self, new_entities: Dict, merge: bool = True):
        """
        Combina entidades nuevas con las existentes.
        
        Ejemplo:
        Turno 1: "necesito psicólogo" → {especialidad: psicología}
        Turno 2: "mañana por la tarde" → {fecha: mañana, horario: tarde}
        Resultado: {especialidad: psicología, fecha: mañana, horario: tarde}
        """
        if merge:
            self.accumulated_entities.update(new_entities)
        else:
            self.accumulated_entities = new_entities.copy()
```

**Ejemplo de conversación:**

```
👤 Usuario: "hola, necesito psicólogo"
🤖 Bot: [Detecta especialidad: psicología]
       "¿Para qué fecha necesitas el turno?"

👤 Usuario: "mañana"
🤖 Bot: [Acumula fecha: mañana]
       [Tiene especialidad + fecha]
       "¿Qué horario preferís? (mañana/tarde/noche)"

👤 Usuario: "tarde"
🤖 Bot: [Acumula horario: tarde]
       [Ejecuta búsqueda con: psicología + mañana + tarde]
```

---

## 🔌 INTEGRACIÓN CON BOT CONTROLLER

### **Flujo de Procesamiento**

```python
# src/bot/bot_controller.py

def process_message(self, phone_number: str, message: str) -> str:
    """
    Punto de entrada principal del bot.
    
    FLUJO:
    1. Identificar usuario (profesional/cliente/nuevo)
    2. Obtener sesión y contexto
    3. ⭐ DETECTAR INTENCIÓN (intent_detector)
    4. Intentar shortcut o seguir flujo normal
    5. Delegar a handlers específicos
    """
    
    # ... código de identificación ...
    
    # ==========================================
    # DETECCIÓN DE INTENCIÓN (NLU)
    # ==========================================
    
    nlu_enabled_states = [
        ConversationState.START,
        ConversationState.CLIENT_MAIN_MENU,
        ConversationState.CLIENT_MULTIFILTER_MENU,
        ConversationState.CLIENT_SHOW_RESULTS,
        ConversationState.CLIENT_FILTER_INPUT,
    ]
    
    if session.state in nlu_enabled_states:
        # Detectar intent y entidades
        intent_result = intent_detector.detect(message, context={
            'role': session.role,
            'state': session.state,
            'user_info': user_info,
            'conversation_history': conv_context.get_history_text()
        })
        
        print(f"[NLU] Intent: {intent_result['intent'].value}")
        print(f"[NLU] Confidence: {intent_result['confidence']:.2f}")
        print(f"[NLU] Entities: {intent_result['entities']}")
        
        # Acumular entidades en contexto
        if intent_result['entities']:
            conv_context.update_entities(intent_result['entities'], merge=True)
        
        # Intentar shortcut
        if intent_result['confidence'] >= 0.7:
            shortcut_response = self._try_intent_shortcut(
                session, intent_result, user_info
            )
            if shortcut_response:
                return shortcut_response
```

### **Lógica de Shortcuts**

```python
def _try_intent_shortcut(
    self, 
    session: SessionData, 
    intent_result: Dict, 
    user_info: Dict
) -> Optional[str]:
    """
    Intenta hacer shortcut basado en el intent detectado.
    
    Returns:
        Respuesta del bot si hace shortcut, None si debe seguir flujo normal
    """
    intent = intent_result['intent']
    
    # Ver mis citas → Ir directo a mostrar citas
    if intent == Intent.VIEW_MY_APPOINTMENTS:
        session.transition_to(ConversationState.CLIENT_VIEW_APPOINTMENTS)
        return self.client_handler.handle_client_view_appointments(session, "")
    
    # Cancelar → Ir a flujo de cancelación
    elif intent == Intent.CANCEL_APPOINTMENT:
        return self._handle_cancel_appointment(session, user_info)
    
    # Ver mañana → Buscar con fecha=mañana
    elif intent == Intent.VIEW_TOMORROW:
        accumulated = {'fecha': 'mañana'}
        accumulated.update(intent_result['entities'])
        return self._execute_smart_search(session, accumulated)
    
    # Buscar profesional → Si tiene entidades suficientes, buscar
    elif intent == Intent.SEARCH_PROFESSIONAL:
        if self._can_execute_search(intent_result['entities']):
            return self._execute_smart_search(session, intent_result['entities'])
        else:
            # Pedir entidades faltantes
            missing = self._get_missing_required_entities(intent_result['entities'])
            return self._ask_for_missing_entity(session, intent_result['entities'], missing)
    
    return None
```

### **Decisión de Ejecutar Búsqueda**

```python
def _can_execute_search(self, entities: Dict) -> bool:
    """
    Decide si hay suficientes entidades para ejecutar búsqueda.
    
    Criterio: Al menos debe tener 'fecha'
    """
    return 'fecha' in entities
```

### **Pedir Entidades Faltantes**

```python
def _ask_for_missing_entity(
    self, 
    session: SessionData, 
    entities: Dict, 
    missing: List[str]
) -> str:
    """
    Pregunta por la siguiente entidad faltante.
    
    Orden de prioridad:
    1. fecha (CRÍTICO)
    2. horario (RECOMENDADO)
    3. especialidad (OPCIONAL)
    """
    next_missing = missing[0] if missing else None
    
    if next_missing == 'fecha':
        return "¿Para qué fecha necesitas el turno?\nEj: 'hoy', 'mañana', 'DD/MM'"
    
    elif next_missing == 'horario':
        return "¿En qué horario preferís?\nEj: 'mañana', 'tarde', 'noche'"
    
    elif next_missing == 'especialidad':
        return "¿Qué especialidad buscás?\nEj: 'psicología', 'nutrición'"
```

---

## ⚠️ LIMITACIONES ACTUALES

### **1. Sinónimos No Cubiertos**

**Problema:**
```python
# ✅ Detecta
"necesito psicólogo" → ✅ especialidad: psicología

# ❌ NO detecta
"quiero terapeuta cognitivo conductual" → ❌ No reconoce TCC
"busco psi" → ❌ Abreviatura no conocida
"atención psicológica" → ❌ Sinónimo no incluido
```

**Impacto:** Usuario debe reformular o usar palabras específicas

---

### **2. Typos y Variaciones Ortográficas**

**Problema:**
```python
# ✅ Detecta
"mañana" → ✅ fecha: mañana

# ❌ NO detecta
"manana" → ✅ fecha: mañana (cubierto con/sin tilde)
"mañanna" → ❌ Typo no reconocido
"mañna" → ❌ Abreviación no reconocida
```

**Impacto:** Requiere escritura exacta o variantes pre-programadas

---

### **3. Frases Complejas**

**Problema:**
```python
# ✅ Detecta
"necesito psicólogo mañana" → ✅ Funciona bien

# ❌ NO detecta correctamente
"estoy buscando un profesional de la salud mental, 
 preferentemente especializado en terapia cognitiva conductual, 
 que tenga disponibilidad para la semana que viene"
→ ❌ Puede perderse información
```

**Impacto:** Mensajes largos o elaborados pueden confundir al sistema

---

### **4. Contexto Implícito**

**Problema:**
```python
# Usuario anterior: "necesito psicólogo"
# Bot: "¿Para qué fecha?"

# ✅ Detecta
Usuario: "mañana" → ✅ fecha: mañana

# ❌ NO detecta contexto complejo
Usuario: "ah, mejor el día después" 
→ ❌ No sabe que "día después" = pasado mañana
```

**Impacto:** Requiere frases directas, no infiere significado contextual

---

### **5. Ambigüedad**

**Problema:**
```python
"necesito turno con María"
→ ¿Es nombre de profesional o nombre del paciente?

"para mi hijo mañana"
→ ¿fecha: mañana? ¿booking_for: other?
```

**Impacto:** Puede malinterpretar en casos ambiguos

---

### **6. Múltiples Intents en Un Mensaje**

**Problema:**
```python
"hola, quiero ver mis turnos y también agendar uno nuevo para mañana"
→ Solo detecta el PRIMER intent (VIEW_MY_APPOINTMENTS)
→ Pierde el segundo (SEARCH_PROFESSIONAL)
```

**Impacto:** Usuario debe dividir en mensajes separados

---

### **7. Negaciones**

**Problema:**
```python
"NO quiero cancelar" → Detecta CANCEL_APPOINTMENT ❌
"no tengo prepaga" → Detecta prepaga: true ❌
```

**Impacto:** No maneja negaciones, puede generar resultados incorrectos

---

### **8. Confianza Artificial**

**Problema:**
```python
# Confianza actual es HEURÍSTICA, no probabilística

confidence = 0.9  # ¿Por qué 0.9? Arbitrario
```

**Impacto:** No refleja la verdadera probabilidad de estar correcto

---

### **9. No Aprende con el Uso**

**Problema:**
- Si 100 usuarios escriben "psi" para psicólogo, el sistema NO aprende
- Requiere actualización manual del código

**Impacto:** No mejora con feedback de usuarios

---

### **10. Mantenimiento Manual**

**Problema:**
```python
# Para agregar nueva especialidad:
# 1. Abrir intent_detector.py
# 2. Editar self.especialidades
# 3. Hacer commit
# 4. Deploy

self.especialidades = {
    # ... 50 líneas de keywords ...
}
```

**Impacto:** Escalabilidad limitada

---

## 🚀 ROADMAP: MIGRACIÓN A ML

### **Objetivo:** Sistema Híbrido (ML + Reglas como Fallback)

```
┌─────────────────────────────────────────────────────┐
│                SISTEMA HÍBRIDO v4.0                  │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────┐
        │   1. Intent Detection (ML)     │
        │   Confidence: 0.0 - 1.0        │
        └────────────────┬───────────────┘
                         │
                    ┌────▼────┐
                    │ >= 0.7? │
                    └────┬────┘
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
         ✅ YES                  ❌ NO
         Use ML                 Fallback to Rules
              │                     │
              ▼                     ▼
        ┌─────────────┐      ┌─────────────┐
        │ ML Entities │      │ Rule-based  │
        │ Extraction  │      │ Detection   │
        └─────────────┘      └─────────────┘
              │                     │
              └──────────┬──────────┘
                         ▼
                   Execute Action
```

---

## 📊 PLAN DE IMPLEMENTACIÓN

### **FASE 1: RECOPILACIÓN DE DATOS** (4-6 semanas)

#### **Objetivos:**
- ✅ Recopilar 1000+ conversaciones reales
- ✅ Etiquetar intenciones manualmente
- ✅ Identificar entidades en cada mensaje

#### **Tareas:**

1. **Implementar Logging de Conversaciones**
```python
# src/services/conversation_logger.py

class ConversationLogger:
    """
    Logger para recopilar datos de entrenamiento.
    """
    
    def log_message(
        self, 
        phone: str, 
        message: str,
        detected_intent: str,
        detected_entities: Dict,
        user_feedback: Optional[str] = None
    ):
        """
        Guarda cada mensaje procesado para posterior etiquetado.
        """
        pass
```

2. **Herramienta de Etiquetado**
```python
# scripts/label_conversations.py

"""
Interfaz CLI para etiquetar conversaciones manualmente.

Uso:
    python scripts/label_conversations.py
"""
```

3. **Formato de Dataset**
```json
{
  "conversations": [
    {
      "id": "conv_001",
      "messages": [
        {
          "text": "necesito psicólogo mañana",
          "intent": "search_professional",
          "entities": {
            "especialidad": "psicología",
            "fecha": "mañana"
          },
          "confidence": 1.0,
          "labeled_by": "human"
        }
      ]
    }
  ]
}
```

**Entregables:**
- [ ] `dataset/training_data.json` (800 ejemplos)
- [ ] `dataset/validation_data.json` (200 ejemplos)
- [ ] Script de etiquetado funcional

---

### **FASE 2: SETUP DE ML** (2 semanas)

#### **Decisión de Tecnología**

**Opción A: spaCy (Recomendado para empezar)**
```python
# Ventajas:
✅ Liviano (30MB modelo español)
✅ Rápido en CPU
✅ Fácil de entrenar
✅ Buena documentación

# Desventajas:
❌ Menos potente que transformers
❌ Requiere más datos de entrenamiento
```

**Opción B: Transformers (Futuro)**
```python
# Ventajas:
✅ Muy potente
✅ Estado del arte en NLP
✅ Menos datos de entrenamiento

# Desventajas:
❌ Requiere GPU
❌ Modelo grande (400MB+)
❌ Más lento en inferencia
```

**Decisión Inicial:** **spaCy** → Si funciona mal, migrar a **Transformers**

#### **Tareas:**

1. **Crear Módulo ML**
```
src/ml/
├── __init__.py
├── ml_intent_detector.py      # Detector con ML
├── entity_extractor.py        # NER con ML
├── model_trainer.py           # Entrenamiento
├── model_evaluator.py         # Evaluación
└── models/                    # Modelos entrenados
    ├── intent_classifier.pkl
    └── entity_model.pkl
```

2. **Dependencias**
```txt
# requirements-ml.txt
spacy>=3.7.0
es-core-news-sm>=3.7.0
scikit-learn>=1.3.0
joblib>=1.3.0
```

3. **Implementar ML Intent Detector**
```python
# src/ml/ml_intent_detector.py

from typing import Dict, Optional
import spacy
import joblib
from src.services.intent_detector import Intent

class MLIntentDetector:
    """
    Detector de intenciones usando Machine Learning.
    
    API compatible con IntentDetector basado en reglas.
    """
    
    def __init__(self, model_path: str = "src/ml/models/intent_classifier.pkl"):
        """Cargar modelo entrenado."""
        self.model = joblib.load(model_path)
        self.nlp = spacy.load("es_core_news_sm")
    
    def detect(self, message: str, context: Optional[Dict] = None) -> Dict:
        """
        Detecta intención usando ML.
        
        Returns:
            {
                'intent': Intent,
                'confidence': float,
                'entities': Dict,
                'can_shortcut': bool
            }
        """
        # Vectorizar mensaje
        doc = self.nlp(message)
        features = self._extract_features(doc)
        
        # Predecir intención (con probabilidades reales)
        intent_probs = self.model.predict_proba([features])[0]
        intent_idx = intent_probs.argmax()
        confidence = float(intent_probs[intent_idx])
        
        # Extraer entidades (usando NER de spaCy)
        entities = self._extract_entities(doc)
        
        # Convertir a Intent enum
        intent = self._idx_to_intent(intent_idx)
        
        return {
            'intent': intent,
            'confidence': confidence,
            'entities': entities,
            'can_shortcut': self._can_shortcut(intent, entities, confidence)
        }
    
    def _extract_features(self, doc) -> list:
        """Extrae features para el clasificador."""
        # TF-IDF + características adicionales
        pass
    
    def _extract_entities(self, doc) -> Dict:
        """Extrae entidades usando NER."""
        entities = {}
        
        # Usar NER de spaCy + reglas custom
        for ent in doc.ents:
            if ent.label_ == "DATE":
                entities['fecha'] = self._normalize_date(ent.text)
            elif ent.label_ == "TIME":
                entities['horario'] = self._normalize_time(ent.text)
        
        # Combinar con reglas para entidades específicas del dominio
        # (especialidad, zona, etc.)
        
        return entities
```

**Entregables:**
- [ ] Módulo `src/ml/` implementado
- [ ] Tests unitarios para ML detector
- [ ] Documentación de API

---

### **FASE 3: ENTRENAMIENTO** (2 semanas)

#### **Tareas:**

1. **Script de Entrenamiento**
```python
# scripts/train_intent_model.py

"""
Entrena modelo de clasificación de intenciones.

Uso:
    python scripts/train_intent_model.py \
        --data dataset/training_data.json \
        --output src/ml/models/intent_classifier.pkl
"""

import argparse
import json
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
import joblib

def train_model(data_path: str, output_path: str):
    # 1. Cargar datos
    with open(data_path) as f:
        data = json.load(f)
    
    # 2. Preparar X, y
    texts = []
    intents = []
    for conv in data['conversations']:
        for msg in conv['messages']:
            texts.append(msg['text'])
            intents.append(msg['intent'])
    
    # 3. Split train/val
    X_train, X_val, y_train, y_val = train_test_split(
        texts, intents, test_size=0.2, random_state=42
    )
    
    # 4. Vectorizar
    vectorizer = TfidfVectorizer(max_features=500, ngram_range=(1, 2))
    X_train_vec = vectorizer.fit_transform(X_train)
    X_val_vec = vectorizer.transform(X_val)
    
    # 5. Entrenar
    model = RandomForestClassifier(n_estimators=100)
    model.fit(X_train_vec, y_train)
    
    # 6. Evaluar
    val_accuracy = model.score(X_val_vec, y_val)
    print(f"Validation Accuracy: {val_accuracy:.2f}")
    
    # 7. Guardar
    joblib.dump(model, output_path)
    joblib.dump(vectorizer, output_path.replace('.pkl', '_vectorizer.pkl'))
```

2. **Evaluación**
```python
# src/ml/model_evaluator.py

class ModelEvaluator:
    """Evalúa performance del modelo."""
    
    def evaluate(self, test_data_path: str) -> Dict:
        """
        Métricas:
        - Accuracy general
        - Precision/Recall/F1 por intent
        - Matriz de confusión
        - Confianza promedio
        """
        pass
    
    def compare_with_rules(self, test_data_path: str) -> Dict:
        """
        Compara ML vs reglas en mismo dataset.
        
        Útil para decidir si vale la pena ML.
        """
        pass
```

3. **Métricas Objetivo**
```
Accuracy general:     > 85%
Precision (promedio): > 80%
Recall (promedio):    > 80%
F1-score (promedio):  > 80%

Intents críticos (search, view_appointments):
- Precision: > 90%
- Recall:    > 90%
```

**Entregables:**
- [ ] Modelo entrenado (`intent_classifier.pkl`)
- [ ] Reporte de evaluación
- [ ] Comparativa ML vs Reglas

---

### **FASE 4: INTEGRACIÓN HÍBRIDA** (1 semana)

#### **Tareas:**

1. **Implementar Detector Híbrido**
```python
# src/ml/hybrid_intent_detector.py

class HybridIntentDetector:
    """
    Detector híbrido: ML como primario, reglas como fallback.
    
    Estrategia:
    1. Intentar con ML
    2. Si confianza < umbral (0.7) → usar reglas
    3. Logging de cuál método se usó (para analytics)
    """
    
    def __init__(self, confidence_threshold: float = 0.7):
        self.ml_detector = MLIntentDetector()
        self.rule_detector = IntentDetector()  # Sistema actual
        self.threshold = confidence_threshold
    
    def detect(self, message: str, context: Optional[Dict] = None) -> Dict:
        # Intentar ML primero
        ml_result = self.ml_detector.detect(message, context)
        
        # Si alta confianza, usar ML
        if ml_result['confidence'] >= self.threshold:
            ml_result['method_used'] = 'ml'
            return ml_result
        
        # Fallback a reglas
        print(f"[HYBRID] Baja confianza ML ({ml_result['confidence']:.2f}), usando reglas")
        rule_result = self.rule_detector.detect(message, context)
        rule_result['method_used'] = 'rules'
        rule_result['ml_confidence'] = ml_result['confidence']  # Para logging
        
        return rule_result
```

2. **Feature Flag**
```python
# src/config/filter_config.py

class FeatureFlags:
    # ... otros flags ...
    
    # Intent Detection
    USE_ML_INTENT_DETECTOR = False      # True para activar ML
    USE_HYBRID_DETECTOR = True          # True para híbrido
    ML_CONFIDENCE_THRESHOLD = 0.7       # Umbral para fallback
```

3. **Integración en Bot Controller**
```python
# src/bot/bot_controller.py

# Al inicio del archivo
if FeatureFlags.USE_ML_INTENT_DETECTOR:
    from src.ml.ml_intent_detector import ml_intent_detector as intent_detector
elif FeatureFlags.USE_HYBRID_DETECTOR:
    from src.ml.hybrid_intent_detector import hybrid_intent_detector as intent_detector
else:
    from src.services.intent_detector import intent_detector

# El resto del código NO cambia (API compatible)
```

4. **Monitoreo**
```python
# src/services/intent_analytics.py

class IntentAnalytics:
    """
    Analytics del sistema de intención.
    
    Métricas:
    - % de veces que se usó ML vs reglas
    - Confianza promedio de ML
    - % de shortcuts exitosos
    - Falsos positivos/negativos (basado en feedback de usuario)
    """
    
    def log_detection(
        self, 
        message: str,
        detected_intent: str,
        confidence: float,
        method_used: str,  # 'ml' o 'rules'
        user_feedback: Optional[str] = None
    ):
        """Registra cada detección para análisis."""
        pass
```

**Entregables:**
- [ ] Detector híbrido funcional
- [ ] Feature flags configurados
- [ ] Sistema de monitoreo implementado
- [ ] Testing A/B (ML vs Reglas)

---

### **FASE 5: MONITOREO Y MEJORA CONTINUA** (Continuo)

#### **Tareas:**

1. **Dashboard de Métricas**
```python
# scripts/generate_intent_report.py

"""
Genera reporte HTML con métricas de intent detection.

Incluye:
- Accuracy ML vs Reglas
- Distribución de intents
- Confianza promedio
- % de fallbacks
- Casos fallidos (para reentrenamiento)
"""
```

2. **Reentrenamiento Periódico**
```python
# scripts/retrain_model.py

"""
Reentrena modelo con nuevos datos etiquetados.

Ejecutar mensualmente o cuando haya +500 nuevos ejemplos.
"""
```

3. **Incorporar Feedback**
```python
# Cuando usuario corrige una detección
if user_says_wrong_intent:
    # Marcar para reentrenamiento
    conversation_logger.mark_for_retraining(
        message=message,
        detected_intent=detected_intent,
        correct_intent=user_corrected_intent
    )
```

**Entregables:**
- [ ] Dashboard de métricas (HTML)
- [ ] Pipeline de reentrenamiento
- [ ] Proceso de incorporación de feedback

---

## 📊 COMPARATIVA: REGLAS VS ML

### **Sistema Basado en Reglas (ACTUAL)**

| Criterio | Rating | Notas |
|----------|--------|-------|
| **Accuracy** | ⭐⭐⭐⭐ (80-85%) | Bueno para casos conocidos |
| **Velocidad** | ⭐⭐⭐⭐⭐ (< 1ms) | Extremadamente rápido |
| **Recursos** | ⭐⭐⭐⭐⭐ | No requiere GPU ni memoria |
| **Mantenimiento** | ⭐⭐ | Requiere actualización manual |
| **Escalabilidad** | ⭐⭐ | Difícil agregar nuevos patrones |
| **Robustez a typos** | ⭐⭐ | Falla con variaciones no previstas |
| **Aprendizaje** | ⭐ | No aprende de errores |
| **Confianza real** | ⭐⭐ | Scoring heurístico, no probabilístico |

**Total:** ⭐⭐⭐ (65/100)

---

### **Sistema ML (FUTURO)**

| Criterio | Rating | Notas |
|----------|--------|-------|
| **Accuracy** | ⭐⭐⭐⭐⭐ (90-95%) | Mejor generalización |
| **Velocidad** | ⭐⭐⭐⭐ (5-20ms) | Rápido en CPU con spaCy |
| **Recursos** | ⭐⭐⭐ | Requiere más memoria (30MB+ modelo) |
| **Mantenimiento** | ⭐⭐⭐⭐ | Se actualiza con datos, no código |
| **Escalabilidad** | ⭐⭐⭐⭐⭐ | Fácil agregar nuevos ejemplos |
| **Robustez a typos** | ⭐⭐⭐⭐ | Maneja variaciones mejor |
| **Aprendizaje** | ⭐⭐⭐⭐⭐ | Mejora con reentrenamiento |
| **Confianza real** | ⭐⭐⭐⭐⭐ | Probabilidades reales |

**Total:** ⭐⭐⭐⭐ (85/100)

---

### **Sistema Híbrido (RECOMENDADO)**

| Criterio | Rating | Notas |
|----------|--------|-------|
| **Accuracy** | ⭐⭐⭐⭐⭐ (92-97%) | Lo mejor de ambos mundos |
| **Velocidad** | ⭐⭐⭐⭐ (5-20ms ML, 1ms reglas) | Rápido, con fallback |
| **Recursos** | ⭐⭐⭐ | Similar a solo ML |
| **Mantenimiento** | ⭐⭐⭐⭐ | Datos + reglas críticas |
| **Escalabilidad** | ⭐⭐⭐⭐⭐ | Máxima flexibilidad |
| **Robustez a typos** | ⭐⭐⭐⭐⭐ | ML maneja variaciones, reglas casos críticos |
| **Aprendizaje** | ⭐⭐⭐⭐⭐ | Mejora continua con ML |
| **Confianza real** | ⭐⭐⭐⭐⭐ | Probabilidades + heurística |

**Total:** ⭐⭐⭐⭐⭐ (95/100)

---

## 🎯 RECOMENDACIÓN FINAL

### **Estrategia Recomendada: Enfoque Incremental**

```
┌─────────────────────────────────────────────────────┐
│ FASE 1 (Actual): Solo Reglas                        │
│ ✅ Funciona bien (80-85% accuracy)                  │
│ ✅ Rápido y simple                                   │
│ ⏱️  Duración: Hasta recopilar datos (2-3 meses)     │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│ FASE 2: Recopilación de Datos                       │
│ 📊 Logging de conversaciones                        │
│ 🏷️  Etiquetado manual (1000+ ejemplos)              │
│ ⏱️  Duración: 4-6 semanas                            │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│ FASE 3: Experimento ML (spaCy)                      │
│ 🧪 Entrenar modelo inicial                          │
│ 📈 Evaluar performance vs reglas                    │
│ ⏱️  Duración: 2 semanas                              │
└─────────────────────────────────────────────────────┘
                         │
                    ┌────▼────┐
                    │ ¿Mejor? │
                    └────┬────┘
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
         ✅ SÍ                   ❌ NO
    (ML > 85% accuracy)     (ML <= 85%)
              │                     │
              ▼                     ▼
┌─────────────────────┐   ┌─────────────────────┐
│ FASE 4: Híbrido     │   │ Seguir con Reglas   │
│ ML + Reglas         │   │ Mejorar keywords    │
│ Fallback en 0.7     │   │ Revisar approach    │
└─────────────────────┘   └─────────────────────┘
              │                     
              ▼                     
┌─────────────────────────────────────────────────────┐
│ FASE 5: Monitoreo y Mejora Continua                 │
│ 📊 Dashboard de métricas                            │
│ 🔄 Reentrenamiento mensual                          │
│ 📈 Incorporar feedback de usuarios                  │
└─────────────────────────────────────────────────────┘
```

### **Hitos Clave**

- **Semana 1-4:** Implementar logging de conversaciones
- **Semana 5-10:** Recopilar y etiquetar 1000+ ejemplos
- **Semana 11-12:** Entrenar primer modelo spaCy
- **Semana 13:** Evaluar y comparar con reglas
- **Semana 14-15:** Implementar híbrido si ML > 85%
- **Semana 16+:** Monitoreo y mejora continua

### **Criterio de Éxito**

```python
# Migrar a ML/Híbrido solo si:
ml_accuracy > 0.85 AND
ml_accuracy > rules_accuracy + 0.05 AND  # Mejora de al menos 5%
ml_inference_time < 100ms  # Latencia aceptable
```

---

## 📚 RECURSOS Y DOCUMENTACIÓN

### **Código Actual**

- `src/services/intent_detector.py`: Detector basado en reglas
- `src/core/conversation_context.py`: Contexto acumulativo
- `src/bot/bot_controller.py`: Integración con bot

### **Próximos Módulos**

- `src/ml/ml_intent_detector.py`: Detector con ML (pendiente)
- `src/ml/hybrid_intent_detector.py`: Detector híbrido (pendiente)
- `scripts/train_intent_model.py`: Entrenamiento (pendiente)
- `scripts/label_conversations.py`: Etiquetado (pendiente)

### **Dependencias Futuras**

```txt
# requirements-ml.txt
spacy>=3.7.0
es-core-news-sm>=3.7.0
scikit-learn>=1.3.0
joblib>=1.3.0
```

### **Referencias**

- [spaCy Documentation](https://spacy.io/usage/training)
- [Intent Classification Guide](https://rasa.com/docs/rasa/nlu-training-data/)
- [NER with spaCy](https://spacy.io/usage/linguistic-features#named-entities)

---

## 📞 CONTACTO Y SOPORTE

Para preguntas sobre la implementación:
- Revisar este documento
- Consultar código en `src/services/intent_detector.py`
- Revisar tests en `tests/test_intent_detector.py` (cuando existan)

---

**Última actualización:** 4 de Febrero, 2026  
**Próxima revisión:** Al completar Fase 2 (Recopilación de datos)
