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

- Assurance work began from clean `4151dc9`; current local checkpoints are listed
  in Git history.
- Python 3.14.2, Node 24.12.0, npm 11.6.2 available.
- Backend baseline: `python -m pytest tests -q`: 93 passed, 1 skipped.
- Frontend lint/typecheck/build: verified locally with the checked-in lockfile.
- Docker, Podman, psql, and pg_ctl are unavailable locally; live PostgreSQL and
  container startup require CI or a host with those services.

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

## Milestone 2

- Authenticated dashboard with memory-only workspace key, upload, persisted history,
  complete server-side severity filtering/pagination, saved analysis, JSON export,
  and confirmed scan deletion.
- Request cancellation prevents stale result reads; failures are distinct from
  empty/clean results. Source is rendered as text, never HTML.
- Five React interaction tests pass, plus ESLint and Next production build.
- Upgraded Next.js 15 to 16.4.0 to resolve published dependency advisories; Node
  22.12+ is required. A Sharp override selects the patched 0.35.5+ release.
- `npm audit --omit=dev --audit-level=high`: zero known vulnerabilities.
- Tests use jsdom with an API contract double; visual browser interaction and
  container deployment have not been verified.

## Milestone 3

- Added an optional Gemini provider behind the provider interface. Its request and
  response boundary is tested without sending live credentials.
- Remote provider settings are validated at startup; mock remains the safe default.
- Backend and frontend production containers run as non-root users, use locked
  dependency manifests, apply security headers, and expose only loopback ports in
  the local Compose stack.
- CI runs backend tests, the opt-in PostgreSQL integration, frontend tests/build,
  and a production dependency audit.
- Live Gemini, Docker, PostgreSQL, and browser-container behavior still require
  environment-specific verification when those services are available.

## Milestone 4 — assurance hardening

- Scanner output is drained through a bounded pipe rather than an unbounded disk
  spool; timeouts reap direct processes and POSIX process groups.
- Upload worker sessions are thread-owned, exclusive-file cleanup cannot delete a
  pre-existing collision, and request cancellation retains active capacity until
  bounded work finishes.
- Approved scanner roots, request framing validation, oversized-header rejection,
  explicit CORS origins, report byte limits, liveness/readiness separation, request
  IDs, and generic unexpected-error responses are covered.
- Optional Gemini failures can persist explicitly labeled deterministic fallback
  guidance. The UI distinguishes that fallback from remote AI.
- Stale queued/running records are reconciled as failed after a bounded grace window
  on protected reads, so worker crashes do not leave scans permanently undeletable.
- Full backend rerun: 120 passed, 2 skipped (PostgreSQL integration and POSIX-only
  descendant fixture on Windows). Frontend lint, typecheck, 6 interaction tests,
  production build, npm audit, YAML parsing, and diff checks pass.
- Docker, live PostgreSQL, live Gemini, and browser/container interaction remain
  environment-blocked locally but are now represented by CI or opt-in checks.
