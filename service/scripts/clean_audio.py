#!/usr/bin/env python3
"""Clean audio files: metadata strip + CPU DSP watermark perturbation.

Metadata (MP4/MOV/M4A, WAV, MP3 ID3v2) is stripped by ``av_meta.clean_av`` —
stdlib, byte-level. On top of that, ``--dsp`` perturbs the *waveform* of
uncompressed 16-bit PCM WAV using two published DSP techniques that break
phase/spectral watermarks:

- ``randomize_phase``: per-frame FFT phase scrambling with 50 % overlap-add.
  Destroys phase-coded marks; the least audible perturbation for speech/music.
- ``notch_tone``: spectral notch around the dominant carrier tone. Attacks
  single-carrier watermark beacons (the kind SynthID-Audio-style beacons
  place below the mask threshold).

Honest boundaries:
- DSP applies only to uncompressed 16-bit PCM WAV. MP3/AAC/M4A are compressed:
  DSP would need a full decoder — metadata-only for those, with a note.
- This is *best-effort* perturbation, not a proven vendor defeat. Nothing here
  claims to remove a specific vendor's watermark; it lowers the confidence a
  phase/spectral detector can place on the sample.
- Pure stdlib (wave, math, cmath); no numpy, no model.
"""

from __future__ import annotations

import argparse
import cmath
import json
import math
import random
import struct
import sys
import wave
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from av_meta import clean_av, detect_av_format
from common import cleaned_path, eprint

FRAME_SIZE = 4096
DEFAULT_SEED = 1
NOTCH_WIDTH_HZ = 60


def _fft(a: list[complex], inverse: bool = False) -> list[complex]:
    """Iterative radix-2 Cooley-Tukey FFT (pure stdlib)."""
    n = len(a)
    if n == 0:
        return []
    if n & (n - 1):
        raise ValueError("FFT length must be a power of two")
    out = a[:]
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j ^= bit
        if i < j:
            out[i], out[j] = out[j], out[i]
    length = 2
    sign = 1.0 if inverse else -1.0
    while length <= n:
        ang = sign * 2.0 * math.pi / length
        wlen = complex(math.cos(ang), math.sin(ang))
        for i in range(0, n, length):
            w = 1 + 0j
            half = length // 2
            for k in range(half):
                u = out[i + k]
                v = out[i + k + half] * w
                out[i + k] = u + v
                out[i + k + half] = u - v
                w *= wlen
        length <<= 1
    if inverse:
        out = [x / n for x in out]
    return out


def _hann(size: int) -> list[float]:
    return [0.5 * (1.0 - math.cos(2.0 * math.pi * i / (size - 1))) for i in range(size)]


def randomize_phase(samples: list[float], seed: int = DEFAULT_SEED) -> list[float]:
    """Frame-wise phase scrambling with 50 % overlap-add (Hann windowed)."""
    n = len(samples)
    if n < FRAME_SIZE:
        return samples
    size = FRAME_SIZE
    step = size // 2
    rng = random.Random(seed)  # noqa: S311  deterministic phase scrambling
    out = [0.0] * n
    win = _hann(size)
    pos = 0
    while pos < n:
        end = min(pos + size, n)
        frame = samples[pos:end]
        if len(frame) < size:
            break
        f = _fft(frame)
        for k in range(1, size // 2):
            phi = rng.uniform(0.0, 2.0 * math.pi)
            f[k] *= cmath.exp(1j * phi)
            f[size - k] = f[k].conjugate()
        back = [v.real for v in _fft(f, inverse=True)]
        for i in range(size):
            out[pos + i] += back[i] * win[i]
        pos += step
    # overlap-add normalized: windows sum to ~1 in the middle region
    for i in range(step, n - step):
        out[i] *= 0.5
    return out


def dominant_tone(samples: list[float], rate: int) -> float | None:
    """Frequency of the strongest spectral bin above 100 Hz (spectral notch target)."""
    n = len(samples)
    if n < 16:
        return None
    size = 1 << (n - 1).bit_length()
    frame = samples + [0.0] * (size - n)
    f = _fft(frame)
    best, best_mag = None, 0.0
    for k in range(1, size // 2):
        freq = k * rate / size
        if freq < 100.0:
            continue
        mag = abs(f[k])
        if mag > best_mag:
            best_mag, best = mag, freq
    return best


def spectral_notch(
    samples: list[float], rate: int, f0: float, width_hz: int = NOTCH_WIDTH_HZ
) -> list[float]:
    """Attenuate the spectral band around f0 (single-carrier beacon removal)."""
    n = len(samples)
    size = 1 << (n - 1).bit_length()
    frame = samples + [0.0] * (size - n)
    f = _fft(frame)
    for k in range(1, size // 2):
        freq = k * rate / size
        if abs(freq - f0) <= width_hz:
            f[k] *= 0.02
            f[size - k] = f[k].conjugate()
    back = [v.real for v in _fft(f, inverse=True)]
    return back[:n]


def notch_tone(
    samples: list[float], rate: int, width_hz: int = NOTCH_WIDTH_HZ
) -> tuple[list[float], float | None]:
    """Notch the dominant carrier tone; returns (samples, tone_freq)."""
    f0 = dominant_tone(samples, rate)
    if f0 is None:
        return samples, None
    return spectral_notch(samples, rate, f0, width_hz), f0


def _read_wav(path: Path) -> tuple[int, int, int, list[int]]:
    with wave.open(str(path), "rb") as w:
        if w.getsampwidth() != 2:
            raise ValueError("DSP requires 16-bit PCM WAV")
        nch = w.getnchannels()
        rate = w.getframerate()
        frames = w.readframes(w.getnframes())
    count = len(frames) // 2
    return nch, rate, 16, list(struct.unpack(f"<{count}h", frames))


def _write_wav(path: Path, nch: int, rate: int, samples: list[int]) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(nch)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(struct.pack(f"<{len(samples)}h", *samples))


def apply_dsp(
    src: Path, dest: Path, *, seed: int = DEFAULT_SEED, notch: bool = True
) -> dict[str, Any]:
    """Phase-randomize (and optionally notch) a 16-bit PCM WAV file."""
    nch, rate, _, samples = _read_wav(src)
    if nch == 2:
        left = samples[0::2]
        right = samples[1::2]
        left2 = randomize_phase([s / 32768.0 for s in left], seed)
        right2 = randomize_phase([s / 32768.0 for s in right], seed)
        if notch:
            left2, f_left = notch_tone(left2, rate)
            right2, f_right = notch_tone(right2, rate)
            tone = f_left or f_right
        else:
            tone = None
        out = []
        for a, b in zip(left2, right2, strict=False):
            out.append(int(max(-1.0, min(1.0, a)) * 32767))
            out.append(int(max(-1.0, min(1.0, b)) * 32767))
    else:
        m = randomize_phase([s / 32768.0 for s in samples], seed)
        if notch:
            m, tone = notch_tone(m, rate)
        else:
            tone = None
        out = [int(max(-1.0, min(1.0, v)) * 32767) for v in m]
    _write_wav(dest, nch, rate, out)
    return {
        "available": True,
        "engine": "dsp",
        "channel_count": nch,
        "sample_rate": rate,
        "phase_randomized": True,
        "notch": notch,
        "notch_tone_hz": round(tone, 1) if tone else None,
        "note": "best-effort phase/spectral perturbation, not a vendor defeat.",
    }


def clean_audio(
    src: Path,
    dest: Path,
    *,
    strip_all_metadata: bool = True,
    dsp: bool = False,
    seed: int = DEFAULT_SEED,
) -> dict[str, Any]:
    """Clean an audio file: metadata always; DSP on 16-bit PCM WAV when asked."""
    report: dict[str, Any] = {"input": str(src), "output": str(dest), "actions": []}
    try:
        fmt = detect_av_format(src.read_bytes())
    except Exception:
        fmt = ""
    report["format"] = fmt
    meta = clean_av(src, dest, strip_all_metadata=strip_all_metadata)
    report["actions"] += meta.get("actions", [])
    report["metadata"] = meta
    if dsp:
        if fmt != "wav":
            report["dsp"] = {
                "available": False,
                "error": "DSP applies only to uncompressed 16-bit PCM WAV; "
                f"{fmt or 'unknown'} is compressed (metadata was stripped).",
            }
        else:
            try:
                report["dsp"] = apply_dsp(dest, dest, seed=seed)
                report["actions"].append("DSP phase randomization")
            except Exception as e:
                report["dsp"] = {"available": False, "error": str(e)}
    return report


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("path", type=Path, help="Input audio (WAV/MP3/MP4/M4A/MOV)")
    p.add_argument("-o", "--output", type=Path, help="Output path (default: *.cleaned.*)")
    p.add_argument(
        "--dsp", action="store_true", help="Also perturb the waveform (16-bit PCM WAV only)"
    )
    p.add_argument("--no-notch", action="store_true", help="Phase-randomize without spectral notch")
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    if not args.path.is_file():
        eprint(f"not a file: {args.path}")
        return 2
    dest = args.output or cleaned_path(args.path)
    try:
        report = clean_audio(args.path, dest, dsp=args.dsp, seed=args.seed)
    except Exception as e:
        eprint(f"error: {e}")
        return 1
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        eprint(f"wrote {dest}")
        for a in report["actions"]:
            eprint(f"  - {a}")
        dsp = report.get("dsp")
        if dsp is not None:
            if dsp.get("available"):
                eprint(f"DSP: phase randomization + notch @ {dsp.get('notch_tone_hz')} Hz")
            else:
                eprint(f"DSP: {dsp.get('error', 'unavailable')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
