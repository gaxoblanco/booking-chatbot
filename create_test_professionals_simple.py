"""
Script SIMPLE para crear 5 profesionales de prueba
==================================================
Versión rápida y directa.

Uso en Docker:
    docker-compose exec whatsapp-webhook python create_test_professionals_simple.py

Uso local:
    python create_test_professionals_simple.py
"""

from client_service import client_service
from database import db
from professional_service import professional_service

print("\n🧪 CREANDO 5 PROFESIONALES DE PRUEBA...")
print("="*60 + "\n")

# Profesional 1: TCC + Contextual, Online + Presencial, Adultos + Parejas
print("1️⃣  Dra. Ana Rodríguez (TCC, Online/Presencial)")
professional_service.register_or_update_professional(
    phone="+5491111111111",
    name="Dra. Ana María Rodríguez",
    email="ana@psivale.com",
    zone="norte",
    gender="f",
    accept_prepaga=True,
    enfoque_terapeutico=["tcc", "contextual"],
    poblacion=["adultos", "parejas"],
    modalidad="ambas",
    horarios_disponibles=["manana", "tarde"],
    bio="Especialista en TCC. 10 años de experiencia.",
    fee_range="15000-25000"
)
db.update_certificate("+5491111111111", "certificates/test1.jpg")
db.add_weekly_schedule("+5491111111111", 0, "09:00", "13:00")  # Lunes mañana
db.add_weekly_schedule("+5491111111111", 2, "14:00",
                       "18:00")  # Miércoles tarde
print("   ✅ Creada\n")

# Profesional 2: Gestáltica, Presencial, Niños/Adolescentes + Adultos
print("2️⃣  Lic. Carlos Gómez (Gestáltica, Presencial)")
professional_service.register_or_update_professional(
    phone="+5491122222222",
    name="Lic. Carlos Gómez",
    email="carlos@psivale.com",
    zone="sur",
    gender="m",
    accept_prepaga=False,
    enfoque_terapeutico=["gestaltica"],
    poblacion=["adultos", "ninos_adolescentes"],
    modalidad="presencial",
    horarios_disponibles=["tarde", "noche"],
    bio="Terapeuta gestáltico con niños y adultos.",
    fee_range="25000-35000"
)
db.update_certificate("+5491122222222", "certificates/test2.jpg")
db.add_weekly_schedule("+5491122222222", 1, "14:00", "18:00")  # Martes tarde
db.add_weekly_schedule("+5491122222222", 3, "18:00", "21:00")  # Jueves noche
print("   ✅ Creado\n")

# Profesional 3: Psicoanálisis, Online, Adultos
print("3️⃣  Lic. María Fernández (Psicoanálisis, Online)")
professional_service.register_or_update_professional(
    phone="+5491133333333",
    name="Lic. María Elena Fernández",
    email="maria@psivale.com",
    zone="nueva_cordoba",
    gender="f",
    accept_prepaga=True,
    enfoque_terapeutico=["psicoanalisis"],
    poblacion=["adultos"],
    modalidad="online",
    horarios_disponibles=["manana", "tarde", "noche"],
    bio="Psicoanalista lacaniana. Atención online.",
    fee_range="35000+"
)
db.update_certificate("+5491133333333", "certificates/test3.jpg")
db.add_weekly_schedule("+5491133333333", 0, "09:00",
                       "21:00")  # Lunes todo el día
db.add_weekly_schedule("+5491133333333", 4, "09:00",
                       "21:00")  # Viernes todo el día
print("   ✅ Creada\n")

# Profesional 4: Sistémica, Ambas, Parejas
print("4️⃣  Lic. Jorge Pérez (Sistémica, Parejas)")
professional_service.register_or_update_professional(
    phone="+5491144444444",
    name="Lic. Jorge Luis Pérez",
    email="jorge@psivale.com",
    zone="norte",
    gender="m",
    accept_prepaga=True,
    enfoque_terapeutico=["sistemica"],
    poblacion=["parejas", "adultos"],
    modalidad="ambas",
    horarios_disponibles=["sabado", "tarde"],
    bio="Terapeuta sistémico en pareja y familia.",
    fee_range="15000-25000"
)
db.update_certificate("+5491144444444", "certificates/test4.jpg")
db.add_weekly_schedule("+5491144444444", 5, "10:00", "14:00")  # Sábado
db.add_weekly_schedule("+5491144444444", 2, "14:00",
                       "18:00")  # Miércoles tarde
print("   ✅ Creado\n")

# Profesional 5: Neuropsicología + TCC, Presencial, Niños/Adolescentes
print("5️⃣  Dra. Laura Martínez (Neuropsicología, Presencial)")
professional_service.register_or_update_professional(
    phone="+5491155555555",
    name="Dra. Laura Beatriz Martínez",
    email="laura@psivale.com",
    zone="sur",
    gender="f",
    accept_prepaga=False,
    enfoque_terapeutico=["neuropsicologia", "tcc"],
    poblacion=["ninos_adolescentes", "adultos"],
    modalidad="presencial",
    horarios_disponibles=["manana"],
    bio="Neuropsicóloga especializada en niños.",
    fee_range="25000-35000"
)
db.update_certificate("+5491155555555", "certificates/test5.jpg")
db.add_weekly_schedule("+5491155555555", 0, "09:00", "13:00")  # Lunes mañana
db.add_weekly_schedule("+5491155555555", 2, "09:00",
                       "13:00")  # Miércoles mañana
db.add_weekly_schedule("+5491155555555", 4, "09:00", "13:00")  # Viernes mañana
print("   ✅ Creada\n")

print("="*60)
print("✅ 5 PROFESIONALES CREADOS EXITOSAMENTE")
print("="*60 + "\n")

# Mostrar estadísticas
stats = db.get_stats()
print("📊 ESTADÍSTICAS:")
print(f"   Total profesionales: {stats.get('total_professionals', 0)}")
print(f"   Total búsquedas: {stats.get('total_searches', 0)}")
print()

# Verificar búsquedas
print("🔍 VERIFICACIÓN DE BÚSQUEDAS:")

tests = [
    ({"enfoque": "tcc"}, "TCC"),
    ({"poblacion": "adultos"}, "Adultos"),
    ({"modalidad": "online"}, "Online"),
    ({"zone": "norte"}, "Zona Norte"),
    ({"horarios": "tarde"}, "Tarde"),
    ({"fee_range": "15000-25000"}, "$15-25k"),
]

for filters, label in tests:
    results = client_service.search_professionals_psivale(**filters)
    print(f"   {label}: {len(results)} encontrados")

print()
print("💡 PARA TESTEAR:")
print("   1. Envía 'hola' al bot")
print("   2. Opción 1: Flujo asesorado")
print("   3. Prueba diferentes combinaciones")
print()
print("🗑️  PARA ELIMINAR (ejecuta en SQLite):")
print("   DELETE FROM professionals WHERE phone LIKE '+549111%';")
print()
