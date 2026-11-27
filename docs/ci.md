# CI & Git workflow

## Pipeline — `.github/workflows/ci.yml`

Triggers on pushes and pull requests to `main` and `dev`.

| Job | Steps |
|---|---|
| **Secret scanning** | full-history checkout → gitleaks (`.gitleaks.toml` extends the default rules) → fail if any `.env` file is tracked |
| **Ruff + Pytest** | set up Python 3.12 → `pip install -r requirements-dev.txt` → `ruff check .` → `ruff format --check .` → `pytest -q` |

Any failing step fails the pipeline. CI uses a throwaway `JWT_SECRET`; tests create their
own temporary databases, so nothing persists between runs.

## Branches

```
feature/<short-name>  ──PR──▶  dev  ──(when stable)──▶  main
```

* `main` — stable, always passing CI.
* `dev` — integration branch; all feature PRs target `dev`.
* `feature/*` — one feature or fix per branch, opened from `dev`.
* Merge `dev` → `main` only when CI is green and the build is considered stable.

Recommended GitHub settings: protect `main` and `dev`, require the two CI jobs to pass
before merge, require one review.

## Commit messages
Short imperative subject (`Add daily transfer limit check`), body explaining *why* when it
isn't obvious.
