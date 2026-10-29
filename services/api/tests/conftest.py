import os
os.environ.setdefault('AUTH_SECRET', 'test-only-secret-not-for-deployment-123456789')
os.environ.setdefault('DATABASE_URL', 'sqlite://')
os.environ['COOKIE_SECURE'] = 'false'
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from gsn import db, main, worker, storage

@pytest.fixture
def studio(monkeypatch):
    url = os.getenv('TEST_DATABASE_URL', 'sqlite://')
    kwargs = {'connect_args': {'check_same_thread': False}, 'poolclass': StaticPool} if url == 'sqlite://' else {}
    engine = create_engine(url, **kwargs)
    db.Base.metadata.drop_all(engine)
    db.Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    def session():
        with factory() as s:
            yield s
    main.app.dependency_overrides[db.get_db] = session
    monkeypatch.setattr(worker, 'Session', factory)
    blobs = {}
    monkeypatch.setattr(storage, 'put', lambda key, data, content_type: blobs.update({key: data}))
    monkeypatch.setattr(storage, 'read', lambda key: blobs[key])
    with TestClient(main.app) as client:
        yield client, factory, blobs
    main.app.dependency_overrides.clear()
    engine.dispose()

def account(client, email='joke@example.test'):
    body = {'email': email, 'password': 'testing-password-123', 'workspace': 'Joke Taiwo Studio'}
    assert client.post('/auth/register', json=body).status_code == 201
    assert client.post('/auth/login', json=body).status_code == 200
    return client.cookies.get('gsn_session')
