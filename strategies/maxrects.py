from typing import Any, Dict, List, Tuple

from montaje_offset_inteligente import montar_pliego_offset_inteligente

from .base import BaseMontajeStrategy
from .common import build_call_args


class MaxRectsStrategy(BaseMontajeStrategy):
    def calcular(
        self,
        disenos: List[Tuple[str, int]],
        config,
        meta: Dict[str, Any],
    ) -> Dict[str, Any]:
        ancho_pliego, alto_pliego, kwargs = build_call_args(config)
        kwargs["estrategia"] = "maxrects"
        return montar_pliego_offset_inteligente(disenos, ancho_pliego, alto_pliego, **kwargs)
