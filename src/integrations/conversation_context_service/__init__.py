"""
Conversation Context Service
=============================
Ubicación: src/integrations/conversation_context_service/

Infiere el contexto de conversación entre sesiones usando eventos
persistidos en BD — sin guardar el texto de los mensajes.

Componentes:
    event_store.py      — lectura/escritura de conversation_events
    context_service.py  — inferencia de contexto

Uso rápido:
    from src.integrations.conversation_context_service import event_store
    from src.integrations.conversation_context_service import context_service
"""

from src.integrations.conversation_context_service.event_store import event_store
from src.integrations.conversation_context_service.context_service import context_service