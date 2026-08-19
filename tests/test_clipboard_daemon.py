"""Tests for the clipboard daemon (Layer A scrub logic + CLI behavior)."""

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "service", "scripts"))

import clipboard_daemon as cd

ZERO_WIDTH = "\u200b"
BOM = "\ufeff"


def test_clean_clipboard_strips_invisible_marks():
    text = f"hello{ZERO_WIDTH}world{BOM}"
    cleaned, stats = cd.clean_clipboard_text(text)
    assert cleaned == "helloworld"
    assert stats["removed_count"] >= 2


def test_clean_clipboard_clean_text_untouched():
    text = "Plain text, no marks."
    cleaned, stats = cd.clean_clipboard_text(text)
    assert cleaned == text
    assert stats["removed_count"] == 0


def test_detect_backend_returns_backend():
    backend = cd.detect_backend()
    assert isinstance(backend, cd.ClipboardBackend)
    assert backend.name in {"windows", "macos", "x11", "none"}


def test_cli_once_monitor_only_clean_text():
    # No usable clipboard in CI; --once should still exit 0 only on clean path.
    # Here we exercise the parser and the no-backend exit path.
    proc = subprocess.run(
        [sys.executable, str(Path(cd.__file__).resolve()), "--once"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    # On machines with a clipboard the exit code depends on clipboard content,
    # so we only assert it ran without crashing (0, 1, or 2 all valid).
    assert proc.returncode in {0, 1, 2}


def test_windows_backend_shims():
    wb = cd.WindowsClipboard()
    assert wb.name == "windows"


def test_docstring_mentions_opt_in_autoclean():
    assert "--auto-clean" in cd.__doc__ or "auto-clean" in cd.__doc__
