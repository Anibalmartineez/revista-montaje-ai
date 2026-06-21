"""Serializadores base para contratos JSON del Sistema Presupuesto."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from .errors import SerializationError
from .models import (
    ClienteSpec,
    ColorSpec,
    CostosSpec,
    EncuadernacionSpec,
    ImpuestoSpec,
    ProductoSpec,
    ProduccionSpec,
    QuoteRequest,
    QuoteResult,
    SizeMM,
    ValidationReport,
)


def decimal_from_contract(value: Any, path: str) -> Decimal:
    """Convierte un numero de contrato a Decimal sin pasar por float."""

    if isinstance(value, bool):
        raise SerializationError(f"{path}: boolean no es numero valido")
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, str):
        try:
            return Decimal(value)
        except InvalidOperation as exc:
            raise SerializationError(f"{path}: numero decimal invalido") from exc
    raise SerializationError(f"{path}: tipo numerico no soportado")


def optional_decimal_from_contract(value: Any, path: str) -> Decimal | None:
    if value is None:
        return None
    return decimal_from_contract(value, path)


def size_from_mapping(payload: dict[str, Any], path: str) -> SizeMM:
    return SizeMM(
        ancho=decimal_from_contract(payload.get("ancho"), f"{path}.ancho"),
        alto=decimal_from_contract(payload.get("alto"), f"{path}.alto"),
    )


def quote_request_from_dict(payload: dict[str, Any]) -> QuoteRequest:
    """Construye un `QuoteRequest` desde un dict ya validado."""

    try:
        cliente_payload = payload.get("cliente") or {}
        producto_payload = payload["producto"]
        produccion_payload = payload["produccion"]
        costos_payload = payload["costos"]
        colores_payload = producto_payload["colores"]

        encuadernacion_payload = producto_payload.get("encuadernacion")
        encuadernacion = None
        if encuadernacion_payload:
            encuadernacion = EncuadernacionSpec(
                tipo=str(encuadernacion_payload.get("tipo") or ""),
                proceso_id=encuadernacion_payload.get("proceso_id"),
            )

        formato_abierto = None
        if producto_payload.get("formato_abierto_mm"):
            formato_abierto = size_from_mapping(
                producto_payload["formato_abierto_mm"],
                "producto.formato_abierto_mm",
            )

        formato_cerrado = None
        if producto_payload.get("formato_cerrado_mm"):
            formato_cerrado = size_from_mapping(
                producto_payload["formato_cerrado_mm"],
                "producto.formato_cerrado_mm",
            )

        impuestos = tuple(
            ImpuestoSpec(
                id=str(impuesto.get("id") or ""),
                nombre=str(impuesto.get("nombre") or ""),
                tasa_pct=decimal_from_contract(impuesto.get("tasa_pct"), "costos.impuestos[].tasa_pct"),
                base=str(impuesto.get("base") or ""),
                incluido=bool(impuesto.get("incluido")),
                es_valor_ejemplo=bool(impuesto.get("es_valor_ejemplo")),
            )
            for impuesto in costos_payload.get("impuestos", [])
        )

        return QuoteRequest(
            schema=str(payload["schema"]),
            schema_version=int(payload["schema_version"]),
            fixture_id=payload.get("fixture_id"),
            descripcion=payload.get("descripcion"),
            cliente=ClienteSpec(
                nombre=cliente_payload.get("nombre"),
                referencia=cliente_payload.get("referencia"),
            ),
            producto=ProductoSpec(
                titulo=str(producto_payload.get("titulo") or ""),
                tipo=str(producto_payload["tipo"]),
                cantidad=decimal_from_contract(producto_payload["cantidad"], "producto.cantidad"),
                unidad_cantidad=str(producto_payload.get("unidad_cantidad") or ""),
                ancho_mm=decimal_from_contract(producto_payload["ancho_mm"], "producto.ancho_mm"),
                alto_mm=decimal_from_contract(producto_payload["alto_mm"], "producto.alto_mm"),
                sangrado_mm=decimal_from_contract(producto_payload["sangrado_mm"], "producto.sangrado_mm"),
                paginas=producto_payload.get("paginas"),
                caras=int(producto_payload["caras"]),
                colores=ColorSpec(
                    frente=int(colores_payload["frente"]),
                    dorso=int(colores_payload["dorso"]),
                    texto=str(colores_payload.get("texto") or ""),
                ),
                formato_abierto_mm=formato_abierto,
                formato_cerrado_mm=formato_cerrado,
                paneles=producto_payload.get("paneles"),
                pliegues=producto_payload.get("pliegues"),
                encuadernacion=encuadernacion,
            ),
            produccion=ProduccionSpec(
                pliego_base_mm=size_from_mapping(produccion_payload["pliego_base_mm"], "produccion.pliego_base_mm"),
                pliego_util_mm=size_from_mapping(produccion_payload["pliego_util_mm"], "produccion.pliego_util_mm"),
                formas_por_pliego_manual=optional_decimal_from_contract(
                    produccion_payload.get("formas_por_pliego_manual"),
                    "produccion.formas_por_pliego_manual",
                ),
                merma_arranque_pliegos=decimal_from_contract(
                    produccion_payload["merma_arranque_pliegos"],
                    "produccion.merma_arranque_pliegos",
                ),
                merma_pct=decimal_from_contract(produccion_payload["merma_pct"], "produccion.merma_pct"),
                imposicion_origen=produccion_payload.get("imposicion_origen"),
            ),
            costos=CostosSpec(
                moneda=str(costos_payload["moneda"]),
                material_id=str(costos_payload["material_id"]),
                maquina_id=str(costos_payload["maquina_id"]),
                procesos_ids=tuple(str(item) for item in costos_payload.get("procesos_ids", [])),
                margen_pct=optional_decimal_from_contract(costos_payload.get("margen_pct"), "costos.margen_pct"),
                markup_pct=optional_decimal_from_contract(costos_payload.get("markup_pct"), "costos.markup_pct"),
                impuestos=impuestos,
            ),
            expected_assertions=payload.get("expected_assertions") or {},
        )
    except KeyError as exc:
        raise SerializationError(f"Campo requerido faltante: {exc}") from exc
    except (TypeError, ValueError, InvalidOperation) as exc:
        raise SerializationError(str(exc)) from exc


def validation_report_to_dict(report: ValidationReport) -> dict[str, Any]:
    return report.to_dict()


def quote_result_to_dict(result: QuoteResult) -> dict[str, Any]:
    """Convierte un resultado calculado a JSON serializable."""

    production = result.produccion
    pricing = result.costos
    return {
        "schema": result.schema,
        "schema_version": result.schema_version,
        "ok": result.ok,
        "request_fixture_id": result.request_fixture_id,
        "produccion": {
            "pieza_con_sangrado_mm": {
                "ancho": str(production.pieza_con_sangrado_mm.ancho),
                "alto": str(production.pieza_con_sangrado_mm.alto),
            },
            "unidades_por_pliego": str(production.unidades_por_pliego),
            "factor_paginas": str(production.factor_paginas),
            "pliegos_buenos": str(production.pliegos_buenos),
            "merma_pliegos": str(production.merma_pliegos),
            "pliegos_brutos": str(production.pliegos_brutos),
            "chapas": str(production.chapas),
            "pasadas": str(production.pasadas),
            "impresiones": str(production.impresiones),
            "horas_tirada": str(production.horas_tirada),
            "horas_maquina_total": str(production.horas_maquina_total),
            "area_pliego_util_m2": str(production.area_pliego_util_m2),
        },
        "costos": {
            "moneda": pricing.moneda,
            "items": [item.to_dict() for item in pricing.items],
            "costo_tecnico": str(pricing.costo_tecnico),
            "margen": {
                "tipo": pricing.margen_tipo,
                "pct": str(pricing.margen_pct) if pricing.margen_pct is not None else None,
                "monto": str(pricing.margen_monto),
            },
            "markup_pct": str(pricing.markup_pct) if pricing.markup_pct is not None else None,
            "descuento": str(pricing.descuento),
            "impuestos": [tax.to_dict() for tax in pricing.impuestos],
            "precio_antes_impuestos": str(pricing.precio_antes_impuestos),
            "precio_final": str(pricing.precio_final),
            "precio_unitario": str(pricing.precio_unitario),
        },
        "warnings": [issue.to_dict() for issue in result.warnings],
    }
