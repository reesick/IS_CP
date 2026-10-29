import json
import subprocess
import time
from ..settings import ROOT, ML_PYTHON

_cache = (0,{})

def capabilities():
    global _cache
    if time.time()-_cache[0]<30:
        return _cache[1]
    result=dict(ready=False,cuda=False,gpu=None,model_ready=False,defender_ready=False,mode='real',reasons=[],setup_command='powershell -ExecutionPolicy Bypass -File scripts/bootstrap.ps1')
    registry_path=ROOT/'model-registry.json'
    registry=json.loads(registry_path.read_text()) if registry_path.exists() else {}
    model=next((m for m in registry.get('models',[]) if m['id']=='sd15_inpaint'),{})
    model_path=ROOT/model.get('snapshot_path',model.get('local_path','models/sd15_inpaint'))
    result['model_ready']=(model_path/'model_index.json').exists() and bool(model.get('revision')) and bool(model.get('weights_ready') or model.get('ready'))
    result['defender_ready']=(ROOT/'third_party/DiffusionGuard/attacks').is_dir()
    if ML_PYTHON.exists():
        code='import torch,json; c=torch.cuda.is_available(); print(json.dumps(dict(cuda=c,gpu=dict(name=torch.cuda.get_device_name(0),free_vram_mb=torch.cuda.mem_get_info()[0]//1048576,total_vram_mb=torch.cuda.mem_get_info()[1]//1048576) if c else None)))'
        try:
            p=subprocess.run([str(ML_PYTHON),'-c',code],capture_output=True,text=True,timeout=25,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            if p.returncode==0:
                result.update(json.loads(p.stdout.strip().splitlines()[-1]))
            else:
                result['reasons'].append('ML dependencies are not installed or could not be imported.')
        except (OSError,subprocess.TimeoutExpired,ValueError):
            result['reasons'].append('ML environment probe did not complete. Run the environment doctor.')
    else:
        result['reasons'].append('The isolated ML environment is not installed.')
    if not result['cuda']:
        result['reasons'].append('CUDA is unavailable in the ML environment.')
    if not result['model_ready']:
        result['reasons'].append('Model files are not installed or their revision is unresolved.')
    if not result['defender_ready']:
        result['reasons'].append('DiffusionGuard source is not installed.')
    result['ready']=result['cuda'] and result['model_ready'] and result['defender_ready']
    result['status']='GPU ready' if result['ready'] else 'Setup required'
    _cache=(time.time(),result)
    return result
