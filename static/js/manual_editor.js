/**
 * Editor manual para Montaje Offset Inteligente.
 * Permite mover y rotar formas sobre el pliego.
 */

(function () {
  const btnMode = document.getElementById("btn-manual-mode");
  const editor = document.getElementById("manual-editor");
  const overlay = document.getElementById("overlay");
  const ctx = overlay.getContext("2d");
  const previewBg = document.getElementById("preview-bg");
  const manualJson = document.getElementById("manual_json");
  const btnApply = document.getElementById("btn-manual-apply");
  const gridInput = document.getElementById("grid_mm");
  const snapOn = document.getElementById("snap_on");
  const cursorLbl = document.getElementById("cursor_mm");

  if (!btnMode || !editor) return;

  let boxes = [];
  let sheet = { w_mm: 0, h_mm: 0 };
  let sangrado = 0;
  let scale = 1;
  let selected = null;

  function mmToPx(mm) {
    return mm * scale;
  }

  function pxToMm(px) {
    return px / scale;
  }

  function rectScreen(b) {
    const w = (b.rot ? b.h_mm_trim : b.w_mm_trim) + 2 * sangrado;
    const h = (b.rot ? b.w_mm_trim : b.h_mm_trim) + 2 * sangrado;
    return {
      x: mmToPx(b.x_mm),
      y: mmToPx(sheet.h_mm - b.y_mm - h),
      w: mmToPx(w),
      h: mmToPx(h),
      w_mm: w,
      h_mm: h,
    };
  }

  function render() {
    if (!ctx) return;
    ctx.clearRect(0, 0, overlay.width, overlay.height);
    boxes.forEach((b) => {
      const r = rectScreen(b);
      ctx.save();
      ctx.strokeStyle = "red";
      ctx.lineWidth = 1;
      ctx.strokeRect(r.x, r.y, r.w, r.h);
      ctx.restore();
    });
  }

  function loadState(data) {
    sangrado = data.sangrado_mm || 0;
    sheet = data.sheet_mm || sheet;
    boxes = (data.positions || []).map((p, idx) => ({
      file_idx: p.file_idx ?? idx,
      x_mm: p.x_mm,
      y_mm: p.y_mm,
      w_mm_trim: p.w_mm,
      h_mm_trim: p.h_mm,
      rot: p.rotado || false,
    }));
    if (data.preview_url) previewBg.src = data.preview_url;
    previewBg.onload = () => {
      scale = previewBg.width / sheet.w_mm;
      overlay.width = previewBg.width;
      overlay.height = previewBg.height;
      render();
    };
  }

  function mouseToMm(evt) {
    const rect = overlay.getBoundingClientRect();
    const x = evt.clientX - rect.left;
    const y = evt.clientY - rect.top;
    return { x: pxToMm(x), y: pxToMm(y) };
  }

  overlay.addEventListener("mousemove", (e) => {
    const m = mouseToMm(e);
    cursorLbl.textContent = `${m.x.toFixed(1)} , ${m.y.toFixed(1)} mm`;
    if (!selected) return;
    const grid = parseFloat(gridInput.value) || 1;
    const totalH = rectScreen(selected.box).h_mm;
    let nx = m.x - selected.dx;
    let nyTop = m.y - selected.dy;
    if (snapOn.checked) {
      nx = Math.round(nx / grid) * grid;
      nyTop = Math.round(nyTop / grid) * grid;
    }
    selected.box.x_mm = nx;
    selected.box.y_mm = sheet.h_mm - nyTop - totalH;
    render();
  });

  overlay.addEventListener("mousedown", (e) => {
    const m = mouseToMm(e);
    selected = null;
    for (const b of boxes) {
      const r = rectScreen(b);
      if (
        m.x >= pxToMm(r.x) &&
        m.x <= pxToMm(r.x + r.w) &&
        m.y >= pxToMm(r.y) &&
        m.y <= pxToMm(r.y + r.h)
      ) {
        selected = {
          box: b,
          dx: m.x - b.x_mm,
          dy: m.y - (sheet.h_mm - b.y_mm - r.h_mm),
        };
        break;
      }
    }
  });

  window.addEventListener("mouseup", () => (selected = null));

  window.addEventListener("keydown", (e) => {
    if (e.key.toLowerCase() === "r" && selected) {
      selected.box.rot = !selected.box.rot;
      render();
    }
  });

  btnMode.addEventListener("click", () => {
    editor.style.display = editor.style.display === "none" ? "block" : "none";
  });

  btnApply.addEventListener("click", () => {
    const payload = {
      sheet: { w_mm: sheet.w_mm, h_mm: sheet.h_mm },
      sangrado_mm: sangrado,
      posiciones: boxes.map((b) => ({
        file_idx: b.file_idx,
        x_mm: b.x_mm,
        y_mm: b.y_mm,
        w_mm: b.w_mm_trim,
        h_mm: b.h_mm_trim,
        rot: b.rot,
      })),
      opciones: {},
    };
    manualJson.value = JSON.stringify(payload);
    fetch("/api/manual/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
      .then((r) => r.json())
      .then((resp) => {
        if (resp.preview_url) {
          loadState(resp);
        }
      })
      .catch((err) => console.error(err));
  });

  // Expose loader
  window.manualEditorLoad = loadState;
})();

