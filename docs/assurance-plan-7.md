# Plan 7: assurance evidence

## Reproduced baseline

Starting checkpoint: `4151dc97c1e1e2b147f5abf899c79edf419d5014`, clean `main`.
Python 3.14.2, Node 24.12.0, npm 11.6.2 on Windows.

- `cd backend; python -m pytest tests -q`: 93 passed, 1 skipped (no TEST_POSTGRES_URL).
- `cd frontend; npm run lint`, `npm run typecheck`, `npm test`, `npm run build`: passed; 5 interaction tests.
- Docker, Podman, psql, pg_ctl are not on PATH. No container or live PostgreSQL claim.

## Product / trust map

Memory-only browser key → authenticated API boundary → bounded multipart upload →
generated temporary path → Bandit subprocess → normalized findings / transactional
counts → SQLAlchemy persistence → paginated findings / report / cascade deletion.
Analysis is explicitly requested for one finding → deterministic provider or fixed
Gemini endpoint → bounded schema → saved provenance → text-only review UI.

All key holders share all data. Integer IDs are not authorization boundaries. Public
health exposes generic availability; schemas/docs expose no workspace data.

## Findings resolved in this mission

- Upload ownership is tracked after exclusive creation, worker sessions are
  thread-owned, request framing is strict, and authentication/resource boundary
  regressions are covered.
- Scanner output is drained through a bounded pipe, direct processes are reaped,
  POSIX process groups are terminated on timeout, targets can be restricted to the
  approved upload root, and actual timeout/output/encoding fixtures pass.
- Gemini responses have configured size and elapsed-time checks plus HTTP client
  timeouts. Provider errors can produce explicitly labeled `mock-fallback` guidance;
  mocked HTTP failures remain distinct from a live-provider verification.
- Reports have an explicit byte ceiling in addition to finding/pagination bounds;
  export, Unicode, analysis association, and cascade deletion are covered.
- API and operator documentation now describe liveness/readiness, request IDs,
  limits, data deletion, Compose posture, and CI container/dependency checks.

## Residual review queue

1. A hard process kill or host crash can leave a `running` scan record until an
   operator reconciles it. Automatic reconciliation needs an execution lease or
   durable queue and should not mark another worker's live scan failed.
2. Limits and semaphores are per process/worker. Shared deployments still need an
   external rate limiter, worker sizing, retention policy, and database pool policy.
3. Docker, live PostgreSQL, Gemini, and browser/container interaction remain
   environment-dependent here. CI now provisions PostgreSQL and smoke-tests Compose;
   the current workspace cannot execute those jobs locally.
4. The scanner subprocess is not a kernel sandbox. Host/container isolation and
   least-privilege deployment remain necessary for untrusted source analysis.

Tests use app-owned subprocess fixtures only. Uploaded source is never executed.
The subprocess environment is isolation hygiene, not an OS sandbox. Prompt text is
not an enforceable injection defense; absence of tools and output-as-text are the
enforceable boundaries.
