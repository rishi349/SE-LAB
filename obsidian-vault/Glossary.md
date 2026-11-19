---
tags: [glossary]
---
# Glossary

- **Paise** — 1/100 rupee; the only money unit in code and DB.
- **User ID** — permanent public ID like `USR7K2M9Q4XAB`; used for lookup and funding.
- **Transaction** — one transfer attempt (SUCCESS/FAILED) or one admin funding.
- **Ledger entry** — immutable DEBIT or CREDIT on one wallet for one transaction.
- **Admin funding** — admin credits a user wallet; no debit anywhere ([[Admin Funding]]).
- **Idempotency key** — client-chosen header that makes retries safe ([[Idempotency]]).
- **IST day** — calendar day in `Asia/Kolkata`; basis of the daily limit.
- **Reconciliation run** — read-only integrity check with a stored report ([[Reconciliation]]).
- **Deactivated** — account closed, waiting 7 days for personal-data deletion ([[Account Deletion]]).
