from playwright.sync_api import Error, sync_playwright


EDITOR_URL = "http://127.0.0.1:5000/editor_offset_visual"


def _is_serious_console_error(text: str) -> bool:
    # Chromium reports missing favicon/static incidental resources as console errors.
    # Keep the smoke test focused on JS/runtime failures in the editor itself.
    ignored_fragments = [
        "Failed to load resource: the server responded with a status of 404 (NOT FOUND)",
    ]
    return not any(fragment in text for fragment in ignored_fragments)


def test_editor_visual_ia_loads_in_browser():
    console_errors: list[str] = []
    page_errors: list[str] = []

    with sync_playwright() as playwright:
        # headless=False is intentional for this first smoke test so the browser is visible.
        # Later this can be switched to headless=True for CI or unattended runs.
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
            page.goto(EDITOR_URL, wait_until="domcontentloaded", timeout=15_000)
            page.wait_for_selector("#sheet", state="attached", timeout=10_000)
            page.wait_for_selector("#sheet-canvas", state="attached", timeout=10_000)

            assert page.locator("#sheet").count() == 1
            assert page.locator("#sheet-canvas").count() == 1

            tabs = page.locator(".editor-tab")
            panels = page.locator(".editor-tab-panel")
            assert tabs.count() >= 8
            assert panels.count() >= 8

            expected_tabs = [
                "Pliego",
                "Trabajos",
                "Diseños",
                "Imposición",
                "Edición",
                "IA",
                "Cuadernillos",
                "CTP",
                "Salida",
            ]
            for label in expected_tabs:
                assert page.locator(".editor-tab", has_text=label).count() == 1

            assert not console_errors
            assert not page_errors
        except Error as exc:
            raise AssertionError(
                f"No se pudo abrir {EDITOR_URL}. Verifica que Flask este corriendo con `python app.py`."
            ) from exc
        finally:
            browser.close()
