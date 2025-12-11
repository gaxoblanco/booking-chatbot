#!/usr/bin/env python3
"""
Script para limpiar citas de prueba
====================================
Elimina todas las citas asociadas a los teléfonos de prueba.

Uso:
    python scripts/clear_test_appointments.py
    
    # O con opciones:
    python scripts/clear_test_appointments.py --all       # Borrar TODAS las citas (cuidado)
    python scripts/clear_test_appointments.py --client    # Solo citas del cliente de prueba
    python scripts/clear_test_appointments.py --prof      # Solo citas del profesional de prueba
"""
import sys
import argparse
from pathlib import Path

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.database import db


# Teléfonos de prueba (AJUSTAR SI ES NECESARIO)
TEST_CLIENT_PHONE = "+5491123456789"
TEST_PROF_PHONE = "+5491112345678"


def clear_client_appointments(client_phone: str):
    """Elimina citas de un cliente específico."""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Primero, ver cuántas hay
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM appointments 
                WHERE client_phone = ?
            """, (client_phone,))
            count_before = cursor.fetchone()['count']
            
            if count_before == 0:
                print(f"ℹ️  No hay citas para el cliente {client_phone}")
                return 0
            
            # Borrar
            cursor.execute("""
                DELETE FROM appointments 
                WHERE client_phone = ?
            """, (client_phone,))
            
            deleted = cursor.rowcount
            print(f"✅ {deleted} citas eliminadas para cliente {client_phone}")
            return deleted
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return 0


def clear_professional_appointments(prof_phone: str):
    """Elimina citas de un profesional específico."""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Primero, ver cuántas hay
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM appointments 
                WHERE professional_phone = ?
            """, (prof_phone,))
            count_before = cursor.fetchone()['count']
            
            if count_before == 0:
                print(f"ℹ️  No hay citas para el profesional {prof_phone}")
                return 0
            
            # Borrar
            cursor.execute("""
                DELETE FROM appointments 
                WHERE professional_phone = ?
            """, (prof_phone,))
            
            deleted = cursor.rowcount
            print(f"✅ {deleted} citas eliminadas para profesional {prof_phone}")
            return deleted
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return 0


def clear_all_appointments():
    """Elimina TODAS las citas (usar con precaución)."""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Primero, ver cuántas hay
            cursor.execute("SELECT COUNT(*) as count FROM appointments")
            count_before = cursor.fetchone()['count']
            
            if count_before == 0:
                print("ℹ️  No hay citas en la base de datos")
                return 0
            
            # Confirmar
            print(f"⚠️  Estás por borrar {count_before} citas")
            confirm = input("¿Estás seguro? (escribe 'SI' para confirmar): ")
            
            if confirm != "SI":
                print("❌ Operación cancelada")
                return 0
            
            # Borrar
            cursor.execute("DELETE FROM appointments")
            
            deleted = cursor.rowcount
            print(f"✅ {deleted} citas eliminadas (TODAS)")
            return deleted
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return 0


def clear_test_data():
    """Limpia datos de prueba (cliente y profesional de prueba)."""
    print("🗑️  Limpiando citas de prueba...\n")
    
    total_deleted = 0
    
    # Borrar citas del cliente de prueba
    print(f"📱 Cliente de prueba: {TEST_CLIENT_PHONE}")
    total_deleted += clear_client_appointments(TEST_CLIENT_PHONE)
    
    print()
    
    # Borrar citas del profesional de prueba
    print(f"👨‍⚕️ Profesional de prueba: {TEST_PROF_PHONE}")
    total_deleted += clear_professional_appointments(TEST_PROF_PHONE)
    
    print()
    
    # Mostrar resumen
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM appointments")
            remaining = cursor.fetchone()['count']
            print(f"📊 Resumen:")
            print(f"   - Citas eliminadas: {total_deleted}")
            print(f"   - Citas restantes: {remaining}")
    except Exception as e:
        print(f"❌ Error al obtener resumen: {e}")


def show_stats():
    """Muestra estadísticas de citas."""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Total de citas
            cursor.execute("SELECT COUNT(*) as count FROM appointments")
            total = cursor.fetchone()['count']
            
            # Por estado
            cursor.execute("""
                SELECT status, COUNT(*) as count 
                FROM appointments 
                GROUP BY status
                ORDER BY count DESC
            """)
            by_status = cursor.fetchall()
            
            # Por teléfonos de prueba
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM appointments 
                WHERE client_phone = ? OR professional_phone = ?
            """, (TEST_CLIENT_PHONE, TEST_PROF_PHONE))
            test_count = cursor.fetchone()['count']
            
            print("📊 Estadísticas de Citas:\n")
            print(f"   Total: {total} citas")
            print(f"   De prueba: {test_count} citas")
            print()
            
            if by_status:
                print("   Por estado:")
                for row in by_status:
                    status = row['status']
                    count = row['count']
                    print(f"      - {status}: {count}")
            else:
                print("   No hay citas en la base de datos")
                
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description='Limpia citas de prueba de la base de datos'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Borrar TODAS las citas (requiere confirmación)'
    )
    parser.add_argument(
        '--client',
        action='store_true',
        help='Borrar solo citas del cliente de prueba'
    )
    parser.add_argument(
        '--prof',
        action='store_true',
        help='Borrar solo citas del profesional de prueba'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Mostrar estadísticas sin borrar nada'
    )
    
    args = parser.parse_args()
    
    # Si se pide stats, mostrar y salir
    if args.stats:
        show_stats()
        return
    
    # Procesar según flags
    if args.all:
        clear_all_appointments()
    elif args.client:
        print("🗑️  Limpiando citas del cliente de prueba...\n")
        print(f"📱 Cliente: {TEST_CLIENT_PHONE}")
        clear_client_appointments(TEST_CLIENT_PHONE)
    elif args.prof:
        print("🗑️  Limpiando citas del profesional de prueba...\n")
        print(f"👨‍⚕️ Profesional: {TEST_PROF_PHONE}")
        clear_professional_appointments(TEST_PROF_PHONE)
    else:
        # Por defecto: limpiar ambos (cliente y profesional de prueba)
        clear_test_data()
    
    print("\n✅ Listo!")


if __name__ == "__main__":
    main()
