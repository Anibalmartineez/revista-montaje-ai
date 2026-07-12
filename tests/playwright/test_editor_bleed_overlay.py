import json

import pytest
from playwright.sync_api import Error, Page, sync_playwright


EDITOR_URL = "http://127.0.0.1:5000/editor_offset_visual"


def _open_editor(page: Page) -> None:
    try:
        page.goto(EDITOR_URL, wait_until="domcontentloaded", timeout=15_000)
        page.wait_for_selector("#sheet", state="attached", timeout=10_000)
    except Error as exc:
        raise AssertionError(
            f"No se pudo abrir {EDITOR_URL}. Verifica que la instancia existente siga disponible."
        ) from exc


def _render_cases(page: Page, slots: list[dict], *, designs=None, bleed_default=3, zoom=1) -> dict:
    return page.evaluate(
        """
        ({ slots, designs, bleedDefault, zoom }) => {
          const renderer = window.EditorOffsetVisual.rendererCanvas;
          const host = document.createElement('div');
          host.className = 'sheet';
          document.body.appendChild(host);
          const layout = {
            sheet_mm: [300, 300],
            bleed_default_mm: bleedDefault,
            designs: designs || [],
            slots,
          };
          const before = JSON.stringify(layout);
          let clicks = 0;
          let pointerDowns = 0;

          renderer.renderSheetSurface({
            sheetEl: host,
            layout,
            activeFace: 'front',
            selectedSlot: slots[0] || null,
            selectedSlots: new Set((slots || []).map((slot) => slot.id)),
            geometryValidation: {
              errors: [],
              warnings: [],
              bySlot: {
                warning: { level: 'warning', issues: [{ message: 'warning' }] },
                error: { level: 'error', issues: [{ message: 'error' }] },
              },
            },
            distanceIndicator: { active: false },
            mmToPx: (mm) => Number(mm) * 2,
            getSlotRenderBox: (slot) => ({
              x: slot.x_mm,
              y: slot.y_mm,
              w: slot.w_mm,
              h: slot.h_mm,
              rotation: slot.rotation_deg || 0,
            }),
            attachSlotHandlers: (slotEl) => {
              slotEl.addEventListener('click', () => { clicks += 1; });
              slotEl.addEventListener('pointerdown', () => { pointerDowns += 1; });
            },
            updateHandleScale: () => {},
            zoom,
            zoomLabelEl: null,
            geometryValidationSummaryEl: null,
            geometryValidationListEl: null,
          });

          const rendered = [...host.querySelectorAll('.slot')].map((slotEl) => {
            const overlay = slotEl.querySelector('.slot-bleed-overlay');
            const trimRect = slotEl.getBoundingClientRect();
            const overlayRect = overlay?.getBoundingClientRect();
            slotEl.dispatchEvent(new MouseEvent('click', { bubbles: true }));
            slotEl.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true }));
            return {
              id: slotEl.dataset.slotId,
              classes: [...slotEl.classList],
              rotation: slotEl.dataset.rotation || '0',
              transform: slotEl.style.getPropertyValue('--slot-rotation-deg'),
              overlay: overlay ? {
                bleedMm: overlay.dataset.bleedMm,
                outerWidthMm: overlay.dataset.outerWidthMm,
                outerHeightMm: overlay.dataset.outerHeightMm,
                left: overlay.style.left,
                top: overlay.style.top,
                width: overlay.style.width,
                height: overlay.style.height,
                pointerEvents: getComputedStyle(overlay).pointerEvents,
                parentSlotId: overlay.parentElement.dataset.slotId,
                extensions: {
                  left: trimRect.left - overlayRect.left,
                  right: overlayRect.right - trimRect.right,
                  top: trimRect.top - overlayRect.top,
                  bottom: overlayRect.bottom - trimRect.bottom,
                },
                trimRect: { width: trimRect.width, height: trimRect.height },
                overlayRect: { width: overlayRect.width, height: overlayRect.height },
              } : null,
            };
          });
          const after = JSON.stringify(layout);
          host.remove();
          return { before, after, rendered, clicks, pointerDowns };
        }
        """,
        {
            "slots": slots,
            "designs": designs or [],
            "bleedDefault": bleed_default,
            "zoom": zoom,
        },
    )


def _slot(slot_id: str, *, bleed, final_box=False, rotation=0, locked=False) -> dict:
    return {
        "id": slot_id,
        "x_mm": 10,
        "y_mm": 20,
        "w_mm": 50,
        "h_mm": 30,
        "bleed_mm": bleed,
        "slot_box_final": final_box,
        "rotation_deg": rotation,
        "locked": locked,
        "face": "front",
        "design_ref": "file0",
    }


def test_canvas_bleed_overlay_cases_and_render_purity():
    slots = [
        _slot("bleed-1", bleed=1),
        _slot("bleed-3", bleed=3),
        _slot("bleed-0", bleed=0),
        {**_slot("legacy", bleed=1, final_box=True), "w_mm": 52, "h_mm": 32},
    ]

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        try:
            _open_editor(page)
            result = _render_cases(page, slots)
        finally:
            browser.close()

    assert json.loads(result["before"]) == json.loads(result["after"])
    by_id = {item["id"]: item for item in result["rendered"]}

    bleed_1 = by_id["bleed-1"]["overlay"]
    assert bleed_1["bleedMm"] == "1"
    assert bleed_1["outerWidthMm"] == "52"
    assert bleed_1["outerHeightMm"] == "32"
    assert bleed_1["left"] == "-2px"
    assert bleed_1["top"] == "-2px"
    assert bleed_1["width"] == "104px"
    assert bleed_1["height"] == "64px"
    assert bleed_1["pointerEvents"] == "none"
    assert bleed_1["parentSlotId"] == "bleed-1"

    bleed_3 = by_id["bleed-3"]["overlay"]
    assert bleed_3["outerWidthMm"] == "56"
    assert bleed_3["outerHeightMm"] == "36"
    assert bleed_3["left"] == "-6px"
    assert bleed_3["width"] == "112px"
    assert by_id["bleed-0"]["overlay"] is None
    assert by_id["legacy"]["overlay"] is None
    assert result["clicks"] == len(slots)
    assert result["pointerDowns"] == len(slots)


def test_canvas_bleed_overlay_fallback_rotation_and_slot_states():
    rotations = [0, 90, 180, 270]
    slots = [
        {
            **_slot("warning" if rotation == 0 else f"rot-{rotation}", bleed=None, rotation=rotation),
            "locked": rotation == 90,
        }
        for rotation in rotations
    ]
    slots.append({**_slot("error", bleed=-1), "bleed_mm": "invalid"})
    designs = [{"ref": "file0", "bleed_mm": 2}]

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        try:
            _open_editor(page)
            result = _render_cases(page, slots, designs=designs, bleed_default=3)
            rebuilt = _render_cases(
                page,
                json.loads(json.dumps(slots)),
                designs=json.loads(json.dumps(designs)),
                bleed_default=3,
            )
        finally:
            browser.close()

    assert result["rendered"] == rebuilt["rendered"]
    by_id = {item["id"]: item for item in result["rendered"]}
    for slot in slots:
        rendered = by_id[slot["id"]]
        assert rendered["overlay"]["bleedMm"] == "2"
        assert rendered["overlay"]["parentSlotId"] == slot["id"]
        assert rendered["transform"] == f'{slot["rotation_deg"]}deg'

    assert "selected" in by_id["warning"]["classes"]
    assert "geometry-warning" in by_id["warning"]["classes"]
    assert "locked" in by_id["rot-90"]["classes"]
    assert "geometry-error" in by_id["error"]["classes"]


def test_canvas_bleed_overlay_is_geometrically_symmetric():
    tolerance_px = 1

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        try:
            _open_editor(page)
            for zoom in (1, 2):
                for bleed in (1, 3):
                    for rotation in (0, 90):
                        result = _render_cases(
                            page,
                            [_slot("measured", bleed=bleed, rotation=rotation)],
                            zoom=zoom,
                        )
                        overlay = result["rendered"][0]["overlay"]
                        extensions = overlay["extensions"]
                        measured = list(extensions.values())
                        expected_px = bleed * 2 * zoom

                        assert max(measured) - min(measured) <= tolerance_px
                        for extension in measured:
                            assert extension == pytest.approx(expected_px, abs=tolerance_px)

                        assert overlay["overlayRect"]["width"] - overlay["trimRect"]["width"] == pytest.approx(
                            2 * expected_px,
                            abs=tolerance_px,
                        )
                        assert overlay["overlayRect"]["height"] - overlay["trimRect"]["height"] == pytest.approx(
                            2 * expected_px,
                            abs=tolerance_px,
                        )
        finally:
            browser.close()
