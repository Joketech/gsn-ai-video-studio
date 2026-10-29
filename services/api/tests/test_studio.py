from datetime import timedelta
from sqlalchemy import select
from conftest import account
from gsn.db import Record, now
from gsn.worker import process, dispatch
from gsn.adapters import MockHermes, CloudGPUWorker, ROLES

def asset(c, mime='image/png'):
    r = c.post('/assets', files={'file': ('reference', b'test-reference', mime)})
    assert r.status_code == 201
    return r.json()['id']

def consent(c, evidence, scope='appearance', commercial=True):
    r = c.post('/consents', json={'subject': 'Joke Taiwo', 'scope': scope, 'evidence_asset_id': evidence,
        'expires_at': (now()+timedelta(days=30)).isoformat(), 'commercial_use': commercial, 'attestation': True})
    assert r.status_code == 201, r.text
    return r.json()['id']

def scene(c, **extra):
    p = c.post('/projects', json={'name':'GSN launch film'}).json()['id']
    return c.post('/scenes', json={'project_id':p,'script':'Welcome to GSN.', **extra})

def test_auth_and_logout_revokes_session(studio):
    c, _, _ = studio
    assert c.get('/records/projects').status_code == 401
    token = account(c)
    assert c.get('/auth/me').status_code == 200
    c.post('/auth/logout')
    c.cookies.set('gsn_session',token)
    assert c.get('/auth/me').status_code == 401

def test_password_and_origin_validation(studio):
    c, _, _ = studio
    assert c.post('/auth/register', json={'email':'joke@example.test','password':'short'}).status_code == 422
    account(c)
    assert c.post('/projects', json={'name':'Bad'}, headers={'Origin':'https://evil.test'}).status_code == 403
    assert c.post('/auth/login',json={'email':'joke@example.test','password':'wrong-password-long'}).status_code == 401

def test_tenant_isolation_all_references(studio):
    c, _, _ = studio
    token_a = account(c)
    a = asset(c); co = consent(c,a)
    s = scene(c).json(); p = s['project_id']
    account(c,'other@example.test')
    assert c.get('/records/projects').json() == []
    assert c.get('/assets/'+a+'/content').status_code == 404
    assert c.post('/consents/'+co+'/revoke').status_code == 404
    assert c.post('/profiles/character',json={'name':'Foreign','consent_id':co,'reference_asset_ids':[a]}).status_code == 404
    assert c.post('/scenes',json={'project_id':p,'script':'foreign'}).status_code == 404
    assert c.post('/renders',json={'scene_id':s['id'],'request_key':'tenant-test-123'}).status_code == 404
    assert c.post('/agent-tasks',json={'project_id':p,'role':'producer','instruction':'foreign'}).status_code == 404
    c.cookies.set('gsn_session', token_a)
    assert len(c.get('/records/projects').json()) == 1

def test_revoked_consent_blocks_submission_and_worker(studio):
    c, _, blobs = studio
    account(c)
    a = asset(c); co = consent(c,a)
    char = c.post('/profiles/character',json={'name':'Joke','consent_id':co,'reference_asset_ids':[a]}).json()['id']
    s = scene(c,character_id=char).json()['id']
    job = c.post('/renders',json={'scene_id':s,'request_key':'revocation-test'}).json()['id']
    c.post('/consents/'+co+'/revoke')
    assert c.post('/renders',json={'scene_id':s,'request_key':'revocation-test2'}).status_code == 409
    process(job)
    assert c.get('/records/jobs').json()[0]['status'] == 'failed'
    assert not any('/renders/' in k for k in blobs)

def test_commercial_voice_and_scope(studio):
    c, _, _ = studio
    account(c)
    a = asset(c,'audio/wav'); co = consent(c,a,'voice',False)
    assert c.post('/profiles/character',json={'name':'Wrong','consent_id':co,'reference_asset_ids':[a]}).status_code == 409
    v = c.post('/profiles/voice',json={'name':'Joke voice','consent_id':co,'reference_asset_ids':[a]}).json()['id']
    assert scene(c,voice_id=v,commercial=True).status_code == 409
    assert scene(c,voice_id=v).status_code == 201

def test_mock_render_idempotency_and_audit(studio):
    c, _, blobs = studio
    account(c)
    s = scene(c).json()['id']
    body = {'scene_id':s,'request_key':'test-idempotent'}
    first = c.post('/renders',json=body).json()
    assert c.post('/renders',json=body).json()['id'] == first['id']
    process(first['id']); process(first['id'])
    job = c.get('/records/jobs').json()[0]
    assert job['status'] == 'succeeded' and job['attempts'] == 1
    result = c.get('/assets/'+job['output_asset_id']+'/content')
    assert result.status_code == 200 and result.json()['simulation'] is True
    assert len([k for k in blobs if '/renders/' in k]) == 1
    actions = [r['action'] for r in c.get('/records/audit').json()]
    assert 'render.queued' in actions and 'render.succeeded' in actions

def test_outbox_and_worker_storage_failure(studio,monkeypatch):
    c, _, _ = studio
    account(c)
    s = scene(c).json()['id']
    job = c.post('/renders',json={'scene_id':s,'request_key':'storage-failure'}).json()['id']
    class FakeRedis:
        ids=[]
        def set(self,*a,**kw): return True
        def rpush(self,key,value): self.ids.append(value)
    queue = FakeRedis(); dispatch(queue)
    assert job in queue.ids
    from gsn import storage
    def fail(*args): raise RuntimeError('storage down')
    monkeypatch.setattr(storage,'put',fail)
    process(job)
    assert c.get('/records/jobs').json()[0]['status'] == 'failed'

def test_expired_consent_and_input_limits(studio):
    c, _, _ = studio
    account(c)
    a = asset(c)
    assert c.post('/consents',json={'subject':'Joke','scope':'appearance','evidence_asset_id':a,
        'expires_at':'2020-01-01T00:00:00Z','attestation':True}).status_code == 422
    assert c.post('/assets',files={'file':('x',b'abc','text/html')}).status_code == 415
    assert scene(c,seconds=100).status_code == 422

def test_hermes_roles_and_live_gpu_fail_closed(studio):
    c, _, _ = studio
    account(c)
    assert len(ROLES) == 13
    p = c.post('/projects',json={'name':'Agents'}).json()['id']
    for role in ROLES:
        r=c.post('/agent-tasks',json={'project_id':p,'role':role,'instruction':'Prepare plan'})
        assert r.status_code == 201 and r.json()['result']['mode'] == 'mock'
    import pytest
    with pytest.raises(RuntimeError,match='not configured'):
        CloudGPUWorker().render({})

def test_worker_lease_recovery_and_duplicate_delivery(studio):
    c, factory, _ = studio
    account(c)
    s = scene(c).json()['id']
    job = c.post('/renders',json={'scene_id':s,'request_key':'lease-recovery'}).json()['id']
    with factory() as db:
        row = db.get(Record,job)
        row.data = {**row.data, 'status':'running', 'attempts':1,
                    'lease_until':(now()+timedelta(minutes=1)).isoformat()}
        db.commit()
    process(job)
    assert c.get('/records/jobs').json()[0]['attempts'] == 1
    with factory() as db:
        row = db.get(Record,job)
        row.data = {**row.data, 'lease_until':(now()-timedelta(seconds=1)).isoformat()}
        db.commit()
    process(job)
    result = c.get('/records/jobs').json()[0]
    assert result['attempts'] == 2 and result['status'] == 'succeeded'

def test_live_hermes_disabled_and_request_key_conflict(studio, monkeypatch):
    c, _, _ = studio
    account(c)
    s = scene(c).json()
    monkeypatch.setenv('HERMES_MODE','live')
    assert c.post('/agent-tasks',json={'project_id':s['project_id'], 'role':'orchestrator',
        'instruction':'Plan production'}).status_code == 503
    c.post('/renders',json={'scene_id':s['id'],'request_key':'same-key-different-scene'})
    other = scene(c).json()['id']
    assert c.post('/renders',json={'scene_id':other,'request_key':'same-key-different-scene'}).status_code == 409

def test_tampered_session_is_rejected(studio):
    c, _, _ = studio
    token = account(c)
    c.cookies.clear()
    c.cookies.set('gsn_session','tampered.'+token)
    assert c.get('/auth/me').status_code == 401
