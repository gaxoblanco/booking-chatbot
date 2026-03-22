"""
Database Module
===============
SQLite database connection and CRUD operations.
Handles all data persistence for professionals, schedules, and client searches.
"""

import sqlite3
import json
from datetime import datetime, date, time
from typing import List, Dict, Optional, Tuple
from contextlib import contextmanager


class Database:
    """
    Database handler for the booking chatbot.
    Uses SQLite for simplicity and zero configuration.
    """

    def __init__(self, db_path: str = "database.db"):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.
        Ensures connections are properly closed.

        Usage:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(...)
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _init_db(self):
        """
        Initialize database schema.
        Creates all tables if they don't exist.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # ==========================================
            # TABLE: professionals
            # ==========================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS professionals (
                    phone TEXT PRIMARY KEY,
                    name TEXT,
                    email TEXT,
                    zone TEXT CHECK(zone IN ('norte', 'sur')),
                    certificate_path TEXT,
                    gender TEXT CHECK(gender IN ('m', 'f', 'otro')),
                    accept_prepaga BOOLEAN DEFAULT 0,
                    category TEXT,
                    bio TEXT,
                    fee_range TEXT,
                    
                    -- Configuración de agenda
                    session_duration_minutes INTEGER DEFAULT 50,
                    buffer_time_minutes INTEGER DEFAULT 10,
                    max_daily_sessions INTEGER DEFAULT 8,
                    accepts_online BOOLEAN DEFAULT 1,
                    accepts_in_person BOOLEAN DEFAULT 1,
                    auto_confirm_appointments BOOLEAN DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    is_accepting_new_patients BOOLEAN DEFAULT 1,
                    
                    -- Metrics
                    total_views INTEGER DEFAULT 0,
                    total_profile_views INTEGER DEFAULT 0,
                    total_contacts INTEGER DEFAULT 0,
                    avg_search_position REAL DEFAULT 0.0,
                    last_contacted_at TIMESTAMP,
                    
                    -- Timestamps
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                           
                    -- GOOGLE CALENDAR INTEGRATION
                    calendar_email TEXT,
                    calendar_id TEXT,
                    working_hours TEXT,
                    slot_duration INTEGER DEFAULT 60,
                    timezone TEXT DEFAULT 'America/Argentina/Buenos_Aires'
                )
            """)
            

            # ==========================================
            # TABLE: client_searches
            # ==========================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS client_searches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_phone TEXT NOT NULL,
                    search_type TEXT NOT NULL,
                    search_params TEXT,
                    result_count INTEGER DEFAULT 0,
                    professional_contacted TEXT,
                    session_id TEXT,
                    search_abandoned BOOLEAN DEFAULT 0,
                    result_position_clicked INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY (professional_contacted) REFERENCES professionals(phone)
                )
            """)

            # Index for analytics queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_searches_client 
                ON client_searches(client_phone)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_searches_professional 
                ON client_searches(professional_contacted)
            """)

            # ==========================================
            # TABLE: clients
            # ==========================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS clients (
                    phone TEXT PRIMARY KEY,
                    name TEXT,
                    email TEXT,
                    
                    -- Datos demográficos
                    age INTEGER,
                    gender TEXT CHECK(gender IN ('m', 'f', 'otro', 'prefiero_no_decir')),
                    
                    -- Preferencias de búsqueda
                    preferred_zone TEXT CHECK(preferred_zone IN ('norte', 'sur', 'indistinto')),
                    preferred_gender TEXT,
                    has_prepaga BOOLEAN DEFAULT 0,
                    prepaga_name TEXT,
                    
                    -- Comunicación
                    preferred_contact TEXT CHECK(preferred_contact IN ('whatsapp', 'email', 'phone')) DEFAULT 'whatsapp',
                    language TEXT DEFAULT 'es',
                    
                    -- Flags importantes
                    first_time_patient BOOLEAN DEFAULT 1,
                    is_active BOOLEAN DEFAULT 1,
                    
                    -- Timestamps
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_interaction_at TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_clients_active 
                ON clients(is_active)
            """)

            # ==========================================
            # TABLE: appointments
            # ==========================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS appointments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    google_event_id TEXT,
                    
                    -- Referencias
                    client_phone TEXT NOT NULL,
                    professional_phone TEXT NOT NULL,
                    
                    -- Detalles de la cita
                    appointment_date DATE NOT NULL,
                    start TEXT NOT NULL,
                    end TEXT NOT NULL,
                    duration_minutes INTEGER DEFAULT 50,
                    
                    -- Tipo de sesión
                    session_type TEXT CHECK(session_type IN ('primera_vez', 'seguimiento', 'evaluacion')) DEFAULT 'primera_vez',
                    modality TEXT CHECK(modality IN ('presencial', 'virtual', 'ambas')) DEFAULT 'presencial',
                    
                    -- Estado de la cita
                    status TEXT CHECK(status IN (
                        'pendiente_confirmacion',
                        'confirmada',
                        'completada',
                        'cancelada_cliente',
                        'cancelada_profesional',
                        'no_asistio',
                        'reagendada'
                    )) DEFAULT 'pendiente_confirmacion',
                    
                    -- Información adicional
                    notes TEXT,
                    cancellation_reason TEXT,
                    reminder_sent BOOLEAN DEFAULT 0,
                    reminder_sent_at TIMESTAMP,

                    -- Waitlist: cliente acepta adelantar turno si se libera uno
                    wants_earlier_slot BOOLEAN DEFAULT 1,
                    -- ID de oferta que originó este movimiento
                    moved_from_offer_id INTEGER,

                    -- Reminder: confirmación explícita del cliente
                    confirmed_by_client BOOLEAN DEFAULT 0,
                    confirmed_by_client_at TIMESTAMP,

                    -- Timestamps
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    confirmed_at TIMESTAMP,
                    cancelled_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    last_synced_at TIMESTAMP,
                    
                    -- Foreign keys
                    FOREIGN KEY (client_phone) REFERENCES clients(phone),
                    FOREIGN KEY (professional_phone) REFERENCES professionals(phone),
                    
                    -- Constraint: No solapamiento de citas del mismo profesional
                    UNIQUE(professional_phone, appointment_date, start)
                )
            """)

            # Índices para optimizar consultas de appointments
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_appointments_client 
                ON appointments(client_phone)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_appointments_professional 
                ON appointments(professional_phone)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_appointments_date 
                ON appointments(appointment_date)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_appointments_status 
                ON appointments(status)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_appointments_date_professional 
                ON appointments(professional_phone, appointment_date)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_appointments_last_synced 
                ON appointments(last_synced_at)
            """)

            # ==========================================
            # TABLE: appointment_history
            # ==========================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS appointment_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    appointment_id INTEGER NOT NULL,
                    
                    -- Cambios
                    previous_status TEXT,
                    new_status TEXT,
                    previous_date DATE,
                    new_date DATE,
                    previous_time TEXT,
                    new_time TEXT,
                    
                    -- Quién hizo el cambio
                    changed_by TEXT CHECK(changed_by IN ('client', 'professional', 'system', 'admin')),
                    change_reason TEXT,
                    
                    -- Timestamp
                    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY (appointment_id) REFERENCES appointments(id) ON DELETE CASCADE
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_history_appointment 
                ON appointment_history(appointment_id)
            """)

            # ==========================================
            # TABLE: notifications
            # ==========================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    
                    -- Destinatario
                    recipient_phone TEXT NOT NULL,
                    recipient_type TEXT CHECK(recipient_type IN ('client', 'professional')) NOT NULL,
                    
                    -- Tipo de notificación
                    notification_type TEXT CHECK(notification_type IN (
                        'appointment_confirmation',
                        'appointment_reminder_24h',
                        'appointment_reminder_1h',
                        'appointment_cancelled',
                        'appointment_rescheduled',
                        'no_show_followup',
                        'feedback_request'
                    )) NOT NULL,
                    
                    -- Contenido
                    message_text TEXT NOT NULL,
                    
                    -- Estado
                    status TEXT CHECK(status IN ('pending', 'sent', 'delivered', 'failed')) DEFAULT 'pending',
                    channel TEXT CHECK(channel IN ('whatsapp', 'email', 'sms')) DEFAULT 'whatsapp',
                    
                    -- Relación con cita (opcional)
                    appointment_id INTEGER,
                    
                    -- Timestamps
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sent_at TIMESTAMP,
                    delivered_at TIMESTAMP,
                    
                    FOREIGN KEY (appointment_id) REFERENCES appointments(id)
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_notifications_recipient 
                ON notifications(recipient_phone)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_notifications_appointment 
                ON notifications(appointment_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_notifications_status 
                ON notifications(status)
            """)

            conn.commit()
            print("✅ Database initialized successfully")

            # ==========================================
            # TABLE: appointment_reminders
            # ==========================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS appointment_reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    appointment_id INTEGER NOT NULL,

                    -- Quién recibe el recordatorio
                    client_phone TEXT NOT NULL,
                    professional_phone TEXT NOT NULL,

                    -- Datos de la cita (desnormalizados para consultas rápidas)
                    appointment_date DATE NOT NULL,
                    appointment_time TEXT NOT NULL,

                    -- Estado del recordatorio
                    -- sent: enviado, esperando respuesta
                    -- confirmed: cliente confirmó asistencia
                    -- rescheduled: cliente quiere reprogramar
                    -- cancelled: cliente canceló
                    status TEXT CHECK(status IN ('sent', 'confirmed', 'rescheduled', 'cancelled'))
                            DEFAULT 'sent',

                    -- Timestamps de ciclo de vida
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    confirmed_at TIMESTAMP,
                    response_received_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY (appointment_id) REFERENCES appointments(id) ON DELETE CASCADE,
                    FOREIGN KEY (client_phone) REFERENCES clients(phone)
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_reminders_appointment 
                ON appointment_reminders(appointment_id)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_reminders_client
                ON appointment_reminders(client_phone, status)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_reminders_status 
                ON appointment_reminders(status)
            """)

            # ==========================================
            # TABLE: slot_offers
            # Ofertas de turno adelantado (sistema waitlist)
            # ==========================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS slot_offers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    -- Turno que se liberó (origen de la oferta)
                    freed_appointment_id INTEGER NOT NULL,

                    -- Cliente al que se le ofrece adelantar
                    offered_to_client_phone TEXT NOT NULL,

                    -- Turno original del cliente (el que se adelantaría)
                    original_appointment_id INTEGER NOT NULL,

                    -- Datos del slot libre
                    freed_date DATE NOT NULL,
                    freed_time TEXT NOT NULL,
                    professional_phone TEXT NOT NULL,
                    professional_name TEXT,

                    -- Estado
                    status TEXT CHECK(status IN ('pending', 'accepted', 'rejected', 'expired'))
                             DEFAULT 'pending',

                    -- Timestamps
                    offered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    response_received_at TIMESTAMP,

                    FOREIGN KEY (offered_to_client_phone) REFERENCES clients(phone),
                    FOREIGN KEY (professional_phone) REFERENCES professionals(phone)
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_slot_offers_client
                ON slot_offers(offered_to_client_phone, status)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_slot_offers_freed
                ON slot_offers(freed_appointment_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_slot_offers_expires
                ON slot_offers(expires_at, status)
            """)


    # ==========================================
    # PROFESSIONAL CRUD OPERATIONS
    # ==========================================

    def add_professional(self, phone: str, name: str, email: str = None,
                         zone: str = None, gender: str = None,
                         accept_prepaga: bool = False,
                         category: str = None) -> bool:  # ⭐ Agregar parámetro
        """
        Add or update a professional.

        Args:
            phone: Professional's phone number (unique identifier)
            name: Professional's name
            email: Email address
            zone: Zone ('norte' or 'sur')
            gender: Gender ('m', 'f', 'otro')
            accept_prepaga: Whether accepts prepaga
            category: Professional specialty  # ⭐ Agregar doc

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO professionals (phone, name, email, zone, gender, accept_prepaga, category)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(phone) DO UPDATE SET
                        name = excluded.name,
                        email = excluded.email,
                        zone = excluded.zone,
                        gender = excluded.gender,
                        accept_prepaga = excluded.accept_prepaga,
                        category = excluded.category,
                        updated_at = CURRENT_TIMESTAMP
                """, (phone, name, email, zone, gender, accept_prepaga, category))

            print(f"[DB] ✅ Professional added/updated: {phone}")
            return True
        except Exception as e:
            print(f"[DB] ❌ Error adding professional: {e}")
            return False

    def update_certificate(self, phone: str, certificate_path: str) -> bool:
        """
        Update professional's certificate path.

        Args:
            phone: Professional's phone
            certificate_path: Path to certificate file

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # Primero verificar si el profesional existe
                cursor.execute(
                    "SELECT phone FROM professionals WHERE phone = ?", (phone,))
                exists = cursor.fetchone() is not None

                if exists:
                    # Si existe, solo actualizar
                    cursor.execute("""
                        UPDATE professionals 
                        SET certificate_path = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE phone = ?
                    """, (certificate_path, phone))
                else:
                    # Si no existe, crear con valores mínimos
                    cursor.execute("""
                        INSERT INTO professionals (phone, name, certificate_path)
                        VALUES (?, ?, ?)
                    """, (phone, 'Usuario Nuevo', certificate_path))

            print(f"[DB] ✅ Certificate updated: {phone}")
            return True
        except Exception as e:
            print(f"[DB] ❌ Error updating certificate: {e}")
            return False

    def update_professional_bio(self, phone: str, bio: str) -> bool:
        """Update professional's bio/description."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE professionals 
                    SET bio = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE phone = ?
                """, (bio, phone))
            print(f"[DB] ✅ Bio updated: {phone}")
            return True
        except Exception as e:
            print(f"[DB] ❌ Error updating bio: {e}")
            return False

    def update_professional_fee_range(self, phone: str, fee_range: str) -> bool:
        """Update professional's fee range."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE professionals 
                    SET fee_range = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE phone = ?
                """, (fee_range, phone))
            print(f"[DB] ✅ Fee range updated: {phone}")
            return True
        except Exception as e:
            print(f"[DB] ❌ Error updating fee range: {e}")
            return False

    def get_professional(self, phone: str) -> Optional[Dict]:
        """
        Get professional data by phone.

        Args:
            phone: Professional's phone

        Returns:
            Dictionary with professional data or None
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM professionals WHERE phone = ?", (phone,))
                row = cursor.fetchone()

                if row:
                    return dict(row)
                return None
        except Exception as e:
            print(f"[DB] ❌ Error getting professional: {e}")
            return None

    def professional_has_certificate(self, phone: str) -> bool:
        """
        Check if professional has uploaded certificate.

        Args:
            phone: Professional's phone

        Returns:
            True if certificate exists, False otherwise
        """
        prof = self.get_professional(phone)
        return prof is not None and prof.get('certificate_path') is not None

    # ==========================================
    # SEARCH OPERATIONS
    # ==========================================

    def search_professionals(
        self,
        zone: str = None,
        gender: str = None,
        accept_prepaga: bool = None,
        online_sessions: bool = None,
        specialty: str = None,  # ← NUEVO
        limit: int = 50
    ) -> List[Dict]:
        """
        Search professionals by filters.

        Args:
            zone: Filter by zone ('norte' or 'sur')
            gender: Filter by gender ('m', 'f', 'otro')
            accept_prepaga: Filter by prepaga acceptance
            online_sessions: Filter by online sessions availability

        Returns:
            List of matching professionals
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                query = "SELECT * FROM professionals WHERE 1=1"
                params = []

                if zone:
                    query += " AND zone = ?"
                    params.append(zone)

                if gender:
                    query += " AND gender = ?"
                    params.append(gender)

                if accept_prepaga is not None:
                    query += " AND accept_prepaga = ?"
                    params.append(accept_prepaga)

                if online_sessions is not None:
                    query += " AND online_sessions = ?"
                    params.append(online_sessions)
                
                if specialty:
                    query += " AND category LIKE ?"
                    params.append(f"%{specialty}%")

                # Only verified professionals (with certificate)

                query += " ORDER BY total_contacts DESC, name ASC"

                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"[DB] ❌ Error searching professionals: {e}")
            return []
    # ==========================================
    # CLIENT SEARCH ANALYTICS
    # ==========================================

    def log_client_search(self, client_phone: str, search_type: str,
                          search_params: Dict, result_count: int,
                          session_id: str = None) -> int:
        """
        Log a client search for analytics.

        Args:
            client_phone: Client's phone
            search_type: Type of search ('zona', 'fecha', etc.)
            search_params: Search parameters as dictionary
            result_count: Number of results found
            session_id: Optional session identifier

        Returns:
            Search ID or None if failed
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO client_searches 
                    (client_phone, search_type, search_params, result_count, session_id)
                    VALUES (?, ?, ?, ?, ?)
                """, (client_phone, search_type, json.dumps(search_params),
                      result_count, session_id))

                search_id = cursor.lastrowid
                print(f"[DB] ✅ Client search logged: {search_id}")
                return search_id
        except Exception as e:
            print(f"[DB] ❌ Error logging search: {e}")
            return None

    def log_professional_contact(self, search_id: int, professional_phone: str,
                                 result_position: int = None) -> bool:
        """
        Log when a client contacts a professional.
        Updates search record and professional metrics.

        Args:
            search_id: ID of the search that led to contact
            professional_phone: Professional that was contacted
            result_position: Position in search results (1-based)

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Update search record
                cursor.execute("""
                    UPDATE client_searches 
                    SET professional_contacted = ?,
                        result_position_clicked = ?,
                        search_abandoned = 0
                    WHERE id = ?
                """, (professional_phone, result_position, search_id))

                # Update professional metrics
                cursor.execute("""
                    UPDATE professionals 
                    SET total_contacts = total_contacts + 1,
                        last_contacted_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE phone = ?
                """, (professional_phone,))

                # Recalculate average position
                cursor.execute("""
                    UPDATE professionals 
                    SET avg_search_position = (
                        SELECT AVG(result_position_clicked)
                        FROM client_searches
                        WHERE professional_contacted = ? 
                        AND result_position_clicked IS NOT NULL
                    )
                    WHERE phone = ?
                """, (professional_phone, professional_phone))

            print(f"[DB] ✅ Professional contact logged: {professional_phone}")
            return True
        except Exception as e:
            print(f"[DB] ❌ Error logging contact: {e}")
            return False

    def increment_professional_views(self, phone: str) -> bool:
        """
        Increment view count when professional appears in search results.

        Args:
            phone: Professional's phone

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE professionals 
                    SET total_views = total_views + 1
                    WHERE phone = ?
                """, (phone,))
            return True
        except Exception as e:
            print(f"[DB] ❌ Error incrementing views: {e}")
            return False

    def increment_profile_views(self, phone: str) -> bool:
        """
        Increment profile view count when client views professional detail.

        Args:
            phone: Professional's phone

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE professionals 
                    SET total_profile_views = total_profile_views + 1
                    WHERE phone = ?
                """, (phone,))
            return True
        except Exception as e:
            print(f"[DB] ❌ Error incrementing profile views: {e}")
            return False

    # ==========================================
    # UTILITY METHODS
    # ==========================================

    def get_all_professionals(self) -> List[Dict]:
        """
        Get all professionals (prefer with certificates, fallback to all).
        Returns:
            List of all professionals
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Intentar primero con certificados
                cursor.execute("""
                    SELECT * FROM professionals 
                    WHERE certificate_path IS NOT NULL
                    ORDER BY total_contacts DESC, name ASC
                """)
                results = [dict(row) for row in cursor.fetchall()]
                
                # Fallback: Si no hay con certificados, devolver todos
                if not results:
                    print(f"[DB] ⚠️ No professionals with certificates, returning all")
                    cursor.execute("""
                        SELECT * FROM professionals 
                        ORDER BY total_contacts DESC, name ASC
                    """)
                    results = [dict(row) for row in cursor.fetchall()]
                
                print(f"[DB] ✅ Loaded {len(results)} professionals")
                return results
                
        except Exception as e:
            print(f"[DB] ❌ Error getting all professionals: {e}")
            return []

    def get_stats(self) -> Dict:
        """
        Get general database statistics.

        Returns:
            Dictionary with statistics
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Count professionals
                cursor.execute(
                    "SELECT COUNT(*) as count FROM professionals WHERE certificate_path IS NOT NULL")
                prof_count = cursor.fetchone()['count']

                # Count searches
                cursor.execute("SELECT COUNT(*) as count FROM client_searches")
                search_count = cursor.fetchone()['count']

                # Count contacts
                cursor.execute(
                    "SELECT COUNT(*) as count FROM client_searches WHERE professional_contacted IS NOT NULL")
                contact_count = cursor.fetchone()['count']

                return {
                    'total_professionals': prof_count,
                    'total_searches': search_count,
                    'total_contacts': contact_count,
                    'conversion_rate': (contact_count / search_count * 100) if search_count > 0 else 0
                }
        except Exception as e:
            print(f"[DB] ❌ Error getting stats: {e}")
            return {}

    # ==========================================
    # CLIENTS CRUD OPERATIONS
    # ==========================================

    def add_client(
        self,
        phone: str,
        name: str = None,
        email: str = None,
        age: int = None,
        gender: str = None,
        preferred_zone: str = None,
        has_prepaga: bool = False,
        prepaga_name: str = None
    ) -> bool:
        """
        Add or update a client.

        Args:
            phone: Client's phone number (unique identifier)
            name: Client's name
            email: Email address
            age: Age
            gender: Gender ('m', 'f', 'otro', 'prefiero_no_decir')
            preferred_zone: Preferred zone ('norte', 'sur', 'indistinto')
            has_prepaga: Whether has prepaga
            prepaga_name: Prepaga name

        Returns:
            True if successful, False otherwise
        """
        # Validación defensiva de formato — segunda línea de defensa
        from src.core.validators import validate_phone_e164
        if not validate_phone_e164(phone):
            print(f"[DB] ❌ add_client rechazado: formato de phone inválido: {phone!r}")
            return False
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO clients (phone, name, email, age, gender, preferred_zone, has_prepaga, prepaga_name)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(phone) DO UPDATE SET
                        name = COALESCE(excluded.name, name),
                        email = COALESCE(excluded.email, email),
                        age = COALESCE(excluded.age, age),
                        gender = COALESCE(excluded.gender, gender),
                        preferred_zone = COALESCE(excluded.preferred_zone, preferred_zone),
                        has_prepaga = excluded.has_prepaga,
                        prepaga_name = COALESCE(excluded.prepaga_name, prepaga_name),
                        updated_at = CURRENT_TIMESTAMP,
                        last_interaction_at = CURRENT_TIMESTAMP
                """, (phone, name, email, age, gender, preferred_zone, has_prepaga, prepaga_name))

            print(f"[DB] ✅ Client added/updated: {phone}")
            return True
        except Exception as e:
            print(f"[DB] ❌ Error adding client: {e}")
            return False

    def get_client(self, phone: str) -> Optional[Dict]:
        """
        Get client data by phone.

        Args:
            phone: Client's phone

        Returns:
            Dictionary with client data or None
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM clients WHERE phone = ?", (phone,))
                row = cursor.fetchone()

                if row:
                    return dict(row)
                return None
        except Exception as e:
            print(f"[DB] ❌ Error getting client: {e}")
            return None

    def update_client_last_interaction(self, phone: str) -> bool:
        """
        Update client's last interaction timestamp.

        Args:
            phone: Client's phone

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE clients 
                    SET last_interaction_at = CURRENT_TIMESTAMP
                    WHERE phone = ?
                """, (phone,))

            return True
        except Exception as e:
            print(f"[DB] ❌ Error updating last interaction: {e}")
            return False

    # ==========================================
    # APPOINTMENTS CRUD OPERATIONS
    # ==========================================

    def create_appointment(
        self,
        client_phone: str,
        professional_phone: str,
        appointment_date: str,
        start: str,
        end: str,
        duration_minutes: int = 50,
        session_type: str = 'primera_vez',
        modality: str = 'presencial',
        google_event_id: str = None,  # ⭐ NUEVO PARÁMETRO
        notes: str = None
    ) -> Optional[int]:
        """
        Create a new appointment.
        
        Args:
            client_phone: Client's phone
            professional_phone: Professional's phone
            appointment_date: Date in YYYY-MM-DD format
            start: Start time in HH:MM format
            end: End time in HH:MM format
            duration_minutes: Duration in minutes
            session_type: Type ('primera_vez', 'seguimiento', 'evaluacion')
            modality: Modality ('presencial', 'virtual', 'ambas')
            google_event_id: Google Calendar event ID (for sync) ⭐ NUEVO
            notes: Optional notes
        
        Returns:
            appointment_id if successful, None if failed
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO appointments (
                        client_phone, professional_phone, appointment_date,
                        start, end, duration_minutes,
                        session_type, modality, google_event_id, notes, status
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'confirmada')
                """, (client_phone, professional_phone, appointment_date,
                    start, end, duration_minutes,
                    session_type, modality, google_event_id, notes))
                
                appointment_id = cursor.lastrowid
                
                # Crear registro en historial
                cursor.execute("""
                    INSERT INTO appointment_history (
                        appointment_id, new_status, changed_by, change_reason
                    )
                    VALUES (?, 'confirmada', 'system', 'Cita creada y confirmada automáticamente')
                """, (appointment_id,))
            
            print(f"[DB] ✅ Appointment created: #{appointment_id} (Google ID: {google_event_id})")
            return appointment_id
        except Exception as e:
            print(f"[DB] ❌ Error creating appointment: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_appointment(self, appointment_id: int) -> Optional[Dict]:
        """
        Obtiene una cita por ID.

        SCOPE: admin / sistema — no filtra por cliente.
        NO usar directamente en handlers de cliente sin verificar ownership.
        Para verificar ownership usar: apt['client_phone'] == session.phone_number

        Args:
            appointment_id: ID de la cita

        Returns:
            Diccionario con datos completos o None si no existe
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT a.*, 
                           c.name as client_name,
                           p.name as professional_name
                    FROM appointments a
                    LEFT JOIN clients c ON a.client_phone = c.phone
                    LEFT JOIN professionals p ON a.professional_phone = p.phone
                    WHERE a.id = ?
                """, (appointment_id,))
                row = cursor.fetchone()

                if row:
                    return dict(row)
                return None
        except Exception as e:
            print(f"[DB] ❌ Error getting appointment: {e}")
            return None

    def get_appointments_by_client(self, client_phone: str, from_date: str = None) -> List[Dict]:
        """
        Obtiene citas de un cliente.

        SCOPE: client-scoped — siempre filtra por client_phone.
        Seguro para uso directo en handlers de cliente.

        Args:
            client_phone: Teléfono del cliente (obligatorio — no tiene default)
            from_date: Fecha desde (YYYY-MM-DD), opcional

        Returns:
            Lista de citas del cliente
        """
        query = """
            SELECT 
                a.*,
                p.name as professional_name
            FROM appointments a
            LEFT JOIN professionals p ON a.professional_phone = p.phone
            WHERE a.client_phone = ?
        """
        
        params = [client_phone]
        
        if from_date:
            query += " AND a.appointment_date >= ?"
            params.append(from_date)
        
        query += " ORDER BY a.appointment_date, a.start"
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def count_active_appointments_for_client_with_professional(
        self,
        client_phone: str,
        professional_phone: str
    ) -> int:
        """
        Cuenta turnos activos de un cliente con un profesional específico.

        Se usa para detectar abuso: un mismo número agendando múltiples
        turnos con el mismo profesional para bloquear su agenda.

        Args:
            client_phone: Teléfono del cliente
            professional_phone: Teléfono del profesional

        Returns:
            Cantidad de turnos con status 'pendiente_confirmacion' o 'confirmada'
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM appointments
                    WHERE client_phone = ?
                    AND professional_phone = ?
                    AND status IN ('pendiente_confirmacion', 'confirmada')
                """, (client_phone, professional_phone))

                row = cursor.fetchone()
                count = row['count'] if row else 0

                print(f"[DB] 📊 Turnos activos de {client_phone} con {professional_phone}: {count}")
                return count

        except Exception as e:
            print(f"[DB] ❌ Error contando turnos activos: {e}")
            return 0

    def count_active_appointments_for_client(
        self,
        client_phone: str
    ) -> int:
        """
        Cuenta el total de turnos activos de un cliente en todo el sistema.

        Se usa para detectar abuso global: un mismo número agendando turnos
        con múltiples profesionales para degradar el servicio.

        A diferencia de count_active_appointments_for_client_with_professional(),
        este método no filtra por profesional — cuenta todos los turnos activos
        del número sin importar con quién estén agendados.

        Args:
            client_phone: Teléfono del cliente

        Returns:
            Cantidad total de turnos con status 'pendiente_confirmacion' o 'confirmada'
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM appointments
                    WHERE client_phone = ?
                    AND status IN ('pendiente_confirmacion', 'confirmada')
                """, (client_phone,))

                row = cursor.fetchone()
                count = row['count'] if row else 0

                print(f"[DB] 📊 Turnos activos globales de {client_phone}: {count}")
                return count

        except Exception as e:
            print(f"[DB] ❌ Error contando turnos activos globales: {e}")
            return 0
        
    def get_appointments_by_professional(
        self,
        professional_phone: str,
        status: str = None,
        from_date: str = None
    ) -> List[Dict]:
        """
        Get all appointments for a professional.

        Args:
            professional_phone: Professional's phone
            status: Optional filter by status
            from_date: Optional filter from date (YYYY-MM-DD)

        Returns:
            List of appointment dictionaries
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                query = """
                    SELECT a.*, c.name as client_name
                    FROM appointments a
                    LEFT JOIN clients c ON a.client_phone = c.phone
                    WHERE a.professional_phone = ?
                """
                params = [professional_phone]

                if status:
                    query += " AND a.status = ?"
                    params.append(status)

                if from_date:
                    query += " AND a.appointment_date >= ?"
                    params.append(from_date)

                query += " ORDER BY a.appointment_date ASC, a.start ASC"

                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"[DB] ❌ Error getting professional appointments: {e}")
            return []

    def update_appointment_status(
        self,
        appointment_id: int,
        new_status: str,
        changed_by: str,
        reason: str = None
    ) -> bool:
        """
        Update appointment status.

        Args:
            appointment_id: Appointment ID
            new_status: New status
            changed_by: Who made the change ('client', 'professional', 'system')
            reason: Optional reason for change

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Obtener estado anterior
                cursor.execute(
                    "SELECT status FROM appointments WHERE id = ?", (appointment_id,))
                row = cursor.fetchone()
                if not row:
                    print(f"[DB] ❌ Appointment not found: #{appointment_id}")
                    return False

                previous_status = row['status']

                # Actualizar estado
                cursor.execute("""
                    UPDATE appointments 
                    SET status = ?,
                        updated_at = CURRENT_TIMESTAMP,
                        confirmed_at = CASE WHEN ? = 'confirmada' THEN CURRENT_TIMESTAMP ELSE confirmed_at END,
                        cancelled_at = CASE WHEN ? IN ('cancelada_cliente', 'cancelada_profesional') THEN CURRENT_TIMESTAMP ELSE cancelled_at END,
                        completed_at = CASE WHEN ? = 'completada' THEN CURRENT_TIMESTAMP ELSE completed_at END,
                        cancellation_reason = CASE WHEN ? IN ('cancelada_cliente', 'cancelada_profesional') THEN ? ELSE cancellation_reason END
                    WHERE id = ?
                """, (new_status, new_status, new_status, new_status, new_status, reason, appointment_id))

                # Registrar en historial
                cursor.execute("""
                    INSERT INTO appointment_history (
                        appointment_id, previous_status, new_status, changed_by, change_reason
                    )
                    VALUES (?, ?, ?, ?, ?)
                """, (appointment_id, previous_status, new_status, changed_by, reason))

            print(
                f"[DB] ✅ Appointment #{appointment_id} status updated: {previous_status} → {new_status}")
            return True
        except Exception as e:
            print(f"[DB] ❌ Error updating appointment status: {e}")
            return False

    def update_appointment_datetime(
        self,
        appointment_id: int,
        new_date: str,
        new_start_time: str,
        new_end_time: str,
        changed_by: str
    ) -> bool:
        """
        Update appointment date and time (reschedule).

        Args:
            appointment_id: Appointment ID
            new_date: New date (YYYY-MM-DD)
            new_start_time: New start time (HH:MM)
            new_end_time: New end time (HH:MM)
            changed_by: Who made the change

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Obtener datos anteriores
                cursor.execute("""
                    SELECT appointment_date, start, end 
                    FROM appointments WHERE id = ?
                """, (appointment_id,))
                row = cursor.fetchone()
                if not row:
                    return False

                previous_date = row['appointment_date']
                previous_start = row['start']
                previous_end = row['end']

                # Actualizar fecha y hora
                cursor.execute("""
                    UPDATE appointments 
                    SET appointment_date = ?,
                        start = ?,
                        end = ?,
                        status = 'confirmada',
                        updated_at = CURRENT_TIMESTAMP,
                        last_synced_at = NULL
                    WHERE id = ?
                """, (new_date, new_start_time, new_end_time, appointment_id))

                # Registrar en historial
                cursor.execute("""
                    INSERT INTO appointment_history (
                        appointment_id, 
                        previous_date, new_date,
                        previous_time, new_time,
                        previous_status, new_status,
                        changed_by, change_reason
                    )
                    VALUES (?, ?, ?, ?, ?, 'confirmada', 'reagendada', ?, 'Cita reprogramada')
                """, (appointment_id, previous_date, new_date,
                      previous_start, new_start_time, changed_by))

            print(f"[DB] ✅ Appointment #{appointment_id} rescheduled")
            return True
        except Exception as e:
            print(f"[DB] ❌ Error rescheduling appointment: {e}")
            return False

    def check_time_slot_available(
        self,
        professional_phone: str,
        appointment_date: str,
        start: str,
        end: str,
        exclude_appointment_id: int = None
    ) -> bool:
        """
        Check if a time slot is available (no overlapping appointments).

        Args:
            professional_phone: Professional's phone
            appointment_date: Date to check (YYYY-MM-DD)
            start: Start time (HH:MM)
            end: End time (HH:MM)
            exclude_appointment_id: Optional appointment ID to exclude from check

        Returns:
            True if available, False if occupied
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                query = """
                    SELECT COUNT(*) as count
                    FROM appointments
                    WHERE professional_phone = ?
                      AND appointment_date = ?
                      AND status IN ('pendiente_confirmacion', 'confirmada')
                      AND (
                          (start < ? AND end > ?) OR
                          (start < ? AND end > ?) OR
                          (start >= ? AND end <= ?)
                      )
                """
                params = [professional_phone, appointment_date,
                          end, start,
                          end, end,
                          start, end]

                if exclude_appointment_id:
                    query += " AND id != ?"
                    params.append(exclude_appointment_id)

                cursor.execute(query, params)
                count = cursor.fetchone()['count']

                return count == 0
        except Exception as e:
            print(f"[DB] ❌ Error checking availability: {e}")
            return False

    # ==========================================
    # APPOINTMENT HISTORY OPERATIONS
    # ==========================================

    def get_appointment_history(self, appointment_id: int) -> List[Dict]:
        """
        Get change history for an appointment.

        Args:
            appointment_id: Appointment ID

        Returns:
            List of history records
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT *
                    FROM appointment_history
                    WHERE appointment_id = ?
                    ORDER BY changed_at ASC
                """, (appointment_id,))

                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"[DB] ❌ Error getting appointment history: {e}")
            return []

    # ==========================================
    # NOTIFICATIONS OPERATIONS
    # ==========================================

    def create_notification(
        self,
        recipient_phone: str,
        recipient_type: str,
        notification_type: str,
        message_text: str,
        appointment_id: int = None,
        channel: str = 'whatsapp'
    ) -> Optional[int]:
        """
        Create a notification record.

        Args:
            recipient_phone: Recipient's phone
            recipient_type: 'client' or 'professional'
            notification_type: Type of notification
            message_text: Message content
            appointment_id: Optional related appointment ID
            channel: Communication channel ('whatsapp', 'email', 'sms')

        Returns:
            notification_id if successful, None if failed
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO notifications (
                        recipient_phone, recipient_type, notification_type,
                        message_text, appointment_id, channel, status
                    )
                    VALUES (?, ?, ?, ?, ?, ?, 'pending')
                """, (recipient_phone, recipient_type, notification_type,
                      message_text, appointment_id, channel))

                notification_id = cursor.lastrowid

            print(f"[DB] ✅ Notification created: #{notification_id}")
            return notification_id
        except Exception as e:
            print(f"[DB] ❌ Error creating notification: {e}")
            return None

    def update_notification_status(
        self,
        notification_id: int,
        status: str,
        sent_at: str = None,
        delivered_at: str = None
    ) -> bool:
        """
        Update notification status.

        Args:
            notification_id: Notification ID
            status: New status ('pending', 'sent', 'delivered', 'failed')
            sent_at: Optional timestamp when sent
            delivered_at: Optional timestamp when delivered

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE notifications 
                    SET status = ?,
                        sent_at = COALESCE(?, sent_at),
                        delivered_at = COALESCE(?, delivered_at)
                    WHERE id = ?
                """, (status, sent_at, delivered_at, notification_id))

            return True
        except Exception as e:
            print(f"[DB] ❌ Error updating notification: {e}")
            return False

    def get_pending_notifications(self) -> List[Dict]:
        """
        Get all pending notifications.

        Returns:
            List of pending notifications
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT *
                    FROM notifications
                    WHERE status = 'pending'
                    ORDER BY created_at ASC
                """)

                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"[DB] ❌ Error getting pending notifications: {e}")
            return []

    def check_slot_availability(
        self,
        professional_phone: str,
        date: str,
        start: str,
        end: str,
        exclude_appointment_id: int = None
    ) -> bool:
        """
        Verificar si un slot está disponible.

        Args:
            professional_phone: Teléfono del profesional
            date: Fecha en formato YYYY-MM-DD
            start: Hora de inicio HH:MM
            end: Hora de fin HH:MM
            exclude_appointment_id: ID de cita a excluir (para reprogramación)

        Returns:
            True si está disponible, False si está ocupado
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Buscar citas que se solapen con este horario
                query = """
                    SELECT COUNT(*) as count
                    FROM appointments
                    WHERE professional_phone = ?
                    AND appointment_date = ?
                    AND status NOT IN ('cancelada_cliente', 'cancelada_profesional')
                    AND (
                        (start >= ? AND start < ?) OR
                        (end > ? AND end <= ?) OR
                        (start <= ? AND end >= ?)
                    )
                """

                params = [
                    professional_phone,
                    date,
                    start, end,
                    start, end,
                    start, end
                ]

                # Excluir cita específica si se proporciona
                if exclude_appointment_id:
                    query += " AND id != ?"
                    params.append(exclude_appointment_id)

                cursor.execute(query, params)
                result = cursor.fetchone()

                # Disponible si count == 0
                return result['count'] == 0

        except Exception as e:
            print(f"[DB] ❌ Error checking slot availability: {e}")
            return False

    def get_professional_calendar_config(self, phone: str) -> Optional[Dict]:
            """
            Obtiene configuración de Google Calendar del profesional.
            
            Args:
                phone: Teléfono del profesional
                
            Returns:
                Dict con calendar_id, working_hours, slot_duration, timezone o None
            """
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT calendar_id, working_hours, slot_duration, timezone
                        FROM professionals
                        WHERE phone = ?
                    """, (phone,))
                    
                    row = cursor.fetchone()
                    return dict(row) if row else None
            except Exception as e:
                print(f"[DB] ❌ Error getting calendar config: {e}")
                return None
            
    def update_appointment_from_google(
        self,
        appointment_id: int,
        google_event_data: dict
    ) -> bool:
        """
        Actualiza una cita local con datos de Google Calendar.
        
        Se usa para sincronización cuando el profesional modifica
        la cita directamente en Google Calendar.
        
        Args:
            appointment_id: ID de la cita en BD local
            google_event_data: Diccionario con datos del evento de Google
                {
                    'date': '2026-01-20',
                    'start': '10:00',
                    'end': '10:50',
                    'status': 'confirmada' | 'cancelada_profesional'
                }
        
        Returns:
            True si se actualizó exitosamente, False en caso contrario
        
        Ejemplo:
            >>> google_data = {
            ...     'date': '2026-01-20',
            ...     'start': '10:00',
            ...     'end': '10:50',
            ...     'status': 'confirmada'
            ... }
            >>> db.update_appointment_from_google(123, google_data)
            True
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Actualizar cita con datos de Google
                cursor.execute("""
                    UPDATE appointments 
                    SET 
                        appointment_date = ?,
                        start = ?,
                        end = ?,
                        status = ?,
                        last_synced_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    google_event_data['date'],
                    google_event_data['start'],
                    google_event_data['end'],
                    google_event_data['status'],
                    appointment_id
                ))
                
                if cursor.rowcount == 0:
                    print(f"[DB] ⚠️ No se encontró cita con ID {appointment_id}")
                    return False
                
                # Registrar en historial si hubo cambio de status
                cursor.execute("""
                    INSERT INTO appointment_history (
                        appointment_id, 
                        new_status, 
                        changed_by, 
                        change_reason
                    )
                    VALUES (?, ?, 'system', 'Sincronización desde Google Calendar')
                """, (appointment_id, google_event_data['status']))
                
                print(f"[DB] ✅ Cita #{appointment_id} actualizada desde Google Calendar")
                print(f"      Nueva fecha: {google_event_data['date']} {google_event_data['start']}")
                print(f"      Status: {google_event_data['status']}")
                
                return True
                
        except Exception as e:
            print(f"[DB] ❌ Error actualizando cita desde Google: {e}")
            import traceback
            traceback.print_exc()
            return False
    # =========================================================================
    # WAITLIST / SLOT OFFERS - Sistema de Lista de Espera
    # =========================================================================

    def create_slot_offer(
        self,
        freed_appointment_id: int,
        offered_to_client_phone: str,
        original_appointment_id: int,
        freed_date: str,
        freed_time: str,
        professional_phone: str,
        professional_name: str,
        expires_at: str
    ) -> int:
        """
        Crea registro de oferta de turno adelantado.
        
        Returns:
            offer_id si se creó exitosamente, None si hubo error
        """
        query = """
            INSERT INTO slot_offers 
            (freed_appointment_id, offered_to_client_phone, original_appointment_id,
             freed_date, freed_time, professional_phone, professional_name, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (
                    freed_appointment_id,
                    offered_to_client_phone,
                    original_appointment_id,
                    freed_date,
                    freed_time,
                    professional_phone,
                    professional_name,
                    expires_at
                ))
                return cursor.lastrowid
        except Exception as e:
            print(f"[DB] Error creating slot offer: {e}")
            return None

    def get_pending_slot_offer(self, client_phone: str) -> Dict:
        """
        Obtiene oferta pendiente de un cliente.
        
        Returns:
            Dict con datos de la oferta o None
        """
        query = """
            SELECT *
            FROM slot_offers
            WHERE offered_to_client_phone = ?
            AND status = 'pending'
            AND expires_at > datetime('now')
            ORDER BY offered_at DESC
            LIMIT 1
        """
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (client_phone,))
                row = cursor.fetchone()
                
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, row))
                return None
        except Exception as e:
            print(f"[DB] Error getting pending offer: {e}")
            return None

    def update_slot_offer_status(
        self,
        offer_id: int,
        status: str,
        response_received_at: str = None
    ) -> bool:
        """
        Actualiza estado de oferta.
        
        Args:
            status: 'accepted', 'rejected', 'expired'
        """
        query = """
            UPDATE slot_offers
            SET status = ?,
                response_received_at = COALESCE(?, CURRENT_TIMESTAMP)
            WHERE id = ?
        """
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (status, response_received_at, offer_id))
                return True
        except Exception as e:
            print(f"[DB] Error updating offer status: {e}")
            return False

    def find_waitlist_candidates(
        self,
        professional_phone: str,
        freed_date: str,
        max_days_ahead: int = 30,
        limit: int = 10
    ) -> List[Dict]:
        """
        Busca candidatos para ofrecer turno adelantado.
        
        Criterios:
        - Mismo profesional
        - Turnos en días posteriores
        - Estado confirmada
        - wants_earlier_slot = 1
        - Sin oferta pendiente
        """
        query = """
            SELECT 
                a.id,
                a.client_phone,
                a.appointment_date,
                a.start,
                a.end,
                c.name as client_name
            FROM appointments a
            LEFT JOIN clients c ON a.client_phone = c.phone
            WHERE a.professional_phone = ?
            AND a.appointment_date > ?
            AND a.appointment_date <= DATE(?, '+' || ? || ' days')
            AND a.status = 'confirmada'
            AND (a.wants_earlier_slot IS NULL OR a.wants_earlier_slot = 1)
            AND a.client_phone NOT IN (
                SELECT offered_to_client_phone 
                FROM slot_offers 
                WHERE status = 'pending'
                AND expires_at > datetime('now')
            )
            ORDER BY a.appointment_date ASC, a.start ASC
            LIMIT ?
        """
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (
                    professional_phone,
                    freed_date,
                    freed_date,
                    max_days_ahead,
                    limit
                ))
                
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            print(f"[DB] Error finding candidates: {e}")
            return []

    def move_appointment_to_earlier_slot(
        self,
        appointment_id: int,
        new_date: str,
        new_time: str,
        offer_id: int
    ) -> bool:
        """
        Mueve un turno a un slot más temprano.
        """
        query = """
            UPDATE appointments
            SET appointment_date = ?,
                start = ?,
                moved_from_offer_id = ?
            WHERE id = ?
        """
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (new_date, new_time, offer_id, appointment_id))
                return True
        except Exception as e:
            print(f"[DB] Error moving appointment: {e}")
            return False

    def expire_old_slot_offers(self) -> int:
        """
        Marca ofertas expiradas.
        
        Returns:
            Cantidad de ofertas expiradas
        """
        query = """
            UPDATE slot_offers
            SET status = 'expired'
            WHERE status = 'pending'
            AND expires_at < datetime('now')
        """
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                return cursor.rowcount
        except Exception as e:
            print(f"[DB] Error expiring offers: {e}")
            return 0

    def get_expired_pending_offers(self) -> list:
        """
        Retorna todas las ofertas con status='pending' cuyo expires_at ya pasó.

        Usado por process_expired_offers() en waitlist_service para
        limpiar ofertas sin respuesta y reintentar la cascada.

        Returns:
            Lista de dicts con los datos completos de cada oferta expirada
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT *
                    FROM slot_offers
                    WHERE status = 'pending'
                    AND expires_at <= CURRENT_TIMESTAMP
                    ORDER BY expires_at ASC
                """)
                columns = [desc[0] for desc in cursor.description]
                results = [dict(zip(columns, row)) for row in cursor.fetchall()]

                print(f"[DB] 📊 Ofertas expiradas sin procesar: {len(results)}")
                return results

        except Exception as e:
            print(f"[DB] ❌ Error obteniendo ofertas expiradas: {e}")
            return []
                
    # ==========================================
    # REMINDER OPERATIONS
    # ==========================================

    def create_reminder(
        self,
        appointment_id: int,
        reminder_type: str,
        scheduled_for: str
    ) -> Optional[int]:
        """
        Crear un recordatorio programado.
        
        Args:
            appointment_id: ID de la cita
            reminder_type: '24h' o '1h'
            scheduled_for: Timestamp en formato ISO
        
        Returns:
            reminder_id si exitoso, None si falla
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO appointment_reminders (
                        appointment_id, reminder_type, scheduled_for
                    )
                    VALUES (?, ?, ?)
                """, (appointment_id, reminder_type, scheduled_for))
                
                reminder_id = cursor.lastrowid
                print(f"[DB] ✅ Reminder created: #{reminder_id}")
                return reminder_id
        except Exception as e:
            print(f"[DB] ❌ Error creating reminder: {e}")
            return None

    def get_pending_reminders(self, before_time: str = None) -> List[Dict]:
        """
        Obtener recordatorios pendientes de envío.
        
        Args:
            before_time: Timestamp límite (formato ISO)
        
        Returns:
            Lista de recordatorios pendientes
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                query = """
                    SELECT r.*, a.client_phone, a.professional_phone
                    FROM appointment_reminders r
                    JOIN appointments a ON r.appointment_id = a.id
                    WHERE r.sent = 0
                """
                
                params = []
                if before_time:
                    query += " AND r.scheduled_for <= ?"
                    params.append(before_time)
                
                query += " ORDER BY r.scheduled_for ASC"
                
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"[DB] ❌ Error getting pending reminders: {e}")
            return []

    def mark_reminder_sent(self, reminder_id: int) -> bool:
        """
        Marcar recordatorio como enviado.
        
        Args:
            reminder_id: ID del recordatorio
        
        Returns:
            True si exitoso
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE appointment_reminders
                    SET sent = 1,
                        sent_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (reminder_id,))
                
                return True
        except Exception as e:
            print(f"[DB] ❌ Error marking reminder sent: {e}")
            return False

    def record_reminder_response(
        self,
        reminder_id: int,
        response: str
    ) -> bool:
        """
        Registrar respuesta del usuario a un recordatorio.
        
        Args:
            reminder_id: ID del recordatorio
            response: Texto de la respuesta
        
        Returns:
            True si exitoso
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE appointment_reminders
                    SET response_received = 1,
                        response = ?,
                        responded_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (response, reminder_id))
                
                return True
        except Exception as e:
            print(f"[DB] ❌ Error recording response: {e}")
            return False

    
# Global database instance
db = Database()