(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.EditorOffsetV2 = root.EditorOffsetV2 || {};
  root.EditorOffsetV2.ContentTransformInspector = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const FIT_MODES = Object.freeze(["actual_size", "contain", "cover", "stretch"]);
  const CLIP_TARGETS = Object.freeze(["none", "trim_box", "bleed_box"]);
  const ROTATIONS = Object.freeze([0, 90, 180, 270]);

  function parseNumber(value, label, positive) {
    const number = Number(String(value ?? "").replace(",", "."));
    if (!Number.isFinite(number) || (positive && number <= 0)) {
      throw new Error(`${label} debe ser ${positive ? "mayor que cero" : "finito"}.`);
    }
    return number;
  }

  class Controller {
    constructor(store, refs, commands) {
      this.store = store;
      this.refs = refs;
      this.commands = commands;
      this.dirty = false;
      refs.contentTransformForm.addEventListener("submit", (event) => {
        event.preventDefault();
        this.apply();
      });
      refs.contentTransformReset.addEventListener("click", () => this.reset());
      for (const element of [
        refs.contentFitMode, refs.contentScaleX, refs.contentScaleY,
        refs.contentOffsetX, refs.contentOffsetY, refs.contentRotation,
        refs.contentMirrorX, refs.contentMirrorY, refs.contentClipTo,
      ]) element.addEventListener("input", () => {
        this.dirty = true;
        this.refs.contentTransformError.textContent = "";
        this.refs.contentTransformError.dataset.state = "idle";
        this.renderState();
      });
      this.unsubscribe = store.subscribe(() => this.render());
      this.render();
    }

    selectedSlots() {
      const ids = new Set(this.store.selection);
      return this.store.layout.slots.filter((slot) => ids.has(slot.id));
    }

    readPayload() {
      const rotation = Number(this.refs.contentRotation.value);
      if (!ROTATIONS.includes(rotation)) throw new Error("La rotación debe ser cardinal.");
      const fitMode = this.refs.contentFitMode.value;
      const clipTo = this.refs.contentClipTo.value;
      if (!FIT_MODES.includes(fitMode) || !CLIP_TARGETS.includes(clipTo)) {
        throw new Error("La configuración gráfica no es válida.");
      }
      return {
        fit_mode: fitMode,
        scale_x: parseNumber(this.refs.contentScaleX.value, "La escala X", true),
        scale_y: parseNumber(this.refs.contentScaleY.value, "La escala Y", true),
        offset_mm: {
          x: parseNumber(this.refs.contentOffsetX.value, "El desplazamiento X", false),
          y: parseNumber(this.refs.contentOffsetY.value, "El desplazamiento Y", false),
        },
        rotation_deg: rotation,
        mirror_x: this.refs.contentMirrorX.checked,
        mirror_y: this.refs.contentMirrorY.checked,
        clip_to: clipTo,
      };
    }

    render() {
      const slots = this.selectedSlots();
      const enabled = slots.length > 0 && this.store.saveState.status !== "saving";
      this.refs.contentTransformPanel.hidden = false;
      this.refs.contentTransformEmpty.hidden = slots.length > 0;
      this.refs.contentTransformForm.hidden = slots.length === 0;
      if (!slots.length) {
        this.dirty = false;
        this.renderState();
        return;
      }
      const current = slots[0].content_transform;
      if (!this.dirty) {
        this.refs.contentFitMode.value = current.fit_mode;
        this.refs.contentScaleX.value = String(current.scale_x);
        this.refs.contentScaleY.value = String(current.scale_y);
        this.refs.contentOffsetX.value = String(current.offset_mm.x);
        this.refs.contentOffsetY.value = String(current.offset_mm.y);
        this.refs.contentRotation.value = String(current.rotation_deg);
        this.refs.contentMirrorX.checked = current.mirror_x;
        this.refs.contentMirrorY.checked = current.mirror_y;
        this.refs.contentClipTo.value = current.clip_to;
      }
      for (const element of this.refs.contentTransformForm.elements) element.disabled = !enabled;
      this.refs.contentTransformSelection.textContent = slots.length === 1
        ? "1 slot seleccionado"
        : `${slots.length} slots seleccionados (se aplicará a todos)`;
      this.renderState();
    }

    renderState() {
      const slots = this.selectedSlots();
      this.refs.contentTransformApply.disabled = !slots.length || !this.dirty
        || this.store.saveState.status === "saving";
      this.refs.contentTransformReset.disabled = !slots.length;
    }

    reset() {
      this.refs.contentFitMode.value = "actual_size";
      this.refs.contentScaleX.value = "1";
      this.refs.contentScaleY.value = "1";
      this.refs.contentOffsetX.value = "0";
      this.refs.contentOffsetY.value = "0";
      this.refs.contentRotation.value = "0";
      this.refs.contentMirrorX.checked = false;
      this.refs.contentMirrorY.checked = false;
      this.refs.contentClipTo.value = "none";
      this.dirty = true;
      this.renderState();
    }

    apply() {
      try {
        const slots = this.selectedSlots();
        if (!slots.length) throw new Error("Selecciona al menos un slot.");
        const payload = this.readPayload();
        const command = new this.commands.SetContentTransformCommand(
          this.store.layout,
          slots.map((slot) => slot.id),
          payload,
        );
        this.store.executeCommand(command);
        this.dirty = false;
        this.store.setFeedback("Ajuste gráfico aplicado.", "content-transform");
        this.render();
      } catch (error) {
        this.refs.contentTransformError.textContent = error.message;
        this.refs.contentTransformError.dataset.state = "error";
      }
    }

    dispose() {
      this.unsubscribe();
    }
  }

  return Object.freeze({ Controller, FIT_MODES, CLIP_TARGETS, ROTATIONS });
});
