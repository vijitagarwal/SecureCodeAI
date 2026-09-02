import json
import subprocess

import pytest

from app.db.models import FindingConfidence, FindingSeverity
from app.scanners.bandit import BanditScanner
from app.scanners.base import ScannerError, SecurityScanner


def test_security_scanner_is_an_abstract_contract():
    with pytest.raises(TypeError):
        SecurityScanner()


def test_bandit_actually_scans_python_file(tmp_path):
    source_path = tmp_path / "vulnerable.py"
    source_path.write_text('password = "not-a-real-secret"\n', encoding="utf-8")

    result = BanditScanner().scan(str(source_path))

    assert result.metadata["exit_code"] != 0
    assert result.findings
    finding = result.findings[0]
    assert finding.tool == "bandit"
    assert finding.rule_id == "B105"
    assert finding.severity == FindingSeverity.LOW
    assert finding.confidence == FindingConfidence.MEDIUM
    assert finding.file_path == "vulnerable.py"
    assert finding.line_number == 1
    assert finding.raw_metadata["test_id"] == "B105"


def test_bandit_accepts_valid_json_when_findings_make_exit_nonzero(monkeypatch, tmp_path):
    source_path = tmp_path / "example.py"
    source_path.write_text("value = 1\n", encoding="utf-8")
    payload = {
        "errors": [],
        "metrics": {},
        "results": [
            {
                "filename": str(source_path),
                "test_id": "B105",
                "issue_text": "Possible hardcoded password",
                "issue_severity": "LOW",
                "issue_confidence": "MEDIUM",
                "line_number": 3,
                "code": "password = 'not-real'",
            }
        ],
    }

    completed = subprocess.CompletedProcess([], 1, json.dumps(payload), "findings reported")
    monkeypatch.setattr("app.scanners.bandit.subprocess.run", lambda *args, **kwargs: completed)

    result = BanditScanner().scan(str(source_path))

    assert len(result.findings) == 1
    assert result.metadata["exit_code"] == 1


def test_bandit_rejects_malformed_json(monkeypatch, tmp_path):
    source_path = tmp_path / "example.py"
    source_path.write_text("value = 1\n", encoding="utf-8")
    completed = subprocess.CompletedProcess([], 0, "not json", "")
    monkeypatch.setattr("app.scanners.bandit.subprocess.run", lambda *args, **kwargs: completed)

    with pytest.raises(ScannerError, match="malformed JSON"):
        BanditScanner().scan(str(source_path))


def test_bandit_handles_timeout(monkeypatch, tmp_path):
    source_path = tmp_path / "example.py"
    source_path.write_text("value = 1\n", encoding="utf-8")

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=1)

    monkeypatch.setattr("app.scanners.bandit.subprocess.run", timeout)

    with pytest.raises(ScannerError, match="timed out"):
        BanditScanner().scan(str(source_path))


def test_bandit_handles_missing_executable(monkeypatch, tmp_path):
    source_path = tmp_path / "example.py"
    source_path.write_text("value = 1\n", encoding="utf-8")

    def missing(*args, **kwargs):
        raise FileNotFoundError

    monkeypatch.setattr("app.scanners.bandit.subprocess.run", missing)

    with pytest.raises(ScannerError, match="not available"):
        BanditScanner().scan(str(source_path))
