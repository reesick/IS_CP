"""CPU numerical checks of JPEG transforms, budget and gradient, not efficacy."""
import json
from pathlib import Path
import sys
import torch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.app.ml.dct_shield import CoefficientJPEG
j=CoefficientJPEG(.95)
torch.manual_seed(12)
x=torch.rand(2,1,32,48)*255-128
assert torch.allclose(j.inverse(j.transform(x)),x,atol=.0003)
rgb=torch.full((1,3,32,32),.5)
coeff=j.encode(rgb)
assert [c.numel() for c in coeff]==[1024,256,256]
assert all(torch.equal(c,c.round()) for c in coeff)
assert torch.max(abs(j.decode(coeff)-rgb))<1/255
d=tuple(torch.zeros_like(c,requires_grad=True) for c in coeff)
weights=torch.rand_like(rgb)
loss=(j.decode(tuple(c+v for c,v in zip(coeff,d)))*weights).sum()
grads=torch.autograd.grad(loss,d)
assert all(torch.isfinite(g).all() and g.abs().max()>0 for g in grads)
index=(0,0,0,0,0,1);eps=.01
plus=[c.clone() for c in coeff];minus=[c.clone() for c in coeff]
plus[0][index]+=eps;minus[0][index]-=eps
numeric=((j.decode(plus)*weights).sum()-(j.decode(minus)*weights).sum())/(2*eps)
assert torch.allclose(numeric,grads[0][index],atol=.008)
result=dict(passed=True,checks=['orthonormal block DCT inversion','4:2:0 coefficient counts','integer original coefficients','neutral color reconstruction','gradient to all coefficient channels','finite difference coefficient gradient'],purpose='mathematical implementation checks only')
(ROOT/'docs/research/DCT_MATHEMATICAL_CHECKS.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
