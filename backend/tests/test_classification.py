from app.security.classification import classify_rule


def test_known_bandit_rules_have_conservative_security_mappings():
    expectations = {
        "B105": ("CWE-259", "A07: Identification and Authentication Failures", "secret-management"),
        "B307": ("CWE-94", "A03: Injection", "safe-evaluation"),
        "B311": ("CWE-330", "A02: Cryptographic Failures", "cryptography"),
        "B303": ("CWE-327", "A02: Cryptographic Failures", "cryptography"),
        "B506": ("CWE-502", "A08: Software and Data Integrity Failures", "safe-deserialization"),
        "B602": ("CWE-78", "A03: Injection", "command-injection"),
    }

    for rule_id, (cwe_id, owasp_category, remediation_category) in expectations.items():
        classification = classify_rule(rule_id)
        assert classification.cwe_id == cwe_id
        assert classification.owasp_category == owasp_category
        assert classification.remediation_category == remediation_category


def test_unknown_rule_requires_manual_review_without_fabricated_mapping():
    classification = classify_rule("B999")

    assert classification.cwe_id is None
    assert classification.owasp_category is None
    assert classification.remediation_category == "manual-review"
