# 🖥️ Configuración del Servidor — WhatsApp Booking Bot
**Fecha:** Mayo 2026  
**Servidor:** VPS Donweb #4575917 — `vps-4575917-x.dattaweb.com`  
**IP:** `149.50.128.92`

---

## 📋 Especificaciones del Servidor

| Parámetro | Valor |
|---|---|
| Proveedor | Donweb Cloud IaaS |
| SO | Ubuntu 22.04 LTS (64 bits) |
| Imagen | Ubuntu2204-64-min |
| Acceso SSH | `ssh -p5119 root@149.50.128.92` |

---

## 🏗️ Stack del Proyecto

| Componente | Tecnología |
|---|---|
| Backend | Python 3.10 / Flask |
| Mensajería | Twilio WhatsApp API |
| NLU/ML | spaCy 3.7.2 + TextCatEnsemble (99.2% accuracy) |
| Base de datos | SQLite |
| Calendario | Google Calendar API (Service Account) |
| Sesiones | Redis 7 (fallback: memoria) |
| Contenedores | Docker 29.4.3 + Docker Compose v5.1.3 |

---

## 🐳 Arquitectura de Contenedores

```
Twilio WhatsApp
      │
      ▼ HTTPS (443)
   Nginx (proxy)
      │
      ├── psivale.com.ar/webhook      → Bot Producción  (localhost:5000)
      ├── gaxoblanco.com/webhook      → Bot Demo        (localhost:5001)
      │
      └── [interno] ml-service:8000  → ML/NLU spaCy    (solo red Docker)
```

### Puertos internos Docker

| Contenedor | Puerto interno | Expuesto al exterior |
|---|---|---|
| Bot Producción (psivale) | 5000 | ❌ Solo vía Nginx |
| Bot Demo (gaxoblanco) | 5001 | ❌ Solo vía Nginx |
| ML Service (spaCy) | 8000 | ❌ Solo red interna Docker |
| Redis | 6379 | ❌ Solo red interna Docker |

---

## 🌐 Configuración Nginx

### Sitios activos (`/etc/nginx/sites-enabled/`)

| Archivo | Dominio | Función |
|---|---|---|
| `psivale-web` | psivale.com.ar | Web estática + webhook bot producción |
| `gaxoblanco-web` | gaxoblanco.com | Web estática + webhook bot demo |
| `demo.gaxoblanco.com` | demo.gaxoblanco.com | Sitio demo estático |

### Routing de webhooks

```nginx
# psivale.com.ar
location /webhook        → proxy_pass http://localhost:5000/webhook

# gaxoblanco.com
location /webhook        → proxy_pass http://localhost:5001/webhook
```

### SSL

| Dominio | Certificado | Vencimiento |
|---|---|---|
| gaxoblanco.com | Let's Encrypt RSA | 21 Jul 2026 |
| psivale.com.ar | Let's Encrypt ECDSA | 25 Jun 2026 |

> ⚠️ Renovar certificados antes de su vencimiento con `certbot renew`

---

## 🔒 Seguridad Aplicada

### 1. Firewall UFW

**Estado:** Activo — política por defecto: `deny incoming`

| Puerto | Protocolo | Acción | Servicio |
|---|---|---|---|
| 80 | TCP | ALLOW | Nginx HTTP |
| 443 | TCP | ALLOW | Nginx HTTPS |
| 5119 | TCP | ALLOW | SSH personalizado |
| 22 | TCP | DENY | SSH estándar (bloqueado) |
| 5000 | TCP | DENY | Flask bot (solo vía Nginx) |
| 5001 | TCP | DENY | Flask demo (solo vía Nginx) |
| 8000 | TCP | DENY | ML service (solo interno) |
| 25 | TCP | DENY | SMTP (no usado) |

### 2. SSH Hardening

- Puerto cambiado de 22 → **5119**
- Autenticación por **clave pública SSH** (RSA 4096 bits)
- Autenticación por contraseña **deshabilitada**
- Clave privada: `donweb.ppk` (almacenada localmente en cliente)

### 3. Fail2ban

**Estado:** Activo — protección contra fuerza bruta

| Jail | Protege | Max intentos | Ban |
|---|---|---|---|
| `sshd` | SSH puertos 22 y 5119 | 3 intentos | 24 horas |
| `nginx-http-auth` | Autenticación Nginx | 5 intentos | 1 hora |
| `nginx-limit-req` | Rate limit Nginx | 10 intentos | 1 hora |

Configuración en `/etc/fail2ban/jail.local`:
- `bantime` = 3600s (1 hora, SSH = 86400s)
- `findtime` = 600s (ventana de 10 minutos)
- `maxretry` = 5 (SSH = 3)

### 4. Actualizaciones del Sistema

- Sistema actualizado al **14 de Mayo 2026**
- Nginx actualizado a `1.18.0-6ubuntu14.11`
- Kernel al día (no requirió reboot)
- **Unattended Upgrades** habilitado para parches de seguridad automáticos

### 5. Seguridad en Docker

- ML service accesible **únicamente por red interna Docker** (`http://ml-service:8000`)
- Puertos de contenedores **no expuestos directamente** al exterior
- Todo el tráfico externo pasa por **Nginx con SSL**

---

## 📡 Configuración Twilio

| Número | Webhook URL | Bot |
|---|---|---|
| Producción | `https://psivale.com.ar/webhook` | Bot psivale (puerto 5000) |
| Demo | `https://gaxoblanco.com/webhook` | Bot demo (puerto 5001) |

Método: `POST`

---

## 🔧 Comandos de Operación

### Ver estado general
```bash
# Contenedores corriendo
docker ps --format "table {{.Names}}\t{{.Ports}}\t{{.Status}}"

# Estado del firewall
ufw status verbose

# IPs baneadas por fail2ban
fail2ban-client status sshd

# Intentos de ataque SSH
grep "Failed password" /var/log/auth.log | tail -20
```

### Gestión de contenedores
```bash
# Ver logs del bot en tiempo real
docker compose logs -f

# Reiniciar bot
docker compose restart

# Reconstruir tras cambios
docker compose up --build -d
```

### Mantenimiento del servidor
```bash
# Actualizar sistema
apt update && apt upgrade -y

# Renovar certificados SSL
certbot renew

# Ver estado de nginx
nginx -t
nginx -s reload
```

---

## 📅 Tareas de Mantenimiento Periódico

| Tarea | Frecuencia | Comando |
|---|---|---|
| Actualizar sistema | Mensual | `apt update && apt upgrade -y` |
| Renovar SSL psivale.com.ar | Antes del 25 Jun 2026 | `certbot renew` |
| Renovar SSL gaxoblanco.com | Antes del 21 Jul 2026 | `certbot renew` |
| Verificar fail2ban | Semanal | `fail2ban-client status sshd` |
| Revisar logs de ataque | Semanal | `grep "Failed password" /var/log/auth.log` |

---

*Documento generado el 14 de Mayo 2026*
