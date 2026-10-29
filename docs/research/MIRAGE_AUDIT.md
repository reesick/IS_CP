# MIRAGE audit: false moderation for image-edit protection

Audit date: 2026-10-28. Research only: no author code executed, dependencies installed, weights downloaded, GPU reproduction performed, or images sent to an external service during this audit.

## Identity and source availability

The audited work is **MIRAGE: Protecting against Malicious Image Editing via False Moderation**, Anshul Nasery, Ramnath Kumar, Cho-Jui Hsieh, Sewoong Oh, arXiv:2606.26199v2, revised June 26, 2026. Primary sources: [versioned full text including Appendices A–C](https://arxiv.org/html/2606.26199v2), [abstract/version history](https://arxiv.org/abs/2606.26199), [PDF](https://arxiv.org/pdf/2606.26199v2). Paper license: CC BY 4.0. The facts and tables below are attributed to that paper, separately from our engineering inferences.

No author-official implementation, project site, target asset bundle, or MIRAGE-specific learned weights was verified. The full text contains no implementation link (its GitHub links concern arXiv HTML infrastructure). [First author's publications](https://anshuln2.github.io/publications/) and [Sewoong Oh's publications](https://homes.cs.washington.edu/~sewoong/papers.html) link the work to arXiv only. [Ramnath Kumar's publications](https://ramnathkumar181.github.io/publications/) lists the work with a PDF. Searches for the exact title, identifier, and MIRAGE plus false moderation did not establish a code release.

Read-only GitHub API checks enumerated all returned repositories for [anshuln2](https://api.github.com/users/anshuln2/repos?per_page=100), [RamnathKumar181](https://api.github.com/users/ramnathkumar181/repos?per_page=100), and [SewoongLab](https://api.github.com/orgs/SewoongLab/repos?per_page=100); none was this implementation. Repository searches for `2606.26199` and `MIRAGE moderation` likewise found no implementation. This is a bounded negative search, not proof that private or unindexed code does not exist. Accordingly, repository commit, stars, activity and source-code license are **not available**, not zero. No `third_party/MIRAGE` checkout was created. Unrelated MIRAGE editing benchmark repositories must not be substituted.

## Published algorithm and implementation contract

The method maximizes surrogate evidence that an otherwise benign input belongs to a policy-prohibited category. The intended outcome is refusal by a commercial editing service, rather than corruption of its generative model. All surrogate parameters remain frozen; gradients act on source pixels.

For source `x`, bounded perturbation `delta`, fixed target set `T`, and encoder `F_i`, define:

```text
phi_i(z,T) = mean_{y in T} cosine(F_i(z), F_i(y))
J(delta) = sum_i [phi_i(global(x+delta),T)
                  + (lambda/k) sum_{j in top_k} phi_i(local_j(x+delta),T)]
maximize J(delta), subject to ||delta||_inf <= B
```

Use image embeddings for image-only DINOv2; image/text compatible embedding spaces for CLIP-style models. The moderation surrogate contributes its scalar unsafe score instead of an embedding cosine. The prose does not specify exactly how this scalar is weighted against other surrogate terms or how ShieldGemma's score is extracted differentiably. Targets are fixed concept examples, not updated during optimization: main experiments use **five sexual-category images and three text descriptions**. Exact text, image provenance, asset bytes, and hashes are not published in the audited paper. Violence/gore is an ablation. No target assets were collected in this audit.

The equation uses raw cosine similarity, not absolute cosine, squared feature distance, a cross entropy classification loss, or an instruction-following objective. Although the paper writes cosine as belonging to `[0,1]`, mathematical cosine generally spans `[-1,1]`; no remapping or clamp is specified. Do not silently implement one.

The global view resizes the full input to each encoder's native resolution. Local views sample native source-image crops and compare their features with the same target features; each surrogate selects the most aligned crops independently. Main settings:

| Setting | Published value |
|---|---|
| Optimizer | L-infinity PGD / iterative FGSM, maximizing objective |
| Iterations | 5,000 |
| Step size / schedule | 1.0 / cosine |
| Main RGB bound | 16/255; ablations 2/255, 4/255, 8/255 |
| EOT samples | 1 per step |
| Local patches | 16 randomly sampled |
| Local patch size | Table V: 256; appendix prose: 255x255; method prose: native encoder r |
| Local aggregation | mean of top 8 similarities |
| Local weight | 0.25 |
| Model drop probability | 0.3 |
| Minimum models selected | 3 |
| Native images | up to 1024x1024; no pre-immunization/API downsampling |

The step-size entry `1.0` has no explicit byte-versus-normalized pixel unit. An implementation that interprets it as `1/255` in `[0,1]` must identify that as its assumption. The natural projected update is `delta <- project_B(delta + alpha_t sign(grad J))`, followed by valid pixel-range clipping, but initialization, precise cosine schedule endpoints, clipping order and byte rounding are not specified. No MIRAGE random seed is published. The seed 0 in Table VI belongs to BlurGuard and must not be attributed to MIRAGE.

EOT samples uniformly from an augmentation set including crop, resize, Gaussian blur, JPEG compression and flips, with a straight-through gradient estimator for JPEG. Training augmentation probabilities, parameter ranges, interpolation, antialiasing, and composition order are not supplied. Do not confuse the separately specified evaluation transforms with training ranges. Encoder preprocessing must preserve gradients through resizing and normalization; conversion to a PIL image inside the optimized path would break these gradients. The paper does not supply exact encoder preprocessing code, feature pooling, precision or dependency versions.

For model dropout, cache two exact gradients `g1,g2` and their perturbations `d1,d2` per surrogate. For a dropped model, use the published secant estimate:

```text
s = d1 - d2
g_pred = g1 + (g1 - g2) * dot(s, delta_current - d1) / dot(s,s)
```

The paper does not state cold-start handling, zero-denominator stabilization, extrapolation clipping or cache dtype/device. Safe handling must be explicit in a reimplementation and recorded as an adaptation. Sequential encoder gradients can sum into a common image gradient; they need not retain every encoder graph simultaneously.

An optional public OpenAI moderation API checkpoint is scored every 250 steps. This is **not** the internal editor safety model and does not prove refusal. Omitting that selection was comparable or better in the authors' ablation. A local-only implementation should omit remote selection and label that choice. No external API call is authorized by reading this paper.

## Exact full ensemble and verified upstream weight sources

Table V's eight models are listed below. Hugging Face model metadata was queried read-only on the audit date; listed revisions are contemporary metadata observations, **not author-pinned revisions or locally downloaded snapshots**. OpenCLIP checkpoint names and corresponding model cards are distinguished.

| Paper model/checkpoint | Verified model card | Observed revision | Card license / access |
|---|---|---|---|
| hf_dinov2:facebook/dinov2-base | [facebook/dinov2-base](https://huggingface.co/facebook/dinov2-base) | f9e44c814b77203eaa57a6bdbbd535f21ede1415 | Apache-2.0 / public |
| hf_siglip:google/siglip-base-patch16-224 | [google/siglip-base-patch16-224](https://huggingface.co/google/siglip-base-patch16-224) | 7fd15f0689c79d79e38b1c2e2e2370a7bf2761ed | Apache-2.0 / public |
| open_clip:ViT-B-32/laion2b_s34b_b79k | [LAION B-32](https://huggingface.co/laion/CLIP-ViT-B-32-laion2B-s34B-b79K) | 1a25a446712ba5ee05982a381eed697ef9b435cf | MIT / public |
| open_clip:ViT-B-16/laion2b_s34b_b88k | [LAION B-16](https://huggingface.co/laion/CLIP-ViT-B-16-laion2B-s34B-b88K) | 7288da5a0d6f0b51c4a2b27c624837a9236d0112 | MIT / public |
| open_clip:ViT-L-14/datacomp_xl_s13b_b90k | [DataComp XL L-14](https://huggingface.co/laion/CLIP-ViT-L-14-DataComp.XL-s13B-b90K) | 84c9828e63dc9a9351d1fe637c346d4c1c4db341 | MIT / public |
| open_clip:ViT-L-14/dfn2b_s39b | [Apple DFN2B L-14](https://huggingface.co/apple/DFN2B-CLIP-ViT-L-14) | 13d68e40771108ec1812f566404e8c6f7de85f67 | apple-amlr / public |
| open_clip:ViT-H-14/dfn5b | [Apple DFN5B H-14](https://huggingface.co/apple/DFN5B-CLIP-ViT-H-14) | 11738501a1db6d5e0a3451a71ba100be02e577e6 | apple-amlr / public |
| shieldgemma:google/shieldgemma-2-4b-it:sexual | [Google ShieldGemma 2](https://huggingface.co/google/shieldgemma-2-4b-it) | eaf60452b5fc41a911338a022e628b0c15283897 | Gemma / manually gated |

These are existing surrogate weights; MIRAGE does not train a new model. Card license labels are metadata, not a full legal compatibility assessment. Public metadata on ShieldGemma does not grant weight access. The prose's claim of eight CLIP-style models plus additional families conflicts with the table: the actual table totals eight including DINOv2 and ShieldGemma. Use the table for the declared full configuration and preserve this discrepancy.

## Published efficacy and robustness, not our reproduction

Authors reran final commercial experiments June 10, 2026 using GPT-Image-2, Gemini-3.1-Flash-Image, and Grok-Imagine-Image developer endpoints. Main data: 100 ImgEditBench images/prompts and 48 SHHQ human images; SHHQ prompt: put this person inside an office. Table I main refusals: **100.0%, 88.5%, 94.0%**, respectively. Some refusals may be post-generation moderation; the observable API refusal alone does not identify which stage fired. Clean-control refusal counts, repeated-query variance and confidence intervals are not supplied in the audited tables.

SHHQ budget study (Table IV; percentages):

| Bound | GPT-Image | Gemini | Grok |
|---|---:|---:|---:|
| 2/255 | 7.1 | 0.0 | 4.8 |
| 4/255 | 50.0 | 16.7 | 22.9 |
| 8/255 | 89.6 | 75.0 | 77.1 |
| 16/255 | 100.0 | 100.0 | 100.0 |

Four-model SHHQ ablation (Table II): at 8/255, 77.1/58.3/52.1%; at 16/255, 93.8/91.7/89.6%. Six-model: at 8/255, 89.6/62.5/77.1%; at 16/255, 97.9/95.8/95.8%. The paper does **not** identify the exact members of those subsets despite referring to Table V, which lists only the full set. A four-encoder local profile cannot claim these ablation results unless subset identity is established. Global/local ablation is consequential: at 8/255 no-GL rates are 66.7/62.5/16.7%; full GL table rates 89.6/68.8/75.0%.

Table III robustness percentages (API order remains GPT/Gemini/Grok): Gaussian blur radius 1, JPEG quality 50, half-size resize, and simulated screenshot each report 100/100/100. Screenshot simulation: long side 1080, slight blur, JPEG75. Subject bounding-box crop: 100/100/97.9. Equalization: 93.8/87.5/83.3. Grayscale: 89.6/77.1/85.4. Simulated screen photo: 91.7/83.3/87.5; simulated social-media square crop plus contrast/sharpen: 73.0/77.0/75.0. These simulations are **not** real social platform or camera round trips; detailed parameters are absent for some transforms.

Strong attacks expose the limit. Foreground segmentation onto white: 89.6/77.1/85.4. Local Flux-v.2-Klein-4B denoising before commercial editing: refusals 56.2/64.6/78.0; GPT's judge-inclusive failure rate is 70.8. A four-embedding-model adversary minimizing the same target alignment for 2,000 PGD steps with bound16/255 cuts Table III refusals to **8.3/10.5/6.2**; judge-inclusive failures 47.9/14.6/12.5. The prose instead describes 12.5% Gemini/Grok refusal, conflicting with the table; do not merge the two metrics. Local editing without a corresponding moderation gate bypasses the mechanism. Exact local-edit percentages are not tabulated in the audited appendix.

Appendix C combines MIRAGE and a PhotoGuard-style Flux4B objective in two qualitative examples. This is preliminary qualitative evidence, without an exact combined loss coefficient/configuration or a quantitative benchmark. It does not establish generic combined protection against arbitrary local editors.

## Fidelity, practical risks, and six-GB implementation prospects

Authors explicitly acknowledge visible artifacts at larger budgets. An L-infinity bound of16/255 permits roughly6.3% channel-intensity changes; it does not establish perceptual invisibility. No PSNR/SSIM/LPIPS acceptance threshold or main-table fidelity statistic is specified. Our exports therefore require saved-file, decoded-pixel quality measurements independent of efficacy.

False moderation only affects services with a compatible, susceptible safety pipeline. It can also interfere with legitimate uploads, hosting, accessibility or intended edits; the paper does not quantify these collateral outcomes. Prompt changes intended to jailbreak the refusal are excluded by its threat model. New service versions, provider preprocessing, purification, inverse optimization, and local editors can defeat the defense. Grok changed silently during the authors' experiments. No present-day guarantee follows from June API measurements.

The authors report15minutes for one1024x1024 image,5000steps on oneA40. There is no measured RTX4050/Windows/Python3.11/PyTorch2.1.1 result. **Engineering inference:** a4B-parameter moderator alone needs about8GB for two-byte weights before activations, so a straightforward full eight-model resident reproduction cannot fit6GB. Model dropout reduces graphs but does not automatically evict weights. CPU offload or quantization changes execution requirements and may change gradients; quantized inference compatibility does not establish differentiable image-input support.

Small frozen encoders processed sequentially, local patch microbatches, frozen precomputed target vectors, and CPU-held gradient caches are plausible local experiments. For1024x1024 RGB, one float32 gradient is12MiB; two gradient plus two perturbation caches across eight models use about384MiB before models/activations. Top-k patch selection can be scored without retaining all graphs, then selected patches recomputed for gradients, preserving the objective only when the same views and encoder state are reused. This is an engineering plan, not measured fit/performance.

A reduced CLIP/SigLIP/DINO profile must be named a **paper-informed experimental implementation**, with its encoder subset, preprocessing, target substitutions, seed, step units, resolution, augmentation assumptions and omitted moderator recorded. It must never inherit the full paper's88%+ claim. The existing project512x512 canvas is a deliberate resolution adaptation relative to MIRAGE's native-resolution study. Torch2.1.1 package compatibility and current ShieldGemma support have not been verified; use an isolated environment and inspect supported package requirements before installation. Do not upgrade the working DiffusionGuard environment implicitly.

## Required evidence before an efficacy claim

No MIRAGE efficacy has been reproduced here. A local loss increase or surrogate moderation score is only optimization evidence. The application should preserve that distinction, record exact asset/model hashes and all deviations, enforce decoded export fidelity independently, and leave modern commercial refusal **unverified** until a user-authorized paired evaluation of the same clean/protected image, prompt, service/version, and input transform is available. Classify policy refusals separately from network failures, invalid requests and quality rejection. Local-only authorization prohibits automatic cloud validation.
