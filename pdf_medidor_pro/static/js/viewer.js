(function () {
  "use strict";

  window.PdfMedidorPro = window.PdfMedidorPro || {};

  class Viewer {
    constructor(options) {
      this.container = options.container;
      this.image = options.image;
      this.canvas = options.canvas;
      this.ctx = this.canvas.getContext("2d");
      this.renderMm = { ancho: 0, alto: 0 };
      this.image.addEventListener("load", () => this.syncCanvas());
      window.addEventListener("resize", () => this.syncCanvas());
    }

    setPreview(url, renderMm) {
      this.renderMm = renderMm || { ancho: 0, alto: 0 };
      this.image.hidden = false;
      this.image.src = url;
    }

    syncCanvas() {
      if (this.image.hidden || !this.image.clientWidth || !this.image.clientHeight) {
        return;
      }
      const imageBox = this.image.getBoundingClientRect();
      const containerBox = this.container.getBoundingClientRect();
      this.canvas.width = Math.round(imageBox.width);
      this.canvas.height = Math.round(imageBox.height);
      this.canvas.style.width = `${imageBox.width}px`;
      this.canvas.style.height = `${imageBox.height}px`;
      this.canvas.style.left = `${imageBox.left - containerBox.left + this.container.scrollLeft}px`;
      this.canvas.style.top = `${imageBox.top - containerBox.top + this.container.scrollTop}px`;
      this.clear();
    }

    clear() {
      this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    }

    pointFromEvent(event) {
      const box = this.canvas.getBoundingClientRect();
      return {
        x: event.clientX - box.left,
        y: event.clientY - box.top,
      };
    }

    mmPerPxX() {
      return this.canvas.width > 0 ? Number(this.renderMm.ancho || 0) / this.canvas.width : 0;
    }

    mmPerPxY() {
      return this.canvas.height > 0 ? Number(this.renderMm.alto || 0) / this.canvas.height : 0;
    }

    drawLine(line, selected) {
      this.ctx.save();
      this.ctx.lineWidth = selected ? 3 : 2;
      this.ctx.strokeStyle = selected ? "#0f766e" : "#d97706";
      this.ctx.fillStyle = this.ctx.strokeStyle;
      this.ctx.beginPath();
      this.ctx.moveTo(line.a.x, line.a.y);
      this.ctx.lineTo(line.b.x, line.b.y);
      this.ctx.stroke();
      this.drawPoint(line.a);
      this.drawPoint(line.b);
      this.ctx.restore();
    }

    drawPoint(point) {
      this.ctx.beginPath();
      this.ctx.arc(point.x, point.y, 4, 0, Math.PI * 2);
      this.ctx.fill();
    }

    drawRectangle(rect, selected) {
      this.ctx.save();
      this.ctx.lineWidth = selected ? 3 : 2;
      this.ctx.strokeStyle = selected ? "#0f766e" : "#2563eb";
      this.ctx.setLineDash(selected ? [] : [8, 5]);
      this.ctx.strokeRect(rect.x, rect.y, rect.w, rect.h);
      this.ctx.restore();
    }
  }

  window.PdfMedidorPro.Viewer = Viewer;
})();
