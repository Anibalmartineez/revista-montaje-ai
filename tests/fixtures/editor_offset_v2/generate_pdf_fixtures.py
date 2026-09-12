"""Generate the canonical PDF inputs used by the V2 parity tests.

The files are intentionally small, asymmetric and self-contained.  They are
test inputs, not production artwork.  Run this module from the repository root
when a fixture must be regenerated after an intentional contract change.
"""

from __future__ import annotations

import json
from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parent
POINT_TO_MM = 25.4 / 72.0


def _set_box(page: fitz.Page, name: str, rect: tuple[float, float, float, float]) -> None:
    page.parent.xref_set_key(page.xref, name, "[" + " ".join(str(value) for value in rect) + "]")


def _document(title: str) -> fitz.Document:
    document = fitz.open()
    document.set_metadata({
        "format": "PDF 1.7",
        "title": title,
        "author": "Editor Offset V2 fixture",
        "creationDate": "D:20200101000000Z",
        "modDate": "D:20200101000000Z",
    })
    return document


def _draw_artwork(page: fitz.Page, label: str) -> None:
    page.insert_text((18, 28), label, fontsize=12, color=(0.05, 0.1, 0.3))
    page.draw_rect(fitz.Rect(18, 38, page.rect.width - 18, page.rect.height - 18), color=(0.1, 0.4, 0.8), width=2)
    page.draw_circle((page.rect.width - 30, 28), 8, color=(0.8, 0.1, 0.1), fill=(0.95, 0.75, 0.1), width=2)


def _save(document: fitz.Document, name: str) -> None:
    target = ROOT / name
    document.save(target, garbage=4, deflate=False, no_new_id=True)
    document.close()


def _case(name: str, title: str, pages: list[dict[str, object]]) -> dict[str, object]:
    return {"file": name, "title": title, "pages": pages}


def _box(rect: tuple[float, float, float, float]) -> dict[str, float]:
    x0, y0, x1, y1 = rect
    return {
        "x": round(x0 * POINT_TO_MM, 6),
        "y": round(y0 * POINT_TO_MM, 6),
        "width": round((x1 - x0) * POINT_TO_MM, 6),
        "height": round((y1 - y0) * POINT_TO_MM, 6),
    }


def main() -> None:
    manifest: dict[str, object] = {
        "schema_version": 1,
        "unit": "mm",
        "point_to_mm": POINT_TO_MM,
        "cases": [],
    }

    all_boxes = {
        "media": (0, 0, 240, 140),
        "crop": (5, 7, 235, 133),
        "trim": (15, 17, 225, 123),
        "bleed": (10, 12, 230, 128),
    }
    document = _document("EV2 boxes offset")
    page = document.new_page(width=240, height=140)
    _draw_artwork(page, "BOXES-OFFSET")
    for key in ("crop", "trim", "bleed"):
        _set_box(page, key.title() + "Box", all_boxes[key])
    _save(document, "boxes-offset.pdf")
    manifest["cases"].append(_case(
        "boxes-offset.pdf", "EV2 boxes offset", [{
            "rotation": 0,
            "boxes": {key: _box(value) for key, value in all_boxes.items()},
        }],
    ))

    media = (0, 0, 240, 140)
    crop_only = (5, 7, 235, 133)
    document = _document("EV2 missing trim and bleed")
    page = document.new_page(width=240, height=140)
    _draw_artwork(page, "MISSING-TRIM-BLEED")
    _set_box(page, "CropBox", crop_only)
    _save(document, "boxes-missing.pdf")
    manifest["cases"].append(_case(
        "boxes-missing.pdf", "EV2 missing trim and bleed", [{
            "rotation": 0,
            "boxes": {"media": _box(media), "crop": _box(crop_only), "trim": None, "bleed": None},
        }],
    ))

    rotation_pages: list[dict[str, object]] = []
    document = _document("EV2 multipage rotations")
    for index, rotation in enumerate((0, 90, 180), start=1):
        page = document.new_page(width=240, height=140)
        _draw_artwork(page, f"MULTIPAGE-{index}-ROT-{rotation}")
        _set_box(page, "CropBox", (4, 4, 236, 136))
        if index != 2:
            _set_box(page, "TrimBox", (12, 10, 228, 130))
            _set_box(page, "BleedBox", (8, 6, 232, 134))
        page.set_rotation(rotation)
        rotation_pages.append({
            "rotation": rotation,
            "boxes": {
                "media": _box(media),
                "crop": _box((4, 4, 236, 136)),
                "trim": _box((12, 10, 228, 130)) if index != 2 else None,
                "bleed": _box((8, 6, 232, 134)) if index != 2 else None,
            },
        })
    _save(document, "multipage-rotations.pdf")
    manifest["cases"].append(_case("multipage-rotations.pdf", "EV2 multipage rotations", rotation_pages))

    marks = {
        "media": (0, 0, 300, 180),
        "crop": (10, 10, 290, 170),
        "trim": (30, 25, 270, 155),
        "bleed": (20, 15, 280, 165),
    }
    document = _document("EV2 marks and clipping")
    page = document.new_page(width=300, height=180)
    _draw_artwork(page, "MARKS-CLIP")
    for key in ("crop", "trim", "bleed"):
        _set_box(page, key.title() + "Box", marks[key])
    for x, y in ((30, 25), (270, 25), (30, 155), (270, 155)):
        page.draw_line((x - 12, y), (x + 12, y), color=(0, 0, 0), width=0.7)
        page.draw_line((x, y - 12), (x, y + 12), color=(0, 0, 0), width=0.7)
    _save(document, "marks-clipping.pdf")
    manifest["cases"].append(_case(
        "marks-clipping.pdf", "EV2 marks and clipping", [{
            "rotation": 0,
            "boxes": {key: _box(value) for key, value in marks.items()},
            "artwork": {"crop_marks": True, "asymmetric": True},
        }],
    ))

    mirror = {
        "media": (0, 0, 240, 140),
        "crop": (0, 0, 240, 140),
    }
    document = _document("EV2 mirror bleed candidate")
    page = document.new_page(width=240, height=140)
    _draw_artwork(page, "MIRROR-BLEED-CANDIDATE")
    _set_box(page, "CropBox", mirror["crop"])
    _save(document, "mirror-bleed-candidate.pdf")
    manifest["cases"].append(_case(
        "mirror-bleed-candidate.pdf", "EV2 mirror bleed candidate", [{
            "rotation": 0,
            "boxes": {"media": _box(mirror["media"]), "crop": _box(mirror["crop"]), "trim": None, "bleed": None},
            "bleed_policy": "mirror_explicit_option",
            "requires_future_stage": True,
        }],
    ))

    document = _document("EV2 front back flip")
    face_pages: list[dict[str, object]] = []
    for face, flip, label in (
        ("front", "none", "FRONT-FACE"),
        ("back", "horizontal", "BACK-FACE-FLIP-H")
    ):
        page = document.new_page(width=240, height=140)
        _draw_artwork(page, label)
        _set_box(page, "CropBox", (0, 0, 240, 140))
        _set_box(page, "TrimBox", (12, 10, 228, 130))
        _set_box(page, "BleedBox", (8, 6, 232, 134))
        face_pages.append({
            "rotation": 0,
            "face": face,
            "flip": flip,
            "boxes": {
                "media": _box(media),
                "crop": _box((0, 0, 240, 140)),
                "trim": _box((12, 10, 228, 130)),
                "bleed": _box((8, 6, 232, 134)),
            },
            "content_transform": {
                "rotation_deg": 90 if face == "back" else 0,
                "offset_mm": {"x": 1.5 if face == "back" else 0.0, "y": -2.0 if face == "back" else 0.0},
                "clip_to": "trim",
            },
        })
    _save(document, "front-back-flip.pdf")
    manifest["cases"].append(_case(
        "front-back-flip.pdf", "EV2 front back flip", face_pages,
    ))

    (ROOT / "pdf_fixture_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
