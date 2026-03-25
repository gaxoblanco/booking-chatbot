# 🛡️ Resumen de Seguridad - ML Intent Service

**Configuración de seguridad implementada y recomendaciones para producción.**

---

## ✅ Estado Actual de Seguridad

### **Implementado y Listo para Usar:**

| Medida de Seguridad | Estado | Nivel |
|---------------------|--------|-------|
| API Key Authentication | ✅ Implementado | Medio |
| IP Whitelist | ✅ Implementado | Alto |
| CORS Configurado | ✅ Implementado | Bajo |
| Red Interna Docker | ✅ Implementado | Alto |
| Usuario No-Root | ✅ Implementado | Medio |
| Read-Only Filesystem | ✅ Implementado | Medio |
| Resource Limits | ✅ Implementado | Bajo |
| Log Rotation | ✅ Implementado | Bajo |
| Health Checks | ✅ Implementado | Bajo |

### **Opcional / Futuro:**

| Medida de Seguridad | Estado | Complejidad |
|---------------------|--------|-------------|
| Rate Limiting (Redis) | 📝 Planificado | Media |
| HTTPS/TLS (Nginx) | 📝 Opcional | Baja |
| Audit Logging | 📝 Opcional | Media |
| Secrets Manager | 📝 Opcional | Alta |
| WAF | 📝 Opcional | Alta |

---

## 🎯 Configuraciones Recomendadas

### **Escenario 1: Desarrollo Local** (Default)

```bash
# .env
API_KEY_ENABLED=false
IP_WHITELIST_ENABLED=false
CORS_ORIGINS=["*"]
LOG_LEVEL=DEBUG
```

**Exposición:** Puerto 8000 mapeado a localhost  
**Riesgo:** ⚠️ Bajo (solo en tu máquina)  
**Uso:** Solo para desarrollo y testing

---

### **Escenario 2: Producción - Red Interna** ⭐ RECOMENDADO

```bash
# .env.production
API_KEY_ENABLED=true
API_KEY=<generada con python app/security.py>
IP_WHITELIST_ENABLED=false
CORS_ORIGINS=["*"]
LOG_LEVEL=WARNING
```

```yaml
# docker-compose.prod.yml
expose:  # NO ports (no acceso desde internet)
  - "8000"
networks:
  - ml-network  # Red interna
```

**Exposición:** Solo contenedores en red `ml-network`  
**Riesgo:** ✅ Bajo (ideal para tu caso)  
**Uso:** Múltiples centros médicos en mismo servidor

**Por qué esta configuración:**
- ✅ **Simplicidad:** Fácil de implementar y mantener
- ✅ **Seguridad:** Servicio no accesible desde internet
- ✅ **Performance:** Sin overhead de TLS/proxy
- ✅ **Suficiente:** API Key protege entre contenedores

---

### **Escenario 3: Expuesto Externamente** (Si necesitas)

```bash
# .env.production
API_KEY_ENABLED=true
API_KEY=<generada>
IP_WHITELIST_ENABLED=true
IP_WHITELIST=["10.0.0.0/8"]
CORS_ORIGINS=["https://app.tudominio.com"]
LOG_LEVEL=WARNING
```

```yaml
# Agregar Nginx reverse proxy con:
# - HTTPS/TLS
# - Rate limiting
# - IP filtering
```

**Exposición:** Internet (mediante Nginx)  
**Riesgo:** ⚠️ Medio-Alto (requiere más configuración)  
**Uso:** Si necesitas acceso desde múltiples servidores

---

## 🚀 Quick Start de Seguridad

### 1. Generar API Key

```bash
python app/security.py
```

**Output:**
```
API Key generada:
  a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4

Agrega esta key a tu .env:
  API_KEY_ENABLED=true
  API_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4
```

### 2. Configurar .env

```bash
# Copiar template de producción
cp .env.production .env

# Editar y agregar la API key
nano .env

# Permisos restrictivos
chmod 600 .env
```

### 3. Iniciar en Modo Seguro

```bash
# Producción con red interna
docker-compose -f docker-compose.prod.yml up -d

# Verificar
docker-compose -f docker-compose.prod.yml logs | grep "API_KEY_ENABLED"
```

### 4. Actualizar Clientes

**Python:**
```python
import requests

response = requests.post(
    "http://ml-service:8000/predict",
    json={"message": "hola"},
    headers={"X-API-Key": "tu-api-key"}  # ⭐ Agregar header
)
```

**Modificar `ml_intent_detector.py` en proyecto principal:**
```python
def detect(self, message: str) -> Dict:
    response = requests.post(
        f"{self.ml_service_url}/predict",
        json={"message": message},
        headers={"X-API-Key": os.getenv('ML_API_KEY')},  # ⭐ API Key
        timeout=2
    )
```

---

## 🔐 Niveles de Protección

### Nivel 1: Sin Protección (❌ NO usar en producción)
- Sin API Key
- Puerto expuesto a internet
- CORS abierto

**Riesgo:** Cualquiera puede usar tu servicio

---

### Nivel 2: API Key (✅ Mínimo recomendado)
- API Key requerida
- Red Docker interna
- CORS configurado

**Riesgo:** Solo clientes con key válida pueden acceder

---

### Nivel 3: API Key + IP Whitelist (✅✅ Recomendado para alta seguridad)
- API Key requerida
- Solo IPs específicas permitidas
- Red Docker interna
- CORS configurado

**Riesgo:** Muy bajo, doble factor de autenticación

---

### Nivel 4: Completo (✅✅✅ Máxima seguridad)
- API Key requerida
- IP Whitelist
- Rate limiting
- HTTPS/TLS
- Nginx reverse proxy
- Audit logging

**Riesgo:** Mínimo, pero mayor complejidad

---

## 📊 Matriz de Decisión

| Necesitas... | Usar Nivel | Complejidad | Seguridad |
|--------------|-----------|-------------|-----------|
| Desarrollo local | Nivel 1 | ⭐ | ⚠️ |
| Múltiples contenedores, mismo servidor | Nivel 2 | ⭐⭐ | ✅ |
| Acceso desde múltiples servidores internos | Nivel 3 | ⭐⭐⭐ | ✅✅ |
| Acceso desde internet | Nivel 4 | ⭐⭐⭐⭐ | ✅✅✅ |

---

## 🎯 Recomendación para Tu Proyecto

**Tu caso:**
- Múltiples centros médicos (contenedores Docker)
- Todos en mismo servidor
- Sin necesidad de acceso externo

**Configuración recomendada: Nivel 2** ⭐

### Arquitectura:

```
Servidor
├── Docker Network (ml-network) - Red interna
│   ├── ml-service (puerto 8000, interno)
│   ├── centro-a (con API Key)
│   ├── centro-b (con API Key)
│   └── centro-c (con API Key)
└── Internet ❌ (sin acceso directo)
```

### Archivos a usar:

1. **docker-compose.prod.yml** - Ya configurado
2. **.env.production** - Copiar a .env y agregar API key
3. **app/security.py** - Generar API key

### Pasos:

```bash
# 1. Generar key
python app/security.py

# 2. Configurar
cp .env.production .env
nano .env  # Agregar API key

# 3. Iniciar
docker-compose -f docker-compose.prod.yml up -d

# 4. Actualizar clientes
# Modificar ml_intent_detector.py con API Key
```

---

## ✅ Checklist Pre-Producción

### Configuración:
- [ ] API key generada con `python app/security.py`
- [ ] `.env` configurado con API_KEY_ENABLED=true
- [ ] `.env` con permisos restrictivos (chmod 600)
- [ ] `.env` NO commiteado a git
- [ ] CORS configurado apropiadamente
- [ ] LOG_LEVEL=WARNING (no DEBUG)

### Docker:
- [ ] Usando `docker-compose.prod.yml`
- [ ] Puerto NO expuesto (`expose` en vez de `ports`)
- [ ] Red interna configurada
- [ ] Resource limits configurados
- [ ] Usuario no-root verificado

### Clientes:
- [ ] Todos los clientes actualizados con API Key
- [ ] API Key en variable de entorno (no hardcoded)
- [ ] Timeout configurado (2-5 segundos)
- [ ] Manejo de errores 401/403

### Testing:
- [ ] Request sin API key rechazado (401)
- [ ] Request con API key funciona (200)
- [ ] Servicio no accesible desde internet
- [ ] Health check funciona
- [ ] Logs funcionando correctamente

---

## 🔄 Mantenimiento de Seguridad

### Cada 90 días:
- [ ] Rotar API keys
- [ ] Revisar logs de acceso
- [ ] Actualizar dependencias

### Cada mes:
- [ ] Verificar logs de seguridad
- [ ] Revisar resource usage
- [ ] Backup de configuración

### Cada semana:
- [ ] Verificar health checks
- [ ] Revisar logs de errores

---

## 📞 Soporte

**Para más detalles:** Ver `SECURITY.md`

**Reportar vulnerabilidades:**
- NO abrir issues públicos
- Contactar directamente al equipo de seguridad

---

## 📚 Documentación Relacionada

- **SECURITY.md** - Guía completa de seguridad
- **ARCHITECTURE.md** - Arquitectura técnica
- **docker-compose.prod.yml** - Configuración de producción
- **.env.production** - Template de configuración segura

---

**Versión:** 1.0.0  
**Última actualización:** 2025-02-11  
**Estado:** ✅ Listo para producción
