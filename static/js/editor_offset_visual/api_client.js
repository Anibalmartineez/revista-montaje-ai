(function () {
  window.EditorOffsetVisual = window.EditorOffsetVisual || {};

  async function saveLayout(jobId, layoutJson) {
    const body = new FormData();
    body.append('job_id', jobId);
    body.append('layout_json', layoutJson);
    const res = await fetch('/editor_offset/save', { method: 'POST', body });
    return res.json();
  }

  async function requestAutoLayout(jobId, layoutJson) {
    const res = await fetch(`/editor_offset/auto_layout/${jobId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ layout_json: layoutJson }),
    });
    return res.json();
  }

  async function applyImposition(jobId, selectedEngine, layoutJson) {
    const body = new FormData();
    body.append('job_id', jobId);
    body.append('selected_engine', selectedEngine);
    body.append('layout_json', layoutJson);
    const res = await fetch('/editor_offset_visual/apply_imposition', { method: 'POST', body });
    return res.json();
  }

  async function runAi(prompt, layout) {
    const res = await fetch('/ai/step_repeat_action_openai', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt,
        layout_json: layout,
      }),
    });
    return res.json();
  }

  async function simulateBooklet(payload) {
    const res = await fetch('/editor_offset/cuadernillos/simular', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    return { ok: res.ok, data };
  }

  async function requestPreview(jobId) {
    const res = await fetch(`/editor_offset/preview/${jobId}`, { method: 'POST' });
    const data = await res.json();
    return { ok: res.ok, data };
  }

  async function requestPdf(jobId) {
    const res = await fetch(`/editor_offset/generar_pdf/${jobId}`, { method: 'POST' });
    const data = await res.json();
    return { ok: res.ok, data };
  }

  async function uploadDesigns(jobId, files, workId) {
    const body = new FormData();
    for (const file of files) body.append('files', file);
    if (workId) {
      body.append('work_id', workId);
    }
    const res = await fetch(`/editor_offset/upload/${jobId}`, { method: 'POST', body });
    return res.json();
  }

  window.EditorOffsetVisual.apiClient = {
    saveLayout,
    requestAutoLayout,
    applyImposition,
    runAi,
    simulateBooklet,
    requestPreview,
    requestPdf,
    uploadDesigns,
  };
})();
