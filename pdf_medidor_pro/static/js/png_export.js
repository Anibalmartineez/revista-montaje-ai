(function () {
  "use strict";

  window.PdfMedidorPro = window.PdfMedidorPro || {};

  function exportPng(options) {
    const image = options.image;
    if (!image || image.hidden || !image.naturalWidth) {
      throw new Error("No hay preview para exportar.");
    }
    const canvas = document.createElement("canvas");
    canvas.width = image.naturalWidth;
    canvas.height = image.naturalHeight;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
    const renderMm = options.renderMm || { ancho: 1, alto: 1 };
    const toPx = (point) => ({
      x: (Number(point.x_mm || 0) / Math.max(0.0001, Number(renderMm.ancho || 0))) * canvas.width,
      y: (Number(point.y_mm || 0) / Math.max(0.0001, Number(renderMm.alto || 0))) * canvas.height,
    });

    if (options.includeGuides) {
      drawGuides(ctx, options.guides || [], renderMm, canvas);
    }
    (options.measurements || []).forEach((item) => {
      if (item.visible === false) return;
      if (item.tipo === "linea") drawLine(ctx, item, toPx, options.fmt);
      if (item.tipo === "rectangulo") drawRect(ctx, item, toPx, options.fmt);
    });
    download(canvas, options.filename || "pdf_medidor_pro.png");
  }

  function drawLine(ctx, line, toPx, fmt) {
    const a = toPx(line.a);
    const b = toPx(line.b);
    ctx.save();
    ctx.strokeStyle = line.color || "#d97706";
    ctx.fillStyle = line.color || "#d97706";
    ctx.lineWidth = Number(line.stroke_width || 2);
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
    const dx = Number(line.b.x_mm || 0) - Number(line.a.x_mm || 0);
    const dy = Number(line.b.y_mm || 0) - Number(line.a.y_mm || 0);
    ctx.font = "14px Arial";
    ctx.fillText(`${line.nombre || "Linea"} ${fmt(Math.hypot(dx, dy))} mm`, (a.x + b.x) / 2 + 6, (a.y + b.y) / 2 - 6);
    ctx.restore();
  }

  function drawRect(ctx, rect, toPx, fmt) {
    const a = toPx({ x_mm: rect.x_mm, y_mm: rect.y_mm });
    const b = toPx({ x_mm: Number(rect.x_mm || 0) + Number(rect.ancho_mm || 0), y_mm: Number(rect.y_mm || 0) + Number(rect.alto_mm || 0) });
    ctx.save();
    ctx.strokeStyle = rect.color || "#2563eb";
    ctx.fillStyle = rect.color || "#2563eb";
    ctx.lineWidth = Number(rect.stroke_width || 2);
    ctx.strokeRect(a.x, a.y, b.x - a.x, b.y - a.y);
    ctx.font = "14px Arial";
    ctx.fillText(`${rect.nombre || "Rectangulo"} ${fmt(rect.ancho_mm)} x ${fmt(rect.alto_mm)} mm`, a.x + 6, a.y - 6);
    ctx.restore();
  }

  function drawGuides(ctx, guides, renderMm, canvas) {
    ctx.save();
    ctx.strokeStyle = "rgba(14, 116, 144, 0.75)";
    ctx.lineWidth = 1;
    ctx.setLineDash([6, 6]);
    guides.forEach((guide) => {
      if (guide.visible === false) return;
      ctx.beginPath();
      if (guide.orientation === "vertical") {
        const x = (Number(guide.value_mm || 0) / Math.max(0.0001, Number(renderMm.ancho || 0))) * canvas.width;
        ctx.moveTo(x, 0);
        ctx.lineTo(x, canvas.height);
      } else {
        const y = (Number(guide.value_mm || 0) / Math.max(0.0001, Number(renderMm.alto || 0))) * canvas.height;
        ctx.moveTo(0, y);
        ctx.lineTo(canvas.width, y);
      }
      ctx.stroke();
    });
    ctx.restore();
  }

  function download(canvas, filename) {
    const link = document.createElement("a");
    link.download = filename;
    link.href = canvas.toDataURL("image/png");
    link.click();
  }

  window.PdfMedidorPro.exportPng = exportPng;
})();
