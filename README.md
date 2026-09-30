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

## Opening an original file on disk (optional)

Searching and citing need no local path setup. A document result may include an
`fs` object. For a local relative file, read `fs.home_var` and join that
environment variable's value with `fs.relative_path`. Each root has its own
variable; configure only the roots available on this machine.

```bash
export RAGFLY_HOME_442681="/Users/ana/Dropbox"
export RAGFLY_HOME_991203="/Volumes/Archive"
```

If `fs.is_cloud_only` is true, use the authorized cloud provider. If
`fs.is_public_url` is true, open its public URL. If `fs.is_absolute` is true,
use the absolute path on the machine where it exists. If `fs.home_var` is null
or unset, do not guess a local root. See the
[MCP guide](https://ragfly.ai/build/mcp#opening-a-document-on-disk-fs-block)
for the full order and examples.

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
