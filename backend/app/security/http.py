import asyncio
import threading

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from starlette.responses import JSONResponse

from app.core.config import settings
from app.security.access import require_workspace_access


class RequestBoundaryMiddleware:
    """Authenticate before multipart parsing; bound request bytes and active scans.

    Capacity is per API worker. Excess scans fail quickly rather than accumulating
    an unbounded queue of uploads or subprocesses.
    """

    def __init__(self, app):
        self.app = app
        self.scan_slots = threading.BoundedSemaphore(settings.max_concurrent_scans)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope["path"].startswith("/api/"):
            return await self.app(scope, receive, send)
        if scope["path"] == "/api/health" or scope["method"] == "OPTIONS":
            return await self.app(scope, receive, send)

        async def reject(code, detail, headers=None):
            await JSONResponse({"detail": detail}, status_code=code, headers=headers)(scope, receive, send)

        headers = dict(scope["headers"])
        auth = headers.get(b"authorization", b"").decode("latin-1").split(" ", 1)
        credentials = (
            HTTPAuthorizationCredentials(scheme=auth[0], credentials=auth[1])
            if len(auth) == 2 and auth[0].lower() == "bearer" and auth[1]
            else None
        )
        try:
            require_workspace_access(credentials)
        except HTTPException as error:
            return await reject(error.status_code, error.detail, error.headers)

        is_scan = scope["path"].rstrip("/") == "/api/scans" and scope["method"] == "POST"
        if is_scan and not self.scan_slots.acquire(blocking=False):
            return await reject(429, "Scanner capacity is busy. Try again shortly.", {"Retry-After": "5"})
        try:
            if scope["method"] in {"POST", "PUT", "PATCH"}:
                limit = settings.max_upload_size_bytes + 65536 if is_scan else 65536
                try:
                    length = int(headers.get(b"content-length", b"0"))
                except ValueError:
                    return await reject(400, "Invalid request length.")
                if length < 0 or length > limit:
                    return await reject(413, "The request exceeds the configured size limit.")

                async def read_body():
                    body = bytearray()
                    while True:
                        message = await receive()
                        if message["type"] == "http.disconnect":
                            return None
                        body.extend(message.get("body", b""))
                        if len(body) > limit:
                            raise OverflowError
                        if not message.get("more_body", False):
                            return bytes(body)

                try:
                    body = await asyncio.wait_for(read_body(), timeout=30)
                except OverflowError:
                    return await reject(413, "The request exceeds the configured size limit.")
                except TimeoutError:
                    return await reject(408, "Upload timed out.")
                if body is None:
                    return
                delivered = False

                async def replay():
                    nonlocal delivered
                    if not delivered:
                        delivered = True
                        return {"type": "http.request", "body": body, "more_body": False}
                    return await receive()

                return await self.app(scope, replay, send)
            return await self.app(scope, receive, send)
        finally:
            if is_scan:
                self.scan_slots.release()
