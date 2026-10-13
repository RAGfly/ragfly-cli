# Changelog

## 2.0.1 — 2026-10-13

- `ragfly login` reads the active group and workspace from the public session (`GET /v1/session`: `active_group`, `active_workspace`) instead of the internal login payload.
- Removed the unused `RAGFLY_CODIGO_ENTIDAD` setting; an existing value in `config.env` is ignored.

## 2.0.0 — 2026-10-12

Breaking: the vocabulary changed. The credential's entity is now a **workspace** and a working space is now a **collection**. There are no aliases: the old commands and options are removed.

- `cloud entity set` -> `cloud workspace set [WORKSPACE_CODE] | --clear` ("Active workspace" in `cloud me` and the login summary).
- `cloud space list | show | compose | read | refresh | promote` -> `cloud collection list | show | compose | read | refresh | save`. `compose --type` now takes `TEMPORARY` (default) or `SAVED` (formerly `AREA` / `SPACE`).
- `--entity` -> `--workspace` (`cloud area list`, `cloud location list`, `cloud document-type list`, `cloud characteristic list`, `cloud search`, `cloud organization show | update | draft`).
- `--space` -> `--collection` (`cloud search`, `cloud skill run`).
- `cloud organization update`: `--entity-description` / `--entity-system-prompt` -> `--workspace-description` / `--workspace-system-prompt`.
- Calls `POST /v1/session/active-workspace` and `/v1/collections` (`/{id}`, `/compose`, `/{id}/read`, `/{id}/refresh`, `/{id}/save`); bodies use `workspace_code`, `collection_id`, `collection_id_a` / `collection_id_b` and `collection_type`.
- Requires a RAGfly Cloud that serves the new `/v1` vocabulary.

## 1.21.1 — 2026-10-09

- Package metadata: PyPI now links the source repository.

## 1.21.0 — 2026-10-08

- New `cloud area set AREA_CODE | set --release | list` and `cloud location list` (`--entity`, `--parent`, `--query`, `--limit`, `--cursor`), matching the SDKs and MCP.
- `--location CODE` narrows `cloud search`, `cloud document list` and `cloud chat ask` to one visible folder subtree, for that request only.
- `cloud entity set --clear` is the published flag; `--release` stays as an alias. `cloud me` shows the active and effective area.

## 1.20.0 — 2026-10-07

- `cloud chat ask --mode help` answers questions about RAGfly itself, without links to web screens.
- `cloud search --space ID --filter JSON` (inline, `@file` or `-`) for the structured filter and working-space scope.
- New `cloud document-type list`, `cloud characteristic list` and `cloud space compose | read | refresh | promote`, matching the SDKs and MCP.

## 1.19.1

- Keep a saved human session's group override out of requests authenticated with
  an API key. This prevents a 403 when an agent lists or executes public `/v1`
  operations after the CLI has previously been used interactively.

## 1.19.0

- Every `cloud` command talks to the English REST `/v1` contract, so an API key
  (`RAGFLY_API_KEY`) works end to end. With 1.18.0 an API key got 403 everywhere.
- New: `cloud operation list | show | run` (with `--confirm` for `write_confirm`),
  `cloud function show`, `cloud usage`, `cloud conversation`, `cloud process`
  and `cloud organization`.
- `cloud api-key` and `cloud group` need `ragfly login`; with an API key they show
  the server's message instead of a traceback.
- Removed the Spanish command and flag aliases and the client-side code translator.
- `cloud chat ask` returns the full answer (no streaming); `cloud agent` profiles are
  `user_chat` and `support_chat`.
- Every request sends `X-RAGfly-Client: cli`.
