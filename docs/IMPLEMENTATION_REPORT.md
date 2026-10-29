# ImageShield execution report

## 29 October 2026 — finished landing and research workspace

User explicitly requested visual finishing first, larger fonts, a black/white
gradient landing page, image-and-arrow pipeline cards, clear mask overlays,
use cases, and a local SD1.5 Playground with preload buttons. Current routes:
landing `/`; workspace `/dashboard`; hash tabs Comparisons, Pipeline,
Playground and Use cases. The latest Playground request supersedes the earlier
read-only-only scope: browsing remains passive, while one explicit Run SD1.5
click starts a matched local edit.

The user-provided portfolio ZIP was inspected and safely extracted as a
design reference. Its serif/sans typography and diagonal light structure were
adapted into a monochrome landing page; personal content and archive scripts
were not reused/executed. Local Inter/Instrument Serif assets and licenses are
retained. See DESIGN_REFERENCE_NOTICE.md. No external font requests or
analytics were added. After the user's instruction to stop delegation, the
primary agent alone completed integration, state fixes and validation.

Raw edit masks remain unchanged. The UI now shows a cyan translucent region
and outline over the original photo; raw masks are separately accessible.
All eight Pipeline cards contain an actual saved/context image and descriptive
text, connected in numbered order with arrows. Unsaved internal representations
are explicitly labeled as previews rather than fabricated latent images.
Readability increased to14–16px body/control text and larger headings.

Playground offers Preload Shorts/Cap/T-shirts, prompt, seed and PNG/JPEG85
controls, separate Load saved comparison and Run SD1.5 actions. It uses the
existing modern isolated runtime with inference CPU offloading. Sample IDs,
prompts, seeds and channels are validated; one job runs at a time. Model
errors recycle the ML child; the parent watchdog and idle release remain.
Results are whitelisted private local files and show safety-filter status.
Restored live results synchronize with their original selected sample.

Final actual browser verification: landing and every tab at1440/390px, local
fonts loaded, all visible images loaded, no JS/CSP errors or horizontal
overflow. Browsing/preloading caused zero model runs. One explicit Playground
run completed with real unfiltered matched SD1.5 outputs:
`fecf3d89-1d64-4210-ab2d-846ec87acc04`. Screenshot/receipt:
`outputs/workspace-qa/`. API checks passed for cross-origin POST403, invalid
seed422, invalid sample422 and unknown result404. Existing core suite last
passed29 tests during this work. No paid/cloud image inference was used.

Use cases are labeled potential research applications: artistic work,
catalog imagery, personal-photo consent, complementary provenance workflows,
and education. Known fidelity failures, compression bypass and reported
ChatGPT/FLUX bypasses remain explicit. The private GPT command `/EDDIT` was
provided without its instructions; no fake GPT integration was implemented.

## 29 October 2026 — pipeline tab and ordered image flow

Current preloaded dashboard now has real Comparisons/Pipeline hash tabs.
Comparisons places Original → Protected candidate → Tampered result in that
order, with the tampered-original control and editing mask below. All three
sample selectors share this layout; no model jobs or mutation endpoints were
added. Pipeline shows eight method-specific steps drawn from actual saved
run parameters, including preparation, mask, transform/objective, optimization,
PNG export, measured fidelity, matched edit settings and result comparison.
Failed quality measurements remain explicit.

Actual Edge QA passed all three samples at1440/390px, both views, all5 images,
correct three-image order, eight pipeline steps and pipeline-view restoration
after reload. No overflow, script errors or mutation requests; metadata is
fetched once per page load. Updated screenshots/receipt are under
`outputs/local-sd15-demo/preloaded-qa/`. URL remains127.0.0.1:8001.

## 29 October 2026 — current dashboard is preloaded and read-only

The user's latest instruction supersedes the live-run UI: preload a few
images; do not run models from the dashboard. The live demo server and its
ML child were stopped, and `backend/research_demo.py` now has no ML imports,
job runner, POST endpoint or polling. All mutation requests return405.

`http://127.0.0.1:8001/` displays three existing measured comparisons:
Shorts / DCT-Shield base; Cap / PhotoGuard encoder; T-shirts / DiffusionGuard
smoke. Each selector loads the actual clean/candidate inputs, mask and paired
saved outputs, with its recorded prompt, seed, method and quality state.
Outputs are labeled Saved, not presented as newly generated or uniformly
successful protection. Shorts and cap failed original fidelity; T-shirts
passed fidelity but have no established edit-resistance claim.

The minimal monochrome dashboard makes one metadata GET, serves images from
an explicit whitelist and starts no GPU work. Startup/import verified not to
load Torch. POST rejection, unknown artifact and invalid Host checks pass
(405/404/400). Desktop/mobile browser QA covers all three selectors and checks
five loaded images each, no overflow, no script errors and zero mutation
requests. Current receipts/screenshots:
`outputs/local-sd15-demo/preloaded-qa/`. Earlier live-run records below are
historical only. Restart with `scripts/start-research-demo.ps1`.

## 29 October 2026 — live local SD1.5 dashboard

Added a separate loopback-only dashboard at `http://127.0.0.1:8001/`, launched
by `scripts/start-research-demo.ps1`. It preloads the exact clean/DCT candidate
and canonical white-editable mask, accepts a prompt/seed and PNG or JPEG85
channel, and runs actual matched local edits through the existing isolated
MLRuntime. Completed images are served from an explicit per-run whitelist;
inputs/artifacts are not mounted as a public output directory. Concurrent
submissions are rejected, and original sources remain untouched.

User requested a minimal Vercel-style layout. GPT-6.1 Sol built and refined
the three dedicated frontend assets: monochrome navigation/panels, compact
controls and large comparison cards, with no marketing filler. A concise
research badge retains the material visible-noise/fidelity limitation.

Initial live checks failed under the machine's current Windows memory/commit
pressure (first host loading, then CUDA allocation). Failure runs remain in
`outputs/local-sd15-demo/`; no saved comparison was substituted for a live run.
The tested fix uses the separate modern ML environment, loads the UNet onto
CUDA before other components to lower host peak, and enables inference CPU
offloading. These settings are opt-in on this research route; the main
protection pipeline's default loading behavior is unchanged. Actual Torch/
Diffusers versions and execution strategy are saved with each experiment.

A real matched PNG edit completed successfully with no safety filtering:
run `afc83c53-8999-4701-9f7b-19158db9a298`. Visual inspection reproduces the
earlier pose/hand/shoe distortion on the candidate branch while the clean
branch produces plausible green shorts. The dashboard restores completed
results after reload. Actual Edge desktop1440/mobile390 checks loaded all5
images with no JavaScript errors or horizontal overflow. Private screenshots
and receipt: `outputs/local-sd15-demo/qa/`.

Loopback host, cross-origin POST, invalid seed and unlisted artifact checks
passed (400/403/422/404 respectively). Main API/worker suite:29 tests passed,
with the existing upstream Starlette/httpx warning. Current scope remains
observed older-model disruption; source fidelity failed and JPEG can bypass
the effect. No ChatGPT or universal protection claim is made.

## 29 October 2026 — teacher demonstration scope narrowed to an older editor

The user explicitly says the teacher demonstration may use an editor other
than GPT Image. Recommended the already-installed
`stable-diffusion-v1-5/stable-diffusion-inpainting` at the pinned registry
revision, using the actual DCT-Shield base candidate and saved edit mask.
The prior PNG-channel paired outputs exhibit visible pose/body distortion;
clean controls produce plausible green-shorts edits. Exact shared settings
are DDIM,512x512,30 steps,CFG7.5,strength0.99, with seeds11/22/33.
Raw settings, prompt and outputs remain under
`outputs/research-2026-10-28/dct-shield/`.

This is a bounded demonstration of observed disruption on an older model.
The candidate itself has visible noise and failed fidelity; JPEG85 restored
plausible edits. Neither issue should be omitted from a project claim. The
recent single-CLIP kit is a different defense and is not substituted for the
DCT candidate. No new optimization, external inference or model download was
needed to identify this existing local demonstration.

## 29 October 2026 — subsequent bypass reports and stronger diagnostic

The user reports that both ChatGPT and the FLUX editor they tried successfully
edited the delivered experimental kit. Exact model snapshots/prompts/outputs
are not supplied, so these are recorded user-reported bypasses, not a scored
benchmark. No working frontier defense is established.

Read the new pasted evidence audit in full. It concludes that no verified,
reproducible, locally feasible protection against the exact current ChatGPT
editor is established. Its claim of runnable VETO source conflicts with a
fresh direct request to github.com/multimodal-ai-lab/VETO (404); a search-cached
README is visible but does not establish current source availability. No
official runnable MIRAGE release was verified by the new bounded search.

The delivered kit had a final1/255 RGB bound. The previously retained
5000-step8/255 native-shorts probe is materially stronger but failed source
quality (31.46dB/.79008). It was not in the delivered kit and has no recorded
frontier test. A hash-checked copy is now available at
`C:\Users\ASUS\Downloads\ImageShield_STRONG_DIAGNOSTIC_quality_failed_shorts.png`
for one optional user-run diagnostic test. It is visibly degraded and **not a
quality-approved protection deliverable**. A refusal on this file would not
meet the combined fidelity/effectiveness objective; a successful edit would
provide further negative evidence for the current single-CLIP configuration.
No new optimization, downloads, paid queries or external image uploads were
performed for this diagnostic. Full MIRAGE ensemble/target assets and exact
current-model effectiveness remain unverified.

## 29 October 2026 — three-image frontier test kit delivered

Subsequent user feedback: the kit "DIDNT WORK" against the model they identify
as GPT Image2. Record this as a **user-reported bypass**, not successful
protection. Exact tested input(s), prompt(s), model snapshot and output images
have not yet been supplied, so no independently reviewed rate can be computed.
The delivered artifact hashes remain unchanged. The user next asked about
testing FLUX; local Kontext weights are still absent. No external FLUX
inference or new large model download has been performed for that request.

User narrowed the next deliverable to three locally exported candidates for
manual ChatGPT/frontier testing. GPT-6.1 Sol performed the read-only exporter
review; its two rerun/publication findings were fixed before the full run.
Existing outputs and Downloads archives cannot silently be overwritten.

The shared-encoder batch retains independent per-image losses, summed before
autograd, with frozen eval-mode CLIP. Three real tiny-CLIP architecture checks
passed: cross-image gradients are zero and batched global/patch gradients
match individual execution. These are correctness checks, not efficacy tests.

The 5,000-step three-image batch completed in1577.76 seconds with about1.92GB
peak CUDA allocation. Its 2/255 exports failed the unchanged SSIM threshold:
T-shirts0.97978, cap0.97325, shorts0.97810. Diagnostics and hashes remain in
`outputs/frontier-test-kit/2026-10-29/`. No failed kit was published.

A further500-step warm-start refinement projected those candidates to1/255.
Clean-reference hashes were verified before reusing each candidate. The final
files pass the existing gate:

| Image | Export dimensions | PSNR dB | SSIM |
|---|---|---:|---:|
| Printed T-shirts | 1024x683 | 49.860 | 0.99439 |
| Black cap | 819x1024 | 49.332 | 0.99306 |
| Pinstripe shorts | 768x1024 | 48.788 | 0.99403 |

Final project artifacts: `outputs/frontier-test-kit/2026-10-29-quality/`.
User-ready folder:
`C:\Users\ASUS\Downloads\ImageShield_Frontier_Test_Kit_2026-10-29`,
with matching `.zip` next to it. Both contain three explicitly EXPERIMENTAL
candidate PNGs, clean references, settings/hashes and instructions allowing
arbitrary user-selected prompts. Source files in D:\dnew remain untouched.

The actual published PNGs decode, match their clean-reference dimensions and
match both manifest and ZIP hashes; ZIP CRC checks pass. The gallery passed
Edge checks at1440/390px with three loaded images, no missing links, script
errors or horizontal overflow. Verification receipt:
`data/frontier-kit-verification.json`; browser receipts are in the final
project output directory. Original API/worker environments remain separate.

**Effectiveness remains untested on ChatGPT/frontier editors.** This is the
disclosed reduced single-CLIP text-only MIRAGE-informed method, not the full
eight-model paper or its reported rate. No source image was uploaded to an
external inference service. Next evidence is the user's exact-model paired
clean/protected tests. FLUX-specific results cannot establish ChatGPT success.

## 28 October 2026 — latest-paper audit and local research implementations

The user supplied an additional DOCX and DCT-Shield/DiffVax links. Both source
documents were treated as references, with no external image inference or
Colab upload. Corrections to release/version claims are recorded in
`docs/research/USER_REPORT_RECONCILIATION.md`. The dated candidate comparison,
primary-service metadata and detailed MIRAGE audit are in `docs/research/`.

- Verified and executed the official DiffVax checkpoint on three user images
  in both released-demo BatchNorm mode and explicitly adapted eval mode.
  Demo-mode fidelity failed on all three. Two eval cases pass aggregate
  fidelity, but the released method enforces no RGB budget and has large
  isolated pixel changes. It has not been added to the product success flow.
- Implemented PhotoGuard's complete 1,000-step released encoder profile using
  the installed pinned SD1.5 inpainting VAE (a disclosed model adaptation).
  Runtime 527.91 seconds; source fidelity failed: PSNR31.91, SSIM0.6588.
  PhotoGuard and both DiffVax modes each completed three paired local editor
  seeds: nine pairs / eighteen generated edits. Clean outputs hash-match
  across methods for every seed. All nine pairs were unfiltered. Visual QA
  shows edited green caps in the candidate outputs as well as the controls;
  changed framing/backgrounds do not establish unusable editing. No formal
  efficacy percentage has been assigned.
- Implemented and ran an explicitly reduced, single-CLIP MIRAGE-informed
  probe. Its full 5,000-step 768x1024 run took583.70 seconds. The source fidelity
  failed: PSNR31.46, SSIM0.7901, visible artifacts. A rising surrogate score is
  not a moderation refusal. Missing target images and seven ensemble members
  mean this is not a MIRAGE reproduction and cannot inherit author rates.
- Added a separate paper-derived DCT-Shield base adapter. It optimizes
  post-quantization coefficients rather than substituting JPEG EOT for that
  algorithm. Official code is unavailable (linked repository empty). JPEG
  implementation choices, zero initialization, unmasked base scope and reused
  VAE are disclosed. Six CPU transform/gradient checks pass. The 1,000-step
  local run completed in447.83 seconds; coefficient maximum delta1.0 meets
  the configured coefficient bound. Source fidelity failed: PSNR27.19,
  SSIM0.5477 and RGB maxdiff0.3412 (no RGB constraint is in the method).
  Six matched pairs / twelve generated edits completed over PNG and real
  JPEG85 4:2:0 channels, with seeds11/22/33. Visual inspection shows distorted
  native outputs, while the JPEG85 candidates again yield plausible edited
  green shorts. This is negative evidence for this local base-profile
  configuration, not a reproduction of every paper variant. No success
  percentage is inferred. Logs: `.cache/dct-shield.log` and `dct-pairs.log`.
- Added CaD Eq13 and MIRAGE arithmetic kernels, with six numerical checks
  passing. CaD captures normalized text AND image Q/K and applies joint RoPE.
  Full pretrained execution is **not validated**: local gated Kontext weights
  are absent, no HF authentication is configured, and the full-resident loader
  cannot fit the RTX4050 6GB. It fails preflight before loading. A separate
  modern environment is installed and locked: Torch2.6.0+cu124,
  Diffusers0.35.2, Transformers4.57.1, Accelerate1.11.0. Official wheel hashes
  matched; pip check passed. Nine real tiny FLUX/VAE architecture checks
  pass, including a nonzero RGB gradient through VAE mode/scaling, Kontext
  packing, joint text/image RoPE and attention. Weights are random and tiny;
  these checks are explicitly not pretrained-model or protection evidence.
  Exact records: `CAD_FLUX_ARCHITECTURE_CHECK.json`, `FRONTIER_ENVIRONMENT.json`,
  `FRONTIER_WHEELS.json` and `FRONTIER_PREFLIGHT.json` under `docs/research/`.
- The existing API/worker environment is unchanged; all29 tests pass, with
  one upstream Starlette/httpx deprecation warning. Git is initialized; private
  images, models, source clones, outputs and environments remain ignored.
  The private research gallery passed actual Edge checks at1440/390px: all64
  images load, no JavaScript errors or horizontal overflow. Screenshots and
  exact checks remain under ignored outputs.

View `outputs/research-2026-10-28/index.html` for actual local artifacts and
failed gates. No frontier-model protection rate or universal anti-editing
claim is established. Full current-model validation remains required.

## 28 October 2026 — speed optimization and real user-image tests

- Replaced per-job model reloads with a single serialized persistent ML child. The API still never imports Torch. Model reuse ends after five idle minutes; cancellation, model errors and timeouts recycle the child. Result files publish atomically. Windows launcher-aware process-tree cleanup and an actual-worker PID watchdog prevent orphan GPU work.
- Benchmarked the same 20-step synthetic input without lowering iterations or quality thresholds: cold/full checkpointing **22.48 s**, warm/full checkpointing **13.79 s**, warm/VAE-only checkpointing **12.83 s**. The final option passed the same visual gate and used about 4.05GB peak allocated CUDA memory. This is about **43% less elapsed time** than the measured cold run, not a guarantee for every image. All three runs' metrics/hashes are preserved under `data/speed-benchmark/`; floating-point outputs were not byte-identical.
- Selected three real files from `D:\dnew`: printed T-shirts, black cap and pinstripe shorts. Source files remained untouched. Each used the actual upload/API/queue/defense and a same-prompt/same-mask/fresh matched seed-11 editor pair. All first 4/255 attempts failed the unchanged quality gate and are preserved as rejected diagnostics. All 2/255 retries passed.

| Image | PSNR dB | SSIM | Warm protection seconds |
|---|---:|---:|---:|
| Printed T-shirts | 46.2474 | 0.983475 | 13.156 |
| Black cap | 45.4520 | 0.980129 | 13.281 |
| Pinstripe shorts | 46.7438 | 0.984583 | 15.922 |

- The complete three-image batch, including rejected attempts and paired edits, finished in about148 seconds. No pair was safety-filtered. The images demonstrate execution and fidelity, not reliable edit prevention: the requested fabric/color/graphic preservation was imperfect on clean inputs too, and formal human scores remain pending. Review results without counting unusable clean edits as defense success.
- User-ready tamper kit: `outputs/dnew-tests/2026-10-28/`, with `index.html`, `comparison.jpg`, per-image `clean.png`, `protected.png`, `edit-mask.png`, clean/protected AI edit outputs, rejected diagnostics and exact `results.json`. The whole outputs directory is Git-ignored and is not mounted publicly.
- Actual CUDA cancellation after iteration1 completed in **1.92 seconds**, published no result, and a subsequent fresh-process protection succeeded with PSNR46.2430dB/SSIM0.983433. Private receipt: `data/dnew-tests/cancellation-recovery.json`.
- Added CPU regressions for reuse, dead-child restart, idle shutdown, atomic files, errors, worker PID ownership and forced Windows descendant cleanup. The complete suite now contains29 tests. The previous report below is retained as the dated initial-build evidence.

Local project: `D:\IS\ImageShield`. Date: 2026-10-27. This report distinguishes working infrastructure from unverified model effectiveness.

## Implemented and checked

- Extracted and read the supplied build handoff; kept its original reference documents intact.
- Initialized Git at the project root. `.gitignore` excludes private data, secrets, environments, source checkouts, downloaded models and caches. No commit has been created.
- Created the FastAPI API, validated settings, signed per-session ownership, bounded image decoder/normalizer, binary mask validation, private artifact routes, SQLite queue, transactional claim, one-worker lock, progress/heartbeat/cancellation, timeout handling, subprocess isolation, paired experiments and bounded review rubric.
- Created the responsive vanilla browser interface with theme and hash navigation, drag/file upload, transparent-PNG consent, pointer/numeric mask editing, export metadata, job cancellation/reconnect, downloads, Attack Lab, all-seed reviews and explicit unavailable phase-2 verification.
- Added the real upstream DiffusionGuard adapter and paired SD1.5 editor. Fixed upstream mask polarity and normalized epsilon units; chose explicit single-mask operation to preserve selected-region topology. This is an adaptation, not paper reproduction.
- Resolved source commit `96e28c19124fbb0e0671f48931ffed180775c7ea` and model snapshot `8a4288a76071f7280aedbdb3253bdb9e9d5d84bb`. The registry contains downloaded model sizes/hashes; available official LFS SHA256 values were matched.
- API CPU doctor passed. Running `/health` confirmed API liveness and worker heartbeat. CPU-only startup does not import Torch.
- `python -m pytest -q` in `.venv`: **21 passed**, with one upstream Starlette/httpx deprecation warning. Tests include deletion/claim races, saved-input failure handling, cancellation during quality assessment, ownership, mask geometry, queue caps, OOM, quality rejection, uncertain scores and safety-filter exclusions. Unit ML subprocess results are test fixtures, not measured model evidence.
- Real browser checks at widths 1440 and 390 passed with no JavaScript/CSP errors or horizontal overflow. Pointer and background-mask pixel checks also passed. Evidence: `docs/FRONTEND_QA.md`, `docs/screenshots/`.

## Verified runtime results

- API and worker launched locally through `scripts/start.ps1` at http://127.0.0.1:8000.
- Hardware detected: NVIDIA GeForce RTX 4050 Laptop, 6141 MiB VRAM. PyTorch CUDA doctor passed.
- Model download completed, including fp16 UNet, VAE, text encoder and safety checker. Large network transfers required resumable validated byte ranges.
- Official CUDA Torch 2.1.1+cu121 and torchvision 0.16.1+cu121 installed. `pip check` passed; API and ML locks now reflect installed packages. Accelerate 0.24.1 was added for efficient model loading.
- Initial runtime revealed a Diffusers 0.24 API mismatch (`pipe.enable_vae_slicing`); corrected to `pipe.vae.enable_slicing`. Attention slicing then exhausted GPU memory. The tested working path uses PyTorch scaled dot-product attention and zero-dropout gradient checkpointing with fixed weights and live image gradients.
- Actual upstream two-region mask semantics, 20-step optimization and matched seed-11 paired editing completed. Peak allocated CUDA memory: 4,052,472,320 bytes; peak reserved: 4,427,087,872 bytes. Source remained unmodified.
- The 4/255 synthetic smoke export measured PSNR 42.1831 dB and SSIM 0.941353: **quality rejected**. A real browser 2/255 run measured 46.0077 dB and 0.975002: **quality rejected**. Failure evidence is preserved; the UI offered diagnostic inspection rather than successful protection downloads.
- A real browser 1/255 run passed the quality gate: PSNR **50.6255 dB**, SSIM **0.992204**, maximum saved-pixel difference 2/255 (budget 1/255 plus 1/255 quantization allowance). Protection took **23.86 seconds**, including subprocess/model startup. This is a lower-budget engineering smoke, not evidence of stronger defense.
- That uploaded image reached the actual worker/adapter, downloaded successfully, and generated a four-image Attack Lab comparison with fresh matched seed 11 and 30 inference steps. Neither edit was safety-filtered. The browser check passed without JavaScript errors; authentic 1440/390 screenshots are in `docs/screenshots/*-real-*.png`. Private session state is excluded from Git under `data/browser-smoke/`.
- A separate real JPEG quality-85/subsampling-2 channel run completed. Its clean/protected post-JPEG input artifacts differ from the original untouched input IDs, so evidence reflects the actual tested pixels. `docs/screenshots/jpeg-channel-smoke.json` preserves the experiment. It is explicitly synthetic stress testing, with no Instagram claim.
- Visual inspection found plausible edits in both outputs; no clear disruptive effect is established. No human scores were fabricated. The experiment remains inconclusive with review pending. The synthetic test establishes working execution, not useful edit prevention.
- `model-registry.json` now marks the exact local model/source as runtime-smoke validated and explicitly effectiveness-unreviewed. Portable measured evidence is in `docs/GPU_SMOKE_RESULTS.json`, `docs/screenshots/gpu-browser-qa.json`, and the preserved quality-rejection JSON.

## Remaining research gates

1. Human visual review and a controlled efficacy study on consented/licensed natural images. A useful defense must preserve quality and reduce usable edits under the recorded conditions. The synthetic smoke has not demonstrated this.
2. The 800-iteration profile and exact original contour-augmentation reproduction have not been benchmarked. The app uses the audited fixed-mask adaptation and never calls it paper reproduction.
3. PhotoGuard/matched-noise controls, unseen masks/editors, real Instagram/Photoshop copies, watermark/signature phase 2 and broader showcase cases remain gated by real efficacy evidence. They are explicitly unavailable/deferred rather than represented by fabricated outputs.

Human review and a controlled efficacy benchmark have not been executed. No observed-disruption, Instagram/Photoshop, universal anti-editing, native-resolution, transfer, watermark or signature claim is established. M4–M7 extensions remain behind the primary pipeline gates.

## Resume

Read `AGENTS.md`, this report, `docs/UPSTREAM_AUDIT.md`, `.cache/gpu-smoke-checkpointed.log` and `.cache/gpu-browser-qa-budget1.log`. Check `/health` and pending jobs before launching duplicate GPU work. Future delegated work must use explicit GPT-6.1 Sol or lower, with file ownership and integration review. All previous delegated agents hit their reported usage limit; the primary agent continued setup, repaired runtime issues and completed the real GPU/browser checks.

No automatic chat-wakeup tool is available in this session. A running PowerShell process can continue local installation/tests without a chat turn, but it cannot automatically restart the assistant after a quota reset.
