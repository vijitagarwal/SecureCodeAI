from app.db.models import FindingConfidence, FindingSeverity
from app.llm.mock import MockSecurityProvider
from app.schemas.analysis import AnalysisStatus
from app.services.analysis_service import analyze_finding
from test_persistence import db_session
from app.llm.base import ProviderError
from app.schemas.analysis import AnalysisContent
import pytest


def test_mock_provider_returns_structured_security_analysis(db_session):
    from app.db.repositories.scan_repository import create_scan

    scan = create_scan(db_session, "example.py")
    db_session.commit()
    from app.db.repositories.finding_repository import create_finding

    finding = create_finding(
        db_session,
        scan_id=scan.id,
        tool="test-scanner",
        rule_id="B602",
        title="Command execution",
        description="subprocess call with shell=True",
        severity=FindingSeverity.HIGH,
        confidence=FindingConfidence.MEDIUM,
        file_path="example.py",
        line_number=1,
        code_snippet="subprocess.run(value, shell=True)",
        raw_metadata={},
    )
    db_session.commit()

    analysis = analyze_finding(db_session, finding, MockSecurityProvider())

    assert analysis.finding_id == finding.id
    assert analysis.status == AnalysisStatus.COMPLETED
    assert "CWE" not in analysis.security_impact
    assert analysis.provider == "mock"
    assert analysis.confidence == 0.0


def test_saved_analysis_is_idempotent_and_generates_review_diff(db_session):
    from app.db.repositories.scan_repository import create_scan
    from app.db.repositories.finding_repository import create_finding
    from test_persistence import finding_values

    scan = create_scan(db_session, "sample.py")
    finding = create_finding(db_session, **{**finding_values(scan.id, FindingSeverity.MEDIUM), "code_snippet": "1 eval(data)\n"})
    db_session.commit()

    class Provider(MockSecurityProvider):
        calls = 0
        name = "gemini"
        model = "test-model"

        def analyze(self, **kwargs):
            self.calls += 1
            return super().analyze(**kwargs).model_copy(update={"fixed_code": "value = json.loads(data)"})

    provider = Provider()
    first = analyze_finding(db_session, finding, provider)
    second = analyze_finding(db_session, finding, provider)
    assert first.id == second.id
    assert provider.calls == 1
    assert first.provider == "gemini" and first.model == "test-model"
    assert "--- a/snippet.py" in first.diff
    assert "-eval(data)" in first.diff
    assert "+value = json.loads(data)" in first.diff


def test_invalid_constructed_model_cannot_be_persisted(db_session):
    from app.db.repositories.scan_repository import create_scan
    from app.db.repositories.finding_repository import create_finding
    from app.db.models import SecurityAnalysis
    from test_persistence import finding_values
    scan = create_scan(db_session, "sample.py")
    finding = create_finding(db_session, **finding_values(scan.id, FindingSeverity.MEDIUM))
    db_session.commit()

    class Provider(MockSecurityProvider):
        def analyze(self, **kwargs):
            return AnalysisContent.model_construct(confidence=float("nan"))

    with pytest.raises(ProviderError):
        analyze_finding(db_session, finding, Provider())
    assert db_session.query(SecurityAnalysis).count() == 0
