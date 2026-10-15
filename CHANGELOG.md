# Changelog

## Unreleased

- Added conservative CWE/OWASP classification and remediation guidance for known Bandit rules.
- Added a provider-independent structured security-analysis service with a deterministic local mock provider.
- Added persisted analysis records and finding analysis API endpoints.
- Added frontend controls for requesting and reviewing AI analysis.
- Hardened health responses so database internals are not exposed.
- Validated Bandit JSON envelopes and finding field shapes before persistence.
- Added a findings dashboard with severity filtering and source snippets.
- Added Docker Compose orchestration for PostgreSQL, FastAPI, and Next.js.
- Added local security, API, and development documentation.
- Prevented scanner-controlled paths from crossing the single-upload API boundary.
- Scoped frontend analysis errors to the finding that was analyzed.
- Rejected empty uploads and malformed required Bandit finding fields.
- Added a clear empty-filter state to the findings dashboard.
- Added explicit health-check and findings-load retry controls for transient API failures.
