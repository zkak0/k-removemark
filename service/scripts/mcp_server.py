"""MCP server bridging to the k-removemark HTTP service.

Speaks the Model Context Protocol (JSON-RPC 2.0 over stdio) so MCP-only
clients (Claude Desktop, ChatGPT, Zed, Windsurf, OpenCode via MCP, ...) can
use the same detection/cleaning engine. Every tool proxies to the local HTTP
service at /detect, /inspect and /clean.

If the HTTP service is not running it is started in the background and
waited for (see _ensure_service). Point this server at an already-running
service with WATERMARKS_SERVER_URL (default http://127.0.0.1:8765); an
optional bearer token is read from WATERMARKS_SERVER_API_KEY, the same
variable the service reads.
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

VERSION = os.environ.get("WATERMARKS_SERVER_VERSION", "dev")
SERVICE_URL = os.environ.get("WATERMARKS_SERVER_URL", "http://127.0.0.1:8765").rstrip("/")
API_KEY = os.environ.get("WATERMARKS_SERVER_API_KEY", "").strip()
SERVER_SCRIPT = Path(__file__).with_name("server.py")

_KNOWN_VERSIONS = ("2024-11-05", "2025-03-26", "2025-06-18")
DEFAULT_PROTOCOL_VERSION = "2025-06-18"

TOOLS = [
    {
        "name": "get_health",
        "description": "Check that the k-removemark service is up and report its version.",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "detect_text",
        "description": (
            "Run watermark detectors on text: statistical KGW/SynthID-class (keyed), "
            "stylometry heuristic, and vendor seams when available. Detectors that "
            "need a key report unavailable rather than guessing."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string", "description": "Text to scan"}},
            "required": ["text"],
        },
    },
    {
        "name": "inspect",
        "description": (
            "Inspect a file (text, image, container, audio/video) for AI provenance "
            "marks: invisible Unicode, C2PA/EXIF/XMP/IPTC metadata, visible marks."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Base64-encoded file bytes (use encode_file for help)",
                },
                "name": {"type": "string", "description": "Original filename; extension routes format"},
            },
            "required": ["content", "name"],
        },
    },
    {
        "name": "clean",
        "description": (
            "Clean AI provenance marks from a file. Returns cleaned bytes (base64), "
            "an actions/stats report, and residual-risk flags. Use on content the "
            "user owns or is authorized to process."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Base64-encoded file bytes",
                },
                "name": {"type": "string", "description": "Original filename"},
                "options": {
                    "type": "object",
                    "description": "Optional clean flags, e.g. nfkc, aggressive_homoglyphs",
                },
            },
            "required": ["content", "name"],
        },
    },
]

ALLOWED_CLEAN_OPTIONS = frozenset(
    {
        "nfkc",
        "aggressive_homoglyphs",
        "keep_non_ai_metadata",
        "also_layer_a_text",
        "remove_pixel",
        "strip_all_metadata",
        "detect_before",
        "detect_after",
        "dsp",
        "scrub_visible",
        "corner",
    }
)


def _http_json(path: str, body: dict | None = None, timeout: float = 10.0) -> dict:
    if not SERVICE_URL.startswith(("http://", "https://")):
        raise RuntimeError(f"WATERMARKS_SERVER_URL must be http(s): {SERVICE_URL}")
    url = SERVICE_URL + path
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    data = None if body is None else json.dumps(body).encode("utf-8")
    # S310: scheme is validated just above (http/https only).
    req = urllib.request.Request(url, data=data, headers=headers, method="GET" if body is None else "POST")  # noqa: S310
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        raise RuntimeError(f"service {path} returned {e.code}: {detail}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"cannot reach service at {SERVICE_URL}: {e.reason}") from e


def _spawn_service(log_path: Path) -> None:
    """Start server.py detached, logging to a temp file."""
    kwargs: dict = {"stdout": log_path.open("ab"), "stderr": subprocess.STDOUT}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
    subprocess.Popen(
        [sys.executable, str(SERVER_SCRIPT)],
        close_fds=True,
        **kwargs,
    )


def ensure_service(timeout: float = 20.0) -> dict:
    """Return health when the service is up, starting it if needed.

    The service is only spawned once and only when nothing listens on the
    default port; a manually started service is reused as-is.
    """
    for attempt in range(int(timeout / 0.5)):
        try:
            return _http_json("/health", timeout=2.0)
        except RuntimeError:
            if attempt == 0:
                _spawn_service(
                    Path(os.environ.get("TMPDIR", os.environ.get("TEMP", Path.home())))
                    / "k-removemark-mcp-server.log"
                )
            time.sleep(0.5)
    raise RuntimeError(f"service at {SERVICE_URL} did not become healthy within {timeout}s")


def _tool_result(payload: dict, is_error: bool = False) -> dict:
    return {
        "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False, indent=2)}],
        "isError": is_error,
    }


def _call_get_health(_args: dict) -> dict:
    return ensure_service()


def _call_detect_text(args: dict) -> dict:
    text = args.get("text", "")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("detect_text requires a non-empty 'text'")
    return _http_json(
        "/detect",
        {"file": base64.b64encode(text.encode("utf-8")).decode("ascii"), "name": "stdin.txt"},
    )


def _call_inspect(args: dict) -> dict:
    content = args.get("content", "")
    name = args.get("name", "")
    if not content or not name:
        raise ValueError("inspect requires 'content' (base64) and 'name'")
    return _http_json("/inspect", {"file": content, "name": name})


def _call_clean(args: dict) -> dict:
    content = args.get("content", "")
    name = args.get("name", "")
    if not content or not name:
        raise ValueError("clean requires 'content' (base64) and 'name'")
    options = args.get("options") or {}
    unknown = set(options) - ALLOWED_CLEAN_OPTIONS
    if unknown:
        raise ValueError(f"unknown clean option(s): {sorted(unknown)}")
    return _http_json("/clean", {"file": content, "name": name, "options": options})


_TOOL_HANDLERS = {
    "get_health": _call_get_health,
    "detect_text": _call_detect_text,
    "inspect": _call_inspect,
    "clean": _call_clean,
}


def handle_message(msg: dict) -> dict | None:
    """Process one JSON-RPC message; return the reply or None for notifications."""
    method = msg.get("method")
    msg_id = msg.get("id")

    if method == "initialize":
        requested = msg.get("params", {}).get("protocolVersion")
        version = requested if requested in _KNOWN_VERSIONS else DEFAULT_PROTOCOL_VERSION
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": version,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "k-removemark-mcp", "version": VERSION},
            },
        }
    if method in ("notifications/initialized",):
        return None
    if method == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = msg.get("params") or {}
        name = params.get("name")
        args = params.get("arguments") or {}
        handler = _TOOL_HANDLERS.get(name)
        if handler is None:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": _tool_result({"error": f"unknown tool: {name}"}, is_error=True),
            }
        try:
            result = handler(args)
        except Exception as e:  # surfaced to the client as an error, not a crash
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": _tool_result({"error": str(e)}, is_error=True),
            }
        return {"jsonrpc": "2.0", "id": msg_id, "result": _tool_result(result)}
    # Unknown method: respond with an empty result so the client never blocks.
    return {"jsonrpc": "2.0", "id": msg_id, "result": {}}


def serve_stdio() -> int:
    """Read newline-delimited JSON-RPC messages from stdin until EOF."""
    for raw_line in sys.stdin:
        payload = raw_line.strip()
        if not payload:
            continue
        try:
            msg = json.loads(payload)
        except json.JSONDecodeError:
            continue
        reply = handle_message(msg)
        if reply is not None:
            sys.stdout.write(json.dumps(reply) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(serve_stdio())
