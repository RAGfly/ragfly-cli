from types import SimpleNamespace

from ragfly_cli import config
from ragfly_cli._http import default_headers


def test_api_key_never_inherits_a_saved_group(monkeypatch):
    monkeypatch.setattr(config, "get_config", lambda: SimpleNamespace(codigo_grupo="OTHER-GROUP"))
    for token in ("rf_fixture", "slm_live_fixture"):
        headers = default_headers(token=token)
        assert headers["Authorization"] == f"Bearer {token}"
        assert "X-Override-Grupo" not in headers


def test_human_session_keeps_its_saved_group(monkeypatch):
    monkeypatch.setattr(config, "get_config", lambda: SimpleNamespace(codigo_grupo="MY-GROUP"))
    headers = default_headers(token="jwt.header.signature")
    assert headers["X-Override-Grupo"] == "MY-GROUP"
