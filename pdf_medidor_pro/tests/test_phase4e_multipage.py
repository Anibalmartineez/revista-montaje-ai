from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_template() -> str:
    return (ROOT / "templates" / "pdf_medidor_pro.html").read_text(encoding="utf-8")


def read_js(name: str) -> str:
    return (ROOT / "static" / "js" / name).read_text(encoding="utf-8")


def test_template_contains_multipage_navigation_controls():
    template = read_template()

    for marker in ["pmp-prev-page", "pmp-page-input", "pmp-page-total", "pmp-next-page"]:
        assert marker in template


def test_controller_tracks_pages_and_calls_render_page_endpoint():
    controller = read_js("pdf_medidor_pro.js")

    assert "storedFilename" in controller
    assert "pages: {}" in controller
    assert "saveActivePage()" in controller
    assert "applyPageState(target" in controller
    assert 'fetch(`${apiBase}/render-page`' in controller
    assert "stored_filename: state.storedFilename" in controller


def test_controller_exports_pages_but_png_uses_active_page_only():
    controller = read_js("pdf_medidor_pro.js")
    exporter = read_js("export.js")

    assert "collectPageExports()" in controller
    assert "pageExport(page, data)" in controller
    assert "ns.buildExportPayload(state, active.medidas_manual, measurements, pages)" in controller
    assert "measurements: state.measurements" in controller
    assert "guides: state.guides" in controller
    assert "payload.paginas = pages" in exporter
    assert "payload.page_count = state.pageCount" in exporter


def test_no_ai_references_in_multipage_frontend():
    combined = "\n".join(
        read_js(name)
        for name in ["pdf_medidor_pro.js", "export.js"]
    ).lower()

    assert "ai_measure" not in combined
    assert "commands_ai" not in combined
    assert "medir con ia" not in combined
