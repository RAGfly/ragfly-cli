"""`ragfly login` shows the active group and workspace from the public session, never from the internal login payload."""
from click.testing import CliRunner

from ragfly_cli import cloud_commands
from ragfly_cli.cli import app


def test_login_summary_reads_the_public_session(monkeypatch):
    internal = {"access_token": "jwt.a.b", "grupo_activo": "OLD-G", "entidad_activa": "OLD-E"}
    monkeypatch.setattr(cloud_commands, "login", lambda email, password: internal)
    calls = []

    def fake_request(method, path, params=None, body=None, token=None, timeout=None):
        calls.append((method, path, token))
        return {"active_group": "G1", "active_workspace": "W1"}

    monkeypatch.setattr(cloud_commands, "cloud_request", fake_request)
    result = CliRunner().invoke(app, ["login", "--email", "a@b.c", "--password-stdin"], input="pw\n")
    assert result.exit_code == 0, result.output
    assert calls == [("GET", "/v1/session", "jwt.a.b")]
    assert "Active workspace:  W1" in result.output and "Active group:      G1" in result.output
    assert "OLD-" not in result.output


def test_login_summary_survives_an_unreachable_session(monkeypatch):
    monkeypatch.setattr(cloud_commands, "login", lambda email, password: {"access_token": "jwt.a.b"})

    def failing(*args, **kwargs):
        raise cloud_commands.CloudError("down", exit_code=2)

    monkeypatch.setattr(cloud_commands, "cloud_request", failing)
    result = CliRunner().invoke(app, ["login", "--email", "a@b.c", "--password-stdin"], input="pw\n")
    assert result.exit_code == 0, result.output
    assert "Active workspace:  —" in result.output
