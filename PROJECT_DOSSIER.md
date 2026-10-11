# SecureCode AI — Current Project Dossier

## Product identity

SecureCode AI is a single-operator Python security review workspace. A developer
unlocks the workspace with a server-configured bearer key, uploads one Python file,
receives a persisted Bandit report, reviews normalized findings, requests saved
structured guidance, exports JSON, and can delete the retained report and source
snippets.

The product is intentionally local-first. Uploaded Python is data for static
analysis; it is never imported, evaluated, executed, installed, or used to invoke
an uploaded command. The default analysis provider is deterministic local guidance.
An optional Gemini boundary is available when explicitly configured.

## Current status

The complete local vertical slice is implemented and tested. The architecture is
appropriate for a single-operator workspace and consists of:

```text
Next.js dashboard
    ↓ bearer key kept in tab memory
FastAPI API + request/resource boundaries
    ↓ generated 0600 temporary file
Bandit subprocess in isolated environment
    ↓ normalized findings + conservative CWE/OWASP enrichment
PostgreSQL-compatible SQLAlchemy persistence
    ↓ optional analysis boundary
Deterministic mock guidance or bounded Gemini provider
```

## Implemented capabilities

### API

- `GET /api/health` — unauthenticated readiness probe with generic database status.
- `GET /api/workspace` — authenticated workspace limits and analysis provider.
- `POST /api/scans` — authenticated, bounded multipart Python upload and scan.
- `GET /api/scans` — authenticated paginated scan history.
- `GET /api/scans/{scan_id}` — persisted scan status, counters, and safe failure reason.
- `GET /api/scans/{scan_id}/findings` — paginated, severity-filtered findings.
- `GET /api/scans/{scan_id}/report` — bounded JSON report export.
- `DELETE /api/scans/{scan_id}` — confirmed frontend deletion with cascade cleanup.
- `POST/GET /api/findings/{finding_id}/analysis` — idempotent persisted analysis.

### Security controls

- Public `/api/live` and database-backed `/api/health` are separated; all workspace
  routes require the bearer key before multipart parsing and return request IDs.
- Bearer-key authentication fails closed before multipart parsing.
- Constant-time API-key comparison and no credential persistence in the browser.
- Request body, upload size, upload time, scanner output, finding count, scan time,
  provider response, and concurrent scan/analysis capacity are bounded.
- Filename metadata is validated; storage uses generated names, exclusive creation,
  restrictive permissions, and unconditional cleanup.
- Bandit receives one argument with `shell=False`, no stdin, an isolated working
  directory, a reduced environment, and `--ignore-nosec`.
- Invalid syntax, malformed scanner data, scanner errors, timeouts, and persistence
  failures become failed scans rather than clean results.
- Source snippets are rendered as text in React and are not interpreted as HTML.
- Error responses and logs avoid source, credentials, subprocess stderr, and database
  internals.
- Security headers, non-root containers, dropped container capabilities, and
  loopback-only local Compose ports are configured. Application containers use
  read-only root filesystems with tmpfs scratch space.

### Analysis boundary

`LLMProvider` accepts only the selected rule, finding text, snippet, classification,
severity, and confidence. The local provider is deterministic and labeled as such.
Gemini uses a fixed HTTPS endpoint with no redirects or retries, bounded timeout and
response size, structured JSON output validation, and prompt-injection-resistant
instructions. Generated code and diffs are review artifacts; they are never applied
or executed. Provider and model provenance is persisted with each analysis.

## Data model

- `scans`: original display filename, lifecycle status, timestamps, scanner names,
  complete severity counters, and generic failure reason.
- `findings`: normalized tool/rule data, severity/confidence, display location,
  bounded source snippet, raw scanner metadata, classification, and remediation.
- `security_analyses`: one idempotent analysis per finding, provider/model provenance,
  validated explanation, optional proposed code, review diff, and confidence.

Alembic migrations are authoritative. SQLite is used only by isolated automated
tests when a PostgreSQL service is unavailable; production configuration remains
PostgreSQL-compatible.

## Validation

Backend:

```text
cd backend
python -m pytest tests -q
pip-audit -r requirements.txt
```

Frontend:

```text
cd frontend
npm run lint
npm test
npm run typecheck
npm run build
npm audit --omit=dev --audit-level=high
```

CI provisions PostgreSQL for the migration/workflow test, audits Python and npm
dependencies, and builds/smoke-tests the Compose containers. Live Gemini and
browser interaction still depend on credentials or a browser environment; local
Docker and PostgreSQL are unavailable in the current workspace.

The practical threat model is documented in `docs/threat-model.md`; operator
startup, probes, data lifecycle, and failure diagnostics are in `docs/operations.md`.

## Deliberate future extensions

Multi-user identity and tenant isolation, distributed rate limiting, asynchronous
job queues, additional scanners, repository/Git integration, RAG, and CI/CD
webhooks are outside the current single-operator scope. They should preserve the
existing trust boundaries if added.

## Important files

| Area | Files |
|---|---|
| API and app | `backend/app/main.py`, `backend/app/api/routes/` |
| Configuration/security | `backend/app/core/config.py`, `backend/app/security/` |
| Scanner | `backend/app/scanners/bandit.py`, `backend/app/services/scanner_service.py` |
| Persistence | `backend/app/db/models.py`, `backend/app/db/repositories/`, `backend/alembic/` |
| Analysis | `backend/app/llm/`, `backend/app/services/analysis_service.py` |
| UI | `frontend/src/app/`, `frontend/src/components/`, `frontend/src/lib/` |
| Deployment | `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile` |
