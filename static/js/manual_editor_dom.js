(function(){
  // Model holds boxes for each canvas.
  const model = { top: { boxes: [] }, bottom: { boxes: [] } };
  let state = { activeCanvas: null, selection: null, drag: null };

  function getZoom(canvas){
    const el = document.querySelector(`.canvas[data-canvas="${canvas}"]`);
    return el ? Number(el.dataset.zoom || 1) : 1;
  }

  function renderCanvas(canvas){
    const canvasEl = document.querySelector(`.canvas[data-canvas="${canvas}"]`);
    if(!canvasEl) return;
    canvasEl.querySelectorAll('.draggable-box').forEach(el => el.remove());
    const z = getZoom(canvas);
    model[canvas].boxes.slice().forEach(box => {
      const el = document.createElement('div');
      el.className = 'draggable-box';
      el.dataset.id = box.id;
      el.style.position = 'absolute';
      el.style.transform = `translate(${box.x*z}px, ${box.y*z}px)`;
      el.style.width = (box.w*z) + 'px';
      el.style.height = (box.h*z) + 'px';
      el.addEventListener('mousedown', handleMouseDown);
      canvasEl.appendChild(el);
    });
  }

  function readInputsAsWorkUnits(){
    const z = getZoom(state.activeCanvas);
    const x = parseFloat(document.getElementById('inp-x')?.value || '0');
    const y = parseFloat(document.getElementById('inp-y')?.value || '0');
    const w = parseFloat(document.getElementById('inp-w')?.value || '0');
    const h = parseFloat(document.getElementById('inp-h')?.value || '0');
    return { x: x/z, y: y/z, w: w/z, h: h/z };
  }

  function applyEdicion(){
    if(!state.selection) return;
    const { canvas, id } = state.selection;
    const patch = readInputsAsWorkUnits();
    const boxes = model[canvas].boxes;
    const box = boxes.find(b => b.id === id);
    if(!box) return;
    Object.assign(box, patch);
    renderCanvas(canvas);
  }

  function handleMouseDown(e){
    const boxEl = e.target.closest('.draggable-box');
    if(!boxEl) return;
    const canvasEl = boxEl.closest('.canvas');
    const canvas = canvasEl.dataset.canvas;
    const id = boxEl.dataset.id;
    state.activeCanvas = canvas;
    state.selection = { canvas, id };
    const boxes = model[canvas].boxes;
    const box = boxes.find(b => b.id === id);
    if(!box) return;
    state.drag = { box, startX:e.clientX, startY:e.clientY, origX:box.x, origY:box.y };
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  }

  function handleMouseMove(e){
    if(!state.drag) return;
    const z = getZoom(state.activeCanvas);
    const dx = (e.clientX - state.drag.startX)/z;
    const dy = (e.clientY - state.drag.startY)/z;
    state.drag.box.x = state.drag.origX + dx;
    state.drag.box.y = state.drag.origY + dy;
    renderCanvas(state.activeCanvas);
  }

  function handleMouseUp(){
    state.drag = null;
    document.removeEventListener('mousemove', handleMouseMove);
    document.removeEventListener('mouseup', handleMouseUp);
  }

  // Public API to load initial boxes
  window.manualEditorDom = {
    load(canvas, boxes){
      model[canvas].boxes = boxes.map(b => ({...b}));
      renderCanvas(canvas);
    }
  };

  document.getElementById('btn-manual-apply')?.addEventListener('click', applyEdicion);
})();
