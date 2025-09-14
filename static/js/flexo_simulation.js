const DEBUG = new URLSearchParams(location.search).has('debug');
document.addEventListener('DOMContentLoaded', initSim);

function initSim() {
  if (DEBUG) console.debug('initSim');
  inicializarRevisionBasica();
  inicializarSimulacionAvanzada();
  inicializarModalSimulacion();
}

function inicializarRevisionBasica() {
  const form = document.querySelector('form[action="/revision"]');
  if (!form) return;
  form.addEventListener('submit', (e) => {
    // El formulario solo necesita enviar el PDF y el material.
    // Se deja que el navegador maneje la validación básica.
  });
}

function calcularTransmisionTinta({ bcm, eficiencia, cobertura, ancho, velocidad, paso }) {
  const paso_m = paso / 1000;
  const volumenPorVuelta = bcm * eficiencia * cobertura * ancho * paso_m;
  const vueltasPorMin = paso_m > 0 ? velocidad / paso_m : 0;
  const mlPorMin = volumenPorVuelta * vueltasPorMin;
  return parseFloat(mlPorMin.toFixed(2));
}

function obtenerCobertura(datos) {
  const c = datos.cobertura || {};
  return (c.C + c.M + c.Y + c.K) / 400 || 0;
}

function inicializarSimulacionAvanzada() {
  const canvas = document.getElementById('sim-canvas');
  const ctx = canvas ? canvas.getContext('2d') : null;
  const lpi = document.getElementById('lpi_slider');
  const bcm = document.getElementById('bcm_slider');
  const vel = document.getElementById('vel_slider');
  const cob = document.getElementById('cov_slider');
  const lpiVal = document.getElementById('lpi_val');
  const bcmVal = document.getElementById('bcm_val');
  const velVal = document.getElementById('vel_val');
  const cobVal = document.getElementById('cov_val');
  const resultado = document.getElementById('sim-ml');
  const saveBtn = document.getElementById('sim-save');
  const debugEl = document.getElementById('sim-debug');
  if (DEBUG && debugEl) debugEl.style.display = 'block';
  if (!canvas || !ctx || !lpi || !bcm || !vel || !cob || !resultado || !lpiVal || !bcmVal || !velVal || !cobVal) {
    if (debugEl) debugEl.textContent = 'Elementos de la simulación incompletos';
    if (DEBUG) console.warn('Elementos de la simulación incompletos');
    return;
  }
  if (DEBUG) console.debug('inicializarSimulacionAvanzada');

  const datos = window.diagnosticoFlexo || {};
  lpi.value = datos.lpi ?? 120;
  bcm.value = datos.bcm ?? 2.0;
  vel.value = datos.velocidad ?? datos.velocidad_impresion ?? 150;
  cob.value = datos.cobertura_estimada ?? Math.round(obtenerCobertura(datos) * 100) || 25;
  const paso = datos.paso_cilindro ?? datos.paso ?? 330;
  const eficiencia = datos.eficiencia || 0.30;
  const ancho = datos.ancho || 0.50;

  const img = new Image();
  img.crossOrigin = 'anonymous';
  const baseImg = document.getElementById('imagen-diagnostico');
  if (baseImg && baseImg.src) {
    img.onload = () => { if (DEBUG) console.debug('imagen base cargada'); renderSimulation(); };
    img.onerror = () => { if (DEBUG) console.debug('imagen base falló'); renderSimulation(); };
    img.src = baseImg.src;
  }

  function actualizarValores() {
    lpiVal.textContent = `${lpi.value} lpi`;
    bcmVal.textContent = `${bcm.value} cm³/m²`;
    velVal.textContent = `${vel.value} m/min`;
    cobVal.textContent = `${cob.value} %`;
  }

  function updateDebug(err) {
    if (!DEBUG || !debugEl) return;
    const dpr = window.devicePixelRatio || 1;
    debugEl.textContent = `css:${canvas.clientWidth}x${canvas.clientHeight} real:${canvas.width}x${canvas.height} DPR:${dpr}`;
    debugEl.textContent += `\nLPI:${lpi.value} BCM:${bcm.value} Vel:${vel.value} Cob:${cob.value}`;
    if (err) debugEl.textContent += `\nError: ${err.message}`;
  }

  function drawBasePattern() {
    ctx.fillStyle = '#ccc';
    for (let x = 0; x < canvas.width; x += 25) {
      for (let y = 0; y < canvas.height; y += 25) {
        ctx.fillRect(x, y, 1, 1);
      }
    }
  }

  function renderSimulation() {
    try {
      console.log('renderSimulation', {
        lpi: lpi.value,
        bcm: bcm.value,
        vel: vel.value,
        cob: cob.value,
      });
      if (DEBUG) console.debug('render start');
      if (canvas.width === 0 || canvas.height === 0) {
        if (DEBUG) console.warn('canvas 0x0, forzando resize');
        resizeCanvas();
      }
      actualizarValores();
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const hasImg = img && img.complete && img.naturalWidth > 0;
      if (hasImg) {
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      } else {
        drawBasePattern();
      }

      if (window.advertencias) {
        const colores = {
          texto_pequeno: 'red',
          trama_debil: 'purple',
          imagen_baja: 'orange',
          overprint: 'blue',
          sin_sangrado: 'darkgreen',
        };
        window.advertencias.forEach(a => {
          const box = a.bbox || a.box;
          if (!box) return;
          const x0 = box[0];
          const y0 = box[1];
          const w = box[2] - box[0];
          const h = box[3] - box[1];
          ctx.strokeStyle = colores[a.tipo] || 'red';
          ctx.lineWidth = 2;
          ctx.strokeRect(x0, y0, w, h);
        });
      }

      const valLpi = Number(lpi.value) || 0;
      const valBcm = Number(bcm.value) || 0;
      const valVel = Number(vel.value) || 0;
      const valCob = Number(cob.value) || 0;

      const spacing = Math.max(2, (600 / Math.max(valLpi, 1)) * 4);
      const radio = Math.max(1, spacing / 2);
      const alpha = Math.min(1, Math.max(0.05, valBcm / 10));
      const blur = (valVel / 500) * 2;
      const jitter = (valVel / 500) * spacing * 0.5;
      ctx.filter = blur > 0 ? `blur(${blur}px)` : 'none';

      function dibujarCapa(offsetX = 0, offsetY = 0, prob = 1) {
        for (let y = 0; y < canvas.height; y += spacing) {
          for (let x = 0; x < canvas.width; x += spacing) {
            if (Math.random() > prob) continue;
            const dx = x + offsetX + (Math.random() * 2 - 1) * jitter;
            const dy = y + offsetY + (Math.random() * 2 - 1) * jitter;
            ctx.beginPath();
            ctx.fillStyle = `rgba(0,0,0,${alpha})`;
            ctx.arc(dx, dy, radio, 0, Math.PI * 2);
            ctx.fill();
          }
        }
      }

      const cobertura = valCob;
      const probBase = Math.min(cobertura, 100) / 100;
      dibujarCapa(0, 0, probBase);
      if (cobertura > 100) {
        const probExtra = Math.min((cobertura - 100) / 100, 1);
        dibujarCapa(spacing / 2, spacing / 2, probExtra);
      }

      ctx.filter = 'none';

      const params = {
        bcm: valBcm,
        paso,
        velocidad: valVel,
        eficiencia,
        cobertura: valCob / 100,
        ancho,
      };
      const mlMin = calcularTransmisionTinta(params);
      const paso_m = params.paso / 1000;
      const repeticiones = paso_m > 0 ? params.velocidad / paso_m : 0;
      resultado.textContent = `ml/min: ${mlMin} | rep/min: ${repeticiones.toFixed(1)}`;
      if (DEBUG) console.debug('render end');
      updateDebug();
    } catch (err) {
      if (DEBUG) console.error(err);
      updateDebug(err);
    }
  }

  function resizeCanvas() {
    if (DEBUG) console.debug('resizeCanvas');
    const DPR = window.devicePixelRatio || 1;
    const cssW = canvas.clientWidth || 800;
    const cssH = Math.round((cssW * 9) / 16);
    canvas.width = Math.floor(Math.max(cssW, 600) * DPR);
    canvas.height = Math.floor(Math.max(cssH, 300) * DPR);
    canvas.style.width = cssW + 'px';
    canvas.style.height = cssH + 'px';
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
    updateDebug();
    renderSimulation();
  }

  function savePNG() {
    if (DEBUG) console.debug('savePNG');
    canvas.toBlob(async blob => {
      try {
        if (!blob) throw new Error('blob nulo');
        const formData = new FormData();
        formData.append('image', blob, `sim_${window.revisionId || 'resultado'}.png`);
        const resp = await fetch(`/guardar_simulacion/${window.revisionId}`, {
          method: 'POST',
          body: formData,
        });
        if (!resp.ok) throw new Error('respuesta no OK');
        const data = await resp.json();
        if (data.url) {
          const link = document.createElement('a');
          link.href = data.url;
          link.download = data.url.split('/').pop();
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
        }
      } catch (err) {
        if (DEBUG) console.error('savePNG error', err);
      }
    });
  }

  [lpi, bcm, vel, cob].forEach(el => {
    el.addEventListener('input', () => {
      console.log('slider change', el.id, el.value);
      renderSimulation();
    });
  });
  if (DEBUG) console.debug('listeners attached');
  let resizeTimeout;
  const onResize = () => {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(resizeCanvas, 150);
  };
  window.addEventListener('resize', onResize);
  window.addEventListener('orientationchange', onResize);
  resizeCanvas();
  if (saveBtn) {
    saveBtn.addEventListener('click', savePNG);
  }
}

function inicializarModalSimulacion() {
  const btn = document.getElementById('sim-view-large');
  const modal = document.getElementById('sim-modal');
  const modalImg = document.getElementById('sim-modal-img');
  const closeBtn = document.getElementById('sim-close');
  const canvas = document.getElementById('sim-canvas');
  if (!btn || !modal || !modalImg || !closeBtn || !canvas) return;

  let scale = 1;
  let lastDist = null;

  btn.addEventListener('click', () => {
    modalImg.src = canvas.toDataURL('image/png');
    scale = 1;
    modalImg.style.transform = 'scale(1)';
    modal.style.display = 'flex';
  });

  function cerrar() {
    modal.style.display = 'none';
  }

  closeBtn.addEventListener('click', cerrar);
  modal.addEventListener('click', e => { if (e.target === modal) cerrar(); });

  modalImg.addEventListener('wheel', e => {
    e.preventDefault();
    scale += e.deltaY * -0.001;
    scale = Math.min(Math.max(1, scale), 5);
    modalImg.style.transform = `scale(${scale})`;
  });

  modalImg.addEventListener('touchstart', e => {
    if (e.touches.length === 2) {
      e.preventDefault();
      lastDist = dist(e.touches[0], e.touches[1]);
    }
  }, { passive: false });

  modalImg.addEventListener('touchmove', e => {
    if (e.touches.length === 2 && lastDist) {
      e.preventDefault();
      const newDist = dist(e.touches[0], e.touches[1]);
      const factor = newDist / lastDist;
      scale = Math.min(Math.max(1, scale * factor), 5);
      lastDist = newDist;
      modalImg.style.transform = `scale(${scale})`;
    }
  }, { passive: false });

  function dist(t1, t2) {
    return Math.hypot(t1.clientX - t2.clientX, t1.clientY - t2.clientY);
  }
}
