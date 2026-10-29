# DESIGN.md — ImageShield

## Design reference from GitHub
Read the actual Markdown guidelines maintained by Vercel Labs:
https://github.com/vercel-labs/web-interface-guidelines/blob/main/AGENTS.md
Raw:
https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/AGENTS.md

This is an interface-quality reference, not an ImageShield template or an official endorsement. Follow relevant principles and credit the source; do not copy Vercel logos, trademarks, a whole site or unrelated infrastructure. React-specific guidance does not apply to this vanilla frontend.

The custom visual specification below is the design source of truth for this app.

## Product feeling
Quiet, precise, professional. A compact tool you can use immediately. Monochrome surfaces, crisp borders, strong typography, image-led results and one primary action.
No marketing landing page, oversized hero, decorative security padlocks, fake attack maps, gradient blobs or stock dashboard cards.
Prefer a light default with optional dark mode. The actual image remains color-managed and unfiltered.

## Visual tokens (custom, not extracted from Vercel)
```css
:root {
  color-scheme: light;
  --page: #fafafa;
  --surface: #ffffff;
  --surface-muted: #f4f4f5;
  --ink: #111111;
  --ink-secondary: #52525b;
  --border: #e4e4e7;
  --button: #111111;
  --button-ink: #ffffff;
  --focus: #2563eb;
  --success: #15803d;
  --warning: #a16207;
  --error: #b91c1c;
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 14px;
  --font: Inter, ui-sans-serif, system-ui, sans-serif;
  --mono: ui-monospace, SFMono-Regular, Consolas, monospace;
}
```
Use a 4px spacing grid. Main content max-width 1120px. Page gutters 24px desktop / 16px mobile. Body 14px, controls 14px, headings 24–28px, secondary text 12–13px. Main buttons 40px desktop and at least 44px on touch. Subtle single shadow for raised controls only.

Dark mode custom tokens: page #09090b, surface #111113, muted #18181b, ink #fafafa, secondary #a1a1aa, border #2a2a2e. Reverse primary button colors; verify every status contrast.

No external font/network dependency is required for first render. System font fallback must look intentional.

## Header
56px high, bottom border. Left: simple geometric mark plus ImageShield wordmark. Center/left navigation: Protect / Attack Lab / Verify. Right: small real capability state (GPU ready / Setup required), theme button.
Do not show VRAM/model IDs across the main flow; put technical details in an expandable panel.

Tabs have real URL hash state (#protect, #attack-lab, #verify), keyboard navigation and selected-state underline. Back/forward restores tab.

## Protect screen
Heading: “Protect an image”
Subtext: “Make compatible AI edits harder while preserving image quality.”

Initial state:
- A large bordered upload area, approximately 420px high on desktop.
- Label: “Drop an image here” and Choose image button.
- Helper: “PNG or JPEG · Up to 10 MB”.
- Keyboard/file-picker alternative to drag and drop.

After upload:
- Left, about two thirds: image preview with contain sizing, coordinate-aware mask canvas.
- Right, about one third: compact controls panel.
- Simple mode switch: “Edit selected area” / “Replace background”.
- Region rectangle selection; Clear selection; keyboard-accessible numeric x/y/width/height fields under Refine region.
- Strength: one sensible default; advanced controls collapsed.
- Primary button “Protect image”.
- Note near image: “512 × 512 research export”. Explain letterboxing in Details.
- A small plain statement: “Effectiveness depends on the editor and image processing.”

Processing:
- Show actual stage and iteration count where available.
- Keep the image visible. No fabricated timer/percentage.
- Button retains label with a spinner; show Cancel.

Result:
- Before/after switch or keyboard-accessible comparison slider.
- Show actual quality metrics in one compact row, with a Details disclosure.
- Primary “Download protected image”.
- Secondary “Test an AI edit”.
- State reads “Protection generated” and “Effectiveness not tested” until results exist.
- Rejected-quality output has a clear explanation and Adjust settings action; no normal success download CTA.

## Attack Lab screen
Heading: “Test the protection”
Keep this practical, not a wall of configuration.
Controls: selected asset, existing mask, short edit prompt, Run comparison. Show advanced seed/model options collapsed.
Results: four equal cards — Original; Protected; AI edit of original; AI edit of protected.
Maintain identical image scale and cropping. Zoom/open controls. Do not stretch images.
On desktop use a two-by-two grid; mobile one column. A 4-column ultra-wide layout is optional.
Below: “Was the requested edit completed?” review controls, realism and retained-subject scores. Clearly identify human review versus automated metrics.
Show failures and bypasses in the same layout as successes.
Channel select: Local PNG; JPEG simulation. Instagram/Photoshop import is hidden until implemented and never prepopulated with simulated evidence.
Label any static demo fixtures “Sample data — not a measured run”.

## Verify screen (phase 2)
Compact upload plus known export ID/receipt input.
Display separate rows:
- Signature: trusted/untrusted/invalid/unavailable.
- Exact file: match/changed/unregistered.
- Watermark: recovered/not recovered/inconclusive.
- Reference assessment: suspicious regions/inconclusive/not available.
Never compress all evidence into “real/fake”.
Show private references only to their owner. Provide an overlay toggle with accessible text explanation.

## Empty, error and unavailable states
- No CUDA: “GPU setup required” with copyable setup instructions; allow upload/UI testing.
- Missing weights: “Model files are not installed.”
- OOM: explain job failure and supported next actions.
- Invalid image: inline error near uploader, retain navigation and retry.
- No observed disruption: show “Edit succeeded in this test”; do not recolor as success.
- Worker stopped: queued/interrupted state with recovery action.
- Loading: stable dimensions, no layout jump.

## Interface-quality requirements adapted from reference
Use semantic controls, visible focus, keyboard alternatives, descriptive labels, inline errors, textual status indicators, reduced motion and responsive layouts. Give async changes an aria-live announcement. Reserve image dimensions. Do not use color as the only result cue. Respect browser zoom. Measure responsiveness; job submission should acknowledge promptly while GPU work runs asynchronously.

## Acceptance screenshots to produce
At 1440px and 390px:
1. Empty Protect.
2. Image and selected region.
3. Running job.
4. Protected export.
5. Four-image comparison.
6. Missing GPU/model error.
Also test keyboard tab order and reduced-motion mode. No screenshot should imply unmeasured protection success.

