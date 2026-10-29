# Research decision and implementation evidence

Date: 28 October 2026. User objective: a visually usable image that resists later AI edits through refusal, no-op, or unusable generation. A fidelity score, completed optimization or changed edit output does not establish that objective. The earlier successful beige-shorts edit is a recorded bypass observation, with editor/version still unspecified.

## Latest-first screening

Sources below are primary papers, official projects or observed service metadata. Publication freshness, stars and screenshots are screening signals, not reproduced efficacy. No source photos were uploaded to external inference services.

| Candidate | Date / mechanism | Reproduction state observed here |
|---|---|---|
| [Copying as Defense, CaD](https://arxiv.org/html/2610.35566v1) | 26 Oct2026; early DiT attention maximization induces copying | Full method/appendix inspected. No verified author code link. Exact Eq13 loss kernel implemented and CPU value/gradient equivalence checked. Full FLUX/FIBO execution not reproduced. |
| [SRIM](https://arxiv.org/abs/2610.07464) | Oct2026; worst-scale optimization for high-resolution images | Full paper audited by research agent; no verified public implementation. FLUX2 models required for its reported frontier tests. |
| [SPIN](https://arxiv.org/abs/2610.06334) | Oct2026; projected denoising-neighborhood objective | Paper inspected; no verified release. Seen/unseen-instruction evaluation must not be called universal cross-model transfer. |
| [NullEdit](https://arxiv.org/abs/2608.10870) | Aug2026; VLM condition redirection toward no-op | No verified relevant author implementation; unrelated same-name LoRA repos excluded. Step1X/Qwen backbones are substantially heavier than the present SD1.5 environment. |
| [VETO](https://arxiv.org/abs/2607.27292) | July2026; attacks reference reading in modern joint-attention editors | Search index showed a repo with5stars, but direct GitHub API and git clone returned404. Availability is404, not a verified release or current star count. |
| [TDAE](https://pubmed.ncbi.nlm.nih.gov/41779663/) | July2026; image/text optimization for transfer | Paper evidence found; no verified runnable official release in this audit. |
| [MIRAGE](https://arxiv.org/html/2606.26199v2) | June2026; false moderation/refusal across commercial APIs | Detailed audit in MIRAGE_AUDIT.md. No official implementation or exact target asset release verified. Full eight-model commercial rate not reproduced. |
| [Universal Immunization](https://arxiv.org/abs/2602.14679) | ECCV2026; image-agnostic semantic-injection perturbation | Official repo clone has website only, literally Code coming soon. No UAP/checkpoint/source available to run. |
| [DiffVax](https://github.com/ozdentarikcan/DiffVax) | ICLR2026; pretrained one-pass NestedUNet | Verified MIT source and36.8MB checkpoint. Actual local CUDA inference completed in both released-demo BatchNorm mode and explicit eval adaptation. |
| [DeContext](https://github.com/LinghuiiShen/DeContext) | Dec2025; DiT context-attention suppression | Actual source cloned and inspected; uses Torch2.6/Diffusers0.35 and gated FLUX Kontext or larger Step1X weights. It is not automatically a refusal defense. |
| [DCT-Shield](https://arxiv.org/html/2504.17894v2) | ICCV2025; optimizes JPEG DCT coefficients | Official project page says Code coming soon; following its actual Code link confirmed an empty SamsungLabs/dct-shield repo. Merely adding JPEG EOT to PhotoGuard would not reproduce its frequency-domain algorithm. |
| [Anti-Diffusion](https://github.com/whulizheng/Anti-Diffusion) | AAAI2025; prompt tuning plus semantic disturbance | Actual code cloned; SD2.1-centered released example. Must distinguish its tested scope from newer closed editors. |
| [DiffusionGuard](https://github.com/choi403/DiffusionGuard) | ICLR2025; denoiser objective and mask augmentation | Actual adapter already runs, but20-step low-budget tests were not the800-step paper profile. Evaluation reproducibility issue remains open. |
| [PhotoGuard](https://github.com/MadryLab/photoguard) | ICML2023; encoder/diffusion attacks | Verified official code cloned at686bea75c786cb46c88fc396a0cd0ee3d7d28c2e. Full1000-step released encoder profile completed; quality failed. |
| [Anti-DreamBooth](https://arxiv.org/html/2303.15433v2) | ICCV2023; poisoning later personalization training | Different task from one-image inference-time editing; not counted as evidence for this product goal. |

## Current primary-service observations

The actual read-only API snapshot is PRIMARY_SERVICE_SNAPSHOT.json. It records source URLs, push dates, licenses, access and observed stars: PhotoGuard729, DiffusionGuard50, DiffVax24, DeContext22, Anti-Diffusion9, website-only Universal-Immunization0, Anti-DreamBooth315. Counts can change and do not validate algorithms. Missing MIRAGE/CaD implementations have unknown stars, not fabricated zeroes.

## Implemented now

1. `backend/app/ml/research_objectives.py`: CaD Eq13 reference-attention ascent loss with query chunking and actual attention-mask handling; MIRAGE raw target-cosine/top-k objective, secant gradient predictor and bounded RGB projection. No random substitute representations are used to generate protected exports. CPU mathematical tests are explicitly not an end-to-end defense.
2. `backend/app/ml/diffvax.py`: verified official model.py imported without package CUDA side effects; checkpoint loaded with `weights_only=True` and strict keys/hash. Matches the released demo's masked-context half-to-float input and restores original editable pixels. No invented epsilon projection. Runs both source-default training BatchNorm and separately labeled eval BatchNorm.
3. `backend/app/ml/photoguard.py`: released notebook encoder objective toward zero latent,1000steps, normalized epsilon.06 and step.02 with linear decay. Reuses the exact installed SD1.5 inpainting VAE, recorded as a model/evaluation adaptation. Detaching iterate history and VAE checkpointing preserve current-pixel derivatives while bounding memory.
4. `backend/app/ml/contrastive_probe.py`: runnable, **reduced experimental** MIRAGE-informed profile using one paper-listed CLIP surrogate and disclosed substitute text targets. It omits unreleased target images, seven ensemble members, full model dropout and remote moderation selection. EOT ranges, step units and initialization are explicit assumptions. It is not the paper's full method and cannot inherit88%+ efficacy.
5. `backend/app/ml/dct_shield.py`: separate paper-derived base coefficient optimizer, with standard JPEG tables/4:2:0 implementation choices disclosed. Actual1000-step local optimization completed; source fidelity failed (27.19dB/.5477). Six actual PNG/JPEG85 editor pairs completed. JPEG85 restored plausible edits in inspected outputs; no robustness success established. Mask-based and Y-only paper variants are not implemented or claimed.
6. `backend/app/ml/cad.py`: paper-derived FLUX joint-attention adapter, including normalized text Q/K and joint RoPE, prefix truncation and Eq13. Full-resident loader rejects the present6GB hardware and missing local gated weights before attempting an impossible allocation. Full model execution and frontier transfer remain unverified.

The isolated `.venv-frontier` now has verified official Torch2.6.0+cu124 wheels,
Diffusers0.35.2 and locked installed dependencies; `pip check` passed. Actual
tiny randomly initialized Diffusers FLUX and VAE architectures pass nine
contract checks, including a live objective gradient all the way to RGB pixels.
This validates the integration path at small scale, not pretrained protection.
See CAD_FLUX_ARCHITECTURE_CHECK.json and FRONTIER_ENVIRONMENT.json. The existing
SD1.5/API environments remain separate.

The full5000-step reduced refusal probe completed in583.70 seconds at768x1024. Its quality failed (31.46dB/.7901), with visible artifacts. No moderation/API inference was performed. The PhotoGuard1000-step cap experiment failed quality too (31.91dB/.6588). Across PhotoGuard and two DiffVax modes, nine actual cap pairs completed with matching clean-output hashes by seed; visually usable green-cap edits remain possible. Fifteen total research pairs / thirty generated edits have now completed including DCT's two channels. No human efficacy rate is fabricated.

All work remains in an isolated research path rather than adding unvalidated methods to the product Protect button. Exact PNGs, model/source provenance, failed quality checks and raw paired results are retained under ignored `outputs/research-2026-10-28/`.

## Actual DiffVax execution findings

Source commit77fe66a8e6d50223a929081ec0851d9a49153903; checkpoint SHA256 b52500bf07a23aaf3d499adfaebe3e894c5d4fe2b4607fd6aa7fa64665bc43c0. Released wrapper ignores its epsilon argument. The demo also runs BatchNorm in training mode. Both are material correctness issues, not evidence supplied by a README picture.

Raw demo-mode exports on T-shirts/cap/shorts measured PSNR24.79/22.46/26.79dB and SSIM.9029/.8485/.9108: all failed the unchanged fidelity thresholds. Eval-mode adaptation measured33.39/37.47/35.68dB and.9874/.9850/.9866; two pass these aggregate thresholds, but maximum per-channel changes reach.86/.48 on those images. No bounded-budget success or editor prevention is implied. Repaired/clipped output would require a new efficacy evaluation.

## Hardware/access facts

Local machine: RTX4050 Laptop6GB, approximately16GB system RAM, approximately16GB free on D at audit start. HF metadata confirms FLUX.1 Kontext is gated; its transformer shards alone total roughly24GB before T5 and other components. FLUX.2-klein4B is public Apache2, but requires roughly7.75GB transformer plus8.05GB text encoder and.17GB VAE on disk; the model card states about13GB native inference VRAM. CPU offload may change execution feasibility, but does not by itself prove differentiable defense optimization works.

MIRAGE's full ShieldGemma4B moderator is manually gated and needs about8GB just for two-byte weights. Its exact target bank and some hyperparameters are unpublished. A6GB small-encoder probe must not be presented as full reproduction. No acceptance of model-license gates, cloud GPU deployment or paid/external image inference has been performed.

## The pasted PhotoGuard guide

Read as reference material, not instructions to use Colab or upload local photos. It correctly identifies PhotoGuard and distinguishes training-time Anti-DreamBooth from edit-time protection. Its plain-target explanation is simplified: the referenced img2img notebook actually minimizes VAE posterior-mean norm toward zero latent. The interactive inpainting demo uses an encoded gray target and different steps/budget. These profiles cannot be merged silently. DCT-Shield is an optimization over JPEG coefficients, not simply a generic compression transform inside another method.

## Acceptance and next evidence

Qualify a clean editor/task first, freeze prompts/masks/seeds, then score paired protected edits by requested change, usability and retained content. Report refusal, no-op, corruption and service failures separately. Keep quality and efficacy gates separate. No current research result permits an all-model guarantee. Commercial frontier refusal remains unverified until the user authorizes or manually supplies actual paired outputs; the local-only instruction remains in force.
