# 🔒 Guía de Seguridad - ML Intent Service

Configuración y mejores prácticas de seguridad para producción.

---

## 📋 Tabla de Contenidos

- [Resumen de Medidas](#resumen-de-medidas)
- [Configuración Rápida](#configuración-rápida)
- [Niveles de Seguridad](#niveles-de-seguridad)
- [Configuración Detallada](#configuración-detallada)
- [Deployment Seguro](#deployment-seguro)
- [Monitoreo](#monitoreo)
- [Checklist](#checklist)

---

## 🎯 Resumen de Medidas Implementadas

### ✅ **Medidas de Seguridad Activas:**

1. ✅ **API Key Authentication** (configurable)
2. ✅ **IP Whitelist** (opcional)
3. ✅ **CORS configurado** (no más `*`)
4. ✅ **Red interna Docker** (sin exposición pública)
5. ✅ **Usuario no-root** en contenedor
6. ✅ **Read-only filesystem** (excepto /tmp)
7. ✅ **Resource limits** (CPU/RAM)
8. ✅ **Health checks** automáticos
9. ✅ **Log rotation** automática
10. ✅ **Secrets en .env** (no en código)

### 🔄 **Medidas Pendientes (Opcional):**

- [ ] Rate limiting (implementar con Redis)
- [ ] HTTPS/TLS (con Nginx reverse proxy)
- [ ] Audit logging (registrar todos los accesos)
- [ ] Alertas de seguridad (Prometheus + Alertmanager)

---

## ⚡ Configuración Rápida

### Paso 1: Generar API Key

```bash
# Generar API key segura
python app/security.py

# Output:
# ============================================================
# 🔑 GENERADOR DE API KEYS
# ============================================================
# 
# Generando nueva API key segura...
# 
# API Key generada:
# 
#   a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4
# 
# Agrega esta key a tu .env:
# 
#   API_KEY_ENABLED=true
#   API_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4
# 
# Y compártela solo con servicios autorizados.
# ============================================================
```

### Paso 2: Configurar .env.production

```bash
# Copiar template
cp .env.production .env

# Editar y agregar la API key generada
nano .env

# Contenido:
API_KEY_ENABLED=true
API_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4
```

### Paso 3: Iniciar en modo producción

```bash
# Usar docker-compose de producción
docker-compose -f docker-compose.prod.yml up -d

# Verificar logs
docker-compose -f docker-compose.prod.yml logs -f
```

### Paso 4: Verificar seguridad

```bash
# Test 1: Sin API Key (debe fallar)
curl http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"message": "hola"}'
# Esperado: HTTP 401 Unauthorized

# Test 2: Con API Key (debe funcionar)
curl http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -H "X-API-Key: a1b2c3d4e5f6..." \
  -d '{"message": "hola"}'
# Esperado: HTTP 200 OK con predicción
```

---

## 🔐 Niveles de Seguridad

### **Nivel 1: Desarrollo Local** (Actual por defecto)

```bash
# .env
API_KEY_ENABLED=false
IP_WHITELIST_ENABLED=false
CORS_ORIGINS=["*"]
LOG_LEVEL=DEBUG
```

**Cuándo usar:** Solo en tu máquina local para desarrollo.

---

### **Nivel 2: Red Interna** ⭐ RECOMENDADO

```bash
# .env.production
API_KEY_ENABLED=true
API_KEY=tu-api-key-generada
IP_WHITELIST_ENABLED=false  # Red Docker interna ya es segura
CORS_ORIGINS=["*"]  # Puede ser * si solo hay acceso interno
LOG_LEVEL=WARNING

# docker-compose.prod.yml
expose:  # NO ports
  - "8000"
networks:
  - ml-network  # Red interna
```

**Cuándo usar:** Producción con múltiples contenedores en mismo servidor.

**Ventajas:**
- ✅ Servicio no accesible desde internet
- ✅ API Key protege contra contenedores no autorizados
- ✅ Simple de implementar

---

### **Nivel 3: Expuesto con Nginx** (Alta seguridad)

```bash
# .env.production
API_KEY_ENABLED=true
API_KEY=tu-api-key-generada
IP_WHITELIST_ENABLED=true
IP_WHITELIST=["10.0.0.0/8"]  # Solo red interna
CORS_ORIGINS=["https://app.tudominio.com"]
LOG_LEVEL=WARNING
```

```yaml
# docker-compose.prod.yml con Nginx
services:
  ml-service:
    expose:
      - "8000"
    networks:
      - ml-network
  
  nginx:
    image: nginx:alpine
    ports:
      - "443:443"  # HTTPS
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    networks:
      - ml-network
      - public
```

**Cuándo usar:** Si necesitas exponer el servicio externamente.

---

## ⚙️ Configuración Detallada

### 1. API Key Authentication

**Habilitar:**

```bash
# .env
API_KEY_ENABLED=true
API_KEY=tu-api-key-generada-con-python-app-security-py
```

**Uso desde clientes:**

```python
# Python
import requests

response = requests.post(
    "http://ml-service:8000/predict",
    json={"message": "hola"},
    headers={"X-API-Key": "tu-api-key"}
)
```

```bash
# cURL
curl -X POST http://ml-service:8000/predict \
  -H "Content-Type: application/json" \
  -H "X-API-Key: tu-api-key" \
  -d '{"message": "hola"}'
```

**Rotación de keys:**

```bash
# 1. Generar nueva key
python app/security.py

# 2. Actualizar .env con nueva key
nano .env

# 3. Reiniciar servicio
docker-compose -f docker-compose.prod.yml restart

# 4. Actualizar clientes con nueva key
# 5. Revocar key antigua (eliminar de backups)
```

---

### 2. IP Whitelist

**Habilitar:**

```bash
# .env
IP_WHITELIST_ENABLED=true
# Lista de IPs/subredes permitidas (formato JSON)
IP_WHITELIST=["172.20.0.0/16","10.0.0.0/8"]
```

**Uso:**

- Solo IPs en la whitelist pueden hacer requests
- Útil si quieres restricción adicional además de API Key
- Verificar IPs de tus contenedores:

```bash
docker inspect whatsapp-bot | grep IPAddress
# Output: "IPAddress": "172.20.0.3"

# Agregar a whitelist:
IP_WHITELIST=["172.20.0.0/16"]
```

---

### 3. CORS

**Configuración segura:**

```bash
# .env - Para red interna (puede ser *)
CORS_ORIGINS=["*"]

# .env - Para expuesto públicamente
CORS_ORIGINS=["https://app.tudominio.com","https://admin.tudominio.com"]
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOW_METHODS=["GET","POST"]
CORS_ALLOW_HEADERS=["X-API-Key","Content-Type"]
```

---

### 4. Red Docker Interna

**docker-compose.prod.yml:**

```yaml
services:
  ml-service:
    expose:  # ⭐ NO "ports"
      - "8000"
    networks:
      - ml-network

networks:
  ml-network:
    driver: bridge
    internal: true  # ⭐ Sin acceso a internet externo
```

**Ventajas:**
- ✅ Servicio no accesible desde internet
- ✅ Solo contenedores en `ml-network` pueden conectarse
- ✅ Sin configuración de firewall adicional

---

### 5. Usuario No-Root

**Ya implementado en Dockerfile:**

```dockerfile
# Crear usuario no-root
RUN useradd -m -u 1000 mluser

# Cambiar a usuario no-root
USER mluser
```

**Verificar:**

```bash
docker exec ml-intent-service-prod whoami
# Output: mluser (no root)
```

---

### 6. Read-Only Filesystem

**docker-compose.prod.yml:**

```yaml
services:
  ml-service:
    read_only: true  # ⭐ Filesystem read-only
    tmpfs:
      - /tmp  # Solo /tmp es escribible
```

**Ventajas:**
- ✅ Previene modificaciones al filesystem
- ✅ Protege contra malware/exploits
- ✅ Inmutabilidad del contenedor

---

## 🚀 Deployment Seguro

### Arquitectura Recomendada para Producción

```
┌────────────────────────────────────────────────────────────┐
│  SERVIDOR / HOST                                           │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  Red Pública (public)                                │ │
│  │                                                       │ │
│  │  ┌────────────┐                                      │ │
│  │  │   Nginx    │ HTTPS/TLS, Rate Limiting             │ │
│  │  │ (opcional) │ IP Filtering                         │ │
│  │  └─────┬──────┘                                      │ │
│  └────────┼───────────────────────────────────────────────┘ │
│           │                                                │
│  ┌────────▼───────────────────────────────────────────────┐ │
│  │  Red Interna (ml-network)                            │ │
│  │                                                       │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐           │ │
│  │  │ Centro A │  │ Centro B │  │ Centro C │           │ │
│  │  │  (con    │  │  (con    │  │  (con    │           │ │
│  │  │ API Key) │  │ API Key) │  │ API Key) │           │ │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘           │ │
│  │       │             │             │                  │ │
│  │       │    X-API-Key Header       │                  │ │
│  │       └─────────────┼─────────────┘                  │ │
│  │                     │                                │ │
│  │              ┌──────▼──────┐                         │ │
│  │              │ ML Service  │                         │ │
│  │              │   :8000     │                         │ │
│  │              │ (interno)   │                         │ │
│  │              └─────────────┘                         │ │
│  └──────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────┘

Internet ❌ NO puede acceder directamente al ML Service
```

### Pasos de Deployment:

#### 1. Preparar entorno

```bash
# En servidor de producción
git clone <repo>
cd ml-intent-service

# Copiar modelo
scp -r modelo-entrenado/ servidor:/path/to/ml-intent-service/models/

# Crear .env de producción
cp .env.production .env

# Generar API key
python app/security.py
# Agregar output a .env
```

#### 2. Configurar secretos

```bash
# NO commitear .env a git
echo ".env" >> .gitignore

# Permisos restrictivos
chmod 600 .env

# Solo usuario propietario puede leer
ls -la .env
# -rw------- 1 user user 1234 Feb 11 10:00 .env
```

#### 3. Iniciar servicios

```bash
# Producción
docker-compose -f docker-compose.prod.yml up -d

# Verificar
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs | grep "Modelo cargado"
```

#### 4. Verificar seguridad

```bash
# Test desde otro contenedor en misma red
docker exec whatsapp-bot curl -X POST http://ml-service:8000/predict \
  -H "Content-Type: application/json" \
  -H "X-API-Key: tu-api-key" \
  -d '{"message": "hola"}'

# Test desde internet (debe fallar si no expusiste puerto)
curl http://IP-SERVIDOR:8000/health
# curl: (7) Failed to connect to IP-SERVIDOR port 8000: Connection refused
```

---

## 📊 Monitoreo de Seguridad

### Logs a Revisar

```bash
# Ver intentos de acceso sin API key
docker-compose -f docker-compose.prod.yml logs | grep "401"

# Ver IPs bloqueadas
docker-compose -f docker-compose.prod.yml logs | grep "IP not authorized"

# Ver todas las requests
docker-compose -f docker-compose.prod.yml logs | grep "POST /predict"
```

### Alertas Recomendadas

- ❌ Más de 10 requests 401 en 1 minuto
- ❌ Requests desde IPs no esperadas
- ❌ Servicio caído por más de 2 minutos
- ❌ Uso de CPU/RAM >90% por más de 5 minutos

---

## ✅ Checklist de Seguridad

### Pre-Deployment

- [ ] API key generada con `python app/security.py`
- [ ] `.env` configurado con API_KEY_ENABLED=true
- [ ] `.env` con permisos restrictivos (chmod 600)
- [ ] `.env` NO commiteado a git
- [ ] CORS configurado (no `*` si expuesto)
- [ ] LOG_LEVEL=WARNING (no DEBUG)
- [ ] Usuario no-root verificado
- [ ] Read-only filesystem habilitado

### Post-Deployment

- [ ] Health check responde correctamente
- [ ] Request sin API key rechazado (401)
- [ ] Request con API key funciona (200)
- [ ] Servicio no accesible desde internet (si red interna)
- [ ] Logs funcionando y rotando
- [ ] Resource limits configurados
- [ ] Backup de .env en lugar seguro

### Mantenimiento Continuo

- [ ] Rotar API keys cada 90 días
- [ ] Revisar logs de seguridad semanalmente
- [ ] Actualizar dependencias mensualmente
- [ ] Backup del modelo regularmente
- [ ] Test de penetración trimestral

---

## 🔧 Troubleshooting de Seguridad

### Problema: "401 Unauthorized" en requests válidos

```bash
# Verificar que API key está configurada
cat .env | grep API_KEY

# Verificar que cliente envía header correcto
curl -v http://ml-service:8000/predict \
  -H "X-API-Key: tu-key" \
  ... | grep "X-API-Key"

# Verificar logs del servicio
docker logs ml-intent-service-prod | grep "API key"
```

### Problema: "403 Forbidden" (IP bloqueada)

```bash
# Ver IP del cliente
docker inspect whatsapp-bot | grep IPAddress

# Verificar whitelist
cat .env | grep IP_WHITELIST

# Agregar IP a whitelist
# Editar .env y reiniciar
```

### Problema: API key comprometida

```bash
# 1. Generar nueva key
python app/security.py

# 2. Actualizar .env INMEDIATAMENTE
nano .env

# 3. Reiniciar servicio
docker-compose -f docker-compose.prod.yml restart

# 4. Actualizar TODOS los clientes con nueva key

# 5. Revisar logs para detectar uso indebido
docker logs ml-intent-service-prod | grep "401"
```

---

## 📖 Referencias

- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [Docker Security Best Practices](https://docs.docker.com/engine/security/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)

---

## 📞 Contacto de Seguridad

Para reportar vulnerabilidades de seguridad:
- Email: security@tudominio.com
- NO abrir issues públicos en GitHub para vulnerabilidades

---

**Última actualización:** 2025-02-11  
**Versión:** 1.0.0
