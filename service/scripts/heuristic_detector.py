#!/usr/bin/env python3
"""Unkeyed heuristic AI-text signal: stylometry + burstiness + n-gram repetition.

There is no secret key needed here — and no proof, either. These signals are
*frequency* artifacts of LLM sampling (low sentence-length variance, high
lexical diversity, formulaic transition cadence, self-repetition), not a
cryptographic mark. The detector reports a probabilistic "suspicion" label and
explicitly never claims verification: `is_watermarked` is always False; callers
must read `suspicion` + `is_suspicious` instead.

Runs on stdlib + the existing score_stylometry.py (also stdlib). In the
fail-soft text-detector contract: unconfigured is impossible (always
available), short text returns a defensively low signal, never an error.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

import score_stylometry as st  # noqa: E402

DEFAULT_THRESHOLD = float(os.environ.get("WATERMARKS_HEURISTIC_THRESHOLD", "0.65"))
MIN_SAMPLE_WORDS = st.MIN_SAMPLE_WORDS


def _ngram_repetition_density(words: list[str], max_n: int = 4) -> float:
    """Fraction of n-gram types (n=2..4) that repeat, weighted by n.

    LLM sampling repeats generic multi-word chunks ("in today's fast-paced
    world", "plays a crucial role"); human prose repeats far fewer distinct
    n-grams. Returns 0.0 for degenerate input.
    """
    total_types = 0
    repeated = 0
    for n in range(2, max_n + 1):
        grams: list[tuple[str, ...]] = []
        for i in range(len(words) - n + 1):
            grams.append(tuple(words[i : i + n]))
        counts = Counter(grams)
        if not counts:
            continue
        total_types += len(counts)
        repeated += sum(1 for c in counts.values() if c > 1)
    if total_types == 0:
        return 0.0
    return repeated / total_types


class HeuristicDetector:
    """Best-effort unkeyed AI-likeness signal (stylometry + burstiness + n-grams)."""

    name = "heuristic-stylometry"
    vendor = "unknown"

    def __init__(self, threshold: float | None = None) -> None:
        self._threshold = threshold if threshold is not None else DEFAULT_THRESHOLD

    def available(self) -> bool:
        return True

    def detect(self, text: str) -> dict[str, Any]:
        sty = st.score_text_stylometry(text)
        words = st.extract_words(text)
        word_count = len(words)
        sentences = st.extract_sentences(text)
        _, _, cv = st.compute_burstiness(sentences)

        # Normalize burstiness: low CV (uniform rhythm) pushes suspicion up.
        # A CV below ~0.4 is unusually uniform for human prose.
        burstiness_signal = max(0.0, 1.0 - min(cv, 1.0) / 0.4) if cv is not None else 0.0

        ngram = _ngram_repetition_density(words)

        stylo_score = sty.score
        marker_count = len(sty.matched_markers)

        # Composite, deliberately conservative for short text. stylometry score
        # already folds in markers + burstiness + MATTR (see score_stylometry),
        # so it carries most weight; n-gram repetition is weak on short samples.
        if word_count >= MIN_SAMPLE_WORDS:
            suspicion = (
                0.65 * stylo_score
                + 0.20 * min(marker_count / 3.0, 1.0)
                + 0.15 * min(ngram * 2.0, 1.0)
            )
        else:
            # Below the statistical floor only hard phrase markers count.
            suspicion = min(0.25 * min(marker_count / 2.0, 1.0), 0.4)
            if word_count == 0:
                suspicion = 0.0

        suspicion = max(0.0, min(suspicion, 1.0))
        if suspicion >= 0.8:
            label = "HIGH"
        elif suspicion >= self._threshold:
            label = "MEDIUM"
        elif suspicion >= 0.3:
            label = "LOW"
        else:
            label = "CLEAN"

        return {
            "detector": self.name,
            "vendor": self.vendor,
            "scheme": "heuristic-stylometry",
            "available": True,
            "keyed": False,
            "is_watermarked": False,
            "is_suspicious": bool(suspicion >= self._threshold),
            "suspicion": round(suspicion, 4),
            "suspicion_level": label,
            "threshold": self._threshold,
            "components": {
                "word_count": word_count,
                "sentence_count": len(sentences),
                "stylometry_score": round(stylo_score, 4),
                "burstiness_cv": round(cv, 4) if cv is not None else None,
                "burstiness_signal": round(burstiness_signal, 4),
                "ngram_repetition_density": round(ngram, 4),
                "ai_marker_count": marker_count,
            },
            "findings": sty.findings,
            "note": (
                "best-effort statistical signal, NOT verified; may be clean "
                "human prose. Do not use as evidence of provenance."
            ),
        }


def _arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Unkeyed heuristic AI-likeness scoring")
    p.add_argument("file", help="text file to score")
    p.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    p.add_argument("--json", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _arg_parser().parse_args(argv)
    try:
        with open(args.file, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    report = HeuristicDetector(threshold=args.threshold).detect(text)
    if args.json:
        print(json.dumps(report, ensure_ascii=False))
    else:
        print(
            f"{report['detector']} | suspicion={report['suspicion']} "
            f"({report['suspicion_level']}, threshold {report['threshold']})"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
