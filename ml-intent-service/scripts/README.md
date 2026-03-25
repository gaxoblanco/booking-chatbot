# Scripts de Entrenamiento ML

Scripts para generar dataset y entrenar el modelo spaCy de detección de intenciones.

---

## 📋 Contenido

- `dataset_base.py` - Dataset base con 80 ejemplos etiquetados manualmente
- `data_augmentation_v3.py` - Generador de variaciones (typos, sinónimos, etc.)
- `generate_training_dataset.py` - Combina base + augmentation → JSONL
- `train_spacy_model.py` - Entrena modelo spaCy
- `evaluate_spacy_model.py` - Evalúa accuracy del modelo

---

## 🚀 Quick Start

### 1. Copiar scripts desde proyecto original

```bash
# Copiar todos los scripts de entrenamiento
cp -r /path/to/proyecto-original/scripts/ml/* ./scripts/

# Verificar que tienes todos los archivos
ls -lh scripts/
# Deberías ver:
# - dataset_base.py
# - data_augmentation_v3.py
# - generate_training_dataset.py
# - train_spacy_model.py
# - evaluate_spacy_model.py
```

### 2. Generar dataset

```bash
cd scripts
python generate_training_dataset.py
```

**Output:**
- `../dataset/dataset_training.jsonl` (~1,050 ejemplos)
- `../dataset/dataset_validation.jsonl` (20% de los datos para validación)

### 3. Entrenar modelo

```bash
python train_spacy_model.py \
  --data ../dataset/dataset_training.jsonl \
  --output ../models/intent_classifier \
  --iterations 30
```

**Output:**
- `../models/intent_classifier/` (modelo entrenado, ~50MB)
- `training_report.json` (métricas de entrenamiento)

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
│ cancel_appointment   │   0.97    │  0.96  │  0.97  │
│ info_center          │   0.96    │  0.98  │  0.97  │
│ view_tomorrow        │   0.98    │  0.97  │  0.98  │
│ unknown              │   0.92    │  0.95  │  0.93  │
└──────────────────────┴───────────┴────────┴────────┘
```

---

## 📁 Estructura del Dataset

### Dataset Base (`dataset_base.py`)

80 ejemplos etiquetados manualmente, 10-15 por intención:

```python
dataset = {
    'search_professional': [
        "necesito psicólogo",
        "quiero turno con nutricionista",
        "busco traumatólogo para mañana",
        # ... más ejemplos
    ],
    'view_my_appointments': [
        "ver mis turnos",
        "cuáles son mis citas",
        "mostrame mis consultas",
        # ... más ejemplos
    ],
    # ... resto de intenciones
}
```

### Data Augmentation (`data_augmentation_v3.py`)

Genera ~970 variaciones aplicando:

1. **Typos comunes** (transposición, duplicación)
   - "necesito" → "nesesito", "nesecito"
   
2. **Sinónimos y variaciones**
   - "psicólogo" → "psi", "psico", "psicologo"
   
3. **Diminutivos**
   - "turno" → "turnito", "turnitito"
   
4. **Abreviaciones**
   - "mañana" → "maña", "mañ"
   
5. **Combinaciones**
   - Múltiples transformaciones por ejemplo

### Dataset Final (JSONL)

```jsonl
{"message": "necesito psicólogo", "intent": "search_professional"}
{"message": "nesesito psicologo", "intent": "search_professional"}
{"message": "ver mis turnos", "intent": "view_my_appointments"}
...
```

**Total: ~1,050 ejemplos**
- 80 base
- ~970 augmentados
- Split 80/20 para train/validation

---

## 🔧 Modificar el Dataset

### Agregar nuevos ejemplos

Editar `dataset_base.py`:

```python
dataset = {
    'search_professional': [
        # ... ejemplos existentes
        "nuevo ejemplo que quiero agregar",
        "otro ejemplo más específico",
    ],
    # ...
}
```

### Agregar nueva intención

1. Editar `ml/intent_enum.py`:
```python
class Intent(str, Enum):
    # ... intenciones existentes
    NEW_INTENT = "new_intent"
```

2. Editar `dataset_base.py`:
```python
dataset = {
    # ... intenciones existentes
    'new_intent': [
        "ejemplo 1 de nueva intención",
        "ejemplo 2 de nueva intención",
        # ... al menos 10 ejemplos
    ],
}
```

3. Editar `ml/ml_intent_detector.py`:
```python
self.intent_map = {
    # ... mapeos existentes
    'new_intent': Intent.NEW_INTENT,
}
```

4. Re-entrenar:
```bash
cd scripts
python generate_training_dataset.py
python train_spacy_model.py --data ../dataset/dataset_training.jsonl
```

---

## 🎯 Parámetros de Entrenamiento

### train_spacy_model.py

```bash
python train_spacy_model.py \
  --data DATASET.jsonl \          # Dataset de entrenamiento
  --output DIR \                   # Directorio de salida
  --base-model es_core_news_sm \  # Modelo base spaCy
  --iterations 30 \                # Épocas de entrenamiento
  --dropout 0.2 \                  # Tasa de dropout
  --batch-size 8                   # Tamaño de batch
```

**Recomendaciones:**
- **iterations**: 30-50 (más épocas = mejor accuracy, pero riesgo de overfitting)
- **dropout**: 0.2-0.3 (regularización para evitar overfitting)
- **batch-size**: 8-16 (ajustar según RAM disponible)

---

## 📊 Interpretación de Métricas

### Accuracy Global
Porcentaje de predicciones correctas sobre el total.
- **>95%**: Excelente
- **90-95%**: Bueno
- **<90%**: Mejorar dataset

### Precision
De todos los ejemplos que predijo como X, ¿cuántos eran realmente X?
- Alta precision = Pocas predicciones falsas positivas

### Recall
De todos los ejemplos que son X, ¿cuántos detectó correctamente?
- Alto recall = Pocas predicciones falsas negativas

### F1 Score
Media armónica de precision y recall.
- Balance entre precision y recall

---

## 🐛 Troubleshooting

### Problema: Accuracy <95%

**Solución 1:** Agregar más ejemplos
```python
# Agregar al menos 15 ejemplos por intención en dataset_base.py
```

**Solución 2:** Aumentar iteraciones
```bash
python train_spacy_model.py --iterations 50
```

**Solución 3:** Verificar balance del dataset
```bash
# Verificar que todas las intenciones tengan ejemplos similares
python -c "
from dataset_base import dataset
for intent, examples in dataset.items():
    print(f'{intent}: {len(examples)} ejemplos')
"
```

### Problema: "Model no converge"

**Solución:** Ajustar learning rate o dropout
```bash
# Editar train_spacy_model.py
# Buscar: dropout=0.2
# Cambiar a: dropout=0.3
```

### Problema: Overfitting (train accuracy alta, validation baja)

**Solución 1:** Aumentar dropout
```bash
python train_spacy_model.py --dropout 0.3
```

**Solución 2:** Agregar más ejemplos de validación

**Solución 3:** Early stopping (ya implementado)

---

## 📝 Notas Importantes

1. **Siempre re-generar dataset antes de entrenar:**
   ```bash
   python generate_training_dataset.py
   python train_spacy_model.py --data ../dataset/dataset_training.jsonl
   ```

2. **Evaluar modelo después de entrenar:**
   ```bash
   python evaluate_spacy_model.py --model ../models/intent_classifier
   ```

3. **Backup del modelo anterior antes de re-entrenar:**
   ```bash
   cp -r ../models/intent_classifier ../models/intent_classifier.backup
   ```

4. **El modelo se carga en el servicio automáticamente:**
   - Después de entrenar, reiniciar el servicio:
   ```bash
   docker-compose restart
   ```

---

## 🔗 Referencias

- **spaCy Training:** https://spacy.io/usage/training
- **Text Classification:** https://spacy.io/usage/training#textcat
- **spaCy Models:** https://spacy.io/models/es

---

## 📞 Soporte

Para dudas sobre entrenamiento, contactar al equipo de ML.
