"""Tests for our unkeyed heuristic AI-likeness signal."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "service", "scripts"))

import heuristic_detector as hd

AI_TEXT = (
    "In today's fast-paced world, technology plays a pivotal role in shaping the "
    "future of work and daily life. It is essential to note that embracing digital "
    "transformation is crucial for organizations seeking to remain competitive in "
    "the ever-evolving landscape of the modern economy. Moreover, it is important "
    "to remember that innovation serves as a cornerstone of sustainable growth and "
    "long-term success. Not only do these developments enhance operational "
    "efficiency, but they also act as a catalyst for creating new opportunities "
    "across diverse sectors. It is worth noting that collaboration remains a key "
    "driver of meaningful progress, underscoring the importance of building "
    "resilient teams and robust frameworks to navigate the complexities of this "
    "new era."
)

PLAIN_TEXT = (
    "The old lighthouse keeper had lived on the island for nearly forty years, "
    "ever since the storm that sank the mail steamer off the southern rocks. Each "
    "evening he climbed the iron stairs to the lamp room, checked the clockwork "
    "that turned the lens, and trimmed the wick with steady hands. In winter the "
    "fog rolled in for days at a time, and he would sit by the stove listening to "
    "the horn bellow through the dark. He kept a small garden behind the cottage, "
    "mostly potatoes and cabbages, and a ledger full of ships he had watched pass "
    "on their way to the harbor."
)


def test_report_shape():
    report = hd.HeuristicDetector().detect(AI_TEXT)
    assert report["detector"] == "heuristic-stylometry"
    assert report["available"] is True
    assert report["keyed"] is False
    assert report["is_watermarked"] is False  # never claims proof
    assert isinstance(report["is_suspicious"], bool)
    assert 0.0 <= report["suspicion"] <= 1.0
    assert report["suspicion_level"] in {"CLEAN", "LOW", "MEDIUM", "HIGH"}
    assert "NOT verified" in report["note"]


def test_ai_cadence_text_is_suspicious():
    report = hd.HeuristicDetector().detect(AI_TEXT)
    assert report["is_suspicious"] is True
    assert report["suspicion"] >= 0.65
    assert report["components"]["ai_marker_count"] >= 4


def test_plain_prose_is_clean():
    report = hd.HeuristicDetector().detect(PLAIN_TEXT)
    assert report["is_suspicious"] is False
    assert report["suspicion"] < 0.5


def test_short_and_empty_text_are_defensive():
    assert hd.HeuristicDetector().detect("hi")["suspicion_level"] == "CLEAN"
    assert hd.HeuristicDetector().detect("")["suspicion_level"] == "CLEAN"


def test_ngram_repetition_density_bounds():
    assert hd._ngram_repetition_density([]) == 0.0
    assert hd._ngram_repetition_density(["a", "b", "c"]) == 0.0
    d = hd._ngram_repetition_density(["the", "quick", "the", "quick"])
    assert 0.0 < d <= 1.0


def test_cli_detect_json(tmp_path):
    f = tmp_path / "ai.txt"
    f.write_text(AI_TEXT, encoding="utf-8")
    import subprocess

    r = subprocess.run(
        [
            sys.executable,
            os.path.join(os.path.dirname(hd.__file__), "heuristic_detector.py"),
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
    assert report["is_suspicious"] is True
