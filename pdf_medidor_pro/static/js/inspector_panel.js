(function () {
  "use strict";

  window.PdfMedidorPro = window.PdfMedidorPro || {};

  function renderInspector(container, context) {
    const selected = context.selected;
    const selectedGuide = context.selectedGuide;
    const fmt = context.fmt;
    if (!container) return;
    if (selectedGuide) {
      container.innerHTML = renderGuideInfo(selectedGuide, fmt);
      return;
    }
    if (!selected) {
      container.innerHTML = renderPdfInfo(context, fmt);
      return;
    }
    const metrics = context.metrics(selected);
    container.innerHTML = [
      '<div class="pmp-inspector-grid">',
      field("Tipo", labelType(selected.tipo), true),
      input("Nombre", "pmp-inspector-name", selected.nombre || "Medicion", "text"),
      input("Color", "pmp-inspector-color", selected.color || "#0f766e", "color"),
      checkbox("Visible", "pmp-inspector-visible", selected.visible !== false),
      field("X", `${fmt(metrics.x_mm)} mm`, true),
      field("Y", `${fmt(metrics.y_mm)} mm`, true),
      number("Ancho", "pmp-inspector-width", metrics.ancho_mm, selected.tipo === "rectangulo"),
      number("Alto", "pmp-inspector-height", metrics.alto_mm, selected.tipo === "rectangulo"),
      field("Area", `${fmt(metrics.area_mm2)} mm2`, true),
      field("Perimetro", `${fmt(metrics.perimetro_mm)} mm`, true),
      field("Angulo", `${fmt(metrics.angulo_deg)} deg`, true),
      field("Pagina", selected.pagina || context.page || 1, true),
      "</div>",
      selected.tipo === "rectangulo"
        ? '<button class="pmp-button pmp-full" type="button" id="pmp-inspector-final">Usar como medida final</button>'
        : "",
      '<button class="pmp-button pmp-full" type="button" id="pmp-inspector-duplicate">Duplicar</button>',
    ].join("");
  }

  function bindInspector(container, handlers) {
    if (!container) return;
    const name = container.querySelector("#pmp-inspector-name");
    const color = container.querySelector("#pmp-inspector-color");
    const visible = container.querySelector("#pmp-inspector-visible");
    const width = container.querySelector("#pmp-inspector-width");
    const height = container.querySelector("#pmp-inspector-height");
    const final = container.querySelector("#pmp-inspector-final");
    const duplicate = container.querySelector("#pmp-inspector-duplicate");
    const guideVisible = container.querySelector("#pmp-inspector-guide-visible");
    if (name) name.addEventListener("change", () => handlers.rename(name.value));
    if (color) color.addEventListener("input", () => handlers.color(color.value));
    if (visible) visible.addEventListener("change", () => handlers.visible(visible.checked));
    if (width) width.addEventListener("change", () => handlers.resize(Number(width.value), null));
    if (height) height.addEventListener("change", () => handlers.resize(null, Number(height.value)));
    if (final) final.addEventListener("click", handlers.useFinal);
    if (duplicate) duplicate.addEventListener("click", handlers.duplicate);
    if (guideVisible && handlers.guideVisible) guideVisible.addEventListener("change", () => handlers.guideVisible(guideVisible.checked));
  }

  function renderGuideInfo(guide, fmt) {
    const orientation = guide.orientation === "horizontal" ? "horizontal" : "vertical";
    const axis = orientation === "vertical" ? "X" : "Y";
    const position = guide.position_mm !== undefined && guide.position_mm !== null ? guide.position_mm : guide.value_mm;
    return [
      '<div class="pmp-inspector-grid">',
      field("Tipo", orientation === "vertical" ? "Guia vertical" : "Guia horizontal", true),
      field("Orientacion", orientation, true),
      field(axis, `${fmt(position)} mm`, true),
      checkbox("Visible", "pmp-inspector-guide-visible", guide.visible !== false),
      field("Bloqueada", guide.locked ? "Si" : "No", true),
      "</div>",
    ].join("");
  }

  function renderPdfInfo(context, fmt) {
    const auto = context.medidasAuto || {};
    const rows = [
      ["Archivo", context.archivo || "Sin PDF"],
      ["Pagina", context.page || 1],
      ["Paginas", context.pageCount || context.page || 1],
      ["Render", `${fmt(context.renderMm.ancho)} x ${fmt(context.renderMm.alto)} mm`],
      ["MediaBox", box(auto.mediabox_mm, fmt)],
      ["CropBox", box(auto.cropbox_mm, fmt)],
      ["TrimBox", box(auto.trimbox_mm, fmt)],
      ["BleedBox", box(auto.bleedbox_mm, fmt)],
      ["ArtBox", box(auto.artbox_mm, fmt)],
    ];
    return [
      '<div class="pmp-inspector-grid">',
      rows.map(([label, value]) => field(label, value, true)).join(""),
      "</div>",
    ].join("");
  }

  function box(value, fmt) {
    const item = value || { ancho: 0, alto: 0 };
    return `${fmt(item.ancho)} x ${fmt(item.alto)} mm`;
  }

  function field(label, value) {
    return `<label class="pmp-field"><span>${label}</span><output>${value}</output></label>`;
  }

  function input(label, id, value, type) {
    return `<label class="pmp-field"><span>${label}</span><input id="${id}" type="${type}" value="${escapeAttr(value)}"></label>`;
  }

  function number(label, id, value, enabled) {
    return `<label class="pmp-field"><span>${label}</span><input id="${id}" type="number" step="0.001" min="0.001" value="${Number(value || 0)}"${enabled ? "" : " disabled"}></label>`;
  }

  function checkbox(label, id, checked) {
    return `<label class="pmp-toggle"><input id="${id}" type="checkbox"${checked ? " checked" : ""}><span>${label}</span></label>`;
  }

  function labelType(type) {
    return type === "linea" ? "Linea" : "Rectangulo";
  }

  function escapeAttr(value) {
    return String(value || "").replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");
  }

  window.PdfMedidorPro.renderInspector = renderInspector;
  window.PdfMedidorPro.bindInspector = bindInspector;
})();
