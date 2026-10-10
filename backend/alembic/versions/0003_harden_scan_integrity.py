"""add complete scan counters and integrity checks

Revision ID: 0003_scan_integrity
Revises: 0002_enrichment_analysis
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0003_scan_integrity"
down_revision: str | None = "0002_enrichment_analysis"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("scans") as batch_op:
        batch_op.add_column(sa.Column("info_count", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("failure_reason", sa.String(length=500), nullable=True))
        batch_op.create_check_constraint(
            "ck_scans_nonnegative_counts",
            "total_findings >= 0 AND critical_count >= 0 AND high_count >= 0 "
            "AND medium_count >= 0 AND low_count >= 0 AND info_count >= 0",
        )
    with op.batch_alter_table("findings") as batch_op:
        batch_op.create_check_constraint(
            "ck_findings_positive_line_number",
            "line_number IS NULL OR line_number > 0",
        )
    with op.batch_alter_table("security_analyses") as batch_op:
        batch_op.create_check_constraint(
            "ck_security_analyses_confidence",
            "confidence >= 0 AND confidence <= 1",
        )
    op.execute("UPDATE scans SET info_count = (SELECT COUNT(*) FROM findings WHERE findings.scan_id = scans.id AND severity = 'INFO')")


def downgrade() -> None:
    with op.batch_alter_table("security_analyses") as batch_op:
        batch_op.drop_constraint("ck_security_analyses_confidence", type_="check")
    with op.batch_alter_table("findings") as batch_op:
        batch_op.drop_constraint("ck_findings_positive_line_number", type_="check")
    with op.batch_alter_table("scans") as batch_op:
        batch_op.drop_constraint("ck_scans_nonnegative_counts", type_="check")
        batch_op.drop_column("failure_reason")
        batch_op.drop_column("info_count")
