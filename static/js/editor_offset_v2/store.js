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
      this.cursorMm = { x: null, y: null };
      this.pointerSession = null;
      this.previewPositions = {};
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
      this.undoStack = [];
      this.redoStack = [];
      this.changeVersion = 0;
      this.savedChangeVersion = 0;
      this.listeners = new Set();
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
        cursorMm: { ...this.cursorMm },
        pointerSession: this.pointerSession,
        previewPositions: this.previewPositions,
        saveState: { ...this.saveState },
        assetPanel: { ...this.assetPanel },
        canUndo: this.undoStack.length > 0,
        canRedo: this.redoStack.length > 0,
        hasUnsavedChanges: this.hasUnsavedChanges(),
      };
    }

    executeCommand(command) {
      command.execute(this.layout);
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
      this.undoStack.push(command);
      this.markChanged();
      this.filterSelection();
      this.emit("redo", command);
      return true;
    }

    markChanged() {
      this.changeVersion += 1;
      if (this.saveState.status !== "saving" && this.saveState.status !== "conflict") {
        this.saveState = { ...this.saveState, status: "dirty", error: null };
      }
    }

    hasUnsavedChanges() {
      return this.changeVersion !== this.savedChangeVersion;
    }

    setSelection(ids, mode) {
      const validIds = new Set(this.layout.slots.map((slot) => slot.id));
      const incoming = [...ids].filter((id) => validIds.has(id));
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
      this.emit("selection");
    }

    clearSelection() {
      if (this.selection.size) {
        this.selection.clear();
        this.emit("selection");
      }
    }

    filterSelection() {
      const validIds = new Set(this.layout.slots.map((slot) => slot.id));
      this.selection = new Set([...this.selection].filter((id) => validIds.has(id)));
    }

    setHover(id) {
      if (this.hoverId !== id) {
        this.hoverId = id;
        this.emit("hover");
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
      this.emit("pointer_start");
    }

    updatePointerPreview(positions) {
      this.previewPositions = clone(positions);
      this.emit("pointer_preview");
    }

    endPointerSession() {
      this.pointerSession = null;
      this.previewPositions = {};
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

  return Object.freeze({ EditorStore, SAVE_STATES, suggestedPdfBox });
});
