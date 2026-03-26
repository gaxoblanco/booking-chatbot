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
    # INTENT: SEARCH_PROFESSIONAL (38 ejemplos)
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

    # --- DÍAS DE SEMANA (5 ejemplos) ---

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

    # --- NOMBRES CON TÍTULOS VARIADOS (5 ejemplos) ---

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

    # --- SOLO APELLIDOS (5 ejemplos) ---

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
    # --- Solo con intencion (3 ejemplos) ---
    {"message": "quiero turno", "intent": "search_professional", "entities": {}},
    {"message": "necesito cita", "intent": "search_professional", "entities": {}},
    {"message": "busco algo virtual para esta semana", "intent": "search_professional", "entities": {"modalidad": "virtual", "fecha": "esta_semana"}},

    # ==========================================
    # INTENT: VIEW_TOMORROW (8 ejemplos)
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
    {"message": "qué hay disponible para mañana", "intent": "view_tomorrow", "entities": {}},
    {"message": "tenés algo mañana", "intent": "view_tomorrow", "entities": {}},
    {"message": "para el día de mañana qué tienen", "intent": "view_tomorrow", "entities": {}},

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
    # INTENT: CANCEL_APPOINTMENT (10 ejemplos)
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
    {"message": "quiero cancelar mi turno de mañana", "intent": "cancel_appointment", "entities": {}},
    {"message": "no voy a poder ir", "intent": "cancel_appointment", "entities": {}},
    {"message": "cancelo el turno con martínez", "intent": "cancel_appointment", "entities": {}},
    {"message": "me arrepentí del turno", "intent": "cancel_appointment", "entities": {}},
    {"message": "quiero dar de baja mi cita", "intent": "cancel_appointment", "entities": {}},

    # ==========================================
    # INTENT: INFO_CENTER (8 ejemplos)
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
    {"message": "cómo los contacto", "intent": "info_center", "entities": {}},
    {"message": "tienen página web", "intent": "info_center", "entities": {}},
    {"message": "quiero saber más del centro", "intent": "info_center", "entities": {}},
    {"message": "me podés dar info del lugar", "intent": "info_center", "entities": {}},

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
    # INTENT: UNKNOWN (10 ejemplos)
    # Mensajes de pacientes fuera del alcance del sistema
    # ==========================================

    {"message": "asdfasdf", "intent": "unknown", "entities": {}},
    {"message": "???", "intent": "unknown", "entities": {}},
    {"message": "cuánto sale la consulta", "intent": "unknown", "entities": {}},
    {"message": "el teléfono del consultorio",
        "intent": "unknown", "entities": {}},
    {"message": "aceptan IOMA", "intent": "unknown", "entities": {}},
    {"message": "tienen estacionamiento", "intent": "unknown", "entities": {}},
    {"message": "cómo llego al consultorio", "intent": "unknown", "entities": {}},
    {"message": "trabajan los sábados", "intent": "unknown", "entities": {}},
    {"message": "puedo pagar con tarjeta", "intent": "unknown", "entities": {}},
    {"message": "cuánto cuesta una sesión", "intent": "unknown", "entities": {}},
    {"message": "tienen psicólogos infantiles", "intent": "unknown", "entities": {}},
    {"message": "aceptan efectivo", "intent": "unknown", "entities": {}},
    {"message": "cuánto dura la consulta", "intent": "unknown", "entities": {}},
    {"message": "con qué obras sociales trabajan", "intent": "unknown", "entities": {}},
    # ==========================================
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
    # ==========================================================================
    # INTENT: AGENDA_VIEW_READY
    # Contexto: profesional revisando el análisis de importación de agenda.
    # Quiere ver los pacientes listos para cargar (sin conflictos).
    # Prefijo: [PROF_AGENDA_IMPORT_REVIEW]
    # ==========================================================================

    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] ver listos",
        "intent": "agenda_view_ready",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] mostrame los listos",
        "intent": "agenda_view_ready",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] cuáles se pueden cargar",
        "intent": "agenda_view_ready",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] ver los nuevos",
        "intent": "agenda_view_ready",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] mostrame los pacientes nuevos",
        "intent": "agenda_view_ready",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] qué está listo",
        "intent": "agenda_view_ready",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] ver los que entran",
        "intent": "agenda_view_ready",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] mostrame los ok",
        "intent": "agenda_view_ready",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] cuántos están listos",
        "intent": "agenda_view_ready",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] ver disponibles para cargar",
        "intent": "agenda_view_ready",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] los que están bien",
        "intent": "agenda_view_ready",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] mostrame los sin problema",
        "intent": "agenda_view_ready",
        "entities": {}
    },

    # ==========================================================================
    # INTENT: AGENDA_VIEW_OVERLAPS
    # Contexto: profesional quiere ver los pacientes con solapamiento de horario.
    # Prefijo: [PROF_AGENDA_IMPORT_REVIEW]
    # ==========================================================================

    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] ver solapamientos",
        "intent": "agenda_view_overlaps",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] mostrame los solapados",
        "intent": "agenda_view_overlaps",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] cuáles se superponen",
        "intent": "agenda_view_overlaps",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] ver los conflictos de horario",
        "intent": "agenda_view_overlaps",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] hay solapamientos",
        "intent": "agenda_view_overlaps",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] mostrame los que se pisan",
        "intent": "agenda_view_overlaps",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] ver superposiciones",
        "intent": "agenda_view_overlaps",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] cuáles tienen conflicto",
        "intent": "agenda_view_overlaps",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] ver los que chocan",
        "intent": "agenda_view_overlaps",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] solapamientos",
        "intent": "agenda_view_overlaps",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] los que se superponen",
        "intent": "agenda_view_overlaps",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] mostrame los problemas de horario",
        "intent": "agenda_view_overlaps",
        "entities": {}
    },

    # ==========================================================================
    # INTENT: AGENDA_VIEW_EXISTING
    # Contexto: profesional quiere ver los pacientes que ya estaban cargados.
    # Prefijo: [PROF_AGENDA_IMPORT_REVIEW]
    # ==========================================================================

    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] ver existentes",
        "intent": "agenda_view_existing",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] mostrame los que ya están",
        "intent": "agenda_view_existing",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] cuáles ya estaban cargados",
        "intent": "agenda_view_existing",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] ver los duplicados",
        "intent": "agenda_view_existing",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] los repetidos",
        "intent": "agenda_view_existing",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] mostrame los que ya tenía",
        "intent": "agenda_view_existing",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] ya existen algunos",
        "intent": "agenda_view_existing",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] ver los que ya cargué",
        "intent": "agenda_view_existing",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] existentes",
        "intent": "agenda_view_existing",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] cuáles ya estaban en el sistema",
        "intent": "agenda_view_existing",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] mostrame los repetidos",
        "intent": "agenda_view_existing",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] ver los que ya están registrados",
        "intent": "agenda_view_existing",
        "entities": {}
    },

    # ==========================================================================
    # INTENT: AGENDA_VIEW_ERRORS
    # Contexto: profesional quiere ver las filas con datos inválidos.
    # Prefijo: [PROF_AGENDA_IMPORT_REVIEW]
    # ==========================================================================

    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] ver errores",
        "intent": "agenda_view_errors",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] mostrame los errores",
        "intent": "agenda_view_errors",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] qué falló",
        "intent": "agenda_view_errors",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] cuáles tienen error",
        "intent": "agenda_view_errors",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] ver los inválidos",
        "intent": "agenda_view_errors",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] mostrame los que fallaron",
        "intent": "agenda_view_errors",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] qué no se puede cargar",
        "intent": "agenda_view_errors",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] errores",
        "intent": "agenda_view_errors",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] ver los problemas",
        "intent": "agenda_view_errors",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] cuántos errores hay",
        "intent": "agenda_view_errors",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] qué está mal",
        "intent": "agenda_view_errors",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] mostrame los datos incorrectos",
        "intent": "agenda_view_errors",
        "entities": {}
    },

    # ==========================================================================
    # INTENT: AGENDA_CONFIRM_UPLOAD
    # Contexto: profesional confirma que quiere cargar los pacientes listos.
    # 15 ejemplos porque "sí", "ok", "dale" son muy ambiguos fuera de contexto.
    # Prefijo: [PROF_AGENDA_IMPORT_REVIEW]
    # ==========================================================================

    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] sí",
        "intent": "agenda_confirm_upload",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] si",
        "intent": "agenda_confirm_upload",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] dale",
        "intent": "agenda_confirm_upload",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] ok",
        "intent": "agenda_confirm_upload",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] cargar",
        "intent": "agenda_confirm_upload",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] confirmar",
        "intent": "agenda_confirm_upload",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] confirmo",
        "intent": "agenda_confirm_upload",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] adelante",
        "intent": "agenda_confirm_upload",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] sí cargar",
        "intent": "agenda_confirm_upload",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] cargá los pacientes",
        "intent": "agenda_confirm_upload",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] va",
        "intent": "agenda_confirm_upload",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] bueno",
        "intent": "agenda_confirm_upload",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] sí, cargá",
        "intent": "agenda_confirm_upload",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] listo cargá",
        "intent": "agenda_confirm_upload",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] proceder",
        "intent": "agenda_confirm_upload",
        "entities": {}
    },

    # ==========================================================================
    # INTENT: AGENDA_CANCEL_UPLOAD
    # Contexto: profesional no quiere proceder con la carga.
    # 15 ejemplos por la misma ambigüedad de "no", "volver", "salir".
    # Prefijo: [PROF_AGENDA_IMPORT_REVIEW]
    # ==========================================================================

    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] no",
        "intent": "agenda_cancel_upload",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] cancelar",
        "intent": "agenda_cancel_upload",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] cancelo",
        "intent": "agenda_cancel_upload",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] no cargar",
        "intent": "agenda_cancel_upload",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] no quiero",
        "intent": "agenda_cancel_upload",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] dejá",
        "intent": "agenda_cancel_upload",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] no gracias",
        "intent": "agenda_cancel_upload",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] cancelá",
        "intent": "agenda_cancel_upload",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] me arrepentí",
        "intent": "agenda_cancel_upload",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] volver",
        "intent": "agenda_cancel_upload",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] salir",
        "intent": "agenda_cancel_upload",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] no lo cargo",
        "intent": "agenda_cancel_upload",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] lo corrijo primero",
        "intent": "agenda_cancel_upload",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] hay muchos errores",
        "intent": "agenda_cancel_upload",
        "entities": {}
    },
    {
        "message": "[PROF_AGENDA_IMPORT_REVIEW] no proceder",
        "intent": "agenda_cancel_upload",
        "entities": {}
    },
    # ==========================================================================
    # INTENT: BOOK_FOR_THIRD_PARTY
    # Sin prefijo — aplica en los mismos estados que search_professional.
    # 25 ejemplos cubriendo relaciones familiares rioplatenses.
    # Casos: relación sola, + especialidad, + nombre con/sin título, + fecha,
    # jerga rioplatense, sin posesivo.
    # ==========================================================================

    # --- Relación sola ---
    {"message": "quiero turno para mi hijo", "intent": "book_for_third_party", "entities": {"third_party_relation": "hijo"}},
    {"message": "necesito sesión para mi mamá", "intent": "book_for_third_party", "entities": {"third_party_relation": "mamá"}},
    {"message": "turno para mi papá", "intent": "book_for_third_party", "entities": {"third_party_relation": "papá"}},
    {"message": "no es para mí es para mi marido", "intent": "book_for_third_party", "entities": {"third_party_relation": "marido"}},
    {"message": "mi hijo necesita sesión", "intent": "book_for_third_party", "entities": {"third_party_relation": "hijo"}},
    {"message": "turno para mi hermana", "intent": "book_for_third_party", "entities": {"third_party_relation": "hermana"}},
    {"message": "es para mi abuelo", "intent": "book_for_third_party", "entities": {"third_party_relation": "abuelo"}},
    {"message": "quiero agendar para un familiar", "intent": "book_for_third_party", "entities": {}},
    {"message": "turno para otra persona", "intent": "book_for_third_party", "entities": {}},
    {"message": "es para mi tía", "intent": "book_for_third_party", "entities": {"third_party_relation": "tía"}},
    {"message": "necesito turno para mi pareja", "intent": "book_for_third_party", "entities": {"third_party_relation": "pareja"}},
    {"message": "turno para mi sobrino", "intent": "book_for_third_party", "entities": {"third_party_relation": "sobrino"}},

    # --- Jerga rioplatense ---
    {"message": "es para mi nena de 10 años", "intent": "book_for_third_party", "entities": {"third_party_relation": "hija"}},
    {"message": "turno para mi nene", "intent": "book_for_third_party", "entities": {"third_party_relation": "hijo"}},
    {"message": "quiero llevar a mi vieja al psicólogo", "intent": "book_for_third_party", "entities": {"third_party_relation": "mamá"}},
    {"message": "mi mamá mayor necesita sesión", "intent": "book_for_third_party", "entities": {"third_party_relation": "mamá"}},
    {"message": "es para mi pibe", "intent": "book_for_third_party", "entities": {"third_party_relation": "hijo"}},
    {"message": "mi viejo necesita turno", "intent": "book_for_third_party", "entities": {"third_party_relation": "papá"}},

    # --- Relación + especialidad ---
    {"message": "busco psicóloga para mi hija", "intent": "book_for_third_party", "entities": {"third_party_relation": "hija"}},
    {"message": "necesito nutricionista para mi mamá", "intent": "book_for_third_party", "entities": {"third_party_relation": "mamá"}},

    # --- Relación + nombre con título ---
    {"message": "quiero turno con la Dra López para mi hijo", "intent": "book_for_third_party", "entities": {"third_party_relation": "hijo", "professional_name": "lópez"}},
    {"message": "para mi viejo con el dr blanco", "intent": "book_for_third_party", "entities": {"third_party_relation": "papá"}},

    # --- Relación + nombre sin título (el bug actual) ---
    {"message": "quiero un turno para mi hijo con gaston", "intent": "book_for_third_party", "entities": {"third_party_relation": "hijo"}},
    {"message": "turno para mi mamá con martinez", "intent": "book_for_third_party", "entities": {"third_party_relation": "mamá"}},
    {"message": "mi nene con rodriguez para la semana que viene", "intent": "book_for_third_party", "entities": {"third_party_relation": "hijo"}},

    # --- Relación + fecha ---
    {"message": "turno para mi hijo para mañana", "intent": "book_for_third_party", "entities": {"third_party_relation": "hijo", "fecha": "mañana"}},
    {"message": "necesito para mi hermana el jueves", "intent": "book_for_third_party", "entities": {"third_party_relation": "hermana", "fecha": "jueves"}},
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
    from collections import Counter

    ok = validate_dataset()

    if ok:
        export_to_jsonl()

        intents = Counter(ex['intent'] for ex in DATASET_BASE)
        total = len(DATASET_BASE)

        print("\n" + "="*60)
        print(
            f"DATASET BASE v3.0 — {total} ejemplos, {len(intents)} intenciones")
        print("="*60)
        print(f"\n{'Intención':<35} {'Ejemplos':>8}   {'%':>5}")
        print("-" * 54)
        for intent, count in intents.most_common():
            bar = "█" * count
            pct = count / total * 100
            print(f"  {intent:<33} {count:>8}  {pct:>5.1f}%  {bar}")
        print("-" * 54)
        print(f"  {'TOTAL':<33} {total:>8}")
        print(
            f"\n  Con augmentation (~20x): ~{total * 20:,} ejemplos esperados")

        print("\n" + "="*60)
        print("PRÓXIMO PASO")
        print("="*60)
        print("\n  python generate_training_dataset.py")
