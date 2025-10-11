"""Utilidades para cálculos de transmisión de tinta coherentes en todo el pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping

__all__ = [
    "InkParams",
    "InkTransfer",
    "calcular_transmision_tinta",
    "normalizar_coberturas",
    "get_ink_ideal_mlmin",
    "clasificar_riesgo_por_ideal",
]


INK_IDEAL_POR_MATERIAL = {
    "film": 120.0,
    "papel": 180.0,
    "carton": 200.0,
    "etiqueta adhesiva": 150.0,
    "default": 150.0,
}


def get_ink_ideal_mlmin(material: str | None) -> float:
    m = (material or "").strip().lower()
    return INK_IDEAL_POR_MATERIAL.get(m, INK_IDEAL_POR_MATERIAL["default"])


def clasificar_riesgo_por_ideal(ml_min: float | None, ideal: float | None):
    if not ml_min or not ideal or ideal <= 0:
        return 1, "Amarillo", ["Sin ideal definido: usar criterio del operador."]
    ratio = ml_min / ideal
    delta_pct = (ratio - 1.0) * 100.0
    # Verde: dentro de ±10%
    if 0.90 <= ratio <= 1.10:
        return 0, "Verde", [
            f"Dentro de ±10% del ideal ({ml_min:.2f} vs {ideal:.0f} ml/min)."
        ]
    # Amarillo: 10–30% por debajo o por encima
    if 0.75 <= ratio < 0.90:
        return 1, "Amarillo", [f"Subcarga {abs(delta_pct):.0f}% bajo el ideal."]
    if 1.10 < ratio <= 1.30:
        return 1, "Amarillo", [f"Sobre carga +{delta_pct:.0f}% sobre el ideal."]
    # Rojo: >30% de desvío
    if ratio < 0.75:
        return 2, "Rojo", [f"Subcarga {abs(delta_pct):.0f}% bajo el ideal."]
    return 2, "Rojo", [f"Sobre carga +{delta_pct:.0f}% sobre el ideal."]


@dataclass(frozen=True)
class InkParams:
    """Parámetros de entrada para calcular transmisión de tinta.

    Attributes
    ----------
    anilox_lpi:
        Lineatura del anilox en líneas por pulgada.
    anilox_bcm:
        Capacidad del anilox en cm³/m².
    velocidad_m_min:
        Velocidad lineal de impresión expresada en metros por minuto.
    ancho_util_m:
        Ancho útil del material en metros.
    coef_material:
        Coeficiente de transmisión/absorción del sustrato (0..1).
    """

    anilox_lpi: int
    anilox_bcm: float  # cm^3/m^2
    velocidad_m_min: float  # m/min
    ancho_util_m: float  # m
    coef_material: float  # 0..1


@dataclass
class InkTransfer:
    """Resultado de transmisión de tinta expresado en ml/min."""

    ml_min_global: float
    ml_min_por_canal: Dict[str, float]


_CANAL_ALIAS: Dict[str, str] = {
    "c": "C",
    "cyan": "C",
    "cian": "C",
    "m": "M",
    "magenta": "M",
    "y": "Y",
    "yellow": "Y",
    "amarillo": "Y",
    "k": "K",
    "key": "K",
    "negro": "K",
}


def normalizar_coberturas(coverage: Mapping[str, Any] | None) -> Dict[str, float]:
    valores: Dict[str, float] = {"C": 0.0, "M": 0.0, "Y": 0.0, "K": 0.0}
    if not coverage:
        return valores

    for canal, bruto in coverage.items():
        if canal is None:
            continue
        clave = str(canal).strip().lower()
        letra = _CANAL_ALIAS.get(clave)
        if letra is None and clave:
            letra = _CANAL_ALIAS.get(clave[0])
        if letra is None:
            continue
        try:
            valor = float(bruto)
        except (TypeError, ValueError):
            continue
        if not (valor == valor):  # NaN check
            continue
        valor = max(0.0, min(100.0, valor))
        valores[letra] = valor
    return valores


def calcular_transmision_tinta(
    params: InkParams,
    coverage_por_canal: Mapping[str, Any] | None,
    thresholds: Any,
) -> InkTransfer:
    """Calcula la transmisión de tinta en ml/min para cada canal CMYK.

    La fórmula canónica multiplica la capacidad del anilox (cm³/m²) por la
    fracción de cobertura de cada canal (``coverage_por_canal`` / 100), el ancho
    útil del sustrato (m) y la velocidad de impresión (m/min). El coeficiente de
    material se aplica como factor multiplicador final. Como 1 cm³ equivale a
    1 ml, el resultado ya queda expresado en ml/min. Se redondea a 2 decimales
    para mantener consistencia con las interfaces previas.

    Parameters
    ----------
    params:
        Parámetros geométricos y de máquina.
    coverage_por_canal:
        Cobertura por canal en porcentaje (0..100).  Valores fuera del rango se
        recortan automáticamente.
    thresholds:
        Perfil de umbrales flexográficos. Se acepta para futura expansión pero
        no altera la fórmula actual.
    """

    coberturas = normalizar_coberturas(coverage_por_canal)
    ancho = max(0.0, float(params.ancho_util_m))
    velocidad = max(0.0, float(params.velocidad_m_min))
    bcm = max(0.0, float(params.anilox_bcm))
    coef_material = max(0.0, float(params.coef_material))

    por_canal_ml: Dict[str, float] = {}
    for canal, porcentaje in coberturas.items():
        fraccion = porcentaje / 100.0
        volumen = bcm * fraccion * velocidad * ancho * coef_material
        por_canal_ml[canal] = round(volumen, 2)

    total = round(sum(por_canal_ml.values()), 2)
    return InkTransfer(ml_min_global=total, ml_min_por_canal=por_canal_ml)
