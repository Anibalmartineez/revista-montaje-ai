"""V2 crop ticks inside the bleed band; dimensions are millimetres.

Keep crop_mark_dimensions in geometry_view.js in parity. Butt caps plus the
half-stroke inset keep ink inside bleed even for narrow bands. Zero bleed
produces no marks; the output capability check reports the omission.
"""
from .geometry import trim_polygon


def crop_mark_dimensions(bleed):
    if bleed <= 0:
        return None
    width = min(.2, bleed / 5)
    start = min(1, bleed / 4)
    end = min(bleed - width / 2, start + 3)
    return start, end, width


def crop_segments(geometry):
    dimensions = crop_mark_dimensions(geometry.bleed)
    if dimensions is None:
        return []
    start, end, _ = dimensions
    polygon = trim_polygon(geometry).points
    lines = []
    for i, point in enumerate(polygon):
        for other in (polygon[i-1], polygon[(i+1) % 4]):
            dx, dy = point.x - other.x, point.y - other.y
            norm = (dx*dx + dy*dy)**.5
            lines.append(((point.x + dx/norm*start, point.y + dy/norm*start),
                          (point.x + dx/norm*end, point.y + dy/norm*end)))
    return lines
