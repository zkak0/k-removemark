#!/usr/bin/env python3
"""Visible image-watermark scrubber (CPU, zero-model).

Targets the visible marks today's generators stamp onto pixels: bright sparkle
grids (Gemini "sparkle"), corner text badges (Doubao/Kling "AI生成", Jimeng
"即梦"). Detection is algorithmic and honest:

- ``detect_bright_grid`` finds a regular grid of high-luminance points — the
  visual signature of Gemini-style sparkle marks. It reports coordinates and a
  *best-effort* flag; it is not a vendor detector.
- ``reverse_alpha_blend`` removes a *known* additive watermark pattern given
  its alpha: base = (pixel - alpha*pattern) / (1 - alpha). The pattern must
  come from the user (clean twin, or GargantuaX gemini-watermark-remover
  assets); without it removal is impossible in general — the honest boundary.
- ``scrub_corner_label`` fills a detected corner text badge by border
  interpolation + light blur.

The pixel math is pure Python. A minimal PNG codec (stdlib zlib) covers the
common case with zero dependencies; when Pillow is importable it transparently
extends decoding to JPEG/WebP/etc. Neither numpy nor OpenCV is used, so this
runs on a bare install.
"""

from __future__ import annotations

import argparse
import binascii
import itertools
import json
import struct
import sys
import zlib
from pathlib import Path
from typing import Any

MIN_GRID_POINTS = 6
GRID_SPACING_TOL = 0.35
BRIGHT_THRESHOLD = 200

# --- minimal PNG codec (stdlib) ----------------------------------------------

_PNG_SIG = b"\x89PNG\r\n\x1a\n"


def _png_chunks(data: bytes) -> list[tuple[str, bytes]]:
    if not data.startswith(_PNG_SIG):
        raise ValueError("not a PNG")
    chunks: list[tuple[str, bytes]] = []
    off = 8
    while off + 8 <= len(data):
        (length,) = struct.unpack(">I", data[off : off + 4])
        typ = data[off + 4 : off + 8].decode("latin-1")
        body = data[off + 8 : off + 8 + length]
        if len(body) != length:
            raise ValueError("truncated PNG chunk")
        chunks.append((typ, body))
        off += 12 + length
    return chunks


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    return a if pa <= pb and pa <= pc else (b if pb <= pc else c)


def decode_png(data: bytes) -> tuple[int, int, list[list[tuple[int, int, int]]]]:
    """Decode an 8-bit PNG (0/2/3/4/6 color types, non-interlaced) to RGB rows."""
    chunks = _png_chunks(data)
    if not chunks or chunks[0][0] != "IHDR":
        raise ValueError("missing IHDR")
    w, h, depth, ctype, comp, filt, interlace = struct.unpack(">IIBBBBB", chunks[0][1])
    if depth != 8 or comp != 0 or filt != 0 or interlace != 0:
        raise ValueError(
            f"unsupported PNG layout (depth={depth} ctype={ctype} interlace={interlace})"
        )
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ctype]
    palette: dict[int, tuple[int, int, int]] = {}
    raw = b""
    for typ, body in chunks[1:]:
        if typ == "IDAT":
            raw += body
        elif typ == "PLTE":
            for i in range(0, len(body) - 2, 3):
                palette[i // 3] = (body[i], body[i + 1], body[i + 2])
        elif typ == "IEND":
            break
    scan = zlib.decompress(raw)
    stride = w * channels
    prev = bytearray(stride)
    rows: list[list[tuple[int, int, int]]] = []
    pos = 0
    for _ in range(h):
        fb = scan[pos]
        pos += 1
        line = bytearray(scan[pos : pos + stride])
        pos += stride
        if fb == 0:
            pass
        elif fb == 1:
            for i in range(channels, stride):
                line[i] = (line[i] + line[i - channels]) & 0xFF
        elif fb == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif fb == 3:
            for i in range(stride):
                a = line[i - channels] if i >= channels else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 0xFF
        elif fb == 4:
            for i in range(stride):
                a = line[i - channels] if i >= channels else 0
                c = prev[i - channels] if i >= channels else 0
                line[i] = (line[i] + _paeth(a, prev[i], c)) & 0xFF
        else:
            raise ValueError(f"bad PNG filter {fb}")
        row: list[tuple[int, int, int]] = []
        for x in range(w):
            base = x * channels
            if ctype == 3:
                idx = line[base]
                row.append(palette.get(idx, (0, 0, 0)))
            elif ctype == 0:
                v = line[base]
                row.append((v, v, v))
            elif ctype == 2:
                row.append((line[base], line[base + 1], line[base + 2]))
            else:  # 4 or 6: drop alpha, keep RGB
                row.append((line[base], line[base + 1], line[base + 2]))
        rows.append(row)
        prev = line
    return w, h, rows


def encode_png(w: int, h: int, rows: list[list[tuple[int, int, int]]]) -> bytes:
    """Re-encode RGB rows as a PNG (filter 0, no interlace)."""
    raw = bytearray()
    for row in rows:
        raw.append(0)
        for px in row:
            raw += bytes(px)
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)

    def chunk(typ: bytes, body: bytes) -> bytes:
        return (
            struct.pack(">I", len(body))
            + typ
            + body
            + struct.pack(">I", binascii.crc32(typ + body) & 0xFFFFFFFF)
        )

    return (
        _PNG_SIG
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(bytes(raw), 6))
        + chunk(b"IEND", b"")
    )


def load_rgb(path: Path) -> tuple[int, int, list[list[tuple[int, int, int]]]]:
    """Decode to RGB rows: stdlib PNG path, or Pillow when available."""
    data = path.read_bytes()
    if data.startswith(_PNG_SIG):
        return decode_png(data)
    try:
        from PIL import Image  # type: ignore[import-not-found]
    except ImportError:
        raise ValueError(
            f"decoding {path.suffix} images needs Pillow (PNG works without it)"
        ) from None
    img = Image.open(path).convert("RGB")
    w, h = img.size
    rows = [[img.getpixel((x, y))[:3] for x in range(w)] for y in range(h)]
    return w, h, rows


def save_rgb(
    w: int, h: int, rows: list[list[tuple[int, int, int]]], path: Path, suffix: str
) -> None:
    if suffix.lower() == ".png":
        path.write_bytes(encode_png(w, h, rows))
        return
    try:
        from PIL import Image  # type: ignore[import-not-found]
    except ImportError:
        raise ValueError(f"writing {suffix} needs Pillow; PNG works without it") from None
    img = Image.new("RGB", (w, h))
    img.putdata([p for row in rows for p in row])
    img.save(path)


# --- detection ---------------------------------------------------------------


def _luminance(px: tuple[int, int, int]) -> float:
    return 0.299 * px[0] + 0.587 * px[1] + 0.114 * px[2]


def _bright_points(rows: list[list[tuple[int, int, int]]], threshold: int) -> list[tuple[int, int]]:
    pts: list[tuple[int, int]] = []
    for y in range(0, len(rows), 2):
        row = rows[y]
        for x in range(0, len(row), 2):
            if _luminance(row[x]) >= threshold:
                pts.append((x, y))
    return pts


def _cluster(points: list[tuple[int, int]], gap: int = 8) -> list[list[tuple[int, int]]]:
    """Greedy bucketing: points closer than `gap` join one bucket (a dot)."""
    buckets: list[list[tuple[int, int]]] = []
    for p in points:
        placed = False
        for b in buckets:
            if any(abs(p[0] - q[0]) <= gap and abs(p[1] - q[1]) <= gap for q in b):
                b.append(p)
                placed = True
                break
        if not placed:
            buckets.append([p])
    return buckets


def _centroids(buckets: list[list[tuple[int, int]]]) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for b in buckets:
        out.append((sum(p[0] for p in b) // len(b), sum(p[1] for p in b) // len(b)))
    return out


def _spacing_regular(points: list[tuple[int, int]]) -> float | None:
    if len(points) < 2:
        return None
    xs = sorted(p[0] for p in points)
    ys = sorted(p[1] for p in points)
    gaps: list[int] = []
    for seq in (xs, ys):
        for a, b in itertools.pairwise(seq):
            if b - a > 0:
                gaps.append(b - a)
    if not gaps:
        return None
    gaps.sort()
    med = gaps[len(gaps) // 2]
    if med <= 0:
        return None
    dev = sum(abs(g - med) for g in gaps) / len(gaps)
    if dev / med > GRID_SPACING_TOL:
        return None
    return float(med)


def detect_bright_grid(path: Path, *, threshold: int = BRIGHT_THRESHOLD) -> dict[str, Any]:
    """Detect a regular grid of bright points (Gemini-sparkle signature)."""
    try:
        _, _, rows = load_rgb(path)
    except Exception as e:
        return {"available": False, "error": f"cannot decode image: {e}"}
    pts = _bright_points(rows, threshold)
    if len(pts) < MIN_GRID_POINTS:
        return {
            "available": True,
            "detector": "visible-bright-grid",
            "is_detected": False,
            "points_found": len(pts),
            "note": "fewer than 6 bright points; no sparkle-grid signature.",
        }
    centroids = _centroids(_cluster(pts))
    if len(centroids) < MIN_GRID_POINTS:
        return {
            "available": True,
            "detector": "visible-bright-grid",
            "is_detected": False,
            "points_found": len(pts),
            "note": "bright points collapse into too few clusters.",
        }
    spacing = _spacing_regular(centroids)
    if spacing is None:
        return {
            "available": True,
            "detector": "visible-bright-grid",
            "is_detected": False,
            "points_found": len(pts),
            "note": "bright clusters present but spacing is irregular.",
        }
    xs = [p[0] for p in centroids]
    ys = [p[1] for p in centroids]
    return {
        "available": True,
        "detector": "visible-bright-grid",
        "is_detected": True,
        "points_found": len(pts),
        "grid_spacing": round(spacing, 1),
        "bbox": [min(xs), min(ys), max(xs), max(ys)],
        "note": (
            "best-effort geometric signal (regular bright grid); not proof of any "
            "vendor. Reverse-removal needs the pattern tile + alpha."
        ),
    }


def reverse_alpha_blend(
    path: Path, pattern_path: Path, alpha: float
) -> tuple[int, int, list[list[tuple[int, int, int]]]]:
    """Remove an additive watermark: base = (pixel - alpha*pattern)/(1-alpha)."""
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be in (0, 1)")
    w, h, img = load_rgb(path)
    pw, ph, pat = load_rgb(pattern_path)
    if (pw, ph) != (w, h):
        raise ValueError(f"pattern {pw}x{ph} does not match image {w}x{h}")
    inv = 1.0 / (1.0 - alpha)
    out = [
        [
            tuple(max(0, min(255, int((px[c] - alpha * pt[c]) * inv))) for c in range(3))
            for px, pt in zip(row, patrow, strict=True)
        ]
        for row, patrow in zip(img, pat, strict=True)
    ]
    return w, h, out


def _label_bbox(
    w: int, h: int, rows: list[list[tuple[int, int, int]]], corner: str
) -> tuple[int, int, int, int] | None:
    if corner == "bottom-left":
        x0, y0, x1, y1 = 0, int(h * 0.90), int(w * 0.30), h
    elif corner == "bottom-right":
        x0, y0, x1, y1 = int(w * 0.70), int(h * 0.90), w, h
    elif corner == "top-left":
        x0, y0, x1, y1 = 0, 0, int(w * 0.30), int(h * 0.10)
    else:
        x0, y0, x1, y1 = int(w * 0.70), 0, w, int(h * 0.10)
    vals = [_luminance(rows[y][x]) for y in range(y0, y1, 2) for x in range(x0, x1, 2)]
    if not vals:
        return None
    mean = sum(vals) / len(vals)
    cols: list[int] = []
    rows_hit: list[int] = []
    for y in range(y0, y1):
        for x in range(x0, x1):
            if abs(_luminance(rows[y][x]) - mean) > 30:
                cols.append(x)
                rows_hit.append(y)
    if len(cols) < 20 or len(rows_hit) < 4:
        return None
    return min(cols), min(rows_hit), max(cols), max(rows_hit)


def _fill_bbox(
    w: int, h: int, rows: list[list[tuple[int, int, int]]], bbox: tuple[int, int, int, int]
) -> list[list[tuple[int, int, int]]]:
    """Inpaint bbox from its 1px border ring via bilinear interpolation + blur."""
    x0, y0, x1, y1 = bbox
    bw, bh = x1 - x0 + 1, y1 - y0 + 1
    if bw <= 2 or bh <= 2:
        return rows

    def get(x: int, y: int) -> tuple[int, int, int]:
        return rows[max(0, min(h - 1, y))][max(0, min(w - 1, x))]

    def blur(px: tuple[int, int, int]) -> tuple[int, int, int]:
        r, g, b = 0, 0, 0
        n = 0
        for _ in (-1, 0, 1):
            for dx in (-1, 0, 1):
                rr, gg, bb = px[0] + dx * 2, px[1] + dx * 2, px[2] + dx * 2
                r += rr
                g += gg
                b += bb
                n += 1
        return r // n, g // n, b // n

    out = [row[:] for row in rows]
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            # bilinear sample from the border ring at (x0-1, y0-1)..(x1+1, y1+1)
            fx = (x - x0 + 1) / (bw + 1)
            fy = (y - y0 + 1) / (bh + 1)
            tl = get(x0 - 1, y0 - 1)
            tr = get(x1 + 1, y0 - 1)
            bl = get(x0 - 1, y1 + 1)
            br = get(x1 + 1, y1 + 1)
            top = tuple(int(tl[c] + (tr[c] - tl[c]) * fx) for c in range(3))
            bot = tuple(int(bl[c] + (br[c] - bl[c]) * fx) for c in range(3))
            px = tuple(int(top[c] + (bot[c] - top[c]) * fy) for c in range(3))
            out[y][x] = blur(px)
    return out


def scrub_corner_label(path: Path, corner: str) -> dict[str, Any]:
    """Remove a corner text badge (Doubao "AI生成"-class) by border inpainting."""
    try:
        w, h, rows = load_rgb(path)
    except Exception as e:
        return {"available": False, "error": f"cannot decode image: {e}"}
    bbox = _label_bbox(w, h, rows, corner)
    if bbox is None:
        return {
            "available": True,
            "detector": "visible-corner-label",
            "is_detected": False,
            "corner": corner,
            "note": "no contrasting text badge found in the corner band.",
        }
    rows = _fill_bbox(w, h, rows, bbox)
    return {
        "available": True,
        "detector": "visible-corner-label",
        "is_detected": True,
        "corner": corner,
        "bbox": list(bbox),
        "note": "best-effort: badge region filled by border inpainting.",
        "w": w,
        "h": h,
        "rows": rows,
    }


def scrub_visible(
    path: Path, *, pattern_path: Path | None = None, corner: str | None = None
) -> dict[str, Any]:
    """Run visible-mark detection (+ optional removal) on an image file."""
    grid = detect_bright_grid(path)
    report: dict[str, Any] = {
        "input": str(path),
        "bright_grid": grid,
        "actions": [],
        "output_w": None,
        "output_h": None,
    }
    if corner is not None:
        res = scrub_corner_label(path, corner)
        if res.get("rows") is not None:
            report["actions"].append(f"corner-label scrub ({corner})")
            report["output_w"], report["output_h"] = res.pop("w"), res.pop("h")
            report["rows"] = res.pop("rows")
        report["corner_label"] = res
    if pattern_path is not None:
        try:
            w, h, rows = reverse_alpha_blend(path, pattern_path, 0.5)
            report["actions"].append(f"reverse-alpha blend (pattern={pattern_path.name})")
            report["output_w"], report["output_h"] = w, h
            report["rows"] = rows
        except Exception as e:
            report["reverse_blend"] = {"available": False, "error": str(e)}
    return report


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("path", type=Path, help="Input image (PNG via stdlib; JPEG/WebP need Pillow)")
    p.add_argument("-o", "--output", type=Path, help="Output path for scrubbed image")
    p.add_argument("--detect", action="store_true", help="Only detect (no rewrite)")
    p.add_argument("--corner", choices=["bottom-left", "bottom-right", "top-left", "top-right"])
    p.add_argument(
        "--pattern", type=Path, help="Known watermark pattern tile (reverse alpha blend)"
    )
    p.add_argument("--alpha", type=float, default=0.5, help="Pattern alpha for reverse blend")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    if not args.path.is_file():
        print(f"not a file: {args.path}", file=sys.stderr)
        return 2
    report = scrub_visible(args.path, pattern_path=args.pattern, corner=args.corner)
    if not args.detect and report.get("rows") is not None and args.output is not None:
        suffix = args.output.suffix
        if suffix.lower() != ".png" and args.pattern is None and args.corner is None:
            pass
        try:
            save_rgb(report["output_w"], report["output_h"], report["rows"], args.output, suffix)
            report["output"] = str(args.output)
        except Exception as e:
            report["save_error"] = str(e)
    report.pop("rows", None)
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        grid = report["bright_grid"]
        print(
            f"bright-grid detected: {grid.get('is_detected', False)} ({grid.get('points_found', 0)} pts)"
        )
        cl = report.get("corner_label")
        if cl:
            print(f"corner label ({cl.get('corner')}) detected: {cl.get('is_detected', False)}")
        print(f"actions: {', '.join(report['actions']) or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
