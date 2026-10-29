import io
import json
from PIL import Image, ImageDraw
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app import db
from backend.app.services import jobs

def image_bytes(size=(720,480),mode='RGB'):
    out=io.BytesIO()
    Image.new(mode,size,'#998877').save(out,'PNG')
    return out.getvalue()

@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client

def upload(client):
    response=client.post('/api/v1/assets',files={'file':('image.png',image_bytes(),'image/png')})
    assert response.status_code==201,response.text
    return response.json()

def put_mask(client,asset,rectangle=(80,150,350,350)):
    image=Image.new('L',(512,512),0)
    ImageDraw.Draw(image).rectangle(rectangle,fill=255)
    out=io.BytesIO(); image.save(out,'PNG')
    return client.put(f'/api/v1/assets/{asset["id"]}/mask',files={'file':('mask.png',out.getvalue(),'image/png')})

def test_health_does_not_import_torch(client):
    import sys
    assert client.get('/health').status_code==200
    assert 'torch' not in sys.modules

def test_upload_geometry_private_download_and_cross_session(client):
    asset=upload(client)
    assert asset['geometry']['padding']==[0,85,0,86]
    response=client.get('/api/v1/artifacts/'+asset['preview_artifact_id'])
    assert response.status_code==200
    assert Image.open(io.BytesIO(response.content)).size==(512,512)
    with TestClient(app) as stranger:
        assert stranger.get('/api/v1/artifacts/'+asset['preview_artifact_id']).status_code==404
        assert stranger.delete('/api/v1/assets/'+asset['id']).status_code==404
    assert client.get('/static/../data/session.secret').status_code==404

def test_alpha_preview_and_metadata_stripping(client):
    response=client.post('/api/v1/assets',files={'file':('alpha.png',image_bytes(mode='RGBA'),'image/png')})
    assert response.status_code==201
    assert response.json()['geometry']['alpha_composited']
    raw=client.get('/api/v1/artifacts/'+response.json()['preview_artifact_id']).content
    assert Image.open(io.BytesIO(raw)).getexif()=={}

def test_reject_malformed_unsupported_and_oversized(client):
    assert client.post('/api/v1/assets',files={'file':('fake.png',b'not an image','image/png')}).status_code==422
    out=io.BytesIO();Image.new('RGB',(10,10)).save(out,'GIF')
    assert client.post('/api/v1/assets',files={'file':('fake.png',out.getvalue(),'image/png')}).status_code==415
    assert client.post('/api/v1/assets',content=b'x',headers={'content-length':str(11*1024*1024)}).status_code==413

def test_mask_semantics_padding_and_tiny_regions(client):
    asset=upload(client)
    assert put_mask(client,asset).status_code==200
    assert put_mask(client,asset,(0,0,100,100)).status_code==422
    assert put_mask(client,asset,(100,100,102,102)).status_code==422
    assert put_mask(client,asset,(0,85,511,425)).status_code==422

def test_unknown_origin_and_host(client):
    assert client.post('/api/v1/assets',headers={'origin':'https://evil.example'}).status_code==403
    assert client.get('/health',headers={'host':'evil.example'}).status_code==400

def test_model_unavailable_is_honest(client,monkeypatch):
    monkeypatch.setattr('backend.app.main.capabilities',lambda:dict(ready=False,reasons=['Model files are not installed.']))
    asset=upload(client)
    mask=put_mask(client,asset).json()['mask_id']
    response=client.post(f'/api/v1/assets/{asset["id"]}/protect',json=dict(mask_id=mask))
    assert response.status_code==503
    assert response.json()['error']['code']=='model_unavailable'

def test_transactional_queue_cancel_ownership_and_delete(client,monkeypatch):
    monkeypatch.setattr('backend.app.main.capabilities',lambda:dict(ready=True))
    asset=upload(client);mask=put_mask(client,asset).json()['mask_id']
    url=f'/api/v1/assets/{asset["id"]}/protect'
    ids=[client.post(url,json=dict(mask_id=mask)).json()['id'] for _ in range(3)]
    assert client.post(url,json=dict(mask_id=mask)).status_code==409
    assert client.post('/api/v1/jobs/'+ids[0]+'/cancel').json()['state']=='cancelled'
    claimed=jobs.claim();assert claimed['id']==ids[1]
    assert jobs.claim()['id']==ids[2]
    with TestClient(app) as stranger:
        assert stranger.get('/api/v1/jobs/'+ids[1]).status_code==404
    assert client.delete('/api/v1/assets/'+asset['id']).status_code==409
    db.execute("UPDATE jobs SET state='cancelled' WHERE asset_id=?",(asset['id'],))
    assert client.delete('/api/v1/assets/'+asset['id']).status_code==200
    assert client.get('/api/v1/artifacts/'+asset['preview_artifact_id']).status_code==404

def test_review_filters_uncertain_and_clean_failure(client):
    asset=upload(client)
    owner=db.one('SELECT owner FROM assets WHERE id=?',(asset['id'],))['owner']
    db.execute('INSERT INTO experiments VALUES(?,?,?,?,?,?,?)',('review-test',owner,asset['id'],'{}',json.dumps([dict(seed=42)]),None,'not_tested'))
    score=dict(requested_edit_completed='yes',realism=5,retained_subject_fidelity=5)
    body=dict(pairs=[dict(seed=42,clean=score,protected=score|dict(requested_edit_completed='no'))])
    response=client.put('/api/v1/experiments/review-test/review',json=body)
    assert response.json()['effectiveness']=='observed_disruption'
    body['pairs'][0]['protected']['requested_edit_completed']='uncertain'
    assert client.put('/api/v1/experiments/review-test/review',json=body).json()['effectiveness']=='inconclusive'

def test_quality_metrics_saved_budget(tmp_path):
    from backend.app.services.metrics import measure
    a=tmp_path/'a.png';b=tmp_path/'b.png'
    Image.new('RGB',(32,32),(100,100,100)).save(a)
    Image.new('RGB',(32,32),(101,101,101)).save(b)
    result=measure(a,b,4/255)
    assert result['gate']=='passed'
    Image.new('RGB',(32,32),(200,200,200)).save(b)
    assert measure(a,b,4/255)['gate']=='failed'
