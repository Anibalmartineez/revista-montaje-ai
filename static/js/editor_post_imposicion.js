(function () {
  const jobId = window.__POST_EDITOR_JOB_ID__;
  if (!jobId) {
    console.warn('[post-editor] jobId no disponible');
    return;
  }

  const POST_EDITOR_DIR = 'ia_jobs';
  const API_BASE = `/layout/${jobId}`;
  const STATIC_BASE = `/static/${POST_EDITOR_DIR}/${jobId}/`;
  const GRID_DEFAULT = 5;

  const canvas = document.getElementById('editor-canvas');
  const statusEl = document.getElementById('editor-status');
  const assetSelect = document.getElementById('asset-select');
  const replaceBtn = document.getElementById('replace-btn');
  const swapBtn = document.getElementById('swap-btn');
  const saveBtn = document.getElementById('save-btn');
  const pdfLink = document.getElementById('pdf-link');
  const previewLink = document.getElementById('preview-link');
  const gridInfo = document.getElementById('grid-info');
  const sheetInfo = document.getElementById('sheet-info');

  let layoutData = null;
  let pieces = [];
  let scale = 2;
  let sheetEl = null;
  let dragState = null;
  const selectedIds = new Set();

  function setStatus(message, type = 'info') {
    if (!statusEl) return;
    statusEl.textContent = message || '';
    statusEl.style.color = type === 'error' ? '#c62828' : type === 'success' ? '#2e7d32' : '#333';
  }

  function mmToPx(mm) {
    return mm * scale;
  }

  function pxToMm(px) {
    return px / scale;
  }

  function snapValue(value, step) {
    if (!step || step <= 0) return value;
    return Math.round(value / step) * step;
  }

  function clamp(value, min, max) {
    return Math.min(Math.max(value, min), max);
  }

  function computeGridStep(grid) {
    if (!grid) return GRID_DEFAULT;
    if (typeof grid === 'number' && grid > 0) {
      return grid;
    }
    if (typeof grid === 'object') {
      const values = ['cell_w', 'cell_h', 'step', 'mm'].map((k) => parseFloat(grid[k]));
      for (const v of values) {
        if (Number.isFinite(v) && v > 0) return v;
      }
    }
    return GRID_DEFAULT;
  }

  function clearSelection() {
    selectedIds.clear();
    pieces.forEach((p) => p.element.classList.remove('selected'));
  }

  function toggleSelection(id, additive) {
    if (!additive) {
      clearSelection();
    }
    if (selectedIds.has(id)) {
      selectedIds.delete(id);
    } else {
      selectedIds.add(id);
    }
    pieces.forEach((p) => {
      p.element.classList.toggle('selected', selectedIds.has(p.id));
    });
  }

  function markOverlaps() {
    const eps = 1e-6;
    pieces.forEach((p) => p.element.classList.remove('overlap'));
    for (let i = 0; i < pieces.length; i++) {
      const a = pieces[i];
      const ax2 = a.x_mm + a.w_mm;
      const ay2 = a.y_mm + a.h_mm;
      for (let j = i + 1; j < pieces.length; j++) {
        const b = pieces[j];
        const bx2 = b.x_mm + b.w_mm;
        const by2 = b.y_mm + b.h_mm;
        const separated =
          a.x_mm >= bx2 - eps ||
          b.x_mm >= ax2 - eps ||
          a.y_mm >= by2 - eps ||
          b.y_mm >= ay2 - eps;
        if (!separated) {
          a.element.classList.add('overlap');
          b.element.classList.add('overlap');
        }
      }
    }
  }

  function updatePiecePosition(piece) {
    piece.element.style.left = `${mmToPx(piece.x_mm)}px`;
    piece.element.style.bottom = `${mmToPx(piece.y_mm)}px`;
    piece.element.style.width = `${mmToPx(piece.w_mm)}px`;
    piece.element.style.height = `${mmToPx(piece.h_mm)}px`;
    piece.element.dataset.xMm = piece.x_mm;
    piece.element.dataset.yMm = piece.y_mm;
  }

  function createPieceElement(piece) {
    const el = document.createElement('div');
    el.className = 'piece';
    el.dataset.id = piece.id;
    el.textContent = piece.label || piece.id;
    updatePiecePosition(piece);

    el.addEventListener('pointerdown', (evt) => {
      evt.preventDefault();
      evt.stopPropagation();
      const additive = evt.shiftKey || evt.metaKey || evt.ctrlKey;
      toggleSelection(piece.id, additive);
      dragState = {
        id: piece.id,
        pointerId: evt.pointerId,
        startX: evt.clientX,
        startY: evt.clientY,
        originX: piece.x_mm,
        originY: piece.y_mm,
      };
      el.setPointerCapture(evt.pointerId);
      el.classList.add('dragging');
      setStatus('Arrastrando pieza…');
    });

    el.addEventListener('pointermove', (evt) => {
      if (!dragState || dragState.id !== piece.id) {
        return;
      }
      evt.preventDefault();
      const dx = pxToMm(evt.clientX - dragState.startX);
      const dy = pxToMm(evt.clientY - dragState.startY);
      const sheet = layoutData.sheet;
      const maxX = sheet.w_mm - piece.w_mm;
      const maxY = sheet.h_mm - piece.h_mm;
      let newX = clamp(dragState.originX + dx, 0, maxX);
      let newY = clamp(dragState.originY + dy, 0, maxY);
      piece.x_mm = newX;
      piece.y_mm = newY;
      updatePiecePosition(piece);
      markOverlaps();
    });

    function finalizeDrag(evt) {
      if (!dragState || dragState.id !== piece.id) {
        return;
      }
      evt.preventDefault();
      const gridStep = computeGridStep(layoutData.grid_mm);
      piece.x_mm = snapValue(piece.x_mm, gridStep);
      piece.y_mm = snapValue(piece.y_mm, gridStep);
      const sheet = layoutData.sheet;
      const maxX = sheet.w_mm - piece.w_mm;
      const maxY = sheet.h_mm - piece.h_mm;
      piece.x_mm = clamp(piece.x_mm, 0, maxX);
      piece.y_mm = clamp(piece.y_mm, 0, maxY);
      updatePiecePosition(piece);
      markOverlaps();
      dragState = null;
      el.classList.remove('dragging');
      setStatus('');
      try {
        el.releasePointerCapture(evt.pointerId);
      } catch (captureErr) {
        /* ignore */
      }
    }

    el.addEventListener('pointerup', finalizeDrag);
    el.addEventListener('pointercancel', finalizeDrag);

    el.addEventListener('dblclick', () => {
      toggleSelection(piece.id, false);
      setStatus('Seleccionar reemplazo y presionar "Reemplazar pieza".');
    });

    return el;
  }

  function buildAssetsSelect(assets) {
    if (!assetSelect) return;
    assetSelect.innerHTML = '';
    const options = assets && assets.length ? assets : [];
    options.forEach((asset) => {
      const opt = document.createElement('option');
      const label = asset.original_src || asset.src || `Asset ${asset.file_idx}`;
      opt.value = String(asset.file_idx ?? asset.id ?? asset.src);
      opt.dataset.src = asset.src;
      opt.dataset.fileIdx = asset.file_idx != null ? asset.file_idx : '';
      opt.textContent = label.split(/[\\/]/).pop();
      assetSelect.appendChild(opt);
    });
  }

  function renderLayout(data) {
    layoutData = data;
    if (!layoutData.pdf_filename) {
      layoutData.pdf_filename = 'pliego.pdf';
    }
    if (!layoutData.preview_filename) {
      layoutData.preview_filename = 'preview_edit.png';
    }
    pieces = [];
    canvas.innerHTML = '';

    const sheet = data.sheet || { w_mm: 0, h_mm: 0 };
    sheet.w_mm = Number(sheet.w_mm) || 0;
    sheet.h_mm = Number(sheet.h_mm) || 0;
    if (!sheet.w_mm || !sheet.h_mm) {
      setStatus('Sheet inválido en layout', 'error');
      return;
    }

    const maxWidthPx = 900;
    scale = Math.min(2, maxWidthPx / sheet.w_mm);
    if (scale <= 0) scale = 1.5;

    sheetEl = document.createElement('div');
    sheetEl.className = 'sheet';
    sheetEl.style.width = `${mmToPx(sheet.w_mm)}px`;
    sheetEl.style.height = `${mmToPx(sheet.h_mm)}px`;
    sheetEl.addEventListener('pointerdown', (evt) => {
      if (evt.target === sheetEl) {
        clearSelection();
        setStatus('');
      }
    });

    canvas.appendChild(sheetEl);

    const items = Array.isArray(data.items) ? data.items : [];
    items.forEach((item, index) => {
      const piece = {
        id: item.id || `item${index}`,
        src: item.src,
        file_idx: Number(item.file_idx ?? index),
        x_mm: Number(item.x_mm) || 0,
        y_mm: Number(item.y_mm) || 0,
        w_mm: Number(item.w_mm) || 0,
        h_mm: Number(item.h_mm) || 0,
        rotation: Number(item.rotation || 0),
        flip_x: Boolean(item.flip_x),
        flip_y: Boolean(item.flip_y),
        page: Number(item.page || 0),
        label: item.label || `${index + 1}`,
      };
      piece.element = createPieceElement(piece);
      sheetEl.appendChild(piece.element);
      pieces.push(piece);
    });

    buildAssetsSelect(data.assets || []);
    updateLinks();
    updateInfo();
    markOverlaps();
  }

  function updateInfo() {
    if (gridInfo && layoutData) {
      const grid = computeGridStep(layoutData.grid_mm);
      gridInfo.textContent = `Grid: ${grid.toFixed(2)} mm`;
    }
    if (sheetInfo && layoutData && layoutData.sheet) {
      const { w_mm, h_mm } = layoutData.sheet;
      sheetInfo.textContent = `Hoja: ${Number(w_mm).toFixed(1)} × ${Number(h_mm).toFixed(1)} mm`;
    }
  }

  function updateLinks() {
    if (!layoutData) return;
    if (pdfLink) {
      pdfLink.href = `${STATIC_BASE}${layoutData.pdf_filename || 'pliego.pdf'}`;
    }
    if (previewLink) {
      previewLink.href = `${STATIC_BASE}${layoutData.preview_filename || 'preview_edit.png'}`;
    }
  }

  function ensureSingleSelection(actionName) {
    if (selectedIds.size !== 1) {
      setStatus(`Seleccioná exactamente una pieza para ${actionName}.`, 'error');
      return null;
    }
    const id = Array.from(selectedIds)[0];
    return pieces.find((p) => p.id === id) || null;
  }

  function replaceSelected() {
    const piece = ensureSingleSelection('reemplazar');
    if (!piece || !assetSelect || assetSelect.options.length === 0) {
      return;
    }
    const option = assetSelect.options[assetSelect.selectedIndex];
    const src = option.dataset.src;
    const fileIdx = option.dataset.fileIdx ? Number(option.dataset.fileIdx) : piece.file_idx;
    if (!src) {
      setStatus('Seleccioná un recurso válido.', 'error');
      return;
    }
    piece.src = src;
    piece.file_idx = fileIdx;
    piece.element.textContent = option.textContent || piece.element.textContent;
    setStatus('Pieza reemplazada. Recordá guardar los cambios.', 'success');
  }

  function swapSelected() {
    if (selectedIds.size !== 2) {
      setStatus('Seleccioná dos piezas para intercambiar.', 'error');
      return;
    }
    const [idA, idB] = Array.from(selectedIds);
    const pieceA = pieces.find((p) => p.id === idA);
    const pieceB = pieces.find((p) => p.id === idB);
    if (!pieceA || !pieceB) return;
    const tmp = { x: pieceA.x_mm, y: pieceA.y_mm };
    pieceA.x_mm = pieceB.x_mm;
    pieceA.y_mm = pieceB.y_mm;
    pieceB.x_mm = tmp.x;
    pieceB.y_mm = tmp.y;
    updatePiecePosition(pieceA);
    updatePiecePosition(pieceB);
    markOverlaps();
    setStatus('Posiciones intercambiadas. Recordá guardar los cambios.', 'success');
  }

  function serializePieces() {
    return pieces.map((piece) => ({
      id: piece.id,
      src: piece.src,
      page: piece.page || 0,
      x_mm: Number(piece.x_mm.toFixed(3)),
      y_mm: Number(piece.y_mm.toFixed(3)),
      w_mm: Number(piece.w_mm.toFixed(3)),
      h_mm: Number(piece.h_mm.toFixed(3)),
      rotation: Number(piece.rotation || 0),
      flip_x: Boolean(piece.flip_x),
      flip_y: Boolean(piece.flip_y),
    }));
  }

  async function saveLayout() {
    setStatus('Guardando cambios…');
    try {
      const body = {
        version: layoutData?.version || 1,
        items: serializePieces(),
      };
      const resp = await fetch(`${API_BASE}/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await resp.json();
      if (!resp.ok || !data.ok) {
        throw new Error(data.error || 'No se pudo guardar el layout');
      }
      layoutData.preview_filename = 'preview_edit.png';
      layoutData.pdf_filename = 'pliego_edit.pdf';
      updateLinks();
      if (data.pdf_url) {
        pdfLink.href = data.pdf_url;
      }
      if (data.preview_url) {
        previewLink.href = data.preview_url;
      }
      setStatus('Montaje guardado correctamente.', 'success');
    } catch (err) {
      console.error('[post-editor] save error', err);
      setStatus(err.message || 'Error al guardar el layout', 'error');
    }
  }

  function initEvents() {
    if (replaceBtn) replaceBtn.addEventListener('click', replaceSelected);
    if (swapBtn) swapBtn.addEventListener('click', swapSelected);
    if (saveBtn) saveBtn.addEventListener('click', saveLayout);
  }

  async function loadLayout() {
    setStatus('Cargando layout…');
    try {
      const resp = await fetch(`${API_BASE}.json`, { cache: 'no-store' });
      if (!resp.ok) {
        throw new Error('No se pudo obtener el layout del servidor');
      }
      const data = await resp.json();
      renderLayout(data);
      setStatus('');
    } catch (err) {
      console.error('[post-editor] load error', err);
      setStatus(err.message || 'Error al cargar layout', 'error');
    }
  }

  initEvents();
  loadLayout();
})();
