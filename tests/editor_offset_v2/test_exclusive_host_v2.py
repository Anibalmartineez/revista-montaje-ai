"""Acceptance of the real V2 host, including transitive import isolation."""
import os
from pathlib import Path
import subprocess
import sys

from editor_offset_v2.web_app import REPO_ROOT, create_app


def test_exclusive_host_routes_resources_and_existing_storage(monkeypatch):
    monkeypatch.delenv("EDITOR_OFFSET_V2_JOBS_ROOT", raising=False)
    app = create_app({"TESTING": True, "EDITOR_OFFSET_V2_DEV_TOOLS_ENABLED": False})
    assert Path(app.config["EDITOR_OFFSET_V2_JOBS_ROOT"]) == REPO_ROOT / "instance/editor_offset_v2_jobs"
    assert app.config["MAX_CONTENT_LENGTH"] == 32 * 1024 * 1024
    assert set(app.blueprints) == {"editor_offset_v2"}
    client = app.test_client()
    assert client.get("/").location.endswith("/editor_offset_visual_v2")
    assert client.get("/health/editor-offset-v2").json == {
        "application": "editor-offset-v2", "hosting": "exclusive", "layout_schema_version": 2,
    }
    assert client.get("/editor_offset_visual_v2").status_code == 200
    resources = ["css/editor_offset_visual_v2.css", "js/editor_offset_visual_v2.js"]
    resources += ["js/editor_offset_v2/" + path.name for path in (REPO_ROOT / "static/js/editor_offset_v2").glob("*.js")]
    for path in resources:
        assert client.get("/static/" + path).status_code == 200, path
    for path in ("/editor_offset_visual", "/revision", "/static/js/editor_offset_visual.js",
                 "/static/constructor_offset_jobs/example/layout_constructor.json",
                 "/static/js/editor_offset_v2/../../../app.py"):
        assert client.get(path).status_code == 404, path


def test_exclusive_host_rejects_oversized_upload_without_creating_job(tmp_path):
    app = create_app({"TESTING": True, "MAX_CONTENT_LENGTH": 8,
                      "EDITOR_OFFSET_V2_JOBS_ROOT": str(tmp_path / "jobs")})
    response = app.test_client().post("/api/editor-offset-v2/jobs", json={"name": "too large"})
    assert response.status_code == 413
    assert response.is_json
    assert not list(tmp_path.rglob("layout_v2.json"))


def test_full_native_workflow_with_all_other_repository_product_imports_blocked():
    script = r'''
import importlib.abc, importlib.machinery, sys
from pathlib import Path
root = Path.cwd().resolve()
def other_product(origin):
    if not origin or origin in ('built-in', 'frozen'): return False
    try: relative = Path(origin).resolve().relative_to(root)
    except ValueError: return False
    return relative.parts[0] not in ('editor_offset_v2', 'venv', 'tests')
class RejectOtherProduct(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        spec = importlib.machinery.PathFinder.find_spec(fullname, path)
        if spec and (other_product(spec.origin) or any(other_product(p) for p in (spec.submodule_search_locations or ()))):
            raise ImportError('V2 attempted another product import: ' + fullname)
sys.meta_path.insert(0, RejectOtherProduct())
sys.path.insert(0, str(root / 'tests/editor_offset_v2'))
import hashlib, tempfile
import fitz
from PIL import Image
import io
from editor_offset_v2.web_app import create_app
from test_preview_v2 import create_job, _save_preview_layout
from test_pdf_final_v2 import _upload_source, _ready_layout
with tempfile.TemporaryDirectory() as directory:
    app = create_app({'TESTING': True, 'EDITOR_OFFSET_V2_JOBS_ROOT': directory,
        'EDITOR_OFFSET_V2_PREVIEW_ENABLED': True, 'EDITOR_OFFSET_V2_PDF_FINAL_ENABLED': True,
        'EDITOR_OFFSET_V2_DEV_TOOLS_ENABLED': False, 'EDITOR_OFFSET_V2_DERIVED_ASSETS_ENABLED': False})
    client = app.test_client()
    created = create_job(client, 'Exclusive acceptance')
    uploaded = _upload_source(client, created)
    layout = _ready_layout(uploaded['layout'], uploaded['asset'])
    layout['slots'] = []
    layout['works'][0]['requested_forms'] = 2
    layout['works'][0]['bleed_mm'] = 0
    saved = _save_preview_layout(client, uploaded, layout)
    api = '/api/editor-offset-v2/jobs/' + created['job_id']
    source = Path(directory) / created['job_id'] / uploaded['asset']['storage_key']
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    before = client.get(api).json
    response = client.post(api + '/imposition/repeat', json={
        'base_revision': saved['revision'], 'face': 'front', 'work_ids': [layout['works'][0]['id']],
        'apply_mode': 'add', 'settings': {'horizontal_gap_mm': 4, 'vertical_gap_mm': 3,
        'exact_quantity': True, 'fill_remaining_space': False, 'allow_partial': False}})
    assert response.status_code == 200, response.json
    proposal = response.json['result']
    assert proposal['success'] and len(proposal['slots']) == 2
    assert client.get(api).json == before
    layout = saved['layout']
    layout['slots'] = proposal['slots']
    saved = _save_preview_layout(client, saved, layout)
    # Reopen the same saved job using a fresh host, without migration or normalization.
    reopened = create_app(dict(app.config)).test_client()
    persisted = reopened.get(api).json
    assert persisted['layout'] == saved['layout'] and persisted['revision'] == saved['revision']
    assert reopened.get('/editor_offset_visual_v2/' + created['job_id']).status_code == 200
    preflight = client.post(api + '/preflight', json={'dpi': 36})
    assert preflight.status_code == 201, preflight.json
    png = client.post(api + '/preview', json={'dpi': 36, 'expected_revision': saved['revision']})
    assert png.status_code == 200, png.json
    size = Image.open(io.BytesIO(png.data)).size
    assert size == (992, 709), size
    pdf = client.post(api + '/pdf-final', json={'dpi': 36, 'expected_revision': saved['revision']})
    assert pdf.status_code == 200, pdf.json
    with fitz.open(stream=pdf.data, filetype='pdf') as document:
        assert len(document) == 1
        assert abs(document[0].rect.width - 700*72/25.4) < .01
        assert abs(document[0].rect.height - 500*72/25.4) < .01
        assert document[0].get_text().count('PREVIEW-V2') == 2
        assert not document[0].get_images(full=True)
    files = {p: p.read_bytes() for p in Path(directory).rglob('*') if p.is_file()}
    stale = client.put(api + '/layout', json={'layout': layout, 'base_revision': 0})
    assert stale.status_code == 409
    assert client.post(api + '/pdf-final', json={'expected_revision': 1}).status_code == 409
    assert files == {p: p.read_bytes() for p in Path(directory).rglob('*') if p.is_file()}
    assert client.get(api).json == persisted
    assert hashlib.sha256(source.read_bytes()).hexdigest() == digest
    assert not list(Path(directory).rglob('*.tmp'))
assert not [name for name, module in sys.modules.items() if other_product(getattr(module, '__file__', None))]
print('Exclusive V2: imports, upload, Repeat, revision, reload, preflight, PNG and vector PDF accepted')
'''
    environment = dict(os.environ, EDITOR_OFFSET_V2_DEV_TOOLS_ENABLED="0")
    result = subprocess.run([sys.executable, "-c", script], cwd=REPO_ROOT, env=environment,
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
