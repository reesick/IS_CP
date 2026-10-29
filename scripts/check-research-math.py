"""CPU mathematical verification; explicitly not model/defense efficacy evidence."""
import json
from pathlib import Path
import sys
import torch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.app.ml.research_objectives import reference_attention_objective,global_local_objective,secant_gradient,project_rgb

torch.manual_seed(7)
q=torch.randn(2,3,7,8,requires_grad=True)
k=torch.randn(2,3,13,8,requires_grad=True)
mask=torch.ones(1,1,7,13,dtype=torch.bool);mask[...,-1]=False
dense=(q@k.transpose(-1,-2)/(8**.5)).masked_fill(~mask,-torch.inf).softmax(-1)
expected=-(1-dense[...,8:12].sum(-1)).square().mean()
actual=reference_attention_objective(q,k,8,12,mask,query_chunk=3)
assert torch.allclose(actual,expected,atol=1e-7)
ga=torch.autograd.grad(actual,(q,k),retain_graph=True)
ge=torch.autograd.grad(expected,(q,k))
assert all(torch.allclose(a,e,atol=1e-7) for a,e in zip(ga,ge))
targets=torch.eye(2)
g=torch.tensor([[1.,0.]])
local=torch.tensor([[1.,0.],[0.,1.],[-1.,0.]])
assert torch.allclose(global_local_objective(g,local,targets,top_k=2),torch.tensor(.625))
g1=torch.tensor([3.,4.]);g2=torch.tensor([1.,2.]);d1=torch.tensor([1.,0.]);d2=torch.tensor([0.,0.])
assert torch.equal(secant_gradient(g1,g2,d1,d2,torch.tensor([2.,0.])),torch.tensor([5.,6.]))
assert torch.equal(secant_gradient(g1,g2,d1,d1,d1),g1)
x=torch.rand(1,3,8,8)
p=project_rgb(x+torch.randn_like(x),x,8/255)
assert (p-x).abs().max()<=8/255+1e-7 and p.min()>=0 and p.max()<=1
result=dict(passed=True,checks=['CaD dense equivalence','CaD query/key gradient equivalence','MIRAGE raw cosine/top-k arithmetic','secant extrapolation','zero-denominator stabilization','RGB projection'],purpose='CPU mathematical checks only; no image-edit protection rate measured')
(ROOT/'docs/research/MATHEMATICAL_CHECKS.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))
