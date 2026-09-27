"""Delivery 1: operation-specific blockers and bounded sheet preview."""
import copy
import io

import fitz
import pytest
from PIL import Image

from test_output_safety_v2 import case
from editor_offset_v2.application.preflight_service import PreflightService, PreflightServiceError
from editor_offset_v2.application.preview_service import PreviewService, PreviewServiceError
from editor_offset_v2.domain.preflight_contract import PreflightContractError, validate_preflight_report
from editor_offset_v2.domain.preview_policy import preview_pixel_size, preview_resource_issue


def decisions(report):
    return {item['operation']: item for item in report['decisions']}


def save_layout(client, job, saved, layout):
    result = client.put(f'/api/editor-offset-v2/jobs/{job}/layout',
                        json={'base_revision': saved['revision'], 'layout': layout})
    assert result.status_code == 200, result.get_json()


@pytest.mark.parametrize('geometry_case,code', [
    ('outside', 'BLEED_OUTSIDE_PRINTABLE'),
    ('overlap', 'BLEED_OVERLAP'),
    ('touching', None),
])
def test_geometry_warning_blocks_only_declared_operations(case, geometry_case, code):
    _, client, job, saved, repo = case
    layout = saved['layout']
    slot = layout['slots'][0]
    slot['geometry'].update(trim_size_mm={'width': 90, 'height': 50}, bleed_mm=3)
    slot['geometry']['position_mm'].update(x_mm=100, y_mm=100)
    slot['content_transform']['clip_to'] = 'bleed_box'
    layout['sheet']['printable_margins_mm'] = dict(left=10, right=10, top=10, bottom=10)
    if geometry_case == 'outside':
        # Trim stays printable (x=55); only the 3 mm bleed crosses x=54.
        layout['sheet']['printable_margins_mm']['left'] = 54
    else:
        other = copy.deepcopy(slot)
        other['id'] = 'slot_adjacent'
        other['geometry']['position_mm']['x_mm'] = 194 if geometry_case == 'overlap' else 196
        layout['slots'].append(other)
    save_layout(client, job, saved, layout)
    before = repo.layout_path(job).read_bytes()
    options = {'dpi': 36, 'allow_mirror_bleed': True}
    report = client.post(f'/api/editor-offset-v2/jobs/{job}/preflight', json=options).get_json()['report']
    state = decisions(report)
    assert state['preview']['status'] == 'eligible'
    if code:
        issue = next(i for i in report['issues'] if i['code'] == code)
        assert issue['severity'] == 'warning'
        for operation in ('pdf_final', 'ctp'):
            assert issue['issue_id'] in state[operation]['blocking_issue_ids']
            assert state[operation]['status'] == 'blocked'
        result = client.post(f'/api/editor-offset-v2/jobs/{job}/pdf-final', json=options)
        assert result.status_code == 422
        assert result.get_json()['error']['code'] == 'PREFLIGHT_BLOCKED'
        assert any(i['code'] == code for i in result.get_json()['error']['issues'])
        assert not list((repo.job_path(job) / 'outputs').glob('*.pdf'))
        # A forged decision cannot turn a blocking warning into authorization.
        forged = copy.deepcopy(report)
        decision = decisions(forged)['pdf_final']
        decision.update(status='eligible', blocking_issue_ids=[], reason_codes=[])
        with pytest.raises(PreflightServiceError, match='current-policy'):
            PreflightService(repo).consume(job, forged, 'pdf_final')
    else:
        assert not any(i['code'] in ('BLEED_OVERLAP', 'TRIM_OVERLAP') for i in report['issues'])
        assert state['pdf_final']['status'] == 'eligible'
        assert client.post(f'/api/editor-offset-v2/jobs/{job}/pdf-final', json=options).status_code == 200
    assert client.post(f'/api/editor-offset-v2/jobs/{job}/preview', json=options).status_code == 200
    assert repo.layout_path(job).read_bytes() == before
    assert not list((repo.job_path(job) / 'outputs').glob('*.tmp'))


def test_large_preview_is_blocked_before_composition_but_vector_pdf_remains_eligible(case, monkeypatch):
    _, client, job, saved, repo = case
    layout = saved['layout']
    layout['sheet']['size_mm'] = {'width': 700, 'height': 700}
    save_layout(client, job, saved, layout)
    before = repo.layout_path(job).read_bytes()
    options = {'dpi': 300}
    report = client.post(f'/api/editor-offset-v2/jobs/{job}/preflight', json=options).get_json()['report']
    issue = next(i for i in report['issues'] if i['code'] == 'PREVIEW_RESOURCE_LIMIT')
    assert issue['blocks'] == ['preview']
    assert decisions(report)['preview']['status'] == 'blocked'
    assert decisions(report)['pdf_final']['status'] == 'eligible'
    import editor_offset_v2.infrastructure.pdf_compositor as compositor
    compose = compositor.compose_pdf
    calls = []
    def tracked(*args, **kwargs):
        calls.append(True)
        return compose(*args, **kwargs)
    monkeypatch.setattr(compositor, 'compose_pdf', tracked)
    response = client.post(f'/api/editor-offset-v2/jobs/{job}/preview', json=options)
    assert response.status_code == 422
    assert response.get_json()['error']['code'] == 'PREFLIGHT_BLOCKED'
    assert any(i['code'] == 'PREVIEW_RESOURCE_LIMIT' for i in response.get_json()['error']['issues'])
    # The renderer retains its own guard even for internal callers skipping preflight.
    with pytest.raises(PreviewServiceError) as error:
        PreviewService(repo).render(job, dpi=300, require_preflight=False)
    assert error.value.code == 'PREVIEW_RESOURCE_LIMIT'
    assert not calls
    assert not list((repo.job_path(job) / 'previews').glob('*.png'))
    pdf = client.post(f'/api/editor-offset-v2/jobs/{job}/pdf-final', json=options)
    assert pdf.status_code == 200
    with fitz.open(stream=pdf.data, filetype='pdf') as document:
        assert document.page_count == 1
        assert document[0].rect.width * 25.4 / 72 == pytest.approx(700, abs=.01)
        assert document[0].rect.height * 25.4 / 72 == pytest.approx(700, abs=.01)
        assert 'PREVIEW-V2' in document[0].get_text()
        assert not document[0].get_images()
    report = client.post(f'/api/editor-offset-v2/jobs/{job}/preflight', json={'dpi': 150}).get_json()['report']
    assert decisions(report)['preview']['status'] == 'eligible'
    preview = client.post(f'/api/editor-offset-v2/jobs/{job}/preview', json={'dpi': 150})
    assert preview.status_code == 200
    with Image.open(io.BytesIO(preview.data)) as image:
        assert image.size == (4134, 4134)
    assert repo.layout_path(job).read_bytes() == before


def test_disabled_gate_and_layout_findings_are_both_reported(case):
    app, client, job, saved, _ = case
    app.config['EDITOR_OFFSET_V2_PDF_FINAL_ENABLED'] = False
    layout = saved['layout']
    layout['slots'][0]['geometry']['position_mm']['x_mm'] = 0
    save_layout(client, job, saved, layout)
    report = client.post(f'/api/editor-offset-v2/jobs/{job}/preflight', json={}).get_json()['report']
    assert set(decisions(report)['pdf_final']['reason_codes']) == {'PREFLIGHT_FINDINGS', 'CAPABILITY_GATE_NOT_ENABLED'}
    assert client.post(f'/api/editor-offset-v2/jobs/{job}/pdf-final', json={}).get_json()['error']['code'] == 'PDF_FINAL_DISABLED'


@pytest.mark.parametrize('component,old_version', [('policy', '2'), ('capabilities', '4')])
def test_old_report_policy_cannot_authorize_output(case, component, old_version):
    _, _, job, _, repo = case
    service = PreflightService(repo)
    report = service.run(job, enabled_operations={'preview': True})
    report[component]['version'] = old_version
    with pytest.raises(PreflightServiceError) as error:
        service.consume(job, report, 'preview')
    assert error.value.code == 'PREFLIGHT_INVALID_REPORT'


def test_report_rejects_unknown_blocking_operation(case):
    _, _, job, _, repo = case
    report = PreflightService(repo).run(job, enabled_operations={'preview': True})
    report['issues'].append({'issue_id': 'bad-operation', 'check_id': 'geometry',
                             'severity': 'warning', 'blocks': ['unknown-output']})
    with pytest.raises(PreflightContractError):
        validate_preflight_report({k: v for k, v in report.items() if k != 'report_path'})


@pytest.mark.parametrize('width_px,expected_width,blocked', [
    (3999.49, 3999, False),
    (4000.0, 4000, False),
    (4000.49, 4000, False),
    (4000.51, 4001, True),
])
def test_preview_budget_uses_rounded_raster_dimensions(width_px, expected_width, blocked):
    sheet = {'width': width_px * 25.4 / 150, 'height': 6000 * 25.4 / 150}
    assert preview_pixel_size(sheet, 150) == (expected_width, 6000)
    assert (preview_resource_issue(sheet, 150) is not None) is blocked
