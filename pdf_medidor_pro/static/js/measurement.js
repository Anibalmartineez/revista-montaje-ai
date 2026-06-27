(function () {
  "use strict";

  window.PdfMedidorPro = window.PdfMedidorPro || {};

  function measureLine(line, viewer, factor) {
    const mmX = viewer.mmPerPxX();
    const mmY = viewer.mmPerPxY();
    const scale = Number(factor || 1);
    const horizontal = Math.abs(line.b.x - line.a.x) * mmX * scale;
    const vertical = Math.abs(line.b.y - line.a.y) * mmY * scale;
    const diagonal = Math.hypot(horizontal, vertical);
    return {
      horizontal_mm: round(horizontal),
      vertical_mm: round(vertical),
      diagonal_mm: round(diagonal),
      a: { x: round(line.a.x), y: round(line.a.y) },
      b: { x: round(line.b.x), y: round(line.b.y) },
    };
  }

  function round(value) {
    return Math.round(Number(value || 0) * 1000) / 1000;
  }

  window.PdfMedidorPro.measureLine = measureLine;
  window.PdfMedidorPro.roundMm = round;
})();
