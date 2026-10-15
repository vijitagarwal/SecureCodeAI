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
        self.timeout_seconds = timeout_seconds if timeout_seconds is not None else settings.scanner_timeout_seconds
        if self.timeout_seconds <= 0:
            raise ValueError("Bandit timeout must be positive.")

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

        if not isinstance(payload, dict):
            raise ScannerError("Bandit returned an invalid JSON document.")
        raw_results = payload.get("results", [])
        if not isinstance(raw_results, list):
            raise ScannerError("Bandit returned invalid finding data.")
        findings = [self._parse_finding(item) for item in raw_results]
        return ScannerResult(
            findings=findings,
            errors=[str(item) for item in payload.get("errors", [])]
            if isinstance(payload.get("errors", []), list)
            else [],
            metadata={"exit_code": completed.returncode, "metrics": payload.get("metrics", {})},
        )

    @staticmethod
    def _parse_finding(item: dict[str, Any]) -> ScannerFinding:
        if not isinstance(item, dict):
            raise ScannerError("Bandit returned an invalid finding.")
        try:
            severity = FindingSeverity(str(item["issue_severity"]).upper())
            confidence = FindingConfidence(str(item["issue_confidence"]).upper())
            file_path = item["filename"]
            rule_id = item["test_id"]
            title = item["issue_text"]
        except (KeyError, ValueError, TypeError) as error:
            raise ScannerError("Bandit returned an invalid finding.") from error
        if not all(
            isinstance(value, str) and value.strip()
            for value in (file_path, rule_id, title)
        ):
            raise ScannerError("Bandit returned an invalid finding.")
        line_number = item.get("line_number")
        if line_number is not None and (
            isinstance(line_number, bool) or not isinstance(line_number, int) or line_number < 1
        ):
            raise ScannerError("Bandit returned an invalid line number.")
        code_snippet = item.get("code")
        if code_snippet is not None and not isinstance(code_snippet, str):
            raise ScannerError("Bandit returned an invalid code snippet.")

        raw_metadata = dict(item)
        raw_metadata["filename"] = Path(file_path).name
        return ScannerFinding(
            tool="bandit",
            rule_id=rule_id,
            title=title,
            description=title,
            severity=severity,
            confidence=confidence,
            file_path=Path(file_path).name,
            line_number=line_number,
            code_snippet=code_snippet,
            raw_metadata=raw_metadata,
        )
