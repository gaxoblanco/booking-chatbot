# WhatsApp Booking Bot

Sistema de gestión de citas y reservas para centros de salud, implementado como bot conversacional de WhatsApp. Permite a **clientes** buscar profesionales con disponibilidad en tiempo real, y a **profesionales** gestionar su agenda a través de Google Calendar.

---

## 🧠 Stack Tecnológico (v7.0)

| Capa | Tecnología |
|------|-----------|
| Mensajería | Meta Cloud API (WhatsApp Business) |
| Backend | Python 3.10+ / Flask |
| NLU/ML | spaCy 3.7.2 + `es_core_news_sm` — **98.1% accuracy** |
| Intent Detection | Híbrido: ML primario + Reglas como fallback |
| Calendar | Google Calendar API (Service Account) |
| Cache | In-memory thread-safe (TTL 15 min, 80–90% hit rate) |
| Base de datos | SQLite |
| Contenedores | Docker + Docker Compose |
| Tests | pytest |

> **Nota sobre el ML:** El servicio ML (spaCy) está **separado del contenedor Docker principal** para mantener la imagen liviana. Por defecto el bot corre solo con reglas. Para activar el modo híbrido ML + Reglas, ver [Activar ML en Docker](#-activar-ml-en-docker-todo-en-uno).

---

## 📁 Estructura del Proyecto

```
booking-chatbot/
├── src/
│   ├── bot/
│   │   ├── bot_controller.py          # Orquestador principal
│   │   ├── client_handler.py          # Flujo conversacional de clientes
│   │   ├── professional_handler.py    # Flujo de profesionales
│   │   ├── freelance_handler.py       # Sub-flujo modo profesional único
│   │   └── reminder_handler.py        # Manejo de respuestas a recordatorios
│   ├── services/
│   │   ├── intent_detector.py         # Detección de intenciones (NLU híbrido)
│   │   ├── user_service.py            # Identificación y contexto de usuarios
│   │   ├── client_service.py          # Búsqueda de profesionales
│   │   ├── professional_service.py    # Gestión de profesionales y horarios
│   │   ├── appointment_service.py     # CRUD de citas
│   │   ├── analytics_service.py       # Métricas
│   │   └── cache_manager.py           # Cache con TTL
│   ├── filters/
│   │   ├── filter_manager.py          # Gestor central de filtros
│   │   ├── filter_types.py            # Enums y tipos
│   │   ├── base_filter.py             # Clase base abstracta
│   │   └── concrete_filters/
│   │       ├── core_filters.py        # Fecha, hora, especialidad
│   │       └── optional_filters.py    # Zona, prepaga, género, modalidad
│   ├── core/
│   │   ├── states.py                  # Estados de la máquina de estados
│   │   ├── conversation_context.py    # Contexto acumulativo por sesión
│   │   └── validators.py              # Validaciones de entrada
│   ├── integrations/
│   │   └── google_calendar_service/   # Integración Google Calendar
│   ├── messages/                      # Templates de mensajes del bot
│   │   └── tones/
│   │       ├── coloquial.py           # Tono para centros multi-profesional
│   │       ├── freelance.py           # Tono para profesional único
│   │       └── demo.py                # Tono para demostración del producto
│   ├── database/                      # Modelos y acceso a SQLite
│   └── config/                        # Feature flags y configuración de dominio
│       └── config_validator.py        # Validación de config al boot (fail fast)
├── scripts/
│   └── ml/
│       ├── generate_training_dataset.py
│       ├── train_spacy_model.py
│       ├── evaluate_spacy_model.py
│       └── intent_classifier/model/   # Modelo entrenado (~50MB)
├── dataset/
│   └── dataset_training.jsonl         # ~1,050 ejemplos etiquetados
├── config/
│   └── google/
│       └── service-account.json       # Credenciales Google (NO commitear)
├── docs/
│   ├── ARCHITECTURE.md
│   ├── INTENT_DETECTION_SYSTEM.md
│   ├── CONVERSATION_ROUTES.md
│   └── GOOGLE_CALENDAR_SERVICE.md
├── tests/
├── docker/
│   └── docker-compose.yml
├── .env.example
├── requirements.txt
└── README.md
```

---

---

## ⚡ Activar ML en Docker (todo en uno)

El ML está desacoplado del contenedor por defecto. Para activarlo y correr el sistema híbrido completo (ML + Reglas) dentro de Docker, hay dos pasos:

**Paso 1 — Renombrar el detector híbrido**

```bash
# Desde la raíz del proyecto
mv src/integrations/ml/hybrid_intent_detector_in_docker.py \
   src/integrations/ml/hybrid_intent_detector.py
```

Este archivo es la versión del detector configurada para correr dentro del contenedor. Al renombrarlo, el `bot_controller.py` lo importa automáticamente.

**Paso 2 — Descomentar las líneas de ML en el Dockerfile**

Abrir `docker/Dockerfile` y descomentar el bloque de instalación de spaCy. Buscar la sección `Install Python dependencies` y activar las líneas comentadas que instalan spaCy y el modelo `es_core_news_sm`.

**Paso 3 — Reconstruir y levantar**

```bash
docker-compose up --build
```

Verificar que el modo híbrido está activo:

```bash
docker-compose logs | grep "HYBRID"
# Esperado: [HYBRID] ✅ Modo híbrido activo (threshold=0.7)
```

> **¿Cuándo usar cada modo?**
> - **Solo reglas (default):** imagen liviana, arranque rápido, ideal para desarrollo general
> - **Híbrido ML + Reglas:** recomendado para producción, aprovecha el 98.1% de accuracy del modelo spaCy

---

## 🚀 Quick Start

### 1. Credenciales

```bash
cp .env.example .env
# Editar .env con tus credenciales
```

Variables requeridas:

```env
# Meta Cloud API
META_PHONE_NUMBER_ID=...
META_WHATSAPP_TOKEN=...        # token permanente (no el de 24hs del panel)
META_APP_SECRET=...
META_WEBHOOK_VERIFY_TOKEN=...
META_API_VERSION=v22.0

# Google Calendar
GOOGLE_CALENDAR_CREDENTIALS_PATH=./config/google/service-account.json

# Flask
FLASK_ENV=development
PORT=5000

# Machine Learning
ML_CONFIDENCE_THRESHOLD=0.7
SPACY_MODEL_PATH=scripts/ml/intent_classifier/model/model-best
ML_ENABLED=true

# Cache
CACHE_TTL_MINUTES=15
CACHE_ENABLED=true
```

---

### 2. Google Calendar

```bash
# Copiar credenciales de Service Account
cp service-account.json config/google/

# Asegurarse que cada profesional compartió su calendario con:
# booking-service@<proyecto>.iam.gserviceaccount.com
```

---

### 3. CSV de Profesionales

El archivo `profesionales_demo.csv` debe incluir el campo `calendar_id`:

```
phone,name,email,calendar_id,...
+5491112345678,María González,maria@ex.com,maria.gonzalez@gmail.com,...
```

---

### 4. Modelo ML (opcional)

El modelo pre-entrenado viene incluido en el repo. Solo re-entrenarlo si se modifica el dataset:

```bash
cd scripts/ml

# Generar dataset
python generate_training_dataset.py
# Output: dataset_training.jsonl (~1,050 ejemplos)

# Entrenar
python train_spacy_model.py --data ../../dataset/dataset_training.jsonl
# Output: intent_classifier/model/model-best/

# Verificar accuracy
cat training_report.json | grep "best_accuracy"
# Esperado: 0.98 o superior
```

---

### 5. Levantar el Proyecto

```bash
docker-compose up --build
```

Al iniciar, el entrypoint automáticamente:
1. Inicializa la BD
2. Carga profesionales desde CSV (si BD vacía)
3. Valida configuración de Google Calendar
4. Carga modelo ML (spaCy)
5. Inicializa cache manager

Verificar logs:

```bash
docker-compose logs | grep "ML model loaded"
# Esperado: [ML] ✅ Model loaded: 98.1% accuracy

docker-compose logs | grep "CACHE"
# Esperado: [CACHE] 🚀 Initialized with TTL=15min
```

---

### 6. Exponer con Túnel Público

**Opción A: ngrok (recomendado)**
```powershell
ngrok http 5000
```

Te va a mostrar una URL tipo `https://xxxx-xxxx.ngrok-free.app`.
Dejá el túnel corriendo en esa terminal y abrí otra para seguir trabajando.

**Opción B: LocalTunnel**
```bash
pnpm add -g localtunnel
lt --port 5000
```

---

### 7. Configurar Meta

1. Ir a [developers.facebook.com](https://developers.facebook.com) → Tu App → WhatsApp → Configuración de la API
2. En **Webhooks → URL de devolución de llamada**:
   ```
   https://TU-URL-PUBLICA/webhook
   ```
3. Token de verificación: el valor de `META_WEBHOOK_VERIFY_TOKEN` en `.env`
4. Suscribir al campo `messages` → **Guardar**

---

### 8. Conectar WhatsApp

El número de Meta Business ya está activo — no requiere sandbox ni código de unión.
Enviá un mensaje al número configurado en `META_PHONE_NUMBER_ID` para probarlo.

---

## 🤖 Capacidades del Bot

### NLU Híbrido (v4.0)

El sistema detecta la intención del usuario combinando ML y reglas:

- **ML (spaCy)**: Se usa cuando `confidence ≥ 0.7`
- **Fallback a reglas**: Cuando el ML no está seguro
- **Normalización de texto**: contracciones, typos, títulos (ej: `"teno q ver al dotor"` → `"tengo que ver al doctor"`)
- **Fuzzy name matching**: 85% de similitud para nombres de profesionales

**Intents soportados:**

| Intent | Ejemplos |
|--------|----------|
| `search_professional` | "busco psicólogo", "necesito turno" |
| `view_my_appointments` | "mis turnos", "ver mi agenda" |
| `cancel_appointment` | "cancelar turno", "anular cita" |
| `reschedule_appointment` | "cambiar horario", "reagendar" |
| `confirm_appointment` | "confirmar", "sí, está bien" |
| `view_tomorrow` | "disponibles mañana" |

**Entidades extraídas:**

| Entidad | Ejemplos |
|---------|----------|
| Fecha | "mañana", "15/02", "15 de febrero" |
| Horario | "por la mañana", "de tarde" |
| Especialidad | "psicólogo", "nutricionista", "kine" |
| Nombre profesional | "con gastón blanco", "dr garcía" |
| Zona | "palermo", "zona norte" |
| Prepaga | "osde", "obra social" |
| Género | "doctora", "mujer" |
| Modalidad | "presencial", "online" |

### Flujo de Búsqueda

Los clientes pueden buscar de 3 formas:

1. **Búsqueda para HOY** → filtro rápido por horario disponible
2. **Búsqueda AVANZADA** → multi-filtro paso a paso
3. **Búsqueda RÁPIDA** → todo en un solo mensaje (ej: `"psicóloga mujer mañana a la tarde en palermo"`)

### Sistema de Filtros Modular

Los filtros son extensibles y configurables desde `src/config/domain_filters_config.py`:

- **Core**: Fecha, horario, especialidad
- **Opcionales**: Zona, prepaga, género, modalidad

### Roles

| Rol | Capacidades |
|-----|-------------|
| **Cliente** | Buscar profesionales, agendar, ver/cancelar/reagendar citas |
| **Profesional** | Ver citas agendadas, gestionar agenda vía Google Calendar |

---

## 🧪 Test Interactivo

Hay tres scripts de testing según lo que se quiera probar. Todos requieren que Docker esté corriendo.

---

### `test_bot_interactive.py` — Test del webhook HTTP *(el más usado)*

Simula mensajes de WhatsApp enviando requests HTTP al webhook real, igual a como lo haría Twilio. Es el test principal para desarrollo del flujo conversacional.

```bash
# Modo interactivo (default) — escribís mensajes manualmente
python tests/test_bot_interactive.py

# Con URL personalizada (si el puerto cambió)
python tests/test_bot_interactive.py --url http://localhost:5001/webhook

# Con teléfono de prueba distinto
python tests/test_bot_interactive.py --phone +5491199999999

# Escenario: test rápido de búsqueda (automatizado)
python tests/test_bot_interactive.py --scenario quick

# Escenario: test de filtros paso a paso (automatizado)
python tests/test_bot_interactive.py --scenario filters
```

> **Nota:** El script verifica la conexión al servidor al iniciar. Si falla, asegurarse de que `docker-compose up` esté corriendo.

---

### `test_appointments_flow.py` — Test del flujo de citas

Test interactivo específico para crear, ver, cancelar y reprogramar citas. Útil cuando se trabaja en lógica de appointments.

```bash
# Menú interactivo (muestra opciones)
python tests/test_appointments_flow.py

# Escenarios disponibles directamente:
python tests/test_appointments_flow.py --scenario booking      # Cliente reserva cita
python tests/test_appointments_flow.py --scenario manage       # Cliente ve sus citas
python tests/test_appointments_flow.py --scenario prof         # Profesional ve citas
python tests/test_appointments_flow.py --scenario interactive  # Modo manual libre
```

Teléfonos de prueba usados por defecto:

| Rol | Teléfono |
|-----|----------|
| Cliente | `+5491123456789` |
| Profesional | `+5491112345678` |

---

### `test_user_service_interactive.py` — Test del servicio de usuarios

Verifica la detección de intenciones y la identificación de roles sin levantar el bot completo. Útil para testear cambios en `user_service.py` de forma aislada.

```bash
python tests/test_user_service_interactive.py
```

Ejecuta automáticamente 4 baterías de tests (detección de intención, identificación de usuario, mensajes de bienvenida, log de acciones) y luego ofrece un modo interactivo donde podés escribir mensajes y ver qué intención detecta el sistema.

---

### Scripts auxiliares de datos

```bash
# Crear una cita de prueba en la BD (útil antes de test_appointments_flow)
python scripts/create_test_appointment.py

# Cita en 3 días a las 14:00, duración 60 min
python scripts/create_test_appointment.py --days 3 --time 14:00 --duration 60

# Crear múltiples citas de prueba de una vez
python scripts/create_test_appointment.py --multiple

# Ver citas futuras existentes sin crear nuevas
python scripts/create_test_appointment.py --list
```

---

### Evaluar el modelo ML

```bash
# Evaluar accuracy con dataset de validación
python scripts/ml/evaluate_spacy_model.py \
  --model scripts/ml/intent_classifier/model/model-best \
  --data dataset/dataset_training.jsonl

# Modo interactivo: escribís frases y ves las predicciones con score por intent
python scripts/ml/evaluate_spacy_model.py \
  --model scripts/ml/intent_classifier/model/model-best \
  --interactive
```

---

```bash
# Ver logs en tiempo real
docker-compose logs -f

# Filtrar por componente
docker-compose logs -f | grep "ML"
docker-compose logs -f | grep "CACHE"
docker-compose logs -f | grep "NLU"

# Ver profesionales cargados en BD
docker exec whatsapp-demo sqlite3 /app/data/booking.db \
  "SELECT phone, name, calendar_id FROM professionals;"

# Estadísticas de cache
docker exec whatsapp-demo python -c "
from src.services.cache_manager import cache_manager
print(cache_manager.get_stats())
"

# Enviar mensaje de prueba
curl -X POST http://localhost:5000/webhook \
  -d "From=whatsapp:+5491112345678" \
  -d "Body=turno con psicólogo mañana"

# Reiniciar servicio
docker-compose restart

# Reconstruir tras cambios
docker-compose up --build
```

---

## 🐛 Troubleshooting

### El bot no responde

1. `docker-compose ps` — verificar que el contenedor corre
2. `docker-compose logs -f` — revisar errores
3. Verificar que el túnel público está activo
4. Verificar webhook en [Meta Developer Console](https://developers.facebook.com)
5. Revisar errores en Meta → Tu App → WhatsApp → Configuración → Webhooks

### "ML model not found"

```bash
# Verificar que el modelo existe
ls scripts/ml/intent_classifier/model/model-best/

# Si no existe, re-entrenar
cd scripts/ml
python generate_training_dataset.py
python train_spacy_model.py --data ../../dataset/dataset_training.jsonl
```

### "spaCy model es_core_news_sm not found"

```bash
python -m spacy download es_core_news_sm
# O reconstruir imagen Docker:
docker-compose down && docker-compose up --build
```

### Accuracy del modelo < 95%

```bash
# Re-entrenar con más épocas
python train_spacy_model.py \
  --data ../../dataset/dataset_training.jsonl \
  --iterations 50
```

### Túnel se cae (LocalTunnel)

1. Ctrl+C y volver a ejecutar `lt --port 5000`
2. Actualizar la nueva URL en Meta Developer Console
3. Usar CloudFlare como alternativa más estable

### Puerto 5000 en uso

```yaml
# En docker-compose.yml
ports:
  - "5001:5000"
```

---

## 📚 Documentación

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — Arquitectura completa del sistema
- [`docs/INTENT_DETECTION_SYSTEM.md`](docs/INTENT_DETECTION_SYSTEM.md) — Sistema NLU/ML en detalle
- [`docs/CONVERSATION_ROUTES.md`](docs/CONVERSATION_ROUTES.md) — Flujos conversacionales y ejemplos
- [`docs/GOOGLE_CALENDAR_SERVICE.md`](docs/GOOGLE_CALENDAR_SERVICE.md) — Integración Google Calendar
- [`scripts/ml/README.md`](scripts/ml/README.md) — Entrenamiento y evaluación del modelo

---

## 🔗 Links Útiles

- [Meta Developer Console](https://developers.facebook.com/)
- [Meta WhatsApp Business API Docs](https://developers.facebook.com/docs/whatsapp)
- [spaCy Documentation](https://spacy.io/)
- [Google Calendar API](https://developers.google.com/calendar)
- [LocalTunnel](https://localtunnel.me/)
- [CloudFlare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)

---

## ✅ Checklist de Setup

- [ ] Docker instalado y corriendo
- [ ] App de Meta configurada con WhatsApp Business API y credenciales en `.env`
- [ ] `service-account.json` copiado a `config/google/`
- [ ] Profesionales con `calendar_id` en `profesionales_demo.csv`
- [ ] `docker-compose up --build` ejecutado exitosamente
- [ ] Logs muestran `ML model loaded` y `CACHE Initialized`
- [ ] Túnel público activo (LocalTunnel o CloudFlare)
- [ ] Webhook configurado en Meta Developer Console
- [ ] Mensaje de prueba enviado y respondido

---

## 📝 Notas

- **Meta Cloud API**: Integración directa sin intermediario, valida firma HMAC-SHA256
- **Modelo ML**: Pre-entrenado incluido en el repo. Solo re-entrenar si se modifica el dataset base
- **Túnel público**: Necesario para recibir webhooks de Meta en desarrollo
- **Modo development**: Activa carga automática de CSV (`FLASK_ENV=development`)
- **Certificados**: Se guardan en `./certificates/{phone}/`