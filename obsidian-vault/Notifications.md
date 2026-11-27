---
tags: [notifications, feature]
---
# Notifications

Added after release 1.0 (decisions D26–D29). Full design: `docs/notifications-design.md`.

- In-app only. Bell + unread badge on `/demo`. No email/SMS/push.
- Events: sent (sender), received (recipient), failed (sender only, no reason), funded (user).
- Admin gets none. Users can only view + mark read.
- Written **after COMMIT** in `notify_transaction`, wrapped in try/except → a transfer never
  fails because of a notification ([[Transfer Flow]], [[Admin Funding]]).
- Replays return before the notifier → no duplicates ([[Idempotency]]).
  `UNIQUE(user_id, transaction_id, type)` is the backup guard.
- Message built on read with current names → purged users show as "a deleted user"
  ([[Account Deletion]]).
- Badge: no polling. Page load / after actions (`unread_notifications` piggybacked on
  `GET /wallets/me`) / bell opened.
- Viva: real systems use a transactional outbox + queue (Kafka/RabbitMQ) and push
  (FCM/APNs, WebSockets/SSE). Ours is the simplified best-effort version.
- Not part of the ledger; reconciliation ignores it ([[Reconciliation]]).
