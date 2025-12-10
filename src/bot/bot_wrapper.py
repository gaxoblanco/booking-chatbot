"""
Bot Wrapper
===========
Wrapper de retrocompatibilidad para mantener la interfaz pública existente.

TODO el código real está ahora en src/bot/ (arquitectura modular):
- src/bot/bot_controller.py → Router principal + integración
- src/bot/client_handler.py → Flujo del cliente
- src/bot/professional_handler.py → Flujo del profesional

Este archivo se mantiene SOLO para:
1. No romper imports existentes en whatsapp_handler.py
2. Mantener la misma interfaz pública (bot.process_message)
3. Facilitar la migración gradual

Uso:
    from bot import bot
    response = bot.process_message(phone_number, message)
"""

from src.bot.bot_controller import bot_controller


class Bot:
    """
    Wrapper class para retrocompatibilidad.
    
    Delega todas las llamadas al bot_controller real.
    Esta clase es simplemente un puente para mantener
    la interfaz pública sin cambios.
    """
    
    def __init__(self):
        """
        Inicializar wrapper.
        
        El bot real (bot_controller) se importa como módulo
        y ya está instanciado.
        """
        self.controller = bot_controller
        self.messages = bot_controller.messages
    
    def process_message(self, phone_number: str, message: str) -> str:
        """
        Procesa mensaje entrante y retorna respuesta.
        
        Esta es la interfaz pública principal del bot.
        Delega directamente a bot_controller.
        
        Args:
            phone_number: Número de WhatsApp del usuario
            message: Mensaje de texto del usuario
            
        Returns:
            Respuesta del bot (string)
        """
        return self.controller.process_message(phone_number, message)
    
    def handle_prof_certificate_uploaded(self, session):
        """
        Maneja evento de certificado subido.
        
        Llamado desde whatsapp_handler.py cuando un profesional
        sube su certificado.
        
        Args:
            session: SessionData del profesional
            
        Returns:
            Mensaje de confirmación con menú
        """
        return self.controller.professional_handler.handle_prof_certificate_uploaded(session)


# ==========================================
# INSTANCIA GLOBAL
# ==========================================
# Se mantiene para retrocompatibilidad con:
# - from bot import bot
# - bot.process_message(phone, message)

bot = Bot()
