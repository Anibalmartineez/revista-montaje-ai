(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.EditorOffsetV2 = root.EditorOffsetV2 || {};
  root.EditorOffsetV2.OutputPanel = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const ISSUE_LABELS = Object.freeze({
    BLEED_REQUIRES_EXPLICIT_MIRROR: "Falta sangrado del archivo: en Preparar cambia el PDF o los milímetros, o autoriza espejo para el trabajo",
    BLEED_GENERATED_BY_MIRROR: "Sangrado generado por espejo; revisa visualmente los bordes",
    BLEED_DERIVED_REVIEW: "Sangrado de una página derivada; revisa su origen y los bordes",
    BLEED_CLIPPED_TO_TRIM: "TrimBox recorta el sangrado: selecciona BleedBox en Corrección gráfica",
    CROP_MARK_OVERPRINT: "Una marca invade otra pieza: aumenta la separación o desactiva las marcas",
    CROP_MARK_OUTSIDE_SHEET: "Marcas fuera del pliego: mueve las piezas hacia dentro",
    CROP_MARKS_OMITTED_NO_BLEED: "Sin sangrado: se omiten las marcas de corte de esta pieza",
    DERIVED_SOURCE_MISSING: "No se encuentra la página derivada: vuelve a prepararla",
    NATIVE_VECTOR_PENDING: "El renderer disponible no conserva vectores",
    OUTPUT_RESOURCE_LIMIT: "La petición supera el límite de recursos del perfil",
    OUTPUT_PLACEMENT_LIMIT: "El montaje supera las 500 piezas admitidas por petición: divide la salida",
    OUTPUT_PROFILE_CONFLICT: "El perfil raster no puede conservar vectores: revisa el perfil de salida",
    OUTPUT_FACE_DISABLED: "La cara elegida no está habilitada: selecciona una cara disponible",
    OUTPUT_NO_SLOTS: "La cara elegida no tiene piezas: coloca piezas o selecciona otra cara",
    OUTPUT_CROP_UNSUPPORTED: "La salida conserva el pliego completo: desactiva el recorte al contenido",
    PREVIEW_MARKS_UNSUPPORTED: "Registros, barras de color o texto técnico no están soportados: revisa el perfil de marcas",
    CTP_NOT_SUPPORTED: "CTP todavía no está disponible: utiliza la salida PDF sin CTP",
    PREVIEW_RESOURCE_LIMIT: "La Preview es demasiado grande: selecciona una resolución menor",
    UNSUPPORTED_PDF_LAYERS: "El PDF contiene capas: requiere una política de aplanado",
    UNSUPPORTED_OUTPUT_INTENT: "El PDF contiene un perfil de salida: requiere un flujo de color compatible",
    UNSUPPORTED_CONTENT_CLIP: "Selecciona recorte al tamaño final o al sangrado en Corrección gráfica",
    ASSET_NOT_READY: "Asset no listo o placeholder",
    ASSET_IDENTITY_MISMATCH: "Identidad física del asset distinta",
    ASSET_MISSING: "Asset usado no encontrado",
    ASSET_UNSAFE_PATH: "Ruta física de asset no segura",
    PDF_UNREADABLE: "PDF físico no legible",
    PDF_METADATA_MISMATCH: "Metadata física del PDF distinta",
    PDF_SEMANTICS_UNSUPPORTED: "Página o caja PDF ausente",
    TRIM_OUTSIDE_SHEET: "La pieza sale del pliego: mueve la pieza o revisa el tamaño del pliego",
    BLEED_OUTSIDE_PRINTABLE: "El sangrado sale del área imprimible: mueve la pieza o revisa los márgenes",
    TRIM_OVERLAP: "Las piezas se superponen: revisa su posición y separación",
    BLEED_OVERLAP: "Los sangrados se superponen: aumenta la separación entre piezas",
    OUTPUT_FEATURE_UNSUPPORTED: "Función de salida no soportada todavía",
  });

  const DIAGNOSIS_INVALIDATING_EVENTS = Object.freeze([
    "command",
    "undo",
    "redo",
    "external_update",
    "save_conflict",
    "save_error",
    "pointer_start",
  ]);

  function issueLabel(issue) {
    return (issue.code === "OUTPUT_FEATURE_UNSUPPORTED" && issue.message) || ISSUE_LABELS[issue.code] || issue.message || issue.code;
  }

  const OPERATION_LABELS = Object.freeze({preview: "Preview", pdf_final: "PDF", ctp: "CTP"});

  function groupPreflightIssues(issues, layout) {
    const slots = new Map((layout?.slots || []).map(slot => [slot.id, slot]));
    const works = new Map((layout?.works || []).map(work => [work.id, work]));
    const assets = new Map((layout?.assets || []).map(asset => [asset.id, asset]));
    const groups = new Map();
    for (const issue of issues || []) {
      const refs = issue.references || {};
      const targets = (refs.slot_ids?.length ? refs.slot_ids : [null]);
      for (const slotId of targets) {
        const slot = slots.get(slotId);
        const workId = slot?.work_id || refs.work_ids?.[0] || null;
        const assetId = slot?.source?.asset_id || refs.asset_ids?.[0] || null;
        const page = slot?.source?.page || refs.page_numbers?.[0] || null;
        const blocks = [...new Set(issue.blocks || [])].sort();
        const key = JSON.stringify([issue.severity, issue.code, issue.message, workId, assetId, page,
          blocks, slotId ? "slot" : [refs.asset_ids, refs.work_ids, refs.page_numbers, refs.path]]);
        if (!groups.has(key)) groups.set(key, {
          code: issue.code, level: issue.severity, message: issue.message,
          path: refs.path || null, assetId, workId, page, blocks,
          workName: works.get(workId)?.name || null,
          filename: assets.get(assetId)?.original_filename || null,
          slotIds: [], count: 0,
        });
        const group = groups.get(key);
        group.count += 1;
        if (slotId && !group.slotIds.includes(slotId)) group.slotIds.push(slotId);
      }
    }
    return [...groups.values()].map(group => ({...group, slotIds: group.slotIds.sort()}));
  }

  function renderIssueGroup(group) {
    const item = document.createElement("li");
    item.dataset.code = group.code;
    item.dataset.level = group.level;
    item.dataset.affectedSlots = String(group.slotIds.length);
    const summary = document.createElement("span");
    const scope = [group.workName || group.filename, group.page && `Página ${group.page}`,
      group.slotIds.length && `${group.slotIds.length} pieza${group.slotIds.length === 1 ? "" : "s"} afectada${group.slotIds.length === 1 ? "" : "s"}`].filter(Boolean);
    summary.textContent = `${scope.length ? scope.join(" · ") + ": " : ""}${issueLabel(group)}`;
    const effect = document.createElement("small");
    effect.textContent = group.blocks.length
      ? `Impide: ${group.blocks.map(op => OPERATION_LABELS[op] || op).join(", ")}.`
      : "Aviso: no impide generar salida.";
    const details = document.createElement("details");
    const toggle = document.createElement("summary");
    toggle.textContent = "Detalles técnicos";
    const metadata = document.createElement("p");
    metadata.textContent = [group.code, group.workId, group.assetId, group.path, group.message].filter(Boolean).join(" · ");
    const ids = document.createElement("ul");
    for (const id of group.slotIds) {
      const row = document.createElement("li");
      const code = document.createElement("code");
      code.textContent = id; row.append(code); ids.append(row);
    }
    details.append(toggle, metadata, ids);
    item.append(summary, effect, details);
    return item;
  }

  function operationSummary(report, operation, options = {}) {
    const label = OPERATION_LABELS[operation];
    const decision = report?.decisions?.find(item => item.operation === operation);
    if (!decision) return `${label}: comprobación incompleta.`;
    const reasons = decision.reason_codes || [];
    const messages = [];
    if (reasons.includes("CAPABILITY_GATE_NOT_ENABLED")) messages.push("función desactivada en este servidor");
    if (operation === "preview" && options.face === "both") messages.push("selecciona Frente o Dorso; ambas caras solo se generan en PDF");
    if (decision.blocking_issue_ids?.length || reasons.includes("PREFLIGHT_FINDINGS")) messages.push("requiere corregir los motivos indicados");
    if (report.execution !== "complete" || reasons.includes("PREFLIGHT_INCOMPLETE")) messages.push("comprobación incompleta; vuelve a comprobar");
    if (decision.status === "eligible" && !messages.length) return `${label}: disponible para generar.`;
    return `${label}: ${messages.join("; ") || "salida bloqueada; vuelve a comprobar"}.`;
  }

  class Panel {
    constructor(store, refs, api, saver, context, runAction) {
      this.store = store;
      this.refs = refs;
      this.api = api;
      this.saver = saver;
      this.context = context;
      this.preflightReport = null;
      this.preflightStale = false;
      this.generating = false;
      this.checking = false;
      this.requestSerial = 0;
      this.outputEpoch = 0;
      this.artifactUrl = null;
      this.downloadUrls = [];
      this.artifactRevision = null;
      this.store.outputOptions = {face: "front", dpi: 150, allow_mirror_bleed: false};
      this.unsubscribe = this.store.subscribe((event) => this.onStoreEvent(event));
      for (const button of [refs.preflightRun, refs.outputRecheck]) {
        button?.addEventListener("click", () => runAction("output.preflight"));
      }
      this.refs.outputPreview?.addEventListener("click", () => runAction("output.preview"));
      this.refs.outputPdf?.addEventListener("click", () => runAction("output.pdf"));
      for (const control of [refs.outputFace, refs.outputDpi, refs.outputMirror]) {
        control?.addEventListener("change", () => runAction("output.options"));
      }
      this.renderOutputControls();
    }

    readOutputOptions() {
      return {face: this.refs.outputFace?.value || "front", dpi: Number(this.refs.outputDpi?.value || 150),
        allow_mirror_bleed: Boolean(this.refs.outputMirror?.checked)};
    }

    changeOutputOptions() {
      this.store.outputOptions = this.readOutputOptions();
      this.invalidateArtifact();
      this.invalidatePreflight();
      this.renderOutputControls();
      this.store.setFeedback("Opciones de salida actualizadas; regenera la Preview o el PDF.");
    }

    renderOutputControls() {
      if (this.disposed || !this.refs.outputFace) return;
      if (this.refs.outputProfile) {
        const profile = this.store.layout.export.render_mode === "raster"
          ? "Perfil raster: rasteriza el pliego a la resolución seleccionada."
          : "Perfil PDF nativo: conserva objetos fuente; las imágenes y los derivados mantienen su resolución.";
        this.refs.outputProfile.textContent = `${profile} El espejo añade bandas raster a 300 dpi. Sin conversión de color ni certificación PDF/X. CTP pendiente.`;
      }
      const faces = this.store.layout.faces.enabled.filter((face) => this.store.layout.export.faces[face]);
      for (const option of this.refs.outputFace.options) option.disabled = option.value === "both" ? faces.length !== 2 : !faces.includes(option.value);
      if (this.refs.outputFace.selectedOptions[0]?.disabled) this.refs.outputFace.value = faces[0] || "front";
      const busy = this.generating || this.checking || Boolean(this.store.pointerSession);
      const decisionBlocks = operation => this.reportIsCurrent() && this.preflightReport.decisions.find(d => d.operation === operation)?.status !== "eligible";
      this.refs.outputPreview.disabled = busy || !this.context.preview_api_url || this.refs.outputFace.value === "both" || decisionBlocks("preview");
      this.refs.outputPdf.disabled = busy || !this.context.pdf_final_api_url || decisionBlocks("pdf_final");
      for (const button of [this.refs.preflightRun, this.refs.outputRecheck]) {
        if (button) button.disabled = busy || !this.context.preflight_api_url;
      }
      if (this.refs.outputAvailability) this.refs.outputAvailability.textContent = [
        `Preview: ${this.context.preview_api_url ? "habilitada" : "desactivada en este servidor"}.`,
        `PDF: ${this.context.pdf_final_api_url ? "habilitado" : "desactivado en este servidor"}.`,
        this.refs.outputFace.value === "both" ? "Para Preview elige Frente o Dorso." : "",
      ].filter(Boolean).join(" ");
    }

    invalidateArtifact() {
      this.outputEpoch += 1;
      this.refs.outputFindings?.replaceChildren();
      if (this.artifactUrl) URL.revokeObjectURL(this.artifactUrl);
      this.artifactUrl = null;
      if (this.refs.outputImage) { this.refs.outputImage.hidden = true; this.refs.outputImage.removeAttribute("src"); }
      if (this.artifactRevision !== null && this.refs.outputResult) {
        this.refs.outputResult.textContent = `Resultado desactualizado (revisión ${this.artifactRevision}). Vuelve a generar con las opciones actuales.`;
        this.refs.outputResult.dataset.state = "warning";
      } else if (this.refs.outputResult?.dataset.state === "error") {
        this.refs.outputResult.textContent = "El montaje o las opciones cambiaron. Vuelve a comprobar la salida.";
        this.refs.outputResult.dataset.state = "warning";
      }
      this.artifactRevision = null;
    }

    showOutputFindings(issues, operation) {
      this.refs.outputFindings?.replaceChildren();
      const relevant = operation ? (issues || []).filter(issue => !issue.blocks?.length || issue.blocks.includes(operation)) : issues;
      for (const group of groupPreflightIssues(relevant, this.store.layout)) {
        this.refs.outputFindings?.append(renderIssueGroup(group));
      }
    }

    reportIsCurrent() {
      const report = this.preflightReport;
      return Boolean(report && !this.preflightStale && !this.disposed && !this.store.hasUnsavedChanges()
        && this.store.saveState.status === "clean" && !this.store.pointerSession
        && report.subject.job_id === this.store.layout.job.id && report.subject.revision === this.store.revision
        && this.reportOptions === JSON.stringify(this.readOutputOptions()) && this.reportVersion === this.store.changeVersion);
    }

    renderReport(report) {
      const blocked = report.decisions.filter(d => ["preview", "pdf_final"].includes(d.operation) && d.status === "blocked");
      const state = blocked.some(d => d.blocking_issue_ids?.length) ? "error" : blocked.length ? "warning" : "success";
      this.refs.preflightStatus.textContent = `Diagnóstico completo · revisión ${report.subject.revision}`;
      this.refs.preflightStatus.dataset.state = state;
      const options = this.readOutputOptions();
      const optionLabel = `${({front:"Frente",back:"Dorso",both:"Ambas caras"})[options.face]} · ${options.dpi} dpi · decisiones de sangrado guardadas por trabajo; permiso temporal para trabajos anteriores ${options.allow_mirror_bleed ? "activado" : "desactivado"}.`;
      const summary = `${optionLabel} ${["preview", "pdf_final"].map(op => operationSummary(report, op, options)).join(" ")}`;
      if (this.refs.preflightSummary) this.refs.preflightSummary.textContent = `${summary} CTP todavía no disponible.`;
      if (this.refs.outputDiagnosis) { this.refs.outputDiagnosis.textContent = summary; this.refs.outputDiagnosis.dataset.state = state; }
      this.refs.preflightIssues?.replaceChildren();
      for (const group of groupPreflightIssues(report.issues, this.store.layout)) {
        this.refs.preflightIssues?.append(renderIssueGroup(group));
      }
      this.showOutputFindings(report.issues);
    }

    async analyze() {
      if (this.store.hasUnsavedChanges()) await this.saver.manualSave();
      if (this.store.hasUnsavedChanges() || this.store.saveState.status !== "clean" || this.store.pointerSession) {
        throw new Error("Guarda o resuelve el conflicto antes de comprobar la salida.");
      }
      const serial = ++this.requestSerial, epoch = this.outputEpoch, revision = this.store.revision;
      const version = this.store.changeVersion, jobId = this.store.layout.job.id;
      const options = this.readOutputOptions(), optionsKey = JSON.stringify(options);
      const {report} = await this.api.runPreflight(this.context.preflight_api_url, options);
      if (this.disposed || serial !== this.requestSerial || epoch !== this.outputEpoch
          || this.store.changeVersion !== version || this.store.hasUnsavedChanges() || this.store.saveState.status !== "clean"
          || this.store.pointerSession || this.store.revision !== revision || this.store.layout.job.id !== jobId
          || JSON.stringify(this.readOutputOptions()) !== optionsKey || report.subject.job_id !== jobId || report.subject.revision !== revision) {
        const error = new Error("Diagnóstico desactualizado: cambió el montaje o las opciones. Vuelve a comprobar la salida.");
        error.code = "OUTPUT_STALE"; throw error;
      }
      this.preflightReport = report; this.preflightStale = false;
      this.reportOptions = optionsKey; this.reportVersion = version;
      this.renderReport(report);
      return {report, options, revision, epoch};
    }

    async generate(operation) {
      if (this.generating || this.checking) return;
      const url = operation === "preview" ? this.context.preview_api_url : this.context.pdf_final_api_url;
      if (!url) return;
      this.invalidateArtifact();
      this.generating = true;
      this.renderOutputControls();
      this.refs.outputResult.textContent = "Guardando y comprobando fuentes, geometría y opciones…";
      this.refs.outputResult.dataset.state = "pending";
      this.showOutputFindings([]);
      try {
        const {report, options, revision, epoch} = await this.analyze();
        const current = () => this.outputEpoch === epoch && this.reportIsCurrent();
        this.showOutputFindings(report.issues, operation);
        const decision = report.decisions.find(item => item.operation === operation);
        if (report.execution !== "complete" || decision?.status !== "eligible") {
          const error = new Error(`Salida bloqueada para ${OPERATION_LABELS[operation]}. ${operationSummary(report, operation)}`);
          error.code = "PREFLIGHT_BLOCKED"; throw error;
        }
        this.refs.outputResult.textContent = `Generando ${operation === "preview" ? "Preview" : "PDF"} de la revisión ${revision}…`;
        const result = await this.api.requestArtifact(url, {...options, expected_revision: revision});
        if (!current() || result.revision !== revision) throw new Error("Resultado desactualizado: el montaje cambió. Vuelve a generar.");
        const expectedType = operation === "preview" ? "image/png" : "application/pdf";
        if (result.blob.type !== expectedType || !result.blob.size) throw new Error("El servidor no entregó un archivo válido.");
        const blobUrl = URL.createObjectURL(result.blob);
        this.artifactRevision = revision;
        if (operation === "preview") {
          this.artifactUrl = blobUrl;
          this.refs.outputImage.src = blobUrl;
          this.refs.outputImage.hidden = false;
        } else {
          const link = document.createElement("a"); link.href = blobUrl;
          link.download = result.filename || `montaje-v2-r${revision}.pdf`;
          document.body.append(link); link.click(); link.remove();
          this.downloadUrls.push(blobUrl);
          if (this.downloadUrls.length > 2) URL.revokeObjectURL(this.downloadUrls.shift());
        }
        this.refs.outputResult.textContent = `${operation === "preview" ? "Preview lista" : "PDF listo; descarga iniciada"} · revisión ${revision} · ${options.face} · ${options.dpi} dpi · decisiones de sangrado guardadas por trabajo. ${report.issues.filter(i=>i.severity==="warning").length} advertencia(s).`;
        this.refs.outputResult.dataset.state = "success";
      } catch (error) {
        if (this.disposed) return;
        if (error.issues?.length) this.showOutputFindings(error.issues, operation);
        this.refs.outputResult.textContent = error.code === "PREFLIGHT_BLOCKED" || error.code === "OUTPUT_STALE" || error.message?.startsWith("Resultado desactualizado")
          ? error.message : `No se pudo generar ${OPERATION_LABELS[operation]}. ${error.message || "Vuelve a intentarlo."}`;
        this.refs.outputResult.dataset.state = "error";
      } finally {
        this.generating = false;
        this.renderOutputControls();
      }
    }

    onStoreEvent(event) {
      if (DIAGNOSIS_INVALIDATING_EVENTS.includes(event.type) ||
          (event.type === "save_success" && this.preflightReport?.subject.revision !== this.store.revision)) {
        this.invalidateArtifact();
        this.invalidatePreflight();
      }
      if (event.type === "pointer_end" || DIAGNOSIS_INVALIDATING_EVENTS.includes(event.type) || event.type === "save_success") this.renderOutputControls();
    }

    invalidatePreflight() {
      if (!this.preflightReport && !this.checking && !this.generating) return false;
      this.preflightStale = true;
      const checked = this.preflightReport?.subject.revision;
      const message = `Diagnóstico desactualizado · ${checked ? `se comprobó la revisión ${checked}; la revisión actual es ${this.store.revision}. ` : ""}${this.store.hasUnsavedChanges() ? "Guarda y vuelve" : "Vuelve"} a comprobar la salida con las opciones actuales.`;
      if (this.refs.preflightStatus) {
        this.refs.preflightStatus.textContent = message;
        this.refs.preflightStatus.dataset.state = "warning";
      }
      this.refs.preflightIssues?.replaceChildren();
      if (this.refs.preflightSummary) this.refs.preflightSummary.textContent = "Vuelve a comprobar la salida; el informe anterior ya no autoriza ninguna operación.";
      if (this.refs.outputDiagnosis) { this.refs.outputDiagnosis.textContent = message; this.refs.outputDiagnosis.dataset.state = "warning"; }
      return true;
    }

    async runPreflight() {
      if (this.checking || this.generating || !this.context.preflight_api_url) return;
      this.checking = true;
      this.invalidateArtifact();
      this.preflightReport = null;
      this.preflightStale = true;
      this.renderOutputControls();
      this.refs.preflightStatus.textContent = "Comprobando la revisión guardada, las fuentes y las opciones de salida…";
      this.refs.preflightStatus.dataset.state = "pending";
      this.refs.preflightIssues?.replaceChildren();
      if (this.refs.preflightSummary) this.refs.preflightSummary.textContent = "";
      if (this.refs.outputDiagnosis) this.refs.outputDiagnosis.textContent = "Comprobando salida…";
      try {
        return await this.analyze();
      } catch (error) {
        if (this.disposed) return;
        this.preflightStale = true;
        const message = error.code === "OUTPUT_STALE" ? error.message : `No se pudo comprobar la salida. ${error.message || "Vuelve a intentarlo."}`;
        this.refs.preflightStatus.textContent = message;
        this.refs.preflightStatus.dataset.state = error.code === "OUTPUT_STALE" ? "warning" : "error";
        if (this.refs.outputDiagnosis) this.refs.outputDiagnosis.textContent = message;
      } finally {
        this.checking = false;
        this.renderOutputControls();
      }
    }

    dispose() {
      this.disposed = true;
      this.invalidateArtifact();
      this.downloadUrls.forEach(url => URL.revokeObjectURL(url));
      this.unsubscribe?.();
      this.unsubscribe = null;
    }
  }

  return Object.freeze({
    ISSUE_LABELS,
    DIAGNOSIS_INVALIDATING_EVENTS,
    Panel,
    groupPreflightIssues,
    operationSummary,
    issueLabel,
    renderIssueGroup,
  });
});
