# Financial Ledger & Digital Wallet API --- Architecture Document

**Project:** Financial Ledger & Digital Wallet API  
**Team:** Paradise  
**Architecture status:** Phase 1 and Phase 3 finalized; Phase 2 reserved  
for database design by a teammate.

This document consolidates the architecture decisions made so far. It is  
an architecture reference, not an implementation prompt.

---

## Architecture Progress

Phase Area Status

---

Phase 1 Technology Stack and Project Foundation Finalized  
Phase 2 Database Design Reserved for teammate  
Phase 3 Security, Authentication and Permissions Finalized

---

# Phase 1 --- Technology Stack and Project Foundation

## 1.1 Technology Decisions

Component Selected technology

---

Programming language Python 3.12  
Backend framework FastAPI  
Architecture Modular monolith  
Database SQLite  
Database access Python built-in `sqlite3`  
ORM No ORM; direct SQL  
API style REST  
API version `/api/v1/`  
Application server Uvicorn  
API documentation FastAPI Swagger UI (`/docs`)  
Dependency management `requirements.txt`  
Virtual environment Python `venv`  
Testing Pytest  
Linting and formatting Ruff  
Environment configuration `.env`, `python-dotenv`, `os.environ`

The backend will be a modular monolith: one application with separate  
modules for authentication, users, wallets, transfers and accounting.

This keeps development straightforward while allowing modules to be  
extracted into separate services in the future if necessary.

The architecture will separate API handling, business/accounting logic  
and persistence responsibilities.

## 1.2 Initial Project Structure

```
financial-ledger-api/
│
├── app/
│   ├── main.py
│   │
│   ├── routers/
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── wallets.py
│   │   └── transfers.py
│   │
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── user_service.py
│   │   ├── wallet_service.py
│   │   └── transfer_service.py
│   │
│   ├── database/
│   │
│   ├── models/
│   │
│   └── schemas/
│
├── tests/
│
├── .env
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

The exact database files and models will be coordinated with Phase 2.

## 1.3 Git and GitHub Workflow

Branch Purpose

---

`main` Stable version  
`dev` Integration branch  
`feature/*` Individual feature development

- Development happens in feature branches.
- Pull requests merge into `dev`.
- Once stable and tested, `dev` is merged into `main`.

## 1.4 Configuration and Secrets

- Store configuration and secrets in `.env`.
- Provide `.env.example` with placeholders.
- Never commit `.env` to GitHub.
- Keep database files, virtual environments and logs out of Git.
- Never hardcode passwords or JWT signing secrets in source code.
- Do not paste credentials, API keys or other secrets into AI tools.

---

# Phase 2 --- Database Design
ROLE AND SCOPE
Implement ONLY Phase 2 (Database management) of the Financial Ledger & Digital Wallet API course project.
Language/framework: [FILL IN - not decided yet]. Database: SQLite (final).
Follow this spec exactly. If anything is not specified here, STOP AND ASK - do not assume or add features.
This is a 1-credit course project: keep it simple, no extra scaling or abstractions.

## IN SCOPE
1. SQLite connection setup
2. One initial migration: 5 tables, indexes, 4 triggers
3. Migration runner
4. Admin seed step
5. Write-transaction helper and read-transaction helper
6. Database-level tests

## OUT OF SCOPE (do not build)
API endpoints, login/session logic, transfer/reversal/funding business logic, reconciliation endpoint, password-hashing algorithm, OTP, any request-digest/fingerprint feature, admin role or marker column, isSystem column, balance >= 0 database check, composite currency foreign key, currencies table, ReconciliationResult table, hash chaining.

## CONVENTIONS
- Money: INTEGER paise. No floats anywhere.
- IDs: UUID stored as TEXT. Timestamps: UTC ISO-8601 TEXT, supplied by the application.
- Only currency is INR: every currency column is TEXT NOT NULL with CHECK (currency = 'INR').
- Tables are plural snake_case, columns snake_case. No ON DELETE CASCADE anywhere.

## SCHEMA
users: user_id PK; display_name NOT NULL; email NOT NULL UNIQUE; password_hash NOT NULL; created_at NOT NULL.
wallets: wallet_id PK; user_id NOT NULL FK->users; currency (INR check); balance INTEGER NOT NULL DEFAULT 0 (no sign check); created_at; UNIQUE(user_id, currency).
transactions: transaction_id PK; seq INTEGER NOT NULL UNIQUE; type NOT NULL CHECK IN ('transfer','reversal','funding'); amount INTEGER NOT NULL CHECK > 0; currency (INR check); status NOT NULL CHECK = 'committed'; idempotency_ref NOT NULL FK->idempotency_records(id); reversal_ref NULL FK->transactions(transaction_id) UNIQUE; created_at.
ledger_entries: entry_id PK; transaction_id NOT NULL FK->transactions; wallet_id NOT NULL FK->wallets; direction NOT NULL CHECK IN ('DEBIT','CREDIT'); amount INTEGER NOT NULL CHECK > 0; currency (INR check); created_at.
idempotency_records: id PK; scope NOT NULL (caller's user_id); idempotency_key NOT NULL; response_ref NOT NULL (plain transaction_id, NO foreign key); created_at; UNIQUE(scope, idempotency_key).

## INDEXES
ledger_entries(wallet_id); ledger_entries(transaction_id). Unique constraints above create their own indexes.

## TRIGGERS (4)
BEFORE UPDATE and BEFORE DELETE on ledger_entries, and on transactions: RAISE(ABORT) with a generic "immutable" message. Do NOT add triggers to wallets, users or idempotency_records.

## CONNECTION SETTINGS
- journal_mode=WAL, set once on the database file (file-backed databases only).
- foreign_keys=ON on every connection opened.
- busy_timeout from configuration, default 5000 ms.
- Leave all other SQLite settings at defaults.

## TRANSACTION HELPERS
- Write helper: BEGIN IMMEDIATE, run the caller's work, COMMIT; ROLLBACK on any error. If the lock cannot be obtained within the timeout, raise a distinct "storage busy" error (the API layer maps it to 503 STORAGE_BUSY).
- Read helper: one read transaction so multi-row reads see a single snapshot.

## MIGRATIONS AND SEED
- Numbered SQL files (0001_initial.sql). Runner reads PRAGMA user_version, applies pending files in order, sets user_version.
- Admin seed is a separate step, idempotent (skip if the admin already exists). Admin email and password come from environment variables, never committed. Create one users row plus one INR wallet with balance 0. Password hashing uses an injected hasher (provider interface); do not choose an algorithm.

## CONTRACT FOR OTHER PHASES (document in a README or code comment)
- Every money-moving operation runs inside the write helper.
- Insert order: wallet row (wallet creation only, balance 0), idempotency_records, transactions, two ledger_entries, then balance updates. Pre-generate transaction_id so response_ref can be stored first.
- seq = (SELECT COALESCE(MAX(seq),0)+1 FROM transactions), computed inside the write lock.
- Initial funding happens at wallet creation: DEBIT admin wallet, CREDIT new wallet, same transaction.
- Same key found for the same scope: return the stored result. No payload comparison.
- The application finds the admin through configuration (admin email), not a database column.
- Use plain INSERT on ledger_entries and transactions, never INSERT OR REPLACE.

## TESTS (database level)
- Migration applies on a fresh database; user_version is set; seed is idempotent.
- foreign_keys is on: an entry with an unknown wallet or transaction fails.
- CHECKs reject amount <= 0, a bad direction, a non-INR currency, a status other than committed.
- Unique constraints: email, (user_id, currency), (scope, idempotency_key), reversal_ref, seq.
- Triggers block UPDATE and DELETE on ledger_entries and transactions; wallet balance UPDATE is allowed.
- Rollback: a failure midway through the write helper leaves no rows.
- Busy timeout: with a file-backed temp database, a second writer gets the storage-busy error while the first holds the lock.
- Unit tests may use in-memory databases; WAL and concurrency tests must use a temporary file.

## RULES
A human reviews every AI-generated change. Never paste or commit secrets.

---

# Phase 3 --- Security, Authentication and Role Management

## 3.1 Authentication Architecture

We will use email/password authentication with JWT access tokens.

Component Decision

---

Registration Email and password  
Login Registered users only  
Duplicate email Registration rejected  
Password hashing bcrypt  
Token type JWT access token  
Signing algorithm HS256  
Token expiry 1 hour  
Refresh token Not implemented  
Secret storage `.env`

### Registration Flow

1. A new user submits an email address and password.
2. The system validates that the email is not already registered.
3. The password is hashed using bcrypt.
4. The system creates the user account and associated wallet.
5. The system generates a unique, permanent User ID.

### Login Flow

1. The user submits their registered email and password.
2. The server verifies the account and password.
3. The server generates a JWT access token.
4. The client receives the token.
5. The client includes the token in protected API requests.

Example:

```
Authorization: Bearer <JWT_ACCESS_TOKEN>
```

The server verifies the token signature and expiry before allowing  
access to protected endpoints.

## 3.2 User Roles

There will be exactly two roles:

- `user`
- `admin`

### A. Ordinary User

Feature Permission

---

Register Yes  
Login Yes  
Receive unique User ID Yes  
Search recipients User ID or email  
Send money Yes  
View transaction history Own sent and received transactions only  
Check balance Own wallet only  
Request account deletion Yes, subject to closure rules

### B. System Funding Admin

There will be one predetermined admin account.

The admin is specifically designed for initial wallet funding and  
application testing.

#### Admin's permitted operations

- Search users by User ID or email.
- View basic recipient identification details (name and User ID).
- Transfer funds from the System Funding Wallet to a user's wallet.

#### Admin's restricted operations

- Cannot view users' personal or sensitive data.
- Cannot access users' JWT tokens.
- Cannot view users' transaction histories.
- Cannot check users' wallet balances.
- Cannot perform normal user-to-user transfers.
- Cannot create additional admin accounts.

The admin account will be provisioned through a controlled initial  
setup. Credentials will not be hardcoded into source code.

## 3.3 System Funding Wallet

The System Funding Wallet will have an initial allocation of  
**₹5,00,000**.

Setting Value

---

Initial funding allocation ₹5,00,000  
Currency INR  
Integer-paise representation 50,000,000 paise  
Funding source System Funding Wallet  
Funding method Recorded debit and credit ledger entries

The initial ₹5 lakh must be represented through a properly recorded  
opening ledger balance, not created through an unrecorded balance  
update.

### Admin Funding Process

1. Admin logs in using the predetermined admin account.
2. Admin searches for a registered user.
3. Admin identifies the recipient using their name and User ID.
4. Admin enters the funding amount.
5. The system checks the available funding-wallet balance.
6. The system debits the System Funding Wallet.
7. The system credits the recipient's wallet.
8. Both sides of the funding operation are recorded in the ledger.

The admin cannot distribute more than the available funding allocation.

## 3.4 User Identification and Recipient Search

Every registered user receives a unique identifier.

Example:

```
User A: USR-10001
User B: USR-10002
```

User ID rules:

- Automatically generated by the system.
- Unique and permanent.
- Cannot be edited by users.
- Used for identification, not authentication.

Users can search for recipients using either:

1. Unique User ID.
2. Registered email address.

The system displays the recipient's name and User ID before the sender  
confirms the payment.

## 3.5 Wallet and Payment Rules

Rule Finalized decision

---

Supported currency INR only  
Money representation Integer paise  
Maximum per transaction ₹50,000  
Maximum outgoing amount per day ₹1,00,000  
Recipient identification User ID or email  
Balance access Own wallet only  
Transaction history Own sent and received transactions

### Money Representation

All monetary values will be stored as integer paise.

Example:

- ₹100.50 = `10050` paise.
- ₹1 = `100` paise.

Floating-point arithmetic will not be used for financial amounts.

### Daily Transaction Limit

- Maximum successful outgoing transfers per user per day: ₹1,00,000.
- Once the limit is reached, further outgoing transfers are rejected  
    until the next daily period.
- Failed or rejected transactions do not consume the daily limit.
- The daily limit is calculated across all successful outgoing  
    transfers by that user.

### Transfer Security and Integrity

- The sender must own the source wallet.
- The recipient must be a valid registered user.
- The sender must have sufficient funds.
- Negative and zero amounts are rejected.
- Every successful transfer must have matching debit and credit ledger  
    entries.
- A transfer must be atomic: either all required financial changes  
    commit or none do.
- Idempotency protection must prevent duplicate transfers on retries.
- The wallet balance must not become negative.
- The stored wallet balance must agree with the balance calculated  
    from ledger entries.

## 3.6 Transaction History Privacy

Users can view:

- Their outgoing transactions.
- Their incoming transactions.

They cannot view another user's complete transaction history.

Example: if User A sends ₹500 to User B:

User What they see

---

A Sent ₹500 to B  
B Received ₹500 from A  
C Cannot see this transaction

## 3.7 Account Deletion

We will implement a deactivation and delayed deletion process.

---

Stage Behaviour

---

Deletion request User requests account closure

Balance settlement Remaining balance must be withdrawn  
or transferred

Deactivation Account becomes inactive

7-day period Account remains deactivated

After 7 days Eligible personal account data is  
permanently deleted, subject to  
applicable retention requirements

## Ledger records Preserved permanently

Additional rules:

- Deactivated users cannot log in or initiate transfers.
- Financial transaction records are never deleted.
- Deleting one user's account must not affect another user's  
    transaction history.
- Historical records must retain enough references to support auditing  
    and reconciliation.

**Operational clarification:** The deletion request should only enter  
the 7-day deactivation period after the remaining wallet balance has  
been settled. This avoids disabling transfers before the user has had a  
chance to settle their balance.

## 3.8 General Security Safeguards

- JWT verification for protected endpoints.
- Role-based authorization.
- Wallet ownership checks.
- Input validation using FastAPI/Pydantic.
- Parameterized SQL queries.
- Secure environment-variable handling.
- Generic client-facing errors.
- Logging without passwords, tokens, SQL text or sensitive request  
    bodies.
- HTTPS outside trusted local development.
- Secret scanning in the CI pipeline.

---

## Overall Architecture Overview

The following is the high-level logical architecture connecting the  
three phases. Phase 2 remains a placeholder until the database design is  
supplied.

```
                  API CLIENTS
             (User / System Admin)
                       |
                       v
                FASTAPI REST LAYER
          (Authentication, validation, routing)
                       |
                       v
             SECURITY & AUTHORIZATION
        (JWT / HS256 / bcrypt / role checks /
                 wallet ownership checks)
                       |
                       v
              BUSINESS LOGIC LAYER
          +------------+-------------+
          |            |             |
          v            v             v
      User Service  Wallet Service  Transfer Service
          |            |             |
          +------------+-------------+
                       |
                       v
                  LEDGER SERVICE
                       |
                       v
             PHASE 2: DATABASE LAYER
              (Design pending)
                       |
                       v
                    SQLite
```

## Final Decision Summary

---

Phase Status Main outcome

---

Phase 1 Finalized Python + FastAPI +  
SQLite technology  
foundation

Phase 2 Reserved Database design by  
teammate

## Phase 3 Finalized Authentication, roles,  
permissions and  
security

## Next Steps

1. Obtain and review the database design from the teammate handling  
    Phase 2.
2. Integrate Phase 2 with this architecture without changing its agreed  
    schema independently.
3. Design the remaining architecture phases.
4. Consolidate all finalized phases into one complete architecture  
    reference.
5. Only after architecture is finalized, prepare Claude implementation  
    prompts phase by phase.
6. Implement and test each phase before moving to the next.

---

**Document note:** This document records the decisions made so far. It  
does not claim that implementation, testing, CI, Agent Skills or other  
project deliverables have been completed.




# Phase 4 ---FINANCIAL TRANSACTION

Implement ONLY Phase 4 (Financial transaction management) of the Financial Ledger & Digital Wallet API course project: the service layer for money movement, built on the existing Phase 2 database layer.
Language/framework: [FILL IN - not decided yet].
Follow this spec exactly. If anything is not specified here, STOP AND ASK - do not assume or add features.
This is a small course project: keep it simple, no extra scaling or abstractions.

## IN SCOPE
1. Amount validation and idempotency-key validation
2. Transfer service
3. Wallet-creation-with-admin-funding service
4. Balance arithmetic with overflow checks
5. Idempotent replay (look up and rebuild stored results)
6. Domain errors carrying the codes below (the API layer maps them to HTTP)
7. Tests

## OUT OF SCOPE (do not build)
Schema changes or migrations (use Phase 2 as is; if a change seems needed, stop and ask), HTTP routing, login/session logic, password hashing, reconciliation endpoint, reversal workflow, any request-digest/fingerprint feature, key-reuse 409, OTP, admin role or marker column, balance bounds or maximum amounts, background workers, queues, pending states, per-wallet locks, savepoints, server-side retry loops.

## CONVENTIONS (carried from Phase 2)
Money is integer paise, never floats. Only currency is INR. IDs are UUID text. Timestamps are UTC ISO-8601 text supplied by the application. Use the Phase 2 write helper (BEGIN IMMEDIATE) for every money-moving request and the read helper for multi-row reads.

## ACCOUNTING CONVENTION (SRS 3.1, BR-3 to BR-7)
Wallet balance = sum of CREDIT amounts minus sum of DEBIT amounts. DEBIT = money leaves the wallet, CREDIT = money enters. Entry amounts are always positive; direction is the only sign. Every transaction has total DEBIT equal to total CREDIT.
Transfer: DEBIT source, CREDIT destination. Funding: DEBIT admin wallet, CREDIT new wallet.

## AMOUNT VALIDATION (BR-1, API-4, FR-2.10)
- Accept only a JSON integer paise value greater than 0.
- Reject with 400 INVALID_AMOUNT (detail rule: must_be_positive_integer_minor_units): zero, negative, fractional, strings, null, booleans, and forms like 10.0 or 1e2.
- Missing amount: 400 VALIDATION_ERROR.
- Request currency must be INR, otherwise 422 CURRENCY_MISMATCH.
- No business maximum. The only upper bound is the signed 64-bit integer range; anything beyond it is 400 INVALID_AMOUNT.

## IDEMPOTENCY (API-5, FR-2.2 to FR-2.14)
- Header Idempotency-Key is required for transfer and wallet creation. Missing: 400 MISSING_IDEMPOTENCY_KEY. Invalid: 400 INVALID_IDEMPOTENCY_KEY. Valid format: 1 to 64 characters from letters, digits, hyphen, underscore.
- Namespace: (scope = caller's user_id, key), exact and case-sensitive. Retention: lifetime of the database, no cleanup job.
- Replay: inside the write transaction, if (scope, key) exists, return the stored result rebuilt from the transaction that response_ref points to, with the identical status and body as the original. Do NOT compare request content.
- A key is consumed only by a committed request. Rejected requests leave no idempotency record.
- Concurrent same-key requests: the write lock serializes them, the second one replays. The unique constraint is the backstop.

## TRANSFER WORKFLOW (SRS 4.5, FR-2, FR-3.4)
Before the database transaction: caller identity comes from the API layer; validate source and destination wallet IDs (UUID), amount, currency, and the idempotency key.
Inside one write transaction:
1. BEGIN IMMEDIATE. If the lock is not obtained within the busy timeout: 503 STORAGE_BUSY.
2. Idempotency lookup; replay if found.
3. Validate in this order: wallets exist (404 NOT_FOUND), source differs from destination (422 SAME_WALLET_TRANSFER), currencies match (422 CURRENCY_MISMATCH), caller owns the source wallet (403 FORBIDDEN, BR-14), source balance >= amount (422 INSUFFICIENT_FUNDS). All reads happen after the lock is held.
4. Write in this order: idempotency_records, transactions (type transfer, seq), DEBIT entry on source, CREDIT entry on destination, both balance updates.
5. COMMIT, then return 201 with: transaction, source and destination wallets, amount, currency, status, created_at, both ledger entries (SRS 4.3).
Any failure or rejection: full ROLLBACK, nothing written.

## ATOMICITY AND CONCURRENCY (SRS 3.2, FR-3, BR-8)
One write transaction per request, one commit point, response only after COMMIT succeeds. No savepoints, no server-side retry; the client retries with the same key. Whole-database write lock only, no per-wallet locks. Unexpected errors: 500 INTERNAL_ERROR with no SQL, stack traces or file paths.
Transaction order (seq): inside the write transaction, after the write lock is held, set seq = COALESCE(MAX(seq), 0) + 1 over the transactions table. It starts at 1 and is never reused. seq is NOT NULL; the UNIQUE constraint is the backstop.

## BALANCE ARITHMETIC AND OVERFLOW (BR-6, BR-13, NFR-REL-5)
- Funds check: balance >= amount (ending at exactly 0 is allowed). The database has no balance check, so this is the only guard for BR-6.
- Exempt only the funding debit on the admin wallet (it goes negative). The admin's ordinary transfers are checked like anyone's.
- Compute new balances in the application with exact integers, range-check against signed 64-bit, then write the absolute value. NEVER write "balance = balance + ?" in SQL (SQLite turns integer overflow into floating point).
- Overflow (destination above the maximum, admin below the minimum): reject, roll back, 400 INVALID_AMOUNT.
- Any aggregate sums must detect overflow too.

## SYNCHRONOUS BEHAVIOR
Every request completes inside its own HTTP call: no queues, no background workers, no pending state. A 2xx response means the movement is committed; any error response (4xx, 500, 503) means nothing was written. Busy timeout 5000 ms from configuration. Reads never wait for writers. Transaction status is always "committed".
If the team uses Python/FastAPI: database-backed handlers are plain def (or run in a worker thread) so lock waits do not block the event loop, and each request uses its own connection.

## ADMIN FUNDING AT WALLET CREATION (FR-1.5 to FR-1.7)
Configuration: admin email, and initial funding amount (positive integer paise, validated at startup).
Funding transactions are created ONLY inside the wallet-creation transaction. Do not write any other function or endpoint that creates a funding transaction.
In one write transaction:
1. BEGIN IMMEDIATE, idempotency lookup, replay if found.
2. Validate: user exists (404 NOT_FOUND), currency is INR (else 400 VALIDATION_ERROR), user has no wallet yet (409 WALLET_ALREADY_EXISTS), admin wallet exists (else 500 INTERNAL_ERROR).
3. Write in this order: wallet row (balance 0), idempotency_records, transactions (type funding, amount = configured amount, seq), DEBIT on admin wallet, CREDIT on new wallet, both balance updates (overflow-checked, no funds check on the admin debit).
4. COMMIT, then return the wallet: wallet_id, user_id, currency, balance, created_at.
Replay: return that wallet's current details, found through the funding transaction's CREDIT entry.
The admin's own wallet is created by the Phase 2 seed with balance 0 and is never funded.

## ERROR CODES (SRS 4.4 format; no internal details exposed)
400 VALIDATION_ERROR, INVALID_AMOUNT, MISSING_IDEMPOTENCY_KEY, INVALID_IDEMPOTENCY_KEY
403 FORBIDDEN | 404 NOT_FOUND | 409 WALLET_ALREADY_EXISTS
422 INSUFFICIENT_FUNDS, CURRENCY_MISMATCH, SAME_WALLET_TRANSFER
500 INTERNAL_ERROR | 503 STORAGE_BUSY
(401 UNAUTHENTICATED belongs to the API layer.)

## TESTS (SRS TQ-1 to TQ-6)
- Unit: amount validation (zero, negative, fractional, string, 10.0, over the 64-bit limit), key-format validation, overflow arithmetic.
- Integration: transfer commits with balanced entries and correct balances; replay creates no second transaction; rejected requests leave no idempotency record; rollback with a failure injected between the DEBIT and CREDIT inserts leaves no rows and unchanged balances.
- Funding: after wallet creation the admin balance is negative by the funded amount, the new wallet holds it, entries balance, the sum of all balances is 0, wallet-creation replay works, a duplicate wallet is rejected.
- Funding concurrency: two concurrent wallet-creation requests for the same user with different keys: exactly one succeeds, the other gets 409, and only one funding transaction exists.
- Concurrency (temporary file-backed database, threads): two transfers over the balance, only one succeeds; same-key concurrent requests, one transaction; incoming and outgoing on one wallet equal the serial result; the storage-busy path.
- Negative: insufficient funds, same wallet, currency mismatch, wrong owner (403 and no changes), unknown wallet, invalid or missing key.

## RULES
A human reviews every AI-generated change. Never paste or commit secrets. Use plain INSERT on ledger tables.
Document these departures from the SRS in the README: no request-digest feature and no key-reuse 409 (replay instead); funding at wallet creation; INR only; no reversal workflow (schema columns kept unused); added code WALLET_ALREADY_EXISTS; dropped IDEMPOTENCY_KEY_REUSED and ALREADY_REVERSED; response-time target still TBD (C-9).
# ***Phase* 5 --- API Management & Design**

Status: Design finalized

Phase 5 defines how clients interact with the Financial Ledger & Digital Wallet API. The API follows a **hybrid design**, combining resource-oriented operations with action-oriented endpoints for financial operations, organized using **role-based and domain-based grouping**.

## **1. API Architecture**

|Decision|Design|
|---|---|
|API style|REST|
|Architecture|Hybrid resource + action based|
|API versioning|`/api/v1/`|
|Grouping|Role-based + domain-based|
|Resource hierarchy|Not used|
|Backend framework|FastAPI|
|API documentation|OpenAPI / Swagger UI|
|Communication|JSON over HTTP|

## **2. Authentication & Identity**

Authentication endpoints cover account registration, login, and retrieval of the currently authenticated user's identity.

|Operation|Access|
|---|---|
|Register|Public|
|Login|Public|
|Get current user|Authenticated|

- Email + password authentication
    
- Password hashing with bcrypt
    
- JWT access tokens (HS256)
    
- Token expiry: 1 hour
    
- No refresh token
    
- Role-based authorization: `user` / `admin`
    

## **3. User & Profile Management**

Profile viewing and editing are separate operations.

|Operation|Access|Rules|
|---|---|---|
|View profile|User|View name, email, user ID, account ID (if applicable)|
|Edit profile|User|Name editable only|
|Change name|User|Once every 60 days, starting after a successful name change|
|Email change|—|Not allowed|
|User ID change|—|Not allowed|
|Account ID change|—|Not allowed|
|Account deletion request|User|Subject to settlement, deactivation, and retention rules|

## **4. Wallet Management**

|Operation|Design|
|---|---|
|Create wallet|Separate operation|
|View wallet|Wallet details and balance together|
|Freeze wallet|User can freeze their own wallet|
|Freeze duration|1 hour|
|Unfreeze|Automatic after 1 hour|
|Manual unfreeze|Not allowed|
|Frozen wallet incoming transfers|Blocked|
|Frozen wallet outgoing transfers|Blocked|
|Other wallet operations|Blocked while frozen, except viewing|
|Wallet deletion|Not allowed|

### **Frozen wallet behavior**

- User can still view their wallet and balance.
    
- Incoming and outgoing financial operations are blocked.
    
- Other wallet operations are restricted.
    
- Wallet automatically becomes unfrozen after one hour.
    

## **5. Transfer Management**

Transfers follow financial transaction principles and must satisfy **ACID, atomicity, and idempotency**.

|Rule|Design|
|---|---|
|Transfer execution|One-sided operation|
|Recipient online requirement|None|
|Atomicity|Either completely succeeds or fails|
|ACID|Required|
|Idempotency|Required|
|Balance validation|Sufficient funds required|
|Negative/zero amount|Rejected|
|Self-transfer|Rejected|
|Frozen wallets|Cannot send or receive|
|Failed transfer|No money movement|
|Automatic retry for insufficient funds|None|
|Ledger entries|Balanced debit and credit for every successful transfer|

### **Transfer limits**

|Limit|Maximum|
|---|---|
|Per transfer|₹50,000|
|Daily outgoing transfers|₹1,00,000|
|Failed transfers counted toward limits|No|

### **Failure behavior**

- Insufficient funds → reject transfer.
    
- Validation failure → reject transfer.
    
- Frozen wallet → reject transfer.
    
- Failed transfers must not modify wallet balances.
    
- Failed attempts must still be stored in transaction history.
    
- Actual internal failure reasons are not exposed to the sender or recipient.
    

### **Notifications**

- Recipient doesn't need to be online to receive money.
    
- Recipient is notified of successful transfers.
    
- Notification failure does not undo a successful transfer.
    

## **6. Transaction History & Audit Visibility**

Transaction history contains both successful transfers and failed attempts.

|Feature|Design|
|---|---|
|History scope|Incoming and outgoing|
|Successful transactions|Visible|
|Failed attempts|Visible to both involved users|
|Failed transaction amount|Visible|
|Failure reason|Hidden from both users|
|Transaction ID|Available|
|Sender/recipient|Identifiable|
|Date/time|Recorded|
|Status|Success or Failed|
|Default ordering|Newest first|
|Pagination|Supported|
|Filtering|Date, status, direction|
|Transaction modification|Not allowed|
|Transaction deletion|Not allowed|

### **Privacy**

- Sender sees their outgoing transaction.
    
- Recipient sees the corresponding incoming transaction attempt.
    
- Unrelated users cannot see either transaction.
    
- Failed attempts are visible to both parties, but internal failure reasons are kept private.
    

## **7. Admin Management**

Admin functionality is deliberately limited.

|Operation|Design|
|---|---|
|Search users|By User ID or email|
|View basic identification|Name and User ID|
|Fund a user's wallet|Allowed|
|Normal user-to-user transfer|Not allowed|
|Reversal|Not supported|
|Create admin accounts|Not through normal API|
|View users' private transaction history|Not allowed|

### **System Funding Wallet**

- Initial allocation: **₹5,00,000**
    
- Admin funding must come from this allocation.
    
- Funding cannot exceed the remaining allocation.
    
- Each funding operation is recorded in the ledger.
    
- Funding must be atomic and idempotent.
    
- Admin funding is intended for controlled wallet funding and testing.
    

## **8. API Response Standards**

All API responses will follow a consistent JSON structure.

### **Success responses**

- Clear success indication.
    
- Returned data.
    
- Relevant identifiers.
    
- No inconsistent response formats between domains.
    

### **Error responses**

- Consistent error structure.
    
- Appropriate HTTP status codes.
    
- Human-readable error messages.
    
- No SQL errors, stack traces, internal failure details, or sensitive information exposed to clients.
    

## **9. Validation & HTTP Standards**

- Validate all request bodies, query parameters, IDs, and amounts.
    
- Use integer paise for monetary calculations.
    
- Reject malformed requests before financial processing.
    
- Use appropriate HTTP methods and status codes.
    
- Use standard HTTP semantics for creation, retrieval, updates, and failures.
    
- No financial operation should partially execute.
    

## **10. Pagination, Filtering & Sorting**

Used primarily for transaction history and other potentially large datasets.

|Feature|Standard|
|---|---|
|Pagination|Supported|
|Sorting|Newest first by default|
|Date filtering|Supported|
|Status filtering|Supported|
|Direction filtering|Incoming / outgoing|
|Response size|Bounded|

## **11. Idempotency & Reliability**

Idempotency is required for financial operations such as:

- User-to-user transfers
    
- Admin wallet funding
    

Repeated requests using the same idempotency key must not cause duplicate money movement. Retrying a request must not create a second financial operation.

## **12. Security Standards**

- JWT authentication for protected endpoints.
    
- Role-based access control.
    
- Wallet ownership verification.
    
- User-specific data access restrictions.
    
- Input validation.
    
- Parameterized SQL queries.
    
- Rate limiting for sensitive operations.
    
- Secrets stored in environment variables.
    
- No sensitive data, tokens, passwords, SQL, or stack traces in logs.
    
- HTTPS outside trusted local development.
    

## **13. API Documentation**

FastAPI OpenAPI / Swagger documentation will provide:

- Endpoint descriptions
    
- Authentication requirements
    
- Request parameters and bodies
    
- Success response formats
    
- Error responses
    
- HTTP status codes
    
- Validation requirements
    

# Phase 6---RECONCILLATION & AUDIT
# Phase 7 --- Testing and Design for Testability

## Objective

Make the architecture independently testable, reliable and maintainable.

The testing strategy should prioritize:
- Easy implementation.
- Easy understanding and explanation during viva.
- Fewer bugs and reliable financial operations.
- Minimal unnecessary dependencies and complexity.
- Realistic testing of application behavior.

## 1. Unit, Integration and End-to-End Testing Structure

Use `pytest` as the primary testing framework.

Organize tests into separate directories:

```text
tests/
├── unit/
├── integration/
└── e2e/
```

Responsibilities:
- **Unit tests:** Test individual functions and business logic independently.
- **Integration tests:** Test interactions between application components and SQLite.
- **End-to-end tests:** Test complete API workflows using FastAPI TestClient.

Avoid introducing additional testing frameworks unnecessarily.

## 2. Isolated Temporary Test Database

Use temporary SQLite database files for testing.

- Use pytest's `tmp_path` fixture to create temporary database files.
- Each test should have an appropriately isolated database.
- Tests must never modify the actual project database.
- Temporary databases should be cleaned up after execution.
- Preserve important database constraints and settings used by the actual application.

## 3. Dependency Injection and Provider Interfaces

Use FastAPI's built-in dependency injection through `Depends()`.

- Provide database sessions and shared resources through dependencies.
- Keep dependencies easy to override during testing.
- Avoid unnecessary abstract classes and provider interfaces.
- Introduce additional interfaces only when genuinely required.

## 4. Injected-Failure Rollback Tests

Use pytest's `monkeypatch` to deliberately inject exceptions during financial operations.

Test failures at meaningful points in the transfer workflow.

Verify that a failed transfer leaves no partial financial changes:

- Sender balance remains unchanged.
- Receiver balance remains unchanged.
- No partial ledger entries remain.
- No incomplete transaction record remains.
- No incorrectly committed idempotency record remains.

All failure tests must use the temporary test database.

## 5. Idempotency and Concurrency Tests

Use pytest, SQLite and Python threads for basic correctness testing.

Test the following cases:

- Same idempotency key with the same request payload must not create duplicate transfers.
- Same idempotency key with a different request payload must be rejected.
- Concurrent transfers must not cause incorrect balances or overspending.
- Ledger entries and wallet balances must remain consistent after concurrent operations.

Use the database locking and transaction strategy selected in the database and transaction-management phases.

Do not introduce dedicated load-testing tools unless performance testing becomes an explicit requirement.

## 6. Security and Authorization Tests

Use pytest and FastAPI TestClient.

Test the following:

- Unauthenticated requests are rejected.
- Invalid JWTs are rejected.
- Expired JWTs are rejected.
- Normal users cannot perform administrator-only operations.
- Users cannot access wallets belonging to other users.
- Users cannot transfer money from wallets they do not own.
- Authorized operations work correctly.

Ensure rejected requests do not cause financial side effects.

## 7. Reconciliation Corruption Tests

Use the temporary test database to deliberately introduce inconsistent financial data.

Test cases should include:

- Stored wallet balance differs from ledger-derived balance.
- Total debits do not equal total credits.

Verify that reconciliation detects and reports discrepancies correctly.

Reconciliation must remain read-only. Corruption should be introduced only by test setup, never by the reconciliation operation itself.

## 8. Regression Test Strategy

Use the complete pytest test suite as the regression testing strategy.

- Run all tests after relevant code changes.
- Fix failing tests before merging changes.
- Configure GitHub Actions to run the same test suite on pushes and pull requests.

Avoid unnecessary selective-test automation initially.

## Technology Choices Summary

| Responsibility | Selected approach |
|---|---|
| Testing framework | pytest |
| API testing | FastAPI TestClient |
| Test database | Temporary SQLite files |
| Temporary database management | pytest `tmp_path` |
| Dependency injection | FastAPI `Depends()` |
| Failure injection | pytest `monkeypatch` |
| Concurrency testing | Python threads |
| Regression testing | Complete pytest suite |
| CI testing | GitHub Actions |

## Project-Wide Constraints

1. Testing must verify the financial business rules defined in the project's SRS.
2. Do not weaken accounting invariants or security requirements to make tests pass.
3. Verify that financial operations are atomic and failed operations leave no partial state.
4. Do not use floating-point arithmetic for money.
5. Do not modify committed ledger entries during normal application operations.
6. Ensure test isolation so execution order does not affect results.
7. Keep test names, fixtures and assertions understandable to beginner-level developers.
8. Avoid unnecessary dependencies and overengineering.
9. Reuse the architecture, database schema, authentication design and API contracts finalized in the other project phases. Do not independently invent conflicting designs.
10. If a decision from another phase is missing or contradictory, identify it and ask for clarification instead of silently assuming a solution.

## Scope

This phase defines the testing architecture, testing strategy and test cases.

Implementation must follow the final combined project specification and approved team decisions.
