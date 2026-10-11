# SecureCode AI

SecureCode AI is a local security-analysis platform for reviewing Python security findings. It accepts source as untrusted data, runs deterministic Bandit analysis without importing or executing the upload, enriches findings with conservative CWE/OWASP mappings, and provides a local structured AI-analysis workflow.

## Prerequisites

- Python 3.11+
- Node.js 22.12+
- Docker Desktop

## Setup

Copy `.env.example` to `.env`, set a local PostgreSQL password and a random `API_KEY`
(at least 32 characters). Generate a key with `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
All scan, history, report, deletion, and analysis API requests require
`Authorization: Bearer <API_KEY>`. The frontend keeps this key in memory only.
The complete stack can then be started with:

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
	-H "Authorization: Bearer $API_KEY" \
	-F "file=@example.py"
```

Successful uploads return:

```json
{
	"scan_id": 123,
	"status": "completed",
	"filename": "example.py",
	"total_findings": 1,
	"failure_reason": null
}
```

The maximum upload size is 5 MB by default (`MAX_UPLOAD_SIZE_BYTES=5242880`). The limit is configurable through backend environment variables. Only the `.py` extension is accepted, case-insensitively; the MIME type is not trusted as the validation mechanism.

AI analysis defaults to the deterministic local provider (`AI_PROVIDER=mock`). It is
clearly labeled as rule-based guidance in the UI. Gemini can be enabled with
`AI_PROVIDER=gemini`, `GEMINI_API_KEY`, and an optional `GEMINI_MODEL`; the backend
fails fast if a remote provider is selected without its credential. Remote analysis
receives only the selected finding context and remains a review artifact.

Files are written to the configurable `UPLOAD_DIR`, which defaults to the operating system temporary directory under `securecode-ai`. Storage names are generated UUIDs with a `.py` suffix, never the user-provided filename. The temporary file is retained for the upcoming scanner pipeline and is not permanent user storage.

Uploaded Python is treated as data only. Bandit performs static analysis through a safe subprocess; the source is never imported or executed. Invalid extensions, traversal-style filenames, missing files, oversized files, storage failures, scanner failures, and database failures are handled without exposing filesystem or database internals.

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

The current dashboard provides workspace unlock, upload, persisted scan history,
scan deletion, severity filtering, paginated findings, finding locations, scanner
rule IDs, confidence, CWE/OWASP classification, remediation guidance, saved
analysis, and JSON report export. The mock provider is deterministic and does not
require credentials. Scans are bounded synchronous jobs; the API moves blocking
scanner/provider work off the async event loop and rejects excess concurrent work.

## Provider configuration

| Setting | Default | Purpose |
|---|---|---|
| `AI_PROVIDER` | `mock` | `mock` for local deterministic guidance or `gemini` for remote analysis |
| `GEMINI_API_KEY` | empty | Required when `AI_PROVIDER=gemini`; never sent to the frontend |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model identifier |
| `AI_TIMEOUT_SECONDS` | `20` | Per-provider request timeout, from 1 to 60 seconds |
| `MAX_AI_RESPONSE_BYTES` | `131072` | Maximum decompressed provider response size |
| `MAX_CONCURRENT_SCANS` | `2` | Per-worker scanner capacity |
| `MAX_CONCURRENT_ANALYSES` | `2` | Per-worker analysis capacity |

The Gemini boundary is covered with a transport double in the backend tests. If a
configured Gemini request fails, the API can save deterministic local guidance with
provider provenance `mock-fallback`; the UI identifies that remote AI was
unavailable. No live provider credential is stored in the repository or required by
CI.
