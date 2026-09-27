"""Native Repeat end-to-end: four PDF pages, history, persistence and physical output."""
import fitz
from test_editor_offset_v2 import sync_playwright, expect, _open_workflow_stage
from test_editor_offset_v2_output_integration import output_server

COLORS=[(1,0,0),(0,1,0),(0,0,1),(1,0,1)]


def test_two_mm_crop_marks_match_canvas_preview_and_pdf(output_server,tmp_path):
    from test_editor_offset_v2 import _open_job_with_repeat, _write_test_pdf
    source=tmp_path/'marks.pdf';_write_test_pdf(source)
    with sync_playwright() as pw:
        browser=pw.chromium.launch()
        page=browser.new_page(viewport={'width':1440,'height':900})
        try:
            _open_job_with_repeat(page,output_server,source)
            page.evaluate('() => window.__EDITOR_OFFSET_V2__.saver.manualSave()')
            page.wait_for_function('() => window.__EDITOR_OFFSET_V2__.store.saveState.status === "clean"')
            api=output_server+'/api/editor-offset-v2/jobs/'+page.url.rsplit('/',1)[1]
            current=page.request.get(api).json();layout=current['layout']
            assert len(layout['slots'])==2
            for profile in layout['export']['marks_profiles']: profile['crop_marks']=True
            for work in layout['works']: work['bleed_strategy']='mirror_if_missing'
            for index,slot in enumerate(layout['slots']):
                slot['geometry'].update(bleed_mm=2,rotation_deg=0)
                slot['geometry']['position_mm'].update(x_mm=100+index*150,y_mm=100)
                slot['content_transform']['clip_to']='bleed_box'
            saved=page.request.put(api+'/layout',data={'base_revision':current['revision'],'layout':layout})
            assert saved.status==200,saved.text()
            page.reload()
            expect(page.locator('.ev2-svg-crop-mark')).to_have_count(8*len(layout['slots']))
            for index,slot in enumerate(layout['slots']):
                group=page.locator('.ev2-svg-slot').nth(index)
                lines=group.locator('.ev2-svg-crop-mark').evaluate_all('els => els.map(e => Object.fromEntries(["x1","x2","y1","y2","stroke-width"].map(k => [k,Number(e.getAttribute(k))])) )')
                half_x=slot['geometry']['trim_size_mm']['width']/2
                half_y=slot['geometry']['trim_size_mm']['height']/2
                for line in lines:
                    assert abs(line['stroke-width']-.2)<1e-9
                    assert max(abs(line['x1']),abs(line['x2']))+.1<=half_x+2+1e-9
                    assert max(abs(line['y1']),abs(line['y2']))+.1<=half_y+2+1e-9
            pdf=page.request.post(api+'/pdf-final',data={'dpi':144,'allow_mirror_bleed':True})
            assert pdf.status==200,pdf.text()
            with fitz.open(stream=pdf.body(),filetype='pdf') as doc:
                ticks=[d for d in doc[0].get_drawings() if len(d['items'])==1 and d['items'][0][0]=='l']
                assert len(ticks)==8*len(layout['slots'])
            png=page.request.post(api+'/preview',data={'dpi':144,'allow_mirror_bleed':True})
            assert png.status==200,png.text()
            (tmp_path/'two-mm-native-preview.png').write_bytes(png.body())
            (tmp_path/'two-mm-native.pdf').write_bytes(pdf.body())
            page.screenshot(path=str(tmp_path/'two-mm-canvas.png'))
            assert page.request.get(api).json()['layout']==saved.json()['layout']
        finally:
            browser.close()


def write_four_pdf(path):
    with fitz.open() as doc:
        for index,color in enumerate(COLORS,1):
            page=doc.new_page(width=720,height=405)  # 254 x 142.875 mm
            page.draw_rect(page.rect,color=None,fill=color)
            page.set_trimbox(page.rect)
            page.insert_text((24,36),f'REPEAT V2 - PAGE {index}',fontsize=20)
        doc.save(path)


def test_four_pages_native_repeat_propose_apply_history_reload_and_pdf(output_server,tmp_path):
    path=tmp_path/'repeat-four-pages.pdf';write_four_pdf(path)
    with sync_playwright() as pw:
        browser=pw.chromium.launch()
        page=browser.new_page(viewport={'width':1440,'height':900})
        errors=[];page.on('pageerror',lambda err:errors.append(str(err)))
        try:
            page.goto(output_server+'/editor_offset_visual_v2')
            page.locator('#ev2-new-job').click();page.wait_for_url('**/editor_offset_visual_v2/ev2_*')
            page.locator('#ev2-asset-file').set_input_files(str(path))
            with page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/assets')):
                page.locator('#ev2-asset-upload-button').click()
            expect(page.locator('.ev2-page-plan-row')).to_have_count(4)
            page.locator('#ev2-preparation-select-all').click()
            page.locator('#ev2-create-page-works').click()
            expect(page.locator('.ev2-prepared-work')).to_have_count(4)
            _open_workflow_stage(page,'impose')
            page.locator('#ev2-repeat-gap-x').fill('3');page.locator('#ev2-repeat-gap-y').fill('3')
            with page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/imposition/repeat')) as response:
                page.locator('#ev2-repeat-calculate').click()
            result=response.value.json()['result']
            assert result['success'] and result['placed']==4 and result['unplaced']==0
            assert result['engine_version']=='v2-repeat-1.1.0'
            assert {s['source']['page'] for s in result['slots']}=={1,2,3,4}
            api=output_server+'/api/editor-offset-v2/jobs/'+page.url.rsplit('/',1)[1]
            assert page.request.get(api).json()['layout']['slots']==[]
            expect(page.locator('.ev2-svg-repeat-proposal')).to_have_count(4)
            expect(page.locator('.ev2-svg-slot')).to_have_count(0)
            expect(page.locator('.ev2-repeat-work-detail')).to_have_count(4)
            assert page.locator('.ev2-svg-repeat-proposal [data-slot-id]').count()==0
            with page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/imposition/repeat')) as alternative:
                page.locator('#ev2-repeat-alternative').click()
            assert alternative.value.request.post_data_json['distribution']=='rows'
            expect(page.locator('#ev2-repeat-placed')).to_have_text('4')
            assert page.request.get(api).json()['layout']['slots']==[]
            page.locator('#ev2-repeat-distribution').select_option('columns')
            expect(page.locator('.ev2-svg-repeat-proposal')).to_have_count(0)
            expect(page.locator('#ev2-repeat-apply')).to_be_disabled()
            with page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/imposition/repeat')):
                page.locator('#ev2-repeat-calculate').click()
            expect(page.locator('.ev2-svg-repeat-proposal')).to_have_count(4)
            expect(page.locator('#ev2-repeat-issues')).to_contain_text('sin sangrado')
            expect(page.locator('.ev2-svg-crop-mark')).to_have_count(0)
            pending_pdf=page.request.post(api+'/pdf-final',data={'dpi':72})
            assert pending_pdf.status==422  # The four temporary pieces cannot make an empty job exportable.
            assert page.request.get(api).json()['layout']['slots']==[]
            page.screenshot(path=str(tmp_path/'native-repeat-proposal.png'))
            expect(page.locator('#ev2-repeat-placed')).to_have_text('4')
            page.locator('#ev2-repeat-apply').click()
            expect(page.locator('.ev2-svg-slot')).to_have_count(4)
            page.locator('#ev2-undo').click();expect(page.locator('.ev2-svg-slot')).to_have_count(0)
            page.locator('#ev2-redo').click();expect(page.locator('.ev2-svg-slot')).to_have_count(4)
            page.evaluate('() => window.__EDITOR_OFFSET_V2__.saver.manualSave()')
            page.wait_for_function('() => window.__EDITOR_OFFSET_V2__.store.saveState.status === "clean"')
            stored=page.request.get(api).json()['layout']
            assert stored['imposition']['engine_version']==result['engine_version']
            page.reload();expect(page.locator('.ev2-svg-slot')).to_have_count(4)
            assert page.evaluate('() => window.__EDITOR_OFFSET_V2__.store.layout.slots')==stored['slots']
            pdf=page.request.post(api+'/pdf-final',data={'dpi':72})
            # Zero bleed now omits crop ticks with a warning, without rewriting profiles.
            assert page.request.get(api).json()['layout']['export']['marks_profiles'][0]['crop_marks'] is True
            assert pdf.status==200,pdf.text()
            (tmp_path/'native-repeat-four.pdf').write_bytes(pdf.body())
            with fitz.open(stream=pdf.body(),filetype='pdf') as document:
                assert len(document)==1
                out=document[0]
                assert abs(out.rect.width-700*72/25.4)<0.01
                assert abs(out.rect.height-500*72/25.4)<0.01
                assert not out.get_images()
                assert all(f'PAGE {n}' in out.get_text() for n in range(1,5))
                pix=out.get_pixmap()
                for slot in stored['slots']:
                    position=slot['geometry']['position_mm']
                    x=round(position['x_mm']*72/25.4)
                    y=round((500-position['y_mm'])*72/25.4)
                    expected=tuple(round(c*255) for c in COLORS[slot['source']['page']-1])
                    assert all(abs(a-b)<=2 for a,b in zip(pix.pixel(x,y),expected))
            png=page.request.post(api+'/preview',data={'dpi':72})
            assert png.status==200,png.text()
            (tmp_path/'native-repeat-four.png').write_bytes(png.body())
            _open_workflow_stage(page,'adjust')
            page.screenshot(path=str(tmp_path/'native-repeat-four-canvas.png'))
            assert not errors
        finally:
            browser.close()


def test_repeat_review_add_replace_discard_invalidation_and_pdf_isolation(output_server,tmp_path):
    from test_editor_offset_v2 import _open_job_with_repeat, _write_test_pdf
    source=tmp_path/'review.pdf';_write_test_pdf(source)
    with sync_playwright() as pw:
        browser=pw.chromium.launch()
        page=browser.new_page(viewport={'width':1440,'height':900})
        errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
        try:
            _open_job_with_repeat(page,output_server,source,2)
            page.wait_for_function('() => window.__EDITOR_OFFSET_V2__.store.saveState.status === "clean"')
            api=output_server+'/api/editor-offset-v2/jobs/'+page.url.rsplit('/',1)[1]
            # Explicit QA profile: output checks isolate proposals from crop-mark spacing.
            current=page.request.get(api).json();layout=current['layout']
            layout['export']['marks_profiles'][0]['crop_marks']=False
            saved=page.request.put(api+'/layout',data={'base_revision':current['revision'],'layout':layout})
            assert saved.status==200,saved.text()
            page.reload();_open_workflow_stage(page,'impose')
            before=page.request.get(api).json()['layout']
            def calculate():
                page.locator('#ev2-repeat-calculate').click()
                expect(page.locator('#ev2-repeat-apply')).to_be_enabled()
                expect(page.locator('.ev2-svg-repeat-proposal')).to_have_count(2)
            # A hidden retained piece must still be visible as a non-editable
            # obstacle during review, without changing the saved visibility choice.
            page.evaluate('() => { const s=window.__EDITOR_OFFSET_V2__.store; s.hideSlots([s.layout.slots[0].id]); }')
            expect(page.locator('.ev2-svg-slot')).to_have_count(1)
            calculate()
            expect(page.locator('.ev2-svg-repeat-obstacle')).to_have_count(1)
            assert page.locator('.ev2-svg-repeat-obstacle [data-slot-id]').count()==0
            page.locator('#ev2-repeat-discard').click()
            expect(page.locator('.ev2-svg-repeat-obstacle')).to_have_count(0)
            expect(page.locator('.ev2-svg-slot')).to_have_count(1)
            page.evaluate('() => window.__EDITOR_OFFSET_V2__.store.setHiddenSlotIds([])')
            calculate()
            expect(page.locator('.ev2-svg-slot')).to_have_count(2)
            expect(page.locator('#ev2-repeat-review-note')).to_contain_text('Total en la cara: 4')
            assert page.request.get(api).json()['layout']==before
            pdf=page.request.post(api+'/pdf-final',data={'dpi':72})
            assert pdf.status==200,pdf.text()
            with fitz.open(stream=pdf.body(),filetype='pdf') as document:
                assert document[0].get_text().count('EDITOR OFFSET V2')==2
            # Input invalidates immediately, without blur or persistence.
            page.locator('#ev2-repeat-gap-x').fill('4')
            expect(page.locator('.ev2-svg-repeat-proposal')).to_have_count(0)
            expect(page.locator('#ev2-repeat-apply')).to_be_disabled()
            calculate()
            page.locator('#ev2-repeat-discard').click()
            expect(page.locator('.ev2-svg-repeat-proposal')).to_have_count(0)
            assert page.request.get(api).json()['layout']==before
            page.locator('[name="ev2-repeat-mode"][value="replace_work_face"]').check()
            calculate()
            expect(page.locator('.ev2-svg-slot.is-repeat-replaced')).to_have_count(2)
            expect(page.locator('#ev2-repeat-review-note')).to_contain_text('se retiran 2')
            expect(page.locator('#ev2-repeat-review-note')).to_contain_text('Total en la cara: 2')
            page.screenshot(path=str(tmp_path/'repeat-replace-proposal.png'))
            # At narrow sizes the detail and actions remain reachable without document overflow.
            page.set_viewport_size({'width':390,'height':844})
            page.locator('#ev2-stage-tab-impose').click()
            assert page.evaluate('() => document.documentElement.scrollWidth <= innerWidth+1')
            page.set_viewport_size({'width':1440,'height':900})
            page.locator('#ev2-repeat-apply').click()
            expect(page.locator('.ev2-svg-repeat-proposal')).to_have_count(0)
            expect(page.locator('.ev2-svg-slot')).to_have_count(2)
            after=page.evaluate('() => structuredClone(window.__EDITOR_OFFSET_V2__.store.layout.slots)')
            assert after!=before['slots']
            page.locator('#ev2-undo').click()
            assert page.evaluate('() => window.__EDITOR_OFFSET_V2__.store.layout.slots')==before['slots']
            page.locator('#ev2-redo').click()
            assert page.evaluate('() => window.__EDITOR_OFFSET_V2__.store.layout.slots')==after
            page.wait_for_function('() => window.__EDITOR_OFFSET_V2__.store.saveState.status === "clean"')
            page.reload();expect(page.locator('.ev2-svg-slot')).to_have_count(2)
            assert page.request.get(api).json()['layout']['slots']==after
            assert not errors
        finally:
            browser.close()
