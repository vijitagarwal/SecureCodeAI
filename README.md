# SecureCode AI

SecureCode AI is a local security-analysis platform. Milestone 3 provides a secure Python source upload pipeline on top of the SQLAlchemy persistence layer.

## Prerequisites

- Python 3.11+
- Node.js 20+
- Docker Desktop

## Setup

Copy `.env.example` to `.env` and set a local PostgreSQL password. Then start PostgreSQL:

```bash
docker compose up -d
```

Start the backend in one terminal:

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

Open http://localhost:3000. The page reports service health and provides the Python upload form. The API endpoint is http://localhost:8000/api/health.

## Secure upload

Milestone 3 accepts Python source files only through:

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
	"status": "queued",
	"filename": "example.py"
}
```

The maximum upload size is 5 MB by default (`MAX_UPLOAD_SIZE_BYTES=5242880`). The limit is configurable through backend environment variables. Only the `.py` extension is accepted, case-insensitively; the MIME type is not trusted as the validation mechanism.

Files are written to the configurable `UPLOAD_DIR`, which defaults to the operating system temporary directory under `securecode-ai`. Storage names are generated UUIDs with a `.py` suffix, never the user-provided filename. The temporary file is retained for the upcoming scanner pipeline and is not permanent user storage.

Uploaded Python is treated as data only. Milestone 3 introduces no subprocesses, imports, dynamic execution, scanner, or AI behavior. Invalid extensions, traversal-style filenames, missing files, oversized files, storage failures, and database failures are handled without exposing filesystem or database internals.

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

Scanners, findings APIs, and AI behavior are intentionally not part of Milestone 3. Bandit begins in Milestone 4.
