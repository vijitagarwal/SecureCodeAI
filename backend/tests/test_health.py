from fastapi.testclient import TestClient

from app.main import app


def test_health_reports_backend_and_database(monkeypatch):
    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def execute(self, query):
            assert str(query).startswith("SELECT")

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


def test_health_does_not_expose_database_error_details(monkeypatch):
    class FakeEngine:
        def connect(self):
            raise RuntimeError("password=super-secret host=internal-db")

    monkeypatch.setattr("app.api.routes.health.engine", FakeEngine())

    response = TestClient(app).get("/api/health")

    assert response.status_code == 503
    assert response.json() == {
        "status": "degraded",
        "backend": {"status": "ok"},
        "database": {"status": "unavailable"},
    }


def test_liveness_does_not_require_database(monkeypatch):
    class BrokenEngine:
        def connect(self):
            raise AssertionError("liveness must not probe the database")

    monkeypatch.setattr("app.api.routes.health.engine", BrokenEngine())
    response = TestClient(app).get("/api/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "backend": "ok"}
    assert response.headers["x-request-id"]
