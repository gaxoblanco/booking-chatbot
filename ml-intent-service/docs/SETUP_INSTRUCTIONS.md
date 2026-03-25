# Setup — ML Intent Service
*Versión 2.0 — Marzo 2026*

---

## Estructura del proyecto

```
ml-intent-service/
├── app/                        # Servicio FastAPI (producción)
├── ml/                         # Código ML del servicio
├── models/                     # Modelo entrenado (volumen Docker)
│   └── intent_classifier/      # Modelo activo
│   └── intent_classifier_best/ # Mejor epoch del último entrenamiento
├── scripts/
│   └── ml/                     # Scripts de entrenamiento
│       ├── dataset_base.py         # Ejemplos base etiquetados (~158)
│       ├── data_augmentation.py    # Generador de variaciones
│       ├── generate_training_dataset.py
│       ├── train_spacy_model.py
│       ├── evaluate_spacy_model.py
│       ├── inspect_dataset.py
│       └── dataset_training.jsonl  # Dataset generado (no commitear)
├── docker-compose.yml          # Desarrollo + entrenamiento
├── docker-compose.prod.yml     # Producción (sin scripts montados)
└── requirements.txt
```

---

## Entornos

### Desarrollo / Entrenamiento (`docker-compose.yml`)

Monta los scripts como volumen para poder entrenar sin rebuild.

```yaml
volumes:
  - ./models:/app/models              # writable — el modelo se guarda aquí
  - ./scripts/ml:/app/scripts/ml      # scripts de entrenamiento en vivo
  - ./ml:/app/ml:ro                   # código ML del servicio
```

### Producción (`docker-compose.prod.yml`)

Solo monta el modelo como read-only. No expone scripts.

```yaml
volumes:
  - ./models:/app/models:ro
```

---

## Levantar el servicio

### Desarrollo

```powershell
# Desde D:\develop-programing\ml-intent-service
docker compose up -d

# Ver logs
docker compose logs -f
```

### Producción

```powershell
docker compose -f docker-compose.prod.yml up -d
```

### Verificar que está corriendo

```powershell
# Health check
curl http://localhost:8000/health

# Respuesta esperada:
# {"status":"healthy","model_loaded":true,"intents_count":14,...}
```

---

## Flujo de entrenamiento

El proceso completo tiene 4 pasos. Todos corren dentro del container
`ml-intent-service` para usar las librerías instaladas (spaCy, scikit-learn).

### Paso 0 — Verificar el container

```powershell
docker ps
# Debe aparecer: ml-intent-service   Up
```

### Paso 1 — Editar los ejemplos base

Archivo: `scripts/ml/dataset_base.py`

Editarlo directamente en el host (VS Code). El volumen lo sincroniza
automáticamente al container. No hace falta copiar nada.

Para verificar cuántos ejemplos y qué intenciones hay:

```powershell
docker exec -it ml-intent-service python /app/scripts/ml/dataset_base.py
```

Salida esperada:
```
DATASET BASE v3.0 — 158 ejemplos, 14 intenciones
  search_professional        35    22.2%  ███...
  agenda_confirm_upload      15     9.5%  ███...
  ...
```

### Paso 2 — Generar el dataset sintético

```powershell
docker exec -it ml-intent-service python /app/scripts/ml/generate_training_dataset.py
```

Genera `scripts/ml/dataset_training.jsonl` (~3.948 ejemplos con augmentation x20).

Verificar que el dataset tiene las intenciones correctas:

```powershell
docker exec -it ml-intent-service python -c "
import json
from collections import Counter
intents = Counter()
with open('/app/scripts/ml/dataset_training.jsonl') as f:
    for line in f: intents[json.loads(line)['intent']] += 1
print(f'Total: {sum(intents.values())} ejemplos, {len(intents)} intenciones')
for intent, count in intents.most_common():
    print(f'  {intent:<35} {count}')
"
```

Debe mostrar **14 intenciones** y ~3.948 ejemplos.
Si muestra 7 intenciones, el `dataset_base.py` no tiene las intenciones nuevas.

### Paso 3 — Entrenar el modelo

```powershell
docker exec -it ml-intent-service python /app/scripts/ml/train_spacy_model.py --data /app/scripts/ml/dataset_training.jsonl --output /app/models/intent_classifier --iterations 30
```

El trainer guarda dos versiones:
- `/app/models/intent_classifier_best` — mejor epoch (usar este en producción)
- `/app/models/intent_classifier` — último epoch

Salida esperada al terminar:
```
Mejor accuracy en eval: 98.x%
Modelo guardado en: /app/models/intent_classifier
```

### Paso 4 — Evaluar el modelo

```powershell
docker exec -it ml-intent-service python /app/scripts/ml/evaluate_spacy_model.py --model /app/models/intent_classifier --data /app/scripts/ml/dataset_training.jsonl
```

Verificar que el modelo cargado tiene 14 intenciones:

```powershell
docker exec -it ml-intent-service python -c "
import spacy
nlp = spacy.load('/app/models/intent_classifier')
tc = nlp.get_pipe('textcat')
print(f'{len(tc.labels)} intenciones:', sorted(tc.labels))
"
```

Debe mostrar las 14 intenciones nuevas incluyendo `agenda_view_ready`,
`agenda_confirm_upload`, `book_for_third_party`, etc.

### Paso 5 — Reiniciar el servicio con el modelo nuevo

```powershell
docker compose restart
```

Verificar que levantó con el modelo nuevo:

```powershell
curl http://localhost:8000/health
# intents_count debe ser 14
```

---

## Comandos de diagnóstico

### Ver qué modelo está cargado en el servicio activo

```powershell
docker exec -it ml-intent-service python -c "
import spacy, os
path = os.getenv('MODEL_PATH', 'models/intent_classifier')
nlp = spacy.load(f'/app/{path}')
tc = nlp.get_pipe('textcat')
print(f'Modelo activo: {path}')
print(f'Intenciones ({len(tc.labels)}): {sorted(tc.labels)}')
"
```

### Probar una predicción manualmente

```powershell
curl -X POST http://localhost:8000/predict `
  -H "Content-Type: application/json" `
  -d "{\"message\": \"necesito psicólogo mañana\"}"
```

### Verificar qué dataset se usó para entrenar

```powershell
docker exec -it ml-intent-service python -c "
import json
from collections import Counter
intents = Counter()
with open('/app/scripts/ml/dataset_training.jsonl') as f:
    for line in f: intents[json.loads(line)['intent']] += 1
print(f'{sum(intents.values())} ejemplos, {len(intents)} intenciones')
"
```

### Ver logs del entrenamiento anterior

```powershell
# El trainer guarda el reporte en el directorio donde corrió
docker exec -it ml-intent-service cat /app/training_report.json
```

---

## Troubleshooting

### "7 intents" en lugar de 14 al evaluar

El trainer usó el dataset viejo. Verificar que el comando de entrenamiento
apunta a `/app/scripts/ml/dataset_training.jsonl` y no a `/app/ml/dataset_training.jsonl`.

### "Read-only file system" al entrenar

El volumen `./models` está montado con `:ro`. Verificar `docker-compose.yml` —
en desarrollo debe ser `- ./models:/app/models` sin `:ro`.

### "No module named sklearn" al evaluar

```powershell
docker exec -it ml-intent-service pip install scikit-learn
```

Para que quede permanente, agregar `scikit-learn>=1.3.0` al `requirements.txt`
y hacer rebuild: `docker compose up --build -d`

### "No such file or directory: dataset_training.jsonl"

El dataset no fue generado todavía o el path es incorrecto.
Correr primero el Paso 2 y verificar que el archivo existe:

```powershell
docker exec -it ml-intent-service ls /app/scripts/ml/
```

### El servicio no conecta al modelo nuevo después de entrenar

Hacer restart para que recargue el modelo desde disco:

```powershell
docker compose restart
```

---

## Agregar intenciones nuevas

1. Editar `scripts/ml/dataset_base.py` — agregar ejemplos en `DATASET_BASE`
2. Verificar con `docker exec -it ml-intent-service python /app/scripts/ml/dataset_base.py`
3. Regenerar dataset (Paso 2)
4. Reentrenar (Paso 3)
5. Evaluar (Paso 4)
6. Reiniciar servicio (Paso 5)
7. Agregar el nuevo valor al enum `Intent` en `booking-chatbot/src/services/intent_detector.py`

---

## Ciclo completo — referencia rápida

```powershell
# 1. Generar dataset
docker exec -it ml-intent-service python /app/scripts/ml/generate_training_dataset.py

# 2. Entrenar
docker exec -it ml-intent-service python /app/scripts/ml/train_spacy_model.py --data /app/scripts/ml/dataset_training.jsonl --output /app/models/intent_classifier --iterations 30

# 3. Evaluar
docker exec -it ml-intent-service python /app/scripts/ml/evaluate_spacy_model.py --model /app/models/intent_classifier --data /app/scripts/ml/dataset_training.jsonl

# 4. Verificar intenciones del modelo
docker exec -it ml-intent-service python -c "import spacy; nlp = spacy.load('/app/models/intent_classifier'); tc = nlp.get_pipe('textcat'); print(len(tc.labels), sorted(tc.labels))"

# 5. Reiniciar servicio
docker compose restart
```