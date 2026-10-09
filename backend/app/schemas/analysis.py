from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.security.diff_validation import contains_unsafe_diff_path


class AnalysisStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    finding_id: int
    status: AnalysisStatus
    finding_summary: str = Field(max_length=2000)
    root_cause: str = Field(max_length=4000)
    security_impact: str = Field(max_length=4000)
    false_positive_assessment: str = Field(max_length=2000)
    remediation: str = Field(max_length=4000)
    fixed_code: str | None = Field(default=None, max_length=10000)
    diff: str | None = Field(default=None, max_length=20000)
    confidence: float = Field(ge=0, le=1)
    created_at: datetime

    @field_validator("diff")
    @classmethod
    def validate_diff(cls, value: str | None) -> str | None:
        if value is not None and contains_unsafe_diff_path(value):
            raise ValueError("Diff contains an unsafe path reference.")
        return value
