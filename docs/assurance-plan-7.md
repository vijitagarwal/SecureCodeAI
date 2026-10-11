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

## Actionable review queue

1. Upload cleanup ownership after exclusive-create failure; request cancellation and
   real worker capacity; strict framing and authentication regression coverage.
2. Polling scanner output permits disk growth between polls; process-tree cleanup
   and actual timeout/output tests need evidence.
3. Gemini timeout is not a hard deadline; automatic decompression precedes the
   application size check. Provider outages lack an explicit local fallback.
4. Exports load up to 5,000 findings and analyses at once; finding-count limits alone
   allow very large JSON allocations. Check consistent export/delete behavior.
5. Lock held over provider I/O; interrupted scans can stay running forever. Provide
   bounded database waits and safe operator recovery without guessing active work.
6. API.md and operational docs are stale. CI lacks container startup and Python
   dependency audits. Browser/live service verification remains an explicit gap.

Tests use app-owned subprocess fixtures only. Uploaded source is never executed.
The subprocess environment is isolation hygiene, not an OS sandbox. Prompt text is
not an enforceable injection defense; absence of tools and output-as-text are the
enforceable boundaries.
