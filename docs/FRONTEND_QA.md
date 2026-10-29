# Local browser validation

Run on 27 October 2026 against the real FastAPI app at `http://127.0.0.1:8000`, using headless Microsoft Edge and Playwright. No API response mocking or protection fixtures were used. The uploaded synthetic picture is visibly labeled **UI TEST IMAGE — Not an efficacy result**. Test assets were deleted after each run.

## Passed

- Desktop 1440 px and mobile 390 px layouts, with no horizontal overflow.
- Image upload, correct 512×512 canvas and letterbox display, numeric mask selection, and selection restoration after refresh.
- Pointer rectangle maps from CSS coordinates to 512-pixel image coordinates. A second test fetched the actual saved background-complement mask and confirmed black padding, black retained selected object, and white editable real-image background.
- Actual unavailable-model response displayed inline; no protected export or success badge appeared.
- URL hash tabs, back navigation, keyboard arrow navigation, light/dark theme, and reduced-motion setting.
- Transparent PNG confirmation with a preview on the same #f4f4f5 background as the backend.
- Asset/artifact deletion and recovery to upload state.
- No browser JavaScript errors or Content Security Policy violations in tested flows.

Screenshots and machine-readable results: `docs/screenshots/`.

## Reproduce

With the local app running:

```powershell
npm install --prefix .cache/ui-test playwright@1.64.1
node scripts/browser/interface-qa.cjs
node scripts/browser/mask-qa.cjs
```

The Playwright npm package is installed under `.cache/ui-test`; these scripts use the installed Microsoft Edge executable and do not download another browser.

## Actual GPU follow-up

The primary agent subsequently ran `node scripts/gpu-browser-qa.cjs` against the real worker and CUDA models. Upload, numeric region, 20-step protection, quality-passing export, and four-image paired editing passed with no page errors. Authentic running/export/comparison screenshots are available at 1440 and 390; `gpu-browser-qa.json` records their actual jobs. Rejected-quality evidence is preserved separately. A 1/255 smoke budget yielded PSNR50.6255dB/SSIM0.992204; 2/255 and4/255 failed SSIM on this synthetic image. Exact download and synthetic JPEG-channel checks have separate JSON receipts. This establishes working execution, not edit-prevention efficacy.

Actual CUDA cancellation, multi-seed human-review interaction and restoration mid-optimization have not been browser-tested. API/worker regression tests cover their lifecycle boundaries. Human visual scores and a controlled efficacy benchmark remain pending.

Interface quality was informed by the [Vercel Labs web interface guidelines](https://github.com/vercel-labs/web-interface-guidelines/blob/main/AGENTS.md), inspected directly, with the project's DESIGN.md as the visual specification. No Vercel branding is used.
