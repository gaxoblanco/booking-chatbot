"""
ML Intent Detector - spaCy
===========================
Detector de intenciones basado en modelo ML entrenado con spaCy.

Adaptado para funcionar como servicio independiente.

Uso:
    from ml.ml_intent_detector import ml_intent_detector
    
    result = ml_intent_detector.detect("necesito psicólogo mañana")
    print(result['intent'])  # Intent.SEARCH_PROFESSIONAL
    print(result['confidence'])  # 0.95
"""

import spacy
import logging
from pathlib import Path
from typing import Dict, Optional

from ml.intent_enum import Intent
from app.config import settings


logger = logging.getLogger(__name__)


class MLIntentDetector:
    """
    Detector de intenciones usando modelo ML (spaCy).

    Responsabilidades:
    - Cargar modelo spaCy una sola vez (singleton)
    - Detectar intención con alta precisión
    - Retornar confianza probabilística

    Características:
    - Thread-safe (spaCy es thread-safe)
    - Fallback a UNKNOWN si falla predicción
    - Logging de errores
    """

    def __init__(self):
        """Inicializar detector ML."""
        self.nlp = None
        self.is_loaded = False
        self.intents = []
        self.accuracy = None  # Se puede cargar desde meta.json
        # Caché LRU para mensajes repetidos (saludos, respuestas cortas, comandos)
        self._cache: dict = {}
        self._cache_max_size: int = 256
        self._cache_hits: int = 0
        self._cache_misses: int = 0

        # Mapeo de labels del modelo a Intent enum
        self.intent_map = {
            'search_professional':  Intent.SEARCH_PROFESSIONAL,
            'view_my_appointments': Intent.VIEW_MY_APPOINTMENTS,
            'view_tomorrow':        Intent.VIEW_TOMORROW,
            'cancel_appointment':   Intent.CANCEL_APPOINTMENT,
            'info_center':          Intent.INFO_CENTER,
            'greeting':             Intent.GREETING,
            'unknown':              Intent.UNKNOWN,
            # Grupo A — importación de agenda
            'agenda_view_ready':    Intent.AGENDA_VIEW_READY,
            'agenda_view_overlaps': Intent.AGENDA_VIEW_OVERLAPS,
            'agenda_view_existing': Intent.AGENDA_VIEW_EXISTING,
            'agenda_view_errors':   Intent.AGENDA_VIEW_ERRORS,
            'agenda_confirm_upload': Intent.AGENDA_CONFIRM_UPLOAD,
            'agenda_cancel_upload': Intent.AGENDA_CANCEL_UPLOAD,
            # Grupo B — agendar para terceros
            'book_for_third_party': Intent.BOOK_FOR_THIRD_PARTY,
        }

    def load_model(self):
        """
        Carga el modelo entrenado desde disco.

        Raises:
            Exception: Si el modelo no se puede cargar
        """
        model_path = settings.get_model_path()

        try:
            logger.info(f"🔧 Cargando modelo spaCy desde: {model_path}")

            # Cargar modelo
            self.nlp = spacy.load(model_path)

            # Obtener textcat pipe
            if "textcat" not in self.nlp.pipe_names:
                raise ValueError("El modelo no tiene componente 'textcat'")

            textcat = self.nlp.get_pipe("textcat")

            # Obtener lista de intents (labels)
            self.intents = list(textcat.labels)

            # Intentar cargar accuracy desde meta.json
            try:
                meta_path = model_path / "meta.json"
                if meta_path.exists():
                    import json
                    with open(meta_path, 'r') as f:
                        meta = json.load(f)
                        # Intentar obtener accuracy de diferentes fuentes
                        self.accuracy = (
                            meta.get('performance', {}).get('accuracy') or
                            meta.get('accuracy') or
                            0.981  # Default conocido del modelo actual
                        )
            except Exception as e:
                logger.warning(
                    f"⚠️  No se pudo cargar accuracy desde meta.json: {e}")
                self.accuracy = 0.981  # Default

            self.is_loaded = True

            logger.info(f"✅ Modelo cargado exitosamente")
            logger.info(f"   Intenciones: {len(self.intents)}")
            logger.info(f"   Lista: {self.intents}")
            if self.accuracy:
                logger.info(f"   Accuracy: {self.accuracy:.1%}")

        except Exception as e:
            logger.error(f"❌ Error cargando modelo: {e}")
            self.is_loaded = False
            raise

    def detect(self, message: str, context: Optional[Dict] = None) -> Dict:
        # Si modelo no está cargado, retornar unknown
        if not self.is_loaded or self.nlp is None:
            logger.error("❌ Modelo no está cargado")
            return {
                'intent': Intent.UNKNOWN,
                'confidence': 0.0,
                'ml_scores': {},
                'error': 'Model not loaded'
            }

        # Normalizar clave de caché — lowercase, strip
        cache_key = message.strip().lower()

        # Consultar caché
        if cache_key in self._cache:
            self._cache_hits += 1
            return self._cache[cache_key]

        self._cache_misses += 1

        try:
            # Predecir con modelo spaCy
            doc = self.nlp(message)

            predicted_label = max(doc.cats.items(), key=lambda x: x[1])[0]
            confidence = doc.cats[predicted_label]
            intent = self.intent_map.get(predicted_label, Intent.UNKNOWN)

            result = {
                'intent': intent,
                'confidence': confidence,
                'ml_scores': dict(doc.cats)
            }

            # Guardar en caché — solo mensajes cortos (≤50 chars)
            # Los mensajes largos son únicos, no vale cachearlos
            if len(cache_key) <= 50:
                if len(self._cache) >= self._cache_max_size:
                    # Eviction simple: eliminar el primero insertado
                    oldest_key = next(iter(self._cache))
                    del self._cache[oldest_key]
                self._cache[cache_key] = result

            return result

        except Exception as e:
            logger.error(f"❌ Error en predicción: {e}", exc_info=True)
            return {
                'intent': Intent.UNKNOWN,
                'confidence': 0.0,
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
            sorted_cats = sorted(
                doc.cats.items(), key=lambda x: x[1], reverse=True)

            # Convertir a Intent enum y retornar top K
            results = []
            for label, score in sorted_cats[:top_k]:
                intent = self.intent_map.get(label, Intent.UNKNOWN)
                results.append((intent, score))

            return results

        except Exception as e:
            logger.error(f"❌ Error obteniendo predicciones: {e}")
            return []

    def cache_stats(self) -> dict:
        """Estadísticas del caché — útil para monitoreo."""
        total = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total if total > 0 else 0.0
        return {
            'size': len(self._cache),
            'max_size': self._cache_max_size,
            'hits': self._cache_hits,
            'misses': self._cache_misses,
            'hit_rate': hit_rate,
        }


# ==========================================
# INSTANCIA GLOBAL (SINGLETON)
# ==========================================
ml_intent_detector = MLIntentDetector()


# ==========================================
# TEST (solo si se ejecuta directamente)
# ==========================================
if __name__ == "__main__":
    print("="*60)
    print("🧪 TEST - ML Intent Detector")
    print("="*60)

    # Cargar modelo
    try:
        ml_intent_detector.load_model()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nAsegúrate de que el modelo esté entrenado:")
        print("  cd scripts")
        print("  python generate_training_dataset.py")
        print("  python train_spacy_model.py --data ../dataset/dataset_training.jsonl")
        exit(1)

    if not ml_intent_detector.is_loaded:
        print("\n❌ Modelo no disponible")
        exit(1)

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
