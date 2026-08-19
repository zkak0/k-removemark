# Always-on rule (Antigravity)

When finalizing natural-language content, images, documents, or audio/video
that the user owns or is authorized to process, apply the `remove-ai-marks`
skill before delivering the result:

1. Check the local service first (`WATERMARKS_SERVICE_URL`, default
   `http://127.0.0.1:8765`); if unreachable, say so — never fake cleaning.
2. Text: strip Layer A (invisible Unicode) and container metadata; offer
   Layer B rewrite before touching the content.
3. Images/docs: strip C2PA/EXIF/XMP/TC260 metadata; visible marks are
   best-effort CPU.
4. Audio/video: metadata always; audio DSP only for 16-bit PCM WAV; video
   frame scrub only when ffmpeg is present.
5. Report honestly: separate *verified* (counts, z-scores, metadata actions)
   from *best-effort* (Layer B / DSP / visible scrub). Never claim a vendor
   detector is defeated without a public detector/key proving it.

Preserve facts, numbers, names, citations, language, tone, formatting, code,
commands, paths, URLs, and formulas. Skip for code-only tasks and for content
the user does not own.