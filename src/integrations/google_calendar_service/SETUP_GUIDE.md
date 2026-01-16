# 🚀 GUÍA DE CONFIGURACIÓN INICIAL
## Google Calendar Service

Esta guía te llevará paso a paso por la configuración inicial del servicio.

---

## 📋 REQUISITOS PREVIOS

- Cuenta de Google (Gmail)
- Acceso a [Google Cloud Console](https://console.cloud.google.com/)
- Python 3.10 o superior instalado

---

## ⚙️ CONFIGURACIÓN PASO A PASO

### 1️⃣ Crear Proyecto en Google Cloud Console

1. Ir a https://console.cloud.google.com/
2. Click en el selector de proyectos (arriba a la izquierda)
3. Click en "NUEVO PROYECTO"
4. Nombre del proyecto: `booking-calendar-service` (o el que prefieras)
5. Click en "CREAR"
6. Esperar unos segundos a que se cree el proyecto

**✅ Resultado:** Tendrás un proyecto de Google Cloud creado

---

### 2️⃣ Habilitar Google Calendar API

1. En el menú lateral, ir a: **APIs y servicios > Biblioteca**
2. Buscar: "Google Calendar API"
3. Click en "Google Calendar API"
4. Click en el botón **"HABILITAR"**
5. Esperar a que se habilite (toma unos segundos)

**✅ Resultado:** La API de Calendar estará habilitada para tu proyecto

---

### 3️⃣ Crear Service Account

1. En el menú lateral, ir a: **APIs y servicios > Credenciales**
2. Click en **"CREAR CREDENCIALES"** (arriba)
3. Seleccionar: **"Cuenta de servicio"**
4. Completar el formulario:
   - **Nombre:** `booking-service`
   - **ID:** Se genera automáticamente
   - **Descripción:** `Service Account para sistema de reservas`
5. Click en **"CREAR Y CONTINUAR"**
6. En "Selecciona una función": Saltar este paso (no es necesario), click en **"CONTINUAR"**
7. En "Otorgar acceso": Saltar este paso, click en **"LISTO"**

**✅ Resultado:** Tendrás una Service Account creada

---

### 4️⃣ Descargar Credenciales JSON

1. En la página de Credenciales, verás tu Service Account listada
2. Click en el **email de la Service Account** (algo como `booking-service@tu-proyecto.iam.gserviceaccount.com`)
3. Ir a la pestaña **"CLAVES"**
4. Click en **"AGREGAR CLAVE"** > **"Crear clave nueva"**
5. Seleccionar tipo: **JSON**
6. Click en **"CREAR"**
7. Se descargará automáticamente un archivo JSON

**⚠️ IMPORTANTE:** 
- Guarda este archivo en un lugar seguro
- NO lo subas a git ni lo compartas públicamente
- Renombralo a: `service-account.json`

**✅ Resultado:** Tendrás el archivo de credenciales descargado

---

### 5️⃣ Configurar Estructura de Directorios

En tu proyecto, crea la siguiente estructura:

```bash
mkdir -p config/google
```

Luego mueve el archivo descargado:

```bash
mv ~/Downloads/tu-proyecto-xxxxx.json config/google/service-account.json
```

**✅ Resultado:** Credenciales en la ubicación correcta

---

### 6️⃣ Instalar Dependencias Python

```bash
# Ir al directorio del módulo
cd google_calendar_service

# Instalar dependencias
pip install -r requirements.txt
```

**✅ Resultado:** Todas las librerías instaladas

---

### 7️⃣ Compartir Calendario con Service Account

**CADA PROFESIONAL debe hacer esto:**

1. Abrir Google Calendar: https://calendar.google.com
2. En el panel izquierdo, buscar "Mis calendarios"
3. Pasar el mouse sobre el calendario que quieres compartir
4. Click en los **tres puntos** (⋮)
5. Seleccionar **"Configuración y uso compartido"**
6. Scroll hasta **"Compartir con personas específicas"**
7. Click en **"+ Agregar personas"**
8. Pegar el email de la Service Account:
   ```
   booking-service@tu-proyecto.iam.gserviceaccount.com
   ```
   (Lo encuentras en Google Cloud Console > Service Account)
9. Permisos: Seleccionar **"Hacer cambios en eventos"**
10. Click en **"Enviar"**

**⚠️ Nota:** 
- Los permisos pueden tardar 1-2 minutos en propagarse
- Cada profesional debe repetir este proceso con SU calendario

**✅ Resultado:** La Service Account tiene acceso al calendario

---

### 8️⃣ Probar la Conexión

Ejecutar el script de prueba:

```bash
cd google_calendar_service/tests
python test_connection.py
```

**Salida esperada:**
```
======================================================================
PRUEBA DE CONEXIÓN CON GOOGLE CALENDAR API
======================================================================

📋 Paso 1: Cargando credenciales...
✅ Archivo de credenciales encontrado
📧 Service Account Email: booking-service@tu-proyecto.iam.gserviceaccount.com
🏗️  Project ID: tu-proyecto

🔑 Paso 2: Autenticando con Google...
✅ Credenciales obtenidas exitosamente
✅ Credenciales validadas correctamente

📅 Paso 3: Conectando con Google Calendar API...
✅ Cliente de Calendar API creado exitosamente

📋 Paso 4: Listando calendarios accesibles...
✅ Se encontraron 1 calendario(s):

1. Mi Calendario
   ID: profesional@gmail.com
   Rol: writer
   Zona horaria: America/Argentina/Buenos_Aires

======================================================================
✅ CONEXIÓN EXITOSA
======================================================================
```

**✅ Resultado:** Todo configurado correctamente!

---

## 🔧 TROUBLESHOOTING

### ❌ Error: "Archivo de credenciales no encontrado"

**Solución:**
```bash
# Verificar que el archivo existe
ls -la config/google/service-account.json

# Si no existe, repetir pasos 4 y 5
```

---

### ❌ Error: "API not enabled"

**Solución:**
1. Ir a Google Cloud Console
2. Verificar que estás en el proyecto correcto (arriba a la izquierda)
3. Repetir paso 2 (Habilitar Google Calendar API)

---

### ❌ Error: "No se encontraron calendarios accesibles"

**Solución:**
1. Verificar que compartiste el calendario (paso 7)
2. Esperar 1-2 minutos para que se propaguen los permisos
3. Verificar que el email de Service Account sea correcto
4. Verificar que los permisos sean "Hacer cambios en eventos"

---

### ❌ Error: "Insufficient Permission" (403)

**Solución:**
- Los permisos del calendario son insuficientes
- Repetir paso 7, asegurándose de dar permisos "Hacer cambios en eventos"

---

## ✅ VERIFICACIÓN FINAL

Checklist antes de continuar:

- [ ] Proyecto creado en Google Cloud Console
- [ ] Google Calendar API habilitada
- [ ] Service Account creada
- [ ] Archivo `service-account.json` descargado y en `config/google/`
- [ ] Dependencias Python instaladas (`pip install -r requirements.txt`)
- [ ] Al menos un calendario compartido con la Service Account
- [ ] Script `test_connection.py` ejecutado exitosamente

Si todos los ítems están marcados: **¡Estás listo para usar el servicio! 🎉**

---

## 📞 ¿NECESITAS AYUDA?

Si algo no funciona, revisa los logs del script de prueba y compara con esta guía.

**Email de Service Account:**
Lo encuentras en: Google Cloud Console > IAM y administración > Cuentas de servicio

**ID del Proyecto:**
Lo encuentras en: Google Cloud Console (arriba, al lado del nombre del proyecto)
