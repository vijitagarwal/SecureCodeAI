from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.repositories.finding_repository import get_findings_for_scan
from app.core.config import settings
from app.db.models import FindingSeverity, ScanStatus
from app.db.repositories.scan_repository import delete_scan, get_scan, list_scans
from app.schemas.finding import FindingResponse
from app.schemas.analysis import AnalysisResponse
from app.schemas.scan import ScanDetailResponse, ScanListResponse, ScanResponse, ScanUploadResponse
from app.llm.base import ProviderError
from app.llm.factory import get_security_analysis_provider
from app.services.analysis_service import analyze_finding
from app.services.upload_service import upload_python_file
from app.security.access import require_workspace_access


router = APIRouter(dependencies=[Depends(require_workspace_access)])


@router.post("/scans", response_model=ScanUploadResponse, status_code=201)
async def create_scan_from_upload(
    file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
) -> ScanUploadResponse:
    return await upload_python_file(db, file)


@router.get("/scans", response_model=ScanListResponse)
def read_scans(
    db: Session = Depends(get_db),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> ScanListResponse:
    scans, total = list_scans(db, offset=offset, limit=limit)
    return ScanListResponse(
        items=[ScanResponse.model_validate(scan, from_attributes=True) for scan in scans],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/scans/{scan_id}", response_model=ScanDetailResponse)
def read_scan(scan_id: int, db: Session = Depends(get_db)) -> ScanDetailResponse:
    scan = get_scan(db, scan_id)
    if scan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found.")
    return scan


@router.get("/workspace")
def read_workspace():
    return {
        "max_upload_size_bytes": settings.max_upload_size_bytes,
        "analysis_provider": settings.ai_provider,
        "remote_analysis": settings.ai_provider != "mock",
    }


@router.delete("/scans/{scan_id}", status_code=204)
def remove_scan(scan_id: int, db: Session = Depends(get_db)) -> Response:
    scan = get_scan(db, scan_id)
    if scan is None:
        raise HTTPException(404, "Scan not found.")
    if scan.status in {ScanStatus.QUEUED, ScanStatus.RUNNING}:
        raise HTTPException(409, "An active scan cannot be deleted.")
    delete_scan(db, scan)
    db.commit()
    return Response(status_code=204)


@router.get("/scans/{scan_id}/report")
def download_report(scan_id: int, db: Session = Depends(get_db)) -> JSONResponse:
    scan = get_scan(db, scan_id)
    if scan is None:
        raise HTTPException(404, "Scan not found.")
    if scan.status not in {ScanStatus.COMPLETED, ScanStatus.FAILED}:
        raise HTTPException(409, "This scan has not finished yet.")
    findings = get_findings_for_scan(db, scan_id, limit=settings.max_findings + 1)
    if len(findings) > settings.max_findings:
        raise HTTPException(409, "This legacy scan exceeds the report limit. Retrieve its paginated findings.")
    return JSONResponse(
        headers={"Content-Disposition": f'attachment; filename="securecode-scan-{scan_id}.json"'},
        content={
            "report_version": 1,
            "scan": ScanResponse.model_validate(scan).model_dump(mode="json"),
            "findings": [
                {**FindingResponse.from_model(finding).model_dump(mode="json"),
                 "analysis": AnalysisResponse.model_validate(finding.analysis).model_dump(mode="json")
                 if finding.analysis else None}
                for finding in findings
            ],
        },
    )


@router.get("/scans/{scan_id}/findings", response_model=list[FindingResponse])
def read_scan_findings(
    scan_id: int,
    db: Session = Depends(get_db),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    severity: FindingSeverity | None = Query(default=None),
) -> list[FindingResponse]:
    if get_scan(db, scan_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found.")
    return [
        FindingResponse.from_model(finding)
        for finding in get_findings_for_scan(
            db, scan_id, offset=offset, limit=limit, severity=severity
        )
    ]


@router.post("/findings/{finding_id}/analysis", response_model=AnalysisResponse, status_code=201)
def create_finding_analysis(finding_id: int, db: Session = Depends(get_db)) -> AnalysisResponse:
    from app.db.repositories.finding_repository import get_finding

    finding = get_finding(db, finding_id)
    if finding is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found.")
    if finding.analysis is not None:
        return AnalysisResponse.model_validate(finding.analysis)
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
