"""
Waitlist Service - Sistema de Adelantamiento de Turnos
=======================================================

Cuando se cancela/reprograma un turno, este servicio:
1. Busca clientes con turnos en días posteriores
2. Les ofrece el slot liberado por WhatsApp
3. Procesa sus respuestas (acepta/rechaza)
4. Mueve el turno si aceptan

Author: Salud Conecta
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

from src.database.database import db

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WaitlistService:
    """Servicio para gestión de lista de espera y adelantamiento de turnos."""
    
    def __init__(self):
        self.db = db
        # Tiempo de expiración de oferta (30 minutos)
        self.offer_expiration_minutes = 30
    
    # =========================================================================
    # MAIN FUNCTION - Cuando se libera un turno
    # =========================================================================
    
    def handle_slot_freed(
        self, 
        freed_appointment_id: int,
        reason: str = "cancelled"
    ) -> Dict:
        """
        Función principal cuando se libera un turno.
        
        Se llama desde:
        - appointment_service.cancel_appointment()
        - appointment_service.reschedule_appointment()
        
        Args:
            freed_appointment_id: ID de la cita que se liberó
            reason: 'cancelled' o 'rescheduled'
        
        Returns:
            {
                'success': True/False,
                'offered_to': phone o None,
                'candidates_found': int
            }
        """
        logger.info("=" * 60)
        logger.info(f"🔓 TURNO LIBERADO - ID #{freed_appointment_id}")
        logger.info("=" * 60)
        
        try:
            # Paso 1: Obtener datos del turno liberado
            freed_apt = self.db.get_appointment(freed_appointment_id)
            
            if not freed_apt:
                logger.error(f"Cita #{freed_appointment_id} no encontrada")
                return {'success': False}
            
            logger.info(f"📅 Turno liberado:")
            logger.info(f"   Profesional: {freed_apt['professional_phone']}")
            logger.info(f"   Fecha: {freed_apt['appointment_date']}")
            logger.info(f"   Hora: {freed_apt['start']}")
            
            # Paso 2: Buscar candidatos
            candidates = self._find_candidates(
                professional_phone=freed_apt['professional_phone'],
                freed_date=freed_apt['appointment_date'],
                freed_time=freed_apt['start']
            )
            
            logger.info(f"👥 Candidatos encontrados: {len(candidates)}")
            
            if not candidates:
                logger.info("✅ No hay candidatos para ofrecer el turno")
                return {
                    'success': True,
                    'offered_to': None,
                    'candidates_found': 0
                }
            
            # Paso 3: Ofrecer al primer candidato
            first_candidate = candidates[0]
            
            success = self._send_offer(
                freed_appointment_id=freed_appointment_id,
                candidate=first_candidate,
                freed_apt=freed_apt
            )
            
            if success:
                logger.info(f"✅ Oferta enviada a {first_candidate['client_phone']}")
                return {
                    'success': True,
                    'offered_to': first_candidate['client_phone'],
                    'candidates_found': len(candidates)
                }
            else:
                logger.error("❌ Error enviando oferta")
                return {
                    'success': False,
                    'candidates_found': len(candidates)
                }
                
        except Exception as e:
            logger.error(f"Error en handle_slot_freed: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False}
    
    # =========================================================================
    # BÚSQUEDA DE CANDIDATOS
    # =========================================================================
    
    def _find_candidates(
        self,
        professional_phone: str,
        freed_date: str,
        freed_time: str,
        exclude_phone: str = None,
        freed_apt_id: int = None
    ) -> List[Dict]:
        """
        Busca clientes candidatos para adelantar turno.

        Criterios:
        - Mismo profesional
        - Turno en días posteriores (próximos 30 días)
        - Estado = 'confirmada'
        - wants_earlier_slot = 1
        - Sin oferta pending activa
        - Sin 3+ rechazos en los últimos 30 días con este profesional (anti-spam)
        - No rechazó ya este slot específico en la cascada actual

        Args:
            professional_phone: Teléfono del profesional
            freed_date: Fecha del turno liberado (YYYY-MM-DD)
            freed_time: Hora del turno liberado (HH:MM)
            exclude_phone: Excluir explícitamente (quien acaba de rechazar)
            freed_apt_id: ID del slot liberado — excluye a todos los que
                          ya rechazaron este slot específico en la cascada

        Returns:
            Lista de candidatos ordenados por fecha más cercana primero
        """
        query = """
            SELECT 
                a.id,
                a.client_phone,
                a.appointment_date,
                a.start,
                a.end,
                c.name as client_name
            FROM appointments a
            LEFT JOIN clients c ON a.client_phone = c.phone
            WHERE a.professional_phone = ?
            AND a.appointment_date > ?
            AND a.appointment_date <= DATE(?, '+30 days')
            AND a.status = 'confirmada'
            AND (a.wants_earlier_slot IS NULL OR a.wants_earlier_slot = 1)
            AND a.client_phone NOT IN (
                -- Excluir clientes con oferta pendiente activa
                SELECT offered_to_client_phone
                FROM slot_offers
                WHERE status = 'pending'
                AND expires_at > CURRENT_TIMESTAMP
            )
            AND a.client_phone NOT IN (
                -- Anti-spam: excluir clientes que rechazaron 3+ veces con el MISMO
                -- profesional en los últimos 30 días.
                -- Acotado a profesional: si el cliente tiene turno con otro profesional
                -- o el mismo pasados 30 días, vuelve a aparecer como candidato.
                SELECT offered_to_client_phone
                FROM slot_offers
                WHERE status = 'rejected'
                AND professional_phone = ?
                AND offered_at >= DATE('now', '-30 days')
                GROUP BY offered_to_client_phone
                HAVING COUNT(*) >= 3
            )
            AND a.client_phone NOT IN (
                -- Cascada: excluir a todos los que ya rechazaron ESTE slot específico.
                -- Evita que la cascada vuelva a ofrecer a alguien que ya dijo que no
                -- en la misma ronda, aunque no haya llegado al límite del anti-spam.
                SELECT offered_to_client_phone
                FROM slot_offers
                WHERE status = 'rejected'
                AND freed_appointment_id = ?
            )
            AND a.client_phone != ?
            ORDER BY a.appointment_date ASC, a.start ASC
            LIMIT 10
        """
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                # Params posicionales:
                # 1. professional_phone (WHERE)
                # 2. freed_date (fecha posterior)
                # 3. freed_date (rango 30 días)
                # 4. professional_phone (filtro anti-spam)
                # 5. freed_apt_id (rechazos de este slot específico)
                #    Si no se provee usamos -1 — nunca coincide con un ID real
                # 6. exclude_phone (quien acaba de rechazar ahora mismo)
                #    Si no hay nadie usamos '' — nunca coincide con un teléfono real
                params = [
                    professional_phone,
                    freed_date,
                    freed_date,
                    professional_phone,
                    freed_apt_id if freed_apt_id else -1,
                    exclude_phone if exclude_phone else '',
                ]

                cursor.execute(query, params)

                columns = [desc[0] for desc in cursor.description]
                candidates = [dict(zip(columns, row)) for row in cursor.fetchall()]

                return candidates

        except Exception as e:
            logger.error(f"Error buscando candidatos: {e}")
            return []
    
    # =========================================================================
    # ENVÍO DE OFERTA
    # =========================================================================
    
    def _send_offer(
        self,
        freed_appointment_id: int,
        candidate: Dict,
        freed_apt: Dict
    ) -> bool:
        """
        Envía oferta de turno adelantado al candidato.
        
        Args:
            freed_appointment_id: ID del turno liberado
            candidate: Datos del candidato
            freed_apt: Datos del turno liberado
        
        Returns:
            True si se envió exitosamente
        """
        try:
            # Formatear mensaje
            message = self._format_offer_message(freed_apt, candidate)
            
            # Calcular expiración (30 minutos desde ahora)
            expires_at = datetime.now() + timedelta(minutes=self.offer_expiration_minutes)
            
            # Registrar oferta en BD
            offer_id = self._create_offer_record(
                freed_appointment_id=freed_appointment_id,
                candidate=candidate,
                freed_apt=freed_apt,
                expires_at=expires_at
            )
            
            if not offer_id:
                return False
            
            # Enviar vía MessageSender centralizado
            from src.core.message_sender import message_sender

            sent = message_sender.send_with_retry(
                to_phone           = candidate['client_phone'],
                message            = message,
                professional_phone = freed_apt['professional_phone'],
                patient_name       = candidate.get('client_name'),
                appointment_id     = candidate.get('id'),
            )

            if sent:
                logger.info(f"✅ Oferta enviada (offer_id: {offer_id})")
                return True
            return False
                
        except Exception as e:
            logger.error(f"Error enviando oferta: {e}")
            return False
    
    def _format_offer_message(self, freed_apt: Dict, candidate: Dict) -> str:
        """Formatea mensaje de oferta."""
        # Formatear fecha
        date_obj = datetime.strptime(freed_apt['appointment_date'], "%Y-%m-%d")
        dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        dia_nombre = dias[date_obj.weekday()]
        fecha_formatted = f"{dia_nombre} {date_obj.strftime('%d/%m/%Y')}"
        
        # Obtener nombre del profesional
        prof = self.db.get_professional(freed_apt['professional_phone'])
        prof_name = prof.get('name', 'Profesional') if prof else 'Profesional'
        
        message = f"""✨ *TURNO DISPONIBLE*

¡Buenas noticias! Se liberó un turno antes de lo esperado:

👨‍⚕️ *Profesional:* {prof_name}
📅 *Fecha:* {fecha_formatted}
⏰ *Horario:* {freed_apt['start']} hs

¿Te gustaría adelantar tu turno?

1️⃣ Sí, acepto este turno
2️⃣ No, prefiero mantener mi turno actual

_Esta oferta expira en {self.offer_expiration_minutes} minutos_"""

        return message
    
    def _create_offer_record(
        self,
        freed_appointment_id: int,
        candidate: Dict,
        freed_apt: Dict,
        expires_at: datetime
    ) -> Optional[int]:
        """Crea registro de oferta en BD."""
        try:
            # Obtener nombre del profesional
            prof = self.db.get_professional(freed_apt['professional_phone'])
            prof_name = prof.get('name') if prof else None
            
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO slot_offers 
                    (freed_appointment_id, offered_to_client_phone, original_appointment_id,
                     freed_date, freed_time, professional_phone, professional_name, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    freed_appointment_id,
                    candidate['client_phone'],
                    candidate['id'],
                    freed_apt['appointment_date'],
                    freed_apt['start'],
                    freed_apt['professional_phone'],
                    prof_name,
                    expires_at.isoformat()
                ))
                
                return cursor.lastrowid
                
        except Exception as e:
            logger.error(f"Error creando registro de oferta: {e}")
            return None
    
    # =========================================================================
    # RESPUESTAS DEL CLIENTE
    # =========================================================================
    
    def handle_offer_response(
        self,
        client_phone: str,
        response: str
    ) -> Dict:
        """
        Procesa respuesta del cliente a oferta de turno.
        
        Args:
            client_phone: Teléfono del cliente
            response: "1" (acepta) o "2" (rechaza)
        
        Returns:
            {
                'success': True/False,
                'action': 'accepted' | 'rejected' | 'expired',
                'message': str
            }
        """
        # Buscar oferta pendiente
        offer = self._get_pending_offer(client_phone)
        
        if not offer:
            return {
                'success': False,
                'message': "No tienes ofertas de turno pendientes."
            }
        
        # Verificar si expiró
        if datetime.now() > datetime.fromisoformat(offer['expires_at']):
            self._mark_offer_expired(offer['id'])
            return {
                'success': False,
                'action': 'expired',
                'message': "⏰ La oferta expiró. Ya fue ofrecida a otro paciente."
            }
        
        # Opción 1: ACEPTA
        if response == '1':
            return self._accept_offer(offer)
        
        # Opción 2: RECHAZA
        elif response == '2':
            return self._reject_offer(offer)
        
        else:
            return {
                'success': False,
                'message': "Opción inválida. Responde 1 o 2."
            }
    
    def _get_pending_offer(self, client_phone: str) -> Optional[Dict]:
        """Obtiene oferta pendiente del cliente."""
        query = """
            SELECT *
            FROM slot_offers
            WHERE offered_to_client_phone = ?
            AND status = 'pending'
            AND expires_at > CURRENT_TIMESTAMP
            ORDER BY offered_at DESC
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
            logger.error(f"Error obteniendo oferta: {e}")
            return None
    
    def _accept_offer(self, offer: Dict) -> Dict:
        """
        Cliente acepta la oferta — mueve el turno en BD y en Google Calendar.

        Orden de operaciones:
            1. Cancelar la cita liberada en BD (libera UNIQUE constraint)
            2. Marcar oferta como 'accepted'
            3. Calcular new_end_time desde duration_minutes de la cita original
            4. Mover la cita del cliente en BD
            5. Actualizar Google Calendar (reschedule del evento)
        """
        try:
            logger.info(
                f"✅ Cliente {offer['offered_to_client_phone']} "
                f"aceptó oferta #{offer['id']}"
            )

            # ── Datos que necesitamos ────────────────────────────────────────
            freed_apt_id    = offer['freed_appointment_id']
            original_apt_id = offer['original_appointment_id']
            new_date        = offer['freed_date']
            new_start       = offer['freed_time']

            # Calcular new_end desde duration_minutes de la cita original
            original_apt = self.db.get_appointment(original_apt_id)
            if not original_apt:
                raise ValueError(f"Cita original #{original_apt_id} no encontrada")

            duration = original_apt.get('duration_minutes', 50)
            h, m     = map(int, new_start.split(':'))
            end_total_min = h * 60 + m + duration
            new_end  = f"{end_total_min // 60:02d}:{end_total_min % 60:02d}"

            # ── Paso 1-4: BD ─────────────────────────────────────────────────
            with self.db.get_connection() as conn:
                cursor = conn.cursor()

                # 1. Cancelar el turno liberado para liberar UNIQUE constraint
                #    (professional_phone, appointment_date, start)
                cursor.execute("""
                    UPDATE appointments
                    SET status = 'cancelada_cliente'
                    WHERE id = ?
                """, (freed_apt_id,))

                # 2. Marcar oferta como aceptada
                cursor.execute("""
                    UPDATE slot_offers
                    SET status = 'accepted',
                        response_received_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (offer['id'],))

                # 3. Mover la cita del cliente a la nueva fecha/hora
                cursor.execute("""
                    UPDATE appointments
                    SET appointment_date    = ?,
                        start               = ?,
                        end                 = ?,
                        moved_from_offer_id = ?
                    WHERE id = ?
                """, (new_date, new_start, new_end, offer['id'], original_apt_id))

            logger.info(
                f"✅ BD actualizada — cita #{original_apt_id} "
                f"movida a {new_date} {new_start}-{new_end}"
            )

            # ── Paso 5: Google Calendar ───────────────────────────────────────
            # Usamos AppointmentCalendarService que ya maneja el reschedule
            # de forma segura (si no hay google_event_id, solo actualiza BD)
            try:
                from src.integrations.appointment_calendar_service import (
                    AppointmentCalendarService,
                )
                calendar_service = AppointmentCalendarService(self.db)
                calendar_service.reschedule_appointment(
                    appointment_id = original_apt_id,
                    new_date       = new_date,
                    new_start_time = new_start,
                    new_end_time   = new_end,
                )
                logger.info(
                    f"✅ Google Calendar actualizado — "
                    f"evento de cita #{original_apt_id} reprogramado"
                )
            except Exception as cal_error:
                # El turno ya está correcto en BD — no revertir.
                # Solo loguear para que el profesional pueda corregir manualmente.
                logger.error(
                    f"⚠️ BD actualizada pero Google Calendar falló "
                    f"para cita #{original_apt_id}: {cal_error}"
                )

            return {
                'success': True,
                'action':  'accepted',
                'message': (
                    f"✅ ¡Perfecto! Tu turno fue adelantado.\n\n"
                    f"📅 *Nuevo turno:*\n"
                    f"Fecha: {new_date}\n"
                    f"Hora: {new_start} hs\n\n"
                    f"Tu turno anterior fue cancelado automáticamente."
                ),
            }

        except Exception as e:
            logger.error(f"Error aceptando oferta: {e}")
            return {
                'success': False,
                'message': "Error moviendo el turno. Intenta nuevamente.",
            }

    def _reject_offer(self, offer: Dict) -> Dict:
        """
        Cliente rechaza la oferta.

        Cascada:
            1. Marca la oferta actual como 'rejected'
            2. Busca el siguiente candidato para el mismo slot liberado
               (excluye a quien acaba de rechazar y a quienes ya rechazaron)
            3. Si hay siguiente → envía nueva oferta
            4. Si no hay más → slot queda libre, fin del ciclo

        Anti-spam (via _find_candidates):
            Si un cliente rechazó 3+ veces en 30 días no aparece más como candidato.
        """
        try:
            client = offer['offered_to_client_phone']
            offer_id = offer['id']
            freed_apt_id = offer['freed_appointment_id']

            logger.info(f"❌ Cliente {client} rechazó oferta #{offer_id}")

            # Paso 1: Marcar como rechazada
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE slot_offers
                    SET status = 'rejected',
                        response_received_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (offer_id,))

            # Paso 2: Obtener datos del slot liberado para buscar siguiente candidato
            freed_apt = self.db.get_appointment(freed_apt_id)
            if not freed_apt:
                logger.warning(f"No se encontró cita #{freed_apt_id} para continuar cascada")
                return {
                    'success': True,
                    'action': 'rejected',
                    'message': "👍 Entendido. Mantenés tu turno original."
                }

            # Paso 3: Buscar siguiente candidato
            # _find_candidates ya excluye:
            #   - Clientes con oferta pending activa
            #   - Clientes con 3+ rechazos en 30 días (anti-spam)
            # Aquí además excluimos al cliente que acaba de rechazar esta oferta
            candidates = self._find_candidates(
                professional_phone=freed_apt['professional_phone'],
                freed_date=freed_apt['appointment_date'],
                freed_time=freed_apt['start'],
                exclude_phone=client,
                freed_apt_id=freed_apt_id  # Excluir todos los que ya rechazaron este slot
            )

            if not candidates:
                logger.info(f"No hay más candidatos para el slot #{freed_apt_id} — fin de cascada")
                return {
                    'success': True,
                    'action': 'rejected',
                    'message': "👍 Entendido. Mantenés tu turno original."
                }

            # Paso 4: Ofrecer al siguiente candidato
            next_candidate = candidates[0]
            logger.info(f"→ Ofreciendo al siguiente candidato: {next_candidate['client_phone']}")

            self._send_offer(
                freed_appointment_id=freed_apt_id,
                candidate=next_candidate,
                freed_apt=freed_apt
            )

            return {
                'success': True,
                'action': 'rejected',
                'message': "👍 Entendido. Mantenés tu turno original."
            }

        except Exception as e:
            logger.error(f"Error rechazando oferta: {e}")
            return {'success': False}
    
    def _mark_offer_expired(self, offer_id: int):
        """Marca oferta como expirada."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE slot_offers
                    SET status = 'expired'
                    WHERE id = ?
                """, (offer_id,))
        except Exception as e:
            logger.error(f"Error marcando oferta expirada: {e}")

    def process_expired_offers(self) -> dict:
        """
        Procesa todas las ofertas de waitlist que expiraron sin respuesta.

        Una oferta expira cuando el cliente no responde antes de expires_at.
        Sin este método, el slot queda en limbo: la oferta sigue 'pending'
        aunque ya no sea válida, y la cascada no continúa.

        Flujo por cada oferta expirada:
            1. Marcar la oferta como 'expired'
            2. Buscar el siguiente candidato para ese mismo slot
            (reutiliza _find_candidates con los mismos filtros anti-spam)
            3. Si hay candidato → enviar nueva oferta (_send_offer)
            4. Si no hay más candidatos → slot queda libre, fin de cascada

        Returns:
            Dict con estadísticas:
            {
                'processed': int,   # total de ofertas expiradas encontradas
                'reoffered': int,   # ofertas que generaron nueva oferta
                'freed': int,       # slots que quedaron libres (sin más candidatos)
                'errors': int       # errores durante el procesamiento
            }
        """
        stats = {'processed': 0, 'reoffered': 0, 'freed': 0, 'errors': 0}

        try:
            expired_offers = self.db.get_expired_pending_offers()
            stats['processed'] = len(expired_offers)

            if not expired_offers:
                logger.info("[WAITLIST] ✅ Sin ofertas expiradas para procesar")
                return stats

            logger.info(f"[WAITLIST] 🔄 Procesando {len(expired_offers)} ofertas expiradas")

            for offer in expired_offers:
                offer_id     = offer['id']
                freed_apt_id = offer['freed_appointment_id']
                client       = offer['offered_to_client_phone']

                try:
                    # Paso 1: Marcar como expirada (ya existe _mark_offer_expired)
                    self._mark_offer_expired(offer_id)
                    logger.info(f"[WAITLIST] ⏰ Oferta #{offer_id} marcada como expired "
                                f"(cliente {client} no respondió)")

                    # Paso 2: Obtener datos del slot liberado
                    freed_apt = self.db.get_appointment(freed_apt_id)
                    if not freed_apt:
                        logger.warning(f"[WAITLIST] ⚠️ Cita #{freed_apt_id} no encontrada, "
                                    f"no se puede continuar cascada")
                        stats['freed'] += 1
                        continue

                    # Paso 3: Buscar siguiente candidato
                    # _find_candidates excluye: clientes con oferta pending,
                    # anti-spam (3+ rechazos en 30 días), y quien expiró esta oferta
                    candidates = self._find_candidates(
                        professional_phone=freed_apt['professional_phone'],
                        freed_date=freed_apt['appointment_date'],
                        freed_time=freed_apt['start'],
                        exclude_phone=client,
                        freed_apt_id=freed_apt_id
                    )

                    # Paso 4: Ofrecer al siguiente o liberar el slot
                    if candidates:
                        next_candidate = candidates[0]
                        self._send_offer(
                            freed_appointment_id=freed_apt_id,
                            candidate=next_candidate,
                            freed_apt=freed_apt
                        )
                        logger.info(f"[WAITLIST] ✅ Nueva oferta enviada a "
                                    f"{next_candidate['client_phone']} "
                                    f"(slot #{freed_apt_id})")
                        stats['reoffered'] += 1
                    else:
                        logger.info(f"[WAITLIST] 🔓 Slot #{freed_apt_id} queda libre "
                                    f"— sin más candidatos")
                        stats['freed'] += 1

                except Exception as e:
                    logger.error(f"[WAITLIST] ❌ Error procesando oferta #{offer_id}: {e}")
                    stats['errors'] += 1

        except Exception as e:
            logger.error(f"[WAITLIST] ❌ Error crítico en process_expired_offers: {e}")
            stats['errors'] += 1

        logger.info(f"[WAITLIST] 📊 Ofertas expiradas procesadas: {stats}")
        return stats


# Instancia global
waitlist_service = WaitlistService()


# =========================================================================
# CLI - Para testing
# =========================================================================

if __name__ == "__main__":
    print("🔓 Testing Waitlist Service...")
    
    # Test: Simular turno liberado
    result = waitlist_service.handle_slot_freed(
        freed_appointment_id=1,
        reason="cancelled"
    )
    
    print(f"\n📊 Resultado: {result}")