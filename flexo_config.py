"""Configuración centralizada de umbrales para diagnóstico flexográfico."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Dict, Iterable, Mapping, Optional

__all__ = [
    "FlexoThresholds",
    "get_flexo_thresholds",
    "threshold_profiles",
]


@dataclass(frozen=True)
class FlexoThresholds:
    """Valores mínimos y máximos recomendados para un perfil flexográfico."""

    min_text_pt: float = 4.0
    min_stroke_mm: float = 0.20
    min_bleed_mm: float = 3.0
    min_resolution_dpi: int = 300
    tac_warning: int = 280
    tac_critical: int = 320
    edge_distance_mm: float = 2.0

    def to_dict(self) -> Dict[str, float | int]:
        """Convierte la instancia a un diccionario serializable."""

        return {
            "min_text_pt": self.min_text_pt,
            "min_stroke_mm": self.min_stroke_mm,
            "min_bleed_mm": self.min_bleed_mm,
            "min_resolution_dpi": self.min_resolution_dpi,
            "tac_warning": self.tac_warning,
            "tac_critical": self.tac_critical,
            "edge_distance_mm": self.edge_distance_mm,
        }


_DEFAULT_THRESHOLDS = FlexoThresholds()

_PROFILE_OVERRIDES: Mapping[str, FlexoThresholds] = {
    "film": FlexoThresholds(min_stroke_mm=0.12, tac_warning=300, tac_critical=320),
    "papel": FlexoThresholds(min_stroke_mm=0.20, tac_warning=280, tac_critical=300),
    "etiqueta_adhesiva": FlexoThresholds(
        min_stroke_mm=0.18, tac_warning=260, tac_critical=280
    ),
    "carton": FlexoThresholds(min_stroke_mm=0.22, tac_warning=300, tac_critical=320),
}

_ANILOX_RULES: Iterable[tuple[float, Dict[str, float]]] = (
    (500.0, {"min_text_pt": 3.8}),
    (600.0, {"min_text_pt": 3.6, "min_stroke_mm": 0.18}),
    (800.0, {"min_text_pt": 3.4, "min_stroke_mm": 0.16}),
)


def _normalizar_clave(valor: Optional[str]) -> str:
    if not valor:
        return ""
    valor = valor.strip().lower()
    reemplazos = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ñ": "n",
    }
    for origen, destino in reemplazos.items():
        valor = valor.replace(origen, destino)
    return valor.replace(" ", "_")


def _aplicar_overrides(
    base: FlexoThresholds, overrides: Mapping[str, float | int]
) -> FlexoThresholds:
    params: Dict[str, float | int] = {}
    for campo, valor in overrides.items():
        if hasattr(base, campo):
            params[campo] = valor
    if not params:
        return base
    return replace(base, **params)


def get_flexo_thresholds(
    material: Optional[str] = None,
    anilox_lpi: Optional[float] = None,
) -> FlexoThresholds:
    """Obtiene los umbrales recomendados según material y lineatura."""

    thresholds = _DEFAULT_THRESHOLDS
    clave_material = _normalizar_clave(material)
    if clave_material and clave_material in _PROFILE_OVERRIDES:
        profile = _PROFILE_OVERRIDES[clave_material]
        thresholds = replace(thresholds, **profile.to_dict())

    if anilox_lpi is not None:
        try:
            lpi = float(anilox_lpi)
        except (TypeError, ValueError):
            lpi = None
        if lpi is not None:
            for limite, overrides in _ANILOX_RULES:
                if lpi >= limite:
                    thresholds = _aplicar_overrides(thresholds, overrides)

    return thresholds


def threshold_profiles() -> Dict[str, Dict[str, float | int]]:
    """Devuelve los perfiles disponibles para inspección o reporte."""

    perfiles: Dict[str, Dict[str, float | int]] = {
        "default": _DEFAULT_THRESHOLDS.to_dict(),
    }
    for nombre, profile in _PROFILE_OVERRIDES.items():
        perfiles[nombre] = profile.to_dict()
    return perfiles
