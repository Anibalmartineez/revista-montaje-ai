(function () {
  const jobId = window.jobIdIA || window.__POST_EDITOR_JOB_ID__;
  const initialLayout = window.layoutIA || null;
  if (!jobId) {
    console.warn('[post-editor] jobId no disponible');
    return;
  }

  const POST_EDITOR_DIR = 'ia_jobs';
  const API_BASE = `/layout/${jobId}`;
  const STATIC_BASE = `/static/${POST_EDITOR_DIR}/${jobId}/`;
  const GRID_DEFAULT = 5;
  const MIN_ZOOM = 0.1;
  const MAX_ZOOM = 4;
  const SNAP_TOLERANCE_MM = 2;

  const canvas = document.getElementById('editor-canvas');
  const sheetViewport = document.getElementById('sheet-viewport');
  const zoomContainer = document.getElementById('sheet-zoom-container');
  const panContainer = document.getElementById('sheet-pan-container');
  const guidesLayer = document.getElementById('guides-layer');
  const marqueeEl = document.getElementById('selection-marquee');
  const tooltipEl = document.getElementById('piece-tooltip');
  const statusEl = document.getElementById('editor-status');
  const assetSelect = document.getElementById('asset-select');
  const replaceBtn = document.getElementById('replace-btn');
  const swapBtn = document.getElementById('swap-btn');
  const saveBtn = document.getElementById('save-btn');
  const duplicateBtn = document.getElementById('duplicate-btn');
  const undoBtn = document.getElementById('undo-btn');
  const redoBtn = document.getElementById('redo-btn');
  const pdfLink = document.getElementById('pdf-link');
  const previewLink = document.getElementById('preview-link');
  const gridInfo = document.getElementById('grid-info');
  const sheetInfo = document.getElementById('sheet-info');
  const zoomInBtn = document.getElementById('zoom-in');
  const zoomOutBtn = document.getElementById('zoom-out');
  const zoomResetBtn = document.getElementById('zoom-reset');
  const notificationArea = document.getElementById('notification-area');
  const statusSheetSize = document.getElementById('status-sheet-size');
  const statusPieceCount = document.getElementById('status-piece-count');
  const statusBreakdown = document.getElementById('status-breakdown');
  const statusOccupancy = document.getElementById('status-occupancy');
  const statusWarnings = document.getElementById('status-warnings');
  const propertiesPanel = {
    x: document.getElementById('prop-x'),
    y: document.getElementById('prop-y'),
    w: document.getElementById('prop-w'),
    h: document.getElementById('prop-h'),
    rot: document.getElementById('prop-rot'),
    locked: document.getElementById('prop-locked'),
  };
  const trimPanel = {
    w: document.getElementById('prop-trim-w'),
    h: document.getElementById('prop-trim-h'),
    bleed: document.getElementById('prop-bleed'),
  };
  const trimToggle = document.getElementById('toggle-trim-box');
  const bleedToggle = document.getElementById('toggle-bleed-box');
  const gapInputs = {
    h: document.getElementById('gap-h-mm'),
    v: document.getElementById('gap-v-mm'),
  };
  const gapApplySelectionBtn = document.getElementById('gap-apply-selection');
  const gapApplySheetBtn = document.getElementById('gap-apply-sheet');
  const alignButtons = Array.from(document.querySelectorAll('.align-btn'));
  const rulerTop = document.getElementById('ruler-top');
  const rulerLeft = document.getElementById('ruler-left');

  let layoutData = null;
  let pieces = [];
  let baseScale = 1.5; // px per mm before zoom
  let zoomScale = 1; // zoom factor for view (zoom/pan comment)
  let pan = { x: 0, y: 0 }; // translate in px
  let sheetEl = null;
  let dragState = null;
  let panState = null;
  let marqueeState = null;
  let pinchState = null;
  let spacePressed = false;
  let showTrimBox = true;
  let showBleedBox = true;
  const selectedIds = new Set();
  const horizontalGuides = [];
  const verticalGuides = [];
  let pendingIaActions = null;
  const iaNamedBBoxes = {};
  const undoStack = [];
  const redoStack = [];

  function setStatus(message, type = 'info') {
    if (!statusEl) return;
    statusEl.textContent = message || '';
    statusEl.style.color =
      type === 'error' ? '#c62828' : type === 'success' ? '#2e7d32' : '#333';
  }

  function showToast(message, type = 'info') {
    if (!notificationArea) return;
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.textContent = message;
    notificationArea.appendChild(el);
    setTimeout(() => {
      el.style.opacity = '0';
      el.style.transition = 'opacity 0.5s ease';
      setTimeout(() => el.remove(), 600);
    }, 2500);
  }

  function mmToPx(mm) {
    return mm * baseScale * zoomScale;
  }

  function pxToMm(px) {
    return px / (baseScale * zoomScale);
  }

  function snapValue(value, step) {
    if (!step || step <= 0) return value;
    return Math.round(value / step) * step;
  }

  function clamp(value, min, max) {
    return Math.min(Math.max(value, min), max);
  }

  function getBleedMm(piece) {
    // Si la pieza tiene un override numérico de sangrado, lo usamos primero.
    if (piece && typeof piece.bleed_override_mm === 'number') {
      const valOverride = Number(piece.bleed_override_mm);
      if (Number.isFinite(valOverride) && valOverride >= 0) {
        return valOverride;
      }
    }
    // Si no hay override, usamos el sangrado global del layout.
    const bleed = layoutData?.bleed_mm;
    const val = Number(bleed);
    return Number.isFinite(val) && val > 0 ? val : 0;
  }

  function updatePieceOverlays(piece) {
    if (!piece || !piece.element) return;
    const bleedMm = getBleedMm(piece);

    let trimBox = piece.element.querySelector('.piece-trim-box');
    let bleedBox = piece.element.querySelector('.piece-bleed-box');

    if (!trimBox) {
      trimBox = document.createElement('div');
      trimBox.className = 'piece-trim-box';
      piece.element.appendChild(trimBox);
    }
    if (!bleedBox) {
      bleedBox = document.createElement('div');
      bleedBox.className = 'piece-bleed-box';
      piece.element.appendChild(bleedBox);
    }

    // Caja de trim: coincide con la pieza (medida final).
    trimBox.style.display = showTrimBox ? 'block' : 'none';
    trimBox.style.left = '0';
    trimBox.style.right = '0';
    trimBox.style.top = '0';
    trimBox.style.bottom = '0';

    // Caja de sangrado: se extiende hacia afuera de la pieza.
    bleedBox.style.display = showBleedBox && bleedMm > 0 ? 'block' : 'none';
    if (bleedMm > 0) {
      const insetPx = bleedMm * baseScale;
      bleedBox.style.left = `${-insetPx}px`;
      bleedBox.style.right = `${-insetPx}px`;
      bleedBox.style.top = `${-insetPx}px`;
      bleedBox.style.bottom = `${-insetPx}px`;
    } else {
      bleedBox.style.left = '0';
      bleedBox.style.right = '0';
      bleedBox.style.top = '0';
      bleedBox.style.bottom = '0';
    }
  }

  function appendChatBubble(role, text) {
    const history = document.getElementById('ia-chat-history');
    if (!history) return;

    const div = document.createElement('div');
    div.classList.add('chat-bubble');
    if (role === 'user') {
      div.classList.add('chat-bubble-user');
    } else {
      div.classList.add('chat-bubble-assistant');
    }
    div.textContent = text;
    history.appendChild(div);
    history.scrollTop = history.scrollHeight;
  }

  function setIaApplyButtonEnabled(enabled) {
    const btn = document.getElementById('ia-chat-apply');
    if (!btn) return;
    btn.disabled = !enabled;
  }

  function toggleIaChatPanel(forceOpen) {
    const panel = document.getElementById('ia-chat-panel');
    if (!panel) return;

    const isHidden = panel.classList.contains('hidden');
    const shouldOpen = typeof forceOpen === 'boolean' ? forceOpen : isHidden;

    if (shouldOpen) {
      panel.classList.remove('hidden');
    } else {
      panel.classList.add('hidden');
    }
  }

  function generatePieceId() {
    return `piece_${Date.now()}_${Math.random().toString(16).slice(2, 8)}`;
  }

  function captureStateSnapshot() {
    return {
      pieces: pieces.map((p) => ({ ...p, element: null })),
      selectedIds: Array.from(selectedIds),
      pan: { ...pan },
      zoomScale,
      horizontalGuides: [...horizontalGuides],
      verticalGuides: [...verticalGuides],
    };
  }

  function updateHistoryButtons() {
    if (undoBtn) undoBtn.disabled = undoStack.length <= 1;
    if (redoBtn) redoBtn.disabled = redoStack.length === 0;
  }

  function pushHistoryState() {
    undoStack.push(captureStateSnapshot());
    if (undoStack.length > 100) undoStack.shift();
    redoStack.length = 0;
    updateHistoryButtons();
  }

  function restoreState(snapshot) {
    if (!snapshot || !sheetEl) return;
    sheetEl.innerHTML = '';
    pieces = snapshot.pieces.map((data) => {
      const piece = { ...data };
      piece.element = createPieceElement(piece);
      sheetEl.appendChild(piece.element);
      return piece;
    });
    selectedIds.clear();
    (snapshot.selectedIds || []).forEach((id) => selectedIds.add(id));
    pieces.forEach((p) => p.element.classList.toggle('selected', selectedIds.has(p.id)));
    horizontalGuides.length = 0;
    verticalGuides.length = 0;
    horizontalGuides.push(...(snapshot.horizontalGuides || []));
    verticalGuides.push(...(snapshot.verticalGuides || []));
    zoomScale = snapshot.zoomScale || zoomScale;
    pan = snapshot.pan ? { ...snapshot.pan } : pan;
    applyViewportTransform();
    renderGuides();
    markOverlaps();
    updateTooltip();
    syncPropertiesPanel(getPrimarySelection());
    updateStatusBar();
    updateHistoryButtons();
  }

  function undo() {
    if (undoStack.length <= 1) return;
    const current = undoStack.pop();
    redoStack.push(current);
    const prev = undoStack[undoStack.length - 1];
    restoreState(prev);
    updateHistoryButtons();
  }

  function redo() {
    if (redoStack.length === 0) return;
    const snapshot = redoStack.pop();
    undoStack.push(snapshot);
    restoreState(snapshot);
    updateHistoryButtons();
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
    tooltipEl.style.display = 'none';
    syncPropertiesPanel(null);
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
    updateTooltip();
    syncPropertiesPanel(getPrimarySelection());
  }

  function getPrimarySelection() {
    if (selectedIds.size === 0) return null;
    const firstId = Array.from(selectedIds)[0];
    return pieces.find((p) => p.id === firstId) || null;
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
          a.x_mm >= bx2 - eps || b.x_mm >= ax2 - eps || a.y_mm >= by2 - eps || b.y_mm >= ay2 - eps;
        if (!separated) {
          a.element.classList.add('overlap');
          b.element.classList.add('overlap');
        }
      }
    }
  }

  function selectPiecesByAssetName(substring) {
    if (!substring) return;
    const term = substring.toString().toLowerCase();
    const assets = Array.isArray(layoutData?.assets) ? layoutData.assets : [];
    const matchingFileIdx = new Set();
    assets.forEach((asset) => {
      const label = (asset.name || asset.original_src || asset.src || '').toString().toLowerCase();
      if (label.includes(term)) {
        if (asset.file_idx != null) matchingFileIdx.add(Number(asset.file_idx));
        if (asset.id != null) matchingFileIdx.add(Number(asset.id));
      }
    });

    clearSelection();

    pieces.forEach((piece) => {
      const srcLabel = (piece.src || '').toLowerCase();
      const fileIdx = Number(piece.file_idx);
      const match = srcLabel.includes(term) || matchingFileIdx.has(fileIdx);
      if (match) {
        selectedIds.add(piece.id);
      }
      piece.element.classList.toggle('selected', selectedIds.has(piece.id));
    });

    syncPropertiesPanel(getPrimarySelection());
    updateTooltip();
    updateStatusBar();
  }

  function selectPiecesByIds(ids) {
    if (!Array.isArray(ids) || ids.length === 0) return;
    const allowed = new Set(ids.map((id) => id.toString()));
    clearSelection();
    pieces.forEach((piece) => {
      if (allowed.has(piece.id.toString())) {
        selectedIds.add(piece.id);
      }
      piece.element.classList.toggle('selected', selectedIds.has(piece.id));
    });
    syncPropertiesPanel(getPrimarySelection());
    updateTooltip();
    updateStatusBar();
  }

  function computeSelectionBoundingBox() {
    const selectedPieces = pieces.filter((p) => selectedIds.has(p.id));
    if (!selectedPieces.length) return null;

    const min_x = Math.min(...selectedPieces.map((p) => p.x_mm));
    const min_y = Math.min(...selectedPieces.map((p) => p.y_mm));
    const max_x = Math.max(...selectedPieces.map((p) => p.x_mm + p.w_mm));
    const max_y = Math.max(...selectedPieces.map((p) => p.y_mm + p.h_mm));
    return {
      min_x,
      min_y,
      max_x,
      max_y,
      width: max_x - min_x,
      height: max_y - min_y,
    };
  }

  function readGapInput(inputEl) {
    if (!inputEl) return 0;
    const val = parseFloat(inputEl.value);
    return Number.isFinite(val) && val >= 0 ? val : 0;
  }

  function applyGapsToPieces(targetPieces, gapH, gapV) {
    if (!layoutData?.sheet || !Array.isArray(targetPieces) || targetPieces.length <= 1) return;
    const sheet = layoutData.sheet;

    if (gapH > 0 && targetPieces.length > 1) {
      const sortedH = [...targetPieces].sort((a, b) => a.x_mm - b.x_mm);
      for (let i = 1; i < sortedH.length; i++) {
        const prev = sortedH[i - 1];
        const curr = sortedH[i];
        curr.x_mm = prev.x_mm + prev.w_mm + gapH;
        curr.x_mm = clamp(curr.x_mm, 0, sheet.w_mm - curr.w_mm);
      }
    }

    if (gapV > 0 && targetPieces.length > 1) {
      const sortedV = [...targetPieces].sort((a, b) => a.y_mm - b.y_mm);
      for (let i = 1; i < sortedV.length; i++) {
        const prev = sortedV[i - 1];
        const curr = sortedV[i];
        curr.y_mm = prev.y_mm + prev.h_mm + gapV;
        curr.y_mm = clamp(curr.y_mm, 0, sheet.h_mm - curr.h_mm);
      }
    }

    targetPieces.forEach(updatePiecePosition);
    markOverlaps();
    updateTooltip();
    updateStatusBar();
    pushHistoryState();
  }

  function arrangeSelectionAsRelativeGrid(action) {
    const selectedPieces = pieces.filter((p) => selectedIds.has(p.id));
    if (!selectedPieces.length) return;
    const bboxRef = action?.relative_to ? iaNamedBBoxes[action.relative_to] : null;
    if (!bboxRef) return;

    const rows = Math.max(1, parseInt(action.rows, 10) || 1);
    const gap = typeof action.gap_mm === 'number' ? action.gap_mm : 0;
    const maxW = Math.max(...selectedPieces.map((p) => p.w_mm));
    const maxH = Math.max(...selectedPieces.map((p) => p.h_mm));
    if (!Number.isFinite(maxW) || !Number.isFinite(maxH)) return;

    const cols = Math.ceil(selectedPieces.length / rows);
    const gridWidth = cols * maxW + (cols - 1) * gap;
    const gridHeight = rows * maxH + (rows - 1) * gap;

    const sheet = layoutData?.sheet;
    const position = action.position || 'above';
    let originX = bboxRef.min_x + (bboxRef.width - gridWidth) / 2;
    let originY = bboxRef.max_y + gap;

    if (position === 'below') {
      originY = bboxRef.min_y - gap - gridHeight;
    } else if (position === 'left') {
      originX = bboxRef.min_x - gap - gridWidth;
      originY = bboxRef.min_y;
    } else if (position === 'right') {
      originX = bboxRef.max_x + gap;
      originY = bboxRef.min_y;
    }

    if (sheet) {
      originX = clamp(originX, 0, Math.max(0, sheet.w_mm - gridWidth));
      originY = clamp(originY, 0, Math.max(0, sheet.h_mm - gridHeight));
    }

    selectedPieces.forEach((piece, idx) => {
      const row = Math.floor(idx / cols);
      const col = idx % cols;
      piece.x_mm = originX + col * (maxW + gap);
      piece.y_mm = originY + row * (maxH + gap);
      updatePiecePosition(piece);
    });
  }

  function getMaxCopiesForFile(fileIdx) {
    if (!layoutData?.assets) return null;
    const asset = layoutData.assets.find((a) => Number(a.file_idx) === Number(fileIdx));
    if (!asset) return null;
    const cantidad = Number(asset.cantidad);
    return Number.isFinite(cantidad) ? cantidad : null;
  }

  function countPiecesForFile(fileIdx) {
    return pieces.filter((p) => Number(p.file_idx) === Number(fileIdx)).length;
  }

  // Comment: sistema de zoom/pan aplicado a contenedor transformado
  function applyViewportTransform() {
    if (!zoomContainer) return;
    zoomContainer.style.transform = `translate(${pan.x}px, ${pan.y}px) scale(${zoomScale})`;
    guidesLayer.style.transform = zoomContainer.style.transform;
    renderGuides();
  }

  function updatePiecePosition(piece) {
    if (!piece || !piece.element || !sheetEl) {
      return;
    }
    piece.element.style.left = `${piece.x_mm * baseScale}px`;
    piece.element.style.bottom = `${piece.y_mm * baseScale}px`;
    piece.element.style.width = `${piece.w_mm * baseScale}px`;
    piece.element.style.height = `${piece.h_mm * baseScale}px`;
    const transforms = [];
    transforms.push(`rotate(${piece.rotation || 0}deg)`);
    if (piece.flip_x) transforms.push('scaleX(-1)');
    if (piece.flip_y) transforms.push('scaleY(-1)');
    piece.element.style.transform = transforms.join(' ');
    piece.element.classList.toggle('locked', Boolean(piece.locked));
    piece.element.dataset.xMm = piece.x_mm;
    piece.element.dataset.yMm = piece.y_mm;
    updatePieceOverlays(piece);
  }

  function computeDistancesForPiece(piece) {
    if (!layoutData?.sheet || !piece) return null;
    const sheet = layoutData.sheet;

    const marginLeft = piece.x_mm;
    const marginBottom = piece.y_mm;
    const marginRight = sheet.w_mm - (piece.x_mm + piece.w_mm);
    const marginTop = sheet.h_mm - (piece.y_mm + piece.h_mm);

    let minGapH = Infinity;
    let minGapV = Infinity;

    pieces.forEach((other) => {
      if (other.id === piece.id) return;
      const dxRight = other.x_mm - (piece.x_mm + piece.w_mm);
      const dxLeft = piece.x_mm - (other.x_mm + other.w_mm);
      if (dxRight >= 0) minGapH = Math.min(minGapH, dxRight);
      if (dxLeft >= 0) minGapH = Math.min(minGapH, dxLeft);

      const dyTop = other.y_mm - (piece.y_mm + piece.h_mm);
      const dyBottom = piece.y_mm - (other.y_mm + other.h_mm);
      if (dyTop >= 0) minGapV = Math.min(minGapV, dyTop);
      if (dyBottom >= 0) minGapV = Math.min(minGapV, dyBottom);
    });

    if (!Number.isFinite(minGapH)) minGapH = 0;
    if (!Number.isFinite(minGapV)) minGapV = 0;

    return {
      gapH: minGapH,
      gapV: minGapV,
      marginLeft,
      marginRight,
      marginTop,
      marginBottom,
    };
  }

  function updateTooltip() {
    if (!tooltipEl || selectedIds.size === 0) {
      tooltipEl.style.display = 'none';
      return;
    }
    const piece = getPrimarySelection();
    if (!piece || !piece.element) return;
    const rect = piece.element.getBoundingClientRect();
    tooltipEl.style.display = 'block';
    // Posicionamos el tooltip debajo de la pieza para que no la tape.
    tooltipEl.style.left = `${rect.left + rect.width / 2}px`;
    tooltipEl.style.top = `${rect.bottom + 8}px`;
    const srcLabel = piece.src ? piece.src.split(/[\\/]/).pop() : '—';
    tooltipEl.innerHTML = `
      <div><strong>ID:</strong> ${piece.id}</div>
      <div><strong>Tamaño:</strong> ${piece.w_mm.toFixed(1)} × ${piece.h_mm.toFixed(1)} mm</div>
      <div><strong>Posición:</strong> X ${piece.x_mm.toFixed(1)} / Y ${piece.y_mm.toFixed(1)} mm</div>
      <div><strong>Rotación:</strong> ${Number(piece.rotation || 0).toFixed(1)}°</div>
      <div><strong>Origen:</strong> ${srcLabel}</div>
    `;

    const distances = computeDistancesForPiece(piece);
    if (distances) {
      const minGap = layoutData?.min_gap_mm;
      const gapHStr = distances.gapH.toFixed(1);
      const gapVStr = distances.gapV.toFixed(1);
      const marginLeftStr = distances.marginLeft.toFixed(1);
      const marginTopStr = distances.marginTop.toFixed(1);

      let gapClassH = '';
      let gapClassV = '';
      if (Number.isFinite(minGap) && minGap > 0) {
        if (distances.gapH < minGap) gapClassH = ' style="color:#dc2626"';
        if (distances.gapV < minGap) gapClassV = ' style="color:#dc2626"';
      }

      tooltipEl.innerHTML += `
        <div${gapClassH}><strong>Gap H:</strong> ${gapHStr} mm</div>
        <div${gapClassV}><strong>Gap V:</strong> ${gapVStr} mm</div>
        <div><strong>Margen izq:</strong> ${marginLeftStr} mm</div>
        <div><strong>Margen sup:</strong> ${marginTopStr} mm</div>
      `;
    }
  }

  // Comment: panel de propiedades sincronizado con selección
  function syncPropertiesPanel(piece) {
    if (!propertiesPanel.x) return;
    const inputs = propertiesPanel;
    if (!piece) {
      inputs.x.value = inputs.y.value = inputs.w.value = inputs.h.value = inputs.rot.value = '';
      inputs.locked.checked = false;
      if (trimPanel.w) trimPanel.w.value = '';
      if (trimPanel.h) trimPanel.h.value = '';
      if (trimPanel.bleed) trimPanel.bleed.value = '';
      return;
    }
    inputs.x.value = piece.x_mm.toFixed(2);
    inputs.y.value = piece.y_mm.toFixed(2);
    inputs.w.value = piece.w_mm.toFixed(2);
    inputs.h.value = piece.h_mm.toFixed(2);
    inputs.rot.value = Number(piece.rotation || 0).toFixed(1);
    inputs.locked.checked = Boolean(piece.locked);

    // Para este flujo: pieza.w_mm / h_mm representan la medida final (trim),
    // y el sangrado es adicional, no se resta del tamaño final.
    const bleedEffective = getBleedMm(piece);
    const trimW = piece.w_mm;
    const trimH = piece.h_mm;

    if (trimPanel.w) {
      trimPanel.w.value = trimW > 0 ? trimW.toFixed(2) : '';
    }
    if (trimPanel.h) {
      trimPanel.h.value = trimH > 0 ? trimH.toFixed(2) : '';
    }
    if (trimPanel.bleed) {
      // Si la pieza tiene override explícito, mostramos ese valor.
      if (typeof piece.bleed_override_mm === 'number' && piece.bleed_override_mm >= 0) {
        trimPanel.bleed.value = piece.bleed_override_mm.toFixed(2);
      } else if (bleedEffective > 0) {
        // Si no hay override pero sí sangrado global efectivo, mostramos ese valor.
        trimPanel.bleed.value = bleedEffective.toFixed(2);
      } else {
        // Sin sangrado definido.
        trimPanel.bleed.value = '';
      }
    }
  }

  function applyPropertiesFromPanel() {
    const selectedPieces = pieces.filter((p) => selectedIds.has(p.id));
    const piece = selectedPieces[0];
    if (!piece) return;
    const readNumber = (input, min = -Infinity) => {
      const val = parseFloat(input.value);
      if (!Number.isFinite(val)) return null;
      return Math.max(val, min);
    };
    const readOptionalNumber = (input, min = -Infinity) => {
      if (!input) return null;
      const raw = String(input.value || '').trim();
      if (raw === '') return null; // vacío = sin override
      const val = parseFloat(raw);
      if (!Number.isFinite(val)) return null;
      return Math.max(val, min);
    };
    const x = readNumber(propertiesPanel.x, 0);
    const y = readNumber(propertiesPanel.y, 0);
    const w = readNumber(propertiesPanel.w, 0.1);
    const h = readNumber(propertiesPanel.h, 0.1);
    const r = readNumber(propertiesPanel.rot, -360);
    const bleedOverride = readOptionalNumber(trimPanel.bleed, 0);
    if (x === null || y === null || w === null || h === null || r === null) {
      showToast('Valores inválidos en propiedades.', 'error');
      return;
    }
    const sheet = layoutData.sheet;
    selectedPieces.forEach((p) => {
      p.x_mm = clamp(x, 0, sheet.w_mm - w);
      p.y_mm = clamp(y, 0, sheet.h_mm - h);
      p.w_mm = w;
      p.h_mm = h;
      p.rotation = r;

      if (bleedOverride === null) {
        // Campo vacío o inválido: eliminamos override y se usará el sangrado global.
        if ('bleed_override_mm' in p) {
          delete p.bleed_override_mm;
        }
      } else {
        p.bleed_override_mm = bleedOverride;
      }

      p.locked = Boolean(propertiesPanel.locked.checked);
      updatePiecePosition(p);
    });
    markOverlaps();
    updateTooltip();
    updateStatusBar();
    pushHistoryState();
  }

  function nudgeSelection(dx, dy) {
    if (!layoutData?.sheet || selectedIds.size === 0) return;
    const sheet = layoutData.sheet;
    const selectedPieces = pieces.filter((p) => selectedIds.has(p.id));
    selectedPieces.forEach((p) => {
      p.x_mm = clamp(p.x_mm + dx, 0, sheet.w_mm - p.w_mm);
      p.y_mm = clamp(p.y_mm + dy, 0, sheet.h_mm - p.h_mm);
      updatePiecePosition(p);
    });
    markOverlaps();
    updateTooltip();
    updateStatusBar();
    pushHistoryState();
  }

  function handleKeyboardShortcuts(evt) {
    const tag = (evt.target?.tagName || '').toLowerCase();
    if (['input', 'textarea', 'select'].includes(tag)) return;

    const key = evt.key;
    const ctrlLike = evt.ctrlKey || evt.metaKey;

    if (ctrlLike && key.toLowerCase() === 's') {
      evt.preventDefault();
      saveLayout();
      return;
    }
    if (ctrlLike && key.toLowerCase() === 'd') {
      evt.preventDefault();
      duplicateSelectedPieces();
      return;
    }
    if (ctrlLike && key.toLowerCase() === 'z') {
      evt.preventDefault();
      if (evt.shiftKey) {
        redo();
      } else {
        undo();
      }
      return;
    }
    if (ctrlLike && key.toLowerCase() === 'y') {
      evt.preventDefault();
      redo();
      return;
    }

    if (key.startsWith('Arrow') && selectedIds.size > 0) {
      const baseStep = computeGridStep(layoutData?.grid_mm);
      const step = evt.shiftKey ? baseStep * 2 : baseStep;
      const dx = key === 'ArrowLeft' ? -step : key === 'ArrowRight' ? step : 0;
      const dy = key === 'ArrowUp' ? -step : key === 'ArrowDown' ? step : 0;
      nudgeSelection(dx, dy);
      evt.preventDefault();
    }
  }

  // Comment: lógica de multi-selección y arrastre conjunto
  function createPieceElement(piece) {
    const el = document.createElement('div');
    el.className = 'piece';
    el.textContent = piece.label || piece.id;
    updatePiecePosition(piece);

    el.addEventListener('pointerdown', (evt) => {
      if (!sheetEl) return;
      if (evt.button === 1 || (evt.button === 0 && evt.metaKey)) {
        return; // dejar al pan
      }
      evt.preventDefault();
      const additive = evt.shiftKey;
      toggleSelection(piece.id, additive);
      const selectionIds = selectedIds.size ? Array.from(selectedIds) : [piece.id];
      const selectedPieces = pieces.filter((p) => selectionIds.includes(p.id));
      dragState = {
        pointerId: evt.pointerId,
        startX: evt.clientX,
        startY: evt.clientY,
        selection: selectedPieces,
        origins: selectedPieces.map((p) => ({ id: p.id, x: p.x_mm, y: p.y_mm })),
      };
      el.setPointerCapture(evt.pointerId);
      el.classList.add('dragging');
      setStatus('Arrastrando pieza…');
    });

    el.addEventListener('pointermove', (evt) => {
      if (!dragState || dragState.pointerId !== evt.pointerId) return;
      evt.preventDefault();
      const dxMm = pxToMm(evt.clientX - dragState.startX);
      const dyMm = pxToMm(evt.clientY - dragState.startY);
      const gridStep = computeGridStep(layoutData.grid_mm);
      const sheet = layoutData.sheet;
      const bounds = { w: sheet.w_mm, h: sheet.h_mm };
      dragState.selection.forEach((p, idx) => {
        const origin = dragState.origins[idx];
        let newX = origin.x + dxMm;
        let newY = origin.y + dyMm;
        newX = snapValue(newX, gridStep);
        newY = snapValue(newY, gridStep);
        const snapOffsets = computeSnapOffsets(p, newX, newY, bounds);
        newX += snapOffsets.x;
        newY += snapOffsets.y;
        newX = clamp(newX, 0, bounds.w - p.w_mm);
        newY = clamp(newY, 0, bounds.h - p.h_mm);
        p.x_mm = newX;
        p.y_mm = newY;
        updatePiecePosition(p);
      });
      markOverlaps();
      updateTooltip();
    });

    function finalizeDrag(evt) {
      if (!dragState || dragState.pointerId !== evt.pointerId) return;
      evt.preventDefault();
      dragState.selection.forEach((p) => updatePiecePosition(p));
      dragState = null;
      el.classList.remove('dragging');
      setStatus('');
      try {
        el.releasePointerCapture(evt.pointerId);
      } catch (captureErr) {
        /* ignore */
      }
      updateStatusBar();
      pushHistoryState();
    }

    el.addEventListener('pointerup', finalizeDrag);
    el.addEventListener('pointercancel', finalizeDrag);

    el.addEventListener('dblclick', () => {
      toggleSelection(piece.id, false);
      setStatus('Seleccionar reemplazo y presionar "Reemplazar pieza".');
    });

    return el;
  }

  function computeSnapOffsets(piece, newX, newY, bounds) {
    // Comment: sistema de snapping con cuadrícula, bordes y márgenes
    const offsets = { x: 0, y: 0 };
    const tolerance = SNAP_TOLERANCE_MM;
    pieces.forEach((other) => {
      if (other.id === piece.id || selectedIds.has(other.id)) return;
      const edgesPiece = [newX, newX + piece.w_mm];
      const edgesOther = [other.x_mm, other.x_mm + other.w_mm];
      edgesPiece.forEach((edge) => {
        edgesOther.forEach((edgeOther) => {
          const diff = edgeOther - edge;
          if (Math.abs(diff) <= tolerance) offsets.x = diff;
        });
      });
      const vPiece = [newY, newY + piece.h_mm];
      const vOther = [other.y_mm, other.y_mm + other.h_mm];
      vPiece.forEach((edge) => {
        vOther.forEach((edgeOther) => {
          const diff = edgeOther - edge;
          if (Math.abs(diff) <= tolerance) offsets.y = diff;
        });
      });
    });
    if (newX < 0 + tolerance) offsets.x = -newX;
    if (newY < 0 + tolerance) offsets.y = -newY;
    if (newX + piece.w_mm > bounds.w - tolerance) offsets.x = bounds.w - piece.w_mm - newX;
    if (newY + piece.h_mm > bounds.h - tolerance) offsets.y = bounds.h - piece.h_mm - newY;
    return offsets;
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
    undoStack.length = 0;
    redoStack.length = 0;
    updateHistoryButtons();
    if (!layoutData.pdf_filename) {
      layoutData.pdf_filename = 'pliego.pdf';
    }
    if (!layoutData.preview_filename) {
      layoutData.preview_filename = 'preview_edit.png';
    }
    pieces = [];
    panContainer.innerHTML = '';

    const sheet = data.sheet || { w_mm: 0, h_mm: 0 };
    sheet.w_mm = Number(sheet.w_mm) || 0;
    sheet.h_mm = Number(sheet.h_mm) || 0;
    if (!sheet.w_mm || !sheet.h_mm) {
      setStatus('Sheet inválido en layout', 'error');
      return;
    }

    const maxWidthPx = canvas.clientWidth ? canvas.clientWidth * 0.8 : 900;
    baseScale = Math.min(2, maxWidthPx / sheet.w_mm);
    if (baseScale <= 0) baseScale = 1.5;
    zoomScale = 1;
    pan = { x: 40, y: 40 };

    sheetEl = document.createElement('div');
    sheetEl.className = 'sheet';
    sheetEl.style.width = `${sheet.w_mm * baseScale}px`;
    sheetEl.style.height = `${sheet.h_mm * baseScale}px`;
    sheetEl.addEventListener('pointerdown', (evt) => {
      if (evt.target === sheetEl && !evt.shiftKey) {
        clearSelection();
        setStatus('');
      }
      if (evt.target === sheetEl && evt.button === 0 && evt.shiftKey) {
        startMarquee(evt);
      }
    });

    panContainer.appendChild(sheetEl);

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
        locked: Boolean(item.locked),
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
    drawRulers();
    updateStatusBar();
    applyViewportTransform();
    pushHistoryState();
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
    updateTooltip();
    pushHistoryState();
    syncPropertiesPanel(piece);
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
    updateTooltip();
    updateStatusBar();
    pushHistoryState();
    syncPropertiesPanel(getPrimarySelection());
    setStatus('Posiciones intercambiadas. Recordá guardar los cambios.', 'success');
  }

  function duplicateSelectedPieces() {
    if (!layoutData?.sheet) return;
    const selectedPieces = pieces.filter((p) => selectedIds.has(p.id));
    if (!selectedPieces.length) {
      setStatus('Seleccioná al menos una pieza para duplicar.', 'error');
      return;
    }

    const sheet = layoutData.sheet;
    const created = [];
    const skipped = [];

    selectedPieces.forEach((p) => {
      const maxCopies = getMaxCopiesForFile(p.file_idx);
      const currentCopies = countPiecesForFile(p.file_idx);
      if (maxCopies !== null && currentCopies >= maxCopies) {
        skipped.push(p);
        return;
      }
      const clone = {
        ...p,
        id: generatePieceId(),
        x_mm: clamp(p.x_mm + 10, 0, sheet.w_mm - p.w_mm),
        y_mm: clamp(p.y_mm + 10, 0, sheet.h_mm - p.h_mm),
        element: null,
      };
      clone.element = createPieceElement(clone);
      sheetEl.appendChild(clone.element);
      pieces.push(clone);
      created.push(clone);
    });

    if (created.length) {
      selectedIds.clear();
      created.forEach((c) => selectedIds.add(c.id));
      pieces.forEach((piece) => piece.element.classList.toggle('selected', selectedIds.has(piece.id)));
      syncPropertiesPanel(getPrimarySelection());
      markOverlaps();
      updateTooltip();
      updateStatusBar();
      pushHistoryState();
    }

    if (skipped.length) {
      const names = skipped
        .map((p) => (p.src || p.label || p.id).toString().split(/[\\/]/).pop())
        .join(', ');
      setStatus(
        `${created.length ? 'Algunas piezas se duplicaron. ' : ''}No se pueden crear más copias de: ${names}. Límite alcanzado según el layout.`,
        'error'
      );
    } else if (created.length) {
      setStatus('Piezas duplicadas. Recordá guardar los cambios.', 'success');
    }
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
      locked: Boolean(piece.locked),
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
      showToast('✅ Layout IA guardado y PDF editado regenerado.', 'success');
    } catch (err) {
      console.error('[post-editor] save error', err);
      setStatus(err.message || 'Error al guardar el layout', 'error');
      showToast(`Error al guardar: ${err.message || 'desconocido'}`, 'error');
    }
  }

  function handleZoom(delta, centerPx) {
    const oldScale = zoomScale;
    zoomScale = clamp(zoomScale * delta, MIN_ZOOM, MAX_ZOOM);
    const ratio = zoomScale / oldScale;
    if (centerPx && sheetViewport) {
      const rect = sheetViewport.getBoundingClientRect();
      const cx = centerPx.x - rect.left;
      const cy = centerPx.y - rect.top;
      pan.x = cx - ratio * (cx - pan.x);
      pan.y = cy - ratio * (cy - pan.y);
    }
    applyViewportTransform();
    drawRulers();
  }

  function zoomToFit() {
    if (!layoutData?.sheet || !canvas) return;
    const sheet = layoutData.sheet;
    const rect = canvas.getBoundingClientRect();
    const scaleX = (rect.width - 100) / (sheet.w_mm * baseScale);
    const scaleY = (rect.height - 100) / (sheet.h_mm * baseScale);
    zoomScale = clamp(Math.min(scaleX, scaleY), MIN_ZOOM, MAX_ZOOM);
    pan = { x: 50, y: 50 };
    applyViewportTransform();
    drawRulers();
  }

  function initZoomPanControls() {
    if (!canvas) return;
    canvas.addEventListener('wheel', (evt) => {
      evt.preventDefault();
      const delta = evt.deltaY < 0 ? 1.1 : 0.9;
      handleZoom(delta, { x: evt.clientX, y: evt.clientY });
    }, { passive: false });

    canvas.addEventListener('pointerdown', (evt) => {
      const isPanButton = evt.button === 1 || evt.button === 2 || spacePressed; // support middle click y barra espaciadora
      if (evt.button === 0 && evt.ctrlKey) return; // avoid conflict
      if (isPanButton || evt.buttons === 4 || evt.code === 'Space') {
        evt.preventDefault();
        panState = { pointerId: evt.pointerId, startX: evt.clientX, startY: evt.clientY, origin: { ...pan } };
        canvas.setPointerCapture(evt.pointerId);
      }
    });

    canvas.addEventListener('pointermove', (evt) => {
      if (!panState || panState.pointerId !== evt.pointerId) return;
      pan.x = panState.origin.x + (evt.clientX - panState.startX);
      pan.y = panState.origin.y + (evt.clientY - panState.startY);
      applyViewportTransform();
    });

    canvas.addEventListener('pointerup', (evt) => {
      if (panState && panState.pointerId === evt.pointerId) {
        panState = null;
      }
    });
    canvas.addEventListener('pointercancel', () => {
      panState = null;
    });

    canvas.addEventListener('keydown', (evt) => {
      if (evt.ctrlKey && (evt.key === '+' || evt.key === '=')) {
        handleZoom(1.1, { x: evt.clientX || canvas.clientWidth / 2, y: evt.clientY || canvas.clientHeight / 2 });
        evt.preventDefault();
      } else if (evt.ctrlKey && evt.key === '-') {
        handleZoom(0.9, { x: evt.clientX || canvas.clientWidth / 2, y: evt.clientY || canvas.clientHeight / 2 });
        evt.preventDefault();
      } else if (evt.ctrlKey && evt.key === '0') {
        zoomToFit();
        evt.preventDefault();
      }
    });

    canvas.addEventListener('touchstart', (evt) => {
      if (evt.touches.length === 2) {
        pinchState = {
          startDist: calcTouchDistance(evt.touches),
          startZoom: zoomScale,
        };
      }
    }, { passive: true });

    canvas.addEventListener('touchmove', (evt) => {
      if (pinchState && evt.touches.length === 2) {
        evt.preventDefault();
        const dist = calcTouchDistance(evt.touches);
        const delta = dist / pinchState.startDist;
        handleZoom(pinchState.startZoom * delta / zoomScale, {
          x: (evt.touches[0].clientX + evt.touches[1].clientX) / 2,
          y: (evt.touches[0].clientY + evt.touches[1].clientY) / 2,
        });
      } else if (evt.touches.length === 2) {
        const dx = evt.touches[0].clientX - evt.touches[1].clientX;
        const dy = evt.touches[0].clientY - evt.touches[1].clientY;
        pan.x += dx * 0.01;
        pan.y += dy * 0.01;
        applyViewportTransform();
      }
    }, { passive: false });

    canvas.addEventListener('touchend', () => {
      pinchState = null;
    });

    window.addEventListener('keydown', (evt) => {
      if (evt.code === 'Space') spacePressed = true;
    });
    window.addEventListener('keyup', (evt) => {
      if (evt.code === 'Space') spacePressed = false;
    });
  }

  function calcTouchDistance(touches) {
    const dx = touches[0].clientX - touches[1].clientX;
    const dy = touches[0].clientY - touches[1].clientY;
    return Math.sqrt(dx * dx + dy * dy);
  }

  function startMarquee(evt) {
    const rect = sheetViewport.getBoundingClientRect();
    marqueeState = {
      startX: evt.clientX - rect.left,
      startY: evt.clientY - rect.top,
    };
    marqueeEl.hidden = false;
    marqueeEl.style.left = `${marqueeState.startX}px`;
    marqueeEl.style.top = `${marqueeState.startY}px`;
    marqueeEl.style.width = '0px';
    marqueeEl.style.height = '0px';
    const move = (e) => {
      const curX = e.clientX - rect.left;
      const curY = e.clientY - rect.top;
      const x = Math.min(marqueeState.startX, curX);
      const y = Math.min(marqueeState.startY, curY);
      const w = Math.abs(curX - marqueeState.startX);
      const h = Math.abs(curY - marqueeState.startY);
      marqueeEl.style.left = `${x}px`;
      marqueeEl.style.top = `${y}px`;
      marqueeEl.style.width = `${w}px`;
      marqueeEl.style.height = `${h}px`;
    };
    const up = (e) => {
      document.removeEventListener('pointermove', move);
      document.removeEventListener('pointerup', up);
      marqueeEl.hidden = true;
      const curX = e.clientX - rect.left;
      const curY = e.clientY - rect.top;
      const x1 = Math.min(marqueeState.startX, curX);
      const y1 = Math.min(marqueeState.startY, curY);
      const x2 = Math.max(marqueeState.startX, curX);
      const y2 = Math.max(marqueeState.startY, curY);
      const mm1 = screenToSheetMm(x1 + rect.left, y1 + rect.top);
      const mm2 = screenToSheetMm(x2 + rect.left, y2 + rect.top);
      clearSelection();
      pieces.forEach((p) => {
        const inside =
          p.x_mm >= mm1.x &&
          p.y_mm >= mm1.y &&
          p.x_mm + p.w_mm <= mm2.x &&
          p.y_mm + p.h_mm <= mm2.y;
        if (inside) selectedIds.add(p.id);
      });
      pieces.forEach((p) => p.element.classList.toggle('selected', selectedIds.has(p.id)));
      syncPropertiesPanel(getPrimarySelection());
      updateTooltip();
      marqueeState = null;
    };
    document.addEventListener('pointermove', move);
    document.addEventListener('pointerup', up);
  }

  function screenToSheetMm(clientX, clientY) {
    const rect = sheetViewport.getBoundingClientRect();
    const localX = (clientX - rect.left - pan.x) / zoomScale;
    const localY = (rect.bottom - clientY + pan.y) / zoomScale;
    return {
      x: localX / baseScale,
      y: localY / baseScale,
    };
  }

  function applyAlignment(type) {
    if (selectedIds.size < 1) return;
    const selectedPieces = pieces.filter((p) => selectedIds.has(p.id));
    const sheet = layoutData.sheet;
    const xs = selectedPieces.map((p) => p.x_mm);
    const ys = selectedPieces.map((p) => p.y_mm);
    const ws = selectedPieces.map((p) => p.w_mm);
    const hs = selectedPieces.map((p) => p.h_mm);
    if (type === 'left') {
      const minX = Math.min(...xs);
      selectedPieces.forEach((p) => (p.x_mm = minX));
    } else if (type === 'right') {
      const maxRight = Math.max(...selectedPieces.map((p, i) => xs[i] + ws[i]));
      selectedPieces.forEach((p, i) => (p.x_mm = maxRight - ws[i]));
    } else if (type === 'center-vertical') {
      const center = (Math.min(...xs) + Math.max(...selectedPieces.map((p, i) => xs[i] + ws[i]))) / 2;
      selectedPieces.forEach((p, i) => (p.x_mm = center - ws[i] / 2));
    } else if (type === 'top') {
      const maxTop = Math.max(...selectedPieces.map((p, i) => ys[i] + hs[i]));
      selectedPieces.forEach((p, i) => (p.y_mm = maxTop - hs[i]));
    } else if (type === 'bottom') {
      const minY = Math.min(...ys);
      selectedPieces.forEach((p) => (p.y_mm = minY));
    } else if (type === 'center-horizontal') {
      const center = (Math.min(...ys) + Math.max(...selectedPieces.map((p, i) => ys[i] + hs[i]))) / 2;
      selectedPieces.forEach((p, i) => (p.y_mm = center - hs[i] / 2));
    } else if (type === 'center-sheet') {
      const bbox = selectedPieces.reduce(
        (acc, p) => {
          return {
            minX: Math.min(acc.minX, p.x_mm),
            maxX: Math.max(acc.maxX, p.x_mm + p.w_mm),
            minY: Math.min(acc.minY, p.y_mm),
            maxY: Math.max(acc.maxY, p.y_mm + p.h_mm),
          };
        },
        { minX: Infinity, maxX: -Infinity, minY: Infinity, maxY: -Infinity }
      );
      const selW = bbox.maxX - bbox.minX;
      const selH = bbox.maxY - bbox.minY;
      const offsetX = sheet.w_mm / 2 - selW / 2 - bbox.minX;
      const offsetY = sheet.h_mm / 2 - selH / 2 - bbox.minY;
      selectedPieces.forEach((p) => {
        p.x_mm += offsetX;
        p.y_mm += offsetY;
      });
    } else if (type === 'dist-h' && selectedPieces.length > 2) {
      const sorted = [...selectedPieces].sort((a, b) => a.x_mm - b.x_mm);
      const totalWidth = sorted.reduce((acc, p) => acc + p.w_mm, 0);
      const space = (sorted[sorted.length - 1].x_mm - sorted[0].x_mm - totalWidth) / (sorted.length - 1);
      let cursor = sorted[0].x_mm + sorted[0].w_mm + space;
      for (let i = 1; i < sorted.length - 1; i++) {
        sorted[i].x_mm = cursor;
        cursor += sorted[i].w_mm + space;
      }
    } else if (type === 'dist-v' && selectedPieces.length > 2) {
      const sorted = [...selectedPieces].sort((a, b) => a.y_mm - b.y_mm);
      const totalHeight = sorted.reduce((acc, p) => acc + p.h_mm, 0);
      const space = (sorted[sorted.length - 1].y_mm - sorted[0].y_mm - totalHeight) / (sorted.length - 1);
      let cursor = sorted[0].y_mm + sorted[0].h_mm + space;
      for (let i = 1; i < sorted.length - 1; i++) {
        sorted[i].y_mm = cursor;
        cursor += sorted[i].h_mm + space;
      }
    }
    selectedPieces.forEach(updatePiecePosition);
    markOverlaps();
    updateTooltip();
    updateStatusBar();
    pushHistoryState();
  }

  // Comment: barra de estado inferior con métricas rápidas
  function updateStatusBar() {
    if (!layoutData || !layoutData.sheet) return;
    const sheetArea = layoutData.sheet.w_mm * layoutData.sheet.h_mm;
    const pieceArea = pieces.reduce((acc, p) => acc + p.w_mm * p.h_mm, 0);
    const occupancy = sheetArea ? (pieceArea / sheetArea) * 100 : 0;
    if (statusSheetSize)
      statusSheetSize.textContent = `Pliego: ${layoutData.sheet.w_mm.toFixed(0)} × ${layoutData.sheet.h_mm.toFixed(0)} mm`;
    if (statusPieceCount) statusPieceCount.textContent = `Piezas: ${pieces.length}`;
    const bySrc = pieces.reduce((acc, p) => {
      const key = (p.src || 'desconocido').split(/[\\/]/).pop();
      acc[key] = (acc[key] || 0) + 1;
      return acc;
    }, {});
    if (statusBreakdown) statusBreakdown.textContent = `Por archivo: ${Object.entries(bySrc)
      .map(([k, v]) => `${k} (${v})`)
      .join(', ')}`;
    if (statusOccupancy) statusOccupancy.textContent = `Ocupación estimada: ${occupancy.toFixed(1)}%`;
    const warnings = [];
    const sheet = layoutData.sheet;
    const outOfBounds = pieces.filter((p) => p.x_mm < 0 || p.y_mm < 0 || p.x_mm + p.w_mm > sheet.w_mm || p.y_mm + p.h_mm > sheet.h_mm);
    if (outOfBounds.length) warnings.push(`${outOfBounds.length} piezas parcialmente fuera del pliego`);
    if (warnings.length === 0) warnings.push('Todas las piezas dentro del pliego');
    if (statusWarnings) statusWarnings.textContent = warnings.join(' · ');
  }

  function drawRulers() {
    if (!layoutData?.sheet || !rulerTop || !rulerLeft) return;
    const stepMm = 10;
    const sheet = layoutData.sheet;
    rulerTop.innerHTML = '';
    rulerLeft.innerHTML = '';
    const totalXPx = sheet.w_mm * baseScale;
    for (let mm = 0; mm <= sheet.w_mm; mm += stepMm) {
      const tick = document.createElement('div');
      tick.className = 'tick';
      const pos = (mm / sheet.w_mm) * totalXPx;
      tick.style.left = `${pos}px`;
      tick.style.height = mm % 50 === 0 ? '12px' : '7px';
      rulerTop.appendChild(tick);
      if (mm % 50 === 0) {
        const label = document.createElement('div');
        label.className = 'tick-label';
        label.style.left = `${pos + 2}px`;
        label.style.bottom = '0';
        label.textContent = mm;
        rulerTop.appendChild(label);
      }
    }
    const totalYPx = sheet.h_mm * baseScale;
    for (let mm = 0; mm <= sheet.h_mm; mm += stepMm) {
      const tick = document.createElement('div');
      tick.className = 'tick';
      const pos = (mm / sheet.h_mm) * totalYPx;
      tick.style.bottom = `${pos}px`;
      tick.style.width = mm % 50 === 0 ? '12px' : '7px';
      rulerLeft.appendChild(tick);
      if (mm % 50 === 0) {
        const label = document.createElement('div');
        label.className = 'tick-label';
        label.style.right = '0';
        label.style.bottom = `${pos - 6}px`;
        label.textContent = mm;
        rulerLeft.appendChild(label);
      }
    }
  }

  function renderGuides() {
    if (!guidesLayer) return;
    guidesLayer.innerHTML = '';
    horizontalGuides.forEach((mm) => {
      const line = document.createElement('div');
      line.className = 'guide-line horizontal';
      line.style.bottom = `${mm * baseScale}px`;
      guidesLayer.appendChild(line);
    });
    verticalGuides.forEach((mm) => {
      const line = document.createElement('div');
      line.className = 'guide-line vertical';
      line.style.left = `${mm * baseScale}px`;
      guidesLayer.appendChild(line);
    });
  }

  function initGuides() {
    const createGuide = (orientation, posPx) => {
      const mm = posPx / baseScale;
      if (orientation === 'horizontal') {
        horizontalGuides.push(mm);
      } else {
        verticalGuides.push(mm);
      }
      renderGuides();
    };

    rulerTop?.addEventListener('pointerdown', (evt) => {
      const pos = evt.offsetX;
      createGuide('vertical', pos);
    });

    rulerLeft?.addEventListener('pointerdown', (evt) => {
      const pos = rulerLeft.clientHeight - evt.offsetY;
      createGuide('horizontal', pos);
    });

    guidesLayer?.addEventListener('dblclick', (evt) => {
      const rect = guidesLayer.getBoundingClientRect();
      const localX = evt.clientX - rect.left;
      const localY = rect.bottom - evt.clientY;
      const xMm = localX / baseScale;
      const yMm = localY / baseScale;
      const idxV = verticalGuides.findIndex((v) => Math.abs(v - xMm) < 2);
      const idxH = horizontalGuides.findIndex((v) => Math.abs(v - yMm) < 2);
      if (idxV >= 0) verticalGuides.splice(idxV, 1);
      if (idxH >= 0) horizontalGuides.splice(idxH, 1);
      renderGuides();
    });
  }

  function initPropertiesPanel() {
    const inputs = Object.values(propertiesPanel).filter(Boolean);
    inputs.forEach((input) => {
      input.addEventListener('change', applyPropertiesFromPanel);
      input.addEventListener('blur', applyPropertiesFromPanel);
      input.addEventListener('keyup', (evt) => {
        if (evt.key === 'Enter') applyPropertiesFromPanel();
      });
    });

    if (trimToggle) {
      showTrimBox = !!trimToggle.checked;
      trimToggle.addEventListener('change', () => {
        showTrimBox = !!trimToggle.checked;
        pieces.forEach(updatePieceOverlays);
      });
    }

    if (bleedToggle) {
      showBleedBox = !!bleedToggle.checked;
      bleedToggle.addEventListener('change', () => {
        showBleedBox = !!bleedToggle.checked;
        pieces.forEach(updatePieceOverlays);
      });
    }

    // === NUEVO: listeners para el sangrado por pieza ===
    if (trimPanel.bleed) {
      trimPanel.bleed.addEventListener('change', applyPropertiesFromPanel);
      trimPanel.bleed.addEventListener('blur', applyPropertiesFromPanel);
      trimPanel.bleed.addEventListener('keyup', (evt) => {
        if (evt.key === 'Enter') applyPropertiesFromPanel();
      });
    }

    // Asegurar que cuando la pieza cambie, el campo bleed se refresque
    // Esto ya existe en syncPropertiesPanel(), pero reforzamos la lógica
    // para que nunca quede desactualizado.
    const oldSync = syncPropertiesPanel;
    syncPropertiesPanel = function(piece) {
      oldSync(piece);
      if (piece && trimPanel.bleed) {
        trimPanel.bleed.value =
          typeof piece.bleed_override_mm === 'number'
            ? piece.bleed_override_mm.toFixed(2)
            : '';
      }
    };
  }

  function initAlignmentButtons() {
    alignButtons.forEach((btn) => {
      btn.addEventListener('click', () => applyAlignment(btn.dataset.align));
    });
  }

  async function sendChatMessage() {
    const input = document.getElementById('ia-chat-input');
    if (!input) return;
    const text = input.value.trim();
    if (!text) return;

    appendChatBubble('user', text);
    input.value = '';

    const selectionIds = Array.from(selectedIds || []);
    const layout_state = {
      sheet: layoutData?.sheet || null,
      assets: layoutData?.assets || [],
      pieces: (pieces || []).map((p) => ({
        id: p.id,
        file_idx: p.file_idx,
        x_mm: p.x_mm,
        y_mm: p.y_mm,
        w_mm: p.w_mm,
        h_mm: p.h_mm,
        rotation: p.rotation,
        locked: !!p.locked,
      })),
      selection: selectionIds,
      settings: {
        grid_mm: layoutData?.grid_mm || null,
        bleed_mm: layoutData?.bleed_mm || null,
        min_gap_mm: layoutData?.min_gap_mm || null,
      },
    };

    try {
      const res = await fetch(`/editor_chat/${jobId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          layout_state,
        }),
      });

      if (!res.ok) {
        appendChatBubble('assistant', 'No se pudo contactar con la IA (error de red).');
        setIaApplyButtonEnabled(false);
        pendingIaActions = null;
        return;
      }

      const data = await res.json();
      const assistantText = data.assistant_message || 'Tengo una propuesta de cambios sobre el montaje.';
      appendChatBubble('assistant', assistantText);

      if (Array.isArray(data.actions)) {
        pendingIaActions = data.actions;
        setIaApplyButtonEnabled(pendingIaActions.length > 0);
      } else {
        pendingIaActions = null;
        setIaApplyButtonEnabled(false);
      }
    } catch (err) {
      console.error('Error en sendChatMessage:', err);
      appendChatBubble('assistant', 'Ocurrió un error al comunicarse con la IA.');
      pendingIaActions = null;
      setIaApplyButtonEnabled(false);
    }
  }

  function executeChatActions(actions) {
    if (!Array.isArray(actions) || actions.length === 0) return;

    let needHistoryPush = false;
    for (const action of actions) {
      if (!action || typeof action.type !== 'string') continue;

      switch (action.type) {
        case 'clear_selection':
          clearSelection?.();
          break;

        case 'filter_by_asset':
          if (action.asset_name_contains) {
            selectPiecesByAssetName(action.asset_name_contains);
          }
          break;

        case 'select_pieces':
          if (Array.isArray(action.piece_ids)) {
            selectPiecesByIds(action.piece_ids);
          }
          break;

        case 'align':
          if (action.target === 'selection' && action.mode) {
            applyAlignment?.(action.mode);
          }
          break;

        case 'distribute':
          if (action.target === 'selection' && action.direction) {
            const spacing = typeof action.spacing_mm === 'number' ? action.spacing_mm : null;
            if (spacing !== null) {
              const selectedPieces = pieces.filter((p) => selectedIds.has(p.id));
              if (selectedPieces.length > 1) {
                const sorted = [...selectedPieces].sort((a, b) =>
                  action.direction === 'vertical' ? a.y_mm - b.y_mm : a.x_mm - b.x_mm
                );
                sorted.forEach((piece, idx) => {
                  if (idx === 0) return;
                  const prev = sorted[idx - 1];
                  if (action.direction === 'vertical') {
                    piece.y_mm = prev.y_mm + prev.h_mm + spacing;
                  } else {
                    piece.x_mm = prev.x_mm + prev.w_mm + spacing;
                  }
                  if (layoutData?.sheet) {
                    piece.x_mm = clamp(piece.x_mm, 0, layoutData.sheet.w_mm - piece.w_mm);
                    piece.y_mm = clamp(piece.y_mm, 0, layoutData.sheet.h_mm - piece.h_mm);
                  }
                  updatePiecePosition(piece);
                });
                needHistoryPush = true;
              }
            } else {
              const mode = action.direction === 'vertical' ? 'dist-v' : 'dist-h';
              applyAlignment?.(mode);
            }
          }
          break;

        case 'move':
          if (action.target === 'selection') {
            const dx = typeof action.dx_mm === 'number' ? action.dx_mm : 0;
            const dy = typeof action.dy_mm === 'number' ? action.dy_mm : 0;
            nudgeSelection?.(dx, dy);
          }
          break;

        case 'duplicate':
          if (action.target === 'selection') {
            duplicateSelectedPieces?.();
          }
          break;

        case 'compute_group_bbox':
          if (action.target === 'selection' && action.save_as) {
            const bbox = computeSelectionBoundingBox();
            if (bbox) {
              iaNamedBBoxes[action.save_as] = bbox;
            }
          }
          break;

        case 'arrange_grid_relative':
          if (action.target === 'selection') {
            arrangeSelectionAsRelativeGrid(action);
            needHistoryPush = true;
          }
          break;

        default:
          console.warn('Acción IA desconocida:', action.type);
          break;
      }
    }

    if (typeof updateTooltip === 'function') {
      updateTooltip();
    }
    if (typeof updateStatusBar === 'function') {
      updateStatusBar();
    }
    if (needHistoryPush && typeof pushHistoryState === 'function') {
      if (typeof markOverlaps === 'function') {
        markOverlaps();
      }
      pushHistoryState();
    }
  }

  function initEvents() {
    if (replaceBtn) replaceBtn.addEventListener('click', replaceSelected);
    if (swapBtn) swapBtn.addEventListener('click', swapSelected);
    if (saveBtn) saveBtn.addEventListener('click', saveLayout);
    if (duplicateBtn) duplicateBtn.addEventListener('click', duplicateSelectedPieces);
    if (undoBtn) undoBtn.addEventListener('click', undo);
    if (redoBtn) redoBtn.addEventListener('click', redo);
    if (zoomInBtn) zoomInBtn.addEventListener('click', () => handleZoom(1.1));
    if (zoomOutBtn) zoomOutBtn.addEventListener('click', () => handleZoom(0.9));
    if (zoomResetBtn) zoomResetBtn.addEventListener('click', zoomToFit);
    document.getElementById('ia-chat-toggle')?.addEventListener('click', () => {
      toggleIaChatPanel();
    });
    document.getElementById('ia-chat-close')?.addEventListener('click', () => {
      toggleIaChatPanel(false);
    });
    document.getElementById('ia-chat-send')?.addEventListener('click', sendChatMessage);
    const inputEl = document.getElementById('ia-chat-input');
    if (inputEl) {
      inputEl.addEventListener('keydown', (evt) => {
        if (evt.key === 'Enter' && !evt.shiftKey) {
          evt.preventDefault();
          sendChatMessage();
        }
      });
    }
    document.getElementById('ia-chat-apply')?.addEventListener('click', () => {
      if (!pendingIaActions || pendingIaActions.length === 0) return;
      executeChatActions(pendingIaActions);
      pendingIaActions = null;
      setIaApplyButtonEnabled(false);
    });

    if (gapApplySelectionBtn) {
      gapApplySelectionBtn.addEventListener('click', () => {
        const gapH = readGapInput(gapInputs.h);
        const gapV = readGapInput(gapInputs.v);
        const selectedPieces = pieces.filter((p) => selectedIds.has(p.id));
        if (!selectedPieces.length) {
          setStatus('Seleccioná al menos dos piezas para ajustar espacios.', 'error');
          return;
        }
        applyGapsToPieces(selectedPieces, gapH, gapV);
        setStatus('Espacios aplicados a la selección.', 'success');
      });
    }

    if (gapApplySheetBtn) {
      gapApplySheetBtn.addEventListener('click', () => {
        const gapH = readGapInput(gapInputs.h);
        const gapV = readGapInput(gapInputs.v);
        if (!pieces.length) return;
        applyGapsToPieces(pieces, gapH, gapV);
        setStatus('Espacios aplicados a todo el pliego.', 'success');
      });
    }
    setIaApplyButtonEnabled(false);
    initZoomPanControls();
    initGuides();
    initPropertiesPanel();
    initAlignmentButtons();
    document.addEventListener('keydown', handleKeyboardShortcuts, { capture: true });
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

  window.addEventListener('resize', () => {
    drawRulers();
    updateTooltip();
  });

  initEvents();
  if (initialLayout) {
    renderLayout(initialLayout);
  } else {
    loadLayout();
  }
})();
