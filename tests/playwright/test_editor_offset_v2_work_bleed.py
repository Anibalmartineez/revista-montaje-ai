"""Saved work bleed policy through preparation, Repeat, canvas and output."""
import fitz
import pytest
from test_editor_offset_v2 import sync_playwright, expect, _open_workflow_stage
from test_editor_offset_v2_output_integration import output_server
from test_editor_offset_v2_preparation import new_job, upload, layout, save


@pytest.mark.parametrize('pages',[1,2])
def test_work_bleed_prepare_history_reload_and_output(output_server,tmp_path,pages):
    source=tmp_path/'bleed-pages.pdf'
    with fitz.open() as doc:
        for n in range(pages):
            p=doc.new_page(width=40*72/25.4,height=20*72/25.4)
            p.draw_rect(p.rect,color=None,fill=(.8,.3,.1) if n==0 else (.1,.3,.8))
            p.insert_text((5,25),f'BLEED PAGE {n+1}',fontsize=8,color=(1,1,1))
        doc.save(source)
    original=source.read_bytes()
    with sync_playwright() as pw:
        browser=pw.chromium.launch(); page=browser.new_page(viewport={'width':1440,'height':1000})
        errors=[]; page.on('pageerror',lambda e:errors.append(str(e)))
        try:
            new_job(page,output_server); upload(page,source)
            expect(page.locator('#ev2-asset-box')).not_to_be_visible()
            expect(page.locator('#ev2-box-dimensions')).to_contain_text('40 × 20')
            page.locator('#ev2-work-quantity').fill('2')
            page.locator('#ev2-work-bleed').fill('3')
            expect(page.locator('#ev2-preparation-coverage')).to_contain_text('Falta cobertura')
            page.locator('#ev2-work-bleed-strategy').select_option('mirror_if_missing')
            expect(page.locator('#ev2-preparation-coverage')).to_contain_text('se generará espejo autorizado')
            if pages==2:
                page.locator('[data-page-plan-selected][data-page="2"]').check()
                page.get_by_role('button',name='Configurar página 2',exact=True).click()
                page.locator('#ev2-work-bleed').fill('3')
            page.locator('#ev2-create-page-works').click()
            expect(page.locator('.ev2-prepared-work')).to_have_count(pages)
            expected=layout(page)['works']
            assert [w['requested_forms'] for w in expected]==([2] if pages==1 else [2,1])
            assert [w['bleed_strategy'] for w in expected]==(['mirror_if_missing'] if pages==1 else ['mirror_if_missing','source_only'])
            page.locator('#ev2-undo').click(); expect(page.locator('.ev2-prepared-work')).to_have_count(0)
            page.locator('#ev2-redo').click(); save(page); page.reload()
            _open_workflow_stage(page,'prepare'); assert layout(page)['works']==expected
            _open_workflow_stage(page,'impose')
            page.locator('#ev2-repeat-calculate').click()
            expect(page.locator('#ev2-repeat-apply')).to_be_enabled(timeout=15000)
            page.locator('#ev2-repeat-apply').click()
            page.wait_for_function('(n)=>window.__EDITOR_OFFSET_V2__.store.layout.slots.length===n',arg=pages+1)
            slots=layout(page)['slots']; save(page)
            _open_workflow_stage(page,'output'); page.locator('#ev2-output-recheck').click()
            if pages==2:
                expect(page.locator('#ev2-output-pdf')).to_be_disabled()
                page.locator('#ev2-output-mirror').check()
                page.locator('#ev2-output-recheck').click()
                expect(page.locator('#ev2-output-findings')).to_contain_text('Falta sangrado del archivo')
                expect(page.locator('#ev2-output-pdf')).to_be_disabled()
                _open_workflow_stage(page,'prepare'); page.locator('[data-edit-work]').nth(1).click()
                page.locator('#ev2-work-bleed-strategy').select_option('mirror_if_missing')
                page.locator('#ev2-preparation-save-work').click()
                assert layout(page)['slots']==slots
                assert layout(page)['works'][1]['bleed_strategy']=='mirror_if_missing'
                page.locator('#ev2-undo').click(); assert layout(page)['works'][1]['bleed_strategy']=='source_only'
                page.locator('#ev2-redo').click(); save(page); page.reload()
            _open_workflow_stage(page,'adjust')
            expect(page.locator('.ev2-svg-artwork[data-bleed-origin="generated-mirror"]')).to_have_count(pages+1)
            _open_workflow_stage(page,'output')
            page.locator('#ev2-output-recheck').click()
            expect(page.locator('#ev2-output-findings')).to_contain_text('Sangrado generado por espejo')
            expect(page.locator('#ev2-output-pdf')).to_be_enabled()
            page.locator('#ev2-output-preview').click()
            expect(page.locator('#ev2-output-result')).to_contain_text('Preview lista',timeout=30000)
            with page.expect_download() as download: page.locator('#ev2-output-pdf').click()
            target=tmp_path/'work-bleed.pdf'; download.value.save_as(target)
            with fitz.open(target) as doc:
                assert len(doc)==1
                text=doc[0].get_text(); assert text.count('BLEED PAGE 1')==2
                if pages==2: assert text.count('BLEED PAGE 2')==1
            for width in [1440,390]:
                page.set_viewport_size({'width':width,'height':1000})
                _open_workflow_stage(page,'prepare')
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
                page.screenshot(path=str(tmp_path/f'preparation-{pages}-{width}.png'))
            assert layout(page)['slots']==slots
            assert source.read_bytes()==original
            assert not errors
        finally: browser.close()
