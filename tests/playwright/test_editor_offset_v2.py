from __future__ import annotations

from pathlib import Path
import threading

import fitz
import pytest
from flask import Flask
from werkzeug.serving import make_server

from editor_offset_v2.blueprint import init_editor_offset_v2


playwright_api = pytest.importorskip("playwright.sync_api")
expect = playwright_api.expect
sync_playwright = playwright_api.sync_playwright

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def v2_server(tmp_path):
    app = Flask(
        __name__,
        template_folder=str(REPO_ROOT / "templates"),
        static_folder=str(REPO_ROOT / "static"),
        instance_path=str(tmp_path / "instance"),
    )
    app.config.update(
        TESTING=True,
        EDITOR_OFFSET_V2_ENABLED=True,
        EDITOR_OFFSET_V2_JOBS_ROOT=str(tmp_path / "v2_jobs"),
    )
    init_editor_offset_v2(app)

    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _write_test_pdf(path: Path) -> None:
    document = fitz.open()
    page = document.new_page(width=255.118, height=141.732)
    page.set_trimbox(fitz.Rect(6, 6, 249, 135))
    page.insert_text((36, 70), "EDITOR OFFSET V2", fontsize=18)
    page.draw_rect(fitz.Rect(18, 18, 237, 123), color=(0.1, 0.4, 0.8), width=3)
    document.save(path)
    document.close()


def test_v2_visible_asset_work_slot_move_save_and_reload(v2_server, tmp_path):
    console_errors: list[str] = []
    page_errors: list[str] = []
    pdf_path = tmp_path / "diseño prueba.pdf"
    _write_test_pdf(pdf_path)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.on(
            "console",
            lambda message: console_errors.append(message.text)
            if message.type == "error" and "favicon" not in message.text.lower()
            else None,
        )
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        try:
            page.goto(
                f"{v2_server}/editor_offset_visual_v2",
                wait_until="domcontentloaded",
            )
            page.locator("#ev2-new-job").click()
            page.wait_for_url("**/editor_offset_visual_v2/ev2_*", timeout=10_000)
            expect(page.locator("#ev2-canvas")).to_be_visible()

            page.locator("#ev2-asset-file").set_input_files(str(pdf_path))
            with page.expect_response(
                lambda response: response.request.method == "POST"
                and "/assets" in response.url,
            ) as upload_info:
                page.locator("#ev2-asset-upload-button").click()
            assert upload_info.value.status == 201
            expect(page.locator(".ev2-asset-card")).to_have_count(1)
            expect(page.locator(".ev2-asset-pages img")).to_have_count(1)
            page.wait_for_function(
                "() => document.querySelector('.ev2-asset-pages img')?.naturalWidth > 0"
            )

            page.locator("#ev2-create-work").click()
            page.wait_for_function(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.works.length === 1"
            )
            page.locator("#ev2-create-real-slot").click()
            expect(page.locator(".ev2-svg-slot")).to_have_count(1)
            expect(page.locator(".ev2-svg-artwork")).to_have_count(1)
            original = page.evaluate(
                "() => structuredClone(window.__EDITOR_OFFSET_V2__.store.layout.slots[0].geometry.position_mm)"
            )

            slot = page.locator(".ev2-svg-slot").first
            box = slot.bounding_box()
            assert box is not None
            start_x = box["x"] + box["width"] / 2
            start_y = box["y"] + box["height"] / 2
            page.mouse.move(start_x, start_y)
            page.mouse.down()
            page.mouse.move(start_x + 70, start_y - 35, steps=8)
            page.mouse.up()
            page.wait_for_function(
                "(x) => window.__EDITOR_OFFSET_V2__.store.layout.slots[0].geometry.position_mm.x_mm !== x",
                arg=original["x_mm"],
            )
            moved = page.evaluate(
                "() => structuredClone(window.__EDITOR_OFFSET_V2__.store.layout.slots[0].geometry.position_mm)"
            )

            page.locator("#ev2-undo").click()
            assert page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.slots[0].geometry.position_mm"
            ) == original
            page.locator("#ev2-redo").click()
            assert page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.slots[0].geometry.position_mm"
            ) == moved

            page.evaluate("() => window.__EDITOR_OFFSET_V2__.saver.manualSave()")
            page.wait_for_function(
                "() => window.__EDITOR_OFFSET_V2__.store.saveState.status === 'clean'",
                timeout=10_000,
            )
            revision = int(page.locator("#ev2-revision").inner_text())
            assert revision >= 2

            page.reload(wait_until="domcontentloaded")
            expect(page.locator(".ev2-asset-card")).to_have_count(1)
            expect(page.locator(".ev2-svg-slot")).to_have_count(1)
            expect(page.locator(".ev2-svg-artwork")).to_have_count(1)
            persisted_counts = page.evaluate(
                "() => ({ assets: window.__EDITOR_OFFSET_V2__.store.layout.assets.length, "
                "works: window.__EDITOR_OFFSET_V2__.store.layout.works.length, "
                "slots: window.__EDITOR_OFFSET_V2__.store.layout.slots.length })"
            )
            assert persisted_counts == {"assets": 1, "works": 1, "slots": 1}
            persisted = page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.slots[0].geometry.position_mm"
            )
            assert persisted == moved
            assert not console_errors
            assert not page_errors
        finally:
            browser.close()
