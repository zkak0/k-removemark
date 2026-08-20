"""Tests for the audio cleaner (metadata + pure-stdlib DSP)."""

import math
import os
import struct
import sys
import wave
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "service", "scripts"))

import clean_audio as ca

RATE = 8000


def _tone_wav(path: Path, freq: int = 440, seconds: float = 0.5) -> list[int]:
    n = int(RATE * seconds)
    samples = [int(8000 * math.sin(2 * math.pi * freq * t / RATE)) for t in range(n)]
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(struct.pack(f"<{n}h", *samples))
    return samples


def _energy_at(samples, freq, width=30):
    size = 1 << (len(samples) - 1).bit_length()
    frame = samples + [0.0] * (size - len(samples))
    f = ca._fft(frame)
    return sum(abs(f[k]) ** 2 for k in range(1, size // 2) if abs(k * RATE / size - freq) <= width)


def test_fft_roundtrip():
    a = [complex(math.sin(i * 0.7), 0.0) for i in range(8)]
    back = ca._fft(ca._fft(a), inverse=True)
    assert max(abs(x - y) for x, y in zip(a, back, strict=True)) < 1e-9


def test_fft_rejects_non_power_of_two():
    try:
        ca._fft([0.0] * 3)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_dominant_tone_finds_carrier(tmp_path):
    samples = [s / 32768.0 for s in _tone_wav(tmp_path / "tone.wav", 440)]
    f0 = ca.dominant_tone(samples, RATE)
    assert f0 is not None and 439 <= f0 <= 441


def test_phase_randomization_changes_but_preserves_length():
    n = int(RATE * 1.2)  # longer than FRAME_SIZE so frames actually process
    samples = [math.sin(2 * math.pi * 440 * t / RATE) for t in range(n)]
    out = ca.randomize_phase(samples, seed=1)
    assert len(out) == len(samples)
    assert out != samples


def test_notch_carrier_energy(tmp_path):
    samples = [s / 32768.0 for s in _tone_wav(tmp_path / "tone.wav", 440)]
    before = _energy_at(samples, 440)
    notched, tone = ca.notch_tone(samples, RATE)
    after = _energy_at(notched, 440)
    assert tone is not None
    assert after < before * 0.02


def test_clean_audio_dsp_pipeline(tmp_path):
    src = tmp_path / "tone.wav"
    _tone_wav(src, 440)
    dest = tmp_path / "tone_cleaned.wav"
    report = ca.clean_audio(src, dest, dsp=True)
    assert report["dsp"]["available"] is True
    assert report["dsp"]["phase_randomized"] is True
    assert "DSP phase randomization" in report["actions"]
    assert dest.exists()
    with wave.open(str(dest), "rb") as w:
        assert w.getframerate() == RATE
        assert w.getnframes() > 0


def test_clean_audio_compressed_refuses_dsp(tmp_path):
    src = tmp_path / "fakemp3.mp3"
    src.write_bytes(b"ID3\x04\x00\x00\x00\x00\x00\x00" + b"\xff\xfb" + b"\x00" * 32)
    dest = tmp_path / "fakemp3_cleaned.mp3"
    report = ca.clean_audio(src, dest, dsp=True)
    assert report["dsp"]["available"] is False
    assert "compressed" in report["dsp"]["error"]


def test_detect_periodic_pulses_finds_morse_like_rhythm():
    rate = 8000
    frame = rate * ca.PULSE_FRAME_MS // 1000
    samples: list[float] = []
    for _ in range(6):
        samples += [0.8] * frame
        samples += [0.0] * frame
    res = ca.detect_periodic_pulses(samples, rate)
    assert res["present"] is True
    assert res["interval_cv"] <= ca.PULSE_CV_MAX
    assert res["pulse_count"] >= 4


def test_detect_periodic_pulses_ignores_flat_signal():
    res = ca.detect_periodic_pulses([0.01] * 8000, 8000)
    assert res["present"] is False


def test_clean_audio_scan_pulses(tmp_path):
    rate = 8000
    frame = rate * ca.PULSE_FRAME_MS // 1000
    samples: list[int] = []
    for _ in range(5):
        samples += [8000] * frame
        samples += [0] * frame
    src = tmp_path / "morse.wav"
    with wave.open(str(src), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    dest = tmp_path / "morse_cleaned.wav"
    report = ca.clean_audio(src, dest, scan_pulses=True)
    assert report["pulses"]["present"] is True
    assert any("periodic (Morse-like) pulse pattern" in a for a in report["actions"])


def test_cli_json(tmp_path):
    import subprocess

    src = tmp_path / "tone.wav"
    _tone_wav(src, 440)
    r = subprocess.run(
        [
            sys.executable,
            os.path.join(os.path.dirname(ca.__file__), "clean_audio.py"),
            str(src),
            "--dsp",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    import json as _json

    report = _json.loads(r.stdout)
    assert report["dsp"]["available"] is True
