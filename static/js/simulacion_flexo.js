document.addEventListener('DOMContentLoaded', () => {
  renderizarDiagnostico();
  inicializarSimulacionViva();
});

function calcularTransmisionTinta({ bcm, eficiencia, cobertura, ancho, velocidad }) {
  const mlPorMin = bcm * eficiencia * cobertura * ancho * velocidad;
  return parseFloat(mlPorMin.toFixed(2));
}

function obtenerCobertura(datos) {
  const c = datos.cobertura || {};
  return (c.C + c.M + c.Y + c.K) / 400 || 0;
}

function renderizarDiagnostico() {
  const datos = window.diagnosticoFlexo || {};
  const cobertura = obtenerCobertura(datos);
  const params = {
    bcm: datos.bcm || 4,
    eficiencia: datos.eficiencia || 0.3,
    cobertura,
    ancho: datos.ancho || 0.5,
    velocidad: datos.velocidad || 150,
  };
  const mlMin = calcularTransmisionTinta(params);
  const sustrato = datos.material || 'papel';
  const cargaObjetivo = sustrato === 'film' ? 4.0 : 3.0;
  const ideal = parseFloat((cargaObjetivo * params.ancho * params.velocidad).toFixed(2));
  const ctx = document.getElementById('tinta-grafico').getContext('2d');
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: ['Calculado', 'Ideal'],
      datasets: [
        {
          label: 'ml/min',
          backgroundColor: ['#36a2eb', '#4caf50'],
          data: [mlMin, ideal],
        },
      ],
    },
    options: {
      responsive: false,
      scales: {
        y: { beginAtZero: true, max: Math.max(mlMin, ideal) * 1.2 },
      },
    },
  });
  const detalles = document.getElementById('tinta-detalles');
  detalles.innerHTML =
    `BCM: ${params.bcm} ml/m²<br>` +
    `Eficiencia: ${params.eficiencia}<br>` +
    `Cobertura: ${cobertura.toFixed(2)}<br>` +
    `Ancho: ${params.ancho} m<br>` +
    `Velocidad: ${params.velocidad} m/min<br>` +
    `<strong>${mlMin} ml/min</strong> (ideal ${ideal} ml/min)`;
}

function inicializarSimulacionViva() {
  const btn = document.getElementById('btn-simulacion-flexo');
  const modal = document.getElementById('simulacion-en-vivo');
  const cerrar = document.getElementById('cerrar-simulacion');
  const lpi = document.getElementById('sim-lpi');
  const bcm = document.getElementById('sim-bcm');
  const vel = document.getElementById('sim-velocidad');
  const eficiencia = document.getElementById('sim-eficiencia');
  const ancho = document.getElementById('sim-ancho');
  const canvas = document.getElementById('sim-canvas');
  const resultado = document.getElementById('sim-ml');
  if (
    !btn ||
    !modal ||
    !cerrar ||
    !lpi ||
    !bcm ||
    !vel ||
    !eficiencia ||
    !ancho ||
    !canvas ||
    !resultado
  ) {
    return;
  }

  const datos = window.diagnosticoFlexo || {};
  const coberturaBase = obtenerCobertura(datos);
  const ctx = canvas.getContext('2d');
  const img = new Image();
  const baseImg = document.getElementById('imagen-diagnostico');

  function dibujar() {
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
      eficiencia: parseFloat(eficiencia.value),
      cobertura: coberturaBase,
      ancho: parseFloat(ancho.value),
      velocidad: parseFloat(vel.value),
    };
    const mlMin = calcularTransmisionTinta(params);
    resultado.textContent = `ml/min: ${mlMin}`;
  }

  img.onload = dibujar;
  if (baseImg) {
    img.src = baseImg.src;
  }

  [lpi, bcm, vel, eficiencia, ancho].forEach(el => el.addEventListener('input', dibujar));

  btn.addEventListener('click', () => {
    modal.classList.add('abierto');
    if (img.complete) dibujar();
  });
  cerrar.addEventListener('click', () => modal.classList.remove('abierto'));
}

