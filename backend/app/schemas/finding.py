from datetime import datetime
from pydantic import BaseModel, ConfigDict

from app.db.models import FindingConfidence, FindingSeverity


class FindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scan_id: int
    tool: str
    rule_id: str
    title: str
    description: str
    severity: FindingSeverity
    confidence: FindingConfidence
    file_path: str
    line_number: int | None
    code_snippet: str | None
    cwe_id: str | None
    cwe_name: str | None
    owasp_category: str | None
    remediation_category: str
    remediation_guidance: str
    analysis_available: bool = False
    created_at: datetime

    @classmethod
    def from_model(cls, finding):
        return cls.model_validate(finding, from_attributes=True).model_copy(
            update={"analysis_available": finding.analysis is not None}
        )
