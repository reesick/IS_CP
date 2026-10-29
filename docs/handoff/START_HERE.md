# START HERE — Give this folder to your coding AI
Date: 27 October 2026. Project: ImageShield. Subject: Information Security.

## Paste this instruction into the coding AI
Implement ImageShield from this documentation. Read BUILD_SPEC.md, MODEL_SETUP.md and DESIGN.md completely, then consult RESEARCH_AND_USE_CASES.md. Follow the numbered milestones and produce real working code, not a mockup.

Main feature: the user uploads an existing image, the system adds visually subtle adversarial perturbations, and a compatible AI editor produces an unusable or degraded requested edit. Keep the protected input good-looking. Build a paired Attack Lab that uses the same prompt, mask and random seed on clean and protected images.

Use Python + FastAPI + SQLite + one Python worker. Serve a simple HTML/CSS/JavaScript frontend from FastAPI. No frontend framework or Node build is needed. Make the interface look like a restrained Vercel developer product, using DESIGN.md. Vercel is visual inspiration; GPU execution is not a Vercel serverless function.

First reproduce DiffusionGuard with a fixed pretrained Stable Diffusion inpainting checkpoint. Do not train a diffusion model. Do not substitute random noise or watermark extraction for adversarial protection. Keep DiffVax optional until its checkpoint and visual quality are independently verified. Watermark and signed verification are phase 2.

Read the actual upstream source and configuration before adapting it. Pin the resolved repository commit and model revision after successful smoke tests. Never invent a revision, output path, benchmark score or compatibility result.

Start with a 512x512 research export and a visible region-selection control. Show resolution changes. A single known mask does not protect every future region. One-click unknown-mask mode is a later evaluated extension.

Make all failure states honest. Missing weights, missing CUDA, OOM, quality-gate failure, or no measured disruption must never produce a “successfully protected” badge. UI fixtures must be visibly labeled and excluded from measured results.

Run CPU/API checks, then real GPU smoke tests when hardware and models are available. Keep implementing independent pieces if model download or GPU access is unavailable. At completion report commands run, results, unresolved blockers, changed files and instructions for local launch. Do not stop after writing a plan.

## Read order
1. BUILD_SPEC.md — architecture, API, acceptance criteria and milestones.
2. MODEL_SETUP.md — exact checkpoints, source setup, dependencies, masks and GPU constraints.
3. DESIGN.md — UI structure, visual tokens and Vercel Labs reference.
4. RESEARCH_AND_USE_CASES.md — research evidence, 100 candidates, 12 selected scenarios and extended security/benchmark plan.
5. models.example.json — machine-readable model registry template.
6. scripts/setup/check_environment.py — executable preflight utility.

## What this package is
A build-ready specification and research handoff. It is not an implemented application. Upstream model documentation was checked; no GPU defense, Instagram round trip or Photoshop benchmark was executed while preparing it.

## Source-of-truth precedence
This package's BUILD_SPEC.md defines the small initial implementation. The research brief describes a broader future architecture with Redis/cloud storage; do not add that infrastructure to v1. DESIGN.md defines appearance. MODEL_SETUP.md defines reproducibility constraints. Report any real incompatibility rather than silently changing the experiment.

