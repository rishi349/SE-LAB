"""Idempotency-Key header validation.

Semantics (see docs/financial-flows.md):
* Keys are scoped to the initiating user and stored on the transaction row
  (UNIQUE(sender_user_id, idempotency_key)).
* A repeated key returns the originally stored transaction and never executes again.
* A transfer attempt that FAILED for a business reason is stored, so its key is consumed.
* Requests rejected before execution (malformed body/header, auth errors) store nothing
  and do not consume the key.
* No payload fingerprinting: a reused key returns the original result whatever the body.
"""

from __future__ import annotations

from app.core.errors import ValidationFailed
from app.core.validators import IDEMPOTENCY_KEY_RE

IDEMPOTENCY_HEADER = "Idempotency-Key"
REPLAY_HEADER = "Idempotent-Replayed"


def require_idempotency_key(value: str | None) -> str:
    if value is None or value.strip() == "":
        raise ValidationFailed(
            f"The {IDEMPOTENCY_HEADER} header is required.", code="IDEMPOTENCY_KEY_REQUIRED"
        )
    if not IDEMPOTENCY_KEY_RE.match(value):
        raise ValidationFailed(
            f"{IDEMPOTENCY_HEADER} must be 8-128 characters of letters, digits, '-' or '_'.",
            code="IDEMPOTENCY_KEY_INVALID",
        )
    return value
