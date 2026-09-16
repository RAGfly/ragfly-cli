"""
Cloud commands — HTTP client for the RAGfly REST API.

Public API:
    obtener_token()                       → str   (API key or session JWT)
    cloud_request(method, path, ...)      → Any   (authenticated request)
    cloud_get / cloud_post / cloud_delete → Any   (shortcuts)
    CLOUD_URL                             → str

Helpers:
    CloudError — network/API error with exit_code
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx

from . import keyring_store

# ── Constants ────────────────────────────────────────────────────────────────

CLOUD_URL = os.environ.get("RAGFLY_BASE_URL", "https://api.ragfly.ai").rstrip("/")
LEGACY_CREDENTIALS_PATH = Path.home() / ".ragfly" / "credentials.json"
CLIENT_HEADER = {"X-RAGfly-Client": "cli"}
# RAGFLY_API_KEY is the documented name; RAGFLY_TOKEN is kept because CI
# pipelines already export it.
TOKEN_ENV_VARS = ("RAGFLY_API_KEY", "RAGFLY_TOKEN")


# ── Errors ───────────────────────────────────────────────────────────────────

class CloudError(Exception):
    """Network or cloud API error."""

    def __init__(self, mensaje: str, exit_code: int = 2):
        super().__init__(mensaje)
        self.exit_code = exit_code


# ── Auth ─────────────────────────────────────────────────────────────────────

def _migrar_legacy_json_a_keyring() -> str | None:
    """Move a v1.0.x ~/.ragfly/credentials.json session into the OS keyring."""
    if not LEGACY_CREDENTIALS_PATH.exists():
        return None
    try:
        creds = json.loads(LEGACY_CREDENTIALS_PATH.read_text())
        token = creds.get("access_token", "")
        if token:
            keyring_store.guardar(token, creds.get("email", ""))
        LEGACY_CREDENTIALS_PATH.unlink()
        return token or None
    except Exception:
        return None


def obtener_token() -> str:
    """Resolve the credential, in order of precedence:

    1. ``RAGFLY_API_KEY`` (or ``RAGFLY_TOKEN``) — an API key (``rf_...``), for
       CI and agents without an OS keyring. It only reaches ``/v1``.
    2. The session JWT stored in the OS keyring by ``ragfly login``.
    """
    for name in TOKEN_ENV_VARS:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    token = keyring_store.leer_token() or _migrar_legacy_json_a_keyring()
    if not token:
        raise CloudError("Not signed in. Run `ragfly login` or export RAGFLY_API_KEY.", exit_code=1)
    return token


def guardar_credenciales(token: str, email: str, expires_in: int = 3600) -> None:
    """Store the JWT in the OS keyring (`expires_in` is ignored)."""
    keyring_store.guardar(token, email)


def borrar_credenciales() -> None:
    """Remove the stored session (logout), including the legacy JSON file."""
    keyring_store.borrar()
    try:
        if LEGACY_CREDENTIALS_PATH.exists():
            LEGACY_CREDENTIALS_PATH.unlink()
    except Exception:
        pass


def hay_sesion_guardada() -> bool:
    """True if `ragfly login` left a session in the keyring (not validated)."""
    return bool(keyring_store.leer_token() or LEGACY_CREDENTIALS_PATH.exists())


# ── HTTP ─────────────────────────────────────────────────────────────────────

def _headers(token: str | None = None) -> dict[str, str]:
    """Standard headers: credential, client version, client surface and the
    local active group override (if any)."""
    from ._http import default_headers

    return {**default_headers(token=token or obtener_token(), content_type=True), **CLIENT_HEADER}


def cloud_request(method: str, path: str, params: dict | None = None, body: Any = None,
                  token: str | None = None, timeout: int | None = None) -> Any:
    """Authenticated request against CLOUD_URL/path. Returns parsed JSON."""
    from ragfly_cli.oop import CloudHttpClient
    return CloudHttpClient()._request(method, path, params=params, body=body, token=token, timeout=timeout)


def cloud_get(path: str, params: dict | None = None, token: str | None = None, timeout: int = 30) -> Any:
    return cloud_request("GET", path, params=params, token=token, timeout=timeout)


def cloud_post(path: str, body: dict | None = None, params: dict | None = None,
               token: str | None = None, timeout: int = 60) -> Any:
    return cloud_request("POST", path, params=params, body=body, token=token, timeout=timeout)


def cloud_delete(path: str, params: dict | None = None, token: str | None = None, timeout: int = 30) -> Any:
    return cloud_request("DELETE", path, params=params, token=token, timeout=timeout)


def _mensaje_de_error(response: httpx.Response) -> str:
    """The server's public message: `/v1` errors carry `message`; routes that
    refuse an API key carry `mensaje_usuario`; FastAPI carries `detail`."""
    try:
        payload = response.json()
    except Exception:
        return response.text[:200] or f"HTTP {response.status_code}"
    if isinstance(payload, dict):
        detail = payload.get("detail")
        if isinstance(detail, dict):
            payload = {**payload, **detail}
        mensaje = payload.get("message") or payload.get("mensaje_usuario")
        if mensaje:
            detalles = payload.get("details")
            return f"{mensaje} {json.dumps(detalles, ensure_ascii=False)}" if detalles else str(mensaje)
        if isinstance(detail, str):
            return detail
        if isinstance(detail, list):
            return "; ".join(str(e.get("msg", e)) if isinstance(e, dict) else str(e) for e in detail)
    return str(payload)[:200]


def _manejar_http_error(e: httpx.HTTPStatusError) -> None:
    status = e.response.status_code
    mensaje = _mensaje_de_error(e.response)
    if status == 401:
        raise CloudError(f"Not authenticated: {mensaje}. Run `ragfly login` or check RAGFLY_API_KEY.", exit_code=1)
    if status == 403:
        raise CloudError(f"Forbidden: {mensaje}", exit_code=1)
    if status == 404:
        raise CloudError(f"Not found: {mensaje}", exit_code=1)
    if status in (400, 409, 422):
        raise CloudError(f"Rejected ({status}): {mensaje}", exit_code=1)
    raise CloudError(f"Error {status}: {mensaje}", exit_code=2)


# ── Login ────────────────────────────────────────────────────────────────────

def login(email: str, password: str) -> dict:
    """Authenticate a person against /auth/login and store the session."""
    try:
        r = httpx.post(f"{CLOUD_URL}/auth/login", json={"email": email, "password": password},
                       headers=CLIENT_HEADER, timeout=30)
        r.raise_for_status()
        data = r.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code in (401, 403):
            raise CloudError("Wrong email or password.", exit_code=1)
        _manejar_http_error(e)
    except httpx.RequestError as e:
        raise CloudError(f"Could not connect to the server: {e}", exit_code=2)

    token = data.get("access_token") or data.get("token", "")
    if not token:
        raise CloudError("The server did not return a token.", exit_code=2)
    try:
        guardar_credenciales(token, email, data.get("expires_in", 3600))
    except keyring_store.KeyringStoreError:
        raise CloudError(
            "Signed in, but the session could not be stored: the OS keyring is not "
            "available (typical in headless/CI).\n"
            "  Use an API key instead: export RAGFLY_API_KEY=rf_...\n"
            "  (create it at app.ragfly.ai → API Keys).",
            exit_code=1,
        )
    return data
