from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.repositories.finding_repository import get_findings_for_scan
from app.db.repositories.scan_repository import get_scan
from app.schemas.finding import FindingResponse
from app.schemas.scan import ScanDetailResponse, ScanUploadResponse
from app.services.upload_service import upload_python_file


router = APIRouter()


@router.post("/scans", response_model=ScanUploadResponse, status_code=201)
async def create_scan_from_upload(
    file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
) -> ScanUploadResponse:
    return await upload_python_file(db, file)


@router.get("/scans/{scan_id}", response_model=ScanDetailResponse)
def read_scan(scan_id: int, db: Session = Depends(get_db)) -> ScanDetailResponse:
    scan = get_scan(db, scan_id)
    if scan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found.")
    return scan


@router.get("/scans/{scan_id}/findings", response_model=list[FindingResponse])
def read_scan_findings(
    scan_id: int,
    db: Session = Depends(get_db),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
) -> list[FindingResponse]:
    if get_scan(db, scan_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found.")
    return get_findings_for_scan(db, scan_id, offset=offset, limit=limit)
