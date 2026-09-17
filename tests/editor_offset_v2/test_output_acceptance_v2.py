"""Operational acceptance: bounded loads, revision identity and option gates."""
import copy
import io
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor
import fitz
import pytest
from test_output_safety_v2 import case
from test_pdf_final_v2 import app_factory, _ready_layout
from test_preview_v2 import create_job, _save_preview_layout
from editor_offset_v2.application.pdf_final_service import PdfFinalService, PdfFinalServiceError
from editor_offset_v2.application.preflight_service import PreflightService


@pytest.mark.parametrize('payload',[{'face':[]},{'dpi':True},{'dpi':float('nan')},{'allow_mirror_bleed':1},{'bogus':1}])
def test_preflight_options_invalid_without_server_exception(case,payload):
    _,client,job,_,_=case
    assert client.post(f'/api/editor-offset-v2/jobs/{job}/preflight',json=payload).status_code==400


def test_expected_revision_and_artifact_headers(case):
    _,client,job,saved,_=case
    url=f'/api/editor-offset-v2/jobs/{job}/pdf-final'
    bad=client.post(url,json={'expected_revision':saved['revision']-1})
    assert bad.status_code==409 and bad.get_json()['error']['code']=='PREFLIGHT_STALE'
    result=client.post(url,json={'expected_revision':saved['revision'],'dpi':72})
    assert result.status_code==200
    assert result.headers['X-V2-Revision']==str(saved['revision'])
    assert result.headers['Cache-Control']=='no-store'
    assert '/' not in result.headers['X-V2-Filename'] and '\\' not in result.headers['X-V2-Filename']


def test_source_memory_budget_blocks_without_artifact(case,monkeypatch):
    _,client,job,_,repo=case
    import editor_offset_v2.infrastructure.output_snapshot as snapshot
    monkeypatch.setattr(snapshot,'MAX_SOURCE_BYTES',8)
    result=client.post(f'/api/editor-offset-v2/jobs/{job}/pdf-final',json={})
    assert result.status_code==422
    assert not list((repo.job_path(job)/'outputs').glob('*.pdf'))


def test_placement_limit_rejects_more_than_accepted_load(case):
    from editor_offset_v2.application.native_output_capabilities import native_output_issues
    _,_,_,saved,_=case
    layout=copy.deepcopy(saved['layout'])
    layout['slots']=[dict(layout['slots'][0],id=f'limit_{i}') for i in range(501)]
    assert any(issue.code=='OUTPUT_PLACEMENT_LIMIT' for issue,_ in native_output_issues(layout))


def test_failed_pdf_publication_preserves_layout_and_cleans_temporaries(case,monkeypatch):
    _,client,job,_,repo=case
    import os
    original=os.replace
    before=repo.layout_path(job).read_bytes()
    def fail(source,target):
        if target.parent.name=='outputs':raise OSError('simulated disk failure')
        return original(source,target)
    monkeypatch.setattr(os,'replace',fail)
    response=client.post(f'/api/editor-offset-v2/jobs/{job}/pdf-final',json={'dpi':72})
    assert response.status_code==500 and response.get_json()['error']['code']=='PDF_FINAL_PUBLISH_FAILED'
    assert repo.layout_path(job).read_bytes()==before
    assert not list((repo.job_path(job)/'outputs').glob('*.pdf'))
    assert not list((repo.job_path(job)/'outputs').glob('*.tmp'))


@pytest.mark.parametrize('count',[14,100,500])
def test_bounded_placement_load_with_shared_vector_source(case,count,record_property):
    _,client,job,saved,repo=case;layout=saved['layout']
    slot=layout['slots'][0];slot['geometry']['trim_size_mm']={'width':90,'height':50}
    # A bounded large sheet permits non-overlap; PDF does not allocate a sheet bitmap.
    layout['sheet']['size_mm']={'width':2000,'height':1400}
    layout['slots']=[]
    for i in range(count):
        item=copy.deepcopy(slot);item['id']=f'load_{i}'
        item['geometry']['position_mm'].update(x_mm=50+(i%20)*95,y_mm=30+(i//20)*54)
        layout['slots'].append(item)
    assert client.put(f'/api/editor-offset-v2/jobs/{job}/layout',json={'layout':layout,'base_revision':saved['revision']}).status_code==200
    start=time.monotonic();result=PdfFinalService(repo).render(job,dpi=300);elapsed=time.monotonic()-start
    with fitz.open(stream=result.data,filetype='pdf') as doc:
        assert doc.page_count==1 and len(doc[0].get_text().split('PREVIEW-V2'))-1==count
        assert not doc[0].get_images()
    assert elapsed<60
    record_property('placements',count);record_property('seconds',round(elapsed,3));record_property('bytes',len(result.data))


@pytest.mark.parametrize('pages',[3,20,249])
def test_multipage_upload_near_inspector_limit(tmp_path,pages,record_property):
    app=app_factory(tmp_path,enabled=True);client=app.test_client();created=create_job(client)
    with fitz.open() as doc:
        for i in range(pages): doc.new_page(width=90*72/25.4,height=50*72/25.4).insert_text((10,20),f'PAGE {i+1}')
        data=doc.tobytes()
    start=time.monotonic()
    uploaded=client.post(f"/api/editor-offset-v2/jobs/{created['job_id']}/assets",data={'base_revision':str(created['revision']),'file':(io.BytesIO(data),'pages.pdf')},content_type='multipart/form-data')
    assert uploaded.status_code==201;uploaded=uploaded.get_json();layout=_ready_layout(uploaded['layout'],uploaded['asset'])
    slot=layout['slots'][0];slot['source'].update(page=pages,pdf_box='media')
    for key in ('front_source','back_source'):layout['works'][0][key]['pdf_box']='media'
    slot['geometry']['trim_size_mm']={'width':90,'height':50}
    _save_preview_layout(client,uploaded,layout)
    result=client.post(f"/api/editor-offset-v2/jobs/{created['job_id']}/pdf-final",json={'dpi':300})
    assert result.status_code==200,result.get_json()
    with fitz.open(stream=result.data,filetype='pdf') as doc: assert f'PAGE {pages}' in doc[0].get_text()
    record_property('pages',pages);record_property('seconds',round(time.monotonic()-start,3))


def test_four_requests_are_bounded_and_capacity_recovers(case,monkeypatch):
    _,_,job,_,repo=case
    original=PreflightService.consume;barrier=threading.Barrier(2);release=threading.Event()
    def consume(self,*args,**kwargs):
        result=original(self,*args,**kwargs);barrier.wait(5);assert release.wait(10);return result
    monkeypatch.setattr(PreflightService,'consume',consume)
    def run():
        try: return PdfFinalService(repo).render(job,dpi=36).data
        except PdfFinalServiceError as exc:return exc.code
    with ThreadPoolExecutor(max_workers=4) as pool:
        a,b=pool.submit(run),pool.submit(run)
        deadline=time.monotonic()+5
        while barrier.n_waiting==0 and time.monotonic()<deadline: time.sleep(.01)
        # The workers remain held at the release event after their barrier.
        c,d=pool.submit(run),pool.submit(run)
        try: assert c.result(5)==d.result(5)=='OUTPUT_BUSY'
        finally: release.set()
        assert a.result(10).startswith(b'%PDF') and b.result(10).startswith(b'%PDF')
    monkeypatch.setattr(PreflightService,'consume',original)
    assert PdfFinalService(repo).render(job,dpi=36).data.startswith(b'%PDF')


def test_large_source_near_upload_budget_preserves_original(tmp_path,record_property):
    import hashlib
    app=app_factory(tmp_path,enabled=True);client=app.test_client();created=create_job(client)
    # Uncompressed unused stream exercises transport/hash/snapshot size without
    # claiming acceptance of a 49 MiB complex artwork or wasting raster memory.
    with fitz.open() as doc:
        doc.new_page(width=90*72/25.4,height=50*72/25.4).insert_text((10,20),'LARGE SOURCE')
        xref=doc.get_new_xref();doc.update_object(xref,'<<>>')
        doc.update_stream(xref,b'X'*(49*1024*1024),compress=False)
        data=doc.tobytes(garbage=0,deflate=False)
    assert 49*1024*1024<len(data)<50*1024*1024
    digest=hashlib.sha256(data).hexdigest();start=time.monotonic()
    response=client.post(f"/api/editor-offset-v2/jobs/{created['job_id']}/assets",data={'base_revision':str(created['revision']),'file':(io.BytesIO(data),'large.pdf')},content_type='multipart/form-data')
    assert response.status_code==201;uploaded=response.get_json()
    assert uploaded['asset']['sha256']==digest
    layout=_ready_layout(uploaded['layout'],uploaded['asset'])
    layout['slots'][0]['source']['pdf_box']='media'
    layout['slots'][0]['geometry']['trim_size_mm']={'width':90,'height':50}
    for key in ('front_source','back_source'):layout['works'][0][key]['pdf_box']='media'
    _save_preview_layout(client,uploaded,layout)
    result=client.post(f"/api/editor-offset-v2/jobs/{created['job_id']}/pdf-final",json={'dpi':300})
    assert result.status_code==200,result.get_json()
    with fitz.open(stream=result.data,filetype='pdf') as doc:assert 'LARGE SOURCE' in doc[0].get_text()
    sources=list((tmp_path/'v2_jobs'/created['job_id']/'assets').rglob('*.pdf'))
    assert len(sources)==1 and hashlib.sha256(sources[0].read_bytes()).hexdigest()==digest
    record_property('source_bytes',len(data));record_property('seconds',round(time.monotonic()-start,3))
