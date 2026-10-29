"""Real upstream mask/gradient smoke; explicitly not a reproduction benchmark.

Run in the isolated ML environment:
python -m backend.app.ml.smoke --output data/ml-smoke [--edit]
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="data/ml-smoke")
    parser.add_argument("--edit", action="store_true")
    parser.add_argument("--mask-only", action="store_true")
    args = parser.parse_args()
    import numpy as np
    from PIL import Image, ImageDraw, ImageOps
    from .defenders import _load_upstream, protect
    from .editor import edit_pair

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    y, x = np.mgrid[:512, :512]
    rgb = np.stack([60 + x * 0.25, 80 + y * 0.2, 100 + (x + y) * 0.08], axis=-1).astype(np.uint8)
    clean = Image.fromarray(rgb)
    draw = ImageDraw.Draw(clean)
    draw.ellipse((180, 180, 332, 332), fill=(188, 105, 62), outline=(70, 40, 20), width=3)
    mask = Image.new("L", (512, 512))
    ImageDraw.Draw(mask).rectangle((160, 160, 352, 352), fill=255)
    clean.save(out / "clean.png")
    mask.save(out / "mask.png")
    _, _, utils, _ = _load_upstream()
    for editable in (mask, ImageOps.invert(mask)):
        retained = ImageOps.invert(editable).convert("RGB")
        canonical = utils.get_mask([retained], retained, utils.get_mask_radius_list([retained]), mode="single")
        expected = np.asarray(editable, dtype=np.float32) / 255
        assert np.array_equal(canonical.numpy().squeeze(), expected), "Upstream single mask polarity is wrong"
    evidence = {"synthetic_input": True, "purpose": "smoke, not efficacy benchmark",
                "two_region_single_mask_semantics": "passed"}
    if args.mask_only:
        print(json.dumps(evidence), flush=True)
        return

    def progress(done, total, stage):
        print(json.dumps({"done": done, "total": total, "stage": stage}), flush=True)

    provenance = protect(out / "clean.png", out / "mask.png", out / "protected.png",
                         {"profile": "smoke", "epsilon": 4 / 255, "seed": 42}, progress=progress)
    delta = np.asarray(Image.open(out / "protected.png"), dtype=np.float64) - np.asarray(clean, dtype=np.float64)
    mse = float(np.mean(delta**2))
    assert np.max(np.abs(delta)) > 0, "Pixels did not change"
    assert np.max(np.abs(delta)) <= 5, "Saved pixels exceed configured epsilon plus quantization tolerance"
    evidence.update(provenance=provenance, max_difference_255=float(np.max(np.abs(delta))),
                    psnr_db=10 * math.log10(255**2 / mse), actual_pixel_change="passed")
    if args.edit:
        evidence["paired_edit"] = edit_pair(out / "clean.png", out / "protected.png", out / "mask.png", out,
                                           {"prompt": "a shiny silver ball", "seeds": [11]}, progress=progress)
    (out / "evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps(evidence), flush=True)


if __name__ == "__main__":
    main()
