# Changelog

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
