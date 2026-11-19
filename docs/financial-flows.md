# Financial flows

All amounts are integer paise. Every money-moving operation runs inside one
`BEGIN IMMEDIATE` SQLite transaction (`app/db/connection.py::write_transaction`). It holds
the single database write lock from *before* the first balance read until commit, so:

* two transfers can never read the same balance and both spend it (no double spending);
* the daily-limit sum is read under the same lock, so parallel transfers cannot jointly
  exceed it;
* any exception rolls everything back — a partial transfer cannot exist.

## 1. Registration → wallet

`auth.service.register_user`: hash password (outside the lock) → `BEGIN IMMEDIATE` → reject
duplicate email → insert user → insert wallet with `balance_paise = 0` → commit. There is no
other way to create a wallet, and wallets cannot be deleted.

## 2. Ordinary transfer

`transfers.service.execute_transfer(sender, recipient, amount_paise, idempotency_key)`

```
BEGIN IMMEDIATE
  existing = transaction with (sender, key)?      ── yes ──▶ return it (replayed) ─┐
  sender must be ACTIVE role 'user'                                                  │
  recipient = ACTIVE role 'user' with that ID (else None)                            │
  reason = first failing rule:                                                       │
     recipient missing → self transfer → amount <= 0 → amount > ₹50,000              │
     → today's successful outgoing + amount > ₹1,00,000 → balance < amount           │
  INSERT transactions (status = FAILED with reason | SUCCESS)                        │
  if SUCCESS:                                                                        │
     UPDATE sender wallet  −amount (WHERE balance >= amount) + DEBIT ledger entry    │
     UPDATE recipient wallet +amount                         + CREDIT ledger entry   │
COMMIT ◀─────────────────────────────────────────────────────────────────────────────┘
```

* "Today" is the IST calendar day (`Asia/Kolkata`); it resets at IST midnight.
* Only `type = TRANSFER, status = SUCCESS` rows of the sender count toward the daily limit.
  Failed attempts and admin funding never count.
* A failed attempt is a stored transaction row with no ledger entries and no balance change.
* Insufficient balance is final for that request; nothing retries automatically.

### Failed-attempt visibility

| Situation | `recipient_user_id` stored | Visible to |
|---|---|---|
| Recipient is a valid active user (any failure reason) | recipient's ID | sender **and** recipient |
| Recipient does not exist / is not an active ordinary user | NULL (typed ID kept in `recipient_ref`) | sender only |
| Self-transfer | sender's own ID | sender |

History shows amount and `FAILED` status; `failure_code` is never selected for any response.

## 3. Admin funding

`admin.service.fund_wallet(admin, recipient, amount_paise, idempotency_key)`

```
BEGIN IMMEDIATE
  replay if (admin, key) exists
  caller must be ACTIVE admin; amount must be > 0; recipient must be ACTIVE ordinary user
  INSERT transactions (type ADMIN_FUNDING, status SUCCESS)
  UPDATE recipient wallet +amount + CREDIT ledger entry
COMMIT
```

* No debit on the admin's wallet; works with the admin at ₹0.
* Not subject to transfer limits. No cap, no system funding account, no initial allocation.
* Invalid funding requests raise an error, roll back, store nothing and do not consume the key.
* Money enters the system **only** through admin funding, so
  `SUM(all wallet balances) == SUM(successful admin funding)` must always hold.

## 4. Idempotency

| Case | Result |
|---|---|
| Same key, same user, after success | stored SUCCESS returned, `Idempotent-Replayed: true`, no new movement |
| Same key after a business failure (transfer) | stored FAILED result returned; key is consumed — use a new key to try again |
| Same key, different body | original stored result returned (no payload fingerprinting) |
| Same key used by a different user | independent (keys are scoped per initiating user) |
| Request rejected before execution (bad JSON, float amount, missing/invalid header, auth, rate limit) | nothing stored, key not consumed |
| Admin funding rejected (bad amount, unknown recipient) | nothing stored, key not consumed |
| Concurrent requests with the same key | serialised by the write lock; exactly one executes, the rest replay. `UNIQUE (sender_user_id, idempotency_key)` is the final guard. |

## 5. Account deletion

1. `POST /users/me/deletion-request` with password. Wallet balance must be exactly ₹0
   (settle it by transferring it out first).
2. Status becomes `DEACTIVATED`: login and existing tokens stop working; the account can
   no longer send or receive.
3. After 7 days `python -m scripts.purge_deactivated_accounts` sets name, email and password
   hash to NULL and status to `DELETED`. User ID, wallet row, transactions and ledger entries
   are kept as financial records.

## 6. Reconciliation (read-only)

See [`app/modules/reconciliation/service.py`](../app/modules/reconciliation/service.py).
Checks, on one consistent snapshot:

| Check | Rule |
|---|---|
| `WALLET_BALANCE_VS_LEDGER` | wallet balance = credits − debits |
| `NEGATIVE_WALLET_BALANCE` | no wallet below 0 |
| `TRANSFER_INTEGRITY` | each successful transfer: 1 DEBIT on sender wallet + 1 CREDIT on recipient wallet, both = amount |
| `DEBIT_CREDIT_BALANCE` | per transfer, debits = credits |
| `STATUS_VS_FINANCIAL_RECORDS` | FAILED ⇒ no ledger entries; SUCCESS ⇒ has entries |
| `ADMIN_FUNDING_INTEGRITY` | each funding: exactly 1 CREDIT = amount on recipient wallet, no DEBIT, sender is admin |
| `SYSTEM_TOTAL_VS_FUNDING` | sum of balances = sum of successful funding |

Outcome: `COMPLETED_CLEAN`, `COMPLETED_WITH_DISCREPANCIES` (finished and found problems), or
`FAILED` (the run itself crashed; `failure_detail` stored). Reports are immutable and kept.
Nothing is ever repaired automatically.
