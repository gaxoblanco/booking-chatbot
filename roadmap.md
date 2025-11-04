# Minimalist Booking Chatbot - Project Roadmap

## Project Overview

A simple WhatsApp-based bot that connects professionals with clients through availability management and contact information sharing.

### Core Actors
- **Professional**: Manages their profile and availability (days/hours free)
- **Client**: Searches for available professionals using filters

### Tech Stack (Minimal)
- **Backend**: Python 3.10+
- **Bot Logic**: Simple menu-based interaction (no ML/NLU)
- **Messaging**: WhatsApp Business API (Twilio for simplicity)
- **Database**: SQLite (file-based, zero config)
- **Architecture**: Single monolithic script (can split later if needed)

---

## Phase 1: Minimalist Architecture (Day 1)

### 1.1 Project Structure
```
booking-chatbot/
├── README.md                 # Main documentation
├── ROADMAP.md               # This file
├── bot.py                   # Main bot logic (~400 lines)
├── database.py              # Database operations (~200 lines)
├── whatsapp_handler.py      # WhatsApp API + Flask webhook (~100 lines)
├── validators.py            # Input validation (~80 lines)
├── analytics.py             # Search tracking (~50 lines)
├── config.py                # Configuration settings
├── requirements.txt         # Dependencies (5-6 packages)
├── .env.example            # Environment variables template
├── database.db             # SQLite database (created on first run)
├── certificates/           # Uploaded professional certificates
│   └── +1234567890/       # One folder per professional
│       └── certificate.jpg
└── tests/
    ├── test_database.py
    ├── test_validators.py
    └── test_bot.py
```

**Total lines of code: ~850 lines**

### 1.2 Core Dependencies
```
twilio                  # WhatsApp API
flask                   # Webhook server
python-dotenv          # Environment variables
requests               # Download media files from Twilio
pytest                 # Testing
```

That's it. No framework overhead.

---

## Phase 2: Database Design (Day 1-2)

### 2.1 Complete Schema (6 tables)

#### specialties
```sql
CREATE TABLE specialties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) UNIQUE NOT NULL,   -- e.g., "Dentist", "Lawyer"
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### professionals
```sql
CREATE TABLE professionals (
    phone VARCHAR(20) PRIMARY KEY,       -- WhatsApp number = unique ID
    name VARCHAR(100) NOT NULL,
    description TEXT,
    contact_info TEXT,                   -- Email, website, etc.
    certificate_path VARCHAR(255),       -- Path to stored certificate file
    is_verified BOOLEAN DEFAULT FALSE,   -- Admin verification status
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### professional_specialties (many-to-many)
```sql
CREATE TABLE professional_specialties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    professional_phone VARCHAR(20) NOT NULL,
    specialty_id INTEGER NOT NULL,
    FOREIGN KEY (professional_phone) REFERENCES professionals(phone) ON DELETE CASCADE,
    FOREIGN KEY (specialty_id) REFERENCES specialties(id),
    UNIQUE(professional_phone, specialty_id)
);
```

#### weekly_schedule
```sql
CREATE TABLE weekly_schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    professional_phone VARCHAR(20) NOT NULL,
    day_of_week INTEGER NOT NULL,        -- 0=Monday, 6=Sunday
    start_time TIME NOT NULL,            -- e.g., "09:00"
    end_time TIME NOT NULL,              -- e.g., "17:00"
    is_busy BOOLEAN DEFAULT FALSE,       -- TRUE = busy/occupied, FALSE = available
    FOREIGN KEY (professional_phone) REFERENCES professionals(phone) ON DELETE CASCADE
);
-- Note: This is the RECURRING weekly pattern. Busy days block availability.
```

#### specific_bookings
```sql
CREATE TABLE specific_bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    professional_phone VARCHAR(20) NOT NULL,
    booking_date DATE NOT NULL,          -- Specific date (YYYY-MM-DD)
    start_time TIME NOT NULL,            -- e.g., "14:00"
    end_time TIME NOT NULL,              -- e.g., "15:00"
    is_available BOOLEAN DEFAULT TRUE,   -- TRUE = slot is FREE (override busy schedule)
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (professional_phone) REFERENCES professionals(phone) ON DELETE CASCADE
);
-- Note: This OVERRIDES weekly_schedule. Used when a slot becomes FREE (e.g., cancellation)
```

#### client_searches (analytics)
```sql
CREATE TABLE client_searches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_phone VARCHAR(20),            -- Client's WhatsApp number
    search_type VARCHAR(50),             -- "by_specialty", "by_day", "by_time"
    search_params TEXT,                  -- JSON: {"specialty": "Dentist", "day": "Monday"}
    results_count INTEGER,               -- How many professionals matched
    professional_contacted VARCHAR(20),  -- Which professional was contacted (if any)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (professional_contacted) REFERENCES professionals(phone)
);
```

### 2.2 Schema Logic Explained

#### Availability System (Corrected)

1. **Weekly Pattern** (`weekly_schedule`): Professional sets recurring BUSY hours
   - Example: "Monday 9am-5pm = BUSY" means every Monday 9-5 is blocked
   - This is their regular work schedule
   - **Default assumption**: If not in table = AVAILABLE
   
2. **Specific Free Slots** (`specific_bookings`): Professional marks slots as FREE
   - Used when: Client cancels, professional has unexpected opening
   - Example: "2025-11-15 14:00-15:00 = AVAILABLE" 
   - **This OVERRIDES weekly_schedule** - makes normally busy time available

3. **Search Logic Flow**:
   ```
   Is Professional Available on Monday 14:00-15:00?
   
   Step 1: Check specific_bookings for that exact date/time
   → IF found AND is_available=TRUE → AVAILABLE ✅ (override)
   
   Step 2: Check weekly_schedule for Monday
   → IF Monday 14:00 falls within busy range → NOT AVAILABLE ❌
   
   Step 3: If not in weekly_schedule → AVAILABLE ✅ (default)
   ```

#### Real-World Example

**Dr. Smith's Setup:**
```
Weekly Schedule (Recurring):
- Monday 9am-5pm (BUSY)
- Tuesday 9am-5pm (BUSY)
- Wednesday OFF (not in table = AVAILABLE all day)
- Thursday 9am-5pm (BUSY)
- Friday 9am-5pm (BUSY)

Specific Free Slots:
- 2025-11-18 (Monday) 14:00-15:00 (AVAILABLE - client cancelled)
- 2025-11-20 (Wednesday) - no override needed, already free
- 2025-11-22 (Friday) 10:00-11:00 (AVAILABLE - gap between appointments)
```

**Client searches "Monday 14:00":**
- Checks specific_bookings → Finds 2025-11-18 14:00-15:00 = AVAILABLE
- ✅ Shows Dr. Smith as available (even though Monday normally busy)

**Client searches "Monday 10:00":**
- Checks specific_bookings → Nothing found
- Checks weekly_schedule → Monday 9am-5pm = BUSY
- ❌ Dr. Smith NOT available

#### Certificate Verification
- Professional uploads certificate via WhatsApp (image/PDF)
- Bot stores file in `/certificates/{phone_number}/` folder
- `is_verified` = FALSE until admin reviews
- Only verified professionals appear in client searches

#### Multi-Specialty Support
- One professional can have multiple specialties
- Stored in junction table `professional_specialties`
- Client can search by any specialty

#### Analytics Tracking
- Every client search is logged
- Track which professional was contacted
- Measure success rate: `contacted / total_searches`

---

## Phase 3: Bot Logic Design (Day 2-3)

### 3.1 Menu-Based Interaction (No NLU)

#### Professional Menu Flow

```
User: [sends any message]
Bot: "Hi! Are you a:
     1️⃣ Professional
     2️⃣ Client"

User: 1
Bot: "Professional Menu:
     1️⃣ Register/Update Profile
     2️⃣ Upload Certificate
     3️⃣ Set Weekly Busy Hours
     4️⃣ Mark Specific Slot as FREE
     5️⃣ View My Schedule
     6️⃣ Remove Free Slot"

User: 1 (Register)
Bot: "Enter your name:"

User: Dr. John Smith
Bot: "Enter specialties (comma separated):
     Available: Dentist, Lawyer, Plumber, Electrician, Doctor"

User: Dentist, Doctor
Bot: "Enter contact info (email, website, etc.):"

User: john@example.com
Bot: "✅ Profile created! 
     ⚠️ Upload certificate to get verified."

---

User: 2 (Upload Certificate)
Bot: "Send your professional certificate (image or PDF)"

User: [uploads image]
Bot: "✅ Certificate received!
     ⏳ Pending admin verification"

---

User: 3 (Set Weekly Busy Hours)
Bot: "Which day?
     1️⃣ Monday
     2️⃣ Tuesday
     3️⃣ Wednesday
     4️⃣ Thursday
     5️⃣ Friday
     6️⃣ Saturday
     7️⃣ Sunday"

User: 1
Bot: "Enter time range (24hr format):
     Example: 09:00-17:00"

User: 09:00-17:00
Bot: "✅ Monday 09:00-17:00 marked as BUSY (recurring)
     This blocks every Monday in this time."

---

User: 4 (Mark Specific Slot as FREE)
Bot: "Enter date (YYYY-MM-DD):
     Example: 2025-11-15"

User: 2025-11-15
Bot: "Enter time range (24hr format):
     Example: 14:00-15:00"

User: 14:00-15:00
Bot: "✅ 2025-11-15 14:00-15:00 marked as FREE
     This slot is now available (overrides weekly schedule)"

---

User: 5 (View My Schedule)
Bot: "Dr. Smith's Schedule:
     
     Weekly Pattern (BUSY):
     ❌ Monday 9am-5pm
     ❌ Tuesday 9am-5pm
     ✅ Wednesday (FREE - not set)
     ❌ Thursday 9am-5pm
     ❌ Friday 9am-5pm
     
     Specific FREE Slots:
     ✅ 2025-11-15 14:00-15:00
     ✅ 2025-11-22 10:00-11:00"
```

#### Client Menu Flow

```
User: [sends any message]
Bot: "Hi! Are you a:
     1️⃣ Professional
     2️⃣ Client"

User: 2
Bot: "Search verified professionals:
     1️⃣ By Specialty
     2️⃣ By Day & Time
     3️⃣ Show All"

User: 1 (By Specialty)
Bot: "Choose specialty:
     1️⃣ Dentist
     2️⃣ Lawyer
     3️⃣ Plumber
     4️⃣ Electrician
     5️⃣ Doctor"

User: 1
Bot: "Found 3 verified dentists:
     
     👤 Dr. Smith
     📱 +1234567890
     📧 john@example.com
     📅 Busy: Mon 9am-5pm, Wed 9am-5pm
     
     👤 Dr. Jones
     📱 +0987654321
     📧 jones@example.com
     📅 Busy: Tue 10am-6pm
     
     👤 Dr. Brown
     📱 +1122334455
     📧 brown@example.com
     📅 Busy: Mon-Fri 9am-5pm
     
     Reply with number to see availability"

User: 1
Bot: "Dr. Smith detailed schedule:
     
     Weekly Pattern:
     ❌ Monday 9am-5pm (BUSY)
     ✅ Tuesday (AVAILABLE)
     ❌ Wednesday 9am-5pm (BUSY)
     ✅ Thursday (AVAILABLE)
     ✅ Friday (AVAILABLE)
     
     Specific Busy Slots:
     ❌ 2025-11-15 9am-10am
     ❌ 2025-11-20 2pm-3pm
     
     Contact: +1234567890"

[Analytics: Log this contact view]

---

User: 2 (By Day & Time)
Bot: "Which day?
     1️⃣ Monday
     2️⃣ Tuesday
     ...
     7️⃣ Sunday"

User: 2 (Tuesday)
Bot: "Enter time (24hr format):
     Example: 09:00"

User: 14:00
Bot: "Professionals available Tuesday at 14:00:
     
     👤 Dr. Smith - Dentist
     📱 +1234567890
     
     👤 Dr. Jones - Lawyer
     📱 +0987654321
     
     2 professionals found."

[Analytics: Log search with results count]
```

### 3.2 State Management

```python
# Simple in-memory session management
sessions = {
    '+1234567890': {
        'state': 'waiting_time_input',
        'role': 'professional',
        'temp_data': {
            'day_selected': 1,  # Monday
            'action': 'set_busy_hours'
        }
    }
}

# States for professionals
STATES = [
    'role_selection',
    'professional_menu',
    'waiting_name',
    'waiting_specialties',
    'waiting_contact',
    'waiting_certificate',
    'waiting_day_selection',
    'waiting_time_range',
    'waiting_date_input',
    'waiting_specific_time'
]

# States for clients
CLIENT_STATES = [
    'client_menu',
    'waiting_specialty_choice',
    'waiting_day_choice',
    'waiting_time_input'
]
```

### 3.3 File Handling (Certificates)

```python
# When user uploads image/PDF
def handle_media(sender_phone, media_url, media_type):
    # Download file from Twilio
    file_data = download_media(media_url)
    
    # Create directory if not exists
    cert_dir = f"certificates/{sender_phone}/"
    os.makedirs(cert_dir, exist_ok=True)
    
    # Save file
    extension = "jpg" if media_type == "image" else "pdf"
    file_path = f"{cert_dir}/certificate.{extension}"
    
    with open(file_path, 'wb') as f:
        f.write(file_data)
    
    # Update database
    db.update_certificate_path(sender_phone, file_path)
    
    return "✅ Certificate uploaded! Pending verification."
```

### 3.4 Time Validation

```python
def parse_time_range(text):
    """
    Parse time range from user input
    Input: "09:00-17:00"
    Output: ("09:00", "17:00")
    """
    try:
        start, end = text.split('-')
        start = start.strip()
        end = end.strip()
        
        # Validate format HH:MM
        datetime.strptime(start, "%H:%M")
        datetime.strptime(end, "%H:%M")
        
        return (start, end)
    except:
        return None

def parse_date(text):
    """
    Parse date from user input
    Input: "2025-11-15"
    Output: date object
    """
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except:
        return None
```

---

## Phase 4: WhatsApp Integration (Day 3-4)

### 4.1 Twilio Setup (Simplest Option)

**Why Twilio:**
- Free trial ($15 credit)
- Takes 10 minutes to setup
- Good documentation
- Webhook-based (no complex polling)
- **Media handling**: Can receive images/PDFs

**Setup Steps:**
1. Create Twilio account
2. Enable WhatsApp Sandbox
3. Get phone number for testing
4. Configure webhook URL

### 4.2 Webhook Handler

```python
# whatsapp_handler.py

from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import requests
import os

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    incoming_msg = request.values.get('Body', '')
    sender = request.values.get('From', '')
    
    # Check if message contains media (certificate upload)
    num_media = int(request.values.get('NumMedia', 0))
    
    if num_media > 0:
        # Handle media upload
        media_url = request.values.get('MediaUrl0', '')
        media_type = request.values.get('MediaContentType0', '')
        reply = handle_certificate_upload(sender, media_url, media_type)
    else:
        # Process text message with bot logic
        reply = bot.process_message(sender, incoming_msg)
    
    # Send response
    response = MessagingResponse()
    response.message(reply)
    return str(response)

def handle_certificate_upload(sender, media_url, media_type):
    """Download and store certificate file"""
    try:
        # Download file from Twilio
        auth = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        file_response = requests.get(media_url, auth=auth)
        
        # Create directory
        cert_dir = f"certificates/{sender.replace('whatsapp:', '')}/"
        os.makedirs(cert_dir, exist_ok=True)
        
        # Determine extension
        extension = "jpg" if "image" in media_type else "pdf"
        file_path = f"{cert_dir}/certificate.{extension}"
        
        # Save file
        with open(file_path, 'wb') as f:
            f.write(file_response.content)
        
        # Update database
        from database import update_certificate
        update_certificate(sender.replace('whatsapp:', ''), file_path)
        
        return "✅ Certificate received! Pending admin verification."
    except Exception as e:
        return f"❌ Error uploading certificate: {str(e)}"
```

### 4.3 Message Flow
```
WhatsApp User → Twilio → Flask Webhook → bot.py → database.py → SQLite
                  ↓                         ↓
            Media Files              analytics.py (track searches)
                  ↓
         certificates/ folder
```

**Total complexity: ~100 lines of code**

---

## Phase 5: Testing & Deployment (Day 4-5)

### 5.1 Simple Testing
```python
# test_validators.py
def test_parse_days():
    assert parse_days("Mon, Wed") == [0, 2]
    assert parse_days("Monday, Friday") == [0, 4]

# test_database.py  
def test_add_professional():
    db.add_professional("+123", "John", "Dentist")
    result = db.get_professional("+123")
    assert result['name'] == "John"
```

### 5.2 Local Testing
```bash
# 1. Run webhook locally
python whatsapp_handler.py

# 2. Use ngrok to expose webhook
ngrok http 5000

# 3. Configure Twilio with ngrok URL
# https://abc123.ngrok.io/webhook
```

### 5.3 Deployment (Minimal)

**Option 1: Heroku (Easiest)**
- Free tier available
- Git-based deployment
- Automatic HTTPS

**Option 2: DigitalOcean Droplet**
- $6/month
- Full control
- Need to configure nginx/SSL

**Requirements:**
- Python 3.10+
- 512MB RAM (sufficient)
- Port 80/443 for webhook

---

## Critical Decisions Simplified

### No Rasa Because:
- ❌ Requires training data (we don't have)
- ❌ Needs 2GB+ RAM server ($15+/month)
- ❌ Complex setup and maintenance
- ✅ Menu-based is predictable and free

### SQLite Because:
- ✅ Zero configuration
- ✅ File-based (easy backup)
- ✅ Sufficient for 1000s of professionals
- ✅ Can migrate to PostgreSQL later if needed

### Twilio Because:
- ✅ Free trial for testing
- ✅ 10-minute setup
- ✅ Reliable delivery
- ✅ Webhook-based (simpler than polling)

---

## MVP Feature Set

### Professional Features
✅ Register with name, specialties, contact
✅ Upload certificate (image/PDF)
✅ Set weekly busy hours (recurring)
✅ Add specific busy time slots
✅ View complete schedule
✅ Remove busy slots

### Client Features
✅ Search verified professionals
✅ Filter by specialty
✅ Filter by day & time availability
✅ Get detailed schedule + contact info
✅ All searches tracked for analytics

### Admin Features (Minimal for MVP)
⚠️ **Decision needed**: Auto-verify or manual review?
- Option A: Auto-verify on upload (faster MVP)
- Option B: Separate admin interface (more secure)

### Explicitly NOT in MVP
❌ No booking/reservation confirmation
❌ No payment integration
❌ No calendar sync
❌ No multi-language
❌ No push notifications
❌ No ratings/reviews
❌ No professional availability exceptions beyond specific dates

---

## Development Timeline

| Day | Tasks | Hours | Deliverable |
|-----|-------|-------|-------------|
| 1 | Database schema + seed data | 4-6h | Working SQLite with test data |
| 2 | Bot logic + state management | 6-8h | Bot responds to menus locally |
| 3 | WhatsApp + media handling | 4-6h | Bot works on WhatsApp |
| 4 | Analytics + testing | 4-6h | All features tested |
| 5 | Deployment + docs | 3-4h | Live bot + README |

**Total: 1 week for fully functional MVP**

---

## Updated Cost Estimate

### Development
- $0 (all free tools)

### Monthly Operating (Production)
- Server: $6/month (DigitalOcean) or $0 (Heroku free tier)
- Twilio: ~$0.005 per message
- File storage: ~$1/month for 100 certificates
- Domain (optional): $12/year

**Total: $0-10/month** for hundreds of users

---

## Analytics Dashboard (Future)

Track these metrics:
```sql
-- Success rate
SELECT 
    COUNT(CASE WHEN professional_contacted IS NOT NULL THEN 1 END) * 100.0 / COUNT(*) as success_rate
FROM client_searches;

-- Popular specialties
SELECT 
    search_params, 
    COUNT(*) as searches
FROM client_searches
WHERE search_type = 'by_specialty'
GROUP BY search_params
ORDER BY searches DESC;

-- Most contacted professionals
SELECT 
    p.name,
    COUNT(*) as times_contacted
FROM client_searches cs
JOIN professionals p ON cs.professional_contacted = p.phone
GROUP BY cs.professional_contacted
ORDER BY times_contacted DESC;
```

---

## Questions Resolved ✅

1. ✅ **Availability Granularity**: Hourly slots (9am-10am format)
2. ✅ **Weekly Schedule**: Professionals mark BUSY days (recurring)
3. ✅ **Specific Bookings**: Override weekly pattern for specific dates
4. ✅ **Specialties**: Pre-defined list (stored in database table)
5. ✅ **Verification**: Professionals upload certificates, admin reviews
6. ✅ **Analytics**: Track all client searches and professional contacts
7. ✅ **Multi-Profile**: No, one profile can have multiple specialties

## New Question to Resolve

1. **Admin Verification Process**: 
   - Who is the admin? (separate WhatsApp number?)
   - How do they review certificates? (manual review? separate interface?)
   - For MVP: Should we auto-verify or require manual approval?
   
   **Recommendation for MVP**: Auto-verify on upload, add manual review later

---

## Next Steps

1. ✅ Review simplified roadmap
2. ⬜ Answer 5 questions above
3. ⬜ Create database.py with schema
4. ⬜ Create bot.py with menu logic
5. ⬜ Test locally with mock WhatsApp
6. ⬜ Integrate Twilio
7. ⬜ Deploy

---

## Success Metrics

- Bot responds within 1 second
- Professional can register in <2 minutes
- Client finds contact in <30 seconds
- Zero server crashes in first week
- Cost stays under $10/month

---

## Document History
- **2025-11-02**: Initial roadmap (over-engineered with Rasa)
- **2025-11-02**: Simplified to menu-based bot (this version)
- Version: 2.0 (Minimalist)