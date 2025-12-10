# WhatsApp Bot Webhook - Setup Guide

Complete guide to set up and test the WhatsApp webhook integration using Twilio, Docker, and ngrok.

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Project Structure](#project-structure)
3. [Twilio Setup](#twilio-setup)
4. [Local Setup](#local-setup)
5. [Docker Setup](#docker-setup)
6. [ngrok Setup](#ngrok-setup)
7. [Testing](#testing)
8. [Troubleshooting](#troubleshooting)
9. [Next Steps](#next-steps)

---

## 🔧 Prerequisites

Before starting, ensure you have:

- [x] **Docker** installed ([Download](https://docs.docker.com/get-docker/))
- [x] **Docker Compose** installed (included with Docker Desktop)
- [x] **ngrok** account and CLI ([Download](https://ngrok.com/download))
- [x] **Twilio** account ([Sign up](https://www.twilio.com/try-twilio))
- [x] **WhatsApp** installed on your phone

---

## 📁 Project Structure

```
whatsapp-test/
├── Dockerfile                 # Container definition
├── docker-compose.yml         # Service orchestration
├── whatsapp_handler.py        # Flask webhook (main file)
├── config.py                  # Configuration loader
├── requirements.txt           # Python dependencies
├── .env.example              # Environment template
├── .env                      # Your credentials (create this)
├── certificates/             # Uploaded files storage
└── README_WHATSAPP.md        # This file
```

---

## 🌐 Twilio Setup

### Step 1: Create Twilio Account

1. Go to [https://www.twilio.com/try-twilio](https://www.twilio.com/try-twilio)
2. Sign up (free trial gives $15 credit)
3. Verify your email and phone number

### Step 2: Get Credentials

1. Go to [Twilio Console](https://console.twilio.com/)
2. Find your **Account SID** and **Auth Token** on the dashboard
3. Copy these values (you'll need them later)

### Step 3: Enable WhatsApp Sandbox

1. In Twilio Console, go to **Messaging** → **Try it out** → **Send a WhatsApp message**
2. You'll see a sandbox number (e.g., `+1 415 523 8886`)
3. Follow instructions to connect your WhatsApp:
   - Send a message like `join <code>` to the sandbox number
   - Example: `join happy-elephant`
4. ✅ You should receive a confirmation message

**Important:** Sandbox has limitations:
- Only works with numbers you've joined
- Messages expire after 24 hours
- For production, you need an approved WhatsApp Business number

---

## 💻 Local Setup

### Step 1: Clone/Create Project

```bash
# Create project directory
mkdir whatsapp-test
cd whatsapp-test

# Copy all files from outputs to this directory
# (Dockerfile, docker-compose.yml, whatsapp_handler.py, etc.)
```

### Step 2: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env  # or use any text editor
```

Fill in your Twilio credentials:

```bash
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
```

### Step 3: Create Certificates Directory

```bash
mkdir -p certificates
```

---

## 🐳 Docker Setup

### Step 1: Build Container

```bash
# Build the Docker image
docker-compose build
```

This will:
- Download Python 3.10 base image
- Install all dependencies from `requirements.txt`
- Copy application files
- Create certificates directory

### Step 2: Start Service

```bash
# Start the webhook service
docker-compose up
```

You should see:

```
whatsapp-webhook | ✅ Configuration validated successfully
whatsapp-webhook | 🚀 Starting WhatsApp webhook server...
whatsapp-webhook | 📍 Listening on: http://0.0.0.0:5000
whatsapp-webhook | 📍 Webhook endpoint: http://0.0.0.0:5000/webhook
```

### Step 3: Verify Service is Running

Open another terminal:

```bash
# Test health check endpoint
curl http://localhost:5000/

# Expected response:
# {"status":"running","service":"WhatsApp Bot Webhook"}
```

✅ If you see this, your webhook is working locally!

---

## 🌍 ngrok Setup

Your webhook is running on `localhost:5000`, but Twilio needs a **public URL** to send messages.

### Step 1: Install ngrok

```bash
# Download from https://ngrok.com/download
# Or install via package manager:

# macOS
brew install ngrok

# Linux
snap install ngrok

# Windows
# Download .exe from website
```

### Step 2: Authenticate ngrok

```bash
# Get your auth token from: https://dashboard.ngrok.com/get-started/your-authtoken
ngrok config add-authtoken YOUR_NGROK_TOKEN
```

### Step 3: Expose Local Server

```bash
# Start ngrok tunnel
ngrok http 5000
```

You'll see:

```
ngrok                                                                     

Session Status     online
Account            your@email.com
Forwarding         https://abc123.ngrok.io -> http://localhost:5000
```

**Copy the HTTPS URL** (e.g., `https://abc123.ngrok.io`)

⚠️ **Important:** 
- Keep ngrok running while testing
- URL changes each time you restart ngrok (free plan)
- For permanent URL, use ngrok paid plan or production server

---

## 🔗 Connect Twilio to Webhook

### Step 1: Configure Twilio Webhook

1. Go to [Twilio Console](https://console.twilio.com/)
2. Navigate to **Messaging** → **Settings** → **WhatsApp Sandbox Settings**
3. Find **"When a message comes in"** field
4. Enter your ngrok URL + `/webhook`:
   ```
   https://abc123.ngrok.io/webhook
   ```
5. Set HTTP method to **POST**
6. Click **Save**

### Step 2: Verify Connection

Send a WhatsApp message to your Twilio sandbox number.

**Expected flow:**
1. You send: `Hello`
2. Webhook receives message (check Docker logs)
3. Bot replies with echo message

---

## ✅ Testing

### Test 1: Text Message Echo

1. Send a text message to Twilio WhatsApp number
2. Check Docker logs:
   ```bash
   docker-compose logs -f whatsapp-bot
   ```
3. You should see:
   ```
   📩 MESSAGE RECEIVED
   ==================================================
   From: whatsapp:+1234567890
   Text: Hello
   Media files: 0
   ==================================================
   
   📤 RESPONSE SENT: ✅ Message received!...
   ```
4. Bot should reply with echo message

**✅ Success:** Bot echoes your message back

### Test 2: Image Upload (Certificate)

1. Send an image to the WhatsApp number
2. Check Docker logs - should see:
   ```
   📎 Processing media 1/1
      URL: https://api.twilio.com/...
      Type: image/jpeg
      ✅ Saved: certificates/+1234567890/certificate_20251102_143022.jpg
   ```
3. Bot should reply with confirmation
4. Verify file was saved:
   ```bash
   ls -la certificates/
   ```

**✅ Success:** Image saved in `certificates/` folder

### Test 3: PDF Upload

1. Send a PDF document
2. Same process as image
3. File should be saved as `.pdf`

**✅ Success:** PDF saved in certificates folder

### Test 4: Multiple Media Files

1. Send multiple images at once
2. Bot should save all files
3. Reply should list all saved files

---

## 🐛 Troubleshooting

### Problem: "Configuration Error"

**Symptoms:** Container starts but shows missing credentials

**Solution:**
1. Check `.env` file exists
2. Verify credentials are correct (no extra spaces)
3. Restart container: `docker-compose restart`

### Problem: "Webhook not receiving messages"

**Symptoms:** Send WhatsApp message, but nothing happens

**Checklist:**
1. ✅ Is Docker container running? (`docker-compose ps`)
2. ✅ Is ngrok running? (check terminal)
3. ✅ Is Twilio webhook URL correct? (check Console)
4. ✅ Did you join the WhatsApp sandbox? (send `join <code>`)
5. ✅ Check ngrok URL hasn't changed

**Debug:**
```bash
# Check container logs
docker-compose logs -f

# Test webhook directly
curl -X POST https://your-ngrok-url.ngrok.io/webhook \
  -d "Body=test" \
  -d "From=whatsapp:+1234567890"
```

### Problem: "Media download fails"

**Symptoms:** Text works, but images fail

**Possible causes:**
1. Invalid Twilio credentials
2. Network/firewall issues
3. Twilio rate limits

**Solution:**
```bash
# Check credentials in .env
cat .env | grep TWILIO

# Test Twilio API directly
curl -X GET 'https://api.twilio.com/2010-04-01/Accounts.json' \
  -u "YOUR_SID:YOUR_TOKEN"
```

### Problem: "ngrok URL expired"

**Symptoms:** Was working, now stopped

**Cause:** ngrok free plan URLs expire/change

**Solution:**
1. Restart ngrok: `ngrok http 5000`
2. Copy new URL
3. Update Twilio webhook URL
4. Restart webhook test

---

## 📊 View Logs

```bash
# View real-time logs
docker-compose logs -f whatsapp-bot

# View last 50 lines
docker-compose logs --tail=50 whatsapp-bot

# Search logs
docker-compose logs whatsapp-bot | grep "MESSAGE RECEIVED"
```

---

## 🔄 Common Commands

```bash
# Start service (detached mode)
docker-compose up -d

# Stop service
docker-compose down

# Restart service
docker-compose restart

# Rebuild after code changes
docker-compose up --build

# View running containers
docker-compose ps

# Access container shell
docker-compose exec whatsapp-bot bash

# Remove everything (including volumes)
docker-compose down -v
```

---

## 🎯 Next Steps

Once WhatsApp integration is working:

1. **Add Bot Logic**
   - Replace echo functionality in `whatsapp_handler.py`
   - Connect to `bot.py` (state machine)
   
2. **Add Database**
   - Create `database.py`
   - Store professionals, schedules, searches
   
3. **Add Validation**
   - Create `validators.py`
   - Validate time formats, phone numbers
   
4. **Add Analytics**
   - Create `analytics.py`
   - Track client searches
   
5. **Deploy to Production**
   - Get approved WhatsApp Business number
   - Deploy to cloud (DigitalOcean, AWS, etc.)
   - Use gunicorn instead of Flask dev server
   - Set up SSL/HTTPS
   - Configure proper logging

---

## 📚 Additional Resources

- [Twilio WhatsApp API Docs](https://www.twilio.com/docs/whatsapp)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Docker Compose Docs](https://docs.docker.com/compose/)
- [ngrok Documentation](https://ngrok.com/docs)

---

## 🆘 Support

If you encounter issues:

1. Check Docker logs: `docker-compose logs -f`
2. Verify Twilio console for webhook errors
3. Test ngrok tunnel: visit ngrok URL in browser
4. Check `.env` file configuration

---

## ✅ Success Checklist

Before moving to next phase:

- [x] Docker container runs without errors
- [x] ngrok tunnel is active
- [x] Twilio webhook configured correctly
- [x] Bot echoes text messages
- [x] Bot receives and saves images
- [x] Bot receives and saves PDFs
- [x] Logs show all activity clearly

**🎉 Once all checked, WhatsApp integration is complete!**

---

**Version:** 1.0  
**Last Updated:** 2025-11-02  
**Author:** Booking Chatbot Project