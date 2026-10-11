import secrets

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings


bearer = HTTPBearer(auto_error=False)


def require_workspace_access(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> None:
    """One operator-owned workspace; fail closed until an access key is configured."""
    if settings.api_key is None:
        raise HTTPException(503, "Workspace access is not configured. Set API_KEY on the server.")
    if credentials is None or len(credentials.credentials) > 256:
        raise HTTPException(401, "A valid workspace access key is required.", headers={"WWW-Authenticate": "Bearer"})
    if credentials is None or not secrets.compare_digest(
        credentials.credentials.encode(), settings.api_key.get_secret_value().encode()
    ):
        raise HTTPException(401, "A valid workspace access key is required.", headers={"WWW-Authenticate": "Bearer"})
