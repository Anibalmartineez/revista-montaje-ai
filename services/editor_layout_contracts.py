import os
from collections import Counter
from typing import Any, Dict, List, Tuple


def ensure_post_editor_layout_defaults(layout: Dict[str, Any]) -> Dict[str, Any]:
    """Garantiza las claves mínimas esperadas por el editor post-imposición."""
    if "bleed_mm" not in layout:
        layout["bleed_mm"] = 0
    if "min_gap_mm" not in layout:
        layout["min_gap_mm"] = 0
    return layout


def sanitize_post_editor_layout_items(
    job_dir: str,
    meta: Dict[str, Any],
    items: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    sheet_info = meta.get("sheet") or {}
    margins = sheet_info.get("margins_mm", {})
    pinza_mm = float(sheet_info.get("pinza_mm", 0.0))
    sheet_w = float(sheet_info.get("w_mm", 0.0))
    sheet_h = float(sheet_info.get("h_mm", 0.0))
    if sheet_w <= 0 or sheet_h <= 0:
        raise ValueError("Dimensiones de pliego inválidas en metadatos")

    left_margin = float(margins.get("left", 0.0))
    right_margin = float(margins.get("right", 0.0))
    top_margin = float(margins.get("top", 0.0))
    bottom_margin = float(margins.get("bottom", 0.0)) + pinza_mm

    designs_meta = meta.get("designs", [])
    design_by_src = {d.get("src"): d for d in designs_meta}
    if not design_by_src:
        raise ValueError("Metadatos del trabajo incompletos")

    sanitized = []
    posiciones_manual = []
    counts = Counter()
    layout_bleed_raw = meta.get("bleed_mm", 0.0)
    try:
        layout_bleed_mm = float(layout_bleed_raw)
    except Exception:
        layout_bleed_mm = 0.0

    for raw in items:
        if not isinstance(raw, dict):
            raise ValueError("Cada item debe ser un objeto")
        src_rel = raw.get("src")
        if not isinstance(src_rel, str):
            raise ValueError("Cada item necesita un 'src'")
        record = design_by_src.get(src_rel)
        if not record:
            raise ValueError(f"Recurso no permitido: {src_rel}")
        abs_src = os.path.normpath(os.path.join(job_dir, record.get("src", "")))
        try:
            common = os.path.commonpath([abs_src, os.path.normpath(job_dir)])
        except ValueError:
            common = ""
        if common != os.path.normpath(job_dir):
            raise ValueError("Ruta de recurso fuera del directorio del trabajo")
        if not os.path.exists(abs_src):
            raise ValueError(f"El recurso no existe en el servidor: {src_rel}")

        try:
            x_mm = float(raw.get("x_mm"))
            y_mm = float(raw.get("y_mm"))
            w_mm = float(raw.get("w_mm"))
            h_mm = float(raw.get("h_mm"))
        except Exception as exc:
            raise ValueError("Coordenadas inválidas en layout") from exc

        if w_mm <= 0 or h_mm <= 0:
            raise ValueError("El ancho/alto debe ser mayor que cero")

        rotation = int(raw.get("rotation", 0)) % 360
        if rotation not in (0, 90, 180, 270):
            raise ValueError("La rotación debe ser 0, 90, 180 o 270")

        bleed_override = raw.get("bleed_override_mm")
        try:
            bleed_effective = (
                float(bleed_override)
                if bleed_override is not None and bleed_override != ""
                else layout_bleed_mm
            )
        except Exception:
            raise ValueError("bleed_override_mm inválido en layout")

        eps = 1e-6
        if x_mm < left_margin - eps or y_mm < bottom_margin - eps:
            raise ValueError("Una pieza está fuera de los márgenes permitidos")
        if x_mm + w_mm > sheet_w - right_margin + eps:
            raise ValueError("Una pieza excede el ancho disponible")
        if y_mm + h_mm > sheet_h - top_margin + eps:
            raise ValueError("Una pieza excede el alto disponible")

        sanitized.append(
            {
                "id": raw.get("id") or f"item{len(sanitized)}",
                "src": src_rel,
                "page": int(raw.get("page", 0)),
                "x_mm": x_mm,
                "y_mm": y_mm,
                "w_mm": w_mm,
                "h_mm": h_mm,
                "rotation": rotation,
                "flip_x": bool(raw.get("flip_x", False)),
                "flip_y": bool(raw.get("flip_y", False)),
                "file_idx": int(record.get("index", 0)),
                "bleed_override_mm": bleed_override,
                "bleed_mm": bleed_effective,
            }
        )
        posiciones_manual.append(
            {
                "file_idx": int(record.get("index", 0)),
                "x_mm": x_mm,
                "y_mm": y_mm,
                "w_mm": w_mm,
                "h_mm": h_mm,
                "rot_deg": rotation,
                "bleed_override_mm": bleed_override,
                "bleed_mm": bleed_effective,
            }
        )
        counts[int(record.get("index", 0))] += 1

    expected = {int(d.get("index", 0)): int(d.get("cantidad", 0)) for d in designs_meta}
    for idx, total in expected.items():
        if counts.get(idx, 0) != total:
            raise ValueError(
                f"La cantidad de piezas para el diseño {idx} no coincide con el montaje original"
            )

    for i, a in enumerate(sanitized):
        ax1, ay1 = a["x_mm"], a["y_mm"]
        ax2, ay2 = ax1 + a["w_mm"], ay1 + a["h_mm"]
        for b in sanitized[i + 1 :]:
            bx1, by1 = b["x_mm"], b["y_mm"]
            bx2, by2 = bx1 + b["w_mm"], by1 + b["h_mm"]
            if ax1 >= bx2 - eps or bx1 >= ax2 - eps:
                continue
            if ay1 >= by2 - eps or by1 >= ay2 - eps:
                continue
            raise ValueError("Hay piezas solapadas en el layout propuesto")

    return sanitized, posiciones_manual
