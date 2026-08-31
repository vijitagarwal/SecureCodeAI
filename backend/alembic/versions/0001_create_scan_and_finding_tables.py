"""create scan and finding tables

Revision ID: 0001_scan_finding
Revises:
Create Date: 2026-08-31

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0001_scan_finding"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("scanner_names", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("total_findings", sa.Integer(), server_default="0", nullable=False),
        sa.Column("critical_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("high_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("medium_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("low_count", sa.Integer(), server_default="0", nullable=False),
        sa.CheckConstraint("status IN ('queued', 'running', 'completed', 'failed')", name="ck_scans_status"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "findings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scan_id", sa.Integer(), nullable=False),
        sa.Column("tool", sa.String(length=100), nullable=False),
        sa.Column("rule_id", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=10), nullable=False),
        sa.Column("confidence", sa.String(length=10), nullable=False),
        sa.Column("file_path", sa.String(length=1000), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=True),
        sa.Column("code_snippet", sa.Text(), nullable=True),
        sa.Column("raw_metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("severity IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO')", name="ck_findings_severity"),
        sa.CheckConstraint("confidence IN ('HIGH', 'MEDIUM', 'LOW')", name="ck_findings_confidence"),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_findings_scan_id", "findings", ["scan_id"])
    op.create_index("ix_findings_severity", "findings", ["severity"])
    op.create_index("ix_findings_tool", "findings", ["tool"])
    op.create_index("ix_findings_rule_id", "findings", ["rule_id"])


def downgrade() -> None:
    op.drop_index("ix_findings_rule_id", table_name="findings")
    op.drop_index("ix_findings_tool", table_name="findings")
    op.drop_index("ix_findings_severity", table_name="findings")
    op.drop_index("ix_findings_scan_id", table_name="findings")
    op.drop_table("findings")
    op.drop_table("scans")
