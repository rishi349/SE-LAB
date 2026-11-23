 Database Architecture: Keeping It Simple.
 SQLite.
 Zero Configuration: To avoid operational overhead, teams are strongly encouraged to use SQLite. It runs serverless as a single file on disk (or in-memory for unit tests). 

 • ACID by Default: SQLite provides immediate support for transactions (BEGIN, COMMIT, ROLLBACK), which are required for double-entry bookkeeping. 
 
 • Handling Concurrency: Teams can enable SQLite's WAL mode (PRAGMA journal_mode=WAL;) or use simple database transaction locks to easily satisfy FR-3 without needing distributed lock servers.
 
 conclusion :
 learnt SQLite implementation.
 learnt about obsidian tools.

  