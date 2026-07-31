import json

from click.testing import CliRunner

from ragfly_cli import cloud_commands
from ragfly_cli.cli import app


def test_cloud_agent_context_json(monkeypatch):
    monkeypatch.setattr(
        cloud_commands,
        "cloud_get",
        lambda path, params=None: {
            "function_profile": params["function_profile"],
            "system_prompt_hash": "abc",
            "tools": [],
        },
    )

    result = CliRunner().invoke(
        app,
        ["cloud", "agent", "context", "--profile", "chat_soporte", "-o", "json"],
    )

    assert result.exit_code == 0
    assert json.loads(result.output)["function_profile"] == "chat_soporte"


def test_cloud_agent_tool_posts_arguments(monkeypatch):
    called = {}

    def fake_post(path, body=None, params=None):
        called.update({"path": path, "body": body, "params": params})
        return {"ok": True}

    monkeypatch.setattr(cloud_commands, "cloud_post", fake_post)
    result = CliRunner().invoke(
        app,
        [
            "cloud", "agent", "tool", "leer_md",
            "--profile", "chat_soporte",
            "--arguments-json", '{"codigo":"RAGFLY_ROOT"}',
            "-o", "json",
        ],
    )

    assert result.exit_code == 0
    assert called == {
        "path": "/agent/tools/leer_md",
        "body": {"arguments": {"codigo": "RAGFLY_ROOT"}},
        "params": {"function_profile": "chat_soporte"},
    }
