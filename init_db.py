"""
Database Initialization Script
===============================
Run this script to initialize/reset the database.
Creates all tables and optionally adds test data.
"""

from database import db
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
    print("\n" + "="*50 + "\n")


def add_test_data():
    """
    Add test data for development.
    """
    print("📝 Adding test data...\n")

    # Test professional 1
    db.add_professional(
        phone="+5491112345678",
        name="Dr. Juan Pérez",
        email="juan.perez@example.com",
        zone="norte",
        gender="m",
        accept_prepaga=True
    )
    db.update_certificate(
        "+5491112345678", "certificates/+5491112345678/cert.jpg")
    db.add_weekly_schedule("+5491112345678", 0, "09:00", "17:00")  # Lunes
    db.add_weekly_schedule("+5491112345678", 2, "09:00", "17:00")  # Miércoles

    # Test professional 2
    db.add_professional(
        phone="+5491187654321",
        name="Dra. María González",
        email="maria.gonzalez@example.com",
        zone="sur",
        gender="f",
        accept_prepaga=False
    )
    db.update_certificate(
        "+5491187654321", "certificates/+5491187654321/cert.pdf")
    db.add_weekly_schedule("+5491187654321", 1, "10:00", "18:00")  # Martes
    db.add_weekly_schedule("+5491187654321", 3, "10:00", "18:00")  # Jueves

    # Test free slot
    db.add_free_slot("+5491112345678", "2025-11-15", "14:00", "15:00")

    print("✅ Test data added successfully\n")


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
