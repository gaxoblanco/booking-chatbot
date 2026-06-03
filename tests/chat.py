#!/usr/bin/env python3
"""
chat.py — Terminal Chat
=======================
Chat interactivo para testear flujos del bot directamente,
sin pasar por Meta ni Twilio.

Cómo correr:
    docker exec -it whatsapp-demo python tests/chat.py

Comandos especiales durante el chat:
    /switch     → cambia entre cliente y profesional
    /new        → reinicia la sesión del número activo
    /info       → muestra estado de la sesión actual
    /phone XXXX → cambia el número manualmente
    /exit       → salir
    /help       → muestra esta ayuda
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.bot.bot_controller import bot_controller
from src.core.states import session_manager


# ── Colores ────────────────────────────────────────────────────────────────────

class C:
    BOT     = '\033[96m'    # cyan — respuesta del bot
    USER    = '\033[92m'    # verde — mensaje del usuario
    SYSTEM  = '\033[93m'    # amarillo — mensajes del sistema
    ERROR   = '\033[91m'    # rojo — errores
    DIM     = '\033[2m'     # gris — info secundaria
    BOLD    = '\033[1m'
    END     = '\033[0m'


# ── Helpers ────────────────────────────────────────────────────────────────────

def sep(char='─', width=60):
    print(f"{C.DIM}{char * width}{C.END}")

def system(msg):
    print(f"\n{C.SYSTEM}  ⚙  {msg}{C.END}")

def error(msg):
    print(f"\n{C.ERROR}  ✗  {msg}{C.END}")

def print_response(response: str, msg_num: int):
    sep()
    print(f"{C.DIM}  BOT #{msg_num}{C.END}")
    sep()
    # Indentar cada línea para que sea fácil de leer
    for line in response.split('\n'):
        print(f"  {C.BOT}{line}{C.END}")
    sep()

def print_session_info(phone: str):
    session = session_manager.get_session(phone)
    sep('·')
    print(f"{C.DIM}  Número : {phone}")
    print(f"  Rol    : {session.role.value if session.role else 'sin rol'}")
    print(f"  Estado : {session.state.value}")
    if session.temp_data:
        keys = list(session.temp_data.keys())
        print(f"  Temp   : {keys}")
    print(f"{C.END}", end='')
    sep('·')

def show_help():
    sep()
    print(f"{C.DIM}  Comandos especiales:")
    print(f"    /switch     → alterna entre cliente y profesional")
    print(f"    /new        → reinicia la sesión del número activo")
    print(f"    /info       → estado de la sesión actual")
    print(f"    /phone XXXX → cambiar número manualmente")
    print(f"    /exit       → salir")
    print(f"    /help       → mostrar esta ayuda{C.END}")
    sep()


# ── Chat principal ─────────────────────────────────────────────────────────────

def run():
    # Números por defecto
    phones = {
        'cliente':      '+5491123456789',
        'profesional':  '+5491112345678',
    }
    active_role = 'cliente'
    msg_count = 0

    # Header
    print(f"\n{C.BOLD}{'═' * 60}")
    print(f"  BOOKING BOT — Terminal Chat")
    print(f"{'═' * 60}{C.END}")
    system(f"Número activo  : {phones[active_role]}  [{active_role.upper()}]")
    system(f"Otro número    : {phones['profesional' if active_role == 'cliente' else 'cliente']}")
    print(f"{C.DIM}  Escribí /help para ver comandos especiales{C.END}\n")

    # Enviar "hola" automático para arrancar
    phone = phones[active_role]
    system(f"Iniciando conversación como {active_role.upper()} ({phone})...")
    response = bot_controller.process_message(phone, "hola")
    msg_count += 1
    print_response(response, msg_count)

    # Loop principal
    while True:
        try:
            phone = phones[active_role]
            prompt = (
                f"\n{C.USER}  [{active_role.upper()}] > {C.END}"
            )
            user_input = input(prompt).strip()

            if not user_input:
                continue

            # ── Comandos especiales ────────────────────────────────────────

            if user_input.lower() == '/exit':
                system("Saliendo...")
                break

            if user_input.lower() == '/help':
                show_help()
                continue

            if user_input.lower() == '/info':
                print_session_info(phone)
                continue

            if user_input.lower() == '/new':
                session_manager.delete_session(phone)
                system(f"Sesión reiniciada para {phone}")
                response = bot_controller.process_message(phone, "hola")
                msg_count += 1
                print_response(response, msg_count)
                continue

            if user_input.lower() == '/switch':
                active_role = 'profesional' if active_role == 'cliente' else 'cliente'
                phone = phones[active_role]
                system(f"Cambiado a {active_role.upper()} ({phone})")
                # Mostrar estado actual de la sesión
                session = session_manager.get_session(phone)
                if session.state.value != 'initial':
                    system(f"Sesión existente — estado: {session.state.value}")
                else:
                    system("Sesión nueva — enviando hola...")
                    response = bot_controller.process_message(phone, "hola")
                    msg_count += 1
                    print_response(response, msg_count)
                continue

            if user_input.lower().startswith('/phone '):
                new_phone = user_input[7:].strip()
                if not new_phone:
                    error("Formato: /phone +5491199999999")
                    continue
                phones[active_role] = new_phone
                session_manager.delete_session(new_phone)
                system(f"Número de {active_role.upper()} cambiado a {new_phone}")
                response = bot_controller.process_message(new_phone, "hola")
                msg_count += 1
                print_response(response, msg_count)
                continue

            # ── Mensaje normal ─────────────────────────────────────────────

            response = bot_controller.process_message(phone, user_input)
            msg_count += 1
            print_response(response, msg_count)

        except KeyboardInterrupt:
            system("\nInterrumpido. Saliendo...")
            break
        except Exception as e:
            error(f"{e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    run()
