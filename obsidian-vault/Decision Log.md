---
tags: [decisions, adr]
---
# Decision Log

Full table with reasons: `docs/decisions.md`. The ones most likely to need a second look
against the original design (⚠):

- **D1** Idempotency key on the transaction row, unique per sender → [[Idempotency]]
- **D2** Failed transfer consumes its key; pre-execution rejections don't
- **D3** `BEGIN IMMEDIATE` for all money operations → [[Concurrency]]
- **D4** Six-table schema (`app/db/schema.sql`) → [[Ledger Model]]
- **D9** User ID = `USR` + 10 Crockford base32 chars
- **D11** Failed transfer → `422 TRANSFER_FAILED`, one generic message
- **D13** `POST /users/me/deletion-request`, no cancel → [[Account Deletion]]
- **D14** 7-day purge is a manual script, no scheduler
- **D17** Rate-limit numbers

Template for new decisions:
```
## D<n> — <title>
Context:
Decision:
Consequences:
```
