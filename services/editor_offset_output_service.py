import os
from typing import Callable, Dict, List

from PyPDF2 import PdfReader, PdfWriter


def _slot_has_export_override(slot: dict, key: str) -> bool:
    overrides = slot.get("export_overrides")
    if isinstance(overrides, dict):
        return bool(overrides.get(key))
    legacy_key = f"{key}_override"
    return bool(slot.get(legacy_key))


def _sanitize_slot_bleed(
    slot: dict,
    design_ref: str | None,
    design_export: dict | None,
    export_settings: dict | None,
    bleed_default: float,
    work: dict | None = None,
    prefer_slot: bool = False,
) -> float:
    bleed_val = None

    if _slot_has_export_override(slot, "bleed_mm"):
        bleed_val = slot.get("bleed_mm")

    if bleed_val is None and design_ref is not None:
        design_overrides = (design_export or {}).get(str(design_ref))
        if isinstance(design_overrides, dict):
            bleed_val = design_overrides.get("bleed_mm")

    if bleed_val is None and isinstance(export_settings, dict):
        bleed_val = export_settings.get("bleed_mm")

    if bleed_val is None:
        bleed_val = slot.get("bleed_mm")

    if bleed_val is None and work:
        bleed_val = work.get("default_bleed_mm")
    if bleed_val is None:
        bleed_val = bleed_default
    try:
        return float(bleed_val)
    except (TypeError, ValueError):
        return float(bleed_default)


def _resolve_slot_crop_marks(
    slot: dict, design_ref: str | None, design_export: dict | None, export_settings: dict | None
) -> bool:
    crop_val = None
    if _slot_has_export_override(slot, "crop_marks"):
        crop_val = slot.get("crop_marks")

    if crop_val is None and design_ref is not None:
        design_overrides = (design_export or {}).get(str(design_ref))
        if isinstance(design_overrides, dict):
            crop_val = design_overrides.get("crop_marks")

    if crop_val is None and isinstance(export_settings, dict):
        crop_val = export_settings.get("crop_marks")

    if crop_val is None:
        crop_val = slot.get("crop_marks")

    if crop_val is None:
        crop_val = True
    return bool(crop_val)


def _coerce_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def _numeric_or_none(value):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _normalize_rotation(value) -> int:
    try:
        return int(float(value or 0)) % 360
    except (TypeError, ValueError):
        return 0


def _close_mm(a: float, b: float, tolerance: float = 0.05) -> bool:
    return abs(float(a) - float(b)) <= tolerance


def _design_trim_size(design: dict | None) -> tuple[float, float] | None:
    if not isinstance(design, dict):
        return None
    width = _numeric_or_none(design.get("width_mm"))
    height = _numeric_or_none(design.get("height_mm"))
    if width is None or height is None:
        return None
    return width, height


def _matches_box(w_mm: float, h_mm: float, expected_w: float, expected_h: float) -> bool:
    return _close_mm(w_mm, expected_w) and _close_mm(h_mm, expected_h)


def _resolve_slot_box_final(
    slot: dict,
    design: dict | None,
    bleed_mm: float,
    engine_name: str,
) -> bool:
    if "slot_box_final" in slot:
        return _coerce_bool(slot.get("slot_box_final"))
    if engine_name != "repeat":
        return False

    rot = _normalize_rotation(slot.get("rotation_deg", slot.get("rot_deg", 0)))
    if rot not in (90, 270):
        return True

    design_size = _design_trim_size(design)
    if design_size is None:
        return True

    design_w, design_h = design_size
    final_w = design_w + 2 * float(bleed_mm)
    final_h = design_h + 2 * float(bleed_mm)
    slot_w = float(slot.get("w_mm", 0) or 0)
    slot_h = float(slot.get("h_mm", 0) or 0)

    if _matches_box(slot_w, slot_h, final_h, final_w):
        return True
    if _matches_box(slot_w, slot_h, final_w, final_h):
        return False
    return True


def _resolve_legacy_dependencies(diseno_cls, config_cls, render_fn):
    if diseno_cls is not None and config_cls is not None and render_fn is not None:
        return diseno_cls, config_cls, render_fn

    from montaje_offset_inteligente import Diseno, MontajeConfig, realizar_montaje_inteligente

    return diseno_cls or Diseno, config_cls or MontajeConfig, render_fn or realizar_montaje_inteligente


def _strategy_from_engine(layout_obj: dict) -> str:
    engine = (layout_obj.get("imposition_engine") or "repeat").lower()
    if engine == "nesting":
        return "nesting_pro"
    if engine == "hybrid":
        return "hybrid_nesting_repeat"
    return "grid"


def _resolve_output_path(res, default_path: str) -> str:
    if isinstance(res, str):
        return res
    if isinstance(res, dict):
        return res.get("output_path", default_path)
    return default_path


def _build_designs(layout_data: dict, job_dir: str, diseno_cls) -> tuple[Dict[str, int], list]:
    ref_to_idx: Dict[str, int] = {}
    disenos = []

    for design in layout_data.get("designs", []) or []:
        filename = design.get("filename")
        ref = design.get("ref")
        if not filename or not ref:
            continue
        ruta_pdf = os.path.join(job_dir, filename)
        if not os.path.exists(ruta_pdf):
            continue
        ref_to_idx[str(ref)] = len(disenos)
        forms_per_plate = max(1, int(design.get("forms_per_plate") or 1))
        disenos.append(diseno_cls(ruta=ruta_pdf, cantidad=forms_per_plate))

    return ref_to_idx, disenos


def _positions_for_face(
    layout_data: dict,
    target_face: str,
    ref_to_idx: Dict[str, int],
    works: dict,
    design_export: dict,
    export_settings: dict,
    bleed_default: float,
    bleed_layout: float,
    engine_name: str,
) -> tuple[list[dict], bool]:
    posiciones: List[dict] = []
    face_crop = False
    designs_by_ref = {
        str(design.get("ref")): design
        for design in (layout_data.get("designs", []) or [])
        if isinstance(design, dict) and design.get("ref") is not None
    }
    for slot in layout_data.get("slots", []) or []:
        slot_face = (slot.get("face") or "front").lower()
        if slot_face != target_face:
            continue
        ref = slot.get("design_ref")
        if not ref or ref not in ref_to_idx:
            continue
        work = works.get(slot.get("logical_work_id"))
        bleed_val = _sanitize_slot_bleed(
            slot,
            ref,
            design_export,
            export_settings,
            bleed_default,
            work,
            prefer_slot=engine_name == "repeat",
        )
        w_mm = float(slot.get("w_mm", 0))
        h_mm = float(slot.get("h_mm", 0))
        has_bleed = bool(work.get("has_bleed")) if work else False

        if has_bleed:
            trim_w = w_mm
            trim_h = h_mm
        elif engine_name == "repeat":
            trim_w = w_mm
            trim_h = h_mm
        else:
            trim_w = w_mm - 2 * bleed_layout if w_mm else 0
            trim_h = h_mm - 2 * bleed_layout if h_mm else 0
        if trim_w <= 0:
            trim_w = max(1.0, w_mm)
        if trim_h <= 0:
            trim_h = max(1.0, h_mm)
        rot_deg = _normalize_rotation(slot.get("rotation_deg", slot.get("rot_deg", 0)))
        design = designs_by_ref.get(str(ref))
        slot_box_final = _resolve_slot_box_final(slot, design, bleed_val, engine_name)
        source_size = _design_trim_size(design)
        source_w_mm = None
        source_h_mm = None
        x_mm = float(slot.get("x_mm", slot.get("x", 0)))
        y_mm = float(slot.get("y_mm", slot.get("y", 0)))
        if source_size is not None:
            source_w_mm, source_h_mm = source_size
            source_draw_w = source_w_mm + 2 * bleed_val
            source_draw_h = source_h_mm + 2 * bleed_val
            if (
                engine_name == "repeat"
                and not slot_box_final
                and rot_deg in (90, 270)
                and _matches_box(w_mm, h_mm, source_draw_w, source_draw_h)
            ):
                eff_draw_w = source_draw_h
                eff_draw_h = source_draw_w
                center_x = x_mm + w_mm / 2.0
                center_y = y_mm + h_mm / 2.0
                x_mm = center_x - eff_draw_w / 2.0
                y_mm = center_y - eff_draw_h / 2.0
                trim_w = max(0.1, eff_draw_w - 2 * bleed_val)
                trim_h = max(0.1, eff_draw_h - 2 * bleed_val)
        crop_flag = _resolve_slot_crop_marks(slot, ref, design_export, export_settings)
        face_crop = face_crop or crop_flag
        position = {
            "file_idx": ref_to_idx[ref],
            "x_mm": x_mm,
            "y_mm": y_mm,
            "w_mm": trim_w,
            "h_mm": trim_h,
            "rot_deg": rot_deg,
            "bleed_mm": bleed_val,
            "crop_marks": crop_flag,
            "slot_box_final": slot_box_final,
        }
        if source_w_mm is not None and source_h_mm is not None:
            position["source_w_mm"] = source_w_mm
            position["source_h_mm"] = source_h_mm
        posiciones.append(position)
    return posiciones, face_crop


def montar_offset_desde_layout(
    layout_data,
    job_dir,
    preview: bool = False,
    diseno_cls=None,
    config_cls=None,
    render_fn: Callable | None = None,
):
    """
    layout_data viene del layout_constructor.json.
    job_dir es la carpeta static/constructor_offset_jobs/<job_id>/.
    Si preview=True: genera un PNG y devuelve su ruta.
    Si preview=False: genera un PDF final y devuelve su ruta.
    """

    if layout_data is None:
        raise ValueError("layout_data es requerido")

    diseno_cls, config_cls, render_fn = _resolve_legacy_dependencies(diseno_cls, config_cls, render_fn)

    sheet_mm = layout_data.get("sheet_mm", [640, 880])
    margins = layout_data.get("margins_mm", [10, 10, 10, 10])
    bleed_default_raw = layout_data.get("bleed_default_mm")
    try:
        bleed_default = float(bleed_default_raw)
    except (TypeError, ValueError):
        bleed_default = 3.0
    bleed_layout = bleed_default
    gap_default = layout_data.get("gap_default_mm", 0)
    ctp_cfg = layout_data.get("ctp", {}) or {}
    ctp_enabled = bool(ctp_cfg.get("enabled"))
    gripper_mm = float(ctp_cfg.get("gripper_mm", 0) or 0)
    base_pinza_mm = float(layout_data.get("pinza_mm", 0) or 0)
    export_settings_raw = layout_data.get("export_settings")
    export_settings = export_settings_raw if isinstance(export_settings_raw, dict) else {}
    output_mode = str(export_settings.get("output_mode", "raster")).lower()
    design_export_raw = layout_data.get("design_export")
    design_export = design_export_raw if isinstance(design_export_raw, dict) else {}

    works = {w.get("id"): w for w in (layout_data.get("works", []) or [])}
    ref_to_idx, disenos = _build_designs(layout_data, job_dir, diseno_cls)
    engine_name = (layout_data.get("imposition_engine") or "repeat").lower()

    front_positions, front_crop = _positions_for_face(
        layout_data,
        "front",
        ref_to_idx,
        works,
        design_export,
        export_settings,
        bleed_default,
        bleed_layout,
        engine_name,
    )
    back_positions, back_crop = _positions_for_face(
        layout_data,
        "back",
        ref_to_idx,
        works,
        design_export,
        export_settings,
        bleed_default,
        bleed_layout,
        engine_name,
    )
    has_front = len(front_positions) > 0
    has_back = len(back_positions) > 0

    margin_left, margin_right, margin_top, margin_bottom = margins if len(margins) == 4 else (10, 10, 10, 10)
    preview_path = os.path.join(job_dir, "preview.png") if preview else None
    output_path = os.path.join(job_dir, "montaje_final.pdf")
    estrategia_nombre = _strategy_from_engine(layout_data)

    def _config_for_positions(
        posiciones: List[dict],
        crop_flag: bool,
        output: str,
        preview_target: str | None,
    ):
        modo_manual = bool(posiciones)
        return config_cls(
            tamano_pliego=tuple(sheet_mm),
            separacion=gap_default,
            margen_izquierdo=margin_left,
            margen_derecho=margin_right,
            margen_superior=margin_top,
            margen_inferior=margin_bottom,
            pinza_mm=gripper_mm if ctp_enabled else base_pinza_mm,
            sangrado=bleed_default,
            cutmarks_por_forma=crop_flag,
            posiciones_manual=posiciones if modo_manual else None,
            modo_manual=modo_manual,
            estrategia="manual" if modo_manual else estrategia_nombre,
            es_pdf_final=not preview,
            preview_path=preview_target,
            output_path=output,
            ctp_config=ctp_cfg,
            output_mode=output_mode,
        )

    if not disenos:
        if preview:
            return preview_path
        return output_path

    if preview:
        preview_positions = front_positions if has_front else back_positions
        preview_crop = front_crop if has_front else back_crop
        preview_config = _config_for_positions(preview_positions, preview_crop, output_path, preview_path)
        res = render_fn(disenos, preview_config)
        if isinstance(res, dict):
            return res.get("preview_path", preview_path)
        return preview_path

    if not has_back or not has_front:
        target_positions = front_positions if has_front else back_positions
        crop_flag = front_crop if has_front else back_crop
        config = _config_for_positions(target_positions, crop_flag, output_path, None)
        res = render_fn(disenos, config)
        if isinstance(res, dict):
            return res.get("output_path", output_path)
        if isinstance(res, str):
            return res
        return output_path

    front_output = os.path.join(job_dir, "montaje_front.pdf")
    back_output = os.path.join(job_dir, "montaje_back.pdf")

    front_config = _config_for_positions(front_positions, front_crop, front_output, None)
    back_config = _config_for_positions(back_positions, back_crop, back_output, None)

    front_res = render_fn(disenos, front_config)
    back_res = render_fn(disenos, back_config)

    front_path = _resolve_output_path(front_res, front_output)
    back_path = _resolve_output_path(back_res, back_output)

    writer = PdfWriter()
    for pdf_path in (front_path, back_path):
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            writer.add_page(page)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as fh:
        writer.write(fh)

    return output_path
