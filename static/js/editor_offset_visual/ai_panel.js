(function () {
  window.EditorOffsetVisual = window.EditorOffsetVisual || {};

  let pendingLayout = null;
  let pendingChangeType = null;

  function formatResponse(data) {
    if (!data || data.ok === false) {
      return (data && (data.message || data.error)) || 'No se pudo ejecutar la accion.';
    }
    const parts = [data.message || 'Accion ejecutada.'];
    const toolsUsed = Array.isArray(data.tools_used) ? data.tools_used.filter(Boolean) : [];
    const toolUsed = data.tool_used || (data.raw_tool_result && data.raw_tool_result.tool);
    if (toolsUsed.length) {
      parts.push(`Tools: ${toolsUsed.join(' -> ')}`);
    } else if (toolUsed) {
      parts.push(`Tool: ${toolUsed}`);
    }
    const zoneLabels = {
      auto: 'Automatico',
      top: 'Arriba',
      bottom: 'Abajo',
      left: 'Izquierda',
      right: 'Derecha',
      center: 'Centro',
    };
    const zoneChanges = data.data && Array.isArray(data.data.zone_changes) ? data.data.zone_changes : [];
    if (zoneChanges.length) {
      parts.push(
        `Zonas: ${zoneChanges
          .map((change) => `${change.design_ref || 'Diseno'} -> ${zoneLabels[change.preferred_zone] || change.preferred_zone || 'Automatico'}`)
          .join(', ')}`,
      );
    }
    const analysis = data.data && data.data.analysis;
    if (analysis) {
      parts.push(
        `Slots: ${analysis.slot_count}`,
        `Aprovechamiento: ${analysis.aprovechamiento_pct}%`,
      );
      if (analysis.area_libre_mm2 !== undefined) {
        parts.push(`Area libre: ${analysis.area_libre_mm2} mm2`);
      }
    }
    return parts.filter(Boolean).join('\n');
  }

  function getLayoutChangeType(data) {
    if (data && data.layout_change_type) return data.layout_change_type;
    const layoutMeta = data && data.layout && data.layout.ai_agent;
    if (layoutMeta && layoutMeta.layout_change_type) return layoutMeta.layout_change_type;
    return null;
  }

  async function runAssistant(ctx) {
    const byId = window.EditorOffsetVisual.domRefs.byId;
    const promptEl = byId('ai-prompt');
    const responseEl = byId('ai-response');
    const applyBtn = byId('btn-ai-apply');
    const runBtn = byId('btn-ai-run');
    if (!promptEl || !responseEl || !applyBtn) return;

    const prompt = promptEl.value.trim();
    if (!prompt) {
      responseEl.innerText = 'Escribi una instruccion.';
      return;
    }

    pendingLayout = null;
    pendingChangeType = null;
    applyBtn.hidden = true;
    responseEl.innerText = 'Procesando...';
    if (runBtn) runBtn.disabled = true;

    try {
      ctx.syncSettingsToLayout();
      const data = await window.EditorOffsetVisual.apiClient.runAi(prompt, ctx.state.layout);
      responseEl.innerText = formatResponse(data);

      if (data.ok === false) {
        if (data.error) alert(data.error);
        return;
      }

      if (data.layout && typeof data.layout === 'object') {
        pendingLayout = data.layout;
        pendingChangeType = getLayoutChangeType(data);
        applyBtn.hidden = false;
        if (pendingChangeType === 'metadata_only') {
          responseEl.innerText = `${responseEl.innerText}\n\nPreferencias listas para aplicar. No se regeneraron slots.`;
        } else {
          responseEl.innerText = `${responseEl.innerText}\n\nCambios listos para aplicar.`;
        }
      }
    } catch (err) {
      console.error(err);
      responseEl.innerText = 'Error al ejecutar la IA.';
    } finally {
      if (runBtn) runBtn.disabled = false;
    }
  }

  function applyLayout(ctx) {
    const byId = window.EditorOffsetVisual.domRefs.byId;
    const responseEl = byId('ai-response');
    const applyBtn = byId('btn-ai-apply');
    if (!pendingLayout) return;

    ctx.setLayout(pendingLayout);
    pendingLayout = null;
    const appliedChangeType = pendingChangeType;
    pendingChangeType = null;
    ctx.refreshEditorAfterLayoutReplace();
    ctx.pushHistory();

    if (applyBtn) applyBtn.hidden = true;
    if (responseEl) {
      responseEl.innerText = appliedChangeType === 'metadata_only' ? 'Preferencias aplicadas.' : 'Cambios aplicados.';
    }
  }

  window.EditorOffsetVisual.aiPanel = {
    formatResponse,
    getLayoutChangeType,
    runAssistant,
    applyLayout,
  };
})();
