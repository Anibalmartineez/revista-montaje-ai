from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_phase3_template_exposes_professional_workspace_controls():
    template = (ROOT / "templates" / "pdf_medidor_pro.html").read_text(encoding="utf-8")

    required = [
        "pmp-topbar",
        "pmp-left-panel",
        "pmp-viewer-panel",
        "pmp-right-panel",
        "pmp-history-panel",
        "pmp-inspector",
        "pmp-history",
        "pmp-export-png-button",
        "data-pmp-tool=\"select\"",
        "data-pmp-tool=\"guides\"",
        "js/object_model.js",
        "js/inspector_panel.js",
        "js/history_panel.js",
        "js/png_export.js",
    ]

    for marker in required:
        assert marker in template


def test_phase3_styles_keep_app_layout_sections():
    css = (ROOT / "static" / "css" / "pdf_medidor_pro.css").read_text(encoding="utf-8")

    for marker in [
        ".pmp-shell",
        ".pmp-topbar",
        ".pmp-app-grid",
        ".pmp-left-panel",
        ".pmp-right-panel",
        ".pmp-history-table",
        ".pmp-magnifier",
    ]:
        assert marker in css
