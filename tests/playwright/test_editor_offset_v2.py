from __future__ import annotations

from pathlib import Path
import threading

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


def test_v2_visible_create_move_undo_redo_save_and_reload(v2_server):
    console_errors: list[str] = []
    page_errors: list[str] = []

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

            page.locator("#ev2-create-slot").click()
            expect(page.locator(".ev2-svg-slot")).to_have_count(1)
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
            expect(page.locator(".ev2-svg-slot")).to_have_count(1)
            persisted = page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.slots[0].geometry.position_mm"
            )
            assert persisted == moved
            assert not console_errors
            assert not page_errors
        finally:
            browser.close()
