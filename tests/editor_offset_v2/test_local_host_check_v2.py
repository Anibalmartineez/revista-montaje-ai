"""A shared server or redirect must not pass the exclusive-host check."""
import importlib.util
import io
import json
from pathlib import Path
import sys
from urllib.error import HTTPError

import pytest


path = Path(__file__).resolve().parents[2] / ".agents/skills/editor-offset-local-qa/scripts/check_flask.py"
spec = importlib.util.spec_from_file_location("v2_local_host_check", path)
checker = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = checker
spec.loader.exec_module(checker)


@pytest.mark.parametrize("identity,accepted", [
    ({"application": "editor-offset-v2", "hosting": "exclusive", "layout_schema_version": 2}, True),
    ({"application": "editor-offset-v2", "hosting": "shared", "layout_schema_version": 2}, False),
    ({"application": "another-app"}, False),
])
def test_checker_requires_exclusive_identity(monkeypatch, identity, accepted):
    class Response(io.BytesIO):
        def getcode(self):
            return 200
    class Opener:
        def open(self, request, timeout):
            return Response(json.dumps(identity).encode())
    monkeypatch.setattr(checker.urllib.request, "build_opener", lambda *args: Opener())
    assert checker.check_url(checker.V2_HEALTH_URL, 1).ok is accepted


def test_redirect_is_not_exclusive_identity(monkeypatch):
    class Opener:
        def open(self, request, timeout):
            raise HTTPError(request.full_url, 302, "FOUND", {}, None)
    monkeypatch.setattr(checker.urllib.request, "build_opener", lambda *args: Opener())
    assert not checker.check_url(checker.V2_HEALTH_URL, 1).ok
    assert checker.check_url(checker.ROOT_URL, 1).ok
    assert checker.V2_HEALTH_URL not in checker.URLS_BY_TARGET["both"]
