(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.EditorOffsetV2 = root.EditorOffsetV2 || {};
  root.EditorOffsetV2.ArrangementPanel = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  function matrixPayloadSignature(payload) {
    return JSON.stringify([
      payload.rows,
      payload.columns,
      payload.width,
      payload.height,
      payload.gapX,
      payload.gapY,
    ]);
  }

  function sameIdSelection(left, right) {
    const leftIds = new Set(left || []);
    const rightIds = new Set(right || []);
    if (leftIds.size !== rightIds.size) return false;
    return [...leftIds].every((id) => rightIds.has(id));
  }

  function createMatrixRepeatGuard(selectionAfter, payload) {
    return Object.freeze({
      selectionAfter: Object.freeze([...selectionAfter]),
      payloadSignature: matrixPayloadSignature(payload),
    });
  }

  function shouldBlockMatrixRepeat(guard, selection, payload) {
    return Boolean(guard)
      && guard.payloadSignature === matrixPayloadSignature(payload)
      && sameIdSelection(guard.selectionAfter, selection);
  }

  class Panel {
    constructor(store, refs, registry, contextProvider, actionIds, operations, runAction) {
      this.store = store;
      this.refs = refs;
      this.registry = registry;
      this.contextProvider = contextProvider;
      this.actionIds = actionIds;
      this.operations = operations;
      this.runAction = runAction;
      this.dirtyForms = new Set();
      this.matrixRepeatGuard = null;
      this.bind();
      this.unsubscribe = store.subscribe(() => this.render());
      this.render();
    }

    bind() {
      this.refs.arrangementGeometry.addEventListener("change", () => {
        this.store.setArrangementGeometryReference(this.refs.arrangementGeometry.value);
      });
      for (const button of this.refs.arrangementActionButtons) {
        button.addEventListener("click", () => this.runAction(button.dataset.arrangementAction));
      }
      for (const [form, key, actionId, axis] of [
        [this.refs.arrangementGapHorizontalForm, "gap-horizontal", this.actionIds.GAP_HORIZONTAL, "horizontal"],
        [this.refs.arrangementGapVerticalForm, "gap-vertical", this.actionIds.GAP_VERTICAL, "vertical"],
      ]) {
        form.addEventListener("input", () => this.onDraft(key));
        form.addEventListener("change", () => this.onDraft(key));
        form.addEventListener("submit", (event) => {
          event.preventDefault();
          this.applyGap(axis, actionId, key);
        });
      }
      this.refs.arrangementMatrixForm.addEventListener("input", () => this.onDraft("matrix"));
      this.refs.arrangementMatrixForm.addEventListener("submit", (event) => {
        event.preventDefault();
        this.applyMatrix();
      });
    }

    onDraft(key) {
      this.dirtyForms.add(key);
      if (key === "matrix") this.matrixRepeatGuard = null;
      this.validateDraft(key, false);
      this.renderSummary();
      this.updateFormButtons();
    }

    selectedSlots() {
      const selected = this.store.selection;
      return this.store.layout.slots.filter(
        (slot) => selected.has(slot.id) && slot.face === this.store.activeFace,
      );
    }

    enabled(actionId) {
      return this.registry.isEnabled(actionId, this.contextProvider());
    }

    render() {
      this.refs.arrangementGeometry.value = this.store.arrangement.geometryReference;
      const slots = this.selectedSlots();
      const key = slots.length > 1
        ? slots.find((slot) => slot.id === this.store.arrangement.keySlotId)
        : null;
      const keyLabel = key ? `#${this.store.layout.slots.indexOf(key) + 1}` : null;
      const countLabel = slots.length === 0
        ? "Sin selección"
        : `${slots.length} slot${slots.length === 1 ? "" : "s"}`;
      this.refs.arrangementSelection.textContent = `${countLabel} · Referencia: ${keyLabel || "pliego"}`;
      for (const button of this.refs.arrangementActionButtons) {
        button.disabled = !this.enabled(button.dataset.arrangementAction);
      }
      this.refs.arrangementFeedback.textContent = this.store.feedback || "Estado temporal: no modifica el layout.";
      this.renderSummary();
      this.updateFormButtons();
    }

    gapRefs(axis) {
      return axis === "horizontal"
        ? {
          value: this.refs.arrangementGapHorizontal,
          anchor: null,
          error: this.refs.arrangementGapHorizontalError,
          apply: this.refs.arrangementGapHorizontalApply,
        }
        : {
          value: this.refs.arrangementGapVertical,
          anchor: null,
          error: this.refs.arrangementGapVerticalError,
          apply: this.refs.arrangementGapVerticalApply,
        };
    }

    readGap(axis, showError) {
      const refs = this.gapRefs(axis);
      const parsed = this.operations.parseNonNegativeMillimetres(refs.value.value);
      const error = !parsed.ok ? parsed.error : null;
      refs.value.setAttribute("aria-invalid", String(Boolean(error)));
      refs.error.textContent = showError || error ? (error || "") : "";
      return error
        ? { ok: false, error }
        : { ok: true, payload: { gapMm: parsed.value, anchor: "start" } };
    }

    validateMatrix(showError) {
      const width = this.operations.parsePositiveMillimetres(this.refs.arrangementMatrixWidth.value);
      const height = this.operations.parsePositiveMillimetres(this.refs.arrangementMatrixHeight.value);
      const rows = this.operations.parsePositiveInteger(this.refs.arrangementMatrixRows.value, "Filas");
      const columns = this.operations.parsePositiveInteger(this.refs.arrangementMatrixColumns.value, "Columnas");
      const gapX = this.operations.parseNonNegativeMillimetres(this.refs.arrangementMatrixGapX.value);
      const gapY = this.operations.parseNonNegativeMillimetres(this.refs.arrangementMatrixGapY.value);
      let error = width.error || height.error || rows.error || columns.error || gapX.error || gapY.error;
      let summary = null;
      if (!error) {
        try {
          const payload = { rows: rows.value, columns: columns.value, gapX: gapX.value,
            gapY: gapY.value, width: width.value, height: height.value,
            activeFace: this.store.activeFace };
          const placement = this.operations.findMatrixPlacement(this.store.layout, payload);
          summary = { ...payload, placement, totalCells: rows.value * columns.value };
        } catch (matrixError) {
          error = matrixError.message;
        }
      }
      for (const [element, valid] of [
        [this.refs.arrangementMatrixWidth, width.ok],
        [this.refs.arrangementMatrixHeight, height.ok],
        [this.refs.arrangementMatrixRows, rows.ok],
        [this.refs.arrangementMatrixColumns, columns.ok],
        [this.refs.arrangementMatrixGapX, gapX.ok],
        [this.refs.arrangementMatrixGapY, gapY.ok],
      ]) element.setAttribute("aria-invalid", String(!valid));
      this.refs.arrangementMatrixError.textContent = showError || error ? (error || "") : "";
      return error ? { ok: false, error } : {
        ok: true,
        summary,
        payload: {
          width: width.value,
          height: height.value,
          rows: rows.value,
          columns: columns.value,
          gapX: gapX.value,
          gapY: gapY.value,
          activeFace: this.store.activeFace,
        },
      };
    }

    validateDraft(key, showError) {
      if (key === "gap-horizontal") return this.readGap("horizontal", showError);
      if (key === "gap-vertical") return this.readGap("vertical", showError);
      return this.validateMatrix(showError);
    }

    hasPendingDraft() {
      return this.dirtyForms.size > 0;
    }

    hasInvalidDraft() {
      return [...this.dirtyForms].some((key) => !this.validateDraft(key, false).ok);
    }

    cancelDraft(showFeedback) {
      if (!this.dirtyForms.size) return false;
      this.refs.arrangementGapHorizontal.value = "0";
      this.refs.arrangementGapVertical.value = "0";
      this.refs.arrangementMatrixRows.value = "1";
      this.refs.arrangementMatrixColumns.value = "2";
      this.refs.arrangementMatrixWidth.value = "150";
      this.refs.arrangementMatrixHeight.value = "50";
      this.refs.arrangementMatrixGapX.value = "0";
      this.refs.arrangementMatrixGapY.value = "0";
      this.dirtyForms.clear();
      for (const error of [
        this.refs.arrangementGapHorizontalError,
        this.refs.arrangementGapVerticalError,
        this.refs.arrangementMatrixError,
      ]) error.textContent = "";
      this.renderSummary();
      this.updateFormButtons();
      if (showFeedback) this.store.setFeedback("Borrador de alineación y distribución cancelado.");
      return true;
    }

    applyGap(axis, actionId, key) {
      const result = this.readGap(axis, true);
      if (!result.ok) return false;
      const executed = this.runAction(actionId, result.payload);
      if (executed !== false) this.dirtyForms.delete(key);
      this.updateFormButtons();
      return executed;
    }

    applyMatrix() {
      const result = this.validateMatrix(true);
      if (!result.ok) return false;
      const executed = this.runAction(this.actionIds.MATRIX_CREATE, result.payload);
      if (executed !== false) {
        this.dirtyForms.delete("matrix");
      }
      this.updateFormButtons();
      return executed;
    }

    renderSummary() {
      const result = this.validateMatrix(false);
      this.refs.arrangementMatrixSummary.textContent = result.ok
        ? `${result.summary.totalCells} cuadros · ${result.summary.width} × ${result.summary.height} mm · ubicación X ${result.summary.placement.left.toFixed(1)}, Y ${result.summary.placement.bottom.toFixed(1)} mm.`
        : "Completa una matriz válida para ver el total.";
      if (this.refs.matrixCellStatus) {
        const count = (this.store.layout.matrix_cells || []).filter((cell) => cell.face === this.store.activeFace).length;
        const selected = this.store.matrixCellSelectionIds.size;
        this.refs.matrixCellStatus.textContent = selected
          ? `${selected} cuadro(s) seleccionado(s). Elige un trabajo en Archivos PDF y pulsa “Asignar PDF a ${selected} cuadro(s)”.`
          : count
            ? `${count} cuadro(s) pendiente(s). Mayús o Ctrl + clic para seleccionar varios y asignarles el mismo PDF.`
          : "La matriz se ubica en un espacio libre. Puedes crear otras con medidas distintas; los cuadros pendientes bloquean Preview y PDF hasta asignarlos.";
      }
    }

    updateFormButtons() {
      const canApplyGap = (axis, actionId) => {
        const result = this.readGap(axis, false);
        if (!result.ok || !this.enabled(actionId)) return false;
        try {
          const context = this.contextProvider();
          const plan = this.operations.buildExactGapPlan(
            this.store.layout,
            [...this.store.selection],
            context.geometry,
            {
              ...result.payload,
              axis,
              geometryReference: this.store.arrangement.geometryReference,
              keySlotId: this.store.arrangement.keySlotId,
              activeFace: this.store.activeFace,
            },
          );
          return context.editPolicy.can(this.store.layout, plan.affectedIds, "move");
        } catch (_error) {
          return false;
        }
      };
      this.refs.arrangementGapHorizontalApply.disabled = !canApplyGap(
        "horizontal",
        this.actionIds.GAP_HORIZONTAL,
      );
      this.refs.arrangementGapVerticalApply.disabled = !canApplyGap(
        "vertical",
        this.actionIds.GAP_VERTICAL,
      );
      this.refs.arrangementMatrixApply.disabled = !this.enabled(this.actionIds.MATRIX_CREATE)
        || !this.validateMatrix(false).ok;
    }

    dispose() {
      this.unsubscribe();
    }
  }

  return Object.freeze({
    Panel,
    createMatrixRepeatGuard,
    shouldBlockMatrixRepeat,
  });
});
