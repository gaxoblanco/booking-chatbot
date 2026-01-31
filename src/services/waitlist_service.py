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
        freed_time: str
    ) -> List[Dict]:
        """
        Busca clientes candidatos para adelantar turno.
        
        Criterios:
        - Mismo profesional
        - Turno en días posteriores (próximos 30 días)
        - Estado = 'confirmada'
        - wants_earlier_slot = 1
        - No tiene oferta pendiente activa
        
        Ordenados por:
        1. Fecha más cercana primero
        2. Hora más cercana primero
        
        Args:
            professional_phone: Teléfono del profesional
            freed_date: Fecha del turno liberado (YYYY-MM-DD)
            freed_time: Hora del turno liberado (HH:MM)
        
        Returns:
            Lista de candidatos con sus datos de cita
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
                SELECT offered_to_client_phone 
                FROM slot_offers 
                WHERE status = 'pending'
                AND expires_at > CURRENT_TIMESTAMP
            )
            ORDER BY a.appointment_date ASC, a.start ASC
            LIMIT 10
        """
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (professional_phone, freed_date, freed_date))
                
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
            
            # Enviar vía Twilio (usando template)
            from twilio.rest import Client
            import os
            
            client = Client(
                os.getenv('TWILIO_ACCOUNT_SID'),
                os.getenv('TWILIO_AUTH_TOKEN')
            )
            
            # Formatear fecha para mensaje
            date_obj = datetime.strptime(freed_apt['appointment_date'], "%Y-%m-%d")
            dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
            dia_nombre = dias[date_obj.weekday()]
            fecha_formatted = f"{dia_nombre} {date_obj.strftime('%d/%m/%Y')}"
            
            # Usar template si está aprobado, sino mensaje directo
            result = client.messages.create(
                from_=f"{os.getenv('TWILIO_WHATSAPP_NUMBER')}",
                to=f"{candidate['client_phone']}",
                body=message  # TODO: Usar template cuando esté aprobado
            )
            
            if result.sid:
                logger.info(f"✅ Oferta enviada (SID: {result.sid})")
                return True
            else:
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
        """Cliente acepta la oferta - mover su turno."""
        try:
            logger.info(f"✅ Cliente {offer['offered_to_client_phone']} aceptó oferta #{offer['id']}")
            
            # TODO: Implementar movimiento de turno
            # 1. Actualizar appointment original con nueva fecha/hora
            # 2. Actualizar Google Calendar
            # 3. Marcar oferta como 'accepted'
            # 4. Marcar turno viejo como 'moved'
            
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Actualizar oferta
                cursor.execute("""
                    UPDATE slot_offers
                    SET status = 'accepted',
                        response_received_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (offer['id'],))
                
                # Actualizar cita del cliente
                cursor.execute("""
                    UPDATE appointments
                    SET appointment_date = ?,
                        start = ?,
                        moved_from_offer_id = ?
                    WHERE id = ?
                """, (
                    offer['freed_date'],
                    offer['freed_time'],
                    offer['id'],
                    offer['original_appointment_id']
                ))
                
                logger.info("✅ Turno movido exitosamente")
            
            return {
                'success': True,
                'action': 'accepted',
                'message': f"""✅ ¡Perfecto! Tu turno fue adelantado.

📅 *Nuevo turno:*
Fecha: {offer['freed_date']}
Hora: {offer['freed_time']}

Tu turno anterior fue cancelado automáticamente."""
            }
            
        except Exception as e:
            logger.error(f"Error aceptando oferta: {e}")
            return {
                'success': False,
                'message': "Error moviendo el turno. Intenta nuevamente."
            }
    
    def _reject_offer(self, offer: Dict) -> Dict:
        """Cliente rechaza la oferta - ofrecer al siguiente."""
        try:
            logger.info(f"❌ Cliente {offer['offered_to_client_phone']} rechazó oferta #{offer['id']}")
            
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE slot_offers
                    SET status = 'rejected',
                        response_received_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (offer['id'],))
            
            # Buscar siguiente candidato
            # TODO: Ofrecer al siguiente en la lista
            
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
