from dataclasses import dataclass


@dataclass(frozen=True)
class Classification:
    cwe_id: str | None
    cwe_name: str | None
    owasp_category: str | None
    remediation_category: str
    remediation_guidance: str


_MAPPINGS: dict[str, Classification] = {
    "B105": Classification(
        "CWE-259", "Use of Hard-coded Password", "A07: Identification and Authentication Failures",
        "secret-management", "Store secrets in a managed secret store or environment-backed configuration.",
    ),
    "B307": Classification(
        "CWE-94", "Improper Control of Generation of Code ('Code Injection')",
        "A03: Injection", "safe-evaluation", "Replace eval with an explicit parser or a constrained data format.",
    ),
    "B311": Classification(
        "CWE-330", "Use of Insufficiently Random Values",
        "A02: Cryptographic Failures", "cryptography", "Use the secrets module for security-sensitive randomness.",
    ),
    "B303": Classification(
        "CWE-327", "Use of a Broken or Risky Cryptographic Algorithm",
        "A02: Cryptographic Failures", "cryptography", "Use a modern, approved cryptographic algorithm and key size.",
    ),
    "B506": Classification(
        "CWE-20", "Improper Input Validation", "A08: Software and Data Integrity Failures",
        "safe-deserialization", "Use `yaml.safe_load` with strict schema validation for untrusted YAML.",
    ),
    "B602": Classification(
        "CWE-78", "Improper Neutralization of Special Elements used in an OS Command",
        "A03: Injection", "command-injection", "Avoid shell commands or pass a fixed argument list with shell execution disabled.",
    ),
}


def classify_rule(rule_id: str) -> Classification:
    return _MAPPINGS.get(
        rule_id,
        Classification(
            None, None, None, "manual-review",
            "Review the scanner rule and constrain untrusted inputs according to the rule's documentation.",
        ),
    )
