# AGENTS.md

> Read by AI coding agents (Antigravity, Codex, GitHub Copilot, Cursor, OpenCode, Claude Code via symlink, etc.).

This repository is a **unified, multi-vendor AI watermark remover**. It strips
AI provenance marks from text, code, images, video, audio and file metadata,
across Claude, Gemini/SynthID, OpenAI, xAI, Meta, open-LLM (KGW) and China AIGC
generators.

## Non-negotiable design rules

1. **Zero-model-default (ZMD).** The default install is 100 % CPU: no GPU, no
   model downloads, no `torch`/`diffusers`. All detection/removal must be
   implemented with stdlib + lightweight math (numpy/Pillow/PyWavelets allowed
   in the service image). Heavy model-based backends (CtrlRegen, reverse-SynthID
   scorer, MarkDiffusion, SynthID-Audio) are **strictly optional opt-ins** behind
   explicit flags and are never part of the default path.
2. **The code knows what to look for.** Detection is algorithmic: token hashing,
   z-scores, DWT/DCT, phase/notch DSP, reverse alpha blending. We do not ship a
   "brain" model.
3. **Honest reporting.** Separate *verified* (counts, z-scores, metadata
   actions) from *best-effort* (Layer B rewrite). Never claim a vendor detector
   is defeated unless a public detector/key proves it.
4. **No heavy AI installed on normal computers.** If a feature needs a GPU or a
   multi-GB download, it is documented as optional and clearly marked.

## Repository layout

```
AGENTS.md                 This file (auto-loaded by many agents)
docs/PLAN.md              Roadmap, decisions, status — READ THIS FIRST
docs/ARCHITECTURE.md      Architecture overview
skills/remove-ai-marks/   Agent skill (SKILL.md, open Agent Skills standard)
service/scripts/          HTTP service + all cleaners (Python stdlib first)
  ├── statistical_detector.py  OUR keyed detector (KGW + SynthID-text scoring)
  ├── heuristic_detector.py    OUR unkeyed signal (stylometry/burstiness/clichés)
  ├── verify_harness.py        Synthesizes marks + measures TP/FP in CI
  ├── clean_image.py           metadata + visible (reverse alpha, corner scrub) CPU
  ├── image_watermark.py       visible-mark detector/scrubber (stdlib PNG codec)
  ├── clean_video.py           metadata + ffmpeg frame-wise visible scrub
  ├── clean_audio.py           metadata + stdlib DSP (phase / spectral notch)
  ├── server.py                local HTTP API (the skill talks to this)
  └── ... (upstream scripts)
integrations/             Per-platform installers (opencode, cursor, claude-code, antigravity, vscode, gemini-cli)
tests/                    pytest suite
```

## How to work here

```bash
# One-time setup
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt   # or: pip install pytest ruff
# Run tests
.venv\Scripts\python.exe -m pytest                    # 520+ tests
# Lint (matches CI)
.venv\Scripts\python.exe -m ruff check service/scripts tests
# Smoke
make smoke
# Run the local HTTP service
make serve                  # http://127.0.0.1:8765
```

Conventions:

- **Python 3.10+**, stdlib-first for core scripts. Optional deps only in the
  Docker image or opt-in harnesses.
- Add a test for every new detector/cleaner. New code must keep the CI
  benchmark metrics from regressing (`verify_harness.py`).
- No new comments unless they explain *why*; keep the codebase style of the
  upstream (see `service/scripts/common.py`).
- Docs are bilingual: English primary, Spanish summaries where useful.

## Automatic mode (opt-in)

- Pre-commit hooks: `check_staged.py` (fail) and `clean_staged.py` (auto-fix)
  via `.pre-commit-hooks.yaml`.
- Clipboard daemon: `service/scripts/clipboard_daemon.py` (monitor-only by
  default; `--auto-clean` opt-in). Watch folder:
  `service/scripts/watch_folder.py` (copies cleaned files to `--output`, or
  `--in-place` on a dedicated drop folder).
- Always-on agent rules: `integrations/cursor/remove-ai-marks.mdc` (Cursor),
  `integrations/antigravity/GEMINI.md` (Antigravity). By default agents apply
  Layer A (invisible-Unicode strip) to their own user-facing output and
  report honestly.

## Current status

See `docs/PLAN.md` for the phase-by-phase roadmap and what is done / pending.
Phases: 1 Base (done) · 2 Own detector (done) · 3 Media CPU merge (done) ·
4 Multi-platform (done) · 5 Auto mode (in progress) · 6 CI quality · 7 Docs + release.