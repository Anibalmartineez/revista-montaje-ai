(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.EditorOffsetV2 = root.EditorOffsetV2 || {};
  root.EditorOffsetV2.Preparation = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";
  const clone = (value) => JSON.parse(JSON.stringify(value));
  const BOXES = Object.freeze(["bleed", "media", "trim", "crop"]);
  function detectedBox(page, bleed = 0) {
    // With no requested bleed, use the PDF's existing outer artwork extent.
    // A positive value asks V2 to start from trim and add/preserve that bleed.
    const order = Number(bleed) > 0 ? ["trim", "media", "crop", "bleed"] : ["bleed", "media", "crop", "trim"];
    return order.find((name) => page?.boxes_mm?.[name]) || null;
  }
  function dimensions(page, boxName) {
    const box = page.boxes_mm[boxName];
    if (!box) return null;
    const rotated = [90, 270].includes(page.intrinsic_rotation_deg);
    return { width: Number((rotated ? box.height : box.width).toFixed(3)),
      height: Number((rotated ? box.width : box.height).toFixed(3)) };
  }
  function makeDraft(asset, page) {
    const box = detectedBox(page, 0);
    const size = dimensions(page, box);
    return { assetId: asset.id, page: page.number, box, selected: false,
      name: `${asset.original_filename.replace(/\.pdf$/i, "")} · pág. ${page.number}`.slice(0, 160),
      width: size?.width ?? "", height: size?.height ?? "", sizeMode: "box",
      quantity: 1, bleed: 0, bleedStrategy: "source_only", cropMarks: true,
      rotations: [0, 90, 180, 270], back: false, variant: false };
  }
  function changeBox(draft, page, box) {
    draft.box = box;
    const size = dimensions(page, box);
    if (size && draft.sizeMode === "box") Object.assign(draft, size);
  }
  function applyBleedIntent(draft, page, value) {
    const empty = value === "" || value === null || value === undefined;
    const bleed = empty ? 0 : Number(value);
    draft.bleed = empty ? "" : value;
    draft.bleedStrategy = bleed > 0 ? "mirror_if_missing" : "source_only";
    const box = detectedBox(page, bleed);
    if (!box) throw new Error(`Página ${page?.number}: la medida del PDF no está disponible.`);
    // The operator changed bleed intent; restore the automatically detected
    // source size rather than carrying an older box-based size forward.
    draft.sizeMode = "box";
    changeBox(draft, page, box);
  }
  function source(draft, asset) {
    const page = asset?.pages.find((item) => item.number === draft.page);
    if (asset?.id !== draft.assetId || !page || !page.boxes_mm[draft.box]) throw new Error(`Página ${draft.page}: la caja ${draft.box} no existe. Elige otra caja.`);
    return { asset_id: asset.id, page: page.number, pdf_box: draft.box };
  }
  function entry(draft, asset) {
    const selectedSource = source(draft, asset);
    const invalid = (message) => { throw new Error(`Página ${draft.page}: ${message}`); };
    if (!String(draft.name || "").trim()) invalid("escribe un nombre para el trabajo.");
    if (!Number.isInteger(Number(draft.quantity)) || Number(draft.quantity) < 1) invalid("la cantidad debe ser un entero mayor que cero.");
    if (![draft.width, draft.height].every((value) => Number.isFinite(Number(value)) && Number(value) > 0)) invalid("las medidas finales deben ser mayores que cero.");
    const bleed = draft.bleed === "" || draft.bleed === null || draft.bleed === undefined ? 0 : Number(draft.bleed);
    if (!Number.isFinite(bleed) || bleed < 0) invalid("indica un sangrado de cero o más milímetros.");
    if (!draft.rotations.length || draft.rotations.some((value) => ![0, 90, 180, 270].includes(value))) invalid("elige al menos un giro cardinal.");
    return { source: selectedSource,
      values: { name: draft.name, width: draft.width, height: draft.height,
        bleed, requestedForms: Number(draft.quantity),
        cropMarks: Boolean(draft.cropMarks),
        ...(draft.bleedStrategy === undefined ? {} : { bleedStrategy: draft.bleedStrategy }),
        allowedRotations: [...draft.rotations], useSameSourceForBack: draft.back } };
  }
  function matches(work, draft) {
    return work.front_source?.asset_id === draft.assetId && work.front_source?.page === draft.page;
  }
  function uniqueName(name, works) {
    const names = new Set(works.map((work) => work.name));
    let candidate = name;
    for (let n = 2; names.has(candidate); n += 1) {
      const suffix = ` · variante ${n}`;
      candidate = name.slice(0, 160 - suffix.length) + suffix;
    }
    return candidate;
  }
  class Drafts {
    constructor() { this.pages = new Map(); }
    get(asset, page) {
      const key = `${asset.id}:${page.number}`;
      if (!this.pages.has(key)) this.pages.set(key, makeDraft(asset, page));
      return this.pages.get(key);
    }
    selected(asset) { return asset.pages.map((page) => this.get(asset, page)).filter((draft) => draft.selected); }
    apply(asset, reference, fields) {
      for (const draft of this.selected(asset)) {
        for (const field of fields) draft[field] = clone(reference[field]);
        const page = asset.pages.find((page) => page.number === draft.page);
        if (fields.includes("bleed")) applyBleedIntent(draft, page, draft.bleed);
        else changeBox(draft, page, draft.box);
      }
    }
    entries(asset, works) {
      const selected = this.selected(asset);
      if (!selected.length) throw new Error("Selecciona al menos una página.");
      return selected.map((draft) => {
        if (works.some((work) => matches(work, draft)) && !draft.variant) {
          throw new Error(`Página ${draft.page}: ya tiene trabajos. Edítalos en Trabajos preparados o activa Crear variante.`);
        }
        const result = entry(draft, asset);
        result.values.name = uniqueName(result.values.name, works);
        return result;
      });
    }
  }
  return Object.freeze({ Drafts, BOXES, detectedBox, dimensions, changeBox, applyBleedIntent, source, entry, matches, uniqueName });
});
