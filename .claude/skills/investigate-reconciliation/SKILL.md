---
name: investigate-reconciliation
description: Run reconciliation and investigate a COMPLETED_WITH_DISCREPANCIES or FAILED report without modifying financial data.
---

# Investigate reconciliation

Reconciliation is read-only by design. **Never** edit `wallets`, `transactions` or
`ledger_entries` to make a report go clean.

1. Trigger: `POST /api/v1/admin/reconciliation-runs` with an admin token
   (or in Python: `run_reconciliation(conn, triggered_by=<admin_user_id>)`).
2. Read the report: `GET /api/v1/admin/reconciliation-runs/{run_id}`.
3. For each discrepancy, look up `check_name` in `docs/financial-flows.md` §6 and inspect:
   ```sql
   SELECT * FROM transactions   WHERE transaction_id = :entity_id;
   SELECT * FROM ledger_entries WHERE transaction_id = :entity_id;
   SELECT * FROM ledger_entries WHERE wallet_id = :entity_id ORDER BY entry_id;
   ```
   Open the database read-only: `sqlite3 "file:data/ledger.db?mode=ro" -uri`.
4. `FAILED` status means the run itself crashed — read `failure_detail` and the server log.
5. Write up: which check, which entity, expected vs actual, likely cause (code path), and a
   proposed fix to the *code*. Any data correction is a human decision and must be done as a
   new, documented operation — not by editing history.
