(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  }
  root.EditorOffsetV2 = root.EditorOffsetV2 || {};
  root.EditorOffsetV2.GeometryView = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const CARDINAL_ROTATIONS = Object.freeze([0, 90, 180, 270]);
  const MIN_ZOOM = 0.35;
  const MAX_ZOOM = 4;

  function finiteNumber(value, name) {
    if (typeof value !== "number" || !Number.isFinite(value)) {
      throw new TypeError(`${name || "value"} must be a finite number`);
    }
    return value;
  }

  function cardinalRotation(value) {
    finiteNumber(value, "rotation_deg");
    if (!CARDINAL_ROTATIONS.includes(value)) {
      throw new RangeError("rotation_deg must be 0, 90, 180 or 270");
    }
    return value;
  }

  function productiveSize(trimSize, bleed) {
    const width = finiteNumber(trimSize.width, "trim width");
    const height = finiteNumber(trimSize.height, "trim height");
    const safeBleed = finiteNumber(bleed, "bleed");
    if (width <= 0 || height <= 0 || safeBleed < 0) {
      throw new RangeError("trim must be positive and bleed non-negative");
    }
    return {
      width: width + 2 * safeBleed,
      height: height + 2 * safeBleed,
    };
  }

  function orientedSize(size, rotationDeg) {
    const rotation = cardinalRotation(rotationDeg);
    if (rotation === 90 || rotation === 270) {
      return { width: size.height, height: size.width };
    }
    return { width: size.width, height: size.height };
  }

  function boundsForGeometry(geometry, useBleed) {
    const center = geometry.position_mm;
    const trim = geometry.trim_size_mm;
    const size = useBleed ? productiveSize(trim, geometry.bleed_mm) : trim;
    const oriented = orientedSize(size, geometry.rotation_deg);
    const x = finiteNumber(center.x_mm, "center x");
    const y = finiteNumber(center.y_mm, "center y");
    return {
      left: x - oriented.width / 2,
      right: x + oriented.width / 2,
      bottom: y - oriented.height / 2,
      top: y + oriented.height / 2,
      width: oriented.width,
      height: oriented.height,
    };
  }

  function trimBounds(slot) {
    return boundsForGeometry(slot.geometry, false);
  }

  function bleedBounds(slot) {
    return boundsForGeometry(slot.geometry, true);
  }

  function boundsUnion(boundsList) {
    if (!boundsList.length) {
      return null;
    }
    const left = Math.min(...boundsList.map((item) => item.left));
    const right = Math.max(...boundsList.map((item) => item.right));
    const bottom = Math.min(...boundsList.map((item) => item.bottom));
    const top = Math.max(...boundsList.map((item) => item.top));
    return { left, right, bottom, top, width: right - left, height: top - bottom };
  }

  function isWithinSheet(slot, sheetSize, useBleed) {
    const bounds = useBleed === false ? trimBounds(slot) : bleedBounds(slot);
    return bounds.left >= 0
      && bounds.bottom >= 0
      && bounds.right <= sheetSize.width
      && bounds.top <= sheetSize.height;
  }

  function mmToSvgX(xMm) {
    return finiteNumber(xMm, "x_mm");
  }

  function mmToSvgY(yMm, sheetHeightMm) {
    return finiteNumber(sheetHeightMm, "sheet height") - finiteNumber(yMm, "y_mm");
  }

  function svgToMmX(svgX) {
    return finiteNumber(svgX, "svg x");
  }

  function svgToMmY(svgY, sheetHeightMm) {
    return finiteNumber(sheetHeightMm, "sheet height") - finiteNumber(svgY, "svg y");
  }

  function clampZoom(value) {
    return Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, finiteNumber(value, "zoom")));
  }

  return Object.freeze({
    CARDINAL_ROTATIONS,
    MIN_ZOOM,
    MAX_ZOOM,
    finiteNumber,
    cardinalRotation,
    productiveSize,
    orientedSize,
    boundsForGeometry,
    trimBounds,
    bleedBounds,
    boundsUnion,
    isWithinSheet,
    mmToSvgX,
    mmToSvgY,
    svgToMmX,
    svgToMmY,
    clampZoom,
  });
});
