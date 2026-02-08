"""
Cache Manager - Sistema de Cache para Disponibilidad
=====================================================
Cache centralizado con TTL configurable para consultas de Google Calendar.

Performance:
- Reduce consultas API repetidas
- TTL: 15 minutos (configurable)
- Thread-safe para consultas paralelas
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import threading

class CacheManager:
    """
    Gestor de cache thread-safe para slots de disponibilidad.
    
    Cache Key Format: f"{calendar_id}_{date_str}_{time_pref}"
    Example: "prof@gmail.com_2026-02-12_mañana"
    """
    
    def __init__(self, ttl_minutes: int = 15):
        """
        Inicializar cache manager.
        
        Args:
            ttl_minutes: Tiempo de vida del cache en minutos (default: 15)
        """
        self._cache: Dict[str, Dict] = {}
        self._lock = threading.Lock()
        self.ttl_minutes = ttl_minutes
        
        print(f"[CACHE] 🚀 Initialized with TTL={ttl_minutes}min")
    
    def _is_expired(self, cached_time: datetime) -> bool:
        """Verifica si el cache expiró."""
        age_seconds = (datetime.now() - cached_time).total_seconds()
        return age_seconds > (self.ttl_minutes * 60)
    
    def get(
        self,
        calendar_id: str,
        date_str: str,
        time_preference: Optional[str] = None
    ) -> Optional[List[Dict]]:
        """
        Obtiene slots desde cache si existe y no expiró.
        
        Args:
            calendar_id: Email del profesional
            date_str: Fecha YYYY-MM-DD
            time_preference: 'mañana'|'tarde'|'noche' o None
        
        Returns:
            Lista de slots o None si no hay cache válido
        """
        # Build cache key
        time_key = time_preference or "all"
        cache_key = f"{calendar_id}_{date_str}_{time_key}"
        
        with self._lock:
            if cache_key not in self._cache:
                print(f"[CACHE] ❌ MISS: {cache_key}")
                return None
            
            cached_data = self._cache[cache_key]
            cached_time = cached_data['timestamp']
            
            # Check if expired
            if self._is_expired(cached_time):
                age_minutes = int((datetime.now() - cached_time).total_seconds() / 60)
                print(f"[CACHE] ⏱️ EXPIRED: {cache_key} (age: {age_minutes}min)")
                del self._cache[cache_key]
                return None
            
            # Valid cache hit
            age_seconds = int((datetime.now() - cached_time).total_seconds())
            print(f"[CACHE] ✅ HIT: {cache_key} (age: {age_seconds}s)")
            return cached_data['slots']
    
    def set(
        self,
        calendar_id: str,
        date_str: str,
        slots: List[Dict],
        time_preference: Optional[str] = None
    ):
        """
        Guarda slots en cache.
        
        Args:
            calendar_id: Email del profesional
            date_str: Fecha YYYY-MM-DD
            slots: Lista de slots disponibles
            time_preference: 'mañana'|'tarde'|'noche' o None
        """
        time_key = time_preference or "all"
        cache_key = f"{calendar_id}_{date_str}_{time_key}"
        
        with self._lock:
            self._cache[cache_key] = {
                'timestamp': datetime.now(),
                'slots': slots
            }
            
            print(f"[CACHE] 💾 SET: {cache_key} ({len(slots)} slots)")
    
    def invalidate(self, calendar_id: str, date_str: str):
        """
        Invalida todo el cache para un profesional/fecha específico.
        
        Útil cuando se agenda una cita y queremos forzar refresh.
        
        Args:
            calendar_id: Email del profesional
            date_str: Fecha YYYY-MM-DD
        """
        with self._lock:
            # Find and delete all keys for this calendar_id and date
            keys_to_delete = [
                key for key in self._cache.keys()
                if key.startswith(f"{calendar_id}_{date_str}_")
            ]
            
            for key in keys_to_delete:
                del self._cache[key]
                print(f"[CACHE] 🗑️ INVALIDATED: {key}")
    
    def clear_all(self):
        """Limpia todo el cache."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            print(f"[CACHE] 🧹 CLEARED: {count} entries")
    
    def get_stats(self) -> Dict:
        """
        Obtiene estadísticas del cache.
        
        Returns:
            Dict con estadísticas: total, expired, valid
        """
        with self._lock:
            total = len(self._cache)
            expired = sum(
                1 for data in self._cache.values()
                if self._is_expired(data['timestamp'])
            )
            valid = total - expired
            
            return {
                'total_entries': total,
                'valid_entries': valid,
                'expired_entries': expired,
                'ttl_minutes': self.ttl_minutes
            }
    
    def cleanup_expired(self):
        """
        Limpia entradas expiradas del cache.
        
        Se puede llamar periódicamente para liberar memoria.
        """
        with self._lock:
            keys_to_delete = [
                key for key, data in self._cache.items()
                if self._is_expired(data['timestamp'])
            ]
            
            for key in keys_to_delete:
                del self._cache[key]
            
            if keys_to_delete:
                print(f"[CACHE] 🧹 Cleaned {len(keys_to_delete)} expired entries")


# ==========================================
# SINGLETON INSTANCE
# ==========================================
# Instancia global del cache manager
# TTL: 15 minutos (900 segundos)
cache_manager = CacheManager(ttl_minutes=15)


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def get_cached_slots(
    calendar_id: str,
    date_str: str,
    time_preference: Optional[str] = None
) -> Optional[List[Dict]]:
    """
    Wrapper simple para obtener slots desde cache.
    
    Returns:
        Lista de slots o None si no hay cache válido
    """
    return cache_manager.get(calendar_id, date_str, time_preference)


def cache_slots(
    calendar_id: str,
    date_str: str,
    slots: List[Dict],
    time_preference: Optional[str] = None
):
    """
    Wrapper simple para guardar slots en cache.
    """
    cache_manager.set(calendar_id, date_str, slots, time_preference)


def invalidate_cache(calendar_id: str, date_str: str):
    """
    Wrapper simple para invalidar cache de un profesional/fecha.
    """
    cache_manager.invalidate(calendar_id, date_str)
