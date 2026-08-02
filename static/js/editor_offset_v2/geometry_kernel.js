(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.EditorOffsetV2 = root.EditorOffsetV2 || {};
  root.EditorOffsetV2.GeometryKernel = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const DEFAULT_TOLERANCE_MM = 1e-9;
  const CARDINAL_ROTATIONS = Object.freeze([0, 90, 180, 270]);

  function finiteNumber(value, name) {
    if (typeof value !== "number" || !Number.isFinite(value)) {
      throw new TypeError(`${name || "value"} must be a finite number`);
    }
    return value;
  }

  function positiveNumber(value, name) {
    const result = finiteNumber(value, name);
    if (result <= 0) throw new RangeError(`${name || "value"} must be greater than zero`);
    return result;
  }

  function nonNegativeNumber(value, name) {
    const result = finiteNumber(value, name);
    if (result < 0) throw new RangeError(`${name || "value"} must be zero or greater`);
    return result;
  }

  function tolerance(value) {
    return nonNegativeNumber(value === undefined ? DEFAULT_TOLERANCE_MM : value, "tolerance_mm");
  }

  function point(value, name) {
    const source = value || {};
    return Object.freeze({
      x: finiteNumber(source.x, `${name || "point"}.x`),
      y: finiteNumber(source.y, `${name || "point"}.y`),
    });
  }

  function size(value, name) {
    const source = value || {};
    return Object.freeze({
      width: positiveNumber(source.width, `${name || "size"}.width`),
      height: positiveNumber(source.height, `${name || "size"}.height`),
    });
  }

  function bounds(value, name) {
    const source = value || {};
    const result = {
      left: finiteNumber(source.left, `${name || "bounds"}.left`),
      right: finiteNumber(source.right, `${name || "bounds"}.right`),
      bottom: finiteNumber(source.bottom, `${name || "bounds"}.bottom`),
      top: finiteNumber(source.top, `${name || "bounds"}.top`),
    };
    if (result.right < result.left) throw new RangeError("right must be greater than or equal to left");
    if (result.top < result.bottom) throw new RangeError("top must be greater than or equal to bottom");
    result.width = result.right - result.left;
    result.height = result.top - result.bottom;
    return Object.freeze(result);
  }

  function cardinalRotation(value) {
    const rotation = finiteNumber(value, "rotation_deg");
    if (!CARDINAL_ROTATIONS.includes(rotation)) {
      throw new RangeError("rotation_deg must be 0, 90, 180 or 270");
    }
    return rotation;
  }

  function productiveSize(trimSize, bleed) {
    const trim = size(trimSize, "trim_size");
    const safeBleed = nonNegativeNumber(bleed, "bleed");
    return Object.freeze({
      width: trim.width + 2 * safeBleed,
      height: trim.height + 2 * safeBleed,
    });
  }

  function orientedSize(sourceSize, rotationDeg) {
    const source = size(sourceSize, "size");
    const rotation = cardinalRotation(rotationDeg);
    return rotation === 90 || rotation === 270
      ? Object.freeze({ width: source.height, height: source.width })
      : Object.freeze({ width: source.width, height: source.height });
  }

  function rotatePoint(sourcePoint, pivotPoint, rotationDeg) {
    const source = point(sourcePoint, "point");
    const pivot = point(pivotPoint, "pivot");
    const rotation = cardinalRotation(rotationDeg);
    const dx = source.x - pivot.x;
    const dy = source.y - pivot.y;
    let x = dx;
    let y = dy;
    if (rotation === 90) [x, y] = [-dy, dx];
    else if (rotation === 180) [x, y] = [-dx, -dy];
    else if (rotation === 270) [x, y] = [dy, -dx];
    return Object.freeze({ x: pivot.x + x, y: pivot.y + y });
  }

  function rectanglePolygon(centerPoint, rectangleSize, rotationDeg) {
    const center = point(centerPoint, "center");
    const dimensions = size(rectangleSize, "size");
    const rotation = cardinalRotation(rotationDeg);
    const halfWidth = dimensions.width / 2;
    const halfHeight = dimensions.height / 2;
    return Object.freeze([
      { x: center.x - halfWidth, y: center.y - halfHeight },
      { x: center.x + halfWidth, y: center.y - halfHeight },
      { x: center.x + halfWidth, y: center.y + halfHeight },
      { x: center.x - halfWidth, y: center.y + halfHeight },
    ].map((item) => rotatePoint(item, center, rotation)));
  }

  function slotGeometry(slotOrGeometry) {
    const geometry = slotOrGeometry?.geometry || slotOrGeometry || {};
    return Object.freeze({
      center: point({
        x: geometry.position_mm?.x_mm,
        y: geometry.position_mm?.y_mm,
      }, "center"),
      trimSize: size(geometry.trim_size_mm, "trim_size"),
      bleed: nonNegativeNumber(geometry.bleed_mm, "bleed"),
      rotation: cardinalRotation(geometry.rotation_deg),
    });
  }

  function trimPolygon(slotOrGeometry) {
    const geometry = slotGeometry(slotOrGeometry);
    return rectanglePolygon(geometry.center, geometry.trimSize, geometry.rotation);
  }

  function bleedPolygon(slotOrGeometry) {
    const geometry = slotGeometry(slotOrGeometry);
    return rectanglePolygon(
      geometry.center,
      productiveSize(geometry.trimSize, geometry.bleed),
      geometry.rotation,
    );
  }

  function translatePolygon(polygon, dx, dy) {
    const offsetX = finiteNumber(dx, "dx");
    const offsetY = finiteNumber(dy, "dy");
    return Object.freeze((polygon || []).map((item) => {
      const source = point(item, "polygon point");
      return Object.freeze({ x: source.x + offsetX, y: source.y + offsetY });
    }));
  }

  function polygonBounds(polygon) {
    if (!Array.isArray(polygon) || polygon.length < 3) {
      throw new TypeError("polygon must contain at least three points");
    }
    const points = polygon.map((item) => point(item, "polygon point"));
    return bounds({
      left: Math.min(...points.map((item) => item.x)),
      right: Math.max(...points.map((item) => item.x)),
      bottom: Math.min(...points.map((item) => item.y)),
      top: Math.max(...points.map((item) => item.y)),
    });
  }

  function boundsForGeometry(geometry, useBleed) {
    return polygonBounds(useBleed ? bleedPolygon(geometry) : trimPolygon(geometry));
  }

  function trimBounds(slot) {
    return boundsForGeometry(slot, false);
  }

  function bleedBounds(slot) {
    return boundsForGeometry(slot, true);
  }

  function boundsUnion(boundsList) {
    if (!Array.isArray(boundsList) || !boundsList.length) return null;
    const items = boundsList.map((item) => bounds(item));
    return bounds({
      left: Math.min(...items.map((item) => item.left)),
      right: Math.max(...items.map((item) => item.right)),
      bottom: Math.min(...items.map((item) => item.bottom)),
      top: Math.max(...items.map((item) => item.top)),
    });
  }

  function boundsCenter(value) {
    const item = bounds(value);
    return Object.freeze({
      x: item.left + item.width / 2,
      y: item.bottom + item.height / 2,
    });
  }

  function containsPoint(containerValue, targetValue, toleranceMm) {
    const container = bounds(containerValue, "container");
    const target = point(targetValue, "point");
    const epsilon = tolerance(toleranceMm);
    return target.x >= container.left - epsilon
      && target.x <= container.right + epsilon
      && target.y >= container.bottom - epsilon
      && target.y <= container.top + epsilon;
  }

  function containsBounds(containerValue, candidateValue, toleranceMm) {
    const container = bounds(containerValue, "container");
    const candidate = bounds(candidateValue, "candidate");
    const epsilon = tolerance(toleranceMm);
    return candidate.left >= container.left - epsilon
      && candidate.right <= container.right + epsilon
      && candidate.bottom >= container.bottom - epsilon
      && candidate.top <= container.top + epsilon;
  }

  function intersectsBounds(leftValue, rightValue, includeContact, toleranceMm) {
    const left = bounds(leftValue, "left bounds");
    const right = bounds(rightValue, "right bounds");
    const epsilon = tolerance(toleranceMm);
    const overlapX = Math.min(left.right, right.right) - Math.max(left.left, right.left);
    const overlapY = Math.min(left.top, right.top) - Math.max(left.bottom, right.bottom);
    return includeContact === false
      ? overlapX > epsilon && overlapY > epsilon
      : overlapX >= -epsilon && overlapY >= -epsilon;
  }

  function pointOnSegment(target, start, end, toleranceMm) {
    const dx = end.x - start.x;
    const dy = end.y - start.y;
    const length = Math.hypot(dx, dy);
    const cross = (target.x - start.x) * dy - (target.y - start.y) * dx;
    if (Math.abs(cross) > toleranceMm * Math.max(1, length)) return false;
    return target.x >= Math.min(start.x, end.x) - toleranceMm
      && target.x <= Math.max(start.x, end.x) + toleranceMm
      && target.y >= Math.min(start.y, end.y) - toleranceMm
      && target.y <= Math.max(start.y, end.y) + toleranceMm;
  }

  function pointInPolygon(targetValue, polygon, toleranceMm) {
    const target = point(targetValue, "point");
    const points = (polygon || []).map((item) => point(item, "polygon point"));
    if (points.length < 3) throw new TypeError("polygon must contain at least three points");
    const epsilon = tolerance(toleranceMm);
    let inside = false;
    let previous = points[points.length - 1];
    for (const current of points) {
      if (pointOnSegment(target, previous, current, epsilon)) return true;
      if ((current.y > target.y) !== (previous.y > target.y)) {
        const crossingX = (previous.x - current.x) * (target.y - current.y)
          / (previous.y - current.y) + current.x;
        if (target.x < crossingX) inside = !inside;
      }
      previous = current;
    }
    return inside;
  }

  function polygonWithinBounds(polygon, containerValue, toleranceMm) {
    const container = bounds(containerValue, "container");
    return (polygon || []).every((item) => containsPoint(container, item, toleranceMm));
  }

  function polygonAxes(polygon) {
    const points = (polygon || []).map((item) => point(item, "polygon point"));
    const axes = [];
    for (let index = 0; index < points.length; index += 1) {
      const start = points[index];
      const end = points[(index + 1) % points.length];
      const edgeX = end.x - start.x;
      const edgeY = end.y - start.y;
      const length = Math.hypot(edgeX, edgeY);
      if (length <= DEFAULT_TOLERANCE_MM) continue;
      axes.push(Object.freeze({ x: -edgeY / length, y: edgeX / length }));
    }
    return Object.freeze(axes);
  }

  function projectPolygon(polygon, axisValue) {
    const axis = point(axisValue, "axis");
    const values = (polygon || []).map((item) => {
      const source = point(item, "polygon point");
      return source.x * axis.x + source.y * axis.y;
    });
    if (!values.length) throw new TypeError("polygon must contain points");
    return Object.freeze({ min: Math.min(...values), max: Math.max(...values) });
  }

  function polygonsIntersect(first, second, toleranceMm) {
    const epsilon = tolerance(toleranceMm);
    const axes = [...polygonAxes(first), ...polygonAxes(second)];
    if (!axes.length) throw new TypeError("polygons do not contain usable edges");
    return axes.every((axis) => {
      const left = projectPolygon(first, axis);
      const right = projectPolygon(second, axis);
      return Math.min(left.max, right.max) - Math.max(left.min, right.min) > epsilon;
    });
  }

  function slotsOverlap(first, second, useBleed, toleranceMm) {
    const productive = useBleed !== false;
    return polygonsIntersect(
      productive ? bleedPolygon(first) : trimPolygon(first),
      productive ? bleedPolygon(second) : trimPolygon(second),
      toleranceMm,
    );
  }

  function horizontalGap(firstValue, secondValue) {
    const first = bounds(firstValue, "first bounds");
    const second = bounds(secondValue, "second bounds");
    if (first.right <= second.left) return second.left - first.right;
    if (second.right <= first.left) return first.left - second.right;
    return -(Math.min(first.right, second.right) - Math.max(first.left, second.left));
  }

  function verticalGap(firstValue, secondValue) {
    const first = bounds(firstValue, "first bounds");
    const second = bounds(secondValue, "second bounds");
    if (first.top <= second.bottom) return second.bottom - first.top;
    if (second.top <= first.bottom) return first.bottom - second.top;
    return -(Math.min(first.top, second.top) - Math.max(first.bottom, second.bottom));
  }

  function distanceBetweenBounds(first, second) {
    return Math.hypot(
      Math.max(horizontalGap(first, second), 0),
      Math.max(verticalGap(first, second), 0),
    );
  }

  function distanceBetweenPoints(firstValue, secondValue) {
    const first = point(firstValue, "first point");
    const second = point(secondValue, "second point");
    return Math.hypot(second.x - first.x, second.y - first.y);
  }

  function approximatelyEqual(left, right, toleranceMm) {
    return Math.abs(finiteNumber(left, "left") - finiteNumber(right, "right"))
      <= tolerance(toleranceMm);
  }

  return Object.freeze({
    DEFAULT_TOLERANCE_MM,
    CARDINAL_ROTATIONS,
    finiteNumber,
    positiveNumber,
    nonNegativeNumber,
    cardinalRotation,
    point,
    size,
    bounds,
    productiveSize,
    orientedSize,
    rotatePoint,
    rectanglePolygon,
    trimPolygon,
    bleedPolygon,
    translatePolygon,
    polygonBounds,
    boundsForGeometry,
    trimBounds,
    bleedBounds,
    boundsUnion,
    aggregateBounds: boundsUnion,
    boundsCenter,
    containsPoint,
    containsBounds,
    intersectsBounds,
    pointInPolygon,
    polygonWithinBounds,
    polygonAxes,
    projectPolygon,
    polygonsIntersect,
    slotsOverlap,
    horizontalGap,
    verticalGap,
    distanceBetweenBounds,
    distanceBetweenPoints,
    approximatelyEqual,
  });
});
