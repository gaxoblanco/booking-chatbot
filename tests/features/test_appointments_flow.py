#!/usr/bin/env python3
"""
Appointment Flow Testing Script
=================================
Test interactivo específico para el flujo de citas/appointments.

Escenarios disponibles:
1. Cliente reserva cita
2. Cliente ve sus citas
3. Cliente cancela cita
4. Cliente reprograma cita
5. Profesional ve citas
6. Profesional confirma/rechaza cita
7. Profesional marca cita como completada

Usage:
    python test_appointments_flow.py                    # Interactive menu
    python test_appointments_flow.py --scenario booking # Client booking
    python test_appointments_flow.py --scenario manage  # Client management
    python test_appointments_flow.py --scenario prof    # Professional view
"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from datetime import datetime, date, timedelta
from src.core.states import session_manager, ConversationState
from src.bot.bot_controller import bot_controller
from src.database.database import db

# Add parent directory to path
# sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class AppointmentTester:
    """Interactive appointment flow tester."""

    def __init__(self):
        """Initialize tester."""
        self.client_phone = "+5491123456789"  # Cliente de prueba
        self.prof_phone = "+5491112345678"    # Profesional de prueba
        self.message_count = 0

    def print_header(self, text):
        """Print colored header."""
        print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}")
        print(f"  {text}")
        print(f"{'='*60}{Colors.ENDC}\n")

    def print_bot_response(self, response):
        """Print bot response in color."""
        self.message_count += 1
        print(f"\n{Colors.OKBLUE}[BOT #{self.message_count}]{Colors.ENDC}")
        print(f"{Colors.OKCYAN}{response}{Colors.ENDC}\n")

    def print_user_message(self, message, phone):
        """Print user message."""
        role = "CLIENT" if phone == self.client_phone else "PROFESSIONAL"
        print(f"{Colors.OKGREEN}[{role}] → {message}{Colors.ENDC}")

    def send_message(self, message, phone=None):
        """
        Send message and get response.

        Args:
            message: Message text
            phone: Phone number (defaults to client_phone)

        Returns:
            Bot response
        """
        if phone is None:
            phone = self.client_phone

        self.print_user_message(message, phone)
        response = bot_controller.process_message(phone, message)
        self.print_bot_response(response)
        return response

    def show_session_info(self, phone):
        """Show current session state."""
        session = session_manager.get_session(phone)
        print(f"\n{Colors.WARNING}[SESSION INFO]{Colors.ENDC}")
        print(f"  Phone: {phone}")
        print(f"  Role: {session.role.value}")
        print(f"  State: {session.state.value}")
        if session.temp_data:
            print(f"  Temp Data: {list(session.temp_data.keys())}")
        print()

    # ==========================================
    # SETUP HELPERS
    # ==========================================

    def setup_test_professional(self):
        """Create a test professional with availability."""
        print(f"{Colors.WARNING}Setting up test professional...{Colors.ENDC}")

        # Add professional
        db.add_professional(
            phone=self.prof_phone,
            name="Dr. Test Professional",
            email="test@example.com",
            zone="norte",
            gender="m",
            accept_prepaga=True,
            category="Psicología"
        )

        # Add certificate
        db.update_certificate(self.prof_phone, "certificates/test/cert.jpg")

        # Add weekly schedule (ocupado lunes a viernes 9-17)
        for day in range(1, 6):  # Lunes a viernes
            db.add_weekly_schedule(self.prof_phone, day, "09:00", "17:00")

        # Add some free slots for tomorrow and the day after
        tomorrow = date.today() + timedelta(days=1)
        day_after = date.today() + timedelta(days=2)

        db.add_free_slot(self.prof_phone, tomorrow.strftime(
            "%Y-%m-%d"), "10:00", "11:00")
        db.add_free_slot(self.prof_phone, tomorrow.strftime(
            "%Y-%m-%d"), "14:00", "15:00")
        db.add_free_slot(self.prof_phone, day_after.strftime(
            "%Y-%m-%d"), "11:00", "12:00")

        print(f"{Colors.OKGREEN}✅ Professional setup complete{Colors.ENDC}")
        print(f"   Name: Dr. Test Professional")
        print(f"   Phone: {self.prof_phone}")
        print(
            f"   Available slots: {tomorrow.strftime('%d/%m/%Y')} 10:00, 14:00")
        print(f"                    {day_after.strftime('%d/%m/%Y')} 11:00\n")

    def setup_test_appointment(self):
        """Create a test appointment for testing management."""
        # Usar timestamp para evitar conflictos
        import random

        tomorrow = date.today() + timedelta(days=1)

        # Hora aleatoria para evitar UNIQUE constraint
        hours = random.choice(["10", "11", "14", "15", "16"])
        minutes = random.choice(["00", "15", "30", "45"])
        start_time = f"{hours}:{minutes}"

        # Calcular end_time (1 hora después)
        end_hour = int(hours) + 1
        end_time = f"{end_hour:02d}:{minutes}"

        # Create client first
        db.add_client(
            phone=self.client_phone,
            name="Test Client",
            email="client@test.com"
        )

        # Create appointment
        appointment_id = db.create_appointment(
            client_phone=self.client_phone,
            professional_phone=self.prof_phone,
            appointment_date=tomorrow.strftime("%Y-%m-%d"),
            start_time=start_time,
            end_time=end_time,
            modality="presencial"
        )

        print(
            f"{Colors.OKGREEN}✅ Test appointment created (ID: {appointment_id}){Colors.ENDC}")
        print(f"   Date: {tomorrow.strftime('%d/%m/%Y')} at {start_time}\n")

        return appointment_id

    # ==========================================
    # TEST SCENARIOS
    # ==========================================

    def test_client_booking_flow(self):
        """Test complete client booking flow."""
        self.print_header("TEST: Cliente Reserva Cita")

        # Setup
        self.setup_test_professional()

        # Start as client
        print(f"{Colors.BOLD}Step 1: Iniciar como cliente{Colors.ENDC}")
        self.send_message("hola", self.client_phone)
        self.send_message("2")  # Cliente

        # Search for professional
        print(f"\n{Colors.BOLD}Step 2: Buscar profesional{Colors.ENDC}")
        self.send_message("1")  # Buscar para hoy o búsqueda

        # This is where you continue the flow based on your menu structure
        print(f"\n{Colors.WARNING}⚠️  Continue the flow manually...{Colors.ENDC}")
        print(f"Next steps:")
        print(f"  1. Search for professional")
        print(f"  2. View professional detail")
        print(f"  3. Select 'Agendar cita' option")
        print(f"  4. Follow booking steps")

        self.show_session_info(self.client_phone)

    def test_client_view_appointments(self):
        """Test client viewing their appointments."""
        self.print_header("TEST: Cliente Ve Sus Citas")

        # Setup
        self.setup_test_professional()
        appointment_id = self.setup_test_appointment()

        # Start as client
        self.send_message("hola", self.client_phone)
        self.send_message("2")  # Cliente

        # Go to appointments (need to know your menu structure)
        print(f"\n{Colors.WARNING}⚠️  Navigate to 'Mis Citas' option{Colors.ENDC}")
        print(f"Then you should see appointment ID: {appointment_id}")

        self.show_session_info(self.client_phone)

    def test_professional_view_appointments(self):
        """Test professional viewing appointments."""
        self.print_header("TEST: Profesional Ve Citas")

        # Setup
        self.setup_test_professional()
        appointment_id = self.setup_test_appointment()

        # Change default phone to professional
        original_client = self.client_phone
        self.client_phone = self.prof_phone  # Temporary change

        # Start as professional
        self.send_message("hola")  # Ahora usa prof_phone

        # Navigate to Mis Citas (opción 6)
        print(f"\n{Colors.BOLD}Step 2: Navegar a Mis Citas{Colors.ENDC}")
        self.send_message("6")  # Ahora usa prof_phone

        print(f"\n{Colors.WARNING}Expected: Lista de citas{Colors.ENDC}")
        print(f"Should see appointment ID: {appointment_id}")

        # Restore
        self.client_phone = original_client

        self.show_session_info(self.prof_phone)

    def test_interactive_mode(self):
        """Interactive testing mode - send messages manually."""
        self.print_header("MODO INTERACTIVO - Testing de Citas")

        print(f"{Colors.WARNING}Setup Options:{Colors.ENDC}")
        print("1. Setup test professional with availability")
        print("2. Setup test appointment")
        print("3. Skip setup")

        choice = input("\nChoose setup (1-3): ").strip()

        if choice == "1":
            self.setup_test_professional()
        elif choice == "2":
            self.setup_test_professional()
            self.setup_test_appointment()

        print(f"\n{Colors.OKGREEN}Phones for testing:{Colors.ENDC}")
        print(f"  Client: {self.client_phone}")
        print(f"  Professional: {self.prof_phone}")

        print(f"\n{Colors.BOLD}Select role to test:{Colors.ENDC}")
        print("1. Test as CLIENT")
        print("2. Test as PROFESSIONAL")

        role_choice = input("\nChoose role (1-2): ").strip()
        test_phone = self.client_phone if role_choice == "1" else self.prof_phone
        role_name = "CLIENT" if role_choice == "1" else "PROFESSIONAL"

        print(f"\n{Colors.HEADER}Testing as {role_name}{Colors.ENDC}")
        print(f"Phone: {test_phone}")
        print(f"\nCommands:")
        print(f"  Type your message and press Enter")
        print(f"  'info' - Show session info")
        print(f"  'switch' - Switch to other role")
        print(f"  'quit' - Exit")
        print(f"\n{Colors.WARNING}{'='*60}{Colors.ENDC}\n")

        # Start conversation
        self.send_message("hola", test_phone)

        # Interactive loop
        while True:
            try:
                user_input = input(
                    f"\n{Colors.OKGREEN}[{role_name}] > {Colors.ENDC}").strip()

                if not user_input:
                    continue

                if user_input.lower() == 'quit':
                    print(f"\n{Colors.WARNING}Exiting...{Colors.ENDC}\n")
                    break

                if user_input.lower() == 'info':
                    self.show_session_info(test_phone)
                    continue

                if user_input.lower() == 'switch':
                    test_phone = self.prof_phone if test_phone == self.client_phone else self.client_phone
                    role_name = "PROFESSIONAL" if test_phone == self.prof_phone else "CLIENT"
                    print(
                        f"\n{Colors.WARNING}Switched to {role_name}{Colors.ENDC}")
                    self.show_session_info(test_phone)
                    continue

                # Send message
                self.send_message(user_input, test_phone)

            except KeyboardInterrupt:
                print(
                    f"\n\n{Colors.WARNING}Interrupted. Exiting...{Colors.ENDC}\n")
                break
            except Exception as e:
                print(f"\n{Colors.FAIL}ERROR: {e}{Colors.ENDC}\n")

    def run_menu(self):
        """Show interactive menu."""
        self.print_header("APPOINTMENT FLOW TESTER")

        print("Select test scenario:\n")
        print("1. Client Booking Flow (automated)")
        print("2. Client View Appointments (automated)")
        print("3. Professional View Appointments (automated)")
        print("4. Interactive Mode (manual testing)")
        print("0. Exit")

        choice = input("\nChoice: ").strip()

        if choice == "1":
            self.test_client_booking_flow()
        elif choice == "2":
            self.test_client_view_appointments()
        elif choice == "3":
            self.test_professional_view_appointments()
        elif choice == "4":
            self.test_interactive_mode()
        elif choice == "0":
            print("\nExiting...\n")
            return
        else:
            print(f"\n{Colors.FAIL}Invalid choice{Colors.ENDC}\n")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Test appointment flows')
    parser.add_argument('--scenario', choices=['booking', 'manage', 'prof', 'interactive'],
                        help='Test scenario to run')

    args = parser.parse_args()

    tester = AppointmentTester()

    if args.scenario == 'booking':
        tester.test_client_booking_flow()
    elif args.scenario == 'manage':
        tester.test_client_view_appointments()
    elif args.scenario == 'prof':
        tester.test_professional_view_appointments()
    elif args.scenario == 'interactive':
        tester.test_interactive_mode()
    else:
        # No scenario specified, show menu
        tester.run_menu()


if __name__ == "__main__":
    main()
