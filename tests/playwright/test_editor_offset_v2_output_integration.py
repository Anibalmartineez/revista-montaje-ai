"""Real browser regressions for the approved output closure."""
import fitz
from test_editor_offset_v2 import v2_server, sync_playwright, expect, _open_workflow_stage


def test_page_planner_switch_quantities_and_inspector_stage(v2_server, tmp_path):
    paths=[]
    for count in (1,3):
        path=tmp_path/f'pages-{count}.pdf'
        with fitz.open() as doc:
            for i in range(count):
                p=doc.new_page(width=200,height=100); p.insert_text((20,40),f'PAGE {i+1}')
            doc.save(path)
        paths.append(path)
    with sync_playwright() as pw:
        browser=pw.chromium.launch()
        page=browser.new_page(viewport={'width':1440,'height':900})
        errors=[]; page.on('pageerror',lambda err:errors.append(str(err)))
        try:
            page.goto(v2_server+'/editor_offset_visual_v2')
            page.locator('#ev2-new-job').click(); page.wait_for_url('**/editor_offset_visual_v2/ev2_*')
            for count,path in zip((1,3),paths):
                page.locator('#ev2-asset-file').set_input_files(str(path))
                with page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/assets')):
                    page.locator('#ev2-asset-upload-button').click()
                expect(page.locator('.ev2-page-plan-row')).to_have_count(count)
            quantity=page.get_by_label('Cantidad de formas para página 2',exact=True)
            quantity.fill('7')
            page.locator('[data-page-plan-selected][data-page="2"]').check()
            page.locator('#ev2-asset-select').select_option(label='pages-1.pdf')
            expect(page.locator('.ev2-page-plan-row')).to_have_count(1)
            page.locator('#ev2-asset-select').select_option(label='pages-3.pdf')
            expect(page.locator('.ev2-page-plan-row')).to_have_count(3)
            expect(quantity).to_have_value('7')
            page.get_by_label('Cantidad de formas para página 1',exact=True).fill('2')
            page.locator('#ev2-create-page-works').click()
            page.wait_for_function('() => window.__EDITOR_OFFSET_V2__.store.layout.works.length === 2')
            quantities=page.evaluate('() => window.__EDITOR_OFFSET_V2__.store.layout.works.map(w=>w.requested_forms)')
            assert quantities==[2,7]
            page.locator('#ev2-undo').click()
            page.wait_for_function('() => window.__EDITOR_OFFSET_V2__.store.layout.works.length === 0')
            page.locator('#ev2-redo').click()
            page.wait_for_function('() => window.__EDITOR_OFFSET_V2__.store.layout.works.length === 2')
            _open_workflow_stage(page,'validate')
            page.locator('#ev2-save').click()
            expect(page.locator('#ev2-save')).to_be_disabled()
            expect(page.locator('#ev2-content-transform-panel')).to_be_hidden()
            page.reload()
            page.wait_for_function('() => window.__EDITOR_OFFSET_V2__?.store.layout.works.length === 2')
            assert not errors
        finally:
            browser.close()
