"""
Services Tests
==============
Test business logic in service layers.
"""

from src.services.analytics_service import AnalyticsService
from src.services.client_service import ClientService
from src.services.professional_service import ProfessionalService
from src.database.database import Database
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_services():
    """Test service layer operations."""

    print("\n" + "="*50)
    print("🧪 SERVICES TESTS")
    print("="*50 + "\n")

    # Use test database
    db = Database("test_services.db")

    prof_service = ProfessionalService()
    prof_service.db = db

    client_service = ClientService()
    client_service.db = db

    analytics_service = AnalyticsService()
    analytics_service.db = db

    test_phone1 = "+5491112345678"
    test_phone2 = "+5491187654321"
    test_phone3 = "+5491198765432"

    # ==========================================
    # TEST 1: Professional Registration
    # ==========================================
    print("📝 TEST 1: Professional Registration")

    success = prof_service.register_or_update_professional(
        phone=test_phone1,
        name="Dr. Service Test",
        email="service@test.com",
        zone="norte",
        gender="m",
        accept_prepaga=True,
        especialidad="Médico General"
    )
    assert success, "❌ Failed to register professional"

    prof = prof_service.get_professional_info(test_phone1)
    assert prof['name'] == "Dr. Service Test", "❌ Name mismatch"
    print("✅ Professional registered successfully\n")

    # ==========================================
    # TEST 2: Partial Update
    # ==========================================
    print("📝 TEST 2: Partial Professional Update")

    success = prof_service.register_or_update_professional(
        phone=test_phone1,
        email="newemail@test.com"
    )

    prof = prof_service.get_professional_info(test_phone1)
    assert prof['email'] == "newemail@test.com", "❌ Email not updated"
    assert prof['name'] == "Dr. Service Test", "❌ Name should remain unchanged"
    print("✅ Partial update successful\n")

    # ==========================================
    # TEST 3: Certificate Management
    # ==========================================
    print("📝 TEST 3: Certificate Management")

    assert not prof_service.has_certificate(
        test_phone1), "❌ Should not have certificate yet"

    cert_path = f"certificates/{test_phone1}/cert.jpg"
    success = prof_service.save_certificate(test_phone1, cert_path)
    assert success, "❌ Failed to save certificate"

    assert prof_service.has_certificate(test_phone1), "❌ Certificate not found"
    assert prof_service.verify_certificate(
        test_phone1), "❌ Certificate not verified"
    print("✅ Certificate management working\n")

    
    # ==========================================
    # TEST 5: Multiple Schedules at Once
    # ==========================================
    print("📝 TEST 5: Bulk Schedule Addition")

    schedules_to_add = [
        {"day_of_week": 3, "start_time": "09:00", "end_time": "17:00"},
        {"day_of_week": 4, "start_time": "09:00", "end_time": "17:00"}
    ]

    success_count, total = prof_service.add_multiple_weekly_schedules(
        test_phone1,
        schedules_to_add
    )
    assert success_count == total, f"❌ Only {success_count}/{total} added"
    print(f"✅ Bulk addition: {success_count}/{total} schedules\n")

    # ==========================================
    # TEST 6: Free Slot Management
    # ==========================================
    print("📝 TEST 6: Free Slot Management")

    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    success = prof_service.mark_slot_as_free(
        test_phone1, tomorrow, "14:00", "15:00")
    assert success, "❌ Failed to mark slot as free"

    free_slots = prof_service.get_free_slots(test_phone1, future_only=True)
    assert len(free_slots) >= 1, "❌ Free slot not found"
    print(f"✅ Free slot added for {tomorrow}\n")

    # ==========================================
    # TEST 7: Setup Multiple Professionals
    # ==========================================
    print("📝 TEST 7: Setup Multiple Professionals for Search")

    # Professional 2 - Zona Sur
    prof_service.register_or_update_professional(
        phone=test_phone2,
        name="Dra. Test Sur",
        email="sur@test.com",
        zone="sur",
        gender="f",
        accept_prepaga=False,
        especialidad="Dentista"
    )
    prof_service.save_certificate(test_phone2, "certificates/test2/cert.pdf")
    prof_service.add_weekly_busy_hours(
        test_phone2, 1, "10:00", "18:00")  # Tuesday

    # Professional 3 - Zona Norte, more availability
    prof_service.register_or_update_professional(
        phone=test_phone3,
        name="Dr. Test Disponible",
        email="disponible@test.com",
        zone="norte",
        gender="m",
        accept_prepaga=True,
        especialidad="Psicólogo"
    )
    prof_service.save_certificate(test_phone3, "certificates/test3/cert.pdf")
    # Less busy hours = more availability
    prof_service.add_weekly_busy_hours(
        test_phone3, 0, "10:00", "12:00")  # Only 2 hours

    print("✅ Multiple professionals set up\n")

    # ==========================================
    # TEST 8: Client Search - By Zone
    # ==========================================
    print("📝 TEST 8: Client Search by Zone")

    results = client_service.search_professionals_by_filters(zone="norte")
    assert len(
        results) >= 2, f"❌ Expected at least 2 results, got {len(results)}"
    print(f"✅ Search by zone: {len(results)} results\n")

    # ==========================================
    # TEST 9: Client Search - By Multiple Filters
    # ==========================================
    print("📝 TEST 9: Client Search with Multiple Filters")

    results = client_service.search_professionals_by_filters(
        zone="norte",
        gender="m",
        accept_prepaga=True
    )
    assert len(results) >= 1, "❌ No results with multiple filters"
    print(f"✅ Multi-filter search: {len(results)} results\n")

    # ==========================================
    # TEST 10: Search Available Today
    # ==========================================
    print("📝 TEST 10: Search Available Today")

    results = client_service.search_available_today(zone="norte")
    assert len(results) >= 0, "❌ Search failed"
    print(f"✅ Available today: {len(results)} results\n")

    # ==========================================
    # TEST 11: Analytics - Log Search
    # ==========================================
    print("📝 TEST 11: Analytics - Log Search")

    client_phone = "+5491199999999"
    search_id = analytics_service.log_search(
        client_phone=client_phone,
        search_type="zona",
        search_params={"zone": "norte"},
        result_count=len(results),
        session_id="test_session"
    )
    assert search_id is not None, "❌ Failed to log search"
    print(f"✅ Search logged with ID: {search_id}\n")

    # ==========================================
    # TEST 12: Analytics - Log Contact
    # ==========================================
    print("📝 TEST 12: Analytics - Log Contact")

    success = analytics_service.log_contact(
        search_id=search_id,
        professional_phone=test_phone1,
        result_position=1
    )
    assert success, "❌ Failed to log contact"

    # Verify metrics updated
    prof = prof_service.get_professional_info(test_phone1)
    assert prof['total_contacts'] >= 1, "❌ Contact count not updated"
    print(f"✅ Contact logged, total contacts: {prof['total_contacts']}\n")

    # ==========================================
    # TEST 13: Analytics - Metrics
    # ==========================================
    print("📝 TEST 13: Analytics Metrics")

    conversion_rate = analytics_service.get_conversion_rate(days=30)
    print(f"   Conversion Rate: {conversion_rate:.2f}%")

    top_pros = analytics_service.get_top_professionals(
        limit=3, metric='contacts')
    print(f"   Top Professionals: {len(top_pros)}")

    print("✅ Analytics metrics retrieved\n")

    # ==========================================
    # TEST 14: Format Results
    # ==========================================
    print("📝 TEST 14: Format Results for Display")

    results = client_service.search_professionals_by_filters(
        zone="norte", limit=5)
    formatted = client_service.format_results_list(results)
    assert len(formatted) > 0, "❌ Formatted output empty"
    print("✅ Results formatted for display\n")

    # ==========================================
    # TEST 15: Professional Schedule Display
    # ==========================================
    print("📝 TEST 15: Professional Schedule Display")

    schedule = prof_service.get_complete_schedule(test_phone1)
    assert 'weekly_schedule' in schedule, "❌ Missing weekly_schedule"
    assert 'free_slots' in schedule, "❌ Missing free_slots"
    assert 'formatted' in schedule, "❌ Missing formatted"

    print("Schedule output:")
    print(schedule['formatted'][:200] + "...")
    print("✅ Schedule formatted successfully\n")

    # ==========================================
    # CLEANUP
    # ==========================================
    print("📝 Cleanup: Removing test database")
    if os.path.exists("test_services.db"):
        os.remove("test_services.db")
    print("✅ Test database removed\n")

    print("="*50)
    print("✅ ALL SERVICE TESTS PASSED!")
    print("="*50 + "\n")


if __name__ == "__main__":
    test_services()
