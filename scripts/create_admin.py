"""Create the admin (testing) account. Admins are never created through the public API.

Usage:
    python -m scripts.create_admin --name "Test Admin" --email admin@example.com

The password is read from the ADMIN_PASSWORD environment variable if set, otherwise
prompted for (it is never passed on the command line, so it does not end up in shell history).
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys

from app.config import load_settings
from app.core.errors import AppError
from app.db.connection import connect, init_db
from app.modules.auth.service import create_admin


def _read_password() -> str:
    password = os.getenv("ADMIN_PASSWORD")
    if password:
        return password
    first = getpass.getpass("Admin password: ")
    second = getpass.getpass("Repeat password: ")
    if first != second:
        sys.exit("Passwords do not match.")
    return first


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create an admin account.")
    parser.add_argument("--name", required=True)
    parser.add_argument("--email", required=True)
    args = parser.parse_args(argv)

    settings = load_settings()
    init_db(settings.database_path)
    conn = connect(settings.database_path)
    try:
        result = create_admin(
            conn,
            name=args.name,
            email=args.email,
            password=_read_password(),
            bcrypt_rounds=settings.bcrypt_rounds,
        )
    except (AppError, ValueError) as exc:
        print(f"Could not create admin: {exc}", file=sys.stderr)
        return 1
    finally:
        conn.close()
    print(f"Admin created. User ID: {result['user']['user_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
