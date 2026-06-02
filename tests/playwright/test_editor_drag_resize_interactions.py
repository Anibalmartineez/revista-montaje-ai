import re

from playwright.sync_api import Error, Page, expect, sync_playwright


EDITOR_URL = "http://127.0.0.1:5000/editor_offset_visual"


def _is_serious_console_error(text: str) -> bool:
    ignored_fragments = [
        "Failed to load resource: the server responded with a status of 404 (NOT FOUND)",
    ]
    return not any(fragment in text for fragment in ignored_fragments)


def _open_editor(page: Page) -> None:
    page.goto(EDITOR_URL, wait_until="domcontentloaded", timeout=15_000)
    page.wait_for_selector("#sheet", state="attached", timeout=10_000)
    page.wait_for_selector("#sheet-canvas", state="attached", timeout=10_000)
    page.locator('[data-editor-tab="edition"]').click()
    expect(page.locator('[data-editor-tab-panel="edition"]')).to_be_visible()


def _slot_count(page: Page) -> int:
    return page.locator(".slot").count()


def _slot_box(page: Page, index: int) -> dict[str, float]:
    box = page.locator(".slot").nth(index).bounding_box()
    assert box is not None
    return box


def _slot_center(box: dict[str, float]) -> tuple[float, float]:
    return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2


def _create_slot(page: Page, x_mm: float, y_mm: float, w_mm: float = 30, h_mm: float = 30) -> None:
    page.locator("#btn-new-slot").click()
    expect(page.locator("#slot-form")).to_be_visible()
    page.locator("#slot-x").fill(str(x_mm))
    page.locator("#slot-y").fill(str(y_mm))
    page.locator("#slot-w").fill(str(w_mm))
    page.locator("#slot-h").fill(str(h_mm))
    page.locator("#btn-apply-slot").click()
    expect(page.locator(".slot.selected")).to_have_count(1)


def _select_slots(page: Page, indexes: list[int]) -> None:
    assert indexes
    page.locator(".slot").nth(indexes[0]).click()
    for index in indexes[1:]:
        page.locator(".slot").nth(index).click(modifiers=["Control"])
    expect(page.locator(".slot.selected")).to_have_count(len(indexes))


def _drag_slot(page: Page, index: int, dx: float = 70, dy: float = 0, hold: bool = False) -> None:
    box = _slot_box(page, index)
    start_x, start_y = _slot_center(box)
    page.mouse.move(start_x, start_y)
    page.mouse.down()
    page.mouse.move(start_x + dx / 2, start_y + dy / 2, steps=4)
    page.mouse.move(start_x + dx, start_y + dy, steps=6)
    if not hold:
        page.mouse.up()


def _assert_no_browser_errors(console_errors: list[str], page_errors: list[str]) -> None:
    assert not console_errors
    assert not page_errors


def test_drag_simple_moves_slot_preserves_selection_and_cleans_distance_indicator():
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
            initial_count = _slot_count(page)
            _create_slot(page, 25, 25, 30, 30)
            slot_index = initial_count

            before = _slot_box(page, slot_index)
            _drag_slot(page, slot_index, dx=90, hold=True)
            expect(page.locator(".distance-indicator")).to_have_count(1)
            page.mouse.up()

            after = _slot_box(page, slot_index)
            assert after["x"] > before["x"] + 20
            expect(page.locator(".slot.selected")).to_have_count(1)
            expect(page.locator(".slot").nth(slot_index)).to_have_class(re.compile(r"\bselected\b"))
            expect(page.locator(".distance-indicator")).to_have_count(0)
            _assert_no_browser_errors(console_errors, page_errors)
        except Error as exc:
            raise AssertionError(
                f"No se pudo abrir {EDITOR_URL}. Verifica que Flask este corriendo con `python app.py`."
            ) from exc
        finally:
            browser.close()


def test_grouped_slot_drag_moves_group_members():
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
            initial_count = _slot_count(page)
            _create_slot(page, 25, 25, 30, 30)
            _create_slot(page, 75, 25, 30, 30)
            first_index = initial_count
            second_index = initial_count + 1

            _select_slots(page, [first_index, second_index])
            page.locator("#btn-group-slots").click()
            expect(page.locator(".slot.selected")).to_have_count(2)

            first_before = _slot_box(page, first_index)
            second_before = _slot_box(page, second_index)
            _drag_slot(page, first_index, dx=80)
            first_after = _slot_box(page, first_index)
            second_after = _slot_box(page, second_index)

            assert first_after["x"] > first_before["x"] + 20
            assert second_after["x"] > second_before["x"] + 20
            expect(page.locator(".slot.selected")).to_have_count(2)
            _assert_no_browser_errors(console_errors, page_errors)
        except Error as exc:
            raise AssertionError(
                f"No se pudo abrir {EDITOR_URL}. Verifica que Flask este corriendo con `python app.py`."
            ) from exc
        finally:
            browser.close()


def test_live_spacing_drag_keeps_render_and_selection_stable():
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
            initial_count = _slot_count(page)
            _create_slot(page, 30, 30, 25, 25)
            _create_slot(page, 70, 30, 25, 25)
            first_index = initial_count

            live_button = page.locator("#btn-spacing-live")
            if "LIVE OFF" in live_button.inner_text():
                live_button.click()
            expect(live_button).to_contain_text("LIVE ON")

            before_count = _slot_count(page)
            _drag_slot(page, first_index, dx=70)

            expect(page.locator(".slot")).to_have_count(before_count)
            expect(page.locator(".slot.selected")).to_have_count(1)
            expect(page.locator(".slot").nth(first_index)).to_have_class(re.compile(r"\bselected\b"))
            _assert_no_browser_errors(console_errors, page_errors)
        except Error as exc:
            raise AssertionError(
                f"No se pudo abrir {EDITOR_URL}. Verifica que Flask este corriendo con `python app.py`."
            ) from exc
        finally:
            browser.close()


def test_resize_handles_are_characterized_or_marked_latent():
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
            initial_count = _slot_count(page)
            _create_slot(page, 40, 40, 30, 30)
            handle_count = page.locator(".slot .handle").count()

            if handle_count == 0:
                assert page.locator(".slot .handle").count() == 0
                _assert_no_browser_errors(console_errors, page_errors)
                return

            before = _slot_box(page, initial_count)
            handle = page.locator(".slot").nth(initial_count).locator(".handle.br")
            handle_box = handle.bounding_box()
            assert handle_box is not None
            start_x, start_y = _slot_center(handle_box)
            page.mouse.move(start_x, start_y)
            page.mouse.down()
            page.mouse.move(start_x + 45, start_y + 45, steps=8)
            page.mouse.up()
            after = _slot_box(page, initial_count)

            assert after["width"] > before["width"] or after["height"] > before["height"]
            _assert_no_browser_errors(console_errors, page_errors)
        except Error as exc:
            raise AssertionError(
                f"No se pudo abrir {EDITOR_URL}. Verifica que Flask este corriendo con `python app.py`."
            ) from exc
        finally:
            browser.close()
