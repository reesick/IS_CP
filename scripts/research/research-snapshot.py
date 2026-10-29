"""Read-only primary-service availability/metadata snapshot; never runs repo code."""
import json
from pathlib import Path
import subprocess
import httpx

ROOT=Path(__file__).resolve().parents[2]
repos=['MadryLab/photoguard','choi403/DiffusionGuard','ozdentarikcan/DiffVax','ChanhuiLee1111/Universal-Immunization','LinghuiiShen/DeContext','whulizheng/Anti-Diffusion','multimodal-ai-lab/VETO','VinAIResearch/Anti-DreamBooth']
out=[]
with httpx.Client(timeout=30,follow_redirects=True,headers={'User-Agent':'ImageShield-local-research-audit'}) as client:
    for repo in repos:
        response=client.get('https://api.github.com/repos/'+repo)
        entry=dict(repo=repo,http_status=response.status_code)
        if response.status_code==200:
            data=response.json()
            entry.update(url=data['html_url'],stars=data['stargazers_count'],forks=data['forks_count'],pushed_at=data['pushed_at'],default_branch=data['default_branch'],license=(data.get('license') or {}).get('spdx_id'),archived=data['archived'])
        out.append(entry)
    models=[]
    for repo in ['laion/CLIP-ViT-B-32-laion2B-s34B-b79K','black-forest-labs/FLUX.1-Kontext-dev','black-forest-labs/FLUX.2-klein-4B']:
        response=client.get('https://huggingface.co/api/models/'+repo,params={'blobs':'true'})
        entry=dict(repo=repo,http_status=response.status_code)
        if response.status_code==200:
            data=response.json()
            entry.update(revision=data.get('sha'),gated=data.get('gated'),files=[dict(name=f['rfilename'],size=f.get('size'),lfs=f.get('lfs')) for f in data.get('siblings',[])])
        models.append(entry)
    result=dict(audit_date='2026-10-28',repository_observations=out,model_observations=models,note='Stars are current API observations and are not efficacy evidence. No source image uploaded.')
    destination=ROOT/'docs/research/PRIMARY_SERVICE_SNAPSHOT.json'
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(dict(repositories=out,models=[dict(repo=m['repo'],status=m['http_status'],gated=m.get('gated'),weights=[dict(name=f['name'],bytes=f.get('size')) for f in m.get('files',[]) if f['name'].endswith('.safetensors')]) for m in models]),indent=2))
