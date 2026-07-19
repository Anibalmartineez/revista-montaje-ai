(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.EditorOffsetV2 = root.EditorOffsetV2 || {};
  root.EditorOffsetV2.LayoutMetrics = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  function currentSlotMetrics(layout, face) {
    const slots = layout.slots.filter((slot) => slot.face === face);
    const byWork = {};
    for (const slot of slots) byWork[slot.work_id] = (byWork[slot.work_id] || 0) + 1;
    const operationId = layout.imposition.last_result?.operation_id || null;
    const lastOperationPresent = operationId
      ? slots.filter((slot) => slot.generated_by?.operation_id === operationId).length
      : 0;
    return {
      total: slots.length,
      byWork,
      lastOperationPresent,
      operationId,
    };
  }

  function workCountsLabel(layout, byWork) {
    const names = new Map(layout.works.map((work) => [work.id, work.name]));
    const entries = Object.entries(byWork);
    if (!entries.length) return "Ninguno";
    return entries
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([workId, count]) => `${names.get(workId) || workId}: ${count}`)
      .join(" · ");
  }

  return Object.freeze({ currentSlotMetrics, workCountsLabel });
});
