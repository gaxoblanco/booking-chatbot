"""
Domain Setup Script
===================
Interactive script to configure the domain before starting the application.
Runs during Docker build or manual setup.

Usage:
    python setup_domain.py
"""

import os
import sys


def print_header():
    """Print setup header."""
    print("\n" + "="*60)
    print("🎯 DOMAIN CONFIGURATION SETUP")
    print("="*60 + "\n")


def print_available_domains():
    """Show available domain presets."""
    from domain_config import DomainPresets

    domains = {
        "1": ("SALUD", "Profesionales de la Salud (médicos, dentistas, etc.)"),
        "2": ("PSICOLOGIA", "Centro de Psicología (psicólogos, terapeutas)"),
        "3": ("BELLEZA", "Servicios de Belleza (peluquería, manicura, etc.)"),
        "4": ("LEGAL", "Servicios Legales (abogados)"),
        "5": ("FITNESS", "Fitness y Deportes (entrenadores, instructores)"),
        "6": ("EDUCACION", "Educación (profesores, tutores)"),
        "7": ("HOGAR", "Servicios del Hogar (plomería, electricidad, etc.)"),
    }

    print("📋 Dominios disponibles:\n")

    for key, (domain_id, description) in domains.items():
        preset = getattr(DomainPresets, domain_id, None)
        if preset:
            emoji = preset.get('EMOJI_PROFESSIONAL', '📌')
            print(f"{key}️⃣  {emoji} {domain_id.title()}")
            print(f"   {description}")
            print()

    return domains


def select_domain():
    """Interactive domain selection."""
    domains = print_available_domains()

    while True:
        choice = input("Selecciona el dominio (1-7): ").strip()

        if choice in domains:
            domain_id, description = domains[choice]
            print(f"\n✅ Seleccionaste: {domain_id}")
            return domain_id
        else:
            print("❌ Opción inválida. Intenta nuevamente.\n")


def preview_domain(domain_id: str):
    """Show preview of selected domain configuration."""
    from domain_config import DomainPresets

    preset = getattr(DomainPresets, domain_id)

    print("\n" + "-"*60)
    print("📋 VISTA PREVIA DE CONFIGURACIÓN")
    print("-"*60)
    print(f"Negocio: {preset['BUSINESS_NAME']}")
    print(f"Profesional: {preset['PROFESSIONAL_TITLE']}")
    print(f"Certificado: {preset['CERTIFICATE_NAME']}")
    print(f"Categoría: {preset['CATEGORY_LABEL']}")
    print(f"\nCategorías disponibles:")
    for key, value in list(preset['CATEGORIES'].items())[:5]:
        print(f"  • {value}")
    if len(preset['CATEGORIES']) > 5:
        print(f"  ... y {len(preset['CATEGORIES']) - 5} más")
    print("-"*60 + "\n")


def confirm_selection(domain_id: str) -> bool:
    """Confirm domain selection."""
    preview_domain(domain_id)

    while True:
        confirm = input(
            "¿Confirmas esta configuración? (s/n): ").strip().lower()

        if confirm in ['s', 'si', 'sí', 'y', 'yes']:
            return True
        elif confirm in ['n', 'no']:
            return False
        else:
            print("❌ Responde 's' para sí o 'n' para no.\n")


def apply_domain(domain_id: str):
    """Apply domain configuration to domain_config.py."""
    config_file = 'domain_config.py'

    if not os.path.exists(config_file):
        print(f"❌ Error: {config_file} no encontrado")
        sys.exit(1)

    # Read current file
    with open(config_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Find and update the load_preset line
    new_lines = []
    found_load_preset = False

    for line in lines:
        if '# load_preset(' in line or 'load_preset(' in line:
            # Replace with active load_preset call
            new_lines.append(f"load_preset('{domain_id}')\n")
            found_load_preset = True
        else:
            new_lines.append(line)

    # If load_preset line not found, add it at the end
    if not found_load_preset:
        # Find the end of the file (before if __name__ if exists)
        insert_index = len(new_lines)
        for i, line in enumerate(new_lines):
            if 'if __name__' in line:
                insert_index = i
                break

        new_lines.insert(
            insert_index, f"\n# Auto-configured domain\nload_preset('{domain_id}')\n\n")

    # Write updated file
    with open(config_file, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    print(f"✅ Configuración aplicada a {config_file}")


def initialize_database():
    """Initialize database with selected domain configuration."""
    print("\n🔄 Inicializando base de datos...\n")

    from init_db import init_database

    try:
        init_database()
        print("\n✅ Base de datos inicializada correctamente")
        return True
    except Exception as e:
        print(f"\n❌ Error al inicializar base de datos: {e}")
        return False


def main():
    """Main setup flow."""
    print_header()

    print("Este asistente te ayudará a configurar el dominio del chatbot.\n")

    # Step 1: Select domain
    domain_id = select_domain()

    # Step 2: Preview and confirm
    if not confirm_selection(domain_id):
        print(
            "\n❌ Configuración cancelada. Ejecuta el script nuevamente para configurar.\n")
        sys.exit(0)

    # Step 3: Apply configuration
    print("\n🔄 Aplicando configuración...\n")
    apply_domain(domain_id)

    # Step 4: Ask about database initialization
    print("\n" + "="*60)
    init_db = input(
        "¿Deseas inicializar la base de datos ahora? (s/n): ").strip().lower()

    if init_db in ['s', 'si', 'sí', 'y', 'yes']:
        if initialize_database():
            print("\n" + "="*60)
            print("✅ CONFIGURACIÓN COMPLETA")
            print("="*60)
            print(f"\n🎉 Dominio configurado: {domain_id}")
            print("🚀 Ya puedes iniciar la aplicación con: docker-compose up\n")
        else:
            print("\n⚠️  Configuración aplicada pero falló la inicialización de DB")
            print("   Ejecuta manualmente: python init_db.py\n")
    else:
        print("\n" + "="*60)
        print("✅ CONFIGURACIÓN APLICADA")
        print("="*60)
        print(f"\n🎉 Dominio configurado: {domain_id}")
        print("⚠️  Recuerda inicializar la base de datos con: python init_db.py")
        print("🚀 Luego inicia con: docker-compose up\n")


if __name__ == "__main__":
    main()
