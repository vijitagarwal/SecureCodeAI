from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.security.diff_validation import contains_unsafe_diff_path


class AnalysisStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisContent(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid", allow_inf_nan=False)

    finding_summary: str = Field(min_length=1, max_length=2000)
    root_cause: str = Field(min_length=1, max_length=4000)
    security_impact: str = Field(min_length=1, max_length=4000)
    false_positive_assessment: str = Field(min_length=1, max_length=2000)
    remediation: str = Field(min_length=1, max_length=4000)
    fixed_code: str | None = Field(default=None, max_length=10000)
    diff: str | None = Field(default=None, max_length=20000)
    confidence: float = Field(ge=0, le=1)

    @field_validator("finding_summary", "root_cause", "security_impact", "false_positive_assessment", "remediation")
    @classmethod
    def nonempty_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Analysis text must not be empty.")
        return value.strip()

    @field_validator("diff")
    @classmethod
    def validate_diff(cls, value: str | None) -> str | None:
        if value is not None and contains_unsafe_diff_path(value):
            raise ValueError("Diff contains an unsafe path reference.")
        return value


class AnalysisResponse(AnalysisContent):
    id: int
    finding_id: int
    status: AnalysisStatus
    provider: str = "mock"
    model: str | None = None
    created_at: datetime
