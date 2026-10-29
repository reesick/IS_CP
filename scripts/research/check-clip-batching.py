"""Real tiny CLIP architecture checks; not a protection-effectiveness test."""
import json
from pathlib import Path
import sys
import torch
from transformers import CLIPVisionConfig,CLIPVisionModelWithProjection
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from backend.app.ml.research_objectives import global_local_objective
torch.set_num_threads(1);torch.manual_seed(19)
model=CLIPVisionModelWithProjection(CLIPVisionConfig(hidden_size=32,intermediate_size=64,projection_dim=16,num_hidden_layers=1,num_attention_heads=4,image_size=32,patch_size=16)).eval()
model.requires_grad_(False)
globals=torch.rand(3,3,32,32,requires_grad=True)
patches=torch.rand(48,3,32,32,requires_grad=True)
targets=torch.randn(3,16)
g=model(globals).image_embeds;p=model(patches).image_embeds
losses=[global_local_objective(g[i:i+1],p[i*16:(i+1)*16],targets) for i in range(3)]
isolated,=torch.autograd.grad(losses[0],globals,retain_graph=True)
assert torch.count_nonzero(isolated[1:])==0
batched=torch.autograd.grad(torch.stack(losses).sum(),(globals,patches))
separate_g=[];separate_p=[]
for i in range(3):
    a=globals[i:i+1].detach().requires_grad_(True)
    b=patches[i*16:(i+1)*16].detach().requires_grad_(True)
    loss=global_local_objective(model(a).image_embeds,model(b).image_embeds,targets)
    ga,gb=torch.autograd.grad(loss,(a,b));separate_g.append(ga);separate_p.append(gb)
assert torch.allclose(batched[0],torch.cat(separate_g),atol=1e-7,rtol=1e-4)
assert torch.allclose(batched[1],torch.cat(separate_p),atol=1e-7,rtol=1e-4)
result=dict(passed=True,device='cpu',weights='tiny random real CLIP architecture, not pretrained',checks=['no cross-image gradient','batched vs individual global-input gradients','batched vs individual top-k patch gradients'],purpose='batch execution correctness only, not frontier efficacy')
(ROOT/'docs/research/CLIP_BATCHING_CHECK.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
