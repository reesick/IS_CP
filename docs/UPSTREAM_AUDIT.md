# DiffusionGuard source audit

Inspected locally on 27 October 2026. This file distinguishes source inspection
from runtime evidence; a source checkout is not an efficacy result.

- Official source: https://github.com/choi403/DiffusionGuard
- Checked-out commit: `96e28c19124fbb0e0671f48931ffed180775c7ea`
- Checkout: `third_party/DiffusionGuard`; upstream tracked files are unmodified.
- Inspected: `main.py`, `attacks/__init__.py`, `attacks/common.py`,
  `attacks/attack_diffusionguard.py`, `utils/utils.py`,
  `utils/mask_generation.py`, `config/diffusionguard.yaml`, and requirements.
- There is no LICENSE file in this checkout. Source redistribution terms remain
  unconfirmed; attribution does not supply a missing license.

## Actual objective and configuration

The adapter calls upstream `attacks.protect_image`, which dispatches to
`generate_perturbation` and the actual DiffusionGuard `attack_pipeline`.
The loss is negative UNet noise-prediction L2 norm, divided by batch size,
at the first timestep from the configured scheduler. The implementation
descends the sign of the loss gradient with respect to masked source pixels,
projects into the perturbation budget, and clips the normalized image range.
No diffusion model is trained and no random-noise fallback is used.

Source defaults are 800 iterations, one gradient repetition, batch size one,
four scheduler timesteps, normalized epsilon `16/255`, normalized step size
`1/255`, and contour-shrink mask augmentation. Input images use `[-1,1]`;
therefore a source epsilon `16/255` corresponds to `8/255` in `[0,1]` RGB.
The application receives RGB epsilon and doubles it for upstream configuration.
The upstream PNG conversion truncates floats to byte values. Saved-file budget
checks therefore permit a documented one-byte quantization tolerance.

## Mask semantics and deliberate adaptation

The browser/API canonical mask is white for editable pixels. Upstream mask-image
arguments instead mark the retained region white. The adapter explicitly inverts
the canonical mask, then upstream `get_mask(..., mode="single")` converts this
back to its internal white-editable tensor. Gradient updates are multiplied by
the retained-pixel mask.

Upstream contour-shrink uses `cv2.RETR_EXTERNAL` and fills the selected contour.
A retained background surrounding a central editable object contains a hole;
external-contour filling can erase that hole. Consequently the application
uses the upstream **single known mask** policy for both supported edit modes.
This preserves selected-area and background-edit mask geometry. It removes
contour augmentation and must not be described as a full paper reproduction or
evidence of robustness to unseen masks.

Application research profile: 800 iterations of the upstream objective with
the fixed known mask. Smoke profile: 20 iterations, explicitly not a research
benchmark. The actual epsilon is recorded per run.

## Other adaptations

- Local-only model snapshots; no import-time or pipeline-loader network fetch.
- Model parameters remain frozen; image gradients stay live. During protection,
  Checkpointed modules use training mode solely to activate Diffusers 0.24 gradient
  checkpointing, after checking that every Dropout layer has probability zero.
  These GroupNorm/LayerNorm models do not update batch statistics. Editing
  restores evaluation mode and runs without gradients. The measured faster
  profile checkpoints VAE only and leaves UNet in evaluation mode; the previous
  both-module checkpointing path remains configurable and recorded per run.
- PyTorch scaled dot-product attention and VAE slicing reduce memory. The first
  attention-slicing attempt exhausted the 6GB GPU; the checkpointed/SDPA path
  completed. This numerical execution adaptation is recorded in provenance.
- A small iterator wrapper reports actual iteration boundaries and checks
  cancellation without changing the upstream objective or optimizer.
- Source HEAD and tracked-code cleanliness are verified before loading; drift
  from the audited revision produces an unavailable error.
- Non-finite outputs are rejected. Quality acceptance is measured separately
  on the decoded PNG by the worker, and does not imply editing disruption.
- Model safety components remain enabled for paired editing. Safety-filtered
  outputs are inconclusive, never counted as defense success.

## Paired editor

The adapter loads `StableDiffusionInpaintPipeline` from the resolved local
SD1.5 snapshot. Both calls use the same pipeline/scheduler, prompt, negative
prompt, canonical mask, resolution, guidance 7.5, strength 0.99, and 30 inference
steps. Each call receives a fresh CUDA generator reset to the recorded seed.

The JPEG channel is a synthetic quality-85, chroma-subsampling-2 stress test,
applied identically to clean and protected inputs. Actual decoded input pixels
are saved as separate artifacts. It is not an Instagram round trip.

## Runtime evidence

`backend/app/ml/smoke.py` tests actual upstream single-mask conversion for a
central editable rectangle and its inverse. Its real CUDA smoke creates a
clearly labeled synthetic input, runs 20 upstream iterations at RGB epsilon
`4/255`, checks nonzero saved pixel change and budget, and optionally runs one
paired edit with seed 11. Evidence belongs in `data/ml-smoke/evidence.json`.

The actual two-region mask test, 20 optimization iterations and paired seed-11
editing completed on the RTX 4050. Peak allocated CUDA memory was 4,052,472,320
bytes and peak reserved memory 4,427,087,872 bytes. The exported pixels changed,
with maximum difference 5/255 (budget 4/255 plus byte-quantization tolerance).
PSNR was 42.1831 dB and SSIM 0.941353. This input therefore **failed** the
provisional SSIM quality gate despite completing computation. Both edit outputs
were generated without safety filtering; effectiveness remains unreviewed.
This is synthetic smoke evidence, not a reproduction or efficacy benchmark.

No universal AI-proof, Photoshop-proof, Instagram-safe, unseen-mask, SDXL, WAM,
or quantitative disruption claim follows from this wrapper or a smoke exit code.
