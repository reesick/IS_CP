# ImageShield

A local research app for generating adversarial image perturbations with the actual DiffusionGuard algorithm, then comparing matched Stable Diffusion inpainting edits. The API and interface run entirely on this machine. Downloads fetch upstream source and pretrained weights; images are never uploaded to a hosted inference service.

## Run on this machine

From PowerShell:

```powershell
Set-Location D:\IS\ImageShield
powershell -ExecutionPolicy Bypass -File scripts/start.ps1 -Open
```

Open http://127.0.0.1:8000. To stop both local processes:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/stop.ps1
```

For a fresh installation, run `scripts/bootstrap.ps1` first. See that script's parameters for optional ML setup and download. The installed API environment is `.venv`; the CUDA/legacy Diffusers environment is `.venv-ml`. Their exact resolved versions are recorded in the requirements lock files. Python 3.11 is used here because it is installed and supports the selected wheels; the source pack's Python 3.10 recommendation is not a runtime requirement of the adapter.

Manual launch in two terminals is also supported:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
.\.venv\Scripts\python.exe -m backend.app.worker
```

## Use

1. Choose a PNG/JPEG image, up to 10 MiB and 20 megapixels. Transparent PNGs receive an explicit background preview before browser upload. The research canvas is a fitted and letterboxed 512 × 512 RGB PNG, with neutral `#f4f4f5` compositing and padding. It is never silently restored to native resolution.
2. Draw a rectangle or enter its coordinates under **Refine region**. Choose editing inside the region or replacing its background. At least 5% and at most 95% of real image pixels must be editable; letterbox padding is excluded.
3. Choose **Protect image**. The smoke profile runs 20 actual optimization iterations; the research profile runs 800. Both use the original upstream objective with an explicit known mask. Neither is a claim of paper reproduction or unseen-mask protection. The default perturbation budget is 4/255 in RGB units.
4. A saved export must measurably differ, respect the pixel budget plus 1/255 quantization tolerance, and pass PSNR ≥35 dB and SSIM ≥0.98. The app records human visual review as pending. A quality rejection exposes no ordinary protected download.
5. Use **Attack Lab** with the same mask. For each seed the editor resets a fresh generator for the clean and protected calls. Local PNG and synthetic JPEG quality-85 tests are separate conditions. Review the four images and score requested-edit completion, realism and retained-subject fidelity.

Successful computation means protection was generated; it does not establish edit prevention. Only completed human reviews can produce a scoped observed-disruption or bypass result. Safety-filtered outputs remain inconclusive. This project makes no universal AI-proof, Photoshop or Instagram claims.

## Architecture and privacy

FastAPI serves a vanilla HTML/CSS/JavaScript interface from the same origin. SQLite WAL persists assets, jobs and experiment evidence. A separate worker claims one queued job transactionally, then invokes a fixed isolated ML Python executable using argument lists with `shell=False`. The API never imports Torch or downloads models. Progress reflects actual iterations. A single worker lock prevents concurrent GPU jobs; a 30-minute configurable timeout, cancellation checks, heartbeats and restart interruption handling bound jobs.

All originals, references, exports, logs, sessions and SQLite state stay under `data/`, excluded from Git and static routes. Session-bound opaque artifact IDs authorize downloads. The local session cookie is signed, HttpOnly and SameSite Strict. Mutations reject foreign origins; loopback hosts, byte/pixel limits, queue limits and rate limits are enforced. Exported PNGs omit original EXIF. Delete an image to remove associated registered artifacts; active work is cancelled before deletion completes. Runtime logs/request metadata and empty directories may remain locally. This is a local single-user research service, not a public deployment with production authentication.

Configuration: `IMAGESHIELD_DATA`, `IMAGESHIELD_ML_PYTHON`, `IMAGESHIELD_JOB_TIMEOUT` (60–86400 seconds), and optional `IMAGESHIELD_MODEL_PATH`. Set environment variables before launch or copy `.env.example` to `.env`; existing process environment values take precedence. Configuration is validated at startup.

The worker now keeps one isolated ML process/model loaded across consecutive jobs. `IMAGESHIELD_PERSISTENT_ML=true` is the default; its CUDA model is released after `IMAGESHIELD_MODEL_IDLE_SECONDS=300` idle seconds. Errors, cancellation and timeouts recycle the child. A worker-PID watchdog and Windows process-tree termination prevent orphan GPU jobs. Set persistent mode to false to restore per-job subprocesses. The tested faster profile uses VAE checkpointing and `IMAGESHIELD_UNET_CHECKPOINTING=false`; true restores the earlier UNet recomputation setting. The algorithm, iteration counts and quality thresholds are unchanged.

An actual same-input 20-iteration benchmark measured 22.48 seconds with a cold model, 13.79 seconds with the cached model and both checkpoints, and 12.83 seconds with the cached model/VAE checkpoint only. All three saved outputs passed the same quality gate. CUDA floating-point execution was not byte-identical across runs; exact files, hashes and metrics are recorded under `data/speed-benchmark/`.

Three actual `D:\dnew` images were tested and exported to `outputs/dnew-tests/2026-10-28/`: protected PNGs, clean references, canonical masks, matched edits, quality rejections and a local HTML comparison. These files are private and Git-ignored. Source files were not changed. See that folder's `results.json` for all attempts and `index.html` for viewing; a quality pass is not proof that tampering is prevented.

## Validation and evidence

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv-ml\Scripts\python.exe -m backend.app.ml.smoke --output data/ml-smoke --edit
```

The test suite covers malformed/oversized files, coordinate and padding invariants, session isolation, mutation origin/host restrictions, transactional queues, cancellation, OOM failure handling, measured quality gates and honest effectiveness states. Worker unit tests use explicitly synthetic test-only results; they are not defense evidence. Browser checks and desktop/mobile screenshots are in `docs/screenshots/`. Actual GPU evidence is kept separately under `data/ml-smoke/` when generated.

Read `docs/UPSTREAM_AUDIT.md` for the source audit and mask adaptation, `model-registry.json` for resolved source/model provenance, and `docs/IMPLEMENTATION_REPORT.md` for current execution results and remaining gates. The original handoff files remain intact at the project root as reference material.

## Local paper research (28 October 2026)

See [research decisions](docs/research/DECISION_AND_IMPLEMENTATION_2026-10-28.md),
[supplied-report corrections](docs/research/USER_REPORT_RECONCILIATION.md), and
[MIRAGE audit](docs/research/MIRAGE_AUDIT.md). Research adapters are separate
from the product Protect flow. Local evidence is in
`outputs/research-2026-10-28/index.html`, including quality failures.

`scripts/run-dct-study.ps1` runs the paper-derived base DCT implementation,
coefficient math checks and actual paired PNG/JPEG-85 editor diagnostics.
`scripts/setup-frontier-environment.ps1` provisions an isolated modern Torch
environment; `scripts/check-frontier-environment.ps1` checks the real Diffusers
FLUX architecture using tiny random weights. This architecture test is not a
pretrained editor or protection benchmark. Full CaD execution remains blocked
by missing gated weights and the current full-resident loader's memory needs.

The single-CLIP refusal-surrogate experiment is not full MIRAGE. Its 5,000-step
export failed source fidelity; no commercial refusal rate was measured. None
of the new methods currently establishes protection against frontier models.

## Remaining product gates

WAM watermarking and signed verification are explicitly unavailable phase-2 features. PhotoGuard controls, efficacy benchmarks across consented images, unseen-mask/editor transfer, real Instagram/Photoshop round trips, native-resolution protection and the broader scenario catalogue require separate measured work after the primary pipeline passes. They are not represented by placeholder successes.

## Attribution

The adapter calls source from https://github.com/choi403/DiffusionGuard at the commit recorded in the audit/registry. No source license file was present in that checkout; redistribution permission remains unconfirmed. The source checkout stays local under ignored `third_party/`. The model card and model license are retained with the downloaded snapshot; its stated license is CreativeML OpenRAIL-M. Interface accessibility guidance was consulted from https://github.com/vercel-labs/web-interface-guidelines without copying Vercel branding.
