"""Tests for the video cleaner (metadata always; honest frame-scrub gating)."""

import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "service", "scripts"))

import clean_video as cv


def _isobmff_box(typ: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload) + 8) + typ + payload


def _minimal_mp4_with_udta_tag(tag_text: bytes) -> bytes:
    mvhd = _isobmff_box(b"mvhd", b"\x00" * 20)
    udta = _isobmff_box(
        b"udta", b"\xa9too" + struct.pack(">I", len(tag_text) + 4) + b"\x00\x00\x00\x00" + tag_text
    )
    moov = _isobmff_box(b"moov", mvhd + udta)
    ftyp = _isobmff_box(b"ftyp", b"isom" + struct.pack(">I", 0) + b"isomiso2mp41")
    mdat = _isobmff_box(b"mdat", b"\x00" * 16)
    return ftyp + moov + mdat


def test_metadata_only_cleans_mp4(tmp_path):
    src = tmp_path / "clip.mp4"
    src.write_bytes(_minimal_mp4_with_udta_tag(b"Lavf58.76.100"))
    dest = tmp_path / "clip_cleaned.mp4"
    report = cv.clean_video(src, dest)
    assert report["format"] == "mp4"
    assert report["actions"], "metadata strip should report actions"
    assert dest.exists()
    assert dest.read_bytes() != src.read_bytes()


def test_scrub_visible_without_ffmpeg_is_honest(tmp_path, monkeypatch):
    src = tmp_path / "clip.mp4"
    src.write_bytes(_minimal_mp4_with_udta_tag(b"Lavf58.76.100"))
    dest = tmp_path / "clip_cleaned.mp4"
    monkeypatch.setattr(cv, "ffmpeg_path", lambda: None)
    report = cv.clean_video(src, dest, scrub_visible=True)
    assert report["scrub"]["available"] is False
    assert "ffmpeg" in report["scrub"]["error"].lower()
    assert dest.exists()  # metadata strip still happened


def test_unsupported_container_refuses(tmp_path):
    src = tmp_path / "clip.mkv"
    src.write_bytes(b"EBML" + b"\x00" * 32)
    dest = tmp_path / "clip_cleaned.mkv"
    report = cv.clean_video(src, dest, scrub_visible=True)
    assert report["scrub"]["available"] is False
    assert "MP4/MOV" in report["scrub"]["error"]


def test_cli_json(tmp_path):
    import subprocess

    src = tmp_path / "clip.mp4"
    src.write_bytes(_minimal_mp4_with_udta_tag(b"Lavf58.76.100"))
    r = subprocess.run(
        [
            sys.executable,
            os.path.join(os.path.dirname(cv.__file__), "clean_video.py"),
            str(src),
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    import json as _json

    report = _json.loads(r.stdout)
    assert report["format"] == "mp4"
