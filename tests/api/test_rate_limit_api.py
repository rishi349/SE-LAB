from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app.core.rate_limit import RATE_LIMITS
from app.main import create_app
from tests.api.conftest import API


@pytest.fixture
def limited_client(settings):
    app = create_app(replace(settings, rate_limit_enabled=True))
    with TestClient(app) as test_client:
        yield test_client


def test_login_is_rate_limited(limited_client):
    limit, _ = RATE_LIMITS["login"]
    payload = {"email": "nobody@example.com", "password": "wrong-password"}
    statuses = [
        limited_client.post(f"{API}/auth/login", json=payload).status_code for _ in range(limit + 1)
    ]
    assert statuses[:limit] == [401] * limit
    assert statuses[-1] == 429
    blocked = limited_client.post(f"{API}/auth/login", json=payload)
    assert blocked.json()["error"]["code"] == "RATE_LIMITED"
    assert "Retry-After" in blocked.headers


def test_unknown_route_uses_error_envelope(limited_client):
    response = limited_client.get(f"{API}/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
