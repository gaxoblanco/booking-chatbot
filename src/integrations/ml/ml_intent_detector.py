"""
ML Intent Detector - HTTP Client Version
=========================================
Detector de intenciones que usa el servicio ML centralizado vía HTTP.

Compatible 100% con la versión anterior (spaCy local).
Misma interfaz, mismo comportamiento, pero usa servicio remoto.

Uso:
    from src.integrations.ml.ml_intent_detector import ml_intent_detector
    
    result = ml_intent_detector.detect("necesito psicólogo mañana")
    print(result['intent'])  # Intent.SEARCH_PROFESSIONAL
    print(result['confidence'])  # 0.95
"""

import os
import sys
import requests
from pathlib import Path
from typing import Dict, Optional, List, Tuple

# Importar Intent enum del sistema de reglas
try:
    from src.services.intent_detector import Intent
except ImportError:
    # Fallback si se ejecuta desde otro directorio
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from src.services.intent_detector import Intent


class MLIntentDetector:
    """
    Detector de intenciones usando servicio ML remoto (HTTP).
    
    Responsabilidades:
    - Detectar INTENT con alta precisión
    - Retornar confianza probabilística
    - NO extrae entidades (para eso usar reglas)
    
    Compatible 100% con versión anterior (spaCy local).
    """
    
    def __init__(self, model_path: str = "scripts/ml/models/intent_classifier"):
        """
        Inicializar detector ML.
        
        Args:
            model_path: Ignorado (mantiene compatibilidad). Ahora usa servicio HTTP.
        """
        # Configuración del servicio HTTP
        self.ml_service_url = os.getenv('ML_SERVICE_URL', 'http://ml-service:8000')
        self.api_key = os.getenv('ML_API_KEY')
        
        # Timeout y retries
        self.timeout = int(os.getenv('ML_SERVICE_TIMEOUT', '5'))
        self.max_retries = int(os.getenv('ML_SERVICE_MAX_RETRIES', '2'))
        
        # Estado del servicio
        self.is_loaded = False
        
        # Mapeo de labels del modelo a Intent enum (mismo que antes)
        self.intent_map = {
            'search_professional': Intent.SEARCH_PROFESSIONAL,
            'view_my_appointments': Intent.VIEW_MY_APPOINTMENTS,
            'view_tomorrow': Intent.VIEW_TOMORROW,
            'cancel_appointment': Intent.CANCEL_APPOINTMENT,
            'info_center': Intent.INFO_CENTER,
            'greeting': Intent.GREETING,
            'unknown': Intent.UNKNOWN,
            'book_for_third_party': Intent.BOOK_FOR_THIRD_PARTY,
            'agenda_view_ready':    Intent.AGENDA_VIEW_READY,
            'agenda_view_overlaps': Intent.AGENDA_VIEW_OVERLAPS,
            'agenda_view_existing': Intent.AGENDA_VIEW_EXISTING,
            'agenda_view_errors':   Intent.AGENDA_VIEW_ERRORS,
            'agenda_confirm_upload': Intent.AGENDA_CONFIRM_UPLOAD,
            'agenda_cancel_upload': Intent.AGENDA_CANCEL_UPLOAD,
            # Grupo C — confirmación / negación genérica (flujo cliente)
            'confirm_action':        Intent.CONFIRM_ACTION,
            'deny_action':           Intent.DENY_ACTION,
        }
        
        # Advertencia si model_path fue especificado
        if model_path != "scripts/ml/models/intent_classifier":
            print(f"[ML] ⚠️  model_path='{model_path}' ignorado")
            print(f"[ML]    Ahora se usa ML service en: {self.ml_service_url}")
        
        # Validar configuración
        if not self.api_key:
            print("[ML] ❌ ML_API_KEY no configurada en variables de entorno")
            print("[ML]    ML Intent Detector deshabilitado")
            print("[ML]    Agregar ML_API_KEY a .env")
            self.is_loaded = False
        else:
            # Intentar conectar al servicio
            self._load_model()
    
    def _load_model(self):
        """
        Conecta con el servicio ML (equivalente a cargar modelo).
        
        Verifica que el servicio esté disponible y el modelo cargado.
        """
        try:
            print(f"[ML] Conectando a servicio ML: {self.ml_service_url}")
            
            # Health check del servicio
            response = requests.get(
                f"{self.ml_service_url}/health",
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status') == 'healthy' and data.get('model_loaded', False):
                    self.is_loaded = True
                    accuracy = data.get('model_accuracy', 0)
                    print(f"[ML] ✅ Servicio ML conectado correctamente")
                    print(f"[ML]    Accuracy: {accuracy:.1%}")
                    print(f"[ML]    Intenciones: {data.get('intents_count', 0)}")
                else:
                    print(f"[ML] ⚠️  Servicio responde pero modelo no cargado")
                    print(f"[ML]    Status: {data.get('status', 'unknown')}")
                    self.is_loaded = False
            else:
                print(f"[ML] ⚠️  Servicio ML no disponible (HTTP {response.status_code})")
                self.is_loaded = False
                
        except requests.exceptions.ConnectionError:
            print(f"[ML] ❌ No se puede conectar a {self.ml_service_url}")
            print(f"[ML]    Verifica que el servicio ml-service esté corriendo")
            print(f"[ML]    ML Intent Detector deshabilitado")
            self.is_loaded = False
            
        except Exception as e:
            print(f"[ML] ❌ Error conectando a servicio ML: {e}")
            print(f"[ML]    ML Intent Detector deshabilitado")
            self.is_loaded = False
    
    def detect(self, message: str, context: Optional[Dict] = None) -> Dict:
        """
        Detecta intención usando ML remoto.
        
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
                'ml_scores': dict  # Scores de todos los intents
            }
            
        Example:
            >>> result = ml_intent_detector.detect("necesito psicólogo mañana")
            >>> print(result['intent'])
            Intent.SEARCH_PROFESSIONAL
            >>> print(f"{result['confidence']:.2f}")
            0.95
        """
        # Si servicio no está disponible, retornar unknown
        if not self.is_loaded:
            return {
                'intent': Intent.UNKNOWN,
                'confidence': 0.0,
                'entities': {},
                'can_shortcut': False,
                'missing_entities': [],
                'ml_scores': {},
                'error': 'ML service not available'
            }
        
        # Intentar predicción con retries
        for attempt in range(self.max_retries + 1):
            try:
                # Preparar request
                headers = {
                    "X-API-Key": self.api_key,
                    "Content-Type": "application/json; charset=utf-8"
                }
                
                payload = {"message": message}
                
                # Llamar servicio ML
                response = requests.post(
                    f"{self.ml_service_url}/predict",
                    json=payload,
                    headers=headers,
                    timeout=self.timeout
                )
                
                # Verificar respuesta
                response.raise_for_status()
                
                # Parsear respuesta
                data = response.json()
                
                # Convertir intent string a enum
                predicted_label = data['intent']
                intent = self.intent_map.get(predicted_label, Intent.UNKNOWN)
                confidence = data['confidence']
                ml_scores = data.get('ml_scores', {})
                
                print(f"[ML_RAW] Label recibido del servicio: '{predicted_label}'")
                print(f"[ML_RAW] Intent map tiene esa key: {predicted_label in self.intent_map}")
                print(f"[ML_RAW] Intent map keys: {list(self.intent_map.keys())}")
                print(f"[ML_RAW] Intent resuelto: {intent}")
                
                # Retornar en formato compatible
                return {
                    'intent': intent,
                    'confidence': confidence,
                    'entities': {},  # ML no extrae entidades (usar reglas)
                    'can_shortcut': False,  # Calcular con reglas
                    'missing_entities': [],
                    'ml_scores': ml_scores  # Todos los scores para debugging
                }
                
            except requests.exceptions.Timeout:
                if attempt < self.max_retries:
                    print(f"[ML] ⚠️  Timeout (intento {attempt + 1}/{self.max_retries + 1})")
                    continue
                else:
                    print(f"[ML] ❌ Timeout definitivo del ML service")
                    return self._fallback_response('Timeout')
            
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 401:
                    print(f"[ML] ❌ API Key inválida")
                    return self._fallback_response('Invalid API Key')
                elif e.response.status_code == 503:
                    print(f"[ML] ⚠️  Servicio no disponible (503)")
                    if attempt < self.max_retries:
                        continue
                    return self._fallback_response('Service unavailable')
                else:
                    print(f"[ML] ❌ Error HTTP: {e}")
                    if attempt < self.max_retries:
                        continue
                    return self._fallback_response(f'HTTP {e.response.status_code}')
            
            except Exception as e:
                print(f"[ML] ❌ Error en predicción: {e}")
                if attempt < self.max_retries:
                    continue
                return self._fallback_response(str(e))
        
        # Si todos los intentos fallaron
        return self._fallback_response('All retries failed')
    
    def _fallback_response(self, error_msg: str) -> Dict:
        """
        Respuesta de fallback cuando falla la predicción.
        
        Args:
            error_msg: Mensaje de error
            
        Returns:
            Dict con intent UNKNOWN en formato compatible
        """
        return {
            'intent': Intent.UNKNOWN,
            'confidence': 0.0,
            'entities': {},
            'can_shortcut': False,
            'missing_entities': [],
            'ml_scores': {},
            'error': error_msg
        }
    
    def get_top_predictions(self, message: str, top_k: int = 3) -> List[Tuple[Intent, float]]:
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
        if not self.is_loaded:
            return []
        
        try:
            # Obtener predicción completa (incluye ml_scores)
            result = self.detect(message)
            ml_scores = result.get('ml_scores', {})
            
            if not ml_scores:
                return []
            
            # Ordenar por score descendente
            sorted_scores = sorted(ml_scores.items(), key=lambda x: x[1], reverse=True)
            
            # Convertir a Intent enum y retornar top K
            results = []
            for label, score in sorted_scores[:top_k]:
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
            True si el servicio está conectado y listo
        """
        return self.is_loaded


# ==========================================
# INSTANCIA GLOBAL
# ==========================================
ml_intent_detector = MLIntentDetector()


# ==========================================
# TEST (solo si se ejecuta directamente)
# ==========================================
if __name__ == "__main__":
    print("="*60)
    print("🧪 TEST - ML Intent Detector (HTTP)")
    print("="*60)
    
    if not ml_intent_detector.is_available():
        print("\n❌ Servicio ML no disponible")
        print("   Verificar:")
        print("   1. ML_SERVICE_URL está configurada")
        print("   2. ML_API_KEY está configurada")
        print("   3. Servicio ml-service está corriendo")
        print("   4. docker-compose logs -f ml-service")
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
        if top_3:
            print(f"  Top 3:")
            for intent, conf in top_3:
                bar = "█" * int(conf * 20)
                print(f"    {intent.value:25s}: {conf:.3f} {bar}")
        print()
    
    print("="*60)
    print("✅ Test completado")