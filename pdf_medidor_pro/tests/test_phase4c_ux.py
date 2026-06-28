from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_template() -> str:
    return (ROOT / "templates" / "pdf_medidor_pro.html").read_text(encoding="utf-8")


def read_controller() -> str:
    return (ROOT / "static" / "js" / "pdf_medidor_pro.js").read_text(encoding="utf-8")


def test_topbar_has_no_visible_tool_buttons_and_left_panel_keeps_tools():
    template = read_template()
    topbar = template.split('<section class="pmp-app-grid">', 1)[0]
    left_panel = template.split('<aside class="pmp-left-panel">', 1)[1].split("</aside>", 1)[0]

    assert "data-pmp-tool" not in topbar
    for tool in ["select", "hand", "line", "rectangle", "calibrate", "guides"]:
        assert f'data-pmp-tool="{tool}"' in left_panel


def test_auto_pdf_measurements_live_only_in_inspector():
    template = read_template()
    inspector = (ROOT / "static" / "js" / "inspector_panel.js").read_text(encoding="utf-8")

    assert "Medidas automaticas" not in template
    assert "pmp-auto-table" not in template
    for label in ["MediaBox", "CropBox", "TrimBox", "BleedBox", "ArtBox"]:
        assert label in inspector


def test_statusbar_and_shortcuts_are_available():
    template = read_template()
    controller = read_controller()

    for marker in ["pmp-statusbar", "pmp-status-tool", "pmp-status-zoom", "pmp-status-page", "pmp-status-coords"]:
        assert marker in template

    for shortcut in ['key === "h"', 'key === "l"', 'key === "r"', 'key === "c"', 'key === "g"']:
        assert shortcut in controller
    assert 'key === "v" || key === "s"' in controller


def test_space_pan_uses_delta_x_and_delta_y():
    controller = read_controller()

    assert "const deltaX = event.clientX - panning.x;" in controller
    assert "const deltaY = event.clientY - panning.y;" in controller
    assert "refs.viewer.scrollLeft = panning.left - deltaX;" in controller
    assert "refs.viewer.scrollTop = panning.top - deltaY;" in controller
    assert "event.preventDefault();" in controller
