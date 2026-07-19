(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  }
  root.EditorOffsetV2 = root.EditorOffsetV2 || {};
  root.EditorOffsetV2.Autosave = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const AUTOSAVE_DEBOUNCE_MS = 900;

  class SaveCoordinator {
    constructor(store, apiClient, saveUrl, options) {
      this.store = store;
      this.apiClient = apiClient;
      this.saveUrl = saveUrl;
      this.debounceMs = options?.debounceMs ?? AUTOSAVE_DEBOUNCE_MS;
      this.timer = null;
      this.inFlight = null;
      this.disposed = false;
      this.unsubscribe = store.subscribe((event) => {
        if (["command", "undo", "redo"].includes(event.type)) {
          this.schedule();
        }
        if (event.type === "pointer_end" && store.hasUnsavedChanges()) {
          this.schedule();
        }
      });
    }

    schedule(delay) {
      if (this.disposed || this.store.saveState.status === "conflict") {
        return;
      }
      if (this.timer !== null) {
        clearTimeout(this.timer);
      }
      this.timer = setTimeout(() => {
        this.timer = null;
        this.performSave();
      }, delay ?? this.debounceMs);
    }

    manualSave() {
      if (this.timer !== null) {
        clearTimeout(this.timer);
        this.timer = null;
      }
      return this.performSave();
    }

    async performSave() {
      if (this.disposed || this.store.saveState.status === "conflict") {
        return false;
      }
      if (this.inFlight) {
        return this.inFlight;
      }
      if (this.store.pointerSession) {
        this.schedule();
        return false;
      }
      const ticket = this.store.beginSave();
      if (!ticket) {
        return false;
      }
      this.inFlight = (async () => {
        try {
          const response = await this.apiClient.saveLayout(
            this.saveUrl,
            ticket.baseRevision,
            ticket.layout,
          );
          this.store.completeSave(response.layout, ticket.changeVersion);
          return true;
        } catch (error) {
          this.store.failSave(error, error && error.status === 409);
          return false;
        } finally {
          this.inFlight = null;
          if (this.store.saveState.status === "dirty") {
            this.schedule(0);
          }
        }
      })();
      return this.inFlight;
    }

    dispose() {
      this.disposed = true;
      if (this.timer !== null) {
        clearTimeout(this.timer);
      }
      this.unsubscribe();
    }
  }

  return Object.freeze({ AUTOSAVE_DEBOUNCE_MS, SaveCoordinator });
});
