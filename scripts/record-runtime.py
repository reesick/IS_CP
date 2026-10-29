"""Record observed local smoke evidence; never infers protection effectiveness."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.app.services.metrics import measure

def main():
    evidence_path=ROOT/'data/ml-smoke/evidence.json'
    evidence=json.loads(evidence_path.read_text())
    if evidence.get('actual_pixel_change')!='passed' or evidence.get('two_region_single_mask_semantics')!='passed':
        raise SystemExit('Actual optimization/mask smoke evidence is required.')
    paired=evidence.get('paired_edit',{}).get('pairs',[])
    if not paired:
        raise SystemExit('A completed paired editor run is required.')
    for pair in paired:
        for key in ('edit_clean','edit_protected'):
            if not (ROOT/pair[key]).is_file():
                raise SystemExit('A recorded output file is missing.')
    quality=measure(ROOT/'data/ml-smoke/clean.png',ROOT/'data/ml-smoke/protected.png',evidence['provenance']['epsilon_rgb'])
    summary=dict(purpose=evidence['purpose'],synthetic_input=True,mask_semantics=evidence['two_region_single_mask_semantics'],pixel_change=evidence['actual_pixel_change'],quality=quality,provenance=evidence['provenance'],paired_editor_completed=True,safety_filtered=any(p.get('safety_filtered') for p in paired),effectiveness='not_tested',human_review='pending')
    registry_path=ROOT/'model-registry.json'
    registry=json.loads(registry_path.read_text())
    model=next(m for m in registry['models'] if m['id']=='sd15_inpaint')
    if model['revision']!=summary['provenance']['model_revision'] or not model.get('weights_ready'):
        raise SystemExit('Runtime evidence does not match the downloaded model registry.')
    model.update(ready=True,status='local_runtime_smoke_validated',runtime_smoke=summary)
    defender=next(d for d in registry['defenders'] if d['id']=='diffusionguard')
    defender.update(commit=summary['provenance']['upstream_commit'],status='adapted_single_mask_runtime_smoke_validated',license_status='no_upstream_license_file_found')
    registry['status']='local_runtime_smoke_validated_effectiveness_unreviewed'
    registry['note']='Actual local CUDA optimization and paired editor smoke completed. Quality outcomes are measured separately; no efficacy claim.'
    registry_path.write_text(json.dumps(registry,indent=2),encoding='utf-8')
    (ROOT/'docs/GPU_SMOKE_RESULTS.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':
    main()
