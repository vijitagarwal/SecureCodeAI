# SecureCode AI — Copilot Agent Build Plan

## 0. Mission

Build **SecureCode AI**, a portfolio-grade AI-assisted source-code security analysis platform.

The product should eventually allow a developer to:

1. Upload source code or connect a Git repository.
2. Run deterministic security scanners.
3. Normalize and store findings.
4. Use an LLM to explain findings in context.
5. Generate remediation guidance.
6. Track scans and findings over time.
7. Later add RAG over security knowledge and CI/CD integration.

**Current objective:** Build a small but complete vertical slice first. It must work locally before adding advanced features.

Do not attempt to build the entire roadmap in one pass.

---

# 1. Non-negotiable engineering principles

## 1.1 Build incrementally

Implement one milestone at a time.

After each milestone:

- run the application
- run tests
- fix errors
- verify the feature manually
- only then continue

Do not generate a huge codebase without validating it.

## 1.2 Prefer a modular monolith

Use one frontend and one backend.

Do NOT create microservices.

Do NOT introduce Kubernetes.

Do NOT introduce Redis unless a later milestone explicitly requires it.

Do NOT create unnecessary abstraction layers.

## 1.3 Security first

This is a cybersecurity project.

Never execute uploaded source code.

Uploaded files must be treated as untrusted input.

Never expose API keys to the frontend.

Never commit secrets.

Validate file types and file sizes.

Use subprocess execution carefully for security scanners.

Prefer read-only operations.

## 1.4 Deterministic detection before AI

The LLM must NOT be treated as the primary source of truth for vulnerability detection.

The architecture is:

Static analysis
→ normalized findings
→ contextual AI explanation
→ remediation guidance

AI augments security tooling; it does not replace it.

## 1.5 Do not fake functionality

Do not implement fake scanner results.

Do not hardcode sample findings into production code.

Do not create fake AI responses.

If an external service is unavailable, fail clearly with a useful error message.

---

# 2. Technology stack

## Frontend

- Next.js
- TypeScript
- Tailwind CSS
- React

## Backend

- Python
- FastAPI
- Pydantic

## Security analysis

Start with:

- Bandit for Python SAST
- Gitleaks for secret detection, if available

If Gitleaks is difficult to install cross-platform during the first milestone, implement Bandit first and make Gitleaks a later milestone.

## AI

Use an LLM API through a backend-only provider abstraction.

The API key must exist only in backend environment variables.

## Database

For the first version, use:

- PostgreSQL
- SQLAlchemy
- Alembic

Do not add pgvector yet. It belongs to the later RAG milestone.

## Development

- Git
- Docker Compose for PostgreSQL
- pytest
- ESLint
- TypeScript checks

---

# 3. Target architecture

Use this structure as the target. Adjust only when there is a strong engineering reason.

```text
securecode-ai/
│
├── README.md
├── .gitignore
├── .env.example
├── docker-compose.yml
│
├── backend/
│   ├── requirements.txt
│   ├── alembic.ini
│   │
│   ├── app/
│   │   ├── main.py
│   │   │
│   │   ├── api/
│   │   │   └── routes/
│   │   │       ├── health.py
│   │   │       ├── scans.py
│   │   │       └── findings.py
│   │   │
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── logging.py
│   │   │
│   │   ├── db/
│   │   │   ├── database.py
│   │   │   ├── models.py
│   │   │   └── repositories/
│   │   │
│   │   ├── schemas/
│   │   │   ├── scan.py
│   │   │   └── finding.py
│   │   │
│   │   ├── services/
│   │   │   ├── scanner_service.py
│   │   │   ├── finding_service.py
│   │   │   └── ai_service.py
│   │   │
│   │   ├── scanners/
│   │   │   ├── base.py
│   │   │   ├── bandit.py
│   │   │   └── gitleaks.py
│   │   │
│   │   └── providers/
│   │       ├── llm/
│   │       │   └── base.py
│   │       └── embeddings/
│   │           └── base.py
│   │
│   ├── tests/
│   │   ├── test_health.py
│   │   ├── test_scanner.py
│   │   └── test_findings.py
│   │
│   └── alembic/
│
├── frontend/
│   ├── package.json
│   ├── next.config.ts
│   ├── tsconfig.json
│   └── src/
│       ├── app/
│       │   ├── page.tsx
│       │   ├── scans/
│       │   └── findings/
│       │
│       ├── components/
│       │   ├── FileUpload.tsx
│       │   ├── ScanSummary.tsx
│       │   ├── FindingCard.tsx
│       │   └── SeverityBadge.tsx
│       │
│       └── lib/
│           └── api.ts
│
└── docs/
    ├── architecture.md
    ├── threat-model.md
    └── roadmap.md
```

Do not create every file immediately. Create files when their milestone requires them.

---

# 4. Domain model

The core concepts are:

## Scan

Represents one security analysis execution.

Fields:

- id
- filename/project name
- status
- scanner names
- started_at
- completed_at
- total_findings
- critical_count
- high_count
- medium_count
- low_count

Possible statuses:

- queued
- running
- completed
- failed

## Finding

Represents one normalized security finding.

Fields:

- id
- scan_id
- tool
- rule_id
- title
- description
- severity
- confidence
- file_path
- line_number
- code_snippet
- raw_metadata
- created_at

Severity:

- CRITICAL
- HIGH
- MEDIUM
- LOW
- INFO

## AI Analysis

Later, associate AI analysis with a finding.

Fields:

- finding_id
- explanation
- impact
- remediation
- confidence
- model
- created_at

---

# 5. Milestone 1 — Repository and infrastructure

## Goal

Create a clean monorepo with:

- backend
- frontend
- PostgreSQL
- documentation

Tasks:

1. Initialize Git.
2. Create `.gitignore`.
3. Create `.env.example`.
4. Create Docker Compose PostgreSQL service.
5. Create FastAPI application.
6. Create Next.js application.
7. Add health endpoint.
8. Add frontend page showing backend/database health.
9. Add README with setup instructions.

Expected result:

```text
Browser
   ↓
Next.js
   ↓
FastAPI
   ↓
PostgreSQL
```

## Verification

Run:

```bash
docker compose up -d
```

Backend:

```bash
uvicorn app.main:app --reload
```

Frontend:

```bash
npm run dev
```

Verify the health endpoint works.

Do not continue until this works.

---

# 6. Milestone 2 — Database

## Goal

Implement Scan and Finding persistence.

Tasks:

1. Configure SQLAlchemy.
2. Configure Alembic.
3. Create Scan model.
4. Create Finding model.
5. Create migration.
6. Apply migration.
7. Create repository functions.
8. Add tests.

The backend must be able to:

- create a scan
- update scan status
- create findings
- retrieve findings
- retrieve scan summary

Do not expose raw SQL throughout route handlers.

Use repository/service separation.

---

# 7. Milestone 3 — File upload

## Goal

Allow users to upload Python source files.

For v0.1:

- accept `.py`
- reject unsupported extensions
- enforce a reasonable file-size limit
- never execute uploaded Python
- store the file temporarily for scanning
- delete temporary files after the scan

API:

```text
POST /api/scans
```

Multipart form upload.

Response should contain:

```json
{
  "scan_id": "...",
  "status": "queued"
}
```

For the first implementation, scanning may happen synchronously if the file is small.

Do not introduce a background queue yet.

---

# 8. Milestone 4 — Bandit integration

## Goal

Run Bandit against uploaded Python source.

Use Bandit's machine-readable JSON output.

Never parse human-readable terminal output if structured JSON is available.

Create a scanner interface:

```python
class SecurityScanner(ABC):
    @abstractmethod
    def scan(self, target_path: str) -> ScannerResult:
        ...
```

Bandit implementation:

```text
Bandit
  ↓
JSON
  ↓
Bandit parser
  ↓
Normalized Finding
```

The scanner service should not know Bandit's internal JSON structure.

Create a dedicated parser.

---

# 9. Finding normalization

Different scanners will produce different output formats.

Normalize them into the application's Finding schema.

Example normalized object:

```json
{
  "tool": "bandit",
  "rule_id": "B105",
  "title": "Hardcoded password string",
  "severity": "LOW",
  "confidence": "MEDIUM",
  "file_path": "example.py",
  "line_number": 23,
  "code_snippet": "password = 'secret'",
  "description": "Possible hardcoded password."
}
```

Do not invent severity mappings without documenting them.

Preserve the original scanner metadata in `raw_metadata`.

This will allow additional scanners later.

---

# 10. Milestone 5 — Findings dashboard

Build the first useful frontend.

Home page should allow:

```text
Upload Python file
      ↓
Scan
      ↓
Results
```

Results page:

```text
Security Scan
────────────────────────────

Total findings: 7

Critical    0
High        2
Medium      3
Low         2

────────────────────────────

HIGH
Hardcoded credential
app/config.py:42

MEDIUM
Weak cryptographic algorithm
auth.py:78

LOW
...
```

Implement:

- severity badges
- finding cards
- file path
- line number
- scanner
- rule ID
- description
- code snippet
- filtering by severity

Do not spend excessive time on visual polish.

Functional > fancy.

---

# 11. Milestone 6 — Finding detail view

Clicking a finding should show:

```text
Finding
────────────────────

Title

Severity
Confidence

File
Line

Rule

Description

Code

[Analyze with AI]
```

API:

```text
GET /api/findings/{finding_id}
```

This becomes the entry point for the AI layer.

---

# 12. Milestone 7 — AI explanation

## Goal

Use an LLM to explain an existing security finding.

Do NOT ask the model to scan the entire repository.

Give it:

- finding title
- rule ID
- severity
- scanner description
- relevant source code
- a small amount of surrounding context

Prompt concept:

```text
You are a senior application security engineer.

Analyze the provided security finding.

Return structured JSON containing:

1. explanation
2. security_impact
3. why_the_code_is_risky
4. remediation
5. safer_code_example
6. confidence

Do not invent facts.
Do not claim that a vulnerability is exploitable unless the provided
evidence supports that conclusion.
Clearly distinguish scanner evidence from your own analysis.
```

Use structured output/Pydantic validation where supported.

The frontend should display:

```text
AI Security Analysis

Why this matters
...

Potential impact
...

Recommended remediation
...

Safer example
...
```

---

# 13. LLM provider abstraction

Do not hardcode the AI SDK into business logic.

Create:

```python
class LLMProvider(ABC):
    @abstractmethod
    def analyze_finding(...):
        ...
```

Then implement one concrete provider.

Environment variables:

```text
OPENAI_API_KEY=
OPENAI_MODEL=
```

Never expose these to Next.js.

Never prefix secret backend variables with `NEXT_PUBLIC_`.

---

# 14. Milestone 8 — Security hardening

Because this is a cybersecurity portfolio project, document and implement the threat model.

Threats to consider:

## Malicious source files

Attack:

- oversized file
- path traversal
- malicious filename
- binary disguised as source
- resource exhaustion

Mitigations:

- file-size limits
- extension/content validation
- generated temporary filenames
- safe temporary directory
- cleanup

## Command injection

Never construct scanner commands using shell string concatenation.

Prefer:

```python
subprocess.run(
    ["bandit", "-f", "json", target_path],
    shell=False,
    ...
)
```

Validate paths.

## LLM prompt injection

Source code is untrusted data.

Clearly delimit source code in prompts.

Tell the model that source code is data and must not override system instructions.

## Secret leakage

Never send unrelated source code to the LLM.

Only send the minimal context necessary.

Never send environment variables.

Never include API keys in prompts.

## API abuse

Later add:

- authentication
- rate limiting
- scan quotas

These are not required for v0.1.

---

# 15. Milestone 9 — Testing

Minimum tests:

## Backend

- health endpoint
- upload validation
- unsupported file rejection
- scanner execution
- Bandit parser
- finding normalization
- database persistence
- API error handling

## Frontend

At minimum:

- upload flow
- results rendering
- severity filtering

## Security tests

Test:

- oversized upload
- malicious filename
- unsupported extension
- path traversal attempt
- malformed scanner output
- scanner timeout
- LLM provider failure

The application should fail safely.

---

# 16. Milestone 10 — RAG security knowledge base

This is a FUTURE milestone.

Do not implement during the initial build.

Eventually add:

```text
OWASP
CWE
CVE information
Security documentation
Project-specific security notes
        ↓
Document ingestion
        ↓
Chunking
        ↓
Embeddings
        ↓
pgvector
        ↓
Retrieval
        ↓
AI explanation
```

Then the AI can say:

```text
Relevant security knowledge:

CWE-798
OWASP guidance
...
```

and cite the retrieved sources.

This is where the project begins connecting with the NEXUS architecture.

---

# 17. Milestone 11 — Git repository scanning

Future.

Allow:

```text
GitHub URL
     ↓
Validate URL
     ↓
Clone into isolated temporary directory
     ↓
Detect supported languages
     ↓
Run scanners
     ↓
Normalize findings
     ↓
Store results
```

Do not execute repository code.

Do not run arbitrary build scripts.

Do not run package installation scripts.

Initially support only:

- Python
- JavaScript/TypeScript

Add additional languages later.

---

# 18. Milestone 12 — Additional security tools

Future scanners:

- Gitleaks — secrets
- Semgrep — SAST
- Trivy — dependency/container scanning
- Bandit — Python

Architecture should allow:

```text
ScannerRegistry

Bandit
Gitleaks
Semgrep
Trivy
...
```

without rewriting the scan service.

---

# 19. Milestone 13 — AI remediation

Future.

Given a finding:

```text
Vulnerability
+
Relevant source
+
Security guidance
```

generate:

```text
Explanation
+
Suggested patch
+
Before/after code
+
Reasoning
```

Never automatically modify repositories in the first implementation.

Eventually support human approval.

---

# 20. Milestone 14 — CI/CD

Future.

Add GitHub Actions:

```text
Developer pushes code
        ↓
GitHub Actions
        ↓
SecureCode AI
        ↓
Scan
        ↓
Findings
        ↓
Fail build if policy threshold exceeded
```

Example:

```text
CRITICAL > 0 → fail
HIGH > 3     → fail
```

Make policies configurable.

---

# 21. Milestone 15 — Security analytics

Future dashboard:

```text
Repositories
Scans
Findings
Severity trends
Most common vulnerabilities
Fixed vs unresolved
Scanner coverage
```

This turns the project into a real developer security platform.

---

# 22. Milestone 16 — Portfolio-grade documentation

Create:

## README.md

Include:

- project overview
- screenshots
- architecture
- technology stack
- setup
- example scan
- AI workflow
- security considerations
- limitations
- roadmap

## docs/architecture.md

Explain:

```text
Frontend
    ↓
FastAPI
    ↓
Scan Service
    ↓
Scanner Adapters
    ↓
Finding Normalizer
    ↓
PostgreSQL
    ↓
AI Analysis
```

## docs/threat-model.md

Include:

- assets
- trust boundaries
- threats
- attack scenarios
- mitigations
- residual risks

## docs/roadmap.md

Clearly distinguish:

- completed
- in progress
- planned

---

# 23. Definition of Done for v0.1

Do NOT call v0.1 complete until all of these work:

- [ ] PostgreSQL starts through Docker Compose
- [ ] FastAPI starts
- [ ] Next.js starts
- [ ] Health endpoint works
- [ ] Database migrations work
- [ ] User can upload a Python file
- [ ] Invalid files are rejected
- [ ] Bandit actually scans the file
- [ ] Bandit output is parsed
- [ ] Findings are normalized
- [ ] Findings are stored in PostgreSQL
- [ ] Results are displayed in the UI
- [ ] Findings can be filtered
- [ ] Finding detail page works
- [ ] Automated tests pass
- [ ] README contains setup instructions
- [ ] No secrets are committed
- [ ] Uploaded code is never executed
- [ ] Scanner subprocess uses safe argument handling

AI analysis can be v0.2 if time is limited.

A working deterministic scanner is more valuable than a broken AI layer.

---

# 24. Copilot Agent operating instructions

You are the implementation agent.

Follow this document as the source of truth.

Before making major architectural decisions:

1. Inspect the existing repository.
2. Determine which milestone is currently complete.
3. Read relevant existing code.
4. Avoid rewriting working code unnecessarily.

For each milestone:

1. Explain briefly what you are about to implement.
2. Implement it.
3. Run relevant tests.
4. Start required services when possible.
5. Fix errors.
6. Verify the feature.
7. Summarize what changed.
8. Identify the next milestone.

Do not skip verification.

If a dependency is unavailable:

- do not silently replace the architecture
- choose the smallest compatible alternative
- document the decision

If requirements conflict, prioritize:

1. Security
2. Working functionality
3. Maintainability
4. Simplicity
5. Visual polish

Do not implement future milestones early.

---

# 25. Immediate task

Start with **Milestone 1 only**.

Do not implement the scanner, AI, RAG, GitHub integration, authentication, or agents yet.

First inspect the repository.

Then:

1. create the project structure
2. initialize backend
3. initialize frontend
4. create PostgreSQL Docker Compose configuration
5. create FastAPI health endpoint
6. create frontend health page
7. create `.env.example`
8. create README
9. run everything
10. fix any errors
11. run tests

After Milestone 1 is verified, stop and report the result before proceeding to Milestone 2.

---

# 26. Long-term vision

The final system may eventually become:

```text
                         SECURECODE AI
                               │
              ┌────────────────┼────────────────┐
              │                │                │
          Static Analysis     AI             Platform
              │                │                │
       ┌──────┼──────┐    ┌────┼─────┐    ┌────┼────┐
       │      │      │    │    │     │    │    │    │
     SAST  Secrets   SCA  RAG  LLM  ML  Auth Reports CI/CD

                               │
                               ▼
                            NEXUS
                               │
                     Personal AI Knowledge
                               │
                 Memory + Retrieval + Agents
```

The project must therefore be designed so that the security-analysis engine can eventually become a reusable tool inside a larger personal AI system.

But **do not build NEXUS now**.

Build SecureCode AI one verified milestone at a time.
