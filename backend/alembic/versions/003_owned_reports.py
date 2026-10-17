"""Persist owned reports with the same ID returned to clients."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "003_owned_reports"
down_revision = "002_authentication"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("analysis_reports",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("owner_id", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("result", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_index("ix_analysis_reports_owner_id", "analysis_reports", ["owner_id"])


def downgrade():
    op.drop_table("analysis_reports")
