#!/usr/bin/env python3
"""
Test Interactivo de UserService
================================
Prueba el servicio de identificación de usuarios sin modificar bot.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.services.user_service import user_service


def test_detect_intention():
    """Prueba la detección de intención."""
    print("=" * 60)
    print("TEST 1: DETECCIÓN DE INTENCIÓN")
    print("=" * 60)

    test_cases = [
        ("hola", "client", "Saludo simple → cliente"),
        ("hola soy profesional", "professional", "Identificación directa"),
        ("necesito un turno", "client", "Búsqueda de servicio"),
        ("trabajo como psicólogo", "professional", "Descripción de actividad"),
        ("busco terapeuta", "client", "Búsqueda de profesional"),
        ("buenos días", "client", "Saludo → cliente por defecto"),
    ]

    print("\nProbando detección de intención:\n")

    for message, expected, description in test_cases:
        result = user_service.detect_intention(message)
        status = "✅" if result == expected else "❌"

        print(f"{status} '{message}'")
        print(f"   Esperado: {expected} | Obtenido: {result}")
        print(f"   → {description}")
        print()


def test_identify_user():
    """Prueba la identificación de usuarios."""
    print("=" * 60)
    print("TEST 2: IDENTIFICACIÓN DE USUARIOS")
    print("=" * 60)

    # Caso 1: Usuario nuevo
    print("\n--- Caso 1: Usuario nuevo ---")
    phone_new = "+5491199999999"
    user_info = user_service.identify_user(phone_new)

    print(f"Teléfono: {phone_new}")
    print(f"Tipo: {user_info['user_type']}")
    print(f"Registrado: {user_info['is_registered']}")
    print(f"Tiene citas: {user_info['has_pending_appointments']}")

    if user_info['user_type'] == 'new':
        print("✅ Correctamente identificado como nuevo")
    else:
        print("❌ Error en identificación")

    # Caso 2: Buscar en base de datos real
    # (si hay datos, los mostrará)
    print("\n--- Caso 2: Buscar usuarios existentes ---")
    print("(Si hay profesionales o clientes en la BD, aparecerán aquí)\n")


def test_welcome_messages():
    """Prueba los mensajes de bienvenida."""
    print("=" * 60)
    print("TEST 3: MENSAJES DE BIENVENIDA")
    print("=" * 60)

    # Usuario nuevo
    print("\n--- Usuario Nuevo ---")
    user_info_new = {
        'user_type': 'new',
        'name': None,
        'has_pending_appointments': False,
        'pending_appointments': []
    }
    message = user_service.generate_welcome_message(user_info_new)
    print(message)

    # Cliente registrado sin citas
    print("\n--- Cliente Registrado (sin citas) ---")
    user_info_client = {
        'user_type': 'client',
        'name': 'María',
        'has_pending_appointments': False,
        'pending_appointments': []
    }
    message = user_service.generate_welcome_message(user_info_client)
    print(message)

    # Cliente registrado con citas
    print("\n--- Cliente Registrado (con citas) ---")
    user_info_client_with_apt = {
        'user_type': 'client',
        'name': 'María',
        'has_pending_appointments': True,
        'pending_appointments': [{
            'date': '15/12/2024',
            'time': '14:00',
            'professional_name': 'Lic. Juan Pérez'
        }]
    }
    message = user_service.generate_welcome_message(user_info_client_with_apt)
    print(message)

    # Profesional registrado
    print("\n--- Profesional Registrado ---")
    user_info_prof = {
        'user_type': 'professional',
        'name': 'Dr. Juan Pérez',
        'has_pending_appointments': True,
        'pending_appointments': [1, 2, 3]  # 3 citas pendientes
    }
    message = user_service.generate_welcome_message(user_info_prof)
    print(message)


def test_log_action():
    """Prueba el logging de acciones."""
    print("=" * 60)
    print("TEST 4: LOGGING DE ACCIONES")
    print("=" * 60)

    print("\nRegistrando acciones de ejemplo:\n")

    # Búsqueda
    user_service.log_action(
        phone="+5491112345678",
        action_type='search',
        details={'filters': {'zona': 'norte', 'especialidad': 'tcc'}},
        session_id='session_123'
    )

    # Reserva
    user_service.log_action(
        phone="+5491112345678",
        action_type='book',
        details={'professional': '+5491187654321', 'date': '2024-12-15'},
        session_id='session_123'
    )

    print("\n✅ Acciones registradas (ver output arriba)")


def interactive_test():
    """Modo interactivo para probar mensajes."""
    print("=" * 60)
    print("MODO INTERACTIVO")
    print("=" * 60)
    print("\nEscribe mensajes para ver cómo se detecta la intención.")
    print("Escribe 'salir' para terminar.\n")

    while True:
        try:
            message = input("Tu mensaje: ").strip()

            if message.lower() in ['salir', 'exit', 'quit']:
                print("\n¡Hasta luego!")
                break

            if not message:
                continue

            # Detectar intención
            intention = user_service.detect_intention(message)

            print(f"  → Intención detectada: {intention}")

            if intention == 'professional':
                print("  → Se mostraría: Flujo de registro profesional")
            elif intention == 'client':
                print("  → Se mostraría: Flujo de búsqueda de citas")
            else:
                print("  → Se preguntaría: ¿Sos cliente o profesional?")

            print()

        except KeyboardInterrupt:
            print("\n\n¡Hasta luego!")
            break


def main():
    """Ejecutar todos los tests."""
    print("\n")
    print("🧪 TESTS DE USER SERVICE")
    print("========================\n")

    # Tests automáticos
    test_detect_intention()
    input("Presiona ENTER para continuar...")

    test_identify_user()
    input("Presiona ENTER para continuar...")

    test_welcome_messages()
    input("Presiona ENTER para continuar...")

    test_log_action()
    input("Presiona ENTER para continuar...")

    # Modo interactivo
    print("\n")
    response = input("¿Quieres probar el modo interactivo? (s/n): ")
    if response.lower() in ['s', 'si', 'sí', 'y', 'yes']:
        interactive_test()

    print("\n✅ Tests completados!")
    print("\nPróximo paso: Integrar en bot.py")


if __name__ == "__main__":
    main()
