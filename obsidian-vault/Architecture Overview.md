---
tags: [architecture]
---
# Architecture Overview

**Modular monolith**: one FastAPI app, one SQLite file. Each module = `router.py` (HTTP)
+ `service.py` (rules + SQL) + `schemas.py` (Pydantic).

Modules: auth · users · wallets · ledger · transfers · transactions · admin · reconciliation.

Key idea: services never import FastAPI → testable directly, reused by scripts.

Only `ledger/service.py` changes balances → see [[Ledger Model]].
All money operations run under `BEGIN IMMEDIATE` → see [[Concurrency]].

Run: `uvicorn app.main:create_app --factory --reload`

Related: [[Security Model]], [[Decision Log]]
