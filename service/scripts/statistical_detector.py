#!/usr/bin/env python3
"""Keyed statistical text-watermark detection in stdlib (no LLM, no torch).

Implements two token-sampling watermark families from the public literature,
self-consistently: detection requires only the *key* and the tokenizer — the
generating LLM is never loaded (Kirchenbauer et al. 2023: "detection is cheap
and fast because the LLM does not need to be loaded or run"; DeepMind SynthID-Text
Nature 2024: scoring "only requires access to the tokenized text, the
watermarking key k and the random seed generator").

Schemes
-------
- KGW: green/red-list. At each scored token, PRF(key, context, token) lands in
  [0, 1); it is a "green hit" when < gamma. Detection = one-proportion z-test on
  the green fraction over T scored tokens.
- SynthID-Text Mean: per-token g-value = PRF(key, context, token) in [0, 1).
  Under H0 g ~ U(0,1); the Mean detector z-tests the per-token average.
  (Weighted Mean and Bayesian detectors need a trained prior / word frequencies
  and are out of scope for the zero-model default; see references/.)

Honesty boundary
----------------
Production vendor watermarks (Claude, Gemini) are keyed with a *secret* key. A
scheme is only detectable when its key is known — this is a security property,
not a missing feature. This module ships the algorithm: set the key (env or
kwargs) for open-LLM / controlled experiments, or leave the default key and read
the z-score as a *relative* signal. It is never presented as a vendor detector.

The embedders (KGWEmbedder / SynthIDTextMeanEmbedder) synthesize marks over a
word bank with no model — used by verify_harness.py to measure real TP/FP in CI.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import re
import sys
from collections.abc import Sequence
from typing import Any

# -- configuration (env, overridable by kwargs) -----------------------------

DEFAULT_KEY = int(os.environ.get("WATERMARKS_STATISTICAL_KEY", "15485863"))
DEFAULT_GAMMA = float(os.environ.get("WATERMARKS_STATISTICAL_GAMMA", "0.25"))
DEFAULT_THRESHOLD = float(os.environ.get("WATERMARKS_STATISTICAL_THRESHOLD", "4.0"))
DEFAULT_CONTEXT = int(os.environ.get("WATERMARKS_STATISTICAL_CONTEXT", "1"))
DEFAULT_DELTA = float(os.environ.get("WATERMARKS_STATISTICAL_DELTA", "0.5"))
DEFAULT_BETA = float(os.environ.get("WATERMARKS_STATISTICAL_BETA", "2.0"))

_TOKEN_SPLIT = re.compile(r"[^\W_]+", re.UNICODE)


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


# -- tokenization ------------------------------------------------------------


def tokens(text: str) -> list[str]:
    """Lowercased word tokens (Unicode letters/numbers), no stopword filter.

    Whitespace + case folding is the tokenizer the word-level KGW schemes use;
    it keeps the detector dependency-free and deterministic. The generating
    tokenizer must match for keyed detection to work — same rule as upstream.
    """
    return [m.group(0).lower() for m in _TOKEN_SPLIT.finditer(text)]


def _prf01(key: int, context: Sequence[str], token: str) -> float:
    """Deterministic PRF -> [0, 1): SHA-256(key | context | token)."""
    ctx = "\x00".join(context)
    digest = hashlib.sha256(f"{key}\x00{ctx}\x00{token}".encode()).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


# -- shared scoring ----------------------------------------------------------


def _scored_pairs(toks: list[str], key: int, context: int) -> list[tuple[float, str]]:
    """Per-token PRF values; the first `context` tokens are unscored (no seed)."""
    pairs: list[tuple[float, str]] = []
    for i in range(context, len(toks)):
        ctx = toks[max(0, i - context) : i]
        pairs.append((_prf01(key, ctx, toks[i]), toks[i]))
    return pairs


def _z_green(green: int, total: int, gamma: float) -> float:
    if total <= 0:
        return 0.0
    denom = math.sqrt(total * gamma * (1 - gamma))
    return (green - gamma * total) / denom if denom > 0 else 0.0


def _z_mean(mean_score: float, total: int) -> float:
    """H0: g ~ U(0,1) -> mean ~ N(0.5, 1/(12T))."""
    if total <= 0:
        return 0.0
    return (mean_score - 0.5) * math.sqrt(12.0 * total)


def _p_value(z: float) -> float:
    """One-sided p from a z-score (Abramowitz-Stegun 7.1.26 error function)."""
    return 0.5 * math.erfc(z / math.sqrt(2.0))


def _llr_constants(
    gamma: float, delta: float
) -> tuple[float, float, float, float]:
    """Per-token log-likelihood ratios for the KGW-style boosted step model.

    Under the null the per-token g-score is uniform on [0, 1). Under the
    watermark the top ``gamma`` fraction is boosted by ``delta``. Returns
    (llr_green, llr_red, e_null, var_null) where e_null/var_null are the
    null-distribution mean/variance of a single token's LLR.
    """
    pg = (1.0 + delta) / gamma
    pr = (1.0 - delta) / (1.0 - gamma)
    llr_green = math.log(pg)
    llr_red = math.log(pr)
    e = gamma * llr_green + (1.0 - gamma) * llr_red
    var = gamma * (llr_green - e) ** 2 + (1.0 - gamma) * (llr_red - e) ** 2
    return llr_green, llr_red, e, var


def _bayes_llr(
    pairs: list[tuple[float, str]], gamma: float, delta: float
) -> tuple[float, float, float]:
    """Sum of per-token LLRs plus null-moment z-score.

    Returns (total_llr, e_null_total, z).
    """
    llr_green, llr_red, e, var = _llr_constants(gamma, delta)
    total = len(pairs)
    if total <= 0:
        return 0.0, 0.0, 0.0
    s = sum(llr_green if g < gamma else llr_red for g, _ in pairs)
    e_null = total * e
    std_null = math.sqrt(total * var) if var > 0 else 1.0
    z = (s - e_null) / std_null
    return s, e_null, z


# -- detectors ---------------------------------------------------------------


class KGWDetector:
    """Green/red-list detection over word tokens (Kirchenbauer et al.)."""

    name = "statistical-kgw"
    vendor = "open-llm"

    def __init__(
        self,
        *,
        key: int | None = None,
        gamma: float | None = None,
        threshold: float | None = None,
        context: int | None = None,
    ) -> None:
        self._key = key if key is not None else DEFAULT_KEY
        self._gamma = gamma if gamma is not None else DEFAULT_GAMMA
        self._threshold = threshold if threshold is not None else DEFAULT_THRESHOLD
        self._context = context if context is not None else DEFAULT_CONTEXT

    def available(self) -> bool:
        return True

    def detect(self, text: str) -> dict[str, Any]:
        toks = tokens(text)
        pairs = _scored_pairs(toks, self._key, self._context)
        total = len(pairs)
        green = sum(1 for v, _ in pairs if v < self._gamma)
        z = _z_green(green, total, self._gamma)
        return {
            "detector": self.name,
            "vendor": self.vendor,
            "scheme": "kgw",
            "available": True,
            "keyed": True,
            "tokens_scored": total,
            "green_tokens": green,
            "green_fraction": green / total if total else 0.0,
            "gamma": self._gamma,
            "z_score": round(z, 4),
            "p_value": round(_p_value(z), 6),
            "threshold": self._threshold,
            "is_watermarked": bool(z > self._threshold),
            "note": (
                "keyed statistical detection (self-consistent); only valid "
                "against text generated with the same key/scheme — not a "
                "vendor detector."
            ),
        }


class SynthIDTextMeanDetector:
    """Mean-score detection over word tokens (SynthID-Text, Nature 2024)."""

    name = "statistical-synthid-mean"
    vendor = "open-llm"

    def __init__(
        self,
        *,
        key: int | None = None,
        threshold: float | None = None,
        context: int | None = None,
    ) -> None:
        self._key = key if key is not None else DEFAULT_KEY
        self._threshold = threshold if threshold is not None else DEFAULT_THRESHOLD
        self._context = context if context is not None else DEFAULT_CONTEXT

    def available(self) -> bool:
        return True

    def detect(self, text: str) -> dict[str, Any]:
        toks = tokens(text)
        pairs = _scored_pairs(toks, self._key, self._context)
        total = len(pairs)
        mean = sum(v for v, _ in pairs) / total if total else 0.5
        z = _z_mean(mean, total)
        return {
            "detector": self.name,
            "vendor": self.vendor,
            "scheme": "synthid-text-mean",
            "available": True,
            "keyed": True,
            "tokens_scored": total,
            "mean_score": round(mean, 4),
            "z_score": round(z, 4),
            "p_value": round(_p_value(z), 6),
            "threshold": self._threshold,
            "is_watermarked": bool(z > self._threshold),
            "note": (
                "Mean-score SynthID-Text class detection (keyed, self-consistent). "
                "Weighted Mean / Bayesian need a trained prior and are out of "
                "scope for the zero-model default."
            ),
        }


class SynthIDTextBayesDetector:
    """Bayesian (LLR) detection over keyed per-token scores.

    Each token's g = PRF(key, context, token) is uniform under the null and
    boosted under the watermark. The per-token log-likelihood ratio for a
    step boost model is summed; the null mean/variance come from the model
    moments (no trained prior, fully self-consistent for our embedders).
    """

    name = "statistical-synthid-bayes"
    vendor = "open-llm"

    def __init__(
        self,
        *,
        key: int | None = None,
        gamma: float | None = None,
        delta: float | None = None,
        threshold: float | None = None,
        context: int | None = None,
    ) -> None:
        self._key = key if key is not None else DEFAULT_KEY
        self._gamma = gamma if gamma is not None else DEFAULT_GAMMA
        self._delta = delta if delta is not None else DEFAULT_DELTA
        self._threshold = threshold if threshold is not None else DEFAULT_THRESHOLD
        self._context = context if context is not None else DEFAULT_CONTEXT

    def available(self) -> bool:
        return True

    def detect(self, text: str) -> dict[str, Any]:
        toks = tokens(text)
        pairs = _scored_pairs(toks, self._key, self._context)
        total = len(pairs)
        s, e_null, z = _bayes_llr(pairs, self._gamma, self._delta)
        return {
            "detector": self.name,
            "vendor": self.vendor,
            "scheme": "synthid-text-bayes",
            "available": True,
            "keyed": True,
            "tokens_scored": total,
            "gamma": self._gamma,
            "delta": self._delta,
            "total_llr": round(s, 4),
            "expected_null_llr": round(e_null, 4),
            "z_score": round(z, 4),
            "p_value": round(_p_value(z), 6),
            "threshold": self._threshold,
            "is_watermarked": bool(z > self._threshold),
            "note": (
                "Bayesian log-likelihood-ratio SynthID-Text class detection "
                "(keyed, self-consistent step model, no trained prior). Not a "
                "vendor detector."
            ),
        }


class UnigramWatermarkDetector:
    """Unigram-frequency green/red-list detection (frequency prior, no model).

    The vocabulary is frequency-ranked; the green set for a context is the
    keyed top-``gamma`` fraction of that ranking. Detection counts green tokens
    with a KGW-style z-test. This is the ZMD-compatible stand-in for the
    Unigram-Watermark scheme (which normally uses an LLM frequency list).
    """

    name = "statistical-unigram"
    vendor = "open-llm"

    def __init__(
        self,
        *,
        key: int | None = None,
        gamma: float | None = None,
        threshold: float | None = None,
        context: int | None = None,
        bank: WordBank | None = None,
    ) -> None:
        self._key = key if key is not None else DEFAULT_KEY
        self._gamma = gamma if gamma is not None else DEFAULT_GAMMA
        self._threshold = threshold if threshold is not None else DEFAULT_THRESHOLD
        self._context = context if context is not None else DEFAULT_CONTEXT
        self._bank = bank if bank is not None else WordBank()

    def available(self) -> bool:
        return True

    def detect(self, text: str) -> dict[str, Any]:
        toks = tokens(text)
        total = 0
        green = 0
        for i in range(self._context, len(toks)):
            ctx = toks[max(0, i - self._context) : i]
            total += 1
            if toks[i] in self._bank.green_for(self._key, ctx, self._gamma):
                green += 1
        z = _z_green(green, total, self._gamma)
        return {
            "detector": self.name,
            "vendor": self.vendor,
            "scheme": "unigram",
            "available": True,
            "keyed": True,
            "tokens_scored": total,
            "green_tokens": green,
            "green_fraction": green / total if total else 0.0,
            "gamma": self._gamma,
            "z_score": round(z, 4),
            "p_value": round(_p_value(z), 6),
            "threshold": self._threshold,
            "is_watermarked": bool(z > self._threshold),
            "note": (
                "Unigram-frequency green/red-list detection (ZMD stand-in for "
                "Unigram-Watermark using our word bank as the frequency prior; "
                "self-consistent, keyed). EWD/SWEET remain model-dependent "
                "opt-ins and are not part of this scheme."
            ),
        }


class ExponentialDetector:
    """Exponential-tilting (EXP-edit family) detection, ZMD version.

    Each token contributes ``exp(beta * g)``; under the null g ~ U(0,1) so
    E[exp(beta*g)] = (exp(beta)-1)/beta. The summed score is z-tested against
    the null moments. This mirrors the exponential weighting family (Aaronson &
    Kirchner) without loading a language model.
    """

    name = "statistical-kgw-exp"
    vendor = "open-llm"

    def __init__(
        self,
        *,
        key: int | None = None,
        beta: float | None = None,
        threshold: float | None = None,
        context: int | None = None,
    ) -> None:
        self._key = key if key is not None else DEFAULT_KEY
        self._beta = beta if beta is not None else float(
            os.environ.get("WATERMARKS_STATISTICAL_BETA", "2.0")
        )
        self._threshold = threshold if threshold is not None else DEFAULT_THRESHOLD
        self._context = context if context is not None else DEFAULT_CONTEXT

    def available(self) -> bool:
        return True

    def detect(self, text: str) -> dict[str, Any]:
        toks = tokens(text)
        pairs = _scored_pairs(toks, self._key, self._context)
        total = len(pairs)
        if total <= 0:
            score = 0.0
            e = 0.0
            var = 0.0
        else:
            beta = self._beta
            if beta == 0.0:
                score = sum(g for g, _ in pairs)
                e = total * 0.5
                var = total / 12.0
            else:
                score = sum(math.exp(beta * g) for g, _ in pairs)
                m1 = (math.exp(beta) - 1.0) / beta
                m2 = (math.exp(2.0 * beta) - 1.0) / (2.0 * beta)
                e = total * m1
                var = total * (m2 - m1 * m1)
        std = math.sqrt(var) if var > 0 else 1.0
        z = (score - e) / std
        return {
            "detector": self.name,
            "vendor": self.vendor,
            "scheme": "kgw-exp",
            "available": True,
            "keyed": True,
            "tokens_scored": total,
            "beta": self._beta,
            "exp_score": round(score, 4),
            "z_score": round(z, 4),
            "p_value": round(_p_value(z), 6),
            "threshold": self._threshold,
            "is_watermarked": bool(z > self._threshold),
            "note": (
                "Exponential-tilting detection, EXP-edit family (keyed, "
                "self-consistent, no model). EWD/SWEET require a language "
                "model and remain documented opt-ins."
            ),
        }


# -- embedders (for verify_harness: synthetic marks, no model) ---------------


class WordBank:
    """Small sampling vocabulary for synthetic text generation."""

    def __init__(self, words: Sequence[str] | None = None) -> None:
        self.words = [w.lower() for w in (words or _DEFAULT_BANK)]

    def sample(self, rng: random.Random, n: int) -> list[str]:
        return [rng.choice(self.words) for _ in range(n)]

    def rank(self, word: str) -> int:
        return self.words.index(word) if word in self.words else len(self.words)

    def green_for(self, key: int, context: Sequence[str], gamma: float) -> list[str]:
        return [w for w in self.words if _prf01(key, context, w) < gamma]


class KGWEmbedder:
    """Hard red-list embedder: every sampled token comes from the green set."""

    def __init__(
        self, *, key: int | None = None, gamma: float | None = None, context: int | None = None
    ) -> None:
        self._key = key if key is not None else DEFAULT_KEY
        self._gamma = gamma if gamma is not None else DEFAULT_GAMMA
        self._context = context if context is not None else DEFAULT_CONTEXT

    def watermark(self, n_tokens: int, bank: WordBank, seed: int = 0) -> list[str]:
        rng = random.Random(seed)  # noqa: S311  deterministic synthetic-data sampling
        out: list[str] = []
        for _ in range(n_tokens):
            ctx = out[max(0, len(out) - self._context) :]
            green = bank.green_for(self._key, ctx, self._gamma)
            if not green:
                green = bank.words
            out.append(rng.choice(green))
        return out


class SynthIDTextMeanEmbedder:
    """Tournament-style embedder: among candidates, pick the max-g token."""

    def __init__(self, *, key: int | None = None, context: int | None = None) -> None:
        self._key = key if key is not None else DEFAULT_KEY
        self._context = context if context is not None else DEFAULT_CONTEXT

    def watermark(self, n_tokens: int, bank: WordBank, seed: int = 0) -> list[str]:
        rng = random.Random(seed)  # noqa: S311  deterministic synthetic-data sampling
        out: list[str] = []
        for _ in range(n_tokens):
            ctx = out[max(0, len(out) - self._context) :]
            candidates = rng.sample(bank.words, k=min(8, len(bank.words)))
            out.append(max(candidates, key=lambda w: _prf01(self._key, ctx, w)))
        return out


class SynthIDTextBayesEmbedder:
    """Tournament-style embedder for the LLR test: pick the min-g token.

    The Bayesian test treats g < gamma as the boosted (green) side, so the
    embedder drives g toward 0 to maximise the positive log-likelihood ratio.
    """

    def __init__(self, *, key: int | None = None, context: int | None = None) -> None:
        self._key = key if key is not None else DEFAULT_KEY
        self._context = context if context is not None else DEFAULT_CONTEXT

    def watermark(self, n_tokens: int, bank: WordBank, seed: int = 0) -> list[str]:
        rng = random.Random(seed)  # noqa: S311  deterministic synthetic-data sampling
        out: list[str] = []
        for _ in range(n_tokens):
            ctx = out[max(0, len(out) - self._context) :]
            candidates = rng.sample(bank.words, k=min(8, len(bank.words)))
            out.append(min(candidates, key=lambda w: _prf01(self._key, ctx, w)))
        return out


class UnigramWatermarkEmbedder:
    """Pick the highest-frequency candidate that is green for its context."""

    def __init__(
        self, *, key: int | None = None, gamma: float | None = None, context: int | None = None
    ) -> None:
        self._key = key if key is not None else DEFAULT_KEY
        self._gamma = gamma if gamma is not None else DEFAULT_GAMMA
        self._context = context if context is not None else DEFAULT_CONTEXT

    def watermark(self, n_tokens: int, bank: WordBank, seed: int = 0) -> list[str]:
        rng = random.Random(seed)  # noqa: S311  deterministic synthetic-data sampling
        out: list[str] = []
        for _ in range(n_tokens):
            ctx = out[max(0, len(out) - self._context) :]
            green = bank.green_for(self._key, ctx, self._gamma)
            if not green:
                out.append(rng.choice(bank.words))
                continue
            candidates = rng.sample(bank.words, k=min(8, len(bank.words)))
            green_cands = [w for w in candidates if w in green]
            pool = green_cands or candidates
            out.append(min(pool, key=lambda w: bank.rank(w)))
        return out


class ExponentialEmbedder:
    """Weighted tournament: sample a candidate proportional to exp(beta*g)."""

    def __init__(
        self, *, key: int | None = None, beta: float | None = None, context: int | None = None
    ) -> None:
        self._key = key if key is not None else DEFAULT_KEY
        self._beta = beta if beta is not None else float(
            os.environ.get("WATERMARKS_STATISTICAL_BETA", "2.0")
        )
        self._context = context if context is not None else DEFAULT_CONTEXT

    def watermark(self, n_tokens: int, bank: WordBank, seed: int = 0) -> list[str]:
        rng = random.Random(seed)  # noqa: S311  deterministic synthetic-data sampling
        out: list[str] = []
        for _ in range(n_tokens):
            ctx = out[max(0, len(out) - self._context) :]
            candidates = rng.sample(bank.words, k=min(16, len(bank.words)))
            weights = [math.exp(self._beta * _prf01(self._key, ctx, w)) for w in candidates]
            total_w = sum(weights)
            r = rng.uniform(0.0, total_w)
            acc = 0.0
            chosen = candidates[-1]
            for w, wt in zip(candidates, weights):
                acc += wt
                if r <= acc:
                    chosen = w
                    break
            out.append(chosen)
        return out


# -- CLI ---------------------------------------------------------------------

_DEFAULT_BANK = [
    "the",
    "a",
    "an",
    "and",
    "or",
    "but",
    "of",
    "in",
    "on",
    "at",
    "for",
    "with",
    "from",
    "by",
    "as",
    "to",
    "into",
    "about",
    "over",
    "under",
    "again",
    "also",
    "still",
    "yet",
    "just",
    "only",
    "even",
    "ever",
    "very",
    "quite",
    "rather",
    "almost",
    "enough",
    "however",
    "therefore",
    "meanwhile",
    "more",
    "most",
    "some",
    "any",
    "many",
    "much",
    "other",
    "another",
    "each",
    "every",
    "both",
    "neither",
    "first",
    "last",
    "next",
    "final",
    "new",
    "old",
    "good",
    "great",
    "small",
    "large",
    "high",
    "low",
    "long",
    "short",
    "strong",
    "weak",
    "early",
    "late",
    "recent",
    "future",
    "human",
    "system",
    "data",
    "work",
    "time",
    "world",
    "result",
    "process",
    "change",
    "space",
    "energy",
    "matter",
    "light",
    "sound",
    "water",
    "earth",
    "air",
    "tree",
    "plant",
    "animal",
    "bird",
    "fish",
    "stone",
    "metal",
    "glass",
    "cloth",
    "paper",
    "city",
    "river",
    "mountain",
    "ocean",
    "cloud",
    "storm",
    "wind",
    "rain",
    "snow",
    "field",
    "forest",
    "road",
    "bridge",
    "house",
    "window",
    "door",
    "table",
    "book",
    "word",
    "number",
    "shape",
    "color",
    "sound",
    "step",
    "movement",
    "speed",
    "force",
    "heat",
    "cold",
    "dry",
    "wet",
    "fast",
    "slow",
    "bright",
    "dark",
    "deep",
    "wide",
    "narrow",
    "thick",
    "thin",
    "hard",
    "soft",
    "smooth",
    "rough",
    "simple",
    "complex",
    "open",
    "closed",
    "build",
    "create",
    "make",
    "use",
    "find",
    "keep",
    "take",
    "give",
    "put",
    "bring",
    "leave",
    "run",
    "walk",
    "think",
    "know",
    "feel",
    "see",
    "hear",
    "say",
    "speak",
    "tell",
    "ask",
    "answer",
    "question",
    "problem",
    "solution",
    "method",
    "model",
    "theory",
    "practice",
    "science",
    "nature",
    "society",
    "culture",
    "language",
    "history",
    "future",
    "present",
    "past",
    "morning",
    "noon",
    "night",
    "day",
    "week",
    "month",
    "year",
    "hour",
    "minute",
    "second",
    "order",
    "power",
    "truth",
    "fact",
    "idea",
    "thought",
    "plan",
    "design",
    "form",
    "role",
    "team",
    "group",
    "people",
    "child",
    "parent",
    "friend",
    "family",
    "community",
    "region",
    "nation",
    "planet",
    "star",
    "sky",
    "sun",
    "moon",
    "universe",
    "growth",
    "change",
    "beginning",
    "middle",
    "end",
    "top",
    "bottom",
    "side",
    "center",
    "edge",
    "value",
    "measure",
    "quality",
    "level",
    "standard",
    "amount",
    "number",
    "degree",
    "type",
    "kind",
    "sort",
    "feature",
    "function",
    "purpose",
    "reason",
    "cause",
    "effect",
    "result",
    "outcome",
    "pattern",
    "structure",
    "system",
    "network",
    "connection",
    "link",
    "relation",
]


def _arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Keyed statistical text-watermark detection")
    p.add_argument("subcommand", choices=["detect"])
    p.add_argument("file", help="text file to score")
    p.add_argument(
        "--scheme",
        choices=["kgw", "synthid-mean", "synthid-bayes", "unigram", "kgw-exp"],
        default="kgw",
    )
    p.add_argument("--key", type=int, default=DEFAULT_KEY)
    p.add_argument("--gamma", type=float, default=DEFAULT_GAMMA)
    p.add_argument("--delta", type=float, default=DEFAULT_DELTA)
    p.add_argument("--beta", type=float, default=1.0)
    p.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    p.add_argument("--context", type=int, default=DEFAULT_CONTEXT)
    p.add_argument("--json", action="store_true")
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = _arg_parser().parse_args(argv)
    try:
        with open(args.file, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    if args.scheme == "synthid-mean":
        det = SynthIDTextMeanDetector(key=args.key, threshold=args.threshold, context=args.context)
    elif args.scheme == "synthid-bayes":
        det = SynthIDTextBayesDetector(
            key=args.key, gamma=args.gamma, delta=args.delta, threshold=args.threshold,
            context=args.context,
        )
    elif args.scheme == "unigram":
        det = UnigramWatermarkDetector(
            key=args.key, gamma=args.gamma, threshold=args.threshold, context=args.context
        )
    elif args.scheme == "kgw-exp":
        det = ExponentialDetector(
            key=args.key, beta=args.beta, threshold=args.threshold, context=args.context
        )
    else:
        det = KGWDetector(
            key=args.key, gamma=args.gamma, threshold=args.threshold, context=args.context
        )
    report = det.detect(text)
    if args.json:
        print(json.dumps(report, ensure_ascii=False))
    else:
        verdict = "WATERMARKED" if report["is_watermarked"] else "not watermarked"
        print(
            f"{report['detector']} | z={report['z_score']} "
            f"tokens={report['tokens_scored']} ({verdict}, threshold {report['threshold']})"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
