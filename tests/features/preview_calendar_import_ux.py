#!/usr/bin/env python3
"""
Preview UX — Flujo de importación de agenda
============================================
Muestra en la terminal exactamente cómo luce cada mensaje
que recibe el profesional durante el flujo de carga.

Uso:
    docker exec -it whatsapp-demo python tests/preview_calendar_import_ux.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.calendar_import_service import CalendarImportService

svc = CalendarImportService()

# ── Datos de ejemplo ──────────────────────────────────────────────────────────

ANALYSIS = {
    'ready': [
        {
            'name': 'Juan Pérez',
            'phone': '+5491111111111',
            'weekday': 'lunes',
            'start_time': '09:00',
        },
        {
            'name': 'Maria Garcia',
            'phone': '+5492222222222',
            'weekday': 'martes',
            'start_time': '10:00',
        },
        {
            'name': 'Carlos Lopez',
            'phone': '+5493333333333',
            'weekday': 'viernes',
            'start_time': '14:00',
        },
    ],
    'duplicate': [
        {
            'name': 'Ana Torres',
            'phone': '+5494444444444',
            'weekday': 'lunes',
            'start_time': '11:00',
            'conflict_with': 'Ana Torres (mismo paciente)',
            'conflict_start': '11:00',
            'conflict_end': '11:50',
        },
    ],
    'overlap': [
        {
            'name': 'Pedro Gomez',
            'phone': '+5495555555555',
            'weekday': 'miercoles',
            'start_time': '09:00',
            'conflict_with': 'Luis Martinez',
            'conflict_start': '09:00',
            'conflict_end': '09:50',
        },
    ],
    'error': [
        {
            'name': 'Sin Telefono',
            'phone': '11-1234-5678',
            'weekday': 'jueves',
            'start_time': '15:00',
            'error_reason': 'telefono invalido — usar +549...',
        },
        {
            'name': 'Dia Invalido',
            'phone': '+5496666666666',
            'weekday': 'funday',
            'start_time': '16:00',
            'error_reason': 'dia invalido funday',
        },
    ],
    'analyzed_at': '2026-03-23T15:51:04',
}


# ── Helpers de display ────────────────────────────────────────────────────────

def titulo(n, texto, subtexto=''):
    print()
    print('=' * 52)
    print(f'  MENSAJE {n} — {texto}')
    if subtexto:
        print(f'  ({subtexto})')
    print('=' * 52)

def whatsapp_bubble(texto):
    """Simula una burbuja de WhatsApp con borde."""
    print()
    print('  ┌' + '─' * 48 + '┐')
    for linea in texto.split('\n'):
        # Truncar si es muy larga para que entre en la pantalla
        if len(linea) > 46:
            linea = linea[:43] + '...'
        print(f'  │ {linea:<46} │')
    print('  └' + '─' * 48 + '┘')
    print()


# ── Flujo completo ────────────────────────────────────────────────────────────

print()
print('╔' + '═' * 50 + '╗')
print('║   PREVIEW UX — Importación de agenda           ║')
print('║   Mensajes que recibe el profesional            ║')
print('╚' + '═' * 50 + '╝')

# ── 1. Profesional envía el archivo ──────────────────────────────────────────
titulo(1, 'Menú de confirmación',
       'Profesional envía el CSV/Excel → bot analiza y responde esto')
whatsapp_bubble(svc.format_review_menu(ANALYSIS))

# ── 2. Profesional elige "2" — ver listos ────────────────────────────────────
titulo(2, 'Ver listos para cargar',
       'Profesional escribe "2" o "ver listos"')
whatsapp_bubble(svc.format_detail(ANALYSIS, 'ready'))

# ── 3. Profesional escribe algo → vuelve al menú ─────────────────────────────
titulo(3, 'Volver al menú de confirmación',
       'Profesional escribe cualquier cosa desde el detalle')
whatsapp_bubble(svc.format_review_menu(ANALYSIS))

# ── 4. Profesional elige "3" — ver solapamientos ─────────────────────────────
titulo(4, 'Ver solapamientos',
       'Profesional escribe "3" o "ver solapamientos"')
whatsapp_bubble(svc.format_detail(ANALYSIS, 'overlap'))

# ── 5. Profesional elige "4" — ver ya existentes ─────────────────────────────
titulo(5, 'Ver ya existentes',
       'Profesional escribe "4" o "ver existentes"')
whatsapp_bubble(svc.format_detail(ANALYSIS, 'duplicate'))

# ── 6. Profesional elige "5" — ver errores ───────────────────────────────────
titulo(6, 'Ver errores',
       'Profesional escribe "5" o "ver errores"')
whatsapp_bubble(svc.format_detail(ANALYSIS, 'error'))

# ── 7. Profesional confirma (escribe "1") ────────────────────────────────────
titulo(7, 'Carga exitosa',
       'Profesional escribe "1" para confirmar — todo sale bien')
whatsapp_bubble(svc.format_execute_result({
    'creados':  3,
    'errores':  0,
    'detalles': [],
}))

# ── 8. Carga con errores parciales ───────────────────────────────────────────
titulo(8, 'Carga con errores parciales',
       'Profesional confirma — algunos pacientes fallan en Calendar')
whatsapp_bubble(svc.format_execute_result({
    'creados':  2,
    'errores':  1,
    'detalles': ['Carlos Lopez — error Calendar: credenciales no configuradas'],
}))

# ── 9. Sin pacientes listos ───────────────────────────────────────────────────
titulo(9, 'Sin pacientes listos para cargar',
       'Archivo con solo duplicados y errores')
analisis_vacio = {
    'ready': [],
    'duplicate': ANALYSIS['duplicate'],
    'overlap':   ANALYSIS['overlap'],
    'error':     ANALYSIS['error'],
}
whatsapp_bubble(svc.format_review_menu(analisis_vacio))

# ── 10. Todo falla ────────────────────────────────────────────────────────────
titulo(10, 'Todo falla al ejecutar',
        'Calendar no responde para ninguno')
whatsapp_bubble(svc.format_execute_result({
    'creados':  0,
    'errores':  3,
    'detalles': [
        'Juan Perez — error Calendar: timeout',
        'Maria Garcia — error Calendar: timeout',
        'Carlos Lopez — error Calendar: timeout',
    ],
}))

print()
print('─' * 52)
print('  Fin del preview. Edita format_review_menu(),')
print('  format_detail() o format_execute_result() en')
print('  src/services/calendar_import_service.py')
print('  para ajustar los mensajes.')
print('─' * 52)
print()
