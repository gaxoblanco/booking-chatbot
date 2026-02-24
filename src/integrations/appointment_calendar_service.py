"""
AppointmentCalendarService - Integración entre chatbot y Google Calendar.

Este servicio actúa como puente entre el sistema de citas del chatbot
y Google Calendar, sincronizando las reservas en ambos sistemas.

Uso:
    from src.integrations.appointment_calendar_service import AppointmentCalendarService
    
    calendar_service = AppointmentCalendarService(database)
    
    # Consultar disponibilidad
    slots = calendar_service.get_available_slots(professional_phone, date)
    
    # Crear cita
    appointment_id = calendar_service.create_appointment(...)
    
    # Cancelar cita
    calendar_service.cancel_appointment(appointment_id)
"""

import logging
import json
from datetime import datetime
from typing import List, Dict, Optional

from .google_calendar_service import GoogleCalendarService

# Configurar logger
logger = logging.getLogger(__name__)


class AppointmentCalendarService:
    """
    Servicio de integración entre sistema de citas y Google Calendar.
    
    Sincroniza las operaciones de citas entre la base de datos local
    del chatbot y Google Calendar de los profesionales.
    """
    
    def __init__(self, database):
        """
        Inicializa el servicio de integración.
        
        Args:
            database: Instancia de la base de datos del chatbot
        """
        self.db = database
        self.calendar_service = GoogleCalendarService()
        logger.info("AppointmentCalendarService inicializado")
    
    # ========================================================================
    # DISPONIBILIDAD
    # ========================================================================
    
    def get_available_slots(
        self,
        professional_phone: str,
        date: str
    ) -> List[Dict]:
        """
        Obtiene slots disponibles de un profesional para una fecha.

        Manejo de working_hours (formato por día):
          - Si el JSON tiene claves de días ('lunes', 'martes', etc.)
            extrae el horario del día que corresponde a la fecha pedida.
          - Si el día no está configurado → retorna [] (no trabaja ese día).
          - Retrocompatibilidad: si el JSON tiene formato viejo {'start','end'}
            lo usa tal cual.

        Args:
            professional_phone: Teléfono del profesional
            date: Fecha en formato 'YYYY-MM-DD'

        Returns:
            List[Dict]: Lista de slots disponibles
                [
                    {
                        'date': '2026-01-17',
                        'start': '09:00',
                        'end': '10:00',
                        'start_datetime': '2026-01-17T09:00:00-03:00',
                        'end_datetime': '2026-01-17T10:00:00-03:00',
                        'duration_minutes': 60
                    },
                    ...
                ]

        Raises:
            ValueError: Si el profesional no existe o no tiene calendar_id
        """
        # Mapeo número de día Python (0=lunes) a clave del JSON
        DIA_SEMANA = {
            0: 'lunes',
            1: 'martes',
            2: 'miercoles',
            3: 'jueves',
            4: 'viernes',
            5: 'sabado',
            6: 'domingo'
        }
        DIAS_CONOCIDOS = set(DIA_SEMANA.values())

        logger.info(f"Consultando disponibilidad de {professional_phone} para {date}")

        try:
            # 1. Obtener configuración del profesional desde BD
            professional = self.db.get_professional(professional_phone)
            if not professional:
                raise ValueError(f"Profesional {professional_phone} no encontrado")

            # 2. Verificar calendar_id
            calendar_id = professional.get('calendar_id')
            if not calendar_id:
                raise ValueError(
                    f"Profesional {professional_phone} no tiene calendar_id configurado. "
                    "Configure primero el email de su calendario de Google."
                )

            # 3. Obtener slot_duration de la BD (sin fallback hardcodeado)
            slot_duration = professional.get('slot_duration')
            if not slot_duration:
                raise ValueError(
                    f"Profesional {professional_phone} no tiene slot_duration configurado."
                )

            # 4. Parsear working_hours y resolver el día pedido
            working_hours_json = professional.get('working_hours')
            if not working_hours_json:
                raise ValueError(
                    f"Profesional {professional_phone} no tiene working_hours configurado."
                )

            working_hours_data = json.loads(working_hours_json)

            # Detectar formato: nuevo (por día) vs viejo (plano)
            es_formato_por_dia = any(k in DIAS_CONOCIDOS for k in working_hours_data.keys())

            if es_formato_por_dia:
                # Formato nuevo: extraer el horario del día de la semana
                from datetime import datetime as dt_parser
                numero_dia = dt_parser.strptime(date, '%Y-%m-%d').weekday()
                nombre_dia = DIA_SEMANA[numero_dia]

                if nombre_dia not in working_hours_data:
                    logger.info(
                        f"Profesional {professional_phone} no trabaja los {nombre_dia} ({date})"
                    )
                    return []

                working_hours = working_hours_data[nombre_dia]
                logger.info(f"Horario para {nombre_dia}: {working_hours['start']} - {working_hours['end']}")
            else:
                # Retrocompatibilidad: formato viejo {'start': '09:00', 'end': '18:00'}
                working_hours = working_hours_data
                logger.warning(
                    f"Profesional {professional_phone} usa formato de horario legacy (plano)"
                )

            # 5. Consultar disponibilidad en Google Calendar
            slots = self.calendar_service.get_available_slots(
                calendar_id=calendar_id,
                date=date,
                working_hours=working_hours,
                slot_duration_minutes=slot_duration
            )

            logger.info(f"Encontrados {len(slots)} slots disponibles para {professional_phone}")
            return slots

        except Exception as e:
            logger.error(f"Error al obtener disponibilidad: {e}")
            raise
        
    def check_slot_available(
        self,
        professional_phone: str,
        date: str,
        start_time: str,
        end_time: str
    ) -> bool:
        """
        Verifica si un slot específico está disponible.
        
        Args:
            professional_phone: Teléfono del profesional
            date: Fecha en 'YYYY-MM-DD'
            start_time: Hora inicio en 'HH:MM'
            end_time: Hora fin en 'HH:MM'
        
        Returns:
            bool: True si está disponible
        """
        try:
            professional = self.db.get_professional(professional_phone)
            calendar_id = professional['calendar_id']
            
            is_available = self.calendar_service.check_slot_available(
                calendar_id=calendar_id,
                start_datetime=f"{date} {start_time}",
                end_datetime=f"{date} {end_time}"
            )
            
            return is_available
            
        except Exception as e:
            logger.error(f"Error al verificar slot: {e}")
            return False
    
    # ========================================================================
    # CREACIÓN DE CITAS
    # ========================================================================
    
    def create_appointment(
        self,
        professional_phone: str,
        client_phone: str,
        client_name: str,
        date: str,
        start_time: str,
        end_time: str,
        appointment_type: str,
        notes: Optional[str] = None
    ) -> int:
        """
        Crea una cita en Google Calendar y en la BD local.
        
        Args:
            professional_phone: Teléfono del profesional
            client_phone: Teléfono del cliente
            client_name: Nombre del cliente
            date: Fecha en 'YYYY-MM-DD'
            start_time: Hora inicio en 'HH:MM'
            end_time: Hora fin en 'HH:MM'
            appointment_type: Tipo de consulta
            notes: Notas adicionales (opcional)
        
        Returns:
            int: ID de la cita en BD local
        
        Raises:
            Exception: Si hay error al crear la cita
        """
        logger.info(
            f"Creando cita: {client_name} con {professional_phone} "
            f"el {date} a las {start_time}"
        )
        
        try:
            # 1. Obtener configuración del profesional
            professional = self.db.get_professional(professional_phone)
            calendar_id = professional['calendar_id']
            
            # 2. Crear evento en Google Calendar
            logger.info("Creando evento en Google Calendar...")
            google_event = self.calendar_service.create_appointment(
                calendar_id=calendar_id,
                start_datetime=f"{date} {start_time}",
                end_datetime=f"{date} {end_time}",
                client_name=client_name,
                client_phone=client_phone,
                appointment_type=appointment_type,
                notes=notes
            )
            
            google_event_id = google_event['id']
            logger.info(f"Evento creado en Google Calendar: {google_event_id}")
            
            # 3. Guardar en BD local con referencia a Google Calendar
            logger.info("Guardando cita en BD local...")
            # Calculate duration
            from datetime import datetime as dt
            duration = int((dt.strptime(end_time, '%H:%M') - 
                          dt.strptime(start_time, '%H:%M')).seconds / 60)
            
            # Map appointment_type to valid session_type
            session_type_map = {
                'Consulta': 'primera_vez',
                'primera_vez': 'primera_vez',
                'seguimiento': 'seguimiento',
                'evaluacion': 'evaluacion'
            }
            session_type = session_type_map.get(appointment_type, 'primera_vez')
            
            appointment_id = self.db.create_appointment(
                client_phone=client_phone,
                professional_phone=professional_phone,
                appointment_date=date,
                start=start_time,
                end=end_time,
                duration_minutes=duration,
                session_type=session_type,  # ✅ Mapped value
                modality='presencial',
                google_event_id=google_event_id,  # ⭐ IMPORTANTE
                notes=notes
            )
            
            logger.info(
                f"Cita creada exitosamente. "
                f"BD ID: {appointment_id}, Google ID: {google_event_id}"
            )
            
            # 4. ⭐ NOTIFICAR AL PROFESIONAL por WhatsApp
            try:
                self._notify_professional_new_appointment(
                    professional=professional,
                    client_name=client_name,
                    client_phone=client_phone,
                    date=date,
                    start_time=start_time,
                    end_time=end_time,
                    appointment_id=appointment_id
                )
            except Exception as notify_error:
                logger.error(f"Error al notificar al profesional: {notify_error}")
                # No fallar la creación de cita si falla la notificación
            
            return appointment_id
            
        except Exception as e:
            logger.error(f"Error al crear cita: {e}")
            # Si falló después de crear en Google, intentar limpiar
            if 'google_event_id' in locals():
                try:
                    self.calendar_service.cancel_appointment(
                        calendar_id, google_event_id
                    )
                    logger.info("Evento de Google Calendar limpiado")
                except:
                    pass
            raise
    
    def sync_appointment_from_google(self, appointment_id: int) -> bool:
        """
        Sincroniza una cita desde Google Calendar a la BD local.
        
        Consulta el evento en Google Calendar y actualiza la BD local
        si hay cambios (fecha, hora, status).
        
        Args:
            appointment_id: ID de la cita en BD local
        
        Returns:
            True si se sincronizó exitosamente
            False si hubo error
        """
        from datetime import datetime, timedelta
        
        try:
            print(f"[SYNC] 🔄 Iniciando sync de cita #{appointment_id}")
            
            # ==========================================
            # 1. OBTENER CITA DE BD LOCAL
            # ==========================================
            apt = self.db.get_appointment(appointment_id)
            
            if not apt:
                print(f"[SYNC] ⚠️ Cita #{appointment_id} no encontrada en BD")
                logger.warning(f"[SYNC] ⚠️ Cita #{appointment_id} no encontrada en BD")
                return False
            
            print(f"[SYNC] 📋 Cita en BD local:")
            print(f"       Fecha: {apt['appointment_date']}")
            print(f"       Hora: {apt['start']} - {apt['end']}")
            print(f"       Status: {apt['status']}")
            print(f"       Google Event ID: {apt.get('google_event_id', 'N/A')}")
            
            if not apt.get('google_event_id'):
                print(f"[SYNC] ℹ️ Cita #{appointment_id} no tiene google_event_id, skip")
                logger.debug(f"[SYNC] ℹ️ Cita #{appointment_id} no tiene google_event_id, skip")
                return True
            
            # ==========================================
            # 2. VERIFICAR CACHE (5 MINUTOS)
            # ==========================================
            if apt.get('last_synced_at'):
                try:
                    last_sync = datetime.fromisoformat(apt['last_synced_at'])
                    time_since_sync = (datetime.now() - last_sync).total_seconds()
                    
                    if time_since_sync < 60:  # 1 minutos
                        print(
                            f"[SYNC] ⏭️ Cita #{appointment_id} sincronizada hace "
                            f"{int(time_since_sync)}s, skip (cache)"
                        )
                        logger.debug(
                            f"[SYNC] ⏭️ Cita #{appointment_id} sincronizada hace "
                            f"{int(time_since_sync)}s, skip (cache)"
                        )
                        return True
                except (ValueError, TypeError):
                    pass
            
            # ==========================================
            # 3. OBTENER PROFESIONAL Y CALENDAR_ID
            # ==========================================
            professional = self.db.get_professional(apt['professional_phone'])
            
            if not professional or not professional.get('calendar_id'):
                print(
                    f"[SYNC] ⚠️ Profesional {apt['professional_phone']} "
                    f"no tiene calendar_id configurado"
                )
                logger.warning(
                    f"[SYNC] ⚠️ Profesional {apt['professional_phone']} "
                    f"no tiene calendar_id configurado"
                )
                return False
            
            calendar_id = professional['calendar_id']
            google_event_id = apt['google_event_id']
            
            print(f"[SYNC] 📧 Calendar ID: {calendar_id}")
            print(f"[SYNC] 🆔 Google Event ID: {google_event_id}")
            
            # ==========================================
            # 4. CONSULTAR GOOGLE CALENDAR
            # ==========================================
            print(f"[SYNC] 🌐 Consultando Google Calendar...")
            logger.debug(
                f"[SYNC] 🔄 Consultando Google Calendar para cita #{appointment_id} "
                f"(event {google_event_id})"
            )
            
            try:
                event = self.calendar_service.get_event(
                    calendar_id=calendar_id,
                    event_id=google_event_id
                )
                
                print(f"[SYNC] ✅ Evento obtenido de Google Calendar")
                print(f"       Summary: {event.get('summary', 'N/A')}")
                print(f"       Status: {event.get('status', 'N/A')}")
                
            except Exception as e:
                # Si el evento no existe en Google, marcarlo como cancelado
                if "404" in str(e) or "not found" in str(e).lower():
                    print(
                        f"[SYNC] ⚠️ Evento {google_event_id} no existe en Google Calendar, "
                        f"marcando como cancelado"
                    )
                    logger.warning(
                        f"[SYNC] ⚠️ Evento {google_event_id} no existe en Google Calendar, "
                        f"marcando como cancelado"
                    )
                    
                    google_data = {
                        'date': apt['appointment_date'],
                        'start': apt['start'],
                        'end': apt['end'],
                        'status': 'cancelada_profesional'
                    }
                    
                    return self.db.update_appointment_from_google(appointment_id, google_data)
                else:
                    print(f"[SYNC] ❌ Error consultando Google Calendar: {e}")
                    logger.error(f"[SYNC] ❌ Error consultando Google Calendar: {e}")
                    return False
            
            # ==========================================
            # 5. PARSEAR DATOS DE GOOGLE
            # ==========================================
            # Extraer fecha y hora de start/end
            # Formato Google: '2026-01-20T10:00:00-03:00'
            
            start_datetime = event['start'].get('dateTime', '')
            end_datetime = event['end'].get('dateTime', '')
            
            print(f"[SYNC] 📅 Datos en Google Calendar:")
            print(f"       Start: {start_datetime}")
            print(f"       End: {end_datetime}")
            
            if not start_datetime or not end_datetime:
                print(f"[SYNC] ⚠️ Evento sin dateTime, skip")
                logger.warning(f"[SYNC] ⚠️ Evento sin dateTime, skip")
                return False
            
            # Parsear
            google_date = start_datetime[:10]  # '2026-01-20'
            google_start = start_datetime[11:16]  # '10:00'
            google_end = end_datetime[11:16]  # '10:50'
            
            print(f"[SYNC] 📊 Datos parseados:")
            print(f"       Fecha: {google_date}")
            print(f"       Inicio: {google_start}")
            print(f"       Fin: {google_end}")
            
            # Mapear status de Google a nuestro sistema
            google_status = event.get('status', 'confirmed')
            
            if google_status == 'confirmed':
                our_status = 'confirmada'
            elif google_status == 'cancelled':
                our_status = 'cancelada_profesional'
            else:
                our_status = 'pendiente_confirmacion'
            
            print(f"[SYNC] 🔖 Status Google: {google_status} → Nuestro: {our_status}")
            
            # ==========================================
            # 6. COMPARAR Y ACTUALIZAR SI HAY CAMBIOS
            # ==========================================
            # Detectar si hubo cambios
            has_changes = (
                google_date != apt['appointment_date'] or
                google_start != apt['start'] or
                google_end != apt['end'] or
                our_status != apt['status']
            )
            
            print(f"[SYNC] 🔍 Comparación:")
            print(f"       Fecha BD: {apt['appointment_date']} vs Google: {google_date} → {'CAMBIÓ' if google_date != apt['appointment_date'] else 'OK'}")
            print(f"       Inicio BD: {apt['start']} vs Google: {google_start} → {'CAMBIÓ' if google_start != apt['start'] else 'OK'}")
            print(f"       Fin BD: {apt['end']} vs Google: {google_end} → {'CAMBIÓ' if google_end != apt['end'] else 'OK'}")
            print(f"       Status BD: {apt['status']} vs Google: {our_status} → {'CAMBIÓ' if our_status != apt['status'] else 'OK'}")
            
            if has_changes:
                print(f"[SYNC] 🔄 DETECTADOS CAMBIOS - Actualizando BD local...")
                logger.info(
                    f"[SYNC] 🔄 Detectados cambios en cita #{appointment_id}:"
                )
                
                if google_date != apt['appointment_date']:
                    print(f"[SYNC]    Fecha: {apt['appointment_date']} → {google_date}")
                    logger.info(f"      Fecha: {apt['appointment_date']} → {google_date}")
                if google_start != apt['start']:
                    print(f"[SYNC]    Hora inicio: {apt['start']} → {google_start}")
                    logger.info(f"      Hora inicio: {apt['start']} → {google_start}")
                if google_end != apt['end']:
                    print(f"[SYNC]    Hora fin: {apt['end']} → {google_end}")
                    logger.info(f"      Hora fin: {apt['end']} → {google_end}")
                if our_status != apt['status']:
                    print(f"[SYNC]    Status: {apt['status']} → {our_status}")
                    logger.info(f"      Status: {apt['status']} → {our_status}")
                
                # Actualizar BD
                google_data = {
                    'date': google_date,
                    'start': google_start,
                    'end': google_end,
                    'status': our_status
                }
                
                success = self.db.update_appointment_from_google(appointment_id, google_data)
                
                if success:
                    print(f"[SYNC] ✅ Cita #{appointment_id} actualizada exitosamente")
                    logger.info(f"[SYNC] ✅ Cita #{appointment_id} actualizada exitosamente")
                else:
                    print(f"[SYNC] ❌ Error actualizando cita #{appointment_id}")
                    logger.error(f"[SYNC] ❌ Error actualizando cita #{appointment_id}")
                
                return success
            
            else:
                # No hay cambios, solo actualizar timestamp
                print(f"[SYNC] ✅ Cita #{appointment_id} sin cambios, actualizando timestamp")
                logger.debug(f"[SYNC] ✅ Cita #{appointment_id} sin cambios, actualizando timestamp")
                
                # Actualizar solo last_synced_at
                try:
                    with self.db.get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            UPDATE appointments 
                            SET last_synced_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        """, (appointment_id,))
                    print(f"[SYNC] ✅ Timestamp actualizado")
                except Exception as e:
                    print(f"[SYNC] ⚠️ Error actualizando timestamp: {e}")
                    logger.error(f"[SYNC] Error actualizando timestamp: {e}")
                
                return True
        
        except Exception as e:
            print(f"[SYNC] ❌ Error en sync_appointment_from_google: {e}")
            logger.error(f"[SYNC] ❌ Error en sync_appointment_from_google: {e}")
            import traceback
            traceback.print_exc()
            return False

    def sync_appointments_list(self, appointment_ids: list) -> dict:
        """
        Sincroniza múltiples citas en batch.
        
        Útil para sincronizar todas las citas de un usuario de una vez.
        
        Args:
            appointment_ids: Lista de IDs de citas a sincronizar
        
        Returns:
            Dict con resumen:
            {
                'total': 5,
                'synced': 4,
                'failed': 1,
                'cached': 2,
                'updated': 2
            }
        """
        logger.info(f"[SYNC] 📦 Sincronizando {len(appointment_ids)} citas...")
        
        results = {
            'total': len(appointment_ids),
            'synced': 0,
            'failed': 0,
            'cached': 0,
            'updated': 0
        }
        
        for apt_id in appointment_ids:
            try:
                # Obtener cita para verificar si necesita sync
                apt = self.db.get_appointment(apt_id)
                
                if not apt:
                    results['failed'] += 1
                    continue
                
                # Verificar cache
                needs_sync = True
                if apt.get('last_synced_at'):
                    try:
                        from datetime import datetime
                        last_sync = datetime.fromisoformat(apt['last_synced_at'])
                        if (datetime.now() - last_sync).total_seconds() < 300:
                            needs_sync = False
                            results['cached'] += 1
                    except:
                        pass
                
                if not needs_sync:
                    continue
                
                # Sincronizar
                success = self.sync_appointment_from_google(apt_id)
                
                if success:
                    results['synced'] += 1
                    # TODO: Detectar si realmente se actualizó (no solo timestamp)
                    # Por ahora asumimos que si se sincronizó, se actualizó
                    results['updated'] += 1
                else:
                    results['failed'] += 1
            
            except Exception as e:
                logger.error(f"[SYNC] Error sincronizando cita #{apt_id}: {e}")
                results['failed'] += 1
        
        logger.info(
            f"[SYNC] ✅ Sincronización completada: "
            f"{results['synced']}/{results['total']} exitosas, "
            f"{results['cached']} en cache, "
            f"{results['failed']} fallidas"
        )
        
        return results

    # ========================================================================
    # CANCELACIÓN DE CITAS
    # ========================================================================
    
    def cancel_appointment(
        self,
        appointment_id: int,
        cancellation_reason: str = "Cancelado por el cliente"
    ) -> bool:
        """
        Cancela una cita en Google Calendar y en BD local.
        
        Args:
            appointment_id: ID de la cita en BD local
            cancellation_reason: Motivo de la cancelación
        
        Returns:
            bool: True si se canceló exitosamente
        """
        logger.info(f"Cancelando cita {appointment_id}")
        
        try:
            # 1. Obtener información de la cita desde BD
            appointment = self.db.get_appointment(appointment_id)
            
            if not appointment:
                raise ValueError(f"Cita {appointment_id} no encontrada")
            
            # 2. Obtener google_event_id
            google_event_id = appointment.get('google_event_id')
            
            if google_event_id:
                # 3. Obtener calendar_id del profesional
                professional = self.db.get_professional(
                    appointment['professional_phone']
                )
                calendar_id = professional['calendar_id']
                
                # 4. Cancelar en Google Calendar
                logger.info(f"Cancelando evento en Google Calendar: {google_event_id}")
                self.calendar_service.cancel_appointment(
                    calendar_id=calendar_id,
                    event_id=google_event_id,
                    cancellation_reason=cancellation_reason
                )
                logger.info("Evento cancelado en Google Calendar")
            else:
                logger.warning(
                    f"Cita {appointment_id} no tiene google_event_id, "
                    "solo se cancelará en BD local"
                )
            
            # 5. Actualizar estado en BD local
            self.db.update_appointment_status(
                appointment_id=appointment_id,
                new_status='cancelada_cliente',
                changed_by='client',
                reason=cancellation_reason
            )
            
            logger.info(f"Cita {appointment_id} cancelada exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"Error al cancelar cita: {e}")
            raise
    
    # ========================================================================
    # REPROGRAMACIÓN
    # ========================================================================
    
    def reschedule_appointment(
        self,
        appointment_id: int,
        new_date: str,
        new_start_time: str,
        new_end_time: str
    ) -> bool:
        """
        Reprograma una cita a un nuevo horario.
        
        Args:
            appointment_id: ID de la cita
            new_date: Nueva fecha 'YYYY-MM-DD'
            new_start_time: Nueva hora inicio 'HH:MM'
            new_end_time: Nueva hora fin 'HH:MM'
        
        Returns:
            bool: True si se reprogramó exitosamente
        """
        logger.info(
            f"Reprogramando cita {appointment_id} a {new_date} {new_start_time}"
        )
        
        try:
            # 1. Obtener cita actual
            appointment = self.db.get_appointment(appointment_id)
            google_event_id = appointment.get('google_event_id')
            
            if google_event_id:
                # 2. Obtener calendar_id
                professional = self.db.get_professional(
                    appointment['professional_phone']
                )
                calendar_id = professional['calendar_id']
                
                # 3. Reprogramar en Google Calendar
                self.calendar_service.reschedule_appointment(
                    calendar_id=calendar_id,
                    event_id=google_event_id,
                    new_start_datetime=f"{new_date} {new_start_time}",
                    new_end_datetime=f"{new_date} {new_end_time}"
                )
            
            # 4. Actualizar en BD local
            self.db.update_appointment_datetime(
                appointment_id=appointment_id,
                new_date=new_date,
                new_start_time=new_start_time,
                new_end_time=new_end_time,
                changed_by='client'
            )
            
            logger.info(f"Cita {appointment_id} reprogramada exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"Error al reprogramar cita: {e}")
            raise
    
    # ========================================================================
    # NOTIFICACIONES
    # ========================================================================
    
    def _notify_professional_new_appointment(
        self,
        professional: Dict,
        client_name: str,
        client_phone: str,
        date: str,
        start_time: str,
        end_time: str,
        appointment_id: int
    ):
        """
        Envía notificación por WhatsApp al profesional sobre nueva cita.
        
        Args:
            professional: Dict con datos del profesional
            client_name: Nombre del cliente
            client_phone: Teléfono del cliente
            date: Fecha de la cita (YYYY-MM-DD)
            start: Hora inicio (HH:MM)
            end: Hora fin (HH:MM)
            appointment_id: ID de la cita
        """
        from datetime import datetime as dt
        
        # Format date
        date_obj = dt.strptime(date, '%Y-%m-%d')
        day_names = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        day_name = day_names[date_obj.weekday()]
        formatted_date = f"{day_name} {date_obj.strftime('%d/%m/%Y')}"
        
        # Build message
        message = f"""🔔 *NUEVA CITA CONFIRMADA*
━━━━━━━━━━━━━━━━━━━━━━━━━━

👤 *Paciente:* {client_name}
📱 *Teléfono:* {client_phone}

📅 *Fecha:* {formatted_date}
⏰ *Horario:* {start_time} - {end_time}

🆔 *Código:* #{appointment_id}

━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ La cita está confirmada y registrada en tu calendario de Google.

📝 *Importante:* El paciente ya tiene su cita agendada. Si necesitas cancelar o reprogramar, contacta al paciente directamente."""
        
        # Send WhatsApp message
        professional_phone = professional['phone']
        
        try:
            from src.integrations.twilio_service import twilio_service
            
            twilio_service.send_message(
                to=professional_phone,
                message=message
            )
            
            logger.info(f"✅ Notificación enviada al profesional {professional_phone}")
            
        except Exception as e:
            logger.error(f"❌ Error enviando notificación al profesional: {e}")
            raise