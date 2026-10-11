"""record the provider used to produce saved guidance"""
from alembic import op
import sqlalchemy as sa

revision = "0004_analysis_provenance"
down_revision = "0003_scan_integrity"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("security_analyses", sa.Column("provider", sa.String(40), nullable=False, server_default="mock"))
    op.add_column("security_analyses", sa.Column("model", sa.String(120), nullable=True))
    op.execute("UPDATE findings SET cwe_id = 'CWE-502', cwe_name = 'Deserialization of Untrusted Data' WHERE tool = 'bandit' AND rule_id = 'B506'")


def downgrade():
    op.drop_column("security_analyses", "model")
    op.drop_column("security_analyses", "provider")
