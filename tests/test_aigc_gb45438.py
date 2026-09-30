"""Tests for GB 45438-2025 AIGC file-metadata implicit-label detection + strip."""

from __future__ import annotations

import json
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "service" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from common import parse_aigc_json_marks
from container_meta import _blob_hits
from image_meta import clean_image, inspect_jpeg, inspect_png

AIGC_JSON = {
    "AIGC": {
        "Label": "1",
        "ContentProducer": "001191350100M000100Y4300000",
        "ProduceID": "abc123",
        "ReservedCode1": "e862483430d978cbf828b8b24296ef9328d843a0",
        "ContentPropagator": "99999999",
        "PropagateID": "xyz789",
        "ReservedCode2": "",
    }
}


def _png_chunk(ctype: bytes, payload: bytes) -> bytes:
    crc = zlib.crc32(ctype)
    crc = zlib.crc32(payload, crc) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + ctype + payload + struct.pack(">I", crc)


def _minimal_png_with_aigc() -> bytes:
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    idat = zlib.compress(b"\x00\x00\x00")
    text = b"Comment\x00" + json.dumps(AIGC_JSON, ensure_ascii=False).encode("utf-8")
    return (
        sig
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"tEXt", text)
        + _png_chunk(b"IDAT", idat)
        + _png_chunk(b"IEND", b"")
    )


def _minimal_jpeg_with_aigc() -> bytes:
    app0 = b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    app0_seg = b"\xff\xe0" + struct.pack(">H", len(app0) + 2) + app0
    app1 = b"XMP\x00" + json.dumps(AIGC_JSON, ensure_ascii=False).encode("utf-8")
    app1_seg = b"\xff\xe1" + struct.pack(">H", len(app1) + 2) + app1
    sos_payload = b"\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00"
    sos = b"\xff\xda" + struct.pack(">H", len(sos_payload) + 2) + sos_payload
    return b"\xff\xd8" + app0_seg + app1_seg + sos + b"\x00\x00" + b"\xff\xd9"


def test_parse_aigc_json_marks_label_and_producer():
    blob = json.dumps(AIGC_JSON, ensure_ascii=False).encode("utf-8")
    findings = parse_aigc_json_marks(blob)
    assert len(findings) == 1
    assert "GB 45438-2025" in findings[0]
    assert "Label=1" in findings[0]
    assert "001191350100M000100Y4300000" in findings[0]


def test_parse_aigc_json_marks_label_values():
    assert (
        "Label=2" in parse_aigc_json_marks(b'{"AIGC": {"Label": "2", "ContentProducer": "x"}}')[0]
    )
    assert (
        "Label=3" in parse_aigc_json_marks(b'{"AIGC": {"Label": "3", "ContentProducer": "x"}}')[0]
    )
    assert parse_aigc_json_marks(b"nothing to see here") == []


def test_inspect_png_flags_aigc():
    data = _minimal_png_with_aigc()
    has_c2pa, has_ai, findings = inspect_png(data)
    assert has_ai
    assert any("GB 45438-2025" in f for f in findings)
    assert not has_c2pa


def test_inspect_jpeg_flags_aigc():
    data = _minimal_jpeg_with_aigc()
    _, has_ai, findings = inspect_jpeg(data)
    assert has_ai
    assert any("GB 45438-2025" in f for f in findings)


def test_container_blob_hits_flags_aigc():
    _, has_ai, findings = _blob_hits(json.dumps(AIGC_JSON, ensure_ascii=False).encode("utf-8"))
    assert has_ai
    assert any("GB 45438-2025" in f for f in findings)


def test_clean_image_strips_aigc(tmp_path: Path):
    png = tmp_path / "aigc.png"
    png.write_bytes(_minimal_png_with_aigc())
    out = tmp_path / "aigc.cleaned.png"
    result = clean_image(png, out)
    assert not result["still_has_ai_metadata"]
    cleaned = out.read_bytes()
    _, has_ai, findings = inspect_png(cleaned)
    assert not has_ai
    assert not any("GB 45438-2025" in f for f in findings)
