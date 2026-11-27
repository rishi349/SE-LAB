---
name: add-endpoint
description: How to add or change a REST endpoint in this FastAPI modular monolith while keeping auth, error format, validation and docs consistent.
---

# Add an endpoint

1. **Pick the module** under `app/modules/<feature>/`. Don't create a new module unless the
   feature is genuinely new.
2. **Schema** (`schemas.py`): Pydantic model with `model_config = ConfigDict(extra="forbid")`.
   Amounts: `int` with `strict=True`. Normalise input with helpers from `app/core/validators.py`.
3. **Service** (`service.py`): plain function taking `conn` first. No FastAPI imports.
   Raise errors from `app/core/errors.py` (`ValidationFailed`, `NotFound`, `Conflict`, …).
   Use `write_transaction(conn)` for any write.
4. **Router** (`router.py`):
   - path under the module prefix; final URL is `/api/v1/...`
   - auth dependency: `get_current_user`, `require_ordinary_user` or `require_admin`
   - add `rate_limit_by_user("<scope>")` / `rate_limit_by_ip` for sensitive operations and
     register the scope in `app/core/rate_limit.py::RATE_LIMITS`
   - set `status_code`, `response_model`, `summary`, and `responses` for error codes
5. Register a new router in `app/main.py` (only if you created a new module).
6. **Tests:** service test in `tests/integration`, HTTP test in `tests/api` covering success,
   401, 403 (wrong role), 404/ownership and 422.
7. **Docs:** add the row to `docs/api.md`. Run the `run-checks` skill.
