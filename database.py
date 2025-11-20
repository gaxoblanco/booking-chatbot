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
            # TABLE: professionals (PSIVALE VERSION)
            # ==========================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS professionals (
                    phone TEXT PRIMARY KEY,
                    name TEXT,
                    email TEXT,
                    zone TEXT CHECK(zone IN ('norte', 'sur', 'nueva_cordoba')),
                    certificate_path TEXT,
                    gender TEXT CHECK(gender IN ('m', 'f', 'otro')),
                    accept_prepaga BOOLEAN DEFAULT 0,
                    
                    -- CAMPOS PSIVALE (NUEVOS)
                    enfoque_terapeutico TEXT,  -- JSON array: ["tcc", "gestaltica"]
                    poblacion TEXT,            -- JSON array: ["adultos", "parejas"]
                    modalidad TEXT CHECK(modalidad IN ('online', 'presencial', 'ambas')),
                    horarios_disponibles TEXT, -- JSON array: ["manana", "tarde"]
                    
                    -- Campos descriptivos
                    category TEXT,  -- DEPRECADO en Psivale, usar enfoque_terapeutico
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
            # TABLE: client_searches (ANALYTICS)
            # ==========================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS client_searches (
                    search_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_phone TEXT NOT NULL,
                    search_type TEXT,
                    search_params TEXT,
                    result_count INTEGER,
                    session_id TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Index for analytics queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_searches_client 
                ON client_searches(client_phone)
            """)

            # ==========================================
            # TABLE: contact_logs (ANALYTICS)
            # ==========================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS contact_logs (
                    contact_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    search_id INTEGER,
                    client_phone TEXT NOT NULL,
                    professional_phone TEXT NOT NULL,
                    result_position INTEGER,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (search_id) REFERENCES client_searches(search_id),
                    FOREIGN KEY (professional_phone) REFERENCES professionals(phone)
                )
            """)

            # Index for contact logs
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_contact_logs_professional 
                ON contact_logs(professional_phone)
            """)

            # ==========================================
            # TABLE: profile_views (ANALYTICS)
            # ==========================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS profile_views (
                    view_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    professional_phone TEXT NOT NULL,
                    client_phone TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (professional_phone) REFERENCES professionals(phone)
                )
            """)

            # Index for profile views
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_profile_views_professional 
                ON profile_views(professional_phone)
            """)

            # Commit all changes
            conn.commit()
            print("✅ Database initialized successfully")
    # ==========================================
    # PROFESSIONAL CRUD OPERATIONS
    # ==========================================

    def add_professional(self, phone: str, name: str = None, email: str = None,
                         zone: str = None, gender: str = None,
                         accept_prepaga: bool = False,
                         category: str = None,
                         enfoque_terapeutico: List[str] = None,
                         poblacion: List[str] = None,
                         modalidad: str = None,
                         horarios_disponibles: List[str] = None) -> bool:
        """
        Add or update a professional (Psivale version).

        Args:
            phone: Professional's phone number (unique identifier)
            name: Professional's name
            email: Email address
            zone: Zone ('norte', 'sur', 'nueva_cordoba')
            gender: Gender ('m', 'f', 'otro')
            accept_prepaga: Whether accepts prepaga
            category: DEPRECADO - usar enfoque_terapeutico
            enfoque_terapeutico: List of therapeutic approaches (up to 2)
            poblacion: List of populations served
            modalidad: Modality ('online', 'presencial', 'ambas')
            horarios_disponibles: List of available schedules

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Convert lists to JSON
                enfoque_json = json.dumps(
                    enfoque_terapeutico) if enfoque_terapeutico else None
                poblacion_json = json.dumps(poblacion) if poblacion else None
                horarios_json = json.dumps(
                    horarios_disponibles) if horarios_disponibles else None

                cursor.execute("""
                    INSERT INTO professionals (
                        phone, name, email, zone, gender, accept_prepaga, category,
                        enfoque_terapeutico, poblacion, modalidad, horarios_disponibles
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(phone) DO UPDATE SET
                        name = excluded.name,
                        email = excluded.email,
                        zone = excluded.zone,
                        gender = excluded.gender,
                        accept_prepaga = excluded.accept_prepaga,
                        category = excluded.category,
                        enfoque_terapeutico = excluded.enfoque_terapeutico,
                        poblacion = excluded.poblacion,
                        modalidad = excluded.modalidad,
                        horarios_disponibles = excluded.horarios_disponibles,
                        updated_at = CURRENT_TIMESTAMP
                """, (phone, name, email, zone, gender, accept_prepaga, category,
                      enfoque_json, poblacion_json, modalidad, horarios_json))

            print(f"[DB] ✅ Professional added/updated: {phone}")
            return True
        except Exception as e:
            print(f"[DB] ❌ Error adding professional: {e}")
            import traceback
            traceback.print_exc()
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

    def update_professional_enfoque(self, phone: str, enfoque_list: List[str]) -> bool:
        """
        Update professional's therapeutic approaches (Psivale).

        Args:
            phone: Professional's phone
            enfoque_list: List of approaches (max 2): ["tcc", "gestaltica"]
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                enfoque_json = json.dumps(enfoque_list[:2])  # Max 2
                cursor.execute("""
                    UPDATE professionals 
                    SET enfoque_terapeutico = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE phone = ?
                """, (enfoque_json, phone))
            print(f"[DB] ✅ Enfoque updated: {phone}")
            return True
        except Exception as e:
            print(f"[DB] ❌ Error updating enfoque: {e}")
            return False

    def update_professional_poblacion(self, phone: str, poblacion_list: List[str]) -> bool:
        """
        Update professional's population served (Psivale).

        Args:
            phone: Professional's phone
            poblacion_list: List: ["ninos", "adultos", "parejas"]
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                poblacion_json = json.dumps(poblacion_list)
                cursor.execute("""
                    UPDATE professionals 
                    SET poblacion = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE phone = ?
                """, (poblacion_json, phone))
            print(f"[DB] ✅ Población updated: {phone}")
            return True
        except Exception as e:
            print(f"[DB] ❌ Error updating población: {e}")
            return False

    def update_professional_modalidad(self, phone: str, modalidad: str) -> bool:
        """
        Update professional's modality (Psivale).

        Args:
            phone: Professional's phone
            modalidad: 'online', 'presencial', or 'ambas'
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE professionals 
                    SET modalidad = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE phone = ?
                """, (modalidad, phone))
            print(f"[DB] ✅ Modalidad updated: {phone}")
            return True
        except Exception as e:
            print(f"[DB] ❌ Error updating modalidad: {e}")
            return False

    def update_professional_horarios(self, phone: str, horarios_list: List[str]) -> bool:
        """
        Update professional's available schedules (Psivale).

        Args:
            phone: Professional's phone
            horarios_list: List: ["manana", "tarde", "noche", "sabado"]
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                horarios_json = json.dumps(horarios_list)
                cursor.execute("""
                    UPDATE professionals 
                    SET horarios_disponibles = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE phone = ?
                """, (horarios_json, phone))
            print(f"[DB] ✅ Horarios updated: {phone}")
            return True
        except Exception as e:
            print(f"[DB] ❌ Error updating horarios: {e}")
            return False

    def get_professional(self, phone: str) -> Optional[Dict]:
        """
        Get professional data by phone.

        Returns dict with JSON fields parsed.
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM professionals WHERE phone = ?", (phone,))
                row = cursor.fetchone()

                if row:
                    prof_dict = dict(row)

                    # Parse JSON fields
                    if prof_dict.get('enfoque_terapeutico'):
                        try:
                            prof_dict['enfoque_terapeutico'] = json.loads(
                                prof_dict['enfoque_terapeutico'])
                        except:
                            prof_dict['enfoque_terapeutico'] = []

                    if prof_dict.get('poblacion'):
                        try:
                            prof_dict['poblacion'] = json.loads(
                                prof_dict['poblacion'])
                        except:
                            prof_dict['poblacion'] = []

                    if prof_dict.get('horarios_disponibles'):
                        try:
                            prof_dict['horarios_disponibles'] = json.loads(
                                prof_dict['horarios_disponibles'])
                        except:
                            prof_dict['horarios_disponibles'] = []

                    return prof_dict
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
                             accept_prepaga: bool = None, online_sessions: bool = None) -> List[Dict]:
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

                # Only verified professionals (with certificate)
                query += " AND certificate_path IS NOT NULL"

                query += " ORDER BY total_contacts DESC, name ASC"

                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"[DB] ❌ Error searching professionals: {e}")
            return []

    def search_professionals_psivale(
        self,
        enfoque: str = None,
        poblacion: str = None,
        modalidad: str = None,
        zone: str = None,
        horarios: str = None,
        fee_range: str = None,
        gender: str = None
    ) -> List[Dict]:
        """
        Search professionals with Psivale filters.

        Args:
            enfoque: Therapeutic approach to search (e.g., "tcc")
            poblacion: Population to search (e.g., "adultos")
            modalidad: Modality filter
            zone: Zone filter
            horarios: Schedule filter (e.g., "manana")
            fee_range: Fee range filter
            gender: Gender filter

        Returns:
            List of matching professionals
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Base query - only certified professionals
                query = "SELECT * FROM professionals WHERE certificate_path IS NOT NULL"
                params = []

                # Add filters
                if enfoque:
                    query += " AND enfoque_terapeutico LIKE ?"
                    params.append(f'%"{enfoque}"%')

                if poblacion:
                    query += " AND poblacion LIKE ?"
                    params.append(f'%"{poblacion}"%')

                if modalidad:
                    query += " AND (modalidad = ? OR modalidad = 'ambas')"
                    params.append(modalidad)

                if zone:
                    query += " AND zone = ?"
                    params.append(zone)

                if horarios:
                    query += " AND horarios_disponibles LIKE ?"
                    params.append(f'%"{horarios}"%')

                if fee_range:
                    query += " AND fee_range = ?"
                    params.append(fee_range)

                if gender:
                    query += " AND gender = ?"
                    params.append(gender)

                cursor.execute(query, params)
                rows = cursor.fetchall()

                results = []
                for row in rows:
                    prof_dict = dict(row)

                    # Parse JSON fields
                    if prof_dict.get('enfoque_terapeutico'):
                        try:
                            prof_dict['enfoque_terapeutico'] = json.loads(
                                prof_dict['enfoque_terapeutico'])
                        except:
                            prof_dict['enfoque_terapeutico'] = []

                    if prof_dict.get('poblacion'):
                        try:
                            prof_dict['poblacion'] = json.loads(
                                prof_dict['poblacion'])
                        except:
                            prof_dict['poblacion'] = []

                    if prof_dict.get('horarios_disponibles'):
                        try:
                            prof_dict['horarios_disponibles'] = json.loads(
                                prof_dict['horarios_disponibles'])
                        except:
                            prof_dict['horarios_disponibles'] = []

                    results.append(prof_dict)

                return results

        except Exception as e:
            print(f"[DB] ❌ Error searching professionals: {e}")
            import traceback
            traceback.print_exc()
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
        """Get database statistics."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Total professionals
                cursor.execute("SELECT COUNT(*) FROM professionals")
                total_professionals = cursor.fetchone()[0]

                # Total searches
                cursor.execute("SELECT COUNT(*) FROM client_searches")
                total_searches = cursor.fetchone()[0]

                # Total contacts (usando contact_logs, no professional_contacted)
                try:
                    cursor.execute("SELECT COUNT(*) FROM contact_logs")
                    total_contacts = cursor.fetchone()[0]
                except:
                    total_contacts = 0

                return {
                    'total_professionals': total_professionals,
                    'total_searches': total_searches,
                    'total_contacts': total_contacts
                }

        except Exception as e:
            print(f"[DB] ❌ Error getting stats: {e}")
            return {
                'total_professionals': 0,
                'total_searches': 0,
                'total_contacts': 0
            }


# Global database instance
db = Database()
