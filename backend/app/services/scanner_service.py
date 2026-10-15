import logging
from collections import Counter
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.models import FindingSeverity, Scan, ScanStatus
from app.db.repositories.finding_repository import create_findings
from app.db.repositories.scan_repository import update_scan_counts, update_scan_status
from app.scanners.base import ScannerError, SecurityScanner
from app.security.classification import classify_rule


logger = logging.getLogger(__name__)


class ScanExecutionError(Exception):
    pass


def run_scan(db: Session, scan: Scan, target_path: str, scanner: SecurityScanner) -> None:
    update_scan_status(db, scan, ScanStatus.RUNNING)
    db.commit()
    try:
        result = scanner.scan(target_path)
        values = [
            {
                "scan_id": scan.id,
                "tool": finding.tool,
                "rule_id": finding.rule_id,
                "title": finding.title,
                "description": finding.description,
                "severity": finding.severity,
                "confidence": finding.confidence,
                # A scan contains one uploaded source file; never persist a
                # scanner-controlled path from outside that upload boundary.
                "file_path": scan.name,
                "line_number": finding.line_number,
                "code_snippet": finding.code_snippet,
                "raw_metadata": finding.raw_metadata,
                "cwe_id": classify_rule(finding.rule_id).cwe_id,
                "cwe_name": classify_rule(finding.rule_id).cwe_name,
                "owasp_category": classify_rule(finding.rule_id).owasp_category,
                "remediation_category": classify_rule(finding.rule_id).remediation_category,
                "remediation_guidance": classify_rule(finding.rule_id).remediation_guidance,
            }
            for finding in result.findings
        ]
        create_findings(db, values)
        counts = Counter(finding.severity for finding in result.findings)
        update_scan_counts(db, scan, dict(counts))
        update_scan_status(db, scan, ScanStatus.COMPLETED)
        db.commit()
    except (ScannerError, SQLAlchemyError, ScanExecutionError) as error:
        db.rollback()
        logger.error("Scan failed: %s", error)
        _mark_failed(db, scan)
    finally:
        try:
            Path(target_path).unlink(missing_ok=True)
        except OSError:
            logger.exception("Failed to remove temporary scan file")


def _mark_failed(db: Session, scan: Scan) -> None:
    try:
        persisted_scan = db.get(Scan, scan.id)
        if persisted_scan is not None:
            update_scan_status(db, persisted_scan, ScanStatus.FAILED)
            db.commit()
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Failed to persist failed scan status")
