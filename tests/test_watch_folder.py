"""Tests for the watch-folder daemon (clean copies + in-place mode)."""

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "service", "scripts"))

import watch_folder as wf


def _make_watch(tmp_path: Path) -> tuple[Path, Path]:
    src = tmp_path / "in"
    out = tmp_path / "out"
    src.mkdir()
    out.mkdir()
    return src, out


def test_signature_tracks_size_and_mtime(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("hello", encoding="utf-8")
    sig1 = wf._signature(f)
    import time

    time.sleep(0.02)
    f.write_text("hello world", encoding="utf-8")
    sig2 = wf._signature(f)
    assert sig1 != sig2


def test_state_roundtrip(tmp_path):
    src, _ = _make_watch(tmp_path)
    state = {str(tmp_path / "x"): (10, 123.0)}
    wf._save_state(src, state)
    assert wf._load_state(src) == state


def test_state_handles_missing_file(tmp_path):
    src, _ = _make_watch(tmp_path)
    assert wf._load_state(src) == {}


def test_once_mode_cleans_copy(tmp_path):
    src, out = _make_watch(tmp_path)
    f = src / "note.txt"
    f.write_text("Hello\u200b world\u200b", encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(Path(wf.__file__).resolve()),
            str(src),
            "--output",
            str(out),
            "--once",
        ],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert proc.returncode in {0, 1}  # 1 = cleaned, 0 = nothing to clean
    cleaned = (out / "note.txt").read_text(encoding="utf-8")
    assert "\u200b" not in cleaned
    # original untouched
    assert "\u200b" in f.read_text(encoding="utf-8")
    # state file prevents re-processing
    assert (src / wf.STATE_NAME).is_file()


def test_once_mode_idempotent(tmp_path):
    src, out = _make_watch(tmp_path)
    f = src / "note.txt"
    f.write_text("Hi\u200b", encoding="utf-8")
    base = [
        sys.executable,
        str(Path(wf.__file__).resolve()),
        str(src),
        "--output",
        str(out),
        "--once",
    ]
    subprocess.run(base, capture_output=True, text=True, timeout=120, check=False)
    proc2 = subprocess.run(base, capture_output=True, text=True, timeout=120, check=False)
    assert proc2.returncode == 0  # nothing new to clean
    assert (out / "note.txt").read_text(encoding="utf-8") == "Hi"
