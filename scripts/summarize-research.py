"""Portable measured summary. Never infer efficacy from image differences."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'outputs/research-2026-10-28'
pg=json.loads((out/'paper-baselines/results.json').read_text())
dv=json.loads((out/'diffvax/results.json').read_text())
dct=json.loads((out/'dct-shield/results.json').read_text())
probe=json.loads((out/'contrastive-probe/results-native.json').read_text())
pairs=[]
for key,value in pg.items():
    if key.endswith('_paired'):pairs.extend(value.get('pairs',[]))
for key,value in dct.items():
    if key.startswith('paired_'):pairs.extend(value.get('pairs',[]))
result=dict(audit_date='2026-10-28',scope='actual local runs; no external image inference',photoguard=dict(steps=pg['photoguard']['iterations'],elapsed_seconds=pg['photoguard']['elapsed_seconds'],quality=pg['photoguard_quality']),diffvax=[dict(image=r['image'],batchnorm_mode=r['bn_mode'],quality=r['quality']) for r in dv],dct_shield=dict(steps=dct['steps'],elapsed_seconds=dct['elapsed_seconds'],coefficient_max_delta=dct['coefficient_max_delta'],rgb_budget=dct['rgb_budget'],quality=dct['product_quality_diagnostic']),reduced_refusal_probe=dict(paper_reproduction=False,steps=probe['steps'],elapsed_seconds=probe['elapsed_seconds'],image_size=probe['image_size'],quality=probe['quality'],commercial_refusal_verified=False),local_editor_pairs=len(pairs),generated_edits=2*len(pairs),safety_filtered_pairs=sum(bool(p.get('safety_filtered')) for p in pairs),formal_human_efficacy_rating='not_assigned',frontier_edit_prevention_rate=None,frontier_rate_reason='No exact-target commercial editor study performed; no successful quality-preserving frontier defense established.',visual_observations=['Green-cap edits remain possible across inspected PhotoGuard/DiffVax seeds.','DCT native edits have strong distortion; JPEG85 again yields plausible green-shorts edits.','Source fidelity failed for PhotoGuard, DCT base and the reduced refusal probe.'],limitations=['DCT base implementation and reused VAE are adaptations; no claim that every paper variant is defeated.','MIRAGE-informed probe omits seven encoders and unpublished target image assets.','CaD architecture/math checks are not pretrained-model efficacy.'])
(ROOT/'docs/research/LOCAL_RESEARCH_RESULTS.json').write_text(json.dumps(result,indent=2))
print(json.dumps(dict(pairs=result['local_editor_pairs'],generated_edits=result['generated_edits'],filtered=result['safety_filtered_pairs'],frontier_rate=result['frontier_edit_prevention_rate'])))
