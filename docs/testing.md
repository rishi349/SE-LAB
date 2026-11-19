# Testing

```bash
pip install -r requirements-dev.txt
pytest -q                       # everything
pytest tests/unit -q            # fast, no database
pytest tests/integration -q     # services + real SQLite
pytest tests/api -q             # HTTP through FastAPI's TestClient
```

## Isolation
Every test gets a fresh SQLite file under pytest's `tmp_path` (`tests/conftest.py`). Tests use
`bcrypt_rounds=4` for speed and disable rate limiting except in the dedicated rate-limit test.
No test touches `data/ledger.db` or needs a `.env` file.

## Layout

| Folder | What it covers |
|---|---|
| `tests/unit` | money formatting and limits, IST day boundaries, IDs, rate limiter, bcrypt/JWT (expiry, wrong secret, `alg: none`), request validation (strict int paise, forbidden fields, idempotency key format) |
| `tests/integration` | schema constraints and immutability triggers, wallet lifecycle, transfers, limits, failed attempts, idempotency, concurrency, admin funding, history visibility, profile cooldown, account deletion and purge, reconciliation |
| `tests/api` | endpoint success/failure, authentication, authorization (admin vs user, forged role claim), ownership, validation, error envelope, replay header, rate limiting, OpenAPI |

## Financial-correctness checklist → tests

| Requirement | Test |
|---|---|
| Successful transfer, debit + credit | `integration/test_transfers.py::test_successful_transfer_moves_money_with_debit_and_credit` |
| Insufficient balance | `...::test_insufficient_balance_fails_without_moving_money` |
| Zero / negative amounts | `...::test_zero_and_negative_amounts_fail` |
| Above ₹50,000 | `...::test_single_transfer_limit_is_50000_rupees` |
| Daily limit (successful only) | `...::test_daily_limit_counts_only_successful_outgoing_transfers` |
| IST midnight reset | `...::test_daily_limit_resets_at_ist_midnight_not_utc_midnight` |
| Self-transfer | `...::test_self_transfer_fails` |
| Nonexistent recipient | `...::test_nonexistent_recipient_fails_and_is_recorded` |
| Failed attempts persisted, no ledger, no balance change | `...::test_failed_attempts_are_persisted_but_create_no_ledger_entries` |
| Failure reason hidden | `test_transfers.py::test_failed_transfer_response_has_no_failure_reason`, `test_history.py::test_history_never_contains_failure_reasons`, `api/test_transfers_api.py` |
| Visibility rules | `test_history.py::test_failed_attempt_with_valid_recipient_is_visible_to_both`, `...to_nonexistent_recipient_is_visible_to_sender_only` |
| Concurrency: no double spend / negative / duplicates | `integration/test_concurrency.py` (threads on separate connections, then reconciliation must be clean) |
| Idempotency (Phase 2/4 semantics) | `integration/test_idempotency.py`, `api/test_transfers_api.py::test_idempotent_replay_returns_original` |
| Admin funding | `integration/test_admin_funding.py`, `api/test_history_admin_api.py::test_admin_funding_api` |
| Ledger consistency | reconciliation `run_checks` asserted clean after concurrency tests |
| Reconciliation discrepancies | `integration/test_reconciliation.py` (deliberate corruption, read-only proof, FAILED run) |
