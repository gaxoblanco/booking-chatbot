"""
ML Intent Detector - spaCy
===========================
Detector de intenciones basado en modelo ML entrenado con spaCy.

Compatible con IntentDetector de reglas (misma interfaz).

Uso:
    from src.ml.ml_intent_detector import ml_intent_detector
    
    result = ml_intent_detector.detect("necesito psicólogo mañana")
    print(result['intent'])  # Intent.SEARCH_PROFESSIONAL
    print(result['confidence'])  # 0.95
"""

import spacy
from pathlib import Path
from typing import Dict, Optional
import sys

# Importar Intent enum del sistema de reglas
try:
    from src.services.intent_detector import Intent
except ImportError:
    # Fallback si se ejecuta desde otro directorio
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from src.services.intent_detector import Intent


class MLIntentDetector:
    """
    Detector de intenciones usando modelo ML (spaCy).
    
    Responsabilidades:
    - Detectar INTENT con alta precisión
    - Retornar confianza probabilística
    - NO extrae entidades (para eso usar reglas)
    
    Compatible con IntentDetector de reglas (misma interfaz).
    """
    
    def __init__(self, model_path: str = "scripts/ml/models/intent_classifier"):
        """
        Inicializar detector ML.
        
        Args:
            model_path: Ruta relativa o absoluta al modelo entrenado
        """
        self.model_path = model_path
        self.nlp = None
        self.is_loaded = False
        
        # Mapeo de labels del modelo a Intent enum
        self.intent_map = {
            'search_professional': Intent.SEARCH_PROFESSIONAL,
            'view_my_appointments': Intent.VIEW_MY_APPOINTMENTS,
            'view_tomorrow': Intent.VIEW_TOMORROW,
            'cancel_appointment': Intent.CANCEL_APPOINTMENT,
            'info_center': Intent.INFO_CENTER,
            'greeting': Intent.GREETING,
            'unknown': Intent.UNKNOWN,
        }
        
        # Intentar cargar modelo al inicializar
        self._load_model()
    
    def _load_model(self):
        """Carga el modelo entrenado."""
        try:
            # Buscar modelo en diferentes ubicaciones posibles
            possible_paths = [
                self.model_path,  # Ruta original
                Path(__file__).parent.parent.parent / self.model_path,  # Relativa a src/
                Path.cwd() / self.model_path,  # Relativa a working directory
            ]
            
            model_loaded = False
            for path in possible_paths:
                if Path(path).exists():
                    print(f"[ML] Cargando modelo desde: {path}")
                    self.nlp = spacy.load(path)
                    self.is_loaded = True
                    model_loaded = True
                    print(f"[ML] ✅ Modelo cargado correctamente")
                    break
            
            if not model_loaded:
                print(f"[ML] ⚠️  Modelo no encontrado en ninguna ubicación")
                print(f"[ML]    Buscado en: {[str(p) for p in possible_paths]}")
                print(f"[ML]    ML Intent Detector deshabilitado")
                self.is_loaded = False
                
        except Exception as e:
            print(f"[ML] ❌ Error cargando modelo: {e}")
            print(f"[ML]    ML Intent Detector deshabilitado")
            self.is_loaded = False
    
    def detect(self, message: str, context: Optional[Dict] = None) -> Dict:
        """
        Detecta intención usando ML.
        
        Args:
            message: Mensaje del usuario
            context: Contexto opcional (compatible con reglas, pero no usado)
            
        Returns:
            {
                'intent': Intent,
                'confidence': float (0.0-1.0),
                'entities': dict,  # Siempre vacío (usar reglas para entidades)
                'can_shortcut': bool,  # Siempre False (calcular con reglas)
                'missing_entities': list,  # Siempre vacío
                'ml_scores': dict  # Scores de todos los intents (para debugging)
            }
            
        Example:
            >>> result = ml_intent_detector.detect("necesito psicólogo mañana")
            >>> print(result['intent'])
            Intent.SEARCH_PROFESSIONAL
            >>> print(f"{result['confidence']:.2f}")
            0.95
        """
        # Si modelo no está cargado, retornar unknown
        if not self.is_loaded or self.nlp is None:
            return {
                'intent': Intent.UNKNOWN,
                'confidence': 0.0,
                'entities': {},
                'can_shortcut': False,
                'missing_entities': [],
                'ml_scores': {},
                'error': 'Model not loaded'
            }
        
        try:
            # Predecir con modelo spaCy
            doc = self.nlp(message)
            
            # Obtener intent con mayor score
            predicted_label = max(doc.cats.items(), key=lambda x: x[1])[0]
            confidence = doc.cats[predicted_label]
            
            # Convertir label a Intent enum
            intent = self.intent_map.get(predicted_label, Intent.UNKNOWN)
            
            # Resultado
            return {
                'intent': intent,
                'confidence': confidence,
                'entities': {},  # ML no extrae entidades (usar reglas)
                'can_shortcut': False,  # Calcular con reglas
                'missing_entities': [],
                'ml_scores': dict(doc.cats)  # Todos los scores para debugging
            }
            
        except Exception as e:
            print(f"[ML] ❌ Error en predicción: {e}")
            return {
                'intent': Intent.UNKNOWN,
                'confidence': 0.0,
                'entities': {},
                'can_shortcut': False,
                'missing_entities': [],
                'ml_scores': {},
                'error': str(e)
            }
    
    def get_top_predictions(self, message: str, top_k: int = 3) -> list:
        """
        Obtiene las top K predicciones.
        
        Útil para debugging o mostrar alternativas.
        
        Args:
            message: Mensaje del usuario
            top_k: Número de predicciones a retornar
            
        Returns:
            Lista de tuplas (intent, confidence) ordenadas por confianza
            
        Example:
            >>> predictions = ml_intent_detector.get_top_predictions("hola", top_k=3)
            >>> for intent, conf in predictions:
            ...     print(f"{intent.value}: {conf:.2f}")
            greeting: 0.98
            search_professional: 0.01
            unknown: 0.01
        """
        if not self.is_loaded or self.nlp is None:
            return []
        
        try:
            doc = self.nlp(message)
            
            # Ordenar por score descendente
            sorted_cats = sorted(doc.cats.items(), key=lambda x: x[1], reverse=True)
            
            # Convertir a Intent enum y retornar top K
            results = []
            for label, score in sorted_cats[:top_k]:
                intent = self.intent_map.get(label, Intent.UNKNOWN)
                results.append((intent, score))
            
            return results
            
        except Exception as e:
            print(f"[ML] ❌ Error obteniendo predicciones: {e}")
            return []
    
    def is_available(self) -> bool:
        """
        Verifica si el detector ML está disponible.
        
        Returns:
            True si el modelo está cargado y listo
        """
        return self.is_loaded and self.nlp is not None


# ==========================================
# INSTANCIA GLOBAL
# ==========================================
ml_intent_detector = MLIntentDetector()


# ==========================================
# TEST (solo si se ejecuta directamente)
# ==========================================
if __name__ == "__main__":
    print("="*60)
    print("🧪 TEST - ML Intent Detector")
    print("="*60)
    
    if not ml_intent_detector.is_available():
        print("\n❌ Modelo no disponible")
        print("   Entrena el modelo primero con:")
        print("   python scripts/ml/train_spacy_model.py")
        sys.exit(1)
    
    # Test messages
    test_messages = [
        "necesito psicólogo mañana",
        "nesesito psicologo mañana",  # Con typos
        "ver mis turnos",
        "cancelar turno",
        "hola",
        "información del centro",
        "disponibles mañana",
        "asdfgh",  # Gibberish
    ]
    
    print("\n📊 Probando detector ML:\n")
    
    for msg in test_messages:
        result = ml_intent_detector.detect(msg)
        
        print(f"Mensaje: '{msg}'")
        print(f"  Intent: {result['intent'].value}")
        print(f"  Confianza: {result['confidence']:.2%}")
        
        # Mostrar top 3 predicciones
        top_3 = ml_intent_detector.get_top_predictions(msg, top_k=3)
        print(f"  Top 3:")
        for intent, conf in top_3:
            bar = "█" * int(conf * 20)
            print(f"    {intent.value:25s}: {conf:.3f} {bar}")
        print()
    
    print("="*60)
    print("✅ Test completado")
