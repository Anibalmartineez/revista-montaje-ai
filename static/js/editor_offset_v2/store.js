(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  }
  root.EditorOffsetV2 = root.EditorOffsetV2 || {};
  root.EditorOffsetV2.Store = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const SAVE_STATES = Object.freeze(["clean", "dirty", "saving", "save_error", "conflict"]);

  function clone(value) {
    return typeof structuredClone === "function"
      ? structuredClone(value)
      : JSON.parse(JSON.stringify(value));
  }

  function deepFreeze(value) {
    if (!value || typeof value !== "object" || Object.isFrozen(value)) return value;
    Object.freeze(value);
    for (const nested of Object.values(value)) deepFreeze(nested);
    return value;
  }

  function sameSet(left, right) {
    return left.size === right.size && [...left].every((value) => right.has(value));
  }

  function suggestedPdfBox(page) {
    if (page && page.boxes_mm) {
      if (page.boxes_mm.trim) return "trim";
      if (page.boxes_mm.crop) return "crop";
      if (page.boxes_mm.media) return "media";
    }
    return null;
  }

  function isReadyAsset(asset) {
    return Boolean(asset && asset.status === "ready" && asset.pages && asset.pages.length);
  }

  class EditorStore {
    constructor(layout) {
      if (!layout || layout.layout_schema_version !== 2) {
        throw new Error("EditorStore requires Layout V2");
      }
      this.layout = clone(layout);
      this.revision = this.layout.job.revision;
      this.activeFace = this.layout.faces.enabled[0];
      this.selection = new Set();
      this.hoverId = null;
      this.activeTool = "select";
      this.zoom = 1;
      this.pan = { x: 0, y: 0 };
      this.showSlotLabels = true;
      this.cursorMm = { x: null, y: null };
      this.pointerSession = null;
      this.previewPositions = {};
      this.previewSlots = [];
      this.clipboard = null;
      this.arrangement = {
        geometryReference: "trim",
        target: "selection",
        keySlotId: null,
      };
      this.advancedSelection = {
        marqueeMode: "contain",
        marqueeRect: null,
        hiddenSlotIds: new Set(),
        previousHiddenSlotIds: null,
        visibilityVersion: 0,
        expandedFaceIds: new Set([this.activeFace]),
        expandedWorkIds: new Set(this.layout.works.map((work) => work.id)),
        knownWorkIds: new Set(this.layout.works.map((work) => work.id)),
        treeAnchorSlotId: null,
        cycle: null,
      };
      this.saveState = {
        status: "clean",
        error: null,
        lastSavedAt: this.layout.job.updated_at,
      };
      const firstAsset = this.layout.assets.find(isReadyAsset) || null;
      const firstPage = firstAsset ? firstAsset.pages[0] : null;
      this.assetPanel = {
        selectedAssetId: firstAsset ? firstAsset.id : null,
        selectedPage: firstPage ? firstPage.number : null,
        selectedPdfBox: suggestedPdfBox(firstPage),
        selectedWorkId: this.layout.works[0]?.id || null,
        uploadStatus: "idle",
        message: null,
        error: null,
      };
      this.repeatPanel = {
        status: "idle",
        proposal: null,
        error: null,
      };
      this.feedback = null;
      this.undoStack = [];
      this.redoStack = [];
      this.changeVersion = 0;
      this.savedChangeVersion = 0;
      this.listeners = new Set();
      this.beforeCommandHooks = new Set();
    }

    subscribe(listener) {
      this.listeners.add(listener);
      return () => this.listeners.delete(listener);
    }

    emit(type, detail) {
      const event = { type, detail: detail || null, state: this.getState() };
      for (const listener of this.listeners) {
        listener(event);
      }
    }

    getState() {
      return {
        layout: this.layout,
        revision: this.revision,
        activeFace: this.activeFace,
        selection: [...this.selection],
        hoverId: this.hoverId,
        activeTool: this.activeTool,
        zoom: this.zoom,
        pan: { ...this.pan },
        showSlotLabels: this.showSlotLabels,
        cursorMm: { ...this.cursorMm },
        pointerSession: this.pointerSession,
        previewPositions: this.previewPositions,
        previewSlots: this.previewSlots,
        clipboard: this.clipboard ? clone(this.clipboard) : null,
        arrangement: { ...this.arrangement },
        advancedSelection: {
          marqueeMode: this.advancedSelection.marqueeMode,
          marqueeRect: this.advancedSelection.marqueeRect
            ? { ...this.advancedSelection.marqueeRect }
            : null,
          hiddenSlotIds: [...this.advancedSelection.hiddenSlotIds],
          previousHiddenSlotIds: this.advancedSelection.previousHiddenSlotIds
            ? [...this.advancedSelection.previousHiddenSlotIds]
            : null,
          visibilityVersion: this.advancedSelection.visibilityVersion,
          expandedFaceIds: [...this.advancedSelection.expandedFaceIds],
          expandedWorkIds: [...this.advancedSelection.expandedWorkIds],
          treeAnchorSlotId: this.advancedSelection.treeAnchorSlotId,
          cycle: this.advancedSelection.cycle ? clone(this.advancedSelection.cycle) : null,
        },
        saveState: { ...this.saveState },
        assetPanel: { ...this.assetPanel },
        repeatPanel: clone(this.repeatPanel),
        feedback: this.feedback,
        canUndo: this.undoStack.length > 0,
        canRedo: this.redoStack.length > 0,
        hasUnsavedChanges: this.hasUnsavedChanges(),
      };
    }

    addBeforeCommandHook(listener) {
      if (typeof listener !== "function") {
        throw new TypeError("Before-command hook must be a function");
      }
      this.beforeCommandHooks.add(listener);
      return () => this.beforeCommandHooks.delete(listener);
    }

    executeCommand(command) {
      for (const hook of [...this.beforeCommandHooks]) hook(command);
      command.execute(this.layout);
      this.applyCommandSelection(command, "after");
      this.undoStack.push(command);
      this.redoStack = [];
      this.markChanged();
      this.filterSelection();
      this.emit("command", command);
    }

    undo() {
      const command = this.undoStack.pop();
      if (!command) {
        return false;
      }
      command.undo(this.layout);
      this.applyCommandSelection(command, "before");
      this.redoStack.push(command);
      this.markChanged();
      this.filterSelection();
      this.emit("undo", command);
      return true;
    }

    redo() {
      const command = this.redoStack.pop();
      if (!command) {
        return false;
      }
      command.redo(this.layout);
      this.applyCommandSelection(command, "after");
      this.undoStack.push(command);
      this.markChanged();
      this.filterSelection();
      this.emit("redo", command);
      return true;
    }

    applyCommandSelection(command, phase) {
      const key = phase === "before" ? "selectionBefore" : "selectionAfter";
      if (!Array.isArray(command?.[key])) return;
      const validIds = new Set(this.layout.slots.map((slot) => slot.id));
      this.selection = new Set(command[key].filter((id) => validIds.has(id)));
    }

    markChanged() {
      this.syncNewTreeWorks();
      this.changeVersion += 1;
      this.clearSelectionCycle(false);
      this.feedback = null;
      if (this.saveState.status !== "saving" && this.saveState.status !== "conflict") {
        this.saveState = { ...this.saveState, status: "dirty", error: null };
      }
    }

    hasUnsavedChanges() {
      return this.changeVersion !== this.savedChangeVersion;
    }

    setSelection(ids, mode) {
      const hidden = this.advancedSelection.hiddenSlotIds;
      const validIds = new Set(this.layout.slots
        .filter((slot) => !hidden.has(slot.id))
        .map((slot) => slot.id));
      const incoming = [...ids].filter((id) => validIds.has(id));
      const previous = new Set(this.selection);
      if (mode === "toggle") {
        for (const id of incoming) {
          if (this.selection.has(id)) {
            this.selection.delete(id);
          } else {
            this.selection.add(id);
          }
        }
      } else if (mode === "add") {
        incoming.forEach((id) => this.selection.add(id));
      } else {
        this.selection = new Set(incoming);
      }
      if (!sameSet(previous, this.selection)) {
        this.reconcileKeySlot();
        this.emit("selection");
      }
    }

    clearSelection() {
      if (this.selection.size) {
        this.selection.clear();
        this.reconcileKeySlot();
        this.emit("selection");
      }
    }

    filterSelection() {
      const validIds = new Set(this.layout.slots
        .filter((slot) => !this.advancedSelection.hiddenSlotIds.has(slot.id))
        .map((slot) => slot.id));
      this.selection = new Set([...this.selection].filter((id) => validIds.has(id)));
      const existingIds = new Set(this.layout.slots.map((slot) => slot.id));
      this.advancedSelection.hiddenSlotIds = new Set(
        [...this.advancedSelection.hiddenSlotIds].filter((id) => existingIds.has(id)),
      );
      if (this.advancedSelection.treeAnchorSlotId
          && !existingIds.has(this.advancedSelection.treeAnchorSlotId)) {
        this.advancedSelection.treeAnchorSlotId = null;
      }
      this.reconcileKeySlot();
    }

    syncNewTreeWorks() {
      const state = this.advancedSelection;
      for (const work of this.layout.works) {
        if (state.knownWorkIds.has(work.id)) continue;
        state.knownWorkIds.add(work.id);
        state.expandedWorkIds.add(work.id);
      }
    }

    reconcileKeySlot() {
      const keySlotId = this.arrangement?.keySlotId;
      if (!keySlotId) return false;
      const keySlot = this.layout.slots.find((slot) => slot.id === keySlotId);
      if (!keySlot || keySlot.face !== this.activeFace || !this.selection.has(keySlotId)
          || this.advancedSelection.hiddenSlotIds.has(keySlotId)) {
        this.arrangement = { ...this.arrangement, keySlotId: null };
        return true;
      }
      return false;
    }

    setArrangementGeometryReference(reference) {
      if (!["trim", "productive"].includes(reference)) {
        throw new Error(`Unknown arrangement geometry reference: ${reference}`);
      }
      if (this.arrangement.geometryReference !== reference) {
        this.arrangement = { ...this.arrangement, geometryReference: reference };
        this.emit("arrangement");
      }
    }

    setArrangementTarget(target) {
      if (!["selection", "key", "sheet", "printable"].includes(target)) {
        throw new Error(`Unknown arrangement target: ${target}`);
      }
      if (this.arrangement.target !== target) {
        this.arrangement = { ...this.arrangement, target };
        this.emit("arrangement");
      }
    }

    setKeySlot(slotId) {
      if (slotId === null) {
        if (this.arrangement.keySlotId !== null) {
          this.arrangement = { ...this.arrangement, keySlotId: null };
          this.emit("arrangement");
        }
        return;
      }
      const slot = this.layout.slots.find((item) => item.id === slotId);
      if (!slot || slot.face !== this.activeFace || !this.selection.has(slotId)
          || this.advancedSelection.hiddenSlotIds.has(slotId)) {
        throw new Error("El slot clave debe pertenecer a la selección y a la cara activa.");
      }
      if (this.arrangement.keySlotId !== slotId) {
        this.arrangement = { ...this.arrangement, keySlotId: slotId };
        this.emit("arrangement");
      }
    }

    setMarqueeMode(mode) {
      if (!["contain", "intersect"].includes(mode)) {
        throw new Error(`Unknown marquee mode: ${mode}`);
      }
      if (this.advancedSelection.marqueeMode !== mode) {
        this.advancedSelection.marqueeMode = mode;
        this.clearSelectionCycle(false);
        this.emit("selection_ui");
      }
    }

    setMarqueeRect(rectangle) {
      const next = rectangle ? clone(rectangle) : null;
      this.advancedSelection.marqueeRect = next;
      this.emit("marquee_preview");
    }

    clearMarqueeRect(emitEvent) {
      if (!this.advancedSelection.marqueeRect) return false;
      this.advancedSelection.marqueeRect = null;
      if (emitEvent !== false) this.emit("marquee_preview");
      return true;
    }

    setSelectionCycle(cycle) {
      this.advancedSelection.cycle = cycle ? clone(cycle) : null;
      this.emit("selection_cycle");
    }

    clearSelectionCycle(emitEvent) {
      if (!this.advancedSelection.cycle) return false;
      this.advancedSelection.cycle = null;
      if (emitEvent !== false) this.emit("selection_cycle");
      return true;
    }

    setTreeAnchor(slotId) {
      const valid = slotId === null || this.layout.slots.some((slot) => slot.id === slotId);
      if (!valid) throw new Error("Unknown tree selection anchor");
      if (this.advancedSelection.treeAnchorSlotId !== slotId) {
        this.advancedSelection.treeAnchorSlotId = slotId;
        this.emit("tree_state");
      }
    }

    setTreeExpanded(kind, id, expanded) {
      const target = kind === "face"
        ? this.advancedSelection.expandedFaceIds
        : kind === "work" ? this.advancedSelection.expandedWorkIds : null;
      if (!target) throw new Error(`Unknown tree node kind: ${kind}`);
      const before = target.has(id);
      if (expanded) target.add(id);
      else target.delete(id);
      if (before !== target.has(id)) this.emit("tree_state");
    }

    isSlotHidden(slotId) {
      return this.advancedSelection.hiddenSlotIds.has(slotId);
    }

    setHiddenSlotIds(ids, options) {
      const validIds = new Set(this.layout.slots.map((slot) => slot.id));
      const next = new Set([...ids].filter((id) => validIds.has(id)));
      if (sameSet(next, this.advancedSelection.hiddenSlotIds)) return false;
      if (options?.capturePrevious) {
        this.advancedSelection.previousHiddenSlotIds = new Set(
          this.advancedSelection.hiddenSlotIds,
        );
      }
      this.advancedSelection.hiddenSlotIds = next;
      this.advancedSelection.visibilityVersion += 1;
      this.advancedSelection.cycle = null;
      this.advancedSelection.marqueeRect = null;
      this.selection = new Set([...this.selection].filter((id) => !next.has(id)));
      this.reconcileKeySlot();
      this.emit("visibility");
      return true;
    }

    hideSlots(ids, options) {
      const next = new Set(this.advancedSelection.hiddenSlotIds);
      for (const id of ids || []) next.add(id);
      return this.setHiddenSlotIds(next, options);
    }

    showSlots(ids, options) {
      const next = new Set(this.advancedSelection.hiddenSlotIds);
      for (const id of ids || []) next.delete(id);
      return this.setHiddenSlotIds(next, options);
    }

    restorePreviousVisibility() {
      const previous = this.advancedSelection.previousHiddenSlotIds;
      if (!previous) return false;
      const current = new Set(this.advancedSelection.hiddenSlotIds);
      const changed = this.setHiddenSlotIds(previous, { capturePrevious: false });
      this.advancedSelection.previousHiddenSlotIds = changed ? current : null;
      this.emit("visibility_snapshot");
      return changed;
    }

    setHover(id) {
      if (this.hoverId !== id) {
        this.hoverId = id;
        this.emit("hover");
      }
    }

    setSlotLabelsVisible(visible) {
      const next = Boolean(visible);
      if (this.showSlotLabels !== next) {
        this.showSlotLabels = next;
        this.emit("slot_labels");
      }
    }

    setAssetSelection(assetId, pageNumber, pdfBox) {
      const asset = this.layout.assets.find((item) => item.id === assetId);
      if (!isReadyAsset(asset)) {
        throw new Error("Unknown asset selection");
      }
      const page = asset.pages.find((item) => item.number === pageNumber) || asset.pages[0];
      if (!page) {
        throw new Error("The selected asset has no pages");
      }
      const selectedBox = pdfBox || suggestedPdfBox(page);
      if (!selectedBox || !page.boxes_mm[selectedBox]) {
        throw new Error("The selected PDF box is absent");
      }
      this.assetPanel = {
        ...this.assetPanel,
        selectedAssetId: asset.id,
        selectedPage: page.number,
        selectedPdfBox: selectedBox,
        message: null,
        error: null,
      };
      this.emit("asset_selection");
    }

    setSelectedWork(workId) {
      if (workId !== null && !this.layout.works.some((work) => work.id === workId)) {
        throw new Error("Unknown work selection");
      }
      this.assetPanel = { ...this.assetPanel, selectedWorkId: workId };
      this.emit("work_selection");
    }

    setUploadState(status, message, error) {
      this.assetPanel = {
        ...this.assetPanel,
        uploadStatus: status,
        message: message || null,
        error: error || null,
      };
      this.emit("upload_state");
    }

    setRepeatState(status, proposal, error) {
      this.repeatPanel = {
        status,
        proposal: proposal ? clone(proposal) : null,
        error: error || null,
      };
      this.emit("repeat_state");
    }

    setFeedback(message) {
      this.feedback = message || null;
      this.emit("feedback");
    }

    setClipboard(payload) {
      this.clipboard = payload ? deepFreeze(clone(payload)) : null;
      this.emit("clipboard");
    }

    setClipboardPasteCount(count) {
      if (!this.clipboard) return false;
      if (!Number.isInteger(count) || count < 0) {
        throw new TypeError("Clipboard paste count must be a non-negative integer");
      }
      this.clipboard = deepFreeze({ ...clone(this.clipboard), pasteCount: count });
      this.emit("clipboard");
      return true;
    }

    selectedAssetPage() {
      const asset = this.layout.assets.find(
        (item) => item.id === this.assetPanel.selectedAssetId,
      );
      const page = asset?.pages.find(
        (item) => item.number === this.assetPanel.selectedPage,
      );
      return isReadyAsset(asset) && page ? { asset, page } : null;
    }

    applyServerLayout(canonicalLayout) {
      if (!canonicalLayout || canonicalLayout.layout_schema_version !== 2) {
        throw new Error("Server response is not Layout V2");
      }
      if (canonicalLayout.job.id !== this.layout.job.id) {
        throw new Error("Server layout belongs to another job");
      }
      if (this.hasUnsavedChanges() || this.saveState.status === "saving" || this.pointerSession) {
        throw new Error("Cannot apply a server layout while local changes are pending");
      }
      this.layout = clone(canonicalLayout);
      this.syncNewTreeWorks();
      this.revision = canonicalLayout.job.revision;
      this.savedChangeVersion = this.changeVersion;
      this.saveState = {
        status: "clean",
        error: null,
        lastSavedAt: canonicalLayout.job.updated_at,
      };
      this.filterSelection();
      const selectedAsset = this.layout.assets.find(
        (item) => item.id === this.assetPanel.selectedAssetId && isReadyAsset(item),
      );
      const firstReadyAsset = this.layout.assets.find(isReadyAsset);
      if (!selectedAsset && firstReadyAsset) {
        const firstPage = firstReadyAsset.pages[0];
        this.assetPanel = {
          ...this.assetPanel,
          selectedAssetId: firstReadyAsset.id,
          selectedPage: firstPage.number,
          selectedPdfBox: suggestedPdfBox(firstPage),
        };
      }
      this.emit("external_update");
    }

    beginPointerSession(session) {
      this.pointerSession = clone(session);
      this.previewPositions = {};
      this.previewSlots = clone(session?.previewSlots || []);
      this.emit("pointer_start");
    }

    updatePointerPreview(positions) {
      this.previewPositions = clone(positions);
      this.emit("pointer_preview");
    }

    updatePointerPreviewSlots(slots) {
      this.previewSlots = clone(slots || []);
      this.emit("pointer_preview");
    }

    endPointerSession() {
      this.pointerSession = null;
      this.previewPositions = {};
      this.previewSlots = [];
      this.emit("pointer_end");
    }

    effectivePosition(slot) {
      return this.previewPositions[slot.id] || slot.geometry.position_mm;
    }

    setCursor(position) {
      this.cursorMm = position && Number.isFinite(position.x) && Number.isFinite(position.y)
        ? { x: position.x, y: position.y }
        : { x: null, y: null };
      this.emit("cursor");
    }

    setZoom(value) {
      const next = Math.min(4, Math.max(0.35, value));
      if (Number.isFinite(next) && next !== this.zoom) {
        this.zoom = next;
        this.emit("viewport");
      }
    }

    setPan(position) {
      if (Number.isFinite(position.x) && Number.isFinite(position.y)) {
        this.pan = { x: position.x, y: position.y };
        this.emit("viewport");
      }
    }

    resetView() {
      this.zoom = 1;
      this.pan = { x: 0, y: 0 };
      this.emit("viewport");
    }

    beginSave() {
      if (!this.hasUnsavedChanges()
          || this.saveState.status === "saving"
          || this.saveState.status === "conflict"
          || this.pointerSession) {
        return null;
      }
      this.saveState = { ...this.saveState, status: "saving", error: null };
      const ticket = {
        baseRevision: this.revision,
        layout: clone(this.layout),
        changeVersion: this.changeVersion,
      };
      this.emit("save_start", ticket);
      return ticket;
    }

    completeSave(canonicalLayout, savedVersion) {
      this.revision = canonicalLayout.job.revision;
      this.savedChangeVersion = savedVersion;
      if (this.changeVersion === savedVersion) {
        this.layout = clone(canonicalLayout);
        this.saveState = {
          status: "clean",
          error: null,
          lastSavedAt: canonicalLayout.job.updated_at,
        };
      } else {
        this.layout.job.revision = canonicalLayout.job.revision;
        this.layout.job.created_at = canonicalLayout.job.created_at;
        this.layout.job.updated_at = canonicalLayout.job.updated_at;
        this.saveState = {
          status: "dirty",
          error: null,
          lastSavedAt: canonicalLayout.job.updated_at,
        };
      }
      this.filterSelection();
      this.emit("save_success");
    }

    failSave(error, conflict) {
      this.saveState = {
        ...this.saveState,
        status: conflict ? "conflict" : "save_error",
        error: error && error.message ? error.message : String(error),
      };
      this.emit(conflict ? "save_conflict" : "save_error", error);
    }
  }

  return Object.freeze({
    EditorStore,
    SAVE_STATES,
    deepFreeze,
    sameSet,
    suggestedPdfBox,
  });
});
