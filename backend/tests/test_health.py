from fastapi.testclient import TestClient

from app.main import app


def test_health_reports_backend_and_database(monkeypatch):
    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def execute(self, query):
            assert str(query) == "SELECT 1"

    class FakeEngine:
        def connect(self):
            return FakeConnection()

    monkeypatch.setattr("app.api.routes.health.engine", FakeEngine())

    response = TestClient(app).get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "backend": {"status": "ok"},
        "database": {"status": "ok"},
    }
