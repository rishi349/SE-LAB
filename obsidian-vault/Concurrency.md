---
tags: [concurrency, sqlite]
---
# Concurrency

- SQLite = one writer at a time. We take the write lock **first** with `BEGIN IMMEDIATE`,
  then read balances/limits, then write. No check-then-act race.
- WAL mode → readers (history, wallet view) don't block the writer.
- `busy_timeout` 10 s → waiting writers queue instead of failing; if exceeded → `503 SERVICE_BUSY`.
- One connection per request (`check_same_thread=False` because FastAPI may switch threads).
- Tests: 12 parallel ₹5,000 transfers from ₹30,000 → exactly 6 succeed; 8 parallel retries
  with one key → 1 execution; crossing A↔B transfers keep totals; reconciliation clean after.

Linked: [[Idempotency]], [[Daily Limit and IST]]
