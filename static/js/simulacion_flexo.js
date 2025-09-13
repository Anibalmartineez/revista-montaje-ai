// Simulación de impresión flexográfica en vivo
function inicializarSimulacionFlexo() {
  const btn = document.getElementById('btn-simulacion-flexo');
  const panel = document.getElementById('panel-simulacion');
  const cerrar = document.getElementById('cerrar-simulacion');
  const lpi = document.getElementById('sim-lpi');
  const bcm = document.getElementById('sim-bcm');
  const vel = document.getElementById('sim-velocidad');
  const canvas = document.getElementById('sim-canvas');
  if (!btn || !panel || !canvas) return;
  const ctx = canvas.getContext('2d');
  const img = new Image();
  const baseImg = document.getElementById('imagen-diagnostico');
  if (baseImg) {
    img.src = baseImg.src;
  }
  const datos = window.diagnosticoFlexo || {};
  function dibujar() {
    const valLpi = parseFloat(lpi.value);
    const valBcm = parseFloat(bcm.value);
    const valVel = parseFloat(vel.value);
    const cobertura = datos.cobertura || {};
    const promedio = (cobertura.C + cobertura.M + cobertura.Y + cobertura.K) / 400 || 0;
    ctx.clearRect(0,0,canvas.width,canvas.height);
    if (img.complete) {
      ctx.globalAlpha = 1 - ((valVel - 50) / 250) * 0.3;
      ctx.filter = `saturate(${0.5 + (valBcm - 1) / 7}) brightness(${0.8 + promedio})`;
      ctx.drawImage(img,0,0,canvas.width,canvas.height);
      ctx.filter = 'none';
    }
    ctx.globalAlpha = 1;
    const spacing = 10;
    const radio = (600 - valLpi) / 400 * 3 + 1;
    ctx.fillStyle = 'rgba(0,0,0,0.2)';
    for (let y=0; y<canvas.height; y+=spacing) {
      for (let x=0; x<canvas.width; x+=spacing) {
        ctx.beginPath();
        ctx.arc(x, y, radio, 0, Math.PI*2);
        ctx.fill();
      }
    }
  }
  img.onload = dibujar;
  lpi.addEventListener('input', dibujar);
  bcm.addEventListener('input', dibujar);
  vel.addEventListener('input', dibujar);
  btn.addEventListener('click', () => panel.classList.add('abierto'));
  cerrar.addEventListener('click', () => panel.classList.remove('abierto'));
}

document.addEventListener('DOMContentLoaded', inicializarSimulacionFlexo);
