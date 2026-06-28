(function () {
  "use strict";

  window.PdfMedidorPro = window.PdfMedidorPro || {};

  function renderHistory(container, context) {
    if (!container) return;
    const items = context.measurements || [];
    const fmt = context.fmt;
    if (!items.length) {
      container.innerHTML = '<div class="pmp-empty-row">Sin mediciones.</div>';
      return;
    }
    container.innerHTML = [
      '<table class="pmp-history-table">',
      "<thead><tr><th>#</th><th>Tipo</th><th>Nombre</th><th>Valor</th><th>Pagina</th><th>Visible</th><th>Acciones</th></tr></thead>",
      "<tbody>",
      items.map((item, index) => renderRow(item, index, context, fmt)).join(""),
      "</tbody></table>",
    ].join("");
  }

  function bindHistory(container, handlers) {
    if (!container) return;
    container.querySelectorAll("[data-pmp-select]").forEach((button) => {
      button.addEventListener("click", () => handlers.select(button.dataset.pmpSelect));
    });
    container.querySelectorAll("[data-pmp-delete]").forEach((button) => {
      button.addEventListener("click", () => handlers.delete(button.dataset.pmpDelete));
    });
    container.querySelectorAll("[data-pmp-toggle-visible]").forEach((button) => {
      button.addEventListener("click", () => handlers.toggleVisible(button.dataset.pmpToggleVisible));
    });
    container.querySelectorAll("[data-pmp-use-final]").forEach((button) => {
      button.addEventListener("click", () => handlers.useFinal(button.dataset.pmpUseFinal));
    });
    container.querySelectorAll("[data-pmp-history-name]").forEach((input) => {
      input.addEventListener("change", () => handlers.rename(input.dataset.pmpHistoryName, input.value));
    });
  }

  function renderRow(item, index, context, fmt) {
    const metrics = context.metrics(item);
    const selected = item.id === context.selectedId ? " is-selected" : "";
    const value = item.tipo === "linea"
      ? `${fmt(metrics.distancia_mm)} mm`
      : `${fmt(metrics.ancho_mm)} x ${fmt(metrics.alto_mm)} mm`;
    return [
      `<tr class="${selected}">`,
      `<td>${index + 1}</td>`,
      `<td>${item.tipo === "linea" ? "Linea" : "Rectangulo"}</td>`,
      `<td><input class="pmp-table-input" data-pmp-history-name="${item.id}" value="${escapeAttr(item.nombre || "Medicion")}"></td>`,
      `<td>${value}</td>`,
      `<td>${item.pagina || context.page || 1}</td>`,
      `<td><button type="button" class="pmp-mini-button" data-pmp-toggle-visible="${item.id}">${item.visible === false ? "No" : "Si"}</button></td>`,
      '<td class="pmp-row-actions">',
      `<button type="button" class="pmp-mini-button" data-pmp-select="${item.id}">Seleccionar</button>`,
      item.tipo === "rectangulo" ? `<button type="button" class="pmp-mini-button" data-pmp-use-final="${item.id}">Final</button>` : "",
      `<button type="button" class="pmp-mini-button" data-pmp-delete="${item.id}">Eliminar</button>`,
      "</td>",
      "</tr>",
    ].join("");
  }

  function escapeAttr(value) {
    return String(value || "").replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");
  }

  window.PdfMedidorPro.renderHistory = renderHistory;
  window.PdfMedidorPro.bindHistory = bindHistory;
})();
