/**
 * Editor manual — fit width + zoom + límites de arrastre + mejoras de productividad.
 */
(function () {
  const stage    = document.getElementById('manual-stage');
  const viewport = document.getElementById('viewport');
  const img      = document.getElementById('preview_img');
  const overlay  = document.getElementById('overlay');

  const btnMode  = document.getElementById('btn-manual-mode');

  const gridInput = document.getElementById('grid_mm');
  const snapChk   = document.getElementById('snap_on');
  const snapObjChk = document.getElementById('snap_obj');
  const validarChk = document.getElementById('validar_solapes');
  const warningsDiv = document.getElementById('manual-warnings');
  const cursorMM  = document.getElementById('cursor_mm');

  const zoomRange = document.getElementById('zoom_range');
  const zoomLabel = document.getElementById('zoom_label');
  const fitWidth  = document.getElementById('fit_width');
  const fitPage   = document.getElementById('fit_page');

  const manualJson = document.getElementById('manual_json');

  if (!overlay || !img || !stage || !viewport) return;


  const toNum = (v, def=0) => {
    const n = Number(v);
    return Number.isFinite(n) ? n : def;
  };

  const state = {
    sheet:  { w: 0, h: 0 },        // mm
    sangrado: toNum(window.__sangradoMm, 0),
    baseScale: 1,                  // px/mm con fit width
    zoom: 1,                       // 1 = 100%
    boxes: [],
    selectedIds: new Set(),
    drag: null,                    // {ids:Set,startPx:{x,y},startsTl:[{id,x,y}],moved:false}
    history: [], historyPtr: -1,
    snapObjEnabled: true,
    validarSolapes: false,
    marquee: null,                 // {x0,y0,x1,y1} mm (TL)
    panning: false,
    panStartPx: null,
    panScrollStart: null,
    snapGuides: {x:[], y:[]},
    pointers: new Map(),
    lastPinchDist: null,
  };

  // --- Helpers de archivos ---
  const manualFiles = Array.isArray(window.__manualFiles) ? window.__manualFiles : [];

  function resolveFileIdx(p) {
    // match exacto por ruta inyectada desde el server
    let idx = manualFiles.indexOf(p.archivo);
    if (idx >= 0) return idx;
    // fallback por basename
    const name = (p.archivo || '').split('/').pop();
    if (!name) return 0;
    idx = manualFiles.findIndex(f => f.split('/').pop() === name);
    return idx >= 0 ? idx : 0;
  }

  // Compacta y reindexa cajas antes de enviar
  function compactBoxes() {
    state.boxes = state.boxes.filter(b => !b.deleted);
    state.boxes.forEach((b, i) => { b.id = i; });
  }

  const dpr = window.devicePixelRatio || 1;

  const mmToPx = (mm) => mm * state.baseScale * state.zoom;
  const pxToMm = (px) => px / (state.baseScale * state.zoom);

  // Conversión BL <-> TL (top-left para pintar)
  const blToTl = (x_bl, y_bl, h_total) => ({ x: x_bl, y: state.sheet.h - y_bl - h_total });
  const tlToBl = (x_tl, y_tl, h_total) => ({ x: x_tl, y: state.sheet.h - y_tl - h_total });

  function buildBoxes(positions) {
    return (positions || []).map((p, i) => {
      const rotDeg = Number.isFinite(+p.rot_deg)
        ? (parseInt(p.rot_deg, 10) % 360)
        : (Number.isFinite(+p.rot)
            ? (parseInt(p.rot, 10) % 360)
            : (p.rotado ? 180 : 0));
      const rot90 = rotDeg % 180 !== 0;
      const wT  = toNum(p.w_mm, 0), hT = toNum(p.h_mm, 0);
      const W   = wT + 2*state.sangrado;
      const H   = hT + 2*state.sangrado;
      const tl  = blToTl(toNum(p.x_mm,0), toNum(p.y_mm,0), rot90 ? W : H);
      return {
        id: i,
        archivo: p.archivo ?? null,
        file_idx: Number.isFinite(p.file_idx) ? p.file_idx : resolveFileIdx(p),
        rot_deg: (rotDeg + 360) % 360,
        w_trim_mm: wT,
        h_trim_mm: hT,
        total_w_mm: rot90 ? H : W,
        total_h_mm: rot90 ? W : H,
        x_tl_mm: tl.x,
        y_tl_mm: tl.y,
      };
    });
  }

  function syncBaseScale() {
    const visibleW = img.clientWidth || img.getBoundingClientRect().width || img.naturalWidth || 1;
    state.baseScale = visibleW / (state.sheet.w || 1);
    overlay.width  = Math.round(visibleW * dpr);
    overlay.height = Math.round(state.sheet.h * state.baseScale * dpr);
    overlay.style.width = visibleW + 'px';
    overlay.style.height = (state.sheet.h * state.baseScale) + 'px';
    const ctx = overlay.getContext('2d');
    ctx.setTransform(dpr,0,0,dpr,0,0);
  }

  function setZoom(percent) {
    const z = Math.max(0.1, Math.min(2.0, percent / 100));
    state.zoom = z;
    viewport.style.transform = `scale(${state.zoom})`;
    if (zoomLabel) zoomLabel.textContent = `${Math.round(percent)}%`;
    repaint();
  }

  function fitToWidth() {
    setZoom(Math.max(10, Math.min(200, 100)));
    repaint();
  }

  function fitToPage() {
    const visibleW = img.clientWidth || img.getBoundingClientRect().width || 1;
    const baseHpx  = state.sheet.h * (visibleW / (state.sheet.w || 1));
    const stageH   = stage.clientHeight || 1;
    const ratio    = stageH / baseHpx;
    setZoom(Math.max(10, Math.min(200, Math.floor(ratio * 100))));
  }

  const ctx = overlay.getContext('2d');

  function drawGrid() {
    const gmm = Math.max(0.1, toNum(gridInput.value, 1));
    const step = mmToPx(gmm);
    const W = overlay.width, H = overlay.height;
    ctx.save();
    ctx.lineWidth = 1;
    ctx.strokeStyle = 'rgba(0,0,0,0.08)';
    ctx.beginPath();
    for (let x = 0; x <= W; x += step) { ctx.moveTo(x, 0); ctx.lineTo(x, H); }
    for (let y = 0; y <= H; y += step) { ctx.moveTo(0, y); ctx.lineTo(W, y); }
    ctx.stroke();
    ctx.restore();
  }

  function computeOverlaps(boxes) {
    const pairs = [];
    for (let i=0; i<boxes.length; i++) {
      for (let j=i+1; j<boxes.length; j++) {
        const a = boxes[i], b = boxes[j];
        if (a.x_tl_mm < b.x_tl_mm + b.total_w_mm &&
            a.x_tl_mm + a.total_w_mm > b.x_tl_mm &&
            a.y_tl_mm < b.y_tl_mm + b.total_h_mm &&
            a.y_tl_mm + a.total_h_mm > b.y_tl_mm) {
          pairs.push([a.id, b.id]);
        }
      }
    }
    return pairs;
  }

  function drawBoxes(overlapSet) {
    for (const b of state.boxes) {
      const x = mmToPx(b.x_tl_mm), y = mmToPx(b.y_tl_mm);
      const w = mmToPx(b.total_w_mm), h = mmToPx(b.total_h_mm);

      ctx.save();
      ctx.fillStyle = 'rgba(0,0,0,0.04)'; ctx.fillRect(x+2, y+2, w, h);
      const sel = state.selectedIds.has(b.id);
      const overlap = overlapSet.has(b.id);
      ctx.lineWidth = sel ? 2 : 1;
      ctx.strokeStyle = overlap ? '#c00' : (sel ? '#0ea5e9' : '#111');
      ctx.fillStyle = sel ? 'rgba(14,165,233,0.08)' : 'rgba(0,0,0,0.08)';
      ctx.fillRect(x, y, w, h); ctx.strokeRect(x, y, w, h);

      const trimX = x + mmToPx(state.sangrado);
      const trimY = y + mmToPx(state.sangrado);
      const trimW = mmToPx(b.w_trim_mm);
      const trimH = mmToPx(b.h_trim_mm);
      ctx.setLineDash([4,3]); ctx.strokeStyle='rgba(0,0,0,0.6)';
      ctx.strokeRect(trimX, trimY, trimW, trimH); ctx.setLineDash([]);

      ctx.fillStyle = '#111'; ctx.font = '12px sans-serif';
      const label = (b.archivo ? b.archivo.split('/').pop() : `PDF ${b.file_idx+1}`)
        + (b.rot_deg ? ` • R${b.rot_deg}` : '');
      ctx.fillText(label, x + 6, y + 16);
      ctx.restore();
    }
  }

  function repaint() {
    ctx.clearRect(0,0,overlay.width, overlay.height);
    if (snapChk?.checked) drawGrid();

    const overlaps = state.validarSolapes ? computeOverlaps(state.boxes) : [];
    const overlapSet = new Set();
    overlaps.forEach(p=>{ overlapSet.add(p[0]); overlapSet.add(p[1]); });
    if (warningsDiv) {
      warningsDiv.textContent = overlaps.length ? overlaps.map(p=>p.join('-')).join(', ') : '';
    }

    drawBoxes(overlapSet);

    ctx.save();
    ctx.setLineDash([4,4]);
    ctx.strokeStyle = 'rgba(14,165,233,0.6)';
    for (const x of state.snapGuides.x) {
      const px = mmToPx(x); ctx.beginPath(); ctx.moveTo(px,0); ctx.lineTo(px,overlay.height); ctx.stroke();
    }
    for (const y of state.snapGuides.y) {
      const py = mmToPx(y); ctx.beginPath(); ctx.moveTo(0,py); ctx.lineTo(overlay.width,py); ctx.stroke();
    }
    ctx.restore();

    if (state.marquee) {
      const {x0,y0,x1,y1} = state.marquee;
      const x = Math.min(x0,x1), y = Math.min(y0,y1);
      const w = Math.abs(x1-x0), h = Math.abs(y1-y0);
      const px = mmToPx(x), py = mmToPx(y), pw = mmToPx(w), ph = mmToPx(h);
      ctx.save();
      ctx.fillStyle = 'rgba(14,165,233,0.15)';
      ctx.strokeStyle = '#0ea5e9';
      ctx.setLineDash([4,2]);
      ctx.fillRect(px,py,pw,ph);
      ctx.strokeRect(px,py,pw,ph);
      ctx.restore();
    }
  }

  function hitTest(px, py) {
    for (let i = state.boxes.length-1; i >= 0; i--) {
      const b = state.boxes[i];
      const x = mmToPx(b.x_tl_mm), y = mmToPx(b.y_tl_mm);
      const w = mmToPx(b.total_w_mm), h = mmToPx(b.total_h_mm);
      if (px>=x && px<=x+w && py>=y && py<=y+h) return b.id;
    }
    return null;
  }

  const snapThreshold = 0.5; // mm
  function snapToObjects(nx, ny, box, selectedIds) {
    let bestDx = null, bestDy = null;
    let guideX = [], guideY = [];
    const myEdgesX = [nx, nx + box.total_w_mm, nx + box.total_w_mm/2];
    const myEdgesY = [ny, ny + box.total_h_mm, ny + box.total_h_mm/2];
    for (const ob of state.boxes) {
      if (selectedIds.has(ob.id)) continue;
      const otherX = [ob.x_tl_mm, ob.x_tl_mm + ob.total_w_mm, ob.x_tl_mm + ob.total_w_mm/2];
      const otherY = [ob.y_tl_mm, ob.y_tl_mm + ob.total_h_mm, ob.y_tl_mm + ob.total_h_mm/2];
      for (const m of myEdgesX) {
        for (const o of otherX) {
          const d = o - m;
          if (Math.abs(d) <= snapThreshold && (bestDx===null || Math.abs(d) < Math.abs(bestDx))) {
            bestDx = d; guideX = [o];
          }
        }
      }
      for (const m of myEdgesY) {
        for (const o of otherY) {
          const d = o - m;
          if (Math.abs(d) <= snapThreshold && (bestDy===null || Math.abs(d) < Math.abs(bestDy))) {
            bestDy = d; guideY = [o];
          }
        }
      }
    }
    return { x: nx + (bestDx||0), y: ny + (bestDy||0), guides:{x:guideX,y:guideY} };
  }

  overlay.addEventListener('mousedown', (e) => {
    overlay.focus && overlay.focus();
    const r = overlay.getBoundingClientRect();
    const px = e.clientX - r.left, py = e.clientY - r.top;

    if (state.panning) {
      state.panStartPx = {x:e.clientX, y:e.clientY};
      state.panScrollStart = {left: stage.scrollLeft, top: stage.scrollTop};
      return;
    }

    const id = hitTest(px, py);
    if (id != null) {
      if (e.shiftKey) {
        if (state.selectedIds.has(id)) state.selectedIds.delete(id); else state.selectedIds.add(id);
      } else if (!state.selectedIds.has(id) || state.selectedIds.size > 1) {
        state.selectedIds.clear(); state.selectedIds.add(id);
      }
      const sels = Array.from(state.selectedIds).map(i=>state.boxes.find(b=>b.id===i));
      state.drag = {
        ids: new Set(state.selectedIds),
        startPx: { x:px, y:py },
        startsTl: sels.map(b=>({id:b.id, x:b.x_tl_mm, y:b.y_tl_mm})),
        moved: false,
      };
    } else {
      if (!e.shiftKey) state.selectedIds.clear();
      state.marquee = { x0:pxToMm(px), y0:pxToMm(py), x1:pxToMm(px), y1:pxToMm(py) };
    }
    repaint();
  });

  overlay.addEventListener('mousemove', (e) => {
    const r = overlay.getBoundingClientRect();
    const px = e.clientX - r.left, py = e.clientY - r.top;
    const mmX = pxToMm(px), mmY = pxToMm(py);
    if (cursorMM && Number.isFinite(mmX) && Number.isFinite(mmY)) {
      cursorMM.textContent = `${mmX.toFixed(1)} , ${mmY.toFixed(1)} mm`;
    }

    if (state.panning && state.panStartPx) {
      stage.scrollLeft = state.panScrollStart.left - (e.clientX - state.panStartPx.x);
      stage.scrollTop  = state.panScrollStart.top  - (e.clientY - state.panStartPx.y);
      return;
    }

    if (state.marquee) {
      state.marquee.x1 = pxToMm(px);
      state.marquee.y1 = pxToMm(py);
      const xMin = Math.min(state.marquee.x0, state.marquee.x1);
      const xMax = Math.max(state.marquee.x0, state.marquee.x1);
      const yMin = Math.min(state.marquee.y0, state.marquee.y1);
      const yMax = Math.max(state.marquee.y0, state.marquee.y1);
      state.selectedIds.clear();
      for (const b of state.boxes) {
        const bx = b.x_tl_mm, by = b.y_tl_mm, bw = b.total_w_mm, bh = b.total_h_mm;
        if (bx>=xMin && bx+bw<=xMax && by>=yMin && by+bh<=yMax) state.selectedIds.add(b.id);
      }
      repaint();
      return;
    }

    if (!state.drag) return;

    const sels = state.drag.startsTl;
    let dx = pxToMm(px - state.drag.startPx.x);
    let dy = pxToMm(py - state.drag.startPx.y);
    let ref = sels[0];
    let nx = ref.x + dx;
    let ny = ref.y + dy;
    if (snapChk?.checked) {
      const g = Math.max(0.1, toNum(gridInput.value, 1));
      nx = Math.round(nx / g) * g;
      ny = Math.round(ny / g) * g;
    }
    state.snapGuides = {x:[], y:[]};
    if (state.snapObjEnabled) {
      const b0 = state.boxes.find(b=>b.id===ref.id);
      const res = snapToObjects(nx, ny, b0, state.drag.ids);
      nx = res.x; ny = res.y; state.snapGuides = res.guides;
    }
    const diffX = nx - (ref.x + dx);
    const diffY = ny - (ref.y + dy);
    for (const st of sels) {
      const b = state.boxes.find(bb=>bb.id===st.id);
      let nx2 = st.x + dx + diffX;
      let ny2 = st.y + dy + diffY;
      nx2 = Math.max(0, Math.min(nx2, state.sheet.w - b.total_w_mm));
      ny2 = Math.max(0, Math.min(ny2, state.sheet.h - b.total_h_mm));
      b.x_tl_mm = nx2; b.y_tl_mm = ny2;
    }
    state.drag.moved = true;
    repaint();
  });

  window.addEventListener('mouseup', () => {
    if (state.drag) {
      if (state.drag.moved) pushHistory();
      state.drag = null;
      state.snapGuides = {x:[], y:[]};
      repaint();
    }
    state.marquee = null;
  });

  function moveSelected(dx, dy) {
    if (!state.selectedIds.size) return;
    const sels = Array.from(state.selectedIds).map(id=>state.boxes.find(b=>b.id===id));
    let ref = sels[0];
    let nx = ref.x_tl_mm + dx;
    let ny = ref.y_tl_mm + dy;
    if (snapChk?.checked) {
      const g = Math.max(0.1, toNum(gridInput.value, 1));
      nx = Math.round(nx / g) * g;
      ny = Math.round(ny / g) * g;
    }
    state.snapGuides = {x:[], y:[]};
    if (state.snapObjEnabled) {
      const res = snapToObjects(nx, ny, ref, new Set(state.selectedIds));
      nx = res.x; ny = res.y; state.snapGuides = res.guides;
    }
    const diffX = nx - (ref.x_tl_mm + dx);
    const diffY = ny - (ref.y_tl_mm + dy);
    for (const b of sels) {
      let nx2 = b.x_tl_mm + dx + diffX;
      let ny2 = b.y_tl_mm + dy + diffY;
      nx2 = Math.max(0, Math.min(nx2, state.sheet.w - b.total_w_mm));
      ny2 = Math.max(0, Math.min(ny2, state.sheet.h - b.total_h_mm));
      b.x_tl_mm = nx2; b.y_tl_mm = ny2;
    }
    pushHistory();
    repaint();
  }

  overlay.addEventListener('mousedown', () => overlay.focus?.());

  function rotateSelected(delta = 90){
    if (!state.selectedIds.size) return;
    for (const id of state.selectedIds) {
      const b = state.boxes.find(x=>x.id===id); if (!b) continue;
      const prev = parseInt(b.rot_deg || 0, 10);
      const prev90 = prev % 180 !== 0;
      const r = (prev + delta) % 360;
      b.rot_deg = (r + 360) % 360;
      const now90 = b.rot_deg % 180 !== 0;
      if (prev90 !== now90) {
        [b.w_trim_mm, b.h_trim_mm] = [b.h_trim_mm, b.w_trim_mm];
        [b.total_w_mm, b.total_h_mm] = [b.total_h_mm, b.total_w_mm];
      }
    }
    pushHistory();
  }

  function clampAllToSheet(){
    for (const b of state.boxes) {
      b.x_tl_mm = Math.max(0, Math.min(b.x_tl_mm, state.sheet.w - b.total_w_mm));
      b.y_tl_mm = Math.max(0, Math.min(b.y_tl_mm, state.sheet.h - b.total_h_mm));
    }
  }

  function editorIsVisible(){
    const stage = document.getElementById('manual-stage');
    return !!stage && stage.offsetParent !== null;
  }
  function editorIsActive(state){
    const hasSel = state.selectedIds && state.selectedIds.size > 0;
    const hasFocus = document.activeElement === overlay || document.activeElement === document.getElementById('manual-stage');
    return editorIsVisible() && (hasSel || hasFocus || state.panning);
  }

  window.addEventListener('keydown', (e) => {
    const k = e.key;
    const tag = (document.activeElement?.tagName || '').toLowerCase();
    if (['input','textarea','select'].includes(tag)) return;

    if (!editorIsActive(state)) return;

    if ((e.ctrlKey || e.metaKey) && k.toLowerCase() === 'z') { undo(); e.preventDefault(); return; }
    if ((e.ctrlKey || e.metaKey) && k.toLowerCase() === 'y') { redo(); e.preventDefault(); return; }
    if ((e.ctrlKey || e.metaKey) && k.toLowerCase() === 'd') { duplicateSelection(); e.preventDefault(); return; }
    if (k === 'Delete' || k === 'Backspace') { deleteSelected(); e.preventDefault(); return; }
    if (k === 'f' || k === 'F') { fitToPage(); e.preventDefault(); return; }
    if (k === 'w' || k === 'W') { fitToWidth(); e.preventDefault(); return; }

    if (k === ' ') { state.panning = true; document.getElementById('manual-stage').style.cursor = 'grab'; e.preventDefault(); return; }
    if ((k === 'r' || k === 'R') && state.selectedIds?.size > 0) { rotateSelected(90); clampAllToSheet(); repaint(); e.preventDefault(); return; }
    if (k.startsWith('Arrow') && state.selectedIds?.size > 0) {
      const step = e.shiftKey ? 10 : 1;
      const dx = (k === 'ArrowLeft' ? -step : k === 'ArrowRight' ? step : 0);
      const dy = (k === 'ArrowUp'   ? -step : k === 'ArrowDown'  ? step : 0);
      moveSelected(dx, dy); clampAllToSheet(); repaint(); e.preventDefault();
    }
  }, { capture: true });
  window.addEventListener('keyup', (e) => {
    if (e.key === ' ') {
      state.panning = false;
      state.panStartPx = null;
      state.panScrollStart = null;
      document.getElementById('manual-stage').style.cursor = '';
    }
  });

  function pushHistory() {
    state.history = state.history.slice(0, state.historyPtr + 1);
    state.history.push({ boxes: state.boxes.map(b=>({...b})), selected: Array.from(state.selectedIds) });
    if (state.history.length > 50) state.history.shift();
    state.historyPtr = state.history.length - 1;
  }

  function undo() {
    if (state.historyPtr <= 0) return;
    state.historyPtr -= 1;
    const h = state.history[state.historyPtr];
    state.boxes = h.boxes.map(b=>({...b}));
    state.selectedIds = new Set(h.selected);
    repaint();
  }

  function redo() {
    if (state.historyPtr >= state.history.length - 1) return;
    state.historyPtr += 1;
    const h = state.history[state.historyPtr];
    state.boxes = h.boxes.map(b=>({...b}));
    state.selectedIds = new Set(h.selected);
    repaint();
  }

  function duplicateSelection() {
    const sels = state.boxes.filter(b=>state.selectedIds.has(b.id));
    if (!sels.length) return;
    let maxId = state.boxes.reduce((m,b)=>Math.max(m,b.id), -1);
    const clones = [];
    for (const b of sels) {
      const nb = { ...b, id: ++maxId, x_tl_mm: b.x_tl_mm + 5, y_tl_mm: b.y_tl_mm + 5 };
      state.boxes.push(nb);
      clones.push(nb);
    }
    state.selectedIds = new Set(clones.map(b=>b.id));
    pushHistory();
    repaint();
  }

  function deleteSelected() {
    const ids = Array.from(state.selectedIds);
    if (!ids.length) return;
    state.boxes = state.boxes.filter(b => !ids.includes(b.id));
    state.selectedIds.clear();
    pushHistory && pushHistory();
    repaint();
  }

  function alignSelection(mode) {
    const sels = state.boxes.filter(b=>state.selectedIds.has(b.id));
    if (sels.length < 2) return;
    const minX = Math.min(...sels.map(b=>b.x_tl_mm));
    const maxX = Math.max(...sels.map(b=>b.x_tl_mm + b.total_w_mm));
    const minY = Math.min(...sels.map(b=>b.y_tl_mm));
    const maxY = Math.max(...sels.map(b=>b.y_tl_mm + b.total_h_mm));
    const cx = (minX + maxX)/2, cy = (minY + maxY)/2;
    for (const b of sels) {
      switch(mode) {
        case 'left': b.x_tl_mm = minX; break;
        case 'hcenter': b.x_tl_mm = cx - b.total_w_mm/2; break;
        case 'right': b.x_tl_mm = maxX - b.total_w_mm; break;
        case 'top': b.y_tl_mm = minY; break;
        case 'vcenter': b.y_tl_mm = cy - b.total_h_mm/2; break;
        case 'bottom': b.y_tl_mm = maxY - b.total_h_mm; break;
      }
      b.x_tl_mm = Math.max(0, Math.min(b.x_tl_mm, state.sheet.w - b.total_w_mm));
      b.y_tl_mm = Math.max(0, Math.min(b.y_tl_mm, state.sheet.h - b.total_h_mm));
    }
    pushHistory();
    repaint();
  }

  function distributeSelection(axis) {
    const sels = state.boxes.filter(b=>state.selectedIds.has(b.id));
    if (sels.length <= 2) return;
    if (axis === 'h') {
      const sorted = sels.slice().sort((a,b)=>(a.x_tl_mm + a.total_w_mm/2) - (b.x_tl_mm + b.total_w_mm/2));
      const first = sorted[0], last = sorted[sorted.length-1];
      const span = (last.x_tl_mm + last.total_w_mm/2) - (first.x_tl_mm + first.total_w_mm/2);
      const step = span / (sorted.length - 1);
      sorted.forEach((b,i)=>{
        const center = (first.x_tl_mm + first.total_w_mm/2) + step*i;
        b.x_tl_mm = center - b.total_w_mm/2;
        b.x_tl_mm = Math.max(0, Math.min(b.x_tl_mm, state.sheet.w - b.total_w_mm));
      });
    } else {
      const sorted = sels.slice().sort((a,b)=>(a.y_tl_mm + a.total_h_mm/2) - (b.y_tl_mm + b.total_h_mm/2));
      const first = sorted[0], last = sorted[sorted.length-1];
      const span = (last.y_tl_mm + last.total_h_mm/2) - (first.y_tl_mm + first.total_h_mm/2);
      const step = span / (sorted.length - 1);
      sorted.forEach((b,i)=>{
        const center = (first.y_tl_mm + first.total_h_mm/2) + step*i;
        b.y_tl_mm = center - b.total_h_mm/2;
        b.y_tl_mm = Math.max(0, Math.min(b.y_tl_mm, state.sheet.h - b.total_h_mm));
      });
    }
    pushHistory();
    repaint();
  }

  function buildPayload() {
    compactBoxes();
    const clampIdx = (idx, b) => (
      Number.isFinite(+idx) && +idx >= 0 && +idx < manualFiles.length
    ) ? +idx : resolveFileIdx(b);

    const num = v => Number.isFinite(+v) ? +(+v).toFixed(3) : NaN;

    const payload = [];
    for (const b of state.boxes) {
      if (b.deleted) continue;
      const bl = tlToBl(b.x_tl_mm, b.y_tl_mm, b.total_h_mm);
      const rec = {
        id: b.id,
        archivo: b.archivo ? b.archivo.split('/').pop() : null,
        file_idx: clampIdx(b.file_idx, b),
        x_mm: num(bl.x),
        y_mm: num(bl.y),
        w_mm: num(b.w_trim_mm ?? b.w_mm),
        h_mm: num(b.h_trim_mm ?? b.h_mm),
        rot_deg: Number.isFinite(+b.rot_deg) ? (parseInt(b.rot_deg, 10) % 360) : (
                 Number.isFinite(+b.rot) ? (parseInt(b.rot, 10) % 360) : 0)
      };
      if (![rec.x_mm, rec.y_mm, rec.w_mm, rec.h_mm].every(Number.isFinite)) {
        console.error("Payload inválido:", rec, b);
        throw new Error("Valores numéricos inválidos (NaN) en posiciones.");
      }
      if (rec.w_mm <= 0 || rec.h_mm <= 0) {
        throw new Error("Ancho/alto deben ser mayores a 0 mm.");
      }
      payload.push(rec);
    }
    if (!payload.length) throw new Error("No hay diseños para aplicar.");
    return payload;
  }

  async function applyManual() {
    try {
      const positions = buildPayload();
      const res = await fetch('/api/manual/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ positions })
      });
      const json = await res.json();
      if (!res.ok || json.error) {
        throw new Error(json.error || 'Error en preview');
      }
      const imgEl = document.getElementById('preview_img');
      if (imgEl && json.preview_path) {
        imgEl.src = json.preview_path + '?v=' + Date.now();
      }
    } catch (e) {
      alert(e.message || 'Error al aplicar.');
      console.error('applyManual failed:', e);
    }
  }

  async function generateManual() {
    try {
      const positions = buildPayload();
      const res = await fetch('/api/manual/impose', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ positions })
      });
      const json = await res.json();
      if (!res.ok || json.error) {
        throw new Error(json.error || 'No se pudo generar el PDF.');
      }
      if (json.pdf_url) {
        window.location.href = json.pdf_url;
      }
    } catch (e) {
      alert(e.message || 'No se pudo generar el PDF.');
      console.error('generateManual failed:', e);
    }
  }

  document.getElementById('btn-manual-apply')?.addEventListener('click', applyManual);
  document.getElementById('btn-manual-generate')?.addEventListener('click', generateManual);

  function initFromData(opts) {
    state.sheet = { w: toNum(opts?.sheet_mm?.w, 0), h: toNum(opts?.sheet_mm?.h, 0) };
    state.sangrado = toNum(opts?.sangrado_mm, state.sangrado);
    state.boxes = buildBoxes(Array.isArray(opts?.posiciones) ? opts.posiciones : (Array.isArray(opts?.positions) ? opts.positions : []));
    state.selectedIds.clear();
    if (img.complete) {
      syncBaseScale(); setZoom(toNum(zoomRange?.value, 100)); repaint();
    } else {
      img.addEventListener('load', () => { syncBaseScale(); setZoom(toNum(zoomRange?.value, 100)); repaint(); }, { once:true });
    }
    state.history = []; state.historyPtr = -1; pushHistory();
  }

  window.manualEditorLoad = function(opts) {
    if (opts?.preview_url) img.src = opts.preview_url;
    initFromData({ sheet_mm:opts?.sheet_mm, posiciones:opts?.positions, sangrado_mm:opts?.sangrado_mm });
  };

  btnMode?.addEventListener('click', () => {
    const show = (document.getElementById('manual-editor').style.display !== 'block');
    document.getElementById('manual-editor').style.display = show ? 'block' : 'none';
    if (show) { syncBaseScale(); setZoom(toNum(zoomRange?.value, 100)); repaint(); }
  });

  const ro = new ResizeObserver(() => { syncBaseScale(); repaint(); });
  ro.observe(stage);

  zoomRange?.addEventListener('input', () => setZoom(toNum(zoomRange.value, 100)));
  fitWidth?.addEventListener('click', fitToWidth);
  fitPage?.addEventListener('click', fitToPage);

  snapObjChk?.addEventListener('change', () => { state.snapObjEnabled = snapObjChk.checked; });
  validarChk?.addEventListener('change', () => { state.validarSolapes = validarChk.checked; repaint(); });

  overlay.addEventListener('pointerdown', e=>{ state.pointers.set(e.pointerId,{x:e.clientX,y:e.clientY}); overlay.setPointerCapture(e.pointerId); });
  overlay.addEventListener('pointermove', e=>{
    if(!state.pointers.has(e.pointerId)) return;
    state.pointers.set(e.pointerId,{x:e.clientX,y:e.clientY});
    if(state.pointers.size===2){
      const pts=[...state.pointers.values()];
      const dist=Math.hypot(pts[0].x-pts[1].x, pts[0].y-pts[1].y);
      if(state.lastPinchDist){
        const factor = dist / state.lastPinchDist;
        const oldZoom = state.zoom;
        let newPercent = Math.max(10, Math.min(200, toNum(zoomRange.value,100)*factor));
        zoomRange.value = newPercent;
        setZoom(newPercent);
        const rect = stage.getBoundingClientRect();
        const midX=(pts[0].x+pts[1].x)/2;
        const midY=(pts[0].y+pts[1].y)/2;
        const midContentX = midX - rect.left + stage.scrollLeft;
        const midContentY = midY - rect.top + stage.scrollTop;
        const ratio = state.zoom / oldZoom;
        stage.scrollLeft = midContentX * ratio - (midX - rect.left);
        stage.scrollTop  = midContentY * ratio - (midY - rect.top);
      }
      state.lastPinchDist = dist;
    }
  });
  const clearPtr = e=>{ state.pointers.delete(e.pointerId); if(state.pointers.size<2) state.lastPinchDist=null; };
  overlay.addEventListener('pointerup', clearPtr);
  overlay.addEventListener('pointercancel', clearPtr);

  // Exponer utilidades al ámbito global para la UI
  window.manualEditor = {
    alignSelection,
    distributeSelection,
    duplicateSelection,
    deleteSelected,
    deleteSelection: deleteSelected,
    undo,
    redo,
  };

})();

