"""Audited wrapper around the real upstream DiffusionGuard implementation.

The upstream checkout remains unmodified. See docs/UPSTREAM_AUDIT.md for the
mask polarity, normalized epsilon units and instrumentation adaptations.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[3]
UPSTREAM_COMMIT = "96e28c19124fbb0e0671f48931ffed180775c7ea"
_PIPE = None
_PIPE_PATH = None


class MLUnavailable(RuntimeError):
    code = "model_unavailable"


class JobCancelled(RuntimeError):
    code = "cancelled"


def check_cancel(cancel):
    if cancel and cancel():
        raise JobCancelled("Job cancellation requested")


def resolve_model(config=None):
    config = config or {}
    candidate = config.get("model_path") or config.get("model_snapshot_path") or os.getenv("IMAGESHIELD_MODEL_PATH")
    if not candidate:
        registry_path = ROOT / "model-registry.json"
        if registry_path.exists():
            registry = json.loads(registry_path.read_text(encoding="utf-8-sig"))
            models = registry.get("models", {})
            entries = models.values() if isinstance(models, dict) else models
            for entry in entries:
                if entry.get("id") in (None, "sd15_inpaint") and entry.get("snapshot_path"):
                    candidate = entry["snapshot_path"]
                    break
    if not candidate:
        raise MLUnavailable("Model files are not installed. Run scripts/bootstrap.ps1 -ML -DownloadModel.")
    path = Path(candidate)
    if not path.is_absolute():
        path = ROOT / path
    if not (path / "model_index.json").is_file():
        raise MLUnavailable("The configured local model snapshot is incomplete.")
    return path.resolve()


def load_pipeline(config=None):
    global _PIPE, _PIPE_PATH
    try:
        import torch
        from diffusers import StableDiffusionInpaintPipeline
    except ImportError as exc:
        raise MLUnavailable("ML dependencies are missing; run scripts/bootstrap.ps1 -ML.") from exc
    if not torch.cuda.is_available():
        raise MLUnavailable("CUDA is unavailable. Use the configured NVIDIA ML environment.")
    path = resolve_model(config)
    if _PIPE is None or _PIPE_PATH != str(path):
        kwargs = {"torch_dtype": torch.float16, "local_files_only": True, "use_safetensors": True}
        # Only select a variant proven to exist in the downloaded snapshot.
        if (path / "unet" / "diffusion_pytorch_model.fp16.safetensors").is_file():
            kwargs["variant"] = "fp16"
        if (config or {}).get('sequential_component_load'):
            # Move the largest component before loading the remaining CPU
            # weights. Same checkpoint/dtype; lower peak Windows commit usage.
            import gc
            from diffusers import UNet2DConditionModel
            unet=UNet2DConditionModel.from_pretrained(str(path/'unet'),low_cpu_mem_usage=True,**kwargs).to('cuda')
            gc.collect()
            pipe=StableDiffusionInpaintPipeline.from_pretrained(str(path),unet=unet,**kwargs).to('cuda')
        else:
            pipe = StableDiffusionInpaintPipeline.from_pretrained(str(path), **kwargs).to("cuda")
        for module in (pipe.vae, pipe.unet, pipe.text_encoder):
            module.requires_grad_(False)
            module.eval()
        from diffusers.models.attention_processor import AttnProcessor2_0
        pipe.unet.set_attn_processor(AttnProcessor2_0())
        pipe.vae.set_attn_processor(AttnProcessor2_0())
        pipe.vae.enable_slicing()
        pipe.set_progress_bar_config(disable=True)
        if (config or {}).get('inference_cpu_offload'):
            pipe.enable_model_cpu_offload(gpu_id=0)
        _PIPE, _PIPE_PATH = pipe, str(path)
    return _PIPE


def _load_upstream():
    source = ROOT / "third_party" / "DiffusionGuard"
    if not (source / "attacks" / "common.py").is_file():
        raise MLUnavailable("DiffusionGuard source checkout is missing.")
    try:
        revision = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
        modified = subprocess.run(["git", "-C", str(source), "diff", "--quiet", "HEAD", "--",
                                   "attacks", "utils", "config", "main.py"], capture_output=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise MLUnavailable("Cannot verify the pinned DiffusionGuard source checkout.") from exc
    if revision != UPSTREAM_COMMIT or modified.returncode:
        raise MLUnavailable("DiffusionGuard source differs from the audited pinned revision.")
    if str(source) not in sys.path:
        sys.path.insert(0, str(source))
    import attacks
    import attacks.common as common
    import utils
    from omegaconf import OmegaConf
    return attacks, common, utils, OmegaConf


def model_provenance(config=None):
    path = resolve_model(config)
    registry_path = ROOT / "model-registry.json"
    if registry_path.is_file():
        registry = json.loads(registry_path.read_text(encoding="utf-8-sig"))
        models = registry.get("models", [])
        entries = models.values() if isinstance(models, dict) else models
        for entry in entries:
            candidate = entry.get("snapshot_path") or entry.get("local_path")
            if candidate and Path(candidate).resolve() == path:
                return {"model_id": entry.get("id", "sd15_inpaint"),
                        "model_revision": entry.get("revision"),
                        "model_license": entry.get("license") or entry.get("license_from_model_card")}
    return {"model_id": "sd15_inpaint", "model_revision": None,
            "model_revision_reason": "Local snapshot has no matching resolved registry record"}


def protect(clean_path, mask_path, output_path, config=None, progress: Callable | None = None, cancel=None):
    """Optimize pixels through upstream protect_image; never substitutes noise.

    ``mask_path`` is canonical white=editable. ``epsilon`` is in [0,1] RGB
    units. Progress callback receives (completed_steps, total_steps, stage).
    Cancellation callback returns True when the job should stop.
    """
    config = dict(config or {})
    check_cancel(cancel)
    pipe = load_pipeline(config)
    import torch
    # Checkpointing recomputes activations while preserving gradients to pixels.
    # Diffusers 0.24 enables it only in training mode; all weights stay frozen.
    # These models use GroupNorm/LayerNorm and zero dropout, so this does not
    # update model statistics or introduce training-time stochastic layers.
    checkpoint_unet=bool(config.get('checkpoint_unet',False))
    for module in (pipe.unet, pipe.vae):
        if any(isinstance(layer, torch.nn.Dropout) and layer.p != 0 for layer in module.modules()):
            raise MLUnavailable('Checkpointing profile requires zero-dropout frozen models.')
        if module is pipe.unet and not checkpoint_unet:
            module.disable_gradient_checkpointing()
            module.eval()
        else:
            module.enable_gradient_checkpointing()
            module.train()
    import random
    import numpy as np
    import torch
    from PIL import Image, ImageOps

    attacks, common, utils, OmegaConf = _load_upstream()
    seed = int(config.get("seed", 42))
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    clean = Image.open(clean_path).convert("RGB")
    editable = Image.open(mask_path).convert("L")
    if clean.size != (512, 512) or editable.size != clean.size:
        raise ValueError("Defense requires the normalized 512 x 512 reference and matching mask.")
    if not set(np.unique(np.asarray(editable))).issubset({0, 255}):
        raise ValueError("Canonical mask must contain only 0 and 255.")
    retained = ImageOps.invert(editable).convert("RGB")
    profile = config.get("profile", "research")
    if profile not in {"research", "smoke"}:
        raise ValueError("Unknown defense profile")
    iterations = 800 if profile == "research" else 20
    epsilon = float(config.get("epsilon", 8 / 255))
    if not 0 < epsilon <= 16 / 255:
        raise ValueError("epsilon must be greater than zero and at most 16/255 in RGB units")
    cfg = OmegaConf.load(ROOT / "third_party" / "DiffusionGuard" / "config" / "diffusionguard.yaml")
    cfg.training.iters = iterations
    cfg.training.eps = 2 * epsilon
    # Source contour_shrink fills external contours, which erases holes in a
    # retained-background mask. A fixed known mask preserves both supported
    # editing modes. This is an adaptation, not full paper reproduction.
    cfg.training.mask.generation_method = "single"
    cfg.model.inpainting = str(resolve_model(config))

    class InstrumentedIterations:
        def __init__(self, sequence):
            self.sequence = sequence

        def __iter__(self):
            for index in self.sequence:
                check_cancel(cancel)
                if progress:
                    progress(index, iterations, "Optimizing adversarial pixels")
                yield index
                check_cancel(cancel)
                if progress:
                    progress(index + 1, iterations, "Optimizing adversarial pixels")

        def set_description_str(self, _text):
            pass

    original_tqdm = common.tqdm
    common.tqdm = InstrumentedIterations
    torch.cuda.reset_peak_memory_stats()
    try:
        # Autograd must remain enabled for image pixels despite frozen weights.
        with torch.enable_grad():
            adv = attacks.protect_image("diffusionguard", pipe, clean, [retained], retained,
                                        utils.get_mask_radius_list([retained]), cfg)
        if not torch.isfinite(adv).all().item():
            raise RuntimeError("Non-finite defense output; no protected export was created")
        result = utils.tensor_to_pil_image(adv.detach().cpu())
        check_cancel(cancel)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        result.save(output_path, format="PNG")
        return {
            "method": "diffusionguard", "profile": profile, "iterations": iterations,
            "training_config": OmegaConf.to_container(cfg.training, resolve=True),
            "epsilon_rgb": epsilon, "epsilon_upstream_normalized": 2 * epsilon,
            "mask_policy": "single_known_mask",
            "reproduction_status": "adapted upstream objective; no contour augmentation or robustness claim",
            "step_size_upstream_normalized": float(cfg.training.step_size),
            "seed": seed, "upstream_commit": UPSTREAM_COMMIT,
            "checkpoint_unet": checkpoint_unet,
            "torch_version": torch.__version__,
            "diffusers_version": __import__("diffusers").__version__,
            **model_provenance(config), "mask_conversion": "invert: white retained upstream",
            "adaptations": ["single known mask instead of contour_shrink", "frozen model weights", "PyTorch scaled dot-product attention", "zero-dropout VAE gradient checkpointing", "optional UNet gradient checkpointing", "VAE slicing", "progress/cancel instrumentation"],
            "peak_cuda_allocated_bytes": torch.cuda.max_memory_allocated(),
            "peak_cuda_reserved_bytes": torch.cuda.max_memory_reserved(),
            "human_review": "pending", "effectiveness": "not_tested",
        }
    finally:
        common.tqdm = original_tqdm
        torch.cuda.empty_cache()
