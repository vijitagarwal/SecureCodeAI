from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Finding, FindingSeverity


def create_finding(db: Session, **values) -> Finding:
    finding = Finding(**values)
    db.add(finding)
    db.flush()
    return finding


def create_findings(db: Session, findings: list[dict]) -> list[Finding]:
    records = [Finding(**values) for values in findings]
    db.add_all(records)
    db.flush()
    return records


def get_finding(db: Session, finding_id: int) -> Finding | None:
    return db.get(Finding, finding_id)


def get_findings_for_scan(
    db: Session,
    scan_id: int,
    *,
    offset: int = 0,
    limit: int = 100,
) -> list[Finding]:
    statement = (
        select(Finding)
        .where(Finding.scan_id == scan_id)
        .order_by(Finding.id)
        .offset(offset)
        .limit(limit)
    )
    return list(db.scalars(statement))


def count_findings_by_severity(db: Session, scan_id: int) -> dict[FindingSeverity, int]:
    statement = (
        select(Finding.severity, func.count(Finding.id))
        .where(Finding.scan_id == scan_id)
        .group_by(Finding.severity)
    )
    counts = {severity: count for severity, count in db.execute(statement)}
    return {severity: counts.get(severity, 0) for severity in FindingSeverity}
