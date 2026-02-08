#!/usr/bin/env python3
"""
Script Maestro - Generación de Dataset Completo
================================================
Combina dataset_base.py + data_augmentation.py para generar
el dataset completo de entrenamiento.

Uso:
    python generate_training_dataset.py

Resultado:
    - dataset_training.jsonl (1000+ ejemplos)
    - Reporte de estadísticas
"""

import sys
from pathlib import Path

# Importar módulos locales
from dataset_base import DATASET_BASE
from data_augmentation import generate_dataset_from_examples, MessageAugmenter


def main():
    """Genera dataset de entrenamiento completo."""
    
    print("\n" + "="*80)
    print("🚀 GENERACIÓN DE DATASET DE ENTRENAMIENTO")
    print("="*80)
    
    # ==========================================
    # CONFIGURACIÓN
    # ==========================================
    
    OUTPUT_FILE = "dataset_training.jsonl"
    N_VARIATIONS = 20  # Variaciones por ejemplo
    
    print(f"\n📋 Configuración:")
    print(f"   - Ejemplos base: {len(DATASET_BASE)}")
    print(f"   - Variaciones por ejemplo: {N_VARIATIONS}")
    print(f"   - Ejemplos totales esperados: {len(DATASET_BASE) * (N_VARIATIONS + 1)}")
    print(f"   - Archivo de salida: {OUTPUT_FILE}")
    
    # ==========================================
    # GENERAR DATASET AUGMENTADO
    # ==========================================
    
    print(f"\n🔄 Generando variaciones...")
    
    try:
        generate_dataset_from_examples(
            DATASET_BASE,
            n_variations_per_example=N_VARIATIONS,
            output_file=OUTPUT_FILE
        )
        
        print(f"\n✅ Generación completada")
        
    except Exception as e:
        print(f"\n❌ Error durante la generación: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # ==========================================
    # VALIDAR DATASET GENERADO
    # ==========================================
    
    print(f"\n📊 Validando dataset generado...")
    
    try:
        import json
        from collections import Counter
        
        # Leer dataset
        examples = []
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                examples.append(json.loads(line))
        
        # Estadísticas
        total = len(examples)
        intents = Counter(ex['intent'] for ex in examples)
        augmented_count = sum(1 for ex in examples if ex.get('augmented', False))
        original_count = total - augmented_count
        
        print(f"\n📈 Estadísticas del Dataset:")
        print(f"   - Total de ejemplos: {total}")
        print(f"   - Originales: {original_count}")
        print(f"   - Augmentados: {augmented_count}")
        print(f"   - Factor de expansión: {total / len(DATASET_BASE):.1f}x")
        
        print(f"\n🎯 Distribución por intent:")
        for intent, count in intents.most_common():
            percentage = (count / total) * 100
            print(f"   {intent:25s}: {count:4d} ({percentage:5.1f}%)")
        
        # Muestras aleatorias
        print(f"\n🔍 Ejemplos aleatorios del dataset:")
        import random
        random.seed(42)
        samples = random.sample(examples, min(5, len(examples)))
        
        for i, sample in enumerate(samples, 1):
            aug_label = "🔄 AUGMENTADO" if sample.get('augmented') else "📝 ORIGINAL"
            print(f"\n   {i}. {aug_label}")
            print(f"      Mensaje: {sample['message']}")
            print(f"      Intent: {sample['intent']}")
            if sample['entities']:
                print(f"      Entidades: {sample['entities']}")
        
        print(f"\n✅ Dataset validado correctamente")
        
    except Exception as e:
        print(f"\n⚠️  Error durante validación: {e}")
        print(f"   El dataset fue generado pero no se pudo validar")
    
    # ==========================================
    # INSTRUCCIONES FINALES
    # ==========================================
    
    print(f"\n" + "="*80)
    print("✅ DATASET GENERADO CON ÉXITO")
    print("="*80)
    
    print(f"\n📁 Archivo generado: {OUTPUT_FILE}")
    print(f"📊 Ejemplos totales: {total}")
    
    print(f"\n🎯 PRÓXIMOS PASOS:")
    print(f"\n1. Revisar el dataset:")
    print(f"   head {OUTPUT_FILE}")
    
    print(f"\n2. Entrenar modelo ML:")
    print(f"   python scripts/train_intent_model.py --data {OUTPUT_FILE}")
    
    print(f"\n3. Evaluar modelo:")
    print(f"   python scripts/evaluate_model.py --data dataset_validation.jsonl")
    
    print(f"\n4. Mientras tanto, recopilar datos reales:")
    print(f"   docker exec whatsapp-demo python scripts/review_conversations.py --stats")
    
    print(f"\n💡 TIP: En 2-3 meses, combina este dataset con datos reales")
    print(f"   para mejorar el modelo de 85% → 92% accuracy")
    
    print("\n" + "="*80)


if __name__ == "__main__":
    main()
