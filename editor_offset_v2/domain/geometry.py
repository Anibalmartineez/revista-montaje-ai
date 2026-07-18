"""Pure geometry kernel for Editor Offset Visual V2.

The kernel uses millimetres, a bottom-left sheet origin, positive X to the
right, positive Y upwards and counter-clockwise cardinal rotations around the
trim centre.  It has no dependency on Flask, the DOM, PDF files, jobs or the
productive output implementation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

from .layout_v2 import CARDINAL_ROTATIONS_DEG


# Numerical epsilon only.  It is not a productive gap or safety margin.
DEFAULT_TOLERANCE_MM = 1e-9


class GeometryValidationError(ValueError):
    """Raised when a value cannot participate in the V2 geometry contract."""


def is_finite_number(value: object) -> bool:
    """Return whether *value* is a finite int or float, excluding booleans."""

    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
    )


def validate_finite(value: object, name: str = "value") -> float:
    """Return *value* as float or raise for booleans and non-finite numbers."""

    if not is_finite_number(value):
        raise GeometryValidationError(f"{name} must be a finite number")
    return float(value)


def validate_positive(value: object, name: str = "value") -> float:
    """Return a finite value greater than zero."""

    result = validate_finite(value, name)
    if result <= 0:
        raise GeometryValidationError(f"{name} must be greater than zero")
    return result


def validate_non_negative(value: object, name: str = "value") -> float:
    """Return a finite value greater than or equal to zero."""

    result = validate_finite(value, name)
    if result < 0:
        raise GeometryValidationError(f"{name} must be zero or greater")
    return result


def validate_cardinal_rotation(value: object, name: str = "rotation_deg") -> float:
    """Return an exact V2 cardinal rotation without normalising the input."""

    result = validate_finite(value, name)
    if result not in CARDINAL_ROTATIONS_DEG:
        allowed = ", ".join(str(int(item)) for item in sorted(CARDINAL_ROTATIONS_DEG))
        raise GeometryValidationError(f"{name} must be one of {allowed}")
    return result


def _validate_tolerance(value: object) -> float:
    return validate_non_negative(value, "tolerance_mm")


@dataclass(frozen=True)
class Point:
    """A point in V2 sheet coordinates, expressed in millimetres."""

    x: float
    y: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "x", validate_finite(self.x, "x"))
        object.__setattr__(self, "y", validate_finite(self.y, "y"))


@dataclass(frozen=True)
class Size:
    """A strictly positive width and height in millimetres."""

    width: float
    height: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "width", validate_positive(self.width, "width"))
        object.__setattr__(self, "height", validate_positive(self.height, "height"))


@dataclass(frozen=True)
class Bounds:
    """Axis-aligned bounds in bottom-left V2 coordinates."""

    left: float
    right: float
    bottom: float
    top: float

    def __post_init__(self) -> None:
        left = validate_finite(self.left, "left")
        right = validate_finite(self.right, "right")
        bottom = validate_finite(self.bottom, "bottom")
        top = validate_finite(self.top, "top")
        if right < left:
            raise GeometryValidationError("right must be greater than or equal to left")
        if top < bottom:
            raise GeometryValidationError("top must be greater than or equal to bottom")
        object.__setattr__(self, "left", left)
        object.__setattr__(self, "right", right)
        object.__setattr__(self, "bottom", bottom)
        object.__setattr__(self, "top", top)

    @property
    def width(self) -> float:
        return self.right - self.left

    @property
    def height(self) -> float:
        return self.top - self.bottom

    @property
    def center(self) -> Point:
        return Point(
            self.left + self.width / 2.0,
            self.bottom + self.height / 2.0,
        )


def _signed_area_twice(points: tuple[Point, ...]) -> float:
    return sum(
        first.x * second.y - second.x * first.y
        for first, second in zip(points, points[1:] + points[:1])
    )


def _cross(origin: Point, first: Point, second: Point) -> float:
    return (first.x - origin.x) * (second.y - origin.y) - (
        first.y - origin.y
    ) * (second.x - origin.x)


@dataclass(frozen=True)
class Polygon:
    """A non-degenerate convex polygon with counter-clockwise vertices.

    Rectangles produced by :func:`rectangle_polygon` start at the local
    bottom-left vertex and continue counter-clockwise before rotation.
    """

    points: tuple[Point, ...]

    def __post_init__(self) -> None:
        points = tuple(self.points)
        if len(points) < 3:
            raise GeometryValidationError("polygon must contain at least three points")
        if any(not isinstance(point, Point) for point in points):
            raise GeometryValidationError("polygon points must be Point instances")
        if _signed_area_twice(points) <= 0:
            raise GeometryValidationError(
                "polygon vertices must be non-degenerate and counter-clockwise"
            )

        turn_direction = 0
        for index in range(len(points)):
            turn = _cross(
                points[index],
                points[(index + 1) % len(points)],
                points[(index + 2) % len(points)],
            )
            if abs(turn) <= DEFAULT_TOLERANCE_MM**2:
                continue
            current_direction = 1 if turn > 0 else -1
            if turn_direction and current_direction != turn_direction:
                raise GeometryValidationError("polygon must be convex")
            turn_direction = current_direction
        if turn_direction <= 0:
            raise GeometryValidationError("polygon must be convex and counter-clockwise")
        object.__setattr__(self, "points", points)

    def __iter__(self):
        return iter(self.points)

    def __len__(self) -> int:
        return len(self.points)


@dataclass(frozen=True)
class SlotGeometry:
    """Canonical persisted geometry required to derive a V2 slot footprint."""

    center: Point
    trim_size: Size
    bleed: float
    rotation_deg: float

    def __post_init__(self) -> None:
        if not isinstance(self.center, Point):
            raise GeometryValidationError("center must be a Point")
        if not isinstance(self.trim_size, Size):
            raise GeometryValidationError("trim_size must be a Size")
        object.__setattr__(self, "bleed", validate_non_negative(self.bleed, "bleed"))
        object.__setattr__(
            self,
            "rotation_deg",
            validate_cardinal_rotation(self.rotation_deg),
        )


def _require_point(value: object, name: str) -> Point:
    if not isinstance(value, Point):
        raise GeometryValidationError(f"{name} must be a Point")
    return value


def _require_size(value: object, name: str) -> Size:
    if not isinstance(value, Size):
        raise GeometryValidationError(f"{name} must be a Size")
    return value


def _require_bounds(value: object, name: str) -> Bounds:
    if not isinstance(value, Bounds):
        raise GeometryValidationError(f"{name} must be Bounds")
    return value


def _require_polygon(value: object, name: str) -> Polygon:
    if not isinstance(value, Polygon):
        raise GeometryValidationError(f"{name} must be a Polygon")
    return value


def _require_slot(value: object, name: str) -> SlotGeometry:
    if not isinstance(value, SlotGeometry):
        raise GeometryValidationError(f"{name} must be SlotGeometry")
    return value


def productive_size(trim_size: Size, bleed: object) -> Size:
    """Return the unrotated trim size expanded by uniform bleed."""

    size = _require_size(trim_size, "trim_size")
    bleed_value = validate_non_negative(bleed, "bleed")
    return Size(
        size.width + 2.0 * bleed_value,
        size.height + 2.0 * bleed_value,
    )


def oriented_size(size: Size, rotation_deg: object) -> Size:
    """Return the cardinal axis-aligned size without mutating persisted size."""

    source = _require_size(size, "size")
    rotation = validate_cardinal_rotation(rotation_deg)
    if rotation in (90.0, 270.0):
        return Size(source.height, source.width)
    return Size(source.width, source.height)


def rotate_point(point: Point, pivot: Point, rotation_deg: object) -> Point:
    """Rotate *point* counter-clockwise around *pivot* by a cardinal angle."""

    source = _require_point(point, "point")
    center = _require_point(pivot, "pivot")
    rotation = validate_cardinal_rotation(rotation_deg)
    dx = source.x - center.x
    dy = source.y - center.y

    if rotation == 0.0:
        rotated_x, rotated_y = dx, dy
    elif rotation == 90.0:
        rotated_x, rotated_y = -dy, dx
    elif rotation == 180.0:
        rotated_x, rotated_y = -dx, -dy
    else:
        rotated_x, rotated_y = dy, -dx
    return Point(center.x + rotated_x, center.y + rotated_y)


def rectangle_polygon(center: Point, size: Size, rotation_deg: object) -> Polygon:
    """Return a cardinally rotated rectangle in stable counter-clockwise order."""

    rectangle_center = _require_point(center, "center")
    rectangle_size = _require_size(size, "size")
    rotation = validate_cardinal_rotation(rotation_deg)
    half_width = rectangle_size.width / 2.0
    half_height = rectangle_size.height / 2.0
    local_points = (
        Point(rectangle_center.x - half_width, rectangle_center.y - half_height),
        Point(rectangle_center.x + half_width, rectangle_center.y - half_height),
        Point(rectangle_center.x + half_width, rectangle_center.y + half_height),
        Point(rectangle_center.x - half_width, rectangle_center.y + half_height),
    )
    return Polygon(
        tuple(rotate_point(point, rectangle_center, rotation) for point in local_points)
    )


def trim_polygon(slot_geometry: SlotGeometry) -> Polygon:
    """Return the rotated trim polygon for a slot."""

    slot = _require_slot(slot_geometry, "slot_geometry")
    return rectangle_polygon(slot.center, slot.trim_size, slot.rotation_deg)


def bleed_polygon(slot_geometry: SlotGeometry) -> Polygon:
    """Return the rotated productive polygon, including uniform bleed."""

    slot = _require_slot(slot_geometry, "slot_geometry")
    return rectangle_polygon(
        slot.center,
        productive_size(slot.trim_size, slot.bleed),
        slot.rotation_deg,
    )


def translate_polygon(polygon: Polygon, dx: object, dy: object) -> Polygon:
    """Return a translated polygon without changing the source polygon."""

    source = _require_polygon(polygon, "polygon")
    offset_x = validate_finite(dx, "dx")
    offset_y = validate_finite(dy, "dy")
    return Polygon(
        tuple(Point(point.x + offset_x, point.y + offset_y) for point in source)
    )


def polygon_bounds(polygon: Polygon) -> Bounds:
    """Return the axis-aligned bounds of a polygon."""

    source = _require_polygon(polygon, "polygon")
    x_values = [point.x for point in source]
    y_values = [point.y for point in source]
    return Bounds(
        left=min(x_values),
        right=max(x_values),
        bottom=min(y_values),
        top=max(y_values),
    )


def center_to_trim_bounds(
    center: Point,
    trim_size: Size,
    rotation_deg: object,
) -> Bounds:
    """Convert a trim centre and unrotated trim size to trim bounds."""

    return polygon_bounds(rectangle_polygon(center, trim_size, rotation_deg))


def center_to_bleed_bounds(
    center: Point,
    trim_size: Size,
    bleed: object,
    rotation_deg: object,
) -> Bounds:
    """Convert a trim centre to productive axis-aligned bounds."""

    return polygon_bounds(
        rectangle_polygon(center, productive_size(trim_size, bleed), rotation_deg)
    )


def trim_bounds(slot_geometry: SlotGeometry) -> Bounds:
    """Return the axis-aligned trim bounds for a slot."""

    slot = _require_slot(slot_geometry, "slot_geometry")
    return center_to_trim_bounds(slot.center, slot.trim_size, slot.rotation_deg)


def bleed_bounds(slot_geometry: SlotGeometry) -> Bounds:
    """Return the axis-aligned productive bounds for a slot."""

    slot = _require_slot(slot_geometry, "slot_geometry")
    return center_to_bleed_bounds(
        slot.center,
        slot.trim_size,
        slot.bleed,
        slot.rotation_deg,
    )


def sheet_bounds(sheet_size: Size) -> Bounds:
    """Return sheet bounds for a bottom-left origin."""

    size = _require_size(sheet_size, "sheet_size")
    return Bounds(0.0, size.width, 0.0, size.height)


def _point_on_segment(
    point: Point,
    start: Point,
    end: Point,
    tolerance_mm: float,
) -> bool:
    dx = end.x - start.x
    dy = end.y - start.y
    segment_length = math.hypot(dx, dy)
    cross_product = (point.x - start.x) * dy - (point.y - start.y) * dx
    if abs(cross_product) > tolerance_mm * max(1.0, segment_length):
        return False
    return (
        min(start.x, end.x) - tolerance_mm
        <= point.x
        <= max(start.x, end.x) + tolerance_mm
        and min(start.y, end.y) - tolerance_mm
        <= point.y
        <= max(start.y, end.y) + tolerance_mm
    )


def point_in_polygon(
    point: Point,
    polygon: Polygon,
    tolerance_mm: object = DEFAULT_TOLERANCE_MM,
) -> bool:
    """Return whether a point is inside or on the boundary of a polygon."""

    target = _require_point(point, "point")
    source = _require_polygon(polygon, "polygon")
    tolerance = _validate_tolerance(tolerance_mm)
    inside = False
    previous = source.points[-1]
    for current in source.points:
        if _point_on_segment(target, previous, current, tolerance):
            return True
        if (current.y > target.y) != (previous.y > target.y):
            crossing_x = (previous.x - current.x) * (
                target.y - current.y
            ) / (previous.y - current.y) + current.x
            if target.x < crossing_x:
                inside = not inside
        previous = current
    return inside


def polygon_within_bounds(
    polygon: Polygon,
    bounds: Bounds,
    tolerance_mm: object = DEFAULT_TOLERANCE_MM,
) -> bool:
    """Return whether every polygon vertex is inside axis-aligned bounds."""

    source = _require_polygon(polygon, "polygon")
    container = _require_bounds(bounds, "bounds")
    tolerance = _validate_tolerance(tolerance_mm)
    return all(
        container.left - tolerance <= point.x <= container.right + tolerance
        and container.bottom - tolerance <= point.y <= container.top + tolerance
        for point in source
    )


def slot_within_sheet(
    slot_geometry: SlotGeometry,
    sheet_size: Size,
    *,
    use_bleed: bool = True,
    tolerance_mm: object = DEFAULT_TOLERANCE_MM,
) -> bool:
    """Validate a slot against the sheet, using productive bleed by default."""

    slot = _require_slot(slot_geometry, "slot_geometry")
    if not isinstance(use_bleed, bool):
        raise GeometryValidationError("use_bleed must be a boolean")
    polygon = bleed_polygon(slot) if use_bleed else trim_polygon(slot)
    return polygon_within_bounds(polygon, sheet_bounds(sheet_size), tolerance_mm)


def _polygon_axes(polygon: Polygon) -> Iterable[tuple[float, float]]:
    points = polygon.points
    for start, end in zip(points, points[1:] + points[:1]):
        edge_x = end.x - start.x
        edge_y = end.y - start.y
        length = math.hypot(edge_x, edge_y)
        if length <= DEFAULT_TOLERANCE_MM:
            continue
        yield (-edge_y / length, edge_x / length)


def _project_polygon(
    polygon: Polygon,
    axis: tuple[float, float],
) -> tuple[float, float]:
    axis_x, axis_y = axis
    projections = [point.x * axis_x + point.y * axis_y for point in polygon]
    return min(projections), max(projections)


def polygons_intersect(
    polygon_a: Polygon,
    polygon_b: Polygon,
    tolerance_mm: object = DEFAULT_TOLERANCE_MM,
) -> bool:
    """Return whether two convex polygons overlap with positive area.

    The Separating Axis Theorem is used. Edge or vertex contact is not overlap.
    A penetration no larger than ``tolerance_mm`` is treated as numerical
    contact, not as productive overlap.
    """

    first = _require_polygon(polygon_a, "polygon_a")
    second = _require_polygon(polygon_b, "polygon_b")
    tolerance = _validate_tolerance(tolerance_mm)
    axes = tuple(_polygon_axes(first)) + tuple(_polygon_axes(second))
    if not axes:
        raise GeometryValidationError("polygons do not contain usable edges")

    for axis in axes:
        first_min, first_max = _project_polygon(first, axis)
        second_min, second_max = _project_polygon(second, axis)
        overlap = min(first_max, second_max) - max(first_min, second_min)
        if overlap <= tolerance:
            return False
    return True


def slots_overlap(
    slot_a: SlotGeometry,
    slot_b: SlotGeometry,
    *,
    use_bleed: bool = True,
    tolerance_mm: object = DEFAULT_TOLERANCE_MM,
) -> bool:
    """Return whether two slots overlap, including bleed by default."""

    first = _require_slot(slot_a, "slot_a")
    second = _require_slot(slot_b, "slot_b")
    if not isinstance(use_bleed, bool):
        raise GeometryValidationError("use_bleed must be a boolean")
    first_polygon = bleed_polygon(first) if use_bleed else trim_polygon(first)
    second_polygon = bleed_polygon(second) if use_bleed else trim_polygon(second)
    return polygons_intersect(first_polygon, second_polygon, tolerance_mm)


def horizontal_gap(bounds_a: Bounds, bounds_b: Bounds) -> float:
    """Return signed horizontal separation: positive gap, zero contact, negative overlap."""

    first = _require_bounds(bounds_a, "bounds_a")
    second = _require_bounds(bounds_b, "bounds_b")
    if first.right <= second.left:
        return second.left - first.right
    if second.right <= first.left:
        return first.left - second.right
    return -(min(first.right, second.right) - max(first.left, second.left))


def vertical_gap(bounds_a: Bounds, bounds_b: Bounds) -> float:
    """Return signed vertical separation: positive gap, zero contact, negative overlap."""

    first = _require_bounds(bounds_a, "bounds_a")
    second = _require_bounds(bounds_b, "bounds_b")
    if first.top <= second.bottom:
        return second.bottom - first.top
    if second.top <= first.bottom:
        return first.bottom - second.top
    return -(min(first.top, second.top) - max(first.bottom, second.bottom))


def distance_between_bounds(bounds_a: Bounds, bounds_b: Bounds) -> float:
    """Return the minimum Euclidean distance between two axis-aligned bounds."""

    gap_x = max(horizontal_gap(bounds_a, bounds_b), 0.0)
    gap_y = max(vertical_gap(bounds_a, bounds_b), 0.0)
    return math.hypot(gap_x, gap_y)


__all__ = [
    "DEFAULT_TOLERANCE_MM",
    "GeometryValidationError",
    "Point",
    "Size",
    "Bounds",
    "Polygon",
    "SlotGeometry",
    "is_finite_number",
    "validate_finite",
    "validate_positive",
    "validate_non_negative",
    "validate_cardinal_rotation",
    "productive_size",
    "oriented_size",
    "rotate_point",
    "rectangle_polygon",
    "trim_polygon",
    "bleed_polygon",
    "translate_polygon",
    "polygon_bounds",
    "trim_bounds",
    "bleed_bounds",
    "center_to_trim_bounds",
    "center_to_bleed_bounds",
    "sheet_bounds",
    "point_in_polygon",
    "polygon_within_bounds",
    "slot_within_sheet",
    "polygons_intersect",
    "slots_overlap",
    "horizontal_gap",
    "vertical_gap",
    "distance_between_bounds",
]
