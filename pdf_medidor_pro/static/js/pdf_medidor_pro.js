(function () {
  "use strict";

  const apiBase = "/api/pdf-medidor-pro";
  const ns = window.PdfMedidorPro;
  const refs = {};
  const state = {
    archivo: "",
    pagina: 1,
    previewFilename: "",
    renderMm: { ancho: 0, alto: 0 },
    medidasAuto: ns.emptyAuto(),
    mode: "line",
    previousMode: "line",
    spacePan: false,
    pendingPoint: null,
    hoverSnap: null,
    measurements: [],
    selectedMeasurementId: null,
    finalMeasurementId: null,
    calibration: { activa: false, factor_escala: 1 },
    finalOrigin: "auto",
    finalConfidence: "media",
    snapEnabled: false,
    suppressNextClick: false,
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
    renderAll();
  }

  function bindRefs() {
    refs.status = document.getElementById("pmp-status");
    refs.uploadForm = document.getElementById("pmp-upload-form");
    refs.fileInput = document.getElementById("pmp-file-input");
    refs.autoTable = document.getElementById("pmp-auto-table");
    refs.viewer = document.getElementById("pmp-viewer");
    refs.stage = document.getElementById("pmp-stage");
    refs.emptyState = document.getElementById("pmp-empty-state");
    refs.previewImage = document.getElementById("pmp-preview-image");
    refs.canvas = document.getElementById("pmp-measure-canvas");
    refs.magnifier = document.getElementById("pmp-magnifier");
    refs.currentFile = document.getElementById("pmp-current-file");
    refs.pageInfo = document.getElementById("pmp-page-info");
    refs.toolHint = document.getElementById("pmp-tool-hint");
    refs.zoomCurrent = document.getElementById("pmp-zoom-current");
    refs.snapToggle = document.getElementById("pmp-snap-toggle");
    refs.magnifierToggle = document.getElementById("pmp-magnifier-toggle");
    refs.magnifierFactor = document.getElementById("pmp-magnifier-factor");
    refs.measurements = document.getElementById("pmp-measurements");
    refs.finalBox = document.getElementById("pmp-final-box");
    refs.clearButton = document.getElementById("pmp-clear-button");
    refs.calibrationReal = document.getElementById("pmp-calibration-real");
    refs.calibrateButton = document.getElementById("pmp-calibrate-button");
    refs.calibrationState = document.getElementById("pmp-calibration-state");
    refs.exportButton = document.getElementById("pmp-export-button");
    refs.exportLink = document.getElementById("pmp-export-link");
    refs.jsonOutput = document.getElementById("pmp-json-output");
  }

  function bindEvents() {
    refs.uploadForm.addEventListener("submit", onUpload);
    refs.canvas.addEventListener("click", onCanvasClick);
    refs.canvas.addEventListener("mousemove", onCanvasMove);
    refs.canvas.addEventListener("mousedown", onPanStart);
    window.addEventListener("mousemove", onPanMove);
    window.addEventListener("mouseup", onPanEnd);
    refs.viewer.addEventListener("wheel", onWheel, { passive: false });
    refs.clearButton.addEventListener("click", clearMeasurements);
    refs.calibrateButton.addEventListener("click", calibrateSelected);
    refs.exportButton.addEventListener("click", exportJson);
    refs.snapToggle.addEventListener("change", () => {
      state.snapEnabled = refs.snapToggle.checked;
      setStatus(state.snapEnabled ? "Snap activado." : "Snap desactivado.");
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
    try {
      const response = await fetch(`${apiBase}/upload`, { method: "POST", body: data });
      const payload = await response.json();
      if (!response.ok || !payload.ok) {
        throw new Error(payload.error ? payload.error.message : "No se pudo analizar el PDF.");
      }
      state.archivo = payload.archivo;
      state.pagina = payload.pagina || 1;
      state.previewFilename = payload.preview.filename || "";
      state.renderMm = payload.preview.render_mm || payload.render_mm || { ancho: 0, alto: 0 };
      state.medidasAuto = payload.medidas_auto || ns.emptyAuto();
      state.pendingPoint = null;
      state.hoverSnap = null;
      state.measurements = [];
      state.selectedMeasurementId = null;
      state.finalMeasurementId = null;
      state.calibration = { activa: false, factor_escala: 1 };
      state.finalOrigin = "auto";
      state.finalConfidence = "media";
      refs.emptyState.hidden = true;
      refs.exportButton.disabled = false;
      viewer.setPreview(payload.preview_url, state.renderMm, payload.preview);
      setStatus("PDF analizado.");
    } catch (error) {
      setStatus(error.message, true);
    }
  }

  async function onCanvasClick(event) {
    if (!hasPdf() || panning) return;
    if (state.suppressNextClick) {
      state.suppressNextClick = false;
      return;
    }
    if (state.mode === "hand" || state.spacePan) return;
    const point = snappedPoint(event);
    if (!state.pendingPoint) {
      state.pendingPoint = point;
      renderCanvas();
      return;
    }
    if (state.mode === "line") {
      const line = {
        id: `m_${Date.now()}`,
        tipo: "linea",
        origen: "manual",
        nombre: "Linea manual",
        visible: true,
        a: state.pendingPoint,
        b: point,
        confianza: 1,
      };
      state.measurements.push(line);
      state.selectedMeasurementId = line.id;
    } else if (state.mode === "rectangle") {
      const rect = ns.makeRectangle(state.pendingPoint, point);
      state.measurements.push(rect);
      state.selectedMeasurementId = rect.id;
      state.finalMeasurementId = rect.id;
      state.finalOrigin = "manual";
      state.finalConfidence = "alta";
    }
    state.pendingPoint = null;
    renderAll();
  }

  function onCanvasMove(event) {
    if (!hasPdf()) return;
    const point = viewer.mmFromEvent(event);
    state.hoverSnap = ns.snapPoint(point, state.measurements, state.snapEnabled, event.ctrlKey);
    magnifier.update(event);
    renderCanvas();
  }

  function onWheel(event) {
    if (!hasPdf()) return;
    event.preventDefault();
    const anchor = viewer.pointFromEvent(event);
    viewer.zoomBy(event.deltaY < 0 ? 1.15 : 1 / 1.15, anchor);
  }

  function onPanStart(event) {
    if (!hasPdf() || (state.mode !== "hand" && !state.spacePan)) return;
    panning = {
      x: event.clientX,
      y: event.clientY,
      left: refs.viewer.scrollLeft,
      top: refs.viewer.scrollTop,
      moved: false,
    };
    refs.viewer.classList.add("is-panning");
  }

  function onPanMove(event) {
    if (!panning) return;
    if (Math.abs(event.clientX - panning.x) > 2 || Math.abs(event.clientY - panning.y) > 2) {
      panning.moved = true;
    }
    refs.viewer.scrollLeft = panning.left - (event.clientX - panning.x);
    refs.viewer.scrollTop = panning.top - (event.clientY - panning.y);
    renderCanvas();
  }

  function onPanEnd() {
    if (panning && panning.moved) {
      state.suppressNextClick = true;
    }
    panning = null;
    refs.viewer.classList.remove("is-panning");
  }

  function onKeyDown(event) {
    if (event.code === "Space" && !isTyping(event.target)) {
      event.preventDefault();
      state.spacePan = true;
      refs.viewer.classList.add("is-hand-temp");
    }
    if (event.key === "Alt" && hasPdf()) {
      magnifier.setTemporary(true);
    }
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
    state.previousMode = state.mode;
    state.mode = ["line", "rectangle", "hand"].includes(mode) ? mode : "line";
    state.pendingPoint = null;
    document.querySelectorAll("[data-pmp-tool]").forEach((button) => {
      button.classList.toggle("is-active", button.dataset.pmpTool === state.mode);
    });
    refs.toolHint.textContent = toolHint();
    refs.viewer.classList.toggle("is-hand-tool", state.mode === "hand");
    renderCanvas();
  }

  function toolHint() {
    if (state.mode === "line") return "Linea: selecciona dos puntos.";
    if (state.mode === "rectangle") return "Rectangulo: selecciona dos esquinas.";
    return "Mano: arrastra para desplazar.";
  }

  function clearMeasurements() {
    state.pendingPoint = null;
    state.measurements = [];
    state.selectedMeasurementId = null;
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
      setStatus("Escala calibrada.");
      renderAll();
    } catch (error) {
      setStatus(error.message, true);
    }
  }

  async function exportJson() {
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

  function renderAll() {
    if (!refs.currentFile) return;
    refs.currentFile.textContent = state.archivo || "Ningun archivo";
    refs.pageInfo.textContent = `Pagina ${state.pagina || 1}`;
    refs.zoomCurrent.textContent = `${Math.round((viewer ? viewer.zoom : 1) * 100)}%`;
    renderAutoTable();
    renderMeasurements();
    renderFinalBox();
    renderCalibration();
    refs.jsonOutput.textContent = JSON.stringify(currentExportPayload(), null, 2);
    renderCanvas();
  }

  function renderAutoTable() {
    const labels = [
      ["mediabox_mm", "MediaBox"],
      ["cropbox_mm", "CropBox"],
      ["trimbox_mm", "TrimBox"],
      ["bleedbox_mm", "BleedBox"],
      ["artbox_mm", "ArtBox"],
    ];
    refs.autoTable.innerHTML = labels.map(([key, label]) => {
      const box = state.medidasAuto[key] || { ancho: 0, alto: 0 };
      return `<div class="pmp-auto-row"><strong>${label}</strong><span>${fmt(box.ancho)} x ${fmt(box.alto)} mm</span></div>`;
    }).join("");
  }

  function renderMeasurements() {
    if (!state.measurements.length) {
      refs.measurements.innerHTML = '<p class="pmp-muted">Sin mediciones.</p>';
      return;
    }
    refs.measurements.innerHTML = "";
    state.measurements.forEach((item, index) => {
      const card = document.createElement("article");
      card.className = `pmp-measurement${item.id === state.selectedMeasurementId ? " is-selected" : ""}`;
      const title = `${index + 1}. ${item.nombre || "Medicion"}${item.visible === false ? " (oculta)" : ""}`;
      const body = item.tipo === "linea" ? lineSummary(item) : rectSummary(item);
      card.innerHTML = `<button type="button" class="pmp-measurement-main"><strong>${title}</strong>${body}</button>`;
      card.querySelector("button").addEventListener("click", () => {
        state.selectedMeasurementId = item.id;
        renderAll();
      });
      const actions = document.createElement("div");
      actions.className = "pmp-measurement-actions";
      actions.appendChild(actionButton(item.visible === false ? "Mostrar" : "Ocultar", () => {
        item.visible = item.visible === false;
        renderAll();
      }));
      if (item.tipo === "rectangulo") {
        actions.appendChild(actionButton("Usar final", () => {
          state.finalMeasurementId = item.id;
          state.finalOrigin = item.origen || "manual";
          state.finalConfidence = "alta";
          renderAll();
        }));
      }
      actions.appendChild(actionButton("Borrar", () => {
        state.measurements = state.measurements.filter((m) => m.id !== item.id);
        if (state.finalMeasurementId === item.id) state.finalMeasurementId = null;
        if (state.selectedMeasurementId === item.id) state.selectedMeasurementId = null;
        renderAll();
      }));
      card.appendChild(actions);
      refs.measurements.appendChild(card);
    });
  }

  function lineSummary(line) {
    const measured = ns.measureLine(line, state.calibration.factor_escala);
    return [
      `<small>${line.origen || "manual"} | Diagonal ${fmt(measured.diagonal_mm)} mm</small>`,
      `<small>H ${fmt(measured.horizontal_mm)} mm | V ${fmt(measured.vertical_mm)} mm</small>`,
      `<small>A(${fmt(measured.a.x_mm)}, ${fmt(measured.a.y_mm)}) B(${fmt(measured.b.x_mm)}, ${fmt(measured.b.y_mm)})</small>`,
    ].join("");
  }

  function rectSummary(rect) {
    const measured = ns.measureRectangle(rect, state.calibration.factor_escala);
    return [
      `<small>${rect.origen || "manual"} | ${fmt(measured.ancho_final_mm)} x ${fmt(measured.alto_final_mm)} mm</small>`,
      `<small>X ${fmt(rect.x_mm)} mm | Y ${fmt(rect.y_mm)} mm | Conf. ${fmt((rect.confianza || 0) * 100)}%</small>`,
    ].join("");
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
      `<small>Origen de medida final: ${final.origen || "manual"}</small>`,
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
    state.measurements.forEach((item) => {
      if (item.tipo === "linea") viewer.drawLine(item, item.id === state.selectedMeasurementId);
      if (item.tipo === "rectangulo") viewer.drawRectangle(item, item.id === state.selectedMeasurementId || item.id === state.finalMeasurementId);
    });
    if (state.pendingPoint) {
      viewer.drawPoint(state.pendingPoint, "#b42318");
    }
    if (state.hoverSnap && state.hoverSnap.snapped) {
      viewer.drawSnap(state.hoverSnap.point);
    }
  }

  function currentExportPayload() {
    const final = state.measurements.find((item) => item.id === state.finalMeasurementId && item.tipo === "rectangulo");
    const manualBox = final
      ? ns.measureRectangle(final, state.calibration.factor_escala)
      : { ancho_final_mm: 0, alto_final_mm: 0 };
    const measurements = state.measurements.map((item) => {
      if (item.tipo === "linea") return ns.lineExport(item, state.calibration.factor_escala);
      return ns.rectangleExport(item, state.calibration.factor_escala);
    });
    return ns.buildExportPayload(state, manualBox, measurements);
  }

  function snappedPoint(event) {
    const point = viewer.mmFromEvent(event);
    const snap = ns.snapPoint(point, state.measurements, state.snapEnabled, event.ctrlKey);
    state.hoverSnap = snap;
    if (snap.snapped) setStatus(`Snap: ${snap.candidate.kind}`);
    return snap.point;
  }

  function centerAnchor() {
    return { x: refs.viewer.clientWidth / 2, y: refs.viewer.clientHeight / 2 };
  }

  function currentSelected() {
    return state.measurements.find((item) => item.id === state.selectedMeasurementId);
  }

  function hasPdf() {
    return !refs.previewImage.hidden && state.renderMm.ancho > 0 && state.renderMm.alto > 0;
  }

  function actionButton(label, onClick) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "pmp-mini-button";
    button.textContent = label;
    button.addEventListener("click", onClick);
    return button;
  }

  function isTyping(target) {
    return ["INPUT", "TEXTAREA", "SELECT"].includes(target && target.tagName);
  }

  function setStatus(message, isError) {
    refs.status.textContent = message;
    refs.status.style.color = isError ? "#b42318" : "";
  }

  function fmt(value) {
    const numeric = Number(value || 0);
    return numeric.toLocaleString("es-PY", { maximumFractionDigits: 3 });
  }
})();
