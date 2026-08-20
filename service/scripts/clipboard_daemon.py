#!/usr/bin/env python3
"""Clipboard daemon: monitor the system clipboard for AI provenance marks.

Port of the `antiwatermark` clipboard watcher, rewritten stdlib-only:

  * Windows  : ctypes -> user32 (CF_UNICODETEXT), no pywin32 needed.
  * macOS    : subprocess `pbpaste` / `pbcopy`.
  * Linux/X11: subprocess `xclip` (or `xsel`) if installed.

Behavior:
  * Polls the clipboard every `--interval` seconds; only acts when the text
    actually changed since the last poll.
  * Cleans with the local Layer A scrubber (`text_unicode.clean_text`); no
    service or network required.
  * Default is *monitor-only*: it logs (and optionally beeps) when it finds
    marks. Pass `--auto-clean` to write the cleaned text back to the
    clipboard. Auto-cleaning can fight the user's own copy operations, so it
    is opt-in and never touches the clipboard unless marks were found.

Exit codes: 0 = clean or done, 1 = marks found (monitor-only), 2 = no usable
clipboard backend. Use `--once` to run a single poll instead of looping
(handy for cron/tests).
"""

from __future__ import annotations

import argparse
import ctypes
import logging
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from text_unicode import clean_text, inspect_text

log = logging.getLogger("clipboard_daemon")


class ClipboardBackend:
    name = "none"

    def get(self) -> str | None:  # pragma: no cover - platform shims
        return None

    def set(self, text: str) -> bool:  # pragma: no cover - platform shims
        return False


class WindowsClipboard(ClipboardBackend):
    name = "windows"

    CF_UNICODETEXT = 13
    GMEM_MOVEABLE = 0x0002

    def get(self) -> str | None:
        if not ctypes.windll:  # type: ignore[attr-defined]
            return None
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        if not user32.OpenClipboard(0):
            return None
        try:
            handle = user32.GetClipboardData(self.CF_UNICODETEXT)
            if not handle:
                return None
            ptr = kernel32.GlobalLock(handle)
            if not ptr:
                return None
            try:
                length = kernel32.GlobalSize(handle)
                raw = ctypes.string_at(ptr, length)
                return raw.decode("utf-16-le", errors="replace").rstrip("\x00")
            finally:
                kernel32.GlobalUnlock(handle)
        finally:
            user32.CloseClipboard()
        return None

    def set(self, text: str) -> bool:
        if not ctypes.windll:  # type: ignore[attr-defined]
            return False
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        data = (text + "\x00").encode("utf-16-le")
        if not user32.OpenClipboard(0):
            return False
        try:
            user32.EmptyClipboard()
            hmem = kernel32.GlobalAlloc(self.GMEM_MOVEABLE, len(data))
            if not hmem:
                return False
            ptr = kernel32.GlobalLock(hmem)
            ctypes.memmove(ptr, data, len(data))
            kernel32.GlobalUnlock(hmem)
            user32.SetClipboardData(self.CF_UNICODETEXT, hmem)
            return True
        finally:
            user32.CloseClipboard()


def _run_capture(args: list[str]) -> str | None:
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return proc.stdout if proc.returncode == 0 else None


class MacClipboard(ClipboardBackend):
    name = "macos"

    def get(self) -> str | None:
        return _run_capture(["pbpaste"])

    def set(self, text: str) -> bool:
        try:
            proc = subprocess.run(
                ["pbcopy"],  # noqa: S607 - bare name relies on PATH, like xclip below
                input=text,
                capture_output=True,
                timeout=10,
                check=False,
            )
            return proc.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return False


class XClipboard(ClipboardBackend):
    name = "x11"

    def get(self) -> str | None:
        return _run_capture(["xclip", "-selection", "clipboard", "-o"])

    def set(self, text: str) -> bool:
        try:
            proc = subprocess.run(
                ["xclip", "-selection", "clipboard", "-i"],  # noqa: S607
                input=text,
                capture_output=True,
                timeout=10,
                check=False,
            )
            return proc.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return False


class XSelClipboard(ClipboardBackend):
    name = "x11"

    def get(self) -> str | None:
        return _run_capture(["xsel", "--clipboard", "--output"])

    def set(self, text: str) -> bool:
        try:
            proc = subprocess.run(
                ["xsel", "--clipboard", "--input"],  # noqa: S607
                input=text,
                capture_output=True,
                timeout=10,
                check=False,
            )
            return proc.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return False


def detect_backend() -> ClipboardBackend:
    if sys.platform.startswith("win"):
        return WindowsClipboard()
    if sys.platform == "darwin":
        return MacClipboard()
    if _run_capture(["xclip", "-selection", "clipboard", "-o"]) is not None:
        return XClipboard()
    if _run_capture(["xsel", "--clipboard", "--output"]) is not None:
        return XSelClipboard()
    return ClipboardBackend()


def clean_clipboard_text(text: str) -> tuple[str, dict]:
    """Layer A scrub, isolated for tests. Returns (cleaned, stats)."""
    cleaned, stats = clean_text(text)
    residual = inspect_text(cleaned)
    stats["residual_suspicious"] = residual.suspicious_total
    stats["verified_clean"] = residual.suspicious_total == 0
    return cleaned, stats


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--interval", type=float, default=2.0, help="Poll interval seconds")
    p.add_argument("--auto-clean", action="store_true", help="Write cleaned text back")
    p.add_argument("--once", action="store_true", help="Single poll then exit")
    p.add_argument("--beep", action="store_true", help="Beep when marks found")
    p.add_argument("--log-file", help="Append log lines to this file")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    if args.log_file:
        fh = logging.FileHandler(args.log_file, encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
        log.addHandler(fh)

    backend = detect_backend()
    if backend.name == "none":
        log.error("no clipboard backend available (need Windows, macOS, or xclip/xsel)")
        return 2

    log.info("clipboard backend: %s (auto-clean=%s)", backend.name, args.auto_clean)
    last_text: str | None = None
    marked = False

    try:
        while True:
            text = backend.get()
            if text is not None and text != last_text:
                last_text = text
                cleaned, stats = clean_clipboard_text(text)
                removed = int(stats.get("removed_count", stats.get("removed", 0)))
                replaced = int(stats.get("replaced_count", stats.get("replaced", 0)))
                verified = bool(stats.get("verified_clean"))
                if removed or replaced:
                    marked = True
                    log.info(
                        "marks found: %d removed, %d replaced (%d chars); "
                        "post-clean residual=%d verified=%s",
                        removed,
                        replaced,
                        len(text),
                        int(stats.get("residual_suspicious", 0)),
                        verified,
                    )
                    if args.beep:
                        print("\a", end="", flush=True)
                    if args.auto_clean and cleaned != text and backend.set(cleaned):
                        log.info("clipboard rewritten (cleaned text, verified=%s)", verified)

            if args.once:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        log.info("stopped")

    return 1 if marked and not args.auto_clean else 0


if __name__ == "__main__":
    raise SystemExit(main())
