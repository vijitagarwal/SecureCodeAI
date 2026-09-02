import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.db.models import FindingConfidence, FindingSeverity
from app.scanners.base import ScannerError, ScannerFinding, ScannerResult, SecurityScanner


class BanditScanner(SecurityScanner):
    def __init__(self, timeout_seconds: int | None = None):
        self.timeout_seconds = timeout_seconds or settings.scanner_timeout_seconds

    def scan(self, target_path: str) -> ScannerResult:
        command = [sys.executable, "-m", "bandit", "-f", "json", target_path]
        try:
            completed = subprocess.run(
                command,
                shell=False,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except FileNotFoundError as error:
            raise ScannerError("Bandit is not available.") from error
        except subprocess.TimeoutExpired as error:
            raise ScannerError("Bandit scan timed out.") from error
        except OSError as error:
            raise ScannerError("Bandit could not be started.") from error

        if not completed.stdout.strip():
            raise ScannerError("Bandit returned no usable output.")
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as error:
            raise ScannerError("Bandit returned malformed JSON.") from error

        findings = [self._parse_finding(item) for item in payload.get("results", [])]
        return ScannerResult(
            findings=findings,
            errors=[str(item) for item in payload.get("errors", [])],
            metadata={"exit_code": completed.returncode, "metrics": payload.get("metrics", {})},
        )

    @staticmethod
    def _parse_finding(item: dict[str, Any]) -> ScannerFinding:
        try:
            severity = FindingSeverity(str(item["issue_severity"]).upper())
            confidence = FindingConfidence(str(item["issue_confidence"]).upper())
            file_path = str(item["filename"])
            rule_id = str(item["test_id"])
            title = str(item["issue_text"])
        except (KeyError, ValueError, TypeError) as error:
            raise ScannerError("Bandit returned an invalid finding.") from error

        return ScannerFinding(
            tool="bandit",
            rule_id=rule_id,
            title=title,
            description=title,
            severity=severity,
            confidence=confidence,
            file_path=Path(file_path).name,
            line_number=item.get("line_number"),
            code_snippet=item.get("code"),
            raw_metadata=item,
        )
