#!/usr/bin/env python3
"""Clean video files: metadata strip + optional frame-wise visible-mark scrub.

Metadata (MP4/MOV/M4V C2PA / generator / XMP boxes) is stripped by
``av_meta.clean_av`` — stdlib, byte-level, no codec needed.

Frame-wise visible-mark scrubbing (Sora/Veo/Kling/Seedance corner badges,
sparkle grids) genuinely needs a video codec: there is no honest way to
decode/re-encode H.264/H.265 in pure Python. The scrub path is therefore
behind ``--scrub-visible`` and requires ``ffmpeg`` in PATH. Without it the
tool degrades to metadata-only and says so — it never pretends it removed a
visible watermark it cannot reach.

Pure stdlib for the metadata path; per-frame pixels are handled by
``image_watermark`` (Pillow-free PNG path). Zero model, zero GPU.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import image_watermark as iw
from av_meta import clean_av, detect_av_format
from common import cleaned_path, eprint


def ffmpeg_path() -> str | None:
    return shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")


def scrub_frames_with_ffmpeg(
    src: Path, dest: Path, *, corner: str | None = None, pattern: Path | None = None
) -> dict[str, Any]:
    """Extract frames, scrub each with image_watermark, reassemble with ffmpeg."""
    ffmpeg = ffmpeg_path()
    if ffmpeg is None:
        return {"available": False, "error": "ffmpeg is not in PATH"}
    with tempfile.TemporaryDirectory(prefix="wm-video-") as tmp:
        tmpd = Path(tmp)
        frames = tmpd / "f_%06d.png"
        try:
            subprocess.run(
                [ffmpeg, "-y", "-i", str(src), str(frames)],
                capture_output=True,
                check=True,
                timeout=3600,
            )
        except subprocess.CalledProcessError as e:
            return {"available": False, "error": f"ffmpeg extraction failed: {e.stderr[-400:]}"}
        count = 0
        save_failures = 0
        for f in sorted(tmpd.glob("f_*.png")):
            report = iw.scrub_visible(f, corner=corner, pattern_path=pattern)
            rows = report.pop("rows", None)
            if rows is not None:
                try:
                    iw.save_rgb(report["output_w"], report["output_h"], rows, f, ".png")
                    count += 1
                except Exception:
                    save_failures += 1
        if count == 0:
            return {"available": False, "error": "no decodable frames found"}
        try:
            subprocess.run(
                [
                    ffmpeg,
                    "-y",
                    "-r",
                    "30",
                    "-i",
                    str(frames),
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    str(dest),
                ],
                capture_output=True,
                check=True,
                timeout=3600,
            )
        except subprocess.CalledProcessError as e:
            return {"available": False, "error": f"ffmpeg reassembly failed: {e.stderr[-400:]}"}
    return {
        "available": True,
        "engine": "ffmpeg+image_watermark",
        "frames_scrubbed": count,
        "frame_save_failures": save_failures,
        "corner": corner,
        "pattern": str(pattern) if pattern else None,
        "note": "best-effort frame-wise scrub; audio track copied via default mux.",
    }


def clean_video(
    src: Path,
    dest: Path,
    *,
    strip_all_metadata: bool = True,
    scrub_visible: bool = False,
    corner: str | None = None,
) -> dict[str, Any]:
    """Clean a video file: metadata always; frame scrub only when requested."""
    report: dict[str, Any] = {"input": str(src), "output": str(dest), "actions": []}
    try:
        fmt = detect_av_format(src.read_bytes())
    except Exception:
        fmt = ""
    report["format"] = fmt
    if fmt not in ("mp4", "mov", "m4v"):
        report["scrub"] = {
            "available": False,
            "error": f"unsupported video container {fmt or 'unknown'}; only MP4/MOV are handled.",
        }
        return report
    meta = clean_av(src, dest, strip_all_metadata=strip_all_metadata)
    report["actions"] += meta.get("actions", [])
    report["metadata"] = meta
    if scrub_visible:
        res = scrub_frames_with_ffmpeg(dest, dest, corner=corner)
        report["scrub"] = res
        if res.get("available"):
            report["actions"].append(f"frame-wise scrub ({res.get('frames_scrubbed')} frames)")
    return report


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("path", type=Path, help="Input video (MP4/MOV/M4V)")
    p.add_argument("-o", "--output", type=Path, help="Output path (default: *.cleaned.*)")
    p.add_argument(
        "--scrub-visible", action="store_true", help="Frame-wise visible-mark scrub (needs ffmpeg)"
    )
    p.add_argument("--corner", choices=["bottom-left", "bottom-right", "top-left", "top-right"])
    p.add_argument("--pattern", type=Path, help="Known watermark pattern tile for frame scrub")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    if not args.path.is_file():
        eprint(f"not a file: {args.path}")
        return 2
    dest = args.output or cleaned_path(args.path)
    try:
        report = clean_video(args.path, dest, scrub_visible=args.scrub_visible, corner=args.corner)
    except Exception as e:
        eprint(f"error: {e}")
        return 1
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        eprint(f"wrote {dest}")
        for a in report["actions"]:
            eprint(f"  - {a}")
        scrub = report.get("scrub")
        if scrub is not None:
            if scrub.get("available"):
                eprint(
                    f"frame scrub: {scrub.get('frames_scrubbed')} frames via {scrub.get('engine')}"
                )
            else:
                eprint(f"frame scrub: {scrub.get('error', 'unavailable')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
