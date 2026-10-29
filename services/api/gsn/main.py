import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import jwt
from pwdlib import PasswordHash
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError
from fastapi import FastAPI, Depends, HTTPException, Request, Response, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from .db import Session, Base, engine, Tenant, User, SessionToken, Record, get_db, now
from .schemas import Credentials, Project, Consent, Profile, Scene, Render, AgentTask
from . import storage
from .adapters import ROLES, hermes

SECRET = os.environ.get('AUTH_SECRET', '')
if len(SECRET) < 32:
    raise RuntimeError('Set AUTH_SECRET to at least 32 random characters')
COOKIE_SECURE = os.getenv('COOKIE_SECURE', 'true').lower() == 'true'
passwords = PasswordHash.recommended()
app = FastAPI(title='GSN AI Video Studio', version='0.1.0')
app.add_middleware(CORSMiddleware, allow_origins=[os.getenv('WEB_ORIGIN', 'http://localhost:3000')],
                   allow_credentials=True, allow_methods=['GET', 'POST'], allow_headers=['Content-Type'])

@app.middleware('http')
async def browser_origin(request: Request, call_next):
    # SameSite cookies plus explicit Origin validation for browser mutations.
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        origin = request.headers.get('origin')
        if origin and origin != os.getenv('WEB_ORIGIN', 'http://localhost:3000'):
            from fastapi.responses import JSONResponse
            return JSONResponse({'detail': 'Origin rejected'}, status_code=403)
    return await call_next(request)

def audit(db, user, action, target):
    db.add(Record(tenant_id=user.tenant_id, kind='audit', data={
        'actor_id': user.id, 'action': action, 'target_id': target}))

def current(request: Request, db=Depends(get_db)):
    try:
        claims = jwt.decode(request.cookies.get('gsn_session', ''), SECRET,
                            algorithms=['HS256'], issuer='gsn', audience='gsn-dashboard')
        session = db.get(SessionToken, claims['sid'])
        if not session or session.user_id != claims['sub']:
            raise ValueError()
        expiry = session.expires_at.replace(tzinfo=timezone.utc)
        user = db.get(User, session.user_id)
        if expiry <= now() or not user:
            raise ValueError()
        return user
    except (jwt.InvalidTokenError, ValueError, KeyError):
        raise HTTPException(401, 'Sign in required')

def owned(db, user, rid, kind):
    result = db.scalar(select(Record).where(Record.id == rid, Record.tenant_id == user.tenant_id,
                                          Record.kind == kind))
    if not result:
        raise HTTPException(404, 'Record not found')
    return result

def output(record):
    return {'id': record.id, 'kind': record.kind, 'created_at': record.created_at, **record.data}

def create(db, user, kind, data):
    row = Record(id=str(uuid4()), tenant_id=user.tenant_id, kind=kind, data=data)
    db.add(row)
    audit(db, user, f'{kind}.created', row.id)
    db.commit()
    return output(row)

def check_consent(db, user, consent_id, scope, commercial=False):
    c = owned(db, user, consent_id, 'consent')
    try:
        expiry = datetime.fromisoformat(c.data['expires_at'].replace('Z', '+00:00'))
        valid = expiry.tzinfo is not None and expiry > now()
    except (ValueError, TypeError):
        valid = False
    if c.data.get('revoked') or c.data['scope'] != scope or not valid:
        raise HTTPException(409, 'Consent is expired, revoked or has the wrong scope')
    if commercial and not c.data['commercial_use']:
        raise HTTPException(409, 'Commercial use has not been authorized')
    return c

def validate_scene(db, user, data):
    owned(db, user, data['project_id'], 'project')
    for field, kind, scope in [('character_id', 'character', 'appearance'), ('voice_id', 'voice', 'voice')]:
        if data.get(field):
            p = owned(db, user, data[field], kind)
            check_consent(db, user, p.data['consent_id'], scope, data['commercial'])

@app.get('/health')
def health():
    return {'service': 'api', 'render_mode': os.getenv('RENDER_MODE', 'mock'),
            'hermes_mode': os.getenv('HERMES_MODE', 'mock')}

@app.post('/auth/register', status_code=201)
def register(body: Credentials, db=Depends(get_db)):
    tenant = Tenant(name=body.workspace)
    db.add(tenant)
    db.flush()
    user = User(tenant_id=tenant.id, email=body.email.lower(), password_hash=passwords.hash(body.password))
    db.add(user)
    try:
        db.flush()
        audit(db, user, 'user.registered', user.id)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Account cannot be created')
    return {'id': user.id, 'workspace': tenant.name}

@app.post('/auth/login')
def login(body: Credentials, response: Response, db=Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    # Verify a dummy hash on unknown accounts to avoid a cheap timing shortcut.
    valid = passwords.verify(body.password, user.password_hash if user else DUMMY_HASH)
    if not user or not valid:
        raise HTTPException(401, 'Invalid credentials')
    session = SessionToken(user_id=user.id, expires_at=now() + timedelta(hours=8))
    db.add(session)
    db.flush()
    token = jwt.encode({'sub': user.id, 'sid': session.id, 'iss': 'gsn', 'aud': 'gsn-dashboard',
                        'exp': session.expires_at}, SECRET, algorithm='HS256')
    audit(db, user, 'user.login', user.id)
    db.commit()
    response.set_cookie('gsn_session', token, httponly=True, secure=COOKIE_SECURE,
                        samesite='strict', max_age=28800)
    return {'email': user.email}

DUMMY_HASH = passwords.hash('dummy-account-password-unguessable')

@app.post('/auth/logout')
def logout(request: Request, response: Response, user=Depends(current), db=Depends(get_db)):
    claims = jwt.decode(request.cookies['gsn_session'], SECRET, algorithms=['HS256'],
                        issuer='gsn', audience='gsn-dashboard')
    db.execute(delete(SessionToken).where(SessionToken.id == claims['sid']))
    audit(db, user, 'user.logout', user.id)
    db.commit()
    response.delete_cookie('gsn_session')
    return {'ok': True}

@app.get('/auth/me')
def me(user=Depends(current)):
    return {'id': user.id, 'email': user.email, 'tenant_id': user.tenant_id}

KINDS = {'projects': 'project', 'scenes': 'scene', 'characters': 'character', 'voices': 'voice',
         'consents': 'consent', 'jobs': 'job', 'audit': 'audit', 'assets': 'asset', 'agent-tasks': 'agent_task'}

@app.get('/records/{collection}')
def listing(collection: str, user=Depends(current), db=Depends(get_db)):
    if collection not in KINDS:
        raise HTTPException(404)
    return [output(r) for r in db.scalars(select(Record).where(Record.tenant_id == user.tenant_id,
        Record.kind == KINDS[collection]).order_by(Record.created_at.desc()).limit(200))]

@app.post('/projects', status_code=201)
def project(body: Project, user=Depends(current), db=Depends(get_db)):
    return create(db, user, 'project', body.model_dump())

@app.post('/assets', status_code=201)
def upload(file: UploadFile = File(...), user=Depends(current), db=Depends(get_db)):
    if file.content_type not in {'image/jpeg', 'image/png', 'audio/wav', 'audio/mpeg', 'application/pdf'}:
        raise HTTPException(415, 'Use JPEG, PNG, WAV, MP3 or PDF')
    data = file.file.read(20 * 1024 * 1024 + 1)
    if not data or len(data) > 20 * 1024 * 1024:
        raise HTTPException(413, 'File must be between 1 byte and 20 MB')
    key = f'{user.tenant_id}/references/{uuid4()}'
    storage.put(key, data, file.content_type)
    return create(db, user, 'asset', {'key': key, 'content_type': file.content_type, 'bytes': len(data)})

@app.get('/assets/{asset_id}/content')
def download(asset_id: str, user=Depends(current), db=Depends(get_db)):
    a = owned(db, user, asset_id, 'asset')
    # Attachment prevents uploaded content from executing in the dashboard origin.
    return Response(storage.read(a.data['key']), media_type=a.data['content_type'],
                    headers={'Content-Disposition': 'attachment; filename="gsn-asset"',
                             'X-Content-Type-Options': 'nosniff'})

@app.post('/consents', status_code=201)
def consent(body: Consent, user=Depends(current), db=Depends(get_db)):
    owned(db, user, body.evidence_asset_id, 'asset')
    try:
        expiry = datetime.fromisoformat(body.expires_at.replace('Z', '+00:00'))
        if not expiry.tzinfo or expiry <= now():
            raise ValueError()
    except ValueError:
        raise HTTPException(422, 'Use a future date with timezone')
    return create(db, user, 'consent', {**body.model_dump(), 'revoked': False, 'recorded_by': user.id})

@app.post('/consents/{consent_id}/revoke')
def revoke(consent_id: str, user=Depends(current), db=Depends(get_db)):
    c = owned(db, user, consent_id, 'consent')
    c.data = {**c.data, 'revoked': True, 'revoked_at': now().isoformat()}
    audit(db, user, 'consent.revoked', c.id)
    db.commit()
    return output(c)

@app.post('/profiles/{kind}', status_code=201)
def profile(kind: str, body: Profile, user=Depends(current), db=Depends(get_db)):
    if kind not in {'character', 'voice'}:
        raise HTTPException(404)
    c = check_consent(db, user, body.consent_id, 'appearance' if kind == 'character' else 'voice')
    for rid in body.reference_asset_ids:
        asset = owned(db, user, rid, 'asset')
        expected = 'image/' if kind == 'character' else 'audio/'
        if not asset.data['content_type'].startswith(expected):
            raise HTTPException(422, 'Reference type does not match profile')
    return create(db, user, kind, {**body.model_dump(), 'subject': c.data['subject']})

@app.post('/scenes', status_code=201)
def scene(body: Scene, user=Depends(current), db=Depends(get_db)):
    validate_scene(db, user, body.model_dump())
    return create(db, user, 'scene', body.model_dump())

@app.post('/renders', status_code=201)
def render(body: Render, user=Depends(current), db=Depends(get_db)):
    s = owned(db, user, body.scene_id, 'scene')
    validate_scene(db, user, s.data)
    existing = db.scalar(select(Record).where(Record.tenant_id == user.tenant_id,
        Record.kind == 'job', Record.request_key == body.request_key))
    if existing:
        if existing.data['scene_id'] != s.id:
            raise HTTPException(409, 'Request key already used for another scene')
        return output(existing)
    job = Record(id=str(uuid4()), tenant_id=user.tenant_id, kind='job', request_key=body.request_key,
                 data={'scene_id': s.id, 'actor_id': user.id, 'status': 'queued', 'attempts': 0,
                       'mode': os.getenv('RENDER_MODE', 'mock'), 'estimated_cost_usd': None})
    db.add(job)
    audit(db, user, 'render.queued', job.id)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Duplicate submission; refresh jobs')
    # DB is the durable outbox. Dispatcher retries Redis notification if Redis is unavailable.
    return output(job)

@app.get('/agents')
def agents(user=Depends(current)):
    return {'mode': os.getenv('HERMES_MODE', 'mock'), 'roles': ROLES}

@app.post('/agent-tasks', status_code=201)
def agent_task(body: AgentTask, user=Depends(current), db=Depends(get_db)):
    owned(db, user, body.project_id, 'project')
    if body.role not in ROLES:
        raise HTTPException(422, 'Unknown specialist')
    try:
        result = hermes().run(body.role, body.instruction)
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    return create(db, user, 'agent_task', {**body.model_dump(), 'result': result})
