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
def v2_characterization_server(tmp_path):
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
    page.insert_text((36, 70), "EDITOR OFFSET V2 UX", fontsize=18)
    page.draw_rect(fitz.Rect(18, 18, 237, 123), color=(0.1, 0.4, 0.8), width=3)
    document.save(path)
    document.close()


def _new_page(browser_or_context, *, width: int = 1440, height: int = 900):
    if hasattr(browser_or_context, "new_context"):
        page = browser_or_context.new_page(viewport={"width": width, "height": height})
    else:
        page = browser_or_context.new_page()
    browser_errors = {"console": [], "page": []}
    page.on(
        "console",
        lambda message: browser_errors["console"].append(message.text)
        if message.type == "error" and "favicon" not in message.text.lower()
        else None,
    )
    page.on("pageerror", lambda error: browser_errors["page"].append(str(error)))
    return page, browser_errors


def _open_job_with_repeat(page, server_url: str, pdf_path: Path, *, quantity: int) -> None:
    page.goto(f"{server_url}/editor_offset_visual_v2", wait_until="domcontentloaded")
    page.locator("#ev2-new-job").click()
    page.wait_for_url("**/editor_offset_visual_v2/ev2_*", timeout=10_000)

    page.locator("#ev2-asset-file").set_input_files(str(pdf_path))
    with page.expect_response(
        lambda response: response.request.method == "POST" and "/assets" in response.url,
    ) as upload_info:
        page.locator("#ev2-asset-upload-button").click()
    assert upload_info.value.status == 201
    expect(page.locator(".ev2-asset-card")).to_have_count(1)

    page.locator("#ev2-work-quantity").fill(str(quantity))
    page.locator("#ev2-create-work").click()
    page.wait_for_function(
        "() => window.__EDITOR_OFFSET_V2__.store.layout.works.length === 1"
    )
    with page.expect_response(
        lambda response: response.request.method == "POST"
        and "/imposition/repeat" in response.url,
    ) as repeat_info:
        page.locator("#ev2-repeat-calculate").click()
    assert repeat_info.value.status == 200
    page.wait_for_function(
        "() => window.__EDITOR_OFFSET_V2__.store.repeatPanel.status === 'ready'"
    )
    page.locator("#ev2-repeat-apply").click()
    expect(page.locator(".ev2-svg-slot")).to_have_count(quantity)
    page.wait_for_function(
        "() => window.__EDITOR_OFFSET_V2__.store.saveState.status === 'clean'",
        timeout=10_000,
    )


def _select_slot(page, slot_id: str) -> None:
    page.evaluate(
        "slotId => window.__EDITOR_OFFSET_V2__.store.setSelection([slotId], 'replace')",
        slot_id,
    )


def _move_selected_with_position_form(page, x_mm: float) -> None:
    page.locator("#ev2-position-x").fill(str(x_mm))
    page.locator("#ev2-position-apply").click()


def _assert_no_console_errors(
    errors: dict[str, list[str]],
    *,
    allowed_fragments: tuple[str, ...] = (),
) -> None:
    unexpected = [
        message
        for message in errors["console"]
        if not any(fragment in message for fragment in allowed_fragments)
    ]
    assert not unexpected, f"Errores de consola inesperados: {unexpected}"


def test_stab_001_nudge_moves_without_pageerror(v2_characterization_server, tmp_path):
    pdf_path = tmp_path / "stab-001-nudge.pdf"
    _write_test_pdf(pdf_path)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page, errors = _new_page(browser)
        try:
            _open_job_with_repeat(
                page,
                v2_characterization_server,
                pdf_path,
                quantity=1,
            )
            slot_id = page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.slots[0].id"
            )
            _select_slot(page, slot_id)
            before_x = page.evaluate(
                "id => window.__EDITOR_OFFSET_V2__.store.layout.slots.find(slot => slot.id === id).geometry.position_mm.x_mm",
                slot_id,
            )
            history_before = page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.undoStack.length"
            )

            page.locator("#ev2-canvas").focus()
            page.keyboard.press("ArrowRight")
            page.wait_for_timeout(350)

            after_x = page.evaluate(
                "id => window.__EDITOR_OFFSET_V2__.store.layout.slots.find(slot => slot.id === id).geometry.position_mm.x_mm",
                slot_id,
            )
            assert after_x == pytest.approx(before_x + 0.1)
            assert page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.undoStack.length"
            ) == history_before + 1

            page.keyboard.press("Control+Z")
            assert page.evaluate(
                "id => window.__EDITOR_OFFSET_V2__.store.layout.slots.find(slot => slot.id === id).geometry.position_mm.x_mm",
                slot_id,
            ) == pytest.approx(before_x)
            page.keyboard.press("Control+Shift+Z")
            assert page.evaluate(
                "id => window.__EDITOR_OFFSET_V2__.store.layout.slots.find(slot => slot.id === id).geometry.position_mm.x_mm",
                slot_id,
            ) == pytest.approx(after_x)

            page.evaluate("() => window.__EDITOR_OFFSET_V2__.saver.manualSave()")
            page.wait_for_function(
                "() => window.__EDITOR_OFFSET_V2__.store.saveState.status === 'clean'",
                timeout=10_000,
            )
            page.reload(wait_until="domcontentloaded")
            expect(page.locator(".ev2-svg-slot")).to_have_count(1)
            assert page.evaluate(
                "id => window.__EDITOR_OFFSET_V2__.store.layout.slots.find(slot => slot.id === id).geometry.position_mm.x_mm",
                slot_id,
            ) == pytest.approx(after_x)
            _assert_no_console_errors(errors)
            unexpected = [
                message
                for message in errors["page"]
                if "illegal invocation" not in message.lower()
            ]
            assert not unexpected, f"Pageerrors inesperados: {unexpected}"
            if errors["page"]:
                pytest.xfail(
                    "STAB-001 confirmado: nudge_controller provoca TypeError: Illegal invocation"
                )
            assert not errors["page"]
        finally:
            browser.close()


def test_stab_002_delete_preserves_source_reference_integrity(
    v2_characterization_server,
    tmp_path,
):
    pdf_path = tmp_path / "stab-002-delete-dependency.pdf"
    _write_test_pdf(pdf_path)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page, errors = _new_page(browser)
        try:
            _open_job_with_repeat(
                page,
                v2_characterization_server,
                pdf_path,
                quantity=1,
            )
            source_id = page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.slots[0].id"
            )
            _select_slot(page, source_id)
            page.keyboard.press("Control+D")
            expect(page.locator(".ev2-svg-slot")).to_have_count(2)

            dependent = page.evaluate(
                "() => { const store = window.__EDITOR_OFFSET_V2__.store; "
                "const selected = store.layout.slots.find(slot => store.selection.has(slot.id)); "
                "return { id: selected.id, sourceId: selected.generated_by.source_slot_id }; }"
            )
            assert dependent["sourceId"] == source_id
            page.evaluate("() => window.__EDITOR_OFFSET_V2__.saver.manualSave()")
            page.wait_for_function(
                "() => window.__EDITOR_OFFSET_V2__.store.saveState.status === 'clean'",
                timeout=10_000,
            )

            _select_slot(page, source_id)
            history_before = page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.undoStack.length"
            )
            page.locator("#ev2-canvas").focus()
            page.keyboard.press("Delete")
            expect(page.locator("#ev2-status-message")).to_contain_text(
                "1 slot dependiente quedaría sin origen"
            )
            expect(page.locator("#ev2-status-message")).to_contain_text(
                "Selecciona también ese dependiente"
            )
            expect(page.locator(".ev2-svg-slot")).to_have_count(2)

            result = page.evaluate(
                """() => {
                  const store = window.__EDITOR_OFFSET_V2__.store;
                  const ids = new Set(store.layout.slots.map(slot => slot.id));
                  const broken = store.layout.slots
                    .filter(slot => slot.generated_by?.source_slot_id
                      && !ids.has(slot.generated_by.source_slot_id))
                    .map(slot => ({id: slot.id, source: slot.generated_by.source_slot_id}));
                  return {broken, saveStatus: store.saveState.status};
                }"""
            )
            assert result == {"broken": [], "saveStatus": "clean"}
            assert page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.undoStack.length"
            ) == history_before

            page.evaluate(
                "ids => window.__EDITOR_OFFSET_V2__.store.setSelection(ids, 'replace')",
                [source_id, dependent["id"]],
            )
            page.locator("#ev2-canvas").focus()
            page.keyboard.press("Delete")
            expect(page.locator(".ev2-svg-slot")).to_have_count(0)
            assert page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.undoStack.length"
            ) == history_before + 1
            page.keyboard.press("Control+Z")
            expect(page.locator(".ev2-svg-slot")).to_have_count(2)
            assert page.evaluate(
                "() => [...window.__EDITOR_OFFSET_V2__.store.selection]"
            ) == [source_id, dependent["id"]]

            page.evaluate("() => window.__EDITOR_OFFSET_V2__.saver.manualSave()")
            page.wait_for_function(
                "() => window.__EDITOR_OFFSET_V2__.store.saveState.status === 'clean'",
                timeout=10_000,
            )
            page.reload(wait_until="domcontentloaded")
            expect(page.locator(".ev2-svg-slot")).to_have_count(2)
            assert page.evaluate(
                """() => {
                  const store = window.__EDITOR_OFFSET_V2__.store;
                  const ids = new Set(store.layout.slots.map(slot => slot.id));
                  return store.layout.slots.every(slot => !slot.generated_by?.source_slot_id
                    || ids.has(slot.generated_by.source_slot_id));
                }"""
            ) is True
            _assert_no_console_errors(errors)
            assert not errors["page"], f"Pageerrors inesperados: {errors['page']}"
        finally:
            browser.close()


def test_stab_003_output_diagnosis_is_invalidated_after_revision_change(
    v2_characterization_server,
    tmp_path,
):
    pdf_path = tmp_path / "stab-003-output-revision.pdf"
    _write_test_pdf(pdf_path)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page, errors = _new_page(browser)
        try:
            _open_job_with_repeat(
                page,
                v2_characterization_server,
                pdf_path,
                quantity=1,
            )
            slot_id = page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.slots[0].id"
            )
            _select_slot(page, slot_id)

            with page.expect_response(
                lambda response: response.request.method == "GET"
                and response.url.endswith("/output-capabilities"),
            ):
                page.locator("#ev2-output-check").click()
            checked_revision = page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.revision"
            )
            expect(page.locator("#ev2-output-status")).to_contain_text(
                f"revisión {checked_revision}"
            )

            current_x = page.evaluate(
                "id => window.__EDITOR_OFFSET_V2__.store.layout.slots.find(slot => slot.id === id).geometry.position_mm.x_mm",
                slot_id,
            )
            _move_selected_with_position_form(page, current_x + 0.25)
            expect(page.locator("#ev2-output-status")).to_contain_text(
                "Diagnóstico desactualizado"
            )
            expect(page.locator("#ev2-output-status")).to_contain_text(
                "Guarda y vuelve a consultar compatibilidad"
            )
            expect(page.locator("#ev2-output-status")).to_have_attribute(
                "data-state", "warning"
            )
            page.evaluate("() => window.__EDITOR_OFFSET_V2__.saver.manualSave()")
            page.wait_for_function(
                "() => window.__EDITOR_OFFSET_V2__.store.saveState.status === 'clean'",
                timeout=10_000,
            )
            current_revision = page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.revision"
            )
            assert current_revision > checked_revision

            expect(page.locator("#ev2-output-status")).to_contain_text(
                f"se comprobó la revisión {checked_revision}"
            )
            expect(page.locator("#ev2-output-status")).to_contain_text(
                f"la revisión actual es {current_revision}"
            )
            expect(page.locator("#ev2-output-status")).to_contain_text(
                "Vuelve a consultar compatibilidad"
            )

            with page.expect_response(
                lambda response: response.request.method == "GET"
                and response.url.endswith("/output-capabilities"),
            ):
                page.locator("#ev2-output-check").click()
            expect(page.locator("#ev2-output-status")).to_contain_text(
                f"revisión {current_revision}"
            )
            expect(page.locator("#ev2-output-status")).not_to_contain_text(
                "Diagnóstico desactualizado"
            )
            assert page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.outputPanel.checkedRevision"
            ) == current_revision
            _assert_no_console_errors(errors)
            assert not errors["page"], f"Pageerrors inesperados: {errors['page']}"
        finally:
            browser.close()


def test_stab_004_matrix_double_activation_creates_only_one_operation(
    v2_characterization_server,
    tmp_path,
):
    pdf_path = tmp_path / "stab-004-matrix-double-submit.pdf"
    _write_test_pdf(pdf_path)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page, errors = _new_page(browser, width=1600, height=1000)
        try:
            _open_job_with_repeat(
                page,
                v2_characterization_server,
                pdf_path,
                quantity=1,
            )
            source_id = page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.slots[0].id"
            )
            _select_slot(page, source_id)
            count_before = page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.slots.length"
            )
            history_before = page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.undoStack.length"
            )
            page.locator("#ev2-arrangement-matrix-rows").fill("2")
            page.locator("#ev2-arrangement-matrix-columns").fill("2")
            page.locator("#ev2-arrangement-matrix-gap-x").fill("10")
            page.locator("#ev2-arrangement-matrix-gap-y").fill("10")
            expect(page.locator("#ev2-arrangement-matrix-summary")).to_contain_text(
                "3 slots nuevos"
            )

            page.locator("#ev2-arrangement-matrix-apply").dblclick()
            page.wait_for_timeout(150)

            count_after = page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.slots.length"
            )
            expected_count = count_before + 3
            selected_after = page.evaluate(
                "() => [...window.__EDITOR_OFFSET_V2__.store.selection]"
            )
            _assert_no_console_errors(errors)
            assert not errors["page"], f"Pageerrors inesperados: {errors['page']}"
            assert count_after == expected_count
            assert len(selected_after) == 3
            assert page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.undoStack.length"
            ) == history_before + 1
            expect(page.locator("#ev2-arrangement-feedback")).to_contain_text(
                "La matriz ya fue creada"
            )

            page.locator("#ev2-undo").click()
            expect(page.locator(".ev2-svg-slot")).to_have_count(count_before)
            assert page.evaluate(
                "() => [...window.__EDITOR_OFFSET_V2__.store.selection]"
            ) == [source_id]

            page.locator("#ev2-redo").click()
            expect(page.locator(".ev2-svg-slot")).to_have_count(expected_count)
            assert page.evaluate(
                "() => [...window.__EDITOR_OFFSET_V2__.store.selection]"
            ) == selected_after

            _select_slot(page, source_id)
            page.locator("#ev2-arrangement-matrix-apply").click()
            expect(page.locator(".ev2-svg-slot")).to_have_count(expected_count + 3)
            assert page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.undoStack.length"
            ) == history_before + 2

            page.evaluate("() => window.__EDITOR_OFFSET_V2__.saver.manualSave()")
            page.wait_for_function(
                "() => window.__EDITOR_OFFSET_V2__.store.saveState.status === 'clean'",
                timeout=10_000,
            )
            page.reload(wait_until="domcontentloaded")
            expect(page.locator(".ev2-svg-slot")).to_have_count(expected_count + 3)
            _assert_no_console_errors(errors)
            assert not errors["page"], f"Pageerrors inesperados: {errors['page']}"
        finally:
            browser.close()


def test_stab_005_revision_conflict_explains_recovery_in_operator_language(
    v2_characterization_server,
    tmp_path,
):
    pdf_path = tmp_path / "stab-005-conflict.pdf"
    _write_test_pdf(pdf_path)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        first_page, first_errors = _new_page(context)
        second_page = None
        try:
            _open_job_with_repeat(
                first_page,
                v2_characterization_server,
                pdf_path,
                quantity=1,
            )
            job_url = first_page.url
            slot_id = first_page.evaluate(
                "() => window.__EDITOR_OFFSET_V2__.store.layout.slots[0].id"
            )
            original_x = first_page.evaluate(
                "id => window.__EDITOR_OFFSET_V2__.store.layout.slots.find(slot => slot.id === id).geometry.position_mm.x_mm",
                slot_id,
            )

            second_page, second_errors = _new_page(context)
            second_page.goto(job_url, wait_until="domcontentloaded")
            expect(second_page.locator(".ev2-svg-slot")).to_have_count(1)

            _select_slot(first_page, slot_id)
            _move_selected_with_position_form(first_page, original_x + 0.2)
            first_page.evaluate("() => window.__EDITOR_OFFSET_V2__.saver.manualSave()")
            first_page.wait_for_function(
                "() => window.__EDITOR_OFFSET_V2__.store.saveState.status === 'clean'",
                timeout=10_000,
            )

            _select_slot(second_page, slot_id)
            _move_selected_with_position_form(second_page, original_x + 0.3)
            second_page.evaluate("() => window.__EDITOR_OFFSET_V2__.saver.manualSave()")
            second_page.wait_for_function(
                "() => window.__EDITOR_OFFSET_V2__.store.saveState.status === 'conflict'",
                timeout=10_000,
            )

            expect(second_page.locator("#ev2-save-status")).to_have_text(
                "Conflicto de revisión"
            )
            expect(second_page.locator("#ev2-reload-conflict")).to_be_visible()
            message = second_page.locator("#ev2-status-message").inner_text()
            normalized = message.lower()
            technical_message = "submitted base revision" in normalized
            has_operator_guidance = any(
                token in normalized
                for token in (
                    "otra pestaña",
                    "versión remota",
                    "versión más reciente",
                    "recarga",
                    "cambios más recientes",
                )
            )
            _assert_no_console_errors(first_errors)
            _assert_no_console_errors(
                second_errors,
                allowed_fragments=("status of 409 (CONFLICT)",),
            )
            assert not first_errors["page"], f"Pageerrors inesperados: {first_errors['page']}"
            assert not second_errors["page"], f"Pageerrors inesperados: {second_errors['page']}"
            if technical_message and not has_operator_guidance:
                pytest.xfail(
                    "STAB-005 confirmado: el conflicto muestra el mensaje técnico del API sin guía operativa"
                )
            assert not technical_message
            assert has_operator_guidance
        finally:
            if second_page is not None:
                second_page.close()
            context.close()
            browser.close()
