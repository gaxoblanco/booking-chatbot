# scripts/ml/inspect_dataset.py

import json
from collections import Counter
import random

def inspect_dataset(filepath='../../dataset/dataset_training.jsonl'):
    """Inspecciona el dataset generado."""
    
    print("="*80)
    print("🔍 INSPECCIÓN DEL DATASET")
    print("="*80)
    
    # Leer dataset
    examples = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            examples.append(json.loads(line))
    
    print(f"\n📊 Total: {len(examples)} ejemplos")
    
    # Contar por intent
    intents = Counter(ex['intent'] for ex in examples)
    print(f"\n🎯 Por intent:")
    for intent, count in intents.most_common():
        print(f"   {intent:30s}: {count:4d}")
    
    # Contar originales vs augmentados
    aug_count = sum(1 for ex in examples if ex.get('augmented'))
    print(f"\n📝 Originales: {len(examples) - aug_count}")
    print(f"🔄 Augmentados: {aug_count}")
    
    # Ejemplos por técnica
    print(f"\n🔍 EJEMPLOS POR TÉCNICA:")
    
    # Typos (sin tildes)
    typos = [ex for ex in examples 
             if 'psicologo' in ex['message'].lower() 
             and 'psicólogo' not in ex['message']]
    if typos:
        print(f"\n  📌 Sin tildes:")
        for ex in random.sample(typos, min(3, len(typos))):
            print(f"     - {ex['message']}")
    
    # Diminutivos
    dims = [ex for ex in examples if 'ito' in ex['message'] or 'ita' in ex['message']]
    if dims:
        print(f"\n  📌 Diminutivos:")
        for ex in random.sample(dims, min(3, len(dims))):
            print(f"     - {ex['message']}")
    
    # Formales
    formal = [ex for ex in examples 
              if ex['message'].startswith(('Buenos', 'Buenas', 'Estimados'))]
    if formal:
        print(f"\n  📌 Formales:")
        for ex in random.sample(formal, min(3, len(formal))):
            print(f"     - {ex['message'][:60]}...")
    
    # Typos pesados (adulto mayor)
    heavy = [ex for ex in examples 
             if sum(1 for c in ex['message'] if c.isupper()) == 0  # todo minúsculas
             and any(t in ex['message'].lower() for t in ['nesesit', 'kiero', 'tuno'])]
    if heavy:
        print(f"\n  📌 Typos pesados (adulto mayor):")
        for ex in random.sample(heavy, min(3, len(heavy))):
            print(f"     - {ex['message']}")
    
    # Artículos extra
    articles = [ex for ex in examples if ' el ' in ex['message'].lower() 
                or ' la ' in ex['message'].lower()]
    if articles:
        print(f"\n  📌 Con artículos:")
        for ex in random.sample(articles, min(3, len(articles))):
            print(f"     - {ex['message']}")
    
    # Sinónimos profesionales
    synonyms = [ex for ex in examples 
                if any(s in ex['message'].lower() 
                      for s in ['profesional', 'licenciado', 'lic', 'dr', 'dra'])]
    if synonyms:
        print(f"\n  📌 Sinónimos de profesional:")
        for ex in random.sample(synonyms, min(3, len(synonyms))):
            print(f"     - {ex['message']}")
    
    print(f"\n" + "="*80)
    print("✅ Inspección completada")
    print("="*80)

if __name__ == "__main__":
    inspect_dataset()