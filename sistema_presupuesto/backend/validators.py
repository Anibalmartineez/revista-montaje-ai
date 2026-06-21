"""Validadores puros para contratos JSON del Sistema Presupuesto."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from .errors import ContractValidationError
from .models import CatalogRefs, ValidationReport
from .serializers import quote_request_from_dict

SUPPORTED_SCHEMA = "sistema_presupuesto.quote_request"
SUPPORTED_SCHEMA_VERSION = 1
SUPPORTED_CURRENCIES = frozenset({"PYG"})
SUPPORTED_PRODUCT_TYPES = frozenset(
    {
        "volante",
        "tarjeta",
        "revista",
        "folleto_diptico",
        "folleto_triptico",
    }
)


def catalog_refs_from_catalogs(
    materiales_catalog: dict[str, Any] | None = None,
    maquinas_catalog: dict[str, Any] | None = None,
    procesos_catalog: dict[str, Any] | None = None,
) -> CatalogRefs:
    """Extrae IDs activos desde catalogos JSON de Fase 2."""

    return CatalogRefs(
        materiales=frozenset(
            item["id"]
            for item in (materiales_catalog or {}).get("materiales", [])
            if item.get("activo", True)
        ),
        maquinas=frozenset(
            item["id"]
            for item in (maquinas_catalog or {}).get("maquinas", [])
            if item.get("activo", True)
        ),
        procesos=frozenset(
            item["id"]
            for item in (procesos_catalog or {}).get("procesos", [])
            if item.get("activo", True)
        ),
    )


def validate_quote_request(
    payload: dict[str, Any],
    catalog_refs: CatalogRefs | None = None,
) -> ValidationReport:
    """Valida un contrato `quote_request`.

    Devuelve errores bloqueantes y advertencias. No calcula costos ni confia
    en totales enviados por frontend.
    """

    report = ValidationReport()
    if not isinstance(payload, dict):
        report.add_error("INVALID_ROOT", "El contrato debe ser un objeto JSON.", "$")
        return report

    _validate_schema(payload, report)
    _validate_product(payload.get("producto"), report)
    _validate_production(payload.get("produccion"), report)
    _validate_costs(payload.get("costos"), report, catalog_refs)

    if report.ok:
        try:
            quote_request_from_dict(payload)
        except Exception as exc:  # noqa: BLE001 - reporta error de contrato, no propaga detalle interno.
            report.add_error("SERIALIZATION_ERROR", str(exc), "$")

    return report


def validate_quote_request_or_raise(
    payload: dict[str, Any],
    catalog_refs: CatalogRefs | None = None,
):
    """Valida y devuelve el modelo interno o levanta `ContractValidationError`."""

    report = validate_quote_request(payload, catalog_refs)
    if not report.ok:
        raise ContractValidationError("QuoteRequest invalido.", report=report)
    return quote_request_from_dict(payload)


def _validate_schema(payload: dict[str, Any], report: ValidationReport) -> None:
    if payload.get("schema") != SUPPORTED_SCHEMA:
        report.add_error(
            "INVALID_SCHEMA",
            f"schema debe ser {SUPPORTED_SCHEMA}.",
            "schema",
        )
    if payload.get("schema_version") != SUPPORTED_SCHEMA_VERSION:
        report.add_error(
            "INVALID_SCHEMA_VERSION",
            f"schema_version debe ser {SUPPORTED_SCHEMA_VERSION}.",
            "schema_version",
        )


def _validate_product(producto: Any, report: ValidationReport) -> None:
    if not isinstance(producto, dict):
        report.add_error("MISSING_PRODUCT", "producto debe ser un objeto.", "producto")
        return

    tipo = producto.get("tipo")
    if tipo not in SUPPORTED_PRODUCT_TYPES:
        report.add_error("INVALID_PRODUCT_TYPE", "tipo de producto no soportado.", "producto.tipo")

    _require_positive_decimal(producto, "cantidad", "producto.cantidad", report)
    _require_positive_decimal(producto, "ancho_mm", "producto.ancho_mm", report)
    _require_positive_decimal(producto, "alto_mm", "producto.alto_mm", report)
    _require_non_negative_decimal(producto, "sangrado_mm", "producto.sangrado_mm", report)

    caras = producto.get("caras")
    if not isinstance(caras, int) or caras not in (1, 2):
        report.add_error("INVALID_FACES", "caras debe ser 1 o 2.", "producto.caras")

    colores = producto.get("colores")
    if not isinstance(colores, dict):
        report.add_error("MISSING_COLORS", "producto.colores debe ser un objeto.", "producto.colores")
    else:
        _require_int_range(colores, "frente", "producto.colores.frente", report, minimum=0, maximum=8)
        _require_int_range(colores, "dorso", "producto.colores.dorso", report, minimum=0, maximum=8)
        if not colores.get("texto"):
            report.add_warning("MISSING_COLOR_TEXT", "Conviene declarar colores.texto, por ejemplo 4/4.", "producto.colores.texto")

    if tipo == "revista":
        paginas = producto.get("paginas")
        if not isinstance(paginas, int) or paginas <= 0:
            report.add_error("INVALID_PAGES", "revista requiere paginas enteras positivas.", "producto.paginas")
        elif paginas % 4 != 0:
            report.add_error("INVALID_PAGE_MULTIPLE", "revista requiere paginas multiplo de 4.", "producto.paginas")
        encuadernacion = producto.get("encuadernacion")
        if not isinstance(encuadernacion, dict) or not encuadernacion.get("tipo"):
            report.add_error(
                "MISSING_BINDING",
                "revista requiere encuadernacion.tipo.",
                "producto.encuadernacion",
            )

    if tipo in {"folleto_diptico", "folleto_triptico"}:
        formato_abierto = producto.get("formato_abierto_mm")
        formato_cerrado = producto.get("formato_cerrado_mm")
        _validate_size_mapping(formato_abierto, "producto.formato_abierto_mm", report)
        _validate_size_mapping(formato_cerrado, "producto.formato_cerrado_mm", report)
        expected_paneles = 2 if tipo == "folleto_diptico" else 3
        if producto.get("paneles") != expected_paneles:
            report.add_error("INVALID_PANELS", f"{tipo} requiere paneles={expected_paneles}.", "producto.paneles")


def _validate_production(produccion: Any, report: ValidationReport) -> None:
    if not isinstance(produccion, dict):
        report.add_error("MISSING_PRODUCTION", "produccion debe ser un objeto.", "produccion")
        return

    _validate_size_mapping(produccion.get("pliego_base_mm"), "produccion.pliego_base_mm", report)
    _validate_size_mapping(produccion.get("pliego_util_mm"), "produccion.pliego_util_mm", report)
    _require_non_negative_decimal(produccion, "merma_arranque_pliegos", "produccion.merma_arranque_pliegos", report)
    _require_non_negative_decimal(produccion, "merma_pct", "produccion.merma_pct", report)

    formas_manual = produccion.get("formas_por_pliego_manual")
    if formas_manual is not None:
        _require_positive_decimal(
            produccion,
            "formas_por_pliego_manual",
            "produccion.formas_por_pliego_manual",
            report,
        )


def _validate_costs(costos: Any, report: ValidationReport, catalog_refs: CatalogRefs | None) -> None:
    if not isinstance(costos, dict):
        report.add_error("MISSING_COSTS", "costos debe ser un objeto.", "costos")
        return

    moneda = costos.get("moneda")
    if moneda not in SUPPORTED_CURRENCIES:
        report.add_error("INVALID_CURRENCY", "moneda debe ser PYG.", "costos.moneda")

    material_id = costos.get("material_id")
    maquina_id = costos.get("maquina_id")
    if not material_id:
        report.add_error("MISSING_MATERIAL", "material_id es obligatorio.", "costos.material_id")
    if not maquina_id:
        report.add_error("MISSING_MACHINE", "maquina_id es obligatorio.", "costos.maquina_id")

    if catalog_refs is not None:
        if material_id and material_id not in catalog_refs.materiales:
            report.add_error("UNKNOWN_MATERIAL", "material_id no existe en catalogo activo.", "costos.material_id")
        if maquina_id and maquina_id not in catalog_refs.maquinas:
            report.add_error("UNKNOWN_MACHINE", "maquina_id no existe en catalogo activo.", "costos.maquina_id")
        for index, proceso_id in enumerate(costos.get("procesos_ids", [])):
            if proceso_id not in catalog_refs.procesos:
                report.add_error(
                    "UNKNOWN_PROCESS",
                    "proceso_id no existe en catalogo activo.",
                    f"costos.procesos_ids[{index}]",
                )

    margen = costos.get("margen_pct")
    markup = costos.get("markup_pct")
    if margen is not None:
        _require_percentage(costos, "margen_pct", "costos.margen_pct", report, allow_100=False)
    if markup is not None:
        _require_non_negative_decimal(costos, "markup_pct", "costos.markup_pct", report)
    if margen is not None and markup is not None:
        report.add_error("MARGIN_AND_MARKUP", "No informar margen_pct y markup_pct al mismo tiempo.", "costos")

    impuestos = costos.get("impuestos", [])
    if not isinstance(impuestos, list):
        report.add_error("INVALID_TAXES", "costos.impuestos debe ser una lista.", "costos.impuestos")
    else:
        for index, impuesto in enumerate(impuestos):
            if not isinstance(impuesto, dict):
                report.add_error("INVALID_TAX", "Cada impuesto debe ser un objeto.", f"costos.impuestos[{index}]")
                continue
            _require_percentage(impuesto, "tasa_pct", f"costos.impuestos[{index}].tasa_pct", report, allow_100=True)
            if not impuesto.get("base"):
                report.add_error("MISSING_TAX_BASE", "El impuesto requiere base.", f"costos.impuestos[{index}].base")


def _validate_size_mapping(value: Any, path: str, report: ValidationReport) -> None:
    if not isinstance(value, dict):
        report.add_error("INVALID_SIZE", "Debe ser objeto con ancho y alto.", path)
        return
    _require_positive_decimal(value, "ancho", f"{path}.ancho", report)
    _require_positive_decimal(value, "alto", f"{path}.alto", report)


def _require_positive_decimal(payload: dict[str, Any], key: str, path: str, report: ValidationReport) -> None:
    value = _decimal_value(payload.get(key), path, report)
    if value is not None and value <= 0:
        report.add_error("NON_POSITIVE_NUMBER", "Debe ser mayor que cero.", path)


def _require_non_negative_decimal(payload: dict[str, Any], key: str, path: str, report: ValidationReport) -> None:
    value = _decimal_value(payload.get(key), path, report)
    if value is not None and value < 0:
        report.add_error("NEGATIVE_NUMBER", "No debe ser negativo.", path)


def _require_percentage(
    payload: dict[str, Any],
    key: str,
    path: str,
    report: ValidationReport,
    *,
    allow_100: bool,
) -> None:
    value = _decimal_value(payload.get(key), path, report)
    if value is None:
        return
    upper_ok = value <= 100 if allow_100 else value < 100
    if value < 0 or not upper_ok:
        limit = "menor o igual que 100" if allow_100 else "menor que 100"
        report.add_error("INVALID_PERCENTAGE", f"Debe ser >= 0 y {limit}.", path)


def _decimal_value(value: Any, path: str, report: ValidationReport) -> Decimal | None:
    if value is None:
        report.add_error("MISSING_NUMBER", "Numero requerido.", path)
        return None
    if isinstance(value, bool):
        report.add_error("INVALID_NUMBER", "Boolean no es numero valido.", path)
        return None
    if isinstance(value, float):
        report.add_error("FLOAT_NOT_ALLOWED", "No usar float; enviar numero como string o entero.", path)
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        report.add_error("INVALID_NUMBER", "Numero decimal invalido.", path)
        return None


def _require_int_range(
    payload: dict[str, Any],
    key: str,
    path: str,
    report: ValidationReport,
    *,
    minimum: int,
    maximum: int,
) -> None:
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        report.add_error("INVALID_INTEGER", "Debe ser entero.", path)
        return
    if value < minimum or value > maximum:
        report.add_error("INTEGER_OUT_OF_RANGE", f"Debe estar entre {minimum} y {maximum}.", path)
