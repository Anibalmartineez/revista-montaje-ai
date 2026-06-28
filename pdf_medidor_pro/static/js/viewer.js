(function () {
  "use strict";

  window.PdfMedidorPro = window.PdfMedidorPro || {};

  const ZOOM_PRESETS = [0.25, 0.5, 1, 2, 4, 8, 16, 32];
  const HANDLE_SIZE = 8;

  class Viewer {
    constructor(options) {
      this.container = options.container;
      this.stage = options.stage;
      this.image = options.image;
      this.canvas = options.canvas;
      this.ctx = this.canvas.getContext("2d");
      this.renderMm = { ancho: 0, alto: 0 };
      this.previewFilename = "";
      this.natural = { w: 0, h: 0 };
      this.zoom = 1;
      this.pan = { x: 0, y: 0 };
      this.lastPointerMm = null;
      this.onChange = options.onChange || function () {};
      this.image.addEventListener("load", () => this.onImageLoad());
      this.container.addEventListener("scroll", () => {
        this.syncCanvas();
        this.onChange();
      });
      window.addEventListener("resize", () => {
        this.syncCanvas();
        this.onChange();
      });
    }

    setPreview(url, renderMm, previewInfo) {
      this.renderMm = renderMm || { ancho: 0, alto: 0 };
      this.previewFilename = previewInfo && previewInfo.filename ? previewInfo.filename : "";
      this.image.hidden = false;
      this.image.src = url;
    }

    onImageLoad() {
      this.natural = { w: this.image.naturalWidth || 1, h: this.image.naturalHeight || 1 };
      this.setZoom(1, { center: false });
      this.syncCanvas();
      this.onChange();
    }

    setZoom(value, options) {
      const previousPoint = options && options.anchor ? this.viewportToMm(options.anchor) : null;
      this.zoom = clamp(Number(value || 1), 0.25, 32);
      const width = Math.max(1, Math.round(this.natural.w * this.zoom));
      const height = Math.max(1, Math.round(this.natural.h * this.zoom));
      this.image.style.width = `${width}px`;
      this.image.style.height = `${height}px`;
      this.stage.style.width = `${width}px`;
      this.stage.style.height = `${height}px`;
      if (previousPoint && options && options.anchor) {
        const px = this.mmToImagePx(previousPoint);
        this.pan = this.constrainPan({
          x: options.anchor.x - px.x - this.stage.offsetLeft + this.container.scrollLeft,
          y: options.anchor.y - px.y - this.stage.offsetTop + this.container.scrollTop,
        });
      } else if (options && options.center === false) {
        this.container.scrollLeft = 0;
        this.container.scrollTop = 0;
        this.resetPan();
      }
      this.applyViewTransform();
      this.syncCanvas();
      this.onChange();
    }

    zoomBy(multiplier, anchor) {
      this.setZoom(this.zoom * multiplier, { anchor });
    }

    fitWidth() {
      if (!this.natural.w) return;
      const available = Math.max(1, this.container.clientWidth - 56);
      this.setZoom(available / this.natural.w, { center: false });
    }

    fitPage() {
      if (!this.natural.w || !this.natural.h) return;
      const availableW = Math.max(1, this.container.clientWidth - 56);
      const availableH = Math.max(1, this.container.clientHeight - 56);
      this.setZoom(Math.min(availableW / this.natural.w, availableH / this.natural.h), { center: false });
    }

    oneToOne() {
      this.setZoom(1, { center: false });
    }

    syncCanvas() {
      const dpr = window.devicePixelRatio || 1;
      const width = Math.max(1, this.container.clientWidth);
      const height = Math.max(1, this.container.clientHeight);
      this.canvas.style.width = `${width}px`;
      this.canvas.style.height = `${height}px`;
      this.canvas.style.transform = `translate(${this.container.scrollLeft}px, ${this.container.scrollTop}px)`;
      if (this.canvas.width !== Math.round(width * dpr) || this.canvas.height !== Math.round(height * dpr)) {
        this.canvas.width = Math.round(width * dpr);
        this.canvas.height = Math.round(height * dpr);
      }
      this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    getPan() {
      return { x: this.pan.x, y: this.pan.y };
    }

    setPan(x, y) {
      this.pan = this.constrainPan({
        x: round(x),
        y: round(y),
      });
      this.applyViewTransform();
      this.syncCanvas();
      this.onChange();
    }

    panBy(dx, dy) {
      this.setPan(this.pan.x + Number(dx || 0), this.pan.y + Number(dy || 0));
    }

    resetPan() {
      this.pan = { x: 0, y: 0 };
      this.applyViewTransform();
    }

    applyViewTransform() {
      this.stage.style.transform = `translate(${this.pan.x}px, ${this.pan.y}px)`;
    }

    constrainPan(pan) {
      return {
        x: clampPanAxis(Number(pan.x || 0), this.stage.offsetLeft, this.imageCssWidth(), this.container.clientWidth, this.container.scrollLeft),
        y: clampPanAxis(Number(pan.y || 0), this.stage.offsetTop, this.imageCssHeight(), this.container.clientHeight, this.container.scrollTop),
      };
    }

    clear() {
      this.ctx.clearRect(0, 0, this.canvas.clientWidth, this.canvas.clientHeight);
    }

    pointFromEvent(event) {
      const box = this.canvas.getBoundingClientRect();
      return {
        x: event.clientX - box.left,
        y: event.clientY - box.top,
      };
    }

    mmFromEvent(event) {
      const point = this.viewportToMm(this.pointFromEvent(event));
      this.lastPointerMm = point;
      return point;
    }

    viewportToMm(point) {
      const imageX = point.x + this.container.scrollLeft - this.stage.offsetLeft - this.pan.x;
      const imageY = point.y + this.container.scrollTop - this.stage.offsetTop - this.pan.y;
      return {
        x_mm: round((imageX / this.imageCssWidth()) * Number(this.renderMm.ancho || 0)),
        y_mm: round((imageY / this.imageCssHeight()) * Number(this.renderMm.alto || 0)),
      };
    }

    mmToViewport(point) {
      const imagePx = this.mmToImagePx(point);
      return {
        x: imagePx.x + this.stage.offsetLeft + this.pan.x - this.container.scrollLeft,
        y: imagePx.y + this.stage.offsetTop + this.pan.y - this.container.scrollTop,
      };
    }

    mmToImagePx(point) {
      return {
        x: (Number(point.x_mm || 0) / Math.max(0.0001, Number(this.renderMm.ancho || 0))) * this.imageCssWidth(),
        y: (Number(point.y_mm || 0) / Math.max(0.0001, Number(this.renderMm.alto || 0))) * this.imageCssHeight(),
      };
    }

    imageCssWidth() {
      return Math.max(1, this.natural.w * this.zoom);
    }

    imageCssHeight() {
      return Math.max(1, this.natural.h * this.zoom);
    }

    mmPerImagePxX() {
      return Number(this.renderMm.ancho || 0) / Math.max(1, this.imageCssWidth());
    }

    mmPerImagePxY() {
      return Number(this.renderMm.alto || 0) / Math.max(1, this.imageCssHeight());
    }

    drawRulers(pointer) {
      const ctx = this.ctx;
      const width = this.canvas.clientWidth;
      const height = this.canvas.clientHeight;
      ctx.save();
      ctx.fillStyle = "rgba(248, 250, 252, 0.96)";
      ctx.fillRect(0, 0, width, 24);
      ctx.fillRect(0, 0, 34, height);
      ctx.strokeStyle = "#cbd5df";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(34, 24);
      ctx.lineTo(width, 24);
      ctx.moveTo(34, 24);
      ctx.lineTo(34, height);
      ctx.stroke();
      this.drawRulerTicks("horizontal");
      this.drawRulerTicks("vertical");
      if (pointer) {
        const view = this.mmToViewport(pointer);
        ctx.strokeStyle = "rgba(15, 118, 110, 0.55)";
        ctx.beginPath();
        ctx.moveTo(view.x, 0);
        ctx.lineTo(view.x, 24);
        ctx.moveTo(0, view.y);
        ctx.lineTo(34, view.y);
        ctx.stroke();
      }
      ctx.restore();
    }

    drawRulerTicks(orientation) {
      const ctx = this.ctx;
      const horizontal = orientation === "horizontal";
      const maxMm = horizontal ? Number(this.renderMm.ancho || 0) : Number(this.renderMm.alto || 0);
      const startMm = horizontal
        ? this.viewportToMm({ x: 34, y: 24 }).x_mm
        : this.viewportToMm({ x: 34, y: 24 }).y_mm;
      const endMm = horizontal
        ? this.viewportToMm({ x: this.canvas.clientWidth, y: 24 }).x_mm
        : this.viewportToMm({ x: 34, y: this.canvas.clientHeight }).y_mm;
      const span = Math.max(1, Math.abs(endMm - startMm));
      const step = pickStep(span);
      const first = Math.max(0, Math.floor(startMm / step) * step);
      ctx.fillStyle = "#475569";
      ctx.strokeStyle = "#94a3b8";
      ctx.font = "10px Arial";
      for (let mm = first; mm <= Math.min(maxMm, endMm + step); mm += step) {
        const view = horizontal ? this.mmToViewport({ x_mm: mm, y_mm: 0 }) : this.mmToViewport({ x_mm: 0, y_mm: mm });
        ctx.beginPath();
        if (horizontal) {
          ctx.moveTo(view.x, 24);
          ctx.lineTo(view.x, 15);
          ctx.stroke();
          ctx.fillText(String(Math.round(mm)), view.x + 3, 11);
        } else {
          ctx.moveTo(34, view.y);
          ctx.lineTo(24, view.y);
          ctx.stroke();
          ctx.save();
          ctx.translate(5, view.y - 3);
          ctx.rotate(-Math.PI / 2);
          ctx.fillText(String(Math.round(mm)), 0, 0);
          ctx.restore();
        }
      }
    }

    drawCenter() {
      const center = this.mmToViewport({
        x_mm: Number(this.renderMm.ancho || 0) / 2,
        y_mm: Number(this.renderMm.alto || 0) / 2,
      });
      this.ctx.save();
      this.ctx.strokeStyle = "rgba(100, 116, 139, 0.55)";
      this.ctx.lineWidth = 1;
      this.ctx.setLineDash([5, 5]);
      this.ctx.beginPath();
      this.ctx.moveTo(center.x - 18, center.y);
      this.ctx.lineTo(center.x + 18, center.y);
      this.ctx.moveTo(center.x, center.y - 18);
      this.ctx.lineTo(center.x, center.y + 18);
      this.ctx.stroke();
      this.ctx.restore();
    }

    drawCoordinates(point, fmt) {
      if (!point) return;
      this.ctx.save();
      this.ctx.fillStyle = "rgba(15, 23, 42, 0.82)";
      this.ctx.fillRect(this.canvas.clientWidth - 178, this.canvas.clientHeight - 34, 164, 24);
      this.ctx.fillStyle = "#ffffff";
      this.ctx.font = "12px Arial";
      this.ctx.fillText(`X ${fmt(point.x_mm)} mm  Y ${fmt(point.y_mm)} mm`, this.canvas.clientWidth - 168, this.canvas.clientHeight - 18);
      this.ctx.restore();
    }

    drawGuides(guides) {
      const ctx = this.ctx;
      ctx.save();
      ctx.strokeStyle = "rgba(8, 145, 178, 0.78)";
      ctx.lineWidth = 1;
      ctx.setLineDash([6, 5]);
      (guides || []).forEach((guide) => {
        if (guide.visible === false) return;
        ctx.beginPath();
        if (guide.orientation === "vertical") {
          const x = this.mmToViewport({ x_mm: guide.value_mm, y_mm: 0 }).x;
          ctx.moveTo(x, 24);
          ctx.lineTo(x, this.canvas.clientHeight);
        } else {
          const y = this.mmToViewport({ x_mm: 0, y_mm: guide.value_mm }).y;
          ctx.moveTo(34, y);
          ctx.lineTo(this.canvas.clientWidth, y);
        }
        ctx.stroke();
      });
      ctx.restore();
    }

    drawLine(line, selected) {
      if (line.visible === false) return;
      const a = this.mmToViewport(line.a);
      const b = this.mmToViewport(line.b);
      const color = line.color || "#d97706";
      this.ctx.save();
      this.ctx.lineWidth = Number(line.stroke_width || 2);
      this.ctx.strokeStyle = selected ? "#0f766e" : color;
      this.ctx.fillStyle = this.ctx.strokeStyle;
      this.ctx.beginPath();
      this.ctx.moveTo(a.x, a.y);
      this.ctx.lineTo(b.x, b.y);
      this.ctx.stroke();
      this.drawPointViewport(a);
      this.drawPointViewport(b);
      if (selected) this.drawSelectionLine(a, b);
      this.ctx.restore();
    }

    drawRectangle(rect, selected, final) {
      if (!rect || rect.visible === false) return;
      const origin = this.mmToViewport(rect);
      const far = this.mmToViewport({
        x_mm: Number(rect.x_mm || 0) + Number(rect.ancho_mm || rect.w_mm || 0),
        y_mm: Number(rect.y_mm || 0) + Number(rect.alto_mm || rect.h_mm || 0),
      });
      this.ctx.save();
      this.ctx.lineWidth = Number(rect.stroke_width || 2);
      this.ctx.strokeStyle = selected ? "#0f766e" : rect.color || "#2563eb";
      if (final) this.ctx.setLineDash([8, 5]);
      this.ctx.strokeRect(origin.x, origin.y, far.x - origin.x, far.y - origin.y);
      this.ctx.setLineDash([]);
      if (selected) this.drawSelectionRect(origin, far);
      this.ctx.restore();
    }

    drawLiveLabel(point, text) {
      const view = this.mmToViewport(point);
      this.ctx.save();
      this.ctx.font = "12px Arial";
      const width = this.ctx.measureText(text).width + 16;
      this.ctx.fillStyle = "rgba(15, 23, 42, 0.86)";
      this.ctx.fillRect(view.x + 10, view.y - 28, width, 22);
      this.ctx.fillStyle = "#ffffff";
      this.ctx.fillText(text, view.x + 18, view.y - 13);
      this.ctx.restore();
    }

    drawPoint(point, color) {
      this.drawPointViewport(this.mmToViewport(point), color);
    }

    drawPointViewport(point, color) {
      this.ctx.save();
      this.ctx.fillStyle = color || this.ctx.fillStyle || "#b42318";
      this.ctx.beginPath();
      this.ctx.arc(point.x, point.y, 4, 0, Math.PI * 2);
      this.ctx.fill();
      this.ctx.restore();
    }

    drawSnap(point) {
      const view = this.mmToViewport(point);
      this.ctx.save();
      this.ctx.strokeStyle = "#dc2626";
      this.ctx.lineWidth = 2;
      this.ctx.beginPath();
      this.ctx.arc(view.x, view.y, 7, 0, Math.PI * 2);
      this.ctx.moveTo(view.x - 11, view.y);
      this.ctx.lineTo(view.x + 11, view.y);
      this.ctx.moveTo(view.x, view.y - 11);
      this.ctx.lineTo(view.x, view.y + 11);
      this.ctx.stroke();
      this.ctx.restore();
    }

    drawSelectionLine(a, b) {
      this.ctx.save();
      this.ctx.strokeStyle = "rgba(15, 118, 110, 0.35)";
      this.ctx.lineWidth = 1;
      this.ctx.setLineDash([4, 3]);
      this.ctx.beginPath();
      this.ctx.moveTo(a.x, a.y);
      this.ctx.lineTo(b.x, b.y);
      this.ctx.stroke();
      this.drawHandle(a);
      this.drawHandle(b);
      this.ctx.restore();
    }

    drawSelectionRect(a, b) {
      const handles = [
        { x: a.x, y: a.y }, { x: (a.x + b.x) / 2, y: a.y }, { x: b.x, y: a.y },
        { x: b.x, y: (a.y + b.y) / 2 }, { x: b.x, y: b.y }, { x: (a.x + b.x) / 2, y: b.y },
        { x: a.x, y: b.y }, { x: a.x, y: (a.y + b.y) / 2 },
      ];
      this.ctx.save();
      this.ctx.strokeStyle = "rgba(15, 118, 110, 0.45)";
      this.ctx.setLineDash([4, 3]);
      this.ctx.strokeRect(a.x, a.y, b.x - a.x, b.y - a.y);
      handles.forEach((handle) => this.drawHandle(handle));
      this.ctx.restore();
    }

    drawHandle(point) {
      this.ctx.save();
      this.ctx.fillStyle = "#ffffff";
      this.ctx.strokeStyle = "#0f766e";
      this.ctx.lineWidth = 1.5;
      this.ctx.fillRect(point.x - HANDLE_SIZE / 2, point.y - HANDLE_SIZE / 2, HANDLE_SIZE, HANDLE_SIZE);
      this.ctx.strokeRect(point.x - HANDLE_SIZE / 2, point.y - HANDLE_SIZE / 2, HANDLE_SIZE, HANDLE_SIZE);
      this.ctx.restore();
    }

    hitTest(pointMm, measurements) {
      const threshold = 8;
      const pointView = this.mmToViewport(pointMm);
      for (let i = (measurements || []).length - 1; i >= 0; i -= 1) {
        const item = measurements[i];
        if (item.visible === false) continue;
        const handle = this.hitTestHandle(pointView, item);
        if (handle) return { id: item.id, action: "resize", handle };
        if (item.tipo === "linea" && this.hitTestLine(pointView, item, threshold)) {
          return { id: item.id, action: "move" };
        }
        if (item.tipo === "rectangulo" && this.hitTestRectangle(pointView, item, threshold)) {
          return { id: item.id, action: "move" };
        }
      }
      return null;
    }

    hitTestHandle(pointView, item) {
      if (item.tipo !== "rectangulo") return null;
      const handles = this.rectangleHandles(item);
      const names = Object.keys(handles);
      for (let i = 0; i < names.length; i += 1) {
        const name = names[i];
        const handle = handles[name];
        if (Math.abs(pointView.x - handle.x) <= HANDLE_SIZE && Math.abs(pointView.y - handle.y) <= HANDLE_SIZE) {
          return name;
        }
      }
      return null;
    }

    hitTestLine(pointView, line, threshold) {
      const a = this.mmToViewport(line.a);
      const b = this.mmToViewport(line.b);
      const distance = distanceToSegment(pointView, a, b);
      return distance <= threshold;
    }

    hitTestRectangle(pointView, rect, threshold) {
      const a = this.mmToViewport(rect);
      const b = this.mmToViewport({
        x_mm: Number(rect.x_mm || 0) + Number(rect.ancho_mm || 0),
        y_mm: Number(rect.y_mm || 0) + Number(rect.alto_mm || 0),
      });
      const minX = Math.min(a.x, b.x);
      const maxX = Math.max(a.x, b.x);
      const minY = Math.min(a.y, b.y);
      const maxY = Math.max(a.y, b.y);
      const inside = pointView.x >= minX && pointView.x <= maxX && pointView.y >= minY && pointView.y <= maxY;
      const onEdge = Math.abs(pointView.x - minX) <= threshold || Math.abs(pointView.x - maxX) <= threshold
        || Math.abs(pointView.y - minY) <= threshold || Math.abs(pointView.y - maxY) <= threshold;
      return inside && onEdge || inside;
    }

    rectangleHandles(rect) {
      const a = this.mmToViewport(rect);
      const b = this.mmToViewport({
        x_mm: Number(rect.x_mm || 0) + Number(rect.ancho_mm || 0),
        y_mm: Number(rect.y_mm || 0) + Number(rect.alto_mm || 0),
      });
      return {
        nw: { x: a.x, y: a.y },
        n: { x: (a.x + b.x) / 2, y: a.y },
        ne: { x: b.x, y: a.y },
        e: { x: b.x, y: (a.y + b.y) / 2 },
        se: { x: b.x, y: b.y },
        s: { x: (a.x + b.x) / 2, y: b.y },
        sw: { x: a.x, y: b.y },
        w: { x: a.x, y: (a.y + b.y) / 2 },
      };
    }
  }

  function pickStep(spanMm) {
    if (spanMm > 1000) return 200;
    if (spanMm > 500) return 100;
    if (spanMm > 200) return 50;
    if (spanMm > 100) return 20;
    if (spanMm > 50) return 10;
    if (spanMm > 20) return 5;
    return 1;
  }

  function distanceToSegment(point, a, b) {
    const dx = b.x - a.x;
    const dy = b.y - a.y;
    if (dx === 0 && dy === 0) return Math.hypot(point.x - a.x, point.y - a.y);
    const t = Math.max(0, Math.min(1, ((point.x - a.x) * dx + (point.y - a.y) * dy) / (dx * dx + dy * dy)));
    return Math.hypot(point.x - (a.x + t * dx), point.y - (a.y + t * dy));
  }

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function clampPanAxis(value, stageOffset, contentSize, viewportSize, scrollOffset) {
    const visibleMargin = Math.max(24, Math.min(96, viewportSize / 2, contentSize / 2));
    const min = scrollOffset + visibleMargin - stageOffset - contentSize;
    const max = scrollOffset + viewportSize - visibleMargin - stageOffset;
    if (min > max) return (min + max) / 2;
    return clamp(value, min, max);
  }

  function round(value) {
    return Math.round(Number(value || 0) * 1000) / 1000;
  }

  window.PdfMedidorPro.Viewer = Viewer;
  window.PdfMedidorPro.ZOOM_PRESETS = ZOOM_PRESETS;
})();
