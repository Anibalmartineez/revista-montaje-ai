/**
 * Editor manual — fit width + zoom + NaN fix + límites de arrastre.
 */
(function () {
  const stage    = document.getElementById('manual-stage');
  const viewport = document.getElementById('viewport');
  const img      = document.getElementById('preview-bg');
  const overlay  = document.getElementById('overlay');

  const btnMode  = document.getElementById('btn-manual-mode');
  const btnApply = document.getElementById('btn-manual-apply');
  const btnGen   = document.getElementById('btn-manual-generate');

  const gridInput = document.getElementById('grid_mm');
  const snapChk   = document.getElementById('snap_on');
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
    selectedId: null,
    drag: null,
  };

  const mmToPx = (mm) => mm * state.baseScale * state.zoom;
  const pxToMm = (px) => px / (state.baseScale * state.zoom);

  // Conversión BL <-> TL (top-left para pintar)
  const blToTl = (x_bl, y_bl, h_total) => ({ x: x_bl, y: state.sheet.h - y_bl - h_total });
  const tlToBl = (x_tl, y_tl, h_total) => ({ x: x_tl, y: state.sheet.h - y_tl - h_total });

  // Construcción de cajas desde positions normalizadas
  function buildBoxes(positions) {
    return (positions || []).map((p, i) => {
      const rot = !!(p.rotado || p.rot);
      const wT  = toNum(p.w_mm, 0), hT = toNum(p.h_mm, 0);
      const W   = wT + 2*state.sangrado;
      const H   = hT + 2*state.sangrado;
      const tl  = blToTl(toNum(p.x_mm,0), toNum(p.y_mm,0), H);
      return {
        id: i,
        archivo: p.archivo ?? null,
        file_idx: Number.isFinite(p.file_idx) ? p.file_idx : i,
        rot,
        w_trim_mm: wT,
        h_trim_mm: hT,
        total_w_mm: rot ? H : W,   // al rotar intercambiamos percepción de W/H
        total_h_mm: rot ? W : H,
        x_tl_mm: tl.x,
        y_tl_mm: tl.y,
      };
    });
  }

  // Escalado base: encajar ancho de la imagen al ancho visible
  function syncBaseScale() {
    const visibleW = img.clientWidth || img.getBoundingClientRect().width || img.naturalWidth || 1;
    state.baseScale = visibleW / (state.sheet.w || 1);
    overlay.width  = Math.round(visibleW);
    overlay.height = Math.round(state.sheet.h * state.baseScale);
  }

  // Zoom con CSS transform (escala el viewport completo)
  function setZoom(percent) {
    const z = Math.max(0.1, Math.min(2.0, percent / 100));
    state.zoom = z;
    viewport.style.transform = `scale(${state.zoom})`;
    if (zoomLabel) zoomLabel.textContent = `${Math.round(percent)}%`;
    repaint();
  }

  function fitToWidth() {
    setZoom(100);
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

  function drawBoxes() {
    for (const b of state.boxes) {
      const x = mmToPx(b.x_tl_mm), y = mmToPx(b.y_tl_mm);
      const w = mmToPx(b.total_w_mm), h = mmToPx(b.total_h_mm);

      ctx.save();
      ctx.fillStyle = 'rgba(0,0,0,0.04)'; ctx.fillRect(x+2, y+2, w, h);
      const sel = (state.selectedId === b.id);
      ctx.lineWidth = sel ? 2 : 1;
      ctx.strokeStyle = sel ? '#0ea5e9' : '#111';
      ctx.fillStyle = 'rgba(14,165,233,0.08)';
      ctx.fillRect(x, y, w, h); ctx.strokeRect(x, y, w, h);

      // Área trim (interior)
      const trimX = x + mmToPx(state.sangrado);
      const trimY = y + mmToPx(state.sangrado);
      const trimW = mmToPx(b.w_trim_mm);
      const trimH = mmToPx(b.h_trim_mm);
      ctx.setLineDash([4,3]); ctx.strokeStyle='rgba(0,0,0,0.6)';
      ctx.strokeRect(trimX, trimY, trimW, trimH); ctx.setLineDash([]);

      ctx.fillStyle = '#111'; ctx.font = '12px sans-serif';
      const label = (b.archivo ? b.archivo.split('/').pop() : `PDF ${b.file_idx+1}`) + (b.rot ? ' • R90' : '');
      ctx.fillText(label, x + 6, y + 16);
      ctx.restore();
    }
  }

  function repaint() {
    ctx.clearRect(0,0,overlay.width, overlay.height);
    if (snapChk?.checked) drawGrid();
    drawBoxes();
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

  overlay.addEventListener('mousemove', (e) => {
    const r = overlay.getBoundingClientRect();
    const px = e.clientX - r.left, py = e.clientY - r.top;
    const mmX = pxToMm(px), mmY = pxToMm(py);
    if (cursorMM && Number.isFinite(mmX) && Number.isFinite(mmY)) {
      cursorMM.textContent = `${mmX.toFixed(1)} , ${mmY.toFixed(1)} mm`;
    }

    if (!state.drag) return;
    const b = state.boxes.find(x => x.id === state.drag.id);
    if (!b) return;

    let nx = state.drag.startTl.x + pxToMm(px - state.drag.startPx.x);
    let ny = state.drag.startTl.y + pxToMm(py - state.drag.startPx.y);

    if (snapChk?.checked) {
      const g = Math.max(0.1, toNum(gridInput.value, 1));
      nx = Math.round(nx / g) * g;
      ny = Math.round(ny / g) * g;
    }

    // clamp a bordes
    nx = Math.max(0, Math.min(nx, state.sheet.w - b.total_w_mm));
    ny = Math.max(0, Math.min(ny, state.sheet.h - b.total_h_mm));

    b.x_tl_mm = nx; b.y_tl_mm = ny;
    repaint();
  });

  overlay.addEventListener('mousedown', (e) => {
    const r = overlay.getBoundingClientRect();
    const px = e.clientX - r.left, py = e.clientY - r.top;
    const id = hitTest(px, py);
    state.selectedId = id; repaint();

    if (id != null) {
      const b = state.boxes.find(x => x.id === id);
      state.drag = {
        id,
        startPx: { x:px, y:py },
        startTl: { x:b.x_tl_mm, y:b.y_tl_mm },
      };
    }
  });

  window.addEventListener('mouseup', () => { state.drag = null; });

  window.addEventListener('keydown', (e) => {
    if (!state.selectedId && state.selectedId !== 0) return;
    const b = state.boxes.find(x => x.id === state.selectedId);
    if (!b) return;
    if (e.key.toLowerCase() === 'r') {
      b.rot = !b.rot;
      // intercambiar trim y totales
      [b.w_trim_mm, b.h_trim_mm] = [b.h_trim_mm, b.w_trim_mm];
      [b.total_w_mm, b.total_h_mm] = [b.total_h_mm, b.total_w_mm];
      // re-clamp
      b.x_tl_mm = Math.min(b.x_tl_mm, state.sheet.w - b.total_w_mm);
      b.y_tl_mm = Math.min(b.y_tl_mm, state.sheet.h - b.total_h_mm);
      repaint();
    }
  });

  function buildPayload() {
    const posiciones = state.boxes.map(b => {
      const bl = tlToBl(b.x_tl_mm, b.y_tl_mm, b.total_h_mm);
      return {
        file_idx: b.file_idx,
        x_mm: Number(bl.x.toFixed(3)),
        y_mm: Number(bl.y.toFixed(3)),
        w_mm: Number(b.w_trim_mm.toFixed(3)),
        h_mm: Number(b.h_trim_mm.toFixed(3)),
        rot: !!b.rot
      };
    });
    return { sheet: { w_mm: state.sheet.w, h_mm: state.sheet.h }, sangrado_mm: state.sangrado, posiciones };
  }

  btnApply?.addEventListener('click', () => {
    const payload = buildPayload();
    if (manualJson) manualJson.value = JSON.stringify(payload);
    fetch('/api/manual/preview', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify(payload)
    }).then(r=>r.json()).then(data=>{
      if (data.preview_url) {
        img.src = data.preview_url;
        // recarga posiciones para seguir editando
        initFromData({ sheet_mm:data.sheet_mm, posiciones:data.positions, sangrado_mm: state.sangrado });
      }
    }).catch(console.error);
  });

  btnGen?.addEventListener('click', () => {
    const payload = buildPayload();
    fetch('/api/manual/impose', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify(payload)
    }).then(r=>r.json()).then(resp=>{
      if (resp.pdf_url) window.location.href = resp.pdf_url;
      else alert('No se pudo generar el PDF manual.');
    }).catch(console.error);
  });

  function initFromData(opts) {
    state.sheet = { w: toNum(opts?.sheet_mm?.w, 0), h: toNum(opts?.sheet_mm?.h, 0) };
    state.sangrado = toNum(opts?.sangrado_mm, state.sangrado);
    state.boxes = buildBoxes(Array.isArray(opts?.positions) ? opts.positions : []);
    // (re)calcular escala base y dibujar
    if (img.complete) {
      syncBaseScale(); setZoom(toNum(zoomRange?.value, 100)); repaint();
    } else {
      img.addEventListener('load', () => { syncBaseScale(); setZoom(toNum(zoomRange?.value, 100)); repaint(); }, { once:true });
    }
  }

  // Expuesto para el template
  window.manualEditorLoad = function(opts) {
    if (opts?.preview_url) img.src = opts.preview_url;
    initFromData({ sheet_mm:opts?.sheet_mm, posiciones:opts?.positions, sangrado_mm:opts?.sangrado_mm });
  };

  // Toggle de panel
  btnMode?.addEventListener('click', () => {
    const show = (document.getElementById('manual-editor').style.display !== 'block');
    document.getElementById('manual-editor').style.display = show ? 'block' : 'none';
    if (show) { syncBaseScale(); setZoom(toNum(zoomRange?.value, 100)); repaint(); }
  });

  // Responder a resize del contenedor
  const ro = new ResizeObserver(() => { syncBaseScale(); repaint(); });
  ro.observe(stage);

  // Zoom UI
  zoomRange?.addEventListener('input', () => setZoom(toNum(zoomRange.value, 100)));
  fitWidth?.addEventListener('click', fitToWidth);
  fitPage?.addEventListener('click', fitToPage);
})();
