"""PhotoGuard's released img2img encoder PGD, with bounded-memory iterates."""
from pathlib import Path
import subprocess
import time

ROOT=Path(__file__).resolve().parents[3]
COMMIT='686bea75c786cb46c88fc396a0cd0ee3d7d28c2e'

def protect(clean_path,mask_path,output_path,config=None,progress=None,cancel=None):
    import numpy as np
    import torch
    from PIL import Image
    from diffusers import AutoencoderKL
    from diffusers.models.attention_processor import AttnProcessor2_0
    from .defenders import check_cancel,resolve_model,MLUnavailable
    config=dict(config or {})
    source=ROOT/'third_party/PhotoGuard'
    if subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()!=COMMIT:
        raise MLUnavailable('PhotoGuard checkout differs from the audited source.')
    seed=int(config.get('seed',42));torch.manual_seed(seed);torch.cuda.manual_seed_all(seed)
    vae=AutoencoderKL.from_pretrained(str(resolve_model(config)/'vae'),torch_dtype=torch.float16,variant='fp16',local_files_only=True,use_safetensors=True).to('cuda')
    vae.requires_grad_(False)
    vae.set_attn_processor(AttnProcessor2_0())
    vae.enable_gradient_checkpointing();vae.train()
    a=np.asarray(Image.open(clean_path).convert('RGB')).copy()
    if a.shape!=(512,512,3):raise ValueError('Research reference must be 512px RGB.')
    original=torch.from_numpy(a.transpose(2,0,1)).unsqueeze(0).float()/127.5-1
    original=original.half().cuda()
    eps=.06;step=.02;iterations=1000
    # Match source CPU random initialization and normalized [-1,1] units.
    adv=original.detach().clone()+(torch.rand(original.shape)*2*eps-eps).cuda()
    started=time.perf_counter();loss_first=None;loss_last=None
    torch.cuda.reset_peak_memory_stats()
    with torch.enable_grad(),torch.autocast('cuda'):
        for index in range(iterations):
            check_cancel(cancel)
            # PGD needs only the current image derivative, not iterate-history
            # derivatives. Detachment prevents unbounded graph accumulation.
            adv=adv.detach().requires_grad_(True)
            loss=vae.encode(adv).latent_dist.mean.norm()
            loss_last=float(loss.detach());loss_first=loss_last if loss_first is None else loss_first
            gradient,=torch.autograd.grad(loss,adv)
            actual_step=step-(step-step/100)/iterations*index
            adv=(adv-gradient.detach().sign()*actual_step).detach()
            adv=torch.minimum(torch.maximum(adv,original-eps),original+eps).clamp(-1,1)
            if progress and (index%25==0 or index==iterations-1):progress(index+1,iterations,'PhotoGuard encoder optimization')
    pixels=((adv[0]/2+.5).clamp(0,1)*255).byte().permute(1,2,0).cpu().numpy()
    Path(output_path).parent.mkdir(parents=True,exist_ok=True)
    Image.fromarray(pixels).save(output_path)
    result=dict(method='photoguard_encoder',source_commit=COMMIT,iterations=iterations,epsilon_rgb=eps/2,epsilon_normalized=eps,step_normalized=step,seed=seed,loss_initial=loss_first,loss_final=loss_last,objective='L2 norm of VAE posterior mean toward zero latent, released img2img notebook',mask_scope='all source pixels; subsequent inpainting comparison is a transfer evaluation',elapsed_seconds=time.perf_counter()-started,peak_cuda_allocated_bytes=torch.cuda.max_memory_allocated(),adaptations=['existing pinned SD1.5 inpainting VAE snapshot reused','fixed weights','VAE checkpointing and SDPA','detach PGD iterate history; current-pixel gradient unchanged'],effectiveness='not_tested')
    del vae,adv,gradient,original
    torch.cuda.empty_cache()
    return result
