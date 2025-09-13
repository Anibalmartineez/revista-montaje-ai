// Simulación de impresión flexográfica dividida en bloques

document.addEventListener('DOMContentLoaded', () => {
  inicializarSimulacionReticula();
  inicializarSimulacionTinta();
});

function obtenerDatosBase() {
  const datos = window.diagnosticoFlexo || {};
  const coberturaDatos = datos.cobertura || {};
  const tac = typeof datos.tac_p95 === 'number' ? datos.tac_p95 : null;
  const cobertura = Math.min(
    1,
    Math.max(
      0,
      tac
        ? tac / 400
        : (coberturaDatos.C + coberturaDatos.M + coberturaDatos.Y + coberturaDatos.K) /
          400
    )
  );
  const sustrato = datos.material || 'papel';
  return { datos, cobertura, sustrato };
}

// --- Bloque de simulación en vivo (retícula) ---
function inicializarSimulacionReticula() {
  const btn = document.getElementById('btn-simulacion-flexo');
  const modal = document.getElementById('simulacion-en-vivo');
  const cerrar = document.getElementById('cerrar-simulacion');
  const lpi = document.getElementById('sim-lpi');
  const bcm = document.getElementById('sim-bcm');
  const vel = document.getElementById('sim-velocidad');
  const canvasTrama = document.getElementById('sim-canvas');
  if (!btn || !modal || !cerrar || !lpi || !bcm || !vel || !canvasTrama) return;

  const { datos } = obtenerDatosBase();
  const textos = datos.textos_pequenos || [];

  const canvasTextos = document.createElement('canvas');
  canvasTextos.id = 'sim-canvas-textos';
  canvasTextos.width = canvasTrama.width;
  canvasTextos.height = canvasTrama.height;
  const contenedorCanvas = document.getElementById('sim-canvas-container');
  contenedorCanvas.style.position = 'relative';
  canvasTrama.style.position = canvasTextos.style.position = 'absolute';
  canvasTrama.style.top = canvasTextos.style.top = '0';
  canvasTrama.style.left = canvasTextos.style.left = '0';
  canvasTrama.style.zIndex = '1';
  canvasTextos.style.zIndex = '2';
  contenedorCanvas.appendChild(canvasTextos);

  const ctxTrama = canvasTrama.getContext('2d');
  const ctxTextos = canvasTextos.getContext('2d');

  const img = new Image();
  const baseImg = document.getElementById('imagen-diagnostico');
  if (baseImg) {
    img.src = baseImg.src;
  }

  function dibujarTextos() {
    ctxTextos.clearRect(0, 0, canvasTextos.width, canvasTextos.height);
    textos.forEach((t, i) => {
      const tam = t.tamano || 10;
      ctxTextos.font = `${tam}px sans-serif`;
      ctxTextos.fillStyle = t.color || '#000';
      const x = 10;
      const y = (i + 1) * (tam + 4);
      ctxTextos.fillText('Texto', x, y);
    });
  }

  function dibujarTrama() {
    const valLpi = parseFloat(lpi.value);
    const valBcm = parseFloat(bcm.value);
    const valVel = parseFloat(vel.value);
    const cobertura = datos.cobertura || {};
    const promedio =
      (cobertura.C + cobertura.M + cobertura.Y + cobertura.K) / 400 || 0;
    const minTrama = (datos.trama_minima || 0) / 100;

    let umbralTrama = minTrama;
    if (valLpi > 500) {
      umbralTrama = Math.max(umbralTrama, 0.05);
    } else if (valLpi < 300) {
      umbralTrama = Math.min(umbralTrama, 0.03);
    }

    const spacing = Math.max(2, (600 / valLpi) * 4);
    const baseRadio = spacing / 2;
    const transferencia = (1 - (valVel - 50) / 250) * (0.5 + promedio);

    let ganancia = 1;
    if (valBcm >= 6) {
      ganancia += 0.15 + ((Math.min(valBcm, 8) - 6) / 2) * 0.05;
    } else if (valBcm <= 3) {
      ganancia -= 0.1;
    }
    if (valVel < 100) {
      ganancia += 0.1;
    } else if (valVel > 150 && valBcm <= 3) {
      ganancia -= 0.05;
    }

    ctxTrama.clearRect(0, 0, canvasTrama.width, canvasTrama.height);
    const off = document.createElement('canvas');
    off.width = canvasTrama.width;
    off.height = canvasTrama.height;
    const offCtx = off.getContext('2d');
    offCtx.drawImage(img, 0, 0, canvasTrama.width, canvasTrama.height);
    const data = offCtx.getImageData(0, 0, canvasTrama.width, canvasTrama.height).data;

    for (let y = 0; y < canvasTrama.height; y += spacing) {
      for (let x = 0; x < canvasTrama.width; x += spacing) {
        const px = (Math.floor(y) * canvasTrama.width + Math.floor(x)) * 4;
        const r = data[px];
        const g = data[px + 1];
        const b = data[px + 2];
        const gray = (r + g + b) / 3;
        const coberturaLocal = 1 - gray / 255;

        if (coberturaLocal < umbralTrama) {
          if (valLpi > 500) {
            continue;
          } else if (valLpi < 300) {
            const jitterX = x + (Math.random() - 0.5) * spacing * 0.3;
            const jitterY = y + (Math.random() - 0.5) * spacing * 0.3;
            const radioIrregular =
              baseRadio *
              Math.sqrt(Math.max(coberturaLocal, 0.02)) *
              (0.5 + Math.random() * 0.5) *
              ganancia;
            const alphaIrregular =
              coberturaLocal * (valBcm / 8) * transferencia * 0.5;
            ctxTrama.beginPath();
            ctxTrama.fillStyle = `rgba(0,0,0,${alphaIrregular})`;
            ctxTrama.arc(jitterX, jitterY, radioIrregular, 0, Math.PI * 2);
            ctxTrama.fill();
            continue;
          } else {
            continue;
          }
        }

        const radio = baseRadio * Math.sqrt(coberturaLocal) * ganancia;
        let alpha = coberturaLocal * (valBcm / 8) * transferencia;
        if (valLpi > 500 && coberturaLocal < 0.05) {
          alpha *= 0.1;
        }
        ctxTrama.beginPath();
        ctxTrama.fillStyle = `rgba(0,0,0,${alpha})`;
        ctxTrama.arc(x, y, radio, 0, Math.PI * 2);
        ctxTrama.fill();
      }
    }
  }

  function iniciar() {
    dibujarTrama();
    dibujarTextos();
  }

  img.onload = iniciar;
  lpi.addEventListener('input', dibujarTrama);
  bcm.addEventListener('input', dibujarTrama);
  vel.addEventListener('input', dibujarTrama);
  btn.addEventListener('click', () => modal.classList.add('abierto'));
  cerrar.addEventListener('click', () => modal.classList.remove('abierto'));
}

// --- Bloque de cálculo de transmisión de tinta ---
function inicializarSimulacionTinta() {
  const bcm = document.getElementById('tinta-bcm');
  const eficiencia = document.getElementById('tinta-eficiencia');
  const ancho = document.getElementById('tinta-ancho');
  const vel = document.getElementById('tinta-velocidad');
  const canvasGrafico = document.getElementById('tinta-grafico');
  const detalles = document.getElementById('tinta-detalles');
  if (!bcm || !eficiencia || !ancho || !vel || !canvasGrafico || !detalles) return;

  const { cobertura, sustrato } = obtenerDatosBase();
  const ctxGrafico = canvasGrafico.getContext('2d');

  let chart;
  function inicializarGrafico() {
    chart = new Chart(ctxGrafico, {
      type: 'bar',
      data: {
        labels: ['Calculado', 'Ideal'],
        datasets: [
          {
            label: 'ml/min',
            backgroundColor: ['#36a2eb', '#4caf50'],
            data: [0, 0]
          }
        ]
      },
      options: {
        responsive: false,
        scales: {
          y: {
            beginAtZero: true,
            title: { display: true, text: 'ml/min' }
          }
        }
      }
    });
  }

  function actualizarCalculo() {
    const bcmVal = parseFloat(bcm.value);
    const eficienciaVal = parseFloat(eficiencia.value);
    const anchoVal = parseFloat(ancho.value);
    const velVal = parseFloat(vel.value);
    const mlPorMin = bcmVal * eficienciaVal * cobertura * anchoVal * velVal;
    const cargaObjetivo = sustrato === 'film' ? 4.0 : 3.0;
    const idealMlMin = cargaObjetivo * anchoVal * velVal;
    const eje = Math.max(idealMlMin, mlPorMin) * 1.2;
    chart.data.datasets[0].data = [mlPorMin, idealMlMin];
    chart.options.scales.y.max = eje;
    chart.update();
    detalles.innerHTML =
      `BCM: ${bcmVal} ml/m²<br>Eficiencia: ${eficienciaVal}<br>Cobertura: ${cobertura.toFixed(
        2
      )}<br>Ancho: ${anchoVal} m<br>Velocidad: ${velVal} m/min<br><code>ml/min = ${bcmVal} * ${eficienciaVal} * ${cobertura.toFixed(
        2
      )} * ${anchoVal} * ${velVal} = ${mlPorMin.toFixed(
        2
      )}</code><br>Ideal: ${idealMlMin.toFixed(2)} ml/min`;
  }

  inicializarGrafico();
  actualizarCalculo();
  bcm.addEventListener('input', actualizarCalculo);
  eficiencia.addEventListener('input', actualizarCalculo);
  ancho.addEventListener('input', actualizarCalculo);
  vel.addEventListener('input', actualizarCalculo);
}

