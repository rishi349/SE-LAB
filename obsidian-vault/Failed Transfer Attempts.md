---
tags: [transfers, privacy]
---
# Failed Transfer Attempts

- Stored as `transactions.status = FAILED` with an internal `failure_code`.
- No ledger entries, no balance change, **not counted** in the daily limit.
- `failure_code` is never selected for any response → users see amount + FAILED only.
- Visibility:
  - valid recipient → sender **and** recipient see it
  - recipient doesn't exist / inactive / admin → `recipient_user_id = NULL` → sender only
- Consumes its idempotency key → retry needs a new key ([[Idempotency]]).

Linked: [[Transfer Flow]], [[Security Model]]
