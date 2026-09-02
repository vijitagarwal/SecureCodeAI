# SecureCode AI - AI Build Context

## Purpose

This document is the implementation handoff for future AI coding sessions. It describes what is currently built, why it was built this way, how it was verified, and where the next implementation must begin.

The authoritative product roadmap remains `SECURECODE_AI_COPILOT_BUILD_PLAN.md`.

## Current milestone

Milestone 4 is implemented and verified. Do not begin Milestone 5 or later until explicitly authorized.

### Milestones 1 through 4 scope completed

- Root Git repository initialized.
- Backend scaffold created with FastAPI.
- Frontend scaffold created with Next.js, React, and TypeScript.
- PostgreSQL service defined in Docker Compose.
- Backend health endpoint added.
- Frontend health page added.
- Environment-variable template added.
- Root README added with setup and test commands.
- Backend health test added.
- Frontend lint, typecheck, and production build configured and verified.
- SQLAlchemy 2.x engine, session factory, and FastAPI session dependency added.
- Scan and Finding models added with constraints, indexes, timestamps, and cascade deletion.
- Pydantic schemas added for scan creation/status/response/summary and finding responses.
- Repository functions added for scan and finding persistence.
- Alembic configured with a reversible initial migration.
- Persistence tests added for scans, findings, counts, relationships, and cascade deletion.
- Secure `.py` multipart upload endpoint added at `POST /api/scans`.
- Upload validation, configurable 5 MB limit, UUID temporary storage, cleanup, and queued Scan creation added.
- Minimal frontend upload form added with success and error states.
- Upload API tests added for valid, invalid, oversized, missing, traversal, and non-execution cases.
- Bandit 1.9.4 added as a backend dependency.
- Security scanner abstraction, Bandit adapter, scan service, result APIs, and integration tests added.
- Architecture documentation added.

### Intentionally not implemented yet

These belong to later milestones and must not be added as part of Milestone 4 maintenance:

- Scan and Finding APIs
- Gitleaks or other scanner integrations
- Scanner subprocess execution
- AI/LLM providers
- RAG, authentication, Git repository scanning, CI/CD, or analytics

## Architecture currently implemented

```text
Browser
   |
   v
Next.js frontend (port 3000)
   |
   | GET /api/health from the browser
   v
FastAPI backend (port 8000)
  |
  | SQLAlchemy session / psycopg connection
   v
PostgreSQL (Docker Compose, port 5432)
```

The health route still performs its existing `SELECT 1` probe through the shared SQLAlchemy engine. Application persistence is now available through SQLAlchemy repositories, and schema changes are managed only by Alembic.

## Repository layout

```text
securecode-ai/
├── AI_BUILD_CONTEXT.md
├── README.md
├── SECURECODE_AI_COPILOT_BUILD_PLAN.md
├── .env.example
├── .gitignore
├── docker-compose.yml
├── backend/
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/0001_create_scan_and_finding_tables.py
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── routes/
│   │   │       ├── __init__.py
│   │   │       └── health.py
│   │   └── core/
│   │       ├── __init__.py
│   │       └── config.py
│   │   ├── db/
│   │   │   ├── database.py
│   │   │   ├── models.py
│   │   │   └── repositories/
│   │   │       ├── scan_repository.py
│   │   │       └── finding_repository.py
│   │   └── schemas/
│   │       ├── scan.py
│   │       └── finding.py
│   │   └── services/
│   │       ├── __init__.py
│   │       └── upload_service.py
│   └── tests/
│       ├── __init__.py
│       ├── test_health.py
│       ├── test_persistence.py
│       └── test_upload.py
└── frontend/
    ├── package.json
    ├── package-lock.json
    ├── next.config.ts
    ├── tsconfig.json
    ├── next-env.d.ts
    ├── postcss.config.mjs
    ├── eslint.config.mjs
    └── src/app/
        ├── layout.tsx
        ├── page.tsx
        └── globals.css
```

## Backend details

### `backend/app/main.py`

- Creates the FastAPI application titled `SecureCode AI API`.
- Registers CORS for `http://localhost:3000` by default.
- Allows only `GET` requests through the configured CORS middleware.
- Includes the health router under the `/api` prefix.

### `backend/app/core/config.py`

- Uses Pydantic Settings.
- Reads environment variables from the repository-root `.env` file when the backend is run from `backend/`.
- Default settings:
  - `DATABASE_URL=postgresql+psycopg://securecode:securecode@localhost:5432/securecode`
  - `CORS_ORIGINS=http://localhost:3000`
  - `MAX_UPLOAD_SIZE_BYTES=5242880`
  - `UPLOAD_DIR` defaults to the operating system temporary directory under `securecode-ai`
- `CORS_ORIGINS` supports comma-separated origins through the `allowed_origins` property.

### `backend/app/db/database.py`

- Creates the SQLAlchemy engine from `settings.database_url`.
- Uses `SessionLocal` with `autoflush=False` and `autocommit=False`.
- Exposes `get_db()` as a generator dependency that closes sessions reliably.
- Does not call `Base.metadata.create_all()` or mutate schema during application startup.

### `backend/app/db/models.py`

- Defines `Scan` and `Finding` using SQLAlchemy 2.x typed declarative mappings.
- Uses integer primary keys and a foreign key from `findings.scan_id` to `scans.id`.
- Uses JSON for scanner names and raw scanner metadata.
- Uses Python `StrEnum` values stored as portable strings rather than PostgreSQL-native enum types. This keeps migrations simple and portable while check constraints enforce valid values in the database.
- Defines indexes for finding scan ID, severity, tool, and rule ID.
- Deletes findings with their parent scan through ORM cascade and database `ON DELETE CASCADE`.

### `backend/app/db/repositories/`

- `scan_repository.py` handles scan creation, retrieval, status transitions, count updates, and deletion.
- `finding_repository.py` handles single/bulk finding creation, retrieval, scan listing, and severity aggregation.
- Repositories flush changes but leave transaction commit/rollback ownership to the caller.

### `backend/app/schemas/`

- Pydantic v2 schemas use `ConfigDict(from_attributes=True)` for future ORM-backed API responses.
- `ScanCreate`, `ScanStatusUpdate`, `ScanResponse`, `ScanSummary`, and `FindingResponse` are defined without exposing ORM objects directly.

### `backend/app/api/routes/health.py`

Endpoint:

```text
GET /api/health
```

Behavior:

- Always reports backend status as `ok` when the route is reachable.
- Opens a database connection through the shared SQLAlchemy engine configured from `DATABASE_URL`.
- Runs the parameter-free `SELECT 1` probe.
- Reports database status as `ok` when the query succeeds.
- Reports database status as `unavailable` and the overall status as `degraded` when PostgreSQL cannot be reached.
- Does not execute uploaded code or shell commands.

### `backend/app/api/routes/scans.py`

Endpoint:

```text
POST /api/scans
```

- Accepts one multipart form field named `file`.
- Delegates upload validation, temporary storage, and Scan creation to `upload_service.py`.
- Returns `201` with `scan_id`, `status`, and the original `filename`.
- Does not expose the temporary filesystem path.
- Exposes `GET /api/scans/{scan_id}` and `GET /api/scans/{scan_id}/findings` using repository-backed Pydantic responses.

### `backend/app/services/upload_service.py`

- Accepts only `.py` extensions, case-insensitively.
- Rejects missing names, path separators, null bytes, and filenames longer than 255 characters.
- Streams the upload in 1 MB chunks and enforces `MAX_UPLOAD_SIZE_BYTES` (5 MB by default).
- Creates the Scan as `queued`, writes to a generated UUID filename, and commits only after storage succeeds.
- Rolls back the database and removes a partial file on validation, storage, database, or unexpected failure.
- Closes the `UploadFile` in all cases.
- Stores the original filename in `Scan.name` as metadata. The temporary file remains for the future scanner pipeline and is not permanent storage.
- Never imports, executes, evaluates, dynamically loads, or subprocesses uploaded source.

### `backend/app/scanners/`

- `base.py` defines the `SecurityScanner` contract and normalized scanner result/finding dataclasses.
- `bandit.py` invokes `sys.executable -m bandit -f json <target>` with `shell=False`, `stdin=DEVNULL`, captured output, `check=False`, and a configurable timeout.
- Valid Bandit JSON remains usable when findings cause a non-zero exit code. Missing output, malformed JSON, invalid finding data, startup failure, and timeout become scanner errors.
- Bandit LOW/MEDIUM/HIGH severity and confidence values map directly to application enums. Bandit has no CRITICAL category, so none is fabricated.
- Original Bandit finding objects are preserved in `raw_metadata`.

### `backend/app/services/scanner_service.py`

- Transitions scans from `queued` to `running`, persists normalized findings, calculates counts, and transitions to `completed`.
- Scanner or persistence failures transition scans to `failed`.
- Always removes the temporary upload path after scanning.

Typical healthy response:

```json
{
  "status": "ok",
  "backend": { "status": "ok" },
  "database": { "status": "ok" }
}
```

Typical local response when Docker/PostgreSQL is unavailable:

```json
{
  "status": "degraded",
  "backend": { "status": "ok" },
  "database": { "status": "unavailable" }
}
```

## Frontend details

### `frontend/src/app/page.tsx`

- Uses the browser `fetch` API to call `${NEXT_PUBLIC_API_URL}/api/health`.
- Defaults to `http://localhost:8000` when `NEXT_PUBLIC_API_URL` is not set.
- Displays separate status cards for the backend and PostgreSQL.
- Displays `checking` while the request is pending.
- Displays a useful connection error if the backend cannot be reached.
- Displays the overall `ok` or `degraded` status returned by FastAPI.
- Contains no backend secrets or private environment variables.

### Upload UI

The home page includes a minimal Python upload form. It submits `FormData` to the backend and displays the Scan ID, completed/failed status, filename, and actual finding count. It does not implement the Milestone 5 findings dashboard.

### Styling

`frontend/src/app/globals.css` provides a small responsive interface for the health dashboard. It is intentionally functional rather than a complete product dashboard; the findings UI belongs to Milestone 5.

## PostgreSQL configuration

`docker-compose.yml` defines one service:

- Service: `postgres`
- Image: `postgres:16-alpine`
- Database, username, and password come from environment variables.
- Data is persisted in the named Docker volume `postgres_data`.
- Host port defaults to `5432`.
- A `pg_isready` healthcheck is configured.

Required local setup:

```text
Copy .env.example to .env
Set POSTGRES_PASSWORD to a local-only value
```

Never commit `.env`. The root `.gitignore` excludes it while allowing `.env.example`.

## Commands

### Start PostgreSQL

Run from the repository root:

```bash
docker compose up -d
```

### Start the backend

Run from `backend/`:

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
python -m alembic upgrade head
uvicorn app.main:app --reload
```

### Start the frontend

Run from `frontend/`:

```bash
npm install
npm run dev
```

### Test the backend

Run from `backend/`:

```bash
python -m pytest tests -q
```

### Apply or reverse migrations

Run from `backend/`:

```bash
python -m alembic upgrade head
python -m alembic downgrade base
```

### Validate the frontend

Run from `frontend/`:

```bash
npm run lint
npm run typecheck
npm run build
```

## Verification completed

The following checks passed during Milestone 1 through Milestone 4 implementation:

- Backend suite: `24 passed`, including health, persistence, upload, Bandit, and API integration tests.
- Bandit 1.9.4 was installed and real scans generated findings from deliberately vulnerable Python.
- Malformed output, timeout, missing executable, clean scan, vulnerable scan, and scanner failure tests passed.
- Temporary files were removed after every scan outcome.
- Browser upload verification displayed a completed Scan and actual finding count.
- Live API verification produced `B105` with `LOW` severity for a deliberate hardcoded-password sample and zero findings for a clean sample.
- Alembic migration: upgrade to `0001_scan_finding` and downgrade to `base` passed against an isolated temporary SQLite test database.
- Frontend ESLint: passed.
- Frontend TypeScript check: passed.
- Frontend production build: passed.
- FastAPI served successfully on `http://localhost:8000`.
- Next.js served successfully on `http://localhost:3000`.
- Browser verification confirmed that the frontend fetched the backend health response and rendered:
  - Backend API: `ok`
  - PostgreSQL: `unavailable` when Docker was not installed
  - Overall status: `degraded`

The development servers were stopped after verification. Start them again with the commands above.

## Known environment limitation

Docker was not installed or available on `PATH` in the implementation environment. Therefore PostgreSQL could not be started there. The Compose file was created, but a fully healthy database response still needs to be verified on a machine with Docker Desktop running.

The missing Docker executable is an environment limitation, not an application fallback. Do not replace PostgreSQL with SQLite unless the build plan is explicitly changed.

## Security notes

- No API keys or real credentials are stored in the repository.
- `.env.example` contains only a placeholder password value.
- Backend secrets are not prefixed with `NEXT_PUBLIC_`.
- No uploaded source files or scanner commands exist yet.
- No user-provided content is executed.
- The health route uses the shared SQLAlchemy engine and a parameter-free static SQL probe (`SELECT 1`).
- Future scanner subprocesses must use argument arrays with `shell=False` and must never concatenate shell commands.

## Next implementation: Milestone 5

The exact next milestone is **Milestone 5 - Findings dashboard**.

Implement only these items next:

1. Build the findings results view.
2. Add severity badges and finding cards.
3. Display paths, line numbers, scanner, rule ID, descriptions, and snippets.
4. Add severity filtering.

Required persistence behavior:

- Create a scan.
- Update scan status.
- Create findings.
- Retrieve findings.
- Retrieve a scan summary.

Maintain the existing route/service/repository separation. Do not implement Gitleaks, other scanners, AI, or finding detail/AI views until their specified milestones.

## Handoff rules for future AI sessions

1. Read `SECURECODE_AI_COPILOT_BUILD_PLAN.md` completely before making architectural changes.
2. Read this file to understand the current implementation state.
3. Inspect the repository and preserve unrelated user changes.
4. Work on one milestone only.
5. Run focused tests after edits, then run the complete checks for the milestone.
6. Do not claim PostgreSQL is healthy unless Docker and the database have actually been started and verified.
7. Do not commit secrets, generated dependencies, `.env`, `.next`, or TypeScript build metadata.
8. Stop and report after Milestone 5 verification; wait for explicit authorization before Milestone 6.
