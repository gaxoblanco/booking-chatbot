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
                    
                    -- Metrics
                    total_views INTEGER DEFAULT 0,
                    total_profile_views INTEGER DEFAULT 0,
                    total_contacts INTEGER DEFAULT 0,
                    avg_search_position REAL DEFAULT 0.0,
                    last_contacted_at TIMESTAMP,
                    
                    -- Timestamps
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # ==========================================
            # TABLE: weekly_schedule
            # ==========================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS weekly_schedule (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    professional_phone TEXT NOT NULL,
                    day_of_week INTEGER NOT NULL CHECK(day_of_week BETWEEN 0 AND 6),
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    is_busy BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY (professional_phone) REFERENCES professionals(phone) ON DELETE CASCADE,
                    UNIQUE(professional_phone, day_of_week, start_time, end_time)
                )
            """)

            # Index for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_weekly_schedule_phone 
                ON weekly_schedule(professional_phone)
            """)

            # ==========================================
            # TABLE: specific_free_slots
            # ==========================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS specific_free_slots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    professional_phone TEXT NOT NULL,
                    date TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY (professional_phone) REFERENCES professionals(phone) ON DELETE CASCADE,
                    UNIQUE(professional_phone, date, start_time, end_time)
                )
            """)

            # Index for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_free_slots_phone_date 
                ON specific_free_slots(professional_phone, date)
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

            conn.commit()
            print("✅ Database initialized successfully")

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
    # WEEKLY SCHEDULE OPERATIONS
    # ==========================================

    def add_weekly_schedule(self, phone: str, day_of_week: int,
                            start_time: str, end_time: str) -> bool:
        """
        Add recurring busy hours for a specific day of week.

        Args:
            phone: Professional's phone
            day_of_week: Day number (0=Monday, 6=Sunday)
            start_time: Start time in HH:MM format
            end_time: End time in HH:MM format

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO weekly_schedule 
                    (professional_phone, day_of_week, start_time, end_time, is_busy)
                    VALUES (?, ?, ?, ?, 1)
                    ON CONFLICT(professional_phone, day_of_week, start_time, end_time) 
                    DO UPDATE SET is_busy = 1
                """, (phone, day_of_week, start_time, end_time))

            print(
                f"[DB] ✅ Weekly schedule added: {phone}, day {day_of_week}, {start_time}-{end_time}")
            return True
        except Exception as e:
            print(f"[DB] ❌ Error adding weekly schedule: {e}")
            return False

    def get_weekly_schedule(self, phone: str) -> List[Dict]:
        """
        Get all weekly schedules for a professional.

        Args:
            phone: Professional's phone

        Returns:
            List of schedule dictionaries
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM weekly_schedule 
                    WHERE professional_phone = ? AND is_busy = 1
                    ORDER BY day_of_week, start_time
                """, (phone,))

                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"[DB] ❌ Error getting weekly schedule: {e}")
            return []

    def remove_weekly_schedule(self, phone: str, day_of_week: int,
                               start_time: str, end_time: str) -> bool:
        """
        Remove a recurring busy schedule.

        Args:
            phone: Professional's phone
            day_of_week: Day number
            start_time: Start time
            end_time: End time

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM weekly_schedule 
                    WHERE professional_phone = ? 
                    AND day_of_week = ? 
                    AND start_time = ? 
                    AND end_time = ?
                """, (phone, day_of_week, start_time, end_time))

            print(
                f"[DB] ✅ Weekly schedule removed: {phone}, day {day_of_week}")
            return True
        except Exception as e:
            print(f"[DB] ❌ Error removing weekly schedule: {e}")
            return False

    # ==========================================
    # SPECIFIC FREE SLOTS OPERATIONS
    # ==========================================

    def add_free_slot(self, phone: str, date: str,
                      start_time: str, end_time: str) -> bool:
        """
        Mark a specific date/time as FREE (overrides weekly schedule).

        Args:
            phone: Professional's phone
            date: Date in YYYY-MM-DD format
            start_time: Start time in HH:MM format
            end_time: End time in HH:MM format

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO specific_free_slots 
                    (professional_phone, date, start_time, end_time)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(professional_phone, date, start_time, end_time) 
                    DO NOTHING
                """, (phone, date, start_time, end_time))

            print(
                f"[DB] ✅ Free slot added: {phone}, {date} {start_time}-{end_time}")
            return True
        except Exception as e:
            print(f"[DB] ❌ Error adding free slot: {e}")
            return False

    def get_free_slots(self, phone: str, from_date: str = None) -> List[Dict]:
        """
        Get all specific free slots for a professional.

        Args:
            phone: Professional's phone
            from_date: Optional start date filter (YYYY-MM-DD)

        Returns:
            List of free slot dictionaries
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                if from_date:
                    cursor.execute("""
                        SELECT * FROM specific_free_slots 
                        WHERE professional_phone = ? AND date >= ?
                        ORDER BY date, start_time
                    """, (phone, from_date))
                else:
                    cursor.execute("""
                        SELECT * FROM specific_free_slots 
                        WHERE professional_phone = ?
                        ORDER BY date, start_time
                    """, (phone,))

                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"[DB] ❌ Error getting free slots: {e}")
            return []

    def remove_free_slot(self, phone: str, date: str,
                         start_time: str, end_time: str) -> bool:
        """
        Remove a specific free slot.

        Args:
            phone: Professional's phone
            date: Date in YYYY-MM-DD format
            start_time: Start time
            end_time: End time

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM specific_free_slots 
                    WHERE professional_phone = ? 
                    AND date = ? 
                    AND start_time = ? 
                    AND end_time = ?
                """, (phone, date, start_time, end_time))

            print(f"[DB] ✅ Free slot removed: {phone}, {date}")
            return True
        except Exception as e:
            print(f"[DB] ❌ Error removing free slot: {e}")
            return False

    # ==========================================
    # SEARCH OPERATIONS
    # ==========================================

    def search_professionals(self, zone: str = None, gender: str = None,
                             accept_prepaga: bool = None) -> List[Dict]:
        """
        Search professionals by filters.

        Args:
            zone: Filter by zone ('norte' or 'sur')
            gender: Filter by gender ('m', 'f', 'otro')
            accept_prepaga: Filter by prepaga acceptance

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

                # Only verified professionals (with certificate)
                query += " AND certificate_path IS NOT NULL"

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
        Get all professionals (with certificates only).

        Returns:
            List of all verified professionals
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM professionals 
                    WHERE certificate_path IS NOT NULL
                    ORDER BY total_contacts DESC, name ASC
                """)
                return [dict(row) for row in cursor.fetchall()]
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


# Global database instance
db = Database()
