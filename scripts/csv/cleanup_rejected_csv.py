"""
Script de limpieza de CSVs de pacientes no cargados.
=====================================================
Elimina archivos pacientes_no_cargados_*.csv de /app/data/rechazados/
que tengan más de RETENTION_DAYS días de antigüedad.

Uso:
    python scripts/csv/cleanup_rejected_csv.py
    python scripts/csv/cleanup_rejected_csv.py --days 30
    python scripts/csv/cleanup_rejected_csv.py --dry-run

Recomendación: ejecutar mensualmente via cron o manualmente.
    # Ejemplo cron — primer día de cada mes a las 3am:
    0 3 1 * * docker exec whatsapp-demo python3 scripts/csv/cleanup_rejected_csv.py
"""

import argparse
from pathlib import Path
from datetime import datetime, timedelta


# ── Constantes ────────────────────────────────────────────────────────────────

REJECTED_DIR    = Path('/app/data/rechazados')
RETENTION_DAYS  = 30       # días de retención por defecto
FILE_PATTERN    = 'pacientes_no_cargados_*.csv'


# ── Lógica principal ──────────────────────────────────────────────────────────

def cleanup(days: int, dry_run: bool):
    """
    Elimina archivos de rechazados más viejos que `days` días.

    Args:
        days:    Días de retención. Archivos más viejos se eliminan.
        dry_run: Si True, solo muestra qué se eliminaría sin borrar nada.
    """
    cutoff = datetime.now() - timedelta(days=days)

    print()
    print("=" * 60)
    print("🧹 LIMPIEZA DE CSVs DE PACIENTES RECHAZADOS")
    print("=" * 60)
    print(f"   Directorio  : {REJECTED_DIR}")
    print(f"   Retención   : {days} días")
    print(f"   Eliminar antes de: {cutoff.strftime('%Y-%m-%d')}")
    print(f"   Modo        : {'🔍 DRY RUN' if dry_run else '🗑️  Eliminación real'}")
    print()

    # Verificar que el directorio existe
    if not REJECTED_DIR.exists():
        print(f"   ℹ️  Directorio no existe todavía: {REJECTED_DIR}")
        print(f"   Se creará automáticamente al generar el primer CSV de rechazados.")
        print()
        return

    # Listar todos los archivos que coinciden con el patrón
    archivos = sorted(REJECTED_DIR.glob(FILE_PATTERN))

    if not archivos:
        print(f"   ℹ️  No hay archivos {FILE_PATTERN} en {REJECTED_DIR}")
        print()
        return

    print(f"   📄 Archivos encontrados: {len(archivos)}")
    print()

    eliminados  = 0
    conservados = 0
    errores     = 0

    for archivo in archivos:
        # Obtener fecha de modificación del archivo
        mtime       = datetime.fromtimestamp(archivo.stat().st_mtime)
        antiguedad  = (datetime.now() - mtime).days
        vencido     = mtime < cutoff

        if vencido:
            estado = f"🗑️  ELIMINAR  ({antiguedad} días)"
        else:
            estado = f"✅ Conservar ({antiguedad} días)"

        print(f"   {estado} — {archivo.name}")

        if vencido:
            if dry_run:
                eliminados += 1
            else:
                try:
                    archivo.unlink()
                    eliminados += 1
                except Exception as e:
                    print(f"      ❌ Error al eliminar: {e}")
                    errores += 1
        else:
            conservados += 1

    # Resumen
    print()
    print("=" * 60)
    print("📊 RESUMEN")
    print("=" * 60)
    print(f"   🗑️  {'Se eliminarían' if dry_run else 'Eliminados'} : {eliminados}")
    print(f"   ✅ Conservados              : {conservados}")
    if errores:
        print(f"   ❌ Errores                  : {errores}")

    if dry_run:
        print(f"\n   ⚠️  DRY RUN: ningún archivo fue eliminado.")

    print()
    print("=" * 60)
    print("✅ LIMPIEZA COMPLETADA")
    print("=" * 60)
    print()


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Limpia CSVs de pacientes rechazados más viejos de N días.',
        epilog="""
Ejemplos:
  python scripts/csv/cleanup_rejected_csv.py
  python scripts/csv/cleanup_rejected_csv.py --days 30
  python scripts/csv/cleanup_rejected_csv.py --dry-run

Cron mensual (primer día del mes a las 3am):
  0 3 1 * * docker exec whatsapp-demo python3 scripts/csv/cleanup_rejected_csv.py
        """
    )
    parser.add_argument(
        '--days', type=int, default=RETENTION_DAYS,
        help=f'Días de retención (default: {RETENTION_DAYS})'
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Simula sin eliminar nada'
    )

    args = parser.parse_args()
    cleanup(args.days, args.dry_run)


if __name__ == '__main__':
    main()
