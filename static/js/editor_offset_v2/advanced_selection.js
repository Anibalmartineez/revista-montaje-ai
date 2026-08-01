(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.EditorOffsetV2 = root.EditorOffsetV2 || {};
  root.EditorOffsetV2.AdvancedSelection = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const EPSILON_MM = 1e-9;
  const TRIM_SIZE_TOLERANCE_MM = 1e-9;
  const MARQUEE_DRAG_THRESHOLD_PX = 4;
  const CYCLE_POINT_TOLERANCE_MM = 0.75;
  const MARQUEE_MODES = Object.freeze(["contain", "intersect"]);
  const SELECTION_MODES = Object.freeze(["replace", "add", "toggle", "subtract"]);
  const SIMILAR_CRITERIA = Object.freeze(["work", "asset", "size", "rotation", "provenance"]);
  const GEOMETRY_ISSUES = Object.freeze([
    "outside_sheet",
    "outside_printable",
    "overlap",
  ]);

  function hiddenSet(hiddenSlotIds) {
    return hiddenSlotIds instanceof Set ? hiddenSlotIds : new Set(hiddenSlotIds || []);
  }

  function visibleSlots(layout, activeFace, hiddenSlotIds) {
    const hidden = hiddenSet(hiddenSlotIds);
    return layout.slots.filter((slot) => slot.face === activeFace && !hidden.has(slot.id));
  }

  function geometryBounds(slot, geometry, reference) {
    if (reference === "trim") return geometry.trimBounds(slot);
    if (reference === "productive") return geometry.bleedBounds(slot);
    throw new Error(`Referencia geométrica no válida: ${reference}.`);
  }

  function rectangleFromPoints(start, end) {
    const left = Math.min(start.x, end.x);
    const right = Math.max(start.x, end.x);
    const bottom = Math.min(start.y, end.y);
    const top = Math.max(start.y, end.y);
    return Object.freeze({ left, right, bottom, top, width: right - left, height: top - bottom });
  }

  function boundsContain(container, candidate, tolerance) {
    const epsilon = tolerance ?? EPSILON_MM;
    return candidate.left >= container.left - epsilon
      && candidate.right <= container.right + epsilon
      && candidate.bottom >= container.bottom - epsilon
      && candidate.top <= container.top + epsilon;
  }

  function boundsIntersect(left, right, includeContact) {
    const epsilon = includeContact === false ? EPSILON_MM : -EPSILON_MM;
    return Math.min(left.right, right.right) - Math.max(left.left, right.left) > epsilon
      && Math.min(left.top, right.top) - Math.max(left.bottom, right.bottom) > epsilon;
  }

  function pointInBounds(point, bounds) {
    return point.x >= bounds.left - EPSILON_MM
      && point.x <= bounds.right + EPSILON_MM
      && point.y >= bounds.bottom - EPSILON_MM
      && point.y <= bounds.top + EPSILON_MM;
  }

  function captureMarqueeCandidates(layout, activeFace, hiddenSlotIds, geometry, reference) {
    return Object.freeze(visibleSlots(layout, activeFace, hiddenSlotIds).map((slot) => Object.freeze({
      id: slot.id,
      bounds: Object.freeze(geometryBounds(slot, geometry, reference)),
    })));
  }

  function matchingMarqueeIds(candidates, rectangle, mode) {
    if (!MARQUEE_MODES.includes(mode)) throw new Error(`Modo marquee no válido: ${mode}.`);
    return candidates
      .filter((candidate) => mode === "contain"
        ? boundsContain(rectangle, candidate.bounds)
        : boundsIntersect(rectangle, candidate.bounds, true))
      .map((candidate) => candidate.id);
  }

  function selectionModeFromModifiers(modifiers, startedOnSlot) {
    if (modifiers?.ctrlKey || modifiers?.metaKey) return "toggle";
    if (modifiers?.shiftKey) return "add";
    if (modifiers?.altKey && !startedOnSlot) return "subtract";
    return "replace";
  }

  function applySelectionMode(currentIds, incomingIds, mode) {
    if (!SELECTION_MODES.includes(mode)) throw new Error(`Modo de selección no válido: ${mode}.`);
    const result = mode === "replace" ? new Set() : new Set(currentIds || []);
    for (const id of incomingIds || []) {
      if (mode === "toggle") {
        if (result.has(id)) result.delete(id);
        else result.add(id);
      } else if (mode === "subtract") result.delete(id);
      else result.add(id);
    }
    return [...result];
  }

  function hitTestSlots(layout, activeFace, hiddenSlotIds, geometry, reference, point) {
    return visibleSlots(layout, activeFace, hiddenSlotIds)
      .filter((slot) => pointInBounds(point, geometryBounds(slot, geometry, reference)))
      .reverse()
      .map((slot) => slot.id);
  }

  function sameCycle(previous, candidateIds, point, layoutVersion, visibilityVersion, activeFace) {
    if (!previous || previous.layoutVersion !== layoutVersion
        || previous.visibilityVersion !== visibilityVersion || previous.activeFace !== activeFace) return false;
    const dx = previous.point.x - point.x;
    const dy = previous.point.y - point.y;
    if (Math.hypot(dx, dy) > CYCLE_POINT_TOLERANCE_MM) return false;
    return previous.candidateIds.length === candidateIds.length
      && previous.candidateIds.every((id, index) => id === candidateIds[index]);
  }

  function cycleAtPoint(options) {
    const candidateIds = hitTestSlots(
      options.layout,
      options.activeFace,
      options.hiddenSlotIds,
      options.geometry,
      options.reference,
      options.point,
    );
    if (!candidateIds.length) return Object.freeze({ selectedId: null, cycle: null, position: 0, total: 0 });
    const continuing = sameCycle(
      options.previousCycle,
      candidateIds,
      options.point,
      options.layoutVersion,
      options.visibilityVersion,
      options.activeFace,
    );
    let index;
    if (continuing) index = (options.previousCycle.index + 1) % candidateIds.length;
    else {
      const currentIndex = candidateIds.indexOf(options.currentSlotId);
      index = currentIndex >= 0 ? (currentIndex + 1) % candidateIds.length : 0;
    }
    const cycle = Object.freeze({
      point: Object.freeze({ x: options.point.x, y: options.point.y }),
      candidateIds: Object.freeze(candidateIds),
      index,
      layoutVersion: options.layoutVersion,
      visibilityVersion: options.visibilityVersion,
      activeFace: options.activeFace,
    });
    return Object.freeze({ selectedId: candidateIds[index], cycle, position: index + 1, total: candidateIds.length });
  }

  function selectedSeedSlots(layout, selectedIds) {
    const selected = new Set(selectedIds || []);
    return layout.slots.filter((slot) => selected.has(slot.id));
  }

  function sameTrimSize(left, right) {
    return Math.abs(left.width - right.width) <= TRIM_SIZE_TOLERANCE_MM
      && Math.abs(left.height - right.height) <= TRIM_SIZE_TOLERANCE_MM;
  }

  function matchesCriterion(slot, seeds, criterion) {
    if (criterion === "work") return seeds.some((seed) => seed.work_id === slot.work_id);
    if (criterion === "asset") return seeds.some((seed) => seed.source.asset_id === slot.source.asset_id);
    if (criterion === "size") return seeds.some((seed) => sameTrimSize(
      seed.geometry.trim_size_mm,
      slot.geometry.trim_size_mm,
    ));
    if (criterion === "rotation") return seeds.some(
      (seed) => seed.geometry.rotation_deg === slot.geometry.rotation_deg,
    );
    if (criterion === "provenance") return seeds.some(
      (seed) => seed.generated_by?.type === slot.generated_by?.type,
    );
    return false;
  }

  function selectSimilar(layout, selectedIds, activeFace, hiddenSlotIds, criterion) {
    if (!SIMILAR_CRITERIA.includes(criterion)) throw new Error(`Criterio no válido: ${criterion}.`);
    const seeds = selectedSeedSlots(layout, selectedIds);
    if (!seeds.length) throw new Error("Selecciona al menos un slot como referencia.");
    return visibleSlots(layout, activeFace, hiddenSlotIds)
      .filter((slot) => matchesCriterion(slot, seeds, criterion))
      .map((slot) => slot.id);
  }

  function selectLocked(layout, activeFace, hiddenSlotIds, surface) {
    if (!["geometry", "content", "delete"].includes(surface)) {
      throw new Error(`Superficie de lock no válida: ${surface}.`);
    }
    return visibleSlots(layout, activeFace, hiddenSlotIds)
      .filter((slot) => Array.isArray(slot.locks?.[surface]) && slot.locks[surface].length > 0)
      .map((slot) => slot.id);
  }

  function geometryIssueIndex(layout, activeFace, hiddenSlotIds, geometry, reference) {
    const slots = visibleSlots(layout, activeFace, hiddenSlotIds);
    const entries = new Map(slots.map((slot) => [slot.id, new Set()]));
    const sheet = {
      left: 0,
      right: layout.sheet.size_mm.width,
      bottom: 0,
      top: layout.sheet.size_mm.height,
    };
    const printable = geometry.printableBounds(layout.sheet);
    const bounds = new Map(slots.map((slot) => [slot.id, geometryBounds(slot, geometry, reference)]));
    for (const slot of slots) {
      const slotBounds = bounds.get(slot.id);
      if (!boundsContain(sheet, slotBounds)) entries.get(slot.id).add("outside_sheet");
      else if (!boundsContain(printable, slotBounds)) entries.get(slot.id).add("outside_printable");
    }
    for (let left = 0; left < slots.length; left += 1) {
      for (let right = left + 1; right < slots.length; right += 1) {
        if (boundsIntersect(bounds.get(slots[left].id), bounds.get(slots[right].id), false)) {
          entries.get(slots[left].id).add("overlap");
          entries.get(slots[right].id).add("overlap");
        }
      }
    }
    return entries;
  }

  function selectGeometryIssues(index, issue) {
    if (issue !== "any" && !GEOMETRY_ISSUES.includes(issue)) {
      throw new Error(`Problema geométrico no válido: ${issue}.`);
    }
    return [...index.entries()]
      .filter(([, issues]) => issue === "any" ? issues.size > 0 : issues.has(issue))
      .map(([slotId]) => slotId);
  }

  return Object.freeze({
    CYCLE_POINT_TOLERANCE_MM,
    EPSILON_MM,
    GEOMETRY_ISSUES,
    MARQUEE_DRAG_THRESHOLD_PX,
    MARQUEE_MODES,
    SELECTION_MODES,
    SIMILAR_CRITERIA,
    TRIM_SIZE_TOLERANCE_MM,
    applySelectionMode,
    boundsContain,
    boundsIntersect,
    captureMarqueeCandidates,
    cycleAtPoint,
    geometryBounds,
    geometryIssueIndex,
    hitTestSlots,
    matchingMarqueeIds,
    pointInBounds,
    rectangleFromPoints,
    selectGeometryIssues,
    selectLocked,
    selectSimilar,
    selectionModeFromModifiers,
    visibleSlots,
  });
});
