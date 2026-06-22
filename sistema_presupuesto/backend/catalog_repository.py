"""Repositorio de catalogos JSON del Sistema Presupuesto."""

from __future__ import annotations

import copy
import re
from decimal import Decimal, InvalidOperation
from typing import Any

from .errors import JsonFileNotFoundError, RepositoryError
from .storage import JsonStorage

_ITEM_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


class CatalogRepository:
    """Carga y administra catalogos aislados en `data/catalogo/`."""

    MATERIALS_FILE = "catalogo/materiales_default.json"
    MACHINES_FILE = "catalogo/maquinas_default.json"
    PROCESSES_FILE = "catalogo/procesos_default.json"
    MATERIALS_CUSTOM_FILE = "catalogo/materiales_custom.json"
    MACHINES_CUSTOM_FILE = "catalogo/maquinas_custom.json"
    PROCESSES_CUSTOM_FILE = "catalogo/procesos_custom.json"

    CATALOGS = {
        "materiales": {
            "default_file": MATERIALS_FILE,
            "custom_file": MATERIALS_CUSTOM_FILE,
            "schema": "sistema_presupuesto.catalogo.materiales",
            "collection_key": "materiales",
        },
        "maquinas": {
            "default_file": MACHINES_FILE,
            "custom_file": MACHINES_CUSTOM_FILE,
            "schema": "sistema_presupuesto.catalogo.maquinas",
            "collection_key": "maquinas",
        },
        "procesos": {
            "default_file": PROCESSES_FILE,
            "custom_file": PROCESSES_CUSTOM_FILE,
            "schema": "sistema_presupuesto.catalogo.procesos",
            "collection_key": "procesos",
        },
    }

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

    def load_all_combined(self) -> dict[str, dict[str, Any]]:
        return {
            "materiales_catalog": self.list_combined("materiales"),
            "maquinas_catalog": self.list_combined("maquinas"),
            "procesos_catalog": self.list_combined("procesos"),
        }

    def list_combined(self, tipo: str) -> dict[str, Any]:
        config = self._config_for(tipo)
        default_catalog = self._load_default_for(tipo)
        custom_catalog = self.list_custom(tipo)
        collection_key = config["collection_key"]
        merged_by_id: dict[str, dict[str, Any]] = {}

        for item in default_catalog[collection_key]:
            copied = copy.deepcopy(item)
            copied["origen_catalogo"] = "default"
            merged_by_id[copied["id"]] = copied

        for item in custom_catalog[collection_key]:
            copied = copy.deepcopy(item)
            copied["origen_catalogo"] = "custom"
            merged_by_id[copied["id"]] = copied

        return {
            "schema": config["schema"],
            "schema_version": 1,
            "metadata": {
                **default_catalog.get("metadata", {}),
                "incluye_custom": True,
                "regla_override": "custom_sobrescribe_default_por_id",
            },
            collection_key: list(merged_by_id.values()),
        }

    def list_custom(self, tipo: str) -> dict[str, Any]:
        config = self._config_for(tipo)
        try:
            return self._load_catalog(config["custom_file"], config["schema"], config["collection_key"])
        except JsonFileNotFoundError:
            return self._empty_custom_catalog(tipo)

    def create_custom(self, tipo: str, item: dict[str, Any]) -> dict[str, Any]:
        config = self._config_for(tipo)
        collection_key = config["collection_key"]
        catalog = self.list_custom(tipo)
        normalized = self._validate_item(tipo, item)
        if any(existing.get("id") == normalized["id"] for existing in catalog[collection_key]):
            raise RepositoryError(f"Item custom ya existe: {normalized['id']}")
        catalog[collection_key].append(normalized)
        self._write_custom(tipo, catalog)
        return normalized

    def update_custom(self, tipo: str, item_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(patch, dict):
            raise RepositoryError("El patch debe ser un objeto JSON.")
        self._validate_item_id(item_id)
        config = self._config_for(tipo)
        collection_key = config["collection_key"]
        catalog = self.list_custom(tipo)
        for index, existing in enumerate(catalog[collection_key]):
            if existing.get("id") == item_id:
                candidate = {**existing, **patch, "id": item_id}
                normalized = self._validate_item(tipo, candidate)
                catalog[collection_key][index] = normalized
                self._write_custom(tipo, catalog)
                return normalized
        raise RepositoryError(f"Item custom no encontrado: {item_id}")

    def delete_custom(self, tipo: str, item_id: str) -> dict[str, Any]:
        self._validate_item_id(item_id)
        config = self._config_for(tipo)
        collection_key = config["collection_key"]
        catalog = self.list_custom(tipo)
        remaining = [item for item in catalog[collection_key] if item.get("id") != item_id]
        if len(remaining) == len(catalog[collection_key]):
            raise RepositoryError(f"Item custom no encontrado: {item_id}")
        catalog[collection_key] = remaining
        self._write_custom(tipo, catalog)
        return {"deleted": True, "id": item_id}

    def _load_catalog(self, relative_path: str, expected_schema: str, collection_key: str) -> dict[str, Any]:
        payload = self.storage.read_json(relative_path)
        if payload.get("schema") != expected_schema:
            raise RepositoryError(f"Schema de catalogo invalido: {relative_path}")
        if not isinstance(payload.get(collection_key), list):
            raise RepositoryError(f"Catalogo sin coleccion requerida `{collection_key}`: {relative_path}")
        return payload

    def _load_default_for(self, tipo: str) -> dict[str, Any]:
        config = self._config_for(tipo)
        return self._load_catalog(config["default_file"], config["schema"], config["collection_key"])

    def _write_custom(self, tipo: str, catalog: dict[str, Any]) -> None:
        config = self._config_for(tipo)
        self.storage.write_json(config["custom_file"], catalog, overwrite=True)

    def _empty_custom_catalog(self, tipo: str) -> dict[str, Any]:
        config = self._config_for(tipo)
        return {
            "schema": config["schema"],
            "schema_version": 1,
            "metadata": {
                "descripcion": f"Catalogo custom editable de {tipo}.",
                "valores_son_ejemplo": True,
                "fuente": "Valores configurables por el usuario; pueden ser ficticios.",
            },
            config["collection_key"]: [],
        }

    @classmethod
    def _config_for(cls, tipo: str) -> dict[str, str]:
        if tipo not in cls.CATALOGS:
            raise RepositoryError("Tipo de catalogo no soportado.")
        return cls.CATALOGS[tipo]

    def _validate_item(self, tipo: str, item: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(item, dict):
            raise RepositoryError("El item de catalogo debe ser un objeto JSON.")
        normalized = copy.deepcopy(item)
        self._validate_item_id(normalized.get("id"))
        self._require_string(normalized, "nombre")
        if "activo" in normalized and not isinstance(normalized["activo"], bool):
            raise RepositoryError("activo debe ser boolean.")
        normalized.setdefault("activo", True)

        if tipo == "materiales":
            self._validate_material(normalized)
        elif tipo == "maquinas":
            self._validate_machine(normalized)
        elif tipo == "procesos":
            self._validate_process(normalized)
        else:
            raise RepositoryError("Tipo de catalogo no soportado.")
        return normalized

    @staticmethod
    def _validate_item_id(item_id: Any) -> None:
        if not isinstance(item_id, str) or not item_id.strip():
            raise RepositoryError("id es obligatorio.")
        if not _ITEM_ID_PATTERN.fullmatch(item_id):
            raise RepositoryError("id solo permite letras, numeros, guion y guion bajo.")

    def _validate_material(self, item: dict[str, Any]) -> None:
        self._require_string(item, "tipo")
        self._require_decimal(item, "gramaje_g_m2", positive=True)
        self._require_size(item.get("formato_pliego_mm"), "formato_pliego_mm")
        cost = self._require_mapping(item, "costo")
        self._require_string(cost, "modo")
        self._require_currency(cost)
        self._require_decimal(cost, "valor", positive=False)
        self._require_string(cost, "unidad")
        if "merma_recomendada_pct" in item:
            self._require_decimal(item, "merma_recomendada_pct", positive=False)

    def _validate_machine(self, item: dict[str, Any]) -> None:
        self._require_string(item, "tipo")
        cuerpos = item.get("cuerpos_color")
        if not isinstance(cuerpos, int) or isinstance(cuerpos, bool) or cuerpos <= 0:
            raise RepositoryError("cuerpos_color debe ser entero positivo.")
        self._require_size(item.get("formato_minimo_mm"), "formato_minimo_mm")
        self._require_size(item.get("formato_maximo_mm"), "formato_maximo_mm")
        costs = self._require_mapping(item, "costos")
        self._require_currency(costs)
        self._require_decimal(costs, "costo_hora", positive=False)
        self._require_decimal(costs, "costo_arranque", positive=False)
        self._require_decimal(costs, "costo_lavado_por_color", positive=False)
        rendimiento = self._require_mapping(item, "rendimiento")
        self._require_decimal(rendimiento, "velocidad_pliegos_hora", positive=True)
        self._require_decimal(rendimiento, "setup_horas", positive=False)

    def _validate_process(self, item: dict[str, Any]) -> None:
        self._require_string(item, "categoria")
        self._require_string(item, "modo_cobro")
        self._require_string(item, "base_calculo")
        tarifa = self._require_mapping(item, "tarifa")
        self._require_currency(tarifa)
        self._require_decimal(tarifa, "valor", positive=False)
        self._require_string(tarifa, "unidad")
        if "merma_extra_pct" in item:
            self._require_decimal(item, "merma_extra_pct", positive=False)

    def _require_size(self, payload: Any, field: str) -> None:
        if not isinstance(payload, dict):
            raise RepositoryError(f"{field} debe ser objeto con ancho y alto.")
        self._require_decimal(payload, "ancho", positive=True)
        self._require_decimal(payload, "alto", positive=True)

    @staticmethod
    def _require_mapping(payload: dict[str, Any], field: str) -> dict[str, Any]:
        value = payload.get(field)
        if not isinstance(value, dict):
            raise RepositoryError(f"{field} debe ser un objeto.")
        return value

    @staticmethod
    def _require_string(payload: dict[str, Any], field: str) -> None:
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            raise RepositoryError(f"{field} es obligatorio.")

    @staticmethod
    def _require_currency(payload: dict[str, Any]) -> None:
        if payload.get("moneda") != "PYG":
            raise RepositoryError("moneda debe ser PYG.")

    @staticmethod
    def _require_decimal(payload: dict[str, Any], field: str, *, positive: bool) -> None:
        value = payload.get(field)
        if isinstance(value, bool) or value is None:
            raise RepositoryError(f"{field} debe ser decimal.")
        try:
            decimal_value = Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:
            raise RepositoryError(f"{field} debe ser decimal.") from exc
        if positive and decimal_value <= 0:
            raise RepositoryError(f"{field} debe ser mayor que cero.")
        if not positive and decimal_value < 0:
            raise RepositoryError(f"{field} no debe ser negativo.")
