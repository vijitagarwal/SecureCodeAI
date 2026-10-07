# PROJECT DOSSIER — SecureCode AI

---

## 1. Project Identity

| Field | Value |
|---|---|
| **Project Name** | SecureCode AI |
| **Current Path** | `D:\UOS\securecode-ai\` |
| **Status** | Active |
| **Approximate Maturity** | ~55% complete (backend solid, frontend minimal) |
| **Original Purpose** | Automated code security scanning platform |
| **Current Purpose** | Python file upload → Bandit static analysis → security findings stored in PostgreSQL |
| **Portfolio-Worthy** | ✅ Yes — clean professional backend, real security tooling |
| **Primary Category** | Cybersecurity / Developer Tool |

---

## 2. Problem Being Solved

Developers writing Python code need quick, automated identification of security vulnerabilities without running tools manually. SecureCode AI provides a REST API where users upload a `.py` file, the backend runs Bandit (a well-known Python security linter) on it, and returns structured vulnerability findings (severity, confidence, line number, code snippet) stored in a PostgreSQL database.

**Target User:** Developers, security teams, educators teaching secure code practices.

**Core Value Proposition:** Upload Python code → get a structured security vulnerability report. Eventually: AI-enhanced explanation and remediation suggestions (planned, not implemented).

---

## 3. Product Vision

### Implemented
- POST `/api/scans` — upload a `.py` file, run Bandit scanner, return scan results
- GET `/api/scans/{scan_id}` — retrieve scan metadata
- GET `/api/scans/{scan_id}/findings` — retrieve all findings for a scan
- GET `/api/health` — health check
- Full PostgreSQL persistence (Scan + Finding models with Alembic migrations)
- Secure file upload handling (filename validation, path traversal protection, size limit)
- Bandit scanner wrapper with JSON output parsing
- Structured Pydantic schemas for API responses
- Docker Compose for local PostgreSQL setup
- Repository pattern for database access

### Partially Implemented
- Frontend exists but appears minimal (directory present, content not fully inspected — likely scaffold only based on the AI build context documentation)

### Planned (from `AI_BUILD_CONTEXT.md` and `SECURECODE_AI_COPILOT_BUILD_PLAN.md`)
- AI-powered vulnerability explanations (LLM integration for "why is this dangerous + how to fix")
- Multiple scanner support (Semgrep, Bandit — currently only Bandit)
- Authentication / user accounts
- Scan history per user
- Frontend UI (code viewer with highlighted findings)
- CI/CD integration hooks

---

## 4. Feature Inventory

| Feature | Status | Evidence | Important Files |
|---|---|---|---|
| File Upload Endpoint | Implemented | `POST /api/scans`, `upload_service.py` | `backend/app/api/routes/scans.py`, `backend/app/services/upload_service.py` |
| Filename Validation | Implemented | `.py` only, length limits, path traversal check | `backend/app/services/upload_service.py` |
| Bandit Scanner | Implemented | `BanditScanner.scan()` runs bandit via subprocess, parses JSON | `backend/app/scanners/bandit.py` |
| Scan Persistence | Implemented | `Scan` model with status, counts, timestamps | `backend/app/db/models.py` |
| Finding Persistence | Implemented | `Finding` model with severity, confidence, code snippet | `backend/app/db/models.py` |
| Scan Retrieval | Implemented | `GET /api/scans/{id}`, `GET /api/scans/{id}/findings` | `backend/app/api/routes/scans.py` |
| Repository Pattern | Implemented | `scan_repository.py`, `finding_repository.py` | `backend/app/db/repositories/` |
| Alembic Migrations | Implemented | `alembic/` directory present | `backend/alembic/` |
| Docker Compose (DB) | Implemented | PostgreSQL 16-alpine with healthcheck | `docker-compose.yml` |
| Health Check | Implemented | `GET /api/health` | `backend/app/api/routes/health.py` |
| Frontend UI | Unknown/Partial | Directory present, content not deeply inspected | `frontend/` |
| Authentication | Planned | Not present in backend | — |
| AI Explanation | Planned | Referenced in build plan docs | — |
| Multiple Scanners | Partial | `base.py` defines abstract `SecurityScanner`, only Bandit implemented | `backend/app/scanners/base.py` |
| Tests | Present | `tests/` directory in backend, pytest + httpx configured | `backend/tests/` |

---

## 5. Architecture

```
User/Client
  ↓ HTTP POST (multipart/form-data)
FastAPI Backend
  → upload_service.py validates filename and file size
  → creates Scan record in DB (status: queued)
  → writes temp file to disk
  → calls scanner_service.run_scan()
    → BanditScanner.scan() invokes: python -m bandit -f json <file>
    → parses bandit JSON output → creates Finding records
    → updates Scan status to "completed" + finding counts
  ↓
PostgreSQL (local via Docker Compose, or external)
  → scans table
  → findings table

GET requests return scan metadata and findings list.
```

---

## 6. Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| Backend | FastAPI | REST API |
| Scanner | Bandit (Python CLI) | Static security analysis |
| ORM | SQLAlchemy 2.0 | Database access (modern mapped_column style) |
| Migrations | Alembic | Schema versioning |
| Database | PostgreSQL 16 | Persistence |
| Validation | Pydantic (pydantic-settings) | Request/response schemas, config |
| Testing | pytest + httpx | API tests |
| Frontend | (Next.js — unclear from inspection) | UI (minimal/scaffold) |
| Container | Docker Compose | Local PostgreSQL setup |

---

## 7. Repository / Directory Structure

```
securecode-ai/
├── README.md
├── AI_BUILD_CONTEXT.md             # Detailed build context for AI assistants
├── SECURECODE_AI_COPILOT_BUILD_PLAN.md  # Build plan with feature roadmap
├── .env.example                    # Environment variable template
├── docker-compose.yml              # PostgreSQL 16-alpine service
├── backend/
│   ├── requirements.txt            # fastapi, bandit, sqlalchemy, alembic, psycopg, pytest
│   ├── alembic.ini                 # Alembic config
│   ├── alembic/                    # Migration files
│   └── app/
│       ├── main.py                 # FastAPI app + router registration
│       ├── api/routes/
│       │   ├── health.py           # GET /api/health
│       │   └── scans.py            # POST /api/scans, GET /api/scans/{id}, GET /api/scans/{id}/findings
│       ├── core/
│       │   └── config.py           # Settings (DATABASE_URL, UPLOAD_DIR, scanner timeout, max file size)
│       ├── db/
│       │   ├── database.py         # SQLAlchemy engine + Base + get_db()
│       │   ├── models.py           # Scan + Finding SQLAlchemy models (enums: ScanStatus, FindingSeverity, FindingConfidence)
│       │   └── repositories/       # scan_repository.py + finding_repository.py
│       ├── scanners/
│       │   ├── base.py             # Abstract SecurityScanner, ScannerFinding, ScannerResult dataclasses
│       │   └── bandit.py           # BanditScanner implementation
│       ├── schemas/                # Pydantic schemas (ScanUploadResponse, ScanDetailResponse, FindingResponse)
│       └── services/
│           ├── upload_service.py   # File upload validation + scan orchestration
│           └── scanner_service.py  # run_scan() — updates Scan status, persists findings
└── frontend/                       # UI (appears minimal/scaffold)
    └── ...
```

---

## 8. Backend Deep Dive

### Entry Point
- **File:** `backend/app/main.py`
- **Framework:** FastAPI
- **CORS:** Restricted to `settings.allowed_origins` (not wildcard — more secure than FocusFriend)
- **Allowed methods:** GET and POST only (minimal attack surface)

### API Endpoints

| Method | Endpoint | Purpose | Auth | Request | Response |
|---|---|---|---|---|---|
| GET | `/api/health` | Health check | None | — | `{"status": "ok", ...}` |
| POST | `/api/scans` | Upload Python file for scanning | None | multipart file `.py` | `ScanUploadResponse` (scan_id, status, filename, total_findings) |
| GET | `/api/scans/{scan_id}` | Get scan metadata | None | scan_id path param | `ScanDetailResponse` |
| GET | `/api/scans/{scan_id}/findings` | Get all findings for scan | None | scan_id path param | `list[FindingResponse]` |

**Note:** No authentication currently — any user can submit scans and retrieve results.

### Bandit Scanner (Confirmed from source)
```python
command = [sys.executable, "-m", "bandit", "-f", "json", target_path]
completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
payload = json.loads(completed.stdout)
findings = [self._parse_finding(item) for item in payload.get("results", [])]
```
- Invokes Bandit as a subprocess (correct approach — avoids import-time complexity)
- Parses JSON output → `ScannerFinding` dataclass with severity, confidence, file_path, line_number, code_snippet, raw_metadata
- Handles: timeout, FileNotFoundError (bandit not installed), malformed JSON

### Upload Service Security (Confirmed from source)
- Filename must be present and ≤ 255 chars
- Rejects null bytes (`\x00`)
- Rejects path separators (both POSIX and Windows via `PurePath`)
- Only `.py` extension allowed
- File written to temp location with `uuid4().hex` name (prevents overwrite)
- Enforces `settings.max_upload_size_bytes` by streaming chunks
- Cleans up temp file on any exception

### Scanner Service
- `run_scan(db, scan, filepath, scanner)` sets scan status to `running`, calls `scanner.scan()`, persists findings, updates Scan counts (`critical_count`, `high_count`, etc.), marks `completed` or `failed`

---

## 9. Database Deep Dive

**Technology:** PostgreSQL 16  
**ORM:** SQLAlchemy 2.0 (modern `Mapped`, `mapped_column` style)  
**Migrations:** Alembic (configured)

| Model/Table | Purpose | Important Fields | Relationships |
|---|---|---|---|
| `scans` | Tracks each uploaded file and its scan status | `id`, `name`, `status` (queued/running/completed/failed), `scanner_names`, `started_at`, `completed_at`, `total_findings`, `critical_count`, `high_count`, `medium_count`, `low_count` | Has many findings |
| `findings` | Individual vulnerability findings from scanner | `id`, `scan_id` (FK CASCADE), `tool`, `rule_id`, `title`, `description`, `severity` (CRITICAL/HIGH/MEDIUM/LOW/INFO), `confidence` (HIGH/MEDIUM/LOW), `file_path`, `line_number`, `code_snippet`, `raw_metadata` (JSON) | Belongs to scan |

**Indexes on findings:** `ix_findings_scan_id`, `ix_findings_severity`, `ix_findings_tool`, `ix_findings_rule_id`

---

## 10. Authentication & Authorization

**Current state:** None. No authentication on any endpoint. Any client can submit scans and read all scan results by ID.

This is a significant gap for production use — documented as planned in build docs.

---

## 11. Frontend Deep Dive

The `frontend/` directory exists. Based on `AI_BUILD_CONTEXT.md`, it is described as a Next.js UI. The directory was not deeply inspected, but its presence and the build plan suggest it may be a partial scaffold or early UI for displaying scan results.

**Status: Unknown/Partial** — cannot confirm what is actually implemented without deeper inspection.

---

## 12. AI / ML

**Current state:** No AI/ML in the current codebase. The name "SecureCode AI" implies AI features, but the current implementation is purely Bandit static analysis.

**Planned (from build docs):**
- LLM-powered vulnerability explanations ("why is this dangerous, how to fix it")
- Possibly Groq or OpenAI for explanation generation

**Evidence level:** Documented in `SECURECODE_AI_COPILOT_BUILD_PLAN.md` — not implemented.

---

## 13. External Services

| Service | Purpose | Where Used | Required? |
|---|---|---|---|
| PostgreSQL | Data persistence | Backend DATABASE_URL | Yes |
| Bandit | Static code analysis | Called as subprocess | Yes (must be installed) |

---

## 14. Environment Configuration

From `.env.example`:
```
DATABASE_URL=<postgresql+psycopg://user:password@localhost:5432/securecode>
POSTGRES_DB=securecode
POSTGRES_USER=securecode
POSTGRES_PASSWORD=<secret>
POSTGRES_PORT=5432
UPLOAD_DIR=<path to upload directory>
SCANNER_TIMEOUT_SECONDS=30
MAX_UPLOAD_SIZE_BYTES=524288
ALLOWED_ORIGINS=http://localhost:3000
```

---

## 15. Deployment

- No Dockerfile for the application itself (only Docker Compose for local PostgreSQL)
- No cloud deployment configured or documented
- Local development only: `uvicorn app.main:app --reload`
- Production deployment not set up — would need Dockerfile + hosting config

---

## 16. Testing

- `tests/` directory present in `backend/`
- pytest + httpx configured in `requirements.txt`
- `.pytest_cache/` present — tests have been run
- Specific test content not inspected, but infrastructure is in place

---

## 17. Current State Assessment

### Working
- Bandit scanner integration (subprocess invocation, JSON parsing, finding extraction)
- Upload service with proper security validation
- PostgreSQL persistence via SQLAlchemy
- REST API for scan lifecycle (create → read → findings)
- Alembic migration setup

### Partially Working
- Frontend (status unclear)
- Scanner abstraction (base class defined, only Bandit implemented)

### Broken
- No authentication — privacy/security gap
- "AI" in name is aspirational — no AI currently implemented

### Unknown
- Frontend actual state
- Whether tests pass currently
- Whether Alembic migrations have been applied to a running database

---

## 18. Known Problems

- No authentication — public scan API
- No AI features despite "AI" branding
- Frontend status unclear
- No Dockerfile for the backend application itself
- Bandit must be installed in the Python environment (it's in requirements.txt — OK)
- Scanner runs synchronously in request handler — could time out for large files
- Temp files created during upload may accumulate if cleanup fails

---

## 19. Technical Debt

### Critical
- No authentication

### High
- Synchronous Bandit execution blocks request thread — no background task queue
- No Dockerfile for app deployment

### Medium
- Frontend not built or incomplete
- "SecureCode AI" name implies AI that doesn't exist

### Low
- Only one scanner despite abstract base for multiple
- No rate limiting on file uploads

---

## 20. Future Roadmap

From build planning documents:
- [ ] Add authentication (user accounts, API keys)
- [ ] Add LLM-powered finding explanations
- [ ] Add Semgrep scanner support
- [ ] Build complete frontend UI (code viewer with finding highlights)
- [ ] Background task queue for scans (Celery or FastAPI BackgroundTasks)
- [ ] CI/CD integration (GitHub Actions webhook)
- [ ] Rate limiting per user/IP

---

## 21. Important Files

| File | Why It Matters |
|---|---|
| `backend/app/main.py` | FastAPI entry point, router registration |
| `backend/app/api/routes/scans.py` | All scan endpoints |
| `backend/app/scanners/bandit.py` | Core scanning logic — Bandit integration |
| `backend/app/scanners/base.py` | Abstract scanner interface (extensibility point) |
| `backend/app/services/upload_service.py` | File validation + scan orchestration |
| `backend/app/services/scanner_service.py` | Scan execution + DB persistence |
| `backend/app/db/models.py` | Scan + Finding database models |
| `docker-compose.yml` | Local PostgreSQL setup |
| `AI_BUILD_CONTEXT.md` | Detailed project context and planned features |
| `SECURECODE_AI_COPILOT_BUILD_PLAN.md` | Full feature roadmap |

---

## 22. How To Run

### Prerequisites
- Python 3.11+
- Docker (for local PostgreSQL)
- `DATABASE_URL`, `UPLOAD_DIR` env vars

### Development
```bash
# Start local database
docker compose up -d

cd securecode-ai/backend
pip install -r requirements.txt

# Run migrations (if Alembic configured)
alembic upgrade head

# Start server
uvicorn app.main:app --reload
```

---

## 23. Git / Repository State

- Git repository present
- Active development — appears in early implementation phase
- `.pytest_cache/` present indicating tests have been run

---

## 24. Relationship To Other Projects

- **Related to:** `hacklab/`, `purple-team-platform/`, `sentinel-url-scanner/` — all in the cybersecurity family
- **Differentiator:** SecureCode AI is the only project focused on *developer-side* security (code analysis) rather than *runtime/network* security
- **Future integration:** Could feed findings into HackLab scenarios or portfolio demonstrations

---

## AI HANDOFF

**What it is:** SecureCode AI is a REST API platform for automated Python code security scanning. Users upload `.py` files, the backend runs Bandit (Python static analyzer) as a subprocess, and stores structured vulnerability findings in PostgreSQL. The name "AI" is currently aspirational — no AI/ML is implemented yet.

**Why it exists:** To provide automated security analysis for Python code with plans for AI-powered vulnerability explanations.

**Architecture:** FastAPI backend → secure file upload → Bandit subprocess → findings parsed → PostgreSQL persistence. No frontend confirmed as functional. No authentication.

**Key technologies:** FastAPI, Bandit, SQLAlchemy 2.0, Alembic, PostgreSQL, psycopg3.

**Current state:** Backend fully functional — scanner, persistence, API endpoints all implemented. No authentication, no AI features, frontend unclear.

**Scanner logic:** `BanditScanner.scan()` runs `python -m bandit -f json <filepath>`, parses JSON output, maps to `ScannerFinding` dataclasses with severity/confidence/line/snippet.

**Known problems:** No auth, no AI despite name, no Dockerfile for deployment, synchronous scan blocking.

**Next likely work:** Add LLM explanations (Groq/OpenAI), add authentication, build/complete frontend, add Dockerfile.
