"""Durable DB outbox -> Redis notification -> locked worker. One mock artifact per job."""
import os
import time
import logging
from datetime import timedelta, datetime, timezone
from redis import Redis
from sqlalchemy import select
from .db import Session, Record, User, now
from .main import validate_scene, owned, audit
from .adapters import gpu
from . import storage

log = logging.getLogger('gsn.worker')

def process(job_id):
    with Session() as db:
        job = db.scalar(select(Record).where(Record.id == job_id, Record.kind == 'job').with_for_update())
        if not job or job.data['status'] in ('succeeded', 'failed'):
            return
        if job.data['status'] == 'running':
            lease = datetime.fromisoformat(job.data['lease_until'])
            if lease > now():
                return
        attempts = job.data['attempts'] + 1
        job.data = {**job.data, 'status': 'running', 'attempts': attempts,
                    'lease_until': (now() + timedelta(minutes=5)).isoformat()}
        db.commit()
        try:
            if attempts > 3:
                raise RuntimeError('Retry limit reached')
            user = db.get(User, job.data['actor_id'])
            if not user or user.tenant_id != job.tenant_id:
                raise RuntimeError('Job owner missing')
            scene = owned(db, user, job.data['scene_id'], 'scene')
            validate_scene(db, user, scene.data)
            data, content_type = gpu().render(scene.data)
            # Recheck immediately before making a result available.
            db.expire_all()
            validate_scene(db, user, scene.data)
            key = f'{job.tenant_id}/renders/{job.id}/simulation.json'
            storage.put(key, data, content_type)
            asset = Record(tenant_id=job.tenant_id, kind='asset', data={
                'key': key, 'content_type': content_type, 'bytes': len(data), 'simulation': True})
            db.add(asset)
            db.flush()
            job.data = {**job.data, 'status': 'succeeded', 'output_asset_id': asset.id,
                        'completed_at': now().isoformat(), 'actual_cost_usd': 0 if job.data['mode'] == 'mock' else None}
            audit(db, user, 'render.succeeded', job.id)
        except Exception:
            log.exception('Render failed: %s', job.id)
            job.data = {**job.data, 'status': 'failed', 'error': 'Render failed; inspect worker logs'}
            db.add(Record(tenant_id=job.tenant_id, kind='audit', data={
                'actor_id': job.data['actor_id'], 'action': 'render.failed', 'target_id': job.id}))
        db.commit()

def dispatch(redis):
    with Session() as db:
        jobs = db.scalars(select(Record).where(Record.kind == 'job'))
        for job in jobs:
            if job.data['status'] == 'queued' or (job.data['status'] == 'running' and
                datetime.fromisoformat(job.data['lease_until']) < now()):
                # Expiring notification marker bounds queue duplicates without losing DB work.
                if redis.set(f'notified:{job.id}', '1', nx=True, ex=15):
                    redis.rpush('gsn:renders', job.id)

def main():
    logging.basicConfig(level=logging.INFO)
    redis = Redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379/0'), decode_responses=True)
    while True:
        try:
            dispatch(redis)
            item = redis.blpop('gsn:renders', timeout=2)
            if item:
                process(item[1])
        except Exception:
            log.exception('Worker loop failed; retrying')
            time.sleep(3)

if __name__ == '__main__':
    main()
