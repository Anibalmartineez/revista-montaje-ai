(function (root, factory) {
  "use strict";
  const positioning = typeof module === "object" && module.exports
    ? require("./position_inspector.js") : root.EditorOffsetV2?.PositionInspector;
  const api = factory(positioning);
  if (typeof module === "object" && module.exports) module.exports = api;
  root.EditorOffsetV2 = root.EditorOffsetV2 || {};
  root.EditorOffsetV2.SizeInspector = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function (PositionInspector) {
  "use strict";

  const parseMillimetres = PositionInspector.parseMillimetres;
  const formatMillimetres = PositionInspector.formatMillimetres;

  class Controller {
    constructor(store, refs, registry, contextProvider, editPolicy, actionIds) {
      Object.assign(this, { store, refs, registry, contextProvider, editPolicy, actionIds });
      this.selectionKey = "";
      this.baseSize = null;
      this.draftDirty = false;
      this.touchedWidth = false;
      this.touchedHeight = false;
      this.boundSubmit = (event) => { event.preventDefault(); this.confirm(); };
      this.boundWidth = () => this.onDimensionInput("width");
      this.boundHeight = () => this.onDimensionInput("height");
      this.boundRatio = () => this.updateDisabledState();
      refs.sizeForm.addEventListener("submit", this.boundSubmit);
      refs.sizeWidth.addEventListener("input", this.boundWidth);
      refs.sizeHeight.addEventListener("input", this.boundHeight);
      refs.sizeLockRatio.addEventListener("change", this.boundRatio);
      this.unsubscribe = store.subscribe(() => this.render());
      this.render(true);
    }

    selectedSlots() {
      const ids = new Set(this.store.selection);
      return this.store.layout.slots.filter((slot) => ids.has(slot.id));
    }

    hasPendingDraft() { return this.draftDirty; }

    onDimensionInput(axis) {
      this.draftDirty = true;
      if (axis === "width") this.touchedWidth = true;
      else this.touchedHeight = true;
      if (this.refs.sizeLockRatio.checked && this.baseSize) {
        const changed = parseMillimetres(axis === "width" ? this.refs.sizeWidth.value : this.refs.sizeHeight.value);
        if (changed.ok && changed.value > 0) {
          const ratio = this.baseSize.width / this.baseSize.height;
          if (axis === "width") {
            this.refs.sizeHeight.value = formatMillimetres(changed.value / ratio);
            this.touchedHeight = true;
          } else {
            this.refs.sizeWidth.value = formatMillimetres(changed.value * ratio);
            this.touchedWidth = true;
          }
        }
      }
      this.updateDisabledState();
    }

    render(force = false) {
      const slots = this.selectedSlots();
      const key = slots.map((slot) => slot.id).sort().join("\0");
      if (key !== this.selectionKey) {
        this.selectionKey = key;
        this.draftDirty = false;
        this.touchedWidth = false;
        this.touchedHeight = false;
        this.refs.sizeLockRatio.checked = false;
        this.baseSize = slots.length === 1 ? { ...slots[0].geometry.trim_size_mm } : null;
      }
      const available = slots.length === 1;
      this.refs.sizeEmpty.hidden = available;
      this.refs.sizeForm.hidden = !available;
      this.refs.sizeEmpty.textContent = slots.length > 1
        ? "Elige un solo slot para editar su medida."
        : "Selecciona un slot en el pliego.";
      if (!available) {
        this.refs.sizeStatus.textContent = this.blockedIds(slots).length
          ? `Tamaño bloqueado: ${this.blockedIds(slots).join(", ")}.`
          : "El centro, la rotación y el sangrado se conservan.";
        return;
      }
      if (force || !this.draftDirty) {
        const size = slots[0].geometry.trim_size_mm;
        this.refs.sizeWidth.value = formatMillimetres(size.width);
        this.refs.sizeHeight.value = formatMillimetres(size.height);
        this.baseSize = { ...size };
        this.touchedWidth = false;
        this.touchedHeight = false;
        this.clearInvalid();
      }
      this.updateDisabledState();
    }

    blockedIds(slots = this.selectedSlots()) {
      return this.editPolicy.blockedSlotIds(this.store.layout, slots.map((slot) => slot.id), "resize");
    }

    updateDisabledState() {
      const slots = this.selectedSlots();
      const blocked = this.blockedIds(slots);
      const saving = ["saving", "conflict"].includes(this.store.saveState.status);
      const disabled = slots.length !== 1 || blocked.length > 0 || saving
        || Boolean(this.store.pointerSession);
      const current = slots.length === 1 ? slots[0].geometry.trim_size_mm : null;
      const value = this.readSize();
      const unchanged = value.ok && current
        && value.payload.width === current.width && value.payload.height === current.height;
      this.refs.sizeWidth.disabled = disabled;
      this.refs.sizeHeight.disabled = disabled;
      this.refs.sizeLockRatio.disabled = disabled;
      this.refs.sizeApply.disabled = disabled || !this.draftDirty || !value.ok || unchanged;
      if (blocked.length) this.refs.sizeStatus.textContent = `Tamaño bloqueado: ${blocked.join(", ")}.`;
      else if (saving) this.refs.sizeStatus.textContent = this.store.saveState.status === "saving"
        ? "Espera a que termine el guardado." : "Recarga la versión remota antes de editar.";
      else if (this.draftDirty && !this.readSize().ok) this.refs.sizeStatus.textContent = this.readSize().error;
      else if (this.draftDirty && unchanged) this.refs.sizeStatus.textContent = "La medida coincide con la actual.";
      else if (!this.draftDirty) this.refs.sizeStatus.textContent = "El centro, la rotación y el sangrado se conservan.";
      else this.refs.sizeStatus.textContent = "El cambio todavía no está aplicado.";
    }

    readSize() {
      const width = this.touchedWidth
        ? parseMillimetres(this.refs.sizeWidth.value)
        : { ok: Boolean(this.baseSize), value: this.baseSize?.width };
      const height = this.touchedHeight
        ? parseMillimetres(this.refs.sizeHeight.value)
        : { ok: Boolean(this.baseSize), value: this.baseSize?.height };
      if (!width.ok || !height.ok) return { ok: false, error: "Introduce ancho y alto válidos en milímetros." };
      if (width.value <= 0 || height.value <= 0) return { ok: false, error: "El ancho y el alto deben ser mayores que cero." };
      return { ok: true, payload: { width: width.value, height: height.value } };
    }

    clearInvalid() {
      this.refs.sizeWidth.setAttribute("aria-invalid", "false");
      this.refs.sizeHeight.setAttribute("aria-invalid", "false");
    }

    confirm() {
      if (!this.draftDirty) return;
      const value = this.readSize();
      if (!value.ok) {
        this.refs.sizeWidth.setAttribute("aria-invalid", String(!parseMillimetres(this.refs.sizeWidth.value).ok
          || Number(this.refs.sizeWidth.value.replace(",", ".")) <= 0));
        this.refs.sizeHeight.setAttribute("aria-invalid", String(!parseMillimetres(this.refs.sizeHeight.value).ok
          || Number(this.refs.sizeHeight.value.replace(",", ".")) <= 0));
        this.updateDisabledState();
        return;
      }
      try {
        this.registry.execute(this.actionIds.RESIZE_SET, this.contextProvider(), value.payload);
        this.draftDirty = false;
        this.render(true);
      } catch (error) {
        this.refs.sizeStatus.textContent = error.message || "No se pudo cambiar la medida.";
        this.store.setFeedback(error.message || String(error));
      }
    }

    cancel() {
      if (!this.draftDirty) return false;
      this.draftDirty = false;
      this.touchedWidth = false;
      this.touchedHeight = false;
      this.render(true);
      return true;
    }

    dispose() {
      this.unsubscribe();
      this.refs.sizeForm.removeEventListener("submit", this.boundSubmit);
      this.refs.sizeWidth.removeEventListener("input", this.boundWidth);
      this.refs.sizeHeight.removeEventListener("input", this.boundHeight);
      this.refs.sizeLockRatio.removeEventListener("change", this.boundRatio);
    }
  }

  return Object.freeze({ Controller });
});
