(function (root, factory) {
  "use strict";
  const kernel = typeof module === "object" && module.exports
    ? require("./geometry_kernel.js")
    : root.EditorOffsetV2?.GeometryKernel;
  const api = factory(kernel);
  if (typeof module === "object" && module.exports) module.exports = api;
  root.EditorOffsetV2 = root.EditorOffsetV2 || {};
  root.EditorOffsetV2.SnapEngine = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function (Geometry) {
  "use strict";

  if (!Geometry) throw new Error("Editor V2 geometry kernel is required");

  const SOURCE_PRIORITY = Object.freeze({ guide: 0, printable: 1, sheet: 2, slot: 3 });
  const KIND_PRIORITY = Object.freeze({ edge: 0, center: 1 });

  function geometryBounds(slot, geometry, reference) {
    return reference === "productive" ? geometry.bleedBounds(slot) : geometry.trimBounds(slot);
  }

  function groupBounds(slots, geometry, reference) {
    const result = geometry.boundsUnion((slots || []).map((slot) => (
      geometryBounds(slot, geometry, reference)
    )));
    if (!result) throw new Error("Snap requires at least one moving slot");
    return result;
  }

  function axisAnchors(bounds, axis) {
    const center = axis === "x"
      ? bounds.left + bounds.width / 2
      : bounds.bottom + bounds.height / 2;
    return axis === "x"
      ? Object.freeze([
        Object.freeze({ key: "minX", value: bounds.left, kind: "edge" }),
        Object.freeze({ key: "centerX", value: center, kind: "center" }),
        Object.freeze({ key: "maxX", value: bounds.right, kind: "edge" }),
      ])
      : Object.freeze([
        Object.freeze({ key: "minY", value: bounds.bottom, kind: "edge" }),
        Object.freeze({ key: "centerY", value: center, kind: "center" }),
        Object.freeze({ key: "maxY", value: bounds.top, kind: "edge" }),
      ]);
  }

  function target(axis, value, source, kind, id, order, label) {
    return Object.freeze({
      axis,
      value: Geometry.finiteNumber(value, "snap target"),
      source,
      kind,
      id: String(id || ""),
      order: Number.isFinite(order) ? order : 0,
      label: label || `${source} · ${kind}`,
    });
  }

  function addBoundsTargets(targets, bounds, source, id, order) {
    targets.x.push(
      target("x", bounds.left, source, "edge", `${id}:left`, order, `${source} · borde izquierdo`),
      target("x", bounds.left + bounds.width / 2, source, "center", `${id}:center-x`, order, `${source} · centro X`),
      target("x", bounds.right, source, "edge", `${id}:right`, order, `${source} · borde derecho`),
    );
    targets.y.push(
      target("y", bounds.bottom, source, "edge", `${id}:bottom`, order, `${source} · borde inferior`),
      target("y", bounds.bottom + bounds.height / 2, source, "center", `${id}:center-y`, order, `${source} · centro Y`),
      target("y", bounds.top, source, "edge", `${id}:top`, order, `${source} · borde superior`),
    );
  }

  function captureTargets(options) {
    const geometry = options.geometry;
    const layout = options.layout;
    const sources = options.sources || {};
    const hidden = options.hiddenSlotIds instanceof Set
      ? options.hiddenSlotIds : new Set(options.hiddenSlotIds || []);
    const moving = new Set(options.movingIds || []);
    const targets = { x: [], y: [] };
    if (sources.guides) {
      for (const [order, item] of (options.guides || []).entries()) {
        if (item.axis === "x") {
          targets.x.push(target("x", item.position_mm, "guide", "edge", item.id, order, "guía vertical"));
        } else if (item.axis === "y") {
          targets.y.push(target("y", item.position_mm, "guide", "edge", item.id, order, "guía horizontal"));
        }
      }
    }
    if (sources.printable) {
      addBoundsTargets(targets, geometry.printableBounds(layout.sheet), "printable", "printable", 0);
    }
    if (sources.sheet) {
      addBoundsTargets(targets, Geometry.bounds({
        left: 0,
        right: layout.sheet.size_mm.width,
        bottom: 0,
        top: layout.sheet.size_mm.height,
      }), "sheet", "sheet", 0);
    }
    if (sources.slots) {
      layout.slots.forEach((slot, order) => {
        if (slot.face !== options.activeFace || hidden.has(slot.id) || moving.has(slot.id)) return;
        addBoundsTargets(
          targets,
          geometryBounds(slot, geometry, options.reference),
          "slot",
          slot.id,
          order,
        );
      });
    }
    return Object.freeze({
      x: Object.freeze(targets.x),
      y: Object.freeze(targets.y),
      capturedSlotCount: sources.slots
        ? new Set(targets.x.filter((item) => item.source === "slot").map((item) => item.id.split(":")[0])).size
        : 0,
    });
  }

  function compareCandidates(left, right) {
    const distance = Math.abs(left.offset) - Math.abs(right.offset);
    if (Math.abs(distance) > Geometry.DEFAULT_TOLERANCE_MM) return distance;
    const source = SOURCE_PRIORITY[left.target.source] - SOURCE_PRIORITY[right.target.source];
    if (source) return source;
    const targetKind = KIND_PRIORITY[left.target.kind] - KIND_PRIORITY[right.target.kind];
    if (targetKind) return targetKind;
    const anchorKind = KIND_PRIORITY[left.anchor.kind] - KIND_PRIORITY[right.anchor.kind];
    if (anchorKind) return anchorKind;
    const order = left.target.order - right.target.order;
    if (order) return order;
    const id = left.target.id.localeCompare(right.target.id);
    return id || left.anchor.key.localeCompare(right.anchor.key);
  }

  function resolveAxis(anchors, targets, thresholdMm) {
    const threshold = Geometry.nonNegativeNumber(thresholdMm, "snap threshold_mm");
    const candidates = [];
    for (const anchor of anchors || []) {
      for (const candidateTarget of targets || []) {
        const offset = candidateTarget.value - anchor.value;
        if (Math.abs(offset) <= threshold + Geometry.DEFAULT_TOLERANCE_MM) {
          candidates.push(Object.freeze({ anchor, target: candidateTarget, offset }));
        }
      }
    }
    candidates.sort(compareCandidates);
    return candidates[0] || null;
  }

  function translatedBounds(source, dx, dy) {
    return Geometry.bounds({
      left: source.left + dx,
      right: source.right + dx,
      bottom: source.bottom + dy,
      top: source.top + dy,
    });
  }

  function smartGuide(axis, result) {
    if (!result) return null;
    return Object.freeze({
      axis,
      position_mm: result.target.value,
      source: result.target.source,
      kind: result.target.kind,
      targetId: result.target.id,
      anchor: result.anchor.key,
      label: result.target.label,
      offset_mm: result.offset,
    });
  }

  function snapTranslation(options) {
    const rawDx = Geometry.finiteNumber(options.rawDx, "raw dx");
    const rawDy = Geometry.finiteNumber(options.rawDy, "raw dy");
    const movedBounds = translatedBounds(options.sourceBounds, rawDx, rawDy);
    if (options.enabled === false) {
      return Object.freeze({ dx: rawDx, dy: rawDy, offsetX: 0, offsetY: 0, x: null, y: null, guides: Object.freeze([]) });
    }
    const thresholdX = typeof options.thresholdMm === "number"
      ? options.thresholdMm : options.thresholdMm?.x;
    const thresholdY = typeof options.thresholdMm === "number"
      ? options.thresholdMm : options.thresholdMm?.y;
    const x = resolveAxis(axisAnchors(movedBounds, "x"), options.targets?.x, thresholdX);
    const y = resolveAxis(axisAnchors(movedBounds, "y"), options.targets?.y, thresholdY);
    const guides = [smartGuide("x", x), smartGuide("y", y)].filter(Boolean);
    return Object.freeze({
      dx: rawDx + (x?.offset || 0),
      dy: rawDy + (y?.offset || 0),
      offsetX: x?.offset || 0,
      offsetY: y?.offset || 0,
      x,
      y,
      guides: Object.freeze(guides),
    });
  }

  function snapPoint(options) {
    const source = Geometry.point(options.point, "snap point");
    if (options.enabled === false) return Object.freeze({ point: source, guides: Object.freeze([]) });
    const x = resolveAxis(
      [{ key: "pointX", value: source.x, kind: "center" }],
      options.targets?.x,
      typeof options.thresholdMm === "number" ? options.thresholdMm : options.thresholdMm?.x,
    );
    const y = resolveAxis(
      [{ key: "pointY", value: source.y, kind: "center" }],
      options.targets?.y,
      typeof options.thresholdMm === "number" ? options.thresholdMm : options.thresholdMm?.y,
    );
    return Object.freeze({
      point: Object.freeze({ x: source.x + (x?.offset || 0), y: source.y + (y?.offset || 0) }),
      x,
      y,
      guides: Object.freeze([smartGuide("x", x), smartGuide("y", y)].filter(Boolean)),
    });
  }

  return Object.freeze({
    SOURCE_PRIORITY,
    KIND_PRIORITY,
    geometryBounds,
    groupBounds,
    axisAnchors,
    captureTargets,
    resolveAxis,
    snapTranslation,
    snapPoint,
  });
});
