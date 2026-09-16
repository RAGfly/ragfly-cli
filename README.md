# RAGfly CLI

Operate RAGfly from the terminal and CI — `login` + the full `cloud` API surface
against `api.ragfly.ai`. Lightweight: depends only on `click`, `rich`, `httpx`
and `keyring`. **No desktop / PySide6 / OCR dependencies.**

```bash
pip install ragfly-cli
ragfly version
ragfly login
ragfly cloud me
```

> This package ships the **`ragfly` binary** for scripting and automation.
> It is distinct from `pip install ragfly` (the **Python SDK**, import `import ragfly`)
> and from **RAGfly Desktop** (the DMG/exe that bundles the local file worker for
> `ragfly local scan/sync/daemon`).

## Authentication

```bash
# A person (JWT, stored in the OS keyring)
ragfly login

# Non-interactive / CI / agents (API key, only reaches /v1)
export RAGFLY_API_KEY=rf_xxxxxxxxxx
```

`cloud group` and `cloud api-key` manage a person's session and credentials: they
need `ragfly login`, and the server refuses them for an API key.

## `RAGFLY_ROOT` (optional) — open original files on disk

Searching, asking and citing need zero extra config. Only if a script or agent
on this machine must open the **original file** on disk, set `RAGFLY_ROOT` once:
it is the **parent folder** of the folder you selected when uploading your
documents via the web app. RAGfly never reads it nor stores your absolute
path — documents uploaded via browser carry a *relative* `ruta_archivo`, and
the real path is `$RAGFLY_ROOT + ruta_archivo`.

```bash
# Example: you uploaded /Users/ana/Dropbox/MisDocumentos → the PARENT is the root
echo 'export RAGFLY_ROOT="/Users/ana/Dropbox"' >> ~/.zshrc
# "/MisDocumentos/letras/cancion.txt" → /Users/ana/Dropbox/MisDocumentos/letras/cancion.txt
```

Not needed for documents loaded via RAGfly Desktop (their paths are already
absolute). Step-by-step walkthrough:
<https://ragfly.ai/build/mcp#setting-up-ragfly_root--once-per-machine-in-3-steps>

## Command surface

```
ragfly
├── login / logout / version
└── cloud                      ← the English REST /v1 contract of api.ragfly.ai
    ├── me
    ├── group          list | switch | clear      (signed-in person)
    ├── api-key        create | list | revoke     (signed-in person)
    ├── document       list | show | edges
    ├── space          list | show
    ├── queue          show | runs
    ├── skill          list | show | run
    ├── catalog
    ├── function       show
    ├── search
    ├── chat           ask
    ├── agent          context | tool
    ├── usage
    ├── conversation   list | delete
    ├── process        list | show | update
    ├── organization   show | update | draft
    └── operation      list | show | run
```

Every operation of the RAGfly application is available through `cloud operation`,
with the same permissions and audit as the web app:

```bash
ragfly cloud operation list
ragfly cloud operation show document_types.update          # input/output schema
ragfly cloud operation run document_types.update --input-json '{"code": "TDOC_...", "name": "Invoices"}'

# write_confirm operations (deletes, reverts, resets) only run with --confirm
ragfly cloud operation run document_types.delete --input-json @input.json --confirm
```

`--input-json` takes inline JSON, `@file` or `-` (stdin). Never put secrets in it.
Output is English end to end (`--status VECTORIZED`, `-o json | jq`).

```bash
ragfly cloud document list --status VECTORIZED --limit 20 -o id
ragfly cloud skill run SUMMARIZE_DOCUMENT --space 12
ragfly cloud search "Q1 revenue"
```

Full reference: <https://api.ragfly.ai/docs>.

> **Local operations** (`ragfly local scan/sync/daemon`) require the local file
> worker and ship with **RAGfly Desktop**, not with this package.

## Relation to RAGfly Desktop

RAGfly Desktop bundles its own `ragfly` binary with the local commands and a
signed-in person's session. This package is the standalone cloud surface: since
1.19.0 its `cloud` commands use only the public `/v1` contract, so they no longer
mirror the Desktop copy.
