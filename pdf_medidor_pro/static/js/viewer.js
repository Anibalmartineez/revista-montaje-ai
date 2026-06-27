(function () {
  "use strict";

  window.PdfMedidorPro = window.PdfMedidorPro || {};

  const ZOOM_PRESETS = [0.25, 0.5, 1, 2, 4, 8, 16, 32];

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
      this.onChange = options.onChange || function () {};
      this.image.addEventListener("load", () => this.onImageLoad());
      this.container.addEventListener("scroll", () => this.syncCanvas());
      window.addEventListener("resize", () => this.syncCanvas());
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
        this.container.scrollLeft = Math.max(0, px.x - options.anchor.x);
        this.container.scrollTop = Math.max(0, px.y - options.anchor.y);
      } else if (options && options.center === false) {
        this.container.scrollLeft = 0;
        this.container.scrollTop = 0;
      }
      this.syncCanvas();
      this.onChange();
    }

    zoomBy(multiplier, anchor) {
      this.setZoom(this.zoom * multiplier, { anchor });
    }

    fitWidth() {
      if (!this.natural.w) return;
      const available = Math.max(1, this.container.clientWidth - 36);
      this.setZoom(available / this.natural.w, { center: false });
    }

    fitPage() {
      if (!this.natural.w || !this.natural.h) return;
      const availableW = Math.max(1, this.container.clientWidth - 36);
      const availableH = Math.max(1, this.container.clientHeight - 36);
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
      return this.viewportToMm(this.pointFromEvent(event));
    }

    viewportToMm(point) {
      const imageX = point.x + this.container.scrollLeft - this.stage.offsetLeft;
      const imageY = point.y + this.container.scrollTop - this.stage.offsetTop;
      return {
        x_mm: round((imageX / this.imageCssWidth()) * Number(this.renderMm.ancho || 0)),
        y_mm: round((imageY / this.imageCssHeight()) * Number(this.renderMm.alto || 0)),
      };
    }

    mmToViewport(point) {
      const imagePx = this.mmToImagePx(point);
      return {
        x: imagePx.x + this.stage.offsetLeft - this.container.scrollLeft,
        y: imagePx.y + this.stage.offsetTop - this.container.scrollTop,
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

    drawLine(line, selected) {
      if (line.visible === false) return;
      const a = this.mmToViewport(line.a);
      const b = this.mmToViewport(line.b);
      this.ctx.save();
      this.ctx.lineWidth = selected ? 3 : 2;
      this.ctx.strokeStyle = selected ? "#0f766e" : line.origen === "ia" ? "#7c3aed" : "#d97706";
      this.ctx.fillStyle = this.ctx.strokeStyle;
      this.ctx.beginPath();
      this.ctx.moveTo(a.x, a.y);
      this.ctx.lineTo(b.x, b.y);
      this.ctx.stroke();
      this.drawPointViewport(a);
      this.drawPointViewport(b);
      this.ctx.restore();
    }

    drawRectangle(rect, selected) {
      if (!rect || rect.visible === false) return;
      const origin = this.mmToViewport(rect);
      const far = this.mmToViewport({
        x_mm: Number(rect.x_mm || 0) + Number(rect.ancho_mm || rect.w_mm || 0),
        y_mm: Number(rect.y_mm || 0) + Number(rect.alto_mm || rect.h_mm || 0),
      });
      this.ctx.save();
      this.ctx.lineWidth = selected ? 3 : 2;
      this.ctx.strokeStyle = selected ? "#0f766e" : rect.origen === "ia" ? "#7c3aed" : "#2563eb";
      this.ctx.setLineDash(rect.origen === "ia" ? [8, 5] : []);
      this.ctx.strokeRect(origin.x, origin.y, far.x - origin.x, far.y - origin.y);
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
  }

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function round(value) {
    return Math.round(Number(value || 0) * 1000) / 1000;
  }

  window.PdfMedidorPro.Viewer = Viewer;
  window.PdfMedidorPro.ZOOM_PRESETS = ZOOM_PRESETS;
})();
