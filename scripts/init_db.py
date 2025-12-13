"""
Database Initialization Script
===============================
Run this script to initialize/reset the database.
Creates all tables and optionally adds test data.
"""

from src.database.database import db
import sys


def init_database():
    """
    Initialize database with all tables.
    Database() constructor already calls _init_db(), so this just confirms it.
    """
    print("\n" + "="*50)
    print("DATABASE INITIALIZATION")
    print("="*50 + "\n")

    # Database is already initialized in constructor
    print("✅ All tables created successfully\n")

    # Show stats
    stats = db.get_stats()
    print("📊 Current Statistics:")
    print(f"   Professionals: {stats.get('total_professionals', 0)}")
    print(f"   Searches: {stats.get('total_searches', 0)}")
    print(f"   Contacts: {stats.get('total_contacts', 0)}")

    # Show configured domain
    try:
        from src.config.domain_config import DomainConfig
        print(f"\n🎯 Configured Domain:")
        print(f"   Business: {DomainConfig.BUSINESS_NAME}")
        print(f"   Professional: {DomainConfig.PROFESSIONAL_TITLE}")
        print(f"   Category: {DomainConfig.CATEGORY_LABEL}")
    except Exception as e:
        print(f"\n⚠️  Could not load domain config: {e}")

    print("\n" + "="*50 + "\n")


def add_test_data():
    """
    Add test data for development.
    Creates sample professionals with different configurations.
    """
    from src.config.domain_config import DomainConfig

    print("📝 Adding test data...\n")

    # Get available zones
    zones = list(DomainConfig.ZONES.keys())
    zone1 = zones[0] if len(zones) > 0 else "norte"
    zone2 = zones[1] if len(zones) > 1 else "sur"

    # Get available categories
    categories = list(DomainConfig.CATEGORIES.values())
    category1 = categories[0] if len(categories) > 0 else "General"
    category2 = categories[1] if len(categories) > 1 else "Especialista"

    # Test professional 1
    prof1_data = {
        "phone": "+5491112345678",
        "name": f"Dr. Juan Pérez",
        "email": "juan.perez@example.com",
        "zone": zone1,
        "gender": "m",
        "accept_prepaga": True,
        "category": category1
    }

    # Add custom field 2 if enabled
    if hasattr(DomainConfig, 'CUSTOM_FIELD_2_ENABLED') and DomainConfig.CUSTOM_FIELD_2_ENABLED:
        prof1_data[DomainConfig.CUSTOM_FIELD_2_KEY] = True

    db.add_professional(**prof1_data)
    db.update_certificate(
        "+5491112345678", "certificates/+5491112345678/cert.jpg")
    db.add_weekly_schedule("+5491112345678", 0, "09:00", "17:00")  # Lunes
    db.add_weekly_schedule("+5491112345678", 2, "09:00", "17:00")  # Miércoles

    print(f"✅ Created: {prof1_data['name']} ({zone1})")

    # Test professional 2
    prof2_data = {
        "phone": "+5491187654321",
        "name": "Dra. María González",
        "email": "maria.gonzalez@example.com",
        "zone": zone2,
        "gender": "f",
        "accept_prepaga": False,
        "category": category2
    }

    # Add custom field 2 if enabled
    if hasattr(DomainConfig, 'CUSTOM_FIELD_2_ENABLED') and DomainConfig.CUSTOM_FIELD_2_ENABLED:
        prof2_data[DomainConfig.CUSTOM_FIELD_2_KEY] = False

    db.add_professional(**prof2_data)
    db.update_certificate(
        "+5491187654321", "certificates/+5491187654321/cert.pdf")
    db.add_weekly_schedule("+5491187654321", 1, "10:00", "18:00")  # Martes
    db.add_weekly_schedule("+5491187654321", 3, "10:00", "18:00")  # Jueves

    print(f"✅ Created: {prof2_data['name']} ({zone2})")

    # Test free slot
    db.add_free_slot("+5491112345678", "2025-11-15", "14:00", "15:00")

    print("\n✅ Test data added successfully\n")


if __name__ == "__main__":
    """
    Run this script to initialize database.
    Usage:
        python init_db.py              # Just initialize
        python init_db.py --test-data  # Initialize + add test data
    """
    init_database()

    if "--test-data" in sys.argv:
        add_test_data()

    print("🎉 Database ready to use!")
