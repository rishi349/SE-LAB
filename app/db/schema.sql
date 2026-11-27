-- Financial Ledger & Digital Wallet API — database schema (SQLite).
-- Money is always INTEGER paise. typeof() checks stop REAL values from being stored.
-- Applied idempotently at startup by app.db.connection.init_db.

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------- users
CREATE TABLE IF NOT EXISTS users (
    user_id                  TEXT PRIMARY KEY,               -- permanent public User ID
    email                    TEXT UNIQUE,                    -- NULL only after personal-data deletion
    name                     TEXT,                           -- NULL only after personal-data deletion
    password_hash            TEXT,                           -- NULL only after personal-data deletion
    role                     TEXT NOT NULL CHECK (role IN ('user', 'admin')),
    status                   TEXT NOT NULL DEFAULT 'ACTIVE'
                             CHECK (status IN ('ACTIVE', 'DEACTIVATED', 'DELETED')),
    name_changed_at          TEXT,                           -- last successful name change
    created_at               TEXT NOT NULL,
    deactivated_at           TEXT,
    deletion_due_at          TEXT,                           -- deactivated_at + 7 days
    personal_data_deleted_at TEXT,
    CHECK (status = 'DELETED'
           OR (email IS NOT NULL AND name IS NOT NULL AND password_hash IS NOT NULL)),
    CHECK (status = 'ACTIVE'
           OR (deactivated_at IS NOT NULL AND deletion_due_at IS NOT NULL))
);

-- ---------------------------------------------------------------- wallets
-- Exactly one wallet per user, created in the same DB transaction as the user.
CREATE TABLE IF NOT EXISTS wallets (
    wallet_id     TEXT PRIMARY KEY,
    user_id       TEXT NOT NULL UNIQUE REFERENCES users (user_id),
    balance_paise INTEGER NOT NULL DEFAULT 0
                  CHECK (typeof(balance_paise) = 'integer' AND balance_paise >= 0),
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);

-- ---------------------------------------------------------------- transactions
-- One row per transfer attempt (SUCCESS or FAILED) and per successful admin funding.
-- Rows are written once, with their final status, and never updated.
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id    TEXT PRIMARY KEY,
    type              TEXT NOT NULL CHECK (type IN ('TRANSFER', 'ADMIN_FUNDING')),
    status            TEXT NOT NULL CHECK (status IN ('SUCCESS', 'FAILED')),
    sender_user_id    TEXT NOT NULL REFERENCES users (user_id),  -- initiator (admin for funding)
    recipient_user_id TEXT REFERENCES users (user_id),           -- NULL if recipient invalid
    recipient_ref     TEXT NOT NULL,                             -- recipient ID as entered
    amount_paise      INTEGER NOT NULL CHECK (typeof(amount_paise) = 'integer'),
    failure_code      TEXT,                                      -- internal only, never exposed
    idempotency_key   TEXT NOT NULL,
    created_at        TEXT NOT NULL,
    UNIQUE (sender_user_id, idempotency_key),
    CHECK (status = 'FAILED'
           OR (amount_paise > 0 AND recipient_user_id IS NOT NULL AND failure_code IS NULL)),
    CHECK (status = 'SUCCESS' OR failure_code IS NOT NULL),
    CHECK (type = 'TRANSFER' OR status = 'SUCCESS'),
    CHECK (type = 'ADMIN_FUNDING' OR status = 'FAILED' OR sender_user_id <> recipient_user_id)
);

CREATE INDEX IF NOT EXISTS idx_txn_sender_created
    ON transactions (sender_user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_txn_recipient_created
    ON transactions (recipient_user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_txn_daily_limit
    ON transactions (sender_user_id, type, status, created_at);

-- ---------------------------------------------------------------- ledger
-- Double-entry style: a successful transfer = 1 DEBIT (sender) + 1 CREDIT (recipient).
-- A successful admin funding = 1 CREDIT (recipient) only; the admin wallet is not debited.
CREATE TABLE IF NOT EXISTS ledger_entries (
    entry_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id      TEXT NOT NULL REFERENCES transactions (transaction_id),
    wallet_id           TEXT NOT NULL REFERENCES wallets (wallet_id),
    entry_type          TEXT NOT NULL CHECK (entry_type IN ('DEBIT', 'CREDIT')),
    amount_paise        INTEGER NOT NULL
                        CHECK (typeof(amount_paise) = 'integer' AND amount_paise > 0),
    balance_after_paise INTEGER NOT NULL CHECK (typeof(balance_after_paise) = 'integer'),
    created_at          TEXT NOT NULL,
    UNIQUE (transaction_id, entry_type)
);

CREATE INDEX IF NOT EXISTS idx_ledger_wallet ON ledger_entries (wallet_id);
CREATE INDEX IF NOT EXISTS idx_ledger_txn ON ledger_entries (transaction_id);

-- ---------------------------------------------------------------- reconciliation
CREATE TABLE IF NOT EXISTS reconciliation_runs (
    run_id               TEXT PRIMARY KEY,
    status               TEXT NOT NULL CHECK (status IN
                         ('COMPLETED_CLEAN', 'COMPLETED_WITH_DISCREPANCIES', 'FAILED')),
    triggered_by         TEXT NOT NULL REFERENCES users (user_id),
    started_at           TEXT NOT NULL,
    completed_at         TEXT NOT NULL,
    wallets_checked      INTEGER NOT NULL DEFAULT 0,
    transactions_checked INTEGER NOT NULL DEFAULT 0,
    discrepancy_count    INTEGER NOT NULL DEFAULT 0,
    failure_detail       TEXT,
    CHECK (status = 'FAILED' OR failure_detail IS NULL),
    CHECK (status <> 'COMPLETED_CLEAN' OR discrepancy_count = 0),
    CHECK (status <> 'COMPLETED_WITH_DISCREPANCIES' OR discrepancy_count > 0)
);

CREATE INDEX IF NOT EXISTS idx_recon_started ON reconciliation_runs (started_at);

CREATE TABLE IF NOT EXISTS reconciliation_discrepancies (
    discrepancy_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id         TEXT NOT NULL REFERENCES reconciliation_runs (run_id),
    check_name     TEXT NOT NULL,
    entity_type    TEXT NOT NULL,
    entity_id      TEXT NOT NULL,
    expected       TEXT,
    actual         TEXT,
    detail         TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_recon_disc_run ON reconciliation_discrepancies (run_id);

-- ---------------------------------------------------------------- immutability guards
CREATE TRIGGER IF NOT EXISTS trg_ledger_no_update BEFORE UPDATE ON ledger_entries
BEGIN SELECT RAISE(ABORT, 'ledger_entries are immutable'); END;

CREATE TRIGGER IF NOT EXISTS trg_ledger_no_delete BEFORE DELETE ON ledger_entries
BEGIN SELECT RAISE(ABORT, 'ledger_entries are immutable'); END;

CREATE TRIGGER IF NOT EXISTS trg_txn_no_update BEFORE UPDATE ON transactions
BEGIN SELECT RAISE(ABORT, 'transactions are immutable'); END;

CREATE TRIGGER IF NOT EXISTS trg_txn_no_delete BEFORE DELETE ON transactions
BEGIN SELECT RAISE(ABORT, 'transactions are immutable'); END;

CREATE TRIGGER IF NOT EXISTS trg_wallet_no_delete BEFORE DELETE ON wallets
BEGIN SELECT RAISE(ABORT, 'wallets cannot be deleted'); END;

CREATE TRIGGER IF NOT EXISTS trg_wallet_owner_fixed BEFORE UPDATE OF wallet_id, user_id ON wallets
WHEN NEW.wallet_id IS NOT OLD.wallet_id OR NEW.user_id IS NOT OLD.user_id
BEGIN SELECT RAISE(ABORT, 'wallet identity cannot change'); END;

CREATE TRIGGER IF NOT EXISTS trg_user_no_delete BEFORE DELETE ON users
BEGIN SELECT RAISE(ABORT, 'users are deactivated, never deleted'); END;

CREATE TRIGGER IF NOT EXISTS trg_user_id_fixed BEFORE UPDATE OF user_id ON users
WHEN NEW.user_id IS NOT OLD.user_id
BEGIN SELECT RAISE(ABORT, 'user_id cannot change'); END;

CREATE TRIGGER IF NOT EXISTS trg_user_role_fixed BEFORE UPDATE OF role ON users
WHEN NEW.role IS NOT OLD.role
BEGIN SELECT RAISE(ABORT, 'role cannot change'); END;

CREATE TRIGGER IF NOT EXISTS trg_user_email_fixed BEFORE UPDATE OF email ON users
WHEN NEW.email IS NOT NULL AND NEW.email IS NOT OLD.email
BEGIN SELECT RAISE(ABORT, 'email cannot change'); END;

CREATE TRIGGER IF NOT EXISTS trg_recon_run_no_update BEFORE UPDATE ON reconciliation_runs
BEGIN SELECT RAISE(ABORT, 'reconciliation reports are immutable'); END;

CREATE TRIGGER IF NOT EXISTS trg_recon_run_no_delete BEFORE DELETE ON reconciliation_runs
BEGIN SELECT RAISE(ABORT, 'reconciliation reports are immutable'); END;

CREATE TRIGGER IF NOT EXISTS trg_recon_disc_no_update BEFORE UPDATE ON reconciliation_discrepancies
BEGIN SELECT RAISE(ABORT, 'reconciliation reports are immutable'); END;

CREATE TRIGGER IF NOT EXISTS trg_recon_disc_no_delete BEFORE DELETE ON reconciliation_discrepancies
BEGIN SELECT RAISE(ABORT, 'reconciliation reports are immutable'); END;

-- ---------------------------------------------------------------- notifications
-- In-app notifications. Written AFTER the money transaction commits (best-effort), so a
-- notification can never make a transfer or funding fail. No message text is stored: the
-- API builds it on read with the counterparty's current name. Only is_read/read_at change.
CREATE TABLE IF NOT EXISTS notifications (
    notification_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id              TEXT NOT NULL REFERENCES users (user_id),
    type                 TEXT NOT NULL CHECK (type IN
                         ('TRANSFER_SENT', 'TRANSFER_RECEIVED', 'TRANSFER_FAILED', 'WALLET_FUNDED')),
    transaction_id       TEXT NOT NULL REFERENCES transactions (transaction_id),
    counterparty_user_id TEXT REFERENCES users (user_id),
    amount_paise         INTEGER NOT NULL CHECK (typeof(amount_paise) = 'integer'),
    is_read              INTEGER NOT NULL DEFAULT 0 CHECK (is_read IN (0, 1)),
    created_at           TEXT NOT NULL,
    read_at              TEXT,
    UNIQUE (user_id, transaction_id, type)
);

CREATE INDEX IF NOT EXISTS idx_notif_user_created ON notifications (user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_notif_user_unread ON notifications (user_id, is_read);
