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
    try:
        update_scan_status(db, scan, ScanStatus.RUNNING)
        db.commit()
        result = scanner.scan(target_path)
        if result.errors:
            raise ScannerError("Scanner returned errors; coverage is incomplete.")
        values = [
            {
                "scan_id": scan.id,
                "tool": finding.tool,
                "rule_id": finding.rule_id,
                "title": finding.title,
                "description": finding.description,
                "severity": finding.severity,
                "confidence": finding.confidence,
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
        scan.failure_reason = None
        update_scan_status(db, scan, ScanStatus.COMPLETED)
        db.commit()
    except ScannerError as error:
        db.rollback()
        logger.warning("Scanner failed")
        _mark_failed(db, scan, failure_reason=error.public_message)
    except (SQLAlchemyError, ScanExecutionError):
        db.rollback()
        logger.error("Scan failed due to an internal error")
        _mark_failed(db, scan)
    except Exception:
        db.rollback()
        logger.error("Scan failed due to an unexpected error")
        _mark_failed(db, scan)
    finally:
        try:
            Path(target_path).unlink(missing_ok=True)
        except OSError:
            logger.error("Failed to remove temporary scan file")


def _mark_failed(db: Session, scan: Scan, failure_reason: str = "Scan could not be completed.") -> None:
    try:
        persisted_scan = db.get(Scan, scan.id)
        if persisted_scan is not None:
            persisted_scan.failure_reason = failure_reason[:500]
            update_scan_status(db, persisted_scan, ScanStatus.FAILED)
            db.commit()
    except SQLAlchemyError:
        db.rollback()
        logger.error("Failed to persist failed scan status")
