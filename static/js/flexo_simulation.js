const DEBUG = false;

document.addEventListener('DOMContentLoaded', () => {
  if (DEBUG) console.log('[SIM] DOM ready');

  const canvas = document.getElementById('sim-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  const lpi = document.getElementById('lpi');
  const bcm = document.getElementById('bcm');
  const paso = document.getElementById('paso');
  const vel = document.getElementById('vel');
  const cob = document.getElementById('cov');

  const lpiVal = document.getElementById('lpi-val');
  const bcmVal = document.getElementById('bcm-val');
  const pasoVal = document.getElementById('paso-val');
  const velVal = document.getElementById('vel-val');
  const cobVal = document.getElementById('cov-val');

  const viewLink = document.getElementById('sim-view');
  const saveBtn = document.getElementById('sim-save');

  const diagnostico = window.diagnosticoJson || {};

  let rafId = null;
  let debounceId = null;
  let currentDpr = window.devicePixelRatio || 1;

  function asNumber(value) {
    if (value === null || value === undefined || value === '') return null;
    const num = Number(value);
    return Number.isFinite(num) ? num : null;
  }

  function clampToInputRange(num, input) {
    if (!input) return num;
    const min = asNumber(input.min);
    const max = asNumber(input.max);
    let result = num;
    if (min !== null && result < min) result = min;
    if (max !== null && result > max) result = max;
    return result;
  }

  function resolveDiagnosticoValue(keys) {
    for (const key of keys) {
      if (Object.prototype.hasOwnProperty.call(diagnostico, key)) {
        const val = diagnostico[key];
        if (val !== null && val !== undefined) {
          return val;
        }
      }
    }
    return null;
  }

  function applyInitialValues() {
    const mapping = [
      [lpi, ['anilox_lpi', 'lpi']],
      [bcm, ['anilox_bcm', 'bcm']],
      [paso, ['paso_del_cilindro', 'paso_cilindro', 'paso']],
      [vel, ['velocidad_impresion', 'velocidad']],
      [cob, ['cobertura_estimada', 'cobertura']],
    ];

    mapping.forEach(([input, keys]) => {
      if (!input) return;
      const valor = resolveDiagnosticoValue(keys);
      if (valor === null) return;
      const numerico = asNumber(valor);
      if (numerico !== null) {
        input.value = String(clampToInputRange(numerico, input));
      } else {
        input.value = valor;
      }
    });

    updateLabels();
  }

  function normalizeUrl(url) {
    if (!url) return '';
    const trimmed = String(url).trim();
    if (!trimmed) return '';
    if (/^(?:https?:|data:|blob:)/i.test(trimmed) || trimmed.startsWith('//')) {
      return trimmed;
    }
    if (trimmed.startsWith('/')) {
      return trimmed;
    }
    const clean = trimmed.replace(/^\.?\//, '');
    if (clean.startsWith('static/')) {
      return `/${clean}`;
    }
    return `/static/${clean}`;
  }

  const diagImgUrl = normalizeUrl(window.diag_img_web || canvas.dataset.simImg || '');
  const baseImage = new Image();
  baseImage.crossOrigin = 'anonymous';
  let baseReady = false;

  baseImage.onload = () => {
    baseReady = true;
    if (DEBUG) console.log('[SIM] imagen base cargada');
    render();
  };
  baseImage.onerror = () => {
    baseReady = false;
    if (DEBUG) console.warn('[SIM] error cargando imagen base');
    render();
  };
  if (diagImgUrl) {
    const cacheBusted = diagImgUrl.includes('?')
      ? `${diagImgUrl}&cb=${Date.now()}`
      : `${diagImgUrl}?cb=${Date.now()}`;
    baseImage.src = cacheBusted;
  }

  function updateLabels() {
    if (lpi && lpiVal) lpiVal.textContent = `${lpi.value} lpi`;
    if (bcm && bcmVal) bcmVal.textContent = `${bcm.value} cm³/m²`;
    if (paso && pasoVal) pasoVal.textContent = `${paso.value} mm`;
    if (vel && velVal) velVal.textContent = `${vel.value} m/min`;
    if (cob && cobVal) cobVal.textContent = `${cob.value} %`;
  }

  function drawFallback(targetCtx, width, height) {
    targetCtx.fillStyle = '#fff';
    targetCtx.fillRect(0, 0, width, height);
    targetCtx.fillStyle = '#ccc';
    const spacing = 20;
    for (let y = 0; y < height; y += spacing) {
      for (let x = 0; x < width; x += spacing) {
        targetCtx.beginPath();
        targetCtx.arc(x + spacing / 2, y + spacing / 2, 1.5, 0, Math.PI * 2);
        targetCtx.fill();
      }
    }
  }

  function drawSimulationOverlay(targetCtx, width, height) {
    const l = Number(lpi ? lpi.value : 0) || 0;
    const b = Number(bcm ? bcm.value : 0) || 0;
    const p = Number(paso ? paso.value : 0) || 0;
    const v = Number(vel ? vel.value : 0) || 0;
    const c = Number(cob ? cob.value : 0) || 0;

    const spacing = Math.max(2, (600 / Math.max(l, 1)) * 4);
    const alpha = Math.min(1, Math.max(0.05, (c / 100) * (b / 10)));
    const blur = (v / 500) * 2;
    const offset = (p / 1000) * spacing;

    targetCtx.filter = blur > 0 ? `blur(${blur}px)` : 'none';
    for (let y = offset; y < height; y += spacing) {
      for (let x = offset; x < width; x += spacing) {
        targetCtx.beginPath();
        targetCtx.fillStyle = `rgba(0,0,0,${alpha})`;
        targetCtx.arc(x, y, spacing / 2, 0, Math.PI * 2);
        targetCtx.fill();
      }
    }
    targetCtx.filter = 'none';
  }

  function render(targetCtx = ctx, targetCanvas = canvas, updateUi = true) {
    if (!targetCtx || !targetCanvas) return;
    if (DEBUG) console.log('[SIM] render');
    if (updateUi) updateLabels();

    const { width, height } = targetCanvas;
    targetCtx.clearRect(0, 0, width, height);

    if (baseReady && diagImgUrl) {
      targetCtx.drawImage(baseImage, 0, 0, width, height);
    } else {
      drawFallback(targetCtx, width, height);
    }

    drawSimulationOverlay(targetCtx, width, height);
  }

  function scheduleRender() {
    clearTimeout(debounceId);
    debounceId = setTimeout(() => {
      cancelAnimationFrame(rafId);
      rafId = requestAnimationFrame(() => render());
    }, 120);
  }

  [lpi, bcm, paso, vel, cob].forEach((el) => {
    if (!el) return;
    el.addEventListener('input', scheduleRender);
    el.addEventListener('change', scheduleRender);
  });

  applyInitialValues();

  function resize() {
    const rect = canvas.getBoundingClientRect();
    currentDpr = window.devicePixelRatio || 1;
    canvas.width = Math.max(1, rect.width * currentDpr);
    canvas.height = Math.max(1, rect.height * currentDpr);
    ctx.setTransform(currentDpr, 0, 0, currentDpr, 0, 0);
    render();
  }

  window.addEventListener('resize', resize);

  // Ajustar el lienzo desde el inicio para dibujar el diagnóstico o el patrón.
  resize();
  if (!diagImgUrl) {
    render();
  }

  if (saveBtn) {
    saveBtn.addEventListener('click', () => {
      if (DEBUG) console.log('[SIM] export');
      if (diagImgUrl && !baseReady) {
        alert('La imagen base aún se está cargando. Intentá nuevamente en unos segundos.');
        return;
      }

      const exportCanvas = document.createElement('canvas');
      exportCanvas.width = canvas.width;
      exportCanvas.height = canvas.height;
      const exportCtx = exportCanvas.getContext('2d');
      if (!exportCtx) return;
      exportCtx.setTransform(currentDpr, 0, 0, currentDpr, 0, 0);
      render(exportCtx, exportCanvas, false);

      exportCanvas.toBlob(async (blob) => {
        if (!blob) return;
        const fd = new FormData();
        fd.append('image', blob, `sim_${window.revisionId || 'resultado'}.png`);
        try {
          const resp = await fetch(`/simulacion/exportar/${window.revisionId}`, {
            method: 'POST',
            body: fd,
          });
          const data = await resp.json();
          if (data && data.url) {
            if (viewLink) viewLink.href = data.url;
            alert(`PNG generado: ${data.url}`);
          }
        } catch (err) {
          if (DEBUG) console.error('[SIM] export error', err);
        }
      });
    });
  }
});

