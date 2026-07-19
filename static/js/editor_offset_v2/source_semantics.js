(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.EditorOffsetV2 = root.EditorOffsetV2 || {};
  root.EditorOffsetV2.SourceSemantics = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  function sameSource(left, right) {
    return Boolean(left && right)
      && left.asset_id === right.asset_id
      && left.page === right.page
      && left.pdf_box === right.pdf_box;
  }

  function defaultSourceForSlot(layout, slot) {
    const work = layout.works.find((item) => item.id === slot.work_id);
    if (!work) return null;
    return slot.face === "back" ? work.back_source : work.front_source;
  }

  function hasSourceOverride(layout, slot) {
    return !sameSource(slot.source, defaultSourceForSlot(layout, slot));
  }

  return Object.freeze({ sameSource, defaultSourceForSlot, hasSourceOverride });
});
