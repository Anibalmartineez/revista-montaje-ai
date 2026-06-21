"""Repositorio de catalogos JSON del Sistema Presupuesto."""

from __future__ import annotations

from typing import Any

from .errors import RepositoryError
from .storage import JsonStorage


class CatalogRepository:
    """Carga catalogos desde `data/catalogo/`."""

    MATERIALS_FILE = "catalogo/materiales_default.json"
    MACHINES_FILE = "catalogo/maquinas_default.json"
    PROCESSES_FILE = "catalogo/procesos_default.json"

    def __init__(self, storage: JsonStorage | None = None):
        self.storage = storage or JsonStorage()

    def load_materiales_default(self) -> dict[str, Any]:
        return self._load_catalog(self.MATERIALS_FILE, "sistema_presupuesto.catalogo.materiales", "materiales")

    def load_maquinas_default(self) -> dict[str, Any]:
        return self._load_catalog(self.MACHINES_FILE, "sistema_presupuesto.catalogo.maquinas", "maquinas")

    def load_procesos_default(self) -> dict[str, Any]:
        return self._load_catalog(self.PROCESSES_FILE, "sistema_presupuesto.catalogo.procesos", "procesos")

    def load_all_defaults(self) -> dict[str, dict[str, Any]]:
        return {
            "materiales_catalog": self.load_materiales_default(),
            "maquinas_catalog": self.load_maquinas_default(),
            "procesos_catalog": self.load_procesos_default(),
        }

    def _load_catalog(self, relative_path: str, expected_schema: str, collection_key: str) -> dict[str, Any]:
        payload = self.storage.read_json(relative_path)
        if payload.get("schema") != expected_schema:
            raise RepositoryError(f"Schema de catalogo invalido: {relative_path}")
        if not isinstance(payload.get(collection_key), list):
            raise RepositoryError(f"Catalogo sin coleccion requerida `{collection_key}`: {relative_path}")
        return payload

