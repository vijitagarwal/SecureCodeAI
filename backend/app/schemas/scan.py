from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import ScanStatus


class ScanCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    scanner_names: list[str] = Field(default_factory=list)


class ScanUploadResponse(BaseModel):
    scan_id: int
    status: ScanStatus
    filename: str


class ScanStatusUpdate(BaseModel):
    status: ScanStatus


class ScanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    status: ScanStatus
    scanner_names: list[str]
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    total_findings: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int


class ScanSummary(BaseModel):
    scan_id: int
    total_findings: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
