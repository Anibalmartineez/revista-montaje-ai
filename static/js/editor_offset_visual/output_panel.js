(function () {
  window.EditorOffsetVisual = window.EditorOffsetVisual || {};

  function buildDetails(data) {
    return []
      .concat((data.errors || []).map((item) => `- ${item.message}`))
      .concat((data.warnings || []).map((item) => `- Warning: ${item.message}`));
  }

  async function requestPreview(ctx) {
    if (!ctx.state.layout.slots || ctx.state.layout.slots.length === 0) {
      alert('No hay slots en el pliego. Crea o genera los cuadros antes de generar la preview/PDF.');
      return;
    }
    const validation = ctx.refreshGeometryValidation();
    ctx.renderGeometryValidationPanel();
    if (validation.errors.length || validation.warnings.length) {
      alert(
        `Advertencia geomÃƒÂ©trica antes de la preview:\n- ${validation.errors.length} errores\n- ${validation.warnings.length} advertencias\nRevisa el panel debajo del pliego para mÃƒÂ¡s detalle.`,
      );
    }
    await ctx.saveLayout();
    const result = await window.EditorOffsetVisual.apiClient.requestPreview(ctx.jobId);
    const data = result.data;
    if (!result.ok || data.ok === false) {
      alert([data.error || 'No se pudo generar la preview.', ...buildDetails(data)].join('\n'));
      return;
    }
    if (data.url) {
      ctx.previewImg.src = data.url + `?t=${Date.now()}`;
    }
    if (data.warnings && data.warnings.length) {
      alert(`Preview generada con advertencias:\n${data.warnings.map((item) => `- ${item.message}`).join('\n')}`);
    }
  }

  async function requestPdf(ctx) {
    if (!ctx.state.layout.slots || ctx.state.layout.slots.length === 0) {
      alert('No hay slots en el pliego. Crea o genera los cuadros antes de generar la preview/PDF.');
      return;
    }
    const validation = ctx.refreshGeometryValidation();
    ctx.renderGeometryValidationPanel();
    if (validation.errors.length || validation.warnings.length) {
      alert(
        `Advertencia geomÃƒÂ©trica antes del PDF:\n- ${validation.errors.length} errores\n- ${validation.warnings.length} advertencias\nRevisa el panel debajo del pliego para mÃƒÂ¡s detalle.`,
      );
    }
    await ctx.saveLayout();
    const result = await window.EditorOffsetVisual.apiClient.requestPdf(ctx.jobId);
    const data = result.data;
    if (!result.ok || data.ok === false) {
      alert([data.error || 'No se pudo generar el PDF final.', ...buildDetails(data)].join('\n'));
      return;
    }
    if (data.url) {
      ctx.pdfOutput.innerHTML = `<a href="${data.url}" target="_blank">Descargar PDF</a>`;
    }
    if (data.warnings && data.warnings.length) {
      alert(`PDF generado con advertencias:\n${data.warnings.map((item) => `- ${item.message}`).join('\n')}`);
    }
  }

  window.EditorOffsetVisual.outputPanel = {
    requestPreview,
    requestPdf,
  };
})();
