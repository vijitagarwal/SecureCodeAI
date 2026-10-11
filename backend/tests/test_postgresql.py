"""Opt-in PostgreSQL integration against a disposable, isolated schema."""
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.database import get_db
from app.main import app


@pytest.mark.skipif(not os.environ.get("TEST_POSTGRES_URL"), reason="TEST_POSTGRES_URL not configured")
def test_migrated_postgresql_scan_analysis_and_cascade(tmp_path, monkeypatch):
    url = make_url(os.environ["TEST_POSTGRES_URL"])
    assert url.get_backend_name() == "postgresql"
    schema = "securecode_test_" + uuid4().hex
    admin = create_engine(url, connect_args={"connect_timeout": 5})
    with admin.begin() as connection:
        connection.exec_driver_sql(f"CREATE SCHEMA {schema}")
    isolated = url.update_query_dict({"options": f"-csearch_path={schema}"})
    engine = create_engine(isolated)
    sessions = sessionmaker(bind=engine)
    try:
        env = {**os.environ, "DATABASE_URL": isolated.render_as_string(hide_password=False)}
        migrated = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"],
                                  cwd=Path(__file__).resolve().parents[1], env=env,
                                  stdin=subprocess.DEVNULL, capture_output=True, timeout=30)
        assert migrated.returncode == 0, "PostgreSQL migrations failed (details intentionally omitted)."
        def database():
            with sessions() as session:
                yield session
        app.dependency_overrides[get_db] = database
        monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
        monkeypatch.setattr(settings, "ai_provider", "mock")
        monkeypatch.setattr(settings, "api_key", SecretStr("test-workspace-key-not-for-use-123456"))
        with TestClient(app, headers={"Authorization": "Bearer test-workspace-key-not-for-use-123456"}) as client:
            response = client.post("/api/scans", files={"file": ("sample.py", b"eval(input())\n")})
            assert response.status_code == 201
            scan_id = response.json()["scan_id"]
            assert response.json()["status"] == "completed"
            finding_id = client.get(f"/api/scans/{scan_id}/findings").json()[0]["id"]
            assert client.post(f"/api/findings/{finding_id}/analysis").status_code == 201
            assert client.get(f"/api/findings/{finding_id}/analysis").json()["provider"] == "mock"
            assert client.delete(f"/api/scans/{scan_id}").status_code == 204
            assert client.get(f"/api/findings/{finding_id}/analysis").status_code == 404
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
        with admin.begin() as connection:
            connection.exec_driver_sql(f"DROP SCHEMA {schema} CASCADE")
        admin.dispose()
