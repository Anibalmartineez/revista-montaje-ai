(function (root, factory) {
  "use strict";
  const kernel = typeof module === "object" && module.exports
    ? require("./geometry_kernel.js")
    : root.EditorOffsetV2?.GeometryKernel;
  const api = factory(kernel);
  if (typeof module === "object" && module.exports) module.exports = api;
  root.EditorOffsetV2 = root.EditorOffsetV2 || {};
  root.EditorOffsetV2.PrecisionTools = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function (Geometry) {
  "use strict";

  if (!Geometry) throw new Error("Editor V2 geometry kernel is required");

  const RULER_STEPS_MM = Object.freeze([0.1, 0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500]);
  const MAX_RULER_TICKS = 400;
  const GUIDE_AXES = Object.freeze(["x", "y"]);
  const DECIMAL_PATTERN = /^[+-]?(?:\d+(?:[.,]\d*)?|[.,]\d+)$/;

  function parseMillimetres(rawValue) {
    const text = String(rawValue ?? "").trim();
    if (!text || !DECIMAL_PATTERN.test(text)) {
      return Object.freeze({ ok: false, value: null, error: "Introduce milímetros finitos usando punto o coma." });
    }
    const value = Number(text.replace(",", "."));
    if (!Number.isFinite(value)) {
      return Object.freeze({ ok: false, value: null, error: "Introduce milímetros finitos usando punto o coma." });
    }
    return Object.freeze({ ok: true, value, error: null });
  }

  function formatMillimetres(value, digits) {
    const safe = Geometry.finiteNumber(value, "millimetres");
    const precision = Number.isInteger(digits) ? digits : 3;
    return safe.toFixed(precision).replace(/(?:\.0+|(?:(\.\d*?)0+))$/, "$1");
  }

  function chooseRulerStep(pixelsPerMm, minimumMajorPixels) {
    const scale = Geometry.positiveNumber(pixelsPerMm, "pixels_per_mm");
    const minimum = Geometry.positiveNumber(minimumMajorPixels ?? 64, "minimum_major_pixels");
    return RULER_STEPS_MM.find((step) => step * scale >= minimum)
      || RULER_STEPS_MM[RULER_STEPS_MM.length - 1];
  }

  function decimalPlaces(value) {
    if (value >= 1) return 0;
    if (value >= 0.1) return 1;
    return 2;
  }

  function rulerTicks(options) {
    let start = Geometry.finiteNumber(options?.start, "ruler start");
    let end = Geometry.finiteNumber(options?.end, "ruler end");
    if (end < start) [start, end] = [end, start];
    const pixelsPerMm = Geometry.positiveNumber(options?.pixelsPerMm, "pixels_per_mm");
    const maxTicks = Number.isInteger(options?.maxTicks) && options.maxTicks > 0
      ? options.maxTicks : MAX_RULER_TICKS;
    let majorStep = chooseRulerStep(pixelsPerMm, options?.minimumMajorPixels);
    let minorStep = majorStep / 5;
    if (minorStep * pixelsPerMm < 8) minorStep = majorStep / 2;
    if (minorStep * pixelsPerMm < 5) minorStep = majorStep;
    while (Math.ceil((end - start) / minorStep) + 2 > maxTicks) {
      const next = RULER_STEPS_MM.find((step) => step > majorStep);
      majorStep = next || majorStep * 2;
      minorStep = majorStep / 5;
    }
    const firstIndex = Math.ceil((start - Geometry.DEFAULT_TOLERANCE_MM) / minorStep);
    const lastIndex = Math.floor((end + Geometry.DEFAULT_TOLERANCE_MM) / minorStep);
    const majorEvery = Math.max(1, Math.round(majorStep / minorStep));
    const ticks = [];
    for (let index = firstIndex; index <= lastIndex && ticks.length < maxTicks; index += 1) {
      const value = Number((index * minorStep).toFixed(10));
      const major = ((index % majorEvery) + majorEvery) % majorEvery === 0;
      ticks.push(Object.freeze({
        value,
        major,
        label: major ? value.toFixed(decimalPlaces(majorStep)).replace(/\.0+$/, "") : null,
      }));
    }
    return Object.freeze({ majorStep, minorStep, ticks: Object.freeze(ticks) });
  }

  function guide(axis, positionMm, id) {
    if (!GUIDE_AXES.includes(axis)) throw new Error(`Eje de guía no válido: ${axis}.`);
    return Object.freeze({
      id: String(id || "").trim(),
      axis,
      position_mm: Geometry.finiteNumber(positionMm, "guide position_mm"),
    });
  }

  function nextGuideId(existingIds, token) {
    const used = new Set(existingIds || []);
    const base = String(token || Date.now().toString(36)).replace(/[^a-z0-9_-]/gi, "") || "guide";
    let index = 1;
    let candidate = `guide_${base}_${index}`;
    while (used.has(candidate)) {
      index += 1;
      candidate = `guide_${base}_${index}`;
    }
    return candidate;
  }

  function measurement(startValue, endValue) {
    const start = Geometry.point(startValue, "measurement start");
    const end = Geometry.point(endValue, "measurement end");
    const deltaX = end.x - start.x;
    const deltaY = end.y - start.y;
    return Object.freeze({
      start,
      end,
      deltaX,
      deltaY,
      distance: Geometry.distanceBetweenPoints(start, end),
    });
  }

  function referenceBounds(slot, geometry, reference) {
    if (reference === "trim") return geometry.trimBounds(slot);
    if (reference === "productive") return geometry.bleedBounds(slot);
    throw new Error(`Referencia geométrica no válida: ${reference}.`);
  }

  function pairMetrics(first, second, geometry, reference) {
    const firstBounds = referenceBounds(first, geometry, reference);
    const secondBounds = referenceBounds(second, geometry, reference);
    const firstCenter = geometry.boundsCenter(firstBounds);
    const secondCenter = geometry.boundsCenter(secondBounds);
    const horizontalOrder = [
      { id: first.id, center: firstCenter },
      { id: second.id, center: secondCenter },
    ].sort((left, right) => left.center.x - right.center.x || left.id.localeCompare(right.id));
    const verticalOrder = [
      { id: first.id, center: firstCenter },
      { id: second.id, center: secondCenter },
    ].sort((left, right) => left.center.y - right.center.y || left.id.localeCompare(right.id));
    const gapX = geometry.horizontalGap(firstBounds, secondBounds);
    const gapY = geometry.verticalGap(firstBounds, secondBounds);
    const overlapX = Math.max(-gapX, 0);
    const overlapY = Math.max(-gapY, 0);
    const overlaps = overlapX > Geometry.DEFAULT_TOLERANCE_MM
      && overlapY > Geometry.DEFAULT_TOLERANCE_MM;
    return Object.freeze({
      ids: Object.freeze([first.id, second.id]),
      horizontalOrder: Object.freeze(horizontalOrder.map((item) => item.id)),
      verticalOrder: Object.freeze(verticalOrder.map((item) => item.id)),
      bounds: Object.freeze([firstBounds, secondBounds]),
      deltaX: horizontalOrder[1].center.x - horizontalOrder[0].center.x,
      deltaY: verticalOrder[1].center.y - verticalOrder[0].center.y,
      centerDistance: geometry.distanceBetweenPoints(firstCenter, secondCenter),
      gapX,
      gapY,
      overlapX,
      overlapY,
      overlapArea: overlaps ? overlapX * overlapY : 0,
      overlaps,
    });
  }

  function adjacentGaps(items, axis, geometry) {
    if (items.length < 2) return [];
    const ordered = [...items].sort((left, right) => axis === "x"
      ? left.bounds.left - right.bounds.left || left.id.localeCompare(right.id)
      : right.bounds.top - left.bounds.top || left.id.localeCompare(right.id));
    const gap = axis === "x" ? geometry.horizontalGap : geometry.verticalGap;
    return ordered.slice(1).map((item, index) => gap(ordered[index].bounds, item.bounds));
  }

  function selectionMetrics(layout, slotIds, geometry, options) {
    const selected = new Set(slotIds || []);
    const hidden = options?.hiddenSlotIds instanceof Set
      ? options.hiddenSlotIds : new Set(options?.hiddenSlotIds || []);
    const reference = options?.reference || "trim";
    const slots = layout.slots.filter((slot) => selected.has(slot.id)
      && slot.face === options?.activeFace && !hidden.has(slot.id));
    if (!slots.length) return Object.freeze({ count: 0, reference });
    const entries = slots.map((slot) => Object.freeze({
      id: slot.id,
      slot,
      bounds: referenceBounds(slot, geometry, reference),
    }));
    const aggregate = geometry.boundsUnion(entries.map((item) => item.bounds));
    if (slots.length === 1) {
      const slot = slots[0];
      return Object.freeze({
        count: 1,
        reference,
        id: slot.id,
        center: geometry.boundsCenter(referenceBounds(slot, geometry, reference)),
        trimBounds: geometry.trimBounds(slot),
        productiveBounds: geometry.bleedBounds(slot),
        rotationDeg: slot.geometry.rotation_deg,
        aggregate,
      });
    }
    if (slots.length === 2) {
      return Object.freeze({
        count: 2,
        reference,
        aggregate,
        pair: pairMetrics(slots[0], slots[1], geometry, reference),
      });
    }
    const gapsX = adjacentGaps(entries, "x", geometry);
    const gapsY = adjacentGaps(entries, "y", geometry);
    let overlapPairs = 0;
    for (let left = 0; left < entries.length; left += 1) {
      for (let right = left + 1; right < entries.length; right += 1) {
        if (geometry.intersectsBounds(
          entries[left].bounds,
          entries[right].bounds,
          false,
        )) overlapPairs += 1;
      }
    }
    return Object.freeze({
      count: slots.length,
      reference,
      aggregate,
      horizontalGapMin: Math.min(...gapsX),
      horizontalGapMax: Math.max(...gapsX),
      verticalGapMin: Math.min(...gapsY),
      verticalGapMax: Math.max(...gapsY),
      overlapPairs,
    });
  }

  return Object.freeze({
    RULER_STEPS_MM,
    MAX_RULER_TICKS,
    GUIDE_AXES,
    parseMillimetres,
    formatMillimetres,
    chooseRulerStep,
    rulerTicks,
    guide,
    nextGuideId,
    measurement,
    referenceBounds,
    pairMetrics,
    selectionMetrics,
  });
});
