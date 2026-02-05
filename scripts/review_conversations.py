#!/usr/bin/env python3
"""
Review Conversations Script v1.0
================================
Herramienta CLI para revisar y corregir etiquetas de conversaciones.

Este script permite:
- Ver conversaciones recopiladas automáticamente
- Validar si la detección fue correcta
- Corregir intenciones y entidades incorrectas
- Generar dataset limpio para entrenamiento ML

Uso:
    python scripts/review_conversations.py
    python scripts/review_conversations.py --priority high
    python scripts/review_conversations.py --date 2026-02-05
    python scripts/review_conversations.py --stats

Ejemplos:
    # Revisar solo casos marcados como prioritarios
    python scripts/review_conversations.py --priority high
    
    # Revisar conversaciones de un día específico
    python scripts/review_conversations.py --date 2026-02-05
    
    # Ver estadísticas sin revisar
    python scripts/review_conversations.py --stats
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime


class ConversationReviewer:
    """
    Revisor interactivo de conversaciones.
    
    Permite validar y corregir las etiquetas automáticas
    para generar un dataset de alta calidad.
    """
    
    def __init__(self, data_dir: str = "data/conversations"):
        """
        Inicializar revisor.
        
        Args:
            data_dir: Directorio con los logs de conversaciones
        """
        self.data_dir = Path(data_dir)
        self.output_dir = Path("dataset")
        self.output_dir.mkdir(exist_ok=True)
        
        self.stats = {
            'reviewed': 0,
            'correct': 0,
            'corrected': 0,
            'skipped': 0
        }
    
    def review_all(self, priority: Optional[str] = None, date: Optional[str] = None):
        """
        Revisa conversaciones interactivamente.
        
        Args:
            priority: Filtrar por prioridad ('high', 'normal', 'low')
            date: Filtrar por fecha (formato: YYYY-MM-DD)
        """
        print("\n" + "="*80)
        print("🔍 REVISOR DE CONVERSACIONES - Dataset para ML")
        print("="*80)
        print("\nInstrucciones:")
        print("  's' = Correcto, guardar")
        print("  'n' = Incorrecto, corregir")
        print("  'skip' = Saltar (revisar después)")
        print("  'q' = Salir")
        print("="*80 + "\n")
        
        # Obtener archivos a revisar
        files_to_review = self._get_files_to_review(date)
        
        if not files_to_review:
            print("❌ No hay archivos para revisar")
            return
        
        print(f"📁 Archivos encontrados: {len(files_to_review)}\n")
        
        # Revisar archivo por archivo
        for filepath in files_to_review:
            print(f"📄 Procesando: {filepath.name}")
            self._review_file(filepath, priority)
        
        # Mostrar resumen
        self._show_summary()
    
    def show_stats(self):
        """Muestra estadísticas de los datos recopilados."""
        print("\n" + "="*80)
        print("📊 ESTADÍSTICAS DE DATOS RECOPILADOS")
        print("="*80 + "\n")
        
        total_messages = 0
        by_intent = {}
        by_confidence = {'low': 0, 'medium': 0, 'high': 0}
        by_date = {}
        
        # Analizar todos los archivos
        for filepath in self.data_dir.glob("conversations_*.jsonl"):
            date_str = filepath.stem.replace('conversations_', '')
            by_date[date_str] = 0
            
            with open(filepath, encoding='utf-8') as f:
                for line in f:
                    entry = json.loads(line)
                    total_messages += 1
                    by_date[date_str] += 1
                    
                    # Contar por intent
                    intent = entry['detected_intent']
                    by_intent[intent] = by_intent.get(intent, 0) + 1
                    
                    # Contar por nivel de confianza
                    conf = entry['confidence']
                    if conf < 0.5:
                        by_confidence['low'] += 1
                    elif conf < 0.8:
                        by_confidence['medium'] += 1
                    else:
                        by_confidence['high'] += 1
        
        # Mostrar resultados
        print(f"📨 Total de mensajes: {total_messages}")
        print(f"\n📅 Mensajes por fecha:")
        for date, count in sorted(by_date.items()):
            print(f"   {date}: {count} mensajes")
        
        print(f"\n🎯 Mensajes por intención:")
        for intent, count in sorted(by_intent.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_messages * 100) if total_messages > 0 else 0
            print(f"   {intent:30s}: {count:4d} ({percentage:5.1f}%)")
        
        print(f"\n📊 Distribución de confianza:")
        for level, count in by_confidence.items():
            percentage = (count / total_messages * 100) if total_messages > 0 else 0
            emoji = "🔴" if level == 'low' else "🟡" if level == 'medium' else "🟢"
            print(f"   {emoji} {level.capitalize():8s}: {count:4d} ({percentage:5.1f}%)")
        
        # Pendientes de revisión
        needs_review = 0
        review_file = self.data_dir / "needs_review.jsonl"
        if review_file.exists():
            with open(review_file, encoding='utf-8') as f:
                for line in f:
                    entry = json.loads(line)
                    if not entry.get('reviewed', False):
                        needs_review += 1
        
        print(f"\n⚠️  Mensajes marcados para revisión: {needs_review}")
        
        # Recomendación
        print(f"\n💡 RECOMENDACIÓN:")
        if total_messages < 500:
            print(f"   Recopila más datos. Mínimo recomendado: 500 mensajes")
            print(f"   Te faltan: {500 - total_messages} mensajes")
        elif total_messages < 1000:
            print(f"   Tienes datos suficientes para un modelo básico")
            print(f"   Para mejor resultado: {1000 - total_messages} mensajes más")
        else:
            print(f"   ✅ Excelente! Tienes suficientes datos para entrenar ML")
            print(f"   Puedes comenzar con el entrenamiento")
        
        print("="*80 + "\n")
    
    def _get_files_to_review(self, date: Optional[str] = None) -> List[Path]:
        """
        Obtiene lista de archivos a revisar.
        
        Args:
            date: Filtrar por fecha (YYYY-MM-DD)
            
        Returns:
            Lista de rutas de archivos
        """
        if date:
            # Buscar archivo específico
            pattern = f"conversations_{date}.jsonl"
            files = list(self.data_dir.glob(pattern))
        else:
            # Todos los archivos
            files = list(self.data_dir.glob("conversations_*.jsonl"))
        
        return sorted(files)
    
    def _review_file(self, filepath: Path, priority_filter: Optional[str] = None):
        """
        Revisa un archivo de conversaciones.
        
        Args:
            filepath: Ruta al archivo JSONL
            priority_filter: Filtrar por prioridad
        """
        with open(filepath, encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    entry = json.loads(line)
                    
                    # Saltar si ya fue revisado
                    if entry.get('human_reviewed', False):
                        continue
                    
                    # Aplicar filtro de prioridad (si está configurado)
                    if priority_filter:
                        # Solo revisar casos de baja confianza si priority='high'
                        if priority_filter == 'high' and entry['confidence'] >= 0.5:
                            continue
                    
                    # Mostrar entrada para revisión
                    if not self._review_entry(entry):
                        # Usuario pidió salir
                        return
                    
                except json.JSONDecodeError as e:
                    print(f"⚠️  Error en línea {line_num}: {e}")
                    continue
    
    def _review_entry(self, entry: Dict) -> bool:
        """
        Revisa una entrada individual.
        
        Args:
            entry: Diccionario con datos del mensaje
            
        Returns:
            True para continuar, False para salir
        """
        # Mostrar información
        print("\n" + "-"*80)
        print(f"📨 Mensaje: {entry['message']}")
        print(f"🎯 Intent detectado: {entry['detected_intent']}")
        print(f"📊 Confianza: {entry['confidence']:.2f}")
        
        if entry['entities']:
            print(f"🏷️  Entidades:")
            for key, value in entry['entities'].items():
                print(f"   - {key}: {value}")
        
        print(f"🔄 Shortcut usado: {'Sí' if entry['shortcut_used'] else 'No'}")
        print(f"📍 Estado: {entry['session_state']}")
        print("-"*80)
        
        # Pedir validación
        while True:
            response = input("\n¿Es correcto? (s/n/skip/q): ").lower().strip()
            
            if response == 'q':
                print("\n👋 Saliendo...")
                return False
            
            elif response == 's':
                # Marcar como correcto
                entry['human_reviewed'] = True
                entry['is_correct'] = True
                self._save_to_training_dataset(entry)
                self.stats['reviewed'] += 1
                self.stats['correct'] += 1
                print("✅ Guardado como correcto")
                return True
            
            elif response == 'n':
                # Pedir corrección
                entry['human_reviewed'] = True
                entry['is_correct'] = False
                
                print("\n📝 Corrección:")
                correct_intent = input(f"   Intent correcto (actual: {entry['detected_intent']}): ").strip()
                
                if correct_intent:
                    entry['correct_intent'] = correct_intent
                
                # Preguntar si corregir entidades
                correct_entities = input("   ¿Corregir entidades? (s/n): ").lower().strip()
                if correct_entities == 's':
                    entry['correct_entities'] = {}
                    print("   Ingresa entidades (vacío para terminar):")
                    while True:
                        key = input("      Clave: ").strip()
                        if not key:
                            break
                        value = input(f"      Valor para '{key}': ").strip()
                        entry['correct_entities'][key] = value
                
                notes = input("   Notas (opcional): ").strip()
                if notes:
                    entry['review_notes'] = notes
                
                self._save_to_training_dataset(entry)
                self.stats['reviewed'] += 1
                self.stats['corrected'] += 1
                print("✅ Guardado con correcciones")
                return True
            
            elif response == 'skip':
                # Saltar por ahora
                self.stats['skipped'] += 1
                print("⏭️  Saltado")
                return True
            
            else:
                print("❌ Opción inválida. Usa: s/n/skip/q")
    
    def _save_to_training_dataset(self, entry: Dict):
        """
        Guarda entrada validada en dataset de entrenamiento.
        
        Args:
            entry: Entrada revisada
        """
        output_file = self.output_dir / "training_data.jsonl"
        
        with open(output_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    
    def _show_summary(self):
        """Muestra resumen de la sesión de revisión."""
        print("\n" + "="*80)
        print("📊 RESUMEN DE REVISIÓN")
        print("="*80)
        print(f"✅ Revisados: {self.stats['reviewed']}")
        print(f"   - Correctos: {self.stats['correct']}")
        print(f"   - Corregidos: {self.stats['corrected']}")
        print(f"⏭️  Saltados: {self.stats['skipped']}")
        print("="*80 + "\n")
        
        if self.stats['reviewed'] > 0:
            accuracy = (self.stats['correct'] / self.stats['reviewed']) * 100
            print(f"📈 Precisión del sistema: {accuracy:.1f}%")
            
            if accuracy < 70:
                print("⚠️  La precisión es baja. Considera mejorar el sistema de reglas o entrenar ML.")
            elif accuracy < 85:
                print("👍 Precisión aceptable. ML podría mejorar los resultados.")
            else:
                print("✅ Excelente precisión! El sistema de reglas funciona bien.")
        
        print(f"\n💾 Dataset guardado en: {self.output_dir / 'training_data.jsonl'}\n")


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description="Revisar conversaciones recopiladas para dataset de ML"
    )
    parser.add_argument(
        '--priority',
        choices=['high', 'normal', 'low'],
        help="Filtrar por prioridad (high = solo casos de baja confianza)"
    )
    parser.add_argument(
        '--date',
        help="Filtrar por fecha (formato: YYYY-MM-DD)"
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help="Solo mostrar estadísticas, sin revisar"
    )
    parser.add_argument(
        '--data-dir',
        default='data/conversations',
        help="Directorio con los datos (default: data/conversations)"
    )
    
    args = parser.parse_args()
    
    # Crear revisor
    reviewer = ConversationReviewer(data_dir=args.data_dir)
    
    # Mostrar estadísticas o revisar
    if args.stats:
        reviewer.show_stats()
    else:
        reviewer.review_all(priority=args.priority, date=args.date)


if __name__ == "__main__":
    main()
