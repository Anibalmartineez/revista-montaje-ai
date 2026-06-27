(function () {
  "use strict";

  window.PdfMedidorPro = window.PdfMedidorPro || {};

  function makeRectangle(a, b) {
    const x = Math.min(a.x, b.x);
    const y = Math.min(a.y, b.y);
    const w = Math.abs(b.x - a.x);
    const h = Math.abs(b.y - a.y);
    return { x, y, w, h };
  }

  function measureRectangle(rect, viewer, factor) {
    const scale = Number(factor || 1);
    return {
      ancho_final_mm: window.PdfMedidorPro.roundMm(rect.w * viewer.mmPerPxX() * scale),
      alto_final_mm: window.PdfMedidorPro.roundMm(rect.h * viewer.mmPerPxY() * scale),
    };
  }

  window.PdfMedidorPro.makeRectangle = makeRectangle;
  window.PdfMedidorPro.measureRectangle = measureRectangle;
})();
