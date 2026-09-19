# Stable dependency and runtime modernization

## Scope

The project now targets stable releases only: Python 3.14, Telethon 1.x,
SQLAlchemy 2.0, OpenAI Python 3.x, Alembic 1.x, and current stable support
libraries. Pre-release Telethon 2 and SQLAlchemy 2.1 lines are intentionally
excluded.

## Decisions

- Keep OpenAI Chat Completions because third-party OpenAI-compatible endpoints
  support it more consistently than Responses. A process-owned provider reuses
  one HTTP client, chooses the model per request, and closes during shutdown.
- Use `asyncio.run()` and await scheduler cancellation before disconnecting
  Telegram clients. This is required by Python 3.14 event-loop semantics.
- Keep synchronous SQLAlchemy for the small SQLite workload. ORM data needed by
  the forwarding chain is eagerly loaded and detached before Telethon or AI
  awaits; moving to `AsyncSession` would not remove SQLite serialization.
- Alembic owns all new schema changes. An unversioned legacy database runs the
  existing compatibility migration once, is validated against current model
  columns, and is stamped only after validation succeeds.
- Replace `pytz` with `zoneinfo`, which is available in every supported Python
  version and handles IANA timezone offsets without a third-party runtime
  dependency.
- Runtime and development dependencies are separately hash-locked. CI tests
  Python 3.11 and 3.14 and audits the runtime lock weekly.
