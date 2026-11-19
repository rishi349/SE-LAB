---
tags: [transfers, money]
---
# Transfer Flow

`POST /api/v1/transfers` + `Idempotency-Key` header.

Inside one `BEGIN IMMEDIATE`:
1. Key already used by this sender? → return stored result ([[Idempotency]]).
2. Rules in order: recipient exists & active → not self → amount > 0 → ≤ ₹50,000 →
   today's successful outgoing + amount ≤ ₹1,00,000 ([[Daily Limit and IST]]) → balance ≥ amount.
3. Insert transaction row (SUCCESS or FAILED).
4. If SUCCESS: debit + credit with ledger entries ([[Ledger Model]]).

Responses: `201` success · `422 TRANSFER_FAILED` (generic message, attempt recorded).

Admins can't make ordinary transfers. Insufficient balance never auto-retries.
