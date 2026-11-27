---
tags: [ledger, money]
---
# Ledger Model

- Money = integer **paise**. ₹1 = 100. Never float.
- `transactions` = what was attempted/done. `ledger_entries` = how balances moved.
- Successful transfer → **DEBIT** sender + **CREDIT** recipient, same amount.
- [[Admin Funding]] → single **CREDIT**, no debit.
- [[Failed Transfer Attempts]] → transaction row only, zero entries.
- Each entry stores `balance_after_paise`.
- Invariant: `wallet.balance = Σ credits − Σ debits` → checked by [[Reconciliation]].
- Immutable: DB triggers abort any UPDATE/DELETE on transactions and ledger entries.

Defence in depth for balance ≥ 0: service check → `UPDATE … WHERE balance >= amount` →
`CHECK (balance_paise >= 0)`.
