(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.EditorOffsetV2 = root.EditorOffsetV2 || {};
  root.EditorOffsetV2.WorkBleed = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";
  function allowsMirror(work, legacyPermission = false) {
    return work?.bleed_strategy === undefined ? Boolean(legacyPermission) : work.bleed_strategy === "mirror_if_missing";
  }
  function declaredMargin(boxes, selected) {
    const trim = boxes[selected];
    if (!trim || !boxes.bleed || !boxes.media) return 0;
    return Math.min(...[boxes.media, boxes.bleed].flatMap(outer => [
      trim.x - outer.x, trim.y - outer.y,
      outer.x + outer.width - trim.x - trim.width,
      outer.y + outer.height - trim.y - trim.height,
    ]));
  }
  function availableBleed(boxes, selected) { return Math.max(0, declaredMargin(boxes, selected)); }
  function sourceCoversBleed(boxes, selected, bleed, clip = "bleed_box") {
    return Number(bleed) === 0 || (clip === "bleed_box" && Boolean(boxes.bleed && boxes.media && boxes[selected])
      && declaredMargin(boxes, selected) + 0.001 >= Number(bleed));
  }
  function label(strategy) {
    return strategy === "mirror_if_missing" ? "Espejo autorizado si falta sangrado (generado)"
      : strategy === "source_only" ? "Solo sangrado del archivo" : "Trabajo anterior: permiso temporal en Salida";
  }
  return Object.freeze({ allowsMirror, availableBleed, sourceCoversBleed, label });
});
