"""Add frozen Phase 9 authentication, annotation, and audit schema."""
from alembic import op
revision = "002_authentication"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("\nCREATE TABLE users (\n\temail VARCHAR(255) NOT NULL, \n\tusername VARCHAR(64) NOT NULL, \n\tpassword_hash VARCHAR(255) NOT NULL, \n\tfull_name VARCHAR(255), \n\trole VARCHAR(32) DEFAULT 'viewer' NOT NULL, \n\tis_active BOOLEAN DEFAULT 'true' NOT NULL, \n\tis_verified BOOLEAN DEFAULT 'false' NOT NULL, \n\tfailed_login_count INTEGER DEFAULT '0' NOT NULL, \n\tlocked_until TIMESTAMP WITH TIME ZONE, \n\tlast_login_at TIMESTAMP WITH TIME ZONE, \n\tid UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now(), \n\tPRIMARY KEY (id)\n)\n\n")
    op.execute('CREATE UNIQUE INDEX ix_users_email ON users (email)')
    op.execute('CREATE INDEX ix_users_role ON users (role)')
    op.execute('CREATE UNIQUE INDEX ix_users_username ON users (username)')
    op.execute("\nCREATE TABLE analysis_annotations (\n\tanalysis_id VARCHAR(64) NOT NULL, \n\tuser_id UUID NOT NULL, \n\tannotation_text TEXT NOT NULL, \n\tfield_name VARCHAR(128), \n\tis_original BOOLEAN DEFAULT 'false' NOT NULL, \n\tversion INTEGER NOT NULL, \n\tsuperseded_by_id UUID, \n\tid UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now(), \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, \n\tFOREIGN KEY(superseded_by_id) REFERENCES analysis_annotations (id) ON DELETE SET NULL\n)\n\n")
    op.execute('CREATE INDEX ix_analysis_annotations_analysis_id ON analysis_annotations (analysis_id)')
    op.execute('CREATE INDEX ix_analysis_annotations_user_id ON analysis_annotations (user_id)')
    op.execute('\nCREATE TABLE audit_logs (\n\tuser_id UUID, \n\taction VARCHAR(128) NOT NULL, \n\tresource_type VARCHAR(64), \n\tresource_id VARCHAR(255), \n\tip_address VARCHAR(45), \n\tuser_agent TEXT, \n\toutcome VARCHAR(16) NOT NULL, \n\tdetails JSONB, \n\tid UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now(), \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL\n)\n\n')
    op.execute('CREATE INDEX ix_audit_logs_action ON audit_logs (action)')
    op.execute('CREATE INDEX ix_audit_logs_resource ON audit_logs (resource_type, resource_id)')
    op.execute('CREATE INDEX ix_audit_logs_user_action ON audit_logs (user_id, action)')
    op.execute('CREATE INDEX ix_audit_logs_user_id ON audit_logs (user_id)')


def downgrade():
    for name in ("audit_logs", "analysis_annotations", "users"):
        op.drop_table(name)
