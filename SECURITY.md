# Security

## Trust boundaries

Uploaded Python is untrusted data. The API validates the filename and size, writes it under a generated UUID filename, and passes it to Bandit as one subprocess argument. The source is never imported, evaluated, or executed.

Bandit output is treated as untrusted scanner data. Its JSON shape and finding fields are validated before persistence, and generated temporary paths are reduced to basenames before storage. Scanner failures transition the scan to `failed` without exposing subprocess or filesystem details to the client.

## Secrets

Database credentials and runtime settings are supplied through environment variables. `.env` is not part of the image build context. Use `.env.example` only as a template and replace its local placeholder password.

## API and database

The workspace uses a server-configured bearer API key. Protected API routes fail
closed when `API_KEY` is absent and compare credentials in constant time. The key
is not persisted by the frontend, and database errors are returned only as generic
messages. This is single-operator workspace access rather than a multi-user
identity system; do not expose it directly to the public internet without adding
tenant-aware authentication, authorization, and an external rate limiter.

## LLM status and trust boundary

The default analysis endpoint uses a deterministic local mock provider. It receives
only the rule, finding text, snippet, and classification; it does not receive
credentials, environment variables, or server filesystem paths. Provider output is
validated with bounded schemas before persistence. The configured Gemini provider
also has a wall-clock response timer, decompressed response-size limit, no
redirects/retries, and generic failure handling. When it fails, the API may save
deterministic local fallback guidance under explicit `mock-fallback` provenance;
the UI does not represent that result as Gemini output.

AI analysis is separate from the static scanner result. It cannot change scanner severity or silently overwrite source. Proposed code and diffs are stored as review material only and are never executed or automatically applied.

## Known limitations

- Multi-user authentication, per-user authorization, and distributed rate limiting are not implemented.
- Scans run synchronously from the caller's perspective, with blocking work isolated from the async event loop.
- Bandit is the only scanner.
- Capacity controls are per application worker; deploy behind an appropriate reverse proxy for shared or public environments.
