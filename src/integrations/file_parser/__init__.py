"""
file_parser — Módulo de parseo de archivos CSV y Excel
======================================================
Ubicación: src/integrations/file_parser/__init__.py

Convierte archivos CSV y Excel en listas de dicts normalizadas.
La lógica de negocio (validar pacientes, crear citas) vive en
src/services/calendar_import_service.py — este módulo solo parsea.

Uso:
    from src.integrations.file_parser import FileParser

    parser = FileParser()
    rows   = parser.parse(content_bytes, content_type)
"""

from .file_parser import FileParser

__all__ = ['FileParser']
