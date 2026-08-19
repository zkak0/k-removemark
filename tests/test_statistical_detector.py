"""Tests for our stdlib keyed statistical text-watermark detector."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "service", "scripts"))

import statistical_detector as sd


@pytest.fixture(scope="module")
def bank():
    return sd.WordBank()


def test_tokens_lowercases_and_splits():
    assert sd.tokens("Hello, WORLD — 42!") == ["hello", "world", "42"]


def test_prf_is_deterministic_and_in_unit_interval():
    a = sd._prf01(1, ["the"], "quick")
    b = sd._prf01(1, ["the"], "quick")
    c = sd._prf01(2, ["the"], "quick")
    assert a == b
    assert a != c
    assert 0.0 <= a < 1.0


def test_kgw_detector_report_shape():
    report = sd.KGWDetector().detect("the quick brown fox jumps over the lazy dog")
    assert report["detector"] == "statistical-kgw"
    assert report["available"] is True
    assert report["tokens_scored"] >= 1
    assert 0.0 <= report["green_fraction"] <= 1.0
    assert isinstance(report["is_watermarked"], bool)
    assert "not a vendor detector" in report["note"]


def test_kgw_detects_own_watermark_and_not_plain(bank):
    wm = sd.KGWEmbedder().watermark(200, bank)
    plain = bank.sample(__import__("random").Random(99), 200)
    w = sd.KGWDetector().detect(" ".join(wm))
    p = sd.KGWDetector().detect(" ".join(plain))
    assert w["is_watermarked"] is True and w["z_score"] > 8.0
    assert p["is_watermarked"] is False and p["z_score"] < 3.0


def test_kgw_key_mismatch_does_not_detect(bank):
    wm = sd.KGWEmbedder(key=1).watermark(200, bank)
    report = sd.KGWDetector(key=2).detect(" ".join(wm))
    assert report["is_watermarked"] is False


def test_synthid_mean_detects_own_watermark_and_not_plain(bank):
    wm = sd.SynthIDTextMeanEmbedder().watermark(200, bank)
    plain = bank.sample(__import__("random").Random(99), 200)
    w = sd.SynthIDTextMeanDetector().detect(" ".join(wm))
    p = sd.SynthIDTextMeanDetector().detect(" ".join(plain))
    assert w["is_watermarked"] is True and w["z_score"] > 8.0
    assert p["is_watermarked"] is False and p["z_score"] < 3.0


def test_short_text_is_honest():
    report = sd.KGWDetector().detect("hi")
    assert report["tokens_scored"] == 0
    assert report["is_watermarked"] is False


def test_cli_detect_json(tmp_path, bank):
    wm = " ".join(sd.KGWEmbedder().watermark(120, bank))
    f = tmp_path / "wm.txt"
    f.write_text(wm, encoding="utf-8")
    import subprocess

    r = subprocess.run(
        [
            sys.executable,
            os.path.join(os.path.dirname(sd.__file__), "statistical_detector.py"),
            "detect",
            str(f),
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    import json as _json

    report = _json.loads(r.stdout)
    assert report["is_watermarked"] is True
