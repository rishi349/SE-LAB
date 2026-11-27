---
tags: [limits, time]
---
# Daily Limit and IST

- ₹1,00,000 = 10,000,000 paise of **successful outgoing transfers** per IST day.
- Day = `Asia/Kolkata` calendar day; resets at IST midnight (= 18:30 UTC previous day).
- Implemented in `clock.ist_day_window(now)` → [start, end) in UTC, then
  `SUM(amount)` over SUCCESS TRANSFER rows of the sender.
- Read under the write lock, so concurrent transfers can't jointly exceed it ([[Concurrency]]).
- Gotcha: 00:30 IST and 06:00 IST are different UTC dates but the same IST day — tested.
- `tzdata` is in requirements so Windows machines know `Asia/Kolkata`.

Admin funding is excluded ([[Admin Funding]]).
