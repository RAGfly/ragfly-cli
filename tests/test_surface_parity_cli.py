"""The CLI exposes the same /v1 operations as the SDKs and MCP: ask mode, filtered search, catalogs, spaces."""
import json

import httpx
import pytest
from click.testing import CliRunner

from ragfly_cli.cli import app


@pytest.fixture
def wire(monkeypatch):
    monkeypatch.setenv("RAGFLY_API_KEY", "rf_test")
    monkeypatch.delenv("RAGFLY_TOKEN", raising=False)
    monkeypatch.setattr("ragfly_cli.config.get_config", lambda: type("C", (), {"codigo_grupo": ""})())

    class Wire:
        reply = httpx.Response(200, json={})
        calls: list = []

    def fake_request(method, url, **kwargs):
        Wire.calls.append({"method": method, "url": url, **kwargs})
        response = Wire.reply
        response.request = httpx.Request(method, url)
        return response

    monkeypatch.setattr(httpx, "request", fake_request)
    Wire.calls = []
    return Wire


def run(*args):
    return CliRunner().invoke(app, list(args))


def test_ask_sends_mode_only_when_given(wire):
    wire.reply = httpx.Response(200, json={"answer": "A", "conversation_id": 1})
    assert run("cloud", "chat", "ask", "how do I release the entity?", "--mode", "help").exit_code == 0
    assert wire.calls[0]["json"] == {"question": "how do I release the entity?", "function_code": "CHAT-USER", "mode": "help"}
    assert run("cloud", "chat", "ask", "hello").exit_code == 0
    assert "mode" not in wire.calls[1]["json"]
    assert run("cloud", "chat", "ask", "hello", "--mode", "support").exit_code != 0


def test_search_takes_space_and_structured_filter(wire):
    wire.reply = httpx.Response(200, json={"documents": []})
    flt = {"document_types": ["TDOC_cartola"], "attributes": [{"field": "language", "operator": "EQ", "value": "es"}]}
    result = run("cloud", "search", "cartolas", "--space", "12", "--filter", json.dumps(flt), "-o", "json")
    assert result.exit_code == 0, result.output
    body = wire.calls[0]["json"]
    assert wire.calls[0]["url"].endswith("/v1/documents/search")
    assert body["query"] == "cartolas" and body["space_id"] == 12 and body["filter"] == flt
    assert run("cloud", "search", "x", "--filter", "[1]").exit_code != 0  # a filter is a JSON object


def test_catalog_commands_call_the_public_catalog_routes(wire):
    wire.reply = httpx.Response(200, json={"document_types": [{"code": "T1", "name": "Statement", "parent_code": None, "document_count": 3}]})
    assert run("cloud", "document-type", "list", "--entity", "E1", "-o", "id").output.strip() == "T1"
    assert wire.calls[0]["url"].endswith("/v1/catalog/document-types") and wire.calls[0]["params"] == {"entity_code": "E1"}
    wire.reply = httpx.Response(200, json={"characteristics": []})
    assert run("cloud", "characteristic", "list", "--document-type", "T1", "--document-type", "T2", "-o", "json").exit_code == 0
    assert wire.calls[1]["url"].endswith("/v1/catalog/characteristics")
    assert wire.calls[1]["params"] == {"document_types": "T1,T2"}


def test_space_commands_cover_compose_read_refresh_and_promote(wire):
    wire.reply = httpx.Response(200, json={"space_id": 9})
    assert run("cloud", "space", "compose", "difference", "1", "2", "--name", "N", "--type", "SPACE").exit_code == 0
    assert wire.calls[0]["url"].endswith("/v1/spaces/compose")
    assert wire.calls[0]["json"] == {"operation": "difference", "space_id_a": 1, "space_id_b": 2, "name": "N", "space_type": "SPACE"}
    assert run("cloud", "space", "read", "9", "--resolution", "chunks", "--query", "q", "--limit", "5").exit_code == 0
    assert wire.calls[1]["url"].endswith("/v1/spaces/9/read")
    assert wire.calls[1]["json"] == {"resolution": "chunks", "query": "q", "limit": 5}
    assert run("cloud", "space", "refresh", "9").exit_code == 0 and wire.calls[2]["url"].endswith("/v1/spaces/9/refresh")
    assert run("cloud", "space", "promote", "9").exit_code == 0 and wire.calls[3]["url"].endswith("/v1/spaces/9/promote")
