# 🔄 Guía de Reentrenamiento — ML Intent Service

Paso a paso para actualizar el modelo de detección de intenciones.
Todos los comandos corren dentro del container — no hace falta instalar nada localmente.

**Nota PowerShell:** los comandos multilínea usan backtick `` ` `` para continuar la línea.
En Linux/Mac usar `\` o escribir todo en una sola línea.

---

## Cuándo reentrenar

- Se agregaron ejemplos a `dataset_base.py`
- El bot clasifica mal frases que deberían funcionar
- Se agregó soporte para un dominio nuevo
- La accuracy bajó en producción
- Se agregó una intención nueva / servicio nuevo que el bot debe reconocer

---

## Ciclo completo — referencia rápida

```powershell
# PowerShell (Windows) — todo en una línea por comando
docker exec -it ml-intent-service python /app/scripts/ml/generate_training_dataset.py
docker exec -it ml-intent-service python /app/scripts/ml/train_spacy_model.py --data /app/scripts/ml/dataset_training.jsonl --output /app/models/intent_classifier --iterations 50
docker exec -it ml-intent-service python /app/scripts/ml/evaluate_spacy_model.py --model /app/models/intent_classifier --data /app/scripts/ml/dataset_training.jsonl
docker compose restart
```

```bash
# Linux/Mac (servidor)
docker exec -it ml-intent-service python /app/scripts/ml/generate_training_dataset.py
docker exec -it ml-intent-service python /app/scripts/ml/train_spacy_model.py \
    --data /app/scripts/ml/dataset_training.jsonl \
    --output /app/models/intent_classifier \
    --iterations 50
docker exec -it ml-intent-service python /app/scripts/ml/evaluate_spacy_model.py \
    --model /app/models/intent_classifier \
    --data /app/scripts/ml/dataset_training.jsonl
docker compose restart
```

---

## Paso 1 — Editar el dataset base

El archivo fuente es `scripts/ml/dataset_base.py`.
Editarlo localmente en VS Code — el volumen lo sincroniza al container automáticamente.

Verificar el balance antes de entrenar:

```powershell
docker exec -it ml-intent-service python -c "import re; from collections import Counter; content = open('/app/scripts/ml/dataset_base.py').read(); counts = Counter(re.findall(r'\"intent\":\s*\"(\w+)\"', content)); [print(f'{k:35} {v:3}') for k, v in sorted(counts.items(), key=lambda x: -x[1])]; print(f'Total: {sum(counts.values())}')"
```

**Criterios de calidad del dataset:**
- Ninguna intención debe tener menos de 30 ejemplos (excepto las de agenda: mínimo 12)
- Ratio entre la más grande y la más chica: no superar 4x
- `search_professional` — vocabulario genérico, sin especialidades hardcodeadas de salud
- Intenciones genéricas (cancelar, ver turnos, saludar) deben cubrir todos los dominios

---

## Paso 2 — Backup del modelo actual

Siempre antes de reentrenar:

```powershell
# PowerShell — en una sola línea
docker exec -it ml-intent-service cp -r /app/models/intent_classifier /app/models/intent_classifier.backup
```

```bash
# Linux/Mac
docker exec -it ml-intent-service cp -r \
    /app/models/intent_classifier \
    /app/models/intent_classifier.backup
```

Verificar:

```powershell
docker exec -it ml-intent-service ls /app/models/
# Debe mostrar: intent_classifier  intent_classifier.backup
```

---

## Paso 3 — Generar el dataset completo

Combina los ejemplos base con variaciones generadas por augmentation
(typos, sinónimos, mayúsculas, errores de tipeo).

```powershell
docker exec -it ml-intent-service python /app/scripts/ml/generate_training_dataset.py
```

Verificar que creció correctamente:

```powershell
docker exec -it ml-intent-service python -c "import json; from collections import Counter; intents = Counter(json.loads(l)['intent'] for l in open('/app/scripts/ml/dataset_training.jsonl')); print(f'Total: {sum(intents.values())} ejemplos, {len(intents)} intenciones'); [print(f'  {k:<35} {v}') for k, v in intents.most_common()]"
```

Output esperado: 1.000+ ejemplos, 14 intenciones.

---

## Paso 4 — Entrenar el modelo

```powershell
# PowerShell — en una sola línea
docker exec -it ml-intent-service python /app/scripts/ml/train_spacy_model.py --data /app/scripts/ml/dataset_training.jsonl --output /app/models/intent_classifier --iterations 50 --dropout 0.2 --batch-size 8
```

```bash
# Linux/Mac
docker exec -it ml-intent-service python /app/scripts/ml/train_spacy_model.py \
    --data /app/scripts/ml/dataset_training.jsonl \
    --output /app/models/intent_classifier \
    --iterations 50 \
    --dropout 0.2 \
    --batch-size 8
```

El entrenamiento tarda entre 2 y 10 minutos según el hardware.

---

## Paso 5 — Evaluar el modelo

```powershell
# PowerShell — en una sola línea
docker exec -it ml-intent-service python /app/scripts/ml/evaluate_spacy_model.py --model /app/models/intent_classifier --data /app/scripts/ml/dataset_training.jsonl
```

Output esperado:

```
Accuracy Global: 98%+

Métricas por Intent:
┌──────────────────────┬───────────┬────────┬────────┐
│ Intent               │ Precision │ Recall │ F1     │
├──────────────────────┼───────────┼────────┼────────┤
│ search_professional  │   0.98    │  0.99  │  0.98  │
│ info_center          │   0.96    │  0.98  │  0.97  │
│ cancel_appointment   │   0.97    │  0.96  │  0.97  │
└──────────────────────┴───────────┴────────┴────────┘
```

Si la accuracy baja de 95%, ver sección **Troubleshooting**.

Verificar que el modelo tiene las 14 intenciones:

```powershell
docker exec -it ml-intent-service python -c "import spacy; nlp = spacy.load('/app/models/intent_classifier'); tc = nlp.get_pipe('textcat'); print(len(tc.labels), 'intenciones:', sorted(tc.labels))"
```

---

## Paso 6 — Activar el modelo nuevo

```powershell
docker compose restart
```

Verificar que cargó:

```powershell
curl http://localhost:8000/health
```

```json
{
  "status": "healthy",
  "model_loaded": true,
  "intents_count": 14
}
```

---

## Paso 7 — Probar las frases mejoradas

```powershell
# PowerShell
curl -X POST http://localhost:8000/predict -H "Content-Type: application/json" -d "{\"message\": \"quiero saber mas sobre el servicio\"}"
```

```bash
# Linux/Mac
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"message": "quiero saber más sobre el servicio"}'
```

---

## Rollback — volver al modelo anterior

```powershell
# PowerShell — en una sola línea
docker exec -it ml-intent-service sh -c "rm -rf /app/models/intent_classifier && cp -r /app/models/intent_classifier.backup /app/models/intent_classifier"
docker compose restart
```

```bash
# Linux/Mac
docker exec -it ml-intent-service sh -c \
    "rm -rf /app/models/intent_classifier && \
     cp -r /app/models/intent_classifier.backup /app/models/intent_classifier"
docker compose restart
```

---

## Agregar una intención nueva

1. Editar `scripts/ml/dataset_base.py` — agregar al menos 15 ejemplos
2. Editar `ml/intent_enum.py` — agregar el nuevo valor al enum
3. Editar `ml/ml_intent_detector.py` — agregar al `intent_map`
4. Editar `booking-chatbot/src/services/intent_detector.py` — mismo enum en el bot
5. Correr el ciclo completo (pasos 3 → 6)
6. Conectar la intención en `bot_controller.py`

---

## Troubleshooting

**Accuracy < 95%**

Opciones en orden: verificar balance del dataset → aumentar `--iterations` a 70-100 → revisar ejemplos ambiguos entre intenciones.

---

**"7 intents" en lugar de 14 al evaluar**

El trainer usó el dataset viejo o de otra ruta. Verificar que el comando apunta a `/app/scripts/ml/dataset_training.jsonl`.

---

**"Read-only file system" al entrenar**

El volumen `./models` está montado con `:ro`. En `docker-compose.yml` debe ser `- ./models:/app/models` sin `:ro`.

---

**"No such file: dataset_training.jsonl"**

Correr primero el paso 3. Verificar:

```powershell
docker exec -it ml-intent-service ls /app/scripts/ml/
```

---

**El servicio no carga el modelo nuevo después de reiniciar**

```powershell
docker logs ml-intent-service --tail 30
```

Si hay error de carga, hacer rollback y reentrenar con más iteraciones.