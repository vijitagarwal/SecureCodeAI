from datetime import datetime
from typing import Any

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
    raw_metadata: dict[str, Any] | None
    created_at: datetime
