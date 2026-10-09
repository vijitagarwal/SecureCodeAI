"""add finding enrichment and security analysis

Revision ID: 0002_enrichment_analysis
Revises: 0001_scan_finding
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0002_enrichment_analysis"
down_revision: str | None = "0001_scan_finding"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("findings", sa.Column("cwe_id", sa.String(length=20), nullable=True))
    op.add_column("findings", sa.Column("cwe_name", sa.String(length=255), nullable=True))
    op.add_column("findings", sa.Column("owasp_category", sa.String(length=120), nullable=True))
    op.add_column("findings", sa.Column("remediation_category", sa.String(length=80), nullable=False, server_default="manual-review"))
    op.add_column("findings", sa.Column("remediation_guidance", sa.Text(), nullable=False, server_default=""))
    op.create_table(
        "security_analyses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("finding_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("finding_summary", sa.String(length=2000), nullable=False),
        sa.Column("root_cause", sa.Text(), nullable=False),
        sa.Column("security_impact", sa.Text(), nullable=False),
        sa.Column("false_positive_assessment", sa.String(length=2000), nullable=False),
        sa.Column("remediation", sa.Text(), nullable=False),
        sa.Column("fixed_code", sa.Text(), nullable=True),
        sa.Column("diff", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("status IN ('completed', 'failed')", name="ck_security_analyses_status"),
        sa.ForeignKeyConstraint(["finding_id"], ["findings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("finding_id"),
    )
    op.create_index("ix_security_analyses_finding_id", "security_analyses", ["finding_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_security_analyses_finding_id", table_name="security_analyses")
    op.drop_table("security_analyses")
    op.drop_column("findings", "remediation_guidance")
    op.drop_column("findings", "remediation_category")
    op.drop_column("findings", "owasp_category")
    op.drop_column("findings", "cwe_name")
    op.drop_column("findings", "cwe_id")
