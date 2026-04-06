# ML Intent Service

Servicio de detección de intenciones para bots de WhatsApp multi-tenant.
Parte del stack de [Viner](https://psivale.com.ar) — el turnero inteligente para centros de salud y servicios.

---

## Qué hace

Recibe un mensaje de texto y devuelve la intención del usuario con nivel de confianza.

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"message": "quiero cancelar mi turno del jueves"}'
```

```json
{
  "intent": "cancel_appointment",
  "confidence": 0.97,
  "processing_time_ms": 15
}
```

---

## Intenciones

| Intención | Descripción |
|---|---|
| `search_professional` | Buscar y reservar turno |
| `view_my_appointments` | Ver mis citas |
| `view_tomorrow` | Ver disponibilidad mañana |
| `cancel_appointment` | Cancelar turno |
| `info_center` | Info del centro o del producto |
| `greeting` | Saludo |
| `book_for_third_party` | Reservar para otra persona |
| `unknown` | Fuera de alcance |
| `agenda_view_*` / `agenda_*` | Flujo de importación de agenda (profesional) |

---

## Stack

- **FastAPI** — API REST asíncrona
- **spaCy 3.7** — modelo de clasificación de texto en español
- **Python 3.10**
- **Docker**

---

## Arrancar

```bash
docker compose up --build
```

Health check:

```bash
curl http://localhost:8000/health
```

---

## Métricas del modelo actual

| Métrica | Valor |
|---|---|
| Accuracy global | 98.1% |
| Intenciones | 14 |
| Ejemplos de entrenamiento | ~1.050 |
| Latencia p50 | 15ms |
| Latencia p95 | 35ms |

**Por intención:**

| Intención | Precision | Recall | F1 |
|---|---|---|---|
| `search_professional` | 0.98 | 0.99 | 0.98 |
| `view_my_appointments` | 0.99 | 0.98 | 0.99 |
| `cancel_appointment` | 0.97 | 0.96 | 0.97 |
| `info_center` | 0.96 | 0.98 | 0.97 |
| `view_tomorrow` | 0.98 | 0.97 | 0.98 |
| `greeting` | 1.00 | 1.00 | 1.00 |
| `unknown` | 0.92 | 0.95 | 0.93 |

> Última evaluación: Abril 2026 — dataset v2.0 (multi-dominio)

---

## Documentación

- [Arquitectura del sistema](ARQUITECTURA_ML.md)
- [Guía de reentrenamiento](scripts/REENTRENAMIENTO.md)