import math
from typing import Dict, List


def _layout_issue(level: str, code: str, message: str, path: str | None = None, **extra) -> Dict:
    issue = {
        "level": level,
        "code": code,
        "message": message,
    }
    if path:
        issue["path"] = path
    issue.update(extra)
    return issue


def validate_constructor_output_layout(layout: Dict) -> tuple[List[Dict], List[Dict]]:
    errors: List[Dict] = []
    warnings: List[Dict] = []

    if not isinstance(layout, dict):
        errors.append(
            _layout_issue(
                "error",
                "layout_invalid",
                "El layout persistido no tiene una estructura JSON válida.",
                path="layout",
            )
        )
        return errors, warnings

    designs = layout.get("designs") or []
    works = layout.get("works") or []
    slots = layout.get("slots") or []
    faces = layout.get("faces") or []

    design_refs: Dict[str, int] = {}
    for idx, design in enumerate(designs):
        if not isinstance(design, dict):
            errors.append(
                _layout_issue(
                    "error",
                    "design_invalid",
                    "Cada diseño debe ser un objeto JSON válido.",
                    path=f"designs[{idx}]",
                )
            )
            continue

        ref = design.get("ref")
        if ref is None or str(ref).strip() == "":
            errors.append(
                _layout_issue(
                    "error",
                    "design_ref_missing",
                    "Cada diseño debe tener un ref no vacío para poder enlazar slots.",
                    path=f"designs[{idx}].ref",
                )
            )
            continue

        ref_key = str(ref)
        if ref_key in design_refs:
            errors.append(
                _layout_issue(
                    "error",
                    "design_ref_duplicate",
                    f"El ref de diseño '{ref_key}' está duplicado.",
                    path=f"designs[{idx}].ref",
                    duplicate_of=f"designs[{design_refs[ref_key]}].ref",
                )
            )
        else:
            design_refs[ref_key] = idx

    work_ids = {
        str(work.get("id")) for work in works if isinstance(work, dict) and work.get("id") is not None
    }

    slot_ids: Dict[str, int] = {}
    allowed_faces = {"front", "back"}

    def _require_numeric(slot: Dict, slot_idx: int, field: str) -> float | None:
        raw = slot.get(field)
        if raw is None or raw == "":
            errors.append(
                _layout_issue(
                    "error",
                    "slot_field_missing",
                    f"El campo '{field}' del slot es obligatorio para la salida.",
                    path=f"slots[{slot_idx}].{field}",
                )
            )
            return None
        try:
            value = float(raw)
        except (TypeError, ValueError):
            errors.append(
                _layout_issue(
                    "error",
                    "slot_field_not_numeric",
                    f"El campo '{field}' del slot debe ser numérico.",
                    path=f"slots[{slot_idx}].{field}",
                    value=raw,
                )
            )
            return None
        if not math.isfinite(value):
            errors.append(
                _layout_issue(
                    "error",
                    "slot_field_not_finite",
                    f"El campo '{field}' del slot debe ser un número finito.",
                    path=f"slots[{slot_idx}].{field}",
                    value=raw,
                )
            )
            return None
        return value

    has_back_slot = False
    for idx, slot in enumerate(slots):
        if not isinstance(slot, dict):
            errors.append(
                _layout_issue(
                    "error",
                    "slot_invalid",
                    "Cada slot debe ser un objeto JSON válido.",
                    path=f"slots[{idx}]",
                )
            )
            continue

        slot_id = slot.get("id")
        if slot_id is None or str(slot_id).strip() == "":
            errors.append(
                _layout_issue(
                    "error",
                    "slot_id_missing",
                    "Cada slot debe tener un id no vacío.",
                    path=f"slots[{idx}].id",
                )
            )
        else:
            slot_id_key = str(slot_id)
            if slot_id_key in slot_ids:
                errors.append(
                    _layout_issue(
                        "error",
                        "slot_id_duplicate",
                        f"El id de slot '{slot_id_key}' está duplicado.",
                        path=f"slots[{idx}].id",
                        duplicate_of=f"slots[{slot_ids[slot_id_key]}].id",
                    )
                )
            else:
                slot_ids[slot_id_key] = idx

        face_raw = slot.get("face")
        face = str(face_raw or "front").lower()
        if face not in allowed_faces:
            errors.append(
                _layout_issue(
                    "error",
                    "slot_face_invalid",
                    "El campo face del slot debe ser 'front' o 'back'.",
                    path=f"slots[{idx}].face",
                    value=face_raw,
                )
            )
        if face == "back":
            has_back_slot = True

        _require_numeric(slot, idx, "x_mm")
        _require_numeric(slot, idx, "y_mm")
        w_val = _require_numeric(slot, idx, "w_mm")
        h_val = _require_numeric(slot, idx, "h_mm")
        _require_numeric(slot, idx, "bleed_mm")
        _require_numeric(slot, idx, "rotation_deg")

        if w_val is not None and w_val <= 0:
            errors.append(
                _layout_issue(
                    "error",
                    "slot_width_invalid",
                    "El ancho del slot debe ser mayor que 0.",
                    path=f"slots[{idx}].w_mm",
                    value=w_val,
                )
            )
        if h_val is not None and h_val <= 0:
            errors.append(
                _layout_issue(
                    "error",
                    "slot_height_invalid",
                    "El alto del slot debe ser mayor que 0.",
                    path=f"slots[{idx}].h_mm",
                    value=h_val,
                )
            )

        design_ref = slot.get("design_ref")
        if not design_ref or str(design_ref) not in design_refs:
            errors.append(
                _layout_issue(
                    "error",
                    "slot_design_ref_invalid",
                    "Cada slot debe apuntar a un design_ref existente en designs[].ref.",
                    path=f"slots[{idx}].design_ref",
                    value=design_ref,
                )
            )

        logical_work_id = slot.get("logical_work_id")
        if logical_work_id is not None and str(logical_work_id) not in work_ids:
            warnings.append(
                _layout_issue(
                    "warning",
                    "slot_work_unresolved",
                    "El logical_work_id del slot no resuelve contra works[].id. Se usarán defaults del layout.",
                    path=f"slots[{idx}].logical_work_id",
                    value=logical_work_id,
                )
            )

    if "back" in {str(face).lower() for face in faces} and not has_back_slot:
        warnings.append(
            _layout_issue(
                "warning",
                "back_face_without_slots",
                "El layout declara la cara 'back' en faces[], pero no hay slots con face='back'.",
                path="faces",
            )
        )

    return errors, warnings
