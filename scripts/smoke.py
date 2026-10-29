"""Integration test against a running Compose stack. Uses actual HTTP, Redis worker and S3."""
import http.cookiejar
import json
import time
import uuid
import urllib.request

BASE = 'http://localhost:8000'
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

def call(path, data=None):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(BASE+path, body, {'Content-Type':'application/json'})
    with opener.open(req, timeout=15) as response:
        return json.load(response)

creds = {'email':f'smoke-{uuid.uuid4()}@example.test', 'password':'smoke-test-password-12345'}
call('/auth/register', creds)
call('/auth/login', creds)
project = call('/projects', {'name':'Integration smoke test'})
scene = call('/scenes', {'project_id':project['id'], 'script':'Queue pipeline check'})
job = call('/renders', {'scene_id':scene['id'], 'request_key':str(uuid.uuid4())})
for _ in range(60):
    job = next(j for j in call('/records/jobs') if j['id'] == job['id'])
    if job['status'] in ('succeeded','failed'):
        break
    time.sleep(2)
assert job['status'] == 'succeeded', job
report = call('/assets/'+job['output_asset_id']+'/content')
assert report['simulation'] is True
print('PASS: login -> project -> scene -> durable job -> Redis worker -> S3 -> authorized download')
print('This verifies simulation infrastructure, not AI video generation.')
