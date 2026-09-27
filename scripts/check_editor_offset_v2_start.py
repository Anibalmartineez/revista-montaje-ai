"""Read-only check of the normal V2 profile at the local Flask process."""

import json
import re
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BASE = 'http://127.0.0.1:5000'
JOB = 'invalid'


def request(path):
    req = Request(BASE + path, data=b'{}', headers={'Content-Type': 'application/json'})
    try:
        with urlopen(req, timeout=10) as response:
            return response.status, response.read()
    except HTTPError as error:
        return error.code, error.read()


for route in ('preview', 'pdf-final'):
    status, body = request(f'/api/editor-offset-v2/jobs/{JOB}/{route}')
    code = json.loads(body).get('error', {}).get('code')
    if status != 400 or code != 'INVALID_JOB_ID':
        raise SystemExit(f'{route}: normal gate unavailable ({status}, {code})')

status, body = request(f'/api/editor-offset-v2/jobs/{JOB}/assets/invalid/derived-page')
code = json.loads(body).get('error', {}).get('code')
if status != 404 or code != 'DERIVED_ASSETS_DISABLED':
    raise SystemExit(f'derived-page: expected separate disabled gate ({status}, {code})')

with urlopen(BASE + '/editor_offset_visual_v2', timeout=10) as response:
    shell = response.read().decode('utf-8')
if not re.search(r'"dev_tools_enabled"\s*:\s*false', shell):
    raise SystemExit('V2 dev tools are not confirmed disabled in shell context')
print('V2 normal profile: Preview/PDF enabled, derived assets and dev tools disabled')
