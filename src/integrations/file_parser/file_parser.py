"""
FileParser — Parseo de archivos CSV y Excel
===========================================
Ubicación: src/integrations/file_parser/file_parser.py

Responsabilidad única: convertir bytes de un archivo CSV o Excel
en una lista de dicts con keys normalizadas (lowercase, sin espacios).

Arquitectura:
    - Excel se convierte a CSV primero (_excel_to_csv)
    - Todo el parseo final va por el mismo camino CSV (_parse_csv)
    - El llamador siempre recibe List[Dict] sin importar el formato de origen

Formatos soportados:
    - CSV (.csv) — texto plano con separador coma o punto y coma
    - Excel (.xlsx, .xls) — solo lee la primera hoja activa

No hace validaciones de negocio — solo convierte bytes a estructura de datos.
"""

import csv
import io
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# MIME types reconocidos como CSV
CSV_MIME_TYPES = {
    'text/csv',
    'text/plain',
    'application/csv',
    'application/octet-stream',  # fallback genérico que Twilio usa a veces
}

# MIME types reconocidos como Excel
EXCEL_MIME_TYPES = {
    'application/vnd.ms-excel',                                          # .xls
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', # .xlsx
    'application/xlsx',
    'application/xls',
}

ALL_SPREADSHEET_TYPES = CSV_MIME_TYPES | EXCEL_MIME_TYPES


class FileParser:
    """
    Convierte archivos CSV o Excel en listas de dicts normalizados.

    Diseñado para ser stateless — cada llamada a parse() es independiente.
    Thread-safe: no tiene estado mutable.
    """

    # =========================================================================
    # API PÚBLICA
    # =========================================================================

    def is_supported(self, content_type: str) -> bool:
        """
        Verifica si el MIME type corresponde a un formato soportado.

        Args:
            content_type: MIME type del archivo (puede incluir parámetros
                          como 'text/csv; charset=utf-8')

        Returns:
            True si es CSV o Excel
        """
        normalized = self._normalize_mime(content_type)
        return normalized in ALL_SPREADSHEET_TYPES

    def is_excel(self, content_type: str) -> bool:
        """Retorna True si el MIME type corresponde a Excel."""
        return self._normalize_mime(content_type) in EXCEL_MIME_TYPES

    def parse(self, content: bytes, content_type: str) -> List[Dict]:
        """
        Parsea el contenido de un archivo CSV o Excel.

        Si el archivo es Excel, lo convierte a CSV primero.
        Normaliza los headers (lowercase, sin espacios laterales).
        Descarta filas completamente vacías.

        Args:
            content:      Contenido del archivo en bytes
            content_type: MIME type del archivo

        Returns:
            Lista de dicts. Cada dict es una fila con keys = headers.
            Lista vacía si el archivo no tiene datos.

        Raises:
            ValueError: Si el formato no es soportado o el archivo
                        no se puede leer.
        """
        if not self.is_supported(content_type):
            raise ValueError(
                f"Formato no soportado: '{content_type}'. "
                f"Formatos aceptados: CSV, XLS, XLSX."
            )

        if self.is_excel(content_type):
            logger.info("[FILE-PARSER] Detectado Excel — convirtiendo a CSV")
            csv_text = self._excel_to_csv(content)
        else:
            logger.info("[FILE-PARSER] Detectado CSV — parseando directo")
            csv_text = self._decode_csv(content)

        rows = self._parse_csv(csv_text)
        logger.info(f"[FILE-PARSER] ✅ {len(rows)} filas parseadas")
        return rows

    # =========================================================================
    # CONVERSOR EXCEL → CSV
    # =========================================================================

    def _excel_to_csv(self, content: bytes) -> str:
        """
        Convierte un archivo Excel (.xlsx o .xls) a texto CSV.

        Lee solo la primera hoja activa (wb.active).
        Las celdas None se convierten en string vacío.
        Los números se convierten a string sin decimales cuando son enteros
        (evita que "50" aparezca como "50.0").

        Args:
            content: Contenido del archivo Excel en bytes

        Returns:
            Texto CSV como string

        Raises:
            ImportError: Si openpyxl no está instalado
            Exception:   Si el archivo no es un Excel válido
        """
        try:
            import openpyxl
        except ImportError:
            raise ImportError(
                "openpyxl es requerido para leer archivos Excel. "
                "Agregarlo a requirements.txt: openpyxl>=3.0.0"
            )

        wb  = openpyxl.load_workbook(io.BytesIO(content), read_only=True)
        ws  = wb.active

        out    = io.StringIO()
        writer = csv.writer(out)

        rows_written = 0
        for row in ws.iter_rows(values_only=True):
            # Convertir cada celda a string limpio
            csv_row = []
            for cell in row:
                if cell is None:
                    csv_row.append('')
                elif isinstance(cell, float) and cell == int(cell):
                    # Evitar "50.0" → "50"
                    csv_row.append(str(int(cell)))
                else:
                    csv_row.append(str(cell).strip())
            writer.writerow(csv_row)
            rows_written += 1

        wb.close()
        logger.info(
            f"[FILE-PARSER] Excel convertido a CSV: {rows_written} filas "
            f"(incluyendo header)"
        )
        return out.getvalue()

    # =========================================================================
    # PARSEO CSV
    # =========================================================================

    def _decode_csv(self, content: bytes) -> str:
        """
        Decodifica bytes de CSV a string.

        Intenta en orden: UTF-8 con BOM (común en Excel exportado),
        UTF-8 sin BOM, latin-1 (fallback para Windows).

        Args:
            content: Bytes del archivo CSV

        Returns:
            Texto decodificado

        Raises:
            ValueError: Si ningún encoding funciona
        """
        for encoding in ('utf-8-sig', 'utf-8', 'latin-1'):
            try:
                text = content.decode(encoding)
                logger.debug(f"[FILE-PARSER] CSV decodificado con {encoding}")
                return text
            except UnicodeDecodeError:
                continue

        raise ValueError(
            "No se pudo decodificar el CSV. "
            "Guardá el archivo con encoding UTF-8."
        )

    def _parse_csv(self, csv_text: str) -> List[Dict]:
        """
        Parsea texto CSV en lista de dicts.

        Detecta automáticamente el delimitador (coma o punto y coma).
        Normaliza los headers: lowercase + strip.
        Descarta filas donde todos los valores son cadenas vacías.

        Args:
            csv_text: Contenido CSV como string

        Returns:
            Lista de dicts con keys = headers normalizados
        """
        # Detectar delimitador — contar comas vs punto y coma en la primera línea
        first_line = csv_text.split('\n')[0] if csv_text else ''
        delimiter  = ';' if first_line.count(';') > first_line.count(',') else ','

        reader = csv.DictReader(io.StringIO(csv_text), delimiter=delimiter)

        if not reader.fieldnames:
            return []

        # Normalizar headers
        normalized_headers = {
            original: original.strip().lower()
            for original in reader.fieldnames
            if original  # ignorar columnas sin nombre
        }

        rows = []
        for raw_row in reader:
            # Normalizar keys y values
            row = {
                normalized_headers[k]: v.strip()
                for k, v in raw_row.items()
                if k in normalized_headers
            }

            # Descartar filas vacías
            if not any(v for v in row.values()):
                continue

            rows.append(row)

        return rows

    # =========================================================================
    # HELPERS
    # =========================================================================

    def _normalize_mime(self, content_type: str) -> str:
        """Extrae el tipo base del MIME type (descarta parámetros como charset)."""
        return content_type.lower().split(';')[0].strip()
