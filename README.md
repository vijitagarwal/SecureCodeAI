# SecureCode AI

SecureCode AI is a local security-analysis platform for reviewing Python security findings. It accepts source as untrusted data, runs deterministic Bandit analysis without importing or executing the upload, enriches findings with conservative CWE/OWASP mappings, and provides a local structured AI-analysis workflow.

## Prerequisites

- Python 3.11+
- Node.js 20+
- Docker Desktop

## Setup

Copy `.env.example` to `.env` and set a local PostgreSQL password. The complete stack can then be started with:

```bash
docker compose up --build
```

The frontend is available at http://localhost:3000 and the API at http://localhost:8000. For a non-Docker backend setup, start PostgreSQL first and then run the backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Apply database migrations before starting the backend:

```bash
cd backend
python -m alembic upgrade head
```

Start the frontend in another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000. The page reports service health, provides the Python upload form, and displays persisted findings with severity filtering. The API endpoint is http://localhost:8000/api/health.

## Secure upload

The API accepts Python source files only through:

```text
POST /api/scans
Content-Type: multipart/form-data
```

Example request:

```bash
curl -X POST http://localhost:8000/api/scans \
	-F "file=@example.py"
```

Successful uploads return:

```json
{
	"scan_id": 123,
	"status": "completed",
	"filename": "example.py",
	"total_findings": 1
}
```

The maximum upload size is 5 MB by default (`MAX_UPLOAD_SIZE_BYTES=5242880`). The limit is configurable through backend environment variables. Only the `.py` extension is accepted, case-insensitively; the MIME type is not trusted as the validation mechanism.

AI analysis defaults to the deterministic local provider (`AI_PROVIDER=mock`). No API key is required for local development.

Files are written to the configurable `UPLOAD_DIR`, which defaults to the operating system temporary directory under `securecode-ai`. Storage names are generated UUIDs with a `.py` suffix, never the user-provided filename. The temporary file is retained for the upcoming scanner pipeline and is not permanent user storage.

Uploaded Python is treated as data only. Bandit performs static analysis through a safe subprocess; the source is never imported or executed. Invalid extensions, traversal-style filenames, missing or empty files, oversized files, storage failures, scanner failures, and database failures are handled without exposing filesystem or database internals.

## Bandit analysis

Bandit `1.9.4` is invoked with JSON output and a 30-second configurable timeout (`SCANNER_TIMEOUT_SECONDS`). Valid JSON is parsed even when Bandit returns a non-zero exit code because findings exist. Findings are normalized into the application Finding model, persisted with raw Bandit metadata, and used to calculate scan severity counts. Bandit's LOW, MEDIUM, and HIGH severity/confidence values retain their semantics; no CRITICAL findings are fabricated.

After scanning, temporary files are deleted regardless of success, findings, timeout, malformed output, scanner startup failure, or persistence failure.

Results can be retrieved through:

```text
GET /api/scans/{scan_id}
GET /api/scans/{scan_id}/findings
```

## Tests and checks

Backend tests use an isolated SQLite database when PostgreSQL is unavailable. This does not change the production PostgreSQL configuration.

```bash
cd backend
python -m pytest tests -q

# Migration verification
python -m alembic upgrade head
python -m alembic downgrade base

cd ../frontend
npm run lint
npm run typecheck
npm run build
```

The current dashboard provides upload, scan status, finding count, severity filtering, finding locations, scanner rule IDs, confidence, CWE/OWASP classification, remediation guidance, and local mock AI analysis. The mock provider is deterministic and does not require credentials. Live provider integration, authentication, and asynchronous job queues remain outside the current local MVP.

If a findings request fails after a scan completes, use the dashboard's **Retry loading findings** control rather than uploading the file again. The health panel similarly provides a retry control for transient backend availability errors.
