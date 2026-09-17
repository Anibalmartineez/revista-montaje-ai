"""Regressions from the real-output audit (phase 39A)."""
import copy
from pathlib import Path
import pytest
from test_pdf_final_v2 import app_factory, _upload_source, _ready_layout
from test_preview_v2 import create_job, _save_preview_layout
from editor_offset_v2.application.preflight_service import PreflightService, PreflightServiceError
from editor_offset_v2.application.preview_service import PreviewService
from editor_offset_v2.infrastructure.job_repository import JobRepository

@pytest.fixture
def case(tmp_path):
    app = app_factory(tmp_path, enabled=True)
    app.config.update(EDITOR_OFFSET_V2_PREVIEW_ENABLED=True, EDITOR_OFFSET_V2_DERIVED_ASSETS_ENABLED=True)
    client = app.test_client()
    created = create_job(client)
    uploaded = _upload_source(client, created)
    saved = _save_preview_layout(client, uploaded, _ready_layout(uploaded['layout'], uploaded['asset']))
    return app, client, created['job_id'], saved, JobRepository(Path(app.config['EDITOR_OFFSET_V2_JOBS_ROOT']))

def test_incomplete_report_cannot_be_consumed(case):
    _, _, job, _, repo = case
    service = PreflightService(repo)
    report = service.run(job, enabled_operations={'preview': True})
    report['execution'] = 'incomplete'
    report['checks'][0]['status'] = 'not_run'
    with pytest.raises(PreflightServiceError):
        service.consume(job, report, 'preview')

def test_save_after_preflight_cannot_publish_unchecked_revision(case, monkeypatch):
    _, client, job, saved, repo = case
    original = PreflightService.consume
    def consume(service, job_id, report, operation, **kwargs):
        result = original(service, job_id, report, operation, **kwargs)
        layout = copy.deepcopy(saved['layout'])
        layout['slots'][0]['geometry']['position_mm']['x_mm'] = 0
        assert client.put(f'/api/editor-offset-v2/jobs/{job}/layout', json={'base_revision': saved['revision'], 'layout': layout}).status_code == 200
        return result
    monkeypatch.setattr(PreflightService, 'consume', consume)
    response = client.post(f'/api/editor-offset-v2/jobs/{job}/preview', json={'dpi':36})
    assert response.status_code == 409
    assert not list((repo.job_path(job)/'previews').glob('*.png'))

def test_missing_derived_is_a_preflight_error(case):
    _, client, job, saved, repo = case
    layout = saved['layout']
    layout['slots'][0]['source']['derived'] = {'derived_key':'derived/missing.pdf', 'derived_sha256':'a'*64, 'source_sha256':layout['assets'][0]['sha256']}
    assert client.put(f'/api/editor-offset-v2/jobs/{job}/layout', json={'base_revision':saved['revision'], 'layout':layout}).status_code == 200
    report = PreflightService(repo).run(job, enabled_operations={'preview':True})
    assert any(i['code'] == 'DERIVED_SOURCE_MISSING' for i in report['issues'])
    assert next(d for d in report['decisions'] if d['operation']=='preview')['status']=='blocked'

@pytest.mark.parametrize('payload', [{'face':[]}, {'face':{}}, {'dpi':True}])
def test_pdf_payload_types_are_controlled(case, payload):
    _, client, job, _, _ = case
    assert client.post(f'/api/editor-offset-v2/jobs/{job}/pdf-final', json=payload).status_code == 400

@pytest.mark.parametrize('payload', [{'bleed_mm':float('nan')}, {'content_transform':{'scale_x':float('inf')}}])
def test_derived_nonfinite_values_are_controlled(case, payload):
    _, client, job, saved, _ = case
    asset = saved['layout']['assets'][0]['id']
    assert client.post(f'/api/editor-offset-v2/jobs/{job}/assets/{asset}/derived-page', json={'page':1, **payload}).status_code == 400

def test_native_preflight_accepts_media_without_legacy_page_limit(case):
    _, client, job, saved, repo = case
    layout = saved['layout']
    for slot in layout['slots']:
        slot['source']['pdf_box']='media'
        slot['content_transform'].update(scale_x=0.5, mirror_x=True)
    assert client.put(f'/api/editor-offset-v2/jobs/{job}/layout',json={'base_revision':saved['revision'],'layout':layout}).status_code==200
    report=PreflightService(repo).run(job,enabled_operations={'preview':True,'pdf_final':True})
    assert all(d['status']=='eligible' for d in report['decisions'] if d['operation']!='ctp')

def test_raster_renderer_cannot_claim_vector_preservation(case):
    _,client,job,saved,repo=case
    layout=saved['layout']; layout['export'].update(render_mode='vector_hybrid',preserve_vector_content=True)
    assert client.put(f'/api/editor-offset-v2/jobs/{job}/layout',json={'base_revision':saved['revision'],'layout':layout}).status_code==200
    from editor_offset_v2.application.native_output_capabilities import NATIVE_VECTOR_AVAILABLE
    report=PreflightService(repo).run(job,enabled_operations={'pdf_final':True})
    assert any(i['code']=='NATIVE_VECTOR_PENDING' for i in report['issues']) is (not NATIVE_VECTOR_AVAILABLE)

def test_recovery_waits_for_an_active_publication(case):
    import threading
    from editor_offset_v2.infrastructure.artifact_lifecycle import ArtifactLifecycleService
    from editor_offset_v2.infrastructure.process_lock import exclusive_file_lock
    _,_,job,_,repo=case
    root=repo.job_path(job)/'previews'
    entered,release,finished=threading.Event(),threading.Event(),threading.Event()
    active=root/'.preview-running.tmp'; target=root/'preview_r3_test.png'
    def publish():
        with exclusive_file_lock(root/'.publish.lock'):
            active.write_bytes(b'complete')
            entered.set()
            assert release.wait(5)
            active.replace(target)
    producer=threading.Thread(target=publish); producer.start(); assert entered.wait(2)
    def clean():
        ArtifactLifecycleService(repo).recover_temporaries(job); finished.set()
    cleaner=threading.Thread(target=clean); cleaner.start()
    assert not finished.wait(.1)
    assert active.exists()
    release.set(); producer.join(5); cleaner.join(5)
    assert finished.is_set() and target.read_bytes()==b'complete'

def test_retention_does_not_change_bytes_already_returned(case):
    from editor_offset_v2.infrastructure.artifact_lifecycle import ArtifactLifecycleService
    _,_,job,_,repo=case
    first=PreviewService(repo).render(job,dpi=36)
    PreviewService(repo).render(job,dpi=72)
    ArtifactLifecycleService(repo).retain(job,keep_latest=1)
    assert first.data.startswith(b'\x89PNG')
    assert not first.path.exists()

def test_report_decision_cannot_hide_a_blocking_issue(case):
    _,_,job,_,repo=case
    report=PreflightService(repo).run(job,enabled_operations={'preview':True})
    issue={'issue_id':'fabricated','check_id':'geometry','severity':'error','blocks':['preview']}
    report['issues'].append(issue)
    with pytest.raises(PreflightServiceError):
        PreflightService(repo).consume(job,report,'preview')
