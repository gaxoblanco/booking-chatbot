# WhatsApp Booking Bot

Chatbot minimalista de WhatsApp para conectar profesionales con clientes.

---

## 🚀 Quick Start

### 1. Configurar Credenciales

```bash
# Copiar template
cp .env.example .env

# Editar .env con tus credenciales de Twilio
# TWILIO_ACCOUNT_SID=ACxxxx...
# TWILIO_AUTH_TOKEN=xxxx...
```

Obtén tus credenciales en: [https://console.twilio.com/](https://console.twilio.com/)

---

### 2. Levantar el Proyecto

```bash
# Construir e iniciar
docker-compose up --build

# O en modo detached
docker-compose up -d
```

El bot estará corriendo en: `http://localhost:5000`

---

### 3. Exponer con Túnel Público

**Opción A: LocalTunnel (simple)**
```bash
# Instalar
npm install -g localtunnel

# Ejecutar
lt --port 5000
```

**Test interactivo**: [https://localtunnel.me/](https://localtunnel.me/)
```bash
python tests/test_bot_interactive.py --url http://localhost:5001/webhook
docker exec whatsapp-demo python -m src.services.reminder_service
```

**Opción B: CloudFlare (más estable)**
```powershell
# Descargar cloudflared.exe y ejecutar:
.\cloudflared.exe tunnel --url http://localhost:5000
```

**Copia la URL pública** que te dan (ej: `https://abc123.loca.lt`)

---

### 4. Configurar Twilio

1. Ve a: [Twilio Console - WhatsApp Sandbox](https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn)
2. En **"Sandbox settings"** → **"When a message comes in"**:
   ```
   https://TU-URL-PUBLICA.loca.lt/webhook
   ```
3. Método: **POST**
4. Click **Save**

---

### 5. Conectar WhatsApp

1. En Twilio Console verás un número (ej: `+1 813 608 0792`)
2. Y un código (ej: `join happy-elephant`)
3. Desde tu WhatsApp, envía el código al número
4. Espera confirmación

---

### 6. ¡Probar!

Envía cualquier mensaje al número de Twilio:
```
Hola bot
```

Deberías recibir un echo de tu mensaje.

---

## 📋 Comandos Útiles

```bash
# Ver logs en tiempo real
docker-compose logs -f

# Reiniciar servicio
docker-compose restart

# Detener todo
docker-compose down

# Reconstruir después de cambios
docker-compose up --build
```

---

## 🐛 Troubleshooting

### El bot no responde

1. ✅ Verifica que Docker está corriendo: `docker-compose ps`
2. ✅ Verifica logs: `docker-compose logs -f`
3. ✅ Verifica túnel público: `curl https://TU-URL/`
4. ✅ Verifica webhook en Twilio Console
5. ✅ Verifica errores en Twilio: [Monitor Logs](https://console.twilio.com/us1/monitor/logs/errors)

### Túnel se cae (LocalTunnel)

LocalTunnel gratuito es inestable. Soluciones:

1. **Reiniciar túnel**: Ctrl+C y volver a ejecutar `lt --port 5000`
2. **Actualizar URL** en Twilio con la nueva URL
3. **Usar CloudFlare** (más estable)

### Puerto 5000 en uso

```bash
# Cambiar puerto en docker-compose.yml
ports:
  - "5001:5000"  # Usar 5001 en lugar de 5000

# Reiniciar
docker-compose up
```

---

## 📁 Estructura del Proyecto

```
booking-chatbot/
├── .env                    # Credenciales (NO commitear)
├── .env.example            # Template de credenciales
├── docker-compose.yml      # Configuración Docker
├── Dockerfile              # Imagen del contenedor
├── requirements.txt        # Dependencias Python
├── config.py               # Carga de configuración
├── whatsapp_handler.py     # Webhook principal
├── certificates/           # Archivos subidos (auto-creado)
└── README.md               # Este archivo
```

---

## 🔗 Links Útiles

- [Twilio Console](https://console.twilio.com/)
- [Twilio WhatsApp Docs](https://www.twilio.com/docs/whatsapp)
- [LocalTunnel](https://localtunnel.me/)
- [CloudFlare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)

---

## 📝 Notas

- **Sandbox de Twilio**: Gratis pero con limitaciones (24h de sesión, números limitados)
- **Túnel público**: Necesario para recibir webhooks de Twilio
- **Modo development**: Usa Flask dev server (NO para producción)
- **Certificados**: Se guardan en `./certificates/{phone}/`

---

## ✅ Checklist de Setup

- [ ] Docker instalado y corriendo
- [ ] Cuenta de Twilio creada
- [ ] Archivo `.env` configurado con credenciales
- [ ] `docker-compose up` ejecutado exitosamente
- [ ] Túnel público activo (LocalTunnel o CloudFlare)
- [ ] Webhook configurado en Twilio
- [ ] WhatsApp conectado al sandbox (enviado `join <code>`)
- [ ] Mensaje de prueba enviado y respondido

---
