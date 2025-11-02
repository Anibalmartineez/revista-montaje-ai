from __future__ import annotations

import statistics
from typing import Any, Dict, List, Tuple

from montaje_offset_inteligente import obtener_dimensiones_pdf


def _calc_pdf_meta(disenos: List[Tuple[str, int]], usar_trimbox: bool) -> Dict[str, Any]:
    meta: Dict[str, Any] = {"items": []}
    for ruta, qty in disenos:
        w, h = obtener_dimensiones_pdf(ruta, usar_trimbox=usar_trimbox)
        meta["items"].append(
            {
                "ruta": ruta,
                "qty": qty,
                "w": w,
                "h": h,
                "area": w * h,
                "ar": (w / h) if h else 1,
            }
        )
    return meta


def select_strategy(disenos: List[Tuple[str, int]], config) -> str:
    if getattr(config, "posiciones_manual", None):
        return "manual"

    meta = _calc_pdf_meta(disenos, usar_trimbox=getattr(config, "usar_trimbox", False))
    items = meta["items"]
    n = len(items)
    total_qty = sum(i["qty"] for i in items)
    if n == 0:
        return "flujo"
    if n == 1:
        return "flujo"

    def similar(a: float, b: float, tol: float = 1.0) -> bool:
        return abs(a - b) <= tol

    same_size = all(
        similar(items[0]["w"], it["w"]) and similar(items[0]["h"], it["h"])
        for it in items[1:]
    )

    areas = [it["area"] * it["qty"] for it in items]
    dom = max(areas) / (sum(areas) or 1)

    ws = [it["w"] for it in items]
    hs = [it["h"] for it in items]
    w_var = statistics.pvariance(ws) if len(ws) > 1 else 0.0
    h_var = statistics.pvariance(hs) if len(hs) > 1 else 0.0
    hetero = (w_var + h_var) > 10.0

    if same_size and n >= 2:
        return "grid"

    if dom >= 0.7:
        return "flujo"

    if hetero:
        return "maxrects"

    return "flujo"
