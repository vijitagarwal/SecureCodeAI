import logging

from fastapi import APIRouter, Response
from sqlalchemy import select, text

from app.db.database import engine
from app.db.models import Scan, SecurityAnalysis


router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
def health(response: Response) -> dict[str, object]:
    database: dict[str, str] = {"status": "ok"}
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            connection.execute(select(Scan).limit(0))
            connection.execute(select(SecurityAnalysis).limit(0))
    except Exception:
        logger.warning("Health check database probe failed")
        database = {"status": "unavailable"}
        response.status_code = 503

    return {
        "status": "ok" if database["status"] == "ok" else "degraded",
        "backend": {"status": "ok"},
        "database": database,
    }
