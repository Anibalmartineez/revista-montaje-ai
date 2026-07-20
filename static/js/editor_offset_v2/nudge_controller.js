(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.EditorOffsetV2 = root.EditorOffsetV2 || {};
  root.EditorOffsetV2.NudgeController = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const NUDGE_TIMEOUT_MS = 240;

  function selectionSignature(ids) {
    return [...ids].sort().join("\0");
  }

  function positionsForSelection(layout, ids) {
    const requested = new Set(ids);
    const positions = {};
    for (const slot of layout.slots) {
      if (requested.has(slot.id)) {
        positions[slot.id] = {
          x_mm: slot.geometry.position_mm.x_mm,
          y_mm: slot.geometry.position_mm.y_mm,
        };
      }
    }
    if (Object.keys(positions).length !== requested.size) {
      throw new Error("La selección cambió y la sesión de nudge no puede continuar.");
    }
    return positions;
  }

  function moved(beforePositions, afterPositions) {
    return Object.keys(beforePositions).some((id) => (
      beforePositions[id].x_mm !== afterPositions[id].x_mm
      || beforePositions[id].y_mm !== afterPositions[id].y_mm
    ));
  }

  class Controller {
    constructor(store, commands, editPolicy, options) {
      this.store = store;
      this.commands = commands;
      this.editPolicy = editPolicy;
      this.timeoutMs = options?.timeoutMs ?? NUDGE_TIMEOUT_MS;
      this.setTimer = options?.setTimeout || setTimeout;
      this.clearTimer = options?.clearTimeout || clearTimeout;
      this.timer = null;
      this.session = null;
      this.committing = false;
      this.unsubscribe = store.subscribe((event) => this.onStoreEvent(event));
      this.removeBeforeCommandHook = typeof store.addBeforeCommandHook === "function"
        ? store.addBeforeCommandHook(() => {
          if (this.session && !this.committing) this.finish();
        })
        : () => {};
    }

    isActive() {
      return Boolean(this.session);
    }

    currentSelectionIds() {
      return [...this.store.selection];
    }

    compatible(payload, ids) {
      return Boolean(this.session)
        && this.session.direction === payload.direction
        && this.session.step === payload.step
        && this.session.selectionKey === selectionSignature(ids);
    }

    start(payload, ids) {
      this.editPolicy.assertCan(this.store.layout, ids, "move");
      const beforePositions = positionsForSelection(this.store.layout, ids);
      this.session = {
        type: "nudge",
        direction: payload.direction,
        step: payload.step,
        selectionKey: selectionSignature(ids),
        affectedIds: [...ids],
        beforePositions,
        afterPositions: structuredClone(beforePositions),
        deltaX: 0,
        deltaY: 0,
        changed: false,
      };
      this.store.beginPointerSession({
        type: "nudge",
        direction: payload.direction,
        step: payload.step,
        affectedIds: [...ids],
        beforePositions,
      });
    }

    handleKeyDown(payload) {
      if (!payload || !Number.isFinite(payload.dx) || !Number.isFinite(payload.dy)
          || !Number.isFinite(payload.step) || payload.step <= 0) {
        throw new TypeError("Nudge requires a finite direction and positive step");
      }
      const ids = this.currentSelectionIds();
      if (!ids.length) return false;
      if (this.session && !this.compatible(payload, ids)) this.finish();
      if (!this.session) this.start(payload, ids);

      this.session.deltaX += payload.dx;
      this.session.deltaY += payload.dy;
      const next = {};
      for (const [id, position] of Object.entries(this.session.beforePositions)) {
        next[id] = {
          x_mm: position.x_mm + this.session.deltaX,
          y_mm: position.y_mm + this.session.deltaY,
        };
      }
      this.session.afterPositions = next;
      this.session.changed = moved(this.session.beforePositions, next);
      this.store.updatePointerPreview(next);
      this.armTimeout();
      return true;
    }

    armTimeout() {
      if (this.timer !== null) this.clearTimer(this.timer);
      this.timer = this.setTimer(() => {
        this.timer = null;
        this.finish();
      }, this.timeoutMs);
    }

    handleKeyUp(direction) {
      if (this.session && this.session.direction === direction) return this.finish();
      return false;
    }

    finish() {
      if (!this.session) return false;
      if (this.timer !== null) {
        this.clearTimer(this.timer);
        this.timer = null;
      }
      const session = this.session;
      this.session = null;
      this.store.endPointerSession();
      if (!session.changed || !moved(session.beforePositions, session.afterPositions)) return false;
      try {
        positionsForSelection(this.store.layout, session.affectedIds);
        this.committing = true;
        this.store.executeCommand(new this.commands.MoveSlotsCommand(
          session.beforePositions,
          session.afterPositions,
        ));
        return true;
      } catch (error) {
        this.store.setFeedback(error.message || "No se pudo confirmar el nudge.");
        return false;
      } finally {
        this.committing = false;
      }
    }

    cancel() {
      if (!this.session) return false;
      if (this.timer !== null) {
        this.clearTimer(this.timer);
        this.timer = null;
      }
      this.session = null;
      this.store.endPointerSession();
      return true;
    }

    onStoreEvent(event) {
      if (event.type === "selection" && this.session
          && this.session.selectionKey !== selectionSignature(this.currentSelectionIds())) {
        this.finish();
      }
    }

    dispose() {
      if (this.session) this.cancel();
      if (this.timer !== null) this.clearTimer(this.timer);
      this.unsubscribe();
      this.removeBeforeCommandHook();
    }
  }

  return Object.freeze({
    Controller,
    NUDGE_TIMEOUT_MS,
    moved,
    positionsForSelection,
    selectionSignature,
  });
});
