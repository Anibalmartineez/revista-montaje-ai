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


def _open_job_with_repeat(page, server_url: str, pdf_path: Path, quantity: int = 2) -> None:
    page.goto(f"{server_url}/editor_offset_visual_v2", wait_until="domcontentloaded")
    page.locator("#ev2-new-job").click()
    page.wait_for_url("**/editor_offset_visual_v2/ev2_*", timeout=10_000)
    page.locator("#ev2-asset-file").set_input_files(str(pdf_path))
    with page.expect_response(
        lambda response: response.request.method == "POST" and "/assets" in response.url,
    ):
        page.locator("#ev2-asset-upload-button").click()
    expect(page.locator(".ev2-asset-card")).to_have_count(1)
    page.locator("#ev2-work-quantity").fill(str(quantity))
    page.locator("#ev2-create-work").click()
    page.wait_for_function(
        "() => window.__EDITOR_OFFSET_V2__.store.layout.works.length === 1"
    )
    with page.expect_response(
        lambda response: response.request.method == "POST"
        and "/imposition/repeat" in response.url,
    ):
        page.locator("#ev2-repeat-calculate").click()
    page.wait_for_function(
        "() => window.__EDITOR_OFFSET_V2__.store.repeatPanel.status === 'ready'"
    )
    page.locator("#ev2-repeat-apply").click()
    expect(page.locator(".ev2-svg-slot")).to_have_count(quantity)


def test_v2_visible_repeat_calculate_apply_undo_redo_save_and_reload(v2_server, tmp_path):
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

            page.locator("#ev2-work-quantity").fill("4")
            page.locator("#ev2-create-work").click()
            page.wait_for_function(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.works.length === 1"
            )

            page.locator("#ev2-repeat-gap-x").fill("4")
            page.locator("#ev2-repeat-gap-y").fill("3")
            with page.expect_response(
                lambda response: response.request.method == "POST"
                and "/imposition/repeat" in response.url,
            ) as repeat_info:
                page.locator("#ev2-repeat-calculate").click()
            assert repeat_info.value.status == 200
            page.wait_for_function(
                "() => window.__EDITOR_OFFSET_V2__.store.repeatPanel.status === 'ready'"
            )
            expect(page.locator("#ev2-repeat-summary")).to_be_visible()
            expect(page.locator("#ev2-repeat-requested")).to_have_text("4")
            expect(page.locator("#ev2-repeat-placed")).to_have_text("4")

            page.locator("#ev2-repeat-apply").click()
            expect(page.locator(".ev2-svg-slot")).to_have_count(4)
            expect(page.locator(".ev2-svg-artwork")).to_have_count(4)
            assert page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.imposition.last_result.operation_id"
            ).startswith("repeat_")
            assert page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.slots.every("
                "slot => slot.locks.geometry.length === 0 "
                "&& slot.generated_by.engine === 'repeat')"
            )

            first_slot = page.locator(".ev2-svg-slot").first
            box = first_slot.bounding_box()
            assert box is not None
            before_move = page.evaluate(
                "() => ({ ...window.__EDITOR_OFFSET_V2__.store.layout.slots[0].geometry.position_mm })"
            )
            page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            page.mouse.down()
            page.mouse.move(box["x"] + box["width"] / 2 + 28, box["y"] + box["height"] / 2 - 14)
            page.mouse.up()
            page.wait_for_function(
                "before => window.__EDITOR_OFFSET_V2__.store.layout.slots[0].geometry.position_mm.x_mm !== before.x_mm",
                arg=before_move,
            )
            moved_position = page.evaluate(
                "() => ({ ...window.__EDITOR_OFFSET_V2__.store.layout.slots[0].geometry.position_mm })"
            )

            page.locator("#ev2-undo").click()
            assert page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.slots[0].geometry.position_mm.x_mm"
            ) == pytest.approx(before_move["x_mm"])
            page.locator("#ev2-redo").click()
            assert page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.slots[0].geometry.position_mm.x_mm"
            ) == pytest.approx(moved_position["x_mm"])

            page.evaluate("() => window.__EDITOR_OFFSET_V2__.saver.manualSave()")
            page.wait_for_function(
                "() => window.__EDITOR_OFFSET_V2__.store.saveState.status === 'clean'",
                timeout=10_000,
            )
            revision = int(page.locator("#ev2-revision").inner_text())
            assert revision >= 4

            page.reload(wait_until="domcontentloaded")
            expect(page.locator(".ev2-asset-card")).to_have_count(1)
            expect(page.locator(".ev2-svg-slot")).to_have_count(4)
            expect(page.locator(".ev2-svg-artwork")).to_have_count(4)
            persisted_counts = page.evaluate(
                "() => ({ assets: window.__EDITOR_OFFSET_V2__.store.layout.assets.length, "
                "works: window.__EDITOR_OFFSET_V2__.store.layout.works.length, "
                "slots: window.__EDITOR_OFFSET_V2__.store.layout.slots.length })"
            )
            assert persisted_counts == {"assets": 1, "works": 1, "slots": 4}
            assert page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.imposition.last_result.placed"
            ) == 4
            assert page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.slots[0].geometry.position_mm.x_mm"
            ) == pytest.approx(moved_position["x_mm"])
            assert page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.slots[0].generated_by.engine"
            ) == "repeat"
            assert not console_errors
            assert not page_errors
        finally:
            browser.close()


def test_v2_locks_block_drag_delete_and_source_replacement_atomically(v2_server, tmp_path):
    pdf_path = tmp_path / "locks.pdf"
    _write_test_pdf(pdf_path)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        try:
            _open_job_with_repeat(page, v2_server, pdf_path, quantity=2)
            first_slot = page.locator(".ev2-svg-slot").first
            slot_id = page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.slots[0].id"
            )
            page.evaluate(
                "slotId => window.__EDITOR_OFFSET_V2__.store.setSelection([slotId], 'replace')",
                slot_id,
            )
            before = page.evaluate(
                "() => ({ ...window.__EDITOR_OFFSET_V2__.store.layout.slots[0].geometry.position_mm })"
            )
            page.evaluate(
                "() => { const store = window.__EDITOR_OFFSET_V2__.store; "
                "store.layout.slots[0].locks.geometry = ['system']; "
                "store.emit('external_update'); }"
            )
            box = first_slot.bounding_box()
            assert box is not None
            page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            page.mouse.down()
            page.mouse.move(box["x"] + box["width"] / 2 + 30, box["y"] + box["height"] / 2)
            page.mouse.up()
            after = page.evaluate(
                "() => ({ ...window.__EDITOR_OFFSET_V2__.store.layout.slots[0].geometry.position_mm })"
            )
            assert after == before
            expect(page.locator("#ev2-status-message")).to_contain_text(slot_id)

            page.evaluate(
                "() => { const store = window.__EDITOR_OFFSET_V2__.store; "
                "store.layout.slots[0].locks.geometry = []; "
                "store.layout.slots[0].locks.delete = ['user']; "
                "store.emit('external_update'); }"
            )
            expect(page.locator("#ev2-delete-slots")).to_be_disabled()
            page.keyboard.press("Delete")
            assert page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.slots.length"
            ) == 2
            expect(page.locator("#ev2-status-message")).to_contain_text(slot_id)

            source_before = page.evaluate(
                "() => ({ ...window.__EDITOR_OFFSET_V2__.store.layout.slots[0].source })"
            )
            page.evaluate(
                "() => { const store = window.__EDITOR_OFFSET_V2__.store; "
                "store.layout.slots[0].locks.content = ['ctp']; "
                "store.emit('external_update'); }"
            )
            expect(page.locator("#ev2-replace-source")).to_be_disabled()
            assert page.evaluate(
                "() => ({ ...window.__EDITOR_OFFSET_V2__.store.layout.slots[0].source })"
            ) == source_before
        finally:
            browser.close()


def test_v2_visual_semantics_printable_output_and_approximate_artwork(v2_server, tmp_path):
    pdf_path = tmp_path / "visual-state.pdf"
    _write_test_pdf(pdf_path)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        try:
            _open_job_with_repeat(page, v2_server, pdf_path, quantity=2)
            expect(page.locator("[data-printable-area='true']")).to_have_count(1)
            expect(page.locator("#ev2-create-slot")).to_have_count(0)
            assert page.locator(
                "#ev2-repeat-face option[value='back']"
            ).evaluate("option => option.disabled") is True
            expect(page.locator(".ev2-approximate-artwork")).to_have_count(2)
            expect(page.locator("#ev2-repeat-history")).to_contain_text(
                "Resultado al aplicar la última imposición"
            )
            expect(page.locator("#ev2-repeat-current-face")).to_have_text("2")

            page.evaluate(
                "() => { const store = window.__EDITOR_OFFSET_V2__.store; "
                "const slot = store.layout.slots[0]; "
                "store.layout.sheet.printable_margins_mm.left = 60; "
                "const half = slot.geometry.trim_size_mm.width / 2 + slot.geometry.bleed_mm; "
                "slot.geometry.position_mm.x_mm = half + 1; "
                "slot.content_transform.scale_x = 0.9; "
                "store.markChanged(); store.emit('external_update'); }"
            )
            expect(page.locator(".ev2-svg-slot.is-outside-printable")).to_have_count(1)
            page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.setSelection("
                "[window.__EDITOR_OFFSET_V2__.store.layout.slots[0].id], 'replace')"
            )
            expect(page.locator("#ev2-inspector-values")).to_contain_text(
                "Fuera del área imprimible"
            )
            expect(page.locator("#ev2-inspector-values")).to_contain_text(
                "Vista aproximada del PDF"
            )

            with page.expect_response(
                lambda response: response.request.method == "GET"
                and "/output-capabilities" in response.url,
            ):
                page.locator("#ev2-output-check").click()
            expect(page.locator("#ev2-output-status")).to_contain_text(
                "No compatible con salida temporal"
            )
            expect(page.locator("#ev2-output-issues [data-code='UNSUPPORTED_CONTENT_SCALE']")).to_have_count(1)
        finally:
            browser.close()
