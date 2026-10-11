import asyncio
import threading
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.main import app
from app.security.http import RequestBoundaryMiddleware
from test_upload import upload_client

KEY = "test-workspace-key-not-for-use-123456"


@pytest.mark.parametrize("authorization", [None, "", "Bearer", "Bearer ", "Basic " + KEY, "Bearer wrong"])
def test_every_sensitive_route_requires_key(monkeypatch, authorization):
    monkeypatch.setattr(settings, "api_key", SecretStr(KEY))
    headers = {} if authorization is None else {"Authorization": authorization}
    with TestClient(app) as client:
        for method, path in [
            ("GET", "/api/workspace"), ("GET", "/api/scans"), ("POST", "/api/scans/"),
            ("GET", "/api/scans/1"), ("GET", "/api/scans/1/findings"),
            ("GET", "/api/scans/1/report"), ("DELETE", "/api/scans/1"),
            ("POST", "/api/findings/1/analysis"), ("GET", "/api/findings/1/analysis"),
            ("PATCH", "/api/scans/1"), ("HEAD", "/api/scans"),
        ]:
            response = client.request(method, path, headers=headers)
            assert response.status_code == 401
            assert response.headers["cache-control"] == "no-store"
            assert KEY not in response.text


def test_failed_exclusive_create_preserves_existing_file(upload_client, monkeypatch):
    client, _, directory = upload_client
    existing = directory / "collision.py"
    existing.write_text("original owned data", encoding="utf-8")
    monkeypatch.setattr("app.services.upload_service.uuid4", lambda: SimpleNamespace(hex="collision"))
    response = client.post("/api/scans", files={"file": ("example.py", b"value = 1")})
    assert response.status_code == 503
    assert existing.read_text(encoding="utf-8") == "original owned data"


def test_cancelled_request_keeps_capacity_until_worker_finishes(monkeypatch):
    monkeypatch.setattr(settings, "api_key", SecretStr(KEY))
    monkeypatch.setattr(settings, "max_concurrent_scans", 1)

    async def scenario():
        entered, release = threading.Event(), threading.Event()

        def blocking_work():
            entered.set()
            assert release.wait(timeout=5)

        async def worker(scope, receive, send):
            await run_in_threadpool(blocking_work)

        boundary = RequestBoundaryMiddleware(worker)
        scope = {"type": "http", "method": "POST", "path": "/api/scans", "headers": [
            (b"authorization", f"Bearer {KEY}".encode())]}
        messages = []

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            messages.append(message)

        task = asyncio.create_task(boundary(scope, receive, send))
        while not entered.is_set():
            await asyncio.sleep(0.01)
        task.cancel()
        await asyncio.sleep(0.02)
        assert not task.done(), "Cancellation abandoned active work"
        await boundary(scope, receive, send)
        assert messages[0]["status"] == 429
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        await boundary(scope, receive, send)

    asyncio.run(scenario())


@pytest.mark.parametrize("extra_headers,body,expected", [
    ([(b"content-length", b"-1")], b"", 400),
    ([(b"content-length", b"+1")], b"x", 400),
    ([(b"content-length", b"1"), (b"content-length", b"2")], b"x", 400),
    ([(b"content-length", b"1"), (b"transfer-encoding", b"chunked")], b"x", 400),
    ([(b"content-length", b"1")], b"xx", 400),
    ([(b"content-length", b"99999999")], b"", 413),
    ([(b"authorization", b"Bearer wrong")], b"", 400),
])
def test_ambiguous_framing_never_reaches_parser(monkeypatch, extra_headers, body, expected):
    monkeypatch.setattr(settings, "api_key", SecretStr(KEY))
    messages = []

    async def unused(*args):
        raise AssertionError("Invalid body reached parser")

    async def receive():
        return {"type": "http.request", "body": body}

    async def send(message):
        messages.append(message)

    boundary = RequestBoundaryMiddleware(unused)
    scope = {"type": "http", "method": "POST", "path": "/api/scans", "headers": [
        (b"authorization", f"Bearer {KEY}".encode()), *extra_headers]}
    asyncio.run(boundary(scope, receive, send))
    assert messages[0]["status"] == expected
    assert boundary.scan_slots.acquire(blocking=False)
    boundary.scan_slots.release()


def test_exception_and_disconnect_release_analysis_capacity(monkeypatch):
    monkeypatch.setattr(settings, "api_key", SecretStr(KEY))
    monkeypatch.setattr(settings, "max_concurrent_analyses", 1)

    async def fail(*args):
        raise RuntimeError("fixture failure")

    async def receive():
        return {"type": "http.request", "body": b""}

    async def disconnect():
        return {"type": "http.disconnect"}

    async def send(message):
        pass

    boundary = RequestBoundaryMiddleware(fail)
    scope = {"type": "http", "method": "POST", "path": "/api/findings/1/analysis", "headers": [
        (b"authorization", f"Bearer {KEY}".encode())]}
    with pytest.raises(RuntimeError):
        asyncio.run(boundary(scope, receive, send))
    asyncio.run(boundary(scope, disconnect, send))
    assert boundary.analysis_slots.acquire(blocking=False)
    boundary.analysis_slots.release()
