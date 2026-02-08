#!/usr/bin/env python3
"""
Script de Evaluación - spaCy Intent Detection
==============================================
Evalúa el modelo spaCy entrenado con métricas detalladas.

Uso:
    python evaluate_spacy_model.py --model models/intent_classifier
    python evaluate_spacy_model.py --model models/intent_classifier --data ../../dataset/dataset_validation.jsonl

Resultado:
    - Accuracy global
    - Precision, Recall, F1 por intent
    - Matriz de confusión
    - Ejemplos de errores
"""

import json
import argparse
from pathlib import Path
from typing import List, Dict
from collections import Counter
import spacy
from sklearn.metrics import classification_report, confusion_matrix
import numpy as np


class SpacyIntentEvaluator:
    """
    Evaluador de modelo spaCy para intent detection.
    
    Genera métricas detalladas y análisis de errores.
    """
    
    def __init__(self, model_path: str):
        """
        Inicializar evaluador.
        
        Args:
            model_path: Ruta al modelo entrenado
        """
        self.model_path = Path(model_path)
        self.nlp = None
        self.intents = []
    
    def load_model(self):
        """Carga el modelo entrenado."""
        print(f"\n📂 Cargando modelo: {self.model_path}")
        
        try:
            self.nlp = spacy.load(self.model_path)
            
            # Obtener lista de intents
            textcat = self.nlp.get_pipe("textcat")
            self.intents = list(textcat.labels)
            
            print(f"   ✅ Modelo cargado")
            print(f"   ✅ {len(self.intents)} intents: {self.intents}")
            
        except Exception as e:
            print(f"   ❌ Error cargando modelo: {e}")
            raise
    
    def load_test_data(self, filepath: str) -> List[Dict]:
        """
        Carga datos de test.
        
        Args:
            filepath: Ruta al archivo JSONL
            
        Returns:
            Lista de ejemplos de test
        """
        print(f"\n📂 Cargando datos de test: {filepath}")
        
        data = []
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                entry = json.loads(line)
                data.append({
                    'text': entry['message'],
                    'intent': entry['intent']
                })
        
        print(f"   ✅ {len(data)} ejemplos cargados")
        
        return data
    
    def evaluate(self, test_data: List[Dict]) -> Dict:
        """
        Evalúa el modelo en datos de test.
        
        Args:
            test_data: Lista de ejemplos de test
            
        Returns:
            Diccionario con métricas
        """
        print(f"\n📊 Evaluando modelo...")
        
        y_true = []
        y_pred = []
        errors = []
        
        for example in test_data:
            # Predecir
            doc = self.nlp(example['text'])
            predicted = max(doc.cats.items(), key=lambda x: x[1])[0]
            confidence = doc.cats[predicted]
            
            y_true.append(example['intent'])
            y_pred.append(predicted)
            
            # Guardar errores
            if predicted != example['intent']:
                errors.append({
                    'text': example['text'],
                    'true': example['intent'],
                    'predicted': predicted,
                    'confidence': confidence
                })
        
        # Calcular métricas
        accuracy = sum(1 for t, p in zip(y_true, y_pred) if t == p) / len(y_true)
        
        print(f"   ✅ Evaluación completada")
        print(f"   Accuracy: {accuracy:.1%}")
        
        return {
            'accuracy': accuracy,
            'y_true': y_true,
            'y_pred': y_pred,
            'errors': errors
        }
    
    def print_detailed_report(self, metrics: Dict):
        """
        Imprime reporte detallado de métricas.
        
        Args:
            metrics: Diccionario con métricas de evaluación
        """
        print("\n" + "="*80)
        print("📊 REPORTE DE EVALUACIÓN DETALLADO")
        print("="*80)
        
        # Accuracy global
        print(f"\n🎯 Accuracy Global: {metrics['accuracy']:.1%}")
        
        # Classification report
        print(f"\n📋 Métricas por Intent:")
        print("\n" + classification_report(
            metrics['y_true'],
            metrics['y_pred'],
            labels=self.intents,
            target_names=self.intents,
            digits=3
        ))
        
        # Matriz de confusión
        print(f"\n🔲 Matriz de Confusión:")
        cm = confusion_matrix(metrics['y_true'], metrics['y_pred'], labels=self.intents)
        self._print_confusion_matrix(cm, self.intents)
        
        # Distribución de errores
        if metrics['errors']:
            print(f"\n❌ Errores ({len(metrics['errors'])} total):")
            error_types = Counter((e['true'], e['predicted']) for e in metrics['errors'])
            for (true, pred), count in error_types.most_common(10):
                print(f"   {true:25s} → {pred:25s}: {count:3d} errores")
            
            # Ejemplos de errores
            print(f"\n📝 Ejemplos de Errores (primeros 10):")
            for i, error in enumerate(metrics['errors'][:10], 1):
                print(f"\n   {i}. Mensaje: {error['text']}")
                print(f"      Real: {error['true']}")
                print(f"      Predicho: {error['predicted']} (confianza: {error['confidence']:.2f})")
    
    def _print_confusion_matrix(self, cm: np.ndarray, labels: List[str]):
        """
        Imprime matriz de confusión formateada.
        
        Args:
            cm: Matriz de confusión
            labels: Lista de labels
        """
        # Header
        print("\n   " + " " * 25 + "PREDICHO")
        print("   " + " " * 10 + " | " + " | ".join(f"{l[:8]:8s}" for l in labels))
        print("   " + "-" * (10 + len(labels) * 11))
        
        # Rows
        for i, label in enumerate(labels):
            row_label = f"{label[:8]:8s}"
            if i == 0:
                prefix = "REAL"
            else:
                prefix = "    "
            
            values = " | ".join(f"{cm[i][j]:8d}" for j in range(len(labels)))
            print(f"   {prefix} {row_label} | {values}")
    
    def test_interactive(self):
        """Modo interactivo para probar el modelo."""
        print("\n" + "="*80)
        print("🧪 MODO INTERACTIVO - Prueba el modelo")
        print("="*80)
        print("\nEscribe mensajes para ver las predicciones.")
        print("Escribe 'salir' o 'exit' para terminar.\n")
        
        while True:
            try:
                text = input("Mensaje: ").strip()
                
                if text.lower() in ['salir', 'exit', 'quit']:
                    print("\n👋 ¡Hasta luego!")
                    break
                
                if not text:
                    continue
                
                # Predecir
                doc = self.nlp(text)
                
                # Mostrar resultados
                print(f"\n   📊 Predicciones:")
                sorted_cats = sorted(doc.cats.items(), key=lambda x: x[1], reverse=True)
                for intent, score in sorted_cats:
                    bar = "█" * int(score * 20)
                    print(f"      {intent:25s}: {score:.3f} {bar}")
                
                predicted = sorted_cats[0][0]
                confidence = sorted_cats[0][1]
                print(f"\n   ✅ Intent: {predicted} (confianza: {confidence:.1%})\n")
                
            except KeyboardInterrupt:
                print("\n\n👋 ¡Hasta luego!")
                break
            except Exception as e:
                print(f"\n   ❌ Error: {e}\n")


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description="Evalúa modelo spaCy de intent detection"
    )
    parser.add_argument(
        '--model',
        required=True,
        help="Ruta al modelo entrenado"
    )
    parser.add_argument(
        '--data',
        help="Ruta al dataset de test (JSONL). Si no se proporciona, usa modo interactivo."
    )
    parser.add_argument(
        '--interactive',
        action='store_true',
        help="Modo interactivo para probar el modelo"
    )
    
    args = parser.parse_args()
    
    print("="*80)
    print("📊 EVALUACIÓN DE MODELO SPACY - INTENT DETECTION")
    print("="*80)
    
    # Crear evaluador
    evaluator = SpacyIntentEvaluator(args.model)
    evaluator.load_model()
    
    # Evaluar en datos de test
    if args.data:
        test_data = evaluator.load_test_data(args.data)
        metrics = evaluator.evaluate(test_data)
        evaluator.print_detailed_report(metrics)
    
    # Modo interactivo
    if args.interactive or not args.data:
        evaluator.test_interactive()


if __name__ == "__main__":
    main()
