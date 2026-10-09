from app.db.models import FindingConfidence, FindingSeverity
from app.llm.mock import MockSecurityProvider
from app.schemas.analysis import AnalysisStatus
from app.services.analysis_service import analyze_finding
from test_persistence import db_session


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
    assert analysis.confidence == 0.7
