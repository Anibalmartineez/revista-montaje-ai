"""Nesting PRO engine using rectpack for optimal packing."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from rectpack import newPacker


@dataclass
class NestingPiece:
    design_ref: str
    width_mm: float
    height_mm: float
    bleed_mm: float
    allow_rotation: bool
    forms_per_plate: int

    @property
    def padded_size(self) -> Tuple[float, float]:
        bleed_pad = max(0.0, self.bleed_mm) * 2
        return self.width_mm + bleed_pad, self.height_mm + bleed_pad


@dataclass
class NestingResult:
    slots: List[Dict]
    bbox: Tuple[float, float, float, float]


def _normalize_design(design: Dict) -> NestingPiece | None:
    try:
        ref = design.get("ref") or design.get("file")
        width = float(design.get("width_mm") or design.get("w_mm") or 0)
        height = float(design.get("height_mm") or design.get("h_mm") or 0)
    except (TypeError, ValueError):
        return None
    if not ref or width <= 0 or height <= 0:
        return None
    bleed = float(design.get("bleed_mm") or 0)
    forms = int(design.get("forms_per_plate") or 0)
    return NestingPiece(
        design_ref=str(ref),
        width_mm=width,
        height_mm=height,
        bleed_mm=max(0.0, bleed),
        allow_rotation=bool(design.get("allow_rotation", True)),
        forms_per_plate=max(1, forms),
    )


def _available_area(layout: Dict) -> Tuple[float, float, float, float]:
    sheet_w, sheet_h = layout.get("sheet_mm", [0, 0])
    margins = layout.get("margins_mm", [0, 0, 0, 0])
    left, right, top, bottom = (margins + [0, 0, 0, 0])[:4]
    usable_w = max(0.0, float(sheet_w) - float(left) - float(right))
    usable_h = max(0.0, float(sheet_h) - float(top) - float(bottom))
    return usable_w, usable_h, float(left), float(bottom)


def _rectpack_positions(pieces: List[NestingPiece], layout: Dict) -> NestingResult:
    usable_w, usable_h, offset_x, offset_y = _available_area(layout)
    if usable_w <= 0 or usable_h <= 0:
        return NestingResult(slots=[], bbox=(0, 0, 0, 0))

    gap = float(layout.get("gap_default_mm") or 0)
    pad = max(0.0, gap)
    packer = newPacker(rotation=True)
    packer.add_bin(usable_w, usable_h)

    for piece in pieces:
        padded_w, padded_h = piece.padded_size
        rect_w = padded_w + pad
        rect_h = padded_h + pad
        for _ in range(piece.forms_per_plate):
            # rectpack sólo acepta (width, height, rid).
            # La rotación se controla globalmente con rotation=True al crear el packer.
            # Usamos 'rid' para identificar el diseño y luego inferimos si fue rotado
            # comparando ancho/alto en rect_list().
            packer.add_rect(rect_w, rect_h, rid=piece.design_ref)

    packer.pack()

    slots: List[Dict] = []
    min_x = min_y = float("inf")
    max_x = max_y = 0.0
    piece_map = {p.design_ref: p for p in pieces}

    for _, x, y, w, h, rid in packer.rect_list():
        piece = piece_map.get(rid)
        if not piece:
            continue
        padded_w, padded_h = piece.padded_size
        rot = 0
        width_used, height_used = padded_w, padded_h
        if abs(w - (padded_h + pad)) < 1e-3 and piece.allow_rotation:
            rot = 90
            width_used, height_used = padded_h, padded_w
        center_offset = pad / 2 if pad > 0 else 0
        slot_x = offset_x + x + center_offset
        slot_y_from_top = y + center_offset
        slot_y = offset_y + (usable_h - (slot_y_from_top + h))
        slot = {
            "design_ref": rid,
            "x_mm": round(slot_x, 4),
            "y_mm": round(slot_y, 4),
            "w_mm": round(width_used, 4),
            "h_mm": round(height_used, 4),
            "rotation_deg": rot,
            "bleed_mm": piece.bleed_mm,
        }
        slots.append(slot)
        min_x = min(min_x, slot_x)
        min_y = min(min_y, slot_y)
        max_x = max(max_x, slot_x + width_used)
        max_y = max(max_y, slot_y + height_used)

    if min_x == float("inf"):
        min_x = min_y = max_x = max_y = 0.0

    return NestingResult(slots=slots, bbox=(min_x, min_y, max_x, max_y))


def compute_nesting(layout: Dict) -> NestingResult:
    pieces: List[NestingPiece] = []
    for design in layout.get("designs", []):
        piece = _normalize_design(design)
        if piece:
            pieces.append(piece)
    if not pieces:
        return NestingResult(slots=[], bbox=(0, 0, 0, 0))
    return _rectpack_positions(pieces, layout)
