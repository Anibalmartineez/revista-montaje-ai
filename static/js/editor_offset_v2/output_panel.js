(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.EditorOffsetV2 = root.EditorOffsetV2 || {};
  root.EditorOffsetV2.OutputPanel = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const ISSUE_LABELS = Object.freeze({
    UNSUPPORTED_SOURCE_PAGE: "Página distinta de 1 no soportada",
    UNSUPPORTED_PDF_BOX: "Caja PDF distinta de TrimBox no soportada",
    UNSUPPORTED_INTRINSIC_ROTATION: "Rotación intrínseca no soportada",
    UNSUPPORTED_CONTENT_FIT_MODE: "Modo de ajuste interno no soportado",
    UNSUPPORTED_CONTENT_SCALE: "Escala interna no soportada",
    UNSUPPORTED_CONTENT_OFFSET: "Desplazamiento interno no soportado",
    UNSUPPORTED_CONTENT_ROTATION: "Rotación interna no soportada",
    UNSUPPORTED_CONTENT_MIRROR: "Espejo interno no soportado",
    UNSUPPORTED_CONTENT_CLIP: "Recorte interno no soportado",
    SOURCE_TRIM_SIZE_MISMATCH: "Tamaño fuente/trim incompatible",
    ASSET_NOT_READY: "Asset no listo o placeholder",
  });

  function issueLabel(issue) {
    return ISSUE_LABELS[issue.code] || issue.message || issue.code;
  }

  class Panel {
    constructor(store, refs, api, saver, context) {
      this.store = store;
      this.refs = refs;
      this.api = api;
      this.saver = saver;
      this.context = context;
      this.refs.outputCheck.addEventListener("click", () => this.check());
    }

    async check() {
      this.refs.outputCheck.disabled = true;
      this.refs.outputStatus.textContent = "Analizando la última revisión guardada…";
      this.refs.outputIssues.replaceChildren();
      try {
        if (this.store.hasUnsavedChanges()) await this.saver.manualSave();
        if (this.store.saveState.status !== "clean") {
          throw new Error("Guarda o resuelve el conflicto antes de consultar la compatibilidad.");
        }
        const result = await this.api.getOutputCapabilities(
          this.context.output_capabilities_api_url,
        );
        this.refs.outputStatus.textContent = result.compatible
          ? `Compatible con salida temporal · revisión ${result.revision}`
          : `No compatible con salida temporal · revisión ${result.revision}`;
        this.refs.outputStatus.dataset.state = result.compatible ? "success" : "error";
        for (const issue of result.issues) {
          const item = document.createElement("li");
          const subject = issue.slot_id || issue.asset_id || issue.path;
          item.textContent = `${issueLabel(issue)}${subject ? ` · ${subject}` : ""}`;
          item.dataset.code = issue.code;
          item.dataset.level = issue.level;
          this.refs.outputIssues.append(item);
        }
      } catch (error) {
        this.refs.outputStatus.textContent = error.message || "No se pudo consultar la compatibilidad.";
        this.refs.outputStatus.dataset.state = "error";
      } finally {
        this.refs.outputCheck.disabled = false;
      }
    }
  }

  return Object.freeze({ ISSUE_LABELS, Panel, issueLabel });
});
