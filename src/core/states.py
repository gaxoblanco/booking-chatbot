"""
Conversation States v3.1
=========================
Define todos los estados posibles en el flujo conversacional.
Usa un patrón de máquina de estados para gestionar interacciones del usuario.

CAMBIOS EN v3.1:
- ✅ Simplificado: Solo estados esenciales de cliente y menú profesional
- ✅ Timeout de sesión: Sesiones expiran tras 30 min de inactividad
- ✅ Mejor manejo de datos temporales en sesión
"""

from enum import Enum
from datetime import datetime, timedelta


class UserRole(Enum):
    """
    Rol del usuario en el sistema.
    Determina qué menú y opciones están disponibles.
    """
    UNKNOWN = "unknown"
    PROFESSIONAL = "professional"
    CLIENT = "client"


class ConversationState(Enum):
    """
    Todos los estados posibles en el flujo conversacional.
    Transiciones de máquina de estados basadas en input del usuario.
    
    v3.0: Flujo simplificado enfocado en clientes.
    """

    # ==========================================
    # ESTADOS INICIALES
    # ==========================================
    START = "start"  # Estado inicial

    # Menú principal (solo lectura para profesionales registrados)
    PROF_MAIN_MENU = "prof_main_menu"

    # Ver citas agendadas (lectura desde Google Calendar)
    PROF_VIEW_APPOINTMENTS = "prof_view_appointments"

    # Importación de agenda desde CSV/Excel
    PROF_AGENDA_IMPORT_REVIEW = "prof_agenda_import_review"  # menú de confirmación
    PROF_AGENDA_IMPORT_DETAIL = "prof_agenda_import_detail"  # viendo un subconjunto

    # Edición de información profesional (opcional)
    PROF_INFO_MENU = "prof_info_menu"
    PROF_INFO_NAME = "prof_info_name"
    PROF_INFO_EMAIL = "prof_info_email"
    PROF_INFO_ZONA = "prof_info_zona"
    PROF_INFO_GENERO = "prof_info_genero"
    PROF_INFO_PREPAGA = "prof_info_prepaga"
    PROF_INFO_ESPECIALIDAD = "prof_info_especialidad"
    PROF_INFO_QUICK = "prof_info_quick"
    PROF_INFO_BIO = "prof_info_bio"
    PROF_INFO_FEE_RANGE = "prof_info_fee_range"

    # ==========================================
    # ESTADOS DE CLIENTE - BÚSQUEDA Y FILTROS
    # ==========================================

    # Menú principal
    CLIENT_MAIN_MENU = "client_main_menu"
    CLIENT_NEW_USER_MENU = "client_new_user_menu"
    
    # Búsqueda con múltiples filtros (sistema modular)
    CLIENT_MULTIFILTER_MENU = "client_multifilter_menu"
    CLIENT_FILTER_INPUT = "client_filter_input"
    CLIENT_SEARCH_QUICK = "client_search_quick"
    
    # Mostrar resultados
    CLIENT_SHOW_RESULTS = "client_show_results"
    CLIENT_VIEW_DETAIL = "client_view_detail"

    # ==========================================
    # ESTADOS DE CLIENTE - RESERVA DE CITAS
    # ==========================================

    CLIENT_VIEW_DETAIL_WITH_BOOKING = "client_view_detail_with_booking"
    CLIENT_CONFIRM_BOOKING = "client_confirm_booking"
    CLIENT_COLLECT_OWN_NAME = "client_collect_own_name"

    # GAP 2 — Recolección de datos del tercero (booking_for == 'other')
    CLIENT_THIRD_PARTY_CHOICE = "client_third_party_choice"   # ¿Tus datos o los del paciente?
    CLIENT_THIRD_PARTY_NAME   = "client_third_party_name"     # Nombre del tercero (obligatorio)
    CLIENT_THIRD_PARTY_PHONE  = "client_third_party_phone"    # Teléfono del tercero (opcional)
    CLIENT_THIRD_PARTY_AGE    = "client_third_party_age"      # Edad del tercero (siempre)

    CLIENT_BOOKING_CONFIRMED = "client_booking_confirmed"

    # ==========================================
    # ESTADOS DE CLIENTE - GESTIÓN DE CITAS
    # ==========================================

    # Ver y gestionar citas
    CLIENT_VIEW_APPOINTMENTS = "client_view_appointments"
    CLIENT_APPOINTMENT_DETAIL = "client_appointment_detail"
    
    # Cancelación de citas
    CLIENT_CANCEL_APPOINTMENT = "client_cancel_appointment"
    CLIENT_CANCEL_REASON = "client_cancel_reason"
    CLIENT_CANCEL_SUCCESS = "client_cancel_success"

    # Reprogramación de citas
    CLIENT_RESCHEDULE_APPOINTMENT = "client_reschedule_appointment"
    CLIENT_RESCHEDULE_SELECT_DATE = "client_reschedule_select_date"
    CLIENT_RESCHEDULE_SELECT_TIME = "client_reschedule_select_time"
    CLIENT_RESCHEDULE_CONFIRM = "client_reschedule_confirm"

    AWAITING_REMINDER_RESPONSE = "awaiting_reminder_response"

    # CANCELACIÓN DE CITAS
    CLIENT_CONFIRM_CANCEL = "client_confirm_cancel"    # Confirmar cancelación
    CLIENT_SELECT_CANCEL = "client_select_cancel"       # Seleccionar cuál turno cancelar


# ==========================================
# SESSION DATA CLASS
# ==========================================

class SessionData:
    """
    Datos de sesión del usuario.
    
    Maneja estado de conversación, rol, y datos temporales.
    Se persiste en memoria durante la conversación.
    """

    def __init__(self, phone_number: str):
        """
        Inicializar sesión del usuario.
        
        Args:
            phone_number: Número de teléfono del usuario (ID único)
        """
        self.phone_number = phone_number
        self.current_state = ConversationState.START
        self.role = UserRole.UNKNOWN
        self.temp_data = {}
        self.conversation_history = []
        self.last_activity = datetime.now()  # Para control de expiración
        self._on_change = None  # Callback para persistencia automática en cada transición

    @property
    def state(self):
        """Alias para current_state."""
        return self.current_state

    def transition_to(self, new_state: ConversationState):
        """
        Transicionar a un nuevo estado.
        
        Args:
            new_state: Nuevo estado de conversación
        """
        print(f"[SESSION] {self.phone_number}: {self.current_state.value} -> {new_state.value}")
        self.current_state = new_state
        if self._on_change:
            try:
                self._on_change(self)
            except Exception as e:
                print(f"[SESSION] ⚠️ Error en auto-save: {e}")

    def set_role(self, role: UserRole):
        """
        Establecer rol del usuario.
        
        Args:
            role: Rol del usuario (PROFESSIONAL o CLIENT)
        """
        print(f"[SESSION] {self.phone_number}: Rol establecido como {role.value}")
        self.role = role

    def set_temp(self, key: str, value):
        """
        Guardar dato temporal en la sesión.
        
        Args:
            key: Clave del dato
            value: Valor del dato
        """
        self.temp_data[key] = value

    def get_temp(self, key: str, default=None):
        """
        Obtener dato temporal de la sesión.
        
        Args:
            key: Clave del dato
            default: Valor por defecto si no existe
            
        Returns:
            Valor del dato o default
        """
        return self.temp_data.get(key, default)

    def clear_temp(self):
        """Limpiar todos los datos temporales."""
        self.temp_data = {}

    def touch(self):
        """
        Actualiza el timestamp de última actividad.
        Llamar en cada mensaje recibido para evitar expiración prematura.
        """
        self.last_activity = datetime.now()

    def reset(self):
        """
        Resetear sesión completamente.
        
        Limpia estado, rol y datos temporales.
        Útil para comando "hola" o reinicio.
        """
        print(f"[SESSION] {self.phone_number}: Reset completo")
        self.current_state = ConversationState.START
        self.role = UserRole.UNKNOWN
        self.temp_data = {}
        self.last_activity = datetime.now()


# ==========================================
# SESSION MANAGER
# ==========================================

import os
import logging
 
logger = logging.getLogger(__name__)
 
 
class SessionManager:
    """
    Gestor global de sesiones con backend intercambiable.
 
    Al inicializar detecta si Redis está disponible:
    - Si REDIS_URL está configurada y Redis responde → RedisSessionBackend
    - Si no → MemorySessionBackend (fallback silencioso)
 
    La interfaz pública es idéntica a la versión anterior.
    Todo el código que usa session_manager funciona sin cambios.
    """
 
    def __init__(self):
        """
        Inicializa el backend elegido según disponibilidad de Redis.
        """
        self._backend = self._init_backend()
 
    def _init_backend(self):
        """
        Detecta Redis y elige el backend apropiado.
 
        Orden de prioridad:
        1. REDIS_URL en variables de entorno → intentar Redis
        2. Si falla o no está configurado → MemorySessionBackend
        """
        from src.core.session_backends import (
            RedisSessionBackend,
            MemorySessionBackend,
        )
 
        redis_url = os.getenv('REDIS_URL', '').strip()
 
        if not redis_url:
            logger.info(
                "[SESSION] REDIS_URL no configurada → usando memoria"
            )
            return MemorySessionBackend()
 
        try:
            backend = RedisSessionBackend(redis_url)
            logger.info("[SESSION] ✅ Backend: Redis")
            return backend
        except ImportError:
            logger.warning(
                "[SESSION] ⚠️  redis-py no instalado → usando memoria. "
                "Instalar con: pip install redis"
            )
        except Exception as e:
            logger.warning(
                f"[SESSION] ⚠️  Redis no disponible ({e}) → usando memoria"
            )
 
        return MemorySessionBackend()
 
    # =========================================================================
    # INTERFAZ PÚBLICA — igual que antes
    # =========================================================================
 
    def get_session(self, phone_number: str) -> 'SessionData':
        """
        Obtiene la sesión del usuario. La crea si no existe.
        Si está en Redis, renueva el TTL automáticamente.
 
        Args:
            phone_number: Número de teléfono del usuario
 
        Returns:
            SessionData del usuario
        """
        session = self._backend.get(phone_number)
 
        if session is None:
            # Nueva sesión — importar aquí para evitar circular import
            from src.core.states import SessionData
            session = SessionData(phone_number)
            self._backend.save(session)
            print(f"[SESSION] Nueva sesión creada para: {phone_number}")

        # Registrar callback — transition_to() guardará en Redis automáticamente
        session._on_change = self._backend.save
        return session
 
    def save_session(self, session: 'SessionData'):
        """
        Persiste el estado actual de la sesión.
 
        Debe llamarse después de cualquier cambio en la sesión
        cuando el backend es Redis (en memoria se guarda por referencia).
 
        En la práctica se llama en bot_controller.py al final de
        process_message() para garantizar consistencia.
        """
        self._backend.save(session)
 
    def clear_session(self, phone_number: str):
        """
        Elimina la sesión del usuario.
 
        Args:
            phone_number: Número de teléfono del usuario
        """
        self._backend.delete(phone_number)
        print(f"[SESSION] Sesión eliminada: {phone_number}")
 
    def get_stats(self) -> dict:
        """
        Retorna estadísticas del session manager.
        Útil para monitoreo.
        """
        from src.core.session_backends import (
            RedisSessionBackend, MemorySessionBackend
        )
        backend_type = (
            'redis'  if isinstance(self._backend, RedisSessionBackend)
            else 'memory'
        )
        return {
            'backend':          backend_type,
            'active_sessions':  self._backend.count(),
        }

# ==========================================
# INSTANCIA GLOBAL
# ==========================================
session_manager = SessionManager()