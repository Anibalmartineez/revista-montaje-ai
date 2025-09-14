const DEBUG = false; // Cambiar a true para habilitar logs detallados
document.addEventListener('DOMContentLoaded', () => {
  if (DEBUG) console.log('[SIM] init');
  initSim();
});

function initSim() {
  if (DEBUG) console.debug('[SIM] initSim');
  inicializarRevisionBasica();
  inicializarSimulacionAvanzada();
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
  if (DEBUG) {
    console.log('[SIM] inicializarSimulacionAvanzada');
    console.debug('inicializarSimulacionAvanzada');
  }

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
  const diagUrl = window.diagImg;
  if (diagUrl) {
    img.onload = () => {
      if (DEBUG) console.log('[SIM] imagen base cargada');
      renderSimulation();
    };
    img.onerror = () => {
      if (DEBUG) console.warn('[SIM] error cargando imagen base');
      renderSimulation();
    };
    img.src = diagUrl;
    if (img.complete && img.naturalWidth > 0) {
      if (DEBUG) console.log('[SIM] imagen base ya disponible');
      renderSimulation();
    }
  } else {
    renderSimulation();
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
    ctx.fillStyle = '#eef7ff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.strokeStyle = '#ccc';
    for (let x = 0; x < canvas.width; x += 25) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, canvas.height);
      ctx.stroke();
    }
    for (let y = 0; y < canvas.height; y += 25) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(canvas.width, y);
      ctx.stroke();
    }
  }

  function renderSimulation() {
    try {
      if (DEBUG) console.log('[SIM] render', {
        lpi: lpi.value,
        bcm: bcm.value,
        vel: vel.value,
        cob: cob.value,
      });
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
    if (DEBUG) console.debug('[SIM] resizeCanvas');
    const DPR = window.devicePixelRatio || 1;
    const parent = canvas.parentElement;
    const cssW = parent ? parent.clientWidth : canvas.clientWidth || 300;
    const cssH = Math.round((cssW * 9) / 16);
    canvas.width = Math.max(cssW, 300) * DPR;
    canvas.height = Math.max(cssH, 150) * DPR;
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
        const resp = await fetch(`/simulacion/exportar/${window.revisionId}`, {
          method: 'POST',
          body: formData,
        });
        if (!resp.ok) throw new Error('respuesta no OK');
        const data = await resp.json();
        if (data.url) {
          const link = document.getElementById('sim-view');
          if (link) link.href = data.url;
        }
      } catch (err) {
        if (DEBUG) console.error('[SIM] savePNG error', err);
      }
    });
  }

  [lpi, bcm, vel, cob].forEach(el => {
    el.addEventListener('input', () => {
      if (DEBUG) console.log('[SIM] slider', el.id, el.value);
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
