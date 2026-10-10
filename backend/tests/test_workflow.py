import asyncio

from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import settings
from app.db.models import Finding, SecurityAnalysis
from app.main import app
from app.security.http import RequestBoundaryMiddleware
from test_upload import upload_client


def test_access_is_required_before_upload_parsing(monkeypatch):
    monkeypatch.setattr(settings, "api_key", SecretStr("test-workspace-key-not-for-use-123456"))
    with TestClient(app) as client:
        for method, path in [("POST", "/api/scans"), ("GET", "/api/scans"),
                             ("GET", "/api/scans/1/report"), ("DELETE", "/api/scans/1"),
                             ("POST", "/api/findings/1/analysis")]:
            response = client.request(method, path)
            assert response.status_code == 401
            assert response.headers["cache-control"] == "no-store"
        assert client.get("/api/scans", headers={"Authorization": "Bearer invalid"}).status_code == 401


def test_unconfigured_workspace_fails_closed(monkeypatch):
    monkeypatch.setattr(settings, "api_key", None)
    assert TestClient(app).get("/api/scans").status_code == 503


def test_full_persisted_workflow_export_and_delete(upload_client):
    client, session_factory, _ = upload_client
    result = client.post("/api/scans", files={"file": ("sample.py", b'eval(input())\n')}).json()
    scan_id = result["scan_id"]
    assert result["status"] == "completed"
    findings = client.get(f"/api/scans/{scan_id}/findings").json()
    finding_id = findings[0]["id"]
    assert client.post(f"/api/findings/{finding_id}/analysis").status_code == 201
    report = client.get(f"/api/scans/{scan_id}/report")
    assert report.status_code == 200
    assert len(report.json()["findings"]) == result["total_findings"]
    assert report.json()["findings"][0]["analysis"]["finding_id"] == finding_id
    assert "raw_metadata" not in report.text
    assert client.get(f"/api/scans/{scan_id}/findings?severity=HIGH").json() == []
    assert client.get(f"/api/scans/{scan_id}/findings?severity=MEDIUM").json()
    assert client.delete(f"/api/scans/{scan_id}").status_code == 204
    assert client.get(f"/api/scans/{scan_id}").status_code == 404
    assert client.get(f"/api/findings/{finding_id}/analysis").status_code == 404
    with session_factory() as db:
        assert db.query(Finding).count() == 0
        assert db.query(SecurityAnalysis).count() == 0


def test_invalid_python_failure_is_visible_in_history(upload_client):
    client, _, upload_dir = upload_client
    response = client.post("/api/scans", files={"file": ("bad.py", b"def broken(:")})
    assert response.status_code == 201
    assert response.json()["status"] == "failed"
    assert "syntax" in response.json()["failure_reason"]
    assert client.get("/api/scans").json()["items"][0]["status"] == "failed"
    assert list(upload_dir.iterdir()) == []


def test_empty_file_and_invalid_pagination(upload_client):
    client, _, _ = upload_client
    assert client.post("/api/scans", files={"file": ("empty.py", b"")}).status_code == 400
    assert client.get("/api/scans?offset=-1").status_code == 422
    assert client.get("/api/scans?limit=101").status_code == 422


def test_streamed_body_cannot_bypass_limit(monkeypatch):
    monkeypatch.setattr(settings, "api_key", SecretStr("test-workspace-key-not-for-use-123456"))
    monkeypatch.setattr(settings, "max_upload_size_bytes", 1)
    messages = []

    async def unused_app(*args):
        raise AssertionError("Oversized body reached the application")

    async def receive():
        return {"type": "http.request", "body": b"x" * 70000, "more_body": True}

    async def send(message):
        messages.append(message)

    scope = {"type": "http", "path": "/api/scans", "method": "POST", "headers": [
        (b"authorization", b"Bearer test-workspace-key-not-for-use-123456")
    ]}
    asyncio.run(RequestBoundaryMiddleware(unused_app)(scope, receive, send))
    assert messages[0]["status"] == 413
