"""Audited inference of the released DiffVax network; no invented noise budget."""
from pathlib import Path
import hashlib
import importlib.util
import subprocess
import time

ROOT=Path(__file__).resolve().parents[3]
SOURCE=ROOT/'third_party/candidate-audit/DiffVax'
COMMIT='77fe66a8e6d50223a929081ec0851d9a49153903'
WEIGHT_SHA='b52500bf07a23aaf3d499adfaebe3e894c5d4fe2b4607fd6aa7fa64665bc43c0'

def protect(clean_path,mask_path,output_path,config=None,progress=None,cancel=None):
    import numpy as np
    import torch
    from PIL import Image
    from .defenders import check_cancel,MLUnavailable
    cfg=dict(config or {})
    check_cancel(cancel)
    if not torch.cuda.is_available():
        raise MLUnavailable('CUDA is required for this audited DiffVax profile.')
    revision=subprocess.check_output(['git','-C',str(SOURCE),'rev-parse','HEAD'],text=True).strip()
    changed=subprocess.run(['git','-C',str(SOURCE),'diff','--quiet','HEAD','--','src/diffvax'],capture_output=True)
    if revision!=COMMIT or changed.returncode:
        raise MLUnavailable('DiffVax source differs from the audited revision.')
    weight=SOURCE/'checkpoints/diffvax_trained.pth'
    if not weight.is_file() or hashlib.sha256(weight.read_bytes()).hexdigest()!=WEIGHT_SHA:
        raise MLUnavailable('Verified DiffVax checkpoint is missing or changed.')
    spec=importlib.util.spec_from_file_location('imageshield_audited_diffvax_model',SOURCE/'src/diffvax/model.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    net=module.NestedUNet(num_classes=3)
    state=torch.load(weight,map_location='cpu',weights_only=True)
    net.load_state_dict(state,strict=True)
    net.requires_grad_(False)
    bn_mode=cfg.get('bn_mode','upstream_train')
    if bn_mode not in ('upstream_train','eval'):
        raise ValueError('Unknown BatchNorm inference mode.')
    net.train(bn_mode=='upstream_train')
    net=net.to('cuda')
    clean=np.asarray(Image.open(clean_path).convert('RGB')).copy()
    mask=np.asarray(Image.open(mask_path).convert('L')).copy()
    if clean.shape!=(512,512,3) or mask.shape!=(512,512) or not np.isin(mask,[0,255]).all():
        raise ValueError('DiffVax research profile requires matching binary 512px masks.')
    image=torch.from_numpy(clean.transpose(2,0,1)).unsqueeze(0).float().cuda()/127.5-1
    editable=torch.from_numpy(mask).unsqueeze(0).unsqueeze(0).float().cuda()/255
    # Match the released demo: the network receives masked context, NOT full RGB.
    context=(image*(editable<.5)).half()
    started=time.perf_counter()
    if progress:progress(0,1,'Running released DiffVax checkpoint')
    torch.cuda.reset_peak_memory_stats()
    with torch.inference_mode():
        delta=net(context.float()).half()*(1-editable)
        adv=(context+delta).clamp(-1,1)
        pixels=((adv[0]/2+.5).clamp(0,1)*255).byte().permute(1,2,0).cpu().numpy()
    check_cancel(cancel)
    # Released recover_image(background=True) restores original editable pixels.
    pixels[mask==255]=clean[mask==255]
    Path(output_path).parent.mkdir(parents=True,exist_ok=True)
    Image.fromarray(pixels).save(output_path)
    if progress:progress(1,1,'DiffVax export generated; quality not assessed')
    result=dict(method='diffvax',source_commit=COMMIT,checkpoint_sha256=WEIGHT_SHA,bn_mode=bn_mode,source_license='MIT',epsilon_budget_enforced=False,normalization='[-1,1]',network_input='masked context, half then float32 as released demo',iterations=1,elapsed_seconds=time.perf_counter()-started,peak_cuda_allocated_bytes=torch.cuda.max_memory_allocated(),effectiveness='not_tested',adaptations=['weights_only checkpoint loading','frozen weights/no optimizer','direct audited model import; no upstream package CUDA side effects']+(['eval BatchNorm differs from released demo'] if bn_mode=='eval' else []))
    del net,state,image,editable,context,delta,adv
    torch.cuda.empty_cache()
    return result
