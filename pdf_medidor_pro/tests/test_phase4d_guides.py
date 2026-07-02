from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_js(name: str) -> str:
    return (ROOT / "static" / "js" / name).read_text(encoding="utf-8")


def test_viewer_supports_selectable_guides():
    viewer = read_js("viewer.js")

    assert "drawGuides(guides, selectedGuideId)" in viewer
    assert "hitTestGuide(pointMm, guides, threshold)" in viewer
    assert 'return { id: guide.id, action: "move-guide", orientation: "vertical" }' in viewer
    assert 'return { id: guide.id, action: "move-guide", orientation: "horizontal" }' in viewer


def test_controller_tracks_selected_guide_and_drag_editing():
    controller = read_js("pdf_medidor_pro.js")

    assert "selectedGuideId: null" in controller
    assert "guideEditing: null" in controller
    assert "viewer.hitTestGuide(point, state.guides, 8)" in controller
    assert "state.selectedMeasurementId = null;" in controller
    assert "replaceGuide(ns.guides.moveGuide(original, position));" in controller


def test_delete_and_nudge_prioritize_selected_guide():
    controller = read_js("pdf_medidor_pro.js")

    assert "if (state.selectedGuideId)" in controller
    assert "deleteGuide(state.selectedGuideId);" in controller
    assert "const guide = currentSelectedGuide();" in controller
    assert 'setStatus(`Nudge guia ${fmt(step)} mm.`);' in controller


def test_undo_snapshots_include_guides_without_export_contract_changes():
    undo = read_js("undo_redo.js")
    exporter = read_js("export.js")

    assert "guides: clone(state && state.guides ? state.guides : [])" in undo
    assert "selectedGuideId: state && state.selectedGuideId ? state.selectedGuideId : null" in undo
    assert '"guias"' not in exporter.lower()


def test_no_ai_references_return_with_editable_guides():
    combined = "\n".join(
        read_js(name)
        for name in ["pdf_medidor_pro.js", "viewer.js", "guides.js", "inspector_panel.js"]
    ).lower()

    assert "ai_measure" not in combined
    assert "commands_ai" not in combined
    assert "medir con ia" not in combined
