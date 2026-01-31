#!/usr/bin/env python3
"""
Bot Interactive Testing Script - HTTP Mode
==========================================
Simula mensajes de WhatsApp enviando requests HTTP al webhook real.
Compatible con Docker y el servicio en ejecución.

Usage:
    python test_bot_http.py                    # Interactive mode
    python test_bot_http.py --scenario filters # Test filters
    python test_bot_http.py --url http://localhost:5001/webhook
"""

import argparse
import requests
from datetime import datetime, date, timedelta
from urllib.parse import urlencode
import xml.etree.ElementTree as ET


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


class WebhookTester:
    """
    Tester que simula requests de Twilio al webhook.
    """

    def __init__(self, webhook_url="http://localhost:5001/webhook", test_phone="+5491112345678"):
        """
        Initialize webhook tester.

        Args:
            webhook_url: URL del webhook (ej: http://localhost:5001/webhook)
            test_phone: Phone number to use for testing
        """
        self.webhook_url = webhook_url
        self.test_phone = test_phone
        self.message_count = 0
        
        # Verificar conexión
        try:
            response = requests.get(webhook_url.replace('/webhook', '/'), timeout=2)
            print(f"{Colors.OKGREEN}✅ Conectado al servidor: {webhook_url}{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.FAIL}❌ No se pudo conectar al servidor: {webhook_url}{Colors.ENDC}")
            print(f"{Colors.WARNING}   Asegúrate de que Docker esté corriendo{Colors.ENDC}")
            raise

    def print_header(self):
        """Print welcome header."""
        print("\n" + "="*70)
        print(f"{Colors.HEADER}{Colors.BOLD}🤖 BOT HTTP TESTER - WEBHOOK MODE{Colors.ENDC}")
        print("="*70)
        print(f"{Colors.OKCYAN}Webhook URL: {self.webhook_url}{Colors.ENDC}")
        print(f"{Colors.OKCYAN}Test Phone: {self.test_phone}{Colors.ENDC}")
        print("="*70 + "\n")

    def send_message(self, message: str, show_input=True):
        """
        Envía un mensaje al webhook simulando un request de Twilio.

        Args:
            message: Message text to send
            show_input: Whether to print the input

        Returns:
            Bot response text
        """
        if show_input:
            self.print_user_input(message)

        # Construir payload como lo hace Twilio
        payload = {
            'From': f'whatsapp:{self.test_phone}',
            'To': 'whatsapp:+5493704123456',  # Number doesn't matter
            'Body': message,
            'MessageSid': f'SM{datetime.now().strftime("%Y%m%d%H%M%S")}',
            'NumMedia': '0'
        }

        try:
            # Enviar POST request
            response = requests.post(
                self.webhook_url,
                data=payload,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=10
            )

            if response.status_code == 200:
                # Parsear TwiML response
                bot_response = self.parse_twiml(response.text)
                self.print_bot_response(bot_response)
                return bot_response
            else:
                error_msg = f"Error HTTP {response.status_code}"
                print(f"{Colors.FAIL}❌ {error_msg}{Colors.ENDC}")
                return error_msg

        except requests.exceptions.Timeout:
            error_msg = "⏱️ Timeout - el servidor tardó demasiado"
            print(f"{Colors.FAIL}❌ {error_msg}{Colors.ENDC}")
            return error_msg
        except Exception as e:
            error_msg = f"Error: {e}"
            print(f"{Colors.FAIL}❌ {error_msg}{Colors.ENDC}")
            return error_msg

    def parse_twiml(self, twiml_text: str) -> str:
        """
        Parsea la respuesta TwiML y extrae el mensaje.

        Args:
            twiml_text: XML TwiML response

        Returns:
            Mensaje de texto extraído
        """
        try:
            # Parsear XML
            root = ET.fromstring(twiml_text)
            # Buscar el elemento <Message>
            message_elem = root.find('.//{http://www.twilio.com/2008/version}Message')
            if message_elem is None:
                message_elem = root.find('.//Message')
            
            if message_elem is not None:
                return message_elem.text or ""
            else:
                return "[No message in response]"
        except Exception as e:
            print(f"{Colors.WARNING}⚠️ Error parsing TwiML: {e}{Colors.ENDC}")
            return twiml_text[:200] + "..."

    def print_bot_response(self, response: str):
        """Print bot response with formatting."""
        self.message_count += 1
        print(f"\n{Colors.OKGREEN}{Colors.BOLD}🤖 BOT (Message #{self.message_count}):{Colors.ENDC}")
        print(f"{Colors.OKGREEN}{response}{Colors.ENDC}")

    def print_user_input(self, message: str):
        """Print user input with formatting."""
        print(f"\n{Colors.OKBLUE}{Colors.BOLD}👤 YOU:{Colors.ENDC} {message}")

    def _get_input(self, prompt: str, default=None):
        """Get user input with optional default value."""
        if default:
            user_input = input(f"{Colors.BOLD}💬 {prompt} [{default}]: {Colors.ENDC}").strip()
            return user_input if user_input else default
        else:
            return input(f"{Colors.BOLD}💬 {prompt}: {Colors.ENDC}").strip()

    def run_interactive(self):
        """Run fully interactive mode."""
        self.print_header()
        
        print(f"{Colors.WARNING}📝 Interactive Mode{Colors.ENDC}")
        print(f"{Colors.WARNING}Type 'quit' or 'exit' to stop{Colors.ENDC}")
        print(f"{Colors.WARNING}Type 'reset' to restart conversation (send 'hola'){Colors.ENDC}\n")

        # Start conversation
        self.send_message("hola")

        while True:
            try:
                user_input = input(f"\n{Colors.BOLD}💬 Your message: {Colors.ENDC}").strip()

                if not user_input:
                    continue

                if user_input.lower() in ['quit', 'exit', 'q']:
                    print(f"\n{Colors.WARNING}👋 Goodbye!{Colors.ENDC}\n")
                    break

                if user_input.lower() == 'reset':
                    print(f"\n{Colors.WARNING}🔄 Resetting conversation...{Colors.ENDC}")
                    self.send_message("hola")
                    continue

                # Send message to webhook
                self.send_message(user_input)

            except KeyboardInterrupt:
                print(f"\n\n{Colors.WARNING}👋 Interrupted. Goodbye!{Colors.ENDC}\n")
                break
            except Exception as e:
                print(f"\n{Colors.FAIL}❌ Error: {e}{Colors.ENDC}")
                import traceback
                traceback.print_exc()

    def run_scenario_filters(self):
        """Run filter system test scenario."""
        print(f"\n{Colors.HEADER}🧪 FILTER SYSTEM TEST{Colors.ENDC}\n")
        print(f"{Colors.WARNING}Testing the new modular filter system...{Colors.ENDC}\n")

        # Start conversation
        print(f"\n{Colors.OKCYAN}━━━ STEP 1: Start & Choose Search ━━━{Colors.ENDC}")
        self.send_message("hola")
        self.send_message("1")  # Buscar profesional

        # Test Date Filter
        print(f"\n{Colors.OKCYAN}━━━ STEP 2: Select Date Filter ━━━{Colors.ENDC}")
        print(f"{Colors.WARNING}Testing: DateFilter with direct input{Colors.ENDC}")
        self.send_message("1")  # Select Fecha
        
        # Test date input
        tomorrow = (date.today() + timedelta(days=7)).strftime('%d/%m/%Y')
        message = self._get_input(f"Enter date (DD/MM/YYYY)", default=tomorrow)
        if message == 'quit':
            return
        self.send_message(message)

        # Test Time Filter
        print(f"\n{Colors.OKCYAN}━━━ STEP 3: Select Time Filter ━━━{Colors.ENDC}")
        print(f"{Colors.WARNING}Testing: TimeFilter{Colors.ENDC}")
        self.send_message("2")  # Select Horario
        message = self._get_input("Choose time (1=Morning, 2=Afternoon, or HH:MM)", default="1")
        if message == 'quit':
            return
        self.send_message(message)

        # Test Specialty Filter
        print(f"\n{Colors.OKCYAN}━━━ STEP 4: Select Specialty Filter ━━━{Colors.ENDC}")
        print(f"{Colors.WARNING}Testing: SpecialtyFilter{Colors.ENDC}")
        self.send_message("3")  # Select Especialidad
        message = self._get_input("Choose specialty (1, 2, 3...)", default="1")
        if message == 'quit':
            return
        self.send_message(message)

        # Test Zone Filter
        print(f"\n{Colors.OKCYAN}━━━ STEP 5: Select Zone Filter ━━━{Colors.ENDC}")
        print(f"{Colors.WARNING}Testing: ZoneFilter (Optional){Colors.ENDC}")
        self.send_message("4")  # Select Zona
        message = self._get_input("Choose zone (1=Norte, 2=Sur, 3=Any)", default="1")
        if message == 'quit':
            return
        self.send_message(message)

        # Execute search
        print(f"\n{Colors.OKCYAN}━━━ STEP 6: Execute Search ━━━{Colors.ENDC}")
        print(f"{Colors.WARNING}Testing: Search with all filters{Colors.ENDC}")
        self.send_message("9")  # Buscar

        print(f"\n{Colors.OKGREEN}✅ Filter system test completed!{Colors.ENDC}")

        # Ask if want to continue interactively
        continue_test = input(f"\n{Colors.BOLD}Continue testing interactively? (y/n): {Colors.ENDC}").lower()
        if continue_test == 'y':
            print(f"\n{Colors.OKCYAN}Switching to interactive mode...{Colors.ENDC}\n")
            self.run_interactive()

    def run_scenario_quick(self):
        """Run quick test scenario."""
        print(f"\n{Colors.HEADER}🧪 QUICK TEST{Colors.ENDC}\n")
        
        # Start
        print(f"\n{Colors.OKCYAN}━━━ Starting conversation ━━━{Colors.ENDC}")
        self.send_message("hola")
        
        # Choose search
        print(f"\n{Colors.OKCYAN}━━━ Choose search type ━━━{Colors.ENDC}")
        self.send_message("1")  # Buscar profesional
        
        # Quick filter - just date
        print(f"\n{Colors.OKCYAN}━━━ Add date filter ━━━{Colors.ENDC}")
        self.send_message("1")  # Fecha
        self.send_message("1")  # Hoy
        
        # Search
        print(f"\n{Colors.OKCYAN}━━━ Execute search ━━━{Colors.ENDC}")
        self.send_message("9")  # Buscar
        
        print(f"\n{Colors.OKGREEN}✅ Quick test completed!{Colors.ENDC}")
        
        # Continue interactive
        continue_test = input(f"\n{Colors.BOLD}Continue testing interactively? (y/n): {Colors.ENDC}").lower()
        if continue_test == 'y':
            self.run_interactive()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Interactive webhook testing tool (HTTP mode)'
    )
    parser.add_argument(
        '--scenario',
        choices=['filters', 'quick'],
        help='Run a specific test scenario'
    )
    parser.add_argument(
        '--url',
        default='http://localhost:5001/webhook',
        help='Webhook URL (default: http://localhost:5001/webhook)'
    )
    parser.add_argument(
        '--phone',
        default='+5491112345678',
        help='Test phone number (default: +5491112345678)'
    )

    args = parser.parse_args()

    try:
        # Create tester instance
        tester = WebhookTester(webhook_url=args.url, test_phone=args.phone)

        # Run appropriate mode
        if args.scenario == 'filters':
            tester.run_scenario_filters()
        elif args.scenario == 'quick':
            tester.run_scenario_quick()
        else:
            # Default: interactive mode
            tester.run_interactive()
    
    except Exception as e:
        print(f"\n{Colors.FAIL}❌ Fatal error: {e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())