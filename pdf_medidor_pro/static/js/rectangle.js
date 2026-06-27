(function () {
  "use strict";

  window.PdfMedidorPro = window.PdfMedidorPro || {};

  function makeRectangle(a, b, patch) {
    const x = Math.min(Number(a.x_mm || 0), Number(b.x_mm || 0));
    const y = Math.min(Number(a.y_mm || 0), Number(b.y_mm || 0));
    const w = Math.abs(Number(b.x_mm || 0) - Number(a.x_mm || 0));
    const h = Math.abs(Number(b.y_mm || 0) - Number(a.y_mm || 0));
    return Object.assign(
      {
        id: `r_${Date.now()}`,
        tipo: "rectangulo",
        origen: "manual",
        nombre: "Rectangulo manual",
        visible: true,
        x_mm: round(x),
        y_mm: round(y),
        ancho_mm: round(w),
        alto_mm: round(h),
        confianza: 1,
      },
      patch || {}
    );
  }

  function measureRectangle(rect, factor) {
    const scale = Number(factor || 1);
    return {
      ancho_final_mm: round(Number(rect.ancho_mm || 0) * scale),
      alto_final_mm: round(Number(rect.alto_mm || 0) * scale),
    };
  }

  function rectangleExport(rect, factor) {
    const measured = measureRectangle(rect, factor);
    return {
      id: rect.id,
      tipo: "rectangulo",
      origen: rect.origen || "manual",
      nombre: rect.nombre || "Rectangulo",
      visible: rect.visible !== false,
      ancho_mm: measured.ancho_final_mm,
      alto_mm: measured.alto_final_mm,
      x_mm: round(rect.x_mm),
      y_mm: round(rect.y_mm),
      area_mm2: round(measured.ancho_final_mm * measured.alto_final_mm),
      perimetro_mm: round((measured.ancho_final_mm + measured.alto_final_mm) * 2),
      confianza: rect.confianza || 1,
    };
  }

  function round(value) {
    return window.PdfMedidorPro.roundMm(value);
  }

  window.PdfMedidorPro.makeRectangle = makeRectangle;
  window.PdfMedidorPro.measureRectangle = measureRectangle;
  window.PdfMedidorPro.rectangleExport = rectangleExport;
})();
