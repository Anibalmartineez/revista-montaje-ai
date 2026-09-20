"""Native Repeat end-to-end: four PDF pages, history, persistence and physical output."""
import fitz
from test_editor_offset_v2 import sync_playwright, expect, _open_workflow_stage
from test_editor_offset_v2_output_integration import output_server

COLORS=[(1,0,0),(0,1,0),(0,0,1),(1,0,1)]


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
            assert result['engine_version']=='v2-repeat-1.0.0'
            assert {s['source']['page'] for s in result['slots']}=={1,2,3,4}
            api=output_server+'/api/editor-offset-v2/jobs/'+page.url.rsplit('/',1)[1]
            assert page.request.get(api).json()['layout']['slots']==[]
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
            # Geometric fit does not reserve space for marks. Preserve the real
            # preflight block, then explicitly use a no-marks QA output profile.
            assert pdf.status==422,pdf.text()
            codes={i['code'] for i in pdf.json()['error']['issues']}
            assert codes <= {'CROP_MARK_OUTSIDE_SHEET','CROP_MARK_OVERPRINT'} and codes
            current=page.request.get(api).json()
            output_layout=current['layout']
            output_layout['export']['marks_profiles'][0]['crop_marks']=False
            updated=page.request.put(api+'/layout',data={'base_revision':current['revision'],'layout':output_layout})
            assert updated.status==200,updated.text()
            assert updated.json()['layout']['slots']==stored['slots']
            pdf=page.request.post(api+'/pdf-final',data={'dpi':72})
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
