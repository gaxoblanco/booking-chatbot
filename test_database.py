"""
Database Tests
==============
Test CRUD operations and data integrity.
"""

from database import Database
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_database():
    """Test database operations."""

    print("\n" + "="*50)
    print("🧪 DATABASE TESTS")
    print("="*50 + "\n")

    # Use test database
    db = Database("test_database.db")

    # Test data
    test_phone = "+5491112345678"
    test_phone2 = "+5491187654321"

    # ==========================================
    # TEST 1: Add Professional
    # ==========================================
    print("📝 TEST 1: Add Professional")
    success = db.add_professional(
        phone=test_phone,
        name="Dr. Test Uno",
        email="test1@example.com",
        zone="norte",
        gender="m",
        accept_prepaga=True,
        especialidad="Médico General"
    )
    assert success, "❌ Failed to add professional"
    print("✅ Professional added successfully\n")

    # ==========================================
    # TEST 2: Get Professional
    # ==========================================
    print("📝 TEST 2: Get Professional")
    prof = db.get_professional(test_phone)
    assert prof is not None, "❌ Professional not found"
    assert prof['name'] == "Dr. Test Uno", "❌ Name mismatch"
    assert prof['zone'] == "norte", "❌ Zone mismatch"
    assert prof['especialidad'] == "Médico General", "❌ Especialidad mismatch"
    print(f"✅ Professional retrieved: {prof['name']}\n")

    # ==========================================
    # TEST 3: Update Professional
    # ==========================================
    print("📝 TEST 3: Update Professional")
    success = db.add_professional(
        phone=test_phone,
        name="Dr. Test Actualizado",
        email="nuevo@example.com",
        zone="sur",
        gender="m",
        accept_prepaga=False,
        especialidad="Dentista"
    )
    prof = db.get_professional(test_phone)
    assert prof['name'] == "Dr. Test Actualizado", "❌ Name not updated"
    assert prof['zone'] == "sur", "❌ Zone not updated"
    print("✅ Professional updated successfully\n")

    # ==========================================
    # TEST 4: Add Certificate
    # ==========================================
    print("📝 TEST 4: Add Certificate")
    cert_path = f"certificates/{test_phone}/cert.jpg"
    success = db.update_certificate(test_phone, cert_path)
    assert success, "❌ Failed to update certificate"
    assert db.professional_has_certificate(
        test_phone), "❌ Certificate not found"
    print("✅ Certificate added successfully\n")

    # ==========================================
    # TEST 5: Weekly Schedule
    # ==========================================
    print("📝 TEST 5: Weekly Schedule")

    # Add Monday 9-17
    success = db.add_weekly_schedule(test_phone, 0, "09:00", "17:00")
    assert success, "❌ Failed to add weekly schedule"

    # Add Wednesday 10-18
    success = db.add_weekly_schedule(test_phone, 2, "10:00", "18:00")
    assert success, "❌ Failed to add weekly schedule"

    schedules = db.get_weekly_schedule(test_phone)
    assert len(schedules) == 2, f"❌ Expected 2 schedules, got {len(schedules)}"
    print(f"✅ Weekly schedules added: {len(schedules)} days\n")

    # ==========================================
    # TEST 6: Free Slots
    # ==========================================
    print("📝 TEST 6: Free Slots")

    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    success = db.add_free_slot(test_phone, tomorrow, "14:00", "15:00")
    assert success, "❌ Failed to add free slot"

    free_slots = db.get_free_slots(test_phone)
    assert len(free_slots) >= 1, "❌ Free slot not found"
    print(f"✅ Free slot added for {tomorrow}\n")

    # ==========================================
    # TEST 7: Search Professionals
    # ==========================================
    print("📝 TEST 7: Search Professionals")

    # Add second professional
    db.add_professional(
        phone=test_phone2,
        name="Dra. Test Dos",
        email="test2@example.com",
        zone="norte",
        gender="f",
        accept_prepaga=True,
        especialidad="Psicóloga"
    )
    db.update_certificate(test_phone2, "certificates/test2/cert.pdf")

    # Search by zone
    results = db.search_professionals(zone="norte")
    assert len(results) >= 1, "❌ No results found for zona norte"
    print(f"✅ Search by zone: {len(results)} results\n")

    # Search by gender
    results = db.search_professionals(gender="f")
    assert len(results) >= 1, "❌ No results found for gender f"
    print(f"✅ Search by gender: {len(results)} results\n")

    # Search by prepaga
    results = db.search_professionals(accept_prepaga=True)
    assert len(results) >= 1, "❌ No results found with prepaga"
    print(f"✅ Search by prepaga: {len(results)} results\n")

    # ==========================================
    # TEST 8: Client Search Analytics
    # ==========================================
    print("📝 TEST 8: Client Search Analytics")

    client_phone = "+5491198765432"
    search_params = {"zone": "norte", "prepaga": True}

    search_id = db.log_client_search(
        client_phone=client_phone,
        search_type="zona",
        search_params=search_params,
        result_count=2,
        session_id="test_session_123"
    )
    assert search_id is not None, "❌ Failed to log search"
    print(f"✅ Search logged with ID: {search_id}\n")

    # Log contact
    success = db.log_professional_contact(
        search_id=search_id,
        professional_phone=test_phone,
        result_position=1
    )
    assert success, "❌ Failed to log contact"
    print("✅ Contact logged successfully\n")

    # Check professional metrics updated
    prof = db.get_professional(test_phone)
    assert prof['total_contacts'] >= 1, "❌ Contact count not updated"
    print(
        f"✅ Professional metrics updated: {prof['total_contacts']} contacts\n")

    # ==========================================
    # TEST 9: Database Stats
    # ==========================================
    print("📝 TEST 9: Database Stats")
    stats = db.get_stats()
    print(f"   Total Professionals: {stats['total_professionals']}")
    print(f"   Total Searches: {stats['total_searches']}")
    print(f"   Total Contacts: {stats['total_contacts']}")
    print(f"   Conversion Rate: {stats['conversion_rate']:.2f}%")
    print("✅ Stats retrieved successfully\n")

    # ==========================================
    # CLEANUP
    # ==========================================
    print("📝 Cleanup: Removing test database")
    import os
    if os.path.exists("test_database.db"):
        os.remove("test_database.db")
    print("✅ Test database removed\n")

    print("="*50)
    print("✅ ALL DATABASE TESTS PASSED!")
    print("="*50 + "\n")


if __name__ == "__main__":
    test_database()
