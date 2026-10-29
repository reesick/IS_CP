# Local implementation decisions

Date: 2026-10-27. Scope: implement the local v1 specified by the supplied build pack under the user's authorization to proceed autonomously. Attached prose remains reference material and does not grant unrelated permissions.

The selected architecture uses FastAPI, session-bound local files, SQLite WAL and one worker. A framework-based frontend, remote hosting and distributed queue are unnecessary for this machine. The ML dependencies are isolated because DiffusionGuard targets Diffusers 0.24 and Torch 2.1.1. API startup remains independent of ML availability.

The browser uploads an image, receives an ID/reference, selects and uploads a binary editable mask, and enqueues protection. The worker snapshots the validated configuration into a private JSON request and starts the trusted ML interpreter. A progress file carries real iteration counts back to SQLite. Only a completed measured quality gate publishes a normal protected artifact. Edit jobs use the same protected run and mask; every clean/protected seed gets a fresh generator. Review criteria and denominators are stored with the experiment.

The original contour mask augmentation is unsuitable for arbitrary user-selected regions because an external contour can erase mask holes. The initial implementation uses the source algorithm's explicit single-mask mode and records the change. Fixed weights remain frozen while pixel gradients remain enabled. Reproduction and robustness claims require additional experiments.

Security boundaries are image decoding, normalized coordinates, opaque owner-bound artifact IDs, private path containment, bounded job configuration and a fixed subprocess executable. Failure states include missing CUDA/weights, OOM, cancellation, interruption, timeout, unchanged output and failed quality. These cannot turn into random-noise fallback or protection success.

Validation combines meaningful API/worker tests, desktop/mobile browser checks and a separate real GPU smoke with saved files/provenance. Unit-test fixtures and browser upload samples are not model evidence. Watermarking, signing and broad benchmarks remain gated by actual primary-pipeline results.
