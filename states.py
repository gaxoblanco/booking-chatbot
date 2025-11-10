"""
Conversation States
===================
Defines all possible states in the conversation flow.
Uses a state machine pattern to manage user interactions.
"""

from enum import Enum


class UserRole(Enum):
    """
    User role in the system.
    Determines which menu and options are available.
    """
    UNKNOWN = "unknown"
    PROFESSIONAL = "professional"
    CLIENT = "client"


class ConversationState(Enum):
    """
    All possible states in the conversation flow.
    State machine transitions based on user input.
    """

    # ==========================================
    # INITIAL STATES
    # ==========================================
    START = "start"  # Initial state, ask for role
    ROLE_SELECTION = "role_selection"  # Waiting for role choice

    # ==========================================
    # PROFESSIONAL STATES
    # ==========================================

    # Certificate upload (mandatory first step)
    PROF_NEED_CERTIFICATE = "prof_need_certificate"  # Must upload certificate
    PROF_UPLOADING_CERTIFICATE = "prof_uploading_certificate"  # Waiting for file

    # Main menu
    PROF_MAIN_MENU = "prof_main_menu"  # Show professional menu

    # Option 1: Liberar horario específico (mark slot as FREE)
    PROF_FREE_SLOT_DATE = "prof_free_slot_date"  # Ask for date
    PROF_FREE_SLOT_TIME = "prof_free_slot_time"  # Ask for time range
    PROF_FREE_SLOT_CONFIRM = "prof_free_slot_confirm"  # Confirm before saving

    # Option 3: Cargar semana completa (weekly recurring schedule)
    PROF_WEEK_SCHEDULE_QUICK = "prof_week_schedule_quick"

    # Option 5: Cargar información profesional
    PROF_INFO_MENU = "prof_info_menu"  # Main info menu
    PROF_INFO_NAME = "prof_info_name"  # Ask for name
    PROF_INFO_EMAIL = "prof_info_email"  # Ask for email
    PROF_INFO_ZONA = "prof_info_zona"  # Ask for zone
    PROF_INFO_GENERO = "prof_info_genero"  # Ask for gender
    PROF_INFO_PREPAGA = "prof_info_prepaga"  # Ask for prepaga
    PROF_INFO_ESPECIALIDAD = "prof_info_especialidad"  # Ask for specialty
    PROF_INFO_QUICK = "prof_info_quick"
    PROF_INFO_BIO = "prof_info_bio"
    PROF_INFO_FEE_RANGE = "prof_info_fee_range"

    # Professional - Manage free slots
    PROF_MANAGE_FREE_SLOTS = "prof_manage_free_slots"
    PROF_DELETE_FREE_SLOT = "prof_delete_free_slot"

    # Client states - Multi-filter
    CLIENT_MULTIFILTER_MENU = "client_multifilter_menu"  # Main filter selection menu
    CLIENT_MULTIFILTER_ZONA = "client_multifilter_zona"
    CLIENT_MULTIFILTER_FECHA = "client_multifilter_fecha"
    CLIENT_MULTIFILTER_HORA = "client_multifilter_hora"
    CLIENT_MULTIFILTER_PREPAGA = "client_multifilter_prepaga"
    CLIENT_MULTIFILTER_SEXO = "client_multifilter_sexo"
    CLIENT_MULTIFILTER_ESPECIALIDAD = "client_multifilter_especialidad"
    # Quick search (all filters at once)
    CLIENT_SEARCH_QUICK = "client_search_quick"

    # ==========================================
    # CLIENT STATES
    # ==========================================

    # Main menu
    CLIENT_MAIN_MENU = "client_main_menu"  # Show search options

    # Filter selection
    CLIENT_SELECT_FILTERS = "client_select_filters"  # Which filters to apply?

    # Zona filter
    CLIENT_FILTER_ZONA = "client_filter_zona"  # Ask for zone (Sur/Norte)

    # Disponibilidad filter
    CLIENT_FILTER_FECHA = "client_filter_fecha"  # Ask for date
    CLIENT_FILTER_HORA = "client_filter_hora"  # Ask for time

    # Prepaga filter
    CLIENT_FILTER_PREPAGA = "client_filter_prepaga"  # Ask yes/no

    # Sexo filter
    CLIENT_FILTER_SEXO = "client_filter_sexo"  # Ask M/F/Otro

    # Results
    CLIENT_SHOW_RESULTS = "client_show_results"  # Display search results
    CLIENT_VIEW_DETAIL = "client_view_detail"  # Show professional detail

    # ==========================================
    # COMMON STATES
    # ==========================================
    ERROR = "error"  # Error state, show error message
    CANCELLED = "cancelled"  # User cancelled operation


class SessionData:
    """
    Data structure to store temporary session data.
    Each user has their own session.
    """

    def __init__(self, phone_number: str):
        """
        Initialize session for a user.

        Args:
            phone_number: User's WhatsApp phone number
        """
        self.phone_number = phone_number
        self.role = UserRole.UNKNOWN
        self.state = ConversationState.START
        self.temp_data = {}  # Temporary data for multi-step operations

    def reset(self):
        """Reset session to initial state."""
        self.state = ConversationState.START
        self.temp_data = {}

    def set_role(self, role: UserRole):
        """Set user role and transition to appropriate menu."""
        self.role = role
        if role == UserRole.PROFESSIONAL:
            # Check if certificate exists (will be implemented in bot.py)
            self.state = ConversationState.PROF_NEED_CERTIFICATE
        elif role == UserRole.CLIENT:
            self.state = ConversationState.CLIENT_MAIN_MENU

    def transition_to(self, new_state: ConversationState):
        """
        Transition to a new state.

        Args:
            new_state: Target state
        """
        print(
            f"[STATE] {self.phone_number}: {self.state.value} → {new_state.value}")
        self.state = new_state

    def store_temp(self, key: str, value):
        """
        Store temporary data for current operation.

        Args:
            key: Data key
            value: Data value
        """
        self.temp_data[key] = value

    def get_temp(self, key: str, default=None):
        """
        Retrieve temporary data.

        Args:
            key: Data key
            default: Default value if key not found

        Returns:
            Stored value or default
        """
        return self.temp_data.get(key, default)

    def clear_temp(self):
        """Clear all temporary data."""
        self.temp_data = {}


class SessionManager:
    """
    Manages all user sessions.
    In-memory storage for MVP (can be replaced with Redis later).
    """

    def __init__(self):
        """Initialize session manager."""
        self.sessions = {}  # phone_number -> SessionData

    def get_session(self, phone_number: str) -> SessionData:
        """
        Get or create session for a user.

        Args:
            phone_number: User's WhatsApp phone number

        Returns:
            SessionData for the user
        """
        if phone_number not in self.sessions:
            self.sessions[phone_number] = SessionData(phone_number)
        return self.sessions[phone_number]

    def delete_session(self, phone_number: str):
        """
        Delete a user's session.

        Args:
            phone_number: User's WhatsApp phone number
        """
        if phone_number in self.sessions:
            del self.sessions[phone_number]

    def get_active_sessions_count(self) -> int:
        """
        Get count of active sessions.

        Returns:
            Number of active sessions
        """
        return len(self.sessions)


# Global session manager instance
session_manager = SessionManager()
