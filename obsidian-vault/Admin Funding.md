---
tags: [admin, money]
---
# Admin Funding

- Admin = specialised testing user. Created only by `python -m scripts.create_admin`.
- `POST /api/v1/admin/fundings` + `Idempotency-Key`.
- `type = ADMIN_FUNDING`, one CREDIT entry, **no debit** of the admin wallet.
- Works with admin at ₹0. No limits, no cap, no system account, no initial allocation.
- Invalid request (amount ≤ 0, unknown recipient) → error, nothing stored, key not consumed.
- Only source of money → Σ all balances = Σ successful funding ([[Reconciliation]]).
- Admin search: `GET /admin/users/{user_id}` exact match only → `{user_id, name}`. No email search.
