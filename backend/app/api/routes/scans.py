from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.scan import ScanUploadResponse
from app.services.upload_service import upload_python_file


router = APIRouter()


@router.post("/scans", response_model=ScanUploadResponse, status_code=201)
async def create_scan_from_upload(
    file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
) -> ScanUploadResponse:
    return await upload_python_file(db, file)
