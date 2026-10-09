from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.repositories.finding_repository import get_findings_for_scan
from app.db.repositories.scan_repository import get_scan
from app.schemas.finding import FindingResponse
from app.schemas.analysis import AnalysisResponse
from app.schemas.scan import ScanDetailResponse, ScanUploadResponse
from app.llm.base import ProviderError
from app.llm.factory import get_security_analysis_provider
from app.services.analysis_service import analyze_finding
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
    return [FindingResponse.from_model(finding) for finding in get_findings_for_scan(
        db, scan_id, offset=offset, limit=limit
    )]


@router.post("/findings/{finding_id}/analysis", response_model=AnalysisResponse, status_code=201)
def create_finding_analysis(finding_id: int, db: Session = Depends(get_db)) -> AnalysisResponse:
    from app.db.repositories.finding_repository import get_finding

    finding = get_finding(db, finding_id)
    if finding is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found.")
    try:
        provider = get_security_analysis_provider()
        return analyze_finding(db, finding, provider)
    except ProviderError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Security analysis is currently unavailable.",
        )


@router.get("/findings/{finding_id}/analysis", response_model=AnalysisResponse)
def read_finding_analysis(finding_id: int, db: Session = Depends(get_db)) -> AnalysisResponse:
    from app.db.repositories.finding_repository import get_finding

    finding = get_finding(db, finding_id)
    if finding is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found.")
    if finding.analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found.")
    return finding.analysis
