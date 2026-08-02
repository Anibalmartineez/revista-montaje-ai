(function (root, factory) {
  "use strict";
  const kernel = typeof module === "object" && module.exports
    ? require("./geometry_kernel.js")
    : root.EditorOffsetV2?.GeometryKernel;
  const api = factory(kernel);
  if (typeof module === "object" && module.exports) module.exports = api;
  root.EditorOffsetV2 = root.EditorOffsetV2 || {};
  root.EditorOffsetV2.GeometryView = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function (Kernel) {
  "use strict";

  if (!Kernel) throw new Error("Editor V2 geometry kernel is required");

  const MIN_ZOOM = 0.35;
  const MAX_ZOOM = 4;

  function printableBounds(sheet) {
    const size = sheet?.size_mm || {};
    const margins = sheet?.printable_margins_mm || {};
    const width = Kernel.positiveNumber(size.width, "sheet width");
    const height = Kernel.positiveNumber(size.height, "sheet height");
    const left = Kernel.nonNegativeNumber(margins.left, "printable left");
    const rightMargin = Kernel.nonNegativeNumber(margins.right, "printable right");
    const bottom = Kernel.nonNegativeNumber(margins.bottom, "printable bottom");
    const topMargin = Kernel.nonNegativeNumber(margins.top, "printable top");
    return Kernel.bounds({
      left,
      right: width - rightMargin,
      bottom,
      top: height - topMargin,
    });
  }

  function isWithinSheet(slot, sheetSize, useBleed) {
    const container = Kernel.bounds({
      left: 0,
      right: Kernel.positiveNumber(sheetSize.width, "sheet width"),
      bottom: 0,
      top: Kernel.positiveNumber(sheetSize.height, "sheet height"),
    });
    return Kernel.containsBounds(
      container,
      useBleed === false ? Kernel.trimBounds(slot) : Kernel.bleedBounds(slot),
    );
  }

  function boundsWithin(candidate, container) {
    return Kernel.containsBounds(container, candidate);
  }

  function classifySlotPlacement(slot, sheet) {
    const productive = Kernel.bleedBounds(slot);
    const sheetBounds = Kernel.bounds({
      left: 0,
      right: sheet.size_mm.width,
      bottom: 0,
      top: sheet.size_mm.height,
    });
    if (!Kernel.containsBounds(sheetBounds, productive)) return "outside_sheet";
    if (!Kernel.containsBounds(printableBounds(sheet), productive)) return "outside_printable";
    return "inside";
  }

  function mmToSvgX(xMm) {
    return Kernel.finiteNumber(xMm, "x_mm");
  }

  function mmToSvgY(yMm, sheetHeightMm) {
    return Kernel.finiteNumber(sheetHeightMm, "sheet height")
      - Kernel.finiteNumber(yMm, "y_mm");
  }

  function svgToMmX(svgX) {
    return Kernel.finiteNumber(svgX, "svg x");
  }

  function svgToMmY(svgY, sheetHeightMm) {
    return Kernel.finiteNumber(sheetHeightMm, "sheet height")
      - Kernel.finiteNumber(svgY, "svg y");
  }

  function clampZoom(value) {
    return Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, Kernel.finiteNumber(value, "zoom")));
  }

  return Object.freeze({
    ...Kernel,
    MIN_ZOOM,
    MAX_ZOOM,
    printableBounds,
    isWithinSheet,
    boundsWithin,
    classifySlotPlacement,
    mmToSvgX,
    mmToSvgY,
    svgToMmX,
    svgToMmY,
    clampZoom,
  });
});
