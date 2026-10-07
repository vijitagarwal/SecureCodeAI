# API

## Health

`GET /api/health` returns backend and database readiness:

```json
{
  "status": "ok",
  "backend": {"status": "ok"},
  "database": {"status": "ok"}
}
```

Database failures return `200` with `"status": "degraded"` and `"database": {"status": "unavailable"}`. Internal connection details are not returned.

## Upload and scan

`POST /api/scans` accepts a multipart `file` containing a `.py` file. Files are limited by `MAX_UPLOAD_SIZE_BYTES` and scanned synchronously. The response contains `scan_id`, `status`, `filename`, and `total_findings`.

`GET /api/scans/{scan_id}` returns scan status and severity counts.

`GET /api/scans/{scan_id}/findings` returns normalized Bandit findings with rule, severity, confidence, file, line, description, and source snippet fields. Optional `offset` (default `0`) and `limit` (default `100`, maximum `100`) query parameters bound response size.

Unsupported extensions return `415`; invalid names or missing files return `400`; oversized files return `413`; unknown scan IDs return `404`.
