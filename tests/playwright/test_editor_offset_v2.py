from __future__ import annotations

from pathlib import Path
import json
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


def test_v2_many_slot_labels_grouped_issues_zoom_drag_and_temporary_visibility(
    v2_server, tmp_path
):
    pdf_path = tmp_path / "many-labels.pdf"
    _write_test_pdf(pdf_path)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        try:
            _open_job_with_repeat(page, v2_server, pdf_path, quantity=30)
            page.wait_for_function(
                "() => window.__EDITOR_OFFSET_V2__.store.saveState.status === 'clean'",
                timeout=10_000,
            )
            expect(page.locator(".ev2-svg-slot")).to_have_count(30)
            expect(page.locator(".ev2-svg-slot-label")).to_have_count(30)
            assert page.locator(".ev2-svg-slot-label").all_text_contents()[:3] == [
                "#1",
                "#2",
                "#3",
            ]
            assert page.locator(".ev2-svg-slot-label").last.text_content() == "#30"
            assert page.locator(".ev2-svg-slot-label").first.evaluate(
                "element => getComputedStyle(element).pointerEvents"
            ) == "none"

            server_before = page.evaluate(
                "async () => (await fetch(window.__EDITOR_OFFSET_V2__.context.job_api_url)).json()"
            )
            layout_before = page.evaluate(
                "() => JSON.stringify(window.__EDITOR_OFFSET_V2__.store.layout)"
            )

            page.locator("#ev2-toggle-labels").click()
            expect(page.locator(".ev2-svg-slot-label")).to_have_count(0)
            expect(page.locator("#ev2-toggle-labels")).to_have_attribute("aria-pressed", "false")
            page.locator("#ev2-toggle-labels").click()
            expect(page.locator(".ev2-svg-slot-label")).to_have_count(30)

            font_sizes = []
            for zoom in (0.35, 1, 4):
                page.evaluate(
                    "zoom => window.__EDITOR_OFFSET_V2__.store.setZoom(zoom)",
                    zoom,
                )
                expect(page.locator("#ev2-zoom")).to_have_text(f"{round(zoom * 100)}%")
                expect(page.locator(".ev2-svg-slot-label")).to_have_count(30)
                font_sizes.append(
                    float(page.locator(".ev2-svg-slot-label").first.get_attribute("font-size"))
                )
            assert font_sizes[0] > font_sizes[1] > font_sizes[2]

            original_trim = page.evaluate(
                "() => ({ ...window.__EDITOR_OFFSET_V2__.store.layout.slots[0].geometry.trim_size_mm })"
            )
            page.evaluate(
                "() => { const store = window.__EDITOR_OFFSET_V2__.store; "
                "store.layout.slots[0].geometry.trim_size_mm = { width: 5, height: 5 }; "
                "store.emit('label_test'); }"
            )
            expect(page.locator(".ev2-svg-slot-label")).to_have_count(29)
            page.evaluate(
                "trim => { const store = window.__EDITOR_OFFSET_V2__.store; "
                "store.layout.slots[0].geometry.trim_size_mm = trim; "
                "store.setZoom(1); store.emit('label_test_restore'); }",
                original_trim,
            )
            expect(page.locator(".ev2-svg-slot-label")).to_have_count(30)

            server_after = page.evaluate(
                "async () => (await fetch(window.__EDITOR_OFFSET_V2__.context.job_api_url)).json()"
            )
            assert server_after["revision"] == server_before["revision"]
            assert server_after["layout"] == server_before["layout"]
            assert page.evaluate(
                "() => JSON.stringify(window.__EDITOR_OFFSET_V2__.store.layout)"
            ) == layout_before
            assert page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.hasUnsavedChanges()"
            ) is False

            slot_ids = page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.slots.map(slot => slot.id)"
            )
            current_revision = server_after["revision"]
            grouped_payload = {
                "ok": True,
                "revision": current_revision,
                "compatible": False,
                "errors": [],
                "warnings": [],
                "issues": [
                    {
                        "code": "SOURCE_TRIM_SIZE_MISMATCH",
                        "level": "error",
                        "message": "mismatch",
                        "path": f"$.slots[{index}].geometry.trim_size_mm",
                        "slot_id": slot_id,
                        "asset_id": server_after["layout"]["assets"][0]["id"],
                    }
                    for index, slot_id in enumerate(slot_ids)
                ],
            }
            page.route(
                "**/output-capabilities",
                lambda route: route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(grouped_payload),
                ),
            )
            page.locator("#ev2-output-check").click()
            grouped = page.locator(
                "#ev2-output-issues [data-code='SOURCE_TRIM_SIZE_MISMATCH']"
            )
            expect(grouped).to_have_count(1)
            expect(grouped).to_have_attribute("data-affected-slots", "30")
            expect(grouped).to_contain_text("30 slots afectados")
            grouped.locator("details summary").click()
            expect(grouped.locator("details code")).to_have_count(30)
            page.unroute("**/output-capabilities")

            first_slot = page.locator(".ev2-svg-slot").first
            slot_id = slot_ids[0]
            page.evaluate("() => window.__EDITOR_OFFSET_V2__.store.clearSelection()")
            box = first_slot.bounding_box()
            assert box is not None
            page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            expect(page.locator("#ev2-inspector-values")).to_contain_text(slot_id)
            before_move = page.evaluate(
                "() => ({ ...window.__EDITOR_OFFSET_V2__.store.layout.slots[0].geometry.position_mm })"
            )
            box = first_slot.bounding_box()
            assert box is not None
            page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            page.mouse.down()
            page.mouse.move(box["x"] + box["width"] / 2 + 18, box["y"] + box["height"] / 2)
            page.mouse.up()
            page.wait_for_function(
                "before => window.__EDITOR_OFFSET_V2__.store.layout.slots[0].geometry.position_mm.x_mm !== before.x_mm",
                arg=before_move,
            )
        finally:
            browser.close()


def test_v2_precise_positioning_shortcuts_batching_persistence_and_locks(
    v2_server, tmp_path
):
    pdf_path = tmp_path / "posicionamiento-8a.pdf"
    _write_test_pdf(pdf_path)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        save_requests: list[str] = []
        page.on(
            "request",
            lambda request: save_requests.append(request.url)
            if request.method == "PUT" and request.url.endswith("/layout")
            else None,
        )
        try:
            _open_job_with_repeat(page, v2_server, pdf_path, quantity=4)
            page.wait_for_function(
                "() => window.__EDITOR_OFFSET_V2__.store.saveState.status === 'clean'",
                timeout=10_000,
            )
            slot_ids = page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.slots.map(slot => slot.id)"
            )
            page.evaluate(
                "slotId => window.__EDITOR_OFFSET_V2__.store.setSelection([slotId], 'replace')",
                slot_ids[0],
            )
            expect(page.locator("#ev2-position-form")).to_be_visible()
            expect(page.locator("#ev2-position-x")).to_be_enabled()
            assert page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.slots[0].generated_by.engine"
            ) == "repeat"

            absolute_before = page.evaluate(
                "() => ({ ...window.__EDITOR_OFFSET_V2__.store.layout.slots[0].geometry.position_mm })"
            )
            page.locator("#ev2-position-x").fill("123,456")
            page.locator("#ev2-position-y").fill("210.125")
            page.locator("#ev2-position-apply").click()
            absolute_after = page.evaluate(
                "() => ({ ...window.__EDITOR_OFFSET_V2__.store.layout.slots[0].geometry.position_mm })"
            )
            assert absolute_after["x_mm"] == pytest.approx(123.456)
            assert absolute_after["y_mm"] == pytest.approx(210.125)
            transform = page.locator(
                f".ev2-svg-slot[data-slot-id='{slot_ids[0]}']"
            ).get_attribute("transform")
            assert "translate(123.456 " in transform

            page.keyboard.press("Control+Z")
            restored = page.evaluate(
                "() => ({ ...window.__EDITOR_OFFSET_V2__.store.layout.slots[0].geometry.position_mm })"
            )
            assert restored["x_mm"] == pytest.approx(absolute_before["x_mm"])
            assert restored["y_mm"] == pytest.approx(absolute_before["y_mm"])
            page.keyboard.press("Control+Shift+Z")
            assert page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.slots[0].geometry.position_mm.x_mm"
            ) == pytest.approx(123.456)

            page.evaluate(
                "ids => window.__EDITOR_OFFSET_V2__.store.setSelection(ids, 'replace')",
                slot_ids[:2],
            )
            expect(page.locator("#ev2-position-selection-count")).to_have_text(
                "2 slots seleccionados"
            )
            multi_before = page.evaluate(
                "ids => ids.map(id => ({ ...window.__EDITOR_OFFSET_V2__.store.layout.slots.find(slot => slot.id === id).geometry.position_mm }))",
                slot_ids[:2],
            )
            relative_before = (
                multi_before[1]["x_mm"] - multi_before[0]["x_mm"],
                multi_before[1]["y_mm"] - multi_before[0]["y_mm"],
            )
            page.locator("#ev2-position-x").fill("1,25")
            page.locator("#ev2-position-y").fill("-0.75")
            page.locator("#ev2-position-apply").click()
            multi_after = page.evaluate(
                "ids => ids.map(id => ({ ...window.__EDITOR_OFFSET_V2__.store.layout.slots.find(slot => slot.id === id).geometry.position_mm }))",
                slot_ids[:2],
            )
            assert multi_after[0]["x_mm"] == pytest.approx(multi_before[0]["x_mm"] + 1.25)
            assert multi_after[1]["y_mm"] == pytest.approx(multi_before[1]["y_mm"] - 0.75)
            assert multi_after[1]["x_mm"] - multi_after[0]["x_mm"] == pytest.approx(
                relative_before[0]
            )
            assert multi_after[1]["y_mm"] - multi_after[0]["y_mm"] == pytest.approx(
                relative_before[1]
            )

            page.locator("#ev2-canvas").focus()
            page.keyboard.press("ArrowRight")
            page.keyboard.press("Shift+ArrowUp")
            page.keyboard.press("Control+Shift+ArrowLeft")
            stepped = page.evaluate(
                "ids => ids.map(id => ({ ...window.__EDITOR_OFFSET_V2__.store.layout.slots.find(slot => slot.id === id).geometry.position_mm }))",
                slot_ids[:2],
            )
            assert stepped[0]["x_mm"] == pytest.approx(multi_after[0]["x_mm"] - 9.9)
            assert stepped[0]["y_mm"] == pytest.approx(multi_after[0]["y_mm"] + 1)

            batch_before = page.evaluate(
                "ids => ids.map(id => ({ ...window.__EDITOR_OFFSET_V2__.store.layout.slots.find(slot => slot.id === id).geometry.position_mm }))",
                slot_ids[:2],
            )
            history_before = page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.undoStack.length"
            )
            page.keyboard.down("ArrowRight")
            page.evaluate(
                "() => { for (let index = 0; index < 3; index += 1) { "
                "window.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', code: 'ArrowRight', repeat: true, bubbles: true })); "
                "} }"
            )
            page.keyboard.up("ArrowRight")
            assert page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.undoStack.length"
            ) == history_before + 1
            batch_after = page.evaluate(
                "ids => ids.map(id => ({ ...window.__EDITOR_OFFSET_V2__.store.layout.slots.find(slot => slot.id === id).geometry.position_mm }))",
                slot_ids[:2],
            )
            assert batch_after[0]["x_mm"] == pytest.approx(batch_before[0]["x_mm"] + 0.4)
            page.keyboard.press("Control+Z")
            after_one_undo = page.evaluate(
                "ids => ids.map(id => ({ ...window.__EDITOR_OFFSET_V2__.store.layout.slots.find(slot => slot.id === id).geometry.position_mm }))",
                slot_ids[:2],
            )
            assert after_one_undo == batch_before
            page.keyboard.press("Control+Shift+Z")

            with page.expect_response(
                lambda response: response.request.method == "PUT"
                and response.url.endswith("/layout")
            ) as save_info:
                page.keyboard.press("Control+S")
            assert save_info.value.status == 200
            page.wait_for_function(
                "() => window.__EDITOR_OFFSET_V2__.store.saveState.status === 'clean'",
                timeout=10_000,
            )
            persisted = page.evaluate(
                "ids => ids.map(id => ({ ...window.__EDITOR_OFFSET_V2__.store.layout.slots.find(slot => slot.id === id).geometry.position_mm }))",
                slot_ids[:2],
            )
            page.reload(wait_until="domcontentloaded")
            reloaded = page.evaluate(
                "ids => ids.map(id => ({ ...window.__EDITOR_OFFSET_V2__.store.layout.slots.find(slot => slot.id === id).geometry.position_mm }))",
                slot_ids[:2],
            )
            assert reloaded == persisted

            page.evaluate(
                "slotId => window.__EDITOR_OFFSET_V2__.store.setSelection([slotId], 'replace')",
                slot_ids[0],
            )
            focus_before = page.evaluate(
                "() => ({ ...window.__EDITOR_OFFSET_V2__.store.layout.slots[0].geometry.position_mm })"
            )
            page.locator("#ev2-position-x").focus()
            page.keyboard.press("ArrowRight")
            assert page.evaluate(
                "() => ({ ...window.__EDITOR_OFFSET_V2__.store.layout.slots[0].geometry.position_mm })"
            ) == focus_before

            page.locator("#ev2-position-x").fill("130,75")
            save_count_before_comma = len(save_requests)
            with page.expect_response(
                lambda response: response.request.method == "PUT"
                and response.url.endswith("/layout")
            ):
                page.keyboard.press("Control+S")
            page.wait_for_function(
                "() => window.__EDITOR_OFFSET_V2__.store.saveState.status === 'clean'",
                timeout=10_000,
            )
            assert len(save_requests) == save_count_before_comma + 1
            assert page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.slots[0].geometry.position_mm.x_mm"
            ) == pytest.approx(130.75)

            revision_before_invalid = page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.revision"
            )
            save_count_before_invalid = len(save_requests)
            page.locator("#ev2-position-x").fill("valor-invalido")
            page.keyboard.press("Control+S")
            page.wait_for_timeout(350)
            expect(page.locator("#ev2-position-error")).to_contain_text("números finitos")
            assert len(save_requests) == save_count_before_invalid
            assert page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.revision"
            ) == revision_before_invalid
            page.keyboard.press("Escape")

            help_version = page.evaluate(
                "() => ({ change: window.__EDITOR_OFFSET_V2__.store.changeVersion, revision: window.__EDITOR_OFFSET_V2__.store.revision })"
            )
            page.locator("#ev2-canvas").focus()
            page.keyboard.press("Shift+/")
            expect(page.locator("#ev2-shortcuts-help")).to_be_visible()
            expect(page.locator("#ev2-shortcuts-help-list")).to_contain_text("Guardar")
            expect(page.locator("#ev2-shortcuts-help-list")).to_contain_text("Mover 10 mm")
            expect(page.locator("#ev2-shortcuts-help-list")).to_contain_text("Duplicar")
            page.keyboard.press("Escape")
            expect(page.locator("#ev2-shortcuts-help")).not_to_be_visible()
            assert page.evaluate(
                "() => ({ change: window.__EDITOR_OFFSET_V2__.store.changeVersion, revision: window.__EDITOR_OFFSET_V2__.store.revision })"
            ) == help_version

            page.evaluate(
                "slotId => { const store = window.__EDITOR_OFFSET_V2__.store; "
                "const slot = store.layout.slots.find(item => item.id === slotId); "
                "slot.locks.geometry = ['system']; store.setSelection([slotId], 'replace'); "
                "store.emit('lock_fixture'); }",
                slot_ids[0],
            )
            expect(page.locator("#ev2-position-x")).to_be_disabled()
            expect(page.locator("#ev2-position-lock")).to_contain_text(slot_ids[0])
            locked_before = page.evaluate(
                "slotId => ({ ...window.__EDITOR_OFFSET_V2__.store.layout.slots.find(slot => slot.id === slotId).geometry.position_mm })",
                slot_ids[0],
            )
            first_slot = page.locator(f".ev2-svg-slot[data-slot-id='{slot_ids[0]}']")
            box = first_slot.bounding_box()
            assert box is not None
            page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            page.mouse.down()
            page.mouse.move(box["x"] + box["width"] / 2 + 24, box["y"] + box["height"] / 2)
            page.mouse.up()
            page.locator("#ev2-canvas").focus()
            page.keyboard.press("ArrowRight")
            page.evaluate(
                "() => { const x = document.querySelector('#ev2-position-x'); "
                "x.disabled = false; x.value = '200'; "
                "x.dispatchEvent(new Event('input', { bubbles: true })); "
                "document.querySelector('#ev2-position-form').requestSubmit(); }"
            )
            assert page.evaluate(
                "slotId => ({ ...window.__EDITOR_OFFSET_V2__.store.layout.slots.find(slot => slot.id === slotId).geometry.position_mm })",
                slot_ids[0],
            ) == locked_before
            expect(page.locator("#ev2-status-message")).to_contain_text(slot_ids[0])

            page.locator("#ev2-toggle-labels").click()
            expect(page.locator("#ev2-toggle-labels")).to_have_attribute("aria-pressed", "false")
            page.locator("#ev2-toggle-labels").click()
            with page.expect_response(
                lambda response: response.request.method == "GET"
                and "/output-capabilities" in response.url
            ):
                page.locator("#ev2-output-check").click()
            expect(page.locator("#ev2-output-status")).to_contain_text("salida temporal")
            expect(page.locator("#ev2-object-duplicate")).to_be_visible()
            expect(page.locator("#ev2-object-copy")).to_be_visible()
            expect(page.locator("#ev2-object-rotation")).to_be_visible()
        finally:
            browser.close()


def test_v2_object_operations_clipboard_locks_alt_drag_and_persistence(
    v2_server, tmp_path
):
    pdf_path = tmp_path / "operaciones-objetos-8b.pdf"
    _write_test_pdf(pdf_path)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        try:
            _open_job_with_repeat(page, v2_server, pdf_path, quantity=2)
            page.wait_for_function(
                "() => window.__EDITOR_OFFSET_V2__.store.saveState.status === 'clean'",
                timeout=10_000,
            )
            original_ids = page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.slots.map(slot => slot.id)"
            )
            page.evaluate(
                "slotId => window.__EDITOR_OFFSET_V2__.store.setSelection([slotId], 'replace')",
                original_ids[0],
            )

            before_rotation = page.evaluate(
                "slotId => { const slot = window.__EDITOR_OFFSET_V2__.store.layout.slots.find(item => item.id === slotId); "
                "return { position: { ...slot.geometry.position_mm }, trim: { ...slot.geometry.trim_size_mm }, "
                "bleed: { ...slot.geometry.bleed_mm }, source: structuredClone(slot.source), rotation: slot.geometry.rotation_deg }; }",
                original_ids[0],
            )
            page.locator("#ev2-object-rotate-positive").click()
            after_rotation = page.evaluate(
                "slotId => { const slot = window.__EDITOR_OFFSET_V2__.store.layout.slots.find(item => item.id === slotId); "
                "return { position: { ...slot.geometry.position_mm }, trim: { ...slot.geometry.trim_size_mm }, "
                "bleed: { ...slot.geometry.bleed_mm }, source: structuredClone(slot.source), rotation: slot.geometry.rotation_deg }; }",
                original_ids[0],
            )
            assert after_rotation["rotation"] == (before_rotation["rotation"] + 90) % 360
            assert after_rotation["position"] == before_rotation["position"]
            assert after_rotation["trim"] == before_rotation["trim"]
            assert after_rotation["bleed"] == before_rotation["bleed"]
            assert after_rotation["source"] == before_rotation["source"]
            page.keyboard.press("Control+Z")
            assert page.evaluate(
                "slotId => window.__EDITOR_OFFSET_V2__.store.layout.slots.find(item => item.id === slotId).geometry.rotation_deg",
                original_ids[0],
            ) == before_rotation["rotation"]
            page.keyboard.press("Control+Shift+Z")
            page.locator("#ev2-object-rotation").select_option("180")
            expect(page.locator("#ev2-object-rotation")).to_have_value("180")

            duplicate_origin = page.evaluate(
                "slotId => ({ ...window.__EDITOR_OFFSET_V2__.store.layout.slots.find(item => item.id === slotId).geometry.position_mm })",
                original_ids[0],
            )
            page.keyboard.press("Control+D")
            duplicate = page.evaluate(
                "() => { const store = window.__EDITOR_OFFSET_V2__.store; const id = [...store.selection][0]; "
                "return structuredClone(store.layout.slots.find(slot => slot.id === id)); }"
            )
            assert duplicate["id"] not in original_ids
            assert duplicate["geometry"]["position_mm"]["x_mm"] == pytest.approx(
                duplicate_origin["x_mm"] + 5
            )
            assert duplicate["geometry"]["position_mm"]["y_mm"] == pytest.approx(
                duplicate_origin["y_mm"] - 5
            )
            assert duplicate["generated_by"] == {
                "type": "duplicate",
                "source_slot_id": original_ids[0],
            }
            duplicate_id = duplicate["id"]

            page.keyboard.press("Control+C")
            expect(page.locator("#ev2-object-clipboard")).to_contain_text("1 slot")
            page.keyboard.press("Control+V")
            first_paste = page.evaluate(
                "() => { const store = window.__EDITOR_OFFSET_V2__.store; const id = [...store.selection][0]; "
                "return structuredClone(store.layout.slots.find(slot => slot.id === id)); }"
            )
            page.keyboard.press("Control+V")
            second_paste = page.evaluate(
                "() => { const store = window.__EDITOR_OFFSET_V2__.store; const id = [...store.selection][0]; "
                "return structuredClone(store.layout.slots.find(slot => slot.id === id)); }"
            )
            assert first_paste["geometry"]["position_mm"]["x_mm"] == pytest.approx(
                duplicate["geometry"]["position_mm"]["x_mm"] + 5
            )
            assert second_paste["geometry"]["position_mm"]["x_mm"] == pytest.approx(
                duplicate["geometry"]["position_mm"]["x_mm"] + 10
            )
            assert first_paste["id"] != second_paste["id"]
            expect(page.locator("#ev2-object-clipboard")).to_contain_text("2 pegado")

            page.keyboard.press("Control+X")
            assert page.evaluate(
                "slotId => !window.__EDITOR_OFFSET_V2__.store.layout.slots.some(slot => slot.id === slotId)",
                second_paste["id"],
            )
            page.keyboard.press("Control+Z")
            assert page.evaluate(
                "slotId => window.__EDITOR_OFFSET_V2__.store.layout.slots.some(slot => slot.id === slotId)",
                second_paste["id"],
            )
            page.keyboard.press("Delete")
            assert page.evaluate(
                "slotId => !window.__EDITOR_OFFSET_V2__.store.layout.slots.some(slot => slot.id === slotId)",
                second_paste["id"],
            )
            page.keyboard.press("Control+Z")

            page.keyboard.press("Control+A")
            assert page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.selection.size"
            ) == page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.slots.filter(slot => slot.face === 'front').length"
            )
            page.evaluate(
                "slotId => window.__EDITOR_OFFSET_V2__.store.setSelection([slotId], 'replace')",
                original_ids[0],
            )
            page.locator("#ev2-object-select-work").click()
            assert page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.selection.size"
            ) == page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.slots.filter(slot => slot.face === 'front').length"
            )
            page.evaluate(
                "slotId => window.__EDITOR_OFFSET_V2__.store.setSelection([slotId], 'replace')",
                original_ids[0],
            )
            page.locator("#ev2-object-select-asset").click()
            assert page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.selection.size"
            ) == page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.slots.filter(slot => slot.face === 'front').length"
            )

            page.evaluate(
                "slotId => window.__EDITOR_OFFSET_V2__.store.setSelection([slotId], 'replace')",
                original_ids[0],
            )
            geometry_lock = page.locator(
                "[data-lock-surface='geometry'][data-lock-action='lock']"
            )
            geometry_unlock = page.locator(
                "[data-lock-surface='geometry'][data-lock-action='unlock']"
            )
            geometry_lock.click()
            expect(page.locator("[data-lock-status='geometry']")).to_contain_text("todos")
            locked_rotation = page.evaluate(
                "slotId => window.__EDITOR_OFFSET_V2__.store.layout.slots.find(slot => slot.id === slotId).geometry.rotation_deg",
                original_ids[0],
            )
            expect(page.locator("#ev2-object-rotate-positive")).to_be_disabled()
            page.keyboard.press("R")
            assert page.evaluate(
                "slotId => window.__EDITOR_OFFSET_V2__.store.layout.slots.find(slot => slot.id === slotId).geometry.rotation_deg",
                original_ids[0],
            ) == locked_rotation
            geometry_unlock.click()
            expect(page.locator("[data-lock-status='geometry']")).to_contain_text("ninguno")

            delete_lock = page.locator(
                "[data-lock-surface='delete'][data-lock-action='lock']"
            )
            delete_unlock = page.locator(
                "[data-lock-surface='delete'][data-lock-action='unlock']"
            )
            delete_lock.click()
            expect(page.locator("#ev2-object-delete")).to_be_disabled()
            count_locked = page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.slots.length"
            )
            page.keyboard.press("Delete")
            page.keyboard.press("Control+X")
            assert page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.slots.length"
            ) == count_locked
            delete_unlock.click()

            input_before = page.evaluate(
                "() => ({ count: window.__EDITOR_OFFSET_V2__.store.layout.slots.length, "
                "rotation: window.__EDITOR_OFFSET_V2__.store.layout.slots[0].geometry.rotation_deg, "
                "selection: [...window.__EDITOR_OFFSET_V2__.store.selection] })"
            )
            page.locator("#ev2-position-x").focus()
            for shortcut in ["R", "Control+A", "Control+C", "Control+X", "Control+V", "Delete"]:
                page.keyboard.press(shortcut)
            input_after = page.evaluate(
                "() => ({ count: window.__EDITOR_OFFSET_V2__.store.layout.slots.length, "
                "rotation: window.__EDITOR_OFFSET_V2__.store.layout.slots[0].geometry.rotation_deg, "
                "selection: [...window.__EDITOR_OFFSET_V2__.store.selection] })"
            )
            assert input_after == input_before

            alt_source_id = original_ids[1]
            page.evaluate(
                "slotId => window.__EDITOR_OFFSET_V2__.store.setSelection([slotId], 'replace')",
                alt_source_id,
            )
            original = page.locator(f".ev2-svg-slot[data-slot-id='{alt_source_id}']")
            box = original.bounding_box()
            assert box is not None
            count_before_alt = page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.slots.length"
            )
            page.keyboard.down("Alt")
            page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            page.mouse.down()
            page.mouse.move(
                box["x"] + box["width"] / 2 + 32,
                box["y"] + box["height"] / 2 + 18,
                steps=4,
            )
            expect(page.locator(".ev2-svg-slot.is-duplicate-preview")).to_have_count(1)
            page.mouse.up()
            page.keyboard.up("Alt")
            assert page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.slots.length"
            ) == count_before_alt + 1
            alt_copy = page.evaluate(
                "() => { const store = window.__EDITOR_OFFSET_V2__.store; "
                "return structuredClone(store.layout.slots.find(slot => store.selection.has(slot.id))); }"
            )
            assert alt_copy["generated_by"] == {
                "type": "duplicate",
                "source_slot_id": alt_source_id,
            }

            cancel_target = page.locator(
                f".ev2-svg-slot[data-slot-id='{alt_copy['id']}']"
            )
            cancel_box = cancel_target.bounding_box()
            assert cancel_box is not None
            count_before_cancel = page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.slots.length"
            )
            history_before_cancel = page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.undoStack.length"
            )
            page.keyboard.down("Alt")
            page.mouse.move(
                cancel_box["x"] + cancel_box["width"] / 2,
                cancel_box["y"] + cancel_box["height"] / 2,
            )
            page.mouse.down()
            page.mouse.move(
                cancel_box["x"] + cancel_box["width"] / 2 + 24,
                cancel_box["y"] + cancel_box["height"] / 2 + 12,
                steps=3,
            )
            expect(page.locator(".ev2-svg-slot.is-duplicate-preview")).to_have_count(1)
            page.keyboard.press("Escape")
            expect(page.locator(".ev2-svg-slot.is-duplicate-preview")).to_have_count(0)
            page.mouse.up()
            page.keyboard.up("Alt")
            assert page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.slots.length"
            ) == count_before_cancel
            assert page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.undoStack.length"
            ) == history_before_cancel

            page.keyboard.press("Control+S")
            page.wait_for_function(
                "() => window.__EDITOR_OFFSET_V2__.store.saveState.status === 'clean'",
                timeout=10_000,
            )
            persisted_ids = page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.slots.map(slot => slot.id)"
            )
            page.reload(wait_until="domcontentloaded")
            assert page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.slots.map(slot => slot.id)"
            ) == persisted_ids
            assert duplicate_id in persisted_ids

            page.locator("#ev2-shortcuts-help-button").click()
            expect(page.locator("#ev2-shortcuts-help-list")).to_contain_text("Rotar +90")
            expect(page.locator("#ev2-shortcuts-help-list")).to_contain_text("Copiar")
            expect(page.locator("#ev2-shortcuts-help-list")).to_contain_text("Pegar")
        finally:
            browser.close()


def test_v2_alignment_distribution_gap_matrix_and_persistence(v2_server, tmp_path):
    pdf_path = tmp_path / "fase-8c.pdf"
    _write_test_pdf(pdf_path)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1000})
        page_errors: list[str] = []
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        try:
            _open_job_with_repeat(page, v2_server, pdf_path, quantity=6)
            expect(page.locator("#ev2-arrangement-heading")).to_be_visible()
            expect(page.locator("#ev2-object-operations-heading")).to_be_visible()
            expect(page.locator("#ev2-arrangement-geometry")).to_have_value("trim")

            slot_ids = page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.slots.map(slot => slot.id)"
            )
            page.evaluate(
                "ids => window.__EDITOR_OFFSET_V2__.store.setSelection(ids, 'replace')",
                slot_ids,
            )
            page.locator("#ev2-arrangement-geometry").select_option("trim")
            before_align = page.evaluate(
                "() => structuredClone(window.__EDITOR_OFFSET_V2__.store.layout.slots.map(slot => slot.geometry.position_mm))"
            )
            page.locator('[data-arrangement-action="selection.align.left"]').click()
            left_edges = page.evaluate(
                """() => {
                  const app = window.__EDITOR_OFFSET_V2__;
                  return app.store.layout.slots.map(slot =>
                    window.EditorOffsetV2.GeometryView.trimBounds(slot).left);
                }"""
            )
            assert max(left_edges) - min(left_edges) < 1e-8
            page.locator("#ev2-undo").click()
            assert page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.slots.map(slot => slot.geometry.position_mm)"
            ) == before_align
            page.locator("#ev2-redo").click()

            key_id = slot_ids[0]
            page.locator("#ev2-arrangement-key-candidate").select_option(key_id)
            page.locator("#ev2-arrangement-key-set").click()
            expect(page.locator("#ev2-arrangement-key-status")).to_contain_text(key_id)
            expect(page.locator(f'[data-key-slot-badge="{key_id}"]')).to_have_count(1)
            key_before = page.evaluate(
                "id => structuredClone(window.__EDITOR_OFFSET_V2__.store.layout.slots.find(slot => slot.id === id).geometry.position_mm)",
                key_id,
            )
            page.locator("#ev2-arrangement-target").select_option("key")
            page.locator('[data-arrangement-action="selection.align.top"]').click()
            assert page.evaluate(
                "id => window.__EDITOR_OFFSET_V2__.store.layout.slots.find(slot => slot.id === id).geometry.position_mm",
                key_id,
            ) == key_before

            page.locator("#ev2-arrangement-target").select_option("sheet")
            page.locator('[data-arrangement-action="selection.center.horizontal"]').click()
            sheet_centers = page.evaluate(
                """() => {
                  const app = window.__EDITOR_OFFSET_V2__;
                  const bounds = window.EditorOffsetV2.GeometryView.boundsUnion(
                    app.store.layout.slots.map(slot => window.EditorOffsetV2.GeometryView.trimBounds(slot)));
                  return [bounds.left + bounds.width / 2, app.store.layout.sheet.size_mm.width / 2];
                }"""
            )
            assert abs(sheet_centers[0] - sheet_centers[1]) < 1e-8

            page.locator("#ev2-arrangement-target").select_option("printable")
            page.locator('[data-arrangement-action="selection.center.both"]').click()
            printable_centers = page.evaluate(
                """() => {
                  const app = window.__EDITOR_OFFSET_V2__;
                  const geometry = window.EditorOffsetV2.GeometryView;
                  const selected = app.store.layout.slots.filter(slot => app.store.selection.has(slot.id));
                  const bounds = geometry.boundsUnion(selected.map(slot => geometry.trimBounds(slot)));
                  const printable = geometry.printableBounds(app.store.layout.sheet);
                  return [
                    bounds.left + bounds.width / 2,
                    bounds.bottom + bounds.height / 2,
                    printable.left + printable.width / 2,
                    printable.bottom + printable.height / 2,
                  ];
                }"""
            )
            assert abs(printable_centers[0] - printable_centers[2]) < 1e-8
            assert abs(printable_centers[1] - printable_centers[3]) < 1e-8

            page.locator('[data-arrangement-action="selection.distribute.horizontal"]').click()
            expect(page.locator("#ev2-arrangement-feedback")).to_contain_text("gap")
            page.locator('[data-arrangement-action="selection.distribute.vertical"]').click()

            page.locator("#ev2-arrangement-gap-horizontal").fill("4")
            page.locator("#ev2-arrangement-gap-horizontal-anchor").select_option("start")
            page.locator("#ev2-arrangement-gap-horizontal-apply").click()
            page.locator("#ev2-arrangement-gap-vertical").fill("2,5")
            page.locator("#ev2-arrangement-gap-vertical-anchor").select_option("key")
            page.locator("#ev2-arrangement-gap-vertical-apply").click()
            expect(page.locator("#ev2-arrangement-feedback")).to_contain_text("2.5 mm")
            layout_before_invalid = page.evaluate(
                "() => JSON.stringify(window.__EDITOR_OFFSET_V2__.store.layout)"
            )
            page.locator("#ev2-arrangement-gap-horizontal").fill("-3")
            expect(page.locator("#ev2-arrangement-gap-horizontal-apply")).to_be_disabled()
            page.locator("#ev2-arrangement-gap-horizontal-form").press("Enter")
            assert page.evaluate(
                "() => JSON.stringify(window.__EDITOR_OFFSET_V2__.store.layout)"
            ) == layout_before_invalid
            expect(page.locator("#ev2-arrangement-gap-horizontal-error")).to_contain_text(
                "mayor o igual a 0"
            )
            page.locator("#ev2-arrangement-gap-horizontal").press("Escape")

            moving_id = slot_ids[1]
            page.evaluate(
                "id => window.__EDITOR_OFFSET_V2__.store.setSelection([id], 'replace')",
                moving_id,
            )
            page.locator('[data-lock-surface="geometry"][data-lock-action="lock"]').click()
            expect(page.locator("[data-lock-status='geometry']")).to_contain_text("todos")
            page.evaluate(
                "ids => window.__EDITOR_OFFSET_V2__.store.setSelection(ids, 'replace')",
                slot_ids,
            )
            locked_before = page.evaluate(
                "() => JSON.stringify(window.__EDITOR_OFFSET_V2__.store.layout.slots.map(slot => slot.geometry.position_mm))"
            )
            page.locator("#ev2-arrangement-target").select_option("selection")
            expect(
                page.locator('[data-arrangement-action="selection.align.right"]')
            ).to_be_disabled()
            page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.runAction(window.EditorOffsetV2.CommandRegistry.ACTION_IDS.ALIGN_RIGHT)"
            )
            assert page.evaluate(
                "() => JSON.stringify(window.__EDITOR_OFFSET_V2__.store.layout.slots.map(slot => slot.geometry.position_mm))"
            ) == locked_before
            expect(page.locator("#ev2-status-message")).to_contain_text(moving_id)
            page.evaluate(
                "id => window.__EDITOR_OFFSET_V2__.store.setSelection([id], 'replace')",
                moving_id,
            )
            page.locator('[data-lock-surface="geometry"][data-lock-action="unlock"]').click()

            source_id = slot_ids[0]
            page.evaluate(
                "id => window.__EDITOR_OFFSET_V2__.store.setSelection([id], 'replace')",
                source_id,
            )
            count_before_matrix = page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.slots.length"
            )
            page.locator("#ev2-arrangement-matrix-rows").fill("2")
            page.locator("#ev2-arrangement-matrix-columns").fill("3")
            page.locator("#ev2-arrangement-matrix-gap-x").fill("3")
            page.locator("#ev2-arrangement-matrix-gap-y").fill("4")
            expect(page.locator("#ev2-arrangement-matrix-summary")).to_contain_text(
                "5 slots nuevos"
            )
            page.locator("#ev2-arrangement-matrix-apply").click()
            page.wait_for_function(
                "count => window.__EDITOR_OFFSET_V2__.store.layout.slots.length === count + 5",
                arg=count_before_matrix,
            )
            matrix_ids = page.evaluate(
                "() => [...window.__EDITOR_OFFSET_V2__.store.selection]"
            )
            assert len(matrix_ids) == 5
            assert len(set(matrix_ids)) == 5
            matrix_positions = page.evaluate(
                """ids => ids.map(id => {
                  const slot = window.__EDITOR_OFFSET_V2__.store.layout.slots.find(item => item.id === id);
                  return [slot.geometry.position_mm.x_mm, slot.geometry.position_mm.y_mm, slot.generated_by];
                })""",
                matrix_ids,
            )
            assert all(item[2]["type"] == "duplicate" for item in matrix_positions)
            assert all(item[2]["source_slot_id"] == source_id for item in matrix_positions)
            source_position = page.evaluate(
                "id => window.__EDITOR_OFFSET_V2__.store.layout.slots.find(slot => slot.id === id).geometry.position_mm",
                source_id,
            )
            assert any(item[0] > source_position["x_mm"] for item in matrix_positions)
            assert any(item[1] < source_position["y_mm"] for item in matrix_positions)
            page.locator("#ev2-undo").click()
            assert page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.slots.length"
            ) == count_before_matrix
            page.locator("#ev2-redo").click()
            assert page.evaluate(
                "() => [...window.__EDITOR_OFFSET_V2__.store.selection]"
            ) == matrix_ids

            page.evaluate("() => window.__EDITOR_OFFSET_V2__.saver.manualSave()")
            page.wait_for_function(
                "() => window.__EDITOR_OFFSET_V2__.store.saveState.status === 'clean'"
            )
            persisted_ids = page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.slots.map(slot => slot.id)"
            )
            page.reload(wait_until="domcontentloaded")
            assert page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.slots.map(slot => slot.id)"
            ) == persisted_ids
            assert page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.arrangement.keySlotId"
            ) is None

            page.locator("#ev2-arrangement-gap-horizontal").fill("12,5")
            page.locator("#ev2-arrangement-gap-horizontal").press("ArrowLeft")
            expect(page.locator("#ev2-arrangement-gap-horizontal")).to_have_value("12,5")
            page.locator("#ev2-shortcuts-help-button").click()
            expect(page.locator("#ev2-shortcuts-help-list")).to_contain_text("Duplicar")
            expect(page.locator("#ev2-shortcuts-help-list")).not_to_contain_text(
                "Alinear a la izquierda"
            )
            page.locator("#ev2-shortcuts-help-close").click()
            with page.expect_response(
                lambda response: response.request.method == "GET"
                and response.url.endswith("/output-capabilities")
            ):
                page.locator("#ev2-output-check").click()
            expect(page.locator("#ev2-output-status")).to_be_visible()
            expect(page.locator(".ev2-svg-slot-label").first).to_have_text("#1")
            expect(page.locator("#ev2-object-duplicate")).to_be_visible()
            expect(page.locator("#ev2-object-copy")).to_be_visible()
            expect(page.locator("#ev2-objects-tree")).to_have_count(0)
            assert not page_errors
        finally:
            browser.close()


def test_v2_advanced_selection_tree_and_temporary_visibility(v2_server, tmp_path):
    pdf_path = tmp_path / "fase-8d.pdf"
    _write_test_pdf(pdf_path)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1680, "height": 1050})
        console_errors: list[str] = []
        page_errors: list[str] = []
        page.on(
            "console",
            lambda message: console_errors.append(message.text)
            if message.type == "error" and "favicon" not in message.text.lower()
            else None,
        )
        page.on("pageerror", lambda error: page_errors.append(str(error)))

        def domain_to_client(point: dict[str, float]) -> dict[str, float]:
            return page.evaluate(
                """point => {
                  const app = window.__EDITOR_OFFSET_V2__;
                  const svg = app.renderer.refs.canvas;
                  const svgPoint = svg.createSVGPoint();
                  svgPoint.x = point.x;
                  svgPoint.y = app.store.layout.sheet.size_mm.height - point.y;
                  const client = svgPoint.matrixTransform(svg.getScreenCTM());
                  return {x: client.x, y: client.y};
                }""",
                point,
            )

        def drag_domain(
            start: dict[str, float],
            end: dict[str, float],
            modifier: str | None = None,
        ) -> None:
            start_client = domain_to_client(start)
            end_client = domain_to_client(end)
            if modifier:
                page.keyboard.down(modifier)
            page.mouse.move(start_client["x"], start_client["y"])
            page.mouse.down()
            page.mouse.move(end_client["x"], end_client["y"], steps=4)
            page.mouse.up()
            if modifier:
                page.keyboard.up(modifier)

        try:
            _open_job_with_repeat(page, v2_server, pdf_path, quantity=8)
            expect(page.locator("#ev2-advanced-selection-heading")).to_be_visible()
            expect(page.locator("#ev2-object-tree")).to_have_attribute("role", "tree")
            expect(page.locator("#ev2-marquee-mode")).to_have_value("contain")

            initial = page.evaluate(
                """() => {
                  const app = window.__EDITOR_OFFSET_V2__;
                  return {
                    layout: JSON.stringify(app.store.layout),
                    revision: app.store.revision,
                    changeVersion: app.store.changeVersion,
                    undo: app.store.undoStack.length,
                    ids: app.store.layout.slots.map(slot => slot.id),
                    bounds: app.store.layout.slots.map(slot => window.EditorOffsetV2.GeometryView.trimBounds(slot)),
                  };
                }"""
            )
            first_id, second_id, third_id = initial["ids"][:3]
            first_bounds, second_bounds = initial["bounds"][:2]

            drag_domain(
                {"x": first_bounds["left"] - 1, "y": first_bounds["bottom"] - 1},
                {"x": first_bounds["right"] + 1, "y": first_bounds["top"] + 1},
            )
            assert page.evaluate("() => [...window.__EDITOR_OFFSET_V2__.store.selection]") == [first_id]

            page.locator("#ev2-marquee-mode").select_option("intersect")
            drag_domain(
                {"x": first_bounds["left"] - 1, "y": first_bounds["bottom"] - 1},
                {"x": second_bounds["right"] + 1, "y": second_bounds["top"] + 1},
                "Shift",
            )
            shift_selection = page.evaluate(
                """() => ({
                  ids: [...window.__EDITOR_OFFSET_V2__.store.selection],
                  feedback: window.__EDITOR_OFFSET_V2__.store.feedback,
                  pointer: window.__EDITOR_OFFSET_V2__.store.pointerSession,
                })"""
            )
            assert {
                first_id,
                second_id,
            }.issubset(set(shift_selection["ids"])), shift_selection
            drag_domain(
                {"x": first_bounds["left"] - 1, "y": first_bounds["bottom"] - 1},
                {"x": second_bounds["right"] + 1, "y": second_bounds["top"] + 1},
                "Control",
            )
            toggled = set(page.evaluate("() => [...window.__EDITOR_OFFSET_V2__.store.selection]"))
            assert first_id not in toggled and second_id not in toggled
            page.evaluate(
                "ids => window.__EDITOR_OFFSET_V2__.store.setSelection(ids, 'replace')",
                [first_id, second_id],
            )
            drag_domain(
                {"x": first_bounds["left"] - 1, "y": first_bounds["bottom"] - 1},
                {"x": second_bounds["right"] + 1, "y": second_bounds["top"] + 1},
                "Alt",
            )
            assert page.evaluate("() => window.__EDITOR_OFFSET_V2__.store.selection.size") == 0

            start_client = domain_to_client({"x": first_bounds["left"] - 4, "y": first_bounds["bottom"] - 4})
            end_client = domain_to_client({"x": first_bounds["right"] + 4, "y": first_bounds["top"] + 4})
            page.mouse.move(start_client["x"], start_client["y"])
            page.mouse.down()
            page.mouse.move(end_client["x"], end_client["y"], steps=3)
            expect(page.locator("[data-selection-marquee]")).to_have_count(1)
            page.keyboard.press("Escape")
            page.mouse.up()
            expect(page.locator("[data-selection-marquee]")).to_have_count(0)

            pan_before = page.evaluate("() => ({...window.__EDITOR_OFFSET_V2__.store.pan})")
            page.keyboard.down("Space")
            page.mouse.move(start_client["x"], start_client["y"])
            page.mouse.down()
            page.mouse.move(start_client["x"] + 30, start_client["y"] + 20)
            page.mouse.up()
            page.keyboard.up("Space")
            assert page.evaluate("() => window.__EDITOR_OFFSET_V2__.store.pan") != pan_before
            page.locator("#ev2-reset-view").click()

            first_center = page.evaluate(
                "id => window.__EDITOR_OFFSET_V2__.store.layout.slots.find(slot => slot.id === id).geometry.position_mm",
                first_id,
            )
            center_client = domain_to_client({"x": first_center["x_mm"], "y": first_center["y_mm"]})
            page.mouse.move(center_client["x"], center_client["y"])
            page.mouse.down()
            page.mouse.move(center_client["x"] + 18, center_client["y"], steps=3)
            page.mouse.up()
            assert page.evaluate(
                "id => window.__EDITOR_OFFSET_V2__.store.layout.slots.find(slot => slot.id === id).geometry.position_mm.x_mm",
                first_id,
            ) != first_center["x_mm"]
            page.locator("#ev2-undo").click()

            page.evaluate(
                """ids => {
                  const app = window.__EDITOR_OFFSET_V2__;
                  app.store.setSelection(ids, 'replace');
                  app.runAction(window.EditorOffsetV2.CommandRegistry.ACTION_IDS.ALIGN_LEFT);
                  app.runAction(window.EditorOffsetV2.CommandRegistry.ACTION_IDS.ALIGN_TOP);
                }""",
                [first_id, second_id],
            )
            overlap_center = page.evaluate(
                """id => {
                  const slot = window.__EDITOR_OFFSET_V2__.store.layout.slots.find(item => item.id === id);
                  return {x: slot.geometry.position_mm.x_mm, y: slot.geometry.position_mm.y_mm};
                }""",
                first_id,
            )
            overlap_client = domain_to_client(overlap_center)
            page.keyboard.down("Alt")
            page.mouse.click(overlap_client["x"], overlap_client["y"])
            page.keyboard.up("Alt")
            cycled_once = page.evaluate("() => [...window.__EDITOR_OFFSET_V2__.store.selection][0]")
            page.keyboard.down("Alt")
            page.mouse.click(overlap_client["x"], overlap_client["y"])
            page.keyboard.up("Alt")
            cycled_twice = page.evaluate("() => [...window.__EDITOR_OFFSET_V2__.store.selection][0]")
            assert cycled_once != cycled_twice
            expect(page.locator("#ev2-status-message")).to_contain_text("Ciclo")

            count_before_alt_drag = page.evaluate("() => window.__EDITOR_OFFSET_V2__.store.layout.slots.length")
            page.keyboard.down("Alt")
            page.mouse.move(overlap_client["x"], overlap_client["y"])
            page.mouse.down()
            page.mouse.move(overlap_client["x"] + 25, overlap_client["y"] + 15, steps=4)
            page.mouse.up()
            page.keyboard.up("Alt")
            assert page.evaluate("() => window.__EDITOR_OFFSET_V2__.store.layout.slots.length") > count_before_alt_drag
            page.locator("#ev2-undo").click()

            page.evaluate(
                "id => window.__EDITOR_OFFSET_V2__.store.setSelection([id], 'replace')",
                first_id,
            )
            for selector in [
                '[data-selection-action="selection.select_same_size"]',
                '[data-selection-action="selection.select_same_rotation"]',
                '[data-selection-action="selection.select_same_provenance"]',
            ]:
                page.locator(selector).click()
                assert page.evaluate("() => window.__EDITOR_OFFSET_V2__.store.selection.size") >= 2
                page.evaluate(
                    "id => window.__EDITOR_OFFSET_V2__.store.setSelection([id], 'replace')",
                    first_id,
                )

            page.locator('[data-lock-surface="geometry"][data-lock-action="lock"]').click()
            page.locator('[data-selection-action="selection.select_locked_geometry"]').click()
            assert first_id in page.evaluate("() => [...window.__EDITOR_OFFSET_V2__.store.selection]")
            page.locator('[data-lock-surface="geometry"][data-lock-action="unlock"]').click()

            page.evaluate(
                """id => {
                  const app = window.__EDITOR_OFFSET_V2__;
                  const slot = app.store.layout.slots.find(item => item.id === id);
                  const geometry = window.EditorOffsetV2.GeometryView;
                  const reference = app.store.arrangement.geometryReference;
                  app.store.layout.sheet.printable_margins_mm.left = 20;
                  app.store.markChanged();
                  const printable = geometry.printableBounds(app.store.layout.sheet);
                  const bounds = window.EditorOffsetV2.AdvancedSelection.geometryBounds(
                    slot, geometry, reference
                  );
                  app.store.setSelection([id], 'replace');
                  app.runAction(window.EditorOffsetV2.CommandRegistry.ACTION_IDS.MOVE_ABSOLUTE, {
                    x_mm: slot.geometry.position_mm.x_mm + printable.left - 1 - bounds.left,
                    y_mm: slot.geometry.position_mm.y_mm,
                  });
                }""",
                third_id,
            )
            page.locator('[data-selection-action="selection.select_outside_printable"]').click()
            assert third_id in page.evaluate("() => [...window.__EDITOR_OFFSET_V2__.store.selection]")
            page.locator('[data-selection-action="selection.select_overlaps"]').click()
            assert {first_id, second_id}.issubset(
                set(page.evaluate("() => [...window.__EDITOR_OFFSET_V2__.store.selection]"))
            )

            first_tree = page.locator(f'[data-tree-node-type="slot"][data-tree-node-id="{first_id}"]')
            second_tree = page.locator(f'[data-tree-node-type="slot"][data-tree-node-id="{second_id}"]')
            first_tree.click()
            expect(first_tree).to_have_attribute("aria-selected", "true")
            second_tree.click(modifiers=["Control"])
            assert set(page.evaluate("() => [...window.__EDITOR_OFFSET_V2__.store.selection]")) == {
                first_id,
                second_id,
            }
            page.locator(f'[data-tree-node-type="slot"][data-tree-node-id="{third_id}"]').click(
                modifiers=["Shift"]
            )
            page.locator("#ev2-object-tree [role=treeitem]").first.focus()
            page.keyboard.press("End")
            page.keyboard.press("Home")
            page.keyboard.press("ArrowDown")
            page.keyboard.press("ArrowRight")
            page.keyboard.press("ArrowLeft")
            page.keyboard.press("ArrowRight")
            page.keyboard.press("Enter")

            page.evaluate(
                "ids => window.__EDITOR_OFFSET_V2__.store.setSelection(ids, 'replace')",
                [first_id, second_id],
            )
            page.locator("#ev2-arrangement-key-candidate").select_option(first_id)
            page.locator("#ev2-arrangement-key-set").click()
            expect(page.locator(f'[data-key-slot-badge="{first_id}"]')).to_have_count(1)
            expect(first_tree.locator(".ev2-tree-badge.is-key")).to_have_text("K")

            page.evaluate("() => window.__EDITOR_OFFSET_V2__.saver.manualSave()")
            page.wait_for_function(
                "() => window.__EDITOR_OFFSET_V2__.store.saveState.status === 'clean'"
            )
            temporary_before = page.evaluate(
                """() => {
                  const app = window.__EDITOR_OFFSET_V2__;
                  return {
                    layout: JSON.stringify(app.store.layout), revision: app.store.revision,
                    changeVersion: app.store.changeVersion, undo: app.store.undoStack.length,
                  };
                }"""
            )
            page.locator(f'[data-tree-visibility-slot="{first_id}"]').click()
            assert page.evaluate("() => window.__EDITOR_OFFSET_V2__.store.arrangement.keySlotId") is None
            expect(page.locator(f'.ev2-svg-slot[data-slot-id="{first_id}"]')).to_have_count(0)
            expect(first_tree).to_have_attribute("aria-disabled", "true")
            expect(page.locator('[data-tree-visibility-work]').first).to_have_attribute(
                "data-state", "mixed"
            )

            page.evaluate(
                "id => window.__EDITOR_OFFSET_V2__.store.setSelection([id], 'replace')",
                second_id,
            )
            page.locator("#ev2-visibility-hide-selection").click()
            expect(page.locator(f'.ev2-svg-slot[data-slot-id="{second_id}"]')).to_have_count(0)
            expect(second_tree).to_have_count(1)
            page.keyboard.press("Control+A")
            assert first_id not in page.evaluate("() => [...window.__EDITOR_OFFSET_V2__.store.selection]")
            assert second_id not in page.evaluate("() => [...window.__EDITOR_OFFSET_V2__.store.selection]")

            page.locator("#ev2-visibility-show-all").click()
            page.evaluate(
                "id => window.__EDITOR_OFFSET_V2__.store.setSelection([id], 'replace')",
                third_id,
            )
            page.locator("#ev2-visibility-isolate-selection").click()
            assert page.evaluate("() => window.__EDITOR_OFFSET_V2__.store.advancedSelection.hiddenSlotIds.size") >= 2
            page.locator("#ev2-visibility-restore").click()
            page.locator('[data-tree-visibility-work]').first.click()
            expect(page.locator('[data-tree-visibility-work]').first).to_have_attribute("data-state", "hidden")
            page.locator("#ev2-visibility-show-all").click()
            assert page.evaluate("() => window.__EDITOR_OFFSET_V2__.store.advancedSelection.hiddenSlotIds.size") == 0

            temporary_after = page.evaluate(
                """() => {
                  const app = window.__EDITOR_OFFSET_V2__;
                  return {
                    layout: JSON.stringify(app.store.layout), revision: app.store.revision,
                    changeVersion: app.store.changeVersion, undo: app.store.undoStack.length,
                  };
                }"""
            )
            assert temporary_after == temporary_before

            page.evaluate("() => window.__EDITOR_OFFSET_V2__.saver.manualSave()")
            page.wait_for_function(
                "() => window.__EDITOR_OFFSET_V2__.store.saveState.status === 'clean'"
            )
            persisted_layout = page.evaluate(
                "() => JSON.stringify(window.__EDITOR_OFFSET_V2__.store.layout)"
            )
            page.reload(wait_until="domcontentloaded")
            assert page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.advancedSelection.hiddenSlotIds.size"
            ) == 0
            assert page.evaluate(
                "() => JSON.stringify(window.__EDITOR_OFFSET_V2__.store.layout)"
            ) == persisted_layout
            expect(page.locator("#ev2-arrangement-heading")).to_be_visible()
            expect(page.locator("#ev2-object-operations-heading")).to_be_visible()
            with page.expect_response(
                lambda response: response.request.method == "GET"
                and response.url.endswith("/output-capabilities")
            ):
                page.locator("#ev2-output-check").click()
            expect(page.locator("#ev2-output-status")).to_be_visible()
            expect(page.locator(".ev2-svg-slot-label").first).to_have_text("#1")
            expect(page.locator("text=Reglas y guías")).to_have_count(0)
            assert not console_errors
            assert not page_errors
        finally:
            browser.close()


def test_v2_precision_rulers_guides_snap_measurement_and_reload(v2_server, tmp_path):
    pdf_path = tmp_path / "fase-8e.pdf"
    _write_test_pdf(pdf_path)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1680, "height": 1050})
        console_errors: list[str] = []
        page_errors: list[str] = []
        page.on(
            "console",
            lambda message: console_errors.append(message.text)
            if message.type == "error" and "favicon" not in message.text.lower()
            else None,
        )
        page.on("pageerror", lambda error: page_errors.append(str(error)))

        def domain_to_client(point: dict[str, float]) -> dict[str, float]:
            return page.evaluate(
                """point => {
                  const app = window.__EDITOR_OFFSET_V2__;
                  const svg = app.renderer.refs.canvas;
                  const svgPoint = svg.createSVGPoint();
                  svgPoint.x = point.x;
                  svgPoint.y = app.store.layout.sheet.size_mm.height - point.y;
                  const client = svgPoint.matrixTransform(svg.getScreenCTM());
                  return {x: client.x, y: client.y};
                }""",
                point,
            )

        def add_exact_guide(axis: str, value: float | str) -> None:
            page.locator("#ev2-precision-guide-axis").select_option(axis)
            page.locator("#ev2-precision-guide-position").fill(str(value))
            page.locator("#ev2-precision-guide-add").click()

        try:
            _open_job_with_repeat(page, v2_server, pdf_path, quantity=4)
            page.wait_for_function(
                "() => window.__EDITOR_OFFSET_V2__.store.saveState.status === 'clean'",
                timeout=10_000,
            )
            expect(page.locator("#ev2-precision-heading")).to_be_visible()
            baseline = page.evaluate(
                """() => {
                  const store = window.__EDITOR_OFFSET_V2__.store;
                  return {layout: JSON.stringify(store.layout), revision: store.revision,
                    changeVersion: store.changeVersion, undo: store.undoStack.length};
                }"""
            )

            page.locator("#ev2-precision-rulers").check()
            expect(page.locator(".ev2-svg-ruler-horizontal")).to_have_count(1)
            expect(page.locator(".ev2-svg-ruler-vertical")).to_have_count(1)
            expect(page.locator(".ev2-svg-ruler-corner")).to_have_count(1)
            expect(page.locator(".ev2-svg-ruler-horizontal text").first).to_be_visible()
            labels_before = page.locator(".ev2-svg-ruler-horizontal text").all_text_contents()
            page.evaluate("() => window.__EDITOR_OFFSET_V2__.store.setZoom(2)")
            labels_zoom = page.locator(".ev2-svg-ruler-horizontal text").all_text_contents()
            assert labels_zoom != labels_before
            page.evaluate("() => window.__EDITOR_OFFSET_V2__.store.setPan({x: 45, y: -25})")
            labels_pan = page.locator(".ev2-svg-ruler-horizontal text").all_text_contents()
            assert labels_pan != labels_zoom
            page.locator("#ev2-reset-view").click()

            add_exact_guide("x", "-12,5")
            assert page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.precisionTools.guides[0].position_mm"
            ) == -12.5
            expect(page.locator(".ev2-svg-guide[data-guide-axis='x']")).to_have_count(1)

            canvas_box = page.locator("#ev2-canvas").bounding_box()
            horizontal_box = page.locator(".ev2-svg-ruler-horizontal").bounding_box()
            vertical_box = page.locator(".ev2-svg-ruler-vertical").bounding_box()
            assert canvas_box and horizontal_box and vertical_box
            guide_count = page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.precisionTools.guides.length"
            )
            page.mouse.move(horizontal_box["x"] + horizontal_box["width"] * 0.65,
                            horizontal_box["y"] + 6)
            page.mouse.down()
            page.mouse.move(canvas_box["x"] + canvas_box["width"] * 0.65,
                            canvas_box["y"] + 100, steps=3)
            page.mouse.up()
            page.wait_for_function(
                "count => window.__EDITOR_OFFSET_V2__.store.precisionTools.guides.length === count + 1",
                arg=guide_count,
            )
            page.mouse.move(vertical_box["x"] + 6,
                            vertical_box["y"] + vertical_box["height"] * 0.55)
            page.mouse.down()
            page.mouse.move(canvas_box["x"] + 100,
                            canvas_box["y"] + canvas_box["height"] * 0.55, steps=3)
            page.mouse.up()
            page.wait_for_function(
                "count => window.__EDITOR_OFFSET_V2__.store.precisionTools.guides.length === count + 2",
                arg=guide_count,
            )
            assert page.evaluate(
                "() => new Set(window.__EDITOR_OFFSET_V2__.store.precisionTools.guides.map(g => g.axis)).size"
            ) == 2

            first_row_input = page.locator("#ev2-precision-guides-list li[data-guide-id]").first.locator("input")
            original_value = first_row_input.input_value()
            first_row_input.fill("999")
            first_row_input.press("Escape")
            assert first_row_input.input_value() == original_value
            first_row_input.fill("888")
            page.locator("#ev2-precision-heading").click()
            assert first_row_input.input_value() == original_value
            first_row_input.fill("100,25")
            page.locator("#ev2-precision-guides-list li[data-guide-id]").first.locator(
                "button[data-guide-action='update']"
            ).click()
            assert page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.precisionTools.guides[0].position_mm"
            ) == 100.25
            sheet_height = page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.sheet.size_mm.height"
            )
            guide_start = domain_to_client({"x": 100.25, "y": sheet_height / 2})
            guide_end = domain_to_client({"x": 125.5, "y": sheet_height / 2})
            page.mouse.move(guide_start["x"], guide_start["y"])
            page.mouse.down()
            page.mouse.move(guide_end["x"], guide_end["y"], steps=3)
            page.mouse.up()
            assert page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.precisionTools.guides[0].position_mm"
            ) == pytest.approx(125.5, abs=1e-3)
            last_row = page.locator("#ev2-precision-guides-list li[data-guide-id]").last
            last_row.focus()
            page.keyboard.press("Delete")
            page.wait_for_function(
                "count => window.__EDITOR_OFFSET_V2__.store.precisionTools.guides.length === count + 1",
                arg=guide_count,
            )

            temporary = page.evaluate(
                """() => {
                  const store = window.__EDITOR_OFFSET_V2__.store;
                  return {layout: JSON.stringify(store.layout), revision: store.revision,
                    changeVersion: store.changeVersion, undo: store.undoStack.length};
                }"""
            )
            assert temporary == baseline

            page.locator("#ev2-precision-guides-clear").click()
            first = page.evaluate(
                """() => {
                  const slot = window.__EDITOR_OFFSET_V2__.store.layout.slots[0];
                  return {id: slot.id, x: slot.geometry.position_mm.x_mm,
                    y: slot.geometry.position_mm.y_mm};
                }"""
            )
            snap_x = first["x"] + 40
            add_exact_guide("x", snap_x)
            page.locator("#ev2-precision-snap-enabled").check()
            page.locator("#ev2-precision-snap-slots").uncheck()
            page.locator("#ev2-precision-snap-sheet").uncheck()
            page.locator("#ev2-precision-snap-printable").uncheck()
            page.evaluate(
                "id => window.__EDITOR_OFFSET_V2__.store.setSelection([id], 'replace')",
                first["id"],
            )
            undo_before = page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.undoStack.length"
            )
            start = domain_to_client({"x": first["x"], "y": first["y"]})
            end = domain_to_client({"x": snap_x, "y": first["y"]})
            page.mouse.move(start["x"], start["y"])
            page.mouse.down()
            page.mouse.move(end["x"] - 2, end["y"], steps=4)
            expect(page.locator(".ev2-svg-smart-guide[data-smart-guide-axis='x']")).to_have_count(1)
            expect(page.locator(".ev2-svg-smart-guide-label")).to_contain_text("guía")
            assert page.locator(".ev2-svg-smart-guide").first.evaluate(
                "element => getComputedStyle(element).pointerEvents"
            ) == "none"
            page.mouse.up()
            expect(page.locator(".ev2-svg-smart-guide")).to_have_count(0)
            assert page.evaluate(
                "id => window.__EDITOR_OFFSET_V2__.store.layout.slots.find(s => s.id === id).geometry.position_mm.x_mm",
                first["id"],
            ) == pytest.approx(snap_x)
            assert page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.undoStack.length"
            ) == undo_before + 1
            page.locator("#ev2-undo").click()
            page.locator("#ev2-redo").click()

            count_before_duplicate = page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.slots.length"
            )
            duplicate_x = snap_x + 45
            page.locator("#ev2-precision-guides-clear").click()
            add_exact_guide("x", duplicate_x)
            start = domain_to_client({"x": snap_x, "y": first["y"]})
            end = domain_to_client({"x": duplicate_x, "y": first["y"]})
            page.keyboard.down("Alt")
            page.mouse.move(start["x"], start["y"])
            page.mouse.down()
            page.mouse.move(end["x"] - 2, end["y"], steps=4)
            expect(page.locator(".ev2-svg-smart-guide")).to_have_count(1)
            page.mouse.up()
            page.keyboard.up("Alt")
            assert page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.slots.length"
            ) == count_before_duplicate + 1
            page.locator("#ev2-undo").click()
            assert page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.slots.length"
            ) == count_before_duplicate

            current = page.evaluate(
                """id => {
                  const slot = window.__EDITOR_OFFSET_V2__.store.layout.slots.find(s => s.id === id);
                  return {x: slot.geometry.position_mm.x_mm, y: slot.geometry.position_mm.y_mm};
                }""",
                first["id"],
            )
            start = domain_to_client(current)
            page.mouse.move(start["x"], start["y"])
            page.mouse.down()
            page.mouse.move(start["x"] + 18, start["y"], steps=3)
            page.keyboard.press("Escape")
            page.mouse.up()
            expect(page.locator(".ev2-svg-smart-guide")).to_have_count(0)
            assert page.evaluate(
                "id => window.__EDITOR_OFFSET_V2__.store.layout.slots.find(s => s.id === id).geometry.position_mm.x_mm",
                first["id"],
            ) == pytest.approx(current["x"])

            page.locator("#ev2-precision-snap-enabled").uncheck()
            page.locator("#ev2-precision-measure-toggle").click()
            measure_start = domain_to_client({"x": 30, "y": 30})
            measure_end = domain_to_client({"x": 33, "y": 34})
            page.mouse.click(measure_start["x"], measure_start["y"])
            page.mouse.move(measure_end["x"], measure_end["y"], steps=3)
            expect(page.locator(".ev2-svg-measurement")).to_have_count(1)
            page.mouse.click(measure_end["x"], measure_end["y"])
            measurement = page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.precisionTools.lastMeasurement"
            )
            assert measurement["deltaX"] == pytest.approx(3, abs=1e-3)
            assert measurement["deltaY"] == pytest.approx(4, abs=1e-3)
            assert measurement["distance"] == pytest.approx(5, abs=1e-3)
            expect(page.locator("#ev2-precision-measurement-result")).to_contain_text("Distancia 5 mm")
            page.locator("#ev2-precision-measure-toggle").click()

            ids = page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.slots.slice(0, 3).map(slot => slot.id)"
            )
            page.evaluate(
                "ids => window.__EDITOR_OFFSET_V2__.store.setSelection(ids.slice(0, 2), 'replace')",
                ids,
            )
            expect(page.locator("#ev2-precision-selection-metrics")).to_contain_text("2 slots")
            expect(page.locator("#ev2-precision-selection-metrics")).to_contain_text("Gap X")
            page.evaluate(
                "ids => window.__EDITOR_OFFSET_V2__.store.setSelection(ids, 'replace')", ids
            )
            expect(page.locator("#ev2-precision-selection-metrics")).to_contain_text("3 slots")
            expect(page.locator("#ev2-precision-selection-metrics")).to_contain_text("Aggregate")

            page.evaluate("() => window.__EDITOR_OFFSET_V2__.saver.manualSave()")
            page.wait_for_function(
                "() => window.__EDITOR_OFFSET_V2__.store.saveState.status === 'clean'",
                timeout=10_000,
            )
            persisted = page.evaluate(
                "() => JSON.stringify(window.__EDITOR_OFFSET_V2__.store.layout)"
            )
            assert page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.precisionTools.guides.length"
            ) == 1
            page.reload(wait_until="domcontentloaded")
            assert page.evaluate(
                "() => JSON.stringify(window.__EDITOR_OFFSET_V2__.store.layout)"
            ) == persisted
            assert page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.precisionTools.guides.length"
            ) == 0
            assert page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.precisionTools.measurementMode"
            ) is False
            expect(page.locator("#ev2-arrangement-heading")).to_be_visible()
            expect(page.locator("#ev2-advanced-selection-heading")).to_be_visible()
            expect(page.locator(".ev2-svg-slot-label").first).to_have_text("#1")
            expect(page.locator(".ev2-resize-handle, [data-resize-handle]")).to_have_count(0)
            with page.expect_response(
                lambda response: response.request.method == "GET"
                and response.url.endswith("/output-capabilities")
            ):
                page.locator("#ev2-output-check").click()
            expect(page.locator("#ev2-output-status")).to_be_visible()
            assert not console_errors
            assert not page_errors
        finally:
            browser.close()
