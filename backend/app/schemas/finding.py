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
    created_at: datetime
