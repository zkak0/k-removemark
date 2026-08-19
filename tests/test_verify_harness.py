"""Tests for the CI quality harness (TP/FP/FPR gating)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "service", "scripts"))

import verify_harness as vh


def test_harness_passes_default_gates():
    report = vh.run(samples=20, tokens=150, seed=1)
    assert report["passed"] is True
    worst = report["worst"]
    assert worst["fpr"] <= vh.GATE_MAX_FPR
    assert worst["tpr"] >= vh.GATE_MIN_TPR
    assert worst["tnr"] >= vh.GATE_MIN_TNR


def test_harness_schemes_are_the_three_expected():
    report = vh.run(samples=5, tokens=100)
    names = [r["scheme"] for r in report["results"]]
    assert names == ["statistical-kgw", "statistical-synthid-mean", "kgw-key-mismatch"]


def test_key_mismatch_never_fires():
    report = vh.run(samples=10, tokens=100)
    mismatch = next(r for r in report["results"] if r["scheme"] == "kgw-key-mismatch")
    assert mismatch["fp"] == 0
    assert mismatch["tnr"] == 1.0


def test_noise_reduces_but_does_not_destroy_detection():
    report = vh.run(samples=10, tokens=200, noise_rate=0.30)
    clean = vh.run(samples=10, tokens=200, noise_rate=0.05)
    for r in report["results"]:
        if r["scheme"] == "kgw-key-mismatch":
            continue
        assert r["adv_tpr"] is not None
        assert r["adv_tpr"] <= 1.0
    assert report["worst"]["tpr"] >= clean["worst"]["tpr"] - 0.35


def test_markdown_render_has_tables_and_verdict():
    report = vh.run(samples=3, tokens=100)
    md = vh._render_markdown(report)
    assert "| scheme |" in md
    assert "**PASS**" in md


def test_cli_exit_code_zero_on_pass(tmp_path):
    import subprocess

    out = tmp_path / "report.json"
    r = subprocess.run(
        [
            sys.executable,
            os.path.join(os.path.dirname(vh.__file__), "verify_harness.py"),
            "run",
            "--samples",
            "10",
            "--tokens",
            "100",
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    assert out.exists()
