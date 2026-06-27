(function () {
  "use strict";

  window.PdfMedidorPro = window.PdfMedidorPro || {};

  function calculateScaleFactor(measuredMm, realMm) {
    const measured = Number(measuredMm || 0);
    const real = Number(realMm || 0);
    if (measured <= 0 || real <= 0) {
      throw new Error("La medicion y la medida real deben ser mayores que cero.");
    }
    return Math.round((real / measured) * 1000000) / 1000000;
  }

  window.PdfMedidorPro.calculateScaleFactor = calculateScaleFactor;
})();
