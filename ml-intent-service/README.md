# 🤖 ML Intent Service

Servicio centralizado de Machine Learning para detección de intenciones en mensajes de usuarios.

**Versión:** 1.0.0  
**Modelo:** spaCy v3.7 (intent_classifier)  
**Accuracy:** 98.1%  
**Latencia:** ~15ms promedio

---

## 📋 Tabla de Contenidos

- [Descripción](#descripción)
- [Quick Start](#quick-start)
- [Instalación](#instalación)
- [Uso](#uso)
- [API Reference](#api-reference)
- [Re-entrenamiento](#re-entrenamiento)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)

---

## 🎯 Descripción

Este servicio proporciona predicciones de intenciones mediante un modelo ML entrenado con spaCy.

**Intenciones soportadas:**
1. `search_professional` - Buscar profesional/turno
2. `view_my_appointments` - Ver mis turnos
3. `view_tomorrow` - Ver turnos de mañana
4. `cancel_appointment` - Cancelar turno
5. `info_center` - Información del centro
6. `greeting` - Saludo/bienvenida
7. `unknown` - Intención no reconocida

---

## ⚡ Quick Start

```bash
# 1. Clonar repositorio
git clone <repo-url>
cd ml-intent-service

# 2. Iniciar con Docker
docker-compose up --build

# 3. Probar el servicio
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"message": "necesito psicólogo mañana"}'

# Respuesta:
# {
#   "intent": "search_professional",
#   "confidence": 0.97,
#   "ml_scores": {...},
#   "processing_time_ms": 15
# }
```

---

## 📦 Instalación

### Opción 1: Docker (Recomendado)

```bash
# Iniciar servicio
docker-compose up -d

# Ver logs
docker-compose logs -f

# Detener servicio
docker-compose down
```

### Opción 2: Local (Desarrollo)

```bash
# 1. Crear entorno virtual
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate  # Windows

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Descargar modelo base spaCy
python -m spacy download es_core_news_sm

# 4. Verificar que existe el modelo entrenado
ls -lh models/intent_classifier/

# 5. Iniciar servicio
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 🚀 Uso

### Python (requests)

```python
import requests

response = requests.post(
    "http://localhost:8000/predict",
    json={"message": "necesito psicólogo mañana"}
)

result = response.json()
print(f"Intent: {result['intent']}")
print(f"Confidence: {result['confidence']:.2%}")
```

### cURL

```bash
# Predicción individual
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"message": "ver mis turnos"}'

# Predicción batch
curl -X POST http://localhost:8000/predict/batch \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      "necesito psicólogo",
      "ver mis turnos",
      "cancelar turno"
    ]
  }'

# Health check
curl http://localhost:8000/health
```

### JavaScript (fetch)

```javascript
const response = await fetch('http://localhost:8000/predict', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({message: 'hola'})
});

const result = await response.json();
console.log(`Intent: ${result.intent} (${result.confidence})`);
```

---

## 📚 API Reference

### POST /predict

Predice la intención de un mensaje.

**Request:**
```json
{
  "message": "necesito psicólogo mañana"
}
```

**Response:**
```json
{
  "intent": "search_professional",
  "confidence": 0.97,
  "ml_scores": {
    "search_professional": 0.97,
    "view_my_appointments": 0.01,
    "cancel_appointment": 0.01,
    "greeting": 0.01,
    "info_center": 0.00,
    "view_tomorrow": 0.00,
    "unknown": 0.00
  },
  "processing_time_ms": 15
}
```

**Códigos de respuesta:**
- `200 OK` - Predicción exitosa
- `400 Bad Request` - Mensaje vacío o inválido
- `500 Internal Server Error` - Error en el modelo

---

### POST /predict/batch

Predice la intención de múltiples mensajes en una sola request.

**Request:**
```json
{
  "messages": [
    "necesito psicólogo",
    "ver mis turnos",
    "hola"
  ]
}
```

**Response:**
```json
{
  "predictions": [
    {
      "message": "necesito psicólogo",
      "intent": "search_professional",
      "confidence": 0.98
    },
    {
      "message": "ver mis turnos",
      "intent": "view_my_appointments",
      "confidence": 0.99
    },
    {
      "message": "hola",
      "intent": "greeting",
      "confidence": 0.97
    }
  ],
  "total_processing_time_ms": 42
}
```

---

### GET /health

Health check del servicio.

**Response:**
```json
{
  "status": "healthy",
  "model_loaded": true,
  "model_accuracy": 0.981,
  "intents_count": 7,
  "uptime_seconds": 3600
}
```

---

### GET /metrics

Métricas Prometheus (opcional).

**Response:**
```
# HELP ml_predictions_total Total number of predictions
# TYPE ml_predictions_total counter
ml_predictions_total 1523

# HELP ml_prediction_duration_seconds Time spent processing predictions
# TYPE ml_prediction_duration_seconds histogram
ml_prediction_duration_seconds_bucket{le="0.01"} 1200
ml_prediction_duration_seconds_bucket{le="0.05"} 1500
...
```

---

## 🔄 Re-entrenamiento

Si necesitas actualizar el modelo con nuevos datos:

### 1. Preparar datos

Editar `scripts/dataset_base.py` para agregar nuevos ejemplos:

```python
dataset = {
    'search_professional': [
        "necesito psicólogo",
        "quiero turno con nutricionista",
        # Agregar más ejemplos...
    ],
    # ...
}
```

### 2. Generar dataset completo

```bash
cd scripts
python generate_training_dataset.py
```

Esto genera `dataset/dataset_training.jsonl` con ~1,050 ejemplos (base + augmentation).

### 3. Entrenar modelo

```bash
python train_spacy_model.py \
  --data ../dataset/dataset_training.jsonl \
  --output ../models/intent_classifier \
  --iterations 50
```

**Argumentos opcionales:**
- `--base-model`: Modelo base spaCy (default: `es_core_news_sm`)
- `--iterations`: Épocas de entrenamiento (default: 30)
- `--dropout`: Tasa de dropout (default: 0.2)
- `--batch-size`: Tamaño de batch (default: 8)

### 4. Evaluar modelo

```bash
python evaluate_spacy_model.py \
  --model ../models/intent_classifier
```

**Output esperado:**
```
╔══════════════════════════════════════════════════════════╗
║           REPORTE DE EVALUACIÓN - MODELO SPACY           ║
╚══════════════════════════════════════════════════════════╝

Accuracy Global: 98.1%

Métricas por Intent:
┌──────────────────────┬───────────┬────────┬────────┐
│ Intent               │ Precision │ Recall │ F1     │
├──────────────────────┼───────────┼────────┼────────┤
│ search_professional  │   0.98    │  0.99  │  0.98  │
│ view_my_appointments │   0.99    │  0.98  │  0.99  │
│ greeting             │   1.00    │  1.00  │  1.00  │
└──────────────────────┴───────────┴────────┴────────┘
```

### 5. Reiniciar servicio

```bash
# Si usas Docker
docker-compose restart

# Si usas local
# Ctrl+C para detener uvicorn
# uvicorn app.main:app --reload
```

---

## 🚢 Deployment

### Docker Compose (Simple)

```yaml
# docker-compose.yml
services:
  ml-service:
    build: .
    ports:
      - "8000:8000"
    environment:
      - MODEL_PATH=models/intent_classifier
      - LOG_LEVEL=INFO
    restart: unless-stopped
```

### Producción con Nginx

```yaml
# docker-compose.prod.yml
services:
  ml-service:
    build: .
    deploy:
      replicas: 3  # 3 instancias
      resources:
        limits:
          memory: 512M
    environment:
      - MODEL_PATH=models/intent_classifier
      - LOG_LEVEL=WARNING
    restart: always
  
  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    ports:
      - "80:80"
    depends_on:
      - ml-service
```

**nginx.conf:**
```nginx
upstream ml_backend {
    server ml-service:8000;
}

server {
    listen 80;
    
    location / {
        proxy_pass http://ml_backend;
        proxy_set_header Host $host;
    }
}
```

### Variables de Entorno

Crear `.env` basado en `.env.example`:

```bash
# .env
MODEL_PATH=models/intent_classifier
LOG_LEVEL=INFO
WORKERS=4
```

---

## 🔧 Troubleshooting

### Problema: "Model not loaded"

```bash
# Verificar que existe el modelo
ls -lh models/intent_classifier/

# Debería mostrar:
# config.cfg
# meta.json
# ner/
# textcat/
# tokenizer
# vocab/

# Si no existe, entrena el modelo:
cd scripts
python generate_training_dataset.py
python train_spacy_model.py --data ../dataset/dataset_training.jsonl
```

### Problema: "Port 8000 already in use"

```bash
# Cambiar puerto en docker-compose.yml
services:
  ml-service:
    ports:
      - "8001:8000"  # Usar puerto 8001 externamente

# O matar proceso en puerto 8000
lsof -ti:8000 | xargs kill -9
```

### Problema: Alta latencia (>100ms)

```bash
# Verificar recursos
docker stats ml-service

# Aumentar workers
# En .env:
WORKERS=8

# Considerar múltiples réplicas
docker-compose up --scale ml-service=3
```

### Problema: Baja accuracy en producción

```bash
# 1. Recolectar mensajes mal clasificados
# Ver logs con baja confidence
docker logs ml-service | grep "Low confidence"

# 2. Agregar a dataset_base.py

# 3. Re-entrenar
cd scripts
python generate_training_dataset.py
python train_spacy_model.py --data ../dataset/dataset_training.jsonl --iterations 50

# 4. Evaluar nuevo modelo
python evaluate_spacy_model.py --model ../models/intent_classifier
```

---

## 📊 Performance

**Benchmarks (single instance):**

| Métrica | Valor |
|---------|-------|
| Latencia p50 | 15ms |
| Latencia p95 | 35ms |
| Latencia p99 | 80ms |
| Throughput | ~500 req/s |
| Memoria | 200MB |
| CPU (idle) | <5% |
| CPU (load) | 30-40% |

**Testeo de carga:**

```bash
# Instalar wrk
brew install wrk  # Mac
apt-get install wrk  # Linux

# Test de carga
wrk -t4 -c100 -d30s http://localhost:8000/predict \
    --header "Content-Type: application/json" \
    --body '{"message": "necesito psicólogo"}'
```

---

## 📁 Estructura del Proyecto

```
ml-intent-service/
├── ARCHITECTURE.md         # Documentación técnica detallada
├── README.md              # Este archivo
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
│
├── app/                   # FastAPI application
│   ├── main.py           # Entry point
│   ├── config.py         # Configuración
│   ├── models.py         # Pydantic schemas
│   └── health.py         # Health checks
│
├── ml/                    # ML detector
│   ├── ml_intent_detector.py
│   └── intent_enum.py
│
├── models/               # Modelo entrenado
│   └── intent_classifier/
│
├── scripts/              # Training scripts
│   ├── dataset_base.py
│   ├── data_augmentation_v3.py
│   ├── generate_training_dataset.py
│   ├── train_spacy_model.py
│   ├── evaluate_spacy_model.py
│   └── README.md
│
└── tests/                # Tests
    ├── test_api.py
    └── test_ml_detector.py
```

---

## 🤝 Contribuir

Para contribuir al proyecto:

1. Fork del repositorio
2. Crear branch: `git checkout -b feature/nueva-funcionalidad`
3. Commit: `git commit -am 'Agregar nueva funcionalidad'`
4. Push: `git push origin feature/nueva-funcionalidad`
5. Pull Request

---

## 📝 Changelog

### v1.0.0 (2025-02-11)
- ✅ Servicio inicial FastAPI
- ✅ Modelo spaCy con 98.1% accuracy
- ✅ Endpoints `/predict` y `/health`
- ✅ Docker + docker-compose
- ✅ Scripts de entrenamiento

---

## 📄 Licencia

[Especificar licencia]

---

## 📞 Soporte

Para dudas o problemas:
- Abrir un issue en GitHub
- Contactar al equipo de desarrollo

---

## 🔗 Links Útiles

- [Documentación de Arquitectura](ARCHITECTURE.md)
- [spaCy Documentation](https://spacy.io/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Training Scripts README](scripts/README.md)
