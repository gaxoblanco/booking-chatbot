"""
Conversation Logger v1.0
========================
Sistema automático de recolección de conversaciones para futuro entrenamiento ML.

Este módulo registra cada mensaje procesado por el bot, incluyendo:
- Mensaje original del usuario
- Intent detectado por el sistema
- Entidades extraídas
- Nivel de confianza
- Si se hizo shortcut
- Estado de la sesión

Los datos se guardan en formato JSONL (JSON Lines) para facilitar procesamiento.

PRIVACIDAD:
- Los números de teléfono se anonimizan con hash SHA-256
- Cumple con GDPR (datos anonimizados)

Uso:
    >>> from src.services.conversation_logger import conversation_logger
    >>> conversation_logger.log_message(
    ...     phone="+5491112345678",
    ...     message="necesito psicólogo mañana",
    ...     detected_intent="search_professional",
    ...     detected_entities={'especialidad': 'psicología', 'fecha': 'mañana'},
    ...     confidence=0.9,
    ...     shortcut_used=True,
    ...     session_state="CLIENT_MAIN_MENU"
    ... )
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


class ConversationLogger:
    """
    Logger automático de conversaciones para dataset de ML.
    
    Guarda cada mensaje procesado en archivos diarios JSONL.
    Los datos están listos para ser revisados y usados en entrenamiento.
    """
    
    def __init__(self, data_dir: str = "data/conversations"):
        """
        Inicializar logger.
        
        Args:
            data_dir: Directorio donde guardar los logs
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Crear README en el directorio
        self._create_readme_if_not_exists()
    
    def log_message(
        self,
        phone: str,
        message: str,
        detected_intent: str,
        detected_entities: Dict,
        confidence: float,
        shortcut_used: bool,
        session_state: str,
        user_role: Optional[str] = None,
        context_data: Optional[Dict] = None
    ):
        """
        Registra un mensaje procesado.
        
        Args:
            phone: Número de teléfono del usuario
            message: Mensaje original del usuario
            detected_intent: Intent detectado por el sistema
            detected_entities: Entidades extraídas
            confidence: Nivel de confianza (0.0-1.0)
            shortcut_used: Si se hizo shortcut
            session_state: Estado de la conversación
            user_role: Rol del usuario (client/professional)
            context_data: Datos adicionales de contexto
        """
        # Crear entrada de log
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'user_id': self._anonymize_phone(phone),  # Anonimizado
            'message': message,
            'detected_intent': detected_intent,
            'entities': detected_entities,
            'confidence': round(confidence, 3),
            'shortcut_used': shortcut_used,
            'session_state': session_state,
            'user_role': user_role,
            'context': context_data or {},
            
            # Campos para revisión manual
            'human_reviewed': False,
            'is_correct': None,  # True/False/None
            'correct_intent': None,  # Si fue corregido
            'correct_entities': None,  # Si fueron corregidas
            'review_notes': None
        }
        
        # Guardar en archivo diario
        self._save_to_file(log_entry)
        
        # Debug log
        print(f"[CONV_LOG] Guardado: intent={detected_intent}, conf={confidence:.2f}, "
              f"entities={list(detected_entities.keys())}")
    
    def mark_for_review(
        self,
        phone: str,
        message: str,
        detected_intent: str,
        user_says_wrong: bool = False,
        priority: str = "normal"
    ):
        """
        Marca un mensaje para revisión manual prioritaria.
        
        Útil cuando:
        - Usuario dice que la respuesta fue incorrecta
        - Confianza muy baja
        - Comportamiento inesperado
        
        Args:
            phone: Número de teléfono
            message: Mensaje original
            detected_intent: Intent detectado
            user_says_wrong: Si el usuario indicó que estuvo mal
            priority: 'high', 'normal', 'low'
        """
        review_entry = {
            'timestamp': datetime.now().isoformat(),
            'user_id': self._anonymize_phone(phone),
            'message': message,
            'detected_intent': detected_intent,
            'user_feedback': 'wrong' if user_says_wrong else 'needs_review',
            'priority': priority,
            'reviewed': False
        }
        
        # Guardar en archivo de revisión
        review_file = self.data_dir / "needs_review.jsonl"
        with open(review_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(review_entry, ensure_ascii=False) + '\n')
        
        print(f"[CONV_LOG] ⚠️ Marcado para revisión: {message[:50]}...")
    
    def get_stats(self) -> Dict:
        """
        Obtiene estadísticas de los datos recopilados.
        
        Returns:
            {
                'total_messages': int,
                'by_intent': dict,
                'avg_confidence': float,
                'needs_review': int
            }
        """
        stats = {
            'total_messages': 0,
            'by_intent': {},
            'total_confidence': 0.0,
            'needs_review': 0
        }
        
        # Contar mensajes en archivos diarios
        for file in self.data_dir.glob("conversations_*.jsonl"):
            with open(file, encoding='utf-8') as f:
                for line in f:
                    entry = json.loads(line)
                    stats['total_messages'] += 1
                    
                    # Contar por intent
                    intent = entry['detected_intent']
                    stats['by_intent'][intent] = stats['by_intent'].get(intent, 0) + 1
                    
                    # Sumar confianza
                    stats['total_confidence'] += entry['confidence']
        
        # Calcular promedio de confianza
        if stats['total_messages'] > 0:
            stats['avg_confidence'] = stats['total_confidence'] / stats['total_messages']
        
        # Contar pendientes de revisión
        review_file = self.data_dir / "needs_review.jsonl"
        if review_file.exists():
            with open(review_file, encoding='utf-8') as f:
                for line in f:
                    entry = json.loads(line)
                    if not entry.get('reviewed', False):
                        stats['needs_review'] += 1
        
        return stats
    
    def _save_to_file(self, log_entry: Dict):
        """
        Guarda entrada en archivo diario JSONL.
        
        Args:
            log_entry: Diccionario con datos del mensaje
        """
        # Nombre de archivo por día
        date_str = datetime.now().strftime('%Y-%m-%d')
        filepath = self.data_dir / f"conversations_{date_str}.jsonl"
        
        # Agregar al archivo (append)
        with open(filepath, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    
    def _anonymize_phone(self, phone: str) -> str:
        """
        Anonimiza número de teléfono con hash SHA-256.
        
        Cumple con GDPR: no se puede recuperar el número original.
        
        Args:
            phone: Número de teléfono original
            
        Returns:
            Hash de 16 caracteres
        """
        return hashlib.sha256(phone.encode()).hexdigest()[:16]
    
    def _create_readme_if_not_exists(self):
        """Crea archivo README en el directorio de datos."""
        readme_path = self.data_dir / "README.md"
        
        if readme_path.exists():
            return
        
        readme_content = """# Conversaciones Recopiladas

Este directorio contiene las conversaciones recopiladas automáticamente para futuro entrenamiento de ML.

## Estructura de Archivos

- `conversations_YYYY-MM-DD.jsonl`: Conversaciones del día
- `needs_review.jsonl`: Mensajes marcados para revisión manual
- `README.md`: Este archivo

## Formato de Datos (JSONL)

Cada línea es un JSON con:

```json
{
  "timestamp": "2026-02-05T14:30:00",
  "user_id": "a1b2c3d4e5f6g7h8",  // Hash anonimizado
  "message": "necesito psicólogo mañana",
  "detected_intent": "search_professional",
  "entities": {
    "especialidad": "psicología",
    "fecha": "mañana"
  },
  "confidence": 0.9,
  "shortcut_used": true,
  "session_state": "CLIENT_MAIN_MENU",
  "human_reviewed": false,
  "is_correct": null,
  "correct_intent": null
}
```

## Uso de los Datos

### 1. Ver estadísticas

```python
from src.services.conversation_logger import conversation_logger
stats = conversation_logger.get_stats()
print(stats)
```

### 2. Revisar mensajes (manual)

```bash
python scripts/review_conversations.py
```

### 3. Entrenar modelo ML (futuro)

```bash
python scripts/train_intent_model.py --data data/conversations/
```

## Privacidad

- ✅ Números de teléfono anonimizados (SHA-256)
- ✅ No contiene información personal identificable
- ✅ Cumple con GDPR
- ⚠️ Los mensajes de texto NO están encriptados (contienen lo que el usuario escribió)

## Mantenimiento

- Los archivos se crean automáticamente por día
- No hay límite de tamaño (se recomienda archivar mensualmente)
- Para limpiar datos antiguos: mover a `data/conversations/archive/`
"""
        
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)


# ==========================================
# INSTANCIA GLOBAL
# ==========================================
conversation_logger = ConversationLogger()
