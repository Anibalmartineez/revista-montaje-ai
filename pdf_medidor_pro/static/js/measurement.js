(function () {
  "use strict";

  window.PdfMedidorPro = window.PdfMedidorPro || {};

  function measureLine(line, factor) {
    const scale = Number(factor || 1);
    const horizontal = Math.abs(Number(line.b.x_mm || 0) - Number(line.a.x_mm || 0)) * scale;
    const vertical = Math.abs(Number(line.b.y_mm || 0) - Number(line.a.y_mm || 0)) * scale;
    const diagonal = Math.hypot(horizontal, vertical);
    return {
      horizontal_mm: round(horizontal),
      vertical_mm: round(vertical),
      diagonal_mm: round(diagonal),
      a: { x_mm: round(line.a.x_mm), y_mm: round(line.a.y_mm) },
      b: { x_mm: round(line.b.x_mm), y_mm: round(line.b.y_mm) },
    };
  }

  function lineExport(line, factor) {
    const measured = measureLine(line, factor);
    return {
      id: line.id,
      tipo: "linea",
      origen: line.origen || "manual",
      nombre: line.nombre || "Linea manual",
      visible: line.visible !== false,
      ancho_mm: measured.horizontal_mm,
      alto_mm: measured.vertical_mm,
      x_mm: Math.min(measured.a.x_mm, measured.b.x_mm),
      y_mm: Math.min(measured.a.y_mm, measured.b.y_mm),
      area_mm2: 0,
      perimetro_mm: measured.diagonal_mm,
      confianza: line.confianza || 1,
      a: measured.a,
      b: measured.b,
    };
  }

  function round(value) {
    return Math.round(Number(value || 0) * 1000) / 1000;
  }

  window.PdfMedidorPro.measureLine = measureLine;
  window.PdfMedidorPro.lineExport = lineExport;
  window.PdfMedidorPro.roundMm = round;
})();
