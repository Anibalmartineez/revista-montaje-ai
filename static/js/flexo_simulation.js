document.addEventListener('DOMContentLoaded', () => {
  inicializarRevisionBasica();
  inicializarSimulacionAvanzada();
  inicializarModalSimulacion();
});

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
  const lpi = document.getElementById('sim-lpi');
  const bcm = document.getElementById('sim-bcm');
  const vel = document.getElementById('sim-velocidad');
  const cob = document.getElementById('sim-cobertura');
  const lpiVal = document.getElementById('sim-lpi-val');
  const bcmVal = document.getElementById('sim-bcm-val');
  const velVal = document.getElementById('sim-vel-val');
  const cobVal = document.getElementById('sim-cobertura-val');
  const canvas = document.getElementById('sim-canvas');
  const resultado = document.getElementById('sim-ml');
  const outImg = document.getElementById('sim-output');
  if (!lpi || !bcm || !vel || !cob || !canvas || !resultado || !lpiVal || !bcmVal || !velVal || !cobVal || !outImg) {
    return;
  }

  const datos = window.diagnosticoFlexo || {};
  lpi.value = datos.lpi ?? 360;
  bcm.value = datos.bcm ?? 4;
  vel.value = datos.velocidad ?? datos.velocidad_impresion ?? 150;
  cob.value = datos.cobertura_estimada ?? Math.round(obtenerCobertura(datos) * 100) || 25;
  const paso = datos.paso_cilindro ?? datos.paso ?? 330;
  const eficiencia = datos.eficiencia || 0.30;
  const ancho = datos.ancho || 0.50;
  const ctx = canvas.getContext('2d');
  const img = new Image();
  const baseImg = document.getElementById('imagen-diagnostico');

  function actualizarValores() {
    lpiVal.textContent = `${lpi.value} lpi`;
    bcmVal.textContent = `${bcm.value} cm³/m²`;
    velVal.textContent = `${vel.value} m/min`;
    cobVal.textContent = `${cob.value} %`;
  }

  function dibujar() {
    actualizarValores();
    if (!img.complete) return;
    canvas.width = img.width;
    canvas.height = img.height;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

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

    const valLpi = parseFloat(lpi.value);
    const spacing = Math.max(2, (600 / valLpi) * 4);
    const baseRadio = spacing / 2;
    for (let y = 0; y < canvas.height; y += spacing) {
      for (let x = 0; x < canvas.width; x += spacing) {
        ctx.beginPath();
        ctx.fillStyle = 'rgba(0,0,0,0.2)';
        ctx.arc(x, y, baseRadio, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    const params = {
      bcm: parseFloat(bcm.value),
      paso,
      velocidad: parseFloat(vel.value),
      eficiencia,
      cobertura: parseFloat(cob.value) / 100,
      ancho,
    };
    const mlMin = calcularTransmisionTinta(params);
    const paso_m = params.paso / 1000;
    const repeticiones = paso_m > 0 ? params.velocidad / paso_m : 0;
    resultado.textContent = `ml/min: ${mlMin} | rep/min: ${repeticiones.toFixed(1)}`;

    outImg.src = canvas.toDataURL('image/png');
  }

  img.onload = dibujar;
  if (baseImg) {
    img.src = baseImg.src;
  }

  [lpi, bcm, vel, cob].forEach(el => el.addEventListener('input', dibujar));
  actualizarValores();
  if (img.complete) dibujar();
}

function inicializarModalSimulacion() {
  const btn = document.getElementById('sim-view-large');
  const modal = document.getElementById('sim-modal');
  const modalImg = document.getElementById('sim-modal-img');
  const closeBtn = document.getElementById('sim-close');
  const outImg = document.getElementById('sim-output');
  if (!btn || !modal || !modalImg || !closeBtn || !outImg) return;

  let scale = 1;
  let lastDist = null;

  btn.addEventListener('click', () => {
    modalImg.src = outImg.src;
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
