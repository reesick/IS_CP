# Model and environment runbook

## 1. What is selected
This project has a defender algorithm and an editing checkpoint. They are different components.

| Role | Exact candidate | Initial use |
|---|---|---|
| Main defender | https://github.com/choi403/DiffusionGuard | Source adapter, optimize pixels; no model training |
| Main frozen editor/surrogate | stable-diffusion-v1-5/stable-diffusion-inpainting | Inpainting research at 512px |
| Baseline defender | https://github.com/MadryLab/photoguard | Reproduction/comparison after main path |
| Optional fast defender | https://github.com/ozdentarikcan/DiffVax | Pretrained immunizer only if checkpoint passes independent checks |
| Optional transfer-test editor | diffusers/stable-diffusion-xl-1.0-inpainting-0.1 | Held-out evaluation on a larger GPU |
| Optional watermark | https://github.com/facebookresearch/watermark-anything | Phase 2 pretrained WAM; separate dependency env if needed |

The current SD1.5 model card identifies this repository as a mirror of the deprecated Runway checkpoint. DiffusionGuard's README still names runwayml/stable-diffusion-inpainting. Resolve the current mirror and record hashes/revision; do not silently assume a mirror is bit-identical. Keep the exact downloaded snapshot path in the final configuration.

No direct evidence here establishes protection on Firefly, Gemini, FLUX, image chat tools or every Photoshop Generative Fill model. SDXL is an evaluation candidate, not a promised compatible defender drop-in.

## 2. Reproducibility status
Checked: upstream README, requirements, main entry point, current model card and design Markdown reference.
Not checked: installing full dependencies, downloading model bytes, executing protection, checkpoint loadability, quantitative efficacy, native-resolution output, Instagram or Photoshop.
Treat commands below as a starting runbook. The implementation AI must turn them into tested bootstrap scripts and lock files.

## 3. Source inspection tasks before adaptation
Clone the official repository, inspect config filenames and imports, then record git rev-parse HEAD. Preserve attribution and inspect source/weight license terms before redistribution.
Read main.py, attacks/, config/, utils/ and requirements.txt. Determine:
- configuration structure and all real defaults;
- editable versus protected/context mask polarity;
- input normalization and epsilon units;
- whether model parameters are frozen while image gradients remain live;
- actual exported output path and image quantization.
A fetched main.py shows an assets-based entry point and adv_image.png output below protected_images; our adapter must expose explicit per-job input/output directories rather than scraping shared output folders.
Full configuration files could not be fetched during this research, so exact Hydra override names beyond the README example must be resolved from the checkout.

## 4. First setup, Linux / WSL2
For NVIDIA work on Windows, WSL2 is a reasonable development option; native Windows is also possible if dependencies reproduce. Check actual GPU/driver availability. Do not change the user's system CUDA or drivers automatically.

Run from a new project directory, one command at a time:
```bash
git clone https://github.com/choi403/DiffusionGuard.git third_party/DiffusionGuard
git -C third_party/DiffusionGuard rev-parse HEAD
conda create -n imageshield-ml python=3.10 -y
conda activate imageshield-ml
python -m pip install --upgrade pip
python -m pip install torch==2.1.1 torchvision==0.16.1 --index-url https://download.pytorch.org/whl/cu121
```
The PyTorch command comes from the official previous-version matrix. It is one supported wheel option, not a requirement to install a system CUDA 12.1 toolkit.

The upstream requirements pin diffusers==0.24.0, torch==2.1.1 and torchvision==0.16.1 while leaving several dependencies unpinned. Blindly resolving the newest Hub/Transformers/NumPy against this old stack may fail. Use an isolated environment.

Candidate compatibility constraints to TRY (not independently tested here):
```text
numpy==1.26.4
huggingface-hub==0.25.2
transformers==4.35.2
accelerate==0.24.1
```
Write these to a temporary compatibility constraints file and resolve upstream requirements under them. Other unpinned dependencies may require further constraints. Do not market this as a verified lock. Avoid installing another torch build unintentionally. Once imports and GPU smoke tests pass, freeze the exact environment and retain dependency provenance.

If source modernization is required, keep original reproduction and modernized adapter results separately identified. Do not change the optimizer/objective and still call it an exact reproduction.

## 5. Download model weights explicitly
The coding AI must implement scripts/setup/download_models.py with:
- model registry entries from models.example.json;
- explicit user-selected download, never API import-time downloading;
- Hugging Face snapshot resolution at a recorded commit;
- sufficient free-disk checks and resumable cache behavior;
- prefer safetensors when available and compatible;
- no trust_remote_code unless specifically reviewed and justified;
- write resolved revision, license, component paths and hashes to model-registry.json;
- failures remain unavailable; never invent placeholder weights.

Use the local snapshot directory in defense/editor loaders. Older Diffusers APIs typically use torch_dtype, not a modern dtype/device_map example blindly copied from current docs. Verify fp16 variant availability before specifying variant="fp16"; missing variants are errors, not fallback proof. Authentication/license requirements, if encountered, must be shown explicitly and credentials stay out of logs.

## 6. Minimal editor smoke code
This is a candidate for the legacy environment, not a complete defense implementation:
```python
from pathlib import Path
from PIL import Image
import torch
from diffusers import StableDiffusionInpaintPipeline

snapshot = Path("models/sd15_inpaint")  # replace with resolved local snapshot
pipe = StableDiffusionInpaintPipeline.from_pretrained(
    str(snapshot),
    torch_dtype=torch.float16,
    local_files_only=True,
).to("cuda")

image = Image.open("fixtures/clean_512.png").convert("RGB")
mask = Image.open("fixtures/edit_mask_512.png").convert("L")
assert image.size == mask.size == (512, 512)
generator = torch.Generator(device="cuda").manual_seed(42)

with torch.inference_mode():
    result = pipe(
        prompt="a silver ring with a blue gemstone",
        image=image,
        mask_image=mask,
        generator=generator,
        num_inference_steps=30,
        guidance_scale=7.5,
        strength=0.99,
    ).images[0]
result.save("outputs/editor_smoke.png")
```
Create outputs/ before running. Keep the model's safety components enabled for normal use. A safety-filtered/blank result is inconclusive for this project, not evidence that pixel protection succeeded.

For a clean/protected pair, call with freshly seeded generators and the same pipeline settings. Do not compare different masks/prompts/resolutions.

## 7. First defense execution
Official README example, inside the official repository after setting up its sample assets:
```bash
python main.py --config-name diffusionguard orig_image_name='keanu.png' mask_image_names='["keanu_mask.png"]'
```
Before this runs, adapt the resolved inpainting model path through the ACTUAL configuration field found in source. The original remote checkpoint name may be unavailable. Use a project wrapper to pass explicit input paths and output directory after reproduction; do not permit client-supplied Hydra overrides.

Make test PNG inputs with controlled geometry rather than relying on a downloadable face sample. Show that image gradients update and exported output respects the budget. A single successful CLI exit is not efficacy evidence.

## 8. Optional DiffVax
Source: https://github.com/ozdentarikcan/DiffVax
Issue to reproduce: https://github.com/ozdentarikcan/DiffVax/issues/2
The README advertises a pretrained file and demo; an open issue reports visible perturbations and an unused epsilon. Verify actual bytes, origin, load success and image fidelity. No unrestricted untrusted pickle loading.
If unavailable, malformed or too visibly noisy, mark optional adapter unavailable and keep the DiffusionGuard path.
After clipping/repairing any perturbation bounds, rerun edit tests; clipping can remove its effect.
Do not retrain a new immunizer as part of v1.

## 9. Optional WAM
Source: https://github.com/facebookresearch/watermark-anything
The official repository has pretrained SA-1B/MIT weights and other weights with different terms. Choose weights intentionally, record their license and snapshot.
The research repository is archived; isolate dependencies and pin the working environment.
Use only after main protection passes. Compare both WAM/protection layer orders. Report spatial watermark evidence, not a universal malicious-edit detector.
A short recovered export ID is a lookup hint, not a digital signature or proof of ownership.

## 10. Hardware and memory
Run scripts/setup/check_environment.py --require-cuda in the ML environment; it does not load model weights.
A small VRAM device may run some editor inference but fail during gradient-based protection. Batch size 1, careful dtype and compatible attention slicing can be explored; do not assume inference offload options support gradient optimization.
Do not quantize or offload the defender blindly; changes to gradients may change efficacy.
Measure peak allocated/reserved memory per job and free models between incompatible environments. Explicit OOM error offers lower supported resolution/profile or a larger GPU, not a false fallback.
Use 12–16 GB+ GPU capacity as a planning allowance, not a benchmarked guarantee. The full DiffVax demo README requests 8 GB+; test the actual pipeline. SDXL is optional and heavier.

## 11. Sources checked for this runbook
- https://github.com/choi403/DiffusionGuard
- https://github.com/choi403/DiffusionGuard/blob/main/requirements.txt
- https://github.com/choi403/DiffusionGuard/blob/main/main.py
- https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-inpainting
- https://huggingface.co/diffusers/stable-diffusion-xl-1.0-inpainting-0.1
- https://pytorch.org/get-started/previous-versions/
- https://github.com/MadryLab/photoguard
- https://github.com/ozdentarikcan/DiffVax
- https://github.com/facebookresearch/watermark-anything

