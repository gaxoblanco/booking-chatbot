# ML Intent Service - Arquitectura

## 📋 Descripción General

Servicio centralizado de Machine Learning para detección de intenciones en mensajes de usuarios.

**Propósito:** Proveer predicciones de intenciones a múltiples instancias de la aplicación principal sin duplicar el modelo ML en cada contenedor.

---

## 🎯 Objetivos

1. **Centralización**: Un solo modelo ML cargado en memoria
2. **Eficiencia**: Reducir uso de recursos (RAM/CPU) del sistema completo
3. **Escalabilidad**: Permitir escalar el servicio ML independientemente
4. **Mantenibilidad**: Actualizar modelo en un solo lugar
5. **Performance**: Baja latencia (<100ms) en predicciones

---

## 🏗️ Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                    APLICACIONES CLIENTE                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Centro A    │  │  Centro B    │  │  Centro C    │          │
│  │  (Docker 1)  │  │  (Docker 2)  │  │  (Docker 3)  │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                  │                  │                  │
│         └──────────────────┼──────────────────┘                  │
│                            │                                     │
│                   HTTP POST /predict                            │
│                            │                                     │
└────────────────────────────┼─────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   ML INTENT SERVICE                             │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  FastAPI Application Layer                               │  │
│  │  - POST /predict       → Predicción individual           │  │
│  │  - POST /predict/batch → Predicción batch                │  │
│  │  - GET  /health        → Health check                    │  │
│  │  - GET  /metrics       → Métricas Prometheus             │  │
│  └──────────────────────────────────────────────────────────┘  │
│                             │                                   │
│                             ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  ML Detector Layer                                       │  │
│  │  - Carga modelo spaCy una sola vez                       │  │
│  │  - Predicción de intenciones                             │  │
│  │  - Retorno de scores y confidence                        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                             │                                   │
│                             ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  spaCy Model (intent_classifier)                         │  │
│  │  - 7 intenciones soportadas                              │  │
│  │  - 98.1% accuracy                                         │  │
│  │  - ~50MB en memoria                                       │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔧 Componentes

### 1. FastAPI Application (`app/`)

**Responsabilidad:** Exponer endpoints HTTP para predicciones

**Componentes:**
- `main.py`: Inicialización FastAPI, rutas, middleware
- `models.py`: Pydantic schemas para request/response
- `config.py`: Configuración (env vars, paths)
- `health.py`: Health checks y métricas

**Endpoints:**

```python
POST /predict
Content-Type: application/json

Request:
{
  "message": "necesito psicólogo mañana"
}

Response:
{
  "intent": "search_professional",
  "confidence": 0.97,
  "ml_scores": {
    "search_professional": 0.97,
    "view_my_appointments": 0.01,
    "cancel_appointment": 0.01,
    "greeting": 0.01,
    ...
  },
  "processing_time_ms": 15
}
```

```python
POST /predict/batch
Content-Type: application/json

Request:
{
  "messages": [
    "necesito psicólogo",
    "ver mis turnos",
    "hola"
  ]
}

Response:
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

```python
GET /health

Response:
{
  "status": "healthy",
  "model_loaded": true,
  "model_accuracy": 0.981,
  "intents_count": 7,
  "uptime_seconds": 3600
}
```

---

### 2. ML Detector (`ml/`)

**Responsabilidad:** Lógica de predicción con modelo spaCy

**Componentes:**
- `ml_intent_detector.py`: Clase principal de detección (copiada de proyecto original)
- `intent_enum.py`: Enum de intenciones disponibles

**Características:**
- Singleton: Modelo cargado una sola vez al iniciar
- Thread-safe: Múltiples requests concurrentes
- Fallback: Retorna `unknown` si falla predicción

---

### 3. Modelo Entrenado (`models/`)

**Ubicación:** `models/intent_classifier/`

**Características:**
- Formato: spaCy v3.7+
- Idioma: Español (es_core_news_sm)
- Tamaño: ~50MB
- Accuracy: 98.1%

**Intenciones soportadas:**
1. `search_professional` - Buscar profesional/turno
2. `view_my_appointments` - Ver mis turnos
3. `view_tomorrow` - Ver turnos de mañana
4. `cancel_appointment` - Cancelar turno
5. `info_center` - Información del centro
6. `greeting` - Saludo/bienvenida
7. `unknown` - Intención no reconocida

---

### 4. Scripts de Entrenamiento (`scripts/`)

**Responsabilidad:** Re-entrenar modelo cuando sea necesario

**Flujo:**
```bash
# 1. Generar dataset
python scripts/generate_training_dataset.py
# Output: dataset/dataset_training.jsonl (~1,050 ejemplos)

# 2. Entrenar modelo
python scripts/train_spacy_model.py --data dataset/dataset_training.jsonl
# Output: models/intent_classifier/

# 3. Evaluar
python scripts/evaluate_spacy_model.py --model models/intent_classifier
# Output: Métricas de accuracy, precision, recall
```

**Archivos:**
- `dataset_base.py`: 80 ejemplos base etiquetados manualmente
- `data_augmentation_v3.py`: Generador de variaciones (typos, sinónimos)
- `generate_training_dataset.py`: Combina base + augmentation
- `train_spacy_model.py`: Entrenamiento con spaCy
- `evaluate_spacy_model.py`: Evaluación con métricas

---

## 🔄 Flujo de Trabajo

### Predicción Individual

```
1. Cliente → HTTP POST /predict {"message": "necesito psicólogo"}
              │
              ▼
2. FastAPI → Valida request (Pydantic)
              │
              ▼
3. MLDetector → nlp(message)
              │
              ▼
4. spaCy Model → Calcula scores para cada intent
              │
              ▼
5. MLDetector → Selecciona intent con mayor score
              │
              ▼
6. FastAPI → Retorna JSON response con intent + confidence
              │
              ▼
7. Cliente ← {"intent": "search_professional", "confidence": 0.97}
```

### Startup

```
1. Docker Container inicia
   │
   ▼
2. FastAPI app.__init__()
   │
   ▼
3. Cargar config desde env vars
   │
   ▼
4. Inicializar MLIntentDetector
   │  └─→ Cargar modelo spaCy desde disco
   │       └─→ Validar modelo cargado correctamente
   │
   ▼
5. Registrar endpoints
   │
   ▼
6. Health check OK → Servicio listo
   │
   ▼
7. Escuchar en 0.0.0.0:8000
```

---

## 🚀 Deployment

### Docker Compose (Desarrollo)

```yaml
services:
  ml-service:
    build: .
    ports:
      - "8000:8000"
    environment:
      - MODEL_PATH=models/intent_classifier
      - LOG_LEVEL=INFO
    volumes:
      - ./models:/app/models:ro  # Read-only
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Producción (Docker Swarm / Kubernetes)

**Consideraciones:**
- **Réplicas:** Múltiples instancias para alta disponibilidad
- **Load Balancer:** Nginx/Traefik delante del servicio
- **Monitoreo:** Prometheus + Grafana para métricas
- **Logs:** Centralizar con ELK stack
- **Auto-scaling:** Escalar según CPU/memoria

---

## 📊 Performance

### Métricas Esperadas

| Métrica | Valor |
|---------|-------|
| Latencia p50 | 10-20ms |
| Latencia p95 | 30-50ms |
| Latencia p99 | 80-100ms |
| Throughput | 500-1000 req/s (single instance) |
| Memoria | ~200MB (modelo + FastAPI) |
| CPU | <10% en idle, 30-50% bajo carga |

### Optimizaciones

1. **Model Loading:** Singleton pattern (cargar una sola vez)
2. **Threading:** FastAPI async para concurrencia
3. **Caching:** Cache de predicciones frecuentes (Redis, futuro)
4. **Batch Processing:** Endpoint `/predict/batch` para múltiples mensajes

---

## 🔐 Seguridad

### Consideraciones

1. **Sin autenticación inicial:** Red interna (docker network)
2. **Rate limiting:** Implementar si se expone públicamente
3. **Validación:** Pydantic valida todos los inputs
4. **CORS:** Configurar según necesidad

### Futuro (si se expone públicamente)

- API Key authentication
- Rate limiting (100 req/min por cliente)
- HTTPS obligatorio
- Logging de requests

---

## 📈 Escalabilidad

### Horizontal Scaling

```yaml
# docker-compose.yml
services:
  ml-service:
    deploy:
      replicas: 3  # Múltiples instancias
    
  nginx:  # Load balancer
    image: nginx:alpine
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    ports:
      - "8000:80"
    depends_on:
      - ml-service
```

### Vertical Scaling

- Aumentar CPU/RAM del contenedor
- Usar instancias con GPU (futuro, para modelos Transformer)

---

## 🧪 Testing

### Unit Tests

```bash
pytest tests/test_ml_detector.py -v
```

### Integration Tests

```bash
pytest tests/test_api.py -v
```

### Load Testing

```bash
# Usar wrk o k6
wrk -t4 -c100 -d30s http://localhost:8000/predict \
    -s scripts/load_test.lua
```

---

## 📝 Logs

### Formato

```
[2025-02-11 14:30:15] INFO - Model loaded: 98.1% accuracy
[2025-02-11 14:30:20] INFO - Prediction: "necesito psicólogo" → search_professional (0.97)
[2025-02-11 14:30:21] WARNING - Low confidence: "asdfgh" → unknown (0.45)
[2025-02-11 14:30:22] ERROR - Model prediction failed: Invalid input
```

### Niveles

- **DEBUG:** Detalles de cada predicción
- **INFO:** Startup, requests importantes
- **WARNING:** Baja confidence, errores recuperables
- **ERROR:** Fallos en predicción, modelo no cargado

---

## 🔮 Roadmap

### Fase 1 (Actual) ✅
- [x] Servicio básico FastAPI
- [x] Endpoint `/predict`
- [x] Health checks
- [x] Dockerfile

### Fase 2 (Corto plazo)
- [ ] Cache Redis para predicciones frecuentes
- [ ] Endpoint `/predict/batch` optimizado
- [ ] Métricas Prometheus
- [ ] Rate limiting

### Fase 3 (Mediano plazo)
- [ ] A/B testing de modelos
- [ ] Feedback loop (logs de predicciones incorrectas)
- [ ] Re-entrenamiento automático
- [ ] Monitoreo de drift del modelo

### Fase 4 (Largo plazo)
- [ ] Migración a Transformers (BERT/RoBERTa)
- [ ] GPU support
- [ ] Multi-lenguaje (inglés, portugués)
- [ ] Personalización por cliente

---

## 🆘 Troubleshooting

### Problema: "Model not loaded"

```bash
# Verificar que existe el modelo
ls -lh models/intent_classifier/

# Verificar permisos
chmod -R 755 models/

# Verificar logs
docker logs ml-service | grep "Model"
```

### Problema: Alta latencia

```bash
# Verificar recursos del contenedor
docker stats ml-service

# Verificar concurrencia
curl http://localhost:8000/metrics | grep requests_total

# Considerar aumentar réplicas
docker-compose up --scale ml-service=3
```

### Problema: Baja accuracy

```bash
# Re-entrenar modelo
cd scripts
python train_spacy_model.py --data ../dataset/dataset_training.jsonl

# Evaluar nuevo modelo
python evaluate_spacy_model.py --model ../models/intent_classifier
```

---

## 📚 Referencias

- **FastAPI:** https://fastapi.tiangolo.com/
- **spaCy:** https://spacy.io/
- **Docker:** https://docs.docker.com/
- **Prometheus:** https://prometheus.io/

---

## 📞 Contacto

Para dudas o mejoras, contactar al equipo de desarrollo.
