"""Shared fixtures. Every test gets its own temporary SQLite file (isolated test database)."""

from __future__ import annotations

import itertools

import pytest

from app.config import Settings
from app.db.connection import connect, init_db
from app.modules.admin.service import fund_wallet
from app.modules.auth.service import create_admin, register_user
from tests.helpers import PASSWORD, new_key

TEST_JWT_SECRET = "test-only-secret-not-used-anywhere-else-0123456789"


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        database_path=str(tmp_path / "test-ledger.db"),
        jwt_secret=TEST_JWT_SECRET,
        bcrypt_rounds=4,
        rate_limit_enabled=False,
        log_level="WARNING",
    )


@pytest.fixture
def conn(settings):
    init_db(settings.database_path)
    connection = connect(settings.database_path)
    yield connection
    connection.close()


@pytest.fixture
def admin(conn, settings) -> dict:
    return create_admin(
        conn,
        name="Test Admin",
        email="admin@example.com",
        password=PASSWORD,
        bcrypt_rounds=settings.bcrypt_rounds,
    )["user"]


@pytest.fixture
def make_user(conn, settings):
    counter = itertools.count(1)

    def _make(name: str | None = None) -> dict:
        n = next(counter)
        return register_user(
            conn,
            name=name or f"User {n}",
            email=f"user{n}@example.com",
            password=PASSWORD,
            bcrypt_rounds=settings.bcrypt_rounds,
        )["user"]

    return _make


@pytest.fixture
def fund(conn, admin):
    def _fund(user_id: str, amount_paise: int) -> dict:
        view, _ = fund_wallet(
            conn,
            admin_user_id=admin["user_id"],
            recipient_user_id=user_id,
            amount_paise=amount_paise,
            idempotency_key=new_key(),
        )
        return view

    return _fund
