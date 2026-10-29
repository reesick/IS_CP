"""Explicitly reduced MIRAGE-informed text-only surrogate experiment.

This is NOT the full MIRAGE reproduction or a verified editor refusal system:
the paper's five target images/three exact texts and full eight-model ensemble
were not released. All substitutions below are written into the output record.
"""
from pathlib import Path
import hashlib
import math
import time

ROOT=Path(__file__).resolve().parents[3]
TARGETS=['an image containing nudity','an explicit sexual image','a pornographic image']

def protect(clean_path,output_path,steps=250,epsilon=8/255,seed=42,progress=None,cancel=None):
    return protect_batch([clean_path],[output_path],steps,epsilon,seed,progress,cancel)[0]


def protect_batch(clean_paths,output_paths,steps=5000,epsilon=2/255,seed=42,progress=None,cancel=None,initial_paths=None):
    """Shared frozen encoder; independent per-image losses/budgets and RNGs.

    Batched CLIP inference has no cross-image attention or training BatchNorm.
    Gradients are taken from the SUM, preserving each image's own objective.
    """
    import io
    import random
    import numpy as np
    import torch
    import torch.nn.functional as F
    from PIL import Image
    from transformers import CLIPModel,CLIPTokenizerFast
    from torchvision.transforms.functional import gaussian_blur
    from .research_objectives import global_local_objective,project_rgb
    from .defenders import check_cancel,MLUnavailable
    import json
    path=ROOT/'models/research-clip-b32'
    manifest_path=path/'imageshield-provenance.json'
    if not manifest_path.exists():
        raise MLUnavailable('Download the explicitly selected research encoder first.')
    manifest=json.loads(manifest_path.read_text())
    weight=path/'model.safetensors'
    if hashlib.file_digest(weight.open('rb'),'sha256').hexdigest()!=manifest['sha256']:
        raise MLUnavailable('Research surrogate weights failed their hash check.')
    if not 1<=steps<=5000 or not 0<epsilon<=16/255:
        raise ValueError('Research steps/budget outside declared range.')
    if not 1<=len(clean_paths)<=3 or len(clean_paths)!=len(output_paths):
        raise ValueError('Provide one to three matched input/output paths.')
    rngs=[random.Random(seed+i) for i in range(len(clean_paths))];torch.manual_seed(seed)
    model=CLIPModel.from_pretrained(str(path),local_files_only=True,use_safetensors=True).eval().to('cuda')
    model.requires_grad_(False)
    tokenizer=CLIPTokenizerFast.from_pretrained(str(path),local_files_only=True)
    tokens={k:v.cuda() for k,v in tokenizer(TARGETS,padding=True,return_tensors='pt').items()}
    with torch.no_grad():targets=model.get_text_features(**tokens).detach()
    originals=[];sizes=[]
    for clean_path,output_path in zip(clean_paths,output_paths):
        if Path(clean_path).resolve()==Path(output_path).resolve():raise ValueError('Source and export must be different files.')
        array=np.asarray(Image.open(clean_path).convert('RGB')).copy()
        height,width=array.shape[:2]
        if array.ndim!=3 or array.shape[2]!=3 or min(height,width)<256 or max(height,width)>1024:
            raise ValueError('Experimental native profile needs RGB, minimum side256, maximum side1024.')
        originals.append(torch.from_numpy(array.transpose(2,0,1)).unsqueeze(0).float().cuda()/255)
        sizes.append((height,width))
    currents=[original.clone() for original in originals]
    if initial_paths is not None:
        if len(initial_paths)!=len(originals):raise ValueError('Warm-start inputs must match the batch.')
        for i,(initial_path,original) in enumerate(zip(initial_paths,originals)):
            with Image.open(initial_path) as opened:
                array=np.asarray(opened.convert('RGB')).copy()
            initial=torch.from_numpy(array.transpose(2,0,1)).unsqueeze(0).float().cuda()/255
            if initial.shape!=original.shape:raise ValueError('Warm-start dimensions do not match the clean reference.')
            currents[i]=project_rgb(initial,original,epsilon).detach()
    pre=json.loads((path/'preprocessor_config.json').read_text())
    mean=torch.tensor(pre['image_mean'],device='cuda')[None,:,None,None]
    std=torch.tensor(pre['image_std'],device='cuda')[None,:,None,None]
    def features(batch):
        scaled=F.interpolate(batch,size=(224,224),mode='bicubic',align_corners=False,antialias=True)
        return model.get_image_features(pixel_values=(scaled-mean)/std)
    def augment(z,kind):
        height,width=z.shape[-2:]
        if kind=='flip':return z.flip(-1)
        if kind=='resize':return F.interpolate(F.interpolate(z,size=(round(height*.75),round(width*.75)),mode='bilinear',align_corners=False),size=(height,width),mode='bilinear',align_corners=False)
        if kind=='blur':return gaussian_blur(z,[5,5],[.7,.7])
        if kind=='crop':return F.interpolate(z[:,:,height//8:height-height//8,width//8:width-width//8],size=(height,width),mode='bilinear',align_corners=False)
        if kind=='jpeg':
            pixels=(z.detach()[0].clamp(0,1)*255).byte().permute(1,2,0).cpu().numpy()
            buffer=io.BytesIO();Image.fromarray(pixels).save(buffer,'JPEG',quality=85,subsampling=2);buffer.seek(0)
            decoded=np.asarray(Image.open(buffer).convert('RGB')).copy()
            jpeg=torch.from_numpy(decoded.transpose(2,0,1)).unsqueeze(0).to(z.device,z.dtype)/255
            return z+(jpeg-z).detach()  # declared straight-through JPEG gradient
        return z
    with torch.no_grad():initials=[float(global_local_objective(features(original),features(original.repeat(8,1,1,1)),targets,top_k=8)) for original in originals]
    started=time.perf_counter();histories=[[] for _ in originals]
    torch.cuda.reset_peak_memory_stats()
    for iteration in range(steps):
        check_cancel(cancel)
        currents=[current.detach().requires_grad_(True) for current in currents]
        transforms=[];patch_batches=[]
        for current,rng,(height,width) in zip(currents,rngs,sizes):
            transformed=augment(current,rng.choice(['crop','resize','blur','jpeg','flip']))
            coordinates=[(rng.randrange(width-255),rng.randrange(height-255)) for _ in range(16)]
            transforms.append(F.interpolate(transformed,size=(224,224),mode='bicubic',align_corners=False,antialias=True))
            patch_batches.append(torch.cat([transformed[:,:,y:y+256,x:x+256] for x,y in coordinates]))
        global_features=features(torch.cat(transforms))
        patch_features=features(torch.cat(patch_batches))
        objectives=[global_local_objective(global_features[i:i+1],patch_features[i*16:(i+1)*16],targets,local_weight=.25,top_k=8) for i in range(len(currents))]
        gradients=torch.autograd.grad(torch.stack(objectives).sum(),currents)
        if not all(torch.isfinite(g).all() for g in gradients):raise RuntimeError('Non-finite surrogate image gradient.')
        # Paper lists step1.0 without units; 1/255 RGB is an explicit assumption.
        alpha=(1/255)*.5*(1+math.cos(math.pi*iteration/max(1,steps-1)))
        currents=[project_rgb(current.detach()+alpha*gradient.sign(),original,epsilon).detach() for current,gradient,original in zip(currents,gradients,originals)]
        if iteration%25==0 or iteration==steps-1:
            for i,objective in enumerate(objectives):
                item=dict(image=i+1,completed=iteration+1,total=steps,objective=float(objective.detach()))
                histories[i].append(item)
                if progress:progress(item)
    elapsed=time.perf_counter()-started;peak=torch.cuda.max_memory_allocated();results=[]
    for i,(current,output_path,(height,width)) in enumerate(zip(currents,output_paths,sizes)):
        with torch.no_grad():final=float(global_local_objective(features(current),features(current.repeat(8,1,1,1)),targets,top_k=8))
        pixels=(current[0].clamp(0,1)*255).round().byte().permute(1,2,0).cpu().numpy()
        Path(output_path).parent.mkdir(parents=True,exist_ok=True)
        Image.fromarray(pixels).save(output_path)
        results.append(dict(method='mirage_informed_clip_text_probe',paper='arxiv:2606.26199v2',paper_reproduction=False,commercial_refusal_verified=False,encoder=manifest,steps=steps,epsilon_rgb=epsilon,seed=seed+i,image_size=[width,height],target_texts=TARGETS,target_images=0,global_local_lambda=.25,patches=16,patch_size=256,top_k=8,initial_canonical_score=initials[i],final_canonical_score=final,history=histories[i],elapsed_seconds=elapsed,elapsed_scope='whole shared-encoder batch',execution_batch_size=len(currents),peak_cuda_allocated_bytes=peak,effectiveness='not_tested',adaptations=['single paper-listed CLIP surrogate, not full eight-model ensemble','three disclosed substitute text targets; unreleased target image bank omitted','declared source/export resolution recorded separately','zero initialization; step1/255 RGB cosine schedule assumed','declared EOT: crop1/8 borders, resize75percent, blur sigma0.7, JPEG85, horizontal flip','no model dropout with one surrogate','no remote moderation selection or API calls']))
        results[-1]['initialization']={'kind':'zero' if initial_paths is None else 'projected_prior_candidate','prior_candidate_sha256':None if initial_paths is None else hashlib.sha256(Path(initial_paths[i]).read_bytes()).hexdigest()}
        results[-1]['initial_canonical_score_scope']='clean reference before candidate optimization'
        if initial_paths is not None:
            results[-1]['adaptations']=[a.replace('zero initialization;','projected prior candidate initialization;') for a in results[-1]['adaptations']]
            results[-1]['adaptations'].append('warm-start refinement from a prior candidate, projected to the current RGB budget')
    del model,currents,originals,targets
    torch.cuda.empty_cache()
    return results
