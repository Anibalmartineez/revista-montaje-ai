from __future__ import annotations

from typing import Dict, Type

from .base import BaseMontajeStrategy
from .flow import FlowStrategy
from .grid import GridStrategy
from .manual import ManualStrategy
from .maxrects import MaxRectsStrategy

STRATEGY_CLASSES: Dict[str, Type[BaseMontajeStrategy]] = {
    "flujo": FlowStrategy,
    "grid": GridStrategy,
    "maxrects": MaxRectsStrategy,
    "manual": ManualStrategy,
}


def get_strategy(name: str | None) -> BaseMontajeStrategy:
    clave = (name or "flujo").lower()
    cls = STRATEGY_CLASSES.get(clave)
    if cls is None:
        cls = FlowStrategy
    return cls()
