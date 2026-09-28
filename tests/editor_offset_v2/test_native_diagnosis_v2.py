"""Characterize native findings before separating their historical DTO dependency."""
import copy
from dataclasses import FrozenInstanceError
import json
from pathlib import Path

import pytest

from editor_offset_v2.application.native_output_capabilities import native_output_issues
from editor_offset_v2.web_app import create_app


def native_layout():
    path = Path(__file__).resolve().parents[1] / "fixtures/editor_offset_v2/layout_v2_complete.json"
    layout = json.loads(path.read_text(encoding="utf-8"))
    layout["slots"] = [layout["slots"][0]]
    layout["faces"] = {"enabled": ["front"], "duplex": {"enabled": False, "flip": "none"}}
    layout["export"]["faces"] = {"front": True, "back": False, "combine_in_single_pdf": False, "order": ["front"]}
    layout["slots"][0]["geometry"]["bleed_mm"] = 0
    layout["slots"][0]["content_transform"]["clip_to"] = "trim_box"
    for profile in layout["export"]["marks_profiles"]:
        profile.update(crop_marks=False, registration_marks=False, technical_text=False, color_bar=False)
    layout["ctp"]["enabled"] = False
    return layout


@pytest.mark.parametrize("variant,code,blocks,level", [
    ("scale", None, [], None),
    ("clip", "UNSUPPORTED_CONTENT_CLIP", ["preview", "pdf_final"], "error"),
    ("bleed_clip", "BLEED_CLIPPED_TO_TRIM", ["pdf_final"], "error"),
    ("crop_zero", "CROP_MARKS_OMITTED_NO_BLEED", [], "warning"),
    ("preview_budget", "PREVIEW_RESOURCE_LIMIT", ["preview"], "error"),
    ("raster_vector", "OUTPUT_PROFILE_CONFLICT", ["pdf_final"], "error"),
    ("ctp", "CTP_NOT_SUPPORTED", ["preview", "pdf_final"], "error"),
    ("registration", "PREVIEW_MARKS_UNSUPPORTED", ["preview", "pdf_final"], "error"),
])
def test_native_findings_keep_operation_scope_and_layout_unchanged(variant, code, blocks, level):
    layout = native_layout()
    slot = layout["slots"][0]
    if variant == "scale": slot["content_transform"]["scale_x"] = .75
    elif variant == "clip": slot["content_transform"]["clip_to"] = "none"
    elif variant == "bleed_clip": slot["geometry"]["bleed_mm"] = 3
    elif variant == "crop_zero": layout["export"]["marks_profiles"][0]["crop_marks"] = True
    elif variant == "preview_budget": layout["sheet"]["size_mm"] = {"width": 2000, "height": 2000}
    elif variant == "raster_vector": layout["export"].update(render_mode="raster", preserve_vector_content=True)
    elif variant == "ctp": layout["ctp"]["enabled"] = True
    elif variant == "registration": layout["export"]["marks_profiles"][0]["registration_marks"] = True
    before = copy.deepcopy(layout)
    findings = native_output_issues(layout)
    assert layout == before
    assert [(item.code, operations, item.level) for item, operations in findings] == (
        [(code, blocks, level)] if code else [])
    if code in ("UNSUPPORTED_CONTENT_CLIP", "BLEED_CLIPPED_TO_TRIM", "CROP_MARKS_OMITTED_NO_BLEED", "PREVIEW_MARKS_UNSUPPORTED"):
        issue = findings[0][0].as_dict()
        assert issue["slot_id"] == slot["id"] and issue["asset_id"] == slot["source"]["asset_id"]
        assert issue["path"].startswith("$.slots[0]")


def test_native_issue_is_immutable_and_serializes_without_historical_contract():
    from editor_offset_v2.domain.native_output_contract import NativeOutputIssue
    issue = NativeOutputIssue("TEST", "warning", "Review", path="$.slots", slot_id="s", asset_id="a")
    assert issue.as_dict() == {"code": "TEST", "level": "warning", "message": "Review",
                               "path": "$.slots", "slot_id": "s", "asset_id": "a"}
    assert NativeOutputIssue("TEST", "error", "Blocked").as_dict() == {
        "code": "TEST", "level": "error", "message": "Blocked"}
    with pytest.raises(FrozenInstanceError): issue.code = "changed"
    for args in (("", "error", "Message"), ("TEST", "info", "Message"), ("TEST", "error", "")):
        with pytest.raises(ValueError): NativeOutputIssue(*args)
    layout = native_layout()
    layout["slots"][0]["content_transform"]["clip_to"] = "none"
    assert isinstance(native_output_issues(layout)[0][0], NativeOutputIssue)


def test_capabilities_endpoint_is_native_read_only_and_does_not_certify_source_files(tmp_path):
    app = create_app({"TESTING": True, "EDITOR_OFFSET_V2_JOBS_ROOT": str(tmp_path),
                      "EDITOR_OFFSET_V2_DEV_TOOLS_ENABLED": False})
    client = app.test_client()
    created = client.post("/api/editor-offset-v2/jobs", json={"name": "Native diagnostic"}).json
    layout = native_layout()
    layout["job"] = created["layout"]["job"]
    api = "/api/editor-offset-v2/jobs/" + created["job_id"]
    saved = client.put(api + "/layout", json={"base_revision": 1, "layout": layout})
    assert saved.status_code == 200, saved.json
    files = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    response = client.get(api + "/output-capabilities")
    assert response.status_code == 200
    body = response.json
    assert body["diagnostic_source"] == "native-v2"
    assert body["diagnostic_contract_version"] == 1
    assert body["diagnostic_scope"] == "renderer_capabilities"
    assert body["requires_preflight"] is True
    assert body["compatible"] is True and body["errors"] == []
    assert body["revision"] == saved.json["revision"]
    assert files == {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    # No physical PDF was uploaded: a capabilities check must not pretend to approve output.
    report = client.post(api + "/preflight", json={"dpi": 36})
    assert report.status_code == 201
    assert any(item["severity"] == "error" for item in report.json["report"]["issues"])
    # Preflight writes its report; capabilities must not write anything.
    assert files == {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file() and "reports" not in p.parts}
    shell = client.get("/editor_offset_visual_v2/" + created["job_id"]).text
    start = shell.index('<script id="editor-offset-v2-context" type="application/json">')
    context = json.loads(shell[shell.index(">", start)+1:shell.index("</script>", start)])
    assert "output_capabilities_api_url" not in context
