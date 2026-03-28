"""
Sistema de Data Augmentation para Mensajes de WhatsApp
========================================================
Genera variaciones realistas de mensajes simulando diferentes perfiles de usuarios.

TÉCNICAS IMPLEMENTADAS:
1. ✅ Typos (errores de tipeo)
2. ✅ Eliminación de S y H finales
3. ✅ Artículos extra en nombres ("El Brian", "La Yeni")
4. ✅ Sinónimos de profesionales (doctor → profesional, licenciado)
5. ✅ Diminutivos argentinos (mañana → mañanita, turno → turnito)
6. ✅ Estilo super formal
7. ✅ Múltiples typos (personas mayores con dificultad visual)
8. ✅ Eliminación de tildes
9. ✅ Abreviaturas comunes
10. ✅ Variaciones de capitalización

Uso:
    >>> augmenter = MessageAugmenter()
    >>> 
    >>> # Generar variaciones mixtas
    >>> variations = augmenter.generate_variations(
    ...     "necesito psicólogo mañana",
    ...     n=20
    ... )
    >>> 
    >>> # Generar con perfil específico
    >>> formal = augmenter.generate_with_profile(
    ...     "necesito turno",
    ...     profile="formal"
    ... )
    >>> print(formal)
    >>> # "Buenos días. Solicito un turno para una consulta."
"""

import random
import re
from typing import List, Dict, Set, Optional
from dataclasses import dataclass


@dataclass
class AugmentationProfile:
    """
    Perfil de usuario para augmentation.
    
    Define qué técnicas aplicar y con qué intensidad.
    """
    name: str
    techniques: List[str]
    intensity: float  # 0.0 - 1.0
    description: str


class MessageAugmenter:
    """
    Generador de variaciones realistas de mensajes de WhatsApp.
    
    Simula diferentes perfiles de usuarios:
    - Joven informal (typos, abreviaturas)
    - Adulto mayor (múltiples errores)
    - Usuario formal (lenguaje elaborado)
    - Usuario casual (diminutivos, artículos extra)
    """
    
    def __init__(self, seed: int = 42):
        """
        Inicializar augmenter.
        
        Args:
            seed: Semilla para reproducibilidad
        """
        random.seed(seed)
        self._setup_rules()
        self._setup_profiles()
    
    def _setup_rules(self):
        """Configurar todas las reglas de augmentation."""
        
        # ==========================================
        # 1. TILDES
        # ==========================================
        self.tilde_map = {
            'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
            'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U',
        }
        
        # ==========================================
        # 2. TECLAS ADYACENTES (QWERTY español)
        # ==========================================
        self.keyboard_neighbors = {
            'a': ['s', 'q', 'w'], 'b': ['v', 'g', 'h', 'n'],
            'c': ['x', 'd', 'f', 'v'], 'd': ['s', 'e', 'r', 'f'],
            'e': ['w', 'r', 'd', 's'], 'f': ['d', 'r', 't', 'g'],
            'g': ['f', 't', 'y', 'h'], 'h': ['g', 'y', 'u', 'j'],
            'i': ['u', 'o', 'k', 'j'], 'j': ['h', 'u', 'i', 'k'],
            'k': ['j', 'i', 'o', 'l'], 'l': ['k', 'o', 'p'],
            'm': ['n', 'j', 'k'], 'n': ['b', 'h', 'j', 'm'],
            'o': ['i', 'p', 'l', 'k'], 'p': ['o', 'l'],
            'q': ['w', 'a'], 'r': ['e', 't', 'f', 'd'],
            's': ['a', 'w', 'e', 'd'], 't': ['r', 'y', 'g', 'f'],
            'u': ['y', 'i', 'j', 'h'], 'v': ['c', 'f', 'g', 'b'],
            'w': ['q', 'e', 's', 'a'], 'x': ['z', 's', 'd', 'c'],
            'y': ['t', 'u', 'h', 'g'], 'z': ['x', 's'],
        }
        
        # ==========================================
        # 3. ARTÍCULOS EXTRA (El Brian, La Yeni)
        # ==========================================
        self.articles = ['el', 'la', 'un', 'una']
        
        # Nombres propios comunes (para agregar artículos)
        self.common_names = [
            'juan', 'maría', 'carlos', 'ana', 'pedro', 'laura',
            'diego', 'sofia', 'pablo', 'lucia', 'brian', 'yeni',
            'martin', 'paula', 'fernando', 'carla', 'gonzalez',
            'rodriguez', 'fernandez', 'martinez', 'lopez', 'perez'
        ]
        
        # ==========================================
        # 4. SINÓNIMOS DE PROFESIONALES
        # ==========================================
        self.professional_synonyms = {
            'psicólogo': ['profesional', 'licenciado', 'doctor', 'terapeuta', 
                         'psicologo', 'lic', 'dr', 'dra'],
            'psicologo': ['profesional', 'licenciado', 'doctor', 'terapeuta', 
                         'lic', 'dr', 'dra'],
            'nutricionista': ['profesional', 'licenciado', 'doctor', 'nutri',
                            'lic', 'dr', 'dra'],
            'kinesiólogo': ['profesional', 'licenciado', 'fisioterapeuta', 'kine',
                          'lic', 'dr', 'dra'],
            'kinesiologo': ['profesional', 'licenciado', 'fisioterapeuta', 'kine',
                          'lic', 'dr', 'dra'],
            'terapeuta': ['profesional', 'licenciado', 'doctor', 'psicólogo',
                        'lic', 'dr', 'dra'],
        }
        
        # ==========================================
        # 5. DIMINUTIVOS ARGENTINOS
        # ==========================================
        self.diminutives = {
            'turno': ['turnito', 'turnitito'],
            'mañana': ['mañanita', 'mañanin'],
            'hora': ['horita', 'horin'],
            'consulta': ['consultita'],
            'cita': ['citita'],
            'hueco': ['huequito', 'huequitito'],
            'rato': ['ratito', 'ratitito'],
            'lugar': ['lugarcito'],
            'tiempo': ['tiempito'],
            'día': ['diita', 'diin'],
            'dia': ['diita', 'diin'],
        }
        
        # ==========================================
        # 6. FRASES FORMALES
        # ==========================================
        self.formal_greetings = [
            'Buenos días',
            'Buenas tardes',
            'Buenas noches',
            'Estimados',
            'Saludos cordiales',
        ]
        
        self.formal_requests = {
            'necesito': ['solicito', 'requiero', 'quisiera solicitar', 
                        'me gustaría solicitar', 'desearía'],
            'quiero': ['quisiera', 'me gustaría', 'desearía', 'solicito'],
            'turno': ['cita', 'consulta', 'entrevista', 'sesión'],
            'ver': ['consultar', 'verificar', 'revisar', 'visualizar'],
        }
        
        self.formal_closings = [
            'Quedo a la espera de su respuesta.',
            'Aguardo su confirmación.',
            'Muchas gracias por su atención.',
            'Desde ya muchas gracias.',
            'Saluda atentamente.',
        ]
        
        # ==========================================
        # 7. PALABRAS QUE PIERDEN S Y H
        # ==========================================
        # Común en español informal/rápido
        self.removable_endings = {
            's': 0.3,  # 30% de probabilidad de remover S final
            'h': 0.5,  # 50% de probabilidad de remover H inicial
        }
        
        # ==========================================
        # 8. ABREVIATURAS COMUNES
        # ==========================================
        self.abbreviations = {
            'psicólogo': ['psi', 'psico'],
            'psicologo': ['psi', 'psico'],
            'nutricionista': ['nutri'],
            'kinesiólogo': ['kine', 'fisio'],
            'kinesiologo': ['kine', 'fisio'],
            'por favor': ['porfa', 'porfavor', 'porfabor', 'x favor', 'xfa'],
            'para': ['pa', 'pr'],
            'porque': ['xq', 'xk', 'pq', 'pk'],
            'que': ['q', 'ke'],
            'también': ['tmb', 'tb', 'tambien'],
            'gracias': ['grax', 'grcs', 'thx'],
        }

        # ==========================================
        # 9. ⭐ TYPOS COMUNES EN DÍAS DE SEMANA
        # ==========================================
        self.weekday_typos = {
            'lunes': ['lune', 'lnes'],
            'martes': ['marte', 'marts'],
            'miércoles': ['miercolees', 'miercoles', 'miercols', 'miércols', 'miercol'],
            'miercoles': ['miercolees', 'miercols', 'miercol'],
            'jueves': ['jueve', 'juebes', 'juves'],
            'viernes': ['vierne', 'biernes', 'bierne'],
            'sábado': ['sabado', 'savado', 'sabdo'],
            'sabado': ['savado', 'sabdo'],
            'domingo': ['domigo', 'domino', 'domgo'],
        }

        # ==========================================
        # 10. ⭐ VARIANTES DE TÍTULOS PROFESIONALES
        # ==========================================
        self.title_variants = {
            'doctor': ['dr', 'doc', 'dc', 'dtor', 'dotor'],
            'doctora': ['dra', 'doc', 'dctora', 'dotora'],
            'dr': ['doctor', 'doc', 'dc'],
            'dra': ['doctora', 'doc'],
            'licenciado': ['lic', 'licen', 'licdo'],
            'licenciada': ['lic', 'licen', 'licda'],
        }
    
    def _setup_profiles(self):
        """Configurar perfiles de usuario."""
        
        self.profiles = {
            'casual': AugmentationProfile(
                name='casual',
                techniques=['typo_light', 'remove_accents', 'abbreviate', 
                           'diminutive', 'remove_s', 'add_article'],
                intensity=0.5,
                description='Usuario joven informal con typos leves'
            ),
            
            'elderly': AugmentationProfile(
                name='elderly',
                techniques=['typo_heavy', 'typo_adjacent', 'double_letter',
                           'missing_letter', 'case_variation'],
                intensity=0.4,
                description='Adulto mayor con dificultad visual (múltiples errores)'
            ),
            
            'formal': AugmentationProfile(
                name='formal',
                techniques=['formalize', 'expand_abbreviations'],
                intensity=0.9,
                description='Usuario formal con lenguaje elaborado'
            ),
            
            'diminutive': AugmentationProfile(
                name='diminutive',
                techniques=['diminutive', 'add_article', 'friendly'],
                intensity=0.7,
                description='Usuario que usa diminutivos y trato cercano'
            ),
            
            'abbreviator': AugmentationProfile(
                name='abbreviator',
                techniques=['abbreviate', 'remove_accents', 'remove_vowels'],
                intensity=0.4,
                description='Usuario que abrevia todo (ej: "ncsito psi mañ")'
            ),
            
            'fast_typer': AugmentationProfile(
                name='fast_typer',
                techniques=['keyboard_typos', 'typo_light', 'remove_vowels', 'abbreviate'],
                intensity=0.4,
                description='Usuario que escribe rápido y comete errores de teclado'
            ),
        }
    
    # ==========================================
    # MÉTODO PRINCIPAL
    # ==========================================
    
    def generate_variations(
        self,
        message: str,
        n: int = 10,
        profiles: Optional[List[str]] = None,
        include_original: bool = True
    ) -> List[str]:
        """
        Genera n variaciones del mensaje.
        
        Args:
            message: Mensaje original
            n: Número de variaciones deseadas
            profiles: Lista de perfiles a usar (None = todos)
            include_original: Si incluir el mensaje original
            
        Returns:
            Lista de variaciones únicas
            
        Example:
            >>> augmenter = MessageAugmenter()
            >>> variations = augmenter.generate_variations(
            ...     "necesito psicólogo mañana",
            ...     n=10
            ... )
            >>> for v in variations:
            ...     print(f"- {v}")
        """
        variations = set()
        
        if include_original:
            variations.add(message)
        
        # Si no especifican perfiles, usar todos
        if profiles is None:
            profiles = list(self.profiles.keys())
        
        attempts = 0
        max_attempts = n * 20  # Límite para evitar loop infinito
        
        while len(variations) < (n + 1 if include_original else n) and attempts < max_attempts:
            attempts += 1
            
            # Elegir perfil aleatorio
            profile_name = random.choice(profiles)
            
            # Generar variación con ese perfil
            variation = self.generate_with_profile(message, profile_name)
            
            if variation and variation != message:
                variations.add(variation)
        
        return list(variations)
    
    def generate_with_profile(
        self,
        message: str,
        profile: str
    ) -> str:
        """
        Genera una variación usando un perfil específico.
        
        Args:
            message: Mensaje original
            profile: Nombre del perfil ('casual', 'elderly', 'formal', etc)
            
        Returns:
            Mensaje variado según el perfil
        """
        if profile not in self.profiles:
            return message
        
        prof = self.profiles[profile]
        result = message
        
        # Aplicar técnicas del perfil
        for technique in prof.techniques:
            if random.random() < prof.intensity:
                result = self._apply_technique(result, technique)
        
        return result
    
    # ==========================================
    # TÉCNICAS INDIVIDUALES
    # ==========================================
    
    def _apply_technique(self, text: str, technique: str) -> str:
        """Aplica una técnica específica al texto."""
        
        if technique == 'remove_accents':
            return self._remove_accents(text)
        
        elif technique == 'typo_light':
            return self._add_typo_light(text)
        
        elif technique == 'typo_heavy':
            return self._add_typo_heavy(text)
        
        elif technique == 'typo_adjacent':
            return self._typo_adjacent_key(text)
        
        elif technique == 'double_letter':
            return self._double_random_letter(text)
        
        elif technique == 'missing_letter':
            return self._remove_random_letter(text)
        
        elif technique == 'remove_s':
            return self._remove_final_s(text)
        
        elif technique == 'remove_h':
            return self._remove_initial_h(text)
        
        elif technique == 'keyboard_typos':
            return self._add_keyboard_typos(text)
        
        elif technique == 'add_article':
            return self._add_article_to_name(text)
        
        elif technique == 'synonym_professional':
            return self._replace_with_synonym(text)
        
        elif technique == 'diminutive':
            return self._apply_diminutive(text)
        
        elif technique == 'formalize':
            return self._make_formal(text)
        
        elif technique == 'abbreviate':
            return self._apply_abbreviations(text)
        
        elif technique == 'case_variation':
            return self._vary_case(text)
        
        elif technique == 'friendly':
            return self._add_friendly_touch(text)
        
        else:
            return text
    
    # ==========================================
    # 1. ELIMINACIÓN DE TILDES
    # ==========================================
    
    def _remove_accents(self, text: str) -> str:
        """Elimina todas las tildes del texto."""
        for accented, plain in self.tilde_map.items():
            text = text.replace(accented, plain)
        return text
    
    # ==========================================
    # 2. TYPOS LIGEROS
    # ==========================================
    
    def _add_typo_light(self, text: str) -> str:
        """Agrega 1-2 typos ligeros."""
        words = text.split()
        num_typos = random.randint(1, min(2, len(words)))
        
        for _ in range(num_typos):
            if not words:
                break
            
            word_idx = random.randint(0, len(words) - 1)
            word = words[word_idx]
            
            if len(word) > 3:
                # Elegir técnica aleatoria
                technique = random.choice(['swap', 'duplicate', 'remove'])
                
                if technique == 'swap' and len(word) > 1:
                    # Intercambiar dos letras adyacentes
                    pos = random.randint(0, len(word) - 2)
                    word_list = list(word)
                    word_list[pos], word_list[pos + 1] = word_list[pos + 1], word_list[pos]
                    words[word_idx] = ''.join(word_list)
                
                elif technique == 'duplicate':
                    # Duplicar una letra
                    pos = random.randint(0, len(word) - 1)
                    words[word_idx] = word[:pos+1] + word[pos] + word[pos+1:]
                
                elif technique == 'remove' and len(word) > 4:
                    # Remover una letra
                    pos = random.randint(1, len(word) - 2)  # No primera ni última
                    words[word_idx] = word[:pos] + word[pos+1:]
        
        return ' '.join(words)
    
    # ==========================================
    # 3. TYPOS PESADOS (Adulto Mayor)
    # ==========================================
    
    def _add_typo_heavy(self, text: str) -> str:
        """Agrega múltiples typos (persona con dificultad visual/motriz)."""
        result = text
        
        # 1. Typos ligeros múltiples (intercambios, duplicados)
        result = self._add_typo_light(result)
        result = self._add_typo_light(result)
        
        # 2. ⭐ NUEVO: Typos de teclado QWERTY (2-3 errores)
        result = self._add_keyboard_typos(result)
        
        # 3. ⭐ NUEVO: Typos en días de semana
        result = self._apply_weekday_typos(result)
        
        # 4. ⭐ NUEVO: Variantes de títulos
        result = self._apply_title_variants(result)
        
        # 5. Teclas adyacentes (método existente, 1 error más)
        result = self._typo_adjacent_key(result)
        
        # 6. Letras dobles
        result = self._double_random_letter(result)
        
        # 7. Eliminar tildes (común en personas mayores)
        result = self._remove_accents(result)
        
        # 8. Mayúsculas inconsistentes
        if random.random() < 0.5:
            result = result.lower()
        
        return result
    
    # ==========================================
    # 4. TECLA ADYACENTE
    # ==========================================
    
    def _typo_adjacent_key(self, text: str) -> str:
        """Reemplaza letra por una tecla adyacente."""
        words = text.split()
        if not words:
            return text
        
        word_idx = random.randint(0, len(words) - 1)
        word = words[word_idx].lower()
        
        if len(word) > 2:
            # Elegir posición aleatoria (no primera letra)
            pos = random.randint(1, len(word) - 1)
            char = word[pos]
            
            if char in self.keyboard_neighbors:
                replacement = random.choice(self.keyboard_neighbors[char])
                words[word_idx] = word[:pos] + replacement + word[pos+1:]
        
        return ' '.join(words)
    
    # ==========================================
    # 5. LETRA DOBLE
    # ==========================================
    
    def _double_random_letter(self, text: str) -> str:
        """Duplica una letra aleatoria."""
        words = text.split()
        if not words:
            return text
        
        word_idx = random.randint(0, len(words) - 1)
        word = words[word_idx]
        
        if len(word) > 2:
            pos = random.randint(0, len(word) - 1)
            words[word_idx] = word[:pos+1] + word[pos] + word[pos+1:]
        
        return ' '.join(words)
    
    # ==========================================
    # ⭐ NUEVO: TYPOS DE TECLADO QWERTY (AGRESIVO)
    # ==========================================
    
    def _add_keyboard_typos(self, text: str) -> str:
        """
        Aplica typos de teclado QWERTY de forma más agresiva.
        Simula errores de pulso/precisión al escribir.
        
        Estrategia:
        - 1-3 typos por mensaje
        - Prioriza palabras largas (más probabilidad de error)
        - Reemplaza con teclas adyacentes en QWERTY
        """
        words = text.split()
        if not words:
            return text
        
        # Decidir cuántos typos (1-3 dependiendo del largo del texto)
        num_typos = min(3, max(1, len(words) // 3))
        
        # Candidatos: palabras de 4+ letras (más propensas a typos)
        candidates = [
            (idx, word) for idx, word in enumerate(words) 
            if len(word) >= 4
        ]
        
        if not candidates:
            return text
        
        # Aplicar typos
        for _ in range(num_typos):
            if not candidates:
                break
            
            # Elegir palabra aleatoria
            idx, word = random.choice(candidates)
            word_lower = word.lower()
            
            # Elegir posición aleatoria (no primera ni última letra)
            if len(word_lower) > 2:
                pos = random.randint(1, len(word_lower) - 2)
                char = word_lower[pos]
                
                # Reemplazar con tecla adyacente
                if char in self.keyboard_neighbors:
                    replacement = random.choice(self.keyboard_neighbors[char])
                    
                    # Mantener mayúsculas si las había
                    if word[pos].isupper():
                        replacement = replacement.upper()
                    
                    words[idx] = word[:pos] + replacement + word[pos+1:]
            
            # Remover de candidatos para no repetir
            candidates = [(i, w) for i, w in candidates if i != idx]
        
        return ' '.join(words)
    
    # ==========================================
    # ⭐ NUEVO: TYPOS EN DÍAS DE SEMANA
    # ==========================================
    
    def _apply_weekday_typos(self, text: str) -> str:
        """Aplica typos comunes en días de semana."""
        text_lower = text.lower()
        
        for correct_day, typos in self.weekday_typos.items():
            if correct_day in text_lower:
                # 30% de probabilidad de aplicar typo
                if random.random() < 0.3:
                    typo = random.choice(typos)
                    # Reemplazar manteniendo mayúsculas si las había
                    if correct_day.capitalize() in text:
                        text = text.replace(correct_day.capitalize(), typo.capitalize())
                    else:
                        text = text.replace(correct_day, typo)
        
        return text
    
    # ==========================================
    # ⭐ NUEVO: VARIANTES DE TÍTULOS PROFESIONALES
    # ==========================================
    
    def _apply_title_variants(self, text: str) -> str:
        """Aplica variantes de títulos profesionales (dr, doc, dc, etc)."""
        text_lower = text.lower()
        
        for correct_title, variants in self.title_variants.items():
            if correct_title in text_lower:
                # 40% de probabilidad de aplicar variante
                if random.random() < 0.4:
                    variant = random.choice(variants)
                    # Reemplazar manteniendo mayúsculas si las había
                    if correct_title.capitalize() in text:
                        text = text.replace(correct_title.capitalize(), variant.capitalize())
                    else:
                        text = text.replace(correct_title, variant)
        
        return text
    
    # ==========================================
    # 6. LETRA FALTANTE
    # ==========================================
    
    def _remove_random_letter(self, text: str) -> str:
        """Elimina una letra aleatoria."""
        words = text.split()
        if not words:
            return text
        
        word_idx = random.randint(0, len(words) - 1)
        word = words[word_idx]
        
        if len(word) > 4:  # Solo en palabras largas
            pos = random.randint(1, len(word) - 2)  # No primera ni última
            words[word_idx] = word[:pos] + word[pos+1:]
        
        return ' '.join(words)
    
    # ==========================================
    # 7. ELIMINAR S FINAL
    # ==========================================
    
    def _remove_final_s(self, text: str) -> str:
        """Elimina S final de palabras (común en habla informal)."""
        words = text.split()
        result = []
        
        for word in words:
            if word.lower().endswith('s') and len(word) > 3:
                if random.random() < self.removable_endings['s']:
                    result.append(word[:-1])
                else:
                    result.append(word)
            else:
                result.append(word)
        
        return ' '.join(result)
    
    # ==========================================
    # 8. ELIMINAR H INICIAL
    # ==========================================
    
    def _remove_initial_h(self, text: str) -> str:
        """Elimina H inicial de palabras (común en escritura fonética)."""
        words = text.split()
        result = []
        
        for word in words:
            if word.lower().startswith('h') and len(word) > 2:
                if random.random() < self.removable_endings['h']:
                    result.append(word[1:])
                else:
                    result.append(word)
            else:
                result.append(word)
        
        return ' '.join(result)
    
    # ==========================================
    # 9. ARTÍCULO EXTRA EN NOMBRES
    # ==========================================
    
    def _add_article_to_name(self, text: str) -> str:
        """Agrega artículo antes de nombres propios (El Brian, La Yeni)."""
        words = text.split()
        result = []
        
        i = 0
        while i < len(words):
            word = words[i]
            word_lower = word.lower()
            
            # Si parece nombre propio (capitalizado o en lista)
            if (word[0].isupper() or word_lower in self.common_names):
                # Si no tiene artículo antes
                if i == 0 or words[i-1].lower() not in self.articles:
                    # 50% de probabilidad de agregar artículo
                    if random.random() < 0.5:
                        article = random.choice(['el', 'la'])
                        result.append(article)
            
            result.append(word)
            i += 1
        
        return ' '.join(result)
    
    # ==========================================
    # 10. SINÓNIMOS DE PROFESIONALES
    # ==========================================
    
    def _replace_with_synonym(self, text: str) -> str:
        """Reemplaza profesional con sinónimo."""
        text_lower = text.lower()
        
        for profession, synonyms in self.professional_synonyms.items():
            if profession in text_lower:
                synonym = random.choice(synonyms)
                # Reemplazar manteniendo capitalización original
                pattern = re.compile(re.escape(profession), re.IGNORECASE)
                text = pattern.sub(synonym, text, count=1)
                break
        
        return text
    
    # ==========================================
    # 11. DIMINUTIVOS
    # ==========================================
    
    def _apply_diminutive(self, text: str) -> str:
        """Aplica diminutivos argentinos."""
        text_lower = text.lower()
        
        for word, dims in self.diminutives.items():
            if word in text_lower:
                dim = random.choice(dims)
                # Reemplazar manteniendo capitalización
                pattern = re.compile(re.escape(word), re.IGNORECASE)
                text = pattern.sub(dim, text, count=1)
                break
        
        return text
    
    # ==========================================
    # 12. FORMALIZAR
    # ==========================================
    
    def _make_formal(self, text: str) -> str:
        """Convierte mensaje a estilo formal."""
        result = text
        
        # Agregar saludo formal si no tiene
        if not any(greeting.lower() in result.lower() for greeting in self.formal_greetings):
            greeting = random.choice(self.formal_greetings)
            result = f"{greeting}. {result}"
        
        # Reemplazar palabras informales por formales
        for informal, formals in self.formal_requests.items():
            if informal in result.lower():
                formal = random.choice(formals)
                pattern = re.compile(re.escape(informal), re.IGNORECASE)
                result = pattern.sub(formal, result, count=1)
                break
        
        # Agregar cierre formal
        if random.random() < 0.7:
            closing = random.choice(self.formal_closings)
            result = f"{result} {closing}"
        
        # Capitalizar primera letra
        if result:
            result = result[0].upper() + result[1:]
        
        return result
    
    # ==========================================
    # 13. ABREVIATURAS
    # ==========================================
    
    def _apply_abbreviations(self, text: str) -> str:
        """Aplica abreviaturas comunes."""
        for full, abbrevs in self.abbreviations.items():
            if full in text.lower():
                abbrev = random.choice(abbrevs)
                pattern = re.compile(re.escape(full), re.IGNORECASE)
                text = pattern.sub(abbrev, text, count=1)
                break
        
        return text
    
    # ==========================================
    # 14. VARIACIÓN DE MAYÚSCULAS
    # ==========================================
    
    def _vary_case(self, text: str) -> str:
        """Varía mayúsculas y minúsculas inconsistentemente."""
        options = [
            text.lower(),                    # todo minúsculas
            text.upper(),                    # TODO MAYÚSCULAS
            text.capitalize(),               # Solo primera mayúscula
            text.title(),                    # Cada Palabra Capitalizada
        ]
        return random.choice(options)
    
    # ==========================================
    # 15. TOQUE AMIGABLE
    # ==========================================
    
    def _add_friendly_touch(self, text: str) -> str:
        """Agrega elementos de cercanía."""
        friendly_additions = [
            'che',
            'boludo',
            'man',
            'amigo',
            'por favor',
            'porfa',
        ]
        
        if random.random() < 0.5:
            addition = random.choice(friendly_additions)
            # Agregar al final o al principio
            if random.random() < 0.5:
                text = f"{text} {addition}"
            else:
                text = f"{addition} {text}"
        
        return text


# ==========================================
# FUNCIONES DE UTILIDAD
# ==========================================

def generate_dataset_from_examples(
    examples: List[Dict],
    n_variations_per_example: int = 10,
    output_file: str = "dataset_augmented.jsonl"
) -> None:
    """
    Genera dataset augmentado desde ejemplos base.
    
    Args:
        examples: Lista de diccionarios con 'message', 'intent', 'entities'
        n_variations_per_example: Variaciones por cada ejemplo
        output_file: Archivo de salida JSONL
        
    Example:
        >>> examples = [
        ...     {
        ...         "message": "necesito psicólogo mañana",
        ...         "intent": "search_professional",
        ...         "entities": {"especialidad": "psicología", "fecha": "mañana"}
        ...     },
        ...     # ... más ejemplos ...
        ... ]
        >>> generate_dataset_from_examples(examples, n_variations_per_example=20)
    """
    import json
    
    augmenter = MessageAugmenter()
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for example in examples:
            # Generar variaciones del mensaje
            variations = augmenter.generate_variations(
                example['message'],
                n=n_variations_per_example,
                include_original=True
            )
            
            # Escribir cada variación con los mismos intent/entities
            for variation in variations:
                entry = {
                    'message': variation,
                    'intent': example['intent'],
                    'entities': example['entities'],
                    'original': example['message'],
                    'augmented': variation != example['message']
                }
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    
    print(f"✅ Dataset generado: {output_file}")
    print(f"   - {len(examples)} ejemplos base")
    print(f"   - {len(examples) * n_variations_per_example} variaciones")
    print(f"   - {len(examples) * (n_variations_per_example + 1)} total")


# ==========================================
# EJEMPLO DE USO
# ==========================================

if __name__ == "__main__":
    augmenter = MessageAugmenter()
    
    # Ejemplo 1: Variaciones mixtas
    print("="*60)
    print("EJEMPLO 1: Variaciones Mixtas")
    print("="*60)
    message = "necesito psicólogo mañana"
    variations = augmenter.generate_variations(message, n=10)
    print(f"\nOriginal: {message}\n")
    print("Variaciones:")
    for i, v in enumerate(variations[1:], 1):  # Excluir original
        print(f"{i}. {v}")
    
    # Ejemplo 2: Perfiles específicos
    print("\n" + "="*60)
    print("EJEMPLO 2: Perfiles Específicos")
    print("="*60)
    
    profiles_to_test = ['casual', 'elderly', 'formal', 'diminutive']
    
    for profile in profiles_to_test:
        variation = augmenter.generate_with_profile(message, profile)
        print(f"\n{profile.upper()}: {variation}")
    
    # Ejemplo 3: Dataset completo
    print("\n" + "="*60)
    print("EJEMPLO 3: Generar Dataset")
    print("="*60)
    
    examples = [
        {
            "message": "necesito psicólogo mañana",
            "intent": "search_professional",
            "entities": {"especialidad": "psicología", "fecha": "mañana"}
        },
        {
            "message": "ver mis turnos",
            "intent": "view_my_appointments",
            "entities": {}
        },
        {
            "message": "hola",
            "intent": "greeting",
            "entities": {}
        },
    ]
    
    print("\nGenerando dataset augmentado...")
    generate_dataset_from_examples(
        examples,
        n_variations_per_example=5,
        output_file="dataset_ejemplo.jsonl"
    )