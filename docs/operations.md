# Operations guide

## Probes

- `GET /api/live` is liveness. It should remain `200` while the process can answer.
- `GET /api/health` is readiness. It returns `200` only when the database and
  expected schema can be queried; database failure returns `503` without details.
- Responses include `X-Request-ID`. Preserve that value when reporting a failure.

## Common startup failures

| Symptom | Check |
|---|---|
| API refuses to start with provider configuration | Keep `AI_PROVIDER=mock`, or set `AI_PROVIDER=gemini` and a non-empty `GEMINI_API_KEY`. |
| API readiness is `503` | Check PostgreSQL reachability and run `python -m alembic upgrade head` from `backend/`. |
| Upload returns `429` | Per-worker scan capacity is full; retry after active work finishes. |
| Scan returns `failed` | The persisted `failure_reason` is intentionally generic. Check server logs by `X-Request-ID`; source and subprocess diagnostics are not returned. |
| Analysis returns local fallback | Gemini was unavailable or invalid; review the saved provider value `mock-fallback`. |

## Local Compose

Copy `.env.example` to `.env`, set `POSTGRES_PASSWORD` and a random `API_KEY`, then:

```text
docker compose config --quiet
docker compose up --build -d
curl http://127.0.0.1:8000/api/live
curl http://127.0.0.1:8000/api/health
docker compose down
```

The backend and frontend containers are non-root, drop capabilities, use a
read-only root filesystem with tmpfs scratch space, and bind local ports to
loopback. The PostgreSQL volume is persistent; scan source files are temporary in
the backend upload tmpfs. This Compose posture is for controlled local use, not a
complete public deployment policy.

## Data and deletion

PostgreSQL retains scan metadata, normalized findings, source snippets, and saved
analysis until the authenticated delete endpoint is confirmed. Deletion cascades
from scan to findings and analyses. It does not erase database backups or reports
already downloaded by an operator. No automated retention or backup policy is
implemented by the application.
