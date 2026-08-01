(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.EditorOffsetV2 = root.EditorOffsetV2 || {};
  root.EditorOffsetV2.ObjectOperations = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const DUPLICATE_OFFSET_MM = Object.freeze({ x_mm: 5, y_mm: -5 });
  const PASTE_OFFSET_STEP_MM = Object.freeze({ x_mm: 5, y_mm: -5 });
  const USER_LOCK_SURFACES = Object.freeze(["geometry", "content", "delete"]);

  function clone(value) {
    return typeof structuredClone === "function"
      ? structuredClone(value)
      : JSON.parse(JSON.stringify(value));
  }

  function selectedSlots(store) {
    const ids = new Set(store.selection);
    return store.layout.slots.filter((slot) => ids.has(slot.id));
  }

  function clipboardPayload(store, timestamp) {
    const slots = selectedSlots(store);
    if (!slots.length) throw new Error("Selecciona al menos un slot para copiar.");
    return {
      jobId: store.layout.job.id,
      slots: clone(slots),
      order: slots.map((slot) => slot.id),
      sourceFaces: [...new Set(slots.map((slot) => slot.face))],
      pasteCount: 0,
      capturedAt: timestamp || new Date().toISOString(),
    };
  }

  function sourceExists(layout, source) {
    const asset = layout.assets.find((item) => item.id === source?.asset_id);
    const page = asset?.pages?.find((item) => item.number === source?.page);
    return Boolean(asset && page && page.boxes_mm?.[source.pdf_box]);
  }

  function validateClipboard(layout, clipboard, activeFace) {
    if (!clipboard || !Array.isArray(clipboard.slots) || !clipboard.slots.length) {
      return { ok: false, reason: "El clipboard interno está vacío." };
    }
    if (clipboard.jobId !== layout.job.id) {
      return { ok: false, reason: "El clipboard pertenece a otro job." };
    }
    if (activeFace !== "front") {
      return { ok: false, reason: "Pegar en dorso estará disponible con navegación de caras." };
    }
    const workIds = new Set(layout.works.map((work) => work.id));
    const invalidWork = clipboard.slots.find((slot) => !workIds.has(slot.work_id));
    if (invalidWork) {
      return {
        ok: false,
        reason: `El clipboard referencia un work inexistente: ${invalidWork.work_id}.`,
      };
    }
    const invalidSource = clipboard.slots.find((slot) => !sourceExists(layout, slot.source));
    if (invalidSource) {
      return {
        ok: false,
        reason: `El clipboard referencia un asset, página o caja inexistente: ${invalidSource.id}.`,
      };
    }
    const incompatibleFace = clipboard.slots.find((slot) => slot.face !== activeFace);
    if (incompatibleFace) {
      return {
        ok: false,
        reason: "El clipboard solo puede pegarse en su cara de origen activa.",
      };
    }
    return { ok: true, reason: null };
  }

  function copySelection(store, timestamp) {
    const payload = clipboardPayload(store, timestamp);
    store.setClipboard(payload);
    return payload;
  }

  function createPasteCommand(store, commands, options) {
    const validation = validateClipboard(store.layout, store.clipboard, store.activeFace);
    if (!validation.ok) throw new Error(validation.reason);
    const pasteCount = store.clipboard.pasteCount + 1;
    const offset = {
      x_mm: PASTE_OFFSET_STEP_MM.x_mm * pasteCount,
      y_mm: PASTE_OFFSET_STEP_MM.y_mm * pasteCount,
    };
    const preparedSlots = commands.prepareDuplicateSlotsFromSlots(
      store.layout,
      store.clipboard.slots,
      offset,
      { idFactory: options?.idFactory },
    );
    return {
      pasteCount,
      command: new commands.DuplicateSlotsCommand(
        store.layout,
        store.clipboard.order,
        {
          description: "Pegar slots",
          preparedSlots,
          selectionBefore: [...store.selection],
        },
      ),
    };
  }

  function visibleSlot(slot, activeFace, hiddenSlotIds) {
    const hidden = hiddenSlotIds instanceof Set ? hiddenSlotIds : new Set(hiddenSlotIds || []);
    return slot.face === activeFace && !hidden.has(slot.id);
  }

  function selectAllFace(layout, activeFace, hiddenSlotIds) {
    return layout.slots
      .filter((slot) => visibleSlot(slot, activeFace, hiddenSlotIds))
      .map((slot) => slot.id);
  }

  function selectSameWork(layout, selectedIds, activeFace, hiddenSlotIds) {
    const requested = new Set(selectedIds || []);
    const workIds = new Set(
      layout.slots.filter((slot) => requested.has(slot.id)).map((slot) => slot.work_id),
    );
    return layout.slots
      .filter((slot) => visibleSlot(slot, activeFace, hiddenSlotIds)
        && workIds.has(slot.work_id))
      .map((slot) => slot.id);
  }

  function selectSameAsset(layout, selectedIds, activeFace, hiddenSlotIds) {
    const requested = new Set(selectedIds || []);
    const assetIds = new Set(
      layout.slots
        .filter((slot) => requested.has(slot.id))
        .map((slot) => slot.source.asset_id),
    );
    return layout.slots
      .filter((slot) => visibleSlot(slot, activeFace, hiddenSlotIds)
        && assetIds.has(slot.source.asset_id))
      .map((slot) => slot.id);
  }

  function userLockState(slots, surface) {
    if (!USER_LOCK_SURFACES.includes(surface)) {
      throw new Error(`Unsupported user lock surface: ${surface}`);
    }
    if (!slots.length) return "none";
    const lockedCount = slots.filter(
      (slot) => slot.locks[surface].includes("user"),
    ).length;
    if (lockedCount === 0) return "none";
    if (lockedCount === slots.length) return "all";
    return "mixed";
  }

  function remainingLockSources(slots, surface) {
    return [...new Set(slots.flatMap(
      (slot) => slot.locks[surface].filter((source) => source !== "user"),
    ))];
  }

  function selectionRotation(slots) {
    if (!slots.length) return { state: "none", value: null };
    const rotations = [...new Set(slots.map((slot) => slot.geometry.rotation_deg))];
    return rotations.length === 1
      ? { state: "single", value: rotations[0] }
      : { state: "mixed", value: null };
  }

  return Object.freeze({
    DUPLICATE_OFFSET_MM,
    PASTE_OFFSET_STEP_MM,
    USER_LOCK_SURFACES,
    clipboardPayload,
    copySelection,
    createPasteCommand,
    remainingLockSources,
    selectAllFace,
    selectSameAsset,
    selectSameWork,
    selectedSlots,
    selectionRotation,
    sourceExists,
    userLockState,
    validateClipboard,
    visibleSlot,
  });
});
