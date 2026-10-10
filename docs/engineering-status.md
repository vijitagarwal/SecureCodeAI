# Engineering status

## Decision and acceptance criteria

The FastAPI / SQLAlchemy / Alembic / Bandit / Next.js architecture is appropriate for
a single-operator security workspace. Preserve it and complete the vertical flow.
The historic `PROJECT_DOSSIER.md` and autonomous plan predate the current code;
this document records this implementation's evidence.

A developer must be able to unlock the workspace, upload Python, see a truthful
completed or failed result, reopen persisted history, page/filter all findings,
read saved analysis, export a report, and delete retained source snippets. Invalid
Python and scanner errors must never be presented as a clean result. Source must
never execute. API access and resource usage must be bounded; source/credentials
must not enter error responses or logs. Local guidance must be identified as
deterministic, with remote AI separately configured and tested at its boundary.

## Baseline

- Clean working tree at `5becbe8`.
- Python 3.14.2, Node 24.12.0, npm 11.6.2 available.
- Backend: `python -m pytest tests -q`: 44 passed.
- Frontend lint/typecheck/build: missing installed dependencies.
- Default PostgreSQL migration command: timed out; live PostgreSQL unverified.

## Milestones

1. Complete secure API workflow, scanner correctness, scan management, auth,
   migration and regression checks.
2. Connect a functional workspace UI, persisted analysis and exports; verify
   frontend checks and user behavior.
3. Complete bounded optional AI integration, deployment setup and documentation;
   record actual integration evidence and outstanding limitations.

## Milestone 1 progress

- Fail-closed workspace bearer-key access before multipart parsing.
- Bounded request bodies (including chunked requests), upload time and concurrent scans.
- Blocking scanner/database work runs outside the async HTTP event loop.
- Scanner errors and invalid syntax fail the scan; `nosec` cannot suppress results.
- Isolated subprocess environment, output/timeout/finding limits, no source execution.
- Paginated history and severity filtering, JSON report export, cascaded deletion.
- Safe failure reasons, complete severity counts, constraints and migration.
- Backend regression suite: 69 passed; separate Alembic upgrade/check/downgrade/upgrade test passed.
- Docker CLI absent. PostgreSQL and Docker integration remain unverified.
