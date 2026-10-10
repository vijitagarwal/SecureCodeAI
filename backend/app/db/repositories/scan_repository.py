from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import FindingSeverity, Scan, ScanStatus


def create_scan(
    db: Session,
    name: str,
    scanner_names: list[str] | None = None,
    status: ScanStatus = ScanStatus.QUEUED,
) -> Scan:
    scan = Scan(name=name, scanner_names=scanner_names or ["bandit"], status=status)
    db.add(scan)
    db.flush()
    return scan


def get_scan(db: Session, scan_id: int) -> Scan | None:
    return db.get(Scan, scan_id)


def list_scans(db: Session, *, offset: int = 0, limit: int = 20) -> tuple[list[Scan], int]:
    scans = list(
        db.scalars(
            select(Scan)
            .order_by(Scan.created_at.desc(), Scan.id.desc())
            .offset(offset)
            .limit(limit)
        )
    )
    total = db.scalar(select(func.count(Scan.id))) or 0
    return scans, total


def update_scan_status(db: Session, scan: Scan, status: ScanStatus) -> Scan:
    scan.status = status
    now = datetime.now(timezone.utc)
    if status == ScanStatus.RUNNING and scan.started_at is None:
        scan.started_at = now
    if status in {ScanStatus.COMPLETED, ScanStatus.FAILED}:
        scan.completed_at = now
    db.flush()
    return scan


def update_scan_counts(db: Session, scan: Scan, counts: dict[FindingSeverity, int]) -> Scan:
    scan.total_findings = sum(counts.values())
    scan.critical_count = counts.get(FindingSeverity.CRITICAL, 0)
    scan.high_count = counts.get(FindingSeverity.HIGH, 0)
    scan.medium_count = counts.get(FindingSeverity.MEDIUM, 0)
    scan.low_count = counts.get(FindingSeverity.LOW, 0)
    scan.info_count = counts.get(FindingSeverity.INFO, 0)
    db.flush()
    return scan


def delete_scan(db: Session, scan: Scan) -> None:
    db.delete(scan)
    db.flush()
