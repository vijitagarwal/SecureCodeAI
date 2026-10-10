import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect


def test_migrations_round_trip_and_match_models(tmp_path):
    url = "sqlite:///" + str(tmp_path / "migration.db").replace("\\", "/")
    env = {**os.environ, "DATABASE_URL": url, "API_KEY": "test-workspace-key-not-for-use-123456"}

    def migrate(*args):
        result = subprocess.run(
            [sys.executable, "-m", "alembic", *args], cwd=Path(__file__).resolve().parents[1],
            env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, result.stderr

    migrate("upgrade", "head")
    migrate("check")
    engine = create_engine(url)
    assert {"scans", "findings", "security_analyses"} <= set(inspect(engine).get_table_names())
    engine.dispose()
    migrate("downgrade", "base")
    migrate("upgrade", "head")
