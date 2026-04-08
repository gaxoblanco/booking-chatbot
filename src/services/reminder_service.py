"""
Servicio de Recordatorios Automáticos
======================================

Este servicio:
1. Se ejecuta diariamente a las 17:30
2. Consulta citas para el día siguiente
3. Envía recordatorios por WhatsApp
4. Permite confirmar o reprogramar

Uso:
    python -m src.services.reminder_service

Author: Salud Conecta
"""

import os
from datetime import datetime, timedelta
from typing import List, Dict
import logging

from src.database.database import db
from src.integrations.appointment_calendar_service import AppointmentCalendarService
from src.integrations.conversation_context_service.event_store import event_store

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ReminderService:
    """Servicio para enviar recordatorios automáticos de citas."""
    
    def __init__(self):
        self.db = db
        self.calendar_service = AppointmentCalendarService(db)
        
    # =========================================================================
    # MAIN FUNCTION - Ejecutada por CRON
    # =========================================================================
    
    def send_daily_reminders(self) -> Dict:
        """
        Función principal ejecutada diariamente a las 17:30.
        
        Proceso:
        1. Obtener citas del día siguiente
        2. Filtrar citas que necesitan recordatorio
        3. Enviar WhatsApp a cada cliente
        4. Registrar envío en BD
        
        Returns:
            Dict con estadísticas: {
                'checked': 10,
                'sent': 8,
                'skipped': 2,
                'errors': 0
            }
        """
        logger.info("=" * 60)
        logger.info("🔔 INICIANDO ENVÍO DE RECORDATORIOS DIARIOS")
        logger.info("=" * 60)
        
        # Calcular fecha objetivo (mañana)
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        logger.info(f"📅 Buscando citas para: {tomorrow}")
        
        # Estadísticas
        stats = {
            'checked': 0,
            'sent': 0,
            'skipped': 0,
            'errors': 0
        }
        
        try:
            # Paso 1: Obtener citas del día siguiente
            appointments = self._get_appointments_for_date(tomorrow)
            stats['checked'] = len(appointments)
            
            logger.info(f"📊 Encontradas {len(appointments)} citas para {tomorrow}")
            
            if not appointments:
                logger.info("✅ No hay citas para recordar")
                return stats
            
            # Paso 2: Enviar recordatorio a cada una
            for apt in appointments:
                try:
                    success = self._send_reminder(apt)
                    
                    if success:
                        stats['sent'] += 1
                    else:
                        stats['skipped'] += 1
                        
                except Exception as e:
                    logger.error(f"❌ Error enviando recordatorio cita #{apt['id']}: {e}")
                    stats['errors'] += 1
            
            # Paso 3: Log final
            logger.info("=" * 60)
            logger.info("✅ ENVÍO DE RECORDATORIOS COMPLETADO")
            logger.info(f"📊 Estadísticas:")
            logger.info(f"   • Revisadas: {stats['checked']}")
            logger.info(f"   • Enviadas: {stats['sent']}")
            logger.info(f"   • Omitidas: {stats['skipped']}")
            logger.info(f"   • Errores: {stats['errors']}")
            logger.info("=" * 60)
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error crítico en send_daily_reminders: {e}")
            import traceback
            traceback.print_exc()
            stats['errors'] += 1
            return stats
    
    # =========================================================================
    # PRIVATE HELPERS
    # =========================================================================
    
    def _get_appointments_for_date(self, date_str: str) -> List[Dict]:
        """
        Obtiene citas que necesitan recordatorio para una fecha.
        
        Filtros:
        - Fecha = date_str
        - Estado = 'confirmada'
        - reminder_sent = False
        - Tiene client_phone
        
        Args:
            date_str: Fecha en formato YYYY-MM-DD
        
        Returns:
            Lista de diccionarios con datos de citas
        """
        query = """
            SELECT 
                a.id,
                a.client_phone,
                a.professional_phone,
                a.appointment_date,
                a.start,
                a.end,
                a.status,
                a.reminder_sent,
                p.name as professional_name,
                c.name as client_name
            FROM appointments a
            LEFT JOIN professionals p ON a.professional_phone = p.phone
            LEFT JOIN clients c ON a.client_phone = c.phone
            WHERE a.appointment_date = ?
            AND a.status = 'confirmada'
            AND (a.reminder_sent IS NULL OR a.reminder_sent = 0)
            AND a.client_phone IS NOT NULL
            ORDER BY a.start
        """
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (date_str,))
                
                columns = [desc[0] for desc in cursor.description]
                appointments = [dict(zip(columns, row)) for row in cursor.fetchall()]
                
                return appointments
                
        except Exception as e:
            logger.error(f"Error obteniendo citas para {date_str}: {e}")
            return []
    
    def _send_reminder(self, apt: Dict) -> bool:
        """Envía recordatorio usando MessageSender centralizado."""
        import json
        from src.core.message_sender import message_sender

        content_sid = os.getenv('TWILIO_REMINDER_TEMPLATE_SID')
        if not content_sid:
            logger.error("TWILIO_REMINDER_TEMPLATE_SID no configurado")
            return False

        date_obj        = datetime.strptime(apt['appointment_date'], "%Y-%m-%d")
        dias            = ['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo']
        dia_nombre      = dias[date_obj.weekday()]
        fecha_formatted = date_obj.strftime("%d/%m/%Y")
        prof_name       = apt.get('professional_name', 'tu profesional')

        variables_json = json.dumps({
            "1": prof_name,
            "2": f"{dia_nombre} {fecha_formatted}",
            "3": f"{apt['start']} hs"
        })

        logger.info(f"📤 Enviando recordatorio a {apt['client_phone']} (Cita #{apt['id']})")

        sent = message_sender.send_with_retry(
            to_phone           = apt['client_phone'],
            message            = "",
            professional_phone = apt.get('professional_phone'),
            patient_name       = apt.get('client_name'),
            appointment_id     = apt['id'],
            content_sid        = content_sid,
            content_variables  = variables_json,
        )

        if sent:
            self._mark_reminder_sent(apt['id'])   # ← mantener siempre
            logger.info(f"✅ Recordatorio enviado exitosamente")
            event_store.record(
                client_phone   = apt['client_phone'],
                event_type     = 'reminder_sent',
                appointment_id = apt['id'],
            )

            # Recordatorio informativo al paciente real si tiene número distinto
            patient_phone = apt.get('patient_phone')
            if patient_phone and patient_phone != apt['client_phone']:
                logger.info(
                    f"📤 Enviando recordatorio informativo a paciente "
                    f"{patient_phone} (Cita #{apt['id']})"
                )
                mensaje_paciente = (
                    f"🔔 *Recordatorio de turno*\n\n"
                    f"Hola, te recordamos que tenés un turno agendado:\n\n"
                    f"👨‍⚕️ *Profesional:* {prof_name}\n"
                    f"📅 *Fecha:* {dia_nombre} {fecha_formatted}\n"
                    f"⏰ *Horario:* {apt['start']} hs\n\n"
                    f"_Para cancelar o reprogramar, contactá a quien agendó el turno._"
                )
                message_sender.send_with_retry(
                    to_phone           = patient_phone,
                    message            = mensaje_paciente,
                    professional_phone = apt.get('professional_phone'),
                    patient_name       = apt.get('patient_name'),
                    appointment_id     = apt['id'],
                )

        return sent
    
    def _format_reminder_message(self, apt: Dict) -> str:
        """
        Formatea el mensaje de recordatorio.
        
        Args:
            apt: Datos de la cita
        
        Returns:
            Mensaje formateado para WhatsApp
        """
        # Formatear fecha
        date_obj = datetime.strptime(apt['appointment_date'], "%Y-%m-%d")
        dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        dia_nombre = dias[date_obj.weekday()]
        fecha_formatted = date_obj.strftime("%d/%m/%Y")
        
        # Nombre del cliente (si existe)
        client_name = apt.get('client_name', 'Paciente')
        if client_name:
            saludo = f"Hola {client_name.split()[0]}"  # Primer nombre
        else:
            saludo = "Hola"
        
        # Profesional
        prof_name = apt.get('professional_name', 'Profesional')
        
        message = f"""🔔 *RECORDATORIO DE TURNO*

{saludo}, te recordamos que tenés un turno programado:

👨‍⚕️ *Profesional:* {prof_name}
📅 *Fecha:* {dia_nombre} {fecha_formatted}
⏰ *Horario:* {apt['start']} hs

¿Confirmás tu asistencia?

1️⃣ Sí, confirmo mi asistencia
2️⃣ Necesito reprogramar
0️⃣ Cancelar turno

_Por favor, responde antes de las 20:00 hs_
_Caso de no responder se auto-confirma_"""

        return message
    
    def _mark_reminder_sent(self, appointment_id: int) -> bool:
        """
        Marca la cita como "recordatorio enviado" en BD.
        
        Args:
            appointment_id: ID de la cita
        
        Returns:
            True si se actualizó correctamente
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Actualizar appointment
                cursor.execute("""
                    UPDATE appointments 
                    SET reminder_sent = 1
                    WHERE id = ?
                """, (appointment_id,))
                
                # Registrar en tabla reminders
                cursor.execute("""
                    INSERT INTO appointment_reminders 
                    (appointment_id, client_phone, professional_phone, 
                     appointment_date, appointment_time, status)
                    SELECT id, client_phone, professional_phone, 
                           appointment_date, start, 'sent'
                    FROM appointments
                    WHERE id = ?
                """, (appointment_id,))
                
                logger.info(f"✅ Marcado reminder_sent = 1 para cita #{appointment_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error marcando reminder enviado: {e}")
            return False
    
    # =========================================================================
    # RESPUESTAS DEL CLIENTE
    # =========================================================================
    
    def handle_reminder_response(
        self, 
        client_phone: str, 
        response: str
    ) -> Dict:
        """
        Procesa la respuesta del cliente al recordatorio.
        
        Args:
            client_phone: Teléfono del cliente
            response: "1", "2" o "0"
        
        Returns:
            Dict con resultado y mensaje
        """
        # Buscar recordatorio pendiente
        reminder = self._get_pending_reminder(client_phone)
        
        if not reminder:
            return {
                'success': False,
                'message': "No encontramos un recordatorio pendiente."
            }
        
        appointment_id = reminder['appointment_id']

        # Registrar evento de respuesta
        _action_map = {'1': 'confirmed', '2': 'rescheduled', '0': 'cancelled'}
        event_store.record(
            client_phone   = client_phone,
            event_type     = 'reminder_response',
            intent         = f"reminder_{_action_map.get(response, 'unknown')}",
            appointment_id = appointment_id,
        )

        # Opción 1: CONFIRMAR
        if response == '1':
            return self._confirm_appointment(appointment_id, client_phone)
        
        # Opción 2: REPROGRAMAR
        elif response == '2':
            return self._initiate_reschedule(appointment_id, client_phone)
        
        # Opción 0: CANCELAR
        elif response == '0':
            return self._initiate_cancellation(appointment_id, client_phone)
        
        else:
            return {
                'success': False,
                'message': "Opción inválida. Responde 1, 2 o 0."
            }
    
    def _get_pending_reminder(self, client_phone: str) -> Dict:
        """Obtiene recordatorio pendiente de respuesta del cliente."""
        query = """
            SELECT 
                r.id as reminder_id,
                r.appointment_id,
                r.sent_at,
                a.appointment_date,
                a.start
            FROM appointment_reminders r
            JOIN appointments a ON r.appointment_id = a.id
            WHERE r.client_phone = ?
            AND r.status = 'sent'
            AND a.appointment_date > DATE('now')
            ORDER BY r.sent_at DESC
            LIMIT 1
        """
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (client_phone,))
                row = cursor.fetchone()
                
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, row))
                return None
                
        except Exception as e:
            logger.error(f"Error buscando reminder: {e}")
            return None
    
    def _confirm_appointment(self, appointment_id: int, client_phone: str) -> Dict:
        """Confirma asistencia del cliente."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Actualizar appointment
                cursor.execute("""
                    UPDATE appointments 
                    SET confirmed_by_client = 1,
                        confirmed_by_client_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (appointment_id,))
                
                # Actualizar reminder
                cursor.execute("""
                    UPDATE appointment_reminders
                    SET status = 'confirmed',
                        confirmed_at = CURRENT_TIMESTAMP,
                        response_received_at = CURRENT_TIMESTAMP
                    WHERE appointment_id = ?
                    AND client_phone = ?
                """, (appointment_id, client_phone))
                
                logger.info(f"✅ Cita #{appointment_id} confirmada por cliente")
                
                return {
                    'success': True,
                    'action': 'confirmed',
                    'message': "✅ ¡Perfecto! Tu turno está confirmado.\n\nTe esperamos. ¡Gracias!"
                }
                
        except Exception as e:
            logger.error(f"Error confirmando cita: {e}")
            return {
                'success': False,
                'message': "Error al confirmar. Intenta nuevamente."
            }
    
    def _initiate_reschedule(self, appointment_id: int, client_phone: str) -> Dict:
        """Inicia flujo de reprogramación."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE appointment_reminders
                    SET status = 'rescheduled',
                        response_received_at = CURRENT_TIMESTAMP
                    WHERE appointment_id = ?
                    AND client_phone = ?
                """, (appointment_id, client_phone))
            
            return {
                'success': True,
                'action': 'reschedule',
                'message': "📅 Entendido. Iniciando reprogramación...\n\n¿Qué fecha preferís?"
            }
            
        except Exception as e:
            logger.error(f"Error iniciando reschedule: {e}")
            return {'success': False}
    
    def _initiate_cancellation(self, appointment_id: int, client_phone: str) -> Dict:
        """Inicia flujo de cancelación."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE appointment_reminders
                    SET status = 'cancelled',
                        response_received_at = CURRENT_TIMESTAMP
                    WHERE appointment_id = ?
                    AND client_phone = ?
                """, (appointment_id, client_phone))
            
            return {
                'success': True,
                'action': 'cancel',
                'message': "❌ ¿Estás seguro que querés cancelar?\n\n1️⃣ Sí, cancelar\n2️⃣ No, mantener turno"
            }
            
        except Exception as e:
            logger.error(f"Error iniciando cancellation: {e}")
            return {'success': False}
        
    # =========================================================================
    # AUTO-CONFIRMACIÓN POR TIMEOUT
    # =========================================================================

    def auto_confirm_unanswered(self, timeout_hours: int = 3) -> Dict:
        """
        Confirma automáticamente citas cuyos recordatorios no recibieron
        respuesta dentro del período de timeout.

        Lógica:
            - Busca reminders con status='sent'
            - Cuyo sent_at sea anterior a (ahora - timeout_hours)
            - Para cada uno llama _confirm_appointment() — función real existente

        Diseño deliberado:
            - Si el cliente no responde asumimos que asiste (reduce no-shows)
            - El cliente igual recibió el recordatorio, está avisado
            - No se envía nuevo WhatsApp (evita spam)

        Args:
            timeout_hours: Horas sin respuesta para auto-confirmar (default: 3)

        Returns:
            checked: reminders evaluados
            confirmed: auto-confirmados
            errors: errores
            appointments: IDs de citas confirmadas
        """
        logger.info("=" * 60)
        logger.info(f"AUTO-CONFIRMACION POR TIMEOUT ({timeout_hours}h sin respuesta)")
        logger.info("=" * 60)

        stats = {"checked": 0, "confirmed": 0, "errors": 0, "appointments": []}

        query = """
            SELECT
                r.id            AS reminder_id,
                r.appointment_id,
                r.client_phone,
                r.sent_at,
                a.appointment_date,
                a.start
            FROM appointment_reminders r
            JOIN appointments a ON r.appointment_id = a.id
            WHERE r.status = "sent"
            AND r.sent_at <= datetime("now", :timeout)
            AND a.appointment_date >= DATE("now")
            ORDER BY r.sent_at ASC
        """

        try:
            timeout_param = f"-{timeout_hours} hours"

            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, {"timeout": timeout_param})
                columns = [desc[0] for desc in cursor.description]
                pending = [dict(zip(columns, row)) for row in cursor.fetchall()]

            stats["checked"] = len(pending)
            logger.info(f"Reminders sin respuesta: {len(pending)}")

            for reminder in pending:
                apt_id  = reminder["appointment_id"]
                client  = reminder["client_phone"]
                sent_at = reminder["sent_at"]

                logger.info(f"  > Cita #{apt_id} | {client} | enviado {sent_at}")
                result = self._confirm_appointment(apt_id, client)

                if result.get("success"):
                    stats["confirmed"] += 1
                    stats["appointments"].append(apt_id)
                    logger.info(f"  OK Cita #{apt_id} auto-confirmada")
                    event_store.record(
                        client_phone   = client,
                        event_type     = 'reminder_response',
                        intent         = 'reminder_auto_confirmed',
                        appointment_id = apt_id,
                    )
                else:
                    stats["errors"] += 1
                    logger.error(f"  ERROR auto-confirmando #{apt_id}")

        except Exception as e:
            logger.error(f"Error en auto_confirm_unanswered: {e}")
            import traceback
            traceback.print_exc()
            stats["errors"] += 1

        logger.info(f"Completado - confirmados: {stats['confirmed']}, errores: {stats['errors']}")
        return stats

    # =========================================================================
    # DEMO - Disparar envío de recordatorios desde WhatsApp
    # =========================================================================

    def trigger_reminders_now(self) -> Dict:
        """
        Ejecuta el envío de recordatorios diarios de forma inmediata.

        Funciona exactamente igual que el CRON de las 17:30, buscando
        citas para mañana y enviando WhatsApp a cada cliente registrado.

        Usado por el comando secreto "enviar recordatorio(s)" del bot.

        Returns:
            Dict con estadísticas: {'sent': int, 'checked': int, 'errors': int, 'message': str}
        """
        logger.info("[TRIGGER] 🔔 Ejecución manual de recordatorios solicitada")

        stats = self.send_daily_reminders()

        # Construir mensaje de respuesta para el bot
        sent = stats.get('sent', 0)
        checked = stats.get('checked', 0)
        errors = stats.get('errors', 0)

        if checked == 0:
            message = (
                "📭 No hay citas programadas para mañana.\n\n"
                "Creá una cita con fecha de mañana para probar el flujo."
            )
        elif sent == 0:
            message = (
                f"⚠️ Se revisaron {checked} cita(s) pero no se enviaron recordatorios.\n"
                "Posibles causas: ya fueron enviados hoy, o falta `TWILIO_REMINDER_TEMPLATE_SID` en `.env`."
            )
        else:
            message = (
                f"✅ Recordatorios enviados: {sent}/{checked} cita(s).\n"
                f"{'⚠️ Errores: ' + str(errors) + '.' if errors else ''}"
            ).strip()

        logger.info(f"[TRIGGER] Resultado: {stats}")

        return {**stats, 'message': message}


# Instancia global
reminder_service = ReminderService()


# =========================================================================
# CLI - Para testing manual
# =========================================================================

if __name__ == "__main__":
    print("🔔 Ejecutando servicio de recordatorios...")
    stats = reminder_service.send_daily_reminders()
    print(f"\n📊 Resultados: {stats}")