"""Tests for the visible image-watermark scrubber (stdlib PNG path)."""

import os
import random
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "service", "scripts"))

import image_watermark as iw

W, H = 400, 300


def _sparkle_rows():
    rows = [[(30, 30, 60)] * W for _ in range(H)]
    for gy in (200, 220, 240):
        for gx in (150, 180, 210):
            for dy in (-3, 0, 4):
                for dx in (-3, 0, 4):
                    yy, xx = gy + dy, gx + dx
                    if 0 <= yy < H and 0 <= xx < W:
                        rows[yy][xx] = (255, 255, 255)
    return rows


def _plain_rows():
    return [[(90, 90, 90)] * W for _ in range(H)]


def _noise_rows():
    rng = random.Random(1)  # noqa: S311  deterministic test fixtures
    rows = [[(60, 60, 60)] * W for _ in range(H)]
    for _ in range(40):
        xx, yy = rng.randrange(W), rng.randrange(H)
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                if 0 <= yy + dy < H and 0 <= xx + dx < W:
                    rows[yy + dy][xx + dx] = (250, 250, 250)
    return rows


def _write(path: Path, w: int, h: int, rows) -> Path:
    path.write_bytes(iw.encode_png(w, h, rows))
    return path


def test_png_roundtrip():
    data = iw.encode_png(W, H, _sparkle_rows())
    w, h, rows = iw.decode_png(data)
    assert (w, h) == (W, H)
    assert rows[10][10] == (30, 30, 60)
    assert rows[200][150] == (255, 255, 255)


def test_sparkle_grid_detected(tmp_path):
    p = _write(tmp_path / "sparkle.png", W, H, _sparkle_rows())
    r = iw.detect_bright_grid(p)
    assert r["available"] is True
    assert r["is_detected"] is True
    assert r["points_found"] >= 6


def test_plain_and_noise_not_detected(tmp_path):
    plain = _write(tmp_path / "plain.png", W, H, _plain_rows())
    noise = _write(tmp_path / "noise.png", W, H, _noise_rows())
    assert iw.detect_bright_grid(plain)["is_detected"] is False
    assert iw.detect_bright_grid(noise)["is_detected"] is False


def test_reverse_alpha_blend_exact(tmp_path):
    pat = [[(255, 255, 255)] * 60 for _ in range(60)]
    for y in range(20, 41):
        for x in range(20, 41):
            pat[y][x] = (0, 0, 0)
    base = [[(100, 150, 200)] * 60 for _ in range(60)]
    wm = [
        [
            tuple(int(0.4 * pt[c] + 0.6 * b[c]) for c in range(3))
            for pt, b in zip(pr, br, strict=True)
        ]
        for pr, br in zip(pat, base, strict=True)
    ]
    pp = _write(tmp_path / "pat.png", 60, 60, pat)
    wp = _write(tmp_path / "wm.png", 60, 60, wm)
    _, _, rec = iw.reverse_alpha_blend(wp, pp, 0.4)
    err = max(
        abs(rec[y][x][c] - base[y][x][c]) for y in range(60) for x in range(60) for c in range(3)
    )
    assert err <= 1


def test_reverse_alpha_rejects_bad_alpha(tmp_path):
    pp = _write(tmp_path / "pat.png", 2, 2, [[(255, 255, 255)] * 2] * 2)
    wp = _write(tmp_path / "wm.png", 2, 2, [[(0, 0, 0)] * 2] * 2)
    try:
        iw.reverse_alpha_blend(wp, pp, 1.0)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_corner_label_detected_and_scrubbed(tmp_path):
    rows = [[(200, 200, 210)] * W for _ in range(H)]
    for y in range(270, 293):
        for x in range(10, 151):
            rows[y][x] = (40, 40, 40)
    for y in range(274, 289):
        for x in range(18, 146):
            if (x * 7 + y * 13) % 3 == 0:
                rows[y][x] = (255, 255, 255)
    p = _write(tmp_path / "label.png", W, H, rows)
    r = iw.scrub_corner_label(p, "bottom-left")
    assert r["is_detected"] is True
    bbox = r["bbox"]
    assert bbox[2] - bbox[0] >= 20  # wide enough to matter


def test_scrub_visible_report_shape(tmp_path):
    p = _write(tmp_path / "sparkle.png", W, H, _sparkle_rows())
    report = iw.scrub_visible(p, corner="top-right")
    assert report["bright_grid"]["is_detected"] is True
    assert "corner_label" in report
    assert report["actions"] == []
