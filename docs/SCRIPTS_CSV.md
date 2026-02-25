# 📋 Scripts de carga masiva desde CSV

---

## 🚀 Comandos clave

```bash
# ── PROFESIONALES ──────────────────────────────────────────────────────────────

# Cargar (reintenta Calendar 4 veces, envía email si falla)
docker exec -it whatsapp-demo python scripts/load_professionals_from_csv.py /app/data/csv/profesionales_demo.csv

# Simular sin guardar
docker exec -it whatsapp-demo python scripts/load_professionals_from_csv.py /app/data/csv/profesionales_demo.csv --dry-run

# Generar template CSV de ejemplo
docker exec -it whatsapp-demo python scripts/load_professionals_from_csv.py --template


# ── PACIENTES ──────────────────────────────────────────────────────────────────

# Cargar (interactivo: pregunta CSV y duración)
docker exec -it whatsapp-demo python scripts/load_patients_from_csv.py

# Cargar con path directo (solo pregunta duración)
docker exec -it whatsapp-demo python scripts/load_patients_from_csv.py /app/data/csv/pacientes_demo.csv

# Cargar con todo fijo, sin preguntas
docker exec -it whatsapp-demo python scripts/load_patients_from_csv.py /app/data/csv/pacientes_demo.csv --weeks 12

# Simular sin guardar
docker exec -it whatsapp-demo python scripts/load_patients_from_csv.py /app/data/csv/pacientes_demo.csv --dry-run

# Generar template CSV de ejemplo
docker exec -it whatsapp-demo python scripts/load_patients_from_csv.py --template


# ── LIMPIEZA ───────────────────────────────────────────────────────────────────

# Borrar pacientes (usa el mismo CSV que se usó para cargar)
docker exec -it whatsapp-demo python scripts/delete_patients_from_csv.py /app/data/csv/pacientes_demo.csv

# Simular borrado sin eliminar nada
docker exec -it whatsapp-demo python scripts/delete_patients_from_csv.py /app/data/csv/pacientes_demo.csv --dry-run


# ── EMAILS DE INVITACIÓN CALENDAR (standalone) ─────────────────────────────────

# Enviar a profesionales sin calendar_id configurado
docker exec -it whatsapp-demo python scripts/send_calendar_invitations.py

# Enviar a todos
docker exec -it whatsapp-demo python scripts/send_calendar_invitations.py --all
```

---

## ⚠️ Regla de oro

Siempre ejecutar **dentro del Docker** con `-it` para modo interactivo.

```bash
# ✅ Correcto
docker exec -it whatsapp-demo python scripts/load_patients_from_csv.py

# ❌ Incorrecto — falla por BD desactualizada o sin terminal
python scripts/load_patients_from_csv.py
docker exec whatsapp-demo python scripts/load_patients_from_csv.py   # sin -it falla el input()
```

Los CSV van en `data/` en la raíz del proyecto. Se montan automáticamente en `/app/data/csv/` via `docker-compose.yml`.

---

## 📂 Scripts

### `load_professionals_from_csv.py`

Carga o actualiza profesionales desde CSV. Por cada uno valida acceso al Google Calendar con **4 reintentos** (2s → 5s → 10s → 20s). Si agota los intentos, envía email al profesional con instrucciones para compartir el calendario (requiere SMTP configurado en `.env`).

**Columnas requeridas:** `phone`, `name`, `email`, `calendar_email`, `zone` (`norte`/`sur`), `gender` (`m`/`f`), `accept_prepaga` (`1`/`0`), `category`

---

### `load_patients_from_csv.py`

Carga pacientes y crea un evento **recurrente semanal** (RRULE) en el Google Calendar del profesional asignado. El horario de fin se calcula automáticamente (`start_time` + `duration_minutes`). Sin argumentos, pregunta el CSV y la duración de forma interactiva.

**Duración interactiva:**
```
1. 4 semanas   (~1 mes)
2. 12 semanas  (~3 meses, recomendado)
3. Sin límite  (~10 años)
```

**Columnas requeridas:** `phone`, `name`, `professional_phone`, `weekday`, `start_time`, `duration_minutes`

**Columnas opcionales:** `email`, `modality` (`presencial`/`virtual`), `notes`

**Días válidos:** `lunes`, `martes`, `miércoles`, `jueves`, `viernes`, `sábado`, `domingo`

---

### `delete_patients_from_csv.py`

Toma el mismo CSV usado para cargar y elimina todo: cancela los eventos en Google Calendar y borra clientes y citas de la BD. Si el evento ya no existe en Calendar (borrado a mano), continúa sin romper.

---

### `send_calendar_invitations.py`

Envía email HTML a profesionales con instrucciones para compartir su Google Calendar. Por defecto solo envía a los que no tienen `calendar_id` configurado. Requiere SMTP configurado en `.env`.

**Variables `.env` requeridas:**
```
SMTP_HOST=mail.miweb.com
SMTP_PORT=587
SMTP_USER=sistema@miweb.com
SMTP_PASSWORD=tu_password
SMTP_FROM_NAME=Mi Sistema de Turnos
```

---

## 🔧 Troubleshooting

| Error | Causa | Fix |
|-------|-------|-----|
| `sqlite3.OperationalError: no such column` | Script corrido fuera del Docker | Usar `docker exec -it whatsapp-demo python scripts/...` |
| `EOFError: EOF when reading a line` | Falta `-it` en el comando | Agregar `-it` al `docker exec` |
| `❌ Archivo no encontrado` | Ruta incorrecta | Verificar con `docker exec whatsapp-demo ls /app/data/csv/` |
| `CHECK constraint failed: zone` | Valor de zona inválido en CSV | Solo se aceptan `norte` y `sur` |
| `Profesional no encontrado` | No se cargaron profesionales primero | Correr `load_professionals_from_csv.py` antes |
| `calendar_id no configurado` | Calendar falló al validar | Correr `load_professionals_from_csv.py` nuevamente con conexión |
| `403 Forbidden` en Calendar | Sin permisos de Service Account | El profesional debe compartir con "Hacer cambios en eventos" |