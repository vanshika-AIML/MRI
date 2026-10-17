"""Store self-declared profession separately from authorization roles."""
from alembic import op
import sqlalchemy as sa

revision = "005_self_declared_profession"
down_revision = "004_token_revocation"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column("profession", sa.String(length=32), nullable=False, server_default="viewer"),
    )


def downgrade():
    op.drop_column("users", "profession")
