"""CLI publica errores propios en inglés y conserva sus códigos de salida."""
import httpx
import pytest

from ragfly_cli import grupo_activo
from ragfly_cli.cloud_commands import CloudError
from ragfly_cli.oop.cli_command import CliCommand
from ragfly_cli.oop.http_client import CloudHttpClient


def test_archivo_de_configuracion_ausente(tmp_path, monkeypatch):
    monkeypatch.setattr(grupo_activo, '_config_path', lambda: tmp_path / 'config.env')
    with pytest.raises(FileNotFoundError, match='does not exist.*ragfly setup'):
        grupo_activo.set_grupo_activo('GROUP')


def test_error_de_conexion_es_ingles_y_conserva_codigo(monkeypatch):
    monkeypatch.setattr('ragfly_cli.oop.http_client._headers', lambda token: {})
    def fallar(*args, **kwargs):
        raise httpx.ConnectError('connection refused')
    monkeypatch.setattr(httpx, 'request', fallar)
    with pytest.raises(CloudError, match='Could not connect to the server') as exc:
        CloudHttpClient().get('/v1/test')
    assert exc.value.exit_code == 2


def test_interrupcion_y_error_inesperado_en_ingles(monkeypatch):
    comando = CliCommand()
    mensajes = []
    monkeypatch.setattr(comando, 'aviso', mensajes.append)
    monkeypatch.setattr(comando, 'error', mensajes.append)
    def interrumpir():
        raise KeyboardInterrupt
    with pytest.raises(SystemExit) as exc:
        comando.protegido(interrumpir)
    assert exc.value.code == 130 and mensajes.pop() == 'Interrupted.'
    def fallar():
        raise ValueError('technical detail')
    with pytest.raises(SystemExit) as exc:
        comando.protegido(fallar)
    assert exc.value.code == 2 and mensajes.pop() == 'Unexpected error: technical detail'
