from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.db.models import FindingConfidence, FindingSeverity


@dataclass(frozen=True)
class ScannerFinding:
    tool: str
    rule_id: str
    title: str
    description: str
    severity: FindingSeverity
    confidence: FindingConfidence
    file_path: str
    line_number: int | None
    code_snippet: str | None
    raw_metadata: dict[str, Any]


@dataclass(frozen=True)
class ScannerResult:
    findings: list[ScannerFinding] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class ScannerError(Exception):
    def __init__(self, message: str, *, public_message: str = "The scanner could not complete this file."):
        super().__init__(message)
        self.public_message = public_message


class SecurityScanner(ABC):
    @abstractmethod
    def scan(self, target_path: str) -> ScannerResult:
        """Run static analysis against a target without executing its source."""
