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
    assert result.metadata["exit_code"] == 1
    finding = result.findings[0]
    assert finding.rule_id == "B105"
    assert finding.severity == FindingSeverity.LOW
    assert finding.confidence == FindingConfidence.MEDIUM
    assert finding.file_path == "vulnerable.py"
    assert finding.line_number == 1
    assert finding.raw_metadata["filename"] == "vulnerable.py"


@pytest.fixture
def raw_finding():
    return {
        "filename": "example.py", "test_id": "B105", "issue_text": "Possible hardcoded password",
        "issue_severity": "LOW", "issue_confidence": "MEDIUM", "line_number": 1,
        "code": "password = 'not-real'",
    }


def test_bandit_accepts_findings_exit_code(monkeypatch, raw_finding):
    completed = subprocess.CompletedProcess([], 1, json.dumps({"results": [raw_finding]}), "")
    monkeypatch.setattr("app.scanners.bandit._execute", lambda *args: completed)
    assert len(BanditScanner().scan("example.py").findings) == 1


@pytest.mark.parametrize("payload", [[], {}, {"results": {}}, {"results": [None]}, {"results": [], "errors": {}}])
def test_bandit_rejects_invalid_result_shapes(monkeypatch, payload):
    completed = subprocess.CompletedProcess([], 0, json.dumps(payload), "")
    monkeypatch.setattr("app.scanners.bandit._execute", lambda *args: completed)
    with pytest.raises(ScannerError, match="invalid"):
        BanditScanner().scan("example.py")


def test_bandit_rejects_malformed_json(monkeypatch):
    monkeypatch.setattr("app.scanners.bandit._execute", lambda *args: subprocess.CompletedProcess([], 0, "not json", ""))
    with pytest.raises(ScannerError, match="malformed JSON"):
        BanditScanner().scan("example.py")


@pytest.mark.parametrize("error", [FileNotFoundError(), subprocess.TimeoutExpired("bandit", 1)])
def test_bandit_handles_process_failure(monkeypatch, error):
    def fail(*args):
        raise error
    monkeypatch.setattr("app.scanners.bandit._execute", fail)
    with pytest.raises(ScannerError):
        BanditScanner().scan("example.py")


@pytest.mark.parametrize("field,value", [
    ("filename", "C:\\" + "x" * 300), ("test_id", "x" * 101),
    ("issue_text", "x" * 501), ("code", "x" * 10001),
    ("issue_severity", "CRITICAL"), ("line_number", True), ("issue_text", None),
], ids=["filename", "rule", "title", "snippet", "severity", "line", "missing-text"])
def test_bandit_rejects_invalid_fields(monkeypatch, raw_finding, field, value):
    raw_finding[field] = value
    completed = subprocess.CompletedProcess([], 1, json.dumps({"results": [raw_finding]}), "")
    monkeypatch.setattr("app.scanners.bandit._execute", lambda *args: completed)
    with pytest.raises(ScannerError, match="invalid"):
        BanditScanner().scan("example.py")


@pytest.mark.parametrize("source", [b"def broken(:", b"\x00\xff\x01"])
def test_invalid_python_never_reports_clean(tmp_path, source):
    path = tmp_path / "invalid.py"
    path.write_bytes(source)
    with pytest.raises(ScannerError):
        BanditScanner().scan(str(path))


def test_uploaded_source_is_not_executed_and_cannot_suppress_findings(tmp_path):
    path = tmp_path / "untrusted.py"
    marker = tmp_path / "executed.txt"
    path.write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).touch()\n"
        'password = "not-a-real-secret" # nosec\n', encoding="utf-8",
    )
    assert any(f.rule_id == "B105" for f in BanditScanner().scan(str(path)).findings)
    assert not marker.exists()


@pytest.mark.parametrize("source,rule", [
    ("import subprocess\nsubprocess.run(input(), shell=True)\n", "B602"),
    ("eval(input())\n", "B307"),
    ("import yaml\nyaml.load(input())\n", "B506"),
    ("import random\ntoken = random.random()\n", "B311"),
])
def test_vulnerable_corpus(tmp_path, source, rule):
    path = tmp_path / "vulnerable.py"
    path.write_text(source, encoding="utf-8")
    assert rule in {finding.rule_id for finding in BanditScanner().scan(str(path)).findings}


def test_secure_counterparts(tmp_path):
    path = tmp_path / "secure.py"
    path.write_text("import json\nimport secrets\nvalue = json.loads('{}')\ntoken = secrets.token_hex(32)\n", encoding="utf-8")
    assert BanditScanner().scan(str(path)).findings == []
