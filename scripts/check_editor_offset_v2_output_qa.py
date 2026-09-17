"""Verify gates through controlled invalid requests; creates no jobs/artifacts."""
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError

for route in ('preview','pdf-final'):
    request=Request(f'http://127.0.0.1:5000/api/editor-offset-v2/jobs/invalid/{route}',data=b'{}',headers={'Content-Type':'application/json'})
    try:
        with urlopen(request,timeout=10) as response: payload=json.load(response)
    except HTTPError as error:
        payload=json.loads(error.read())
    code=payload.get('error',{}).get('code')
    if code!='INVALID_JOB_ID':
        raise SystemExit(f'{route}: gate not verified ({code}); restart the registered QA server.')
    print(f'{route}: gate enabled; invalid job rejected without writes')
