# Security

## Trust boundaries

Uploaded Python is untrusted data. The API validates the filename and size, writes it under a generated UUID filename, and passes it to Bandit as one subprocess argument. The source is never imported, evaluated, or executed.

Bandit output is treated as untrusted scanner data. Its JSON shape and finding fields are validated before persistence, and generated temporary paths are reduced to basenames before storage. Scanner failures transition the scan to `failed` without exposing subprocess or filesystem details to the client.

## Secrets

Database credentials and runtime settings are supplied through environment variables. `.env` is not part of the image build context. Use `.env.example` only as a template and replace its local placeholder password.

## API and database

The current MVP does not provide user authentication or authorization; it is intended for a trusted local developer environment. Do not expose the service directly to the public internet. Database errors are logged server-side and returned to health clients only as an unavailable status.

## LLM status

There is no live LLM integration in the current MVP. This avoids sending source code to an external provider without an explicit trust and configuration boundary. Any future provider integration must validate structured output, apply timeouts, avoid logging source or credentials, and keep remediation behind developer review.

## Known limitations

- Authentication, authorization, rate limiting, and multi-tenant isolation are not implemented.
- Scans run synchronously in the API process.
- Bandit is the only scanner.
- Docker image dependency installation uses the manifests available in this repository; lockfiles should be added before production deployment.
