"""API-level fixtures: a FastAPI TestClient bound to the isolated test database."""

from __future__ import annotations

import itertools

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.helpers import PASSWORD, new_key

API = "/api/v1"


class ApiHelper:
    def __init__(self, client: TestClient) -> None:
        self.client = client
        self._n = itertools.count(1)

    def register(self, name: str | None = None, email: str | None = None) -> dict:
        n = next(self._n)
        response = self.client.post(
            f"{API}/auth/register",
            json={
                "name": name or f"Api User {n}",
                "email": email or f"api{n}@example.com",
                "password": PASSWORD,
            },
        )
        assert response.status_code == 201, response.text
        return response.json()

    def token(self, email: str, password: str = PASSWORD) -> str:
        response = self.client.post(
            f"{API}/auth/login", json={"email": email, "password": password}
        )
        assert response.status_code == 200, response.text
        return response.json()["access_token"]

    def headers(self, email: str, *, key: str | None = None) -> dict:
        headers = {"Authorization": f"Bearer {self.token(email)}"}
        if key:
            headers["Idempotency-Key"] = key
        return headers

    def new_user(self, name: str | None = None) -> tuple[dict, dict]:
        """Register and log in. Returns (user, auth headers)."""
        user = self.register(name)["user"]
        return user, self.headers(user["email"])

    def fund(self, admin_headers: dict, user_id: str, amount: int) -> dict:
        response = self.client.post(
            f"{API}/admin/fundings",
            json={"recipient_user_id": user_id, "amount_paise": amount},
            headers={**admin_headers, "Idempotency-Key": new_key()},
        )
        assert response.status_code == 201, response.text
        return response.json()

    def transfer(self, headers: dict, recipient: str, amount: int, key: str | None = None):
        return self.client.post(
            f"{API}/transfers",
            json={"recipient_user_id": recipient, "amount_paise": amount},
            headers={**headers, "Idempotency-Key": key or new_key()},
        )


@pytest.fixture
def client(settings):
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def api(client) -> ApiHelper:
    return ApiHelper(client)


@pytest.fixture
def admin_headers(api, admin) -> dict:
    return api.headers(admin["email"])


__all__ = ["API", "PASSWORD"]
