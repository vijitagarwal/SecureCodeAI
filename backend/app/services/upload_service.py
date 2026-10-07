import logging
from pathlib import Path, PureWindowsPath
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.repositories.scan_repository import create_scan
from app.scanners.bandit import BanditScanner
from app.schemas.scan import ScanUploadResponse
from app.services.scanner_service import run_scan


logger = logging.getLogger(__name__)
CHUNK_SIZE = 1024 * 1024


def _validate_filename(filename: str | None) -> str:
    if not filename or len(filename) > 255:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A valid filename is required.")
    if "\x00" in filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Path separators are not allowed in filenames.")
    if PureWindowsPath(filename).is_absolute():
        filename = PureWindowsPath(filename).name
    elif Path(filename).name != filename or PureWindowsPath(filename).name != filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Path separators are not allowed in filenames.")
    if Path(filename).suffix.lower() != ".py":
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Only Python (.py) files are supported.")
    return filename


async def upload_python_file(db: Session, upload: UploadFile | None) -> ScanUploadResponse:
    filename = _validate_filename(upload.filename if upload else None)
    upload_path: Path | None = None
    scan = None

    try:
        scan = create_scan(db, name=filename)
        upload_directory = Path(settings.upload_dir)
        upload_directory.mkdir(parents=True, exist_ok=True)
        upload_path = upload_directory / f"{uuid4().hex}.py"

        bytes_written = 0
        with upload_path.open("xb") as target:
            while chunk := await upload.read(CHUNK_SIZE):
                bytes_written += len(chunk)
                if bytes_written > settings.max_upload_size_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        detail="The uploaded file exceeds the configured size limit.",
                    )
                target.write(chunk)

        db.commit()
        db.refresh(scan)
        run_scan(db, scan, str(upload_path), BanditScanner())
        db.refresh(scan)
        return ScanUploadResponse(
            scan_id=scan.id,
            status=scan.status,
            filename=filename,
            total_findings=scan.total_findings,
        )
    except HTTPException:
        db.rollback()
        if upload_path:
            upload_path.unlink(missing_ok=True)
        raise
    except (OSError, SQLAlchemyError):
        db.rollback()
        if upload_path:
            upload_path.unlink(missing_ok=True)
        logger.exception("Failed to persist uploaded file")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The upload could not be stored.",
        )
    except Exception:
        db.rollback()
        if upload_path:
            upload_path.unlink(missing_ok=True)
        logger.exception("Unexpected failure while processing uploaded file")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The upload could not be stored.",
        )
    finally:
        if upload:
            await upload.close()
