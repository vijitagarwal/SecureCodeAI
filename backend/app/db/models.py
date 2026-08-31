from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class ScanStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class FindingSeverity(StrEnum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class FindingConfidence(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Scan(Base):
    __tablename__ = "scans"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed')",
            name="ck_scans_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[ScanStatus] = mapped_column(
        Enum(
            ScanStatus,
            native_enum=False,
            values_callable=lambda enum_type: [member.value for member in enum_type],
            length=20,
        ),
        nullable=False,
        default=ScanStatus.QUEUED,
    )
    scanner_names: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    total_findings: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    critical_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    high_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    medium_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    low_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    findings: Mapped[list["Finding"]] = relationship(
        back_populates="scan",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Finding(Base):
    __tablename__ = "findings"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO')",
            name="ck_findings_severity",
        ),
        CheckConstraint(
            "confidence IN ('HIGH', 'MEDIUM', 'LOW')",
            name="ck_findings_confidence",
        ),
        Index("ix_findings_scan_id", "scan_id"),
        Index("ix_findings_severity", "severity"),
        Index("ix_findings_tool", "tool"),
        Index("ix_findings_rule_id", "rule_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scan_id: Mapped[int] = mapped_column(
        ForeignKey("scans.id", ondelete="CASCADE"), nullable=False
    )
    tool: Mapped[str] = mapped_column(String(100), nullable=False)
    rule_id: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[FindingSeverity] = mapped_column(
        Enum(
            FindingSeverity,
            native_enum=False,
            values_callable=lambda enum_type: [member.value for member in enum_type],
            length=10,
        ),
    )
    confidence: Mapped[FindingConfidence] = mapped_column(
        Enum(
            FindingConfidence,
            native_enum=False,
            values_callable=lambda enum_type: [member.value for member in enum_type],
            length=10,
        ),
    )
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    line_number: Mapped[int | None] = mapped_column(Integer)
    code_snippet: Mapped[str | None] = mapped_column(Text)
    raw_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    scan: Mapped[Scan] = relationship(back_populates="findings")
