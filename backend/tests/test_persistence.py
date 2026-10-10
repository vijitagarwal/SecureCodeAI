import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import Base
from app.db.models import FindingConfidence, FindingSeverity, ScanStatus
from app.db.repositories.finding_repository import (
    count_findings_by_severity,
    create_finding,
    create_findings,
    get_finding,
    get_findings_for_scan,
)
from app.db.repositories.scan_repository import (
    create_scan,
    delete_scan,
    get_scan,
    update_scan_counts,
    update_scan_status,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, connection_record):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    with session_factory() as session:
        yield session
    Base.metadata.drop_all(engine)


def finding_values(scan_id: int, severity: FindingSeverity, rule_id: str = "TEST-001") -> dict:
    return {
        "scan_id": scan_id,
        "tool": "test-scanner",
        "rule_id": rule_id,
        "title": "Test finding",
        "description": "A finding created by a persistence test.",
        "severity": severity,
        "confidence": FindingConfidence.MEDIUM,
        "file_path": "example.py",
        "line_number": 10,
        "code_snippet": "value = input()",
        "raw_metadata": {"source": "test"},
    }


def test_scan_create_retrieve_status_and_counts(db_session: Session):
    scan = create_scan(db_session, "example.py", ["bandit"])
    db_session.commit()

    retrieved = get_scan(db_session, scan.id)
    assert retrieved is not None
    assert retrieved.name == "example.py"
    assert retrieved.status == ScanStatus.QUEUED
    assert retrieved.scanner_names == ["bandit"]

    update_scan_status(db_session, retrieved, ScanStatus.RUNNING)
    assert retrieved.started_at is not None
    update_scan_status(db_session, retrieved, ScanStatus.COMPLETED)
    assert retrieved.completed_at is not None
    update_scan_counts(
        db_session,
        retrieved,
        {
            FindingSeverity.CRITICAL: 1,
            FindingSeverity.HIGH: 2,
            FindingSeverity.MEDIUM: 3,
            FindingSeverity.LOW: 4,
            FindingSeverity.INFO: 5,
        },
    )
    db_session.commit()

    assert retrieved.status == ScanStatus.COMPLETED
    assert retrieved.total_findings == 15
    assert retrieved.critical_count == 1
    assert retrieved.high_count == 2
    assert retrieved.medium_count == 3
    assert retrieved.low_count == 4
    assert retrieved.info_count == 5


def test_findings_create_retrieve_and_count_by_severity(db_session: Session):
    scan = create_scan(db_session, "project", ["bandit", "gitleaks"])
    db_session.commit()
    first = create_finding(db_session, **finding_values(scan.id, FindingSeverity.HIGH))
    create_findings(
        db_session,
        [
            finding_values(scan.id, FindingSeverity.MEDIUM, "TEST-002"),
            finding_values(scan.id, FindingSeverity.MEDIUM, "TEST-003"),
            finding_values(scan.id, FindingSeverity.LOW, "TEST-004"),
        ],
    )
    db_session.commit()

    retrieved = get_finding(db_session, first.id)
    findings = get_findings_for_scan(db_session, scan.id)
    counts = count_findings_by_severity(db_session, scan.id)

    assert retrieved is not None
    assert retrieved.rule_id == "TEST-001"
    assert len(findings) == 4
    assert counts == {
        FindingSeverity.CRITICAL: 0,
        FindingSeverity.HIGH: 1,
        FindingSeverity.MEDIUM: 2,
        FindingSeverity.LOW: 1,
        FindingSeverity.INFO: 0,
    }


def test_deleting_scan_cascades_to_findings(db_session: Session):
    scan = create_scan(db_session, "delete-me")
    db_session.commit()
    finding = create_finding(db_session, **finding_values(scan.id, FindingSeverity.INFO))
    finding_id = finding.id
    db_session.commit()

    delete_scan(db_session, scan)
    db_session.commit()

    assert get_scan(db_session, scan.id) is None
    assert get_finding(db_session, finding_id) is None
