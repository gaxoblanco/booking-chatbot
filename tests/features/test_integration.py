"""
Integration Tests
=================
Test complete user flows simulating real WhatsApp conversations.
Tests the entire stack: bot.py + services + database.
"""

from src.services.analytics_service import AnalyticsService
from src.services.client_service import ClientService
from src.services.professional_service import ProfessionalService
from src.core.states import session_manager, ConversationState, UserRole
from src.bot.bot import Bot
from src.database.database import Database
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class IntegrationTest:
    """Integration test suite for complete user flows."""

    def __init__(self):
        """Initialize test environment."""
        self.db = Database("test_integration.db")
        self.bot = Bot()

        # Override services to use test database
        from src.services.professional_service import professional_service
        from src.services.client_service import client_service
        from src.services.analytics_service import analytics_service

        professional_service.db = self.db
        client_service.db = self.db
        analytics_service.db = self.db

        self.test_prof_phone = "+5491112345678"
        self.test_client_phone = "+5491198765432"

    # ==========================================
    # SETUP: CREATE TEST PROFESSIONALS
    # ==========================================

    def setup_test_professionals(self):
        """Create test professionals in database for client searches."""
        self.print_section("SETUP: Creating Test Professionals")

        from src.services.professional_service import professional_service

        # Professional 1 - Zona Norte, con prepaga
        prof1_phone = "+5491111111111"
        professional_service.register_or_update_professional(
            phone=prof1_phone,
            name="Dr. Test Norte",
            email="norte@test.com",
            zone="norte",
            gender="m",
            accept_prepaga=True,
            especialidad="Médico General"
        )
        professional_service.save_certificate(
            prof1_phone, f"certificates/{prof1_phone}/cert.jpg")
        professional_service.add_weekly_busy_hours(
            prof1_phone, 0, "09:00", "17:00")  # Lunes
        print(f"✅ Created: Dr. Test Norte (zona norte, prepaga)")

        # Professional 2 - Zona Sur, sin prepaga
        prof2_phone = "+5491122222222"
        professional_service.register_or_update_professional(
            phone=prof2_phone,
            name="Dra. Test Sur",
            email="sur@test.com",
            zone="sur",
            gender="f",
            accept_prepaga=False,
            especialidad="Dentista"
        )
        professional_service.save_certificate(
            prof2_phone, f"certificates/{prof2_phone}/cert.pdf")
        professional_service.add_weekly_busy_hours(
            prof2_phone, 1, "10:00", "18:00")  # Martes
        print(f"✅ Created: Dra. Test Sur (zona sur, sin prepaga)")

        # Professional 3 - Zona Norte, sin prepaga, más disponible
        prof3_phone = "+5491133333333"
        professional_service.register_or_update_professional(
            phone=prof3_phone,
            name="Dr. Test Disponible",
            email="disponible@test.com",
            zone="norte",
            gender="m",
            accept_prepaga=False,
            especialidad="Psicólogo"
        )
        professional_service.save_certificate(
            prof3_phone, f"certificates/{prof3_phone}/cert.jpg")
        professional_service.add_weekly_busy_hours(
            prof3_phone, 0, "10:00", "12:00")  # Solo 2 horas
        print(f"✅ Created: Dr. Test Disponible (zona norte, sin prepaga, muy disponible)")

        # Marcar un slot libre para mañana
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        professional_service.mark_slot_as_free(
            prof1_phone, tomorrow, "14:00", "15:00")
        print(f"✅ Free slot marked for tomorrow")

        print("\n✅ Test professionals created successfully\n")

    def cleanup(self):
        """Clean up test environment."""
        session_manager.delete_session(self.test_prof_phone)
        session_manager.delete_session(self.test_client_phone)
        if os.path.exists("test_integration.db"):
            os.remove("test_integration.db")

    def send_message(self, phone: str, message: str) -> str:
        """Simulate sending a message to the bot."""
        return self.bot.process_message(phone, message)

    def assert_contains(self, text: str, expected: str, error_msg: str):
        """Assert that text contains expected string."""
        # 🔍 DEBUG: Ver el texto completo
        print(f"\n🔍 DEBUG - Buscando: '{expected}'")
        print(f"🔍 DEBUG - En texto (primeros 300 chars):")
        print(f"{text[:300]}")
        print(
            f"🔍 DEBUG - ¿Contiene '{expected.lower()}'? {expected.lower() in text.lower()}")

        if expected.lower() not in text.lower():
            print(f"\n❌ ASSERTION FAILED: {error_msg}")
            print(f"Expected to find: '{expected}'")
            print(f"In text: {text[:200]}...")
            raise AssertionError(error_msg)

    def print_section(self, title: str):
        """Print test section header."""
        print(f"\n{'='*60}")
        print(f"📝 {title}")
        print('='*60)

    def print_message(self, sender: str, message: str, response: str):
        """Print message exchange."""
        print(f"\n👤 {sender}: {message}")
        print(f"🤖 Bot: {response[:150]}...")

    # ==========================================
    # TEST 1: PROFESSIONAL REGISTRATION FLOW
    # ==========================================

    def test_professional_registration(self):
        """Test complete professional registration flow."""
        self.print_section("TEST 1: Professional Registration Flow")

        phone = self.test_prof_phone

        # Step 1: Start conversation
        response = self.send_message(phone, "Hola")
        self.assert_contains(response, "profesional",
                             "Should show role selection")
        self.print_message(phone, "Hola", response)

        # Step 2: Select professional role
        response = self.send_message(phone, "1")
        self.assert_contains(response, "certificado",
                             "Should ask for certificate")
        self.print_message(phone, "1", response)

        # Step 3: Simulate certificate upload (in real flow, this happens via media)
        # For testing, we'll manually save certificate
        from src.services.professional_service import professional_service
        professional_service.save_certificate(
            phone, f"certificates/{phone}/test_cert.jpg")

        # Manually transition state (simulating successful upload)
        session = session_manager.get_session(phone)
        session.transition_to(ConversationState.PROF_MAIN_MENU)

        # Step 4: Get professional menu
        response = self.send_message(phone, "menu")
        self.assert_contains(response, "Menú Profesional",
                             "Should show professional menu")
        self.print_message(phone, "menu", response)

        print("\n✅ Professional registration flow completed")

    # ==========================================
    # TEST 2: PROFESSIONAL LOAD INFO (STEP BY STEP)
    # ==========================================

    def test_professional_load_info_step_by_step(self):
        """Test loading professional info step by step."""
        self.print_section("TEST 2: Professional Info - Step by Step")

        phone = self.test_prof_phone

        # Ensure we're at main menu
        session = session_manager.get_session(phone)
        session.transition_to(ConversationState.PROF_MAIN_MENU)

        # Step 1: Enter info menu
        response = self.send_message(phone, "5")
        self.assert_contains(response, "Cargar Información",
                             "Should show info menu")
        self.print_message(phone, "5 (Cargar Información)", response)

        # Step 2: Set name
        response = self.send_message(phone, "1")
        self.assert_contains(response, "nombre", "Should ask for name")
        response = self.send_message(phone, "Dr. Juan Pérez")
        self.assert_contains(response, "guardad", "Should confirm name saved")
        self.print_message(phone, "Dr. Juan Pérez", response)

        # Step 3: Set email
        response = self.send_message(phone, "2")
        self.assert_contains(response, "email", "Should ask for email")
        response = self.send_message(phone, "juan.perez@test.com")
        self.assert_contains(response, "guardad",
                             "Should confirm email saved")
        self.print_message(phone, "juan.perez@test.com", response)

        # Step 4: Set zona
        response = self.send_message(phone, "3")
        self.assert_contains(response, "zona", "Should ask for zone")
        response = self.send_message(phone, "1")  # Norte
        self.assert_contains(response, "norte", "Should confirm zone saved")
        self.print_message(phone, "1 (Norte)", response)

        # Step 5: Set gender
        response = self.send_message(phone, "4")
        self.assert_contains(response, "género", "Should ask for gender")
        response = self.send_message(phone, "1")  # Masculino
        self.assert_contains(response, "Masculino",
                             "Should confirm gender saved")
        self.print_message(phone, "1 (Masculino)", response)

        # Step 6: Set prepaga
        response = self.send_message(phone, "5")
        self.assert_contains(response, "prepaga", "Should ask for prepaga")
        response = self.send_message(phone, "1")  # Sí
        self.assert_contains(response, "Sí", "Should confirm prepaga saved")
        self.print_message(phone, "1 (Sí)", response)

        # Step 7: Set especialidad
        response = self.send_message(phone, "6")
        self.assert_contains(response, "especialidad",
                             "Should ask for especialidad")
        response = self.send_message(phone, "1")  # Médico General
        self.assert_contains(response, "guardad",
                             "Should confirm especialidad saved")
        self.print_message(phone, "1 (Médico General)", response)

        # Step 8: Save all info
        response = self.send_message(phone, "9")
        self.assert_contains(response, "guardada", "Should confirm info saved")
        self.print_message(phone, "9 (Guardar)", response)

        # Verify in database
        from src.services.professional_service import professional_service
        prof = professional_service.get_professional_info(phone)
        assert prof['name'] == "Dr. Juan Pérez", "Name not saved in DB"
        assert prof['email'] == "juan.perez@test.com", "Email not saved in DB"
        assert prof['zone'] == "norte", "Zone not saved in DB"

        print("\n✅ Professional info loaded step by step")

    # ==========================================
    # TEST 3: PROFESSIONAL LOAD WEEKLY SCHEDULE
    # ==========================================

    def test_professional_load_weekly_schedule(self):
        """Test loading weekly schedule."""
        self.print_section("TEST 3: Professional Weekly Schedule")

        phone = self.test_prof_phone

        # Go to main menu
        session = session_manager.get_session(phone)
        session.transition_to(ConversationState.PROF_MAIN_MENU)

        # Step 1: Select weekly schedule option
        response = self.send_message(phone, "3")
        self.assert_contains(response, "día", "Should ask for day")
        self.print_message(phone, "3 (Cargar Semana)", response)

        # Step 2: Select Monday
        response = self.send_message(phone, "1")
        self.assert_contains(response, "Lunes", "Should ask for Monday hours")
        self.print_message(phone, "1 (Lunes)", response)

        # Step 3: Set hours 9-17
        response = self.send_message(phone, "09:00-17:00")
        self.assert_contains(response, "configurado", "Should confirm hours")
        self.print_message(phone, "09:00-17:00", response)

        # Step 4: Add another day
        response = self.send_message(phone, "1")  # Sí, agregar otro
        self.assert_contains(response, "día", "Should ask for another day")

        # Step 5: Select Wednesday
        response = self.send_message(phone, "3")
        self.assert_contains(response, "Miércoles",
                             "Should ask for Wednesday hours")

        # Step 6: Set hours 10-18
        response = self.send_message(phone, "10:00-18:00")
        self.assert_contains(response, "configurado", "Should confirm hours")

        # Step 7: Finish
        response = self.send_message(phone, "2")  # No, finalizar
        self.assert_contains(response, "Semana configurada",
                             "Should confirm schedule saved")
        self.print_message(phone, "2 (Finalizar)", response)

        # Verify in database
        from src.services.professional_service import professional_service
        schedules = professional_service.get_weekly_schedule(phone)
        assert len(
            schedules) >= 2, f"Expected at least 2 schedules, got {len(schedules)}"

        print("\n✅ Weekly schedule loaded successfully")

    # ==========================================
    # TEST 4: PROFESSIONAL MARK FREE SLOT
    # ==========================================

    def test_professional_mark_free_slot(self):
        """Test marking a specific slot as free."""
        self.print_section("TEST 4: Professional Mark Free Slot")

        phone = self.test_prof_phone

        # Go to main menu
        session = session_manager.get_session(phone)
        session.transition_to(ConversationState.PROF_MAIN_MENU)

        # Step 1: Select free slot option
        response = self.send_message(phone, "1")
        self.assert_contains(response, "día", "Should ask for date")
        self.print_message(phone, "1 (Liberar Horario)", response)

        # Step 2: Enter date (tomorrow)
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")
        response = self.send_message(phone, tomorrow)
        self.assert_contains(response, "horario", "Should ask for time")
        self.print_message(phone, tomorrow, response)

        # Step 3: Enter time range
        response = self.send_message(phone, "14:00-15:00")
        self.assert_contains(response, "Confirmar",
                             "Should ask for confirmation")
        self.print_message(phone, "14:00-15:00", response)

        # Step 4: Confirm
        response = self.send_message(phone, "1")
        self.assert_contains(response, "liberado", "Should confirm slot freed")
        self.print_message(phone, "1 (Confirmar)", response)

        # Verify in database
        from src.services.professional_service import professional_service
        free_slots = professional_service.get_free_slots(phone)
        assert len(free_slots) >= 1, "Free slot not saved"

        print("\n✅ Free slot marked successfully")

    # ==========================================
    # TEST 5: CLIENT SEARCH BY ZONE
    # ==========================================

    def test_client_search_by_zone(self):
        """Test client searching professionals by zone."""
        self.print_section("TEST 5: Client Search by Zone")

        phone = self.test_client_phone

        # Step 1: Start conversation
        response = self.send_message(phone, "Hola")
        self.assert_contains(response, "cliente", "Should show role selection")
        self.print_message(phone, "Hola", response)

        # Step 2: Select client role
        response = self.send_message(phone, "2")
        self.assert_contains(response, "Menú Cliente",
                             "Should show client menu")
        self.print_message(phone, "2 (Cliente)", response)

        # Step 3: Search by zone norte
        response = self.send_message(phone, "4")  # Zona Norte
        self.assert_contains(response, "profesional", "Should show results")
        self.print_message(phone, "4 (Zona Norte)", response)

        # Verify results contain our test professional
        session = session_manager.get_session(phone)
        results = session.get_temp('search_results', [])
        assert len(results) >= 1, "Should find at least 1 professional"

        # Check that search was logged in analytics
        from src.services.analytics_service import analytics_service
        search_id = session.get_temp('current_search_id')
        assert search_id is not None, "Search should be logged"

        print(f"\n✅ Client search completed: {len(results)} results found")

    # ==========================================
    # TEST 6: CLIENT VIEW PROFESSIONAL DETAIL
    # ==========================================

    def test_client_view_detail_and_contact(self):
        """Test client viewing professional detail and contacting."""
        self.print_section("TEST 6: Client View Detail & Contact")

        phone = self.test_client_phone

        # Ensure we have search results
        session = session_manager.get_session(phone)
        results = session.get_temp('search_results', [])

        if len(results) == 0:
            print("⚠️  No results from previous test, running search first...")
            self.test_client_search_by_zone()
            session = session_manager.get_session(phone)
            results = session.get_temp('search_results', [])

        assert len(results) >= 1, "Need at least 1 result to test detail view"

        # Step 1: Select first professional
        response = self.send_message(phone, "1")
        self.assert_contains(response, "Contacto",
                             "Should show professional detail")
        self.print_message(phone, "1 (Ver primer profesional)", response)

        # Step 2: Contact professional
        response = self.send_message(phone, "1")
        self.assert_contains(response, "registrado", "Should confirm contact")
        self.print_message(phone, "1 (Contactar)", response)

        # Verify contact was logged
        from src.services.professional_service import professional_service
        prof = professional_service.get_professional_info(self.test_prof_phone)
        assert prof['total_contacts'] >= 1, "Contact should be logged"

        print("\n✅ Client viewed detail and contacted professional")

    # ==========================================
    # TEST 7: CLIENT ADVANCED SEARCH
    # ==========================================

    def test_client_advanced_search(self):
        """Test client advanced search with multiple filters."""
        self.print_section("TEST 7: Client Advanced Search")

        phone = self.test_client_phone

        # Go to main menu
        session = session_manager.get_session(phone)
        session.transition_to(ConversationState.CLIENT_MAIN_MENU)

        # Step 1: Enter advanced search
        response = self.send_message(phone, "2")
        self.assert_contains(response, "Búsqueda Avanzada",
                             "Should show filter menu")
        self.print_message(phone, "2 (Búsqueda Avanzada)", response)

        # Step 2: Add zone filter
        response = self.send_message(phone, "1")
        self.assert_contains(response, "zona", "Should ask for zone")
        response = self.send_message(phone, "1")  # Norte
        self.assert_contains(response, "activos", "Should show active filters")
        self.print_message(phone, "1 (Zona Norte)", response)

        # Step 3: Add prepaga filter
        response = self.send_message(phone, "3")
        self.assert_contains(response, "prepaga", "Should ask for prepaga")
        response = self.send_message(phone, "1")  # Sí
        self.assert_contains(response, "activos", "Should show active filters")
        self.print_message(phone, "1 (Con prepaga)", response)

        # Step 4: Execute search
        response = self.send_message(phone, "9")
        self.assert_contains(response, "profesional", "Should show results")
        self.print_message(phone, "9 (Buscar)", response)

        # Verify results
        results = session.get_temp('search_results', [])
        assert len(
            results) >= 1, "Should find at least 1 professional with filters"

        print(f"\n✅ Advanced search completed: {len(results)} results")

    # ==========================================
    # TEST 8: ANALYTICS VERIFICATION
    # ==========================================

    def test_analytics_data(self):
        """Verify analytics data is being tracked correctly."""
        self.print_section("TEST 8: Analytics Verification")

        from src.services.analytics_service import analytics_service

        # Get stats
        stats = self.db.get_stats()
        print(f"\n📊 Database Stats:")
        print(f"   Professionals: {stats['total_professionals']}")
        print(f"   Searches: {stats['total_searches']}")
        print(f"   Contacts: {stats['total_contacts']}")
        print(f"   Conversion Rate: {stats['conversion_rate']:.2f}%")

        assert stats['total_professionals'] >= 1, "Should have at least 1 professional"
        assert stats['total_searches'] >= 1, "Should have at least 1 search"
        assert stats['total_contacts'] >= 1, "Should have at least 1 contact"

        # Get professional stats
        prof_stats = analytics_service.get_professional_stats(
            self.test_prof_phone)
        print(f"\n📊 Professional Stats:")
        print(f"   Views: {prof_stats['total_views']}")
        print(f"   Profile Views: {prof_stats['total_profile_views']}")
        print(f"   Contacts: {prof_stats['total_contacts']}")

        assert prof_stats['total_contacts'] >= 1, "Professional should have contacts"

        print("\n✅ Analytics data verified")

    # ==========================================
    # RUN ALL TESTS
    # ==========================================

    def run_all_tests(self):
        """Run all integration tests."""
        print("\n" + "="*60)
        print("🚀 STARTING INTEGRATION TESTS")
        print("="*60)

        try:
            self.test_professional_registration()
            self.test_professional_load_info_step_by_step()
            self.test_professional_load_weekly_schedule()
            self.test_professional_mark_free_slot()
            # Crear profesionales adicionales para búsquedas de clientes
            self.setup_test_professionals()

            self.test_client_search_by_zone()
            self.test_client_view_detail_and_contact()
            self.test_client_advanced_search()
            self.test_analytics_data()

            print("\n" + "="*60)
            print("✅ ALL INTEGRATION TESTS PASSED!")
            print("="*60 + "\n")

        except Exception as e:
            print(f"\n❌ TEST FAILED: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

        finally:
            print("\n🧹 Cleaning up test environment...")
            self.cleanup()
            print("✅ Cleanup complete\n")


if __name__ == "__main__":
    test = IntegrationTest()
    test.run_all_tests()
