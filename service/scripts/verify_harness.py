#!/usr/bin/env python3
"""CI quality harness for OUR keyed statistical detectors (no model, no GPU).

Synthesizes marks with the embedded token-sampling watermarks (KGW green/red-list,
SynthID-Text Mean tournament) over a word bank — no LLM is loaded — then measures
detection quality:

  TPR   true-positive rate on self-consistent marks
  TNR   true-negative rate on plain text (and on key-mismatched marks)
  FPR   false-positive rate on clean controls
  adv   TPR after adversarial token noise (insertions / deletions), informational

The harness gates CI: exit 1 when the gated metrics regress (FPR too high, or
TPR too low). Detectors report honestly: only the exact keyed scheme that
produced the mark is expected to fire; everything else is a relative signal.

Zero-model rule: no torch, no models, no downloads. Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import statistical_detector as sd  # noqa: E402

DEFAULT_SAMPLES = 60
DEFAULT_TOKENS = 200
GATE_MAX_FPR = 0.01
GATE_MIN_TPR = 0.95
GATE_MIN_TNR = 0.95


@dataclass
class SchemeResult:
    scheme: str
    tp: int = 0
    tn: int = 0
    fp: int = 0
    fn: int = 0
    tpr: float = 0.0
    tnr: float = 0.0
    fpr: float = 0.0
    adv_tpr: float | None = None
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "scheme": self.scheme,
            "tp": self.tp,
            "tn": self.tn,
            "fp": self.fp,
            "fn": self.fn,
            "tpr": round(self.tpr, 4),
            "tnr": round(self.tnr, 4),
            "fpr": round(self.fpr, 4),
            "adv_tpr": round(self.adv_tpr, 4) if self.adv_tpr is not None else None,
            "note": self.note,
        }


def _add_noise(words: list[str], bank: sd.WordBank, rate: float, rng: random.Random) -> list[str]:
    """Token-level noise: delete or insert tokens at the given rate."""
    out: list[str] = []
    for w in words:
        if rng.random() < rate:
            continue
        out.append(w)
        if rng.random() < rate:
            out.append(rng.choice(bank.words))
    return out


def _run_scheme(
    embedder: Any,
    detector: Any,
    bank: sd.WordBank,
    samples: int,
    tokens: int,
    seed: int,
    noise_rate: float,
) -> SchemeResult:
    res = SchemeResult(scheme=detector.name)
    adv_positives = 0
    rng = random.Random(seed)  # noqa: S311  deterministic synthetic-data noise

    for i in range(samples):
        seed_i = seed + i
        wm = " ".join(embedder.watermark(tokens, bank, seed=seed_i))
        plain = " ".join(bank.sample(random.Random(seed_i * 7), tokens))  # noqa: S311
        wm_noise = " ".join(
            _add_noise(embedder.watermark(tokens, bank, seed=seed_i), bank, noise_rate, rng)
        )

        if detector.detect(wm)["is_watermarked"]:
            res.tp += 1
        else:
            res.fn += 1

        if detector.detect(plain)["is_watermarked"]:
            res.fp += 1
        else:
            res.tn += 1

        if detector.detect(wm_noise)["is_watermarked"]:
            adv_positives += 1

    total = res.tp + res.fn
    res.tpr = res.tp / total if total else 0.0
    res.tnr = res.tn / (res.tn + res.fp) if (res.tn + res.fp) else 0.0
    res.fpr = res.fp / (res.fp + res.tn) if (res.fp + res.tn) else 0.0
    res.adv_tpr = adv_positives / samples if samples else None
    return res


def run(
    *,
    samples: int = DEFAULT_SAMPLES,
    tokens: int = DEFAULT_TOKENS,
    key: int = sd.DEFAULT_KEY,
    gamma: float = sd.DEFAULT_GAMMA,
    context: int = sd.DEFAULT_CONTEXT,
    noise_rate: float = 0.05,
    seed: int = 0,
) -> dict[str, Any]:
    bank = sd.WordBank()
    schemes = [
        (
            sd.KGWEmbedder(key=key, gamma=gamma, context=context),
            sd.KGWDetector(key=key, gamma=gamma, context=context),
        ),
        (
            sd.SynthIDTextMeanEmbedder(key=key, context=context),
            sd.SynthIDTextMeanDetector(key=key, context=context),
        ),
        (
            sd.SynthIDTextBayesEmbedder(key=key, context=context),
            sd.SynthIDTextBayesDetector(key=key, context=context),
        ),
        (
            sd.UnigramWatermarkEmbedder(key=key, gamma=gamma, context=context),
            sd.UnigramWatermarkDetector(key=key, gamma=gamma, context=context),
        ),
        (
            sd.ExponentialEmbedder(key=key, context=context),
            sd.ExponentialDetector(key=key, context=context),
        ),
    ]
    results = [
        _run_scheme(emb, det, bank, samples, tokens, seed, noise_rate) for emb, det in schemes
    ]
    # Key-mismatch must not fire: honest property, not a failure to detect.
    mismatch = 0
    for i in range(samples):
        wm = " ".join(sd.KGWEmbedder(key=key, gamma=gamma).watermark(tokens, bank, seed=seed + i))
        if sd.KGWDetector(key=key + 1).detect(wm)["is_watermarked"]:
            mismatch += 1
    results.append(
        SchemeResult(
            scheme="kgw-key-mismatch",
            tn=samples - mismatch,
            fp=mismatch,
            tnr=(samples - mismatch) / samples,
            fpr=mismatch / samples,
            note="marks made with key K must NOT trigger key K+1 detection",
        )
    )

    worst_fpr = max((r.fpr for r in results), default=0.0)
    worst_tpr = min((r.tpr for r in results if r.scheme != "kgw-key-mismatch"), default=0.0)
    worst_tnr = min((r.tnr for r in results), default=0.0)
    passed = worst_fpr <= GATE_MAX_FPR and worst_tpr >= GATE_MIN_TPR and worst_tnr >= GATE_MIN_TNR
    return {
        "detectors": [
            "statistical-kgw",
            "statistical-synthid-mean",
            "statistical-synthid-bayes",
            "statistical-unigram",
            "statistical-kgw-exp",
            "kgw-key-mismatch",
        ],
        "config": {
            "samples": samples,
            "tokens": tokens,
            "key": key,
            "gamma": gamma,
            "context": context,
            "noise_rate": noise_rate,
            "seed": seed,
        },
        "gates": {
            "max_fpr": GATE_MAX_FPR,
            "min_tpr": GATE_MIN_TPR,
            "min_tnr": GATE_MIN_TNR,
        },
        "worst": {
            "fpr": round(worst_fpr, 4),
            "tpr": round(worst_tpr, 4),
            "tnr": round(worst_tnr, 4),
        },
        "passed": passed,
        "results": [r.to_dict() for r in results],
    }


def _render_markdown(report: dict[str, Any]) -> str:
    cfg = report["config"]
    lines = [
        "# verify_harness report",
        "",
        f"config: samples={cfg['samples']}, tokens={cfg['tokens']}, key={cfg['key']}, "
        f"gamma={cfg['gamma']}, context={cfg['context']}, noise={cfg['noise_rate']}",
        "",
        "| scheme | TP | TN | FP | FN | TPR | TNR | FPR | adv-TPR |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in report["results"]:
        adv = f"{r['adv_tpr']:.4f}" if r["adv_tpr"] is not None else "—"
        lines.append(
            f"| {r['scheme']} | {r['tp']} | {r['tn']} | {r['fp']} | {r['fn']} | "
            f"{r['tpr']:.4f} | {r['tnr']:.4f} | {r['fpr']:.4f} | {adv} |"
        )
    lines.append("")
    worst = report["worst"]
    lines.append(
        f"worst: FPR={worst['fpr']:.4f} (gate ≤ {report['gates']['max_fpr']}), "
        f"TPR={worst['tpr']:.4f} (gate ≥ {report['gates']['min_tpr']}), "
        f"TNR={worst['tnr']:.4f} (gate ≥ {report['gates']['min_tnr']})"
    )
    lines.append(f"**{'PASS' if report['passed'] else 'FAIL'}**")
    return "\n".join(lines)


def _arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="CI quality harness for keyed statistical detectors")
    p.add_argument("subcommand", choices=["run"])
    p.add_argument("--samples", type=int, default=DEFAULT_SAMPLES)
    p.add_argument("--tokens", type=int, default=DEFAULT_TOKENS)
    p.add_argument("--key", type=int, default=sd.DEFAULT_KEY)
    p.add_argument("--gamma", type=float, default=sd.DEFAULT_GAMMA)
    p.add_argument("--context", type=int, default=sd.DEFAULT_CONTEXT)
    p.add_argument("--noise-rate", type=float, default=0.05)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--json", action="store_true")
    p.add_argument("--out", default=None, help="write the report to a file (.json or .md)")
    return p


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    args = _arg_parser().parse_args(argv)
    report = run(
        samples=args.samples,
        tokens=args.tokens,
        key=args.key,
        gamma=args.gamma,
        context=args.context,
        noise_rate=args.noise_rate,
        seed=args.seed,
    )
    if args.out:
        out = Path(args.out)
        if out.suffix == ".md":
            out.write_text(_render_markdown(report), encoding="utf-8")
        else:
            out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"report written to {out}", file=sys.stderr)
    if args.json:
        print(json.dumps(report, ensure_ascii=False))
    else:
        print(_render_markdown(report))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
