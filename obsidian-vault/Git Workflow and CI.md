---
tags: [ci, git]
---
# Git Workflow and CI

`feature/*` → PR → `dev` → (stable) → `main`.

CI on push/PR to `main` and `dev`:
1. gitleaks (full history) + fail if `.env` tracked
2. Python 3.12 → install `requirements-dev.txt`
3. `ruff check .` and `ruff format --check .`
4. `pytest -q`

Protect `main` and `dev`; require both jobs green.
