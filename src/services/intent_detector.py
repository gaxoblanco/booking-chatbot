"""
Intent Detector v1.0
====================
Sistema simple de detección de intenciones basado en reglas y keywords.

Este módulo detecta la intención del usuario y extrae entidades relevantes
para acortar el flujo conversacional.

INTENCIONES SOPORTADAS:
- SEARCH_PROFESSIONAL: Buscar profesional con filtros
- VIEW_TOMORROW: Ver disponibles mañana
- VIEW_MY_APPOINTMENTS: Ver mis citas
- INFO_CENTER: Información del centro
- GREETING: Saludo simple sin intención clara

ENTIDADES EXTRAÍDAS:
- fecha: (hoy, mañana, fecha específica)
- horario: (mañana, tarde, noche)
- zona: (norte, sur, centro, online)
- especialidad: (psicología, nutrición, etc)
- modalidad: (presencial, virtual)

Uso:
    >>> detector = IntentDetector()
    >>> result = detector.detect("necesito psicólogo mañana por la tarde en palermo")
    >>> print(result)
    {
        'intent': 'SEARCH_PROFESSIONAL',
        'confidence': 0.9,
        'entities': {
            'especialidad': 'psicología',
            'fecha': 'mañana',
            'horario': 'tarde',
            'zona': 'palermo'
        },
        'can_shortcut': True
    }
"""

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from enum import Enum


class Intent(Enum):
    """Intenciones detectables."""
    SEARCH_PROFESSIONAL = "search_professional"
    VIEW_TOMORROW = "view_tomorrow"
    VIEW_MY_APPOINTMENTS = "view_my_appointments"
    CANCEL_APPOINTMENT = "cancel_appointment"  # ⭐ NUEVO
    INFO_CENTER = "info_center"
    GREETING = "greeting"
    UNKNOWN = "unknown"


class IntentDetector:
    """
    Detector de intenciones basado en reglas.
    
    Analiza el mensaje del usuario y detecta:
    1. Intención principal
    2. Entidades mencionadas
    3. Nivel de confianza
    4. Si puede hacer shortcut (omitir menú)
    """
    
    def __init__(self):
        """Inicializar detector con patrones y keywords."""
        self._setup_patterns()
    
    def _setup_patterns(self):
        """Configurar patrones de detección."""
        
        # ==========================================
        # KEYWORDS DE INTENCIONES
        # ==========================================
        
        self.search_keywords = [
            'buscar', 'busco', 'necesito', 'quiero', 'quisiera',
            'buscando', 'encontrar', 'conseguir', 'agendar',
            'reservar', 'turno', 'cita', 'sesión', 'consulta',
            'sacar turno', 'pedir turno', 'coordinar'
        ]
        
        self.tomorrow_keywords = [
            'disponibles mañana', 'disponibles manana',
            'horarios mañana', 'horarios manana', 
            'turnos mañana', 'turnos manana',
            'libres mañana', 'libres manana'
        ]
        
        self.appointments_keywords = [
            'mis turnos', 'mis citas', 'ver mis turnos',
            'ver mis citas', 'mis reservas', 'turnos agendados',
            'citas programadas', 'agenda', 'agendados',
            'ver turnos', 'ver citas', 'mis consultas',
            'consultar turnos', 'consultar citas', 'revisar turnos',
            'revisar citas', 'ver agenda', 'mi agenda'
        ]
        
        # ⭐ NUEVO: Keywords de cancelación
        self.cancel_keywords = [
            'cancelar', 'anular', 'borrar turno', 'eliminar turno',
            'borrar cita', 'eliminar cita', 'cancelar turno',
            'cancelar cita', 'no voy a ir', 'no puedo ir',
            'quiero cancelar', 'necesito cancelar'
        ]
        
        self.info_keywords = [
            'información', 'info', 'sobre el centro',
            'conocer más', 'datos', 'contacto', 'ubicación',
            'horarios de atención', 'dónde están'
        ]
        
        # ==========================================
        # KEYWORDS PARA FILTRO POR PROFESIONAL
        # ==========================================
        
        self.professional_keywords = [
            'con', 'dr', 'dra', 'doctor', 'doctora',
            'lic', 'licenciado', 'licenciada',
            'profesional'
        ]
        
        # ==========================================
        # KEYWORDS DE ENTIDADES
        # ==========================================
        
        # Especialidades (con y sin tildes)
        # IMPORTANTE: Palabras más específicas primero para evitar falsos positivos
        self.especialidades = {
            'psicología': ['psicólogo', 'psicóloga', 'psicologo', 'psicologa', 
                          'psicología', 'psicologia', 'terapeuta', 'terapia psicológica', 
                          'terapia psicologica', 'psico'],
            'nutrición': ['nutricionista', 'nutri', 'nutrición', 'nutricion', 'dietista'],
            'kinesiología': ['kinesiólogo', 'kinesióloga', 'kinesiologo', 'kinesiologia', 
                           'kine', 'fisioterapia', 'fisioterapeuta'],
            'fonoaudiología': ['fonoaudiólogo', 'fonoaudiologo', 'fono'],
            'terapia ocupacional': ['terapia ocupacional', 'terapeuta ocupacional', 't.o.'],
        }
        
        # Zonas (con y sin tildes)
        self.zonas = {
            'norte': ['palermo', 'belgrano', 'nuñez', 'nunez', 'saavedra', 'colegiales', 'zona norte', 'norte'],
            'sur': ['barracas', 'pompeya', 'parque patricios', 'zona sur', 'sur'],
            'centro': ['centro', 'microcentro', 'retiro', 'monserrat', 'san nicolás', 'san nicolas'],
            'oeste': ['caballito', 'flores', 'villa crespo', 'paternal', 'zona oeste', 'oeste'],
            'online': ['online', 'virtual', 'videollamada', 'zoom', 'a distancia', 'remoto'],
        }
        
        # Horarios (con y sin tildes)
        self.horarios = {
            'mañana': ['por la mañana', 'por la manana', 'en la mañana', 'en la manana', 'de mañana', 'temprano', 'am', 'antes del mediodía', 'antes del mediodia'],
            'tarde': ['tarde', 'por la tarde', 'después del mediodía', 'despues del mediodia', 'pm'],
            'noche': ['noche', 'por la noche', 'nocturno', 'después de las 6', 'despues de las 6'],
        }
        
        # ⭐ NUEVO: Género del profesional
        self.generos = {
            'femenino': ['mujer', 'femenino', 'femenina', 'doctora', 'dra', 'licenciada', 'profesional mujer'],
            'masculino': ['hombre', 'masculino', 'varon', 'varón', 'doctor', 'dr', 'licenciado', 'profesional hombre'],
        }
        
        # ⭐ NUEVO: Prepaga / Obra Social
        self.prepaga_keywords = [
            'prepaga', 'obra social', 'obra-social',
            'osde', 'swiss medical', 'galeno', 'medicus',
            'que acepte', 'acepta prepaga', 'acepta obra',
            'con prepaga', 'con obra social'
        ]
        
        # Modalidad
        self.modalidades = {
            'presencial': ['presencial', 'en consultorio', 'en persona', 'cara a cara'],
            'virtual': ['virtual', 'online', 'videollamada', 'remoto', 'zoom', 'meet'],
        }
        
        # Fechas relativas (con y sin tildes)
        self.fechas_relativas = {
            'hoy': ['hoy', 'para hoy', 'ahora', 'ya'],
            'mañana': ['mañana', 'manana', 'para mañana', 'para manana'],
            'pasado_mañana': ['pasado mañana', 'pasado manana'],
            'esta_semana': ['esta semana'],
            'próxima_semana': ['próxima semana', 'proxima semana', 'semana que viene', 'la semana que viene'],
        }

    def _normalize_text(self, message: str) -> str:
        """
        Normaliza texto para casos de mensajes complejos.
        Expande contracciones y corrige errores comunes.
        """
        msg = ' ' + message.lower() + ' '  # Espacios para match exacto
        
        # Expandir contracciones y errores comunes
        replacements = {
            # Contracciones
            ' pa ': ' para ',
            ' pal ': ' para el ',
            ' xa ': ' para ',
            ' q ': ' que ',
            ' xq ': ' porque ',
            ' xfa ': ' por favor ',
            ' bn ': ' bien ',
            ' tmb ': ' también ',
            
            # Errores fonéticos
            ' nesesito ': ' necesito ',
            ' nececito ': ' necesito ',
            ' quero ': ' quiero ',
            ' quier ': ' quiero ',
            ' teno ': ' tengo ',
            ' aora ': ' ahora ',
            ' aber ': ' a ver ',
            
            # ⭐ NUEVO: Títulos abreviados
            ' lic ': ' licenciado ',
            ' lic. ': ' licenciado ',
            ' dr ': ' doctor ',
            ' dr. ': ' doctor ',
            ' dra ': ' doctora ',
            ' dra. ': ' doctora ',
            ' dc ': ' doctor ',
            ' dc. ': ' doctor ',
            ' dotor ': ' doctor ',
            ' dotora ': ' doctora ',
            
            # Títulos mal escritos
            ' licen ': ' licenciado ',
            ' licdo ': ' licenciado ',
            
            # Días abreviados
            ' lun ': ' lunes ',
            ' lune ': ' lunes ',
            ' mar ': ' martes ',
            ' mier ': ' miércoles ',
            ' jue ': ' jueves ',
            ' vier ': ' viernes ',
            ' vie ': ' viernes ',
            ' sab ': ' sábado ',
            ' dom ': ' domingo ',
        }
        
        for old, new in replacements.items():
            msg = msg.replace(old, new)
        
        return msg.strip()
    
    def detect(self, message: str, context: Optional[Dict] = None) -> Dict:
        """
        Detecta intención y extrae entidades del mensaje.
        
        Args:
            message: Mensaje del usuario
            context: Contexto opcional (rol, estado previo, etc)
            
        Returns:
            {
                'intent': Intent,
                'confidence': float (0-1),
                'entities': dict,
                'can_shortcut': bool,
                'missing_entities': list
            }
        """
        message_lower = message.lower().strip()
        message_normalized = self._normalize_text(message_lower)
        
        print(f"[NLU] Original: {message_lower}")
        print(f"[NLU] Normalizado: {message_normalized}")
        
        # Resultado inicial
        result = {
            'intent': Intent.UNKNOWN,
            'confidence': 0.0,
            'entities': {},
            'can_shortcut': False,
            'missing_entities': []
        }
        
        # ==========================================
        # 1. DETECTAR INTENCIÓN PRINCIPAL
        # ==========================================
        
        intent, confidence = self._detect_intent(message_normalized)
        result['intent'] = intent
        result['confidence'] = confidence
        
        # ==========================================
        # 2. EXTRAER ENTIDADES (SIEMPRE)
        # ==========================================
        
        # ⭐ CAMBIO: Extraer entidades SIEMPRE, no solo para intents específicos
        entities = self._extract_entities(message_normalized)
        result['entities'] = entities
        
        print(f"[NLU] 📋 Entities extracted:")
        for key, value in entities.items():
            print(f"[NLU]    {key}: {value}")
        
        # ==========================================
        # 3. DETERMINAR SHORTCUT
        # ==========================================
        
        if intent in [Intent.SEARCH_PROFESSIONAL, Intent.VIEW_TOMORROW]:
            result['can_shortcut'], result['missing_entities'] = self._can_shortcut(
                intent, entities
            )
        
        return result
    
    def _detect_intent(self, message: str) -> tuple:
        """
        Detecta la intención principal del mensaje.
        
        Returns:
            (Intent, confidence)
        """
        # Prioridad 1: Ver citas
        if self._contains_any(message, self.appointments_keywords):
            return Intent.VIEW_MY_APPOINTMENTS, 0.95
        
        # Prioridad 2: Cancelar turno  ⭐ NUEVO
        if self._contains_any(message, self.cancel_keywords):
            return Intent.CANCEL_APPOINTMENT, 0.95
        
        # Prioridad 3: Ver disponibles mañana
        if self._contains_any(message, self.tomorrow_keywords):
            return Intent.VIEW_TOMORROW, 0.9
        
        # Prioridad 4: Información del centro
        if self._contains_any(message, self.info_keywords):
            return Intent.INFO_CENTER, 0.9
        
        # Prioridad 5: Búsqueda de profesional
        # (es la más común, así que tiene keywords más amplios)
        if self._contains_any(message, self.search_keywords):
            return Intent.SEARCH_PROFESSIONAL, 0.85
        
        # Si menciona especialidad o zona, asumir búsqueda
        if self._extract_especialidad(message) or self._extract_zona(message):
            return Intent.SEARCH_PROFESSIONAL, 0.8
        
        # Prioridad 5: Solo saludo
        if self._is_greeting(message):
            return Intent.GREETING, 0.9
        
        # Desconocido
        return Intent.UNKNOWN, 0.0
    
    def _extract_entities(self, message: str) -> Dict:
        """
        Extrae entidades del mensaje.
        
        Returns:
            Dict con entidades encontradas
        """
        entities = {}
        
        # Especialidad
        especialidad = self._extract_especialidad(message)
        if especialidad:
            entities['especialidad'] = especialidad
        
        # Zona
        zona = self._extract_zona(message)
        if zona:
            entities['zona'] = zona
        
        # Fecha
        fecha = self._extract_fecha(message)
        if fecha:
            entities['fecha'] = fecha
        
        # Horario
        horario = self._extract_horario(message)
        if horario:
            entities['horario'] = horario
        
        # Modalidad
        modalidad = self._extract_modalidad(message)
        if modalidad:
            entities['modalidad'] = modalidad
        
        # Género
        genero = self._extract_genero(message)
        if genero:
            entities['genero'] = genero
        
        # Prepaga
        prepaga = self._extract_prepaga(message)
        if prepaga:
            entities['prepaga'] = prepaga
        
        # ⭐ CRÍTICO: Nombre de profesional
        professional_name = self._extract_professional_name(message)
        if professional_name:
            entities['professional_name'] = professional_name
            print(f"[NLU] ✅ Professional name detectado: {professional_name}")
        else:
            print(f"[NLU] ⚠️ No se detectó nombre de profesional")
        
        return entities

    def _extract_especialidad(self, message: str) -> Optional[str]:
        """
        Extrae especialidad mencionada.
        
        Busca keywords de especialidades, pero evita falsos positivos
        con palabras comunes como 'ayuda'.
        """
        # Palabras que NO deben considerarse como especialidades
        excluded_words = ['ayuda', 'ayudar', 'ayudame', 'help']
        
        # Si el mensaje es muy corto y solo contiene palabras excluidas, no buscar
        if any(excluded in message for excluded in excluded_words):
            # Solo si el mensaje es principalmente esa palabra
            words = message.split()
            if len(words) <= 3:  # Mensajes cortos como "necesito ayuda"
                return None
        
        # Buscar especialidades en orden (más específicas primero)
        for especialidad, keywords in self.especialidades.items():
            if self._contains_any(message, keywords):
                return especialidad
        return None
    
    def _extract_zona(self, message: str) -> Optional[str]:
        """Extrae zona mencionada."""
        for zona, keywords in self.zonas.items():
            if self._contains_any(message, keywords):
                return zona
        return None
    
    def _extract_fecha(self, message: str) -> Optional[str]:
        """
        Extrae fecha mencionada.
        
        Puede ser:
        - Relativa: "hoy", "mañana", "pasado mañana"
        - Absoluta numérica: "25/12", "25/12/2026"
        - Absoluta texto: "15 de febrero", "25 de diciembre"
        
        IMPORTANTE: Buscar frases completas PRIMERO para evitar falsos positivos
        (ej: "pasado mañana" debe detectarse antes que "mañana")
        
        Valida que las fechas absolutas sean válidas (ej: no acepta 31 de febrero)
        """
        # ⭐ IMPORTANTE: Buscar frases MÁS LARGAS primero
        # Esto evita que "mañana" capture "pasado mañana"
        ordered_fechas = [
            ('pasado_mañana', ['pasado mañana', 'pasado manana']),
            ('próxima_semana', ['próxima semana', 'proxima semana', 'semana que viene', 'la semana que viene']),
            ('esta_semana', ['esta semana']),
            ('mañana', ['mañana', 'manana', 'para mañana', 'para manana']),  # Después de "pasado mañana"
            ('hoy', ['hoy', 'para hoy', 'ahora', 'ya']),
            ('ayer', ['ayer', 'para ayer']),  # Siempre será rechazada
        ]

        dias_semana_map = {
            # Lunes + variantes
            'lunes': 0, 'lune': 0, 'lnes': 0, 'lun': 0,
            
            # Martes + variantes
            'martes': 1, 'marte': 1, 'marts': 1, 'mar': 1,
            
            # Miércoles + variantes
            'miércoles': 2, 'miercoles': 2, 'miercolees': 2, 'miercols': 2, 
            'miercol': 2, 'mier': 2, 'mx': 2,
            
            # Jueves + variantes
            'jueves': 3, 'juebe': 3, 'juebes': 3, 'juves': 3, 
            'jue': 3, 'juev': 3,
            
            # Viernes + variantes
            'viernes': 4, 'vierne': 4, 'biernes': 4, 'bierne': 4,
            'vier': 4, 'vie': 4,
            
            # Sábado + variantes
            'sábado': 5, 'sabado': 5, 'savado': 5, 'sabdo': 5,
            'sab': 5, 'sabao': 5,
            
            # Domingo + variantes
            'domingo': 6, 'domigo': 6, 'domino': 6, 'domgo': 6,
            'dom': 6, 'dgo': 6,
        }

        for dia_nombre, dia_numero in dias_semana_map.items():
            # Patrones que indican "próximo X día"
            patrones_dia = [
                f'{dia_nombre} que viene',
                f'el {dia_nombre}',
                f'para el {dia_nombre}',
                f'pa el {dia_nombre}',        # ⭐ NUEVO
                f'pal {dia_nombre}',           # ⭐ NUEVO
                f'xa el {dia_nombre}',         # ⭐ NUEVO
                f'próximo {dia_nombre}',
                f'proximo {dia_nombre}',
                f'este {dia_nombre}',
            ]
            
            # Verificar si algún patrón está en el mensaje
            if any(patron in message for patron in patrones_dia):
                # Calcular próximo día de esa semana
                today = datetime.now().date()
                current_weekday = today.weekday()  # 0=lunes, 6=domingo
                
                days_ahead = dia_numero - current_weekday
                
                # Si el día ya pasó esta semana, ir a la próxima semana
                if days_ahead <= 0:
                    days_ahead += 7
                
                target_date = today + timedelta(days=days_ahead)
                fecha_str = target_date.strftime('%Y-%m-%d')
                
                print(f"[NLU] Día de semana detectado: '{dia_nombre}' → {fecha_str} ({target_date.strftime('%d/%m')})")
                return fecha_str
        
        # Buscar en orden de especificidad (más largas primero)
        for fecha_key, keywords in ordered_fechas:
            for keyword in keywords:
                if keyword in message:
                    print(f"[NLU] Fecha detectada: '{keyword}' → {fecha_key}")
                    
                    # ⭐ VALIDACIÓN: "ayer" siempre es fecha pasada
                    if fecha_key == 'ayer':
                        print(f"[NLU] ⚠️ 'ayer' es fecha pasada, rechazando")
                        return 'fecha_pasada'
                    
                    return fecha_key
        
        # ⭐ NUEVO: Buscar fecha en formato texto "DD de MES"
        meses = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
            'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
            'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12,
            # Variaciones comunes
            'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4,
            'jun': 6, 'jul': 7, 'ago': 8, 'sep': 9, 'sept': 9,
            'oct': 10, 'nov': 11, 'dic': 12
        }
        
        # Patrón: "15 de febrero" o "el 15 de febrero"
        meses_pattern = '|'.join(meses.keys())
        text_date_pattern = rf'\b(?:el\s+)?(\d{{1,2}})\s+de\s+({meses_pattern})\b'
        match = re.search(text_date_pattern, message.lower())
        
        if match:
            day = int(match.group(1))
            month_name = match.group(2)
            month = meses[month_name]
            year = datetime.now().year
            
            # Si el mes ya pasó este año, asumir año siguiente
            current_month = datetime.now().month
            if month < current_month:
                year += 1
            
            try:
                # Validar que la fecha sea válida
                date_obj = datetime(year, month, day)
                date_str = date_obj.strftime("%d/%m/%Y")
                
                # ⭐ VALIDACIÓN: Rechazar fechas pasadas
                if date_obj.date() < datetime.now().date():
                    print(f"[NLU] ⚠️ Fecha en el pasado rechazada: {date_str}")
                    return 'fecha_pasada'  # Flag especial para manejar en bot
                
                print(f"[NLU] Fecha texto detectada: '{match.group(0)}' → {date_str}")
                return date_str
            except ValueError:
                # Fecha inválida (ej: 31 de febrero)
                print(f"[NLU] Fecha inválida detectada: {day}/{month}/{year}")
                return None
        
        # Buscar fecha absoluta numérica (DD/MM o DD/MM/YYYY)
        date_pattern = r'\b(\d{1,2})[/\-](\d{1,2})(?:[/\-](\d{2,4}))?\b'
        match = re.search(date_pattern, message)
        if match:
            day, month, year = match.groups()
            day = int(day)
            month = int(month)
            
            if year is None:
                year = datetime.now().year
            else:
                year = int(year)
                # Si es año de 2 dígitos, convertir a 4 dígitos
                if year < 100:
                    year = 2000 + year
            
            try:
                # Validar que la fecha sea válida
                date_obj = datetime(year, month, day)
                date_str = date_obj.strftime("%d/%m/%Y")
                
                # ⭐ VALIDACIÓN: Rechazar fechas pasadas
                if date_obj.date() < datetime.now().date():
                    print(f"[NLU] ⚠️ Fecha en el pasado rechazada: {date_str}")
                    return 'fecha_pasada'  # Flag especial
                
                return date_str
            except ValueError:
                # Fecha inválida (ej: 31 de febrero)
                print(f"[NLU] Fecha inválida detectada: {day}/{month}/{year}")
                return None
        
        return None
    
    def _extract_horario(self, message: str) -> Optional[str]:
        """
        Extrae horario mencionado (mañana/tarde/noche).
        
        También detecta horas específicas como "14:00" y las convierte
        al período del día correspondiente.
        """
        # Primero buscar horarios explícitos (mañana/tarde/noche)
        for horario, keywords in self.horarios.items():
            if self._contains_any(message, keywords):
                return horario
        
        # Buscar hora específica (HH:MM)
        import re
        time_pattern = r'\b([01]?[0-9]|2[0-3]):([0-5][0-9])\b'
        match = re.search(time_pattern, message)
        if match:
            hour = int(match.group(1))
            # Convertir a período del día
            if 6 <= hour < 13:
                return 'mañana'
            elif 13 <= hour < 19:
                return 'tarde'
            elif 19 <= hour < 24 or 0 <= hour < 6:
                return 'noche'
        
        return None
    
    def _extract_modalidad(self, message: str) -> Optional[str]:
        """Extrae modalidad (presencial/virtual)."""
        for modalidad, keywords in self.modalidades.items():
            if self._contains_any(message, keywords):
                return modalidad
        return None
    
    def _extract_genero(self, message: str) -> Optional[str]:
        """
        Extrae género del profesional buscado.
        
        Returns:
            'masculino' o 'femenino' o None
        """
        for genero, keywords in self.generos.items():
            if self._contains_any(message, keywords):
                print(f"[NLU] Género detectado: {genero}")
                return genero
        return None
    
    def _extract_prepaga(self, message: str) -> Optional[bool]:
        """
        Detecta si el usuario menciona prepaga/obra social.
        
        Returns:
            True si menciona prepaga/obra social, None si no
        """
        if self._contains_any(message, self.prepaga_keywords):
            print(f"[NLU] Prepaga detectada")
            return True
        return None
    
    def _extract_professional_name(self, message: str) -> Optional[str]:
        """
        Extrae nombre de profesional usando:
        1. Patrones de texto (con/al/a la/ver al + palabras)
        2. Fuzzy matching contra DB de profesionales
        3. Match por apellido solo, nombre solo, o nombre completo
        
        Returns:
            Nombre normalizado del profesional (lowercase) o None
        """
        import re
        from difflib import SequenceMatcher
        
        # ⭐ DEBUG
        print(f"[NLU] 🔍 _extract_professional_name() called")
        print(f"[NLU]    Input: '{message}'")
        
        stopwords = {
            'para', 'hoy', 'mañana', 'manana', 'pasado', 'ayer',
            'por', 'en', 'de', 'del', 'a', 'la', 'el', 'los', 'las',
            'tarde', 'noche', 'temprano', 'tempranito',
            'zona', 'norte', 'sur', 'centro', 'oeste', 'este',
            'turno', 'cita', 'sesion', 'consulta', 'ver', 'quiero', 'necesito', 'tener', 'tengo'
        }
        
        # ==========================================
        # PASO 1: Extraer candidatos del mensaje
        # ==========================================
        candidates = []

        print(f"[NLU] 📋 Probando patrones de extracción...")

        # Patrón 1: "con [el/la] [título] [palabras]"
        con_pattern = r'con\s+(?:el|la)?\s*(?:dr\.?|dra\.?|doc\.?|dotor\.?|dotora\.?|dc\.?|dtor\.?|lic\.?|licen\.?|licdo\.?|licenciado|licenciada|doctor|doctora)\s+([a-záéíóúñA-ZÁÉÍÓÚÑ\s]+)'
        con_match = re.search(con_pattern, message, re.IGNORECASE)
        if con_match:
            con_extracted = con_match.group(1).strip()
            print(f"[NLU]    ✅ Patrón 'con [el/la] [título]': '{con_extracted}'")
            candidates.append(con_extracted)
        else:
            print(f"[NLU]    ❌ Patrón 'con [el/la] [título]': no match")

        # Patrón 2: "al/a la [título] [palabras]"
        al_pattern = r'(?:al|a\s+la)\s+(?:dr\.?|dra\.?|doc\.?|dotor\.?|dotora\.?|dc\.?|dtor\.?|lic\.?|licen\.?|licdo\.?|licenciado|licenciada|doctor|doctora)\s+([a-záéíóúñA-ZÁÉÍÓÚÑ\s]+)'
        al_match = re.search(al_pattern, message, re.IGNORECASE)
        if al_match:
            al_extracted = al_match.group(1).strip()
            print(f"[NLU]    ✅ Patrón 'al/a la [título]': '{al_extracted}'")
            candidates.append(al_extracted)
        else:
            print(f"[NLU]    ❌ Patrón 'al/a la [título]': no match")

        # Patrón 3: "ver [al/a la] [título] [palabras]"
        ver_al_pattern = r'ver\s+(?:al|a\s+la)\s+(?:dr\.?|dra\.?|doc\.?|dotor\.?|dotora\.?|dc\.?|dtor\.?|lic\.?|licen\.?|licdo\.?|licenciado|licenciada|doctor|doctora)\s+([a-záéíóúñA-ZÁÉÍÓÚÑ\s]+)'
        ver_al_match = re.search(ver_al_pattern, message, re.IGNORECASE)
        if ver_al_match:
            ver_al_extracted = ver_al_match.group(1).strip()
            print(f"[NLU]    ✅ Patrón 'ver al/a la [título]': '{ver_al_extracted}'")
            candidates.append(ver_al_extracted)
        else:
            print(f"[NLU]    ❌ Patrón 'ver al/a la [título]': no match")

        # Patrón 4: "ver a [palabras]" (sin título obligatorio)
        ver_pattern = r'ver\s+a\s+(?:la\s+)?([a-záéíóúñA-ZÁÉÍÓÚÑ\s]+)'
        ver_match = re.search(ver_pattern, message, re.IGNORECASE)
        if ver_match:
            ver_extracted = ver_match.group(1).strip()
            print(f"[NLU]    ✅ Patrón 'ver a': '{ver_extracted}'")
            candidates.append(ver_extracted)
        else:
            print(f"[NLU]    ❌ Patrón 'ver a': no match")
        
        print(f"[NLU] 📊 Total candidatos extraídos: {len(candidates)}")
        if not candidates:
            print(f"[NLU] ⚠️ No se encontraron candidatos")
            return None
        
        # ==========================================
        # PASO 2: Limpiar candidatos
        # ==========================================
        cleaned_candidates = []
        
        for candidate in candidates:
            print(f"[NLU] 🧹 Limpiando: '{candidate}'")
            
            # Dividir en palabras
            words = candidate.split()
            valid_words = []
            
            for word in words:
                word_clean = word.lower().strip('.,;:')
                
                # Detener en stopword
                if word_clean in stopwords:
                    print(f"[NLU]    ⏹️ Deteniendo en stopword: '{word_clean}'")
                    break
                
                # Agregar palabra válida (más de 1 letra)
                if len(word) > 1:
                    valid_words.append(word)
                
                # Máximo 3 palabras (nombre + apellido1 + apellido2)
                if len(valid_words) >= 3:
                    break
            
            if valid_words:
                # Remover títulos al inicio
                name = ' '.join(valid_words)
                name = re.sub(r'^(dr\.?|dra\.?|doc\.?|dotor\.?|dotora\.?|dc\.?|dtor\.?|lic\.?|licen\.?|doctor|doctora|licenciado|licenciada)\s+', '', name, flags=re.IGNORECASE)
                
                if name:
                    print(f"[NLU]    ✅ Candidato limpio: '{name}'")
                    cleaned_candidates.append(name)
                else:
                    print(f"[NLU]    ⚠️ Candidato vacío después de limpiar")
            else:
                print(f"[NLU]    ⚠️ No hay palabras válidas")
        
        print(f"[NLU] 📋 Candidatos limpios: {cleaned_candidates}")
        
        # ==========================================
        # PASO 3: Fuzzy matching contra DB
        # ==========================================
        if not cleaned_candidates:
            print(f"[NLU] ⚠️ No hay candidatos limpios para comparar")
            return None
        
        # Importar Database
        from src.database.database import db
        
        # Obtener todos los profesionales de la DB
        try:
            professionals = db.get_all_professionals()
            if not professionals:
                print(f"[NLU] ⚠️ No hay profesionales en DB para comparar")
                return None
            print(f"[NLU] 📊 Profesionales en DB: {len(professionals)}")
        except Exception as e:
            print(f"[NLU] ❌ Error obteniendo profesionales: {e}")
            import traceback
            traceback.print_exc()
            return None
        
        # Función de similaridad
        def similarity(a: str, b: str) -> float:
            """Retorna similaridad 0.0-1.0"""
            return SequenceMatcher(None, a.lower(), b.lower()).ratio()
        
        # Normalizar texto para matching (quitar acentos)
        import unicodedata
        def normalize_text(text: str) -> str:
            """Quita acentos y convierte a minúsculas."""
            nfd = unicodedata.normalize('NFD', text)
            without_accents = ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')
            return without_accents.lower()
        
        best_match = None
        best_score = 0.0
        
        for candidate in cleaned_candidates:
            candidate_normalized = normalize_text(candidate)
            candidate_words = candidate_normalized.split()
            
            print(f"[NLU] 🔍 Buscando match para: '{candidate}' ({len(candidate_words)} palabras)")
            
            for prof in professionals:
                prof_name = prof.get('name', '')
                if not prof_name:
                    continue
                
                prof_normalized = normalize_text(prof_name)
                prof_words = prof_normalized.split()
                
                # Match 1: Nombre completo exacto
                if candidate_normalized == prof_normalized:
                    print(f"[NLU]   ✅ EXACT MATCH: '{prof_name}'")
                    return prof_name.lower()
                
                # Match 2: Solo apellido (última palabra)
                if len(candidate_words) == 1 and len(prof_words) >= 2:
                    prof_apellido = prof_words[-1]
                    score = similarity(candidate_normalized, prof_apellido)
                    
                    if score >= 0.85:
                        print(f"[NLU]   ✅ APELLIDO MATCH ({score:.2f}): '{candidate}' → '{prof_name}'")
                        if score > best_score:
                            best_match = prof_name
                            best_score = score
                
                # Match 3: Apellido + Nombre parcial
                elif len(candidate_words) >= 2:
                    matches = 0
                    for cand_word in candidate_words:
                        for prof_word in prof_words:
                            if similarity(cand_word, prof_word) >= 0.85:
                                matches += 1
                                break
                    
                    if matches >= 1:
                        overall_score = matches / max(len(candidate_words), len(prof_words))
                        
                        if overall_score >= 0.5:
                            print(f"[NLU]   ✅ PARTIAL MATCH ({overall_score:.2f}): '{candidate}' → '{prof_name}'")
                            if overall_score > best_score:
                                best_match = prof_name
                                best_score = overall_score
                
                # Match 4: Fuzzy general (fallback)
                general_score = similarity(candidate_normalized, prof_normalized)
                if general_score >= 0.75:
                    print(f"[NLU]   ✅ FUZZY MATCH ({general_score:.2f}): '{candidate}' → '{prof_name}'")
                    if general_score > best_score:
                        best_match = prof_name
                        best_score = general_score
        
        # ==========================================
        # PASO 4: Retornar mejor match si existe
        # ==========================================
        if best_match and best_score >= 0.75:
            print(f"[NLU] 🎯 BEST MATCH: '{best_match}' (score: {best_score:.2f})")
            return best_match.lower()
        
        # Si no hay match, retornar candidato original
        if cleaned_candidates:
            fallback = cleaned_candidates[0]
            print(f"[NLU] ⚠️ No DB match, usando candidato original: '{fallback}'")
            return fallback.lower()
        
        print(f"[NLU] ❌ No se pudo extraer nombre de profesional")
        return None

    def _can_shortcut(self, intent: Intent, entities: Dict) -> tuple:
        """
        Determina si puede hacer shortcut (ir directo a resultados).
        
        Returns:
            (can_shortcut: bool, missing_entities: list)
        """
        if intent == Intent.VIEW_TOMORROW:
            # Para "ver mañana" solo necesitamos horario opcional
            # Siempre puede hacer shortcut
            missing = []
            if 'horario' not in entities:
                missing.append('horario')
            return True, missing
        
        if intent == Intent.SEARCH_PROFESSIONAL:
            # Para búsqueda necesitamos al menos fecha
            required = ['fecha']
            optional = ['horario', 'zona', 'especialidad']
            
            missing = [e for e in required if e not in entities]
            
            # Puede hacer shortcut si tiene la fecha
            if not missing:
                return True, [e for e in optional if e not in entities]
            else:
                return False, missing
        
        return False, []
    
    def _contains_any(self, message: str, keywords: List[str]) -> bool:
        """Verifica si el mensaje contiene alguna de las keywords."""
        return any(keyword in message for keyword in keywords)
    
    def _is_greeting(self, message: str) -> bool:
        """Verifica si es solo un saludo."""
        greetings = [
            'hola', 'buenos días', 'buenas tardes', 'buenas noches',
            'buenas', 'buen día', 'hi', 'hello', 'hey'
        ]
        # Es saludo si SOLO contiene el saludo (max 3 palabras)
        words = message.split()
        if len(words) <= 3:
            return self._contains_any(message, greetings)
        return False
    
    def _extract_all_entities(self, message: str) -> Dict:
        """
        Extrae TODAS las entidades posibles del mensaje.
        
        Se ejecuta siempre, incluso cuando no se detecta un intent claro.
        Esto permite acumular entidades en el contexto conversacional.
        
        Args:
            message: Mensaje del usuario
            
        Returns:
            Diccionario con entidades detectadas
        """
        entities = {}
        message_lower = message.lower()
        
        # ⭐ FECHAS (CRÍTICO - siempre detectar)
        fecha = self._extract_fecha(message_lower)
        if fecha:
            entities['fecha'] = fecha
        
        # ⭐ HORARIOS
        for horario in ['mañana', 'tarde', 'noche']:
            if horario in message_lower:
                entities['horario'] = horario
                break
        
        # ⭐ ESPECIALIDADES
        if 'psicolog' in message_lower or 'psicologo' in message_lower or 'psicologa' in message_lower:
            entities['especialidad'] = 'psicología'
        elif 'nutri' in message_lower:
            entities['especialidad'] = 'nutrición'
        elif 'kinesio' in message_lower:
            entities['especialidad'] = 'kinesiología'
        # ... agregar más especialidades según necesites
        
        # ⭐ GÉNERO
        if self._contains_any(message_lower, ['mujer', 'femenino', 'doctora', 'dra']):
            entities['genero'] = 'femenino'
        elif self._contains_any(message_lower, ['hombre', 'masculino', 'doctor', 'dr']):
            entities['genero'] = 'masculino'
        
        # ⭐ PREPAGA
        if self._contains_any(message_lower, ['prepaga', 'obra social', 'osde', 'swiss medical', 'galeno']):
            entities['prepaga'] = True
        
        return entities

# ==========================================
# INSTANCIA GLOBAL
# ==========================================
intent_detector = IntentDetector()