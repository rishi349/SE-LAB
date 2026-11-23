SOFTWARE REQUIREMENTS
SPECIFICATION
Financial Ledger & Digital Wallet API

9 November 2026


 Document Control
Field	Value
Document title	Software Requirements Specification – Financial Ledger & Digital Wallet API
Project	Financial Ledger API (Original Course Project Scope)
Version	1.0
Date	9 November 2026
Status	Draft for team review and Stage 1 approval
Prepared by	Project team
Baseline	Project Statement: Financial Ledger & Digital Wallet API; The AI-Assisted Software Development Life Cycle (SDLC)

Approval of this document establishes the agreed requirements baseline only. It does not constitute evidence that implementation, testing, Agent Skills, CI, or any stage deliverable has been completed.
Contents

1  Introduction ................................................ 3
   1.1 Purpose ................................................. 3
   1.2 Scope ................................................... 3
   1.3 Definitions and abbreviations .......................... 3
   1.4 References .............................................. 4
   1.5 Conventions ............................................. 4

2  Overall Description ......................................... 4
   2.1 Product perspective and functions ...................... 4
   2.2 User classes ............................................ 4
   2.3 Operating environment ................................... 4
   2.4 Design and implementation constraints .................. 5
   2.5 Assumptions and dependencies ............................ 5
   2.6 Out of scope ............................................ 5
   2.7 Integrity and threat boundary ........................... 6

3  Accounting Model and Business Rules .......................... 6
   3.1 Balance convention ...................................... 7
   3.2 Transaction atomicity ................................... 7
   3.3 Reversal semantics ...................................... 7

4  External Interface Requirements ............................. 7
   4.1 API conventions ......................................... 7
   4.2 Proposed endpoint catalogue ............................ 8
   4.3 Transfer request and response ........................... 8
   4.4 Error format and catalogue .............................. 8
   4.5 Validation and execution order .......................... 9
   4.6 Configuration and software interfaces .................. 9

5  Functional Requirements .................................... 10
   5.1 FR-1: Wallet initialization ............................ 10
   5.2 FR-2: Idempotent transfers ............................. 10
   5.3 FR-3: Concurrent balance mutability .................... 11
   5.4 FR-4: Immutable audit trail and reversals .............. 11
   5.5 FR-5: Ledger reconciliation ............................ 12

6  Non-Functional Requirements ................................ 13
   6.1 Performance and capacity ............................... 13
   6.2 Reliability and data integrity .......................... 14
   6.3 Security ............................................... 14
   6.4 Documentation, maintainability, and portability ........ 15
   6.5 Observability .......................................... 15

7  Skill Requirements ......................................... 15
   7.1 simulate-transfer expected outcome ..................... 16

8  Process Requirements and Testing ........................... 16
   8.1 Shared AI-Assisted SDLC process requirements ........... 16
   8.2 Required test coverage ................................. 17
   8.3 Concurrency test scenarios ............................. 18
   8.4 Test evidence and reporting ............................ 18

9  Data Requirements .......................................... 18
   9.1 Data integrity constraints ............................. 19
   9.2 Data retention and backup ............................... 19

10 Verification and Traceability .............................. 19
   10.1 Verification summary .................................. 19
   10.2 Traceability .......................................... 19

11 Acceptance Criteria and Stage Deliverables .................. 20
   11.1 Product acceptance .................................... 20
   11.2 Stage deliverables .................................... 20
   11.3 Revision history ...................................... 21

Appendix A. Requirement and decision register ................. 21

Appendix B. Open decisions for team approval .................. 21

Appendix C. TBD List .......................................... 22
1. Introduction
1.1 Purpose
This Software Requirements Specification (SRS) defines the requirements for a RESTful backend service that manages digital wallets and records money movements using a double-entry ledger. It is the reference for architecture, implementation, testing, review, and acceptance. Requirements are assigned stable identifiers so that they can be traced to GitHub issues, pull requests, tests, Agent Skills, and Obsidian Second Brain notes.
The intended readers are the project team, course instructors/reviewers, developers, testers, and future maintainers.
1.2 Scope
The product shall expose a REST API to create user accounts and currency-specific wallets, transfer funds between wallets, prevent duplicate processing on retries, safely process concurrent transfers, retain an immutable audit trail, record reversals as new transactions, and reconcile ledger-derived balances against stored wallet balances.
The system's central correctness objective is that money must not be created, lost, or transferred twice because of concurrent requests, application failures, or network retries. Each successful money movement shall be represented by equal debit and credit entries. Wallet balances shall be consistent with the ledger.
The project is a backend API and does not require a graphical user interface. A command-line client or HTTP tool may be used for demonstrations and manual testing.
1.3 Definitions and abbreviations
Term	Meaning
API	Application Programming Interface.
REST	Representational State Transfer; the HTTP resource-oriented interface used by this service.
Wallet	A user-associated balance-holding account denominated in one currency.
Ledger	The append-only record of debit and credit entries representing financial events.
Transaction	One logical financial operation represented by a balanced set of ledger entries.
Double-entry bookkeeping	Accounting method in which each transaction has equal total debits and credits.
Debit / Credit	The two directions of a ledger entry. Their effect on a wallet is defined by the accounting convention in Section 3.
Idempotency key	Client-provided token identifying one logical money-moving request so retries do not create another transaction.
Fingerprint	Deterministic digest of the normalized operation and request payload associated with an idempotency key.
Reversal	A new transaction that offsets an earlier transaction without editing or deleting the original.
Reconciliation	Read-only verification that ledger entries balance and stored wallet balances equal ledger-derived balances.
ACID	Atomicity, Consistency, Isolation, and Durability properties of database transactions.
WAL	Write-Ahead Logging, a SQLite journal mode that supports reader/writer concurrency characteristics.
CI/CD	Continuous Integration / Continuous Delivery or Deployment.
SRS	Software Requirements Specification.
ADR	Architecture Decision Record.
Agent Skill	A documented, reusable workflow for an AI assistant, stored in a skill folder with a SKILL.md file.
Second Brain	The team's Obsidian knowledge base organized using the PARA method.

1.4 References
•	Project Statement: Financial Ledger & Digital Wallet API (course-provided project brief).
•	The AI-Assisted Software Development Life Cycle (SDLC) (course-provided workflow and deliverables).
•	SQLite documentation: transactions, locking, and WAL mode.
•	HTTP Semantics, RFC 9110; JSON Data Interchange Format, RFC 8259.
•	Agent Skills format specification, https://agentskills.io.
•	Obsidian documentation for internal links and vault organization.
The two course documents are authoritative for mandatory assignment requirements. This SRS adds proposed API-level detail to make those requirements testable. Any proposed implementation choice not explicitly required by the course brief is identified as a team decision or an open decision.
1.5 Conventions
The word “shall” denotes a mandatory requirement. “Should” denotes a recommendation that may be deferred with a documented reason. “May” denotes an optional capability. Requirement identifiers use FR (functional), NFR (non-functional), BR (business rule), API (interface), SK (Agent Skill), PC (process), TQ (testing quality), and A (assumption/open decision).
Verification codes: U = unit test; I = integration test; S = HTTP system/end-to-end test; N = negative/security test; P = performance test; R = review/inspection; D = live demonstration. A verification method specifies required evidence; it does not claim that the requirement has already passed.
2. Overall Description
2.1 Product perspective and functions
The Financial Ledger API is a standalone backend application. Clients submit HTTP requests to the API. The application validates requests, applies wallet and accounting rules, coordinates database transactions, stores ledger entries, and returns JSON responses. SQLite is the database technology recommended by the course brief because it provides local, serverless storage and ACID transaction support.
The logical responsibilities are: (1) HTTP/API boundary; (2) application services implementing wallet and transfer use cases; (3) domain/accounting rules; (4) provider/boundary interfaces for persistence, time, identifier generation, and hashing where appropriate; and (5) SQLite persistence.
2.2 User classes
User class	Responsibilities
Client / calling application	Requests user and wallet creation, initiates transfers, and reads wallet/transaction information exposed by the API.
Administrator	Invokes administrative reconciliation and authorized reversal operations. Administrative authorization shall be enforced by the API.
Developer / tester	Builds and tests the service, uses isolated test data, and runs local Agent Skills.
Reviewer	Inspects requirements, design, tests, repository history, Second Brain evidence, and stage demonstrations.

The exact end-user authentication model is not prescribed by the project statement. The implementation shall nevertheless distinguish authorized administrative operations from ordinary client operations. The selected authentication mechanism must be documented before implementation.
2.3 Operating environment
•	A development and demonstration environment capable of running the selected backend language/framework and SQLite.
•	A local filesystem location for the SQLite database.
•	HTTP/HTTPS-capable clients such as cURL, Postman, or Bruno for API testing.
•	Git and GitHub for source control, issues, pull requests, CI workflows, and release tags.
•	Obsidian for the project Second Brain.
•	An AI coding assistant capable of using the team's custom Agent Skills.
2.4 Design and implementation constraints
ID	Constraint	Verify
DC-1	The service shall expose a RESTful HTTP API with JSON request and response bodies.	S
DC-2	SQLite is the recommended persistence option in the course brief; if selected, money-moving operations shall use SQLite transactions and appropriate locking.	R, I
DC-3	Money shall be represented using integer minor units (for example, paise/cents) or an exact decimal representation. Floating-point arithmetic shall not be used for money.	U, R
DC-4	A successful transfer shall be represented by equal debit and credit ledger entries.	U, I
DC-5	Committed ledger records shall not be updated or deleted through supported application operations.	I, N
DC-6	External dependencies shall be isolated behind provider interfaces where applicable, as required by SE-6 of  SDLC.	R
DC-7	All project work shall be maintained in a GitHub repository with issues, reviewed pull requests, and CI checks.	R
DC-8	The implementation language and framework shall be selected and documented by the team before design is baselined.	R

2.5 Assumptions and dependencies
ID	Assumption / dependency	Verify
A-1	Each wallet belongs to one user and is denominated in one currency.	R
A-2	A normal transfer is permitted only between wallets using the same currency.	U, S
A-3	A wallet's currency does not change after creation.	I
A-4	The service has one authoritative database for the project deployment. Multi-node distributed deployment is not required by the course brief.	R
A-5	The database and host filesystem provide the durability guarantees documented by the chosen database configuration.	R, I
A-6	Supported currencies and their minor-unit precision will be configured or explicitly documented by the team.	R
A-7	The project is an educational backend implementation and is not connected to real banking/payment networks.	R

2.6 Out of scope
•	Real payment gateway, bank, card-network, or UPI integration.
•	Currency conversion, foreign-exchange rates, and cross-currency transfers.
•	Interest, fees, overdrafts, loans, credit scoring, or investment functionality.
•	A production-grade consumer mobile application or graphical web interface.
•	Multi-region or distributed ledger deployment.
•	Financial statements, trial balance, balance sheet, income statement, and other LedgerFlow-specific accounting reports.
•	Blockchain, cryptocurrency, or public-chain anchoring.
•	Complex end-user identity verification or regulatory KYC workflows unless separately approved.
2.7 Integrity and threat boundary
The application shall prevent ordinary API operations from editing or deleting committed ledger records. Reconciliation shall detect accounting inconsistencies and mismatches between stored balances and ledger-derived balances. Database constraints and/or triggers should provide additional protection against accidental mutation.
Application-level immutability does not make a local database tamper-proof against a privileged operator who can directly modify the database file, disable triggers, or replace backups. The project shall not claim protection against a fully privileged database attacker unless an independently trusted external checkpoint or equivalent mechanism is designed and implemented. Such external anchoring is outside the original course-project scope.
3. Accounting Model and Business Rules
This section defines the minimum accounting invariants that every implementation and test shall preserve. These rules are the foundation of FR-1 through FR-5.
ID	Business rule	Verify
BR-1	All monetary values shall use integer minor units or an exact decimal type. Floating-point values shall not be used in monetary calculations.	U, R
BR-2	Each wallet shall have exactly one currency. The currency shall be stored with the wallet and shall not change after creation.	U, I
BR-3	A successful transfer shall create at least one debit entry and one credit entry, with equal positive amounts and the same currency.	U, I
BR-4	The debit and credit entries for a transfer shall reference different wallets.	U, N
BR-5	The sender's wallet balance shall decrease by the transfer amount and the receiver's wallet balance shall increase by the same amount.	U, S
BR-6	A wallet balance shall not become negative as a result of a transfer.	U, N
BR-7	The sum of debits shall equal the sum of credits for every committed transfer and for the ledger as a whole, within the defined accounting scope.	U, I, S
BR-8	A rejected or rolled-back transfer shall not leave a partial balance update or a partial set of ledger entries.	I, N
BR-9	A retry of a successful money-moving request with the same idempotency identity and same request fingerprint shall not create another financial transaction.	I, S
BR-10	Reuse of an idempotency key for a different request payload shall be rejected and shall not create a financial transaction.	U, S
BR-11	A reversal shall be recorded as a new transaction that offsets the original; the original transaction and its entries shall remain unchanged.	U, I
BR-12	Wallet balances stored for efficient retrieval shall equal the balances calculated from the corresponding ledger entries.	U, I, S
BR-13	All balance arithmetic and aggregate calculations shall detect overflow and preserve exactness.	U, N
BR-14	An authenticated user shall only be permitted to transfer funds from a source wallet that they own. Attempts to use another user’s wallet as the source shall be rejected without financial side effects.	N, S

3.1 Balance convention
For this project, the API and database design shall document one consistent debit/credit sign convention. For wallet balances, a transfer debit decreases the sender's available balance and a transfer credit increases the receiver's available balance. Reconciliation shall use the same convention. The precise internal representation may differ, but public balance behavior shall conform to BR-5.
3.2 Transaction atomicity
The debit entry, credit entry, sender balance update, receiver balance update, and idempotency record for a successful transfer shall be committed as one atomic operation. If any required step fails before commit, the operation shall roll back in full.
3.3 Reversal semantics
A reversal shall not delete or edit the original transaction. It shall create a new transaction with entries that offset the original financial effect. The system shall prevent a transaction from being reversed more than once unless the team explicitly defines a different policy. The reversal must itself satisfy the ledger balancing and atomicity rules.
4. External Interface Requirements
4.1 API conventions
ID	Requirement	Verify
API-1	API request and response bodies shall use UTF-8 JSON.	S, N
API-2	The API shall use a documented base path, proposed as /api/v1. The final path prefix shall be fixed in the API design document.	R, S
API-3	Resource identifiers shall use one documented format consistently. UUIDs are recommended; exact version/format shall be fixed during design.	U, N
API-4	Money request and response fields shall be integer minor-unit values or exact decimal strings, consistently documented. JSON floating-point values shall not be accepted for money.	U, N
API-5	Money-moving requests shall include an Idempotency-Key header.	S, N
API-6	Every API response shall use an appropriate HTTP status code and documented JSON response/error schema.	S
API-7	Error responses shall not expose SQL statements, stack traces, credentials, or internal filesystem paths.	N
API-8	Pagination, if used for transaction history, shall have documented limits and stable ordering.	S, N

4.2 Endpoints
The following endpoint catalogue is a proposed contract for the selected course scope. Exact route names and payload fields shall be approved by the team and captured in OpenAPI before implementation. It deliberately excludes features not required by the course brief.
Method and path	Purpose	Authorization (proposed)
POST /api/v1/users	Create a user account.	Client
GET /api/v1/users/{userId}	Retrieve a user and associated wallet summary.	Client
POST /api/v1/users/{userId}/wallets	Create a currency wallet with an initial zero balance.	Client
GET /api/v1/wallets/{walletId}	Retrieve wallet details and current balance.	Client
GET /api/v1/wallets/{walletId}/balance	Retrieve the current wallet balance.	Client
POST /api/v1/transfers	Transfer funds between two wallets; requires Idempotency-Key.	Client
GET /api/v1/transactions/{transactionId}	Retrieve a transaction and its ledger entries.	Client
GET /api/v1/wallets/{walletId}/transactions	Retrieve wallet transaction history.	Client
POST /api/v1/transactions/{transactionId}/reversal	Create a reversal transaction; requires Idempotency-Key.	Admin or authorized client, to be decided
GET /api/v1/admin/reconciliation	Run read-only ledger and wallet-balance reconciliation.	Admin
GET /api/v1/health	Return service health status.	Public/read-only

4.3 Transfer request and response
Proposed request fields for POST /api/v1/transfers: sourceWalletId, destinationWalletId, amount, currency, and an optional client reference. The Idempotency-Key shall be supplied as an HTTP header, not as a body field.
A successful response shall identify the transaction, source and destination wallets, amount, currency, status, creation timestamp, and the associated debit and credit ledger entries. The response shall make clear that the transfer was committed. A replay shall return the previously stored outcome or a documented equivalent and shall not create another transaction.
4.4 Error format and catalogue
The proposed common error format is: {"error":{"code":"VALIDATION_ERROR","message":"Invalid request","details":[{"field":"amount","rule":"must_be_positive_integer_minor_units"}]}}. The exact schema shall be documented in OpenAPI.
HTTP status	Proposed error code	Meaning
400	VALIDATION_ERROR	Malformed JSON, missing field, invalid field, or unsupported field.
400	INVALID_AMOUNT	Amount is zero, negative, fractional, non-numeric, or outside the permitted range.
400	MISSING_IDEMPOTENCY_KEY	Money-moving request has no idempotency key.
400	INVALID_IDEMPOTENCY_KEY	Idempotency key does not satisfy the documented format/length.
401	UNAUTHENTICATED	Credentials are missing or invalid, if authentication is implemented.
403	FORBIDDEN	Caller is authenticated but lacks the required permission.
404	NOT_FOUND	Referenced user, wallet, or transaction does not exist.
409	IDEMPOTENCY_KEY_REUSED	The same key was previously used with a different request fingerprint.
409	ALREADY_REVERSED	The original transaction has already been reversed.
422	INSUFFICIENT_FUNDS	Sender wallet does not have sufficient available funds.
422	CURRENCY_MISMATCH	Wallet currencies or request currency do not match.
422	SAME_WALLET_TRANSFER	Source and destination wallet are identical.
503	STORAGE_BUSY	Database write lock could not be obtained within the configured timeout.
500	INTERNAL_ERROR	Unexpected server-side failure; no internal details are disclosed.

Status-code mapping above is a proposed contract, not a requirement explicitly enumerated by the project brief. The team shall confirm it during API design and keep implementation, tests, and OpenAPI synchronized.
4.5 Validation and execution order
•	Resolve the route and HTTP method; return a documented error for unsupported methods.
•	Validate request media type and enforce a configured request-body size limit.
•	Authenticate and authorize the caller if the selected security design requires credentials.
•	Parse JSON and validate required fields, types, identifier formats, amount precision, and idempotency header.
•	For a money-moving request, begin the database transaction and obtain the required write lock.
•	Look up the idempotency key in its defined namespace. If the same key and fingerprint already succeeded, return the stored outcome without changing financial state. If the fingerprint differs, reject the request.
•	For a new request, validate wallet existence, wallet distinction, currency equality, positive amount, and balance bounds; also verify that the authenticated user owns the source wallet before checking available funds or writing financial records.
•	Write ledger entries, update balances, store the idempotency outcome, and commit atomically.
•	Return success only after the database commit succeeds.
4.6 Configuration and software interfaces
The service shall support configuration for its listening address/port, database path, supported currencies and precision, and any authentication credentials/roles selected by the team. Secrets shall be supplied through environment variables or a secure local configuration mechanism and shall not be committed to Git. The storage interface shall isolate SQLite-specific operations from the domain rules where practical.
5. Functional Requirements
5.1 FR-1: Wallet initialization
ID	Requirement	Verify
FR-1.1	The system shall allow creation of a user account with a unique user identifier.	S, N
FR-1.2	The system shall allow a user to create one or more wallets, each denominated in a distinct supported currency.	S
FR-1.3	Each wallet shall have a unique wallet identifier and shall be associated with exactly one user.	I, S
FR-1.4	A wallet shall have exactly one currency, and its currency shall not be changed after creation.	I, N
FR-1.5	A newly created wallet shall have a zero balance unless an initial funding operation is explicitly supported by the approved design.	S
FR-1.6	The system shall ensure that every non-zero balance is backed by corresponding ledger entries.	I, S
FR-1.7	The creation of a wallet and its required account/ledger metadata shall be atomic.	I
FR-1.8	The API shall return a unique wallet identifier, associated user identifier, currency, current balance, and creation timestamp after successful creation.	S
FR-1.9	The system shall reject creation requests referencing an unknown user or unsupported currency.	N
FR-1.10	The system shall reject duplicate wallets for the same user and currency if the team adopts a one-wallet-per-currency policy; otherwise the approved multiplicity rule shall be enforced.	N, R
5.2 FR-2: Idempotent transfers
ID	Requirement	Verify
FR-2.1	The system shall expose an API operation to transfer a positive amount from a source wallet to a destination wallet.	S
FR-2.2	Every transfer request shall require an Idempotency-Key HTTP header.	S, N
FR-2.3	The system shall associate the idempotency key with a deterministic fingerprint of the logical request.	U, I
FR-2.4	A retry using the same key and equivalent request payload shall not create a second transfer or a second debit.	I, S
FR-2.5	Reuse of the same key with a different request payload shall be rejected without financial side effects.	U, N
FR-2.6	A successful transfer shall debit the source wallet and credit the destination wallet by the same amount and currency.	U, S
FR-2.7	The transfer shall create balanced ledger entries linked to one transaction identifier.	U, I
FR-2.8	The system shall reject transfers when the source and destination wallets are identical.	N
FR-2.9	The system shall reject transfers when the wallets do not use the same currency or the request currency does not match the wallets.	N
FR-2.10	The system shall reject zero, negative, fractional, malformed, or out-of-range amounts.	U, N
FR-2.11	The system shall reject a transfer that would make the source wallet balance negative.	U, N
FR-2.12	Only a successfully committed money-moving operation shall be recorded as a completed idempotent result; rejected/rolled-back operations shall not be treated as completed transfers.	I, N
FR-2.13	The idempotency retention period and key namespace shall be documented. The recommended project default is retention for the lifetime of the database.	R, I
FR-2.14	Concurrent requests using the same key and same fingerprint shall result in at most one committed transfer.	I, N
FR-2.15	The system shall provide a read operation to retrieve a transaction by its identifier.	S

5.3 FR-3: Concurrent balance mutability
ID	Requirement	Verify
FR-3.1	The system shall safely process multiple simultaneous incoming and outgoing transfer requests involving the same wallet.	I, N
FR-3.2	The system shall prevent race conditions and lost balance updates.	N
FR-3.3	The system shall ensure that concurrent debits cannot collectively overdraw a wallet.	N
FR-3.4	Each transfer shall execute its balance reads, business checks, ledger writes, balance updates, and idempotency recording within one atomic database transaction.	I, R
FR-3.5	The implementation shall use a database-supported locking or transaction-isolation strategy appropriate to the selected database. For SQLite, BEGIN IMMEDIATE or an equivalent documented strategy may be used.	I, R
FR-3.6	If the database cannot obtain the required write lock within a configured timeout, the API shall return a documented retryable error and shall not leave partial financial effects.	I, N
FR-3.7	A read operation shall not expose a partially applied transfer.	I, N
FR-3.8	Injected failures before commit shall roll back all changes belonging to the transfer.	I
FR-3.9	The result of committed concurrent transfers shall be equivalent to a valid serial ordering of those transfers.	N

5.4 FR-4: Immutable audit trail and reversals
ID	Requirement	Verify
FR-4.1	Every successful transfer shall create permanent ledger records containing transaction identity, wallet/account reference, entry direction, amount, currency, and timestamp.	I, S
FR-4.2	Committed ledger records shall not be updated or deleted through the API or normal application operations.	I, N
FR-4.3	The API shall not expose an endpoint for editing or deleting committed ledger entries.	R, S
FR-4.4	The system shall support correction/cancellation by creating an explicit reversal transaction rather than changing the original transaction.	S
FR-4.5	A reversal shall reference the original transaction and shall create entries that offset the original financial effect.	U, I
FR-4.6	The original transaction and its ledger entries shall remain unchanged after reversal.	I, N
FR-4.7	The system shall prevent duplicate reversal of the same original transaction unless a different policy is explicitly approved.	N
FR-4.8	The system shall provide transaction history retrieval for a wallet, including original and reversal transactions.	S
FR-4.9	The audit trail shall preserve transaction ordering using a stable sequence or creation ordering mechanism.	I, R
FR-4.10	If hash chaining is selected as an implementation enhancement, the design shall 
 define canonical hash input and reconciliation shall verify the chain. Hash chaining is not mandatory in the original course brief.	R, U

5.5 FR-5: Ledger reconciliation
ID	Requirement	Verify
FR-5.1	The system shall provide an administrative API operation that starts reconciliation for the ledger scope selected by the caller. The operation shall return a result identifying the scope and the time at which the check was performed.	S
FR-5.2	Reconciliation shall calculate the total debit amount and total credit amount within the selected ledger scope, using the same currency and scope boundaries. It shall report a balancing failure when the two totals are not equal.	U, I, S
FR-5.3	Reconciliation shall derive each wallet's expected balance by aggregating its ledger entries according to their debit or credit direction. The calculation shall use the exact monetary representation defined for the system.	U, I
FR-5.4	Reconciliation shall compare each derived wallet balance with the balance currently stored for that wallet. Any difference shall be recorded as a discrepancy that identifies the wallet and both balance values.	I, S
FR-5.5	Reconciliation shall produce an overall consistency result for the selected ledger scope and identify every discrepancy detected during the check. A consistent result shall be reported only when all required checks pass.	S
FR-5.6	Reconciliation shall read ledger entries and wallet balances from one consistent database snapshot. This prevents concurrent transfers from making the comparison appear inconsistent when the data was valid at a single point in time.	I
FR-5.7	Reconciliation shall be a read-only operation and shall not change wallet balances, ledger entries, or transaction records. Detected discrepancies shall be reported for investigation rather than silently repaired.	I, N
FR-5.8	The reconciliation response shall include the check timestamp, overall status, debit and credit totals, and the list of detected discrepancies. The discrepancy list shall be empty when no inconsistency is found.	S

6. Non-Functional Requirements
6.1 Performance and capacity
ID	Requirement	Verify
NFR-PERF-1	The API shall complete ordinary wallet reads and transfer requests within a response-time target agreed by the team and measured on documented reference hardware.	P
NFR-PERF-2	The service shall support concurrent requests without violating accounting invariants.	P, N
NFR-PERF-3	Reconciliation shall complete for the test dataset size agreed in the test plan; dataset size and elapsed time shall be reported.	P
NFR-PERF-4	Performance results shall record hardware, operating system, runtime/compiler, database version, build mode, dataset size, and commit identifier.	R, P

The course brief does not prescribe numeric latency, throughput, or capacity targets. The team shall not claim numerical performance guarantees until it has agreed measurable targets and produced repeatable test evidence.
6.2 Reliability and data integrity
ID	Requirement	Verify
NFR-REL-1	A money transfer shall be atomic: either all required ledger and balance changes commit, or none do.	I
NFR-REL-2	Committed financial records shall remain available after a normal application restart, subject to the database's documented durability guarantees.	I, R
NFR-REL-3	A failed operation shall not leave a debit without its matching credit or a balance update without its ledger entries.	I, N
NFR-REL-4	Repeated matching requests shall not cause duplicate money movement.	I, S
NFR-REL-5	Money calculations shall be exact and shall detect overflow before persistence.	U, N
NFR-REL-6	Database backups and restore procedures, if implemented, shall preserve ledger/balance consistency and be documented.	R, I

6.3 Security
ID	Requirement	Verify
NFR-SEC-1	All API inputs shall be validated for type, format, range, and required presence.	N
NFR-SEC-2	Negative and zero transfer amounts shall be rejected without side effects.	N
NFR-SEC-3	Wallet access and administrative reconciliation/reversal operations shall be protected by the authorization mechanism. For transfers, the server shall verify that the authenticated user owns the source wallet before permitting the operation.	N, R
NFR-SEC-4	Database access shall use parameterized queries or equivalent safe query binding.	R, N
NFR-SEC-5	Credentials, API keys, tokens, and other secrets shall not be committed to the repository or pasted into AI tools.	R
NFR-SEC-6	Logs and error responses shall not expose secrets, raw credentials, SQL text, stack traces, or sensitive request bodies.	N, R
NFR-SEC-7	If the API is exposed beyond a trusted local development environment, transport protection such as HTTPS shall be configured.	R
NFR-SEC-8	The CI pipeline shall run secret scanning on pull requests.	R

6.4 Documentation, maintainability, and portability
ID	Requirement	Verify
NFR-DOC-1	The API contract shall be documented using OpenAPI or an equivalent machine-readable/API reference.	R
NFR-DOC-2	User/developer documentation shall explain setup, configuration, endpoints, request examples, error responses, and test execution.	R
NFR-MNT-1	The implementation shall separate API handling, business/accounting logic, and persistence responsibilities.	R
NFR-MNT-2	External dependencies shall be isolated behind provider interfaces where applicable.	R
NFR-MNT-3	Significant architectural decisions shall be recorded as ADRs in docs/adr/ and cite at least one distilled Obsidian note.	R
NFR-MNT-4	The project shall maintain automated tests and add regression tests for significant defects.	R, U, I
NFR-POR-1	The repository shall document prerequisites and reproducible build/test commands for team members.	R

6.5 Observability
ID	Requirement	Verify
NFR-OBS-1	The service shall record operational events sufficient to diagnose request failures and transaction outcomes.	R, I
NFR-OBS-2	Logs shall identify a request or transaction using non-secret identifiers where available.	R
NFR-OBS-3	Logs shall not be treated as the authoritative financial ledger; the ledger database remains the source of truth.	R
NFR-OBS-4	The service shall provide a read-only health endpoint or equivalent local health check.	S

7. Skill Requirements
Custom Agent Skills shall guide AI-assisted development and product verification. Skills shall be stored in one folder per skill, each containing a valid SKILL.md with frontmatter and instructions. The exact directory may be .claude/skills/ or another documented Agent Skills-compatible location.
ID	Skill requirement	Verify
SK-1	Every skill shall follow the Agent Skills format, use valid frontmatter, have a name matching its folder, and include a concise description.	R, CI
SK-2: local-check	The skill shall (1) build the project; (2) run the automated test suite; (3) start the local server; (4) invoke one read-only endpoint; and (5) report pass/fail for each step. It shall stop the server it started and use an isolated disposable test database.	D
SK-3: simulate-transfer	The skill shall create two test wallets, record initial balances, execute a transfer with an idempotency key, submit two concurrent transfer requests to test race prevention, invoke reconciliation, and summarize final balances and consistency.	D, S
SK-4: brain-ingest	The skill shall add new sourced research notes or AI-session summaries to brain/inbox/ using the agreed note schema, link relevant requirement IDs, and append a run record to brain/log.md.	D, R
SK-5: brain-refine	The skill shall organize notes into PARA folders, merge duplicates, repair internal links, update brain/index.md, and record its run.	D, R
SK-6: brain-query	The skill shall retrieve relevant Second Brain notes, answer with note citations, and support drafting SRS/ADR documents from the stored project knowledge.	D
SK-7	Skills due at a stage shall be evaluated before that stage submission, and results shall be recorded. Skills scheduled for later stages shall be marked not yet due rather than reported as passed.	R
SK-8	Skills shall not contain credentials or secrets. API-calling skills shall read credentials from environment variables and use disposable databases for mutating workflows.	R, N

7.1 simulate-transfer expected outcome
The skill shall report initial balances, transfer request result, replay result, concurrent request outcomes, final balances, and reconciliation status. A passing run requires that the retry does not create another transfer, concurrent operations do not corrupt balances or violate available-funds rules, final balances match expected arithmetic, and reconciliation reports consistency. The skill shall not delete committed records from a shared or production database; it shall use and discard only a disposable test database.
8. Process Requirements and Testing
8.1 Shared AI-Assisted SDLC process requirements
ID	Process requirement	Verify
PC-1	The Obsidian Second Brain shall use PARA folders: brain/inbox/, brain/projects/, brain/areas/, brain/resources/, and brain/archive/, with brain/index.md and brain/log.md.	R
PC-2	Notes shall use [[wikilinks]] and link relevant requirement IDs, GitHub issues, and pull requests.	R
PC-3	Each stage shall end with a short review note describing what worked, what did not, and what should change.	R
PC-4	Every ADR and every Agent Skill shall cite at least one distilled Second Brain note.	R
PC-5	An AGENTS.md or equivalent guidance file shall exist at the repository root.	R
PC-6	Changes to the Second Brain, including AI-generated changes, shall be submitted through pull requests.	R
PC-7	Every team member shall author notes and make meaningful incremental commits visible in Git history.	R
PC-8	Every work item and defect shall have a GitHub issue. Changes shall use pull requests with at least one review by another team member.	R
PC-9	The team shall document its branching strategy, use release tags, and maintain a changelog.	R
PC-10	GitHub Actions shall run build, lint/format checks, automated tests, secret scanning, SKILL.md validation, and Second Brain note/broken-link validation on every pull request.	R, CI
PC-11	Automated tests shall run against an isolated fresh test database on every push and pull request. WAL/concurrency tests shall use a file-backed temporary database when needed.	R, CI
PC-12	A human shall review every AI-generated change before merge. Team members shall be able to explain merged code, skills, and documents.	R
PC-13	Significant AI sessions shall be recorded as ai-session notes stating the goal and what worked or failed. Secrets shall not be pasted into AI tools.	R
PC-14	The team shall maintain architecture/design documents, UML/ER diagrams, a development plan, task breakdown, and requirement-to-issue-to-PR-to-test-to-skill-to-brain traceability.	R

8.2 Required test coverage
Area / ID	Minimum required evidence
Unit tests (TQ-1)	Accounting calculations; debit/credit balance assertions; idempotency-key/fingerprint hashing; exact monetary parsing; validation; overflow checks.
Integration tests (TQ-2)	Database transactions; commit and rollback; injected transfer failures; persistence of idempotency records; concurrency/locking behavior.
System tests (TQ-3)	HTTP end-to-end tests for FR-1 through FR-5, including successful wallet creation, transfers, history/reversal, and reconciliation.
Negative tests (TQ-4)	Negative/zero amounts; insufficient funds; invalid/reused idempotency keys; malformed identifiers; unknown wallets; currency mismatch; same-wallet transfer; duplicate reversal; concurrent transfers.; authenticated user attempts to transfer from a wallet owned by another user (expect FORBIDDEN and no balance or ledger changes)
CI isolation (TQ-5)	CI tests shall use an isolated in-memory or fresh local test database on every push/PR; tests shall not mutate developer or production data.
Money precision (TQ-6)	Verify integer minor-unit or exact decimal handling; reject floating-point money inputs; test overflow and exact aggregate calculations.
Skill evaluation (TQ-7)	Evaluate skills due before each stage submission and record evidence in test documentation.
Regression (TQ-8)	Every significant defect shall receive a regression test linked to its GitHub issue.
Security	Validate API parameters, authorization, negative amount prevention, safe database access, secret handling, and error/log redaction.
Reconciliation	Test a clean ledger, empty ledger, concurrently written ledger, and deliberately corrupted disposable test database.

8.3 Concurrency test scenarios
•	Two concurrent transfers from the same source wallet where the combined amount exceeds the available balance: no overdraw shall occur.
•	Two concurrent requests using the same idempotency key and same payload: at most one transfer shall be committed.
•	Two concurrent requests using the same idempotency key but different payloads: at most one payload shall win; the other shall receive the documented key-reuse response.
•	Concurrent incoming and outgoing transfers to the same wallet: final balance shall equal the serially valid result.
•	A simulated failure between debit and credit persistence: the transaction shall roll back with no partial financial state.
8.4 Test evidence and reporting
Test reports shall identify the requirement IDs exercised, test environment, database mode, test data setup, expected result, actual result, pass/fail status, and relevant issue/commit. A passing test suite is evidence only for the cases executed; it shall not be described as proof against every possible failure.
9. Data Requirements
This section defines the logical data entities needed to satisfy the original course-project scope. The physical schema, indexes, foreign keys, constraints, triggers, and migration strategy shall be specified during Stage 2 design.
Entity	Logical attributes	Constraints / notes
User	userId, displayName or name, createdAt	Primary key userId. User identity fields shall be validated. Authentication details, if required, shall not be stored as plaintext secrets.
Wallet	walletId, userId, currency, balance, createdAt	Primary key walletId; userId references User; currency is required and immutable; balance uses exact monetary representation.
Transaction	transactionId, type, amount, currency, status, idempotency reference, createdAt, reversal reference	Primary key transactionId. A committed transaction shall be immutable. Types shall include at least transfer and reversal; any initialization/funding type must be agreed in design.
LedgerEntry	entryId, transactionId, walletId/accountId, direction, amount, currency, createdAt	Primary key entryId; references transaction and wallet/account; direction is DEBIT or CREDIT; amount is positive; entries are append-only.
IdempotencyRecord	credential/client scope, key, request fingerprint, response/status reference, createdAt	Unique key within the chosen namespace; retained according to the approved policy; committed atomically with the money-moving operation.
ReconciliationResult (optional)	reconciliationId, checkedAt, status, totals, discrepancy summary	May be generated on demand rather than persisted. If persisted, it shall not modify financial ledger data.

9.1 Data integrity constraints
•	Foreign-key relationships shall prevent ledger entries from referencing nonexistent transactions or wallets.
•	A ledger entry shall have a valid direction, positive amount, and currency consistent with the referenced wallet/account.
•	A committed transfer shall have balanced debit and credit entries.
•	Wallet balance shall equal the ledger-derived balance according to the chosen sign convention.
•	Idempotency uniqueness shall be enforced at the database level to prevent duplicate processing under concurrency.
•	Ledger and committed transaction rows shall be protected against ordinary UPDATE and DELETE operations.
•	Database transactions shall ensure related changes are committed or rolled back together.
9.2 Data retention and backup
Committed ledger records and idempotency records should be retained for the lifetime of the project database unless a retention policy is explicitly approved. Backup and restore procedures, if included, shall be documented and tested against ledger reconciliation. The project shall not claim that a backup is valid solely because a file copy completed; restored data shall be checked for consistency.
10. Verification and Traceability
10.1 Verification summary
Requirement group	Minimum verification evidence
FR-1 Wallet initialization	Create user and wallets; validate unique identifiers, ownership, currency, and initial balance behavior; test invalid user/currency.
FR-2 Idempotent transfers	Successful transfer; retry same key/payload; same key/different payload; insufficient funds; invalid amount; verify no duplicate ledger entries.
FR-3 Concurrency	Contended source-wallet tests; concurrent same-key requests; concurrent different-key requests; injected rollback; verify no lost updates or overdraw.
FR-4 Immutable audit trail	Attempt ordinary update/delete through supported paths; verify no edit/delete API; reverse a transaction; verify original unchanged and history includes reversal.
FR-5 Reconciliation	Clean ledger reports consistent; intentionally corrupted disposable test data reports discrepancy; concurrent write snapshot test; verify reconciliation is read-only.
NFRs	Security/validation tests, precision tests, performance evidence against agreed targets, documentation and maintainability inspection.
SKs and PC requirements	Live skill evaluations, CI workflow results, GitHub PR review evidence, Obsidian note/links validation, stage review notes.

10.2 Traceability
docs/traceability.md shall contain one row per mandatory FR, NFR, SK, DC, BR, and PC identifier, with links to the applicable issue, PR, test/inspection, skill, and brain note. Assumptions shall link to the checks or decisions that establish their applicability. An inapplicable column shall contain a rationale, not a fabricated link. Pending Stage 1 implementation/test links shall be visibly pending. Completion requires evidence in every applicable column. Identifiers shall not be reassigned. Withdrawn requirements retain their identifier and withdrawal explanation. Changes shall be reflected in tests, OpenAPI, traceability, and affected design documents in the same PR.

11. Acceptance Criteria and Stage Deliverables
11.1 Product acceptance
•	Users can be created and currency-specific wallets can be initialized according to the approved wallet policy.
•	A valid transfer updates both wallets and creates balanced ledger entries.
•	A matching retry with the same idempotency key does not create a duplicate financial transaction.
•	Reusing an idempotency key with a different request is rejected without financial side effects.
•	Insufficient funds, negative/zero amounts, invalid currencies, malformed identifiers, and invalid wallet combinations are rejected.
•	Concurrent transfer requests do not cause lost updates, corrupted balances, or negative wallet balances.
•	A transfer is atomic and injected failures do not leave partial state.
•	Committed ledger records cannot be edited or deleted through supported application operations.
•	A reversal is recorded as a new transaction and leaves the original record unchanged.
•	Reconciliation verifies debit-credit equality and compares stored wallet balances with ledger-derived balances.
•	Unit, integration, system, negative, precision, and regression tests pass in the CI environment.
•	The API documentation, user/developer documentation, Agent Skills, Second Brain records, and traceability matrix match the delivered implementation.
•	The team can demonstrate the required product workflow and explain all merged AI-assisted changes.
11.2 Stage deliverables
Stage	Required deliverables
Stage 1 – Requirements	This SRS containing FR/NFR/SK; Obsidian PARA vault with index.md and log.md; at least 10 research notes added using brain-ingest; root AGENTS.md; GitHub repository and CI skeleton; stage review note; evaluations for skills due at this stage.
Stage 2 – Design	Architecture and design documentation; UML and ER diagrams; ADRs in docs/adr/ citing distilled brain notes; development plan and task breakdown; brain-refine and brain-query skills; first local-check skill version; stage review and skill evaluations.
Stage 3 – Testing and CI	Continuous testing/CI plan and results; simulate-transfer skill with evaluation results; defect log and regression tests; updated traceability; stage review and required skill results.
Stage 4 – Review	Live demonstration of FR-1 through FR-5 using an HTTP client; live simulate-transfer, local-check, and brain-query; walkthrough from brain note to ADR, requirement, code, and test; final release tag and changelog; final review/evaluation evidence.

Stage acceptance applies only to deliverables due at that stage. Stage 1 does not require the complete product to be implemented. Later-stage skills and tests shall be marked planned/not yet due until they exist and have evidence.
Appendix A – Glossary and Abbreviations
A.1 Glossary
Term	Definition
Financial Ledger	A record of all financial transactions, including debit and credit entries, used to track the movement of money.
Digital Wallet	An account maintained by the system that stores a user's available balance in a particular currency.
Double-Entry Bookkeeping	An accounting method in which every financial transaction creates corresponding debit and credit entries of equal value.
Debit	A ledger entry representing an amount deducted from a wallet or account.
Credit	A ledger entry representing an amount added to a wallet or account.
Transaction	A financial operation that transfers money between two wallets or records another supported financial movement.
Idempotency	A property that ensures repeating the same request does not create duplicate financial operations.
Idempotency Key	A unique identifier supplied with a request to recognize retries of the same operation.
Reconciliation	The process of checking whether ledger entries and stored wallet balances are consistent and correctly balanced.
Atomicity	A database transaction property ensuring that all operations either succeed together or fail together.
Rollback	The process of undoing uncommitted database changes when an operation fails.
Wallet Ownership	The association between a wallet and the user who is authorized to operate on it.
API Key	A credential used to authenticate a client application when accessing the API.
Authentication	The process of verifying the identity of a client or user making an API request.
Authorization	The process of determining whether an authenticated requester is permitted to perform a particular operation.
Ledger Immutability	The principle that committed ledger entries must not be directly modified or deleted; corrections are recorded through new entries.
System Funding Account	An accounting account used as the counterparty when introducing initial funds into user wallets, if funding is supported.
A.2 Abbreviations
Abbreviation	Full Form
API	Application Programming Interface
REST	Representational State Transfer
HTTP	Hypertext Transfer Protocol
HTTPS	Hypertext Transfer Protocol Secure
JSON	JavaScript Object Notation
SQL	Structured Query Language
SQLite	Self-contained SQL Database Engine
ACID	Atomicity, Consistency, Isolation, Durability
CRUD	Create, Read, Update, Delete
FR	Functional Requirement
NFR	Non-Functional Requirement
BR	Business Rule
SK	Skill Requirement
PC	Process Requirement
TQ	Testing Quality Requirement
CI	Continuous Integration
PR	Pull Request

Appendix C – TBD List
The following items remain to be finalized by the team before or during the relevant development stages. Each item shall be resolved, documented, and reflected in the affected requirements and design documents.
C.1 Technology Stack
•	TBD-C1: Confirm the programming language and version.
•	TBD-C2: Confirm the backend framework and version.
•	TBD-C3: Confirm the build system and dependency-management approach.
C.2 Authentication and Security
•	TBD-C4: Finalize the authentication mechanism and token or credential validation process.
•	TBD-C5: Define how CLIENT and ADMIN roles are assigned and authorized.
•	TBD-C6: Define the procedure for credential generation, storage, expiration, rotation, and revocation.
C.3 Database and Accounting
•	TBD-C7: Finalize the physical database schema, including column types, constraints, and indexes.
•	TBD-C8: Confirm the initial funding mechanism and the accounting treatment of the system funding account.
•	TBD-C9: Finalize the supported currencies and their minor-unit precision.
•	TBD-C10: Confirm the wallet creation policy, including whether one user may have multiple wallets in the same currency.
•	TBD-C11: Finalize the monetary representation and overflow-handling strategy.
C.4 Transaction Processing
•	TBD-C12: Finalize the database concurrency-control mechanism.
•	TBD-C13: Define the idempotency key format, namespace, and retention policy.
•	TBD-C14: Confirm the duplicate-reversal policy and reversal authorization rules.
C.5 Ledger Reconciliation
•	TBD-C15: Finalize the supported reconciliation scopes and their API parameters.
•	TBD-C16: Define the exact reconciliation response format and discrepancy-reporting details.
C.6 API and Performance
•	TBD-C17: Finalize the REST API contracts, request/response schemas, and HTTP status codes in OpenAPI.
•	TBD-C18: Establish measurable API response-time and concurrency targets before performance testing.
C.7 Development and Testing
•	TBD-C19: Finalize the GitHub repository structure, branch strategy, and CI workflow.
•	TBD-C20: Finalize the test framework and test-database configuration.