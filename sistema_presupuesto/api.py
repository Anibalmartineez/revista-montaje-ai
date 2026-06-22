"""Blueprint Flask aislado para Sistema Presupuesto.

Este modulo define un Blueprint importable. No lo registra en ninguna app.
"""

from __future__ import annotations

from typing import Any

from flask import Blueprint, current_app, jsonify, request
from werkzeug.exceptions import BadRequest

from .backend.calculation_engine import calculate_quote_from_dict
from .backend.catalog_repository import CatalogRepository
from .backend.client_repository import ClientRepository
from .backend.errors import (
    ContractValidationError,
    JsonDecodeStorageError,
    JsonFileNotFoundError,
    PresupuestoError,
    RepositoryError,
    StoragePathError,
)
from .backend.quote_numbering import QuoteNumbering
from .backend.repositories import BudgetRepository
from .backend.serializers import quote_result_to_dict
from .backend.storage import JsonStorage

API_PREFIX = "/api/sistema-presupuesto"


def create_presupuesto_api_blueprint() -> Blueprint:
    """Crea el Blueprint aislado del Sistema Presupuesto."""

    bp = Blueprint("sistema_presupuesto_api", __name__, url_prefix=API_PREFIX)

    @bp.get("/health")
    def health():
        return jsonify({"ok": True, "service": "sistema_presupuesto", "status": "ready"})

    @bp.get("/catalogos/materiales")
    def catalogos_materiales():
        catalog_repo, _ = _repositories()
        return jsonify({"ok": True, "catalogo": catalog_repo.list_combined("materiales")})

    @bp.get("/catalogos/maquinas")
    def catalogos_maquinas():
        catalog_repo, _ = _repositories()
        return jsonify({"ok": True, "catalogo": catalog_repo.list_combined("maquinas")})

    @bp.get("/catalogos/procesos")
    def catalogos_procesos():
        catalog_repo, _ = _repositories()
        return jsonify({"ok": True, "catalogo": catalog_repo.list_combined("procesos")})

    @bp.get("/catalogos/<tipo>")
    def catalogos_por_tipo(tipo: str):
        catalog_repo, _ = _repositories()
        return jsonify({"ok": True, "catalogo": catalog_repo.list_combined(tipo)})

    @bp.get("/catalogos/<tipo>/custom")
    def catalogos_custom(tipo: str):
        catalog_repo, _ = _repositories()
        return jsonify({"ok": True, "catalogo": catalog_repo.list_custom(tipo)})

    @bp.post("/catalogos/<tipo>/custom")
    def crear_catalogo_custom(tipo: str):
        payload = _request_json()
        catalog_repo, _ = _repositories()
        item = catalog_repo.create_custom(tipo, payload)
        return jsonify({"ok": True, "item": item}), 201

    @bp.put("/catalogos/<tipo>/custom/<item_id>")
    def actualizar_catalogo_custom(tipo: str, item_id: str):
        payload = _request_json()
        catalog_repo, _ = _repositories()
        item = catalog_repo.update_custom(tipo, item_id, payload)
        return jsonify({"ok": True, "item": item})

    @bp.delete("/catalogos/<tipo>/custom/<item_id>")
    def eliminar_catalogo_custom(tipo: str, item_id: str):
        catalog_repo, _ = _repositories()
        result = catalog_repo.delete_custom(tipo, item_id)
        return jsonify({"ok": True, **result})

    @bp.post("/cotizar")
    def cotizar():
        payload = _request_json()
        catalog_repo, _ = _repositories()
        result = calculate_quote_from_dict(payload, **catalog_repo.load_all_combined())
        return jsonify({"ok": True, "result": quote_result_to_dict(result)})

    @bp.post("/cotizar-y-guardar")
    def cotizar_y_guardar():
        payload = _request_json()
        catalog_repo, budget_repo = _repositories()
        result = calculate_quote_from_dict(payload, **catalog_repo.load_all_combined())
        record = budget_repo.save_calculated_budget(result, request_payload=payload)
        return (
            jsonify(
                {
                    "ok": True,
                    "presupuesto_id": record["presupuesto_id"],
                    "numero_comercial": record["numero_comercial"],
                    "record": record,
                }
            ),
            201,
        )

    @bp.get("/numeracion")
    def numeracion():
        numbering = _quote_numbering()
        return jsonify({"ok": True, "numeracion": numbering.status()})

    @bp.get("/clientes")
    def clientes():
        client_repo = _client_repository()
        return jsonify({"ok": True, "clientes": client_repo.list_clients()})

    @bp.post("/clientes")
    def crear_cliente():
        payload = _request_json()
        client_repo = _client_repository()
        client = client_repo.create_client(payload)
        return jsonify({"ok": True, "cliente": client}), 201

    @bp.get("/clientes/<cliente_id>")
    def cliente_por_id(cliente_id: str):
        client_repo = _client_repository()
        return jsonify({"ok": True, "cliente": client_repo.get_client(cliente_id)})

    @bp.put("/clientes/<cliente_id>")
    def actualizar_cliente(cliente_id: str):
        payload = _request_json()
        client_repo = _client_repository()
        return jsonify({"ok": True, "cliente": client_repo.update_client(cliente_id, payload)})

    @bp.delete("/clientes/<cliente_id>")
    def eliminar_cliente(cliente_id: str):
        client_repo = _client_repository()
        result = client_repo.delete_client(cliente_id)
        return jsonify({"ok": True, **result})

    @bp.get("/presupuestos")
    def presupuestos():
        _, budget_repo = _repositories()
        return jsonify({"ok": True, "presupuestos": budget_repo.list_budgets()})

    @bp.get("/presupuestos/<presupuesto_id>")
    def presupuesto_por_id(presupuesto_id: str):
        _, budget_repo = _repositories()
        return jsonify({"ok": True, "record": budget_repo.get_budget(presupuesto_id)})

    @bp.errorhandler(BadRequest)
    def handle_bad_request(exc: BadRequest):
        return _error_response(exc, "INVALID_JSON", 400)

    @bp.errorhandler(ContractValidationError)
    def handle_contract_error(exc: ContractValidationError):
        payload: dict[str, Any] = {
            "ok": False,
            "error": {
                "code": "CONTRACT_INVALID",
                "type": exc.__class__.__name__,
                "message": str(exc),
            },
        }
        if exc.report is not None:
            payload["validation"] = exc.report.to_dict()
        return jsonify(payload), 400

    @bp.errorhandler(JsonFileNotFoundError)
    def handle_not_found(exc: JsonFileNotFoundError):
        return _error_response(exc, "JSON_NOT_FOUND", 404)

    @bp.errorhandler(JsonDecodeStorageError)
    def handle_bad_json_storage(exc: JsonDecodeStorageError):
        return _error_response(exc, "JSON_INVALID", 400)

    @bp.errorhandler(RepositoryError)
    @bp.errorhandler(StoragePathError)
    def handle_repository_error(exc: PresupuestoError):
        return _error_response(exc, "REPOSITORY_ERROR", 400)

    @bp.errorhandler(PresupuestoError)
    def handle_presupuesto_error(exc: PresupuestoError):
        return _error_response(exc, "PRESUPUESTO_ERROR", 400)

    return bp


presupuesto_api_bp = create_presupuesto_api_blueprint()


def _repositories() -> tuple[CatalogRepository, BudgetRepository]:
    storage = JsonStorage(current_app.config.get("SISTEMA_PRESUPUESTO_DATA_DIR"))
    return CatalogRepository(storage), BudgetRepository(storage)


def _client_repository() -> ClientRepository:
    storage = JsonStorage(current_app.config.get("SISTEMA_PRESUPUESTO_DATA_DIR"))
    return ClientRepository(storage)


def _quote_numbering() -> QuoteNumbering:
    storage = JsonStorage(current_app.config.get("SISTEMA_PRESUPUESTO_DATA_DIR"))
    return QuoteNumbering(storage)


def _request_json() -> dict[str, Any]:
    payload = request.get_json(silent=False)
    if not isinstance(payload, dict):
        raise BadRequest("El cuerpo debe ser un objeto JSON.")
    return payload


def _error_response(exc: Exception, code: str, status: int):
    return (
        jsonify(
            {
                "ok": False,
                "error": {
                    "code": code,
                    "type": exc.__class__.__name__,
                    "message": str(exc),
                },
            }
        ),
        status,
    )
