from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import settings
from app.db.database import engine


router = APIRouter()


@router.get("/health")
def health() -> dict[str, object]:
    database: dict[str, str] = {"status": "ok"}
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as error:
        database = {"status": "unavailable", "detail": str(error)}

    return {
        "status": "ok" if database["status"] == "ok" else "degraded",
        "backend": {"status": "ok"},
        "database": database,
    }
