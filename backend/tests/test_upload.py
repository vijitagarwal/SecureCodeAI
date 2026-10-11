from pathlib import Path
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session, sessionmaker
from pydantic import SecretStr

from app.db.database import Base, get_db
from app.db.models import ScanStatus
from app.db.repositories.scan_repository import get_scan
from app.main import app
from app.scanners.base import ScannerError


@pytest.fixture
def upload_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, connection_record):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    def override_get_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr("app.services.upload_service.settings.upload_dir", str(tmp_path))
    monkeypatch.setattr("app.services.upload_service.settings.max_upload_size_bytes", 5 * 1024 * 1024)
    monkeypatch.setattr("app.core.config.settings.api_key", SecretStr("test-workspace-key-not-for-use-123456"))
    monkeypatch.setattr("app.core.config.settings.ai_provider", "mock")

    with TestClient(app, headers={"Authorization": "Bearer test-workspace-key-not-for-use-123456"}) as client:
        yield client, session_factory, tmp_path

    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def test_vulnerable_upload_creates_completed_scan_and_cleans_temp_file(upload_client):
    client, session_factory, upload_dir = upload_client
    source = b'password = "not-a-real-secret"\n'

    response = client.post(
        "/api/scans",
        files={"file": ("example.py", source, "text/x-python")},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == ScanStatus.COMPLETED
    assert payload["filename"] == "example.py"
    assert isinstance(payload["scan_id"], int)
    assert payload["total_findings"] >= 1

    with session_factory() as session:
        scan = get_scan(session, payload["scan_id"])
        assert scan is not None
        assert scan.name == "example.py"
        assert scan.status == ScanStatus.COMPLETED
        assert scan.total_findings >= 1

    stored_files = list(upload_dir.iterdir())
    assert stored_files == []


def test_clean_upload_creates_completed_scan_without_findings(upload_client):
    client, session_factory, upload_dir = upload_client

    response = client.post(
        "/api/scans",
        files={"file": ("clean.py", b"value = 1\n", "text/x-python")},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == ScanStatus.COMPLETED
    assert payload["total_findings"] == 0
    with session_factory() as session:
        scan = get_scan(session, payload["scan_id"])
        assert scan is not None
        assert scan.total_findings == 0
    assert list(upload_dir.iterdir()) == []


def test_scan_and_findings_endpoints_return_persisted_results(upload_client):
    client, _, _ = upload_client
    response = client.post(
        "/api/scans",
        files={"file": ("example.py", b'password = "not-a-real-secret"\n', "text/x-python")},
    )
    scan_id = response.json()["scan_id"]

    scan_response = client.get(f"/api/scans/{scan_id}")
    findings_response = client.get(f"/api/scans/{scan_id}/findings")

    assert scan_response.status_code == 200
    assert scan_response.json()["status"] == ScanStatus.COMPLETED
    assert scan_response.json()["total_findings"] >= 1
    assert findings_response.status_code == 200
    assert findings_response.json()[0]["tool"] == "bandit"
    assert "raw_metadata" not in findings_response.json()[0]


def test_scan_history_is_paginated_and_newest_first(upload_client):
    client, _, _ = upload_client
    first = client.post(
        "/api/scans",
        files={"file": ("first.py", b"value = 1\n", "text/x-python")},
    )
    second = client.post(
        "/api/scans",
        files={"file": ("second.py", b'password = "not-a-real-secret"\n', "text/x-python")},
    )

    response = client.get("/api/scans?offset=0&limit=1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert payload["offset"] == 0
    assert payload["limit"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["id"] == second.json()["scan_id"]
    assert payload["items"][0]["scanner_names"] == ["bandit"]
    assert first.json()["scan_id"] != second.json()["scan_id"]


def test_stale_running_scan_is_reconciled_as_failed(upload_client, monkeypatch):
    client, session_factory, _ = upload_client
    from app.db.repositories.scan_repository import create_scan, update_scan_status
    from app.db.models import ScanStatus

    monkeypatch.setattr("app.core.config.settings.stale_scan_timeout_seconds", 30)
    with session_factory() as session:
        scan = create_scan(session, "interrupted.py")
        update_scan_status(session, scan, ScanStatus.RUNNING)
        scan.started_at = datetime.now(timezone.utc) - timedelta(seconds=60)
        session.commit()
        scan_id = scan.id

    response = client.get(f"/api/scans/{scan_id}")

    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert response.json()["failure_reason"] == "The scan worker stopped before completion."
    assert client.delete(f"/api/scans/{scan_id}").status_code == 204


def test_scan_and_api_responses_include_security_headers(upload_client):
    client, _, _ = upload_client

    response = client.post(
        "/api/scans",
        files={"file": ("example.py", b"value = 1\n", "text/x-python")},
    )

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["content-security-policy"] == "default-src 'none'; frame-ancestors 'none'"
    assert response.headers["x-request-id"]


def test_finding_analysis_can_be_generated_and_retrieved(upload_client):
    client, _, _ = upload_client
    scan_response = client.post(
        "/api/scans",
        files={"file": ("example.py", b'password = "not-a-real-secret"\n', "text/x-python")},
    )
    finding_id = client.get(
        f"/api/scans/{scan_response.json()['scan_id']}/findings"
    ).json()[0]["id"]

    create_response = client.post(f"/api/findings/{finding_id}/analysis")
    read_response = client.get(f"/api/findings/{finding_id}/analysis")

    assert create_response.status_code == 201
    assert create_response.json()["finding_id"] == finding_id
    assert read_response.status_code == 200
    assert read_response.json()["status"] == "completed"


def test_analysis_for_unknown_finding_is_not_found(upload_client):
    client, _, _ = upload_client

    response = client.post("/api/findings/999999/analysis")

    assert response.status_code == 404


def test_report_size_limit_is_enforced_before_export(upload_client, monkeypatch):
    client, _, _ = upload_client
    monkeypatch.setattr("app.api.routes.scans.settings.max_report_bytes", 1)
    scan_response = client.post(
        "/api/scans", files={"file": ("example.py", b'password = "not-a-real-secret"\n')}
    )

    report = client.get(f"/api/scans/{scan_response.json()['scan_id']}/report")

    assert report.status_code == 409
    assert report.json()["detail"] == "This report exceeds the configured export size. Retrieve findings in pages."


def test_unknown_analysis_provider_returns_safe_503(upload_client, monkeypatch):
    client, _, _ = upload_client
    from app.llm.factory import settings

    monkeypatch.setattr(settings, "ai_provider", "unknown")

    scan_response = client.post(
        "/api/scans",
        files={"file": ("example.py", b'password = "not-a-real-secret"\n', "text/x-python")},
    )
    finding_id = client.get(f"/api/scans/{scan_response.json()['scan_id']}/findings").json()[0]["id"]

    response = client.post(f"/api/findings/{finding_id}/analysis")

    assert response.status_code == 503
    assert response.json()["detail"] == "Security analysis is currently unavailable."


def test_remote_analysis_failure_saves_explicit_local_fallback(upload_client, monkeypatch):
    client, _, _ = upload_client
    from app.llm.base import ProviderError

    monkeypatch.setattr("app.core.config.settings.ai_provider", "gemini")
    monkeypatch.setattr(
        "app.api.routes.scans.get_security_analysis_provider",
        lambda: (_ for _ in ()).throw(ProviderError("provider unavailable")),
    )
    scan_response = client.post(
        "/api/scans",
        files={"file": ("example.py", b'password = "not-a-real-secret"\n')},
    )
    finding_id = client.get(f"/api/scans/{scan_response.json()['scan_id']}/findings").json()[0]["id"]

    response = client.post(f"/api/findings/{finding_id}/analysis")

    assert response.status_code == 201
    assert response.json()["provider"] == "mock-fallback"


def test_scanner_failure_marks_scan_failed_and_cleans_file(upload_client, monkeypatch):
    client, session_factory, upload_dir = upload_client
    monkeypatch.setattr(
        "app.services.upload_service.BanditScanner.scan",
        lambda self, target_path: (_ for _ in ()).throw(ScannerError("test failure")),
    )

    response = client.post(
        "/api/scans",
        files={"file": ("example.py", b"value = 1\n", "text/x-python")},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == ScanStatus.FAILED
    assert payload["failure_reason"] == "The scanner could not complete this file."
    with session_factory() as session:
        assert get_scan(session, payload["scan_id"]).status == ScanStatus.FAILED
    assert list(upload_dir.iterdir()) == []


@pytest.mark.parametrize("filename", ["example.txt", "script.exe", "run.sh", "archive.zip"])
def test_unsupported_extension_is_rejected(upload_client, filename: str):
    client, _, upload_dir = upload_client

    response = client.post("/api/scans", files={"file": (filename, b"data", "text/plain")})

    assert response.status_code == 415
    assert response.json()["detail"] == "Only Python (.py) files are supported."
    assert list(upload_dir.iterdir()) == []


def test_extension_check_is_case_insensitive(upload_client):
    client, _, upload_dir = upload_client

    response = client.post("/api/scans", files={"file": ("example.PY", b"value = 1\n", "text/plain")})

    assert response.status_code == 201
    assert response.json()["filename"] == "example.PY"
    assert response.json()["status"] == ScanStatus.COMPLETED
    assert list(upload_dir.iterdir()) == []


def test_oversized_upload_is_rejected_and_cleaned_up(upload_client, monkeypatch):
    client, _, upload_dir = upload_client
    monkeypatch.setattr("app.services.upload_service.settings.max_upload_size_bytes", 4)

    response = client.post("/api/scans", files={"file": ("large.py", b"12345", "text/x-python")})

    assert response.status_code == 413
    assert response.json()["detail"] == "The uploaded file exceeds the configured size limit."
    assert list(upload_dir.iterdir()) == []


@pytest.mark.parametrize("filename", ["../../evil.py", r"..\..\evil.py"])
def test_path_traversal_filename_is_rejected(upload_client, filename: str):
    client, _, upload_dir = upload_client

    response = client.post("/api/scans", files={"file": (filename, b"safe = True", "text/x-python")})

    assert response.status_code == 400
    assert response.json()["detail"] == "Path separators are not allowed in filenames."
    assert list(upload_dir.iterdir()) == []


def test_windows_absolute_filename_is_stored_under_generated_name(upload_client):
    client, _, upload_dir = upload_client

    response = client.post(
        "/api/scans",
        files={"file": (r"C:\Windows\evil.py", b"safe = True", "text/x-python")},
    )

    assert response.status_code == 201
    assert response.json()["status"] == ScanStatus.COMPLETED
    assert list(upload_dir.iterdir()) == []


def test_missing_file_is_rejected(upload_client):
    client, _, upload_dir = upload_client

    response = client.post("/api/scans")

    assert response.status_code == 400
    assert response.json()["detail"] == "A valid filename is required."
    assert list(upload_dir.iterdir()) == []
