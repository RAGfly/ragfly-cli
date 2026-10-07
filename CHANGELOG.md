# Changelog

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
