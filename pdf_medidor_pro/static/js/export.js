(function () {
  "use strict";

  window.PdfMedidorPro = window.PdfMedidorPro || {};

  function buildExportPayload(state, manualBox, measurements, pages) {
    const hasManual = manualBox.ancho_final_mm > 0 && manualBox.alto_final_mm > 0;
    const payload = {
      archivo: state.archivo || "trabajo.pdf",
      pagina: state.pagina || 1,
      medidas_auto: state.medidasAuto || emptyAuto(),
      medidas_manual: manualBox,
      calibracion: state.calibration,
      origen_medida_final: state.finalOrigin || (hasManual ? "manual" : "auto"),
      confianza: state.finalConfidence || (hasManual ? "alta" : "media"),
      mediciones: Array.isArray(measurements) ? measurements : [],
    };
    if (state.pageCount) payload.page_count = state.pageCount;
    if (Array.isArray(pages)) payload.paginas = pages;
    return payload;
  }

  function emptyAuto() {
    return {
      mediabox_mm: { ancho: 0, alto: 0 },
      cropbox_mm: { ancho: 0, alto: 0 },
      trimbox_mm: { ancho: 0, alto: 0 },
      bleedbox_mm: { ancho: 0, alto: 0 },
      artbox_mm: { ancho: 0, alto: 0 },
    };
  }

  window.PdfMedidorPro.buildExportPayload = buildExportPayload;
  window.PdfMedidorPro.emptyAuto = emptyAuto;
})();
