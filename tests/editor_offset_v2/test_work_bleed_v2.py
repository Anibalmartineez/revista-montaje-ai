"""Delivery 3: work-owned decisions, physical coverage, persisted compatibility."""
import copy
import io
import json
from pathlib import Path

import fitz
import pytest
from PIL import Image, ImageChops
from jsonschema import Draft202012Validator

from test_output_safety_v2 import case
from editor_offset_v2.domain.validation import validate_layout_v2
from editor_offset_v2.domain.work_bleed import allows_mirror, available_bleed, source_covers_bleed

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / 'tests/fixtures/editor_offset_v2'


def test_shared_physical_coverage_fixtures():
    for c in json.loads((FIXTURES / 'work_bleed_coverage.json').read_text()):
        assert available_bleed(c['boxes'], c['selected']) == pytest.approx(c['available']), c['name']
        assert source_covers_bleed(c['boxes'], c['selected'], c['bleed']) == c['covered'], c['name']
        if c['bleed']:
            assert not source_covers_bleed(c['boxes'], c['selected'], c['bleed'], 'trim_box')


@pytest.mark.parametrize('strategy', ['source_only', 'mirror_if_missing', None, False, 'automatic', {}, []])
def test_optional_strategy_schema_and_validator_agree(strategy):
    layout = json.loads((FIXTURES / 'layout_v2_complete.json').read_text())
    schema = json.loads((ROOT / 'editor_offset_v2/schemas/layout-v2.schema.json').read_text())
    validator = Draft202012Validator(schema)
    assert not list(validator.iter_errors(layout)) and not validate_layout_v2(layout)
    layout['works'][0]['bleed_strategy'] = strategy
    valid = strategy in ('source_only', 'mirror_if_missing')
    assert (not list(validator.iter_errors(layout))) == valid
    assert (not validate_layout_v2(layout)) == valid


def setup_bleed(case, strategy):
    _, client, job, saved, repo = case
    layout = copy.deepcopy(saved['layout'])
    if strategy is not None:
        layout['works'][0]['bleed_strategy'] = strategy
    layout['works'][0]['bleed_mm'] = 3
    slot = layout['slots'][0]
    slot['geometry'].update(bleed_mm=3, trim_size_mm={'width':90, 'height':50})
    slot['geometry']['position_mm'].update(x_mm=100, y_mm=100)
    slot['content_transform']['clip_to'] = 'bleed_box'
    response = client.put(f'/api/editor-offset-v2/jobs/{job}/layout', json={'base_revision':saved['revision'], 'layout':layout})
    assert response.status_code == 200, response.json
    return client, f'/api/editor-offset-v2/jobs/{job}', response.json, repo


@pytest.mark.parametrize('strategy,global_permission,allowed', [
    ('source_only', True, False), ('source_only', False, False),
    ('mirror_if_missing', False, True), ('mirror_if_missing', True, True),
    (None, False, False), (None, True, True),
])
def test_saved_work_policy_controls_preflight_preview_pdf_and_preserves_old_jobs(case, strategy, global_permission, allowed):
    client, api, saved, repo = setup_bleed(case, strategy)
    before = repo.layout_path(saved['job_id']).read_bytes()
    options = {'dpi':36, 'allow_mirror_bleed':global_permission}
    assert allows_mirror(saved['layout']['works'][0], global_permission) == allowed
    report = client.post(api+'/preflight', json=options).json['report']
    for d in report['decisions']:
        if d['operation'] != 'ctp': assert (d['status'] == 'eligible') == allowed
    code = 'BLEED_GENERATED_BY_MIRROR' if allowed else 'BLEED_REQUIRES_EXPLICIT_MIRROR'
    assert any(i['code'] == code for i in report['issues'])
    png = client.post(api+'/preview', json=options)
    pdf = client.post(api+'/pdf-final', json=options)
    assert png.status_code == pdf.status_code == (200 if allowed else 422)
    if allowed:
        with fitz.open(stream=pdf.data, filetype='pdf') as doc:
            assert doc.page_count == 1
            assert doc[0].rect.width / (72/25.4) == pytest.approx(700, abs=.01)
            image = Image.open(io.BytesIO(png.data)).convert('RGB')
            pix = doc[0].get_pixmap(matrix=fitz.Matrix(image.width/doc[0].rect.width,image.height/doc[0].rect.height),alpha=False)
            rendered=Image.frombytes('RGB',(pix.width,pix.height),pix.samples).crop((0,0,image.width,image.height))
            assert ImageChops.difference(image,rendered).getbbox() is None
    assert repo.layout_path(saved['job_id']).read_bytes() == before


def test_mixed_work_authorizations_do_not_leak_through_prepared_source_cache(case):
    client, api, saved, _ = setup_bleed(case, 'mirror_if_missing')
    layout = saved['layout']
    other = copy.deepcopy(layout['works'][0]); other.update(id='work_source_only',bleed_strategy='source_only')
    layout['works'].append(other)
    slot = copy.deepcopy(layout['slots'][0]); slot.update(id='slot_source_only',work_id=other['id'])
    slot['geometry']['position_mm']['x_mm']=220
    layout['slots'].append(slot)
    assert client.put(api+'/layout',json={'base_revision':saved['revision'],'layout':layout}).status_code==200
    report=client.post(api+'/preflight',json={'allow_mirror_bleed':True}).json['report']
    blocked=[i for i in report['issues'] if i['code']=='BLEED_REQUIRES_EXPLICIT_MIRROR']
    assert len(blocked)==1 and blocked[0]['references']['slot_ids']==['slot_source_only']
    assert any(i['code']=='BLEED_GENERATED_BY_MIRROR' for i in report['issues'])


def test_materialized_mirror_remains_identified_and_cannot_bypass_source_only(case):
    client, api, saved, _ = setup_bleed(case, 'mirror_if_missing')
    layout=saved['layout']; slot=layout['slots'][0]; source=slot['source']
    response=client.post(api+f"/assets/{source['asset_id']}/derived-page",json={
        'page':source['page'],'pdf_box':source['pdf_box'],'bleed_mm':3,'allow_mirror_bleed':True,
        'content_transform':slot['content_transform']})
    assert response.status_code==201, response.json
    manifest=response.json['result']['manifest']; assert manifest['bleed_origin']=='mirror'
    slot['source']['derived']={k:manifest[k] for k in ('derived_key','derived_sha256','source_sha256')}
    response=client.put(api+'/layout',json={'base_revision':saved['revision'],'layout':layout})
    assert response.status_code==200
    report=client.post(api+'/preflight',json={}).json['report']
    assert any(i['code']=='BLEED_GENERATED_BY_MIRROR' for i in report['issues'])
    layout=response.json['layout']
    layout['works'][0]['bleed_strategy']='source_only'
    assert client.put(api+'/layout',json={'base_revision':response.json['revision'],'layout':layout}).status_code==200
    report=client.post(api+'/preflight',json={'allow_mirror_bleed':True}).json['report']
    assert any(i['code']=='BLEED_REQUIRES_EXPLICIT_MIRROR' for i in report['issues'])


@pytest.mark.parametrize('strategy', ['source_only', 'mirror_if_missing'])
def test_real_bleed_is_preserved_under_both_work_strategies(tmp_path,strategy):
    from test_legacy_output_probe_v2 import make_job, rgb_at, COLOR_TOLERANCE
    from test_pdf_final_v2 import app_factory, _ready_layout
    from test_preview_v2 import create_job, _save_preview_layout
    _, source=make_job(tmp_path/'fixture',bleed=3)
    original=source.read_bytes()
    app=app_factory(tmp_path,enabled=True); client=app.test_client(); created=create_job(client)
    api=f"/api/editor-offset-v2/jobs/{created['job_id']}"
    uploaded=client.post(api+'/assets',data={'base_revision':str(created['revision']),
        'file':(io.BytesIO(original),'physical-bleed.pdf')},content_type='multipart/form-data').json
    layout=_ready_layout(uploaded['layout'],uploaded['asset'])
    layout['works'][0].update(bleed_strategy=strategy,bleed_mm=3,trim_size_mm={'width':40,'height':20})
    slot=layout['slots'][0]; slot['geometry'].update(trim_size_mm={'width':40,'height':20},bleed_mm=3,rotation_deg=0)
    slot['geometry']['position_mm'].update(x_mm=100,y_mm=100)
    slot['content_transform']['clip_to']='bleed_box'
    _save_preview_layout(client,uploaded,layout)
    report=client.post(api+'/preflight',json={}).json['report']
    assert not any(i['code'].startswith('BLEED_') and i['code']!='BLEED_OVERLAP' for i in report['issues'])
    pdf=client.post(api+'/pdf-final',json={}); assert pdf.status_code==200, pdf.json
    with fitz.open(stream=pdf.data,filetype='pdf') as doc:
        # Source bleed is magenta; a mirrored band from the trim is red/blue.
        assert rgb_at(doc[0],78.5,100)==pytest.approx((255,0,255),abs=COLOR_TOLERANCE)
    assert source.read_bytes()==original
