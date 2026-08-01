(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.EditorOffsetV2 = root.EditorOffsetV2 || {};
  root.EditorOffsetV2.EditPolicy = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const CAPABILITY_LOCK = Object.freeze({
    move: "geometry",
    rotate: "geometry",
    delete: "delete",
    replace_content: "content",
    replace_by_repeat: "delete",
  });

  const CAPABILITY_LABEL = Object.freeze({
    move: "mover",
    rotate: "rotar",
    delete: "eliminar",
    replace_content: "sustituir la fuente de",
    replace_by_repeat: "reemplazar mediante Repeat",
  });

  class EditPolicyError extends Error {
    constructor(capability, blockedDetails) {
      const details = [...blockedDetails];
      const ids = details.map((item) => item.id);
      const labels = details.map((item) => `${item.id} [${item.sources.join(", ")}]`);
      super(`No se puede ${CAPABILITY_LABEL[capability]}: slots bloqueados ${labels.join("; ")}.`);
      this.name = "EditPolicyError";
      this.code = "SLOT_EDIT_LOCKED";
      this.capability = capability;
      this.blockedIds = Object.freeze(ids);
      this.blockedDetails = Object.freeze(details.map((item) => Object.freeze({
        id: item.id,
        sources: Object.freeze([...item.sources]),
      })));
    }
  }

  function lockSources(slot, capability) {
    const lockName = CAPABILITY_LOCK[capability];
    if (!lockName) throw new Error(`Unknown edit capability: ${capability}`);
    const sources = slot?.locks?.[lockName];
    return Array.isArray(sources) ? sources.filter(Boolean) : [];
  }

  function blockedSlotIds(layout, slotIds, capability) {
    return blockedSlotDetails(layout, slotIds, capability).map((item) => item.id);
  }

  function blockedSlotDetails(layout, slotIds, capability) {
    const ids = new Set(slotIds || []);
    return (layout?.slots || [])
      .filter((slot) => ids.has(slot.id))
      .map((slot) => ({ id: slot.id, sources: lockSources(slot, capability) }))
      .filter((item) => item.sources.length > 0);
  }

  function can(layout, slotIds, capability) {
    return blockedSlotIds(layout, slotIds, capability).length === 0;
  }

  function assertCan(layout, slotIds, capability) {
    const blocked = blockedSlotDetails(layout, slotIds, capability);
    if (blocked.length) throw new EditPolicyError(capability, blocked);
    return true;
  }

  return Object.freeze({
    CAPABILITY_LOCK,
    EditPolicyError,
    lockSources,
    blockedSlotIds,
    blockedSlotDetails,
    can,
    assertCan,
  });
});
