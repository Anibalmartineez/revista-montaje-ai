(function () {
  "use strict";

  const apiBase = "/api/pdf-medidor-pro";
  const ns = window.PdfMedidorPro;
  const model = ns.objectModel;
  const undoHistory = ns.undoRedo.createHistory(50);
  const refs = {};
  const state = {
    archivo: "",
    storedFilename: "",
    pagina: 1,
    pageCount: 1,
    pages: {},
    previewUrl: "",
    previewFilename: "",
    renderMm: { ancho: 0, alto: 0 },
    medidasAuto: ns.emptyAuto(),
    mode: "select",
    spacePan: false,
    pointerMm: null,
    hoverSnap: null,
    measurements: [],
    guides: [],
    selectedMeasurementId: null,
    selectedGuideId: null,
    finalMeasurementId: null,
    calibration: { activa: false, factor_escala: 1 },
    finalOrigin: "auto",
    finalConfidence: "media",
    snapEnabled: false,
    showGuides: true,
    includeGuidesInPng: true,
    options: {
      color: "#d97706",
      strokeWidth: 2,
      decimals: 3,
      unit: "mm",
      live: true,
    },
    drawing: null,
    editing: null,
    guideEditing: null,
  };

  let viewer = null;
  let magnifier = null;
  let panning = null;

  document.addEventListener("DOMContentLoaded", init);

  function init() {
    bindRefs();
    viewer = new ns.Viewer({
      container: refs.viewer,
      stage: refs.stage,
      image: refs.previewImage,
      canvas: refs.canvas,
      onChange: renderAll,
    });
    magnifier = new ns.Magnifier({
      viewer,
      element: refs.magnifier,
      image: refs.previewImage,
    });
    bindEvents();
    setMode("select");
    renderAll();
  }

  function bindRefs() {
    refs.status = document.getElementById("pmp-status");
    refs.uploadForm = document.getElementById("pmp-upload-form");
    refs.openButton = document.getElementById("pmp-open-button");
    refs.saveButton = document.getElementById("pmp-save-button");
    refs.undoButton = document.getElementById("pmp-undo-button");
    refs.redoButton = document.getElementById("pmp-redo-button");
    refs.fileInput = document.getElementById("pmp-file-input");
    refs.viewer = document.getElementById("pmp-viewer");
    refs.stage = document.getElementById("pmp-stage");
    refs.emptyState = document.getElementById("pmp-empty-state");
    refs.previewImage = document.getElementById("pmp-preview-image");
    refs.canvas = document.getElementById("pmp-measure-canvas");
    refs.magnifier = document.getElementById("pmp-magnifier");
    refs.currentFile = document.getElementById("pmp-current-file");
    refs.pageInfo = document.getElementById("pmp-page-info");
    refs.prevPageButton = document.getElementById("pmp-prev-page");
    refs.nextPageButton = document.getElementById("pmp-next-page");
    refs.pageInput = document.getElementById("pmp-page-input");
    refs.pageTotal = document.getElementById("pmp-page-total");
    refs.toolHint = document.getElementById("pmp-tool-hint");
    refs.zoomCurrent = document.getElementById("pmp-zoom-current");
    refs.zoomDisplay = document.getElementById("pmp-zoom-display");
    refs.statusTool = document.getElementById("pmp-status-tool");
    refs.statusZoom = document.getElementById("pmp-status-zoom");
    refs.statusPage = document.getElementById("pmp-status-page");
    refs.statusCoords = document.getElementById("pmp-status-coords");
    refs.snapToggle = document.getElementById("pmp-snap-toggle");
    refs.guidesToggle = document.getElementById("pmp-guides-toggle");
    refs.liveToggle = document.getElementById("pmp-live-toggle");
    refs.colorInput = document.getElementById("pmp-color-input");
    refs.strokeInput = document.getElementById("pmp-stroke-input");
    refs.decimalsInput = document.getElementById("pmp-decimals-input");
    refs.unitSelect = document.getElementById("pmp-unit-select");
    refs.magnifierToggle = document.getElementById("pmp-magnifier-toggle");
    refs.magnifierFactor = document.getElementById("pmp-magnifier-factor");
    refs.clearButton = document.getElementById("pmp-clear-button");
    refs.calibrationReal = document.getElementById("pmp-calibration-real");
    refs.calibrateButton = document.getElementById("pmp-calibrate-button");
    refs.calibrationState = document.getElementById("pmp-calibration-state");
    refs.exportButton = document.getElementById("pmp-export-button");
    refs.exportPngButton = document.getElementById("pmp-export-png-button");
    refs.exportLink = document.getElementById("pmp-export-link");
    refs.jsonOutput = document.getElementById("pmp-json-output");
    refs.inspector = document.getElementById("pmp-inspector");
    refs.history = document.getElementById("pmp-history");
    refs.finalBox = document.getElementById("pmp-final-box");
  }

  function bindEvents() {
    refs.uploadForm.addEventListener("submit", onUpload);
    refs.openButton.addEventListener("click", () => refs.fileInput.click());
    refs.fileInput.addEventListener("change", () => {
      if (refs.fileInput.files.length) refs.uploadForm.requestSubmit();
    });
    refs.saveButton.addEventListener("click", saveLocalState);
    refs.undoButton.addEventListener("click", undoAction);
    refs.redoButton.addEventListener("click", redoAction);
    refs.canvas.addEventListener("mousedown", onCanvasDown);
    refs.canvas.addEventListener("mousemove", onCanvasMove);
    window.addEventListener("mousemove", onWindowMove);
    window.addEventListener("mouseup", onWindowUp);
    refs.viewer.addEventListener("wheel", onWheel, { passive: false });
    refs.clearButton.addEventListener("click", clearMeasurements);
    refs.calibrateButton.addEventListener("click", calibrateSelected);
    refs.exportButton.addEventListener("click", exportJson);
    refs.exportPngButton.addEventListener("click", exportPng);
    refs.snapToggle.addEventListener("change", () => {
      state.snapEnabled = refs.snapToggle.checked;
      setStatus(state.snapEnabled ? "Snap activado." : "Snap desactivado.");
      renderAll();
    });
    refs.guidesToggle.addEventListener("change", () => {
      state.showGuides = refs.guidesToggle.checked;
      renderAll();
    });
    refs.liveToggle.addEventListener("change", () => {
      state.options.live = refs.liveToggle.checked;
      renderAll();
    });
    refs.colorInput.addEventListener("input", () => {
      state.options.color = refs.colorInput.value;
      updateSelected((item) => model.setObjectColor(item, refs.colorInput.value));
    });
    refs.strokeInput.addEventListener("change", () => {
      state.options.strokeWidth = Number(refs.strokeInput.value || 2);
      updateSelected((item) => model.updateObject(item, { stroke_width: state.options.strokeWidth }));
    });
    refs.decimalsInput.addEventListener("change", () => {
      state.options.decimals = clamp(Number(refs.decimalsInput.value || 3), 0, 4);
      renderAll();
    });
    refs.unitSelect.addEventListener("change", () => {
      state.options.unit = refs.unitSelect.value;
      renderAll();
    });
    refs.magnifierToggle.addEventListener("click", () => {
      magnifier.setEnabled(!magnifier.enabled);
      refs.magnifierToggle.classList.toggle("is-active", magnifier.enabled);
    });
    refs.magnifierFactor.addEventListener("change", () => magnifier.setFactor(refs.magnifierFactor.value));
    document.querySelectorAll("[data-pmp-tool]").forEach((button) => {
      button.addEventListener("click", () => setMode(button.dataset.pmpTool));
    });
    document.querySelectorAll("[data-pmp-zoom]").forEach((button) => {
      button.addEventListener("click", () => viewer.setZoom(Number(button.dataset.pmpZoom), { center: false }));
    });
    document.getElementById("pmp-zoom-in").addEventListener("click", () => viewer.zoomBy(1.25, centerAnchor()));
    document.getElementById("pmp-zoom-out").addEventListener("click", () => viewer.zoomBy(0.8, centerAnchor()));
    document.getElementById("pmp-fit-width").addEventListener("click", () => viewer.fitWidth());
    document.getElementById("pmp-fit-page").addEventListener("click", () => viewer.fitPage());
    document.getElementById("pmp-one-to-one").addEventListener("click", () => viewer.oneToOne());
    document.getElementById("pmp-add-guide-v").addEventListener("click", () => addGuide("vertical"));
    document.getElementById("pmp-add-guide-h").addEventListener("click", () => addGuide("horizontal"));
    refs.prevPageButton.addEventListener("click", () => goToPage(state.pagina - 1));
    refs.nextPageButton.addEventListener("click", () => goToPage(state.pagina + 1));
    refs.pageInput.addEventListener("change", () => goToPage(Number(refs.pageInput.value || 1)));
    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup", onKeyUp);
  }

  async function onUpload(event) {
    event.preventDefault();
    const file = refs.fileInput.files[0];
    if (!file) {
      setStatus("Selecciona un PDF.", true);
      return;
    }
    const data = new FormData();
    data.append("pdf", file);
    setStatus("Analizando PDF...");
    refs.exportButton.disabled = true;
    refs.exportPngButton.disabled = true;
    try {
      const response = await fetch(`${apiBase}/upload`, { method: "POST", body: data });
      const payload = await response.json();
      if (!response.ok || !payload.ok) {
        throw new Error(payload.error ? payload.error.message : "No se pudo analizar el PDF.");
      }
      state.archivo = payload.archivo;
      state.storedFilename = payload.stored_filename || "";
      state.pagina = payload.pagina || 1;
      state.pageCount = payload.page_count || state.pagina || 1;
      state.pages = {};
      state.previewUrl = payload.preview_url || (payload.preview && payload.preview.url) || "";
      state.previewFilename = payload.preview.filename || "";
      state.renderMm = payload.preview.render_mm || payload.render_mm || { ancho: 0, alto: 0 };
      state.medidasAuto = payload.medidas_auto || ns.emptyAuto();
      state.pointerMm = null;
      state.hoverSnap = null;
      state.measurements = [];
      state.guides = [];
      state.selectedMeasurementId = null;
      state.selectedGuideId = null;
      state.finalMeasurementId = null;
      state.calibration = { activa: false, factor_escala: 1 };
      state.finalOrigin = "auto";
      state.finalConfidence = "media";
      refs.emptyState.hidden = true;
      refs.exportButton.disabled = false;
      refs.exportPngButton.disabled = false;
      viewer.setPreview(payload.preview_url, state.renderMm, payload.preview);
      saveActivePage();
      restoreLocalState();
      applyPageState(state.pagina);
      resetUndoHistory();
      setStatus("PDF analizado.");
    } catch (error) {
      setStatus(error.message, true);
    }
  }

  async function goToPage(page) {
    if (!state.storedFilename || !hasPdf()) return;
    const requested = Math.trunc(Number(page || 1));
    const target = clamp(Number.isFinite(requested) ? requested : 1, 1, state.pageCount || 1);
    if (target === state.pagina) {
      renderAll();
      return;
    }
    saveActivePage();
    setStatus(`Cargando pagina ${target}...`);
    try {
      if (!state.pages[String(target)] || !state.pages[String(target)].previewUrl) {
        await fetchPage(target);
      }
      applyPageState(target, { resetUndo: true, resetPan: true });
      setStatus(`Pagina ${target} cargada.`);
    } catch (error) {
      setStatus(error.message, true);
      applyPageState(state.pagina);
    }
  }

  async function fetchPage(page) {
    const response = await fetch(`${apiBase}/render-page`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        stored_filename: state.storedFilename,
        pagina: page,
      }),
    });
    const payload = await response.json();
    if (!response.ok || !payload.ok) {
      throw new Error(payload.error ? payload.error.message : "No se pudo renderizar la pagina.");
    }
    state.pageCount = payload.page_count || state.pageCount || page;
    mergePageMetadata(page, payload);
  }

  function mergePageMetadata(page, payload) {
    const key = String(page);
    const existing = state.pages[key] || emptyPageState(page);
    state.pages[key] = Object.assign({}, existing, {
      medidasAuto: payload.medidas_auto || existing.medidasAuto || ns.emptyAuto(),
      renderMm: payload.preview && payload.preview.render_mm ? payload.preview.render_mm : payload.render_mm || existing.renderMm || { ancho: 0, alto: 0 },
      previewUrl: payload.preview_url || (payload.preview && payload.preview.url) || existing.previewUrl || "",
      previewInfo: payload.preview || existing.previewInfo || null,
    });
  }

  function saveActivePage() {
    if (!state.pagina) return;
    state.pages[String(state.pagina)] = activePageSnapshot();
  }

  function activePageSnapshot() {
    return {
      measurements: clone(state.measurements || []),
      guides: ns.guides.normalizeGuides(state.guides || []),
      selectedMeasurementId: state.selectedMeasurementId || null,
      selectedGuideId: state.selectedGuideId || null,
      finalMeasurementId: state.finalMeasurementId || null,
      finalOrigin: state.finalOrigin || "auto",
      finalConfidence: state.finalConfidence || "media",
      medidasAuto: state.medidasAuto || ns.emptyAuto(),
      renderMm: state.renderMm || { ancho: 0, alto: 0 },
      previewUrl: state.previewUrl || "",
      previewInfo: state.previewFilename ? { filename: state.previewFilename, render_mm: state.renderMm } : null,
    };
  }

  function applyPageState(page, options) {
    const data = state.pages[String(page)] || emptyPageState(page);
    state.pagina = page;
    state.measurements = clone(data.measurements || []);
    state.guides = ns.guides.normalizeGuides(data.guides || []);
    state.selectedMeasurementId = data.selectedMeasurementId || null;
    state.selectedGuideId = data.selectedGuideId || null;
    state.finalMeasurementId = data.finalMeasurementId || null;
    state.finalOrigin = data.finalOrigin || "auto";
    state.finalConfidence = data.finalConfidence || "media";
    state.medidasAuto = data.medidasAuto || ns.emptyAuto();
    state.renderMm = data.renderMm || { ancho: 0, alto: 0 };
    state.previewUrl = data.previewUrl || "";
    state.previewFilename = data.previewInfo && data.previewInfo.filename ? data.previewInfo.filename : "";
    state.pointerMm = null;
    state.hoverSnap = null;
    state.drawing = null;
    state.editing = null;
    state.guideEditing = null;
    if (state.previewUrl) {
      viewer.setPreview(state.previewUrl, state.renderMm, data.previewInfo || { filename: state.previewFilename });
    }
    if (options && options.resetPan && viewer) viewer.resetPan();
    if (options && options.resetUndo) resetUndoHistory();
    renderAll();
  }

  function emptyPageState(page) {
    return {
      measurements: [],
      guides: [],
      selectedMeasurementId: null,
      selectedGuideId: null,
      finalMeasurementId: null,
      finalOrigin: "auto",
      finalConfidence: "media",
      medidasAuto: ns.emptyAuto(),
      renderMm: { ancho: 0, alto: 0 },
      previewUrl: "",
      previewInfo: null,
      pagina: page,
    };
  }

  function onCanvasDown(event) {
    if (!hasPdf()) return;
    if (state.mode === "hand" || state.spacePan) {
      event.preventDefault();
      beginPan(event);
      return;
    }
    const point = snappedPoint(event);
    if (state.mode === "select") {
      const hit = viewer.hitTest(point, state.measurements);
      if (hit) {
        state.selectedMeasurementId = hit.id;
        state.selectedGuideId = null;
        state.editing = {
          action: hit.action,
          handle: hit.handle,
          start: point,
          object: clone(currentSelected()),
          historyCaptured: false,
        };
      } else {
        const guideHit = viewer.hitTestGuide(point, state.guides, 8);
        state.selectedGuideId = guideHit ? guideHit.id : null;
        state.selectedMeasurementId = null;
        if (guideHit) {
          state.guideEditing = {
            start: point,
            guide: clone(currentSelectedGuide()),
            historyCaptured: false,
          };
        }
      }
      renderAll();
      return;
    }
    if (state.mode === "guides") {
      const guideHit = viewer.hitTestGuide(point, state.guides, 8);
      if (guideHit) {
        state.selectedGuideId = guideHit.id;
        state.selectedMeasurementId = null;
        state.guideEditing = {
          start: point,
          guide: clone(currentSelectedGuide()),
          historyCaptured: false,
        };
        setStatus("Guia seleccionada.");
      } else {
        const orientation = event.shiftKey ? "horizontal" : "vertical";
        captureUndo();
        const guide = ns.guides.createGuide(orientation, clampGuidePosition(orientation, event.shiftKey ? point.y_mm : point.x_mm));
        state.guides.push(guide);
        state.selectedGuideId = guide.id;
        state.selectedMeasurementId = null;
        setStatus("Guia creada.");
      }
      renderAll();
      return;
    }
    if (["line", "rectangle", "calibrate"].includes(state.mode)) {
      state.drawing = {
        type: state.mode === "rectangle" ? "rectangle" : "line",
        start: point,
        current: point,
      };
      renderAll();
    }
  }

  function onCanvasMove(event) {
    if (!hasPdf()) return;
    state.pointerMm = viewer.mmFromEvent(event);
    state.hoverSnap = snapForPoint(state.pointerMm, event.ctrlKey);
    magnifier.update(event);
    if (state.drawing) {
      let point = state.hoverSnap.point;
      if (event.shiftKey && state.drawing.type === "line") {
        point = model.constrainLineAngle(state.drawing.start, point);
      }
      state.drawing.current = point;
      renderCanvas();
      return;
    }
    if (state.editing) {
      const point = state.hoverSnap.point;
      const original = state.editing.object;
      if (!state.editing.historyCaptured) {
        captureUndo();
        state.editing.historyCaptured = true;
      }
      if (state.editing.action === "resize") {
        replaceMeasurement(model.resizeRectangle(original, state.editing.handle, point));
      } else {
        replaceMeasurement(model.moveObject(original, point.x_mm - state.editing.start.x_mm, point.y_mm - state.editing.start.y_mm));
      }
      renderAll();
      return;
    }
    if (state.guideEditing) {
      const original = state.guideEditing.guide;
      if (!original) return;
      if (!state.guideEditing.historyCaptured) {
        captureUndo();
        state.guideEditing.historyCaptured = true;
      }
      const position = original.orientation === "vertical"
        ? clampGuidePosition("vertical", state.pointerMm.x_mm)
        : clampGuidePosition("horizontal", state.pointerMm.y_mm);
      replaceGuide(ns.guides.moveGuide(original, position));
      renderAll();
      return;
    }
    renderCanvas();
  }

  function onWindowMove(event) {
    if (!panning) return;
    event.preventDefault();
    const deltaX = event.clientX - panning.x;
    const deltaY = event.clientY - panning.y;
    if (Math.abs(deltaX) > 2 || Math.abs(deltaY) > 2) {
      panning.moved = true;
    }
    viewer.setPan(panning.startPan.x + deltaX, panning.startPan.y + deltaY);
    renderCanvas();
  }

  function onWindowUp(event) {
    if (panning) {
      refs.viewer.classList.remove("is-panning");
      panning = null;
      return;
    }
    if (state.editing) {
      state.editing = null;
      renderAll();
      return;
    }
    if (state.guideEditing) {
      state.guideEditing = null;
      renderAll();
      return;
    }
    if (!state.drawing) return;
    const drawing = state.drawing;
    state.drawing = null;
    if (Math.hypot(drawing.current.x_mm - drawing.start.x_mm, drawing.current.y_mm - drawing.start.y_mm) < 0.05) {
      renderAll();
      return;
    }
    const patch = {
      color: state.options.color,
      stroke_width: state.options.strokeWidth,
      pagina: state.pagina,
    };
    if (drawing.type === "line") {
      const line = model.createLine(drawing.start, drawing.current, patch);
      captureUndo();
      state.measurements.push(line);
      state.selectedMeasurementId = line.id;
      state.selectedGuideId = null;
      if (state.mode === "calibrate") refs.calibrationReal.focus();
    } else {
      const rect = model.createRectangle(drawing.start, drawing.current, patch);
      captureUndo();
      state.measurements.push(rect);
      state.selectedMeasurementId = rect.id;
      state.selectedGuideId = null;
      state.finalMeasurementId = rect.id;
      state.finalOrigin = "manual";
      state.finalConfidence = "alta";
    }
    renderAll();
  }

  function beginPan(event) {
    panning = {
      x: event.clientX,
      y: event.clientY,
      startPan: viewer.getPan(),
      moved: false,
    };
    refs.viewer.classList.add("is-panning");
  }

  function onWheel(event) {
    if (!hasPdf()) return;
    event.preventDefault();
    const anchor = viewer.pointFromEvent(event);
    viewer.zoomBy(event.deltaY < 0 ? 1.15 : 1 / 1.15, anchor);
  }

  function onKeyDown(event) {
    if (isTyping(event.target)) return;
    if (isDialogOpen()) return;
    if (handleUndoRedoShortcut(event)) return;
    if (handleNudgeShortcut(event)) return;
    if (event.code === "Space") {
      event.preventDefault();
      state.spacePan = true;
      refs.viewer.classList.add("is-hand-temp");
      return;
    }
    if (event.key === "Alt" && hasPdf()) {
      magnifier.setTemporary(true);
      return;
    }
    const key = event.key.toLowerCase();
    if (key === "h") setMode("hand");
    if (key === "l") setMode("line");
    if (key === "r") setMode("rectangle");
    if (key === "c") setMode("calibrate");
    if (key === "g") setMode("guides");
    if (key === "v" || key === "s") setMode("select");
    if (event.key === "Delete" || event.key === "Backspace") deleteSelected();
  }

  function onKeyUp(event) {
    if (event.code === "Space") {
      state.spacePan = false;
      refs.viewer.classList.remove("is-hand-temp");
    }
    if (event.key === "Alt") {
      magnifier.hideIfTemporary();
    }
  }

  function setMode(mode) {
    state.mode = ["select", "line", "rectangle", "hand", "calibrate", "guides"].includes(mode) ? mode : "select";
    state.drawing = null;
    state.editing = null;
    state.guideEditing = null;
    document.querySelectorAll("[data-pmp-tool]").forEach((button) => {
      button.classList.toggle("is-active", button.dataset.pmpTool === state.mode);
    });
    refs.toolHint.textContent = toolHint();
    ["select", "line", "rectangle", "hand", "calibrate", "guides"].forEach((tool) => {
      refs.viewer.classList.toggle(`is-${tool}-tool`, state.mode === tool);
    });
    refs.viewer.classList.toggle("is-hand-tool", state.mode === "hand");
    renderCanvas();
  }

  function toolHint() {
    if (state.mode === "select") return "Seleccionar: mover, editar o redimensionar objetos.";
    if (state.mode === "line") return "Linea: arrastra entre dos puntos. Shift bloquea angulo.";
    if (state.mode === "rectangle") return "Rectangulo: arrastra el area final.";
    if (state.mode === "calibrate") return "Calibracion: mide una linea y aplica la medida real.";
    if (state.mode === "guides") return "Guias: clic crea vertical; Shift clic crea horizontal.";
    return "Mano: arrastra para desplazar.";
  }

  function toolLabel(mode) {
    const labels = {
      select: "Seleccionar",
      hand: "Mano",
      line: "Linea",
      rectangle: "Rectangulo",
      calibrate: "Calibracion",
      guides: "Guias",
    };
    return labels[mode] || "Seleccionar";
  }

  function clearMeasurements() {
    if (state.measurements.length || state.guides.length || state.finalMeasurementId) captureUndo();
    state.drawing = null;
    state.editing = null;
    state.guideEditing = null;
    state.measurements = [];
    state.guides = [];
    state.selectedMeasurementId = null;
    state.selectedGuideId = null;
    state.finalMeasurementId = null;
    state.calibration = { activa: false, factor_escala: 1 };
    state.finalOrigin = "auto";
    state.finalConfidence = "media";
    refs.calibrationReal.value = "";
    renderAll();
  }

  function calibrateSelected() {
    const selected = currentSelected();
    if (!selected || selected.tipo !== "linea") {
      setStatus("Selecciona una linea para calibrar.", true);
      return;
    }
    try {
      const raw = ns.measureLine(selected, 1);
      const factor = ns.calculateScaleFactor(raw.diagonal_mm, refs.calibrationReal.value);
      state.calibration = { activa: true, factor_escala: factor };
      selected.nombre = selected.nombre || "Linea calibrada";
      setStatus("Escala calibrada.");
      renderAll();
    } catch (error) {
      setStatus(error.message, true);
    }
  }

  async function exportJson() {
    saveActivePage();
    const payload = currentExportPayload();
    setStatus("Exportando JSON...");
    try {
      const response = await fetch(`${apiBase}/export`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const result = await response.json();
      if (!response.ok || !result.ok) {
        throw new Error(result.error ? result.error.message : "No se pudo exportar el JSON.");
      }
      refs.jsonOutput.textContent = JSON.stringify(result.export, null, 2);
      refs.exportLink.href = result.url;
      refs.exportLink.hidden = false;
      setStatus("JSON exportado.");
    } catch (error) {
      setStatus(error.message, true);
    }
  }

  function exportPng() {
    try {
      ns.exportPng({
        image: refs.previewImage,
        renderMm: state.renderMm,
        measurements: state.measurements,
        guides: state.guides,
        includeGuides: state.includeGuidesInPng && state.showGuides,
        filename: `${safeName(state.archivo || "pdf_medidor_pro")}.png`,
        fmt,
      });
      setStatus("PNG exportado.");
    } catch (error) {
      setStatus(error.message, true);
    }
  }

  function renderAll() {
    if (!refs.currentFile) return;
    refs.currentFile.textContent = state.archivo || "Ningun archivo";
    refs.pageInfo.textContent = `Pagina ${state.pagina || 1}/${state.pageCount || 1}`;
    const zoomText = `${Math.round((viewer ? viewer.zoom : 1) * 100)}%`;
    refs.zoomCurrent.textContent = zoomText;
    refs.zoomDisplay.textContent = zoomText;
    renderPageControls();
    renderUndoRedoButtons();
    renderStatusbar(zoomText);
    renderInspectorPanel();
    renderHistoryPanel();
    renderFinalBox();
    renderCalibration();
    refs.jsonOutput.textContent = JSON.stringify(currentExportPayload(), null, 2);
    renderCanvas();
  }

  function renderPageControls() {
    const hasDocument = Boolean(state.storedFilename);
    const pageCount = state.pageCount || 1;
    refs.prevPageButton.disabled = !hasDocument || state.pagina <= 1;
    refs.nextPageButton.disabled = !hasDocument || state.pagina >= pageCount;
    refs.pageInput.disabled = !hasDocument;
    refs.pageInput.min = "1";
    refs.pageInput.max = String(pageCount);
    refs.pageInput.value = String(state.pagina || 1);
    refs.pageTotal.textContent = `de ${pageCount}`;
  }

  function renderInspectorPanel() {
    ns.renderInspector(refs.inspector, {
      selected: currentSelected(),
      selectedGuide: currentSelectedGuide(),
      archivo: state.archivo,
      page: state.pagina,
      pageCount: state.pageCount,
      renderMm: state.renderMm,
      medidasAuto: state.medidasAuto,
      metrics,
      fmt,
    });
    ns.bindInspector(refs.inspector, {
      rename: (name) => updateSelected((item) => model.renameObject(item, name)),
      color: (color) => {
        state.options.color = color;
        refs.colorInput.value = color;
        updateSelected((item) => model.setObjectColor(item, color));
      },
      visible: (visible) => updateSelected((item) => model.setObjectVisible(item, visible)),
      resize: (width, height) => updateSelected((item) => resizeSelectedDimensions(item, width, height)),
      useFinal: () => useFinal(state.selectedMeasurementId),
      duplicate: duplicateSelected,
      guideVisible: (visible) => updateSelectedGuide((guide) => Object.assign({}, guide, { visible: Boolean(visible) })),
    });
  }

  function renderHistoryPanel() {
    ns.renderHistory(refs.history, {
      measurements: state.measurements,
      selectedId: state.selectedMeasurementId,
      page: state.pagina,
      metrics,
      fmt,
    });
    ns.bindHistory(refs.history, {
      select: (id) => {
        state.selectedMeasurementId = id;
        state.selectedGuideId = null;
        renderAll();
      },
      delete: deleteMeasurement,
      toggleVisible: (id) => {
        const item = state.measurements.find((m) => m.id === id);
        if (item) {
          captureUndo();
          item.visible = item.visible === false;
        }
        renderAll();
      },
      useFinal,
      rename: (id, name) => {
        const item = state.measurements.find((m) => m.id === id);
        if (item) replaceMeasurement(model.renameObject(item, name), { record: true });
      },
    });
  }

  function renderFinalBox() {
    const final = state.measurements.find((item) => item.id === state.finalMeasurementId && item.tipo === "rectangulo");
    if (!final) {
      refs.finalBox.textContent = "Sin rectangulo final.";
      return;
    }
    const measured = ns.measureRectangle(final, state.calibration.factor_escala);
    refs.finalBox.innerHTML = [
      `<strong>${fmt(measured.ancho_final_mm)} x ${fmt(measured.alto_final_mm)} mm</strong>`,
      `<small>${final.nombre || "Rectangulo"} | origen ${final.origen || "manual"}</small>`,
    ].join("");
  }

  function renderCalibration() {
    const factor = state.calibration.factor_escala;
    refs.calibrationState.textContent = state.calibration.activa
      ? `Escala calibrada: factor ${factor}`
      : "Escala sin calibrar";
    refs.calibrationState.classList.toggle("is-active", state.calibration.activa);
  }

  function renderCanvas() {
    if (!viewer) return;
    viewer.syncCanvas();
    viewer.clear();
    if (hasPdf()) {
      if (state.showGuides) viewer.drawGuides(state.guides, state.selectedGuideId);
      viewer.drawCenter();
    }
    state.measurements.forEach((item) => {
      const selected = item.id === state.selectedMeasurementId;
      if (item.tipo === "linea") viewer.drawLine(item, selected);
      if (item.tipo === "rectangulo") viewer.drawRectangle(item, selected, item.id === state.finalMeasurementId);
    });
    if (state.drawing) {
      drawDraft();
    }
    if (state.hoverSnap && state.hoverSnap.snapped) {
      viewer.drawSnap(state.hoverSnap.point);
    }
    if (hasPdf()) {
      viewer.drawRulers(state.pointerMm);
      viewer.drawCoordinates(state.pointerMm, fmt);
    }
    renderStatusbar(`${Math.round((viewer ? viewer.zoom : 1) * 100)}%`);
  }

  function renderStatusbar(zoomText) {
    if (!refs.statusTool) return;
    refs.statusTool.textContent = `Herramienta activa: ${toolLabel(state.mode)}`;
    refs.statusZoom.textContent = `Zoom: ${zoomText}`;
    refs.statusPage.textContent = `Pagina: ${state.pagina || 1}${state.pageCount ? `/${state.pageCount}` : ""}`;
    refs.statusCoords.textContent = state.pointerMm
      ? `X: ${fmt(state.pointerMm.x_mm)} mm · Y: ${fmt(state.pointerMm.y_mm)} mm`
      : "X: -- mm · Y: -- mm";
  }

  function drawDraft() {
    if (!state.drawing) return;
    if (state.drawing.type === "line") {
      const line = model.createLine(state.drawing.start, state.drawing.current, {
        id: "draft_line",
        color: state.options.color,
        stroke_width: state.options.strokeWidth,
        nombre: "Linea en dibujo",
      });
      viewer.drawLine(line, true);
      if (state.options.live) {
        const measured = ns.measureLine(line, state.calibration.factor_escala);
        viewer.drawLiveLabel(state.drawing.current, `D ${fmt(measured.diagonal_mm)} mm  dX ${fmt(measured.horizontal_mm)}  dY ${fmt(measured.vertical_mm)}`);
      }
    } else {
      const rect = model.createRectangle(state.drawing.start, state.drawing.current, {
        id: "draft_rect",
        color: state.options.color,
        stroke_width: state.options.strokeWidth,
        nombre: "Rectangulo en dibujo",
      });
      viewer.drawRectangle(rect, true, false);
      if (state.options.live) {
        const item = metrics(rect);
        viewer.drawLiveLabel(state.drawing.current, `${fmt(item.ancho_mm)} x ${fmt(item.alto_mm)} mm  A ${fmt(item.area_mm2)} mm2`);
      }
    }
  }

  function currentExportPayload() {
    const pages = collectPageExports();
    const active = pages.find((page) => page.pagina === state.pagina) || pageExport(state.pagina, activePageSnapshot());
    const measurements = pages.reduce((items, page) => items.concat(page.mediciones || []), []);
    return ns.buildExportPayload(state, active.medidas_manual, measurements, pages);
  }

  function collectPageExports() {
    const active = activePageSnapshot();
    const pages = [];
    const total = Math.max(1, Number(state.pageCount || 1));
    for (let page = 1; page <= total; page += 1) {
      const data = page === state.pagina ? active : state.pages[String(page)] || emptyPageState(page);
      pages.push(pageExport(page, data));
    }
    return pages;
  }

  function pageExport(page, data) {
    const measurements = (data.measurements || []).map((item) => {
      const withPage = Object.assign({}, item, { pagina: page });
      if (withPage.tipo === "linea") return ns.lineExport(withPage, state.calibration.factor_escala);
      return ns.rectangleExport(withPage, state.calibration.factor_escala);
    });
    const final = (data.measurements || []).find((item) => item.id === data.finalMeasurementId && item.tipo === "rectangulo");
    const manualBox = final
      ? ns.measureRectangle(final, state.calibration.factor_escala)
      : { ancho_final_mm: 0, alto_final_mm: 0 };
    return {
      pagina: page,
      medidas_auto: data.medidasAuto || ns.emptyAuto(),
      medidas_manual: manualBox,
      origen_medida_final: data.finalOrigin || (final ? "manual" : "auto"),
      confianza: data.finalConfidence || (final ? "alta" : "media"),
      mediciones: measurements,
    };
  }

  function snappedPoint(event) {
    const point = viewer.mmFromEvent(event);
    state.pointerMm = point;
    const snap = snapForPoint(point, event.ctrlKey);
    state.hoverSnap = snap;
    if (snap.snapped) setStatus(`Snap: ${snap.candidate.kind}`);
    return snap.point;
  }

  function snapForPoint(point, strict) {
    const snap = ns.snapPoint(point, state.measurements, state.snapEnabled, strict);
    if (!state.snapEnabled || snap.snapped) return snap;
    const threshold = strict ? 0.75 : 2;
    let best = null;
    ns.guides.guideSnapCandidates(state.guides, state.renderMm).forEach((candidate) => {
      const projected = candidate.kind.indexOf("vertical") >= 0
        ? { x_mm: candidate.x_mm, y_mm: point.y_mm }
        : { x_mm: point.x_mm, y_mm: candidate.y_mm };
      const distance = Math.hypot(projected.x_mm - point.x_mm, projected.y_mm - point.y_mm);
      if (distance <= threshold && (!best || distance < best.distance_mm)) {
        best = { candidate: Object.assign({}, candidate, projected), distance_mm: distance };
      }
    });
    if (!best) return snap;
    return {
      snapped: true,
      point: { x_mm: model.round(best.candidate.x_mm), y_mm: model.round(best.candidate.y_mm) },
      candidate: best.candidate,
      distance_mm: model.round(best.distance_mm),
    };
  }

  function addGuide(orientation) {
    if (!hasPdf()) return;
    const value = orientation === "vertical" ? Number(state.renderMm.ancho || 0) / 2 : Number(state.renderMm.alto || 0) / 2;
    captureUndo();
    const guide = ns.guides.createGuide(orientation, value);
    state.guides.push(guide);
    state.selectedGuideId = guide.id;
    state.selectedMeasurementId = null;
    renderAll();
  }

  function saveLocalState() {
    if (!state.archivo) {
      setStatus("No hay PDF cargado.", true);
      return;
    }
    saveActivePage();
    localStorage.setItem(localDocumentKey(), JSON.stringify({
      pages: editablePagesForLocal(),
      calibration: state.calibration,
    }));
    setStatus("Estado guardado en este navegador.");
  }

  function restoreLocalState() {
    if (!state.archivo) return;
    const documentRaw = localStorage.getItem(localDocumentKey());
    if (documentRaw) {
      try {
        const saved = JSON.parse(documentRaw);
        mergeSavedPages(saved.pages || {});
        state.calibration = saved.calibration || { activa: false, factor_escala: 1 };
        setStatus("Estado local restaurado.");
        return;
      } catch (error) {
        setStatus("No se pudo restaurar el estado local.", true);
      }
    }
    const raw = localStorage.getItem(localStateKey());
    if (!raw) return;
    try {
      const saved = JSON.parse(raw);
      const current = state.pages[String(state.pagina)] || emptyPageState(state.pagina);
      state.pages[String(state.pagina)] = Object.assign({}, current, editablePageForLocal(saved));
      state.calibration = saved.calibration || { activa: false, factor_escala: 1 };
      setStatus("Estado local restaurado.");
    } catch (error) {
      setStatus("No se pudo restaurar el estado local.", true);
    }
  }

  function editablePagesForLocal() {
    const pages = {};
    Object.keys(state.pages || {}).forEach((key) => {
      pages[key] = editablePageForLocal(state.pages[key]);
    });
    return pages;
  }

  function editablePageForLocal(page) {
    return {
      measurements: clone(page && page.measurements ? page.measurements : []),
      guides: ns.guides.normalizeGuides(page && page.guides ? page.guides : []),
      selectedMeasurementId: page && page.selectedMeasurementId ? page.selectedMeasurementId : null,
      selectedGuideId: page && page.selectedGuideId ? page.selectedGuideId : null,
      finalMeasurementId: page && page.finalMeasurementId ? page.finalMeasurementId : null,
      finalOrigin: page && page.finalOrigin ? page.finalOrigin : "auto",
      finalConfidence: page && page.finalConfidence ? page.finalConfidence : "media",
    };
  }

  function mergeSavedPages(pages) {
    Object.keys(pages || {}).forEach((key) => {
      const page = clamp(Math.trunc(Number(key || 1)), 1, state.pageCount || 1);
      const current = state.pages[String(page)] || emptyPageState(page);
      state.pages[String(page)] = Object.assign({}, current, editablePageForLocal(pages[key]));
    });
  }

  function localDocumentKey() {
    return `pdf_medidor_pro:${state.archivo}:document`;
  }

  function localStateKey() {
    return `pdf_medidor_pro:${state.archivo}:${state.pagina || 1}`;
  }

  function resizeSelectedDimensions(item, width, height) {
    if (!item || item.tipo !== "rectangulo") return item;
    return model.updateObject(item, {
      ancho_mm: width && width > 0 ? model.round(width / state.calibration.factor_escala) : item.ancho_mm,
      alto_mm: height && height > 0 ? model.round(height / state.calibration.factor_escala) : item.alto_mm,
    });
  }

  function useFinal(id) {
    const item = state.measurements.find((m) => m.id === id);
    if (!item || item.tipo !== "rectangulo") return;
    captureUndo();
    state.finalMeasurementId = id;
    state.finalOrigin = "manual";
    state.finalConfidence = "alta";
    state.selectedMeasurementId = id;
    state.selectedGuideId = null;
    renderAll();
  }

  function duplicateSelected() {
    const selected = currentSelected();
    if (!selected) return;
    captureUndo();
    const duplicated = model.duplicateObject(selected);
    state.measurements.push(duplicated);
    state.selectedMeasurementId = duplicated.id;
    state.selectedGuideId = null;
    renderAll();
  }

  function deleteSelected() {
    if (state.selectedGuideId) {
      deleteGuide(state.selectedGuideId);
      return;
    }
    if (!state.selectedMeasurementId) return;
    deleteMeasurement(state.selectedMeasurementId);
  }

  function deleteGuide(id) {
    if (!state.guides.some((guide) => guide.id === id)) return;
    captureUndo();
    state.guides = ns.guides.deleteGuide(state.guides, id);
    if (state.selectedGuideId === id) state.selectedGuideId = null;
    renderAll();
  }

  function deleteMeasurement(id) {
    if (!state.measurements.some((item) => item.id === id)) return;
    captureUndo();
    state.measurements = model.deleteObject(state.measurements, id);
    if (state.finalMeasurementId === id) state.finalMeasurementId = null;
    if (state.selectedMeasurementId === id) state.selectedMeasurementId = null;
    renderAll();
  }

  function updateSelected(updater) {
    const selected = currentSelected();
    if (!selected) return;
    captureUndo();
    replaceMeasurement(updater(selected));
  }

  function replaceMeasurement(item, options) {
    if (options && options.record) captureUndo();
    state.measurements = model.replaceObject(state.measurements, item);
    renderAll();
  }

  function updateSelectedGuide(updater) {
    const selected = currentSelectedGuide();
    if (!selected) return;
    captureUndo();
    replaceGuide(updater(selected));
  }

  function replaceGuide(guide) {
    state.guides = ns.guides.replaceGuide(state.guides, guide);
    renderAll();
  }

  function handleUndoRedoShortcut(event) {
    const key = event.key.toLowerCase();
    if (!event.ctrlKey || key !== "z" && key !== "y") return false;
    event.preventDefault();
    if (key === "z" && event.shiftKey) {
      redoAction();
    } else if (key === "z") {
      undoAction();
    } else {
      redoAction();
    }
    return true;
  }

  function handleNudgeShortcut(event) {
    const directions = {
      ArrowUp: { dx: 0, dy: -1 },
      ArrowDown: { dx: 0, dy: 1 },
      ArrowLeft: { dx: -1, dy: 0 },
      ArrowRight: { dx: 1, dy: 0 },
    };
    const direction = directions[event.key];
    const guide = currentSelectedGuide();
    if (direction && guide) {
      const step = event.ctrlKey ? 0.01 : event.shiftKey ? 1 : 0.1;
      const delta = guide.orientation === "vertical" ? direction.dx * step : direction.dy * step;
      if (delta === 0) return false;
      event.preventDefault();
      captureUndo();
      replaceGuide(ns.guides.moveGuide(guide, clampGuidePosition(guide.orientation, ns.guides.guidePosition(guide) + delta)));
      setStatus(`Nudge guia ${fmt(step)} mm.`);
      return true;
    }
    const selected = currentSelected();
    if (!direction || !selected) return false;
    event.preventDefault();
    const step = event.ctrlKey ? 0.01 : event.shiftKey ? 1 : 0.1;
    captureUndo();
    replaceMeasurement(model.moveObject(selected, direction.dx * step, direction.dy * step));
    setStatus(`Nudge ${fmt(step)} mm.`);
    return true;
  }

  function undoAction() {
    if (!undoHistory.canUndo()) {
      renderUndoRedoButtons();
      return;
    }
    applyUndoSnapshot(undoHistory.undo(state));
    setStatus("Accion deshecha.");
  }

  function redoAction() {
    if (!undoHistory.canRedo()) {
      renderUndoRedoButtons();
      return;
    }
    applyUndoSnapshot(undoHistory.redo(state));
    setStatus("Accion rehecha.");
  }

  function captureUndo() {
    undoHistory.capture(state);
  }

  function resetUndoHistory() {
    undoHistory.reset();
    renderUndoRedoButtons();
  }

  function applyUndoSnapshot(snapshot) {
    state.measurements = clone(snapshot.measurements || []);
    state.guides = ns.guides.normalizeGuides(snapshot.guides || []);
    state.selectedMeasurementId = snapshot.selectedMeasurementId || null;
    state.selectedGuideId = snapshot.selectedGuideId || null;
    state.finalMeasurementId = snapshot.finalMeasurementId || null;
    state.finalOrigin = snapshot.finalOrigin || "auto";
    state.finalConfidence = snapshot.finalConfidence || "media";
    state.drawing = null;
    state.editing = null;
    state.guideEditing = null;
    renderAll();
  }

  function renderUndoRedoButtons() {
    if (!refs.undoButton || !refs.redoButton) return;
    refs.undoButton.disabled = !undoHistory.canUndo();
    refs.redoButton.disabled = !undoHistory.canRedo();
  }

  function metrics(item) {
    return model.metrics(item, state.calibration.factor_escala);
  }

  function centerAnchor() {
    return { x: refs.viewer.clientWidth / 2, y: refs.viewer.clientHeight / 2 };
  }

  function currentSelected() {
    return state.measurements.find((item) => item.id === state.selectedMeasurementId);
  }

  function currentSelectedGuide() {
    return state.guides.find((guide) => guide.id === state.selectedGuideId) || null;
  }

  function clampGuidePosition(orientation, value) {
    const max = orientation === "vertical" ? Number(state.renderMm.ancho || 0) : Number(state.renderMm.alto || 0);
    return model.round(clamp(Number(value || 0), 0, max));
  }

  function hasPdf() {
    return !refs.previewImage.hidden && state.renderMm.ancho > 0 && state.renderMm.alto > 0;
  }

  function isTyping(target) {
    if (!target) return false;
    return ["INPUT", "TEXTAREA", "SELECT", "BUTTON"].includes(target.tagName) || target.isContentEditable;
  }

  function isDialogOpen() {
    return Boolean(document.querySelector("dialog[open], [role='dialog'][aria-modal='true']"));
  }

  function setStatus(message, isError) {
    refs.status.textContent = message;
    refs.status.classList.toggle("is-error", Boolean(isError));
  }

  function fmt(value) {
    const numeric = Number(value || 0);
    return numeric.toLocaleString("es-PY", {
      minimumFractionDigits: 0,
      maximumFractionDigits: state.options.decimals,
    });
  }

  function safeName(name) {
    return String(name || "pdf_medidor_pro").replace(/\.pdf$/i, "").replace(/[^a-z0-9_-]+/gi, "_");
  }

  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }
})();
