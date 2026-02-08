#!/usr/bin/env python3
"""
Script de Entrenamiento - spaCy Intent Detection
=================================================
Entrena un modelo spaCy para clasificación de intenciones.

Uso:
    python train_spacy_model.py --data ../../dataset/dataset_training.jsonl
    python train_spacy_model.py --data ../../dataset/dataset_training.jsonl --iterations 50
    python train_spacy_model.py --help

Resultado:
    - Modelo entrenado en: models/intent_classifier/
    - Métricas de entrenamiento
    - Reporte de accuracy
"""

import json
import random
import argparse
from pathlib import Path
from typing import List, Dict, Tuple
import spacy
from spacy.training import Example
from spacy.util import minibatch, compounding
from tqdm import tqdm


class SpacyIntentTrainer:
    """
    Entrenador de modelo spaCy para clasificación de intenciones.
    
    Pipeline:
    1. Cargar dataset
    2. Preparar datos para spaCy
    3. Crear modelo base
    4. Entrenar con early stopping
    5. Guardar modelo
    """
    
    def __init__(
        self,
        model_output_dir: str = "models/intent_classifier",
        base_model: str = "es_core_news_sm"
    ):
        """
        Inicializar trainer.
        
        Args:
            model_output_dir: Directorio para guardar modelo entrenado
            base_model: Modelo base de spaCy (es_core_news_sm/md/lg)
        """
        self.model_output_dir = Path(model_output_dir)
        self.base_model = base_model
        self.nlp = None
        self.intents = set()
    
    def load_dataset(self, filepath: str) -> Tuple[List, List]:
        """
        Carga dataset desde archivo JSONL.
        
        Args:
            filepath: Ruta al archivo JSONL
            
        Returns:
            (train_data, eval_data): Tuplas con datos de entrenamiento y evaluación
        """
        print(f"\n📂 Cargando dataset: {filepath}")
        
        data = []
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                entry = json.loads(line)
                data.append({
                    'text': entry['message'],
                    'intent': entry['intent']
                })
                self.intents.add(entry['intent'])
        
        print(f"   ✅ {len(data)} ejemplos cargados")
        print(f"   ✅ {len(self.intents)} intents: {sorted(self.intents)}")
        
        # Split 80-20 para train/eval
        random.shuffle(data)
        split_idx = int(len(data) * 0.8)
        train_data = data[:split_idx]
        eval_data = data[split_idx:]
        
        print(f"   ✅ Train: {len(train_data)} ejemplos")
        print(f"   ✅ Eval: {len(eval_data)} ejemplos")
        
        return train_data, eval_data
    
    def prepare_training_data(self, data: List[Dict]) -> List[Example]:
        """
        Convierte datos al formato de spaCy.
        
        Args:
            data: Lista de diccionarios con 'text' e 'intent'
            
        Returns:
            Lista de Examples de spaCy
        """
        examples = []
        
        for entry in data:
            doc = self.nlp.make_doc(entry['text'])
            
            # Crear diccionario de categorías (todas a 0.0 excepto la correcta a 1.0)
            cats = {intent: 0.0 for intent in self.intents}
            cats[entry['intent']] = 1.0
            
            # Crear Example
            example = Example.from_dict(doc, {"cats": cats})
            examples.append(example)
        
        return examples
    
    def create_model(self):
        """
        Crea modelo base de spaCy con text classifier.
        """
        print(f"\n🔧 Creando modelo base...")
        
        try:
            # Intentar cargar modelo pre-entrenado en español
            print(f"   Cargando modelo: {self.base_model}")
            self.nlp = spacy.load(self.base_model)
            print(f"   ✅ Modelo {self.base_model} cargado")
        except OSError:
            print(f"   ⚠️  Modelo {self.base_model} no encontrado")
            print(f"   📥 Descargando modelo...")
            print(f"   Ejecuta: python -m spacy download {self.base_model}")
            print(f"\n   Creando modelo en blanco mientras tanto...")
            self.nlp = spacy.blank("es")
        
        # Agregar text classifier si no existe
        if "textcat" not in self.nlp.pipe_names:
            textcat = self.nlp.add_pipe(
                "textcat",
                config={
                    "threshold": 0.5,
                    "model": {
                        "@architectures": "spacy.TextCatEnsemble.v2",
                        "tok2vec": {
                            "@architectures": "spacy.Tok2Vec.v2",
                            "embed": {
                                "@architectures": "spacy.MultiHashEmbed.v2",
                                "width": 64,
                                "rows": [2000, 2000, 1000, 1000],
                                "attrs": ["NORM", "LOWER", "PREFIX", "SUFFIX"],
                                "include_static_vectors": False
                            },
                            "encode": {
                                "@architectures": "spacy.MaxoutWindowEncoder.v2",
                                "width": 64,
                                "window_size": 1,
                                "maxout_pieces": 3,
                                "depth": 2
                            }
                        },
                        "linear_model": {
                            "@architectures": "spacy.TextCatBOW.v2",
                            "exclusive_classes": True,
                            "ngram_size": 1,
                            "no_output_layer": False
                        }
                    }
                }
            )
        else:
            textcat = self.nlp.get_pipe("textcat")
        
        # Agregar labels (intents)
        for intent in self.intents:
            textcat.add_label(intent)
        
        print(f"   ✅ Text classifier agregado con {len(self.intents)} labels")
    
    def train(
        self,
        train_examples: List[Example],
        eval_examples: List[Example],
        n_iter: int = 30,
        dropout: float = 0.2,
        batch_size: int = 8
    ) -> Dict:
        """
        Entrena el modelo.
        
        Args:
            train_examples: Ejemplos de entrenamiento
            eval_examples: Ejemplos de evaluación
            n_iter: Número de iteraciones
            dropout: Tasa de dropout
            batch_size: Tamaño de batch
            
        Returns:
            Diccionario con métricas de entrenamiento
        """
        print(f"\n🎓 Entrenando modelo...")
        print(f"   Iteraciones: {n_iter}")
        print(f"   Dropout: {dropout}")
        print(f"   Batch size: {batch_size}")
        
        # Deshabilitar otros componentes del pipeline
        other_pipes = [pipe for pipe in self.nlp.pipe_names if pipe != "textcat"]
        with self.nlp.disable_pipes(*other_pipes):
            
            # Inicializar
            self.nlp.initialize(lambda: train_examples)
            
            # Entrenar
            best_accuracy = 0.0
            history = []
            
            for epoch in range(n_iter):
                # Shuffle training data
                random.shuffle(train_examples)
                
                # Entrenamiento por batches
                losses = {}
                batches = minibatch(train_examples, size=compounding(4.0, batch_size, 1.001))
                
                for batch in batches:
                    self.nlp.update(
                        batch,
                        drop=dropout,
                        losses=losses
                    )
                
                # Evaluar
                train_acc = self._evaluate(train_examples)
                eval_acc = self._evaluate(eval_examples)
                
                # Guardar mejor modelo
                if eval_acc > best_accuracy:
                    best_accuracy = eval_acc
                    self._save_model(suffix=f"_best")
                
                # Guardar historial
                history.append({
                    'epoch': epoch + 1,
                    'loss': losses.get('textcat', 0.0),
                    'train_acc': train_acc,
                    'eval_acc': eval_acc
                })
                
                # Mostrar progreso
                print(f"   Epoch {epoch + 1:2d}/{n_iter} | "
                      f"Loss: {losses.get('textcat', 0.0):6.4f} | "
                      f"Train: {train_acc:.1%} | "
                      f"Eval: {eval_acc:.1%} {'⭐' if eval_acc == best_accuracy else ''}")
        
        print(f"\n✅ Entrenamiento completado")
        print(f"   Mejor accuracy en eval: {best_accuracy:.1%}")
        
        return {
            'best_accuracy': best_accuracy,
            'history': history
        }
    
    def _evaluate(self, examples: List[Example]) -> float:
        """
        Evalúa el modelo en un conjunto de ejemplos.
        
        Args:
            examples: Lista de Examples
            
        Returns:
            Accuracy (0.0 - 1.0)
        """
        correct = 0
        total = len(examples)
        
        for example in examples:
            # Predecir
            doc = self.nlp(example.reference.text)
            predicted = max(doc.cats.items(), key=lambda x: x[1])[0]
            
            # Obtener label correcto
            correct_label = max(example.reference.cats.items(), key=lambda x: x[1])[0]
            
            if predicted == correct_label:
                correct += 1
        
        return correct / total if total > 0 else 0.0
    
    def _save_model(self, suffix: str = ""):
        """
        Guarda el modelo entrenado.
        
        Args:
            suffix: Sufijo para el nombre del directorio
        """
        output_dir = Path(str(self.model_output_dir) + suffix)
        output_dir.mkdir(parents=True, exist_ok=True)
        self.nlp.to_disk(output_dir)
    
    def save_final_model(self):
        """Guarda el modelo final."""
        print(f"\n💾 Guardando modelo final...")
        self.model_output_dir.mkdir(parents=True, exist_ok=True)
        self.nlp.to_disk(self.model_output_dir)
        print(f"   ✅ Modelo guardado en: {self.model_output_dir}")
    
    def save_training_report(self, metrics: Dict, output_file: str = "training_report.json"):
        """
        Guarda reporte de entrenamiento.
        
        Args:
            metrics: Métricas de entrenamiento
            output_file: Archivo de salida
        """
        report = {
            'model': str(self.model_output_dir),
            'base_model': self.base_model,
            'intents': sorted(list(self.intents)),
            'best_accuracy': metrics['best_accuracy'],
            'history': metrics['history']
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"   ✅ Reporte guardado en: {output_file}")


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description="Entrena modelo spaCy para intent detection"
    )
    parser.add_argument(
        '--data',
        required=True,
        help="Ruta al dataset JSONL"
    )
    parser.add_argument(
        '--output',
        default='models/intent_classifier',
        help="Directorio de salida para el modelo"
    )
    parser.add_argument(
        '--base-model',
        default='es_core_news_sm',
        help="Modelo base de spaCy (es_core_news_sm/md/lg)"
    )
    parser.add_argument(
        '--iterations',
        type=int,
        default=30,
        help="Número de iteraciones de entrenamiento"
    )
    parser.add_argument(
        '--dropout',
        type=float,
        default=0.2,
        help="Tasa de dropout"
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=8,
        help="Tamaño de batch"
    )
    
    args = parser.parse_args()
    
    print("="*80)
    print("🚀 ENTRENAMIENTO DE MODELO SPACY - INTENT DETECTION")
    print("="*80)
    
    # Crear trainer
    trainer = SpacyIntentTrainer(
        model_output_dir=args.output,
        base_model=args.base_model
    )
    
    # Cargar dataset
    train_data, eval_data = trainer.load_dataset(args.data)
    
    # Crear modelo
    trainer.create_model()
    
    # Preparar datos
    print(f"\n📊 Preparando datos para spaCy...")
    train_examples = trainer.prepare_training_data(train_data)
    eval_examples = trainer.prepare_training_data(eval_data)
    print(f"   ✅ {len(train_examples)} ejemplos de entrenamiento")
    print(f"   ✅ {len(eval_examples)} ejemplos de evaluación")
    
    # Entrenar
    metrics = trainer.train(
        train_examples,
        eval_examples,
        n_iter=args.iterations,
        dropout=args.dropout,
        batch_size=args.batch_size
    )
    
    # Guardar modelo final
    trainer.save_final_model()
    
    # Guardar reporte
    trainer.save_training_report(metrics)
    
    print("\n" + "="*80)
    print("✅ ENTRENAMIENTO COMPLETADO")
    print("="*80)
    print(f"\n📊 Resultados:")
    print(f"   Mejor accuracy: {metrics['best_accuracy']:.1%}")
    print(f"   Modelo guardado en: {args.output}")
    print(f"\n🎯 Próximo paso:")
    print(f"   python evaluate_spacy_model.py --model {args.output}")


if __name__ == "__main__":
    main()
