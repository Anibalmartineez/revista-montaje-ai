from pathlib import Path
from test_editor_offset_v2 import v2_server, sync_playwright, expect, _open_workflow_stage, REPO_ROOT

PDF = REPO_ROOT / 'tests/fixtures/editor_offset_v2/multipage-rotations.pdf'


def upload(page, pdf=PDF):
    page.locator('#ev2-asset-file').set_input_files(str(pdf))
    with page.expect_response(lambda r: r.request.method == 'POST' and '/assets' in r.url):
        page.locator('#ev2-asset-upload-button').click()
    expect(page.locator('#ev2-asset-upload-status')).to_contain_text('listo')


def layout(page):
    return page.evaluate('() => window.__EDITOR_OFFSET_V2__.store.layout')


def save(page):
    page.evaluate('() => window.__EDITOR_OFFSET_V2__.saver.manualSave()')
    page.wait_for_function("() => window.__EDITOR_OFFSET_V2__.store.saveState.status === 'clean'")


def new_job(page, server):
    page.goto(f'{server}/editor_offset_visual_v2')
    page.locator('#ev2-new-job').click()
    page.wait_for_url('**/editor_offset_visual_v2/ev2_*')
    expect(page.locator('#ev2-preparation')).to_be_visible()


def test_preparation_batch_drafts_missing_box_edit_variant_history_and_reload(v2_server):
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={'width':1440,'height':1000})
            errors=[]
            page.on('pageerror',lambda error:errors.append(str(error)))
            new_job(page,v2_server)
            upload(page)
            first_asset=layout(page)['assets'][0]['id']
            page.locator('#ev2-work-name').fill('Frente especial')
            page.locator('#ev2-work-quantity').fill('4')
            page.locator('#ev2-work-bleed').fill('3')
            page.get_by_text('Opciones avanzadas del PDF',exact=True).click()
            page.locator('#ev2-asset-box').select_option('media')
            expect(page.locator('#ev2-work-quantity')).to_have_value('4')
            expect(page.locator('#ev2-work-bleed')).to_have_value('3')
            expect(page.locator('#ev2-work-name')).to_have_value('Frente especial')
            page.locator('#ev2-work-size-mode').select_option('custom')
            page.locator('#ev2-work-width').fill('55')
            page.locator('#ev2-asset-box').select_option('trim')
            expect(page.locator('#ev2-work-width')).to_have_value('55')
            page.get_by_role('button',name='Configurar página 2',exact=True).click()
            page.locator('#ev2-work-quantity').fill('2')
            page.locator('[data-page-plan-selected][data-page="2"]').check()
            upload(page)
            page.locator('#ev2-work-quantity').fill('8')
            page.locator('#ev2-asset-select').select_option(first_asset)
            expect(page.locator('#ev2-work-name')).to_have_value('Frente especial')
            expect(page.locator('#ev2-work-quantity')).to_have_value('4')
            expect(page.locator('[data-page-plan-quantity][data-page="2"]')).to_have_value('2')
            page.locator('[data-preparation-field="box"]').check()
            page.locator('#ev2-preparation-apply-common').click()
            page.locator('#ev2-create-page-works').click()
            expect(page.locator('#ev2-preparation-status')).to_contain_text('Página 2: la caja trim no existe')
            assert layout(page)['works']==[]
            page.get_by_role('button',name='Configurar página 2',exact=True).click()
            page.locator('#ev2-asset-box').select_option('crop')
            page.locator('#ev2-create-page-works').click()
            expect(page.locator('.ev2-prepared-work')).to_have_count(2)
            works=layout(page)['works']
            assert [w['requested_forms'] for w in works]==[4,2]
            assert [w['bleed_mm'] for w in works]==[3,3]
            assert [w['front_source']['pdf_box'] for w in works]==['trim','crop']
            assert works[0]['trim_size_mm']['width']==55
            assert works[1]['trim_size_mm']['height']>works[1]['trim_size_mm']['width']
            expect(page.locator('[data-page-plan-selected]:checked')).to_have_count(0)
            page.locator('#ev2-undo').click()
            expect(page.locator('.ev2-prepared-work')).to_have_count(0)
            page.locator('#ev2-redo').click()
            expect(page.locator('.ev2-prepared-work')).to_have_count(2)
            page.locator('[data-page-plan-selected][data-page="1"]').check()
            page.locator('#ev2-create-page-works').click()
            expect(page.locator('#ev2-preparation-status')).to_contain_text('ya tiene trabajos')
            assert len(layout(page)['works'])==2
            page.locator('[data-edit-work]').first.click()
            page.locator('#ev2-asset-page').select_option('3')
            page.locator('#ev2-work-name').fill('Revisado')
            page.locator('#ev2-work-quantity').fill('6')
            page.locator('#ev2-preparation-save-work').click()
            updated=layout(page)['works'][0]
            assert updated['id']==works[0]['id']
            assert updated['front_source']['page']==3
            assert updated['requested_forms']==6
            assert updated['name']=='Revisado'
            page.locator('[data-edit-work]').first.click()
            page.locator('#ev2-preparation-variant').click()
            page.locator('#ev2-create-page-works').click()
            expect(page.locator('.ev2-prepared-work')).to_have_count(4)
            # The previously selected original page remains selected, plus the explicit variant.
            all_works=layout(page)['works']
            assert len({w['id'] for w in all_works})==4
            save(page)
            page.reload()
            _open_workflow_stage(page,'prepare')
            expect(page.locator('.ev2-prepared-work')).to_have_count(4)
            assert layout(page)['works']==all_works
            expect(page.locator('[data-page-plan-selected]:checked')).to_have_count(0)
            assert not errors
        finally:
            browser.close()


def test_preparation_placed_edit_preserves_slots_invalidates_repeat_and_responsive(v2_server):
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        try:
            page=browser.new_page(viewport={'width':1440,'height':1000})
            new_job(page,v2_server); upload(page)
            page.locator('#ev2-create-page-works').click()
            page.locator('#ev2-create-real-slot').click()
            before=layout(page)['slots']
            assert len(before)==1
            _open_workflow_stage(page,'impose')
            page.locator('#ev2-repeat-calculate').click()
            expect(page.locator('#ev2-repeat-apply')).to_be_enabled(timeout=10000)
            _open_workflow_stage(page,'prepare')
            page.locator('[data-edit-work]').click()
            for selector in ['#ev2-asset-select','#ev2-asset-page','#ev2-asset-box','#ev2-work-bleed','#ev2-work-size-mode','#ev2-work-back']:
                expect(page.locator(selector)).to_be_disabled()
            page.locator('#ev2-work-quantity').fill('9')
            page.locator('#ev2-preparation-save-work').click()
            assert layout(page)['works'][0]['requested_forms']==9, page.locator('#ev2-preparation-status').inner_text()
            assert layout(page)['slots']==before
            _open_workflow_stage(page,'impose')
            expect(page.locator('#ev2-repeat-apply')).to_be_disabled()
            page.locator('#ev2-undo').click()
            assert layout(page)['works'][0]['requested_forms']==1
            assert layout(page)['slots']==before
            page.locator('#ev2-redo').click()
            save(page)
            for width in [1140,820,390]:
                page.set_viewport_size({'width':width,'height':900})
                _open_workflow_stage(page,'prepare')
                expect(page.locator('#ev2-preparation')).to_be_visible()
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
                expect(page.locator('#ev2-responsive-panel-backdrop')).to_be_hidden()
                page.locator('[data-edit-work]').click()
                expect(page.locator('#ev2-work-quantity')).to_have_value('9')
                page.locator('#ev2-preparation-cancel-edit').click()
            assert layout(page)['slots']==before
        finally:
            browser.close()
