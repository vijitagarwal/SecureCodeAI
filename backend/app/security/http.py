import asyncio
import re
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
        self.analysis_slots = threading.BoundedSemaphore(settings.max_concurrent_analyses)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope["path"].startswith("/api/"):
            return await self.app(scope, receive, send)
        if scope["path"] in {"/api/health", "/api/live"} or scope["method"] == "OPTIONS":
            return await self.app(scope, receive, send)

        async def reject(code, detail, headers=None):
            await JSONResponse({"detail": detail}, status_code=code, headers=headers)(scope, receive, send)

        headers = dict(scope["headers"])
        for name in (b"authorization", b"content-length", b"transfer-encoding"):
            if sum(key == name for key, _ in scope["headers"]) > 1:
                return await reject(400, "Ambiguous request headers.")
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
        is_analysis = scope["path"].rstrip("/").endswith("/analysis") and scope["method"] == "POST"
        if is_analysis and not self.analysis_slots.acquire(blocking=False):
            return await reject(429, "Analysis capacity is busy. Try again shortly.", {"Retry-After": "5"})
        if is_scan and not self.scan_slots.acquire(blocking=False):
            return await reject(429, "Scanner capacity is busy. Try again shortly.", {"Retry-After": "5"})
        try:
            if scope["method"] in {"POST", "PUT", "PATCH"}:
                limit = settings.max_upload_size_bytes + 65536 if is_scan else 65536
                raw_length = headers.get(b"content-length", b"0")
                if not re.fullmatch(rb"[0-9]{1,20}", raw_length):
                    return await reject(400, "Invalid request length.")
                if b"content-length" in headers and b"transfer-encoding" in headers:
                    return await reject(400, "Ambiguous request framing.")
                length = int(raw_length)
                if length > limit:
                    return await reject(413, "The request exceeds the configured size limit.")

                async def read_body():
                    body = bytearray()
                    while True:
                        message = await receive()
                        if message["type"] == "http.disconnect":
                            return None
                        chunk = message.get("body", b"")
                        if len(body) + len(chunk) > limit:
                            raise OverflowError
                        body.extend(chunk)
                        if not message.get("more_body", False):
                            if b"content-length" in headers and len(body) != length:
                                raise ValueError
                            return bytes(body)

                try:
                    body = await asyncio.wait_for(read_body(), timeout=30)
                except OverflowError:
                    return await reject(413, "The request exceeds the configured size limit.")
                except ValueError:
                    return await reject(400, "Request length does not match its body.")
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

                if is_scan or is_analysis:
                    return await _finish_work(self.app(scope, replay, send))
                return await self.app(scope, replay, send)
            return await self.app(scope, receive, send)
        finally:
            if is_scan:
                self.scan_slots.release()
            if is_analysis:
                self.analysis_slots.release()


async def _finish_work(awaitable):
    """Retain slots, sessions and upload handles until bounded worker work finishes.

    asyncio task cancellation can otherwise abandon an AnyIO worker thread. A
    disconnected caller does not cancel a submitted scan; it can reopen history.
    Force-killing the API process still requires offline operator recovery.
    """
    task = asyncio.create_task(awaitable)
    cancelled = False
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            cancelled = True
    if cancelled:
        # Retrieve a possible exception so it is not logged with request data.
        if not task.cancelled():
            task.exception()
        raise asyncio.CancelledError
    return task.result()
