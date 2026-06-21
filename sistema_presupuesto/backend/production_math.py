"""Matematica tecnica offset para Sistema Presupuesto.

No calcula dinero. Las funciones son puras y trabajan con `Decimal`.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_CEILING

from .defaults import MM2_PER_M2, PERCENT_BASE
from .models import ProductionEstimate, QuoteRequest, SizeMM, ValidationIssue


def ceil_decimal(value: Decimal) -> Decimal:
    """Redondea hacia arriba y conserva `Decimal`."""

    return value.to_integral_value(rounding=ROUND_CEILING)


def piece_size_with_bleed(request: QuoteRequest) -> SizeMM:
    producto = request.producto
    bleed_total = producto.sangrado_mm * Decimal("2")
    return SizeMM(
        ancho=producto.ancho_mm + bleed_total,
        alto=producto.alto_mm + bleed_total,
    )


def units_per_sheet(piece_size: SizeMM, sheet_size: SizeMM) -> Decimal:
    """Calcula unidades por pliego con grilla no rotada.

    La rotacion y nesting real quedan para integraciones futuras.
    """

    across = sheet_size.ancho // piece_size.ancho
    down = sheet_size.alto // piece_size.alto
    units = across * down
    if units <= 0:
        return Decimal("0")
    return Decimal(units)


def page_factor(request: QuoteRequest) -> Decimal:
    """Factor tecnico minimo para productos multipagina."""

    if request.producto.tipo == "revista":
        # Aproximacion inicial: una firma logica cada 4 paginas.
        return Decimal(request.producto.paginas or 0) / Decimal("4")
    return Decimal("1")


def plate_count(request: QuoteRequest, factor_paginas: Decimal) -> Decimal:
    colors = Decimal(request.producto.colores.frente + request.producto.colores.dorso)
    return colors * factor_paginas


def press_passes(request: QuoteRequest, machine_catalog: dict) -> Decimal:
    bodies = Decimal(str(machine_catalog.get("cuerpos_color") or 1))
    passes = Decimal("0")
    if request.producto.colores.frente > 0:
        passes += ceil_decimal(Decimal(request.producto.colores.frente) / bodies)
    if request.producto.colores.dorso > 0:
        passes += ceil_decimal(Decimal(request.producto.colores.dorso) / bodies)
    return passes


def estimate_production(request: QuoteRequest, machine_catalog: dict) -> ProductionEstimate:
    warnings: list[ValidationIssue] = []
    piece_size = piece_size_with_bleed(request)
    calculated_units = units_per_sheet(piece_size, request.produccion.pliego_util_mm)

    if request.produccion.formas_por_pliego_manual is not None:
        units = request.produccion.formas_por_pliego_manual
        warnings.append(
            ValidationIssue(
                code="MANUAL_FORMS_PER_SHEET",
                message="Se usa formas_por_pliego_manual sin validacion geometrica avanzada.",
                path="produccion.formas_por_pliego_manual",
            )
        )
    else:
        units = calculated_units
        warnings.append(
            ValidationIssue(
                code="GRID_IMPOSITION_APPROXIMATION",
                message="Unidades por pliego calculadas por grilla no rotada; no es nesting real.",
                path="produccion.pliego_util_mm",
            )
        )

    if units <= 0:
        warnings.append(
            ValidationIssue(
                code="PIECE_DOES_NOT_FIT",
                message="La pieza con sangrado no entra en el pliego util.",
                path="producto",
            )
        )
        units = Decimal("1")

    factor_paginas = page_factor(request)
    if request.producto.tipo == "revista":
        warnings.append(
            ValidationIssue(
                code="MAGAZINE_SIGNATURE_APPROXIMATION",
                message="Revista calculada con factor paginas/4; cuadernillos reales quedan para fase posterior.",
                path="producto.paginas",
            )
        )

    pliegos_buenos = ceil_decimal((request.producto.cantidad * factor_paginas) / units)
    merma_porcentaje = ceil_decimal(pliegos_buenos * request.produccion.merma_pct / PERCENT_BASE)
    merma_pliegos = request.produccion.merma_arranque_pliegos + merma_porcentaje
    pliegos_brutos = pliegos_buenos + merma_pliegos
    pasadas = press_passes(request, machine_catalog)
    impresiones = pliegos_brutos * pasadas

    rendimiento = machine_catalog.get("rendimiento", {})
    velocidad = Decimal(str(rendimiento.get("velocidad_pliegos_hora") or "1"))
    setup_horas = Decimal(str(rendimiento.get("setup_horas") or "0"))
    horas_tirada = impresiones / velocidad
    horas_maquina_total = setup_horas + horas_tirada
    area_pliego_util_m2 = (
        request.produccion.pliego_util_mm.ancho * request.produccion.pliego_util_mm.alto / MM2_PER_M2
    )

    return ProductionEstimate(
        pieza_con_sangrado_mm=piece_size,
        unidades_por_pliego=units,
        factor_paginas=factor_paginas,
        pliegos_buenos=pliegos_buenos,
        merma_pliegos=merma_pliegos,
        pliegos_brutos=pliegos_brutos,
        chapas=plate_count(request, factor_paginas),
        pasadas=pasadas,
        impresiones=impresiones,
        horas_tirada=horas_tirada,
        horas_maquina_total=horas_maquina_total,
        area_pliego_util_m2=area_pliego_util_m2,
        warnings=tuple(warnings),
    )
