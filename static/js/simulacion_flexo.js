document.addEventListener('DOMContentLoaded', () => {
  inicializarSimulacionAvanzada();
});

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
  const paso = document.getElementById('sim-paso');
  const vel = document.getElementById('sim-velocidad');
  const lpiVal = document.getElementById('sim-lpi-val');
  const bcmVal = document.getElementById('sim-bcm-val');
  const pasoVal = document.getElementById('sim-paso-val');
  const velVal = document.getElementById('sim-vel-val');
  const canvas = document.getElementById('sim-canvas');
  const resultado = document.getElementById('sim-ml');
  if (!lpi || !bcm || !paso || !vel || !canvas || !resultado || !lpiVal || !bcmVal || !pasoVal || !velVal) {
    return;
  }

  const datos = window.diagnosticoFlexo || {};
  lpi.value = datos.anilox_lpi ?? datos.lpi ?? lpi.value;
  bcm.value = datos.anilox_bcm ?? datos.bcm ?? bcm.value;
  paso.value = datos.paso_cilindro ?? datos.paso ?? paso.value;
  vel.value = datos.velocidad ?? datos.velocidad_impresion ?? vel.value;
  const coberturaBase = obtenerCobertura(datos);
  const eficiencia = datos.eficiencia || 0.30;
  const ancho = datos.ancho || 0.50;
  const ctx = canvas.getContext('2d');
  const img = new Image();
  const baseImg = document.getElementById('imagen-diagnostico');

  function actualizarValores() {
    lpiVal.textContent = `${lpi.value} lpi`;
    bcmVal.textContent = `${bcm.value} cm³/m²`;
    pasoVal.textContent = `${paso.value} mm`;
    velVal.textContent = `${vel.value} m/min`;
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
      paso: parseFloat(paso.value),
      velocidad: parseFloat(vel.value),
      eficiencia,
      cobertura: coberturaBase,
      ancho,
    };
    const mlMin = calcularTransmisionTinta(params);
    const paso_m = params.paso / 1000;
    const repeticiones = paso_m > 0 ? params.velocidad / paso_m : 0;
    resultado.textContent = `ml/min: ${mlMin} | rep/min: ${repeticiones.toFixed(1)}`;
  }

  img.onload = dibujar;
  if (baseImg) {
    img.src = baseImg.src;
  }

  [lpi, bcm, paso, vel].forEach(el => el.addEventListener('input', dibujar));
  actualizarValores();
  if (img.complete) dibujar();
}
