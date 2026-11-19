---
tags: [idempotency, correctness]
---
# Idempotency

- Header `Idempotency-Key` (8–128 chars) on transfers and admin funding.
- Stored on the transaction row: `UNIQUE(sender_user_id, idempotency_key)`.
- Replay → stored result + `Idempotent-Replayed: true`. Never executes twice.
- No fingerprinting: same key + different body → still the original result.
- Business-rule failure (transfer) → stored as FAILED → key consumed.
- Rejected before execution (422 schema, 401, 429) → nothing stored → key free.
- Concurrent same-key requests serialise on the write lock; exactly one runs ([[Concurrency]]).

⚠ This is decision D1/D2 in [[Decision Log]] — verify against the original Phase 2/4 design.
