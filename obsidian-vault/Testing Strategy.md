---
tags: [testing]
---
# Testing Strategy

- `tests/unit` — pure functions, schemas, JWT/bcrypt, rate limiter.
- `tests/integration` — services against a real temp SQLite file per test.
- `tests/api` — FastAPI `TestClient`, auth/roles/ownership/error envelope.
- Fixtures: `settings` (tmp DB, bcrypt rounds 4, rate limit off), `conn`, `admin`,
  `make_user`, `fund`.
- Time-dependent rules take a `now=` argument → deterministic tests for IST midnight,
  60-day cooldown, 7-day purge.
- Corruption tests drop a trigger on purpose to prove [[Reconciliation]] detects it.
- Requirement → test map: `docs/testing.md`.

## Manual demo
Start the server and open `http://127.0.0.1:8000/demo`. The right-hand "API calls" panel shows
each request/response, which is handy for explaining idempotency (`replayed`) and the generic
`TRANSFER_FAILED` error during a viva.
