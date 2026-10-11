# SecureCode AI threat model

## Scope and assumptions

This model covers the local single-operator deployment in Compose or a directly
started FastAPI/Next.js process. The workspace bearer key is a shared secret: every
holder can read, analyze, export, and delete every scan. There is no multi-user
identity, tenant isolation, distributed rate limiter, or claim that Bandit is an
OS sandbox. The operator must protect the key and bind public exposure behind an
appropriate reverse proxy and network policy.

## Assets and boundaries

| Asset / boundary | Threat | Current mitigation | Residual risk |
|---|---|---|---|
| Workspace key | Browser, log, URL, or error leakage | Memory-only frontend state, Authorization header, `SecretStr`, constant-time comparison, no key in responses/URLs | Shared-key rotation and revocation require server configuration and process restart |
| Uploaded Python | Import, execution, traversal, source exposure | Extension/name validation, bounded body/file, generated 0600 path, no import/eval, text-only rendering, cleanup | Bandit subprocess is not a kernel sandbox; host/container hardening remains necessary |
| Scanner process | Shell injection, child escape, hangs, output flood | Argument list with `shell=False`, no stdin, reduced env, approved target root, output/timeout/finding limits, process-group kill on POSIX | Windows descendant termination is limited to direct child; container/OS policy is deployment responsibility |
| API capacity | Memory, CPU, process, disk exhaustion | Pre-parser body bound, upload/scan/analysis semaphores, worker timeout, output and report limits, pagination | Limits are per worker and do not provide distributed fairness or long-term retention |
| Findings/database | Tampering, partial state, orphan records | SQLAlchemy transactions, constraints, FK cascade, unique analysis record, migrations, generic database errors | Shared workspace has no per-record ownership boundary; live PostgreSQL is CI/environment dependent |
| Gemini boundary | Prompt injection, secret disclosure, malicious output, provider outage | Finding-only context, instruction boundary, fixed HTTPS origin, no redirects/retries, size/time/schema validation, fallback provenance, text-only advisory output | Remote provider receives source snippets when explicitly enabled; no live provider test is run without credentials |
| Reports/deletion | Unauthorized export, oversized response, incomplete delete | Same auth boundary, bounded export, no raw scanner metadata, active-delete conflict, cascade delete | Deleting database records cannot erase backups or previously downloaded reports |
| Containers | Privilege escalation, exposed services, writable filesystem | Non-root images, dropped capabilities, no-new-privileges, read-only app containers, tmpfs scratch, loopback local ports | Image base tags are not digest-pinned; Docker runtime and host kernel are outside application control |

## Entry points and regression evidence

- `/api/health` and `/api/live` are public operational probes; all workspace routes
  require the bearer key before multipart parsing.
- Multipart requests are tested for missing/malformed/duplicate framing, chunked
  overflow, path-like names, cleanup, and exclusive-file collisions.
- Bandit tests cover real findings, invalid syntax, `nosec` suppression, malformed
  JSON, invalid fields, timeout, output flood, non-UTF-8 output, secret environment
  filtering, approved roots, and cleanup.
- Analysis tests cover strict output validation, unsafe diff paths, provider errors,
  saved idempotence, remote fallback provenance, and mocked Gemini HTTP failures.
- Workflow tests cover unauthenticated sensitive routes, failed scans, export,
  deletion cascade, pagination, and severity filtering.

These are application regression tests, not a penetration test or a guarantee of
security against a compromised host, kernel, container runtime, database, browser,
or remote provider.
