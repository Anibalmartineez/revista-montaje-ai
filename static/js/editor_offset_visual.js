(function () {
  const sheetEl = document.getElementById('sheet');
  const sheetCanvas = document.getElementById('sheet-canvas');
  const worksListEl = document.getElementById('works-list');
  const designsListEl = document.getElementById('designs-list');
  const previewImg = document.getElementById('preview-image');
  const pdfOutput = document.getElementById('pdf-output');
  const slotForm = document.getElementById('slot-form');
  const slotNone = document.getElementById('slot-none');
  const uploadForm = document.getElementById('upload-form');

  const state = {
    layout: {},
    scale: 1,
    zoom: 1,
    activeFace: 'front',
    selectedSlot: null,
    selectedSlots: new Set(),
    selectedWork: null,
    snapSettings: {
      snapSlots: true,
      snapMargins: true,
      snapGrid: true,
      tolerance_mm: 3,
      grid_mm: 5,
    },
    spacingSettings: {
      spacingX_mm: 4,
      spacingY_mm: 3,
      live: true,
    },
  };

  const history = {
    stack: [],
    pointer: -1,
    maxSize: 50,
  };

  function getSelectedSlot() {
    if (!state.selectedSlot && state.selectedSlots && state.selectedSlots.size > 0) {
      const firstSelectedId = state.selectedSlots.values().next().value;
      state.selectedSlot = state.layout.slots.find((s) => s.id === firstSelectedId) || null;
    }
    if (!state.selectedSlot) return null;
    return state.layout.slots.find((s) => s.id === state.selectedSlot.id) || null;
  }

  function parseInitialLayout() {
    let layout = window.INITIAL_LAYOUT_JSON;
    if (typeof layout === 'string') {
      try {
        layout = JSON.parse(layout);
      } catch (err) {
        layout = {};
      }
    }
    state.layout = layout || {};
    state.layout.works = state.layout.works || [];
    state.layout.slots = state.layout.slots || [];
    state.layout.designs = state.layout.designs || [];
    ensureEngineDefaults();
    normalizeDesignDefaults();
    if (!state.layout.sheet_mm) {
      state.layout.sheet_mm = [640, 880];
    }
    if (!state.layout.margins_mm) {
      state.layout.margins_mm = [10, 10, 10, 10];
    }
    if (state.layout.bleed_default_mm === undefined) {
      state.layout.bleed_default_mm = 3;
    }
    state.snapSettings = {
      ...state.snapSettings,
      ...(state.layout.snapSettings || state.layout.snap_settings || {}),
    };
    state.spacingSettings = {
      ...state.spacingSettings,
      ...(state.layout.spacingSettings || state.layout.spacing_settings || {}),
    };
    state.layout.snapSettings = { ...state.snapSettings };
    state.layout.spacingSettings = { ...state.spacingSettings };
    normalizeLayoutFaces();
  }

  function ensureEngineDefaults() {
    if (!Array.isArray(state.layout.allowed_engines) || state.layout.allowed_engines.length === 0) {
      state.layout.allowed_engines = ['repeat', 'nesting', 'hybrid'];
    }
    if (!state.layout.imposition_engine || !state.layout.allowed_engines.includes(state.layout.imposition_engine)) {
      state.layout.imposition_engine = state.layout.allowed_engines[0];
    }
  }

  function normalizeDesignDefaults() {
    state.layout.designs = (state.layout.designs || []).map((d) => ({
      ...d,
      width_mm: d.width_mm ?? d.w_mm ?? 0,
      height_mm: d.height_mm ?? d.h_mm ?? 0,
      bleed_mm: d.bleed_mm ?? state.layout.bleed_default_mm ?? 0,
      allow_rotation: d.allow_rotation !== false,
      forms_per_plate: Math.max(1, parseInt(d.forms_per_plate || '1', 10)),
    }));
  }

  function normalizeFormsPerPlateValue(value) {
    const parsed = parseInt(value, 10);
    if (!Number.isFinite(parsed) || parsed < 1) return 1;
    return parsed;
  }

  function normalizeNonNegativeNumber(value, fallback = 0) {
    const parsed = parseFloat(value);
    if (!Number.isFinite(parsed) || parsed < 0) return fallback;
    return parsed;
  }

  function normalizeLayoutFaces() {
    if (!state.layout) return;
    if (!Array.isArray(state.layout.faces) || state.layout.faces.length === 0) {
      state.layout.faces = ['front'];
    }
    if (!state.layout.active_face || !state.layout.faces.includes(state.layout.active_face)) {
      state.layout.active_face = state.layout.faces[0];
    }
    if (!state.layout.slots) {
      state.layout.slots = [];
    }
    state.layout.slots.forEach((slot) => {
      if (!slot.face) {
        slot.face = 'front';
      }
    });
    state.activeFace = state.layout.active_face || 'front';
  }

  function pushHistory() {
    if (!state.layout) return;
    const snapshot = JSON.parse(JSON.stringify(state.layout));
    if (history.pointer < history.stack.length - 1) {
      history.stack = history.stack.slice(0, history.pointer + 1);
    }
    history.stack.push(snapshot);
    if (history.stack.length > history.maxSize) {
      history.stack.shift();
    }
    history.pointer = history.stack.length - 1;
  }

  function undoHistory() {
    if (history.pointer <= 0) return;
    history.pointer -= 1;
    state.layout = JSON.parse(JSON.stringify(history.stack[history.pointer]));
    state.snapSettings = {
      ...state.snapSettings,
      ...(state.layout.snapSettings || state.layout.snap_settings || {}),
    };
    state.spacingSettings = {
      ...state.spacingSettings,
      ...(state.layout.spacingSettings || state.layout.spacing_settings || {}),
    };
    ensureEngineDefaults();
    normalizeDesignDefaults();
    normalizeLayoutFaces();
    state.selectedSlot = null;
    state.selectedSlots = new Set();
    initSheetControls();
    renderWorks();
    renderDesigns();
    renderSnapControls();
    renderSpacingControls();
    renderImpositionControls();
    recalcScale();
    renderSheet();
    renderSlotForm();
    renderFaceToggle();
  }

  function mmToPx(mm) {
    return mm * state.scale;
  }

  function getSlotRenderBox(slot) {
    const baseW = slot.w_mm || 0;
    const baseH = slot.h_mm || 0;
    const rotation = ((slot.rotation_deg || 0) % 360 + 360) % 360;
    const rotated = rotation === 90 || rotation === 270;

    const visualW = rotated ? baseH : baseW;
    const visualH = rotated ? baseW : baseH;

    const centerX = slot.x_mm + baseW / 2;
    const centerY = slot.y_mm + baseH / 2;

    return {
      x: centerX - visualW / 2,
      y: centerY - visualH / 2,
      w: visualW,
      h: visualH,
      rotation,
    };
  }

  function recalcScale() {
    const sheet = state.layout.sheet_mm || [640, 880];
    const prevScale = state.scale || 1;
    const maxW = Math.max((sheetCanvas?.clientWidth || 0) - 20, 0);
    const maxH = Math.max(Math.max((sheetCanvas?.clientHeight || 0) - 20, 400), 0);
    if (!maxW || !maxH || !sheet[0] || !sheet[1]) {
      return;
    }
    const scale = Math.min(maxW / sheet[0], maxH / sheet[1]);
    if (!Number.isFinite(scale) || scale <= 0) {
      state.scale = prevScale;
      return;
    }
    state.scale = Math.max(scale, 0.2);
  }

  function applySnap(x, y, slot) {
    const tolerance = Number(state.snapSettings.tolerance_mm) || 0;
    const grid = Number(state.snapSettings.grid_mm) || 1;
    let snappedX = x;
    let snappedY = y;

    if (state.snapSettings.snapGrid && grid > 0) {
      const nearestGridX = Math.round(x / grid) * grid;
      const nearestGridY = Math.round(y / grid) * grid;
      if (Math.abs(nearestGridX - x) <= tolerance) snappedX = nearestGridX;
      if (Math.abs(nearestGridY - y) <= tolerance) snappedY = nearestGridY;
    }

    if (state.snapSettings.snapMargins && state.layout.sheet_mm) {
      const [sheetW, sheetH] = state.layout.sheet_mm;
      const margins = state.layout.margins_mm || [0, 0, 0, 0];
      const [mLeft, mRight, mTop, mBottom] = margins;
      const marginTargetsX = [0, mLeft, sheetW - slot.w_mm - mRight, sheetW - slot.w_mm];
      const marginTargetsY = [0, mBottom, sheetH - slot.h_mm - mTop, sheetH - slot.h_mm];

      marginTargetsX.forEach((targetX) => {
        if (Math.abs(targetX - x) <= tolerance) snappedX = targetX;
      });
      marginTargetsY.forEach((targetY) => {
        if (Math.abs(targetY - y) <= tolerance) snappedY = targetY;
      });
    }

    if (state.snapSettings.snapSlots && state.layout.slots) {
      const activeFace = slot.face || state.activeFace || 'front';
      state.layout.slots.forEach((other) => {
        if (other.id === slot.id) return;
        if ((other.face || 'front') !== activeFace) return;
        const edgesX = [other.x_mm, other.x_mm + other.w_mm];
        const edgesY = [other.y_mm, other.y_mm + other.h_mm];
        edgesX.forEach((edgeX) => {
          if (Math.abs(edgeX - x) <= tolerance) snappedX = edgeX;
        });
        edgesY.forEach((edgeY) => {
          if (Math.abs(edgeY - y) <= tolerance) snappedY = edgeY;
        });
      });
    }

    return { x: snappedX, y: snappedY };
  }

  function updateHandleScale() {
    const handles = document.querySelectorAll('.slot .handle');
    const zoom = state.zoom || 1;

    // Tamaño base muy pequeño (4 px a 100%)
    let size = 4 * zoom;

    // Limitar para que nunca se hagan molestos
    if (size < 2) size = 2;
    if (size > 5) size = 5;

    handles.forEach((h) => {
      h.style.width = `${size}px`;
      h.style.height = `${size}px`;
    });
  }

  function applyZoom() {
    const sheet = document.getElementById('sheet');
    if (!sheet) return;
    sheet.style.transformOrigin = 'top left';
    sheet.style.transform = `scale(${state.zoom})`;
    const label = document.getElementById('zoom-label');
    if (label) {
      label.textContent = `${Math.round(state.zoom * 100)}%`;
    }
    updateHandleScale();
  }

  function syncSettingsToLayout() {
    state.layout.snapSettings = { ...state.snapSettings };
    state.layout.spacingSettings = { ...state.spacingSettings };
  }

  function renderSnapControls() {
    const snapSlotsInput = document.getElementById('snap-slots');
    const snapMarginsInput = document.getElementById('snap-margins');
    const snapGridInput = document.getElementById('snap-grid');
    const toleranceInput = document.getElementById('snap-tolerance');
    if (snapSlotsInput) snapSlotsInput.checked = !!state.snapSettings.snapSlots;
    if (snapMarginsInput) snapMarginsInput.checked = !!state.snapSettings.snapMargins;
    if (snapGridInput) snapGridInput.checked = !!state.snapSettings.snapGrid;
    if (toleranceInput) toleranceInput.value = state.snapSettings.tolerance_mm;
  }

  function updateSpacingLiveButton() {
    const liveBtn = document.getElementById('btn-spacing-live');
    if (!liveBtn) return;
    liveBtn.textContent = state.spacingSettings.live ? 'LIVE ON' : 'LIVE OFF';
    liveBtn.classList.toggle('btn-secondary', !!state.spacingSettings.live);
  }

  function renderSpacingControls() {
    const spacingXInput = document.getElementById('spacing-x');
    const spacingYInput = document.getElementById('spacing-y');
    if (spacingXInput) spacingXInput.value = state.spacingSettings.spacingX_mm;
    if (spacingYInput) spacingYInput.value = state.spacingSettings.spacingY_mm;
    updateSpacingLiveButton();
  }

  function updateSnapSettingsFromUI() {
    const snapSlotsInput = document.getElementById('snap-slots');
    const snapMarginsInput = document.getElementById('snap-margins');
    const snapGridInput = document.getElementById('snap-grid');
    const toleranceInput = document.getElementById('snap-tolerance');
    state.snapSettings.snapSlots = snapSlotsInput ? snapSlotsInput.checked : state.snapSettings.snapSlots;
    state.snapSettings.snapMargins = snapMarginsInput ? snapMarginsInput.checked : state.snapSettings.snapMargins;
    state.snapSettings.snapGrid = snapGridInput ? snapGridInput.checked : state.snapSettings.snapGrid;
    state.snapSettings.tolerance_mm = toleranceInput
      ? parseFloat(toleranceInput.value || state.snapSettings.tolerance_mm)
      : state.snapSettings.tolerance_mm;
    syncSettingsToLayout();
  }

  function updateSpacingSettingsFromUI() {
    const spacingXInput = document.getElementById('spacing-x');
    const spacingYInput = document.getElementById('spacing-y');
    state.spacingSettings.spacingX_mm = spacingXInput
      ? parseFloat(spacingXInput.value || state.spacingSettings.spacingX_mm)
      : state.spacingSettings.spacingX_mm;
    state.spacingSettings.spacingY_mm = spacingYInput
      ? parseFloat(spacingYInput.value || state.spacingSettings.spacingY_mm)
      : state.spacingSettings.spacingY_mm;
    syncSettingsToLayout();
  }

  function toggleLiveSpacing() {
    state.spacingSettings.live = !state.spacingSettings.live;
    syncSettingsToLayout();
    updateSpacingLiveButton();
  }

  function clearChildren(el) {
    while (el.firstChild) el.removeChild(el.firstChild);
  }

  function initSheetControls() {
    const layout = state.layout;
    if (!layout.sheet_mm) {
      layout.sheet_mm = [640, 880];
    }
    const sheetWInput = document.getElementById('sheet-w');
    const sheetHInput = document.getElementById('sheet-h');
    if (sheetWInput) sheetWInput.value = layout.sheet_mm[0];
    if (sheetHInput) sheetHInput.value = layout.sheet_mm[1];
  }

  function renderSheet() {
    const [sheetW, sheetH] = state.layout.sheet_mm;
    sheetEl.style.width = `${mmToPx(sheetW)}px`;
    sheetEl.style.height = `${mmToPx(sheetH)}px`;
    clearChildren(sheetEl);

    const activeFace = state.activeFace || 'front';
    const visibleSlots = state.layout.slots.filter((slot) => (slot.face || 'front') === activeFace);

    visibleSlots.forEach((slot) => {
      const slotEl = document.createElement('div');
      slotEl.className = 'slot';
      if (slot.locked) slotEl.classList.add('locked');
      const isSelectedSet = state.selectedSlots && state.selectedSlots.has(slot.id);
      if (isSelectedSet || (state.selectedSlot && state.selectedSlot.id === slot.id)) {
        slotEl.classList.add('selected');
      }
      slotEl.dataset.slotId = slot.id;
      const renderBox = getSlotRenderBox(slot);
      slotEl.style.left = `${mmToPx(renderBox.x)}px`;
      slotEl.style.bottom = `${mmToPx(renderBox.y)}px`;
      slotEl.style.width = `${mmToPx(renderBox.w)}px`;
      slotEl.style.height = `${mmToPx(renderBox.h)}px`;
      slotEl.style.transformOrigin = 'center';
      slotEl.style.transform = `rotate(${renderBox.rotation}deg)`;

      // Handles de esquina desactivados, el usuario escala solo desde el panel lateral.

      slotEl.addEventListener('mousedown', (ev) => onSlotMouseDown(ev, slot));
      slotEl.addEventListener('click', (ev) => {
        ev.stopPropagation();
        const toggle = ev.ctrlKey || ev.metaKey || ev.shiftKey;
        selectSlot(slot.id, { toggle });
      });
      sheetEl.appendChild(slotEl);
    });
    updateHandleScale();
    applyZoom();
  }

  function renderFaceToggle() {
    const frontInput = document.getElementById('face-front');
    const backInput = document.getElementById('face-back');
    if (frontInput) {
      frontInput.checked = state.activeFace === 'front';
    }
    if (backInput) {
      backInput.checked = state.activeFace === 'back';
    }
  }

  function setActiveFace(face) {
    if (!face) return;
    if (!state.layout.faces.includes(face)) {
      state.layout.faces.push(face);
    }
    state.activeFace = face;
    state.layout.active_face = face;
    state.selectedSlot = null;
    state.selectedSlots = new Set();
    renderFaceToggle();
    renderSheet();
    renderSlotForm();
  }

  function selectSlot(id, opts = {}) {
    const toggle = opts.toggle;
    if (!id) {
      state.selectedSlots = new Set();
      state.selectedSlot = null;
      renderSheet();
      renderSlotForm();
      return;
    }

    if (!state.selectedSlots) {
      state.selectedSlots = new Set();
    }

    if (toggle) {
      if (state.selectedSlots.has(id)) {
        state.selectedSlots.delete(id);
      } else {
        state.selectedSlots.add(id);
      }
    } else {
      state.selectedSlots = new Set([id]);
    }

    const firstSelectedId = state.selectedSlots.values().next().value;
    state.selectedSlot = state.layout.slots.find((s) => s.id === firstSelectedId) || null;
    renderSheet();
    renderSlotForm();
  }

  function renderSlotForm() {
    const slot = state.selectedSlot || (state.selectedSlots && state.selectedSlots.size > 0
      ? state.layout.slots.find((s) => state.selectedSlots.has(s.id))
      : null);

    if (!slot) {
      slotForm.classList.add('hidden');
      slotNone.classList.remove('hidden');
      return;
    }
    slotForm.classList.remove('hidden');
    slotNone.classList.add('hidden');
    document.getElementById('slot-x').value = slot.x_mm ?? 0;
    document.getElementById('slot-y').value = slot.y_mm ?? 0;
    document.getElementById('slot-w').value = slot.w_mm ?? 0;
    document.getElementById('slot-h').value = slot.h_mm ?? 0;
    document.getElementById('slot-rot').value = slot.rotation_deg || 0;
    document.getElementById('slot-bleed').value = slot.bleed_mm ?? 0;
    document.getElementById('slot-crop').checked = !!slot.crop_marks;
    document.getElementById('slot-locked').checked = !!slot.locked;

    const workSelect = document.getElementById('slot-work');
    clearChildren(workSelect);
    state.layout.works.forEach((w) => {
      const opt = document.createElement('option');
      opt.value = w.id;
      opt.textContent = `${w.name} (${w.final_size_mm?.join('x')} mm)`;
      if (slot.logical_work_id === w.id) opt.selected = true;
      workSelect.appendChild(opt);
    });

    const designSelect = document.getElementById('slot-design');
    clearChildren(designSelect);
    const noneOpt = document.createElement('option');
    noneOpt.value = '';
    noneOpt.textContent = 'Sin PDF';
    designSelect.appendChild(noneOpt);
    state.layout.designs.forEach((d) => {
      const opt = document.createElement('option');
      opt.value = d.ref;
      opt.textContent = `${d.filename} (${d.ref})`;
      if (slot.design_ref === d.ref) opt.selected = true;
      designSelect.appendChild(opt);
    });
  }

  function renderWorks() {
    clearChildren(worksListEl);
    const workSelectForUpload = document.getElementById('design-work-select');
    const prevSelectedWork = workSelectForUpload ? workSelectForUpload.value : '';
    if (workSelectForUpload) {
      clearChildren(workSelectForUpload);
      const defaultOpt = document.createElement('option');
      defaultOpt.value = '';
      defaultOpt.textContent = '-- Sin trabajo específico --';
      workSelectForUpload.appendChild(defaultOpt);
    }
    state.layout.works.forEach((w) => {
      const item = document.createElement('div');
      item.className = 'item';
      if (state.selectedWork && state.selectedWork.id === w.id) item.classList.add('active');
      item.textContent = `${w.name} · ${w.final_size_mm?.join('x')} mm · copias ${w.desired_copies}`;
      item.addEventListener('click', () => {
        state.selectedWork = w;
        fillWorkForm(w);
        renderWorks();
      });
      worksListEl.appendChild(item);
      if (workSelectForUpload) {
        const opt = document.createElement('option');
        opt.value = w.id;
        opt.textContent = `${w.name} (${w.final_size_mm?.join('x')} mm)`;
        workSelectForUpload.appendChild(opt);
      }
    });
    if (workSelectForUpload && prevSelectedWork) {
      workSelectForUpload.value = prevSelectedWork;
    }
  }

  function fillWorkForm(work) {
    document.getElementById('work-name').value = work?.name || '';
    document.getElementById('work-w').value = work?.final_size_mm?.[0] ?? '';
    document.getElementById('work-h').value = work?.final_size_mm?.[1] ?? '';
    document.getElementById('work-copies').value = work?.desired_copies ?? 1;
    document.getElementById('work-bleed').value = work?.default_bleed_mm ?? 0;
    document.getElementById('work-has-bleed').checked = !!(work && work.has_bleed);
  }

  function newWork() {
    const work = {
      id: `w${Date.now()}`,
      name: 'Nuevo trabajo',
      final_size_mm: [50, 50],
      desired_copies: 1,
      default_bleed_mm: state.layout.bleed_default_mm || 0,
      has_bleed: false,
    };
    state.layout.works.push(work);
    state.selectedWork = work;
    renderWorks();
    fillWorkForm(work);
    pushHistory();
  }

  function saveWork() {
    if (!state.selectedWork) newWork();
    const w = state.selectedWork;
    w.name = document.getElementById('work-name').value || 'Trabajo';
    w.final_size_mm = [
      parseFloat(document.getElementById('work-w').value) || 0,
      parseFloat(document.getElementById('work-h').value) || 0,
    ];
    w.desired_copies = parseInt(document.getElementById('work-copies').value || '1', 10);
    w.default_bleed_mm = parseFloat(document.getElementById('work-bleed').value || '0');
    w.has_bleed = document.getElementById('work-has-bleed').checked;
    renderWorks();
    pushHistory();
  }

  function deleteWork() {
    if (!state.selectedWork) return;
    const workId = state.selectedWork.id;
    const slotsInUse = state.layout.slots.some((s) => s.logical_work_id === workId);
    const designsInUse = state.layout.designs.some((d) => d.work_id === workId);
    if (slotsInUse || designsInUse) {
      alert('No se puede eliminar: hay slots o PDFs que usan este trabajo.');
      return;
    }
    state.layout.works = state.layout.works.filter((w) => w.id !== workId);
    state.selectedWork = null;
    fillWorkForm(null);
    renderWorks();
    pushHistory();
  }

  function renderDesigns() {
    clearChildren(designsListEl);
    state.layout.designs.forEach((d) => {
      const li = document.createElement('li');
      li.className = 'design-item';

      const title = document.createElement('div');
      title.className = 'design-title';
      const work = state.layout.works.find((w) => w.id === d.work_id);
      const workLabel = work ? ` · Trabajo: ${work.name}` : '';
      title.textContent = `${d.filename || d.ref} (${d.ref})${workLabel}`;
      li.appendChild(title);

      const grid = document.createElement('div');
      grid.className = 'design-grid';

      const formsLabel = document.createElement('label');
      formsLabel.textContent = 'Formas/pliego';
      const formsInput = document.createElement('input');
      formsInput.type = 'number';
      formsInput.min = '1';
      formsInput.value = d.forms_per_plate ?? 1;
      formsInput.addEventListener('change', () => {
        const normalized = normalizeFormsPerPlateValue(formsInput.value);
        formsInput.value = normalized;
        d.forms_per_plate = normalized;
        pushHistory();
      });
      formsLabel.appendChild(formsInput);
      grid.appendChild(formsLabel);

      const widthLabel = document.createElement('label');
      widthLabel.textContent = 'Ancho (mm)';
      const widthInput = document.createElement('input');
      widthInput.type = 'number';
      widthInput.step = '0.1';
      widthInput.value = d.width_mm ?? 0;
      widthInput.addEventListener('change', () => {
        const normalized = normalizeNonNegativeNumber(widthInput.value, 0);
        widthInput.value = normalized;
        d.width_mm = normalized;
        pushHistory();
      });
      widthLabel.appendChild(widthInput);
      grid.appendChild(widthLabel);

      const heightLabel = document.createElement('label');
      heightLabel.textContent = 'Alto (mm)';
      const heightInput = document.createElement('input');
      heightInput.type = 'number';
      heightInput.step = '0.1';
      heightInput.value = d.height_mm ?? 0;
      heightInput.addEventListener('change', () => {
        const normalized = normalizeNonNegativeNumber(heightInput.value, 0);
        heightInput.value = normalized;
        d.height_mm = normalized;
        pushHistory();
      });
      heightLabel.appendChild(heightInput);
      grid.appendChild(heightLabel);

      const bleedLabel = document.createElement('label');
      bleedLabel.textContent = 'Bleed (mm)';
      const bleedInput = document.createElement('input');
      bleedInput.type = 'number';
      bleedInput.step = '0.1';
      bleedInput.value = d.bleed_mm ?? 0;
      bleedInput.addEventListener('change', () => {
        const normalized = normalizeNonNegativeNumber(bleedInput.value, 0);
        bleedInput.value = normalized;
        d.bleed_mm = normalized;
        pushHistory();
      });
      bleedLabel.appendChild(bleedInput);
      grid.appendChild(bleedLabel);

      const rotationLabel = document.createElement('label');
      rotationLabel.className = 'checkbox-inline';
      const rotationInput = document.createElement('input');
      rotationInput.type = 'checkbox';
      rotationInput.checked = d.allow_rotation !== false;
      rotationInput.addEventListener('change', () => {
        d.allow_rotation = rotationInput.checked;
        pushHistory();
      });
      rotationLabel.appendChild(rotationInput);
      rotationLabel.append(' Permitir rotación');
      grid.appendChild(rotationLabel);

      li.appendChild(grid);
      designsListEl.appendChild(li);
    });
    renderSlotForm();
    renderImpositionControls();
  }

  function renderImpositionControls() {
    ensureEngineDefaults();
    const engine = state.layout.imposition_engine || 'repeat';
    document.querySelectorAll('input[name="imposition-engine"]').forEach((input) => {
      if (input) input.checked = input.value === engine;
    });

    const hint = document.getElementById('imposition-engine-hint');
    if (hint) {
      if (engine === 'nesting') {
        hint.textContent = 'Nesting PRO optimiza la ubicación de cada diseño con rotación opcional.';
      } else if (engine === 'hybrid') {
        hint.textContent = 'Híbrido: se arma un patrón con Nesting PRO y se repite como bloque donde haya espacio disponible.';
      } else {
        hint.textContent = 'Step & Repeat PRO repetirá las formas declaradas respetando márgenes y pinzas.';
      }
    }

    const warning = document.getElementById('imposition-warning');
    if (warning) {
      warning.classList.toggle('hidden', !!(state.layout.designs && state.layout.designs.length));
    }

    const stepPanel = document.getElementById('step-repeat-panel');
    if (stepPanel) {
      stepPanel.classList.toggle('hidden', engine === 'nesting');
    }
  }

  function addSlot() {
    const idx = state.layout.slots.length + 1;
    const workId = state.layout.works[0]?.id || null;
    const slot = {
      id: `s${Date.now()}_${idx}`,
      x_mm: 10,
      y_mm: 10,
      w_mm: 50,
      h_mm: 50,
      rotation_deg: 0,
      logical_work_id: workId,
      bleed_mm: state.layout.bleed_default_mm || 0,
      crop_marks: true,
      locked: false,
      design_ref: null,
      face: state.activeFace || state.layout.active_face || 'front',
    };
    state.layout.slots.push(slot);
    pushHistory();
    selectSlot(slot.id);
  }

  function duplicateSlot() {
    if (!state.selectedSlot) return;
    const base = state.selectedSlot;
    const copy = { ...base, id: `s${Date.now()}` };
    copy.face = copy.face || base.face || state.activeFace || 'front';
    copy.x_mm += 5;
    copy.y_mm += 5;
    state.layout.slots.push(copy);
    pushHistory();
    selectSlot(copy.id);
  }

  function deleteSlot() {
    if (!state.selectedSlot) return;
    state.layout.slots = state.layout.slots.filter((s) => s.id !== state.selectedSlot.id);
    state.selectedSlot = null;
    state.selectedSlots = new Set();
    pushHistory();
    renderSheet();
    renderSlotForm();
  }

  function groupSelectedSlots() {
    if (!state.selectedSlots || state.selectedSlots.size < 2) {
      alert('Seleccioná al menos dos slots para agrupar.');
      return;
    }

    const groupId = `g${Date.now()}_${Math.floor(Math.random() * 1000)}`;

    state.layout.slots.forEach((slot) => {
      if (state.selectedSlots.has(slot.id)) {
        slot.group_id = groupId;
      }
    });

    pushHistory();
    renderSheet();
    renderSlotForm();
  }

  function ungroupSelectedSlots() {
    if (!state.selectedSlots || state.selectedSlots.size === 0) {
      alert('No hay slots seleccionados para desagrupar.');
      return;
    }

    state.layout.slots.forEach((slot) => {
      if (state.selectedSlots.has(slot.id)) {
        delete slot.group_id;
      }
    });

    pushHistory();
    renderSheet();
    renderSlotForm();
  }

  function groupSlotsByRow(slots) {
    const margin = 2; // tolerancia extra en mm
    const rows = [];
    const byCenterY = [...slots].sort(
      (a, b) => a.y_mm + a.h_mm / 2 - (b.y_mm + b.h_mm / 2),
    );

    byCenterY.forEach((slot) => {
      const centerY = slot.y_mm + slot.h_mm / 2;
      let targetRow = rows.find(
        (row) => Math.abs(row.centerY - centerY) <= (Math.max(row.maxHeight, slot.h_mm) / 2 + margin),
      );
      if (!targetRow) {
        targetRow = { slots: [], centerY, maxHeight: slot.h_mm };
        rows.push(targetRow);
      }
      targetRow.slots.push(slot);
      targetRow.centerY =
        (targetRow.centerY * (targetRow.slots.length - 1) + centerY) / targetRow.slots.length;
      targetRow.maxHeight = Math.max(targetRow.maxHeight, slot.h_mm);
    });

    rows.sort((a, b) => a.centerY - b.centerY);
    rows.forEach((row) => row.slots.sort((a, b) => a.x_mm - b.x_mm));
    return rows;
  }

  function groupSlotsByColumn(slots) {
    const margin = 2;
    const cols = [];
    const byCenterX = [...slots].sort(
      (a, b) => a.x_mm + a.w_mm / 2 - (b.x_mm + b.w_mm / 2),
    );

    byCenterX.forEach((slot) => {
      const centerX = slot.x_mm + slot.w_mm / 2;
      let targetCol = cols.find(
        (col) => Math.abs(col.centerX - centerX) <= (Math.max(col.maxWidth, slot.w_mm) / 2 + margin),
      );
      if (!targetCol) {
        targetCol = { slots: [], centerX, maxWidth: slot.w_mm };
        cols.push(targetCol);
      }
      targetCol.slots.push(slot);
      targetCol.centerX =
        (targetCol.centerX * (targetCol.slots.length - 1) + centerX) / targetCol.slots.length;
      targetCol.maxWidth = Math.max(targetCol.maxWidth, slot.w_mm);
    });

    cols.sort((a, b) => a.centerX - b.centerX);
    cols.forEach((col) => col.slots.sort((a, b) => a.y_mm - b.y_mm));
    return cols;
  }

  function applyGapToSlots() {
    if (!state.layout.slots || state.layout.slots.length === 0) {
      alert('No hay slots para reordenar.');
      return;
    }

    const selectedIds = state.selectedSlots ? Array.from(state.selectedSlots) : [];
    const targetSlots =
      selectedIds.length >= 2
        ? state.layout.slots.filter((s) => selectedIds.includes(s.id))
        : selectedIds.length === 0
        ? [...state.layout.slots]
        : null;

    if (!targetSlots) {
      alert('Selecciona al menos 2 slots o ninguno para aplicar la separación.');
      return;
    }

    const gapX = parseFloat(document.getElementById('gap-x').value || '0');
    const gapY = parseFloat(document.getElementById('gap-y').value || '0');

    const startX = Math.min(...targetSlots.map((s) => s.x_mm));
    const startY = Math.min(...targetSlots.map((s) => s.y_mm));

    const rows = groupSlotsByRow(targetSlots);
    let currentY = startY;

    rows.forEach((row) => {
      let currentX = startX;
      row.slots.forEach((slot) => {
        slot.x_mm = currentX;
        slot.y_mm = currentY;
        currentX += slot.w_mm + gapX;
      });
      currentY += row.maxHeight + gapY;
    });

    renderSheet();
    renderSlotForm();
    pushHistory();
  }

  function applySpacing(mode = 'all', opts = {}) {
    const { render = true, push = false, face = state.activeFace || 'front' } = opts;
    const spacingX = Number(state.spacingSettings.spacingX_mm) || 0;
    const spacingY = Number(state.spacingSettings.spacingY_mm) || 0;
    const visibleSlots = state.layout.slots.filter((s) => (s.face || 'front') === face);
    if (!visibleSlots.length) return false;

    const createInitialMap = () => {
      const map = new Map();
      state.layout.slots.forEach((s) => map.set(s.id, { x: s.x_mm, y: s.y_mm }));
      return map;
    };

    const moveGroup = (slot, dx, dy, initialMap, movedGroups) => {
      if (!slot.group_id || movedGroups.has(slot.group_id)) return;
      const faceKey = slot.face || face;
      const members = state.layout.slots.filter(
        (s) => s.group_id === slot.group_id && (s.face || 'front') === faceKey,
      );
      members.forEach((member) => {
        const init = initialMap.get(member.id) || { x: member.x_mm, y: member.y_mm };
        member.x_mm = init.x + dx;
        member.y_mm = init.y + dy;
      });
      movedGroups.add(slot.group_id);
    };

    if (mode === 'all' || mode === 'rows') {
      const initialMap = createInitialMap();
      const movedGroups = new Set();
      const rows = groupSlotsByRow(visibleSlots);
      rows.forEach((row) => {
        let currentX = row.slots[0].x_mm;
        row.slots.forEach((slot, index) => {
          if (index === 0) {
            moveGroup(slot, 0, 0, initialMap, movedGroups);
            return;
          }
          const prev = row.slots[index - 1];
          currentX = prev.x_mm + prev.w_mm + spacingX;
          const dx = currentX - slot.x_mm;
          slot.x_mm = currentX;
          moveGroup(slot, dx, 0, initialMap, movedGroups);
        });
      });
    }

    if (mode === 'all' || mode === 'columns') {
      const initialMap = createInitialMap();
      const movedGroups = new Set();
      const cols = groupSlotsByColumn(visibleSlots);
      cols.forEach((col) => {
        let currentY = col.slots[0].y_mm;
        col.slots.forEach((slot, index) => {
          if (index === 0) {
            moveGroup(slot, 0, 0, initialMap, movedGroups);
            return;
          }
          const prev = col.slots[index - 1];
          currentY = prev.y_mm + prev.h_mm + spacingY;
          const dy = currentY - slot.y_mm;
          slot.y_mm = currentY;
          moveGroup(slot, 0, dy, initialMap, movedGroups);
        });
      });
    }

    if (render) {
      renderSheet();
      renderSlotForm();
    }
    if (push) pushHistory();
    return true;
  }

  async function generateStepRepeatFromSelectedSlot() {
    const master = getSelectedSlot();
    if (!master) {
      alert('Seleccioná primero un slot maestro.');
      return;
    }

    const masterFace = master.face || 'front';
    master.face = masterFace;

    const rows = parseInt(document.getElementById('sr-rows').value || '1', 10);
    const cols = parseInt(document.getElementById('sr-cols').value || '1', 10);
    const gapH = parseFloat(document.getElementById('sr-gap-h').value || '0') || 0;
    const gapV = parseFloat(document.getElementById('sr-gap-v').value || '0') || 0;
    const mode = document.getElementById('sr-mode').value;
    const autoMargin = document.getElementById('sr-auto-margin').checked;
    const rotationMode = document.getElementById('sr-rotation').value;
    const pdfMode = document.getElementById('sr-assign-pdf-mode').value;
    const groupMode = document.getElementById('sr-group-mode').value;
    const copyBleed = document.getElementById('sr-copy-bleed').checked;
    const nudgeX = parseFloat(document.getElementById('sr-nudge-x').value || '0') || 0;
    const nudgeY = parseFloat(document.getElementById('sr-nudge-y').value || '0') || 0;

    if (rows < 1 || cols < 1) {
      alert('Filas y columnas deben ser al menos 1.');
      return;
    }

    const sheetW = (state.layout.sheet_mm && state.layout.sheet_mm[0]) || 640;
    const sheetH = (state.layout.sheet_mm && state.layout.sheet_mm[1]) || 880;
    const margins = state.layout.margins_mm || [10, 10, 10, 10];
    const [mLeft, mRight, mTop, mBottom] = margins;

    const slotW = master.w_mm;
    const slotH = master.h_mm;

    const baseBleed = copyBleed ? master.bleed_mm || 0 : state.layout.bleed_default_mm || 0;
    const baseCrop = copyBleed ? !!master.crop_marks : false;

    const totalW = cols * slotW + (cols - 1) * gapH;
    const totalH = rows * slotH + (rows - 1) * gapV;

    let x0 = master.x_mm;
    let y0 = master.y_mm;

    if (mode === 'center') {
      x0 = (sheetW - totalW) / 2;
      y0 = (sheetH - totalH) / 2;
    } else if (mode === 'align-left') {
      x0 = autoMargin ? mLeft : 0;
    } else if (mode === 'align-right') {
      x0 = autoMargin ? sheetW - mRight - totalW : sheetW - totalW;
    } else if (mode === 'align-top') {
      y0 = autoMargin ? mTop : 0;
    } else if (mode === 'align-bottom') {
      y0 = autoMargin ? sheetH - mBottom - totalH : sheetH - totalH;
    }

    x0 += nudgeX;
    y0 += nudgeY;

    let groupId = null;
    if (groupMode === 'grouped') {
      groupId = `g${Date.now()}_${Math.floor(Math.random() * 1000)}`;
    }

    if (groupId) {
      master.group_id = groupId;
    }

    let rotDeg = master.rotation_deg || 0;
    if (rotationMode !== 'keep') {
      rotDeg = parseFloat(rotationMode) || 0;
    }

    let designRef = master.design_ref || null;
    if (pdfMode === 'none') {
      designRef = null;
    }

    const newSlots = [];
    let index = 0;
    for (let r = 0; r < rows; r += 1) {
      for (let c = 0; c < cols; c += 1) {
        const isMasterPosition = r === 0 && c === 0;
        const x = x0 + c * (slotW + gapH);
        const y = y0 + r * (slotH + gapV);

        if (isMasterPosition) {
          master.x_mm = x;
          master.y_mm = y;
          master.bleed_mm = baseBleed;
          master.crop_marks = baseCrop;
          master.rotation_deg = rotDeg;
          if (groupId) master.group_id = groupId;
          if (pdfMode === 'same') master.design_ref = designRef;
          continue;
        }

        const clone = {
          ...master,
          id: `s${Date.now()}_${r}_${c}_${index}`,
          x_mm: x,
          y_mm: y,
          bleed_mm: baseBleed,
          crop_marks: baseCrop,
          rotation_deg: rotDeg,
        };

        clone.face = masterFace;

        if (groupId) {
          clone.group_id = groupId;
        } else {
          delete clone.group_id;
        }

        if (pdfMode === 'same') {
          clone.design_ref = designRef;
        } else if (pdfMode === 'none') {
          clone.design_ref = null;
        }

        newSlots.push(clone);
        index += 1;
      }
    }

    state.layout.slots = state.layout.slots.concat(newSlots);
    renderSheet();
    renderSlotForm();
    pushHistory();
    selectSlot(master.id);
  }

  function onSlotMouseDown(ev, slot) {
    if (slot.locked) return;
    const target = ev.target;
    const isHandle = target.classList.contains('handle');
    const startX = ev.clientX;
    const startY = ev.clientY;
    const initSlot = { ...slot };
    let moved = false;
    const handleType = isHandle ? [...target.classList].find((c) => ['br', 'bl', 'tr', 'tl'].includes(c)) : null;
    const isGroupMove = !isHandle && slot.group_id;
    const groupSlots = isGroupMove
      ? state.layout.slots.filter((s) => s.group_id === slot.group_id)
      : [];
    const groupInitialPositions = new Map();
    if (isGroupMove) {
      groupSlots.forEach((s) => {
        groupInitialPositions.set(s.id, { x: s.x_mm, y: s.y_mm });
      });
    }

    function onMove(moveEv) {
      moveEv.preventDefault();
      const dxPx = moveEv.clientX - startX;
      const dyPx = startY - moveEv.clientY; // invert because bottom reference
      const effectiveScale = state.scale * state.zoom;
      const dx = dxPx / effectiveScale;
      const dy = dyPx / effectiveScale;

      if (!isHandle) {
        if (isGroupMove) {
          const snapped = applySnap(initSlot.x_mm + dx, initSlot.y_mm + dy, slot);
          const deltaX = snapped.x - initSlot.x_mm;
          const deltaY = snapped.y - initSlot.y_mm;
          groupSlots.forEach((s) => {
            const initPos = groupInitialPositions.get(s.id);
            if (!initPos) return;
            s.x_mm = initPos.x + deltaX;
            s.y_mm = initPos.y + deltaY;
          });
        } else {
          const snapped = applySnap(initSlot.x_mm + dx, initSlot.y_mm + dy, slot);
          slot.x_mm = snapped.x;
          slot.y_mm = snapped.y;
        }
        if (state.spacingSettings.live) {
          applySpacing('all', { render: false, push: false, face: slot.face || state.activeFace });
        }
      } else {
        if (handleType.includes('b')) {
          slot.h_mm = Math.max(5, initSlot.h_mm + dy);
        }
        if (handleType.includes('t')) {
          const newH = Math.max(5, initSlot.h_mm - dy);
          slot.h_mm = newH;
          slot.y_mm = initSlot.y_mm + dy;
        }
        if (handleType.includes('r')) {
          slot.w_mm = Math.max(5, initSlot.w_mm + dx);
        }
        if (handleType.includes('l')) {
          const newW = Math.max(5, initSlot.w_mm - dx);
          slot.w_mm = newW;
          slot.x_mm = initSlot.x_mm + dx;
        }
      }
      moved = true;
      renderSheet();
      renderSlotForm();
    }

    function onUp() {
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
      if (moved) {
        pushHistory();
      }
    }

    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  }

  function applySlotForm() {
    if (!state.selectedSlot) return;
    const slot = state.selectedSlot;
    slot.x_mm = parseFloat(document.getElementById('slot-x').value || '0');
    slot.y_mm = parseFloat(document.getElementById('slot-y').value || '0');
    slot.w_mm = parseFloat(document.getElementById('slot-w').value || '0');
    slot.h_mm = parseFloat(document.getElementById('slot-h').value || '0');
    slot.rotation_deg = parseFloat(document.getElementById('slot-rot').value || '0');
    slot.bleed_mm = parseFloat(document.getElementById('slot-bleed').value || '0');
    slot.crop_marks = document.getElementById('slot-crop').checked;
    slot.locked = document.getElementById('slot-locked').checked;
    slot.logical_work_id = document.getElementById('slot-work').value || null;
    slot.design_ref = document.getElementById('slot-design').value || null;
    renderSheet();
    pushHistory();
  }

  function applyDesignToSelected() {
    const designRef = document.getElementById('slot-design').value;
    if (!designRef) {
      alert('Selecciona un PDF primero.');
      return;
    }

    const selectedIds = state.selectedSlots && state.selectedSlots.size > 0
      ? [...state.selectedSlots]
      : [];

    if (selectedIds.length === 0) {
      if (state.selectedSlot) {
        state.selectedSlot.design_ref = designRef;
        renderSheet();
        renderSlotForm();
        pushHistory();
      } else {
        alert('No hay slots seleccionados.');
      }
      return;
    }

    state.layout.slots.forEach((slot) => {
      if (state.selectedSlots.has(slot.id)) {
        slot.design_ref = designRef;
      }
    });

    renderSheet();
    renderSlotForm();
    pushHistory();
  }

  function duplicateFrontToBack() {
    normalizeLayoutFaces();
    if (!state.layout.faces.includes('back')) {
      state.layout.faces.push('back');
    }
    const frontSlots = state.layout.slots.filter((slot) => (slot.face || 'front') === 'front');
    if (frontSlots.length === 0) {
      alert('No hay slots en el frente para duplicar.');
      return;
    }

    const timestamp = Date.now();
    const clones = frontSlots.map((slot, idx) => ({
      ...slot,
      id: `s${timestamp}_${idx}_back`,
      face: 'back',
    }));

    state.layout.slots = state.layout.slots.concat(clones);
    setActiveFace('back');
    pushHistory();
  }

  function layoutToJson() {
    normalizeLayoutFaces();
    syncSettingsToLayout();
    ensureEngineDefaults();
    normalizeDesignDefaults();
    return JSON.stringify(state.layout);
  }

  async function saveLayout() {
    const body = new FormData();
    body.append('job_id', window.JOB_ID);
    body.append('layout_json', layoutToJson());
    const res = await fetch('/editor_offset/save', { method: 'POST', body });
    return res.json();
  }

  async function requestAutoLayout() {
    if (!state.layout.works || state.layout.works.length === 0) {
      alert('Primero crea al menos un Trabajo lógico con su medida final y copias.');
      return;
    }
    await saveLayout();
    const res = await fetch(`/editor_offset/auto_layout/${window.JOB_ID}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ layout_json: layoutToJson() }),
    });
    const data = await res.json();
    if (data.layout) {
      state.layout = data.layout;
      normalizeLayoutFaces();
      selectSlot(null);
      initSheetControls();
      renderWorks();
      renderDesigns();
      recalcScale();
      renderSheet();
      renderFaceToggle();
      pushHistory();
    }
  }

  async function applyImpositionEngine() {
    if (!state.layout.designs || state.layout.designs.length === 0) {
      const warning = document.getElementById('imposition-warning');
      if (warning) warning.classList.remove('hidden');
      alert('Configura al menos un diseño antes de aplicar el motor de imposición.');
      return;
    }
    normalizeDesignDefaults();
    ensureEngineDefaults();
    syncSettingsToLayout();
    if (Array.isArray(state.layout.slots) && state.layout.slots.length > 0) {
      const confirmed = window.confirm(
        'Aplicar el motor de imposición reemplazará los slots actuales del pliego.\n'
          + 'Si realizaste ajustes manuales, se perderán esos cambios.\n'
          + '¿Deseas continuar?',
      );
      if (!confirmed) return;
    }
    const body = new FormData();
    body.append('job_id', window.JOB_ID);
    body.append('selected_engine', state.layout.imposition_engine);
    body.append('layout_json', layoutToJson());
    const res = await fetch('/editor_offset_visual/apply_imposition', { method: 'POST', body });
    const data = await res.json();
    if (!data.ok && data.error) {
      alert(data.error);
      return;
    }
    if (data.layout) {
      state.layout = data.layout;
      ensureEngineDefaults();
      normalizeDesignDefaults();
      normalizeLayoutFaces();
      state.snapSettings = {
        ...state.snapSettings,
        ...(state.layout.snapSettings || state.layout.snap_settings || {}),
      };
      state.spacingSettings = {
        ...state.spacingSettings,
        ...(state.layout.spacingSettings || state.layout.spacing_settings || {}),
      };
      initSheetControls();
      renderWorks();
      renderDesigns();
      renderSnapControls();
      renderSpacingControls();
      renderImpositionControls();
      recalcScale();
      renderSheet();
      renderFaceToggle();
      pushHistory();
    }
  }

  async function requestPreview() {
    if (!state.layout.slots || state.layout.slots.length === 0) {
      alert('No hay slots en el pliego. Crea o genera los cuadros antes de generar la preview/PDF.');
      return;
    }
    await saveLayout();
    const res = await fetch(`/editor_offset/preview/${window.JOB_ID}`, { method: 'POST' });
    const data = await res.json();
    if (data.url) {
      previewImg.src = data.url + `?t=${Date.now()}`;
    }
  }

  async function requestPdf() {
    if (!state.layout.slots || state.layout.slots.length === 0) {
      alert('No hay slots en el pliego. Crea o genera los cuadros antes de generar la preview/PDF.');
      return;
    }
    await saveLayout();
    const res = await fetch(`/editor_offset/generar_pdf/${window.JOB_ID}`, { method: 'POST' });
    const data = await res.json();
    if (data.url) {
      pdfOutput.innerHTML = `<a href="${data.url}" target="_blank">Descargar PDF</a>`;
    }
  }

  async function uploadDesigns(ev) {
    ev.preventDefault();
    const filesInput = document.getElementById('design-files');
    if (!filesInput.files.length) return;
    const body = new FormData();
    for (const f of filesInput.files) body.append('files', f);
    const workSelectForUpload = document.getElementById('design-work-select');
    const selectedWorkId = workSelectForUpload ? workSelectForUpload.value : '';
    if (selectedWorkId) {
      body.append('work_id', selectedWorkId);
    }
    const res = await fetch(`/editor_offset/upload/${window.JOB_ID}`, { method: 'POST', body });
    const data = await res.json();
    if (data.designs) {
      state.layout.designs = data.designs;
      normalizeDesignDefaults();
      ensureEngineDefaults();
      renderDesigns();
      filesInput.value = '';
      pushHistory();
    }
  }

  async function init() {
    parseInitialLayout();
    initSheetControls();
    recalcScale();
    pushHistory();
    renderWorks();
    renderSheet();
    renderFaceToggle();
    renderDesigns();
    renderSnapControls();
    renderSpacingControls();
    renderImpositionControls();
    fillWorkForm(state.layout.works[0]);
    applyZoom();
    document.getElementById('btn-new-slot').addEventListener('click', addSlot);
    document.getElementById('btn-dup-slot').addEventListener('click', duplicateSlot);
    document.getElementById('btn-del-slot').addEventListener('click', deleteSlot);
    document.getElementById('btn-group-slots')?.addEventListener('click', groupSelectedSlots);
    document
      .getElementById('btn-ungroup-slots')
      ?.addEventListener('click', ungroupSelectedSlots);
    document.getElementById('btn-save').addEventListener('click', saveLayout);
    document.getElementById('btn-preview').addEventListener('click', requestPreview);
    document.getElementById('btn-pdf').addEventListener('click', requestPdf);
    document.getElementById('btn-auto').addEventListener('click', requestAutoLayout);
    document.getElementById('btn-apply-imposition')?.addEventListener('click', applyImpositionEngine);
    document.getElementById('btn-apply-gap').addEventListener('click', applyGapToSlots);
    document.getElementById('snap-slots')?.addEventListener('change', updateSnapSettingsFromUI);
    document.getElementById('snap-margins')?.addEventListener('change', updateSnapSettingsFromUI);
    document.getElementById('snap-grid')?.addEventListener('change', updateSnapSettingsFromUI);
    document.getElementById('snap-tolerance')?.addEventListener('input', updateSnapSettingsFromUI);
    document.getElementById('spacing-x')?.addEventListener('change', updateSpacingSettingsFromUI);
    document.getElementById('spacing-y')?.addEventListener('change', updateSpacingSettingsFromUI);
    document.getElementById('btn-spacing-apply-all')?.addEventListener('click', () => {
      updateSpacingSettingsFromUI();
      applySpacing('all', { push: true });
    });
    document.getElementById('btn-spacing-rows')?.addEventListener('click', () => {
      updateSpacingSettingsFromUI();
      applySpacing('rows', { push: true });
    });
    document.getElementById('btn-spacing-cols')?.addEventListener('click', () => {
      updateSpacingSettingsFromUI();
      applySpacing('columns', { push: true });
    });
    document.getElementById('btn-spacing-live')?.addEventListener('click', () => {
      toggleLiveSpacing();
      syncSettingsToLayout();
    });
    document.getElementById('face-front')?.addEventListener('change', () => setActiveFace('front'));
    document.getElementById('face-back')?.addEventListener('change', () => setActiveFace('back'));
    document.getElementById('btn-duplicate-face')?.addEventListener('click', () => duplicateFrontToBack());
    document.getElementById('btn-new-work').addEventListener('click', newWork);
    document.getElementById('btn-save-work').addEventListener('click', saveWork);
    document.getElementById('btn-delete-work').addEventListener('click', deleteWork);
    document.getElementById('btn-apply-slot').addEventListener('click', applySlotForm);
    document
      .getElementById('btn-apply-design-selection')
      .addEventListener('click', (ev) => {
        ev.preventDefault();
        applyDesignToSelected();
      });
    const stepRepeatBtn = document.getElementById('sr-generate');
    if (stepRepeatBtn) {
      stepRepeatBtn.addEventListener('click', generateStepRepeatFromSelectedSlot);
    }
    uploadForm.addEventListener('submit', uploadDesigns);
    document.querySelectorAll('input[name="imposition-engine"]').forEach((input) => {
      input.addEventListener('change', (ev) => {
        state.layout.imposition_engine = ev.target.value;
        renderImpositionControls();
      });
    });
    const zoomInBtn = document.getElementById('zoom-in');
    const zoomOutBtn = document.getElementById('zoom-out');
    if (zoomInBtn) {
      zoomInBtn.addEventListener('click', () => {
        state.zoom = Math.min(2.0, state.zoom + 0.1);
        applyZoom();
      });
    }
    if (zoomOutBtn) {
      zoomOutBtn.addEventListener('click', () => {
        state.zoom = Math.max(0.5, state.zoom - 0.1);
        applyZoom();
      });
    }
    if (sheetCanvas) {
      sheetCanvas.addEventListener('wheel', (ev) => {
        if (!ev.ctrlKey) return;
        ev.preventDefault();
        const delta = ev.deltaY < 0 ? 0.1 : -0.1;
        state.zoom = Math.min(2.0, Math.max(0.5, state.zoom + delta));
        applyZoom();
      });
    }
    document.getElementById('sheet-w')?.addEventListener('change', () => {
      const w = parseFloat(document.getElementById('sheet-w').value || '0');
      if (w > 0) {
        state.layout.sheet_mm[0] = w;
        recalcScale();
        renderSheet();
        applyZoom();
        pushHistory();
      }
    });
    document.getElementById('sheet-h')?.addEventListener('change', () => {
      const h = parseFloat(document.getElementById('sheet-h').value || '0');
      if (h > 0) {
        state.layout.sheet_mm[1] = h;
        recalcScale();
        renderSheet();
        applyZoom();
        pushHistory();
      }
    });
    document.getElementById('sheet-preset')?.addEventListener('change', (ev) => {
      const val = ev.target.value;
      if (!val) return;
      const [wStr, hStr] = val.split('x');
      const w = parseFloat(wStr);
      const h = parseFloat(hStr);
      if (w > 0 && h > 0) {
        state.layout.sheet_mm = [w, h];
        document.getElementById('sheet-w').value = w;
        document.getElementById('sheet-h').value = h;
        recalcScale();
        renderSheet();
        applyZoom();
        pushHistory();
      }
    });
    document.addEventListener('click', (ev) => {
      if (ev.target === sheetCanvas || ev.target === sheetEl) {
        state.selectedSlot = null;
        state.selectedSlots = new Set();
        renderSlotForm();
        renderSheet();
      }
    });
    window.addEventListener('resize', () => {
      recalcScale();
      renderSheet();
    });
    document.addEventListener('keydown', (ev) => {
      if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === 'z') {
        ev.preventDefault();
        undoHistory();
      }
    });
  }

  document.addEventListener('DOMContentLoaded', init);
})();
