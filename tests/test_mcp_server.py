"""Tests for the MCP server (JSON-RPC 2.0 over stdio, stdlib only)."""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "service", "scripts"))

import mcp_server


def _msg(method: str, msg_id=1, params=None) -> dict:
    m = {"jsonrpc": "2.0", "id": msg_id, "method": method}
    if params is not None:
        m["params"] = params
    return m


def test_initialize_handshake_echoes_known_version():
    reply = mcp_server.handle_message(
        _msg("initialize", params={"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {}})
    )
    assert reply["id"] == 1
    assert reply["result"]["protocolVersion"] == "2025-03-26"
    assert reply["result"]["serverInfo"]["name"] == "k-removemark-mcp"
    assert reply["result"]["capabilities"]["tools"] == {}


def test_initialize_falls_back_to_default_version():
    reply = mcp_server.handle_message(_msg("initialize", params={"protocolVersion": "1999-01-01"}))
    assert reply["result"]["protocolVersion"] == mcp_server.DEFAULT_PROTOCOL_VERSION


def test_initialized_notification_returns_none():
    assert mcp_server.handle_message(_msg("notifications/initialized")) is None


def test_ping_returns_empty_result():
    reply = mcp_server.handle_message(_msg("ping"))
    assert reply["result"] == {}


def test_tools_list_exposes_expected_tools():
    reply = mcp_server.handle_message(_msg("tools/list"))
    names = {t["name"] for t in reply["result"]["tools"]}
    assert names == {"get_health", "detect_text", "inspect", "clean"}


def test_unknown_method_returns_empty_result():
    reply = mcp_server.handle_message(_msg("something/else"))
    assert reply["result"] == {}


def test_detect_text_proxies_text_as_base64(monkeypatch):
    import base64

    seen: dict = {}

    def fake_http_json(path, body=None, timeout=10.0):
        seen["path"] = path
        seen["body"] = body
        return {"ok": True, "detections": []}

    monkeypatch.setattr(mcp_server, "_http_json", fake_http_json)
    reply = mcp_server.handle_message(_msg("tools/call", params={"name": "detect_text", "arguments": {"text": "Hello \u200b"}}))
    assert not reply["result"]["isError"]
    assert seen["path"] == "/detect"
    assert seen["body"]["name"] == "stdin.txt"
    decoded = base64.b64decode(seen["body"]["file"]).decode("utf-8")
    assert decoded == "Hello \u200b"


def test_detect_text_requires_text(monkeypatch):
    def fake_http_json(path, body=None, timeout=10.0):
        raise AssertionError("should not reach the service")

    monkeypatch.setattr(mcp_server, "_http_json", fake_http_json)
    reply = mcp_server.handle_message(_msg("tools/call", params={"name": "detect_text", "arguments": {"text": ""}}))
    assert reply["result"]["isError"]
    assert "non-empty" in reply["result"]["content"][0]["text"]


def test_clean_rejects_unknown_option(monkeypatch):
    def fake_http_json(path, body=None, timeout=10.0):
        raise AssertionError("should not reach the service")

    monkeypatch.setattr(mcp_server, "_http_json", fake_http_json)
    reply = mcp_server.handle_message(
        _msg("tools/call", params={"name": "clean", "arguments": {"content": "aGk=", "name": "a.txt", "options": {"nope": True}}})
    )
    assert reply["result"]["isError"]
    assert "nope" in reply["result"]["content"][0]["text"]


def test_tool_error_is_surfaced_as_iserror(monkeypatch):
    def boom(path, body=None, timeout=10.0):
        raise RuntimeError("service /detect returned 500")

    monkeypatch.setattr(mcp_server, "_http_json", boom)
    reply = mcp_server.handle_message(_msg("tools/call", params={"name": "inspect", "arguments": {"content": "aGk=", "name": "x.bin"}}))
    assert reply["result"]["isError"]
    assert "500" in reply["result"]["content"][0]["text"]


def test_serve_stdio_roundtrip(monkeypatch, capsys):
    import io

    fake_in = io.StringIO(
        json.dumps(_msg("initialize", params={"protocolVersion": "2024-11-05"}))
        + "\n"
        + json.dumps(_msg("tools/list"))
        + "\n"
    )
    monkeypatch.setattr(sys, "stdin", fake_in)
    assert mcp_server.serve_stdio() == 0
    out = capsys.readouterr().out.strip().splitlines()
    assert len(out) == 2
    assert json.loads(out[0])["result"]["protocolVersion"] == "2024-11-05"
    assert "tools" in json.loads(out[1])["result"]


def test_ensure_service_reuses_running_service(monkeypatch):
    def healthy(path, body=None, timeout=2.0):
        return {"ok": True, "version": "test"}

    monkeypatch.setattr(mcp_server, "_http_json", healthy)
    assert mcp_server.ensure_service(timeout=1.0) == {"ok": True, "version": "test"}


def test_ensure_service_spawns_and_waits(monkeypatch):
    calls = {"n": 0, "spawned": False}

    def flaky(path, body=None, timeout=2.0):
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("down")
        return {"ok": True, "version": "test"}

    def spawn(log_path):
        calls["spawned"] = True
        assert log_path.name.endswith(".log")

    monkeypatch.setattr(mcp_server, "_http_json", flaky)
    monkeypatch.setattr(mcp_server, "_spawn_service", spawn)
    assert mcp_server.ensure_service(timeout=2.0) == {"ok": True, "version": "test"}
    assert calls["spawned"]


def test_ensure_service_raises_when_never_healthy(monkeypatch):
    def down(path, body=None, timeout=2.0):
        raise RuntimeError("down")

    monkeypatch.setattr(mcp_server, "_http_json", down)
    try:
        mcp_server.ensure_service(timeout=0.6)
        raise AssertionError("expected RuntimeError")
    except RuntimeError as e:
        assert "did not become healthy" in str(e)
