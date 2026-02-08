"""
Hybrid Intent Detector
======================
Combina ML (spaCy) + Reglas para máxima precisión.

Estrategia:
- ML detecta INTENT (robusto a typos, variaciones)
- Reglas extraen ENTIDADES (precisas, específicas del dominio)
- Fallback inteligente basado en confianza

Uso:
    from src.integrations.ml.hybrid_intent_detector import hybrid_intent_detector
    
    result = hybrid_intent_detector.detect("nesesito psicologo mañana")
    print(result['intent'])  # Intent.SEARCH_PROFESSIONAL (de ML)
    print(result['entities'])  # {'especialidad': 'psicología', 'fecha': 'mañana'} (de Reglas)
    print(result['source'])  # 'ml' o 'rules'
"""

from typing import Dict, Optional
import sys
from pathlib import Path

# Importar detectores
try:
    from src.services.intent_detector import intent_detector, Intent
    from services.ml_intent_detector import ml_intent_detector
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from src.services.intent_detector import intent_detector, Intent
    from services.ml_intent_detector import ml_intent_detector


class HybridIntentDetector:
    """
    Detector híbrido que combina ML + Reglas.
    
    Lógica de decisión:
    1. Ejecutar AMBOS detectores en paralelo
    2. Si ML confianza >= threshold → Usar intent de ML
    3. Si ML confianza < threshold → Usar intent de Reglas (fallback)
    4. SIEMPRE usar entidades de Reglas (más precisas)
    5. SIEMPRE usar can_shortcut de Reglas
    
    Ventajas:
    - Robustez de ML (typos, variaciones)
    - Precisión de Reglas (entidades, shortcuts)
    - Fallback automático
    - Auditable (sabes qué componente decidió)
    """
    
    def __init__(
        self,
        confidence_threshold: float = 0.7,
        enable_ml: bool = True,
        enable_logging: bool = True
    ):
        """
        Inicializar detector híbrido.
        
        Args:
            confidence_threshold: Umbral de confianza para usar ML (0.0-1.0)
                - 0.5: Agresivo (usa ML casi siempre)
                - 0.7: Balanceado (recomendado) ⭐
                - 0.9: Conservador (usa Reglas más seguido)
            enable_ml: Si False, solo usa Reglas (fallback total)
            enable_logging: Si True, imprime decisiones para debugging
        """
        self.confidence_threshold = confidence_threshold
        self.enable_ml = enable_ml and ml_intent_detector.is_available()
        self.enable_logging = enable_logging
        
        # Estadísticas (para análisis)
        self.stats = {
            'total_calls': 0,
            'ml_used': 0,
            'rules_used': 0,
            'ml_fallback': 0,  # Veces que ML falló y usamos reglas
        }
        
        if self.enable_logging:
            if self.enable_ml:
                print(f"[HYBRID] ✅ Modo híbrido activo (threshold={confidence_threshold})")
            else:
                print(f"[HYBRID] ⚠️  ML no disponible, usando solo Reglas")
    
    def detect(self, message: str, context: Optional[Dict] = None) -> Dict:
        """
        Detecta intención y entidades usando sistema híbrido.
        
        Args:
            message: Mensaje del usuario
            context: Contexto opcional (estado, historial, etc)
            
        Returns:
            {
                'intent': Intent,  # De ML o Reglas según threshold
                'confidence': float,  # Del detector usado
                'entities': dict,  # SIEMPRE de Reglas
                'can_shortcut': bool,  # SIEMPRE de Reglas
                'missing_entities': list,  # SIEMPRE de Reglas
                'source': str,  # 'ml', 'rules', o 'ml_fallback'
                'ml_confidence': float,  # Para análisis
                'rules_confidence': float,  # Para análisis
                'ml_available': bool,  # Si ML está disponible
            }
            
        Example:
            >>> result = hybrid_intent_detector.detect("nesesito psicologo mañana")
            >>> print(f"Intent: {result['intent'].value} (from {result['source']})")
            Intent: search_professional (from ml)
            >>> print(f"Entities: {result['entities']}")
            Entities: {'especialidad': 'psicología', 'fecha': 'mañana'}
        """
        self.stats['total_calls'] += 1
        
        # ==========================================
        # 1. DETECTAR CON REGLAS (SIEMPRE)
        # ==========================================
        rules_result = intent_detector.detect(message, context)
        
        # ==========================================
        # 2. DETECTAR CON ML (SI ESTÁ DISPONIBLE)
        # ==========================================
        ml_result = None
        if self.enable_ml:
            try:
                ml_result = ml_intent_detector.detect(message, context)
            except Exception as e:
                if self.enable_logging:
                    print(f"[HYBRID] ⚠️  ML falló: {e}, usando Reglas")
                ml_result = None
        
        # ==========================================
        # 3. DECIDIR QUÉ INTENT USAR
        # ==========================================
        
        # Caso 1: ML no disponible o falló → Usar Reglas
        if ml_result is None:
            final_intent = rules_result['intent']
            final_confidence = rules_result['confidence']
            source = 'rules'
            self.stats['rules_used'] += 1
            
            if self.enable_logging:
                print(f"[HYBRID] 📊 ML no disponible → Rules: {final_intent.value} ({final_confidence:.2f})")
        
        # Caso 2: ML con alta confianza → Usar ML
        elif ml_result['confidence'] >= self.confidence_threshold:
            final_intent = ml_result['intent']
            final_confidence = ml_result['confidence']
            source = 'ml'
            self.stats['ml_used'] += 1
            
            if self.enable_logging:
                print(f"[HYBRID] 🤖 ML ({ml_result['confidence']:.2f} >= {self.confidence_threshold}) → {final_intent.value}")
        
        # Caso 3: ML con baja confianza → Fallback a Reglas
        else:
            final_intent = rules_result['intent']
            final_confidence = rules_result['confidence']
            source = 'rules_fallback'
            self.stats['ml_fallback'] += 1
            
            if self.enable_logging:
                print(f"[HYBRID] 📉 ML baja confianza ({ml_result['confidence']:.2f} < {self.confidence_threshold})")
                print(f"[HYBRID] → Fallback Rules: {final_intent.value} ({final_confidence:.2f})")
        
        # ==========================================
        # 4. CONSTRUIR RESULTADO FINAL
        # ==========================================
        
        result = {
            # Intent decidido por lógica híbrida
            'intent': final_intent,
            'confidence': final_confidence,
            
            # Entidades y shortcuts SIEMPRE de Reglas
            'entities': rules_result['entities'],
            'can_shortcut': rules_result['can_shortcut'],
            'missing_entities': rules_result['missing_entities'],
            
            # Metadata para debugging y análisis
            'source': source,
            'ml_available': self.enable_ml,
            'ml_confidence': ml_result['confidence'] if ml_result else 0.0,
            'rules_confidence': rules_result['confidence'],
        }
        
        # Agregar scores de ML si están disponibles (para debugging)
        if ml_result and 'ml_scores' in ml_result:
            result['ml_scores'] = ml_result['ml_scores']
        
        return result
    
    def set_threshold(self, new_threshold: float):
        """
        Ajusta el threshold de confianza dinámicamente.
        
        Args:
            new_threshold: Nuevo umbral (0.0-1.0)
            
        Example:
            >>> hybrid_intent_detector.set_threshold(0.8)
            >>> # Ahora es más conservador (usa más reglas)
        """
        if not 0.0 <= new_threshold <= 1.0:
            raise ValueError("Threshold debe estar entre 0.0 y 1.0")
        
        old_threshold = self.confidence_threshold
        self.confidence_threshold = new_threshold
        
        if self.enable_logging:
            print(f"[HYBRID] 🔧 Threshold ajustado: {old_threshold:.2f} → {new_threshold:.2f}")
    
    def get_stats(self) -> Dict:
        """
        Obtiene estadísticas de uso.
        
        Útil para analizar qué detector se usa más.
        
        Returns:
            Diccionario con estadísticas
            
        Example:
            >>> stats = hybrid_intent_detector.get_stats()
            >>> print(f"ML usado: {stats['ml_percentage']:.1f}%")
        """
        total = self.stats['total_calls']
        
        if total == 0:
            return {
                **self.stats,
                'ml_percentage': 0.0,
                'rules_percentage': 0.0,
            }
        
        return {
            **self.stats,
            'ml_percentage': (self.stats['ml_used'] / total) * 100,
            'rules_percentage': (self.stats['rules_used'] / total) * 100,
            'fallback_percentage': (self.stats['ml_fallback'] / total) * 100,
        }
    
    def reset_stats(self):
        """Reinicia las estadísticas."""
        self.stats = {
            'total_calls': 0,
            'ml_used': 0,
            'rules_used': 0,
            'ml_fallback': 0,
        }
        if self.enable_logging:
            print(f"[HYBRID] 🔄 Estadísticas reiniciadas")
    
    def enable_ml_detector(self, enable: bool = True):
        """
        Habilita o deshabilita el detector ML.
        
        Útil para A/B testing o debugging.
        
        Args:
            enable: True para habilitar, False para deshabilitar
        """
        if enable and not ml_intent_detector.is_available():
            print(f"[HYBRID] ❌ No se puede habilitar ML: modelo no disponible")
            return
        
        self.enable_ml = enable
        status = "habilitado" if enable else "deshabilitado"
        
        if self.enable_logging:
            print(f"[HYBRID] 🔧 Detector ML {status}")


# ==========================================
# INSTANCIA GLOBAL
# ==========================================
hybrid_intent_detector = HybridIntentDetector(
    confidence_threshold=0.7,  # Balanceado (recomendado)
    enable_ml=True,
    enable_logging=True  # Cambiar a False en producción para menos logs
)


# ==========================================
# TEST (solo si se ejecuta directamente)
# ==========================================
if __name__ == "__main__":
    print("="*60)
    print("🧪 TEST - Hybrid Intent Detector")
    print("="*60)
    
    # Test messages con diferentes características
    test_cases = [
        ("necesito psicólogo mañana", "Normal"),
        ("nesesito psicologo mañana", "Con typos"),
        ("ver mis turnos", "Claro"),
        ("asdfgh", "Gibberish"),
        ("Buenos días. Quisiera solicitar un turno.", "Formal"),
        ("quiero un turnitito para mañanita", "Diminutivos"),
        ("busco psi pa mañ", "Abreviaturas"),
    ]
    
    print("\n📊 Probando detector híbrido:\n")
    
    for msg, description in test_cases:
        print(f"{'='*60}")
        print(f"Mensaje: '{msg}' ({description})")
        print(f"{'-'*60}")
        
        result = hybrid_intent_detector.detect(msg)
        
        print(f"✅ Intent Final: {result['intent'].value}")
        print(f"   Confianza: {result['confidence']:.2%}")
        print(f"   Source: {result['source']}")
        print(f"   Entidades: {result['entities']}")
        
        print(f"\n📊 Detalles:")
        print(f"   ML confianza: {result['ml_confidence']:.2%}")
        print(f"   Rules confianza: {result['rules_confidence']:.2%}")
        print()
    
    # Mostrar estadísticas
    print("="*60)
    print("📊 ESTADÍSTICAS DE USO")
    print("="*60)
    stats = hybrid_intent_detector.get_stats()
    print(f"Total llamadas: {stats['total_calls']}")
    print(f"ML usado: {stats['ml_used']} ({stats['ml_percentage']:.1f}%)")
    print(f"Rules usado: {stats['rules_used']} ({stats['rules_percentage']:.1f}%)")
    print(f"ML fallback: {stats['ml_fallback']} ({stats['fallback_percentage']:.1f}%)")
    print("="*60)
    print("✅ Test completado")
