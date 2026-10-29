#!/usr/bin/env python3
"""Read-only environment preflight. Does not install packages or load model weights."""
import argparse
import importlib.metadata
import json
import platform
import sys

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-cuda", action="store_true")
    args = parser.parse_args()
    packages = {}
    for name in ("torch", "torchvision", "diffusers", "transformers", "huggingface-hub",
                 "numpy", "Pillow", "fastapi", "uvicorn"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    report = {
        "python": platform.python_version(), "platform": platform.system(),
        "packages": packages, "cuda_available": False, "gpu": None,
        "vram_gib": None, "model_weights_checked": False, "errors": [],
    }
    if packages["torch"] is not None:
        try:
            import torch
            report["cuda_available"] = bool(torch.cuda.is_available())
            if report["cuda_available"]:
                props = torch.cuda.get_device_properties(0)
                report["gpu"] = props.name
                report["vram_gib"] = round(props.total_memory / (1024 ** 3), 2)
        except Exception as exc:
            report["errors"].append({"code": "TORCH_IMPORT_OR_CUDA_ERROR", "type": type(exc).__name__})
    if args.require_cuda and not report["cuda_available"]:
        report["errors"].append({"code": "CUDA_REQUIRED", "message": "Use a CUDA-enabled ML environment and supported NVIDIA GPU."})
    report["preflight_ok"] = not report["errors"]
    print(json.dumps(report, indent=2))
    return 1 if report["errors"] else 0

if __name__ == "__main__":
    sys.exit(main())

