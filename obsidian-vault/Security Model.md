---
tags: [security]
---
# Security Model

- bcrypt passwords (8–72 bytes). JWT HS256, 1 h, no refresh. Secret ≥ 32 chars from env.
- Role + status re-read from DB every request → forged `role` claim does nothing;
  deactivated user's token dies immediately.
- No API path creates admins or changes roles; DB trigger blocks `UPDATE users.role`.
- Ownership: others' transactions → 404.
- Generic login error; dummy bcrypt check for unknown emails (timing).
- Failure reasons hidden ([[Failed Transfer Attempts]]); validation errors don't echo input.
- Rate limits on register/login (per IP) and money/admin actions (per user).
- Logs: method, path, status, ms. Nothing else.
- CI: gitleaks + "no tracked .env" ([[Git Workflow and CI]]).
