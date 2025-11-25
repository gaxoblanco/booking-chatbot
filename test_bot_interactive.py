#!/usr/bin/env python3
"""
Bot Interactive Testing Script
================================
Simulates WhatsApp conversations for testing without sending real messages.

Usage:
    python test_bot_interactive.py                    # Interactive mode
    python test_bot_interactive.py --scenario client  # Client flow
    python test_bot_interactive.py --scenario professional  # Professional flow
"""

import argparse
from datetime import datetime
from states import session_manager, ConversationState
from bot import bot
import sys
import os
from professional_service import professional_service
from database import db

# Add parent directory to path to import bot modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


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


class BotTester:
    """Interactive bot testing simulator."""

    def __init__(self, test_phone="+5491112345678"):
        """
        Initialize bot tester.

        Args:
            test_phone: Phone number to use for testing
        """
        self.test_phone = test_phone
        self.message_count = 0
        self.session = session_manager.get_session(test_phone)

    def print_header(self):
        """Print welcome header."""
        print("\n" + "="*70)
        print(
            f"{Colors.HEADER}{Colors.BOLD}🤖 PSIVALE BOT - INTERACTIVE TESTER{Colors.ENDC}")
        print("="*70)
        print(f"{Colors.OKCYAN}Test Phone: {self.test_phone}{Colors.ENDC}")
        print(f"{Colors.OKCYAN}Session State: {self.session.state}{Colors.ENDC}")
        print("="*70 + "\n")

    def print_bot_response(self, response: str):
        """Print bot response with formatting."""
        self.message_count += 1
        print(
            f"\n{Colors.OKGREEN}{Colors.BOLD}🤖 BOT (Message #{self.message_count}):{Colors.ENDC}")
        print(f"{Colors.OKGREEN}{response}{Colors.ENDC}")
        print(f"\n{Colors.OKCYAN}[State: {self.session.state}]{Colors.ENDC}")

    def print_user_input(self, message: str):
        """Print user input with formatting."""
        print(f"\n{Colors.OKBLUE}{Colors.BOLD}👤 YOU:{Colors.ENDC} {message}")

    def send_message(self, message: str, show_input=True):
        """
        Send a message to the bot and get response.

        Args:
            message: Message text to send
            show_input: Whether to print the input

        Returns:
            Bot response
        """
        if show_input:
            self.print_user_input(message)

        response = bot.process_message(self.test_phone, message)
        self.print_bot_response(response)

        return response

    def send_image(self, filename="test_certificate.jpg"):
        """
        Simulate sending an image (for certificate upload).

        Esta función simula la carga de una imagen creando:
        1. Un archivo físico simulado en el sistema
        2. La actualización en la base de datos
        3. El procesamiento del bot como si hubiera recibido una imagen real

        Args:
            filename: Filename to simulate (default: test_certificate.jpg)
        """
        print(
            f"\n{Colors.WARNING}📎 Simulating image upload: {filename}{Colors.ENDC}")

        # Paso 1: Crear el directorio de certificados si no existe
        cert_dir = f"certificates/{self.test_phone}"
        os.makedirs(cert_dir, exist_ok=True)

        # Paso 2: Crear un archivo simulado
        fake_path = f"{cert_dir}/{filename}"
        with open(fake_path, 'w') as f:
            f.write(
                f"MOCK CERTIFICATE FOR TESTING\nPhone: {self.test_phone}\nTimestamp: {datetime.now()}")

        print(f"{Colors.OKCYAN}  📁 Created mock file: {fake_path}{Colors.ENDC}")

        # Paso 3: Verificar el estado actual
        current_state = self.session.state
        print(f"{Colors.OKCYAN}  📊 Current state: {current_state}{Colors.ENDC}")

        # Paso 4: Actualizar certificado en la base de datos
        success = professional_service.save_certificate(
            self.test_phone, fake_path)

        if success:
            print(
                f"{Colors.OKGREEN}  ✅ Certificate path saved to database{Colors.ENDC}")

            # Paso 5: Si estamos en PROF_NEED_CERTIFICATE, cambiar estado manualmente
            # y procesar el siguiente paso
            if current_state == ConversationState.PROF_NEED_CERTIFICATE:
                # Cambiar estado a PROF_INFO_NAME
                self.session.state = ConversationState.PROF_INFO_NAME
                print(
                    f"{Colors.OKCYAN}  🔄 State changed: PROF_NEED_CERTIFICATE → PROF_INFO_NAME{Colors.ENDC}")

                # Obtener el mensaje de bienvenida para el siguiente paso
                from messages import Messages
                response = Messages.PROF_INFO_ASK_NAME
                self.print_bot_response(response)
            else:
                # Si no estamos en el estado esperado, mostrar advertencia
                print(
                    f"{Colors.WARNING}  ⚠️  Warning: Not in PROF_NEED_CERTIFICATE state{Colors.ENDC}")
                # Intentar procesar un mensaje para ver qué pasa
                response = bot.process_message(
                    self.test_phone, "[imagen recibida]")
                self.print_bot_response(response)
        else:
            print(
                f"{Colors.FAIL}❌ Failed to save certificate to database{Colors.ENDC}")

    def _get_input(self, prompt: str, default: str = None) -> str:
        """
        Get input from user with optional default value.

        Args:
            prompt: Prompt to show user
            default: Default value if user presses Enter or types 'skip'

        Returns:
            User input or default value
        """
        if default:
            full_prompt = f"{Colors.BOLD}{prompt} [{Colors.OKGREEN}{default}{Colors.ENDC}{Colors.BOLD}] (or 'quit'): {Colors.ENDC}"
        else:
            full_prompt = f"{Colors.BOLD}{prompt}: {Colors.ENDC}"

        user_input = input(full_prompt).strip()

        if user_input.lower() == 'quit':
            return 'quit'
        elif user_input.lower() == 'skip' or user_input == '':
            return default if default else ''
        else:
            return user_input

    def run_interactive_continue(self):
        """Continue interactive testing from current state."""
        print(f"\n{Colors.WARNING}Commands:{Colors.ENDC}")
        print("  - Type your message and press Enter")
        print("  - Type 'quit' to exit")
        print("  - Type 'state' to see current state")
        print("  - Type 'reset' to reset session")
        print("  - Type 'image' to simulate image upload")
        print()

        while True:
            try:
                user_input = input(
                    f"\n{Colors.BOLD}Your message: {Colors.ENDC}").strip()

                if not user_input:
                    continue

                if user_input.lower() == 'quit':
                    print(
                        f"\n{Colors.WARNING}👋 Ending session. Goodbye!{Colors.ENDC}\n")
                    break

                elif user_input.lower() == 'reset':
                    session_manager.reset_session(self.test_phone)
                    self.session = session_manager.get_session(self.test_phone)
                    self.message_count = 0
                    print(f"\n{Colors.WARNING}🔄 Session reset!{Colors.ENDC}")
                    self.send_message("hola")
                    continue

                elif user_input.lower() == 'state':
                    print(
                        f"\n{Colors.OKCYAN}📊 Current State: {self.session.state}{Colors.ENDC}")
                    print(
                        f"{Colors.OKCYAN}📊 Role: {self.session.role}{Colors.ENDC}")
                    print(
                        f"{Colors.OKCYAN}📊 Temp Data: {self.session.temp_data}{Colors.ENDC}")
                    continue

                elif user_input.lower() == 'image':
                    self.send_image()
                    continue

                self.send_message(user_input)

            except KeyboardInterrupt:
                print(
                    f"\n\n{Colors.WARNING}👋 Interrupted. Goodbye!{Colors.ENDC}\n")
                break
            except Exception as e:
                print(f"\n{Colors.FAIL}❌ Error: {e}{Colors.ENDC}")
                import traceback
                traceback.print_exc()

    def run_interactive(self):
        """Run interactive testing session."""
        self.print_header()

        print(f"{Colors.WARNING}Commands:{Colors.ENDC}")
        print("  - Type your message and press Enter")
        print("  - Type 'quit' or 'exit' to end session")
        print("  - Type 'reset' to reset session")
        print("  - Type 'state' to see current state")
        print("  - Type 'help' for more commands")
        print("  - Type 'image' to simulate image upload")
        print()

        # Send initial "hola" to start
        self.send_message("hola")

        while True:
            try:
                # Get user input
                user_input = input(
                    f"\n{Colors.BOLD}Your message: {Colors.ENDC}").strip()

                if not user_input:
                    continue

                # Handle special commands
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print(
                        f"\n{Colors.WARNING}👋 Ending test session. Goodbye!{Colors.ENDC}\n")
                    break

                elif user_input.lower() == 'reset':
                    session_manager.reset_session(self.test_phone)
                    self.session = session_manager.get_session(self.test_phone)
                    self.message_count = 0
                    print(f"\n{Colors.WARNING}🔄 Session reset!{Colors.ENDC}")
                    self.send_message("hola")
                    continue

                elif user_input.lower() == 'state':
                    print(
                        f"\n{Colors.OKCYAN}📊 Current State: {self.session.state}{Colors.ENDC}")
                    print(
                        f"{Colors.OKCYAN}📊 Role: {self.session.role}{Colors.ENDC}")
                    print(
                        f"{Colors.OKCYAN}📊 Temp Data: {self.session.temp_data}{Colors.ENDC}")
                    continue

                elif user_input.lower() == 'help':
                    print(f"\n{Colors.OKCYAN}Available commands:{Colors.ENDC}")
                    print("  quit/exit - End session")
                    print("  reset - Reset conversation")
                    print("  state - Show current state")
                    print("  image - Simulate image upload")
                    print("  help - Show this help")
                    continue

                elif user_input.lower() == 'image':
                    self.send_image()
                    continue

                # Send message to bot
                self.send_message(user_input)

            except KeyboardInterrupt:
                print(
                    f"\n\n{Colors.WARNING}👋 Interrupted. Goodbye!{Colors.ENDC}\n")
                break
            except Exception as e:
                print(f"\n{Colors.FAIL}❌ Error: {e}{Colors.ENDC}")
                import traceback
                traceback.print_exc()

    def run_scenario_client(self):
        """Run interactive client scenario test."""
        print(
            f"\n{Colors.HEADER}🧪 CLIENT SCENARIO - INTERACTIVE MODE{Colors.ENDC}\n")
        print(
            f"{Colors.WARNING}You'll be prompted for input at each step.{Colors.ENDC}")
        print(
            f"{Colors.WARNING}Press Enter to use default value, or type 'quit' to exit.{Colors.ENDC}\n")

        # Start conversation
        print(
            f"\n{Colors.OKCYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.ENDC}")
        print(f"{Colors.OKCYAN}STEP 1: Start conversation{Colors.ENDC}")
        print(f"{Colors.OKCYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.ENDC}")
        message = self._get_input("Your message", default="hola")
        if message == 'quit':
            return
        self.send_message(message)

        # Choose search type
        print(
            f"\n{Colors.OKCYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.ENDC}")
        print(f"{Colors.OKCYAN}STEP 2: Choose search type{Colors.ENDC}")
        print(f"{Colors.OKCYAN}  1 = Guided search | 2 = Quick search{Colors.ENDC}")
        print(f"{Colors.OKCYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.ENDC}")
        message = self._get_input("Your choice", default="1")
        if message == 'quit':
            return
        self.send_message(message)

        # If quick search, handle differently
        if message == '2':
            print(
                f"\n{Colors.OKCYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.ENDC}")
            print(f"{Colors.OKCYAN}STEP 3: Enter search filters{Colors.ENDC}")
            print(
                f"{Colors.OKCYAN}Format: enfoque\\npoblacion\\nmodalidad{Colors.ENDC}")
            print(
                f"{Colors.OKCYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.ENDC}")
            message = self._get_input(
                "Filters (multiline)", default="tcc\nadultos\nonline")
            if message == 'quit':
                return
            self.send_message(message)
            print(
                f"\n{Colors.OKGREEN}✅ Quick search scenario completed!{Colors.ENDC}\n")

            # Ask if want to continue interactively
            continue_test = input(
                f"\n{Colors.BOLD}Continue testing interactively? (y/n): {Colors.ENDC}").lower()
            if continue_test == 'y':
                print(
                    f"\n{Colors.OKCYAN}Switching to interactive mode...{Colors.ENDC}\n")
                self.run_interactive_continue()
            return

        # Guided search continues
        # Select enfoque
        print(
            f"\n{Colors.OKCYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.ENDC}")
        print(f"{Colors.OKCYAN}STEP 3: Select therapeutic approach{Colors.ENDC}")
        print(f"{Colors.OKCYAN}  1=TCC | 2=Contextual | 3=Sistémica | 4=Gestáltica | 5=Psicoanálisis | 6=Neuropsico{Colors.ENDC}")
        print(f"{Colors.OKCYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.ENDC}")
        message = self._get_input("Enfoque", default="1")
        if message == 'quit':
            return
        self.send_message(message)

        # Select población
        print(
            f"\n{Colors.OKCYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.ENDC}")
        print(f"{Colors.OKCYAN}STEP 4: Select target population{Colors.ENDC}")
        print(
            f"{Colors.OKCYAN}  1=Niño/Adolescente | 2=Adulto | 3=Pareja/Familia{Colors.ENDC}")
        print(f"{Colors.OKCYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.ENDC}")
        message = self._get_input("Población", default="2")
        if message == 'quit':
            return
        self.send_message(message)

        # Select modalidad
        print(
            f"\n{Colors.OKCYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.ENDC}")
        print(f"{Colors.OKCYAN}STEP 5: Select modality{Colors.ENDC}")
        print(f"{Colors.OKCYAN}  1=Online | 2=Presencial | 3=Me da igual{Colors.ENDC}")
        print(f"{Colors.OKCYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.ENDC}")
        message = self._get_input("Modalidad", default="1")
        if message == 'quit':
            return
        modalidad_selected = message
        self.send_message(message)

        # If presencial, ask zone
        if modalidad_selected == '2':
            print(
                f"\n{Colors.OKCYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.ENDC}")
            print(f"{Colors.OKCYAN}STEP 6: Select zone{Colors.ENDC}")
            print(f"{Colors.OKCYAN}  1=Norte | 2=Sur | 3=Nueva Córdoba{Colors.ENDC}")
            print(
                f"{Colors.OKCYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.ENDC}")
            message = self._get_input("Zona", default="1")
            if message == 'quit':
                return
            self.send_message(message)

        # Select horarios
        print(
            f"\n{Colors.OKCYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.ENDC}")
        print(f"{Colors.OKCYAN}STEP 7: Select schedule{Colors.ENDC}")
        print(f"{Colors.OKCYAN}  1=Mañana | 2=Tarde | 3=Noche | 4=Sábado{Colors.ENDC}")
        print(f"{Colors.OKCYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.ENDC}")
        message = self._get_input("Horarios", default="2")
        if message == 'quit':
            return
        self.send_message(message)

        # Select honorarios
        print(
            f"\n{Colors.OKCYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.ENDC}")
        print(f"{Colors.OKCYAN}STEP 8: Select fee range{Colors.ENDC}")
        print(f"{Colors.OKCYAN}  1=Hasta $15k | 2=$15-25k | 3=$25-35k | 4=Más de $35k | 5=Prefiero no decir{Colors.ENDC}")
        print(f"{Colors.OKCYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.ENDC}")
        message = self._get_input("Honorarios", default="2")
        if message == 'quit':
            return
        self.send_message(message)

        print(f"\n{Colors.OKGREEN}✅ Guided search scenario completed!{Colors.ENDC}")
        print(
            f"{Colors.WARNING}⏰ Waiting for delayed message (3 seconds)...{Colors.ENDC}\n")

        import time
        time.sleep(4)  # Wait for delayed message to arrive

        # Ask if want to continue interactively
        continue_test = input(
            f"\n{Colors.BOLD}Continue testing interactively? (y/n): {Colors.ENDC}").lower()
        if continue_test == 'y':
            print(
                f"\n{Colors.OKCYAN}Switching to interactive mode...{Colors.ENDC}\n")
            self.run_interactive_continue()

    def run_scenario_professional(self):
        """Run interactive professional scenario test."""
        print(
            f"\n{Colors.HEADER}🧪 PROFESSIONAL SCENARIO - INTERACTIVE MODE{Colors.ENDC}\n")
        print(
            f"{Colors.WARNING}You'll be prompted for input at each step.{Colors.ENDC}")
        print(
            f"{Colors.WARNING}Press Enter to use default value, or type 'quit' to exit.{Colors.ENDC}\n")

        # Identify as professional
        print(
            f"\n{Colors.OKCYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.ENDC}")
        print(f"{Colors.OKCYAN}STEP 1: Identify as professional{Colors.ENDC}")
        print(f"{Colors.OKCYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.ENDC}")
        message = self._get_input("Your message", default="hola soy psicólogo")
        if message == 'quit':
            return
        self.send_message(message)

        # Choose option (1=register, 2=info)
        print(
            f"\n{Colors.OKCYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.ENDC}")
        print(f"{Colors.OKCYAN}STEP 2: Registration confirmation{Colors.ENDC}")
        print(
            f"{Colors.OKCYAN}  1=Sí, quiero unirme | 2=Necesito más información{Colors.ENDC}")
        print(f"{Colors.OKCYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.ENDC}")
        message = self._get_input("Your choice", default="1")
        if message == 'quit':
            return
        first_choice = message
        self.send_message(message)

        # If chose info (2), show it and ask again
        if first_choice == '2':
            print(
                f"\n{Colors.OKCYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.ENDC}")
            print(
                f"{Colors.OKCYAN}STEP 3: Confirm registration after seeing info{Colors.ENDC}")
            print(f"{Colors.OKCYAN}  1=Sí, quiero unirme | 0=Volver{Colors.ENDC}")
            print(
                f"{Colors.OKCYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.ENDC}")
            message = self._get_input("Your choice", default="1")
            if message == 'quit':
                return
            self.send_message(message)

        # Now we should be at certificate upload
        print(
            f"\n{Colors.OKCYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.ENDC}")
        print(f"{Colors.OKCYAN}STEP 4: Upload certificate{Colors.ENDC}")
        print(
            f"{Colors.OKCYAN}  Type 'image' to simulate upload, or 0 to go back{Colors.ENDC}")
        print(f"{Colors.OKCYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.ENDC}")
        message = self._get_input("Action", default="image")
        if message == 'quit':
            return

        if message.lower() == 'image':
            self.send_image("test_certificate.jpg")
        else:
            self.send_message(message)

        print(
            f"\n{Colors.OKGREEN}✅ Professional registration completed!{Colors.ENDC}\n")

        # Ask if want to continue interactively
        continue_test = input(
            f"\n{Colors.BOLD}Continue testing interactively? (y/n): {Colors.ENDC}").lower()
        if continue_test == 'y':
            print(
                f"\n{Colors.OKCYAN}Switching to interactive mode...{Colors.ENDC}\n")
            self.run_interactive_continue()

    def simulate_certificate_upload(phone_number):
        """Simulate certificate upload for testing."""
        from datetime import datetime

        print(f"\n{'='*50}")
        print(f"[MOCK] Simulating certificate upload...")
        print(f"{'='*50}")

        # Create mock certificate path
        mock_cert_path = f"certificates/{phone_number}/mock_cert_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"

        # Create directory if doesn't exist
        os.makedirs(os.path.dirname(mock_cert_path), exist_ok=True)

        # Create empty mock file
        with open(mock_cert_path, 'w') as f:
            f.write("MOCK CERTIFICATE FOR TESTING")

        # Save certificate path
        professional_service.save_certificate(phone_number, mock_cert_path)

        print(f"✅ Certificate uploaded successfully")
        print(f"   Phone: {phone_number}")
        print(f"   Path: {mock_cert_path}")
        print(f"{'='*50}\n")

        return mock_cert_path

    def setup_test_professional(phone="+5491112345678"):
        """Setup a complete test professional with certificate and data."""
        print(f"\n{'='*50}")
        print(f"[SETUP] Creating test professional...")
        print(f"{'='*50}")

        # Create mock certificate
        mock_cert_path = f"certificates/{phone}/mock_cert.jpg"
        os.makedirs(os.path.dirname(mock_cert_path), exist_ok=True)

        with open(mock_cert_path, 'w') as f:
            f.write("MOCK CERTIFICATE FOR TESTING")

        # Save certificate
        professional_service.save_certificate(phone, mock_cert_path)

        # Add professional info
        success = professional_service.register_or_update_professional(
            phone=phone,
            name="Dr. Test Professional",
            email="test@psivale.com",
            zone="norte",
            gender="m",
            enfoque_terapeutico=["tcc", "contextual"],
            poblacion=["adultos", "parejas"],
            modalidad="ambas",
            horarios_disponibles=["tarde", "noche"],
            bio="Psicólogo de prueba para testing",
            fee_range="15000-25000"
        )

        if success:
            print(f"✅ Test professional created successfully!")
            print(f"   Phone: {phone}")
            print(f"{'='*50}\n")
            return True
        else:
            print(f"❌ Failed to create test professional")
            print(f"{'='*50}\n")
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Interactive bot testing tool for PSIVALE'
    )
    parser.add_argument(
        '--scenario',
        choices=['client', 'professional', 'interactive'],
        default='interactive',
        help='Test scenario to run'
    )
    parser.add_argument(
        '--phone',
        default='+5491112345678',
        help='Test phone number to use'
    )

    args = parser.parse_args()

    tester = BotTester(test_phone=args.phone)

    if args.scenario == 'client':
        tester.run_scenario_client()
    elif args.scenario == 'professional':
        tester.run_scenario_professional()
    else:
        tester.run_interactive()


if __name__ == "__main__":
    main()
