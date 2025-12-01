from __future__ import annotations

from typing import Dict, Type

from .base import BaseMontajeStrategy
from .flow import FlowStrategy
from .grid import GridStrategy
from .hybrid_nesting_strategy import HybridNestingStrategy
from .manual import ManualStrategy
from .maxrects import MaxRectsStrategy
from .nesting_pro_strategy import NestingProStrategy

STRATEGY_CLASSES: Dict[str, Type[BaseMontajeStrategy]] = {
    "flujo": FlowStrategy,
    "grid": GridStrategy,
    "maxrects": MaxRectsStrategy,
    "manual": ManualStrategy,
    "nesting_pro": NestingProStrategy,
    "hybrid_nesting_repeat": HybridNestingStrategy,
}


def get_strategy(name: str | None) -> BaseMontajeStrategy:
    clave = (name or "flujo").lower()
    cls = STRATEGY_CLASSES.get(clave)
    if cls is None:
        cls = FlowStrategy
    return cls()
