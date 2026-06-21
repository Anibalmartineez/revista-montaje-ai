"""Motor monetario de Fase 4.

Usa `Decimal`, no persiste datos y no confia en totales enviados por frontend.
"""

from __future__ import annotations

from decimal import Decimal

from .defaults import CTP_COST_PER_PLATE_EXAMPLE, MONEY_ZERO, PERCENT_BASE
from .models import CostLineItem, PricingResult, ProductionEstimate, QuoteRequest, TaxLineItem, ValidationIssue


def calculate_pricing(
    request: QuoteRequest,
    production: ProductionEstimate,
    material_catalog: dict,
    machine_catalog: dict,
    process_catalogs: tuple[dict, ...],
) -> PricingResult:
    warnings: list[ValidationIssue] = [
        ValidationIssue(
            code="EXAMPLE_CATALOG_VALUES",
            message="Los catalogos actuales contienen valores ficticios de diseno.",
            path="data/catalogo",
        )
    ]
    items: list[CostLineItem] = []

    items.append(_paper_cost_line(production, material_catalog))
    items.append(_ctp_cost_line(production))
    items.append(_machine_cost_line(production, machine_catalog))
    items.extend(_process_cost_lines(request, production, process_catalogs))

    costo_tecnico = sum((item.subtotal for item in items), MONEY_ZERO)
    precio_antes_impuestos, margen_tipo, margen_monto = _apply_margin_or_markup(request, costo_tecnico)
    impuestos = _tax_lines(request, precio_antes_impuestos)
    impuesto_total = sum((tax.monto for tax in impuestos if not tax.incluido), MONEY_ZERO)
    precio_final = precio_antes_impuestos + impuesto_total
    precio_unitario = precio_final / request.producto.cantidad

    return PricingResult(
        moneda=request.costos.moneda,
        items=tuple(items),
        costo_tecnico=costo_tecnico,
        margen_tipo=margen_tipo,
        margen_pct=request.costos.margen_pct,
        margen_monto=margen_monto,
        markup_pct=request.costos.markup_pct,
        descuento=MONEY_ZERO,
        impuestos=tuple(impuestos),
        precio_antes_impuestos=precio_antes_impuestos,
        precio_final=precio_final,
        precio_unitario=precio_unitario,
        warnings=tuple(warnings),
    )


def _paper_cost_line(production: ProductionEstimate, material_catalog: dict) -> CostLineItem:
    cost = material_catalog["costo"]
    unit_cost = Decimal(str(cost["valor"]))
    subtotal = production.pliegos_brutos * unit_cost
    return CostLineItem(
        codigo="papel",
        descripcion=material_catalog["nombre"],
        cantidad=production.pliegos_brutos,
        unidad=cost.get("unidad", "pliego"),
        costo_unitario=unit_cost,
        subtotal=subtotal,
        es_valor_ejemplo=bool(cost.get("es_valor_ejemplo", True)),
    )


def _ctp_cost_line(production: ProductionEstimate) -> CostLineItem:
    subtotal = production.chapas * CTP_COST_PER_PLATE_EXAMPLE
    return CostLineItem(
        codigo="chapas_ctp",
        descripcion="Chapas CTP",
        cantidad=production.chapas,
        unidad="chapa",
        costo_unitario=CTP_COST_PER_PLATE_EXAMPLE,
        subtotal=subtotal,
        es_valor_ejemplo=True,
    )


def _machine_cost_line(production: ProductionEstimate, machine_catalog: dict) -> CostLineItem:
    costs = machine_catalog["costos"]
    unit_cost = Decimal(str(costs["costo_hora"]))
    startup = Decimal(str(costs.get("costo_arranque") or "0"))
    subtotal = startup + (production.horas_maquina_total * unit_cost)
    return CostLineItem(
        codigo="maquina",
        descripcion=machine_catalog["nombre"],
        cantidad=production.horas_maquina_total,
        unidad="hora",
        costo_unitario=unit_cost,
        subtotal=subtotal,
        es_valor_ejemplo=bool(costs.get("es_valor_ejemplo", True)),
    )


def _process_cost_lines(
    request: QuoteRequest,
    production: ProductionEstimate,
    process_catalogs: tuple[dict, ...],
) -> list[CostLineItem]:
    lines: list[CostLineItem] = []
    for process in process_catalogs:
        tarifa = process["tarifa"]
        unit_cost = Decimal(str(tarifa["valor"]))
        quantity, unit = _process_quantity(request, production, process)
        lines.append(
            CostLineItem(
                codigo=f"proceso:{process['id']}",
                descripcion=process["nombre"],
                cantidad=quantity,
                unidad=unit,
                costo_unitario=unit_cost,
                subtotal=quantity * unit_cost,
                es_valor_ejemplo=bool(tarifa.get("es_valor_ejemplo", True)),
            )
        )
    return lines


def _process_quantity(
    request: QuoteRequest,
    production: ProductionEstimate,
    process: dict,
) -> tuple[Decimal, str]:
    mode = process["modo_cobro"]
    if mode == "fijo":
        return Decimal("1"), process["tarifa"].get("unidad", "trabajo")
    if mode == "por_unidad":
        return request.producto.cantidad, "unidad"
    if mode == "por_pliego":
        return production.pliegos_brutos, "pliego"
    if mode == "por_hora":
        return production.horas_maquina_total, "hora"
    if mode == "por_millar":
        return request.producto.cantidad / Decimal("1000"), "millar"
    if mode == "por_m2":
        return production.area_pliego_util_m2 * production.pliegos_brutos, "m2"
    if mode == "por_kg":
        return Decimal("0"), "kg"
    return Decimal("0"), process["tarifa"].get("unidad", "unidad")


def _apply_margin_or_markup(request: QuoteRequest, costo_tecnico: Decimal) -> tuple[Decimal, str | None, Decimal]:
    if request.costos.margen_pct is not None:
        factor = Decimal("1") - (request.costos.margen_pct / PERCENT_BASE)
        precio = costo_tecnico / factor
        return precio, "margen_sobre_venta", precio - costo_tecnico
    if request.costos.markup_pct is not None:
        precio = costo_tecnico * (Decimal("1") + request.costos.markup_pct / PERCENT_BASE)
        return precio, "markup_sobre_costo", precio - costo_tecnico
    return costo_tecnico, None, MONEY_ZERO


def _tax_lines(request: QuoteRequest, precio_antes_impuestos: Decimal) -> list[TaxLineItem]:
    taxes: list[TaxLineItem] = []
    for tax in request.costos.impuestos:
        base = precio_antes_impuestos
        amount = base * tax.tasa_pct / PERCENT_BASE
        taxes.append(
            TaxLineItem(
                id=tax.id,
                nombre=tax.nombre,
                tasa_pct=tax.tasa_pct,
                base=base,
                monto=amount,
                incluido=tax.incluido,
                es_valor_ejemplo=tax.es_valor_ejemplo,
            )
        )
    return taxes

