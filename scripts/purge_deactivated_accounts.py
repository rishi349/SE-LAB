"""Delete personal data of accounts deactivated more than 7 days ago.

Usage:
    python -m scripts.purge_deactivated_accounts

Run it manually (or from the OS scheduler, if you choose). Financial records are kept.
"""

from __future__ import annotations

from app.config import load_settings
from app.db.connection import connect, init_db
from app.modules.users.service import purge_expired_accounts


def main() -> int:
    settings = load_settings()
    init_db(settings.database_path)
    conn = connect(settings.database_path)
    try:
        count = purge_expired_accounts(conn)
    finally:
        conn.close()
    print(f"Personal data deleted for {count} account(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
