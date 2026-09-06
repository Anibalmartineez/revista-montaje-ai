(function (root, factory) {
  "use strict";
  const geometry = typeof module === "object" && module.exports
    ? require("./geometry_view.js")
    : root.EditorOffsetV2?.GeometryView;
  const api = factory(geometry);
  if (typeof module === "object" && module.exports) module.exports = api;
  root.EditorOffsetV2 = root.EditorOffsetV2 || {};
  root.EditorOffsetV2.SheetPanel = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function (DefaultGeometry) {
  "use strict";

  const FIELD_NAMES = Object.freeze([
    "width",
    "height",
    "left",
    "right",
    "bottom",
    "top",
  ]);

  function parseMillimetres(value) {
    if (typeof value === "number") return Number.isFinite(value) ? value : null;
    const normalized = String(value ?? "").trim().replace(",", ".");
    if (!normalized) return null;
    const numeric = Number(normalized);
    return Number.isFinite(numeric) ? numeric : null;
  }

  function validateSheetDraft(draft) {
    const values = Object.fromEntries(
      FIELD_NAMES.map((name) => [name, parseMillimetres(draft?.[name])]),
    );
    const errors = {};
    for (const name of ["width", "height"]) {
      if (values[name] === null || values[name] <= 0) {
        errors[name] = "Debe ser mayor que cero.";
      }
    }
    for (const name of ["left", "right", "bottom", "top"]) {
      if (values[name] === null || values[name] < 0) {
        errors[name] = "Debe ser cero o mayor.";
      }
    }
    if (!errors.width && !errors.left && !errors.right
        && values.left + values.right >= values.width) {
      errors.left = "Izquierda + derecha debe ser menor que el ancho.";
      errors.right = errors.left;
    }
    if (!errors.height && !errors.bottom && !errors.top
        && values.bottom + values.top >= values.height) {
      errors.bottom = "Inferior + superior debe ser menor que el alto.";
      errors.top = errors.bottom;
    }
    const valid = Object.keys(errors).length === 0;
    return Object.freeze({
      valid,
      values: Object.freeze(values),
      errors: Object.freeze(errors),
      sheet: valid ? Object.freeze({
        size_mm: Object.freeze({ width: values.width, height: values.height }),
        printable_margins_mm: Object.freeze({
          left: values.left,
          right: values.right,
          bottom: values.bottom,
          top: values.top,
        }),
      }) : null,
    });
  }

  function sameSheet(left, right) {
    if (!left || !right) return false;
    return left.size_mm.width === right.size_mm.width
      && left.size_mm.height === right.size_mm.height
      && left.printable_margins_mm.left === right.printable_margins_mm.left
      && left.printable_margins_mm.right === right.printable_margins_mm.right
      && left.printable_margins_mm.bottom === right.printable_margins_mm.bottom
      && left.printable_margins_mm.top === right.printable_margins_mm.top;
  }

  function sheetFingerprint(sheet) {
    return JSON.stringify([
      sheet.size_mm.width,
      sheet.size_mm.height,
      sheet.printable_margins_mm.left,
      sheet.printable_margins_mm.right,
      sheet.printable_margins_mm.bottom,
      sheet.printable_margins_mm.top,
    ]);
  }

  function placementImpact(layout, nextSheet, geometry) {
    const engine = geometry || DefaultGeometry;
    if (!engine?.classifySlotPlacement) {
      throw new Error("La geometría del pliego no está disponible.");
    }
    const result = { total: 0, inside: 0, outsideSheet: 0, outsidePrintable: 0 };
    for (const slot of layout?.slots || []) {
      result.total += 1;
      const placement = engine.classifySlotPlacement(slot, nextSheet);
      if (placement === "outside_sheet") result.outsideSheet += 1;
      else if (placement === "outside_printable") result.outsidePrintable += 1;
      else result.inside += 1;
    }
    result.warningCount = result.outsideSheet + result.outsidePrintable;
    return Object.freeze(result);
  }

  function formatMillimetres(value) {
    const rounded = Math.round(Number(value) * 1000) / 1000;
    return String(rounded).replace(".", ",");
  }

  function usefulArea(sheet) {
    return Object.freeze({
      width: sheet.size_mm.width
        - sheet.printable_margins_mm.left
        - sheet.printable_margins_mm.right,
      height: sheet.size_mm.height
        - sheet.printable_margins_mm.bottom
        - sheet.printable_margins_mm.top,
    });
  }

  function impactLabel(impact) {
    if (!impact.total) return "Sin slots que comprobar.";
    return `${impact.inside} dentro · ${impact.outsideSheet} fuera del pliego`
      + ` · ${impact.outsidePrintable} fuera del área imprimible.`;
  }

  class Panel {
    constructor(store, refs, geometry, actionId, runAction, isActionEnabled) {
      this.store = store;
      this.refs = refs;
      this.geometry = geometry || DefaultGeometry;
      this.actionId = actionId;
      this.runAction = runAction;
      this.isActionEnabled = typeof isActionEnabled === "function"
        ? isActionEnabled
        : () => true;
      this.pendingConfirmation = null;
      this.listeners = [];
      this.unsubscribe = this.store.subscribe((event) => this.onStoreEvent(event));
      this.bind();
      this.syncFromLayout(true);
    }

    listen(element, type, listener) {
      element.addEventListener(type, listener);
      this.listeners.push(() => element.removeEventListener(type, listener));
    }

    inputs() {
      return {
        width: this.refs.sheetWidth,
        height: this.refs.sheetHeight,
        left: this.refs.sheetMarginLeft,
        right: this.refs.sheetMarginRight,
        bottom: this.refs.sheetMarginBottom,
        top: this.refs.sheetMarginTop,
      };
    }

    readDraft() {
      return Object.fromEntries(
        Object.entries(this.inputs()).map(([name, input]) => [name, input.value]),
      );
    }

    setStatus(message, state) {
      this.refs.sheetStatus.textContent = message || "";
      this.refs.sheetStatus.dataset.state = state || "idle";
    }

    clearConfirmation() {
      this.pendingConfirmation = null;
      this.refs.sheetApply.textContent = "Aplicar configuración";
    }

    setValidity(result) {
      for (const [name, input] of Object.entries(this.inputs())) {
        const error = result.errors[name] || "";
        input.setAttribute("aria-invalid", String(Boolean(error)));
        input.title = error;
      }
    }

    renderDraft(options) {
      const settings = options || {};
      const result = validateSheetDraft(this.readDraft());
      this.setValidity(result);
      this.refs.sheetApply.disabled = !result.valid || !this.isActionEnabled(this.actionId);
      if (!result.valid) {
        this.refs.sheetUsefulArea.textContent = "Área útil: —";
        this.refs.sheetImpact.textContent = "Corrige los valores para calcular el impacto.";
        if (settings.announce !== false) {
          const firstError = Object.values(result.errors)[0];
          this.setStatus(firstError || "La configuración no es válida.", "error");
        }
        return result;
      }
      const area = usefulArea(result.sheet);
      const impact = placementImpact(this.store.layout, result.sheet, this.geometry);
      this.refs.sheetUsefulArea.textContent = `Área útil: ${formatMillimetres(area.width)}`
        + ` × ${formatMillimetres(area.height)} mm`;
      this.refs.sheetImpact.textContent = impactLabel(impact);
      if (settings.announce !== false) {
        this.setStatus(
          impact.warningCount
            ? "Hay slots que quedarían fuera. Se pedirá una segunda confirmación."
            : "La configuración es válida y no desplaza ningún slot fuera de límites.",
          impact.warningCount ? "warning" : "ready",
        );
      }
      return Object.freeze({ ...result, impact });
    }

    syncFromLayout(force) {
      if (!force && this.refs.sheetForm.contains(document.activeElement)) return;
      const sheet = this.store.layout.sheet;
      const values = {
        width: sheet.size_mm.width,
        height: sheet.size_mm.height,
        left: sheet.printable_margins_mm.left,
        right: sheet.printable_margins_mm.right,
        bottom: sheet.printable_margins_mm.bottom,
        top: sheet.printable_margins_mm.top,
      };
      for (const [name, input] of Object.entries(this.inputs())) {
        input.value = String(values[name]);
      }
      this.clearConfirmation();
      this.renderDraft({ announce: false });
    }

    onInput() {
      this.clearConfirmation();
      this.renderDraft();
    }

    onSwap() {
      const beforeWidth = this.refs.sheetWidth.value;
      this.refs.sheetWidth.value = this.refs.sheetHeight.value;
      this.refs.sheetHeight.value = beforeWidth;
      this.clearConfirmation();
      this.renderDraft();
      this.refs.sheetWidth.focus();
    }

    onReset() {
      this.syncFromLayout(true);
      this.setStatus("Se restauraron los valores guardados del pliego.", "idle");
    }

    onSubmit(event) {
      event.preventDefault();
      const result = this.renderDraft();
      if (!result.valid) {
        const firstInvalid = Object.values(this.inputs())
          .find((input) => input.getAttribute("aria-invalid") === "true");
        firstInvalid?.focus();
        return false;
      }
      if (sameSheet(this.store.layout.sheet, result.sheet)) {
        this.clearConfirmation();
        this.setStatus("El pliego ya tiene esos valores.", "idle");
        return false;
      }
      const fingerprint = sheetFingerprint(result.sheet);
      if (result.impact.warningCount && this.pendingConfirmation !== fingerprint) {
        this.pendingConfirmation = fingerprint;
        this.refs.sheetApply.textContent = "Confirmar cambio";
        this.setStatus(
          `Advertencia: ${result.impact.outsideSheet} fuera del pliego y `
          + `${result.impact.outsidePrintable} fuera del área imprimible. `
          + "Los slots conservarán tamaño y posición; no se moverán ni escalarán. "
          + "Vuelve a confirmar para aplicar.",
          "warning",
        );
        return false;
      }
      const applied = this.runAction(this.actionId, { sheet: result.sheet });
      if (!applied) return false;
      this.clearConfirmation();
      this.setStatus(
        `Pliego actualizado. ${impactLabel(result.impact)} `
        + "Los slots conservaron tamaño y posición.",
        result.impact.warningCount ? "warning" : "success",
      );
      return true;
    }

    onStoreEvent(event) {
      if (["undo", "redo", "external_update"].includes(event.type)) {
        this.syncFromLayout(true);
        const labels = {
          undo: "Se deshizo la última configuración del pliego.",
          redo: "Se rehízo la configuración del pliego.",
          external_update: "Se cargó la configuración remota del pliego.",
        };
        this.setStatus(labels[event.type], "idle");
        return;
      }
      if (event.type === "command") {
        if (event.detail?.description === "Configurar pliego") {
          this.syncFromLayout(false);
        } else {
          this.renderDraft({ announce: false });
        }
      }
    }

    bind() {
      for (const input of Object.values(this.inputs())) {
        this.listen(input, "input", () => this.onInput());
      }
      this.listen(this.refs.sheetSwap, "click", () => this.onSwap());
      this.listen(this.refs.sheetReset, "click", () => this.onReset());
      this.listen(this.refs.sheetForm, "submit", (event) => this.onSubmit(event));
    }

    destroy() {
      for (const remove of this.listeners.splice(0)) remove();
      if (this.unsubscribe) this.unsubscribe();
      this.unsubscribe = null;
    }
  }

  return Object.freeze({
    Panel,
    FIELD_NAMES,
    parseMillimetres,
    validateSheetDraft,
    sameSheet,
    sheetFingerprint,
    placementImpact,
    usefulArea,
    impactLabel,
    formatMillimetres,
  });
});
