"""Boundary regressions. ML subprocesses are stubbed only for lifecycle tests."""
import io
import json
import shutil
from pathlib import Path
from uuid import uuid4

import pytest
from PIL import Image, ImageDraw
from fastapi.testclient import TestClient

from backend.app import db, worker
from backend.app.main import app
from backend.app.services import jobs


@pytest.fixture
def owned_asset():
    with TestClient(app) as client:
        image = io.BytesIO()
        Image.new('RGB', (512, 512), '#887766').save(image, 'PNG')
        response = client.post('/api/v1/assets', files={'file': ('test.png', image.getvalue(), 'image/png')})
        assert response.status_code == 201
        asset = response.json()
        mask = Image.new('L', (512, 512), 0)
        ImageDraw.Draw(mask).rectangle((100, 100, 300, 300), fill=255)
        mask_bytes = io.BytesIO()
        mask.save(mask_bytes, 'PNG')
        response = client.put(f'/api/v1/assets/{asset["id"]}/mask', files={'file': ('mask.png', mask_bytes.getvalue(), 'image/png')})
        assert response.status_code == 200
        asset['mask_id'] = response.json()['mask_id']
        asset['owner'] = db.one('SELECT owner FROM assets WHERE id=?', (asset['id'],))['owner']
        yield client, asset
        db.execute("UPDATE jobs SET state='cancelled' WHERE asset_id=? AND state IN ('queued','running')", (asset['id'],))
        client.delete('/api/v1/assets/' + asset['id'])


def enqueue_claimed(asset, **overrides):
    config = dict(mask_id=asset['mask_id'], epsilon=4/255, profile='smoke', seed=42)
    config.update(overrides)
    job_id = jobs.enqueue(asset['owner'], asset['id'], 'protect', config)
    claimed = jobs.claim()
    assert claimed['id'] == job_id
    return claimed


def test_worker_records_missing_mask_instead_of_crashing(owned_asset):
    _, asset = owned_asset
    job = enqueue_claimed(asset, mask_id=str(uuid4()))
    worker.process_job(job)
    stored = db.one('SELECT * FROM jobs WHERE id=?', (job['id'],))
    assert stored['state'] == 'failed'
    assert stored['error_code']
    assert stored['error_message']
    assert str(worker.DATA) not in stored['error_message']


def test_claim_does_not_start_previously_cancel_requested_job(owned_asset):
    _, asset = owned_asset
    job_id = jobs.enqueue(asset['owner'], asset['id'], 'protect', dict(mask_id=asset['mask_id']))
    db.execute('UPDATE jobs SET cancel_requested=1 WHERE id=?', (job_id,))
    assert jobs.claim() is None
    assert db.one('SELECT state FROM jobs WHERE id=?', (job_id,))['state'] == 'cancelled'


def test_delete_cannot_race_a_queued_job_claim(owned_asset, monkeypatch):
    client, asset = owned_asset
    jobs.enqueue(asset['owner'], asset['id'], 'protect', dict(mask_id=asset['mask_id']))
    claims = []
    real_rmtree = shutil.rmtree

    def interleaved_rmtree(path, *args, **kwargs):
        if asset['id'] in path.parts:
            claims.append(jobs.claim())
        return real_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(shutil, 'rmtree', interleaved_rmtree)
    response = client.delete('/api/v1/assets/' + asset['id'])
    assert response.status_code == 200
    assert claims, 'The simulated worker must run during the actual file-deletion phase.'
    assert all(claim is None for claim in claims)


def test_cancel_during_quality_measurement_cannot_succeed(owned_asset, monkeypatch):
    _, asset = owned_asset
    job = enqueue_claimed(asset)

    class CompletedMLProcess:
        def __init__(self, args, **kwargs):
            request = json.loads(Path(args[-1]).read_text())
            Image.open(request['clean_path']).save(request['output_path'])
            Path(request['result_path']).write_text(json.dumps(dict(ok=True, output={'test_fixture': True})))

        def poll(self):
            return 0

    def cancel_during_measurement(*args):
        db.execute('UPDATE jobs SET cancel_requested=1 WHERE id=?', (job['id'],))
        return dict(gate='passed', psnr_db=45.0, ssim=0.999)

    monkeypatch.setattr(worker.subprocess, 'Popen', CompletedMLProcess)
    monkeypatch.setattr(worker, 'measure', cancel_during_measurement)
    worker.process_job(job)
    stored = db.one('SELECT * FROM jobs WHERE id=?', (job['id'],))
    assert stored['state'] == 'cancelled'
    assert not stored['output'], 'A cancellation must not publish a protection result.'


def test_invalid_content_length_returns_controlled_error(owned_asset):
    client, _ = owned_asset
    response = client.post('/api/v1/assets', content=b'bad', headers={'content-length': 'not-a-number'})
    assert response.status_code in (400, 413)
    assert response.json()['error']['code']


def test_multi_seed_review_keeps_uncertain_pairs_inconclusive(owned_asset):
    client, asset = owned_asset
    experiment_id = str(uuid4())
    db.execute('INSERT INTO experiments VALUES(?,?,?,?,?,?,?)', (experiment_id, asset['owner'], asset['id'], '{}', json.dumps([{'seed': 11}, {'seed': 22}, {'seed': 33}]), None, 'inconclusive'))
    usable = dict(requested_edit_completed='yes', realism=5, retained_subject_fidelity=5)
    failed = usable | dict(requested_edit_completed='no')
    uncertain = usable | dict(requested_edit_completed='uncertain')
    pairs = [dict(seed=11, clean=usable, protected=failed), dict(seed=22, clean=usable, protected=usable), dict(seed=33, clean=usable, protected=uncertain)]
    response = client.put(f'/api/v1/experiments/{experiment_id}/review', json={'pairs': pairs})
    assert response.status_code == 200
    result = response.json()
    assert result['effectiveness'] == 'inconclusive'
    assert result['review']['disrupted_pairs'] == 1
    assert result['review']['eligible_pairs'] == 3
    assert client.put(f'/api/v1/experiments/{experiment_id}/review', json={'pairs': pairs[:2]}).status_code == 422
    duplicate = [pairs[0], pairs[0], pairs[2]]
    assert client.put(f'/api/v1/experiments/{experiment_id}/review', json={'pairs': duplicate}).status_code == 422


def test_failed_clean_edits_and_filtered_outputs_never_count_as_success(owned_asset):
    client, asset = owned_asset
    experiment_id = str(uuid4())
    db.execute('INSERT INTO experiments VALUES(?,?,?,?,?,?,?)', (experiment_id, asset['owner'], asset['id'], '{}', json.dumps([dict(seed=11)]), None, 'inconclusive'))
    failed = dict(requested_edit_completed='no', realism=5, retained_subject_fidelity=5)
    body = dict(pairs=[dict(seed=11, clean=failed, protected=failed)])
    result = client.put(f'/api/v1/experiments/{experiment_id}/review', json=body).json()
    assert result['effectiveness'] == 'inconclusive'
    assert result['review']['eligible_pairs'] == 0
    db.execute('UPDATE experiments SET pairs=? WHERE id=?', (json.dumps([dict(seed=11, safety_filtered=True)]), experiment_id))
    response = client.put(f'/api/v1/experiments/{experiment_id}/review', json=body)
    assert response.status_code == 409
    assert response.json()['error']['code'] == 'safety_filtered'
