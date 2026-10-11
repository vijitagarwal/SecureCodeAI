import logging
import os
from pathlib import Path, PureWindowsPath
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.db.repositories.scan_repository import create_scan
from app.scanners.bandit import BanditScanner
from app.schemas.scan import ScanUploadResponse
from app.services.scanner_service import run_scan


logger = logging.getLogger(__name__)
CHUNK_SIZE = 64 * 1024


def _validate_filename(filename: str | None) -> str:
    if not filename or len(filename) > 255:
        raise HTTPException(400, "A valid filename is required.")
    if any(ord(char) < 32 or ord(char) == 127 for char in filename):
        raise HTTPException(400, "Path separators are not allowed in filenames.")
    # Browsers may send C:\fakepath\name.py. Only the basename is display metadata.
    if PureWindowsPath(filename).is_absolute():
        filename = PureWindowsPath(filename).name
    elif Path(filename).name != filename or PureWindowsPath(filename).name != filename:
        raise HTTPException(400, "Path separators are not allowed in filenames.")
    if ":" in filename or filename in {"", ".", ".."}:
        raise HTTPException(400, "A valid filename is required.")
    if Path(filename).suffix.lower() != ".py":
        raise HTTPException(415, "Only Python (.py) files are supported.")
    return filename


def _store_and_scan(bind, upload: UploadFile | None) -> ScanUploadResponse:
    # A SQLAlchemy Session is not thread-safe. The request dependency supplies
    # the configured Engine/bind; the blocking worker owns its own Session.
    db = sessionmaker(bind=bind, autoflush=False, autocommit=False)()
    upload_path: Path | None = None
    owns_path = False
    try:
        filename = _validate_filename(upload.filename if upload else None)
        upload_directory = Path(settings.upload_dir)
        upload_directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        upload_path = upload_directory / f"{uuid4().hex}.py"
        bytes_written = 0
        descriptor = os.open(upload_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o600)
        owns_path = True
        with os.fdopen(descriptor, "wb") as target:
            while chunk := upload.file.read(CHUNK_SIZE):
                bytes_written += len(chunk)
                if bytes_written > settings.max_upload_size_bytes:
                    raise HTTPException(413, "The uploaded file exceeds the configured size limit.")
                target.write(chunk)
        if bytes_written == 0:
            raise HTTPException(400, "The uploaded file is empty.")

        # Keep all blocking database/file/subprocess work off the ASGI event loop.
        scan = create_scan(db, name=filename, scanner_names=["bandit"])
        db.commit()
        run_scan(db, scan, str(upload_path), BanditScanner())
        db.refresh(scan)
        return ScanUploadResponse(
            scan_id=scan.id, status=scan.status, filename=filename,
            total_findings=scan.total_findings, failure_reason=scan.failure_reason,
        )
    except HTTPException:
        db.rollback()
        raise
    except (OSError, SQLAlchemyError):
        db.rollback()
        logger.error("Upload storage failed")
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "The upload could not be stored.")
    finally:
        if owns_path and upload_path is not None:
            try:
                upload_path.unlink(missing_ok=True)
            except OSError:
                logger.error("Temporary upload cleanup failed")
        db.close()


async def upload_python_file(db: Session, upload: UploadFile | None) -> ScanUploadResponse:
    try:
        return await run_in_threadpool(_store_and_scan, db.get_bind(), upload)
    finally:
        if upload:
            await upload.close()
