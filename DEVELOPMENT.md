# Development

## Local setup

Use Python 3.11+ and Node.js 20+. Copy `.env.example` to `.env`, set `POSTGRES_PASSWORD`, and run `docker compose up --build` for the complete stack.

For backend-only work, install `backend/requirements.txt`, apply migrations with `python -m alembic upgrade head`, and start `uvicorn app.main:app --reload` from `backend/`.

## Validation

```text
cd backend
python -m pytest tests -q
cd ../frontend
npm run lint
npm run typecheck
npm run build
```

The backend tests use isolated SQLite fixtures where a live PostgreSQL service is unnecessary. Bandit subprocess behavior is tested with both the installed scanner and deterministic mocks.

Finding responses are paginated at the API boundary so a scan with many findings cannot produce an unbounded response.

The default `AI_PROVIDER=mock` is deterministic and local, so analysis tests do not need an API key. Provider-specific integrations should be added behind `LLMProvider` and covered with fakes for malformed output, timeouts, and provider failures.

## Migrations

Create and review Alembic migrations before changing persisted models. Do not recreate the production database to apply schema changes.

## Workflow

Keep uploads and scanner output untrusted, preserve response schemas, add a regression test for security fixes, and run the smallest relevant checks before committing.
