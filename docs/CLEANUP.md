# Repository cleanup, 2026-10-29 15:30

Everything below was removed because nothing in the running app, dashboard, verify page, face pipeline, tests or research scripts references it. Freed: 17.36 GB. DiffVax moved to third_party/DiffVax.

| Path | Group | Size | Why it was removed |
| --- | --- | --- | --- |
| `..\New folder` | Unused folders | 8.20 GB | Separate DiffVax clone with its own Python env, pip temp and a stray image. ImageShield uses third_party/DiffVax; nothing references this folder. |
| `.cache` | Caches | 7.64 GB | Download and build cache: two torch wheels (~5 GB), partial wheel chunks, pip caches, temp files, old run logs, the extracted portfolio design ZIP and UI test leftovers. All environments are already installed; bootstrap recreates what it needs. |
| `models\sd15_inpaint\.cache` | Caches | 690.0 MB | Leftover .incomplete duplicate downloads (~720 MB). The real weights live in unet/, vae/, text_encoder/, safety_checker/ and are hash-recorded in model-registry.json. |
| `models\research-clip-b32\model.safetensors.parts` | Caches | 577.1 MB | 73 download chunks (~600 MB) already merged into model.safetensors. |
| `models\research-clip-b32\.cache` | Caches | 1 KB | Hugging Face download metadata for the merged file. |
| `third_party\BlurGuard` | Unused third-party code | 166.7 MB | Candidate defence that was only read during the paper audit. Never imported. |
| `third_party\DeContext` | Unused third-party code | 52.7 MB | Needs gated FLUX Kontext weights and much more GPU memory; audited, never imported. |
| `third_party\ResearchIndex` | Unused third-party code | 116 KB | A list of links to papers, not code. Never imported. |
| `third_party\candidate-audit\Anti-Diffusion` | Unused third-party code | 24.6 MB | Audited candidate (SD2.1 prompt tuning); never imported. |
| `third_party\candidate-audit\Universal-Immunization` | Unused third-party code | 3.9 MB | Repository only contained a website ("code coming soon"); never imported. |
| `outputs\playground` | Old outputs | 5.5 MB | Old Playground runs. The server only shows runs from its current session, so these folders are never read again. |
| `outputs\local-sd15-demo` | Old outputs | 9.5 MB | QA receipts and failed attempts from an earlier version of the dashboard. |
| `outputs\workspace-qa` | Old outputs | 10.1 MB | Screenshots of an earlier dashboard layout. |
| `outputs\dashboard-previews` | Old outputs | 6.9 MB | Mask, change-map and verdict previews; regenerated automatically when the dashboard starts. |
| `data\browser-smoke` | Old outputs | 192 KB | Browser QA artefacts from the first GPU smoke test. |
| `frontend\research-demo\flow.css` | Unused scripts and styles | 1 KB | old pipeline grid styles; the page now loads pipeline.css instead |
| `scripts\finalize-workspace-ui.py` | Unused scripts and styles | 2 KB | one-off patch that rewrote the dashboard HTML once (and caused the broken characters); nothing calls it |
| `scripts\read-design-reference.py` | Unused scripts and styles | 1 KB | one-off reader for the portfolio design ZIP; fonts are already copied into frontend |
| `scripts\import-reference-assets.ps1` | Unused scripts and styles | 1 KB | one-off font import from the portfolio ZIP; already done |
| `scripts\finish-local-setup.ps1` | Unused scripts and styles | 1 KB | installed torch from local wheel files in .cache that are being deleted; bootstrap.ps1 installs from requirements-ml.lock |
| `scripts\install-ml-deps.ps1` | Unused scripts and styles | 1 KB | early installer superseded by requirements-ml.lock + bootstrap.ps1 |
| `scripts\install-environments.ps1` | Unused scripts and styles | 1 KB | earlier copy of bootstrap.ps1 (same steps); bootstrap.ps1 is the maintained one |
| `scripts\show-demo.ps1` | Unused scripts and styles | 0 KB | superseded by start-visible.ps1 (closes ports, opens log windows, runs face jobs) |
| `scripts\restart-research-demo.ps1` | Unused scripts and styles | 1 KB | only used by show-demo.ps1; start-visible.ps1 already restarts |
| `scripts\run-portrait-demo.ps1` | Unused scripts and styles | 1 KB | single-face runner superseded by run-faces.ps1, which handles every face sample |
| `scripts\browser\local-demo-qa.cjs` | Unused scripts and styles | 3 KB | tests the old live-run dashboard (removed /api/run route); no longer matches the UI |
| `scripts\browser\workspace-qa.cjs` | Unused scripts and styles | 4 KB | tests the earlier dashboard layout; superseded by the current tabs |
| `BUILD_SPEC.md` | Old locations of moved files | 17 KB | Moved to docs/handoff/BUILD_SPEC.md: original build hand-off pack; reference material, not needed at the repo root. |
| `DESIGN.md` | Old locations of moved files | 7 KB | Moved to docs/handoff/DESIGN.md: original build hand-off pack; reference material, not needed at the repo root. |
| `MODEL_SETUP.md` | Old locations of moved files | 10 KB | Moved to docs/handoff/MODEL_SETUP.md: original build hand-off pack; reference material, not needed at the repo root. |
| `RESEARCH_AND_USE_CASES.md` | Old locations of moved files | 33 KB | Moved to docs/handoff/RESEARCH_AND_USE_CASES.md: original build hand-off pack; reference material, not needed at the repo root. |
| `START_HERE.md` | Old locations of moved files | 3 KB | Moved to docs/handoff/START_HERE.md: original build hand-off pack; reference material, not needed at the repo root. |
| `models.example.json` | Old locations of moved files | 2 KB | Moved to docs/handoff/models.example.json: original build hand-off pack; reference material, not needed at the repo root. |
| `frontend\index.html` | Old locations of moved files | 10 KB | Moved to frontend/app/index.html: main app UI grouped in its own folder next to research-demo. |
| `frontend\app.js` | Old locations of moved files | 23 KB | Moved to frontend/app/app.js: main app UI grouped in its own folder next to research-demo. |
| `frontend\mask-editor.js` | Old locations of moved files | 4 KB | Moved to frontend/app/mask-editor.js: main app UI grouped in its own folder next to research-demo. |
| `frontend\styles.css` | Old locations of moved files | 12 KB | Moved to frontend/app/styles.css: main app UI grouped in its own folder next to research-demo. |
| `data\frontier-user-report.txt` | Old locations of moved files | 17 KB | Moved to docs/research/frontier-user-report.txt: research reference text, not runtime data. |
| `scripts\check_environment.py` | Old locations of moved files | 2 KB | Moved to scripts/setup/check_environment.py: grouped by purpose. |
| `scripts\download_models.py` | Old locations of moved files | 5 KB | Moved to scripts/setup/download_models.py: grouped by purpose. |
| `scripts\download_range.py` | Old locations of moved files | 2 KB | Moved to scripts/setup/download_range.py: grouped by purpose. |
| `scripts\freeze-ml.py` | Old locations of moved files | 1 KB | Moved to scripts/setup/freeze-ml.py: grouped by purpose. |
| `scripts\setup-frontier-environment.ps1` | Old locations of moved files | 2 KB | Moved to scripts/setup/setup-frontier-environment.ps1: grouped by purpose. |
| `scripts\download-frontier-wheels.py` | Old locations of moved files | 2 KB | Moved to scripts/setup/download-frontier-wheels.py: grouped by purpose. |
| `scripts\freeze-frontier.py` | Old locations of moved files | 1 KB | Moved to scripts/setup/freeze-frontier.py: grouped by purpose. |
| `scripts\check-frontier-environment.ps1` | Old locations of moved files | 1 KB | Moved to scripts/setup/check-frontier-environment.ps1: grouped by purpose. |
| `scripts\check-frontier-preflight.py` | Old locations of moved files | 0 KB | Moved to scripts/setup/check-frontier-preflight.py: grouped by purpose. |
| `scripts\setup-research-encoder.ps1` | Old locations of moved files | 0 KB | Moved to scripts/setup/setup-research-encoder.ps1: grouped by purpose. |
| `scripts\download-research-encoder.py` | Old locations of moved files | 2 KB | Moved to scripts/setup/download-research-encoder.py: grouped by purpose. |
| `scripts\run-dct-study.ps1` | Old locations of moved files | 1 KB | Moved to scripts/research/run-dct-study.ps1: grouped by purpose. |
| `scripts\check-dct-math.py` | Old locations of moved files | 2 KB | Moved to scripts/research/check-dct-math.py: grouped by purpose. |
| `scripts\run-dct-shield.py` | Old locations of moved files | 1 KB | Moved to scripts/research/run-dct-shield.py: grouped by purpose. |
| `scripts\run-dct-pairs.py` | Old locations of moved files | 1 KB | Moved to scripts/research/run-dct-pairs.py: grouped by purpose. |
| `scripts\build-research-gallery.py` | Old locations of moved files | 5 KB | Moved to scripts/research/build-research-gallery.py: grouped by purpose. |
| `scripts\research-contact-sheet.py` | Old locations of moved files | 2 KB | Moved to scripts/research/research-contact-sheet.py: grouped by purpose. |
| `scripts\run-paper-baselines.py` | Old locations of moved files | 2 KB | Moved to scripts/research/run-paper-baselines.py: grouped by purpose. |
| `scripts\check-diffvax.py` | Old locations of moved files | 1 KB | Moved to scripts/research/check-diffvax.py: grouped by purpose. |
| `scripts\check-research-math.py` | Old locations of moved files | 2 KB | Moved to scripts/research/check-research-math.py: grouped by purpose. |
| `scripts\run-contrastive-probe.py` | Old locations of moved files | 1 KB | Moved to scripts/research/run-contrastive-probe.py: grouped by purpose. |
| `scripts\run-frontier-research.ps1` | Old locations of moved files | 0 KB | Moved to scripts/research/run-frontier-research.ps1: grouped by purpose. |
| `scripts\run-native-refusal-probe.ps1` | Old locations of moved files | 0 KB | Moved to scripts/research/run-native-refusal-probe.ps1: grouped by purpose. |
| `scripts\check-clip-batching.py` | Old locations of moved files | 2 KB | Moved to scripts/research/check-clip-batching.py: grouped by purpose. |
| `scripts\build-frontier-test-kit.ps1` | Old locations of moved files | 1 KB | Moved to scripts/research/build-frontier-test-kit.ps1: grouped by purpose. |
| `scripts\build-frontier-test-kit.py` | Old locations of moved files | 7 KB | Moved to scripts/research/build-frontier-test-kit.py: grouped by purpose. |
| `scripts\verify-frontier-kit.py` | Old locations of moved files | 1 KB | Moved to scripts/research/verify-frontier-kit.py: grouped by purpose. |
| `scripts\run-cad.py` | Old locations of moved files | 1 KB | Moved to scripts/research/run-cad.py: grouped by purpose. |
| `scripts\check-cad-flux.py` | Old locations of moved files | 5 KB | Moved to scripts/research/check-cad-flux.py: grouped by purpose. |
| `scripts\research-snapshot.py` | Old locations of moved files | 2 KB | Moved to scripts/research/research-snapshot.py: grouped by purpose. |
| `scripts\summarize-research.py` | Old locations of moved files | 2 KB | Moved to scripts/research/summarize-research.py: grouped by purpose. |
| `scripts\run-dnew-tests.ps1` | Old locations of moved files | 0 KB | Moved to scripts/research/run-dnew-tests.ps1: grouped by purpose. |
| `scripts\test-dnew.py` | Old locations of moved files | 7 KB | Moved to scripts/research/test-dnew.py: grouped by purpose. |
| `scripts\benchmark-runtime.py` | Old locations of moved files | 1 KB | Moved to scripts/qa/benchmark-runtime.py: grouped by purpose. |
| `scripts\record-runtime.py` | Old locations of moved files | 3 KB | Moved to scripts/qa/record-runtime.py: grouped by purpose. |
| `scripts\check-persistent-cancel.py` | Old locations of moved files | 2 KB | Moved to scripts/qa/check-persistent-cancel.py: grouped by purpose. |
| `scripts\check-jpeg-channel.py` | Old locations of moved files | 2 KB | Moved to scripts/qa/check-jpeg-channel.py: grouped by purpose. |
| `scripts\check-download.py` | Old locations of moved files | 1 KB | Moved to scripts/qa/check-download.py: grouped by purpose. |
| `scripts\gpu-browser-qa.cjs` | Old locations of moved files | 5 KB | Moved to scripts/qa/gpu-browser-qa.cjs: grouped by purpose. |
| `scripts\browser\interface-qa.cjs` | Old locations of moved files | 5 KB | Moved to scripts/qa/interface-qa.cjs: grouped by purpose. |
| `scripts\browser\mask-qa.cjs` | Old locations of moved files | 2 KB | Moved to scripts/qa/mask-qa.cjs: grouped by purpose. |
| `scripts\browser\research-gallery-qa.cjs` | Old locations of moved files | 2 KB | Moved to scripts/qa/research-gallery-qa.cjs: grouped by purpose. |
| `scripts\smoke_test.py` | Old locations of moved files | 1 KB | Moved to scripts/qa/smoke_test.py: grouped by purpose. |
| `scripts\run-portrait-demo.py` | Old locations of moved files | 4 KB | Moved to scripts/research/run-face-sample.py: grouped by purpose. |
