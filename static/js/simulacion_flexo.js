// Simulación de impresión flexográfica en vivo
function inicializarSimulacionFlexo() {
  const btn = document.getElementById('btn-simulacion-flexo');
  const panel = document.getElementById('panel-simulacion');
  const cerrar = document.getElementById('cerrar-simulacion');
  const lpi = document.getElementById('sim-lpi');
  const bcm = document.getElementById('sim-bcm');
  const vel = document.getElementById('sim-velocidad');
  const canvasTrama = document.getElementById('sim-canvas');
  if (!btn || !panel || !canvasTrama) return;

  // Preparar capa de textos separada
  const canvasTextos = document.createElement('canvas');
  canvasTextos.id = 'sim-canvas-textos';
  canvasTextos.width = canvasTrama.width;
  canvasTextos.height = canvasTrama.height;
  panel.style.position = 'relative';
  canvasTrama.style.position = canvasTextos.style.position = 'absolute';
  canvasTrama.style.top = canvasTextos.style.top = '0';
  canvasTrama.style.left = canvasTextos.style.left = '0';
  canvasTrama.style.zIndex = '1';
  canvasTextos.style.zIndex = '2';
  panel.appendChild(canvasTextos);

  const ctxTrama = canvasTrama.getContext('2d');
  const ctxTextos = canvasTextos.getContext('2d');

  const img = new Image();
  const baseImg = document.getElementById('imagen-diagnostico');
  if (baseImg) {
    img.src = baseImg.src;
  }

  const datos = window.diagnosticoFlexo || {};
  const textos = datos.textos_pequenos || [];

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
    const promedio = (cobertura.C + cobertura.M + cobertura.Y + cobertura.K) / 400 || 0;
    const minTrama = (datos.trama_minima || 0) / 100;

    const spacing = Math.max(2, (600 / valLpi) * 4);
    const baseRadio = spacing / 2;
    const transferencia = (1 - (valVel - 50) / 250) * (0.5 + promedio);

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
        if (coberturaLocal < minTrama) continue;
        const radio = baseRadio * Math.sqrt(coberturaLocal);
        const alpha = coberturaLocal * (valBcm / 8) * transferencia;
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
  btn.addEventListener('click', () => panel.classList.add('abierto'));
  cerrar.addEventListener('click', () => panel.classList.remove('abierto'));
}

document.addEventListener('DOMContentLoaded', inicializarSimulacionFlexo);
