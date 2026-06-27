(function () {
  "use strict";

  window.PdfMedidorPro = window.PdfMedidorPro || {};

  function parseCommand(value) {
    const text = normalize(value);
    if (!text) {
      return { action: "empty", needsClick: false, message: "Escribe un comando." };
    }
    if (text.includes("medi esta etiqueta") || text.includes("mide esta etiqueta")) {
      return { action: "detect_click", needsClick: true, name: "Etiqueta (IA)", message: "Ahora hace clic sobre el objeto." };
    }
    if (text.includes("conta cuantas etiquetas") || text.includes("contar etiquetas")) {
      return { action: "count", needsClick: false, message: "Contando objetos candidatos." };
    }
    if (text.includes("medi la separacion") || text.includes("mide la separacion")) {
      return { action: "measure_gap", needsClick: true, name: "Separacion (IA)", message: "Ahora hace clic cerca de la separacion." };
    }
    if (text.includes("detectar area impresa")) {
      return { action: "printed_area", needsClick: false, message: "Detectando area impresa." };
    }
    if (text.includes("buscar sangrado")) {
      return { action: "bleed_hint", needsClick: false, message: "Sangrado: compara BleedBox/TrimBox automaticos y valida manualmente." };
    }
    return { action: "unknown", needsClick: false, message: "No pude resolver ese comando todavia." };
  }

  function normalize(value) {
    return String(value || "")
      .trim()
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "");
  }

  window.PdfMedidorPro.parseAiCommand = parseCommand;
})();
