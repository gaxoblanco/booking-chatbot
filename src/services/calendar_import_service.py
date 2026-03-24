"""
CalendarImportService — Importación de agenda desde CSV/Excel vía WhatsApp
=========================================================================
Ubicación: src/services/calendar_import_service.py

Flujo de 2 pasos:
    1. analyze()  — clasifica filas sin tocar BD ni Calendar
                    resultado se guarda en session.temp_data['agenda_analysis']
    2. execute()  — carga solo los 'ready' en BD y Google Calendar

Separación de responsabilidades:
    - FileParser   (integrations/file_parser): bytes → List[Dict]
    - CalendarImportService (services/):         lógica de negocio
"""

import os
import logging
from datetime import date, timedelta, datetime
from typing import Dict, List, Optional
import requests
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

DEFAULT_WEEKS = 12
TIMEZONE      = 'America/Argentina/Buenos_Aires'
REQUIRED_COLS = {'phone', 'name', 'weekday', 'start_time', 'duration_minutes'}


class CalendarImportService:

    # =========================================================================
    # DETECCIÓN DE TIPO
    # =========================================================================

    def is_spreadsheet(self, content_type: str) -> bool:
        """Delega a FileParser para no duplicar los MIME types."""
        from src.integrations.file_parser import FileParser
        return FileParser().is_supported(content_type)

    # =========================================================================
    # PASO 0 — DESCARGA Y PARSEO
    # =========================================================================

    def download_and_parse(
        self,
        file_url:     str,
        content_type: str,
    ) -> tuple:
        """
        Descarga el archivo desde Twilio y lo parsea via FileParser.

        Returns:
            (rows, error_msg)
            rows      — List[Dict] si tuvo éxito, None si falló
            error_msg — string con el mensaje de error, None si tuvo éxito
        """
        # Descargar
        content = self._download(file_url)
        if content is None:
            return None, (
                "❌ No se pudo descargar el archivo.\n\n"
                "Por favor intentá enviarlo de nuevo."
            )

        # Parsear
        from src.integrations.file_parser import FileParser
        try:
            rows = FileParser().parse(content, content_type)
        except Exception as e:
            logger.error(f"[AGENDA-IMPORT] ❌ Error de parseo: {e}")
            return None, (
                "❌ No se pudo leer el archivo.\n\n"
                "Asegurate de que sea un CSV o Excel con las columnas:\n"
                "*phone, name, weekday, start_time, duration_minutes*"
            )

        if not rows:
            return None, (
                "⚠️ El archivo está vacío o no tiene filas de datos.\n\n"
                "Verificá que tenga al menos una fila después del header."
            )

        # Validar columnas
        missing = REQUIRED_COLS - set(rows[0].keys())
        if missing:
            return None, (
                f"❌ Faltan columnas: *{', '.join(sorted(missing))}*\n\n"
                f"Requeridas: phone, name, weekday, start_time, duration_minutes\n"
                f"Opcionales: email, modality, notes"
            )

        return rows, None

    # =========================================================================
    # PASO 1 — ANÁLISIS (sin escribir nada)
    # =========================================================================

    def analyze(
        self,
        rows:               List[Dict],
        professional_phone: str,
    ) -> Dict:
        """
        Clasifica cada fila en 4 categorías sin tocar BD ni Calendar.

        Orden de clasificación por fila:
            1. Validar E.164               → error      si falla
            2. Validar weekday             → error      si falla
            3. Duplicado exacto (mismo paciente + mismo horario) → duplicate
            4. Solapamiento con otro       → overlap
            5. Pasa todo                   → ready

        Returns:
            {
                'ready':     List[Dict],
                'duplicate': List[Dict],
                'overlap':   List[Dict],
                'error':     List[Dict],
                'analyzed_at': str,       # ISO timestamp
            }
        """
        from src.core.validators import validate_phone_e164
        from scripts.csv.load_patients_from_csv import (
            parse_weekday, next_weekday_date, add_minutes, check_overlap,
        )

        result = {
            'ready':       [],
            'duplicate':   [],
            'overlap':     [],
            'error':       [],
            'analyzed_at': datetime.now().isoformat(),
        }

        for i, row in enumerate(rows, 1):
            phone    = row.get('phone', '').strip()
            name     = row.get('name', '').strip()
            weekday  = row.get('weekday', '').strip()
            start    = row.get('start_time', '').strip()
            duration = int(row.get('duration_minutes', '') or 50)
            email    = row.get('email') or None
            modality = row.get('modality') or 'presencial'
            notes    = row.get('notes') or None

            base = {
                'row':              i,
                'phone':            phone,
                'name':             name,
                'weekday':          weekday,
                'start_time':       start,
                'duration_minutes': duration,
                'email':            email,
                'modality':         modality,
                'notes':            notes,
            }

            # ── Datos básicos ─────────────────────────────────────────────
            if not all([phone, name, weekday, start]):
                result['error'].append({
                    **base, 'error_reason': 'datos incompletos'
                })
                continue

            # ── Validar E.164 ─────────────────────────────────────────────
            if not validate_phone_e164(phone):
                result['error'].append({
                    **base,
                    'error_reason': f"teléfono inválido '{phone}' — usar +549..."
                })
                continue

            # ── Validar día de semana ─────────────────────────────────────
            weekday_idx = parse_weekday(weekday)
            if weekday_idx is None:
                result['error'].append({
                    **base,
                    'error_reason': f"día inválido '{weekday}'"
                })
                continue

            # ── Calcular horario ──────────────────────────────────────────
            end_time = add_minutes(start, duration)
            base['end_time']      = end_time
            base['weekday_idx']   = weekday_idx
            base['first_date']    = next_weekday_date(weekday_idx).isoformat()

            # ── Verificar duplicado / solapamiento ────────────────────────
            conflicto = check_overlap(
                prof_phone    = professional_phone,
                weekday_idx   = weekday_idx,
                start_time    = start,
                end_time      = end_time,
                patient_phone = phone,
            )

            if conflicto:
                if conflicto['tipo'] == 'duplicado':
                    result['duplicate'].append({
                        **base,
                        'conflict_with':  conflicto.get('ocupado_por', ''),
                        'conflict_start': conflicto.get('inicio', ''),
                        'conflict_end':   conflicto.get('fin', ''),
                    })
                else:
                    result['overlap'].append({
                        **base,
                        'conflict_with':  conflicto.get('ocupado_por', ''),
                        'conflict_start': conflicto.get('inicio', ''),
                        'conflict_end':   conflicto.get('fin', ''),
                    })
                continue

            # ── Listo para cargar ─────────────────────────────────────────
            result['ready'].append(base)

        logger.info(
            f"[AGENDA-IMPORT] Análisis completado — "
            f"ready={len(result['ready'])}, "
            f"duplicate={len(result['duplicate'])}, "
            f"overlap={len(result['overlap'])}, "
            f"error={len(result['error'])}"
        )
        return result

    # =========================================================================
    # PASO 2 — EJECUCIÓN (solo los 'ready')
    # =========================================================================

    def execute(
        self,
        analysis:           Dict,
        professional_phone: str,
        calendar_id:        str,
        weeks:              int = DEFAULT_WEEKS,
    ) -> Dict:
        """
        Carga en BD y Google Calendar solo los pacientes clasificados como 'ready'.

        Args:
            analysis:           resultado de analyze()
            professional_phone: teléfono del profesional
            calendar_id:        Google Calendar ID del profesional
            weeks:              semanas de recurrencia

        Returns:
            { 'creados': int, 'errores': int, 'detalles': List[str] }
        """
        from src.database.database import db
        from src.integrations.google_calendar_service import GoogleCalendarService
        from scripts.csv.load_patients_from_csv import build_rrule, dt_iso
        from datetime import date as date_type

        ready  = analysis.get('ready', [])
        stats  = {'creados': 0, 'errores': 0, 'detalles': []}

        if not ready:
            return stats

        until_date       = date_type.today() + timedelta(weeks=weeks)
        calendar_service = GoogleCalendarService()

        for item in ready:
            phone            = item['phone']
            name             = item['name']
            start            = item['start_time']
            end              = item['end_time']
            duration         = item['duration_minutes']
            weekday_idx      = item['weekday_idx']
            first_date_str   = item['first_date']
            email            = item.get('email')
            modality         = item.get('modality', 'presencial')
            notes            = item.get('notes')

            from datetime import date as date_type
            first_date = date_type.fromisoformat(first_date_str)
            rrule      = build_rrule(weekday_idx, until_date)

            # Crear cliente en BD
            try:
                db.add_client(phone=phone, name=name, email=email)
            except Exception as e:
                logger.warning(f"[AGENDA-IMPORT] add_client({phone}): {e}")

            # Crear evento recurrente en Google Calendar
            try:
                created = calendar_service.create_recurring_appointment(
                    calendar_id    = calendar_id,
                    start_datetime = dt_iso(first_date, start),
                    end_datetime   = dt_iso(first_date, end),
                    client_name    = name,
                    client_phone   = phone,
                    rrule          = rrule,
                    modality       = modality,
                    email          = email,
                    notes          = notes,
                    timezone_str   = TIMEZONE,
                )
                google_event_id = created['id']
            except Exception as e:
                stats['errores'] += 1
                stats['detalles'].append(
                    f"{name} — error Calendar: {str(e)[:80]}"
                )
                logger.error(f"[AGENDA-IMPORT] ❌ Calendar {name}: {e}")
                continue

            # Registrar primera ocurrencia en BD
            try:
                db.create_appointment(
                    client_phone       = phone,
                    professional_phone = professional_phone,
                    appointment_date   = first_date_str,
                    start              = start,
                    end                = end,
                    duration_minutes   = duration,
                    modality           = modality,
                    google_event_id    = google_event_id,
                    notes              = notes,
                )
            except Exception as e:
                logger.warning(f"[AGENDA-IMPORT] ⚠️ BD {name}: {e}")

            stats['creados'] += 1
            logger.info(f"[AGENDA-IMPORT] ✅ {name} — {item['weekday']} {start}")

        return stats

    # =========================================================================
    # FORMATEO DE MENSAJES
    # =========================================================================

    def format_review_menu(self, analysis: Dict) -> str:
        """
        Genera el menú de confirmación con el resumen del análisis.
        Se envía al profesional después de analyze().
        """
        ready      = len(analysis.get('ready', []))
        duplicate  = len(analysis.get('duplicate', []))
        overlap    = len(analysis.get('overlap', []))
        error      = len(analysis.get('error', []))
        total      = ready + duplicate + overlap + error

        msg = (
            f"📋 *Revisé tu agenda*\n\n"
            f"Encontré {total} pacientes:\n"
            f"✅ {ready} listos para cargar\n"
            f"🔄 {duplicate} ya existentes (se omiten)\n"
            f"⚠️ {overlap} con solapamiento de horario\n"
            f"❌ {error} con datos inválidos\n\n"
        )

        if ready > 0:
            msg += (
                f"¿Qué querés hacer?\n"
                f"1️⃣ Confirmar carga ({ready} pacientes)\n"
            )
        else:
            msg += "⚠️ No hay pacientes nuevos para cargar.\n\n"

        msg += (
            f"2️⃣ Ver listos para cargar\n"
            f"3️⃣ Ver solapamientos\n"
            f"4️⃣ Ver ya existentes\n"
            f"5️⃣ Ver errores\n"
            f"0️⃣ Cancelar"
        )

        return msg

    def format_detail(self, analysis: Dict, subset: str) -> str:
        """
        Genera el detalle de un subconjunto (ready/overlap/duplicate/error).
        Máximo 10 filas para no saturar WhatsApp.

        Args:
            analysis: resultado de analyze()
            subset:   'ready' | 'overlap' | 'duplicate' | 'error'
        """
        labels = {
            'ready':     ('✅', 'Listos para cargar'),
            'duplicate': ('🔄', 'Ya existentes'),
            'overlap':   ('⚠️', 'Con solapamiento'),
            'error':     ('❌', 'Con errores'),
        }

        emoji, title = labels.get(subset, ('📋', subset))
        items        = analysis.get(subset, [])
        total        = len(items)

        if total == 0:
            return f"{emoji} No hay pacientes en esta categoría.\n\n_Escribí cualquier cosa para volver_"

        shown = items[:10]
        msg   = f"{emoji} *{title}* ({total})\n\n"

        for item in shown:
            name    = item.get('name', '?')
            phone   = item.get('phone', '?')
            weekday = item.get('weekday', '?')
            start   = item.get('start_time', '?')

            line = f"• {name} — {weekday} {start} ({phone})"

            if subset == 'overlap':
                line += f"\n  ↳ solapamiento con {item.get('conflict_with', '?')} ({item.get('conflict_start', '?')}-{item.get('conflict_end', '?')})"
            elif subset == 'error':
                line += f"\n  ↳ {item.get('error_reason', '?')}"

            msg += line + "\n"

        if total > 10:
            msg += f"\n_... y {total - 10} más_"

        msg += "\n\n_Escribí cualquier cosa para volver al menú_"
        return msg

    def format_execute_result(self, stats: Dict) -> str:
        """Mensaje final después de execute()."""
        creados = stats['creados']
        errores = stats['errores']

        if creados > 0 and errores == 0:
            msg = (
                f"✅ *Agenda cargada exitosamente*\n\n"
                f"Se cargaron {creados} paciente(s).\n"
                f"Los turnos ya aparecen en tu Google Calendar."
            )
        elif creados > 0:
            msg = (
                f"⚠️ *Agenda cargada con errores*\n\n"
                f"Cargados: {creados}\n"
                f"Errores:  {errores}"
            )
        else:
            msg = "❌ No se pudo cargar ningún paciente. Revisá los errores e intentá de nuevo."

        if stats.get('detalles'):
            msg += "\n\n📋 *Detalle de errores:*"
            for d in stats['detalles'][:5]:
                msg += f"\n• {d}"

        return msg

    # =========================================================================
    # DESCARGA (privado)
    # =========================================================================
    
    
    def _download(self, file_url: str) -> Optional[bytes]:
        """
        Descarga el archivo desde Twilio con validaciones de seguridad.
    
        Validaciones aplicadas (en orden):
            1. URL pertenece al dominio de Twilio (api.twilio.com)
            2. Tamaño según Content-Length no supera 5 MB
            3. Descarga en streaming — corta si supera 5 MB durante la bajada
            4. Timeout de 30 segundos
    
        Args:
            file_url: URL del archivo en Twilio (MediaUrl0 del request)
    
        Returns:
            bytes con el contenido del archivo, o None si falló
        """
        # Constantes de seguridad
        MAX_FILE_SIZE_BYTES  = 5 * 1024 * 1024   # 5 MB
        ALLOWED_MEDIA_DOMAIN = 'api.twilio.com'  # único dominio aceptado
        
        # ── 1. Validar dominio ───────────────────────────────────────────────────
        try:
            parsed = urlparse(file_url)
        except Exception:
            logger.error(f"[SECURITY] ❌ URL malformada: {file_url[:80]}")
            return None
    
        if parsed.netloc != ALLOWED_MEDIA_DOMAIN:
            logger.error(
                f"[SECURITY] 🚨 URL de descarga rechazada: dominio '{parsed.netloc}' "
                f"no es '{ALLOWED_MEDIA_DOMAIN}'"
            )
            return None
    
        if parsed.scheme != 'https':
            logger.error(
                f"[SECURITY] 🚨 URL sin HTTPS rechazada: {file_url[:80]}"
            )
            return None
    
        # ── 2. Descargar con límite de tamaño ────────────────────────────────────
        try:
            resp = requests.get(
                file_url,
                auth    = (
                    os.getenv('TWILIO_ACCOUNT_SID'),
                    os.getenv('TWILIO_AUTH_TOKEN'),
                ),
                timeout = 30,
                stream  = True,   # no cargar todo en RAM antes de verificar
            )
    
            if resp.status_code != 200:
                logger.error(
                    f"[AGENDA-IMPORT] ❌ HTTP {resp.status_code} "
                    f"descargando archivo"
                )
                return None
    
            # Verificar Content-Length si el servidor lo provee
            content_length = int(resp.headers.get('Content-Length', 0))
            if content_length > MAX_FILE_SIZE_BYTES:
                logger.warning(
                    f"[SECURITY] ⚠️ Archivo rechazado por Content-Length: "
                    f"{content_length / 1024 / 1024:.1f} MB "
                    f"(límite: {MAX_FILE_SIZE_BYTES / 1024 / 1024:.0f} MB)"
                )
                return None
    
            # Descargar en chunks — cortar si supera el límite
            content = b''
            for chunk in resp.iter_content(chunk_size=8192):
                content += chunk
                if len(content) > MAX_FILE_SIZE_BYTES:
                    logger.warning(
                        f"[SECURITY] ⚠️ Descarga cortada: archivo superó "
                        f"{MAX_FILE_SIZE_BYTES / 1024 / 1024:.0f} MB "
                        f"— abortando"
                    )
                    return None
    
            size_kb = len(content) / 1024
            logger.info(
                f"[AGENDA-IMPORT] ✅ Archivo descargado: {size_kb:.1f} KB"
            )
            return content
    
        except requests.exceptions.Timeout:
            logger.error(
                f"[AGENDA-IMPORT] ❌ Timeout descargando archivo "
                f"(límite: 30s)"
            )
            return None
    
        except Exception as e:
            logger.error(f"[AGENDA-IMPORT] ❌ Error descargando: {e}")
            return None
# Instancia global
calendar_import_service = CalendarImportService()