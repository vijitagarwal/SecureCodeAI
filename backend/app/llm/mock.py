from app.llm.base import LLMProvider
from app.schemas.analysis import AnalysisContent
from app.security.classification import Classification


class MockSecurityProvider(LLMProvider):
    def analyze(self, *, rule_id: str, title: str, description: str, snippet: str | None,
                classification: Classification, severity: str = "UNKNOWN", confidence: str = "UNKNOWN") -> AnalysisContent:
        return AnalysisContent(
            finding_summary=title,
            root_cause=description,
            security_impact=f"The {rule_id} pattern may allow an attacker to compromise confidentiality, integrity, or availability.",
            false_positive_assessment="Static analysis is a signal; verify the data flow and execution context during review.",
            remediation=classification.remediation_guidance,
            fixed_code=None,
            diff=None,
            confidence=0.0,
        )
