---
tags: [reconciliation, audit]
---
# Reconciliation

- Admin triggers `POST /api/v1/admin/reconciliation-runs`; read-only; runs on one snapshot.
- Checks: wallet vs ledger · negative balance · transfer integrity · debit = credit ·
  status vs records · admin funding integrity · Σ balances = Σ funding.
- Status: `COMPLETED_CLEAN` | `COMPLETED_WITH_DISCREPANCIES` (finished, found issues) |
  `FAILED` (the run crashed; `failure_detail`).
- Reports + discrepancies stored, immutable, listable newest first.
- **Never repairs data.** Investigation steps: `.claude/skills/investigate-reconciliation`.

Linked: [[Ledger Model]], [[Admin Funding]]
