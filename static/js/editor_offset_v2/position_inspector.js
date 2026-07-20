(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.EditorOffsetV2 = root.EditorOffsetV2 || {};
  root.EditorOffsetV2.PositionInspector = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const DECIMAL_PATTERN = /^[+-]?(?:\d+(?:[.,]\d*)?|[.,]\d+)$/;

  function parseMillimetres(rawValue) {
    const text = String(rawValue ?? "").trim();
    if (!text || !DECIMAL_PATTERN.test(text)) {
      return Object.freeze({ ok: false, value: null, error: "Introduce un número finito en milímetros." });
    }
    const value = Number(text.replace(",", "."));
    if (!Number.isFinite(value)) {
      return Object.freeze({ ok: false, value: null, error: "Introduce un número finito en milímetros." });
    }
    return Object.freeze({ ok: true, value, error: null });
  }

  function uniqueIds(slotIds) {
    return [...new Set(slotIds || [])];
  }

  function finite(value, name) {
    if (!Number.isFinite(value)) throw new TypeError(`${name} must be finite millimetres`);
    return value;
  }

  function buildMovePlan(layout, slotIds, mode, payload) {
    const affectedIds = uniqueIds(slotIds);
    const slotsById = new Map((layout?.slots || []).map((slot) => [slot.id, slot]));
    const missing = affectedIds.filter((id) => !slotsById.has(id));
    if (missing.length) throw new Error(`No existen los slots: ${missing.join(", ")}.`);
    if (!affectedIds.length) throw new Error("Se requiere una selección para mover.");
    if (mode === "absolute" && affectedIds.length !== 1) {
      throw new Error("La posición absoluta requiere exactamente un slot.");
    }
    if (mode === "delta" && affectedIds.length < 2) {
      throw new Error("El desplazamiento requiere al menos dos slots.");
    }
    if (!['absolute', 'delta'].includes(mode)) throw new Error(`Unknown positioning mode: ${mode}`);

    const beforePositions = {};
    const afterPositions = {};
    const absoluteX = mode === "absolute" ? finite(payload?.x_mm, "x_mm") : null;
    const absoluteY = mode === "absolute" ? finite(payload?.y_mm, "y_mm") : null;
    const deltaX = mode === "delta" ? finite(payload?.dx_mm, "dx_mm") : null;
    const deltaY = mode === "delta" ? finite(payload?.dy_mm, "dy_mm") : null;
    let changed = false;

    for (const id of affectedIds) {
      const position = slotsById.get(id).geometry.position_mm;
      const before = { x_mm: position.x_mm, y_mm: position.y_mm };
      const after = mode === "absolute"
        ? { x_mm: absoluteX, y_mm: absoluteY }
        : { x_mm: position.x_mm + deltaX, y_mm: position.y_mm + deltaY };
      beforePositions[id] = before;
      afterPositions[id] = after;
      changed ||= before.x_mm !== after.x_mm || before.y_mm !== after.y_mm;
    }
    return Object.freeze({
      affectedIds: Object.freeze(affectedIds),
      beforePositions: Object.freeze(beforePositions),
      afterPositions: Object.freeze(afterPositions),
      changed,
    });
  }

  function formatMillimetres(value) {
    return Number(value).toFixed(3);
  }

  class Controller {
    constructor(store, refs, registry, contextProvider, editPolicy, actionIds) {
      this.store = store;
      this.refs = refs;
      this.registry = registry;
      this.contextProvider = contextProvider;
      this.editPolicy = editPolicy;
      this.actionIds = actionIds;
      this.selectionKey = "";
      this.mode = null;
      this.basePositions = {};
      this.draftDirty = false;
      this.touchedX = false;
      this.touchedY = false;
      this.boundSubmit = (event) => {
        event.preventDefault();
        this.confirmPending();
      };
      this.boundInputX = () => this.onInput("x");
      this.boundInputY = () => this.onInput("y");
      refs.positionForm.addEventListener("submit", this.boundSubmit);
      refs.positionX.addEventListener("input", this.boundInputX);
      refs.positionY.addEventListener("input", this.boundInputY);
      this.unsubscribe = store.subscribe((event) => this.onStoreEvent(event));
      this.render(true);
    }

    selectedSlots() {
      const ids = new Set(this.store.selection);
      return this.store.layout.slots.filter((slot) => ids.has(slot.id));
    }

    currentSelectionKey() {
      return this.selectedSlots().map((slot) => slot.id).sort().join("\0");
    }

    hasPendingDraft() {
      return this.draftDirty;
    }

    hasInvalidDraft() {
      return this.draftDirty && !this.readPayload(false).ok;
    }

    onInput(axis) {
      this.draftDirty = true;
      if (axis === "x") this.touchedX = true;
      if (axis === "y") this.touchedY = true;
      this.validateAndRenderError(false);
      this.updateDisabledState();
      this.store.emit("position_draft");
    }

    onStoreEvent() {
      const nextKey = this.currentSelectionKey();
      if (nextKey !== this.selectionKey && this.draftDirty) {
        this.selectionKey = nextKey;
        this.draftDirty = false;
        this.touchedX = false;
        this.touchedY = false;
        this.store.setFeedback("La edición numérica pendiente se descartó al cambiar la selección.");
        this.render(true);
        return;
      }
      this.render(false);
    }

    captureBase(slots) {
      this.basePositions = Object.fromEntries(slots.map((slot) => [slot.id, {
        x_mm: slot.geometry.position_mm.x_mm,
        y_mm: slot.geometry.position_mm.y_mm,
      }]));
    }

    previewDelta(slots) {
      if (!this.store.pointerSession || this.store.pointerSession.type !== "nudge" || !slots.length) {
        return { x_mm: 0, y_mm: 0 };
      }
      const id = slots[0].id;
      const before = this.store.pointerSession.beforePositions?.[id];
      const after = this.store.previewPositions[id];
      return before && after
        ? { x_mm: after.x_mm - before.x_mm, y_mm: after.y_mm - before.y_mm }
        : { x_mm: 0, y_mm: 0 };
    }

    render(force) {
      const slots = this.selectedSlots();
      const nextKey = slots.map((slot) => slot.id).sort().join("\0");
      const nextMode = slots.length === 1 ? "absolute" : slots.length >= 2 ? "delta" : null;
      const selectionChanged = nextKey !== this.selectionKey || nextMode !== this.mode;
      if (selectionChanged) {
        this.selectionKey = nextKey;
        this.mode = nextMode;
        this.draftDirty = false;
        this.touchedX = false;
        this.touchedY = false;
      }
      this.refs.positionEmpty.hidden = Boolean(nextMode);
      this.refs.positionForm.hidden = !nextMode;
      if (!nextMode) {
        this.refs.positionEmpty.textContent = "Selecciona un slot.";
        this.clearError();
        return;
      }

      this.captureBase(slots);
      this.refs.positionSelectionCount.textContent = slots.length === 1
        ? "1 slot seleccionado"
        : `${slots.length} slots seleccionados`;
      this.refs.positionXLabel.textContent = nextMode === "absolute" ? "Centro X" : "Delta X";
      this.refs.positionYLabel.textContent = nextMode === "absolute" ? "Centro Y" : "Delta Y";
      this.refs.positionApply.textContent = nextMode === "absolute" ? "Aplicar posición" : "Aplicar desplazamiento";

      if (force || selectionChanged || !this.draftDirty) {
        if (nextMode === "absolute") {
          const position = this.store.effectivePosition(slots[0]);
          this.refs.positionX.value = formatMillimetres(position.x_mm);
          this.refs.positionY.value = formatMillimetres(position.y_mm);
        } else {
          const delta = this.previewDelta(slots);
          this.refs.positionX.value = formatMillimetres(delta.x_mm);
          this.refs.positionY.value = formatMillimetres(delta.y_mm);
        }
        this.clearError();
      }
      this.updateDisabledState();
    }

    blockedIds() {
      return this.editPolicy.blockedSlotIds(
        this.store.layout,
        [...this.store.selection],
        "move",
      );
    }

    updateDisabledState() {
      const blocked = this.blockedIds();
      const saving = this.store.saveState.status === "saving";
      const disabled = blocked.length > 0 || saving;
      this.refs.positionX.disabled = disabled;
      this.refs.positionY.disabled = disabled;
      this.refs.positionApply.disabled = disabled || this.hasInvalidDraft();
      this.refs.positionLock.textContent = blocked.length
        ? `Movimiento bloqueado: ${blocked.join(", ")}.`
        : saving ? "Guardando…" : "Posición canónica: centro trim, milímetros.";
      this.refs.positionLock.dataset.state = blocked.length ? "error" : "ready";
    }

    readPayload(showError) {
      if (!this.mode) return { ok: false, error: "No hay una selección editable." };
      const parsedX = parseMillimetres(this.refs.positionX.value);
      const parsedY = parseMillimetres(this.refs.positionY.value);
      if (!parsedX.ok || !parsedY.ok) {
        const result = { ok: false, error: "X e Y deben ser números finitos; se acepta punto o coma decimal." };
        if (showError) this.setError(result.error, !parsedX.ok, !parsedY.ok);
        return result;
      }
      if (this.mode === "absolute") {
        const slotId = [...this.store.selection][0];
        const base = this.basePositions[slotId];
        return {
          ok: true,
          payload: {
            x_mm: this.touchedX ? parsedX.value : base.x_mm,
            y_mm: this.touchedY ? parsedY.value : base.y_mm,
          },
        };
      }
      return { ok: true, payload: { dx_mm: parsedX.value, dy_mm: parsedY.value } };
    }

    validateAndRenderError(showError) {
      const result = this.readPayload(showError);
      if (result.ok) this.clearError();
      else if (!showError) {
        this.refs.positionX.setAttribute("aria-invalid", String(!parseMillimetres(this.refs.positionX.value).ok));
        this.refs.positionY.setAttribute("aria-invalid", String(!parseMillimetres(this.refs.positionY.value).ok));
      }
      return result;
    }

    setError(message, invalidX, invalidY) {
      this.refs.positionError.textContent = message;
      this.refs.positionError.dataset.state = "error";
      this.refs.positionX.setAttribute("aria-invalid", String(Boolean(invalidX)));
      this.refs.positionY.setAttribute("aria-invalid", String(Boolean(invalidY)));
    }

    clearError() {
      this.refs.positionError.textContent = "";
      this.refs.positionError.dataset.state = "idle";
      this.refs.positionX.setAttribute("aria-invalid", "false");
      this.refs.positionY.setAttribute("aria-invalid", "false");
    }

    confirmPending() {
      if (!this.draftDirty) return true;
      const result = this.validateAndRenderError(true);
      if (!result.ok) {
        this.updateDisabledState();
        return false;
      }
      try {
        const actionId = this.mode === "absolute"
          ? this.actionIds.MOVE_ABSOLUTE
          : this.actionIds.MOVE_DELTA;
        this.registry.execute(actionId, this.contextProvider(), result.payload);
        this.draftDirty = false;
        this.touchedX = false;
        this.touchedY = false;
        this.render(true);
        this.store.emit("position_draft");
        return true;
      } catch (error) {
        this.setError(error.message || "No se pudo aplicar la posición.", true, true);
        this.store.setFeedback(error.message);
        this.updateDisabledState();
        return false;
      }
    }

    cancelPending(showFeedback) {
      const hadDraft = this.draftDirty;
      this.draftDirty = false;
      this.touchedX = false;
      this.touchedY = false;
      this.render(true);
      this.store.emit("position_draft");
      if (hadDraft && showFeedback) this.store.setFeedback("Edición numérica cancelada.");
      return hadDraft;
    }

    dispose() {
      this.unsubscribe();
      this.refs.positionForm.removeEventListener("submit", this.boundSubmit);
      this.refs.positionX.removeEventListener("input", this.boundInputX);
      this.refs.positionY.removeEventListener("input", this.boundInputY);
    }
  }

  return Object.freeze({ Controller, buildMovePlan, formatMillimetres, parseMillimetres });
});
