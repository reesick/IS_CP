"""Use the REAL Diffusers FLUX architecture with tiny random CPU weights.

Tests API/shape, joint text+image RoPE and differentiability only. Not an editor
benchmark, pretrained-model run, image defense or frontier protection evidence.
"""
import json
from pathlib import Path
import sys
import torch
import diffusers
from diffusers import FluxTransformer2DModel,FluxKontextPipeline,AutoencoderKL
from diffusers.models.embeddings import apply_rotary_emb
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from backend.app.ml.cad import JointAttentionCapture,_PrefixComplete
torch.manual_seed(31)
model=FluxTransformer2DModel(in_channels=16,num_layers=2,num_single_layers=1,attention_head_dim=8,num_attention_heads=2,joint_attention_dim=16,pooled_projection_dim=8,axes_dims_rope=(2,2,4),guidance_embeds=True)
model.eval();model.requires_grad_(False)
hidden=torch.randn(1,8,16,requires_grad=True)
text=torch.randn(1,3,16)
txt_ids=torch.zeros(3,3)
img_ids=torch.tensor([[i//4,i%2,(i%4)//2] for i in range(8)],dtype=torch.float32)
rotary=model.pos_embed(torch.cat([txt_ids,img_ids]))
stopped=False
try:
    with JointAttentionCapture(model,blocks=2) as capture:
        try:
            model(hidden_states=hidden,encoder_hidden_states=text,pooled_projections=torch.randn(1,8),timestep=torch.tensor([.99]),guidance=torch.tensor([3.5]),txt_ids=txt_ids,img_ids=img_ids,return_dict=False)
        except _PrefixComplete:stopped=True
        assert stopped and len(capture.values)==8
        actual=capture.objective(3,4,rotary,apply_rotary_emb)
        dense=[]
        for index in range(2):
            q=torch.cat([capture.values[index,'norm_added_q'],capture.values[index,'norm_q']],dim=2)
            k=torch.cat([capture.values[index,'norm_added_k'],capture.values[index,'norm_k']],dim=2)
            q=apply_rotary_emb(q,rotary,sequence_dim=2)[:,:,3:7]
            k=apply_rotary_emb(k,rotary,sequence_dim=2)
            attention=(q@k.transpose(-1,-2)/(8**.5)).softmax(-1)
            dense.append(-(1-attention[...,7:].sum(-1)).square().mean())
        expected=torch.stack(dense).mean()
        assert torch.allclose(actual,expected,atol=1e-7)
        grad,=torch.autograd.grad(actual,hidden,retain_graph=True)
        expected_grad,=torch.autograd.grad(expected,hidden)
        assert torch.isfinite(grad).all() and grad[:,:,4:].abs().max()>0
        assert torch.allclose(grad,expected_grad,atol=1e-7)
finally:
    assert all(not module._forward_hooks for module in model.modules())
# Validate the actual VAE -> mode -> shift/scale -> packing -> attention path.
# This is still random architecture validation, never a protected-image export.
vae=AutoencoderKL(in_channels=3,out_channels=3,down_block_types=('DownEncoderBlock2D','DownEncoderBlock2D'),up_block_types=('UpDecoderBlock2D','UpDecoderBlock2D'),block_out_channels=(32,64),layers_per_block=1,latent_channels=4,norm_num_groups=32,sample_size=32,scaling_factor=.3611,shift_factor=.1159)
vae.eval();vae.requires_grad_(False)
pixels=torch.rand(1,3,32,32,requires_grad=True)
latent=vae.encode(pixels*2-1).latent_dist.mode()
latent=(latent-vae.config.shift_factor)*vae.config.scaling_factor
b,c,h,w=latent.shape
packed_ref=FluxKontextPipeline._pack_latents(latent,b,c,h,w)
packed_target=FluxKontextPipeline._pack_latents(torch.randn_like(latent),b,c,h,w)
image_ids=FluxKontextPipeline._prepare_latent_image_ids(b,h//2,w//2,'cpu',latent.dtype)
ref_ids=image_ids.clone();ref_ids[...,0]=1
joint_ids=torch.cat([image_ids,ref_ids])
rotary=model.pos_embed(torch.cat([txt_ids,joint_ids]))
with JointAttentionCapture(model,blocks=2) as capture:
    try:
        model(hidden_states=torch.cat([packed_target,packed_ref],dim=1),encoder_hidden_states=text,pooled_projections=torch.randn(1,8),timestep=torch.tensor([.99]),guidance=torch.tensor([3.5]),txt_ids=txt_ids,img_ids=joint_ids,return_dict=False)
    except _PrefixComplete:pass
    objective=capture.objective(3,packed_target.shape[1],rotary,apply_rotary_emb)
    pixel_gradient,=torch.autograd.grad(objective,pixels)
    assert torch.isfinite(pixel_gradient).all() and pixel_gradient.abs().max()>0
assert all(not module._forward_hooks for module in model.modules())
result=dict(passed=True,torch=torch.__version__,diffusers=diffusers.__version__,device='cpu',weights='tiny random initialization, NOT pretrained',checks=['actual FluxTransformer2DModel forward contract','both normalized modalities captured','joint rotary position embedding','Eq13 dense objective and gradient equivalence','reference input receives gradients','prefix truncation','hooks removed after exception','real VAE posterior-mode/shift/scale and Kontext packing helpers','objective gradient reaches RGB pixels through actual VAE and transformer'],effectiveness='not_tested')
(ROOT/'docs/research/CAD_FLUX_ARCHITECTURE_CHECK.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
