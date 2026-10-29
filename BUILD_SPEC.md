# ImageShield — Implementation specification

## 1. Product contract
Upload an existing image, create a visually faithful protected export, and demonstrate disruption of a compatible AI edit. The output is a normal raster image. No encryption wrapper or metadata flag can force an arbitrary editor to fail.

Main deliverable: upload → protect → download → paired AI edit comparison.
Supporting phase 2: watermark provenance and signed integrity verification.
Project title: **Adversarial Image Immunization with Invisible Watermarking for AI Edit Resistance and Tamper Verification.**

Use claims such as “Protection generated; effectiveness not yet tested” and “Observed disruption in these test conditions.” Do not claim universal AI-proof, Photoshop-proof or Instagram-safe behavior.

## 2. Small v1 architecture
- Python 3.10 for the legacy ML environment; separate modern Python environment for FastAPI if dependencies conflict.
- FastAPI with Pydantic schemas; Uvicorn binds 127.0.0.1 by default.
- SQLite, WAL mode, busy timeout, parameterized queries.
- One Python worker process consumes SQLite jobs. No Redis, Celery or microservices initially.
- HTML, CSS and small JavaScript modules served from FastAPI on the same origin.
- Private local data directory, excluded from git and static mounts.
- One GPU job at a time; load compatible models once per worker when possible.
- API imports must never initialize CUDA or fetch model weights.

Browser → FastAPI → validated private assets and SQLite queue → GPU worker → saved output/metrics → authorized artifact endpoint → browser.

Expected launch after implementation:
Terminal A: python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
Terminal B: python -m backend.app.worker
Open http://127.0.0.1:8000

Use a current supported API dependency set resolved and locked during implementation. MODEL_SETUP.md separately specifies legacy ML compatibility. Add python-multipart for upload parsing. Include Pillow, numpy, cryptography, pydantic-settings and pytest/httpx where needed. Pin all resolved versions in lock/constraint files after checking installability.

## 3. Required project layout
- backend/app/main.py: FastAPI app, routes and static frontend.
- backend/app/settings.py: validated configuration.
- backend/app/db.py: schema and SQLite access.
- backend/app/schemas.py: request/response definitions.
- backend/app/worker.py: single worker, claim/heartbeat/cancellation.
- backend/app/services/uploads.py: decode, limits and normalization.
- backend/app/services/jobs.py: lifecycle and transactional enqueue.
- backend/app/services/artifacts.py: artifact IDs mapped to private files.
- backend/app/services/metrics.py: fidelity and perturbation measurements.
- backend/app/services/signing.py: phase-2 detached signed record.
- backend/app/ml/defenders.py: DiffusionGuard and optional adapters.
- backend/app/ml/editor.py: paired inpainting adapter.
- backend/app/ml/masks.py: canonical mask conversion and transforms.
- backend/app/ml/watermark.py: phase-2 WAM adapter.
- frontend/index.html, frontend/styles.css, frontend/app.js.
- frontend/mask-editor.js: canvas region selection.
- scripts/bootstrap.*, scripts/download_models.py, scripts/smoke_test.py.
- tests/: upload, job, mask, verification and paired-input checks.
- docs/: these handoff docs plus final reproducibility report.
- data/: private runtime state, never git tracked.
- third_party/: pinned source checkouts with origin, commit and license attribution.
- model-registry.json: exact successful model/repo revisions, licenses, hashes and statuses.
- .env.example, requirements-api.lock, requirements-ml.lock, README.md.

Do not create a giant main.py holding every subsystem.

## 4. Processing and mask contract
1. Accept JPEG or PNG only in v1. Read bytes under a 10 MiB cap; enforce 20 megapixel decoded limit and reject malformed, animated or unsupported images.
2. EXIF-transpose, convert to sRGB/RGB, and create a reproducible research canvas: fit within 512x512 preserving aspect, then letterbox. Record scale and padding.
3. For transparent PNG, composite on a documented neutral background after showing a preview. Never silently discard alpha.
4. The resulting 512x512 canvas is the clean reference used for BOTH clean and protected attack tests. Retain the uploaded original privately.
5. Canonical editing mask is grayscale L: 255 means editable; 0 means retained. Padding remains uneditable. Use nearest-neighbor mask resampling.
6. UI permits a rectangle to mark an object. “Edit selected region” uses that mask. “Replace background” uses its complement over real image pixels. Add brush refinement later.
7. Reject empty and whole-canvas masks initially. Keep at least 5% editable and 5% retained on real-image pixels. Small jewellery mode may deliberately relax the editable minimum after tests; never silently enlarge a tiny object.
8. Convert this canonical mask to upstream defense semantics explicitly. Determine the semantics from upstream code and a two-region smoke test. Do not infer them from filename alone.
9. Preserve the working resolution through protection and final PNG export. Save metadata about letterboxing. Do not upscale back to the original and call it equally protected.
10. A later native-resolution profile needs new protection generation and new measurements.

User sees a small “512 × 512 research export” label. V1 can require one region selection before Protect. If a no-region mode is provided, label it experimental and benchmark unseen masks. Do not hide a known-mask assumption.

## 5. Defense engine
The adapter must call real upstream DiffusionGuard logic through a small audited wrapper. Inspect protect_image and its utilities/configuration. Preserve the paper's objective and document every adaptation. Do not derive a new objective from the project name.

Inputs: clean reference path, canonical edit-mask path, immutable resolved model config, perturbation budget and job context.
Outputs: protected PNG, effective configuration, perturbation statistics, fidelity metrics, elapsed time and model provenance.

Fixed pretrained model parameters require no optimizer updates. Gradients still must flow from the defense objective to image pixels. Do not wrap the protection computation in torch.no_grad()/inference_mode(). Those contexts are for editing inference and other compatible operations only.

Use upstream settings for a labeled reproduction profile. A faster smoke profile may lower iterations (for example 20), but its success is not paper reproduction. Quality experiments may test epsilon 4/255, 8/255 and 16/255 in [0,1] RGB units. Validate upstream normalization before applying the numbers. Never publish a “strong” preset as proven stronger until measurements support it.

Budget check on actual decoded saved PNG:
- measure max absolute difference and mean absolute difference against clean canvas;
- do not violate configured epsilon after quantization beyond an explained rounding tolerance;
- compute PSNR and SSIM; optional LPIPS comes later;
- evaluate at 100% scale and inspect edges, skin, jewellery, text and smooth backgrounds.

Suggested initial quality gate: SSIM >= 0.98 and PSNR >= 35 dB, plus an explicitly recorded human-review field. These are provisional engineering thresholds, not scientific guarantees. A failed gate produces rejected_quality and no ordinary protected-download action. Researchers may inspect the rejected output under a clearly labeled diagnostics action.

Prefer a strict quality outcome over quietly increasing perturbation strength. Clipping upstream outputs changes efficacy; measure again.

## 6. Job persistence
Jobs: id, owner_id, kind, input_asset_id, config_json, state, stage, completed_steps, total_steps, created_at, updated_at, heartbeat_at, cancel_requested, output_json, error_code.
States: queued → running → succeeded | failed | cancelled | rejected_quality.
“succeeded” means computation completed, not guaranteed edit prevention.

One worker claims a job using a transaction (BEGIN IMMEDIATE), selects one queued row, updates it and commits before processing. Use short transactions. Persist progress only when the algorithm reports real iterations/stages; otherwise use an indeterminate stage.
Worker timeout defaults to 30 minutes and is configurable. Set heartbeat about every 10 seconds. On startup classify stale running jobs as failed/interrupted; do not strand them forever. Queued jobs survive restart. Cancellation checks at iteration boundaries and before each editor run.

For legacy dependency isolation, a fixed configured ML Python executable may run an internal worker entry point via subprocess with shell=False and an argument list. Paths/config come from trusted IDs. Do not concatenate prompts into shell commands. Handle process-tree termination and persist interruptions. Start with one ML environment, add a separate one for WAM only if required.

## 7. API
Use /api/v1. IDs are opaque UUIDs. Artifact names below are logical types, not raw file paths.

| Method | Route | Purpose |
|---|---|---|
| GET | /health | API liveness, no GPU/model downloads |
| GET | /capabilities | CUDA, free/total VRAM, adapter readiness, weight readiness, real/fixture mode |
| POST | /assets | multipart image upload; returns asset ID, normalized dimensions, preview artifact |
| PUT | /assets/{id}/mask | multipart canonical PNG mask; validates geometry |
| POST | /assets/{id}/protect | JSON method/profile/config; returns 202 job ID |
| GET | /jobs/{id} | state, stage, actual progress, metrics and output artifact IDs |
| POST | /jobs/{id}/cancel | request cancellation |
| POST | /assets/{id}/edit-tests | queue paired clean/protected edit experiment |
| GET | /artifacts/{id} | owner/session-scoped safe FileResponse |
| GET | /experiments/{id} | inputs, outputs, parameters and human scores |
| PUT | /experiments/{id}/review | human edit-completion/realism scores |
| POST | /verify | phase 2: submitted image plus record/export ID |
| DELETE | /assets/{id} | explicit deletion; cancel related work and remove owned artifacts |

POST protect example:
{
  "method": "diffusionguard",
  "profile": "research",
  "mask_id": "UUID",
  "watermark": false,
  "seed": 42
}

POST edit-tests example:
{
  "protection_job_id": "UUID",
  "mask_id": "UUID",
  "prompt": "a silver ring with a blue gemstone",
  "editor": "sd15_inpaint",
  "seeds": [11, 22, 33],
  "channel": "local_png"
}

Server validates bounded prompt length (for example 500 characters), allowed model/method enum, seed count and resource limits. Never let an API client supply a model download URL, Python path or arbitrary output path.
Return 413 for oversized uploads, 415 unsupported format, 422 invalid configuration, 409 invalid state, 503 model unavailable. Errors have {error: {code, message, retryable}, request_id}. Never return secrets or full host paths.

On a successful protection job report:
{
  "state": "succeeded",
  "protection_generated": true,
  "effectiveness": "not_tested",
  "quality": {"gate": "passed", "psnr_db": "<measured number>", "ssim": "<measured number>"},
  "artifacts": {"protected": "UUID"},
  "scope": {"editor": "sd15_inpaint", "mask": "UUID", "channel": "local_png"}
}
The angle-bracket values are schema explanations, not values to return. Metrics must be numbers; missing metrics are null with a reason, never invented.

effectiveness enum: not_tested, inconclusive, observed_disruption, bypass_observed. Set the latter two only from a completed, recorded test/review; keep model/task/channel scope attached.

## 8. Paired Attack Lab
For each seed, reset a fresh torch.Generator to that same seed for clean and protected calls. Reusing an already advanced generator invalidates the pairing.
Hold constant: model checkpoint, scheduler, prompt, negative prompt, seed, mask, resolution, guidance and denoising settings.
Load editor with the selected compatible Diffusers API, record its version. Initial proposed settings: 30 steps, guidance 7.5, strength 0.99; first reproduce upstream paper settings separately. Do not merge outcomes across configurations.

Save clean, protected, edit-clean and edit-protected as separate artifacts and show a four-image comparison. Include actual settings in Details. Optional matched-budget random-noise baseline is a control, never the protection implementation.

Human review per output:
- requested_edit_completed: yes/no/uncertain;
- realism: 1–5;
- retained_subject_fidelity: 1–5;
- notes.
Predeclare “usable requested edit” as completed=yes and realism>=4 and retained fidelity>=4. Defense success is a failed usable edit on protected input among pairs where the clean input produced a usable edit. Show numerator/denominator and image count. “Uncertain” is not success.
PSNR between two edited outputs or high CLIP distance alone is not an edit-failure verdict.

## 9. Distribution tests
V1 channels: local PNG and synthetic JPEG/resize stress test. Mark simulation clearly.
Phase 2: user uploads clean/protected copies returned by Instagram and screenshot copies. Pair like with like; store channel provenance.
Never claim Instagram verification without that actual round trip. Manual Photoshop and proprietary AI results require real exported outputs and editor/model/version details; do not substitute our attack editor while calling it Photoshop.

## 10. Security
Local demo defaults: 127.0.0.1; same-origin frontend; deny unknown Origin/Host on mutation; per-session signed HttpOnly SameSite cookie; bind assets and jobs to session owner. Session secrets live outside git. A local single-user session is not production login.
No public data/static mount; use artifact IDs and authorization. Validate resolved paths stay under private root, reject symlinks/path traversal, use random stored names, no raw filenames in HTML injection.
Apply byte/decoded-pixel caps, queue limits, parser handling and per-session rate limits.
Keep original input, normalized reference and protected export separate.
Do not retain EXIF GPS in public exports. Provide deletion and document retention.
Sign final exact-export hashes in phase 2 with Ed25519; trusted public key stays outside untrusted submitted records. Canonicalize signed JSON consistently, excluding its signature field. Key ID and revocation status are explicit.
A self-signed registry proves issuer authenticity within the project's trust model, not copyright ownership or scene truth.

Remote deployment is a separate mode: real login, per-user object authorization, TLS, private storage and restricted CORS are mandatory before exposing the service. GPU worker runs on a GPU host. Do not place GPU loops into static/Vercel functions.

## 11. Milestones with gates
M0 — resolve model/source revisions and environment. CPU doctor passes; if no CUDA, show explicit blocker while building independent API/UI.
M1 — generate one real DiffusionGuard export through a CLI adapter and run one clean/protected edit pair. Inspect quality. No UI needed to pass this gate.
M2 — build upload, mask, queued protection, progress, download and four-image Attack Lab. API is nonblocking and input errors recover.
M3 — complete DESIGN.md interface and test browser flows. No placeholders on a real-results route.
M4 — add controlled fidelity/protection benchmark with matched random-noise and PhotoGuard controls.
M5 — add optional WAM + signatures, only after main AI-disruption feature works. Test both layer orders.
M6 — evaluate unseen masks/editors, JPEG/resize and real platform copies. Optional SDXL transfer runs are separate and may fail.
M7 — add the 12 showcase presets described in research; they share adapters and differ in sample/prompt/mask, not fake success criteria.

If M1 does not show meaningful disruption, investigate input/mask semantics, perturbation units and objective before increasing UI scope. Preserve failures in the evidence report.

## 12. Acceptance checklist
- A real uploaded file reaches the real defense adapter.
- Protected image differs measurably but stays within configured visual budget.
- Four-image paired comparison is generated with fresh matched seeds.
- CPU-only API startup works without importing/loading a diffusion model.
- Missing GPU/checkpoint returns an actionable unavailable state.
- Model failure cannot silently become random noise or fixture success.
- Bad files and path traversal are rejected; asset IDs cannot cross session boundaries.
- Worker cancellation, OOM, interruption and restart do not corrupt job state.
- Mask-to-image coordinates remain correct after fit/letterbox.
- Local PNG and JPEG simulation are never merged into an Instagram claim.
- Mobile, keyboard and reduced-motion states work.
- Signature failure and byte mismatch are distinguished from semantic malicious tampering.

Tests should cover these meaningful boundaries and invariants. Real defense efficacy needs GPU integration evidence and human review, not a unit test that only checks an output file exists.

Final handoff must include installed locks, exact model/repository revisions, launch commands, sample artifacts, test output and an honest “not run” list.

