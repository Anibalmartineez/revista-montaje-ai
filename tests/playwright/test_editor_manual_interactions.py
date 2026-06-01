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


def _selected_slot_count(page: Page) -> int:
    return page.locator(".slot.selected").count()


def _slot_box(page: Page, index: int) -> dict[str, float]:
    box = page.locator(".slot").nth(index).bounding_box()
    assert box is not None
    return box


def _selected_slot_boxes(page: Page) -> list[dict[str, float]]:
    selected = page.locator(".slot.selected")
    boxes = []
    for index in range(selected.count()):
        box = selected.nth(index).bounding_box()
        assert box is not None
        boxes.append(box)
    return boxes


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


def _ensure_advanced_tools_visible(page: Page) -> None:
    panel = page.locator("#manual-advanced-tools")
    if not panel.is_visible():
        page.locator("#btn-manual-advanced-toggle").click()
    expect(panel).to_be_visible()


def _assert_no_browser_errors(console_errors: list[str], page_errors: list[str]) -> None:
    assert not console_errors
    assert not page_errors


def test_manual_selection_duplicate_delete_group_and_ungroup():
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

            _create_slot(page, 20, 20)
            _create_slot(page, 65, 20)
            first_new_index = initial_count
            second_new_index = initial_count + 1

            page.locator(".slot").nth(first_new_index).click()
            expect(page.locator(".slot.selected")).to_have_count(1)

            page.locator(".slot").nth(second_new_index).click(modifiers=["Control"])
            expect(page.locator(".slot.selected")).to_have_count(2)

            page.locator("#btn-group-slots").click()
            expect(page.locator(".slot.selected")).to_have_count(2)

            page.locator("#btn-ungroup-slots").click()
            expect(page.locator(".slot.selected")).to_have_count(2)

            page.locator("#btn-dup-slot").click()
            expect(page.locator(".slot")).to_have_count(initial_count + 4)
            expect(page.locator(".slot.selected")).to_have_count(2)

            page.locator("#btn-del-slot").click()
            expect(page.locator(".slot")).to_have_count(initial_count + 2)
            expect(page.locator(".slot.selected")).to_have_count(0)

            _assert_no_browser_errors(console_errors, page_errors)
        except Error as exc:
            raise AssertionError(
                f"No se pudo abrir {EDITOR_URL}. Verifica que Flask este corriendo con `python app.py`."
            ) from exc
        finally:
            browser.close()


def test_manual_select_all_nudge_align_and_distribute():
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

            _create_slot(page, 15, 20, 25, 25)
            _create_slot(page, 80, 45, 25, 25)
            _create_slot(page, 155, 30, 25, 25)

            page.locator("#sheet-canvas").click()
            expect(page.locator(".slot.selected")).to_have_count(0)

            page.keyboard.press("Control+A")
            expect(page.locator(".slot.selected")).to_have_count(initial_count + 3)

            _select_slots(page, [initial_count, initial_count + 1, initial_count + 2])
            before_nudge = _slot_box(page, initial_count)
            page.locator("#nudge-step").fill("5")
            page.locator("#btn-nudge-right").click()
            after_nudge = _slot_box(page, initial_count)
            assert after_nudge["x"] > before_nudge["x"]

            _ensure_advanced_tools_visible(page)
            _select_slots(page, [initial_count, initial_count + 1, initial_count + 2])
            page.locator("#btn-align-left").click()
            aligned_boxes = _selected_slot_boxes(page)
            assert len(aligned_boxes) == 3
            aligned_x = [round(box["x"], 1) for box in aligned_boxes]
            assert max(aligned_x) - min(aligned_x) <= 1.0

            page.locator("#btn-distribute-y").click()
            expect(page.locator(".slot.selected")).to_have_count(3)

            _assert_no_browser_errors(console_errors, page_errors)
        except Error as exc:
            raise AssertionError(
                f"No se pudo abrir {EDITOR_URL}. Verifica que Flask este corriendo con `python app.py`."
            ) from exc
        finally:
            browser.close()
