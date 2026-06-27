"""Local image heuristics for PDF Medidor Pro AI measurement."""

from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import Any

from PIL import Image


def detect_object_near(
    image_path: str | Path,
    *,
    x_px: float,
    y_px: float,
    max_width_ratio: float = 0.45,
    max_height_ratio: float = 0.45,
    search_radius_px: int = 28,
) -> dict[str, Any] | None:
    """Find a non-white connected component near a click."""

    with Image.open(image_path) as image:
        rgb = image.convert("RGB")
        width, height = rgb.size
        pixels = rgb.load()
        seed = _nearest_ink_pixel(pixels, width, height, int(x_px), int(y_px), search_radius_px)
        if seed is None:
            return None
        bbox, count = _connected_component_bbox(pixels, width, height, seed)
        bbox = _clamp_large_bbox(bbox, int(x_px), int(y_px), width, height, max_width_ratio, max_height_ratio)
        bw = max(0, bbox[2] - bbox[0] + 1)
        bh = max(0, bbox[3] - bbox[1] + 1)
        if bw <= 1 or bh <= 1:
            return None
        confidence = _confidence(bw, bh, width, height, count)
        return {
            "bbox_px": {"x": bbox[0], "y": bbox[1], "w": bw, "h": bh},
            "image_px": {"w": width, "h": height},
            "ink_pixels": count,
            "confidence": confidence,
        }


def detect_printed_area(image_path: str | Path) -> dict[str, Any] | None:
    with Image.open(image_path) as image:
        rgb = image.convert("RGB")
        width, height = rgb.size
        pixels = rgb.load()
        x0, y0, x1, y1, count = width, height, -1, -1, 0
        for y in range(height):
            for x in range(width):
                if _is_ink(pixels[x, y]):
                    x0 = min(x0, x)
                    y0 = min(y0, y)
                    x1 = max(x1, x)
                    y1 = max(y1, y)
                    count += 1
        if count == 0:
            return None
        return {
            "bbox_px": {"x": x0, "y": y0, "w": x1 - x0 + 1, "h": y1 - y0 + 1},
            "image_px": {"w": width, "h": height},
            "ink_pixels": count,
            "confidence": _confidence(x1 - x0 + 1, y1 - y0 + 1, width, height, count),
        }


def count_objects(image_path: str | Path, min_area_px: int = 80) -> dict[str, Any]:
    with Image.open(image_path) as image:
        rgb = image.convert("RGB")
        width, height = rgb.size
        pixels = rgb.load()
        visited: set[tuple[int, int]] = set()
        components: list[dict[str, Any]] = []
        for y in range(height):
            for x in range(width):
                if (x, y) in visited or not _is_ink(pixels[x, y]):
                    continue
                bbox, count = _connected_component_bbox(pixels, width, height, (x, y), visited=visited)
                if count >= min_area_px:
                    components.append(
                        {
                            "bbox_px": {"x": bbox[0], "y": bbox[1], "w": bbox[2] - bbox[0] + 1, "h": bbox[3] - bbox[1] + 1},
                            "ink_pixels": count,
                        }
                    )
        return {"count": len(components), "components": components, "image_px": {"w": width, "h": height}}


def _nearest_ink_pixel(pixels: Any, width: int, height: int, x: int, y: int, radius: int) -> tuple[int, int] | None:
    x = max(0, min(width - 1, x))
    y = max(0, min(height - 1, y))
    if _is_ink(pixels[x, y]):
        return (x, y)
    for r in range(1, radius + 1):
        for yy in range(max(0, y - r), min(height, y + r + 1)):
            for xx in range(max(0, x - r), min(width, x + r + 1)):
                if abs(xx - x) != r and abs(yy - y) != r:
                    continue
                if _is_ink(pixels[xx, yy]):
                    return (xx, yy)
    return None


def _connected_component_bbox(
    pixels: Any,
    width: int,
    height: int,
    seed: tuple[int, int],
    *,
    visited: set[tuple[int, int]] | None = None,
) -> tuple[tuple[int, int, int, int], int]:
    own_visited = visited is None
    visited = visited if visited is not None else set()
    queue: deque[tuple[int, int]] = deque([seed])
    visited.add(seed)
    x0 = x1 = seed[0]
    y0 = y1 = seed[1]
    count = 0
    while queue:
        x, y = queue.popleft()
        count += 1
        x0 = min(x0, x)
        y0 = min(y0, y)
        x1 = max(x1, x)
        y1 = max(y1, y)
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if nx < 0 or ny < 0 or nx >= width or ny >= height or (nx, ny) in visited:
                continue
            if _is_ink(pixels[nx, ny]):
                visited.add((nx, ny))
                queue.append((nx, ny))
    if own_visited:
        visited.clear()
    return (x0, y0, x1, y1), count


def _clamp_large_bbox(
    bbox: tuple[int, int, int, int],
    cx: int,
    cy: int,
    width: int,
    height: int,
    max_width_ratio: float,
    max_height_ratio: float,
) -> tuple[int, int, int, int]:
    max_w = max(8, int(width * max_width_ratio))
    max_h = max(8, int(height * max_height_ratio))
    bw = bbox[2] - bbox[0] + 1
    bh = bbox[3] - bbox[1] + 1
    if bw <= max_w and bh <= max_h:
        return bbox
    half_w = max_w // 2
    half_h = max_h // 2
    return (
        max(0, cx - half_w),
        max(0, cy - half_h),
        min(width - 1, cx + half_w),
        min(height - 1, cy + half_h),
    )


def _confidence(bw: int, bh: int, width: int, height: int, ink_pixels: int) -> float:
    area_ratio = (bw * bh) / max(1, width * height)
    density = ink_pixels / max(1, bw * bh)
    if area_ratio < 0.25 and density > 0.12:
        return 0.86
    if area_ratio < 0.45 and density > 0.05:
        return 0.62
    return 0.38


def _is_ink(rgb: tuple[int, int, int]) -> bool:
    r, g, b = rgb
    return min(r, g, b) < 245 and (255 - ((int(r) + int(g) + int(b)) / 3)) > 8
