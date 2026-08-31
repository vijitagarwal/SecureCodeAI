from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import Base, get_db
from app.db.models import ScanStatus
from app.db.repositories.scan_repository import get_scan
from app.main import app


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

    with TestClient(app) as client:
        yield client, session_factory, tmp_path

    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def test_valid_upload_creates_queued_scan_and_safe_temp_file(upload_client):
    client, session_factory, upload_dir = upload_client
    source = b'raise RuntimeError("THIS FILE MUST NEVER EXECUTE")\n'

    response = client.post(
        "/api/scans",
        files={"file": ("example.py", source, "text/x-python")},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == ScanStatus.QUEUED
    assert payload["filename"] == "example.py"
    assert isinstance(payload["scan_id"], int)

    with session_factory() as session:
        scan = get_scan(session, payload["scan_id"])
        assert scan is not None
        assert scan.name == "example.py"
        assert scan.status == ScanStatus.QUEUED

    stored_files = list(upload_dir.iterdir())
    assert len(stored_files) == 1
    assert stored_files[0].name != "example.py"
    assert stored_files[0].suffix == ".py"
    assert stored_files[0].read_bytes() == source


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
    assert len(list(upload_dir.iterdir())) == 1


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
    stored_files = list(upload_dir.iterdir())
    assert len(stored_files) == 1
    assert stored_files[0].name != "evil.py"
    assert stored_files[0].parent == upload_dir


def test_missing_file_is_rejected(upload_client):
    client, _, upload_dir = upload_client

    response = client.post("/api/scans")

    assert response.status_code == 400
    assert response.json()["detail"] == "A valid filename is required."
    assert list(upload_dir.iterdir()) == []
