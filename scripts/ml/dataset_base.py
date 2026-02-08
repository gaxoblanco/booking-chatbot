"""
Dataset Base - MEJORADO con Casos Problemáticos
================================================
Versión 2.0 - Agregados 15 nuevos ejemplos para:
- Días de semana con typos
- Títulos profesionales con typos (dr, dc, doc)
- Solo apellidos sin nombre
- Combinaciones problemáticas
"""

DATASET_BASE = [
    # ==========================================
    # INTENT: SEARCH_PROFESSIONAL (35 ejemplos)
    # ==========================================
    
    # --- CASOS ORIGINALES (20) ---
    
    # Con especialidad + fecha
    {
        "message": "necesito psicólogo mañana",
        "intent": "search_professional",
        "entities": {"especialidad": "psicología", "fecha": "mañana"}
    },
    {
        "message": "busco nutricionista para hoy",
        "intent": "search_professional",
        "entities": {"especialidad": "nutrición", "fecha": "hoy"}
    },
    {
        "message": "quiero turno con kinesiólogo el 15/02",
        "intent": "search_professional",
        "entities": {"especialidad": "kinesiología", "fecha": "15/02"}
    },
    
    # Con especialidad + fecha + horario
    {
        "message": "necesito psicólogo mañana por la tarde",
        "intent": "search_professional",
        "entities": {"especialidad": "psicología", "fecha": "mañana", "horario": "tarde"}
    },
    {
        "message": "busco nutricionista para hoy por la mañana",
        "intent": "search_professional",
        "entities": {"especialidad": "nutrición", "fecha": "hoy", "horario": "mañana"}
    },
    {
        "message": "quiero kine para esta semana por la noche",
        "intent": "search_professional",
        "entities": {"especialidad": "kinesiología", "fecha": "esta_semana", "horario": "noche"}
    },
    
    # Con especialidad + fecha + zona
    {
        "message": "necesito psicólogo mañana en palermo",
        "intent": "search_professional",
        "entities": {"especialidad": "psicología", "fecha": "mañana", "zona": "norte"}
    },
    {
        "message": "busco nutricionista en zona sur",
        "intent": "search_professional",
        "entities": {"especialidad": "nutrición", "zona": "sur"}
    },
    {
        "message": "quiero kine online",
        "intent": "search_professional",
        "entities": {"especialidad": "kinesiología", "zona": "online"}
    },
    
    # Con especialidad + género
    {
        "message": "necesito psicóloga mujer",
        "intent": "search_professional",
        "entities": {"especialidad": "psicología", "genero": "femenino"}
    },
    {
        "message": "busco nutricionista hombre",
        "intent": "search_professional",
        "entities": {"especialidad": "nutrición", "genero": "masculino"}
    },
    
    # Con prepaga
    {
        "message": "necesito psicólogo que acepte OSDE",
        "intent": "search_professional",
        "entities": {"especialidad": "psicología", "prepaga": True}
    },
    {
        "message": "busco nutricionista con obra social",
        "intent": "search_professional",
        "entities": {"especialidad": "nutrición", "prepaga": True}
    },
    
    # Solo especialidad (incompleto)
    {
        "message": "necesito psicólogo",
        "intent": "search_professional",
        "entities": {"especialidad": "psicología"}
    },
    {
        "message": "busco nutricionista",
        "intent": "search_professional",
        "entities": {"especialidad": "nutrición"}
    },
    {
        "message": "quiero turno con kinesiólogo",
        "intent": "search_professional",
        "entities": {"especialidad": "kinesiología"}
    },
    
    # Complejo (múltiples filtros)
    {
        "message": "necesito psicóloga mujer mañana por la tarde en zona norte que acepte OSDE",
        "intent": "search_professional",
        "entities": {
            "especialidad": "psicología",
            "genero": "femenino",
            "fecha": "mañana",
            "horario": "tarde",
            "zona": "norte",
            "prepaga": True
        }
    },
    {
        "message": "busco nutricionista hombre para hoy por la mañana en zona centro",
        "intent": "search_professional",
        "entities": {
            "especialidad": "nutrición",
            "genero": "masculino",
            "fecha": "hoy",
            "horario": "mañana",
            "zona": "centro"
        }
    },
    
    # Con nombre de profesional
    {
        "message": "quiero turno con la doctora María González",
        "intent": "search_professional",
        "entities": {"professional_name": "maría gonzález"}
    },
    {
        "message": "necesito ver al doctor Juan Pérez",
        "intent": "search_professional",
        "entities": {"professional_name": "juan pérez"}
    },
    
    # --- ⭐ NUEVOS: DÍAS DE SEMANA (5 ejemplos) ---
    
    {
        "message": "quiero turno para el martes",
        "intent": "search_professional",
        "entities": {"fecha": "martes"}
    },
    {
        "message": "necesito psicólogo el miércoles que viene",
        "intent": "search_professional",
        "entities": {"especialidad": "psicología", "fecha": "miércoles"}
    },
    {
        "message": "busco nutricionista para el jueves",
        "intent": "search_professional",
        "entities": {"especialidad": "nutrición", "fecha": "jueves"}
    },
    {
        "message": "turno el viernes por la tarde",
        "intent": "search_professional",
        "entities": {"fecha": "viernes", "horario": "tarde"}
    },
    {
        "message": "cita para el sábado que viene",
        "intent": "search_professional",
        "entities": {"fecha": "sábado"}
    },
    
    # --- ⭐ NUEVOS: NOMBRES CON TÍTULOS VARIADOS (5 ejemplos) ---
    
    {
        "message": "turno con el dr García",
        "intent": "search_professional",
        "entities": {"professional_name": "garcía"}
    },
    {
        "message": "necesito ver a la dra López",
        "intent": "search_professional",
        "entities": {"professional_name": "lópez"}
    },
    {
        "message": "quiero cita con el doctor Fernández",
        "intent": "search_professional",
        "entities": {"professional_name": "fernández"}
    },
    {
        "message": "busco al lic Rodríguez",
        "intent": "search_professional",
        "entities": {"professional_name": "rodríguez"}
    },
    {
        "message": "sesión con la doctora Martínez",
        "intent": "search_professional",
        "entities": {"professional_name": "martínez"}
    },
    
    # --- ⭐ NUEVOS: SOLO APELLIDOS (5 ejemplos) ---
    
    {
        "message": "turno con Blanco",
        "intent": "search_professional",
        "entities": {"professional_name": "blanco"}
    },
    {
        "message": "necesito ver a González",
        "intent": "search_professional",
        "entities": {"professional_name": "gonzález"}
    },
    {
        "message": "quiero cita con el blanco",
        "intent": "search_professional",
        "entities": {"professional_name": "blanco"}
    },
    {
        "message": "busco a la garcía",
        "intent": "search_professional",
        "entities": {"professional_name": "garcía"}
    },
    {
        "message": "sesión con pérez",
        "intent": "search_professional",
        "entities": {"professional_name": "pérez"}
    },
    
    # ==========================================
    # INTENT: VIEW_TOMORROW (5 ejemplos)
    # ==========================================
    
    {
        "message": "quiénes tienen disponible mañana",
        "intent": "view_tomorrow",
        "entities": {}
    },
    {
        "message": "disponibles mañana",
        "intent": "view_tomorrow",
        "entities": {}
    },
    {
        "message": "turnos libres mañana",
        "intent": "view_tomorrow",
        "entities": {}
    },
    {
        "message": "horarios mañana por la tarde",
        "intent": "view_tomorrow",
        "entities": {"horario": "tarde"}
    },
    {
        "message": "ver disponibles mañana por la mañana",
        "intent": "view_tomorrow",
        "entities": {"horario": "mañana"}
    },
    
    # ==========================================
    # INTENT: VIEW_MY_APPOINTMENTS (8 ejemplos)
    # ==========================================
    
    {
        "message": "ver mis turnos",
        "intent": "view_my_appointments",
        "entities": {}
    },
    {
        "message": "mis citas",
        "intent": "view_my_appointments",
        "entities": {}
    },
    {
        "message": "qué tengo agendado",
        "intent": "view_my_appointments",
        "entities": {}
    },
    {
        "message": "consultar mis turnos",
        "intent": "view_my_appointments",
        "entities": {}
    },
    {
        "message": "ver mi agenda",
        "intent": "view_my_appointments",
        "entities": {}
    },
    {
        "message": "mis reservas",
        "intent": "view_my_appointments",
        "entities": {}
    },
    {
        "message": "turnos agendados",
        "intent": "view_my_appointments",
        "entities": {}
    },
    {
        "message": "revisar mis citas",
        "intent": "view_my_appointments",
        "entities": {}
    },
    
    # ==========================================
    # INTENT: CANCEL_APPOINTMENT (5 ejemplos)
    # ==========================================
    
    {
        "message": "cancelar turno",
        "intent": "cancel_appointment",
        "entities": {}
    },
    {
        "message": "quiero anular mi cita",
        "intent": "cancel_appointment",
        "entities": {}
    },
    {
        "message": "necesito cancelar",
        "intent": "cancel_appointment",
        "entities": {}
    },
    {
        "message": "no puedo ir mañana",
        "intent": "cancel_appointment",
        "entities": {}
    },
    {
        "message": "borrar mi turno",
        "intent": "cancel_appointment",
        "entities": {}
    },
    
    # ==========================================
    # INTENT: INFO_CENTER (4 ejemplos)
    # ==========================================
    
    {
        "message": "información del centro",
        "intent": "info_center",
        "entities": {}
    },
    {
        "message": "dónde están ubicados",
        "intent": "info_center",
        "entities": {}
    },
    {
        "message": "horarios de atención",
        "intent": "info_center",
        "entities": {}
    },
    {
        "message": "datos de contacto",
        "intent": "info_center",
        "entities": {}
    },
    
    # ==========================================
    # INTENT: GREETING (6 ejemplos)
    # ==========================================
    
    {
        "message": "hola",
        "intent": "greeting",
        "entities": {}
    },
    {
        "message": "buenos días",
        "intent": "greeting",
        "entities": {}
    },
    {
        "message": "buenas tardes",
        "intent": "greeting",
        "entities": {}
    },
    {
        "message": "hey",
        "intent": "greeting",
        "entities": {}
    },
    {
        "message": "hola qué tal",
        "intent": "greeting",
        "entities": {}
    },
    {
        "message": "buenas",
        "intent": "greeting",
        "entities": {}
    },
    
    # ==========================================
    # INTENT: UNKNOWN (2 ejemplos - edge cases)
    # ==========================================
    
    {
        "message": "asdfasdf",
        "intent": "unknown",
        "entities": {}
    },
    {
        "message": "???",
        "intent": "unknown",
        "entities": {}
    },
    {
        "message": "nesesito turno pa mañana",
        "intent": "search_professional",
        "entities": {"fecha": "mañana"}
    },
    {
        "message": "quero cita pal jueves",
        "intent": "search_professional",
        "entities": {"fecha": "jueves"}
    },
    {
        "message": "teno q ver al dotor xa mañana",
        "intent": "search_professional",
        "entities": {"fecha": "mañana"}
    },

    # Días abreviados + contracciones
    {
        "message": "pa el vier tarde",
        "intent": "search_professional",
        "entities": {"fecha": "viernes", "horario": "tarde"}
    },
    {
        "message": "turno pal lun",
        "intent": "search_professional",
        "entities": {"fecha": "lunes"}
    },
    {
        "message": "cita pa el jue",
        "intent": "search_professional",
        "entities": {"fecha": "jueves"}
    },

    # Nombres con errores + contracciones
    {
        "message": "pa el vier con el lic fernandes",
        "intent": "search_professional",
        "entities": {"fecha": "viernes", "professional_name": "fernandes"}
    },
    {
        "message": "quero ver al dotor garsía",
        "intent": "search_professional",
        "entities": {"professional_name": "garcía"}
    },
    {
        "message": "nesesito turno con la dra lopes",
        "intent": "search_professional",
        "entities": {"professional_name": "lópez"}
    },

    # Mezcla completa
    {
        "message": "ola nesesito turno pa el miercolees xfa",
        "intent": "search_professional",
        "entities": {"fecha": "miércoles"}
    },
    {
        "message": "quero cita pal jue con la dra",
        "intent": "search_professional",
        "entities": {"fecha": "jueves"}
    },
    {
        "message": "turno xa el domigo",
        "intent": "search_professional",
        "entities": {"fecha": "domingo"}
    },

    # Sin tildes + typos
    {
        "message": "turno para el domigo con lopez",
        "intent": "search_professional",
        "entities": {"fecha": "domingo", "professional_name": "lópez"}
    },
    {
        "message": "nesesito al psicologo xa mañana",
        "intent": "search_professional",
        "entities": {"especialidad": "psicología", "fecha": "mañana"}
    },
    {
        "message": "quero nutricionista pal lune",
        "intent": "search_professional",
        "entities": {"especialidad": "nutrición", "fecha": "lunes"}
    },
    # Día + horario sin "por la"
    {
        "message": "viernes tarde",
        "intent": "search_professional",
        "entities": {"fecha": "viernes", "horario": "tarde"}
    },
    {
        "message": "jueves mañana",
        "intent": "search_professional",
        "entities": {"fecha": "jueves", "horario": "mañana"}
    },
    {
        "message": "lunes noche",
        "intent": "search_professional",
        "entities": {"fecha": "lunes", "horario": "noche"}
    },

    # Día abreviado + horario
    {
        "message": "vier tarde",
        "intent": "search_professional",
        "entities": {"fecha": "viernes", "horario": "tarde"}
    },
    {
        "message": "jue mañana",
        "intent": "search_professional",
        "entities": {"fecha": "jueves", "horario": "mañana"}
    },
    {
        "message": "lun tarde",
        "intent": "search_professional",
        "entities": {"fecha": "lunes", "horario": "tarde"}
    },

    # Con coma (como escribe la gente)
    {
        "message": "viernes, tarde",
        "intent": "search_professional",
        "entities": {"fecha": "viernes", "horario": "tarde"}
    },
    {
        "message": "jueves, mañana",
        "intent": "search_professional",
        "entities": {"fecha": "jueves", "horario": "mañana"}
    },
    {
        "message": "sábado, tarde",
        "intent": "search_professional",
        "entities": {"fecha": "sábado", "horario": "tarde"}
    },

    # Con "para"
    {
        "message": "para el viernes tarde",
        "intent": "search_professional",
        "entities": {"fecha": "viernes", "horario": "tarde"}
    },
    {
        "message": "pa el vier tarde",
        "intent": "search_professional",
        "entities": {"fecha": "viernes", "horario": "tarde"}
    },
    {
        "message": "pal jue mañana",
        "intent": "search_professional",
        "entities": {"fecha": "jueves", "horario": "mañana"}
    },

    # Turno explícito
    {
        "message": "turno viernes tarde",
        "intent": "search_professional",
        "entities": {"fecha": "viernes", "horario": "tarde"}
    },
    {
        "message": "cita jueves mañana",
        "intent": "search_professional",
        "entities": {"fecha": "jueves", "horario": "mañana"}
    },
    {
        "message": "necesito lunes tarde",
        "intent": "search_professional",
        "entities": {"fecha": "lunes", "horario": "tarde"}
    },
]


# ==========================================
# VALIDACIÓN DEL DATASET
# ==========================================

def validate_dataset():
    """Valida que el dataset esté bien formado."""
    
    print("="*60)
    print("VALIDACIÓN DEL DATASET BASE")
    print("="*60)
    
    # Contar por intent
    from collections import Counter
    intents = Counter(ex['intent'] for ex in DATASET_BASE)
    
    print(f"\n📊 Total de ejemplos: {len(DATASET_BASE)}")
    print(f"\n📋 Distribución por intent:")
    for intent, count in intents.most_common():
        percentage = (count / len(DATASET_BASE)) * 100
        print(f"   {intent:25s}: {count:2d} ({percentage:5.1f}%)")
    
    # Verificar estructura
    print(f"\n✅ Estructura:")
    required_keys = {'message', 'intent', 'entities'}
    for i, ex in enumerate(DATASET_BASE):
        if not required_keys.issubset(ex.keys()):
            print(f"   ❌ Ejemplo {i} tiene estructura incorrecta")
            return False
        
        if not ex['message']:
            print(f"   ❌ Ejemplo {i} tiene mensaje vacío")
            return False
    
    print(f"   ✅ Todos los ejemplos tienen estructura correcta")
    
    # Verificar entidades
    all_entity_types = set()
    for ex in DATASET_BASE:
        all_entity_types.update(ex['entities'].keys())
    
    print(f"\n🏷️ Tipos de entidades encontradas:")
    for entity_type in sorted(all_entity_types):
        count = sum(1 for ex in DATASET_BASE if entity_type in ex['entities'])
        print(f"   {entity_type:20s}: {count:2d} ejemplos")
    
    print(f"\n✅ Dataset validado correctamente")
    return True


# ==========================================
# EXPORTAR A JSONL
# ==========================================

def export_to_jsonl(output_file: str = "dataset_base.jsonl"):
    """Exporta el dataset a formato JSONL."""
    import json
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for example in DATASET_BASE:
            f.write(json.dumps(example, ensure_ascii=False) + '\n')
    
    print(f"\n💾 Dataset exportado: {output_file}")


# ==========================================
# MAIN
# ==========================================

if __name__ == "__main__":
    validate_dataset()
    export_to_jsonl()
    
    print("\n" + "="*60)
    print("⭐ CAMBIOS EN VERSIÓN 2.0")
    print("="*60)
    print("\n✅ Agregados 15 nuevos ejemplos:")
    print("   - 5 con días de semana (martes, miércoles, jueves...)")
    print("   - 5 con títulos variados (dr, dra, lic, doctor...)")
    print("   - 5 con solo apellidos (Blanco, González, García...)")
    print("\n📊 Total: 65 ejemplos base → ~1,300 con augmentation")
    
    print("\n" + "="*60)
    print("PRÓXIMO PASO")
    print("="*60)
    print("\n🔄 Ahora ejecuta:")
    print("   python generate_training_dataset.py")
    print("\n🎯 Resultado: 65 → 1,300 ejemplos listos para ML")