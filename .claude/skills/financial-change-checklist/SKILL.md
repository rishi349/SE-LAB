---
name: financial-change-checklist
description: Mandatory checklist for any change that touches money, balances, transfers, admin funding, idempotency, limits, the ledger or the database schema of this project.
---

# Financial change checklist

Read `docs/financial-flows.md` and `docs/decisions.md` first. Then confirm every item:

**Money**
- [ ] Amounts are `int` paise end to end. No `float`, no `Decimal` conversions, no rounding.
- [ ] New request fields use `Field(strict=True)` for amounts.

**Atomicity & concurrency**
- [ ] All reads that decide a money movement and all writes happen inside one
      `write_transaction(conn)` (`BEGIN IMMEDIATE`).
- [ ] Balances change only through `app/modules/ledger/service.py` (`debit`/`credit`),
      which always writes a ledger entry.

**Ledger**
- [ ] Successful transfer = exactly 1 DEBIT + 1 CREDIT of the same amount.
- [ ] Admin funding = exactly 1 CREDIT, no DEBIT.
- [ ] Failed attempt = transaction row only, no ledger entry, no balance change.
- [ ] No code issues `UPDATE`/`DELETE` on `transactions` or `ledger_entries` (triggers will abort it).

**Rules**
- [ ] ₹50,000 single limit and ₹1,00,000 IST-day limit still apply to transfers only, and
      only `SUCCESS` transfers count.
- [ ] Failure reasons never appear in responses (`failure_code` is never selected for output).
- [ ] Idempotency semantics unchanged (see D1/D2 in `docs/decisions.md`).

**Proof**
- [ ] Added/updated tests in `tests/integration` (and `tests/api` if the contract changed).
- [ ] `run_checks(conn).discrepancies == []` after the scenario.
- [ ] `pytest -q` and `ruff check .` pass.
- [ ] Docs updated if behaviour changed (only describe what is implemented).
