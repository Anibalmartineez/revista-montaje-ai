"""Modelos internos base para contratos de presupuesto.

Estos modelos no calculan costos. Solo normalizan una solicitud validada
para que fases futuras puedan construir motores y persistencia sobre una
superficie estable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class ValidationIssue:
    """Error o advertencia producido por validadores."""

    code: str
    message: str
    path: str

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "message": self.message,
            "path": self.path,
        }


@dataclass
class ValidationReport:
    """Resultado auditable de validacion de contrato."""

    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def add_error(self, code: str, message: str, path: str) -> None:
        self.errors.append(ValidationIssue(code=code, message=message, path=path))

    def add_warning(self, code: str, message: str, path: str) -> None:
        self.warnings.append(ValidationIssue(code=code, message=message, path=path))

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "errors": [issue.to_dict() for issue in self.errors],
            "warnings": [issue.to_dict() for issue in self.warnings],
        }


@dataclass(frozen=True)
class ClienteSpec:
    nombre: str | None = None
    referencia: str | None = None


@dataclass(frozen=True)
class ColorSpec:
    frente: int
    dorso: int
    texto: str


@dataclass(frozen=True)
class SizeMM:
    ancho: Decimal
    alto: Decimal


@dataclass(frozen=True)
class EncuadernacionSpec:
    tipo: str
    proceso_id: str | None = None


@dataclass(frozen=True)
class ProductoSpec:
    titulo: str
    tipo: str
    cantidad: Decimal
    unidad_cantidad: str
    ancho_mm: Decimal
    alto_mm: Decimal
    sangrado_mm: Decimal
    paginas: int | None
    caras: int
    colores: ColorSpec
    formato_abierto_mm: SizeMM | None = None
    formato_cerrado_mm: SizeMM | None = None
    paneles: int | None = None
    pliegues: int | None = None
    encuadernacion: EncuadernacionSpec | None = None


@dataclass(frozen=True)
class ProduccionSpec:
    pliego_base_mm: SizeMM
    pliego_util_mm: SizeMM
    formas_por_pliego_manual: Decimal | None
    merma_arranque_pliegos: Decimal
    merma_pct: Decimal
    imposicion_origen: str | None = None


@dataclass(frozen=True)
class ImpuestoSpec:
    id: str
    nombre: str
    tasa_pct: Decimal
    base: str
    incluido: bool
    es_valor_ejemplo: bool = False


@dataclass(frozen=True)
class CostosSpec:
    moneda: str
    material_id: str
    maquina_id: str
    procesos_ids: tuple[str, ...]
    margen_pct: Decimal | None
    markup_pct: Decimal | None
    impuestos: tuple[ImpuestoSpec, ...] = ()


@dataclass(frozen=True)
class QuoteRequest:
    schema: str
    schema_version: int
    fixture_id: str | None
    descripcion: str | None
    cliente: ClienteSpec
    producto: ProductoSpec
    produccion: ProduccionSpec
    costos: CostosSpec
    expected_assertions: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CatalogRefs:
    """IDs disponibles para validacion de catalogos."""

    materiales: frozenset[str] = frozenset()
    maquinas: frozenset[str] = frozenset()
    procesos: frozenset[str] = frozenset()


@dataclass(frozen=True)
class ProductionEstimate:
    """Resultado tecnico de produccion, sin costos monetarios."""

    pieza_con_sangrado_mm: SizeMM
    unidades_por_pliego: Decimal
    factor_paginas: Decimal
    pliegos_buenos: Decimal
    merma_pliegos: Decimal
    pliegos_brutos: Decimal
    chapas: Decimal
    pasadas: Decimal
    impresiones: Decimal
    horas_tirada: Decimal
    horas_maquina_total: Decimal
    area_pliego_util_m2: Decimal
    warnings: tuple[ValidationIssue, ...] = ()


@dataclass(frozen=True)
class CostLineItem:
    """Linea auditable de costo."""

    codigo: str
    descripcion: str
    cantidad: Decimal
    unidad: str
    costo_unitario: Decimal
    subtotal: Decimal
    es_valor_ejemplo: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "codigo": self.codigo,
            "descripcion": self.descripcion,
            "cantidad": str(self.cantidad),
            "unidad": self.unidad,
            "costo_unitario": str(self.costo_unitario),
            "subtotal": str(self.subtotal),
            "es_valor_ejemplo": self.es_valor_ejemplo,
        }


@dataclass(frozen=True)
class TaxLineItem:
    """Linea auditable de impuesto aplicado."""

    id: str
    nombre: str
    tasa_pct: Decimal
    base: Decimal
    monto: Decimal
    incluido: bool
    es_valor_ejemplo: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "nombre": self.nombre,
            "tasa_pct": str(self.tasa_pct),
            "base": str(self.base),
            "monto": str(self.monto),
            "incluido": self.incluido,
            "es_valor_ejemplo": self.es_valor_ejemplo,
        }


@dataclass(frozen=True)
class PricingResult:
    """Resultado monetario calculado a partir de una estimacion tecnica."""

    moneda: str
    items: tuple[CostLineItem, ...]
    costo_tecnico: Decimal
    margen_tipo: str | None
    margen_pct: Decimal | None
    margen_monto: Decimal
    markup_pct: Decimal | None
    descuento: Decimal
    impuestos: tuple[TaxLineItem, ...]
    precio_antes_impuestos: Decimal
    precio_final: Decimal
    precio_unitario: Decimal
    warnings: tuple[ValidationIssue, ...] = ()


@dataclass(frozen=True)
class QuoteResult:
    """Resultado final de calculo determinista."""

    schema: str
    schema_version: int
    ok: bool
    request_fixture_id: str | None
    produccion: ProductionEstimate
    costos: PricingResult
    warnings: tuple[ValidationIssue, ...] = ()
