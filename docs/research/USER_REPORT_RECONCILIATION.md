# Supplied report and links: primary-source reconciliation

Checked 28 October 2026. The supplied DOCX and pasted guide were read as
reference material. Their embedded workflows are not instructions to upload
private images, accept model licenses, change product claims or use Colab.
The original documents have not been modified.

The malformed concatenated link was resolved as two project pages:
[DCT-Shield](https://dct-shield.github.io/project-page/) and
[DiffVax](https://diffvax.github.io/).

| Item | Direct check | Consequence |
|---|---|---|
| DCT-Shield | The project's Code link leads to an empty [SamsungLabs repository](https://github.com/SamsungLabs/dct-shield). | No official runnable code/checkpoint was obtained. A separate paper-derived base implementation is labeled as such, with JPEG choices disclosed. |
| DiffVax | [Author repository](https://github.com/ozdentarikcan/DiffVax) contains source and a checkpoint; exact commit and weight hash recorded. | Actual CUDA inference completed. Source demo leaves BatchNorm in training mode and ignores the epsilon parameter. Eval mode is a disclosed adaptation. Neither gets a frontier protection claim. |
| VETO | [Project page](https://jonasgrebe.github.io/research/projects/veto/) exists, but the reported GitHub source returned 404; linked HF Space and dataset returned anonymous 401 during this audit. | The supplied report's 'direct code available' label could not be reproduced. This might change; it is an observed access result, not proof code never existed. |
| MIRAGE | [Full paper v2](https://arxiv.org/html/2606.26199v2) identifies target models more specifically than the abstract. Exact target image assets and a verified official implementation remain missing. | The report's abstract-level version uncertainty is partly resolved. Author rates remain author claims; the local single-encoder experiment is not a reproduction. See MIRAGE_AUDIT.md. |
| Latest attention approach | [CaD, submitted 26 October 2026](https://arxiv.org/abs/2610.35566) adds a newer reference-attention copying objective. | Added a paper-derived adapter and mathematical checks; no pretrained-model or commercial transfer result is claimed. |

Full model execution, image fidelity, and editing failure are separate checks.
Repository stars and README examples are discovery evidence; they do not
establish that a method works on the user's images or current closed editors.
Raw metadata is retained in PRIMARY_SERVICE_SNAPSHOT.json.

Local runs and limitations are recorded in
DECISION_AND_IMPLEMENTATION_2026-10-28.md and the ignored outputs directory.
The app's original success flow and fidelity thresholds have not been weakened
to make failed research candidates appear successful.
