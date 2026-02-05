# 🧪 GUÍA DE TESTING Y MANEJO DE DATOS DE CONVERSACIONES
## Comandos, Exportación y Formato de Datos

**Última actualización:** 5 de Febrero, 2026  
**Versión:** 1.0

---

## 📋 ÍNDICE

1. [Comandos de Testing](#comandos-de-testing)
2. [Exportación de Datos](#exportación-de-datos)
3. [Formato de Datos](#formato-de-datos)
4. [Análisis de Datos](#análisis-de-datos)
5. [Troubleshooting](#troubleshooting)
6. [Referencia Rápida](#referencia-rápida)

---

## 🧪 COMANDOS DE TESTING

### **Test 1: Verificar que el Logger Está Funcionando**

#### **Opción A: Script de Test (Recomendado)**

```powershell
# 1. Copiar el script al contenedor
docker cp test_logger.py whatsapp-demo:/app/scripts/

# 2. Ejecutar
docker exec whatsapp-demo python scripts/test_logger.py
```

**Salida esperada:**
```
🧪 Probando conversation_logger...
[CONV_LOG] Guardado: intent=search_professional, conf=0.90, entities=['especialidad']
✅ Mensaje guardado

📊 Estadísticas:
   Total mensajes: 1
   Por intent: {'search_professional': 1}
   Confianza promedio: 0.90

✅ Test completado!
```

#### **Opción B: Comando Directo (Una línea)**

```powershell
docker exec whatsapp-demo python -c "from src.services.conversation_logger import conversation_logger; conversation_logger.log_message(phone='+5491112345678', message='test', detected_intent='search_professional', detected_entities={'especialidad': 'psicología'}, confidence=0.9, shortcut_used=False, session_state='CLIENT_MAIN_MENU'); print('✅ OK')"
```

#### **Opción C: Desde Bash Interactivo**

```powershell
# Entrar al contenedor
docker exec -it whatsapp-demo bash

# Dentro del contenedor:
python << 'EOF'
from src.services.conversation_logger import conversation_logger

conversation_logger.log_message(
    phone='+5491112345678',
    message='test desde bash',
    detected_intent='search_professional',
    detected_entities={'especialidad': 'psicología', 'fecha': 'mañana'},
    confidence=0.95,
    shortcut_used=True,
    session_state='CLIENT_MAIN_MENU',
    user_role='client'
)
print('✅ Test OK')
EOF

# Salir
exit
```

---

### **Test 2: Verificar que los Archivos se Crean**

```powershell
# Listar archivos en el directorio de conversaciones
docker exec whatsapp-demo ls -lh /app/data/conversations/

# Debe mostrar:
# README.md
# conversations_YYYY-MM-DD.jsonl
```

**Ejemplo de salida:**
```
total 12K
-rw-r--r-- 1 root root 2.1K Feb  5 14:30 README.md
-rw-r--r-- 1 root root 1.5K Feb  5 14:32 conversations_2026-02-05.jsonl
```

---

### **Test 3: Verificar Persistencia (Sobrevive a Reinicios)**

```powershell
# 1. Crear datos de test
docker exec whatsapp-demo python -c "from src.services.conversation_logger import conversation_logger; conversation_logger.log_message(phone='+5491112345678', message='test persistencia', detected_intent='search_professional', detected_entities={}, confidence=0.9, shortcut_used=False, session_state='CLIENT_MAIN_MENU')"

# 2. Contar archivos ANTES del reinicio
docker exec whatsapp-demo ls -1 /app/data/conversations/*.jsonl | wc -l

# 3. Reiniciar contenedor
docker compose restart

# 4. Verificar que los archivos SIGUEN AHÍ
docker exec whatsapp-demo ls -lh /app/data/conversations/

# 5. Contar archivos DESPUÉS del reinicio (debe ser igual)
docker exec whatsapp-demo ls -1 /app/data/conversations/*.jsonl | wc -l
```

**✅ Si ambos conteos son iguales → Persistencia funciona correctamente**

---

### **Test 4: Ver Estadísticas**

```powershell
# Estadísticas completas
docker exec whatsapp-demo python scripts/review_conversations.py --stats
```

**Salida esperada:**
```
📊 ESTADÍSTICAS DE DATOS RECOPILADOS
================================================================================

📨 Total de mensajes: 15

📅 Mensajes por fecha:
   2026-02-05: 15 mensajes

🎯 Mensajes por intención:
   search_professional        :    8 ( 53.3%)
   greeting                   :    4 ( 26.7%)
   view_my_appointments       :    2 ( 13.3%)
   unknown                    :    1 ( 6.7%)

📊 Distribución de confianza:
   🟢 High     :   12 ( 80.0%)
   🟡 Medium   :    2 ( 13.3%)
   🔴 Low      :    1 ( 6.7%)

⚠️  Mensajes marcados para revisión: 1

💡 RECOMENDACIÓN:
   Recopila más datos. Mínimo recomendado: 500 mensajes
   Te faltan: 485 mensajes
```

---

## 📦 EXPORTACIÓN DE DATOS

### **Método 1: Copiar Archivo Individual (Rápido)**

```powershell
# Crear carpeta de backup
mkdir -p backup

# Copiar archivo de hoy
docker cp whatsapp-demo:/app/data/conversations/conversations_2026-02-05.jsonl ./backup/

# Abrir con tu editor favorito
code ./backup/conversations_2026-02-05.jsonl
# O con notepad
notepad ./backup/conversations_2026-02-05.jsonl
```

---

### **Método 2: Copiar TODO el Directorio**

```powershell
# Copiar todas las conversaciones
docker cp whatsapp-demo:/app/data/conversations ./backup/conversations_$(Get-Date -Format "yyyy-MM-dd")

# Verificar
ls ./backup/conversations_$(Get-Date -Format "yyyy-MM-dd")
```

**Estructura exportada:**
```
backup/
└── conversations_2026-02-05/
    ├── README.md
    ├── conversations_2026-02-01.jsonl
    ├── conversations_2026-02-02.jsonl
    ├── conversations_2026-02-03.jsonl
    ├── conversations_2026-02-04.jsonl
    ├── conversations_2026-02-05.jsonl
    └── needs_review.jsonl
```

---

### **Método 3: Exportar con Fecha Específica**

```powershell
# Exportar conversaciones de una fecha específica
$fecha = "2026-02-01"
docker cp whatsapp-demo:/app/data/conversations/conversations_$fecha.jsonl ./conversations_$fecha.jsonl

# Ver contenido
cat ./conversations_$fecha.jsonl
```

---

### **Método 4: Backup Automatizado (Script PowerShell)**

Crear archivo `backup_conversations.ps1`:

```powershell
# backup_conversations.ps1

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupDir = "backups/$timestamp"

Write-Host "📦 Iniciando backup de conversaciones..." -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null

# Copiar conversaciones
docker cp whatsapp-demo:/app/data/conversations "$backupDir/conversations"
Write-Host "✅ Conversaciones copiadas" -ForegroundColor Green

# Copiar dataset (si existe)
docker cp whatsapp-demo:/app/dataset "$backupDir/dataset" 2>$null
if ($?) {
    Write-Host "✅ Dataset copiado" -ForegroundColor Green
}

# Copiar base de datos
docker cp whatsapp-demo:/app/data/booking.db "$backupDir/booking.db"
Write-Host "✅ Base de datos copiada" -ForegroundColor Green

# Comprimir
Compress-Archive -Path "$backupDir/*" -DestinationPath "$backupDir.zip"
Write-Host "✅ Backup comprimido: $backupDir.zip" -ForegroundColor Green

# Mostrar tamaño
$size = (Get-Item "$backupDir.zip").Length / 1MB
Write-Host "📊 Tamaño del backup: $([math]::Round($size, 2)) MB" -ForegroundColor Yellow

Write-Host "`n💾 Backup completado en: $backupDir.zip" -ForegroundColor Green
```

**Uso:**
```powershell
# Ejecutar backup
.\backup_conversations.ps1

# Resultado:
# backups/20260205_143022.zip
```

---

### **Método 5: Ver Contenido Directamente (Sin Copiar)**

```powershell
# Ver archivo completo
docker exec whatsapp-demo cat /app/data/conversations/conversations_2026-02-05.jsonl

# Ver primeras 5 líneas
docker exec whatsapp-demo head -5 /app/data/conversations/conversations_2026-02-05.jsonl

# Ver últimas 5 líneas
docker exec whatsapp-demo tail -5 /app/data/conversations/conversations_2026-02-05.jsonl

# Contar líneas (= número de mensajes)
docker exec whatsapp-demo wc -l /app/data/conversations/conversations_2026-02-05.jsonl
```

---

### **Método 6: Exportar Formateado (Pretty Print)**

```powershell
# Ver JSON formateado y legible
docker exec whatsapp-demo python -c "import json; [print(json.dumps(json.loads(line), indent=2, ensure_ascii=False)) for line in open('/app/data/conversations/conversations_2026-02-05.jsonl')]"

# Guardar formateado en archivo local
docker exec whatsapp-demo python -c "import json; [print(json.dumps(json.loads(line), indent=2, ensure_ascii=False)) for line in open('/app/data/conversations/conversations_2026-02-05.jsonl')]" > conversations_formatted.json
```

---

## 📊 FORMATO DE DATOS

### **Estructura de Archivo JSONL**

Cada archivo `conversations_YYYY-MM-DD.jsonl` contiene **una línea por mensaje** en formato JSON.

**Extensión:** `.jsonl` (JSON Lines)  
**Formato:** Un objeto JSON por línea (sin comas entre líneas)

```jsonl
{"timestamp": "2026-02-05T14:30:15", "message": "hola", ...}
{"timestamp": "2026-02-05T14:31:22", "message": "necesito turno", ...}
{"timestamp": "2026-02-05T14:32:05", "message": "para mañana", ...}
```

---

### **Schema de Cada Entrada**

```json
{
  // ==========================================
  // METADATOS
  // ==========================================
  "timestamp": "2026-02-05T14:30:15.123456",
  "user_id": "4debb560f3d844b2",
  
  // ==========================================
  // DATOS DEL MENSAJE
  // ==========================================
  "message": "necesito psicólogo mañana por la tarde",
  
  // ==========================================
  // DETECCIÓN AUTOMÁTICA (Sistema de Reglas)
  // ==========================================
  "detected_intent": "search_professional",
  "entities": {
    "especialidad": "psicología",
    "fecha": "mañana",
    "horario": "tarde"
  },
  "confidence": 0.90,
  "shortcut_used": true,
  
  // ==========================================
  // CONTEXTO DE LA CONVERSACIÓN
  // ==========================================
  "session_state": "CLIENT_MAIN_MENU",
  "user_role": "client",
  "context": {
    "has_accumulated_entities": true,
    "conversation_turns": 3
  },
  
  // ==========================================
  // CAMPOS PARA REVISIÓN MANUAL
  // ==========================================
  "human_reviewed": false,
  "is_correct": null,
  "correct_intent": null,
  "correct_entities": null,
  "review_notes": null
}
```

---

### **Diccionario de Campos**

#### **Campos de Identificación**

| Campo | Tipo | Descripción | Ejemplo |
|-------|------|-------------|---------|
| `timestamp` | string (ISO 8601) | Fecha y hora del mensaje | `"2026-02-05T14:30:15.123456"` |
| `user_id` | string (hash) | ID anonimizado del usuario (SHA-256 truncado) | `"4debb560f3d844b2"` |

#### **Campos del Mensaje**

| Campo | Tipo | Descripción | Ejemplo |
|-------|------|-------------|---------|
| `message` | string | Texto original enviado por el usuario | `"necesito psicólogo mañana"` |

#### **Campos de Detección (Sistema Actual)**

| Campo | Tipo | Descripción | Valores Posibles |
|-------|------|-------------|------------------|
| `detected_intent` | string | Intención detectada por el sistema | `search_professional`, `view_my_appointments`, `greeting`, `cancel_appointment`, `view_tomorrow`, `info_center`, `unknown` |
| `entities` | object | Entidades extraídas del mensaje | Ver tabla de entidades abajo |
| `confidence` | float | Nivel de confianza (0.0-1.0) | `0.0` (sin confianza) - `1.0` (máxima confianza) |
| `shortcut_used` | boolean | Si se hizo shortcut (omitió menú) | `true` / `false` |

#### **Entidades Detectables**

| Entidad | Tipo | Descripción | Ejemplos |
|---------|------|-------------|----------|
| `especialidad` | string | Especialidad médica | `"psicología"`, `"nutrición"`, `"kinesiología"` |
| `fecha` | string | Fecha del turno | `"hoy"`, `"mañana"`, `"15/02"` |
| `horario` | string | Franja horaria | `"mañana"`, `"tarde"`, `"noche"` |
| `zona` | string | Zona geográfica | `"norte"`, `"sur"`, `"centro"`, `"online"` |
| `genero` | string | Género del profesional | `"masculino"`, `"femenino"` |
| `prepaga` | boolean | Acepta obra social | `true` / `false` |
| `professional_name` | string | Nombre del profesional | `"juan pérez"`, `"maría gonzález"` |
| `modalidad` | string | Modalidad de atención | `"presencial"`, `"virtual"` |

#### **Campos de Contexto**

| Campo | Tipo | Descripción | Ejemplo |
|-------|------|-------------|---------|
| `session_state` | string | Estado de la conversación | `"CLIENT_MAIN_MENU"`, `"CLIENT_MULTIFILTER_MENU"`, `"CLIENT_SHOW_RESULTS"` |
| `user_role` | string | Rol del usuario | `"client"`, `"professional"`, `null` |
| `context` | object | Información adicional de contexto | `{"has_accumulated_entities": true, "conversation_turns": 3}` |

#### **Campos de Revisión Manual**

| Campo | Tipo | Descripción | Valores |
|-------|------|-------------|---------|
| `human_reviewed` | boolean | Si fue revisado por humano | `true` / `false` |
| `is_correct` | boolean/null | Si la detección fue correcta | `true`, `false`, `null` |
| `correct_intent` | string/null | Intent correcto (si fue corregido) | `"search_professional"` o `null` |
| `correct_entities` | object/null | Entidades corregidas | `{"fecha": "hoy"}` o `null` |
| `review_notes` | string/null | Notas del revisor | `"Usuario usó sinónimo no reconocido"` |

---

### **Ejemplos Completos por Tipo de Mensaje**

#### **Ejemplo 1: Búsqueda Simple**

```json
{
  "timestamp": "2026-02-05T14:30:15.123456",
  "user_id": "4debb560f3d844b2",
  "message": "necesito psicólogo",
  "detected_intent": "search_professional",
  "entities": {
    "especialidad": "psicología"
  },
  "confidence": 0.85,
  "shortcut_used": false,
  "session_state": "CLIENT_MAIN_MENU",
  "user_role": "client",
  "context": {},
  "human_reviewed": false,
  "is_correct": null,
  "correct_intent": null,
  "correct_entities": null,
  "review_notes": null
}
```

#### **Ejemplo 2: Búsqueda con Múltiples Entidades**

```json
{
  "timestamp": "2026-02-05T14:31:22.789012",
  "user_id": "4debb560f3d844b2",
  "message": "necesito psicólogo mañana por la tarde en palermo",
  "detected_intent": "search_professional",
  "entities": {
    "especialidad": "psicología",
    "fecha": "mañana",
    "horario": "tarde",
    "zona": "norte"
  },
  "confidence": 0.95,
  "shortcut_used": true,
  "session_state": "CLIENT_MAIN_MENU",
  "user_role": "client",
  "context": {
    "has_accumulated_entities": false,
    "conversation_turns": 1
  },
  "human_reviewed": false,
  "is_correct": null,
  "correct_intent": null,
  "correct_entities": null,
  "review_notes": null
}
```

#### **Ejemplo 3: Ver Citas**

```json
{
  "timestamp": "2026-02-05T14:35:10.456789",
  "user_id": "a1b2c3d4e5f6g7h8",
  "message": "ver mis turnos",
  "detected_intent": "view_my_appointments",
  "entities": {},
  "confidence": 0.95,
  "shortcut_used": true,
  "session_state": "CLIENT_MAIN_MENU",
  "user_role": "client",
  "context": {},
  "human_reviewed": false,
  "is_correct": null,
  "correct_intent": null,
  "correct_entities": null,
  "review_notes": null
}
```

#### **Ejemplo 4: Saludo Simple**

```json
{
  "timestamp": "2026-02-05T10:00:00.000000",
  "user_id": "xyz123abc456def7",
  "message": "hola",
  "detected_intent": "greeting",
  "entities": {},
  "confidence": 1.0,
  "shortcut_used": false,
  "session_state": "START",
  "user_role": null,
  "context": {},
  "human_reviewed": false,
  "is_correct": null,
  "correct_intent": null,
  "correct_entities": null,
  "review_notes": null
}
```

#### **Ejemplo 5: Intent Desconocido (Baja Confianza)**

```json
{
  "timestamp": "2026-02-05T16:45:30.123456",
  "user_id": "9z8y7x6w5v4u3t2s",
  "message": "quiero algo para el estres",
  "detected_intent": "unknown",
  "entities": {},
  "confidence": 0.0,
  "shortcut_used": false,
  "session_state": "CLIENT_MAIN_MENU",
  "user_role": "client",
  "context": {},
  "human_reviewed": false,
  "is_correct": null,
  "correct_intent": null,
  "correct_entities": null,
  "review_notes": null
}
```

#### **Ejemplo 6: Mensaje Revisado y Corregido**

```json
{
  "timestamp": "2026-02-05T17:20:45.654321",
  "user_id": "1a2b3c4d5e6f7g8h",
  "message": "busco psi para mi hijo",
  "detected_intent": "unknown",
  "entities": {},
  "confidence": 0.3,
  "shortcut_used": false,
  "session_state": "CLIENT_MAIN_MENU",
  "user_role": "client",
  "context": {},
  "human_reviewed": true,
  "is_correct": false,
  "correct_intent": "search_professional",
  "correct_entities": {
    "especialidad": "psicología",
    "booking_for": "other"
  },
  "review_notes": "Usuario usó abreviatura 'psi' para psicólogo. Agregar a keywords."
}
```

---

## 📈 ANÁLISIS DE DATOS

### **Análisis en Python (Local)**

Una vez exportados los datos, puedes analizarlos con Python:

```python
# analizar_conversaciones.py

import json
from collections import Counter
from pathlib import Path

# Cargar datos
data = []
for line in open('conversations_2026-02-05.jsonl', encoding='utf-8'):
    data.append(json.loads(line))

print(f"Total mensajes: {len(data)}")

# Contar por intent
intents = Counter(entry['detected_intent'] for entry in data)
print("\nIntents más comunes:")
for intent, count in intents.most_common():
    print(f"  {intent}: {count}")

# Confianza promedio
avg_conf = sum(entry['confidence'] for entry in data) / len(data)
print(f"\nConfianza promedio: {avg_conf:.2f}")

# Mensajes con baja confianza
low_conf = [e for e in data if e['confidence'] < 0.5]
print(f"\nMensajes con baja confianza: {len(low_conf)}")
for entry in low_conf[:5]:  # Mostrar primeros 5
    print(f"  - {entry['message']} (conf: {entry['confidence']:.2f})")

# Entidades más comunes
all_entities = []
for entry in data:
    all_entities.extend(entry['entities'].keys())
entity_counts = Counter(all_entities)
print("\nEntidades más extraídas:")
for entity, count in entity_counts.most_common(5):
    print(f"  {entity}: {count}")
```

---

### **Análisis en Excel/Google Sheets**

#### **1. Convertir JSONL a CSV**

```powershell
# Dentro del contenedor
docker exec whatsapp-demo python << 'EOF'
import json
import csv

# Leer JSONL
with open('/app/data/conversations/conversations_2026-02-05.jsonl') as f:
    data = [json.loads(line) for line in f]

# Escribir CSV
with open('/tmp/conversations.csv', 'w', newline='', encoding='utf-8') as f:
    if data:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
print('✅ CSV creado')
EOF

# Copiar CSV a local
docker cp whatsapp-demo:/tmp/conversations.csv ./conversations.csv
```

#### **2. Abrir en Excel**

```powershell
# Abrir automáticamente en Excel (Windows)
Start-Process excel.exe conversations.csv
```

---

### **Análisis con pandas (Avanzado)**

```python
# analisis_avanzado.py

import pandas as pd
import json

# Cargar JSONL como DataFrame
def load_jsonl(filepath):
    data = []
    with open(filepath, encoding='utf-8') as f:
        for line in f:
            data.append(json.loads(line))
    return pd.DataFrame(data)

# Cargar datos
df = load_jsonl('conversations_2026-02-05.jsonl')

# Estadísticas básicas
print("="*60)
print("ESTADÍSTICAS DESCRIPTIVAS")
print("="*60)
print(df['confidence'].describe())

# Distribución de intents
print("\n" + "="*60)
print("DISTRIBUCIÓN DE INTENTS")
print("="*60)
print(df['detected_intent'].value_counts())

# Confianza por intent
print("\n" + "="*60)
print("CONFIANZA PROMEDIO POR INTENT")
print("="*60)
print(df.groupby('detected_intent')['confidence'].mean().sort_values(ascending=False))

# Timeline de mensajes
df['timestamp'] = pd.to_datetime(df['timestamp'])
df['hour'] = df['timestamp'].dt.hour
print("\n" + "="*60)
print("MENSAJES POR HORA")
print("="*60)
print(df['hour'].value_counts().sort_index())

# Guardar reporte
df.to_excel('reporte_conversaciones.xlsx', index=False)
print("\n✅ Reporte guardado: reporte_conversaciones.xlsx")
```

---

## 🔧 TROUBLESHOOTING

### **Problema: No se crean archivos**

```powershell
# Verificar que el directorio existe
docker exec whatsapp-demo ls -la /app/data/

# Verificar permisos
docker exec whatsapp-demo ls -la /app/data/conversations/

# Ver logs del contenedor
docker logs whatsapp-demo --tail 50

# Verificar que el logger está importado
docker exec whatsapp-demo python -c "from src.services.conversation_logger import conversation_logger; print('✅ Logger OK')"
```

---

### **Problema: Archivos vacíos**

```powershell
# Ver tamaño del archivo
docker exec whatsapp-demo ls -lh /app/data/conversations/

# Ver contenido
docker exec whatsapp-demo cat /app/data/conversations/conversations_2026-02-05.jsonl

# Si está vacío, verificar que el bot está recibiendo mensajes
docker logs whatsapp-demo | grep "CONV_LOG"
```

---

### **Problema: No puedo copiar archivos**

```powershell
# Verificar que el contenedor está corriendo
docker ps | findstr whatsapp-demo

# Si no aparece, iniciarlo
docker compose up -d

# Intentar copiar de nuevo
docker cp whatsapp-demo:/app/data/conversations ./backup/
```

---

### **Problema: Error "no such file or directory"**

```powershell
# Verificar la ruta exacta
docker exec whatsapp-demo pwd
docker exec whatsapp-demo ls /app/data/

# Si data/conversations no existe, crearla
docker exec whatsapp-demo mkdir -p /app/data/conversations
```

---

## 📚 REFERENCIA RÁPIDA

### **Comandos Esenciales**

```powershell
# Ver archivos
docker exec whatsapp-demo ls -lh /app/data/conversations/

# Copiar archivo de hoy
docker cp whatsapp-demo:/app/data/conversations/conversations_$(Get-Date -Format "yyyy-MM-dd").jsonl ./

# Ver estadísticas
docker exec whatsapp-demo python scripts/review_conversations.py --stats

# Test rápido
docker exec whatsapp-demo python scripts/test_logger.py

# Backup completo
docker cp whatsapp-demo:/app/data/conversations ./backup/conversations_$(Get-Date -Format "yyyyMMdd")

# Ver contenido formateado
docker exec whatsapp-demo python -c "import json; [print(json.dumps(json.loads(line), indent=2, ensure_ascii=False)) for line in open('/app/data/conversations/conversations_2026-02-05.jsonl')]" | more
```

---

### **Atajos de PowerShell**

Agregar a tu perfil de PowerShell (`$PROFILE`):

```powershell
# Ver conversaciones de hoy
function Get-ConversationsToday {
    $today = Get-Date -Format "yyyy-MM-dd"
    docker exec whatsapp-demo cat /app/data/conversations/conversations_$today.jsonl
}
Set-Alias -Name convs -Value Get-ConversationsToday

# Copiar conversaciones de hoy
function Copy-ConversationsToday {
    $today = Get-Date -Format "yyyy-MM-dd"
    docker cp whatsapp-demo:/app/data/conversations/conversations_$today.jsonl ./conversations_$today.jsonl
    Write-Host "✅ Copiado: conversations_$today.jsonl" -ForegroundColor Green
}
Set-Alias -Name cpconvs -Value Copy-ConversationsToday

# Ver stats
function Get-ConversationStats {
    docker exec whatsapp-demo python scripts/review_conversations.py --stats
}
Set-Alias -Name convstats -Value Get-ConversationStats
```

**Uso:**
```powershell
# Ver conversaciones de hoy
convs

# Copiar a local
cpconvs

# Ver estadísticas
convstats
```

---

## 📞 SOPORTE

Si tienes problemas:
1. Revisa la sección [Troubleshooting](#troubleshooting)
2. Verifica que el contenedor está corriendo: `docker ps`
3. Revisa los logs: `docker logs whatsapp-demo --tail 100`

---

**Última actualización:** 5 de Febrero, 2026  
**Autor:** Sistema de Logging de Conversaciones v1.0
