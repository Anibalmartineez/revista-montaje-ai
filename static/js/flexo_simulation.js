const DEBUG = false;

document.addEventListener('DOMContentLoaded', () => {
  if (DEBUG) console.log('[SIM] DOM ready');

  const canvas = document.getElementById('sim-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

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

  const baseUrl = canvas.dataset.simImg;
  const img = new Image();
  img.crossOrigin = 'anonymous';
  let baseReady = false;

  img.onload = () => {
    baseReady = true;
    if (DEBUG) console.log('[SIM] imagen base cargada');
    resize();
  };
  img.onerror = () => {
    baseReady = false;
    if (DEBUG) console.warn('[SIM] error cargando imagen base');
    resize();
  };
  if (baseUrl) {
    img.src = baseUrl + '?cb=' + Date.now();
  } else {
    resize();
  }

  function updateLabels() {
    if (lpiVal) lpiVal.textContent = `${lpi.value} lpi`;
    if (bcmVal) bcmVal.textContent = `${bcm.value} cm³/m²`;
    if (pasoVal) pasoVal.textContent = `${paso.value} mm`;
    if (velVal) velVal.textContent = `${vel.value} m/min`;
    if (cobVal) cobVal.textContent = `${cob.value} %`;
  }

  function drawFallback() {
    ctx.fillStyle = '#fff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#ccc';
    const spacing = 20;
    for (let y = 0; y < canvas.height; y += spacing) {
      for (let x = 0; x < canvas.width; x += spacing) {
        ctx.beginPath();
        ctx.arc(x + spacing / 2, y + spacing / 2, 1.5, 0, Math.PI * 2);
        ctx.fill();
      }
    }
  }

  function render() {
    if (DEBUG) console.log('[SIM] render');
    updateLabels();

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (baseReady) {
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    } else {
      drawFallback();
    }

    const l = Number(lpi.value) || 0;
    const b = Number(bcm.value) || 0;
    const p = Number(paso.value) || 0;
    const v = Number(vel.value) || 0;
    const c = Number(cob.value) || 0;

    const spacing = Math.max(2, (600 / Math.max(l, 1)) * 4);
    const alpha = Math.min(1, Math.max(0.05, (c / 100) * (b / 10)));
    const blur = (v / 500) * 2;
    const offset = (p / 1000) * spacing;

    ctx.filter = blur > 0 ? `blur(${blur}px)` : 'none';
    for (let y = offset; y < canvas.height; y += spacing) {
      for (let x = offset; x < canvas.width; x += spacing) {
        ctx.beginPath();
        ctx.fillStyle = `rgba(0,0,0,${alpha})`;
        ctx.arc(x, y, spacing / 2, 0, Math.PI * 2);
        ctx.fill();
      }
    }
    ctx.filter = 'none';
  }

  let rafId = null;
  let debounceId = null;
  function scheduleRender() {
    clearTimeout(debounceId);
    debounceId = setTimeout(() => {
      cancelAnimationFrame(rafId);
      rafId = requestAnimationFrame(render);
    }, 120);
  }

  [lpi, bcm, paso, vel, cob].forEach((el) => {
    if (!el) return;
    el.addEventListener('input', scheduleRender);
    el.addEventListener('change', scheduleRender);
  });

  function resize() {
    const rect = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    render();
  }

  window.addEventListener('resize', () => {
    resize();
  });

  const saveBtn = document.getElementById('sim-save');
  const viewLink = document.getElementById('sim-view');
  if (saveBtn) {
    saveBtn.addEventListener('click', () => {
      if (DEBUG) console.log('[SIM] export');
      canvas.toBlob(async (blob) => {
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

