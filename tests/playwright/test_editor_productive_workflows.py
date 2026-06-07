import re
import uuid
from io import BytesIO

from playwright.sync_api import Error, Page, Response, expect, sync_playwright


EDITOR_URL = "http://127.0.0.1:5000/editor_offset_visual"


def _is_serious_console_error(text: str) -> bool:
    ignored_fragments = [
        "Failed to load resource: the server responded with a status of 404 (NOT FOUND)",
    ]
    return not any(fragment in text for fragment in ignored_fragments)


def _job_url() -> str:
    return f"{EDITOR_URL}?job_id=pw6b_{uuid.uuid4().hex}"


def _open_editor(page: Page, tab: str = "edition") -> None:
    page.goto(_job_url(), wait_until="domcontentloaded", timeout=15_000)
    page.wait_for_selector("#sheet", state="attached", timeout=10_000)
    page.wait_for_selector("#sheet-canvas", state="attached", timeout=10_000)
    _open_tab(page, tab)


def _open_tab(page: Page, tab: str) -> None:
    page.locator(f'[data-editor-tab="{tab}"]').click()
    expect(page.locator(f'[data-editor-tab-panel="{tab}"]')).to_be_visible()


def _slot_count(page: Page) -> int:
    return page.locator(".slot").count()


def _create_slot(page: Page, x_mm: float, y_mm: float, w_mm: float = 30, h_mm: float = 30) -> None:
    _open_tab(page, "edition")
    page.locator("#btn-new-slot").click()
    expect(page.locator("#slot-form")).to_be_visible()
    page.locator("#slot-x").fill(str(x_mm))
    page.locator("#slot-y").fill(str(y_mm))
    page.locator("#slot-w").fill(str(w_mm))
    page.locator("#slot-h").fill(str(h_mm))
    page.locator("#btn-apply-slot").click()
    expect(page.locator(".slot.selected")).to_have_count(1)


def _assert_no_browser_errors(console_errors: list[str], page_errors: list[str]) -> None:
    assert not console_errors
    assert not page_errors


def _json(response: Response) -> dict:
    data = response.json()
    assert isinstance(data, dict)
    return data


def _wait_for_post(page: Page, url_fragment: str):
    return page.expect_response(
        lambda response: url_fragment in response.url and response.request.method == "POST"
    )


def _minimal_pdf_bytes() -> bytes:
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(50 * mm, 35 * mm))
    c.setTitle("playwright-6b-fixture")
    c.rect(5 * mm, 5 * mm, 40 * mm, 25 * mm, stroke=1, fill=0)
    c.drawString(8 * mm, 18 * mm, "PW 6B")
    c.save()
    return buffer.getvalue()


def test_face_switch_zoom_and_geometry_panel_survive_rerenders():
    console_errors: list[str] = []
    page_errors: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.on(
            "console",
            lambda msg: console_errors.append(msg.text)
            if msg.type == "error" and _is_serious_console_error(msg.text)
            else None,
        )
        page.on("pageerror", lambda exc: page_errors.append(str(exc)))

        try:
            _open_editor(page)
            _create_slot(page, 20, 20, 35, 25)

            expect(page.locator("#geometry-validation-panel")).to_be_visible()
            expect(page.locator("#geometry-validation-summary")).not_to_contain_text("Sin revisar")

            initial_zoom = page.locator("#zoom-label").inner_text()
            page.locator("#zoom-in").click()
            page.wait_for_function(
                "initial => document.querySelector('#zoom-label')?.textContent !== initial",
                arg=initial_zoom,
            )
            zoomed_in = page.locator("#zoom-label").inner_text()
            page.locator("#zoom-out").click()
            page.wait_for_function(
                "current => document.querySelector('#zoom-label')?.textContent !== current",
                arg=zoomed_in,
            )

            page.locator("#btn-duplicate-face").click()
            expect(page.locator("#face-back")).to_be_checked()
            expect(page.locator(".slot")).to_have_count(1)

            page.locator("#face-front").check()
            expect(page.locator(".slot")).to_have_count(1)
            page.locator("#face-back").check()
            expect(page.locator(".slot")).to_have_count(1)
            expect(page.locator(".slot .handle")).to_have_count(0)

            _assert_no_browser_errors(console_errors, page_errors)
        except Error as exc:
            raise AssertionError(
                f"No se pudo abrir {EDITOR_URL}. Verifica que Flask este corriendo con `python app.py`."
            ) from exc
        finally:
            browser.close()


def test_save_layout_from_ui_keeps_canvas_stable():
    console_errors: list[str] = []
    page_errors: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.on(
            "console",
            lambda msg: console_errors.append(msg.text)
            if msg.type == "error" and _is_serious_console_error(msg.text)
            else None,
        )
        page.on("pageerror", lambda exc: page_errors.append(str(exc)))

        try:
            _open_editor(page)
            _create_slot(page, 25, 25, 30, 30)

            with _wait_for_post(page, "/editor_offset/save") as response_info:
                page.locator("#btn-save").click()
            response = response_info.value
            assert response.status == 200
            assert _json(response).get("ok") is True

            expect(page.locator("#sheet")).to_be_visible()
            expect(page.locator("#sheet-canvas")).to_be_visible()
            expect(page.locator(".slot")).to_have_count(1)
            expect(page.locator(".slot.selected")).to_have_count(1)
            expect(page.locator("#geometry-validation-panel")).to_be_visible()

            _assert_no_browser_errors(console_errors, page_errors)
        except Error as exc:
            raise AssertionError(
                f"No se pudo abrir {EDITOR_URL}. Verifica que Flask este corriendo con `python app.py`."
            ) from exc
        finally:
            browser.close()


def test_step_repeat_ui_generates_slots_and_undo_restores_count():
    console_errors: list[str] = []
    page_errors: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.on(
            "console",
            lambda msg: console_errors.append(msg.text)
            if msg.type == "error" and _is_serious_console_error(msg.text)
            else None,
        )
        page.on("pageerror", lambda exc: page_errors.append(str(exc)))

        try:
            _open_editor(page)
            _create_slot(page, 15, 15, 25, 20)
            expect(page.locator(".slot")).to_have_count(1)

            page.locator("#sr-rows").fill("2")
            page.locator("#sr-cols").fill("2")
            page.locator("#sr-gap-h").fill("4")
            page.locator("#sr-gap-v").fill("5")
            page.locator("#sr-generate").click()

            expect(page.locator(".slot")).to_have_count(4)
            expect(page.locator(".slot.selected")).to_have_count(1)

            page.locator("#sheet-canvas").click()
            page.keyboard.press("Control+Z")
            expect(page.locator(".slot")).to_have_count(1)
            expect(page.locator(".slot.selected")).to_have_count(0)

            _assert_no_browser_errors(console_errors, page_errors)
        except Error as exc:
            raise AssertionError(
                f"No se pudo abrir {EDITOR_URL}. Verifica que Flask este corriendo con `python app.py`."
            ) from exc
        finally:
            browser.close()


def test_upload_apply_imposition_preview_and_pdf_from_ui():
    console_errors: list[str] = []
    page_errors: list[str] = []
    pdf_bytes = _minimal_pdf_bytes()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.on(
            "console",
            lambda msg: console_errors.append(msg.text)
            if msg.type == "error" and _is_serious_console_error(msg.text)
            else None,
        )
        page.on("pageerror", lambda exc: page_errors.append(str(exc)))
        page.on("dialog", lambda dialog: dialog.accept())

        try:
            _open_editor(page, tab="works")
            page.locator("#btn-new-work").click()
            page.locator("#work-name").fill("Trabajo 6B")
            page.locator("#work-w").fill("50")
            page.locator("#work-h").fill("35")
            page.locator("#work-copies").fill("2")
            page.locator("#work-bleed").fill("0")
            page.locator("#btn-save-work").click()
            expect(page.locator("#works-list .item")).to_have_count(1)

            _open_tab(page, "designs")
            page.locator("#design-work-select").select_option(index=1)
            page.locator("#design-files").set_input_files(
                {
                    "name": "pieza_6b.pdf",
                    "mimeType": "application/pdf",
                    "buffer": pdf_bytes,
                }
            )
            with _wait_for_post(page, "/editor_offset/upload/") as upload_info:
                page.locator('#upload-form button[type="submit"]').click()
            upload_response = upload_info.value
            assert upload_response.status == 200
            assert len(_json(upload_response).get("designs", [])) == 1
            expect(page.locator(".design-item")).to_have_count(1)

            _open_tab(page, "imposition")
            page.locator('input[name="imposition-engine"][value="repeat"]').check()
            with _wait_for_post(page, "/editor_offset_visual/apply_imposition") as imposition_info:
                page.locator("#btn-apply-imposition").click()
            imposition_response = imposition_info.value
            assert imposition_response.status == 200
            assert _json(imposition_response).get("ok") is True
            page.wait_for_function("() => document.querySelectorAll('.slot').length >= 1")
            assert page.locator(".slot").count() >= 1
            expect(page.locator(".slot .handle")).to_have_count(0)

            _open_tab(page, "output")
            with _wait_for_post(page, "/editor_offset/preview/") as preview_info:
                page.locator("#btn-preview").click()
            preview_response = preview_info.value
            assert preview_response.status == 200
            assert _json(preview_response).get("ok") is True
            expect(page.locator("#preview-image")).to_have_attribute("src", re.compile(r".+"))

            with _wait_for_post(page, "/editor_offset/generar_pdf/") as pdf_info:
                page.locator("#btn-pdf").click()
            pdf_response = pdf_info.value
            assert pdf_response.status == 200
            assert _json(pdf_response).get("ok") is True
            expect(page.locator("#pdf-output a")).to_be_visible()
            expect(page.locator("#pdf-output a")).to_have_attribute("href", re.compile(r"\.pdf"))

            _assert_no_browser_errors(console_errors, page_errors)
        except Error as exc:
            raise AssertionError(
                f"No se pudo abrir {EDITOR_URL}. Verifica que Flask este corriendo con `python app.py`."
            ) from exc
        finally:
            browser.close()
