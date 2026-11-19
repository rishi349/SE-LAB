from app.main import DEMO_PAGE


def test_demo_page_is_served(client):
    response = client.get("/demo")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Ledger Wallet" in response.text
    assert "/api/v1" in response.text


def test_root_redirects_to_demo(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code in (302, 307)
    assert response.headers["location"] == "/demo"


def test_demo_page_is_not_part_of_the_api_spec(client):
    paths = client.get("/api/v1/openapi.json").json()["paths"]
    assert "/demo" not in paths and "/" not in paths


def test_demo_page_uses_integer_paise_and_no_external_scripts():
    html = DEMO_PAGE.read_text(encoding="utf-8")
    assert "parseFloat" not in html  # amounts are converted to paise with integer maths
    assert "<script src=" not in html  # works offline, nothing loaded from a CDN
