import logging

from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import settings
from app.db.database import engine


router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
def health() -> dict[str, object]:
    database: dict[str, str] = {"status": "ok"}
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        logger.warning("Health check database probe failed")
        database = {"status": "unavailable"}

    return {
        "status": "ok" if database["status"] == "ok" else "degraded",
        "backend": {"status": "ok"},
        "database": database,
    }
