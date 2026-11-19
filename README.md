# Financial Ledger & Digital Wallet API

A REST API for digital wallets: users register (a ₹0 wallet is created automatically), an
admin funds wallets for testing, users send money to each other, and every movement is
recorded in an immutable debit/credit ledger that can be reconciled at any time.

**Stack:** Python 3.12 · FastAPI · SQLite (built-in `sqlite3`, direct SQL, no ORM) ·
JWT (HS256) · bcrypt · Pytest · Ruff · GitHub Actions. Modular monolith.

**Money rule:** every amount is an integer number of **paise** (`₹1 = 100 paise`). Floats
are rejected everywhere.

---

## Quick start

```bash
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

cp .env.example .env               # then set JWT_SECRET to a long random value:
python -c "import secrets; print(secrets.token_urlsafe(48))"

python -m scripts.create_admin --name "Test Admin" --email admin@example.com
uvicorn app.main:create_app --factory --reload
```

Then open:

* **<http://127.0.0.1:8000/demo>** — demo web page (log in, send money, history, admin funding,
  reconciliation, plus a live log of every API call). `/` redirects here.
* **<http://127.0.0.1:8000/docs>** — Swagger documentation for calling endpoints directly.

> Windows/Miniconda: if `python3.12` or `py` is not found, use `python` instead, and run the
> server with `python -m uvicorn app.main:create_app --factory --reload`.

### Run the checks

```bash
ruff check .
ruff format --check .
pytest -q
```

---

## What it does

| Area | Endpoints (prefix `/api/v1`) |
|---|---|
| Auth | `POST /auth/register`, `POST /auth/login` |
| Profile | `GET /users/me`, `PATCH /users/me`, `POST /users/me/deletion-request`, `GET /users/{user_id}` |
| Wallet | `GET /wallets/me` |
| Transfers | `POST /transfers` (needs `Idempotency-Key`) |
| History | `GET /transactions`, `GET /transactions/{transaction_id}` |
| Admin | `GET /admin/users/{user_id}`, `POST /admin/fundings` (needs `Idempotency-Key`) |
| Reconciliation | `POST/GET /admin/reconciliation-runs`, `GET /admin/reconciliation-runs/{run_id}` |
| Health | `GET /health` |
| Demo page | `GET /demo` (static page, not part of the API) |

Key rules: ₹50,000 maximum per transfer, ₹1,00,000 successful outgoing per IST day
(resets at midnight `Asia/Kolkata`), no self-transfers, failed attempts are stored and shown
in history without their reason, name changes once every 60 days, and account deletion
needs a ₹0 balance plus a 7-day waiting period.

## Project layout

```
app/
  main.py              application factory, router registration, request logging
  static/demo.html     demo client page (vanilla HTML/JS, calls /api/v1 only)
  config.py            settings from environment / .env
  core/                errors, security (bcrypt/JWT), deps, money, clock, ids, rate limit
  db/                  schema.sql + connection and transaction helpers
  modules/
    auth/ users/ wallets/ transfers/ transactions/ ledger/ admin/ reconciliation/
scripts/               create_admin.py, purge_deactivated_accounts.py
tests/                 unit/  integration/  api/
docs/                  architecture, database, API, financial flows, security, testing, CI, decisions
.claude/skills/        Agent Skills for working on this repo
obsidian-vault/        Obsidian "second brain" engineering notes
.github/workflows/     CI pipeline
```

## Documentation

* [Architecture](docs/architecture.md)
* [Database](docs/database.md)
* [API](docs/api.md)
* [Financial flows](docs/financial-flows.md)
* [Security](docs/security.md)
* [Testing](docs/testing.md)
* [CI & Git workflow](docs/ci.md)
* [Engineering decisions & assumptions](docs/decisions.md)

## Out of scope

Notifications (email/SMS/push), refresh tokens, scheduled reconciliation, wallet freezing,
multi-currency, and any external payment gateway.
