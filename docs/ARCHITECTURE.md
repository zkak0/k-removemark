# Architecture

> How the pieces fit together. English primary; ES summaries where useful.

```
user / agent app (Claude Code, Antigravity, Cursor, OpenCode, VS Code…)
        │  invokes skill (SKILL.md, open standard)
        ▼
skills/remove-ai-marks/        thin client, NO code — calls the service over HTTP
        │  curl http://127.0.0.1:8765
        ▼
service/scripts/server.py      stdlib HTTP API  (/health /capabilities /inspect /detect /clean)
        │  routes by filename extension + magic bytes
        ├── text      → inspect_text.py / clean_text.py / rewrite_text.py
        │                + statistical_detector.py  (keyed: KGW + SynthID-Text, CPU)
        │                + heuristic_detector.py    (unkeyed signal, CPU)
        │                + score_stylometry.py      (perplexity-free stylometry)
        ├── images    → inspect_image.py / clean_image.py
        │                + image_meta.py        (C2PA/EXIF/XMP/PNG-chunks strip)
        │                + DWT-DCT decoder      (numpy/PyWavelets, CPU)   [F3]
        │                + reverse-alpha visible (sparkle/"AI生成")        [F3]
        │                + [opt-in GPU] reverse-SynthID scorer / CtrlRegen / MarkDiffusion
        ├── video     → clean_video.py frame-wise visible marks             [F3]
        ├── audio     → clean_audio.py DSP-only (phase/notch)               [F3]
        └── containers→ clean_file.py / container_meta.py (DOCX, PPTX, XLSX,
                         EPUB, ODT, PDF[qpdf/exiftool], SVG, HTML, MD, MP4, MP3, WAV)
```

## Layers

- **Layer A** — deterministic Unicode hygiene: ZWSP, bidi, tag chars, exotic
  spaces, homoglyph folding. Verifiable (counts). `text_unicode.py`.
- **Layer B** — statistical (token-sampling) text watermarks: rewrite via
  paraphrase / back-translate / structural prompts. Best-effort; costs style.
  `rewrite_text.py` + the agent itself as the rewrite model (non-origin).
- **Files** — C2PA / EXIF / XMP / IPTC / TC260 / container props. Deterministic.
  `image_meta.py`, `container_meta.py`, `av_meta.py`.
- **Media (CPU)** — visible overlays (reverse alpha blending + inpainting),
  DWT-DCT frequency marks. [Fase 3]
- **Media (opt-in GPU)** — SynthID-class pixel removal via regeneration
  (CtrlRegen / DiffusionPurification); reverse-SynthID scoring. Never default.

## Zero-model-default rule

The default install is 100 % CPU and downloads nothing. Anything that imports
`torch` / `diffusers` or fetches a multi-GB artifact lives behind an explicit
opt-in flag (`--remove-pixel ctrlregen`, `setup_synthid.sh`, `setup_markllm.sh`,
etc.) and is documented as requiring GPU + large download. The HTTP service
reports what is available via `/capabilities`, and the skill only recommends an
opt-in backend when the service says it is present.

## Verification & honesty

- `verify_harness.py` (Fase 2) synthesizes a real KGW-style mark over
  whitespace tokens — no LLM — and measures TP/FP + rewrite divergence in CI.
- Reports separate **verified** (counts, z-scores, metadata actions) from
  **best-effort** (Layer B). No claim that a vendor detector is defeated
  without a public detector/key proving it.
- Vendor seams: `claude-text` and `gemini-synthid-text` detector slots exist
  and activate when official public detection APIs ship.