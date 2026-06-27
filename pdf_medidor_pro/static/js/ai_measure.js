(function () {
  "use strict";

  window.PdfMedidorPro = window.PdfMedidorPro || {};

  async function detectObject(apiBase, state, point, name) {
    const response = await fetch(`${apiBase}/ai/detect`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        preview_filename: state.previewFilename,
        render_mm: state.renderMm,
        x_mm: point.x_mm,
        y_mm: point.y_mm,
        nombre: name || "Objeto detectado (IA)",
      }),
    });
    return parseAiResponse(response);
  }

  async function detectPrintedArea(apiBase, state) {
    const response = await fetch(`${apiBase}/ai/printed-area`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        preview_filename: state.previewFilename,
        render_mm: state.renderMm,
      }),
    });
    return parseAiResponse(response);
  }

  async function countObjects(apiBase, state) {
    const response = await fetch(`${apiBase}/ai/count`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ preview_filename: state.previewFilename }),
    });
    const payload = await response.json();
    if (!response.ok || !payload.ok) {
      throw new Error(payload.error ? payload.error.message : "No se pudo contar objetos.");
    }
    return payload;
  }

  async function parseAiResponse(response) {
    const payload = await response.json();
    if (!response.ok || !payload.ok) {
      throw new Error(payload.error ? payload.error.message : "No se pudo medir con IA.");
    }
    return payload.measurement;
  }

  window.PdfMedidorPro.aiMeasure = { detectObject, detectPrintedArea, countObjects };
})();
