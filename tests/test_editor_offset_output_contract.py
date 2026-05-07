from pathlib import Path
import os
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("OPENAI_API_KEY", "test")

from routes import _validate_constructor_output_layout


def _valid_layout():
    return {
        "designs": [
            {
                "ref": "file0",
                "filename": "pieza.pdf",
            }
        ],
        "works": [
            {
                "id": "work0",
            }
        ],
        "faces": ["front"],
        "slots": [
            {
                "id": "slot0",
                "x_mm": 10,
                "y_mm": 20,
                "w_mm": 100,
                "h_mm": 50,
                "bleed_mm": 3,
                "rotation_deg": 0,
                "design_ref": "file0",
                "logical_work_id": "work0",
                "face": "front",
            }
        ],
    }


def _codes(issues):
    return {issue["code"] for issue in issues}


def test_validate_constructor_output_layout_accepts_valid_layout():
    errors, warnings = _validate_constructor_output_layout(_valid_layout())

    assert errors == []
    assert warnings == []


def test_validate_constructor_output_layout_rejects_invalid_design_ref():
    layout = _valid_layout()
    layout["slots"][0]["design_ref"] = "missing"

    errors, warnings = _validate_constructor_output_layout(layout)

    assert "slot_design_ref_invalid" in _codes(errors)
    assert warnings == []


def test_validate_constructor_output_layout_rejects_duplicate_ids():
    layout = _valid_layout()
    layout["designs"].append({"ref": "file0", "filename": "duplicado.pdf"})
    layout["slots"].append({**layout["slots"][0], "id": "slot0"})

    errors, _warnings = _validate_constructor_output_layout(layout)

    assert "design_ref_duplicate" in _codes(errors)
    assert "slot_id_duplicate" in _codes(errors)


def test_validate_constructor_output_layout_rejects_missing_numeric_fields():
    layout = _valid_layout()
    del layout["slots"][0]["x_mm"]

    errors, warnings = _validate_constructor_output_layout(layout)

    assert "slot_field_missing" in _codes(errors)
    assert any(issue["path"] == "slots[0].x_mm" for issue in errors)
    assert warnings == []


def test_validate_constructor_output_layout_rejects_invalid_face():
    layout = _valid_layout()
    layout["slots"][0]["face"] = "retira"

    errors, warnings = _validate_constructor_output_layout(layout)

    assert "slot_face_invalid" in _codes(errors)
    assert warnings == []


def test_validate_constructor_output_layout_warns_unresolved_logical_work_id():
    layout = _valid_layout()
    layout["slots"][0]["logical_work_id"] = "missing-work"

    errors, warnings = _validate_constructor_output_layout(layout)

    assert errors == []
    assert "slot_work_unresolved" in _codes(warnings)


def test_validate_constructor_output_layout_warns_back_face_without_slots():
    layout = _valid_layout()
    layout["faces"] = ["front", "back"]

    errors, warnings = _validate_constructor_output_layout(layout)

    assert errors == []
    assert "back_face_without_slots" in _codes(warnings)
