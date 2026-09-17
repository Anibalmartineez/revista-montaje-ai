"""Real browser regressions for the approved output closure."""
import fitz
import pytest
import json
import io
import base64
import threading
from pathlib import Path
from flask import Flask
from werkzeug.serving import make_server
from editor_offset_v2.blueprint import init_editor_offset_v2
from PIL import Image, ImageChops, ImageStat
from test_editor_offset_v2 import v2_server, sync_playwright, expect, _open_workflow_stage


@pytest.fixture
def output_server(tmp_path):
    root=Path(__file__).resolve().parents[2]
    app=Flask(__name__,template_folder=str(root/'templates'),static_folder=str(root/'static'))
    app.config.update(TESTING=True,EDITOR_OFFSET_V2_ENABLED=True,EDITOR_OFFSET_V2_PREVIEW_ENABLED=True,
                      EDITOR_OFFSET_V2_PDF_FINAL_ENABLED=True,EDITOR_OFFSET_V2_DERIVED_ASSETS_ENABLED=True,
                      EDITOR_OFFSET_V2_JOBS_ROOT=str(tmp_path/'jobs'))
    init_editor_offset_v2(app)
    server=make_server('127.0.0.1',0,app,threaded=True);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try: yield f'http://127.0.0.1:{server.server_port}'
    finally: server.shutdown();server.server_close();thread.join(5)


@pytest.mark.parametrize('variant',['scale','mirror','rotate_offset'])
def test_actual_svg_artwork_matches_preview_and_native_pdf(output_server,tmp_path,variant):
    from test_editor_offset_v2 import _open_job_with_repeat
    path=tmp_path/'asymmetric.pdf'
    with fitz.open() as doc:
        p=doc.new_page(width=40*72/25.4,height=20*72/25.4)
        p.draw_rect(fitz.Rect(0,0,p.rect.width/2,p.rect.height),color=None,fill=(1,0,0))
        p.draw_rect(fitz.Rect(p.rect.width/2,0,p.rect.width,p.rect.height),color=None,fill=(0,0,1))
        p.set_trimbox(p.rect);doc.save(path)
    with sync_playwright() as pw:
        browser=pw.chromium.launch();page=browser.new_page(viewport={'width':1440,'height':900})
        try:
            _open_job_with_repeat(page,output_server,path,1)
            page.locator('#ev2-save').click();expect(page.locator('#ev2-save')).to_be_disabled()
            page.wait_for_function('() => !window.__EDITOR_OFFSET_V2__.store.hasUnsavedChanges() && window.__EDITOR_OFFSET_V2__.store.saveState.status === "clean"')
            job=page.url.rsplit('/',1)[1];api=f'{output_server}/api/editor-offset-v2/jobs/{job}'
            current=page.request.get(api).json();layout=current['layout'];slot=layout['slots'][0]
            layout['sheet']['size_mm']={'width':120,'height':80}
            layout['sheet']['printable_margins_mm']={k:0 for k in ('left','right','top','bottom')}
            slot['geometry']['position_mm'].update(x_mm=60,y_mm=40);slot['geometry']['rotation_deg']=0
            transform=slot['content_transform']
            if variant=='scale': transform.update(scale_x=.7,scale_y=.8)
            elif variant=='mirror': transform.update(mirror_x=True,mirror_y=True)
            else:
                transform.update(rotation_deg=90,scale_x=.5,scale_y=.8,offset_mm={'x':2,'y':-1})
                slot['geometry']['rotation_deg']=90
            layout['export']['marks_profiles'][0]['crop_marks']=True
            response=page.request.put(api+'/layout',data={'layout':layout,'base_revision':current['revision']})
            assert response.status==200,response.text()
            page.reload();expect(page.locator('.ev2-svg-artwork')).to_have_count(1)
            captured=page.evaluate('''async () => {
                const original=document.querySelector('#ev2-canvas');
                const svg=original.cloneNode(true);
                svg.querySelectorAll('*').forEach(el=>{
                    if (!['defs','clipPath','rect','g','image','line'].includes(el.tagName)) el.remove();
                });
                svg.querySelectorAll('rect,line,g').forEach(el=>{
                    if (el.tagName==='rect' && !el.closest('clipPath')) el.remove();
                    if (el.tagName==='line' && !el.classList.contains('ev2-svg-crop-mark')) el.remove();
                    if (el.tagName==='g' && !el.classList.contains('ev2-svg-slot')) el.remove();
                });
                for (const img of svg.querySelectorAll('image')) {
                    const blob=await (await fetch(img.getAttribute('href'))).blob();
                    const encoded=await new Promise(resolve=>{const r=new FileReader();r.onload=()=>resolve(r.result);r.readAsDataURL(blob);});
                    img.setAttribute('href',encoded);
                }
                svg.setAttribute('viewBox','0 0 120 80');svg.setAttribute('width','680');svg.setAttribute('height','454');
                const data=new XMLSerializer().serializeToString(svg);
                const img=new Image();img.src='data:image/svg+xml;base64,'+btoa(unescape(encodeURIComponent(data)));await img.decode();
                const c=document.createElement('canvas');c.width=680;c.height=454;const ctx=c.getContext('2d');ctx.fillStyle='white';ctx.fillRect(0,0,680,454);ctx.drawImage(img,0,0);
                return c.toDataURL('image/png').split(',')[1];
            }''')
            png=page.request.post(api+'/preview',data={'dpi':144});assert png.status==200,png.text()
            pdf=page.request.post(api+'/pdf-final',data={'dpi':144});assert pdf.status==200,pdf.text()
            svg_image=Image.open(io.BytesIO(base64.b64decode(captured))).convert('RGB')
            preview=Image.open(io.BytesIO(png.body())).convert('RGB')
            # Crop around artwork/marks; white sheet cannot dilute a placement bug.
            roi=(190,80,490,374)
            delta=ImageChops.difference(svg_image.crop(roi),preview.crop(roi))
            mean=sum(ImageStat.Stat(delta).mean)/3
            changed=sum(max(p)>32 for p in delta.getdata())/(delta.width*delta.height)
            assert changed<=.02 and mean<=8,(variant,changed,mean)
            wrong=ImageChops.offset(svg_image.crop(roi),25,0)
            wrong_delta=ImageChops.difference(wrong,preview.crop(roi))
            assert sum(max(p)>32 for p in wrong_delta.getdata())/(delta.width*delta.height)>.02
            with fitz.open(stream=pdf.body(),filetype='pdf') as doc:
                assert len(doc[0].get_drawings())>=10 and not doc[0].get_images()
            (tmp_path/f'{variant}-actual-svg.png').write_bytes(base64.b64decode(captured))
        finally: browser.close()


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
            page.wait_for_function('() => !window.__EDITOR_OFFSET_V2__.store.hasUnsavedChanges() && window.__EDITOR_OFFSET_V2__.store.saveState.status === "clean"')
            page.reload()
            page.wait_for_function('() => window.__EDITOR_OFFSET_V2__?.store.layout.works.length === 2')
            assert not errors
        finally:
            browser.close()


def test_operator_preview_download_retry_and_stale_result(output_server,tmp_path):
    from test_editor_offset_v2 import _write_test_pdf, _open_job_with_repeat
    path=tmp_path/'operator.pdf';_write_test_pdf(path)
    with sync_playwright() as pw:
        browser=pw.chromium.launch();page=browser.new_page(viewport={'width':1440,'height':900})
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        try:
            _open_job_with_repeat(page,output_server,path,1)
            page.get_by_label('Centro X',exact=True).fill('150')
            page.get_by_label('Centro Y',exact=True).fill('150')
            page.get_by_role('button',name='Aplicar posición',exact=True).click()
            _open_workflow_stage(page,'output')
            page.locator('#ev2-output-dpi').select_option('72')
            page.locator('#ev2-output-preview').click()
            expect(page.locator('#ev2-output-result')).to_contain_text('Preview lista',timeout=20000)
            expect(page.locator('#ev2-output-image')).to_be_visible()
            with page.expect_download() as download:
                page.locator('#ev2-output-pdf').click()
            target=tmp_path/'downloaded.pdf';download.value.save_as(target)
            with fitz.open(target) as doc:
                assert 'EDITOR OFFSET V2' in doc[0].get_text()
                assert doc[0].get_drawings() and not doc[0].get_images()
            expect(page.locator('#ev2-output-result')).to_contain_text('PDF listo; descarga iniciada')
            # A controlled network failure can be retried without duplicating output.
            page.route('**/preview',lambda route:route.fulfill(status=503,content_type='application/json',body=json.dumps({'ok':False,'error':{'message':'Prueba de red interrumpida','code':'TEST_UNAVAILABLE'}})))
            page.locator('#ev2-output-preview').click()
            expect(page.locator('#ev2-output-result')).to_contain_text('Prueba de red interrumpida')
            page.unroute('**/preview')
            page.locator('#ev2-output-preview').click()
            expect(page.locator('#ev2-output-result')).to_contain_text('Preview lista',timeout=20000)
            def late(route):
                response=route.fetch()
                page.locator('#ev2-output-mirror').check()
                route.fulfill(response=response)
            page.route('**/pdf-final',late)
            page.locator('#ev2-output-pdf').click()
            expect(page.locator('#ev2-output-result')).to_contain_text('Resultado desactualizado',timeout=20000)
            expect(page.locator('#ev2-output-image')).to_be_hidden()
            page.unroute('**/pdf-final')
            assert not errors
        finally:browser.close()
