"""
Main RAGfly CLI — `ragfly-cli` package (the `ragfly` binary).

Every `cloud` command talks to the English REST `/v1` contract, so it works the
same with `ragfly login` (a person) and with an API key (`RAGFLY_API_KEY`).
`cloud group` and `cloud api-key` manage the signed-in person's session and
credentials: with an API key the server refuses them on purpose.

Commands:
  ragfly version | login | logout
  ragfly cloud me
  ragfly cloud group         list | switch | clear      (signed-in person only)
  ragfly cloud api-key       create | list | revoke     (signed-in person only)
  ragfly cloud document      list | show | edges
  ragfly cloud space         list | show
  ragfly cloud queue         show | runs
  ragfly cloud skill         list | show | run
  ragfly cloud catalog | function show | search | chat ask
  ragfly cloud agent         context | tool
  ragfly cloud usage
  ragfly cloud conversation  list | delete
  ragfly cloud process       list | show | update
  ragfly cloud organization  show | update | draft
  ragfly cloud operation     list | show | run

Local filesystem operations (`ragfly local scan/sync/daemon`) do NOT live in
this package: they ship with RAGfly Desktop.

Global flag: `-v/--verbose` (method+URL+status of each request, to stderr),
placed before the subcommand: `ragfly -v cloud document list`.
"""

import json
import sys
from pathlib import Path
from urllib.parse import quote

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import __version__, _runtime

console = Console()
err_console = Console(stderr=True)

OUTPUT_TABLE = click.Choice(["table", "json"])
OUTPUT_LIST = click.Choice(["table", "json", "id"])


# ── Output helpers ───────────────────────────────────────────────────────────
# Rich interprets `[...]` as markup and wraps to the terminal width: both break
# JSON when piped to `jq`. Machine-readable output goes straight to stdout.

def _emit_json(obj) -> None:
    click.echo(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


def _emit_ids(items, key: str) -> None:
    for item in items or []:
        value = item.get(key) if isinstance(item, dict) else item
        if value not in (None, ""):
            click.echo(str(value))


def _cell(value, width: int = 60) -> str:
    if value is None or value == "":
        return "—"
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False, default=str)
    return str(value)[:width]


def _table(title: str, rows, columns: list[tuple[str, str]]) -> None:
    table = Table(title=title, border_style="dim")
    for header, _ in columns:
        table.add_column(header)
    for row in rows or []:
        table.add_row(*[_cell(row.get(key)) if isinstance(row, dict) else _cell(row) for _, key in columns])
    console.print()
    console.print(table)
    console.print()


def _fields(title: str, data: dict, fields: list[tuple[str, str]]) -> None:
    table = Table(show_header=False, border_style="dim", title=title)
    table.add_column("Field", style="bold")
    table.add_column("Value")
    for label, key in fields:
        table.add_row(label, _cell((data or {}).get(key), 120))
    console.print()
    console.print(table)
    console.print()


def _show(data, output: str, title: str, fields: list[tuple[str, str]]) -> None:
    if output == "json":
        _emit_json(data)
    else:
        _fields(title, data, fields)


def _list(data, output: str, *, key: str, id_key: str, title: str, columns: list[tuple[str, str]]) -> list:
    items = (data or {}).get(key, []) if isinstance(data, dict) else (data or [])
    if output == "json":
        _emit_json(data)
    elif output == "id":
        _emit_ids(items, id_key)
    else:
        _table(title, items, columns)
        total = data.get("total") if isinstance(data, dict) else None
        if total is not None:
            console.print(f"  [dim]Total: {total}[/dim]")
    return items


def _json_argument(value: str, option: str) -> dict:
    """Parse a JSON object given inline, as `@file` or as `-` (stdin)."""
    if value == "-":
        value = sys.stdin.read()
    elif value.startswith("@"):
        value = Path(value[1:]).expanduser().read_text(encoding="utf-8")
    try:
        parsed = json.loads(value or "{}")
    except json.JSONDecodeError as exc:
        raise click.UsageError(f"{option} is not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise click.UsageError(f"{option} must be a JSON object")
    return parsed


def _v1(method: str, path: str, *, params: dict | None = None, body=None):
    """Call a `/v1` route with uniform error handling (exits on failure)."""
    from .cloud_commands import cloud_request
    from .oop import CliCommand

    clean = {k: v for k, v in (params or {}).items() if v is not None} or None
    return CliCommand().protegido(cloud_request, method, path, params=clean, body=body)


def _segment(value) -> str:
    return quote(str(value), safe="")


# ════════════════════════════════════════════════════════════════════════════
# Root group, login and logout
# ════════════════════════════════════════════════════════════════════════════

@click.group()
@click.option("-v", "--verbose", is_flag=True, help="Show method+URL+status of each request (to stderr).")
def app(verbose: bool):
    """RAGfly — `ragfly-cli` package (the `ragfly` binary)."""
    if verbose:
        _runtime.set_verbose(True)


@app.command()
@click.option("--email", "-e", default=None, help="Email (for non-interactive use)")
@click.option("--password-stdin", is_flag=True, help="Read the password from stdin")
def login(email: str | None, password_stdin: bool):
    """Authenticate a person against the cloud and store the session."""
    from .cloud_commands import CloudError, login as _login

    console.print()
    if not email:
        email = click.prompt("  Email")
    password = sys.stdin.readline().rstrip("\n") if password_stdin else click.prompt("  Password", hide_input=True)

    console.print()
    console.print("[dim]  Connecting...[/dim]", end="")
    try:
        data = _login(email, password)
    except CloudError as e:
        console.print()
        err_console.print(f"[red]✗ {e}[/red]")
        raise SystemExit(e.exit_code)

    console.print()
    console.print(f"[green]✓ Logged in as[/green] {email}")
    usuario = data.get("usuario", {}) if isinstance(data.get("usuario"), dict) else {}
    console.print(f"  Active group:  {data.get('grupo_activo') or usuario.get('grupo_por_defecto') or '—'}")
    console.print(f"  Active entity: {data.get('entidad_activa') or usuario.get('entidad_por_defecto') or '—'}")
    console.print("  Session stored in [dim]OS keyring[/dim]")
    console.print()


@app.command()
def logout():
    """Log out (removes the session from the keyring)."""
    from .cloud_commands import borrar_credenciales, hay_sesion_guardada

    if hay_sesion_guardada():
        borrar_credenciales()
        console.print("[green]✓ Logged out.[/green]")
    else:
        console.print("[yellow]No active session.[/yellow]")


@app.command()
def version():
    """Show the client version and warn if an update is available."""
    console.print(f"[bold blue]RAGfly[/bold blue] CLI v{__version__}")
    try:
        from .version_check import chequear_actualizacion
        aviso = chequear_actualizacion()
        if aviso:
            console.print(f"[yellow]{aviso}[/yellow]")
    except Exception:
        pass  # silent: don't break `version` without config or network


# ════════════════════════════════════════════════════════════════════════════
# cloud
# ════════════════════════════════════════════════════════════════════════════

@app.group()
def cloud():
    """Operations against the RAGfly cloud (`ragfly login` or RAGFLY_API_KEY)."""


@cloud.command("me")
@click.option("-o", "--output", type=OUTPUT_TABLE, default="table")
def cloud_me(output: str):
    """Show who the credential is and its active context."""
    data = _v1("GET", "/v1/session")
    user = data.get("user") or {}
    if output == "json":
        _emit_json(data)
    else:
        _fields("Session", {
            "user": user.get("code"), "name": user.get("name"), "profile": data.get("profile"),
            "roles": ", ".join(data.get("roles") or []), "group": data.get("active_group"),
            "entity": data.get("active_entity"),
        }, [("User", "user"), ("Name", "name"), ("Profile", "profile"), ("Roles", "roles"),
            ("Active group", "group"), ("Active entity", "entity")])


# ── cloud group (signed-in person only) ──────────────────────────────────────

@cloud.group("group")
def cloud_group():
    """The person's active group (parity with the web header dropdown)."""


@cloud_group.command("list")
@click.option("-o", "--output", type=OUTPUT_TABLE, default="table")
def cloud_group_list(output: str):
    """List the groups available to the signed-in person."""
    from .grupo_activo import get_grupo_activo_local

    data = _v1("GET", "/auth/me")
    grupos = data.get("grupos") or []
    activo = get_grupo_activo_local()
    if output == "json":
        _emit_json({"active": activo, "groups": grupos})
        return
    rows = [{"active": "●" if g.get("codigo_grupo") == activo else "", "code": g.get("codigo_grupo"),
             "name": g.get("nombre_grupo"), "alias": g.get("alias_grupo")} for g in grupos]
    _table("Available groups", rows, [("", "active"), ("Code", "code"), ("Name", "name"), ("Alias", "alias")])
    console.print(f"  [dim]{'Local active group: ' + activo if activo else 'No local active group — using the default.'}[/dim]")


@cloud_group.command("switch")
@click.argument("group_code")
def cloud_group_switch(group_code: str):
    """Switch the active group. The backend validates membership first."""
    from .grupo_activo import set_grupo_activo

    contexto = _v1("POST", "/auth/cambiar-grupo", body={"codigo_grupo": group_code})
    set_grupo_activo(group_code)
    console.print(f"[green]✓ Active group switched to:[/green] [bold]{group_code}[/bold] ({contexto.get('nombre_grupo') or group_code})")


@cloud_group.command("clear")
def cloud_group_clear():
    """Clear the local active group (back to the default group)."""
    from .grupo_activo import clear_grupo_activo, get_grupo_activo_local

    actual = get_grupo_activo_local()
    if not actual:
        console.print("[yellow]No local active group configured.[/yellow]")
        return
    clear_grupo_activo()
    console.print(f"[green]✓ Local active group '{actual}' cleared.[/green]")


# ── cloud api-key (signed-in person only) ────────────────────────────────────

@cloud.group("api-key")
def cloud_api_key():
    """Manage API keys (`rf_...`). Requires `ragfly login`: an API key cannot manage keys."""


@cloud_api_key.command("create")
@click.option("--name", required=True, help="Descriptive name for the key (e.g. pipeline-ci)")
@click.option("--role", default=None, help="Requested role. Default: the owner's primary role")
@click.option("--area", default=None, help="Scope the key to an area subtree")
@click.option("--target-user", default=None, help="(admin) create the key for another user of the group")
@click.option("-o", "--output", type=click.Choice(["text", "json"]), default="text")
def cloud_api_key_create(name: str, role: str | None, area: str | None, target_user: str | None, output: str):
    """Create an API key. The secret is shown ONLY once."""
    body = {"nombre": name, "rol_solicitado": role, "codigo_area": area, "codigo_usuario_destino": target_user}
    data = _v1("POST", "/auth/api-key", body={k: v for k, v in body.items() if v})
    if output == "json":
        _emit_json(data)
        return
    console.print()
    console.print(f"[green]✓ API key created:[/green] [bold]{data.get('nombre')}[/bold]")
    console.print(Panel(f"[bold yellow]{data.get('api_key')}[/bold yellow]",
                        title="Save it NOW — it won't be shown again", border_style="yellow"))
    console.print(f"  Prefix: [dim]{data.get('prefijo')}[/dim]   Role: {data.get('codigo_rol') or '—'}")
    console.print("  Usage: [dim]export RAGFLY_API_KEY=<the key above>[/dim]")
    console.print()


@cloud_api_key.command("list")
@click.option("-o", "--output", type=OUTPUT_TABLE, default="table")
def cloud_api_key_list(output: str):
    """List the person's API keys (prefix only, never the secret)."""
    data = _v1("GET", "/auth/api-key")
    items = data if isinstance(data, list) else (data or {}).get("items", [])
    if output == "json":
        _emit_json(items)
        return
    rows = [{"prefix": k.get("prefijo"), "name": k.get("nombre"), "role": k.get("codigo_rol"),
             "created": (k.get("creada_en") or "")[:10], "last_used": (k.get("ultimo_uso") or "")[:10],
             "status": "revoked" if k.get("revocada_en") else "active"} for k in items]
    _table("API keys", rows, [("Prefix", "prefix"), ("Name", "name"), ("Role", "role"),
                              ("Created", "created"), ("Last used", "last_used"), ("Status", "status")])


@cloud_api_key.command("revoke")
@click.argument("prefix")
def cloud_api_key_revoke(prefix: str):
    """Revoke an API key by its prefix (stops authenticating immediately)."""
    _v1("DELETE", f"/auth/api-key/{_segment(prefix)}")
    console.print(f"[green]✓ API key revoked:[/green] [bold]{prefix}[/bold]")


# ── cloud document ───────────────────────────────────────────────────────────

@cloud.group("document")
def cloud_document():
    """Documents of the active group."""


@cloud_document.command("list")
@click.option("--status", default=None, help="Filter by status (e.g. VECTORIZED)")
@click.option("--limit", default=20, show_default=True)
@click.option("--page", default=1, show_default=True)
@click.option("-o", "--output", type=OUTPUT_LIST, default="table")
def cloud_document_list(status: str | None, limit: int, page: int, output: str):
    """List documents."""
    data = _v1("GET", "/v1/documents", params={"status": status, "limit": limit, "page": page})
    _list(data, output, key="documents", id_key="code", title=f"Documents (page {page})",
          columns=[("Code", "code"), ("Name", "name"), ("Status", "status"), ("Location", "location_url"), ("KB", "size_kb")])


@cloud_document.command("show")
@click.argument("document_code")
@click.option("-o", "--output", type=OUTPUT_TABLE, default="table")
def cloud_document_show(document_code: str, output: str):
    """Show one document."""
    data = _v1("GET", f"/v1/documents/{_segment(document_code)}")
    _show(data, output, f"Document {document_code}", [
        ("Code", "code"), ("Name", "name"), ("Status", "status"), ("Status detail", "status_detail"),
        ("Type", "document_type"), ("Format", "file_format"), ("Location", "location"),
        ("Size (KB)", "size_kb"), ("Updated", "updated_at"), ("Open with", "fs"),
    ])


@cloud_document.command("edges")
@click.argument("document_code")
@click.option("--neighbor-limit", default=50, show_default=True, help="Maximum documents at 2 hops")
def cloud_document_edges(document_code: str, neighbor_limit: int):
    """Corpus graph edges of a document (JSON)."""
    _emit_json(_v1("GET", f"/v1/documents/{_segment(document_code)}/edges", params={"neighbor_limit": neighbor_limit}))


# ── cloud space ──────────────────────────────────────────────────────────────

@cloud.group("space")
def cloud_space():
    """Working spaces."""


@cloud_space.command("list")
@click.option("--limit", default=20, show_default=True)
@click.option("-o", "--output", type=OUTPUT_LIST, default="table")
def cloud_space_list(limit: int, output: str):
    """List working spaces."""
    data = _v1("GET", "/v1/spaces", params={"limit": limit})
    _list(data, output, key="spaces", id_key="space_id", title="Working spaces",
          columns=[("ID", "space_id"), ("Name", "name"), ("Type", "type"), ("Scope", "scope"),
                   ("Docs", "total_documents"), ("Created", "created_at")])


@cloud_space.command("show")
@click.argument("space_id", type=int)
@click.option("--document-limit", default=20, show_default=True)
@click.option("-o", "--output", type=OUTPUT_TABLE, default="table")
def cloud_space_show(space_id: int, document_limit: int, output: str):
    """Show a working space with its documents."""
    data = _v1("GET", f"/v1/spaces/{space_id}", params={"document_limit": document_limit})
    if output == "json":
        _emit_json(data)
        return
    _fields(f"Working space #{space_id}", data.get("space") or {}, [
        ("Name", "name"), ("Type", "type"), ("Scope", "scope"), ("Criterion", "criterion"),
        ("Documents", "total_documents"), ("Created", "created_at"),
    ])
    _table("Documents", data.get("documents") or [], [("Code", "code"), ("Name", "name"), ("Status", "status")])


# ── cloud queue ──────────────────────────────────────────────────────────────

@cloud.group("queue")
def cloud_queue():
    """Processing queue and run history."""


@cloud_queue.command("show")
@click.option("--process", default=None, help="Filter by process")
@click.option("--status", default=None, help="Filter by status (PENDING, RUNNING, COMPLETED…)")
@click.option("--limit", default=20, show_default=True)
@click.option("-o", "--output", type=OUTPUT_LIST, default="table")
def cloud_queue_show(process: str | None, status: str | None, limit: int, output: str):
    """Current state of the processing queue."""
    data = _v1("GET", "/v1/queue", params={"process": process, "status": status, "limit": limit})
    _list(data, output, key="items", id_key="queue_id", title="Processing queue",
          columns=[("ID", "queue_id"), ("Document", "document_code"), ("Status", "status"),
                   ("Started", "started_at"), ("Result", "result")])


@cloud_queue.command("runs")
@click.option("--limit", default=10, show_default=True)
@click.option("-o", "--output", type=OUTPUT_LIST, default="table")
def cloud_queue_runs(limit: int, output: str):
    """History of runs."""
    data = _v1("GET", "/v1/runs", params={"limit": limit})
    _list(data, output, key="runs", id_key="process_code", title="Runs",
          columns=[("Process", "process_code"), ("Type", "process_type"), ("Started", "started_at"),
                   ("Finished", "finished_at"), ("Cost", "cost")])


# ── cloud skill ──────────────────────────────────────────────────────────────

@cloud.group("skill")
def cloud_skill():
    """LLM skills of the catalog."""


@cloud_skill.command("list")
@click.option("-o", "--output", type=OUTPUT_LIST, default="table")
def cloud_skill_list(output: str):
    """List the available skills."""
    data = _v1("GET", "/v1/skills")
    _list(data, output, key="skills", id_key="code", title="Skills",
          columns=[("Code", "code"), ("Name", "name"), ("Applies to", "applies_to"), ("Output", "output_destination")])


@cloud_skill.command("show")
@click.argument("skill_code")
@click.option("-o", "--output", type=OUTPUT_TABLE, default="table")
def cloud_skill_show(skill_code: str, output: str):
    """Show one skill."""
    data = _v1("GET", f"/v1/skills/{_segment(skill_code)}")
    _show(data, output, f"Skill {skill_code}", [
        ("Code", "code"), ("Name", "name"), ("Description", "description"), ("Applies to", "applies_to"),
        ("Kind", "kind"), ("Model level", "model_level"), ("Output", "output_destination"), ("Format", "output_format"),
    ])


@cloud_skill.command("run")
@click.argument("skill_code")
@click.option("--space", type=int, default=None, help="Working space ID")
@click.option("--document", default=None, help="Single document code")
@click.option("-o", "--output", type=OUTPUT_TABLE, default="table")
def cloud_skill_run(skill_code: str, space: int | None, document: str | None, output: str):
    """Run a skill on a working space or a document."""
    if not space and not document:
        raise click.UsageError("Provide --space <ID> or --document <CODE>")
    body = {k: v for k, v in {"space_id": space, "document_code": document}.items() if v is not None}
    data = _v1("POST", f"/v1/skills/{_segment(skill_code)}/run", body=body)
    if output == "json":
        _emit_json(data)
        return
    console.print(f"[green]✓ Queued[/green]" if data.get("accepted", True) else "[red]✗ Not accepted[/red]")
    console.print(f"  Process: {data.get('process_code') or '—'}   Status: {data.get('status') or '—'}")
    console.print("  Track progress: [dim]ragfly cloud queue show[/dim]")


# ── catalog, functions, search, chat ─────────────────────────────────────────

@cloud.command("catalog")
@click.option("--type", "type_", type=click.Choice(["ALL", "FUNCTIONS", "SKILLS"]), default="ALL", show_default=True)
@click.option("-o", "--output", type=OUTPUT_TABLE, default="table")
def cloud_catalog(type_: str, output: str):
    """What this credential can use: functions and skills."""
    data = _v1("GET", "/v1/catalog", params={"type": type_})
    if output == "json":
        _emit_json(data)
        return
    if data.get("functions"):
        _table("Functions", data["functions"], [("Code", "code"), ("Name", "name"), ("URL", "url")])
    if data.get("skills"):
        _table("Skills", data["skills"], [("Code", "code"), ("Name", "name"), ("Applies to", "applies_to")])


@cloud.group("function")
def cloud_function():
    """Functions (screens) of the RAGfly application."""


@cloud_function.command("show")
@click.argument("function_code")
@click.option("-o", "--output", type=click.Choice(["text", "json"]), default="text")
def cloud_function_show(function_code: str, output: str):
    """A function with its documentation and the operations it allows."""
    data = _v1("GET", f"/v1/functions/{_segment(function_code)}")
    if output == "json":
        _emit_json(data)
        return
    click.echo(data.get("documentation") or data.get("summary") or data.get("name") or "")
    _table("Operations", data.get("operations") or [], [("Code", "code"), ("Kind", "kind")])


@cloud.command("search")
@click.argument("query", nargs=-1, required=True)
@click.option("--limit", type=int, default=10, show_default=True)
@click.option("--min-similarity", type=float, default=0.0, show_default=True)
@click.option("--entity", default=None, help="Filter by entity code")
@click.option("-o", "--output", type=OUTPUT_TABLE, default="table")
def cloud_search(query: tuple[str, ...], limit: int, min_similarity: float, entity: str | None, output: str):
    """Semantic search over the group's vectorized documents."""
    text = " ".join(query).strip()
    if not text:
        raise click.UsageError("The query cannot be empty.")
    body = {"query": text, "limit": limit, "min_similarity": min_similarity}
    if entity:
        body["entity_code"] = entity
    data = _v1("POST", "/v1/documents/search", body=body)
    if output == "json":
        _emit_json(data)
        return
    rows = [{**d, "fragment": ((d.get("chunks") or [{}])[0].get("text") or "")} for d in data.get("documents") or []]
    if not rows:
        console.print("[yellow]No results.[/yellow]")
        return
    _table(f"Search: {text[:60]}", rows, [("Code", "code"), ("Document", "name"),
                                          ("Similarity", "max_similarity"), ("Fragment", "fragment")])


@cloud.group("chat")
def cloud_chat():
    """Ask your documents (RAG)."""


@cloud_chat.command("ask")
@click.argument("message", nargs=-1, required=True)
@click.option("--function", "function_code", default="CHAT-USER", show_default=True, help="Chat function code")
@click.option("--conversation", "conversation_id", type=int, default=None, help="Continue an existing conversation")
@click.option("-o", "--output", type=click.Choice(["text", "json"]), default="text")
def cloud_chat_ask(message: tuple[str, ...], function_code: str, conversation_id: int | None, output: str):
    """Ask a question. Creates a conversation unless --conversation is given."""
    question = " ".join(message).strip()
    if not question:
        raise click.UsageError("The message cannot be empty.")
    body = {"question": question, "function_code": function_code}
    if conversation_id:
        body["conversation_id"] = conversation_id
    data = _v1("POST", "/v1/ask", body=body)
    if output == "json":
        _emit_json(data)
        return
    click.echo(data.get("answer", ""))
    console.print(f"[dim]Conversation #{data.get('conversation_id')}[/dim]")


# ── cloud agent ──────────────────────────────────────────────────────────────

PROFILES = click.Choice(["user_chat", "support_chat"])


@cloud.group("agent")
def cloud_agent():
    """AgentContext and its authorized tools."""


@cloud_agent.command("context")
@click.option("--profile", type=PROFILES, default="user_chat", show_default=True)
@click.option("-o", "--output", type=OUTPUT_TABLE, default="json")
def cloud_agent_context(profile: str, output: str):
    """The authenticated AgentContext for a functional profile."""
    data = _v1("GET", "/v1/agent/context", params={"function_profile": profile})
    if output == "json":
        _emit_json(data)
        return
    _fields("Agent context", {**data, "tool_count": len(data.get("tools") or [])},
            [("Profile", "function_profile"), ("Hash", "system_prompt_hash"), ("Tools", "tool_count")])


@cloud_agent.command("tool")
@click.argument("public_name")
@click.option("--arguments-json", default="{}", show_default=True, help="JSON object, @file or - (stdin)")
@click.option("--profile", type=PROFILES, default="user_chat", show_default=True)
def cloud_agent_tool(public_name: str, arguments_json: str, profile: str):
    """Run one tool authorized by the AgentContext (JSON output)."""
    arguments = _json_argument(arguments_json, "--arguments-json")
    _emit_json(_v1("POST", f"/v1/agent/tools/{_segment(public_name)}",
                   body={"arguments": arguments, "function_profile": profile}))


# ── usage, conversations, processes, organization ────────────────────────────

@cloud.command("usage")
@click.option("-o", "--output", type=OUTPUT_TABLE, default="table")
def cloud_usage(output: str):
    """Plan, quotas and consumption of the current period."""
    data = _v1("GET", "/v1/usage")
    if output == "json":
        _emit_json(data)
        return
    console.print(f"\n  Plan: [bold]{data.get('plan_name') or data.get('plan_code')}[/bold]  "
                  f"{data.get('period_start')} → {data.get('period_end')}")
    _table("Quotas", data.get("quotas") or [], [("Feature", "feature"), ("Name", "name"), ("Used", "used"),
                                                ("Included", "included"), ("Unit", "unit"), ("On limit", "on_limit")])


@cloud.group("conversation")
def cloud_conversation():
    """Conversation history."""


@cloud_conversation.command("list")
@click.option("--function", "function_code", default=None, help="Filter by chat function code")
@click.option("--limit", default=50, show_default=True)
@click.option("-o", "--output", type=OUTPUT_LIST, default="table")
def cloud_conversation_list(function_code: str | None, limit: int, output: str):
    """List conversations."""
    data = _v1("GET", "/v1/conversations", params={"function_code": function_code, "limit": limit})
    _list(data, output, key="conversations", id_key="conversation_id", title="Conversations",
          columns=[("ID", "conversation_id"), ("Title", "title"), ("Function", "function_code"), ("Updated", "updated_at")])


@cloud_conversation.command("delete")
@click.argument("conversation_id", type=int)
@click.option("--yes", is_flag=True, help="Do not ask for confirmation")
def cloud_conversation_delete(conversation_id: int, yes: bool):
    """Delete a conversation and its messages."""
    if not yes:
        click.confirm(f"Delete conversation #{conversation_id}?", abort=True)
    _v1("DELETE", f"/v1/conversations/{conversation_id}")
    console.print(f"[green]✓ Conversation #{conversation_id} deleted.[/green]")


@cloud.group("process")
def cloud_process():
    """Process instances (requests, tasks, runs)."""


@cloud_process.command("list")
@click.option("--status", default=None)
@click.option("--process-type", default=None)
@click.option("--category", default=None)
@click.option("--mine", is_flag=True, help="Only created by or assigned to me")
@click.option("--only-open", is_flag=True)
@click.option("--limit", default=20, show_default=True)
@click.option("--page", default=1, show_default=True)
@click.option("-o", "--output", type=OUTPUT_LIST, default="table")
def cloud_process_list(status, process_type, category, mine, only_open, limit, page, output):
    """List processes."""
    data = _v1("GET", "/v1/processes", params={
        "status": status, "process_type": process_type, "category": category,
        "mine": "true" if mine else None, "only_open": "true" if only_open else None,
        "limit": limit, "page": page,
    })
    _list(data, output, key="processes", id_key="code", title="Processes",
          columns=[("Code", "code"), ("Name", "name"), ("Status", "status"), ("Priority", "priority"), ("Due", "due_at")])


@cloud_process.command("show")
@click.argument("process_code")
@click.option("-o", "--output", type=OUTPUT_TABLE, default="table")
def cloud_process_show(process_code: str, output: str):
    """Show one process."""
    data = _v1("GET", f"/v1/processes/{_segment(process_code)}")
    _show(data, output, f"Process {process_code}", [
        ("Code", "code"), ("Name", "name"), ("Status", "status"), ("Category", "category"),
        ("Priority", "priority"), ("Assigned to", "assigned_to"), ("Due", "due_at"), ("Comments", "comments"),
    ])


@cloud_process.command("update")
@click.argument("process_code")
@click.option("--status", default=None)
@click.option("--priority", default=None)
@click.option("--name", default=None)
@click.option("--description", default=None)
@click.option("--comments", default=None)
@click.option("--assigned-to", default=None)
@click.option("--due-at", default=None)
@click.option("--finished-at", default=None)
@click.option("--cost", type=float, default=None)
def cloud_process_update(process_code: str, **fields):
    """Update a process. Only the options you pass are written."""
    body = {k: v for k, v in fields.items() if v is not None}
    if not body:
        raise click.UsageError("Pass at least one field to update.")
    _emit_json(_v1("PATCH", f"/v1/processes/{_segment(process_code)}", body=body))


@cloud.group("organization")
def cloud_organization():
    """Organization profile (group and entity descriptions and system prompts)."""


@cloud_organization.command("show")
@click.option("--entity", default=None, help="Entity code (default: the active entity)")
def cloud_organization_show(entity: str | None):
    """Show the organization profile (JSON)."""
    _emit_json(_v1("GET", "/v1/organization", params={"entity_code": entity}))


@cloud_organization.command("update")
@click.option("--group-description", default=None)
@click.option("--group-system-prompt", default=None)
@click.option("--entity-description", default=None)
@click.option("--entity-system-prompt", default=None)
@click.option("--entity", "entity_code", default=None)
def cloud_organization_update(**fields):
    """Update the organization profile. Only the options you pass are written."""
    body = {k: v for k, v in fields.items() if v is not None}
    if not body:
        raise click.UsageError("Pass at least one field to update.")
    _emit_json(_v1("PUT", "/v1/organization", body=body))


@cloud_organization.command("draft")
@click.option("--source-file", type=click.Path(exists=True, dir_okay=False), default=None,
              help="Text describing the organization (default: stdin)")
@click.option("--entity", "entity_code", default=None)
def cloud_organization_draft(source_file: str | None, entity_code: str | None):
    """Draft the profile texts from a source text (does not write them)."""
    source = Path(source_file).read_text(encoding="utf-8") if source_file else sys.stdin.read()
    body = {"source_text": source}
    if entity_code:
        body["entity_code"] = entity_code
    _emit_json(_v1("POST", "/v1/organization/draft", body=body))


# ── cloud operation ──────────────────────────────────────────────────────────

@cloud.group("operation")
def cloud_operation():
    """Every operation of the RAGfly application, with the web app's permissions."""


@cloud_operation.command("list")
@click.option("-o", "--output", type=OUTPUT_LIST, default="table")
def cloud_operation_list(output: str):
    """Operations this credential can run."""
    data = _v1("GET", "/v1/operations")
    rows = [{**op, "functions": ", ".join(op.get("functions") or [])} for op in data.get("operations") or []]
    _list({**data, "operations": rows} if output == "table" else data, output, key="operations", id_key="code",
          title="Operations", columns=[("Code", "code"), ("Kind", "kind"), ("Functions", "functions")])


@cloud_operation.command("show")
@click.argument("code")
def cloud_operation_show(code: str):
    """One operation with its input and output schema (JSON)."""
    _emit_json(_v1("GET", f"/v1/operations/{_segment(code)}"))


@cloud_operation.command("run")
@click.argument("code")
@click.option("--input-json", "input_json", default="{}", show_default=True,
              help="Input fields as a JSON object, @file or - (stdin). Never put secrets here.")
@click.option("--confirm", is_flag=True, help="Required to run a write_confirm operation")
@click.option("-o", "--output", type=click.Choice(["text", "json"]), default="json")
def cloud_operation_run(code: str, input_json: str, confirm: bool, output: str):
    """Run an operation. write_confirm operations only run with --confirm."""
    payload = {"input": _json_argument(input_json, "--input-json"), "confirm": confirm}
    data = _v1("POST", f"/v1/operations/{_segment(code)}:execute", body=payload)
    if output == "json":
        _emit_json(data)
    if not data.get("executed"):
        err_console.print(
            f"[yellow]⚠ {code} was NOT executed: it needs confirmation.[/yellow] "
            "Review the preview and repeat with --confirm."
        )
        if output == "text":
            _emit_json(data.get("preview"))
        return
    if output == "text":
        console.print(f"[green]✓ {code} executed.[/green]")
        _emit_json(data.get("result"))
