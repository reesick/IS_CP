# ImageShield

Local research system that adds adversarial perturbations to a photo so that AI inpainting editors produce a broken edit, then proves which images are protected through a SHA-256 evidence registry and a hash-chained audit log. Information Security course project, VIT Pune, CSE (AI), AY 2026-27.

Everything runs on this machine. Images are never sent to a hosted inference service.

## Run it

```powershell
cd D:\IS\ImageShield
powershell -ExecutionPolicy Bypass -File scripts/start-visible.ps1
```

This closes ports 8000/8001, opens log windows (dashboard server, model log, face jobs) and opens the dashboard at http://127.0.0.1:8001.

| URL | What it is |
| --- | --- |
| http://127.0.0.1:8001/dashboard | Comparisons, Pipeline, Playground (live SD1.5 edit with timer), Verify & audit, Use cases |
| http://127.0.0.1:8001/verify | Public verify page: drop any image, get proof whether it is protected |
| http://127.0.0.1:8000 | Main app: upload, mask, protect with DiffusionGuard, paired Attack Lab (`scripts/start.ps1`) |

Other commands:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run-faces.ps1          # protect + tamper-test every face sample (skips finished ones)
.\.venv\Scripts\python.exe scripts\verify-image.py photo.jpg             # identify any image from the command line
.\.venv\Scripts\python.exe scripts\verify-image.py --chain               # check the audit log hash chain
.\.venv\Scripts\python.exe -m pytest -q                                  # API and worker tests
powershell -ExecutionPolicy Bypass -File scripts/stop.ps1                # stop the main app
powershell -ExecutionPolicy Bypass -File scripts/push-github.ps1 "msg"  # commit and push to GitHub
```

## Repository layout

```
backend/
  app/                 main app API (FastAPI), worker, SQLite, services
    ml/                defences and editor: DiffusionGuard, DCT-Shield, PhotoGuard, DiffVax, MIRAGE probe, CaD
  research_demo.py     dashboard + verify page server (port 8001)
  audit.py             evidence registry, image identification, hash-chained audit log
frontend/
  app/                 main app UI (port 8000)
  research-demo/       dashboard, landing and verify pages (port 8001)
scripts/               everyday commands (start, stop, faces, verify, push, bootstrap, doctor)
  setup/               environment and model download helpers
  research/            reproduce the research runs (DCT-Shield, PhotoGuard/DiffVax baselines, MIRAGE probe, CaD checks, face samples)
  qa/                  benchmarks, browser QA, smoke checks
tests/                 pytest suite for the main app
docs/
  IMPLEMENTATION_REPORT.md, ARCHITECTURE.md, UPSTREAM_AUDIT.md, FRONTEND_QA.md
  research/            paper audits, decisions, measured results
  handoff/             original build specification pack
  screenshots/         UI screenshots
model-registry.json    pinned model revision and file hashes
requirements-*.lock    exact Python environments (.venv API, .venv-ml SD1.5, .venv-frontier modern Torch)
```

Not in Git (see `.gitignore`): `.venv*`, `models/` (SD1.5 inpainting, CLIP encoder), `third_party/` (DiffusionGuard, PhotoGuard, DiffVax source), `data/` (main app runtime), `outputs/` (results, face samples, audit log).

## How protection works

1. Fit the photo to a 512 x 512 canvas and mark the region an attacker would edit.
2. Optimise a pixel or DCT-coefficient perturbation against the frozen Stable Diffusion 1.5 inpainting model.
3. Save the protected PNG and measure fidelity (PSNR, SSIM, max pixel change).
4. Run the same edit (prompt, mask, seed) on the clean and protected image and compare.
5. Register every image in `outputs/integrity/` (SHA-256 + perceptual hash) and log it in the hash chain.

Measured results: DCT-Shield broke SD1.5 edits on 4 of 4 photos (PNG). Limits: the perturbation is visible up close (about 27 dB PSNR), JPEG-85 removes the effect, and ChatGPT and FLUX still edited our test kit. See `docs/IMPLEMENTATION_REPORT.md` and `docs/research/`.

## Fresh setup

```powershell
powershell -ExecutionPolicy Bypass -File scripts/bootstrap.ps1 -ML -DownloadModel        # .venv, .venv-ml, DiffusionGuard source, SD1.5 weights
powershell -ExecutionPolicy Bypass -File scripts/setup/setup-frontier-environment.ps1      # .venv-frontier (used by the Playground)
powershell -ExecutionPolicy Bypass -File scripts/doctor.ps1                                # environment check
```

## Attribution

DiffusionGuard (https://github.com/choi403/DiffusionGuard), PhotoGuard (https://github.com/MadryLab/photoguard) and DiffVax (https://github.com/ozdentarikcan/DiffVax) are used from local checkouts at pinned commits. SD1.5 inpainting model card licence: CreativeML OpenRAIL-M. Fonts: Inter and Instrument Serif (OFL, see `frontend/research-demo/fonts`).
