(function () {
  "use strict";

  window.PdfMedidorPro = window.PdfMedidorPro || {};

  class Magnifier {
    constructor(options) {
      this.viewer = options.viewer;
      this.el = options.element;
      this.image = options.image;
      this.factor = 10;
      this.enabled = false;
      this.temporary = false;
    }

    setFactor(value) {
      this.factor = Number(value || 10);
    }

    setEnabled(enabled) {
      this.enabled = Boolean(enabled);
      this.updateVisibility();
    }

    setTemporary(enabled) {
      this.temporary = Boolean(enabled);
      this.updateVisibility();
    }

    update(event) {
      if (!this.enabled && !this.temporary) return;
      const point = this.viewer.pointFromEvent(event);
      const mm = this.viewer.viewportToMm(point);
      const imagePx = this.viewer.mmToImagePx(mm);
      const size = 180;
      this.el.style.left = `${point.x + this.viewer.container.scrollLeft + 18}px`;
      this.el.style.top = `${point.y + this.viewer.container.scrollTop + 18}px`;
      this.el.style.width = `${size}px`;
      this.el.style.height = `${size}px`;
      this.el.style.backgroundImage = [
        "linear-gradient(rgba(180, 35, 24, 0.85), rgba(180, 35, 24, 0.85))",
        "linear-gradient(90deg, rgba(180, 35, 24, 0.85), rgba(180, 35, 24, 0.85))",
        `url("${this.image.src}")`,
      ].join(", ");
      this.el.style.backgroundSize = [
        "1px 100%",
        "100% 1px",
        `${this.viewer.imageCssWidth() * this.factor}px ${this.viewer.imageCssHeight() * this.factor}px`,
      ].join(", ");
      this.el.style.backgroundPosition = [
        "50% 0",
        "0 50%",
        `${size / 2 - imagePx.x * this.factor}px ${size / 2 - imagePx.y * this.factor}px`,
      ].join(", ");
      this.el.dataset.coords = `X ${fmt(mm.x_mm)} mm | Y ${fmt(mm.y_mm)} mm | ${this.factor}x`;
      this.updateVisibility();
    }

    hideIfTemporary() {
      if (this.temporary) {
        this.temporary = false;
        this.updateVisibility();
      }
    }

    updateVisibility() {
      this.el.hidden = !(this.enabled || this.temporary);
    }
  }

  function fmt(value) {
    return Number(value || 0).toLocaleString("es-PY", { maximumFractionDigits: 3 });
  }

  window.PdfMedidorPro.Magnifier = Magnifier;
})();
