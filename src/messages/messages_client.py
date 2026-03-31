"""
Client Messages
===============
Mensajes del flujo de cliente. Leen del tono activo.
Los métodos helper estáticos se mantienen sin cambios.
"""

from src.config.domain_config import DomainConfig
from src.messages.loader import get_msg


class ClientMessages:

    # --- Menú y búsqueda ---

    @property
    def CLIENT_MAIN_MENU(self):
        return get_msg("CLIENT_MAIN_MENU")

    @property
    def CLIENT_ASK_FECHA(self):
        return get_msg("CLIENT_ASK_FECHA")

    @property
    def CLIENT_ASK_HORA(self):
        return get_msg("CLIENT_ASK_HORA")

    @property
    def CLIENT_ASK_ZONA(self):
        return get_msg("CLIENT_ASK_ZONA")

    @property
    def CLIENT_ASK_PREPAGA(self):
        return get_msg("CLIENT_ASK_PREPAGA")

    @property
    def CLIENT_ASK_SEXO(self):
        return get_msg("CLIENT_ASK_SEXO")

    @property
    def CLIENT_NO_RESULTS(self):
        return get_msg("CLIENT_NO_RESULTS")

    @property
    def CLIENT_MULTIFILTER_ADDED(self):
        return get_msg("CLIENT_MULTIFILTER_ADDED")

    @property
    def CLIENT_SEARCH_QUICK_FORMAT(self):
        return get_msg("CLIENT_SEARCH_QUICK_FORMAT")

    # --- Métodos helper estáticos — sin cambios ---

    @staticmethod
    def CLIENT_MULTIFILTER_MENU(active_filters: str = "") -> str:
        """Genera menú de filtros con filtros activos."""
        filters_section = ""
        if active_filters:
            filters_section = f"\nFiltros activos:\n{active_filters}\n"

        zone_options = "\n".join(
            f"{i}️⃣ {v}"
            for i, (_, v) in enumerate(DomainConfig.ZONES.items(), 1)
        )

        return (
            f"Búsqueda por filtros\n\n"
            f"Elegí los filtros que necesitás:\n\n"
            f"1️⃣ Zona\n"
            f"2️⃣ Fecha y hora\n"
            f"3️⃣ {DomainConfig.CUSTOM_FIELD_1_LABEL if DomainConfig.CUSTOM_FIELD_1_ENABLED else 'Prepaga'}\n"
            f"4️⃣ Género del {DomainConfig.PROFESSIONAL_TITLE_LOWER}\n"
            f"5️⃣ {DomainConfig.CATEGORY_LABEL}\n\n"
            f"9️⃣ Buscar ahora\n"
            f"0️⃣ Volver al menú"
            f"{filters_section}"
        )

    @staticmethod
    def format_zone_options() -> str:
        return "\n".join(
            f"{i}️⃣ {v}"
            for i, (_, v) in enumerate(DomainConfig.ZONES.items(), 1)
        )

    @staticmethod
    def format_category_options() -> str:
        return "\n".join(
            f"{k}. {v}"
            for k, v in DomainConfig.CATEGORIES.items()
        )

    @staticmethod
    def format_filters_summary(filters: dict) -> str:
        parts = []
        if filters.get("zona"):
            parts.append(f"📍 Zona: {DomainConfig.ZONES.get(filters['zona'], filters['zona'])}")
        if filters.get("fecha"):
            parts.append(f"📅 Fecha: {filters['fecha']}")
        if filters.get("hora"):
            parts.append(f"⏰ Hora: {filters['hora']}")
        if filters.get("prepaga") is not None:
            label = DomainConfig.CUSTOM_FIELD_1_LABEL if DomainConfig.CUSTOM_FIELD_1_ENABLED else "Prepaga"
            parts.append(f"💳 {label}: {'Sí' if filters['prepaga'] else 'No'}")
        if filters.get("genero"):
            parts.append(f"👤 Género: {filters['genero']}")
        if filters.get("especialidad"):
            parts.append(f"💼 {DomainConfig.CATEGORY_LABEL}: {filters['especialidad']}")
        return "\n".join(parts) if parts else "Sin filtros aplicados"


client_messages = ClientMessages()