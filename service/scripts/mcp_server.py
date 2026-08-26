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
MAX_LOG_BYTES = 5 * 1024 * 1024  # rotate the service log past 5 MB

_KNOWN_VERSIONS = ("2024-11-05", "2025-03-26", "2025-06-18")
DEFAULT_PROTOCOL_VERSION = "2025-06-18"

TOOLS = [
    {
        "name": "get_health",
        "description": "Verifica que el servicio k-removemark esté activo y reporta su versión.",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "detect_text",
        "description": (
            "Ejecuta detectores de marcas de agua en texto: marcas estadísticas KGW/SynthID "
            "(con clave), heurística de estilometría y señales de vendor cuando estén disponibles. "
            "Los detectores que necesitan clave reportan no disponible en vez de adivinar."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string", "description": "Texto a escanear"}},
            "required": ["text"],
        },
    },
    {
        "name": "inspect",
        "description": (
            "Inspecciona un archivo (texto, imagen, contenedor, audio/video) en busca de "
            "marcas de procedencia de IA: Unicode invisible, metadatos C2PA/EXIF/XMP/IPTC, "
            "marcas visibles."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Bytes del archivo codificados en base64",
                },
                "name": {
                    "type": "string",
                    "description": "Nombre original del archivo; la extensión define el formato",
                },
            },
            "required": ["content", "name"],
        },
    },
    {
        "name": "clean",
        "description": (
            "Limpia marcas de procedencia de IA de un archivo. Devuelve los bytes limpios "
            "(base64), un informe de acciones/estadísticas y flags de riesgo residual. "
            "Usar solo en contenido propio o autorizado."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Bytes del archivo codificados en base64",
                },
                "name": {"type": "string", "description": "Nombre original del archivo"},
                "options": {
                    "type": "object",
                    "description": "Opciones de limpieza, ej: nfkc, aggressive_homoglyphs",
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


class ServiceHTTPStatus(RuntimeError):
    """The service answered with a non-2xx status (alive but unhappy)."""


def _http_json(path: str, body: dict | None = None, timeout: float = 10.0) -> dict:
    if not SERVICE_URL.startswith(("http://", "https://")):
        raise ValueError(f"WATERMARKS_SERVER_URL must be http(s): {SERVICE_URL}")
    url = SERVICE_URL + path
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    data = None if body is None else json.dumps(body).encode("utf-8")
    # S310: scheme is validated just above (http/https only).
    req = urllib.request.Request(  # noqa: S310
        url, data=data, headers=headers, method="GET" if body is None else "POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        raise ServiceHTTPStatus(f"service {path} returned {e.code}: {detail}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"cannot reach service at {SERVICE_URL}: {e.reason}") from e


def _spawn_service(log_path: Path) -> None:
    """Start server.py detached, logging to a temp file."""
    kwargs: dict = {"stderr": subprocess.STDOUT}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
    try:
        # Log rotation: a runaway service loop must not grow the log forever.
        if log_path.exists() and log_path.stat().st_size > MAX_LOG_BYTES:
            log_path.unlink()
    except OSError:
        pass
    with log_path.open("ab") as log_f:
        kwargs["stdout"] = log_f
        subprocess.Popen(
            [sys.executable, str(SERVER_SCRIPT)],
            close_fds=True,
            **kwargs,
        )


def _service_log_path() -> Path:
    return (
        Path(os.environ.get("TMPDIR", os.environ.get("TEMP", Path.home())))
        / "k-removemark-mcp-server.log"
    )


def _foreign_port_error() -> RuntimeError:
    from urllib.parse import urlparse

    port = urlparse(SERVICE_URL).port or (443 if SERVICE_URL.startswith("https") else 80)
    return RuntimeError(
        f"el puerto {port} ya está ocupado por otra aplicación que no es k-removemark. "
        "Cerrá ese programa o elegí otro puerto exportando WATERMARKS_SERVER_PORT "
        "(y apuntá WATERMARKS_SERVER_URL al nuevo puerto)."
    )


def ensure_service(timeout: float = 20.0) -> dict:
    """Return health when the service is up, starting it if needed.

    The service is only spawned once and only when nothing listens on the
    port; a manually started service is reused as-is. If some other HTTP
    application owns the port (it answers /health but is not k-removemark),
    fail fast with an actionable message instead of burning the timeout.
    """
    spawned = False
    deadline = time.monotonic() + timeout
    while True:
        try:
            health = _http_json("/health", timeout=2.0)
        except ServiceHTTPStatus:
            # Alive but not ours: k-removemark always answers /health 200.
            raise _foreign_port_error() from None
        except RuntimeError:
            pass  # nothing listening yet — fall through to spawn/retry
        else:
            if isinstance(health, dict) and health.get("ok"):
                return health
            raise _foreign_port_error()
        if not spawned:
            _spawn_service(_service_log_path())
            spawned = True
        if time.monotonic() >= deadline:
            break
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
        except (json.JSONDecodeError, TypeError) as exc:
            sys.stdout.write(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {"code": -32700, "message": f"Parse error: {exc}"},
                    }
                )
                + "\n"
            )
            sys.stdout.flush()
            continue
        if not isinstance(msg, dict):
            sys.stdout.write(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {"code": -32600, "message": "Invalid Request: expected object"},
                    }
                )
                + "\n"
            )
            sys.stdout.flush()
            continue
        reply = handle_message(msg)
        if reply is not None:
            sys.stdout.write(json.dumps(reply) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(serve_stdio())
