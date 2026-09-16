"""The CLI talks to /v1 only, in English, and reports server refusals cleanly."""
import json

import httpx
import pytest
from click.testing import CliRunner

from ragfly_cli import cloud_commands
from ragfly_cli.cli import app


@pytest.fixture
def wire(monkeypatch):
    """Capture every request the CLI sends and answer with `wire.reply`."""
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


def test_every_cloud_call_goes_to_v1_with_the_cli_surface(wire):
    wire.reply = httpx.Response(200, json={"documents": [{"code": "D1", "name": "Contract", "status": "VECTORIZED"}], "total": 1})
    result = run("cloud", "document", "list", "--status", "VECTORIZED", "-o", "id")
    assert result.exit_code == 0, result.output
    assert result.output.strip() == "D1"
    [call] = wire.calls
    assert call["url"].endswith("/v1/documents")
    assert call["params"] == {"status": "VECTORIZED", "limit": 20, "page": 1}
    assert call["headers"]["Authorization"] == "Bearer rf_test"
    assert call["headers"]["X-RAGfly-Client"] == "cli"


def test_agent_context_and_tool(wire):
    wire.reply = httpx.Response(200, json={"function_profile": "support_chat", "system_prompt_hash": "abc", "tools": []})
    result = run("cloud", "agent", "context", "--profile", "support_chat")
    assert result.exit_code == 0
    assert json.loads(result.output)["function_profile"] == "support_chat"
    assert wire.calls[0]["params"] == {"function_profile": "support_chat"}

    wire.reply = httpx.Response(200, json={"ok": True})
    result = run("cloud", "agent", "tool", "read_md", "--arguments-json", '{"code":"RAGFLY_ROOT"}')
    assert result.exit_code == 0
    assert wire.calls[1]["url"].endswith("/v1/agent/tools/read_md")
    assert wire.calls[1]["json"] == {"arguments": {"code": "RAGFLY_ROOT"}, "function_profile": "user_chat"}


def test_operation_run_needs_confirm_for_write_confirm(wire):
    wire.reply = httpx.Response(200, json={"code": "document_types.delete", "kind": "write_confirm", "executed": False,
                                           "confirm_required": True, "preview": {"input": {"code": "T"}}})
    result = run("cloud", "operation", "run", "document_types.delete", "--input-json", '{"code": "T"}')
    assert result.exit_code == 0
    assert "NOT executed" in result.output
    assert wire.calls[0]["url"].endswith("/v1/operations/document_types.delete:execute")
    assert wire.calls[0]["json"] == {"input": {"code": "T"}, "confirm": False}

    wire.reply = httpx.Response(200, json={"code": "document_types.delete", "executed": True, "result": {}})
    result = run("cloud", "operation", "run", "document_types.delete", "--input-json", '{"code": "T"}', "--confirm")
    assert result.exit_code == 0
    assert wire.calls[1]["json"] == {"input": {"code": "T"}, "confirm": True}


def test_operation_input_from_file(wire, tmp_path):
    source = tmp_path / "input.json"
    source.write_text('{"code": "T", "name": "Invoices"}')
    wire.reply = httpx.Response(200, json={"executed": True, "result": {}})
    assert run("cloud", "operation", "run", "document_types.update", "--input-json", f"@{source}").exit_code == 0
    assert wire.calls[0]["json"]["input"] == {"code": "T", "name": "Invoices"}


def test_api_key_management_with_a_key_shows_the_server_message_without_traceback(wire):
    wire.reply = httpx.Response(403, json={
        "mensaje_usuario": "This operation requires a signed-in person: an API key cannot manage API keys.",
        "codigo_proceso": "ERR-SIN-REGISTRO",
    })
    result = run("cloud", "api-key", "list")
    assert result.exit_code == 1
    assert "requires a signed-in person" in result.output
    assert "Traceback" not in result.output


def test_public_validation_errors_show_details(wire):
    wire.reply = httpx.Response(422, json={"code": "VALIDATION_ERROR", "message": "The request could not be validated.",
                                           "details": {"unknown_fields": ["nombre"]}})
    result = run("cloud", "operation", "run", "document_types.update", "--input-json", '{"nombre": "x"}')
    assert result.exit_code == 1
    assert "unknown_fields" in result.output


def test_there_are_no_spanish_command_aliases():
    spanish = {"listar", "ver", "arcos", "buscar", "preguntar", "cambiar", "limpiar", "crear", "revocar",
               "ejecutar", "ejecuciones", "catalogo", "grupo", "documento", "espacio", "cola", "habilidad",
               "agente", "contexto"}

    def names(group):
        for name, command in group.commands.items():
            yield name
            if hasattr(command, "commands"):
                yield from names(command)

    assert not spanish & set(names(app))


def test_the_legacy_token_variable_still_works(monkeypatch):
    monkeypatch.delenv("RAGFLY_API_KEY", raising=False)
    monkeypatch.setenv("RAGFLY_TOKEN", "rf_legacy")
    assert cloud_commands.obtener_token() == "rf_legacy"
