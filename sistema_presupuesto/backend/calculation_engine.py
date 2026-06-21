"""Orquestador puro del calculo de presupuesto offset."""

from __future__ import annotations

from typing import Any

from .defaults import QUOTE_RESULT_SCHEMA, QUOTE_RESULT_SCHEMA_VERSION
from .errors import CatalogValidationError, ContractValidationError
from .models import CatalogRefs, QuoteRequest, QuoteResult, ValidationIssue
from .pricing_engine import calculate_pricing
from .production_math import estimate_production
from .serializers import quote_request_from_dict
from .validators import catalog_refs_from_catalogs, validate_quote_request


def calculate_quote_from_dict(
    payload: dict[str, Any],
    *,
    materiales_catalog: dict[str, Any],
    maquinas_catalog: dict[str, Any],
    procesos_catalog: dict[str, Any],
) -> QuoteResult:
    """Valida y calcula un presupuesto desde JSON de contrato."""

    refs = catalog_refs_from_catalogs(materiales_catalog, maquinas_catalog, procesos_catalog)
    report = validate_quote_request(payload, refs)
    if not report.ok:
        raise ContractValidationError("QuoteRequest invalido.", report=report)
    request = quote_request_from_dict(payload)
    return calculate_quote(request, materiales_catalog, maquinas_catalog, procesos_catalog, refs)


def calculate_quote(
    request: QuoteRequest,
    materiales_catalog: dict[str, Any],
    maquinas_catalog: dict[str, Any],
    procesos_catalog: dict[str, Any],
    catalog_refs: CatalogRefs | None = None,
) -> QuoteResult:
    """Calcula un presupuesto validado sin efectos secundarios."""

    refs = catalog_refs or catalog_refs_from_catalogs(materiales_catalog, maquinas_catalog, procesos_catalog)
    material = _find_catalog_item(materiales_catalog, "materiales", request.costos.material_id, refs.materiales)
    machine = _find_catalog_item(maquinas_catalog, "maquinas", request.costos.maquina_id, refs.maquinas)
    processes = tuple(
        _find_catalog_item(procesos_catalog, "procesos", process_id, refs.procesos)
        for process_id in request.costos.procesos_ids
    )

    production = estimate_production(request, machine)
    pricing = calculate_pricing(request, production, material, machine, processes)
    warnings = tuple(
        [
            *production.warnings,
            *pricing.warnings,
            ValidationIssue(
                code="NO_REAL_TARIFFS",
                message="Resultado calculado con catalogos ficticios de diseno.",
                path="data/catalogo",
            ),
        ]
    )

    return QuoteResult(
        schema=QUOTE_RESULT_SCHEMA,
        schema_version=QUOTE_RESULT_SCHEMA_VERSION,
        ok=True,
        request_fixture_id=request.fixture_id,
        produccion=production,
        costos=pricing,
        warnings=warnings,
    )


def _find_catalog_item(catalog: dict[str, Any], collection_key: str, item_id: str, active_ids: frozenset[str]) -> dict:
    if item_id not in active_ids:
        raise CatalogValidationError(f"ID de catalogo no activo o inexistente: {item_id}")
    for item in catalog.get(collection_key, []):
        if item.get("id") == item_id:
            return item
    raise CatalogValidationError(f"ID de catalogo no encontrado: {item_id}")
