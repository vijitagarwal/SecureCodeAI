# API

## Health

`GET /api/health` is the unauthenticated readiness probe. It checks that the API
process is responding and that the configured database schema can be queried:

```json
{
  "status": "ok",
  "backend": {"status": "ok"},
  "database": {"status": "ok"}
}
```

Database failures return `503` with `"status": "degraded"` and
`"database": {"status": "unavailable"}`. Internal connection details are not
returned. The response includes `Cache-Control: no-store` and is not a workspace
data endpoint.

## Authentication

All endpoints except `/api/health` and CORS `OPTIONS` requests require:

```text
Authorization: Bearer <API_KEY>
```

The server fails closed when `API_KEY` is absent or shorter than 32 characters.
This is single-workspace shared-key access, not multi-user identity or tenant
authorization. Integer scan and finding IDs are therefore not ownership controls.

## Upload and scan

`POST /api/scans` accepts a multipart `file` containing a `.py` file. Files are
limited by `MAX_UPLOAD_SIZE_BYTES` and scanned synchronously from the caller's
perspective. Blocking upload, database, and Bandit work runs in a worker with an
independent SQLAlchemy session. The response contains `scan_id`, `status`,
`filename`, `total_findings`, and an optional safe `failure_reason`.

`GET /api/scans/{scan_id}` returns scan status and severity counts.

`GET /api/scans/{scan_id}/findings` returns normalized Bandit findings with rule, severity, confidence, file, line, description, and source snippet fields. Optional `offset` (default `0`) and `limit` (default `100`, maximum `100`) query parameters bound response size.

Findings also include conservative `cwe_id`, `cwe_name`, `owasp_category`,
`remediation_category`, `remediation_guidance`, and `analysis_available` fields.
Unknown scanner rules remain unmapped and are marked for manual review. Responses
are capped at 100 findings per request and use stable ID ordering.

`POST /api/findings/{finding_id}/analysis` runs the configured local or explicitly
configured Gemini structured analysis provider and stores the result. Repeated
requests return the saved result without regenerating it. `GET
/api/findings/{finding_id}/analysis` retrieves the stored analysis. A missing
finding returns `404`; provider or persistence failures return a generic `503`
response. Provider/model provenance is included in saved analysis.

## Reports and deletion

`GET /api/scans/{scan_id}/report` exports a completed or failed scan as JSON. It
includes normalized findings and saved analysis, never raw Bandit metadata,
credentials, environment settings, or server filesystem paths. The report is
bounded by `MAX_FINDINGS`; active scans return `409`.

`DELETE /api/scans/{scan_id}` deletes a completed or failed scan and cascades to
findings and saved analyses. Active scans return `409`. Temporary upload files are
removed after scan success, failure, timeout, and persistence exceptions.

Unsupported extensions return `415`; invalid names or missing files return `400`; oversized files return `413`; unknown scan IDs return `404`.
