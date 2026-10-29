"""Paper-derived DCT-Shield base profile; not an official implementation.

Continuous perturbations are applied AFTER integer coefficient quantization.
There is intentionally no RGB epsilon projection: it would change the method.
JPEG implementation choices absent from the paper are disclosed in provenance.
"""
from pathlib import Path
import math
import time

LUMA = [16,11,10,16,24,40,51,61,12,12,14,19,26,58,60,55,14,13,16,24,40,57,69,56,14,17,22,29,51,87,80,62,18,22,37,56,68,109,103,77,24,35,55,64,81,104,113,92,49,64,78,87,103,121,120,101,72,92,95,98,112,100,103,99]
CHROMA = [17,18,24,47,99,99,99,99,18,21,26,66,99,99,99,99,24,26,56,99,99,99,99,99,47,66,99,99,99,99,99,99]+[99]*32

class CoefficientJPEG:
    """Differentiable 4:2:0 JPEG decode with explicit quantized coefficient API."""
    def __init__(self,quality=.95,device='cpu'):
        import torch
        if not 0<quality<=1:raise ValueError('JPEG quality must be in (0, 1].')
        self.quality=quality
        u=torch.arange(8,device=device,dtype=torch.float32)[:,None]
        x=torch.arange(8,device=device,dtype=torch.float32)[None,:]
        self.basis=torch.cos((2*x+1)*u*math.pi/16)*.5
        self.basis[0]/=math.sqrt(2)
        q=quality*100
        scale=5000/q if q<50 else 200-2*q
        self.tables=[torch.floor((torch.tensor(v,device=device).float().reshape(8,8)*scale+50)/100).clamp(1,255) for v in (LUMA,CHROMA,CHROMA)]

    def transform(self,plane):
        # B,1,H,W -> B,1,H/8,W/8,8,8
        blocks=plane.unfold(2,8,8).unfold(3,8,8)
        return self.basis@blocks@self.basis.T

    def inverse(self,coefficients):
        blocks=self.basis.T@coefficients@self.basis
        b,c,h,w,_,_=blocks.shape
        return blocks.permute(0,1,2,4,3,5).reshape(b,c,h*8,w*8)

    def encode(self,rgb):
        import torch
        import torch.nn.functional as F
        if rgb.ndim!=4 or rgb.shape[1]!=3 or rgb.shape[2]%16 or rgb.shape[3]%16:
            raise ValueError('RGB tensor dimensions must be multiples of 16.')
        r,g,b=(rgb[:,i:i+1]*255 for i in range(3))
        planes=[.299*r+.587*g+.114*b,-.168736*r-.331264*g+.5*b+128,.5*r-.418688*g-.081312*b+128]
        planes=[planes[0]]+[F.avg_pool2d(p,2,2) for p in planes[1:]]
        return tuple(torch.round(self.transform(p-128)/q).detach() for p,q in zip(planes,self.tables))

    def decode(self,coefficients):
        import torch
        import torch.nn.functional as F
        planes=[self.inverse(c*q)+128 for c,q in zip(coefficients,self.tables)]
        y=planes[0];cb,cr=[F.interpolate(p,scale_factor=2,mode='nearest')-128 for p in planes[1:]]
        return torch.cat([y+1.402*cr,y-.344136*cb-.714136*cr,y+1.772*cb],dim=1).div(255).clamp(0,1)

def protect(clean_path,output_path,steps=1000,quality=.95,coefficient_epsilon=1.,progress=None,cancel=None):
    import numpy as np
    import torch
    from PIL import Image
    from diffusers import AutoencoderKL
    from diffusers.models.attention_processor import AttnProcessor2_0
    from .defenders import resolve_model,check_cancel,model_provenance
    if not 1<=steps<=1000 or not 0<coefficient_epsilon<=2:raise ValueError('Invalid research parameters.')
    a=np.asarray(Image.open(clean_path).convert('RGB')).copy()
    if a.shape!=(512,512,3):raise ValueError('Base profile expects 512px RGB.')
    original=torch.from_numpy(a.transpose(2,0,1)).unsqueeze(0).float().cuda()/255
    jpeg=CoefficientJPEG(quality,'cuda');base=jpeg.encode(original)
    delta=tuple(torch.zeros_like(c) for c in base)
    vae=AutoencoderKL.from_pretrained(str(resolve_model({})/'vae'),torch_dtype=torch.float16,variant='fp16',local_files_only=True,use_safetensors=True).cuda()
    vae.requires_grad_(False);vae.set_attn_processor(AttnProcessor2_0());vae.enable_gradient_checkpointing();vae.train()
    history=[];started=time.perf_counter();torch.cuda.reset_peak_memory_stats()
    for step in range(steps):
        check_cancel(cancel)
        delta=tuple(d.detach().requires_grad_(True) for d in delta)
        decoded=jpeg.decode(tuple(c+d for c,d in zip(base,delta)))
        with torch.autocast('cuda'):
            loss=vae.encode(decoded*2-1).latent_dist.mean.norm()
        gradients=torch.autograd.grad(loss,delta)
        if not all(torch.isfinite(g).all() for g in gradients):raise RuntimeError('Non-finite DCT gradients.')
        delta=tuple((d.detach()-.1*g.sign()).clamp(-coefficient_epsilon,coefficient_epsilon) for d,g in zip(delta,gradients))
        if step%25==0 or step==steps-1:
            item=dict(completed=step+1,total=steps,objective=float(loss.detach()));history.append(item)
            if progress:progress(item)
    with torch.no_grad():
        decoded=jpeg.decode(tuple(c+d for c,d in zip(base,delta)))
        pixels=(decoded[0]*255).round().byte().permute(1,2,0).cpu().numpy()
    Path(output_path).parent.mkdir(parents=True,exist_ok=True);Image.fromarray(pixels).save(output_path)
    result=dict(method='dct_shield_base_paper_reimplementation',paper='https://arxiv.org/abs/2504.17894v2',model=model_provenance({}),official_code_available=False,steps=steps,quality=quality,coefficient_epsilon=coefficient_epsilon,coefficient_step=.1,coefficient_max_delta=max(float(d.abs().max()) for d in delta),rgb_budget=None,elapsed_seconds=time.perf_counter()-started,peak_cuda_allocated_bytes=torch.cuda.max_memory_allocated(),history=history,effectiveness='not_tested',scope='base all-channel unmasked profile, not mask-based or Y-only variants',assumptions=['standard IJG integer-scaled luminance/chrominance tables','4:2:0 average downsampling and nearest upsampling','zero coefficient-delta initialization','posterior mean chosen for VAE encoding','existing pinned SD1.5 inpainting VAE reused','continuous post-quantization deltas; no subsequent rounding of perturbed coefficients','PNG export; real JPEG re-encoding is a separate robustness test'])
    del vae,delta,decoded,original,gradients
    torch.cuda.empty_cache()
    return result
