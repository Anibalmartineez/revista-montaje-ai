(function () {
  "use strict";

  const apiBase = "/api/pdf-medidor-pro";
  const ns = window.PdfMedidorPro;
  const refs = {};
  const state = {
    archivo: "",
    pagina: 1,
    medidasAuto: ns.emptyAuto(),
    mode: "line",
    pendingPoint: null,
    measurements: [],
    selectedMeasurementId: null,
    finalRectangle: null,
    calibration: { activa: false, factor_escala: 1 },
  };

  let viewer = null;

  document.addEventListener("DOMContentLoaded", init);

  function init() {
    bindRefs();
    viewer = new ns.Viewer({
      container: refs.viewer,
      image: refs.previewImage,
      canvas: refs.canvas,
    });
    refs.uploadForm.addEventListener("submit", onUpload);
    refs.canvas.addEventListener("click", onCanvasClick);
    refs.clearButton.addEventListener("click", clearMeasurements);
    refs.calibrateButton.addEventListener("click", calibrateSelected);
    refs.exportButton.addEventListener("click", exportJson);
    document.querySelectorAll("[data-pmp-tool]").forEach((button) => {
      button.addEventListener("click", () => setMode(button.dataset.pmpTool));
    });
    renderAll();
  }

  function bindRefs() {
    refs.status = document.getElementById("pmp-status");
    refs.uploadForm = document.getElementById("pmp-upload-form");
    refs.fileInput = document.getElementById("pmp-file-input");
    refs.autoTable = document.getElementById("pmp-auto-table");
    refs.viewer = document.getElementById("pmp-viewer");
    refs.emptyState = document.getElementById("pmp-empty-state");
    refs.previewImage = document.getElementById("pmp-preview-image");
    refs.canvas = document.getElementById("pmp-measure-canvas");
    refs.currentFile = document.getElementById("pmp-current-file");
    refs.pageInfo = document.getElementById("pmp-page-info");
    refs.toolHint = document.getElementById("pmp-tool-hint");
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
      const response = await fetch(`${apiBase}/upload`, {
        method: "POST",
        body: data,
      });
      const payload = await response.json();
      if (!response.ok || !payload.ok) {
        throw new Error(payload.error ? payload.error.message : "No se pudo analizar el PDF.");
      }
      state.archivo = payload.archivo;
      state.pagina = payload.pagina || 1;
      state.medidasAuto = payload.medidas_auto || ns.emptyAuto();
      state.pendingPoint = null;
      state.measurements = [];
      state.selectedMeasurementId = null;
      state.finalRectangle = null;
      state.calibration = { activa: false, factor_escala: 1 };
      refs.emptyState.hidden = true;
      refs.exportButton.disabled = false;
      viewer.setPreview(payload.preview_url, payload.preview.render_mm || payload.render_mm);
      setStatus("PDF analizado.");
      setTimeout(renderAll, 100);
    } catch (error) {
      setStatus(error.message, true);
    }
  }

  function onCanvasClick(event) {
    if (refs.previewImage.hidden) {
      return;
    }
    const point = viewer.pointFromEvent(event);
    if (!state.pendingPoint) {
      state.pendingPoint = point;
      renderCanvas();
      return;
    }
    if (state.mode === "line") {
      const line = {
        id: `m_${Date.now()}`,
        a: state.pendingPoint,
        b: point,
      };
      state.measurements.push(line);
      state.selectedMeasurementId = line.id;
    } else {
      state.finalRectangle = ns.makeRectangle(state.pendingPoint, point);
    }
    state.pendingPoint = null;
    renderAll();
  }

  function setMode(mode) {
    state.mode = mode === "rectangle" ? "rectangle" : "line";
    state.pendingPoint = null;
    document.querySelectorAll("[data-pmp-tool]").forEach((button) => {
      button.classList.toggle("is-active", button.dataset.pmpTool === state.mode);
    });
    refs.toolHint.textContent = state.mode === "line"
      ? "Linea: selecciona dos puntos."
      : "Rectangulo: selecciona dos esquinas.";
    renderCanvas();
  }

  function clearMeasurements() {
    state.pendingPoint = null;
    state.measurements = [];
    state.selectedMeasurementId = null;
    state.finalRectangle = null;
    state.calibration = { activa: false, factor_escala: 1 };
    refs.calibrationReal.value = "";
    renderAll();
  }

  function calibrateSelected() {
    const selected = state.measurements.find((item) => item.id === state.selectedMeasurementId);
    if (!selected) {
      setStatus("Selecciona una linea para calibrar.", true);
      return;
    }
    try {
      const raw = ns.measureLine(selected, viewer, 1);
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
    refs.currentFile.textContent = state.archivo || "Ningun archivo";
    refs.pageInfo.textContent = `Pagina ${state.pagina || 1}`;
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
      refs.measurements.innerHTML = '<p class="pmp-muted">Sin lineas medidas.</p>';
      return;
    }
    refs.measurements.innerHTML = "";
    state.measurements.forEach((line, index) => {
      const measured = ns.measureLine(line, viewer, state.calibration.factor_escala);
      const button = document.createElement("button");
      button.type = "button";
      button.className = `pmp-measurement${line.id === state.selectedMeasurementId ? " is-selected" : ""}`;
      button.innerHTML = [
        `<strong>Linea ${index + 1}: ${fmt(measured.diagonal_mm)} mm</strong>`,
        `<small>H ${fmt(measured.horizontal_mm)} mm | V ${fmt(measured.vertical_mm)} mm</small>`,
        `<small>A(${fmt(measured.a.x)}, ${fmt(measured.a.y)}) B(${fmt(measured.b.x)}, ${fmt(measured.b.y)})</small>`,
      ].join("");
      button.addEventListener("click", () => {
        state.selectedMeasurementId = line.id;
        renderAll();
      });
      refs.measurements.appendChild(button);
    });
  }

  function renderFinalBox() {
    if (!state.finalRectangle) {
      refs.finalBox.textContent = "Sin rectangulo final.";
      return;
    }
    const measured = ns.measureRectangle(state.finalRectangle, viewer, state.calibration.factor_escala);
    refs.finalBox.innerHTML = [
      `<strong>${fmt(measured.ancho_final_mm)} x ${fmt(measured.alto_final_mm)} mm</strong>`,
      "<small>Origen de medida final: manual</small>",
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
    viewer.syncCanvas();
    viewer.clear();
    state.measurements.forEach((line) => {
      viewer.drawLine(line, line.id === state.selectedMeasurementId);
    });
    if (state.finalRectangle) {
      viewer.drawRectangle(state.finalRectangle, true);
    }
    if (state.pendingPoint) {
      viewer.ctx.save();
      viewer.ctx.fillStyle = "#b42318";
      viewer.drawPoint(state.pendingPoint);
      viewer.ctx.restore();
    }
  }

  function currentExportPayload() {
    const manualBox = state.finalRectangle
      ? ns.measureRectangle(state.finalRectangle, viewer, state.calibration.factor_escala)
      : { ancho_final_mm: 0, alto_final_mm: 0 };
    return ns.buildExportPayload(state, manualBox);
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
