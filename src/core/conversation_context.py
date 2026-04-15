"""
Conversation Context Manager
=============================
Maneja el contexto acumulativo de la conversación.
Permite combinar entidades de múltiples turnos.

Compatible con migración a ML - el modelo puede consultar
el contexto completo para mejores predicciones.

Ejemplo de uso:
    >>> from src.core.conversation_context import context_manager
    >>> context = context_manager.get_context("+5491112345678")
    >>> context.update_entities({'especialidad': 'psicología'})
    >>> context.update_entities({'fecha': 'mañana'})
    >>> context.get_entities()
    {'especialidad': 'psicología', 'fecha': 'mañana'}
"""

from typing import Dict, List, Optional
from datetime import datetime
from src.core.logger import _sanitize

class ConversationContext:
    """
    Contexto acumulativo de una conversación.
    
    Permite al modelo ML (futuro) o al NLU de reglas (actual)
    tomar decisiones basadas en toda la conversación, no solo
    el último mensaje.
    """
    
    def __init__(self, phone_number: str):
        """
        Inicializar contexto.
        
        Args:
            phone_number: Número de teléfono del usuario
        """
        self.phone_number = phone_number
        self.accumulated_entities = {}  # Entidades acumuladas
        self.conversation_history = []  # Historial de mensajes
        self.current_intent = None      # Intent activo
        self.last_search_filters = {}   # Última búsqueda
        
    def add_message(self, message: str, intent: str, entities: Dict):
        """
        Agregar mensaje al historial.
        
        Args:
            message: Texto del usuario
            intent: Intent detectado
            entities: Entidades extraídas
        """
        self.conversation_history.append({
            'timestamp': datetime.now(),
            'message': message,
            'intent': intent,
            'entities': entities
        })
        
        # Limitar historial a últimos 10 mensajes
        if len(self.conversation_history) > 10:
            self.conversation_history.pop(0)
    
    def update_entities(self, new_entities: Dict, merge: bool = True):
        """
        Actualizar entidades acumuladas.
        
        Args:
            new_entities: Nuevas entidades detectadas
            merge: Si True, combina con las existentes. Si False, reemplaza.
        """
        if merge:
            # Combinar entidades (las nuevas sobrescriben las viejas)
            self.accumulated_entities.update(new_entities)
            print(f"[CONTEXT] Entidades acumuladas: {self.accumulated_entities}")
        else:
            # Reemplazar completamente
            self.accumulated_entities = new_entities.copy()
            print(f"[CONTEXT] Entidades reemplazadas: {self.accumulated_entities}")
    
    def get_entities(self) -> Dict:
        """
        Obtener todas las entidades acumuladas.
        
        Returns:
            Copia del diccionario de entidades
        """
        return self.accumulated_entities.copy()
    
    def has_entity(self, entity_name: str) -> bool:
        """
        Verificar si existe una entidad.
        
        Args:
            entity_name: Nombre de la entidad
            
        Returns:
            True si existe y tiene valor
        """
        return entity_name in self.accumulated_entities and self.accumulated_entities[entity_name]
    
    def get_entity(self, entity_name: str, default=None):
        """
        Obtener valor de una entidad específica.
        
        Args:
            entity_name: Nombre de la entidad
            default: Valor por defecto si no existe
            
        Returns:
            Valor de la entidad o default
        """
        return self.accumulated_entities.get(entity_name, default)
    
    def clear_entities(self):
        """Limpiar entidades acumuladas."""
        self.accumulated_entities = {}
        print(f"[CONTEXT] Entidades limpiadas")
    
    def set_intent(self, intent: str):
        """
        Establecer intent actual.
        
        Args:
            intent: Intent a establecer
        """
        self.current_intent = intent
    
    def get_intent(self) -> Optional[str]:
        """
        Obtener intent actual.
        
        Returns:
            Intent actual o None
        """
        return self.current_intent
    
    def save_search_filters(self, filters: Dict):
        """
        Guardar filtros de última búsqueda.
        
        Args:
            filters: Filtros utilizados
        """
        self.last_search_filters = filters.copy()
    
    def get_search_filters(self) -> Dict:
        """
        Obtener filtros de última búsqueda.
        
        Returns:
            Copia de los filtros
        """
        return self.last_search_filters.copy()
    
    def get_history_text(self, last_n: int = 5) -> str:
        """
        Obtener historial como texto para contexto de ML.
        
        Útil para modelos como GPT que necesitan el historial completo.
        
        Args:
            last_n: Número de mensajes a incluir
            
        Returns:
            Texto formateado del historial
        """
        history = self.conversation_history[-last_n:]
        lines = []
        for h in history:
            lines.append(f"User: {h['message']}")
            lines.append(f"Intent: {h['intent']}")
            if h['entities']:
                lines.append(f"Entities: {h['entities']}")
        return "\n".join(lines)
    
    def get_conversation_summary(self) -> str:
        """
        Obtener resumen de la conversación actual.
        
        Útil para debugging y analytics.
        
        Returns:
            Resumen formateado
        """
        summary = f"Conversación: {self.phone_number}\n"
        summary += f"Intent actual: {self.current_intent}\n"
        summary += f"Entidades acumuladas: {self.accumulated_entities}\n"
        summary += f"Mensajes en historial: {len(self.conversation_history)}\n"
        return summary
    
    def reset(self):
        """Resetear contexto completamente."""
        self.accumulated_entities = {}
        self.conversation_history = []
        self.current_intent = None
        self.last_search_filters = {}
        print(f"[CONTEXT] Contexto reseteado para {self.phone_number}")


class ContextManager:
    """
    Gestor global de contextos por usuario.
    
    Mantiene un contexto separado para cada usuario (por teléfono).
    """
    
    def __init__(self):
        """Inicializar gestor."""
        self.contexts = {}
    
    def get_context(self, phone_number: str) -> ConversationContext:
        """
        Obtener o crear contexto para un usuario.
        
        Args:
            phone_number: Número de teléfono del usuario
            
        Returns:
            Contexto del usuario
        """
        if phone_number not in self.contexts:
            print(f"[CONTEXT] Nuevo contexto creado para {_sanitize(phone_number)}")
            self.contexts[phone_number] = ConversationContext(phone_number)
        return self.contexts[phone_number]
    
    def clear_context(self, phone_number: str):
        """
        Limpiar contexto de un usuario.
        
        Args:
            phone_number: Número de teléfono del usuario
        """
        if phone_number in self.contexts:
            del self.contexts[phone_number]
            print(f"[CONTEXT] Contexto eliminado para {_sanitize(phone_number)}")
    
    def reset_context(self, phone_number: str):
        """
        Resetear contexto sin eliminarlo.
        
        Args:
            phone_number: Número de teléfono del usuario
        """
        if phone_number in self.contexts:
            self.contexts[phone_number].reset()


# ==========================================
# INSTANCIA GLOBAL
# ==========================================
context_manager = ContextManager()