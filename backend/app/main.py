from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes.health import router as health_router
from app.api.routes.scans import router as scans_router
from app.core.config import settings
from app.security.http import RequestBoundaryMiddleware


app = FastAPI(title="SecureCode AI API", version="0.1.0")
app.add_middleware(RequestBoundaryMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Accept", "Content-Type", "Authorization"],
    max_age=600,
)


@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    if request.url.path.startswith("/api/"):
        response.headers.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
        response.headers.setdefault("Cache-Control", "no-store")
    return response


app.include_router(health_router, prefix="/api")
app.include_router(scans_router, prefix="/api")


@app.exception_handler(SQLAlchemyError)
async def database_unavailable(request, error):
    # SQLAlchemy exceptions may embed source snippets and credentials. Never echo/log them.
    return JSONResponse(status_code=503, content={"detail": "Database is unavailable. Try again shortly."})
