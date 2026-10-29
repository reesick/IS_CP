"""CaD FLUX-Kontext adapter derived from arXiv2610.35566v1 Appendix B.

Requires a separately provisioned modern environment and resolved local weights.
No author code release or frontier-model run has been verified in this project.
The implementation status must never be represented as reproduced efficacy.
"""
from pathlib import Path
import json
import time

ROOT=Path(__file__).resolve().parents[3]

class _PrefixComplete(Exception):
    pass

class JointAttentionCapture:
    """Capture BOTH modalities' normalized Q/K; truncate after selected prefix."""
    def __init__(self,transformer,blocks=10):
        self.transformer=transformer;self.blocks=blocks;self.values={};self.handles=[]
        if len(transformer.transformer_blocks)<blocks:
            raise ValueError('Transformer does not have the requested double-stream prefix.')

    def __enter__(self):
        try:
            for index,block in enumerate(self.transformer.transformer_blocks[:self.blocks]):
                attn=block.attn
                for field in ('norm_q','norm_k','norm_added_q','norm_added_k'):
                    if not hasattr(attn,field):
                        raise ValueError('Unsupported joint-attention structure: '+field)
                    def capture(module,inputs,output,index=index,field=field,heads=attn.heads):
                        if output.ndim!=4:raise ValueError('Expected a four-dimensional normalized Q/K tensor.')
                        if output.shape[1]==heads:
                            self.values[index,field]=output
                        elif output.shape[2]==heads:
                            self.values[index,field]=output.permute(0,2,1,3)
                        else:raise ValueError('Cannot identify attention head axis.')
                    self.handles.append(getattr(attn,field).register_forward_hook(capture))
            def stop(*_):raise _PrefixComplete()
            self.handles.append(self.transformer.transformer_blocks[self.blocks-1].register_forward_hook(stop))
        except Exception:
            self.__exit__(None,None,None)
            raise
        return self

    def __exit__(self,*_):
        for handle in self.handles:handle.remove()
        self.handles=[]

    def objective(self,text_tokens,target_tokens,rotary,apply_rotary):
        import torch
        from .research_objectives import reference_attention_objective
        losses=[]
        for index in range(self.blocks):
            q=torch.cat([self.values[index,'norm_added_q'],self.values[index,'norm_q']],dim=2)
            k=torch.cat([self.values[index,'norm_added_k'],self.values[index,'norm_k']],dim=2)
            q=apply_rotary(q,rotary,sequence_dim=2)
            k=apply_rotary(k,rotary,sequence_dim=2)
            reference_start=text_tokens+target_tokens
            losses.append(reference_attention_objective(q[:,:,text_tokens:reference_start],k,reference_start,k.shape[-2]))
        return torch.stack(losses).mean()

def preflight(model_path=None):
    from importlib.metadata import version,PackageNotFoundError
    path=Path(model_path or ROOT/'models/flux-kontext')
    reasons=[]
    for name,minimum in [('torch',(2,6)),('diffusers',(0,35))]:
        try:
            actual=version(name);parts=tuple(int(p) for p in actual.split('+')[0].split('.')[:2])
            if parts<minimum:reasons.append(f'{name} {actual} is older than the separate frontier environment requirement.')
        except PackageNotFoundError:reasons.append(f'{name} is missing.')
    hardware={'strategy':'full-resident research adapter; CPU/quantized staged optimization is not implemented'}
    try:
        import torch
        hardware['cuda_available']=torch.cuda.is_available()
        if not hardware['cuda_available']:reasons.append('Full-resident adapter requires CUDA.')
        else:
            hardware['total_vram_bytes']=torch.cuda.get_device_properties(0).total_memory
            # Weights alone exceed 30GB including text encoders. Never launch
            # the known full-resident loader on this machine's 6GB GPU.
            if hardware['total_vram_bytes']<36*1024**3:
                reasons.append('Current full-resident loader requires a 40GB-class CUDA device; this GPU is smaller. A staged differentiable loader is not validated.')
    except ImportError:reasons.append('Torch is unavailable for the hardware preflight.')
    if not (path/'model_index.json').exists():reasons.append('Resolved local FLUX.1-Kontext-dev snapshot is not installed.')
    if not (path/'imageshield-provenance.json').exists():reasons.append('Exact local model revision/hash manifest is missing.')
    return dict(ready=not reasons,reasons=reasons,hardware=hardware,paper='arxiv:2610.35566v1',scope='FLUX.1 Kontext only',author_code_verified=False,full_model_execution_verified=False)

def protect(clean_path,output_path,model_path=None,steps=1000,epsilon_rgb=12/255,seed=42,progress=None,cancel=None):
    from .defenders import MLUnavailable,check_cancel
    status=preflight(model_path)
    if not status['ready']:raise MLUnavailable(' '.join(status['reasons']))
    import numpy as np
    import torch
    from PIL import Image,ImageOps
    from diffusers import FluxKontextPipeline
    from diffusers.models.embeddings import apply_rotary_emb
    from .research_objectives import project_rgb
    if not 1<=steps<=1000 or not 0<epsilon_rgb<=16/255:raise ValueError('Invalid CaD research parameters.')
    path=Path(model_path or ROOT/'models/flux-kontext')
    provenance=json.loads((path/'imageshield-provenance.json').read_text())
    torch.manual_seed(seed);torch.cuda.manual_seed_all(seed)
    pipe=FluxKontextPipeline.from_pretrained(str(path),torch_dtype=torch.bfloat16,local_files_only=True,use_safetensors=True)
    pipe.to('cuda')
    for module in (pipe.vae,pipe.transformer,pipe.text_encoder,pipe.text_encoder_2):
        module.eval();module.requires_grad_(False)
    with torch.no_grad():
        prompt_embeds,pooled,text_ids=pipe.encode_prompt(prompt='',prompt_2='',device='cuda',num_images_per_prompt=1,max_sequence_length=512)
    # The empty prompt is encoded once; text encoders are not in the pixel path.
    pipe.text_encoder.to('cpu');pipe.text_encoder_2.to('cpu');torch.cuda.empty_cache()
    image=ImageOps.fit(Image.open(clean_path).convert('RGB'),(512,512),method=Image.Resampling.BICUBIC)
    original=torch.from_numpy(np.asarray(image).copy().transpose(2,0,1)).unsqueeze(0).float().cuda()/255
    current=original.clone();history=[];started=time.perf_counter()
    for step in range(steps):
        check_cancel(cancel)
        current=current.detach().requires_grad_(True)
        latent=pipe.vae.encode((2*current-1).to(torch.bfloat16)).latent_dist.mode()
        latent=(latent-pipe.vae.config.shift_factor)*pipe.vae.config.scaling_factor
        noise=torch.randn_like(latent)
        ids=pipe._prepare_latent_image_ids(1,latent.shape[2]//2,latent.shape[3]//2,'cuda',latent.dtype)
        ref_ids=ids.clone();ref_ids[...,0]=1
        image_ids=torch.cat([ids,ref_ids],dim=0)
        packed_noise=pipe._pack_latents(noise,1,latent.shape[1],latent.shape[2],latent.shape[3])
        packed_reference=pipe._pack_latents(latent,1,latent.shape[1],latent.shape[2],latent.shape[3])
        packed=torch.cat([packed_noise,packed_reference],dim=1)
        rotary=pipe.transformer.pos_embed(torch.cat([text_ids,image_ids],dim=0))
        t=torch.randint(980,1000,(1,),device='cuda').to(latent.dtype)/1000
        with JointAttentionCapture(pipe.transformer,blocks=10) as capture:
            try:
                pipe.transformer(hidden_states=packed,timestep=t,guidance=torch.full((1,),3.5,device='cuda'),pooled_projections=pooled,encoder_hidden_states=prompt_embeds,txt_ids=text_ids,img_ids=image_ids,return_dict=False)
            except _PrefixComplete:
                pass
            loss=capture.objective(prompt_embeds.shape[1],packed_noise.shape[1],rotary,apply_rotary_emb)
        gradient,=torch.autograd.grad(loss,current)
        if not torch.isfinite(gradient).all():raise RuntimeError('CaD pixel gradients are non-finite.')
        # Appendix step.005 is normalized [-1,1]; RGB step is half that.
        current=project_rgb(current.detach()+.0025*gradient.sign(),original,epsilon_rgb).detach()
        if step%25==0 or step==steps-1:
            item=dict(completed=step+1,total=steps,objective=float(loss.detach()));history.append(item)
            if progress:progress(item)
    pixels=(current[0]*255).round().byte().permute(1,2,0).cpu().numpy()
    Path(output_path).parent.mkdir(parents=True,exist_ok=True);Image.fromarray(pixels).save(output_path)
    return dict(method='cad_flux_kontext_reimplementation',paper='arxiv:2610.35566v1',author_code_verified=False,implementation_validation='math and tiny random real-architecture contracts checked; full pretrained integration and efficacy unverified',model=provenance,steps=steps,epsilon_rgb=epsilon_rgb,normalized_step=.005,blocks=list(range(10)),empty_prompt=True,timesteps=[980,999],seed=seed,history=history,elapsed_seconds=time.perf_counter()-started,effectiveness='not_tested',notes=['reported epsilon treated as RGB and mapped consistently into normalized model input','512px center crop disclosed; original source is unchanged','no robustness or commercial API transfer is established'])
