"""Paired local SD1.5 inpainting with a fresh generator for every call."""
from __future__ import annotations

from pathlib import Path

from .defenders import check_cancel, load_pipeline, model_provenance


def edit_pair(clean_path, protected_path, mask_path, output_dir, config=None, progress=None, cancel=None):
    config = dict(config or {})
    check_cancel(cancel)
    pipe = load_pipeline(config)
    pipe.unet.eval()
    pipe.vae.eval()
    if pipe.safety_checker is not None and not config.get('inference_cpu_offload'):
        pipe.safety_checker.to('cuda')
    import io
    import torch
    from PIL import Image

    prompt = config.get("prompt", "")
    if not isinstance(prompt, str) or not 1 <= len(prompt) <= 500:
        raise ValueError("An edit prompt of 1 to 500 characters is required")
    seeds = config.get("seeds", [11, 22, 33])
    if not 1 <= len(seeds) <= 3 or any(type(seed) is not int or not 0 <= seed < 2**32 for seed in seeds):
        raise ValueError("Provide one to three unsigned 32-bit seeds")
    channel = config.get("channel", "local_png")
    if channel not in {"local_png", "jpeg_simulation"}:
        raise ValueError("Unsupported experiment channel")
    mask = Image.open(mask_path).convert("L")
    images = [Image.open(path).convert("RGB") for path in (clean_path, protected_path)]
    if any(image.size != (512, 512) for image in images) or mask.size != (512, 512):
        raise ValueError("Paired inputs and mask must be the same 512 x 512 canvas")
    if channel == "jpeg_simulation":
        for index, image in enumerate(images):
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=85, subsampling=2)
            buffer.seek(0)
            images[index] = Image.open(buffer).convert("RGB")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    input_paths = {}
    for name, image in zip(("clean_input", "protected_input"), images):
        input_path = output_dir / f"{name}.png"
        image.save(input_path, format="PNG")
        input_paths[name] = str(input_path)
    settings = {"num_inference_steps": 30, "guidance_scale": 7.5, "strength": 0.99,
                "negative_prompt": "", "height": 512, "width": 512}
    outputs = []
    import inspect
    # Report every denoising step when the installed Diffusers supports it.
    per_step = "callback_on_step_end" in inspect.signature(pipe.__call__).parameters
    unit = max(1, int(settings["num_inference_steps"] * settings["strength"])) if per_step else 1
    total = len(seeds) * 2 * unit
    stages = {"edit_clean": "Editing original image", "edit_protected": "Editing protected image"}
    for seed in seeds:
        pair = {"seed": seed, "safety_filtered": False, **input_paths}
        for name, image in zip(("edit_clean", "edit_protected"), images):
            check_cancel(cancel)
            base = (len(outputs) * 2 + (name == "edit_protected")) * unit
            if progress:
                progress(base, total, stages[name])
            extra = {}
            if per_step:
                def on_step(_pipe, index, _timestep, kwargs, base=base, stage=stages[name]):
                    check_cancel(cancel)
                    if progress:
                        progress(min(base + index + 1, base + unit), total, stage)
                    return kwargs
                extra["callback_on_step_end"] = on_step
            generator = torch.Generator(device="cuda").manual_seed(seed)
            with torch.inference_mode():
                result = pipe(prompt=prompt, image=image, mask_image=mask, generator=generator, **settings, **extra)
            filtered = bool(result.nsfw_content_detected and result.nsfw_content_detected[0])
            path = output_dir / f"{seed}_{name}.png"
            result.images[0].save(path, format="PNG")
            pair[name] = str(path)
            pair["safety_filtered"] |= filtered
        outputs.append(pair)
    if progress:
        progress(total, total, "Paired editing complete")
    return {"pairs": outputs, "settings": settings, "prompt": prompt, "seeds": seeds,
            "torch_version": torch.__version__,
            "diffusers_version": __import__("diffusers").__version__,
            **model_provenance(config),
            "channel": channel, "scheduler": dict(pipe.scheduler.config),
            "channel_transform": ({"format": "JPEG", "quality": 85, "subsampling": 2,
                                   "description": "synthetic stress test"}
                                  if channel == "jpeg_simulation" else None),
            "execution_strategy": "model_cpu_offload" if config.get('inference_cpu_offload') else "resident_cuda",
            "effectiveness": "inconclusive", "human_review": "pending"}
