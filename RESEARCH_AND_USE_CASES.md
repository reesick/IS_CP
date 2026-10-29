> Implementation note: BUILD_SPEC.md in this package supersedes the broader infrastructure suggestions below for v1. Start with a Python worker and SQLite, not Redis or cloud services. Anti-editing is the primary feature; watermarking is phase 2.

# ImageShield — Research and implementation brief
Prepared 27 October 2026 for Shreeviraj Matale, Information Security, VIT Pune.

## Decision
Build an upload–protect–publish system for existing raster images. Its primary research goal is to reduce the success of specified AI edits while preserving the published image's quality. Add watermarking and signed verification as fallback evidence when prevention fails.

Proposed title: **Adversarial Image Immunization with Invisible Watermarking for AI Edit Resistance and Tamper Verification.**

“AI-proof”, “Photoshop-proof”, and “tamper-proof” are unsupported universal claims. Ordinary Photoshop operations are not forced to create artifacts by these methods. AI Generative Fill is a different, model-dependent target. Once a readable image is public, the system cannot enforce viewer permissions on those pixels.

Status: research and proposed design only. No GPU model was executed, no checkpoint downloaded or validated, and no Instagram or Photoshop test was performed in this investigation.

## Evidence and reuse decision
Source links are in Appendix B. Stars below are displayed GitHub snapshots retrieved during this research, not exact audited API counts. They can change and do not measure security.

| Component | Displayed stars | Reuse decision | Material caveat |
|---|---:|---|---|
| MadryLab/photoguard | 704 | Baseline; official research code | Existing issues report broken demos/dependencies; compression bypass literature exists |
| choi403/DiffusionGuard | 50 | Primary optimization-based candidate | Official ICLR 2025 implementation; masks/configuration required; evaluation reproducibility request is open |
| ozdentarikcan/DiffVax | 24 | Conditional pretrained fast candidate | README advertises pretrained model; checkpoint bytes/loadability were not verified; open issue alleges visible noise and unconstrained epsilon |
| psyker-team/mist-v2 | 670 | Related work / later training-misuse extension | Primarily unauthorized customization/LoRA protection, a different evaluation task |
| facebookresearch/watermark-anything | about 1.1k | Watermark and localization candidate | Archived August 1, 2026; pin dependencies and use appropriate weight license |
| contentauth/c2pa-python | 109 | Optional provenance interoperability | Signature and provenance are not scene-truth or copyright proof |

These are research components, not a single turnkey package satisfying this project. PhotoGuard's authors demonstrate adversarial perturbations disrupting targeted diffusion editors. DiffusionGuard specifically studies masked editing. DiffVax offers a learned immunizer; use pretrained inference if the released artifacts reproduce acceptably. Do not train a replacement merely because the first checkpoint fails; fall back to the optimization baseline.

PhotoGuard and DiffusionGuard optimize an image's perturbation while keeping pretrained model weights fixed. This is iterative computation, not retraining the diffusion model.

Glaze is an example of an actual user-facing upload/process workflow, with a different goal: style-mimicry protection. UChicago reported over one million downloads in 2023; that is historical adoption evidence, not evidence of universal editing resistance. Nightshade is about training-data poisoning, not our core workflow.

A Reddit photographer describes a client feeding delivered images into an AI editor. Replies raise screenshots, compression, and model changes. Treat these as user needs and attack ideas, not controlled efficacy evidence. A JPEG-bypass paper and a 2026 image-to-image purification preprint justify testing such bypasses ourselves. Their conclusions do not establish that every current or future defense fails.

## Twelve selected showcase scenarios
These scenarios share modules. A new sector does not require a new model. All disruption claims remain experimental and model-specific.

Modules: P = adversarial pixel protection; R = transformation and platform robustness tests; W = localized invisible watermark; S = signed registry; V = reference-assisted verification.

| Priority | Candidate ID | Scenario | Attack demonstration | Modules | Observable outcome |
|---:|---:|---|---|---|---|
| 1 | 1 | Portrait background replacement | Replace a consented portrait background with a warehouse | P,R,W,S | Compare usable edits on original versus protected image |
| 2 | 11 | Fashion garment replacement | Change a jacket into a different garment | P,R,W,S | Score requested change and retention of face/body |
| 3 | 12 | Jewellery replacement | Replace a ring or necklace in a campaign | P,R,W,V | Inspect small-object shape, reflections and edit success |
| 4 | 21 | Ecommerce product replacement | Swap a bottle or shoe while retaining the scene | P,R,W,V | Check product fidelity and edit plausibility |
| 5 | 22 | Packaging/logo alteration | Replace a fictional label or emblem | P,R,W,V | Inspect label region and compare approved reference |
| 6 | 31 | Wedding preview re-editing | Change backdrop or dress details in a consented photo | P,R,W,S | Paired edit comparison and approved-version record |
| 7 | 41 | Real-estate misrepresentation | Remove a staged wall crack or add a window | P,R,W,V | Measure edit success; surface reference mismatch if successful |
| 8 | 51 | News-photo scene changes | Insert an object in a staged event scene | P,R,W,S,V | Disruption or detected change; no claim of truth verification |
| 9 | 61 | Illustration instruction restyling | Ask an instruction editor to change the depicted medium | P,R,W,S | Held-out editor transfer test; not a LoRA training claim |
| 10 | 62 | Concept-art design changes | Replace a vehicle or building in a design preview | P,R,W,V | Object edit outcome and watermark survival |
| 11 | 40 | Manual Photoshop clone-stamp | Remove an object using ordinary editing tools | W,S,V | Expected: editing still works; verifier investigates changed region |
| 12 | 81 | Recipient preview tracing | Make two watermarked exports; crop/recompress one | W,R,S | Recover recipient export ID when possible; no automatic proof who leaked it |

Instagram upload/download and screenshot paths apply across the shortlist, rather than being advertised as a separate content-protection mechanism.

## Architecture

### Service layout
- Browser UI: upload, optional region selection, Protect, download, Verify, and benchmark results.
- FastAPI: authentication, upload validation, ownership checks, job submission and result authorization.
- Redis plus a worker queue: long GPU tasks remain outside API request timeouts.
- GPU worker: fixed pretrained editor/defender checkpoints, per-image optimization or pretrained immunizer, WAM and evaluation jobs.
- Private object storage: original, normalized reference, protected exports, comparison images and reports.
- Registry database: asset ID, export ID, owner account, parent version, model/config hashes, file hashes, signatures and job evidence.
- Signing service: SHA-256 + Ed25519 for the project's sidecar registry. Optional C2PA uses its SDK, supported signing algorithms and certificate/trust requirements; a custom Ed25519 JSON signature is not automatically C2PA.

For a single-machine prototype, local private files and SQLite can substitute for object storage and a shared database. Keep the model worker isolated from the API.

### Protection path
1. Authenticate the uploader. Validate format by decoding, enforce dimensions/byte limits, normalize orientation and color, strip unnecessary private metadata, then create the clean processing reference. This happens before protection.
2. Select target export dimensions and define candidate edit masks. Offer a simple user region selector first; automatic face/product segmentation is an optional convenience.
3. Embed a short export identifier using WAM. Store its mapping server-side. Do not put private identity, secrets or a full signature into the small watermark payload.
4. Generate adversarial perturbations using DiffusionGuard as the primary reproducible baseline. Try DiffVax as a fast alternative after validating its checkpoint and image quality.
5. Evaluate the exact saved output, including quantization and selected PNG/JPEG export. Test watermark extraction, visible fidelity and paired AI edit success. Watermarking and perturbations can interfere: neither order is assumed correct.
6. Reject candidates that fail the configured image-quality budget. Try a finite set of strengths/orders/masks; retain a quality/protection tradeoff, not an arbitrary “100% protected” score.
7. Serialize the final image. Hash those exact bytes and sign the sidecar record. Hash the record's canonical serialized content excluding the signature field itself. Include model versions, protected-export ID and measured test conditions.
8. Release the protected export and verification receipt; retain the clean original privately with the user's retention choice.

Initial product mode can restrict supported editing tasks to background changes or a selected object. It must not silently pretend a single mask protects all possible future edits. For unknown edits, evaluate many masks and shapes; a whole-image perturbation and broader-mask optimization are research variants.

### Robustness extension
After reproducing a baseline, add expectation over transformations (EOT) to per-image refinement: sample differentiable approximations of resize, JPEG and mild crop, optimize expected edit disruption under a fixed visual budget, then evaluate with real codecs and unseen transformations.

This is a proposed extension, not a feature guaranteed by the selected repositories. Validate surrogate gradients. Do not resize a small protected image and assume its protection transfers to the final-resolution export.

A conceptual objective is:
  maximize expected editing failure over models, prompts, masks and transformations
  subject to a perturbation budget, acceptable visual fidelity and recoverable watermark.

A differentiable surrogate objective need not predict actual editing failure. Evaluate the final generated images, not just the optimization loss.

### Verification path
1. Accept a known export ID, or attempt watermark-based lookup with an abstain state.
2. Check registry signature and signing-key trust/revocation.
3. An exact file-hash match authenticates the registered byte sequence.
4. A mismatch means “changed bytes”, including benign recompression.
5. Extract watermark confidence/messages and check consistency with the signed content record.
6. If a trusted reference is available, align the images before comparing them. Estimate candidate changed regions using watermark evidence and registered-reference differences.
7. Report evidence separately: exact match, changed derivative, suspicious regions, or unverified/insufficient evidence.

Absence of a watermark does not prove tampering. A surviving watermark does not prove unchanged content. Perceptual similarity is useful for lookup but is not a cryptographic integrity proof. Watermark replay and re-embedding need explicit attack tests.

### Layer-interaction experiment
Run four configurations before choosing the production order:
- P only.
- W only.
- W followed by P.
- P followed by W.

Compare protection success, watermark recovery and image fidelity. If neither combined order performs acceptably, offer separately labeled protection/provenance exports and document that the combined research goal remains unmet. Do not claim an integrated defense merely because both modules execute.

## Concrete prototype implementation
API surface:
- POST /assets: validate and register original.
- POST /assets/{id}/protect: choose method, profile and optional region.
- GET /jobs/{id}: status and owner-authorized results.
- POST /verify: return signature/hash/watermark/reference evidence.
- POST /benchmarks: queue authorized benchmark matrix.
- GET /benchmarks/{id}: per-condition results and comparisons.

Internal adapter contracts:
- protect(image, context_masks, config) -> protected_pixels, provenance
- embed(image, export_message, config) -> marked_pixels
- extract(image) -> spatial_scores, candidate_messages
- edit(image, mask, prompt, model_id, seed) -> edited_image
- verify(image, record, optional_reference) -> structured_evidence

Do not expose filesystem paths or shell commands through requests. User prompts and names are data, not executable worker commands.

First reproducibility commands, taken from official READMEs; these were not run in this research:
- DiffusionGuard, from its repository: python main.py --config-name diffusionguard orig_image_name='keanu.png' mask_image_names='["keanu_mask.png"]'
- DiffVax, from its repository: python scripts/demo.py --image photo.png --mask mask.png --edit-prompt "a cat sitting"

Masks have method-specific semantics. Check whether a mask marks the area to edit or retained context before connecting adapters.

Use isolated environments for research repos; their PyTorch/Diffusers pins differ. Verify checkpoint provenance, expected shape, checksum and license; avoid unrestricted loading of untrusted pickle checkpoints.

Hardware: the DiffVax README requests 8 GB+ VRAM for its demo stack. Do not assume it runs unchanged on a 6 GB device. Benchmark actual peak VRAM. Pretrained immunizer-only inference can have different requirements from diffusion editing or gradient optimization. Use a larger GPU for the full benchmark if needed; inference offloading advice does not automatically work for a gradient-based protection loop.

## Benchmark and acceptance plan
Start with a reproducibility gate: 10 consented or licensed images and controlled prompts. No claim of success until paired baseline results exist.

Then use 50 images across five strata (portraits, fashion/jewellery, products, scenes/property, illustration). Split 10 for tuning, 40 held out. Reserve human reviewers from tuning where practical.

For the held-out core comparison:
- 40 images x 3 compatible editing tasks x 3 seeds x 2 editor models x 4 image variants (clean, PhotoGuard, DiffusionGuard, selected combined pipeline) = 2,880 editing outputs.
- Match prompt, mask, seed, model and preprocessing within each clean/protected comparison.
- Report in-distribution versus genuinely held-out editor results separately.
- Budget robustness runs separately to avoid silently multiplying GPU cost.

For 10 images, two methods, four channel conditions, three tasks, three seeds and one editor, channel stress testing adds 720 editing outputs. An ablation should include matched-magnitude random noise so any effect is not simply generic image degradation.

Quality measures:
- Protected versus clean: PSNR, SSIM, LPIPS and visual review at final export resolution.
- Attack outcome: requested-edit completion, realism and preservation of relevant identity/product details.
- Defense success: among attack conditions where the clean image yielded a usable requested edit, fraction where the protected image fails the predetermined usability rubric.
- Watermark: bit/message accuracy, detection false positives on unrelated clean images and recovery after transformations.
- Localization: IoU/pixel F1 against saved known edit masks, with benign-transformation false alarms.
- Operations: runtime, peak memory and failure rate.
- Small-object tests: inspect and score the object region separately; whole-image metrics can hide jewellery/logo failures.

Suggested initial engineering gates, not published guarantees: SSIM at least 0.98 and PSNR at least 35 dB, paired with human review. Calibrate them for the content. If a method cannot satisfy both quality and protection, report the tradeoff. Do not distort the original merely to make later edits look bad.

Report denominators, confidence intervals and failures. For stochastic repeats, aggregate per image or use image-level bootstrap; do not pretend thousands of correlated outputs are thousands of independent subjects.

### Real Instagram scenario
1. Produce clean and protected exports at the intended final dimensions.
2. Upload both with matching settings to an authorized test account.
3. Obtain the delivered image copies and a screenshot copy; keep these channels separate.
4. Run the same edit benchmark on local clean/protected files and platform-returned clean/protected files.
5. Test actual Photoshop Generative Fill separately, record Photoshop version and selected model. Adobe documents multiple model choices; testing Stable Diffusion does not establish Firefly or partner-model protection.
6. Include ordinary crop, brush, copy-paste, clone stamp and color-adjustment controls. These should remain usable; investigate authenticity afterward.
7. If only local PNG works, label it local-file resistance. Do not market Instagram survival.

Synthetic JPEG/resizing stress tests are useful before platform testing but do not reproduce Instagram's full proprietary processing. Do not hardcode one JPEG quality as “Instagram”.

### Adaptive attacker tests
- Re-encode JPEG at 95/85/70/50; try multiple sizes and crops.
- Denoise or upscale before editing.
- Use a different image editor or stronger edit settings.
- Change masks and seeds, including removal of perturbed context.
- Screenshot capture, color transforms and metadata stripping.
- Transfer/re-embed another registered watermark.
- Supply a valid signed record with a different image.
- Access another user's asset/job ID.
- Edit the registry record or substitute a signing key.

## Information Security implementation and demonstrations
Threat model: attacker has the public protected image, knows the algorithms and can preprocess, crop, screenshot, edit, denoise and query other editors. The clean original, signing key and private registry are trusted assets; compromise of those is a separate tested service-security risk.

| Security property | Concrete control | Demonstration |
|---|---|---|
| Integrity | Signed exact-file hash and immutable versioned records | Change one byte or record field; verification fails |
| Authenticity | Ed25519 signature with a pinned trusted public key and key ID | Wrong signer is rejected even if signature is mathematically valid |
| Confidentiality | Private originals, HTTPS, encrypted storage, owner authorization | Second account cannot retrieve another user's original |
| Authorization | Per-asset and per-job ownership checks | Swap IDs and receive denial |
| Availability | Upload/pixel caps, job timeout, concurrency limit, queue quota | Oversized/decompression-bomb or excessive job requests are bounded |
| Secure input handling | Decode formats, normalize before protection, random storage IDs, isolated parsers | Executable renamed to .jpg is rejected |
| Auditability | Signed job evidence and append-only audit events | Tie an export to model/config/version and authenticated actions |
| Key security | Separate signing process/secret store, key rotation and revocation | Old/compromised key status visible to verifier |
| Adversarial robustness | Public algorithms, held-out editors, purification and transformation attacks | Show successes and bypasses under a reproducible matrix |
| Privacy | EXIF removal, consented data, retention/deletion controls | Published artifact omits GPS; private input can be deleted |

A key in an environment file is acceptable only as a local demonstration secret; it is not a complete deployment key-management system. A detached registry signature is a project trust model, not third-party notarization. A registry timestamp is a server claim unless independently timestamped.

Do not expose private reference images through a public verifier. An identifier recovered from pixels must not grant access to private data. Rate-limit public lookup and return minimal evidence.

C2PA is optional interoperability. Verify incoming credentials before normalization if preservation matters; ordinary transcoding may remove or invalidate them. Sign only after final pixel export; C2PA embedding changes file bytes, so compute the external exact-file hash afterward. Demo certificates are not automatically globally trusted.

The system authenticates registered issuance and changes after issuance; it does not prove rightful copyright ownership, truth of a scene, or which person leaked a recipient-tagged export.

## Build sequence and stopping rules
1. Reproduce PhotoGuard/DiffusionGuard on a few images; record clean/protected edit outcomes.
2. Test DiffVax checkpoint and visible-fidelity issue. Enforce measured perturbation bounds if adapting; clipping may reduce defense efficacy, so retest.
3. Build upload–protect–download for one supported edit family. No general all-editor claim.
4. Add watermark, registry, signature verification and layer ablation.
5. Add paired attack dashboard and manual-edit negative controls.
6. Evaluate transformation-aware refinement, unseen editors and real Instagram copies.
7. Complete the 12-scenario presentation from the shared modules.

If no defense preserves fidelity and disrupts the tested editor, the scientifically valid result is a measured limitation. The verification subsystem can still function, but it must not be relabeled as successful edit prevention.

## Showcase UI
Three tabs: Protect, Attack Lab, Verify.
Protect: original/protected slider, method/profile, download, quality evidence.
Attack Lab: identical prompt/mask on clean and protected, side-by-side outputs, seed and model, local versus platform-returned condition.
Verify: registry signature, exact-hash result, watermark evidence, optional suspicious-region overlay and an inconclusive state.
Show the following four states prominently in the assessment:
1. Clean input can be edited.
2. Protected input disrupts a particular tested edit, if observed.
3. A bypass succeeds or transfer fails.
4. Manual editing succeeds but evidence of modification can be examined.

A good course contribution is the joint quality–protection–provenance evaluation, especially after publishing transformations. It is an implementation and experimental contribution unless a new method is actually developed and established against prior work.


## Appendix A — 100-candidate screening

This is an analyst-generated pool of 100 candidate scenarios, screened against the research above; it is not a survey of 100 deployed products or 100 experiments. Selection favors security relevance, reuse of available code, visible demonstrations, compatibility with a single-image workflow, and distinct coverage. The 12 selections are project priorities, not measured efficacy rankings. Instagram survival is a cross-cutting condition for all selected scenarios.

A = attempted AI edit disruption; V = verification/access control only; E = evaluation condition; X = excluded or separate research task.

| ID | Candidate | Route | Decision / reason |
|---|---|---|---|
| 1 | Portrait background replacement | A | **SHORTLIST** — core masked diffusion edit |
| 2 | Profile-photo expression changes | A | Secondary: face geometry harder to score |
| 3 | Unauthorized hairstyle changes | A | Secondary: overlaps local portrait edit |
| 4 | Skin-tone manipulation | A | Secondary: color changes also work manually |
| 5 | Fake location for a public figure | A | Secondary: use consented or synthetic subjects |
| 6 | Face-swap prevention | X | Separate identity/face-swap model required |
| 7 | Face-recognition evasion | X | Different security task and model |
| 8 | Identity LoRA cloning | X | Separate training-time evaluation |
| 9 | Prevent screenshot copying | X | Cannot prevent capture of visible pixels |
| 10 | Stop manual portrait retouching | V | Detect changes; cannot disable brushes |
| 11 | Garment replacement in a campaign | A | **SHORTLIST** — core masked edit |
| 12 | Jewellery replacement in a campaign | A | **SHORTLIST** — tests small reflective objects |
| 13 | Footwear replacement | A | Secondary: overlaps accessory replacement |
| 14 | Fabric-pattern copying | X | Reconstruction and training need distinct tests |
| 15 | Campaign model replacement | A | Secondary: large mask and identity confounds |
| 16 | Change garment color | V | Manual recoloring cannot be blocked |
| 17 | Counterfeit fashion listing attribution | V | Secondary: provenance not counterfeit detection |
| 18 | Unapproved campaign crop | V | Secondary: transformed derivative verification |
| 19 | Campaign skin retouching | V | Secondary: compare approved reference |
| 20 | Publish approved versus draft campaign | V | Secondary: version and issuer verification |
| 21 | Product replacement in listing image | A | **SHORTLIST** — core object inpainting |
| 22 | Packaging or logo alteration | A | **SHORTLIST** — tiny structured edit |
| 23 | Fake product damage | A | Secondary: local inpainting variant |
| 24 | Remove product defects | A | Secondary: reference comparison needed |
| 25 | Fake product color variant | V | Secondary: ordinary color tools bypass protection |
| 26 | Product background replacement | A | Secondary: overlaps portrait background |
| 27 | Manufacture fake labels | V | Secondary: OCR and manual-edit validation |
| 28 | Hide expiry date | V | Secondary: integrity evidence only |
| 29 | Prevent product-image scraping | X | Pixels remain downloadable |
| 30 | Prevent product recreation from scratch | X | No control over independent generation |
| 31 | Client re-editing of wedding previews | A | **SHORTLIST** — practical consented-photo demo |
| 32 | Commercial photographer scene restyling | A | Secondary: overlaps client re-edit |
| 33 | Food-photo ingredient replacement | A | Secondary: domain extension |
| 34 | Automotive paint or part replacement | A | Secondary: domain extension |
| 35 | Travel-photo landmark replacement | A | Secondary: domain extension |
| 36 | Wildlife-photo species replacement | A | Secondary: domain extension |
| 37 | Sports-photo equipment changes | A | Secondary: domain extension |
| 38 | Concert-photo performer removal | A | Secondary: domain extension |
| 39 | Remove visible photographer watermark | A | Secondary: logo removal and purification confound |
| 40 | Prevent manual clone-stamp use | V | **SHORTLIST** — negative control plus verification |
| 41 | Real-estate feature fabrication | A | **SHORTLIST** — remove crack or add window |
| 42 | Fake virtual furniture staging | A | Secondary: overlap local scene edit |
| 43 | Erase construction damage | V | Secondary: forensic reference use |
| 44 | Change building signage | V | Secondary: text/manual edit |
| 45 | Invent hotel amenities | A | Secondary: local scene edit |
| 46 | Manipulate rental room size | V | Secondary: geometric edits not prevented |
| 47 | Remove industrial safety hazards | V | Secondary: forensic comparison |
| 48 | Fake vehicle accident scene | V | Secondary: high-stakes evidence limits |
| 49 | Modify drone survey landmarks | V | Secondary: geometric alignment needed |
| 50 | Protect CAD/vector design editing | X | Raster pipeline does not protect source vectors |
| 51 | News-photo scene manipulation | A | **SHORTLIST** — consented staged news image |
| 52 | Fake event crowd size | A | Secondary: larger masks and counting evaluation |
| 53 | Insert object into protest photo | A | Secondary: local scene edit |
| 54 | Erase person from official photograph | V | Secondary: reference-based forensics |
| 55 | Modify public-information poster | V | Secondary: text edit detection |
| 56 | Fake endorsement in campaign visual | V | Secondary: attribution not truth verification |
| 57 | Misleading recaptioning of unchanged photo | X | Pixels unchanged; needs context analysis |
| 58 | Verify signed press image | V | Secondary: exact signed-file verification |
| 59 | False before-and-after comparison | V | Secondary: provenance and history |
| 60 | Prove a photo depicts a true event | X | Signatures do not establish scene truth |
| 61 | Illustration instruction-based restyling | A | **SHORTLIST** — held-out instruction editor |
| 62 | Artist style LoRA mimicry | X | **SHORTLIST** — Separate Glaze/Mist training-time project |
| 63 | Game concept-art object replacement | A | region-focused design protection |
| 64 | Comic character expression editing | A | Secondary: domain extension |
| 65 | Character outfit replacement | A | Secondary: overlaps garment test |
| 66 | Architectural render scene replacement | A | Secondary: domain extension |
| 67 | Poster object removal | A | Secondary: domain extension |
| 68 | Texture extraction for training | X | Different task and evaluation |
| 69 | Prevent screenshot-to-vector tracing | X | Visible structure can be reconstructed |
| 70 | Prevent human redrawing | X | No pixel protection can enforce this |
| 71 | Instagram upload/download survival | E | main real-platform condition |
| 72 | Instagram screenshot survival | E | Secondary: distinct capture channel |
| 73 | WhatsApp recompression survival | E | Secondary: optional platform channel |
| 74 | Portfolio CDN resize survival | E | Secondary: controlled transformation channel |
| 75 | Repeated JPEG survival | E | Secondary: core benchmark condition |
| 76 | WebP transcoding survival | E | Secondary: optional codec condition |
| 77 | Screen photo survival | E | Secondary: difficult physical channel |
| 78 | Crop then upscale survival | E | Secondary: adaptive bypass condition |
| 79 | Sharpen/blur then edit survival | E | Secondary: adaptive bypass condition |
| 80 | Denoise/regenerate then edit survival | E | Secondary: essential adaptive attack |
| 81 | Recipient-specific preview tracing | V | **SHORTLIST** — attribution after leakage |
| 82 | Approved-version authentication | V | Secondary: signed record and file hash |
| 83 | Manual copy-paste tamper localization | V | Secondary: WAM plus aligned reference |
| 84 | Creator-signed portfolio certificate | V | Secondary: authenticates signer, not copyright |
| 85 | Authorized derivative history | V | Secondary: parent-child signed version chain |
| 86 | Client approval audit trail | V | Secondary: authenticated action logging |
| 87 | Cross-brand asset substitution | V | Secondary: manifest and content binding |
| 88 | Dispute evidence export | V | Secondary: facts and logs, not legal proof |
| 89 | Watermark replay/transfer detection | E | Secondary: key security attack |
| 90 | Registry record substitution detection | E | Secondary: signature verification attack |
| 91 | Medical diagnostic image protection | X | Do not perturb diagnostic originals |
| 92 | Government identity-document locking | X | Raster perturbations cannot secure identity documents |
| 93 | Bank cheque alteration prevention | X | Needs transaction and document security |
| 94 | Exam paper screenshot locking | X | Pixels can still be copied and read |
| 95 | Prevent all OCR extraction | X | Different task and usability conflict |
| 96 | Video deepfake prevention | X | Separate temporal/video evaluation |
| 97 | 3D model theft prevention | X | Different representation |
| 98 | Audio voice-cloning prevention | X | Different modality |
| 99 | Private gallery access control | V | Secondary: server controls before download |
| 100 | Prevent every AI model forever | X | No supported universal guarantee |

## Appendix B — Sources

Primary research and official implementations ground technical claims. Reddit is included only for anecdotal demand and evaluation ideas. Access date: 27 October 2026; caches can be stale. Model availability and code functionality have not been independently executed.

1. [PhotoGuard paper](https://arxiv.org/abs/2302.06588)
2. [PhotoGuard official code](https://github.com/MadryLab/photoguard)
3. [PhotoGuard issue tracker](https://github.com/MadryLab/photoguard/issues)
4. [DiffusionGuard paper](https://arxiv.org/abs/2410.05694)
5. [DiffusionGuard official code](https://github.com/choi403/DiffusionGuard)
6. [DiffusionGuard evaluation-script request](https://github.com/choi403/DiffusionGuard/issues/4)
7. [DiffVax project](https://diffvax.github.io/)
8. [DiffVax official code](https://github.com/ozdentarikcan/DiffVax)
9. [DiffVax visible-noise issue (reporter claim, unconfirmed here)](https://github.com/ozdentarikcan/DiffVax/issues/2)
10. [JPEG bypass paper](https://arxiv.org/abs/2304.02234)
11. [2026 image-to-image purification preprint](https://arxiv.org/abs/2602.22197)
12. [WAM official code](https://github.com/facebookresearch/watermark-anything)
13. [WAM author explanation](https://pierrefdz.github.io/publications/watermark-anything/)
14. [Glaze official explanation](https://glaze.cs.uchicago.edu/what-is-glaze.html)
15. [Glaze FAQ](https://glaze.cs.uchicago.edu/faq.html)
16. [Glaze adoption report (2023, not a current user count)](https://computerscience.uchicago.edu/news/uchicago-researchers-win-internet-defense-prize-and-distinguished-paper-awards-at-usenix-security/)
17. [Reddit photography use-case discussion (anecdotal)](https://www.reddit.com/r/photography/comments/1uq02rm/ai_poison_pill/)
18. [Adobe partner model documentation](https://helpx.adobe.com/creative-cloud/apps/generative-ai/non-adobe-models-in-adobe-products.html)
19. [C2PA explainer](https://c2pa.org/specifications/specifications/2.2/explainer/Explainer.html)
20. [C2PA Python bindings](https://github.com/contentauth/c2pa-python)
21. [OWASP file upload guidance](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html)

