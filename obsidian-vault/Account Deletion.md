---
tags: [accounts, privacy]
---
# Account Deletion

1. `POST /users/me/deletion-request` with password; balance must be exactly ₹0.
2. Status → `DEACTIVATED`: can't log in, old tokens rejected, can't send/receive.
3. After 7 days: `python -m scripts.purge_deactivated_accounts` → name, email, password hash
   = NULL; status `DELETED`.
4. Kept forever: User ID, wallet row, transactions, ledger entries.

- Email becomes reusable only after the purge.
- Wallets are never deleted independently (DB trigger).
- No wallet states / freeze — only the *account* has a status.

Profile side note: name change once per 60 days; first change allowed right after
registration; same-name request doesn't start the cooldown.
