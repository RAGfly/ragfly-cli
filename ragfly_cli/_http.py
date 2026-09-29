"""
Helpers HTTP comunes para todo el cliente.

`default_headers()` — Headers que TODA request al backend cloud debe llevar:
- `Authorization: Bearer <token>` (opcional; solo si token presente)
- `Content-Type: application/json` (opcional, para writes)
- `X-Client-Version: <__version__>` (siempre — el backend loggea y, en el
  futuro, puede rechazar versiones incompatibles si ENFORCE_CLIENT_VERSION=true)

Para usar:

    from ragfly_cli._http import default_headers
    headers = default_headers(token=jwt, content_type=True)
    httpx.post(url, headers=headers, json=...)

Notas:
- Si tu request va a un servicio que NO es el backend cloud (ej: LLM externo
  como Anthropic/Google/Ollama), NO uses esta función — usa los headers que
  pida el proveedor.
"""

from __future__ import annotations

from typing import Optional


def default_headers(
    *,
    token: Optional[str] = None,
    content_type: bool = False,
    grupo_override: Optional[str] = None,
) -> dict[str, str]:
    """Construye los headers estándar para una request al backend cloud.

    Args:
        token: JWT (sin "Bearer " prefix). Si None, no agrega Authorization.
        content_type: Si True, agrega Content-Type: application/json (writes).
        grupo_override: Override explícito del grupo activo. Si None, se lee
            de `ClienteConfig.codigo_grupo` (si está seteado).

    Returns:
        dict de headers listo para pasar a httpx.

    El header `X-Override-Grupo` solo se envía para una sesión humana. Una API
    key tiene un grupo fijo en el servidor y nunca hereda el grupo local del CLI.
    """
    from ragfly_cli import __version__ as _client_version

    headers: dict[str, str] = {"X-Client-Version": _client_version}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if content_type:
        headers["Content-Type"] = "application/json"

    # El override pertenece a la sesión humana. Enviar el grupo guardado en
    # otra sesión con una API key puede dar 403 y nunca debe cambiar su alcance.
    grupo = None
    if not (token and token.startswith(("rf_", "slm_live_"))):
        grupo = grupo_override
        if grupo is None:
            try:
                from .config import get_config
                grupo = get_config().codigo_grupo or None
            except Exception:
                grupo = None
    if grupo:
        headers["X-Override-Grupo"] = grupo

    return headers
