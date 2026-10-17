"""Persist account token generation for refresh rotation and logout."""
from alembic import op
import sqlalchemy as sa

revision = "004_token_revocation"
down_revision = "003_owned_reports"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('token_version', sa.Integer(), nullable=False, server_default='0'))


def downgrade():
    op.drop_column('users', 'token_version')
