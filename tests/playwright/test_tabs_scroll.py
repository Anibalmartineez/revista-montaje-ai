from playwright.sync_api import Error, expect, sync_playwright


EDITOR_URL = "http://127.0.0.1:5000/editor_offset_visual"


def _is_serious_console_error(text: str) -> bool:
    # Chromium reports missing favicon/static incidental resources as console errors.
    # Keep the test focused on JS/runtime failures in the editor itself.
    ignored_fragments = [
        "Failed to load resource: the server responded with a status of 404 (NOT FOUND)",
    ]
    return not any(fragment in text for fragment in ignored_fragments)


def test_editor_tabs_switch_and_side_panel_scrolls():
    console_errors: list[str] = []
    page_errors: list[str] = []

    with sync_playwright() as playwright:
        # headless=False is intentional while this visual QA base is being built.
        # Later this can be switched to headless=True for CI or unattended runs.
        browser = playwright.chromium.launch(headless=False)
        page = browser.new_page(viewport={"width": 1440, "height": 560})

        page.on(
            "console",
            lambda msg: console_errors.append(msg.text)
            if msg.type == "error" and _is_serious_console_error(msg.text)
            else None,
        )
        page.on("pageerror", lambda exc: page_errors.append(str(exc)))

        try:
            page.goto(EDITOR_URL, wait_until="domcontentloaded", timeout=15_000)
            page.wait_for_selector("#sheet", state="attached", timeout=10_000)
            page.wait_for_selector(".editor-tab", state="visible", timeout=10_000)

            tabs = [
                "plate",
                "works",
                "designs",
                "imposition",
                "edition",
                "ai",
                "booklets",
                "ctp",
                "output",
            ]

            for tab_name in tabs:
                tab = page.locator(f'[data-editor-tab="{tab_name}"]')
                expect(tab).to_be_visible()
                tab.click()
                expect(tab).to_have_attribute("aria-selected", "true")
                expect(page.locator(f'[data-editor-tab-panel="{tab_name}"]')).to_be_visible()

            page.locator('[data-editor-tab="booklets"]').click()
            scroll_info = page.locator(".editor-tab-panels").evaluate(
                """(el) => {
                    el.scrollTop = 0;
                    const before = el.scrollTop;
                    el.scrollTop = el.scrollHeight;
                    return {
                        before,
                        after: el.scrollTop,
                        clientHeight: el.clientHeight,
                        scrollHeight: el.scrollHeight
                    };
                }"""
            )

            assert scroll_info["scrollHeight"] > scroll_info["clientHeight"]
            assert scroll_info["after"] > scroll_info["before"]
            assert page.locator("#cuadernillo-resultado").count() == 1

            assert not console_errors
            assert not page_errors
        except Error as exc:
            raise AssertionError(
                f"No se pudo abrir {EDITOR_URL}. Verifica que Flask este corriendo con `python app.py`."
            ) from exc
        finally:
            browser.close()
