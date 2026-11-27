---
name: run-checks
description: Run the project's lint and test suite exactly as CI does. Use before every commit or PR, and after any code change in app/ or tests/.
---

# Run checks

1. Activate the virtualenv (`source .venv/bin/activate`). If missing:
   `python3.12 -m venv .venv && pip install -r requirements-dev.txt`.
2. Run, in order, stopping at the first failure:
   ```bash
   ruff check .
   ruff format --check .
   pytest -q
   ```
3. If `ruff format --check` fails, run `ruff format .` and re-run step 2.
4. For a quick loop while editing financial code, run only
   `pytest tests/integration -q` first, then the full suite.
5. Report: number of tests passed/failed, and any Ruff findings with file:line.

Never "fix" a failing financial test by changing its expected numbers without checking
`docs/financial-flows.md` — the test is usually right.
